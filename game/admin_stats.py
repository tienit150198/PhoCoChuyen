"""Operator statistics ("Thống kê") for the admin dashboard, built so that the admin can
never slow the players down.

Endpoints (server.py), all admin only:
* GET /api/admin/stats/summary?range=7|30|90 -> get_summary(): the first screen in one
  call (players, activity, retention, feedback, AI, light server facts).
* GET /api/admin/stats/section?name=saves|system -> get_section(): the save-derived cards
  (play, economy, life, board) and the table sizes, loaded on demand.
* GET /api/admin/stats?range= -> get(): everything in one payload (the in-game tab).
Only aggregate numbers leave this module: no sid, token, csrf, password, e-mail, player
name or free text other than the operator's own feedback previews.

How players are protected
* No request ever reads a save. The summary is SQL on small tables and indexes: the day
  tables `stat_births` / `stat_active` kept by triggers (see SCHEMA; on PostgreSQL the
  same triggers live in game/pg_schema.py), the covering index stat_sessions_seen, and
  feedback / account rows.
* Every request-time read has a hard time budget and cannot write:
  - SQLite: a separate read-only connection (mode=ro, query_only), closed afterwards, with
    a progress handler that aborts past the budget. Each statement is its own short read
    snapshot, so no read can pin the WAL.
  - PostgreSQL: a READ ONLY transaction with SET LOCAL statement_timeout.
  Nothing here takes the writer lock on a request.
* The save-derived numbers and the table sizes come from ONE background job per database
  (a lock file elects the worker process that runs it; the others read its result file).
  The job keeps each save's compact row with the revision it was read at (in
  `<db>-adminstats-rows.json`), lists (sid, revision) from the covering index, and reads
  only the saves whose revision moved, a few dozen per statement, each chunk under a time
  budget, pausing three times as long as it worked between chunks (a quarter of one core at
  most). It reads the saves every SAVES_EVERY (30 min) from the SAMPLE (400) most recent ones,
  and waits, then gives the pass up, while the machine is busy with players (load average).
  It runs only while an operator has looked at the page in the last IDLE seconds, and
  writes its result to `<db>-adminstats.json` (atomic replace). Before its first pass is
  done the saves section answers {pending: true, progress}.
* Results are cached in memory: the summary per range for SUMMARY_TTL, the full payload for
  TTL. Concurrent requests for the same entry share one computation (single flight); a
  stale entry is served at once while one thread refreshes it.
* AI usage has no stored log, so `install_ai_counters()` wraps ai.chat, ai.clean_reply
  and ai.abusive with in-memory per-day counters ("since restart").
* Live counters (GET /api/admin/stats/section?name=live, cached LIVE_TTL): sessions active in
  the last 5 min / 1 h / 24 h, new players today, the database size, the backend, and the
  commands per minute with their p50/p90 latency. A handful of index range reads, never a
  save, never the job. Command timings: `install_command_timer()` wraps store.command with
  an in-memory per-minute histogram per worker process, flushed at most every CMD_FLUSH
  seconds to `<db>-adminstats-cmd.<pid>.json`; the admin merges the workers' files.
  `sessions.updated_at` is TEXT 'YYYY-MM-DD HH:MM:SS' (UTC) on both backends: it is compared
  with a threshold in that same text form (dbm.utc_text), never cast, so the covering index
  stat_sessions_seen serves the range.
* Play time (GET /api/admin/stats/section?name=playtime, cached PLAY_TTL): minutes per player
  per day, sessions, their distribution, the hours of the day and new players' first day, from
  `stat_play` (one row per save per day, kept by a trigger on receipts: one receipt = one game
  command; see "play time" below) and `stat_births`. Finished days are summed once per worker.
  backfill_play() seeds the last days from receipts, once, by hand (estimates: stat_play_est).
  Per-player rows are kept PLAY_KEEP_DAYS (60); upkeep() first sums each older day into
  stat_play_daily (kept), then deletes it.
* Giữ chân (GET /api/admin/stats/section?name=retention[&format=csv]): game/admin_retention.py,
  from the tables of game/retention.py. upkeep() (this job and the server's housekeeping) also
  runs retention.maintain(): rollups and pruning of those tables.

Is the snapshot current? (`snapshot` in the saves/system sections, `computed_at`/`age`/
`old` on the summary.) The job writes a heartbeat {pid, at, phase} into its own lock file.
A worker that cannot take the lock and sees no fresh heartbeat knows the lock is HELD
without a job running: an operator hold (e.g. a transient systemd unit that flock()s
`<db>-adminstats.lock` at peak hours so the save scan never competes with players) or a
stuck job. The hold is honoured: nothing here breaks it; the page says the save numbers are
held and from when. A lock left by a crashed process is no problem: flock() dies with its
process, the next request takes it over. A pass that fails is logged to stderr with its
message, recorded in the result (`errors`) and retried after its normal period (no retry
storm), and it never blocks the other passes.

Days are Vietnam days (UTC+7), matching the players.
"""
from __future__ import annotations
import bisect
import datetime
from array import array
import glob
import hashlib
import json
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path

from . import __version__
from . import kpi
from .pg_schema import PLAY_GAP, PLAY_IDLE_TAIL

try:  # PostgreSQL backend (game/db.py); a tree without it is SQLite only
    from . import db as dbm
except ImportError:  # pragma: no cover
    dbm = None

RANGES = (7, 30, 90)
TTL = 60.0                 # full payload (in-game tab)
# The saves section is expensive (each save is parsed whole): it is refreshed rarely, from a
# small sample, and never while the machine is busy serving players (see _Job.may_go).
SAVES_EVERY = float(os.environ.get('ADMIN_STATS_SAVES_EVERY', '1800') or 1800)  # seconds between two passes over the saves
BUSY_LOAD = float(os.environ.get('ADMIN_STATS_BUSY_LOAD', '0.7') or 0.7)  # the job waits while the 1-minute load average is over this per core
BUSY_WAIT = 60.0           # ... and gives the pass up after waiting this long (the next one tries again)
SUMMARY_TTL = 30.0
SYSTEM_EVERY = 120.0       # table sizes
SUMMARY_EVERY = 60.0       # the job's copy of the first screen (served when a live read runs out of time)
KPI_EVERY = float(os.environ.get('ADMIN_STATS_KPI_EVERY', '600') or 600)   # the investor overview (game/admin_kpi.py)
IDLE = 600.0               # the job stops this long after the last admin request
SAMPLE = max(100, int(os.environ.get('ADMIN_STATS_SAMPLE', '400') or 400))
KEEP_DAYS = 120            # stat_active history kept
PLAY_KEEP_DAYS = max(31, int(os.environ.get('ADMIN_STATS_PLAY_DAYS', '60') or 60))  # stat_play rows kept (older days: stat_play_daily only)
COHORT_DAYS = 30           # retention looks at players who started in the last 30 days (or the range, if longer)
TZ = '+7 hours'
VN = datetime.timezone(datetime.timedelta(hours=7))
STARTED = time.time()
TOP_CAREERS = 20
WALLET_BUCKETS = ((None, 0, 'Nợ (< 0)'), (0, 100, '0–99'), (100, 500, '100–499'), (500, 2000, '500–1.999'), (2000, None, '≥ 2.000'))
LEVEL_CAP = 6              # "6+"
AI_DAYS = 14
# Time budgets (milliseconds).
REQUEST_MS = int(os.environ.get('ADMIN_STATS_REQUEST_MS', '1500') or 1500)   # all queries of one summary
STATEMENT_MS = int(os.environ.get('ADMIN_STATS_STATEMENT_MS', '1000') or 1000)  # one statement (PostgreSQL)
CHUNK_MS = 800             # one chunk of saves in the job
COUNT_MS = 250             # an exact COUNT(*) of one table in the job; past it the size is estimated
JOB_SUMMARY_MS = 30000     # the job's summary (a cold disk can take seconds per index); each statement is its own read
CHUNK = 40                 # saves per chunk (halved when a chunk runs out of time)
PAUSE = 3.0                # the job sleeps PAUSE x the time a chunk took (a quarter of one core at most)
LIVE_MS = int(os.environ.get('ADMIN_STATS_LIVE_MS', '800') or 800)  # all queries of the live counters
LIVE_TTL = 10.0            # live counters cached this long (per worker)
STALE_AFTER = 600.0        # a snapshot older than this (beyond its normal period) is shown as old
BEAT_EVERY = 10.0          # the job's heartbeat in its lock file ...
BEAT_STALE = 150.0         # ... and past this without one, a taken lock means "held", not "running"
SAVES_RETRY = 300.0        # a saves pass that FAILED is tried again after this (not at once)
CMD_FLUSH = 10.0           # a worker writes its command timings at most this often
CMD_MINUTES = 15           # minutes of command timings kept
CMD_WINDOW = 5             # the page shows the last CMD_WINDOW minutes plus the current one
# Latency histogram (ms, upper bounds); one more bucket past the last edge.
CMD_EDGES = (2, 5, 10, 15, 20, 30, 40, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000, 3000, 5000, 10000)

_NOW = "((julianday('now') - 2440587.5) * 86400.0)"   # unix time with milliseconds, like PostgreSQL's epoch
SCHEMA = f"""
CREATE INDEX IF NOT EXISTS stat_sessions_seen ON sessions(updated_at, revision, sid);
CREATE TABLE IF NOT EXISTS stat_births (sid TEXT PRIMARY KEY, day TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS stat_births_day ON stat_births(day);
CREATE TABLE IF NOT EXISTS stat_active (day TEXT NOT NULL, sid TEXT NOT NULL, PRIMARY KEY(day, sid)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS stat_active_sid ON stat_active(sid);
CREATE TABLE IF NOT EXISTS stat_fb_ack (id INTEGER PRIMARY KEY, at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS stat_fb_created ON player_feedback(created_at);
CREATE INDEX IF NOT EXISTS stat_accounts_created ON accounts(created_at);
CREATE TRIGGER IF NOT EXISTS stat_session_born AFTER INSERT ON sessions BEGIN
  INSERT OR IGNORE INTO stat_births(sid, day) VALUES (NEW.sid, date('now', '{TZ}'));
END;
CREATE TRIGGER IF NOT EXISTS stat_session_active AFTER UPDATE OF updated_at ON sessions BEGIN
  INSERT OR IGNORE INTO stat_active(day, sid) VALUES (date('now', '{TZ}'), NEW.sid);
END;
CREATE TRIGGER IF NOT EXISTS stat_session_gone AFTER DELETE ON sessions BEGIN
  DELETE FROM stat_births WHERE sid = OLD.sid;
  DELETE FROM stat_active WHERE sid = OLD.sid;
END;
CREATE TABLE IF NOT EXISTS stat_play (day TEXT NOT NULL, sid TEXT NOT NULL, secs INTEGER NOT NULL, sessions INTEGER NOT NULL,
  cmds INTEGER NOT NULL, first_at REAL NOT NULL, last_at REAL NOT NULL, hours INTEGER NOT NULL DEFAULT 0,
  sess_at REAL NOT NULL, lens TEXT NOT NULL DEFAULT '', PRIMARY KEY(day, sid)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS stat_play_sid ON stat_play(sid);
CREATE TABLE IF NOT EXISTS stat_play_est (day TEXT PRIMARY KEY, saves INTEGER NOT NULL, capped INTEGER NOT NULL, at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS stat_play_daily (day TEXT PRIMARY KEY, players INTEGER NOT NULL, secs INTEGER NOT NULL, sessions INTEGER NOT NULL,
  cmds INTEGER NOT NULL, data TEXT NOT NULL, at REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS stat_play_cmd AFTER INSERT ON receipts BEGIN
  INSERT INTO stat_play(day, sid, secs, sessions, cmds, first_at, last_at, hours, sess_at, lens)
  VALUES (date('now', '{TZ}'), NEW.sid, {PLAY_IDLE_TAIL}, 1, 1, {_NOW}, {_NOW},
          1 << CAST(strftime('%H', 'now', '{TZ}') AS INTEGER), {_NOW}, '')
  ON CONFLICT(day, sid) DO UPDATE SET
    secs = secs + CASE WHEN excluded.last_at - last_at <= {PLAY_GAP} THEN MAX(0, CAST(round(excluded.last_at - last_at) AS INTEGER)) ELSE {PLAY_IDLE_TAIL} END,
    sessions = sessions + CASE WHEN excluded.last_at - last_at <= {PLAY_GAP} THEN 0 ELSE 1 END,
    cmds = cmds + 1,
    last_at = MAX(last_at, excluded.last_at),
    hours = hours | excluded.hours,
    sess_at = CASE WHEN excluded.last_at - last_at <= {PLAY_GAP} THEN sess_at ELSE excluded.last_at END,
    lens = CASE WHEN excluded.last_at - last_at <= {PLAY_GAP} THEN lens
                ELSE lens || (CAST(round(last_at - sess_at) AS INTEGER) + {PLAY_IDLE_TAIL}) || ',' END;
END;
CREATE TRIGGER IF NOT EXISTS stat_play_gone AFTER DELETE ON sessions BEGIN
  DELETE FROM stat_play WHERE sid = OLD.sid;
END;
CREATE TRIGGER IF NOT EXISTS stat_fb_seen AFTER UPDATE OF status ON player_feedback
  WHEN OLD.status = 'new' AND NEW.status != 'new' BEGIN
  INSERT OR IGNORE INTO stat_fb_ack(id, at) VALUES (NEW.id, NEW.updated_at);
END;
CREATE TRIGGER IF NOT EXISTS stat_fb_gone AFTER DELETE ON player_feedback BEGIN
  DELETE FROM stat_fb_ack WHERE id = OLD.id;
END;
"""
# PostgreSQL: tables, indexes and triggers come from game/pg_schema.py; these two indexes
# serve only the admin queries (small tables, built in milliseconds). Created here too so
# a database made by an older pg_schema gets them.
PG_INDEXES = (('stat_fb_created', 'CREATE INDEX IF NOT EXISTS stat_fb_created ON player_feedback (created_at)'),
              ('stat_accounts_created', 'CREATE INDEX IF NOT EXISTS stat_accounts_created ON accounts (created_at)'))


def _is_pg(db) -> bool:
    return getattr(db, 'dialect', 'sqlite') == 'pg'


def _store_pg(store) -> bool:
    return bool(getattr(store, 'pg', None))


def ensure(store) -> None:
    """Idempotent: indexes, day tables and triggers (see the module doc), and the investor KPI tables of
    game/kpi.py (stat_counters, stat_kpi_daily, stat_players: new tables only, nothing existing is altered)."""
    if _store_pg(store):
        _ensure_pg(store)
    else:
        with store.connect() as db:
            db.executescript(SCHEMA)
            db.executescript(kpi.SCHEMA)
    install_ai_counters(store)
    install_command_timer(store)


def _ensure_pg(store) -> None:
    """The admin indexes, skipped when present. Several workers start at once, and two
    concurrent CREATE INDEX IF NOT EXISTS can still collide: the loser just moves on (the
    admin queries work without the index, only slower)."""
    for name, sql in PG_INDEXES + kpi.PG_DDL:
        try:
            with store.connect() as db:
                if not db.execute('SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace '
                                  'WHERE n.nspname = current_schema() AND c.relname = ?', (name,)).fetchone():
                    db.execute(sql)
        except dbm.Error:
            pass


# ---------------------------------------------------------------- AI counters (in memory)
_ai_lock = threading.Lock()
_ai: dict[str, dict] = {}
_blocked: dict[str, set] = {}
AI_KEYS = ('calls', 'ok', 'failed', 'busy', 'rejected', 'guard')
# The store whose stat_counters keep the AI counts of every worker (kpi.add, `ai:<key>`): before 1.4.2 each worker
# process only had its own in-memory counts, so with WORKERS=8 the page showed ~1/8 of the calls, and 0 after a restart.
_ai_store = [None]
AI_TTL = 10.0
_ai_read: dict = {}   # db path -> (monotonic time, days)


def _today() -> str:
    return datetime.datetime.now(VN).date().isoformat()


def _bump(key: str, n: int = 1) -> None:
    day = _today()
    with _ai_lock:
        row = _ai.setdefault(day, {k: 0 for k in AI_KEYS})
        row[key] += n
        if len(_ai) > AI_DAYS:
            for old in sorted(_ai)[:-AI_DAYS]:
                _ai.pop(old, None)
                _blocked.pop(old, None)
    kpi.add(_ai_store[0], 'ai:' + key, n)


def _counted_chat(real):
    def chat(*args, **kwargs):
        text, reason = real(*args, **kwargs)
        if reason != 'not_configured':
            _bump('calls')
            _bump('ok' if text else ('busy' if reason == 'busy' else 'failed'))
        return text, reason
    chat._counted = True
    chat.__wrapped__ = real
    chat.__doc__ = real.__doc__
    return chat


def _counted_clean(real):
    def clean_reply(*args, **kwargs):
        out = real(*args, **kwargs)
        if isinstance(out, tuple) and out and not out[0]:
            _bump('rejected')
        return out
    clean_reply._counted = True
    clean_reply.__wrapped__ = real
    clean_reply.__doc__ = real.__doc__
    return clean_reply


def _counted_abusive(real):
    def abusive(text, *args, **kwargs):
        hit = real(text, *args, **kwargs)
        if hit and isinstance(text, str):
            # One message is checked several times on its way; count it once a day.
            key = hashlib.sha256(text.encode('utf-8', 'replace')).hexdigest()[:16]
            day = _today()
            with _ai_lock:
                seen = _blocked.setdefault(day, set())
                fresh = key not in seen and len(seen) < 20000
                seen.add(key)
            if fresh:
                _bump('guard')
        return hit
    abusive._counted = True
    abusive.__wrapped__ = real
    abusive.__doc__ = real.__doc__
    return abusive


def install_ai_counters(store=None) -> None:
    from . import ai
    if store is not None:
        _ai_store[0] = store
    for name, wrap in (('chat', _counted_chat), ('clean_reply', _counted_clean), ('abusive', _counted_abusive)):
        fn = getattr(ai, name, None)
        if callable(fn) and not getattr(fn, '_counted', False):
            setattr(ai, name, wrap(fn))


def ai_usage(store=None) -> dict:
    """AI calls per Vietnam day. With `store`: every worker's counts from stat_counters (`ai:*`, written every
    kpi.FLUSH_EVERY seconds, kept), plus this process's counts not written yet (`persisted` True). Without it, or
    when that read fails: this process's own memory since it started (`persisted` False)."""
    from . import ai
    days = None
    if store is not None:
        try:
            days = _ai_persisted(store)
        except (Busy, OSError) + _db_errors() as exc:
            _log('ai usage', exc)
            days = None
    persisted = days is not None
    if days is None:
        with _ai_lock:
            days = [dict(day=d, **row) for d, row in sorted(_ai.items())]
    total = {k: sum(r[k] for r in days) for k in AI_KEYS}
    since = (days[0]['day'] if days else _today()) if persisted else None
    return dict(since=round(STARTED, 3), since_day=since, persisted=persisted, configured=bool(ai.available()), total=total,
                days=days[-AI_DAYS:])


def _ai_persisted(store) -> list:
    now = time.monotonic()
    hit = _ai_read.get(store.path)
    if hit and now - hit[0] < AI_TTL:
        got = hit[1]
    else:
        first = (datetime.datetime.now(VN).date() - datetime.timedelta(days=AI_DAYS - 1)).isoformat()
        with _read(store, LIVE_MS) as db:
            got = kpi.read(db, first, 'ai:')
        _ai_read[store.path] = (now, got)
    merged = {d: dict(v) for d, v in got.items()}
    for (d, k), n in kpi.pending(store).items():   # this worker's last seconds, not written yet
        if k.startswith('ai:'):
            merged.setdefault(d, {})[k] = merged.get(d, {}).get(k, 0) + n
    return [dict(day=d, **{k: int(merged[d].get('ai:' + k, 0)) for k in AI_KEYS}) for d in sorted(merged)]


# ---------------------------------------------------------------- command timings (in memory, per worker)
_cmd_lock = threading.Lock()
_cmd: dict[str, dict] = {}          # file prefix -> {minute: [count, total ms, histogram]}
_cmd_meta: dict[str, dict] = {}     # file prefix -> {since: first minute, flushed: time}


def _cmd_prefix(store) -> str:
    return str(store.path) + '-adminstats-cmd.'


def record_command(ms: float, prefix: str, now: float | None = None) -> None:
    """One game command took `ms` (called by the store.command wrapper): a counter and a
    histogram bucket of the current minute; the file is rewritten at most every CMD_FLUSH s."""
    now = time.time() if now is None else now
    minute = int(now // 60)
    flush = None
    with _cmd_lock:
        rows = _cmd.setdefault(prefix, {})
        row = rows.get(minute)
        if row is None:
            row = rows[minute] = [0, 0.0, [0] * (len(CMD_EDGES) + 1)]
            for old in [m for m in rows if m <= minute - CMD_MINUTES]:
                del rows[old]
        row[0] += 1
        row[1] += ms
        row[2][bisect.bisect_left(CMD_EDGES, ms)] += 1
        meta = _cmd_meta.setdefault(prefix, dict(since=minute, flushed=0.0))
        if now - meta['flushed'] >= CMD_FLUSH:
            meta['flushed'] = now
            flush = dict(pid=os.getpid(), at=round(now, 3), since=meta['since'],
                         minutes={str(m): [r[0], round(r[1], 1), list(r[2])] for m, r in rows.items()})
    if flush is not None:
        try:
            _write_json(f'{prefix}{os.getpid()}.json', flush)
        except OSError:
            pass  # no writable data directory: this worker's numbers stay in its memory


def install_command_timer(store) -> None:
    """Wrap this store's command() with record_command (idempotent). Every save write of a
    player goes through it; the cost is a lock, a bisect and, every CMD_FLUSH s, a ~2 KB file."""
    real = getattr(store, 'command', None)
    if not callable(real) or getattr(real, '_timed', False):
        return
    prefix = _cmd_prefix(store)

    def command(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            return real(*args, **kwargs)
        finally:
            ms = (time.perf_counter() - t0) * 1000
            record_command(ms, prefix)
            kpi.add(store, f'cmd_ms:{bisect.bisect_left(CMD_EDGES, ms)}')   # the day's latency histogram (kept)
    command._timed = True
    command.__wrapped__ = real
    command.__doc__ = real.__doc__
    store.command = command


def _hist_pct(hist: list, q: float):
    """The q-quantile (ms) of a CMD_EDGES histogram, interpolated inside its bucket."""
    n = sum(hist)
    if not n:
        return None
    rank, seen = q * n, 0
    for i, c in enumerate(hist):
        if c and seen + c >= rank:
            lo = CMD_EDGES[i - 1] if i else 0
            hi = CMD_EDGES[i] if i < len(CMD_EDGES) else CMD_EDGES[-1] * 2
            return round(lo + (hi - lo) * max(0.0, rank - seen) / c, 1)
        seen += c
    return float(CMD_EDGES[-1] * 2)


def command_stats(store, now: float | None = None) -> dict:
    """Commands of every worker of this database over the last CMD_WINDOW minutes (and the
    current one so far): per minute, p50/p90/avg latency. This process from memory, the
    others from their files (files silent for an hour are removed)."""
    now = time.time() if now is None else now
    prefix = _cmd_prefix(store)
    cur = int(now // 60)
    window = range(cur - CMD_WINDOW, cur + 1)
    sources = []
    with _cmd_lock:
        mine = _cmd.get(prefix) or {}
        if mine:
            sources.append(({m: r for m, r in mine.items()}, _cmd_meta[prefix]['since']))
    for path in glob.glob(glob.escape(prefix) + '*.json'):
        data = _load_json(path, {}) or {}
        if data.get('pid') == os.getpid():
            continue
        at = float(data.get('at') or 0)
        if now - at > 3600:
            try:
                os.unlink(path)
            except OSError:
                pass
            continue
        rows = {}
        for m, r in (data.get('minutes') or {}).items():
            try:
                rows[int(m)] = r
            except ValueError:
                continue
        sources.append((rows, int(data.get('since') or cur)))
    n, total, hist = 0, 0.0, [0] * (len(CMD_EDGES) + 1)
    workers = 0
    for rows, _ in sources:
        workers += any(rows.get(m) for m in window)
        for m in window:
            r = rows.get(m)
            if not r:
                continue
            n += int(r[0])
            total += float(r[1])
            for i, c in enumerate(r[2][:len(hist)]):
                hist[i] += int(c)
    # The rate over the time the window really covers (a worker started 2 minutes ago: 2 minutes).
    first = min((since for _, since in sources), default=cur)
    seconds = max(60.0, now - max(window[0], first) * 60)
    return dict(per_min=round(n * 60 / seconds, 1), n=n, minutes=round(seconds / 60, 1), workers=workers,
                p50=_hist_pct(hist, .5), p90=_hist_pct(hist, .9), avg=round(total / n, 1) if n else None)


# ---------------------------------------------------------------- helpers
def _days(end: datetime.date, n: int) -> list[str]:
    return [(end - datetime.timedelta(days=n - 1 - i)).isoformat() for i in range(n)]


def _series(days: list[str], rows) -> list[int]:
    got = {r[0]: int(r[1]) for r in rows}
    return [got.get(d, 0) for d in days]


def _pct(values: list[float], q: float):
    if not values:
        return None
    v = sorted(values)
    i = (len(v) - 1) * q
    lo, hi = int(i), min(int(i) + 1, len(v) - 1)
    return round(v[lo] + (v[hi] - v[lo]) * (i - lo), 1)


def _share(counter: dict) -> list[dict]:
    total = sum(counter.values()) or 1
    return [dict(key=k, n=n, pct=round(100 * n / total, 1)) for k, n in sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0])))]


def _int(v, default=0) -> int:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)) and v == v:
        return int(v)
    return default


def _truthy(v) -> bool:
    return bool(v) and v not in ('0', 'false')


# ---------------------------------------------------------------- state sample
# One compact row per save: the few fields the dashboard reads, nothing personal.
_COMPACT = """json_object(
  'lang', json_extract(state, '$.settings.lang'),
  'theme', json_extract(state, '$.settings.uiTheme'),
  'ai', json_extract(state, '$.settings.aiConsent'),
  'music', json_extract(state, '$.settings.music'),
  'track', json_extract(state, '$.settings.musicTrack'),
  'story', json_extract(state, '$.journey.story'),
  'chapter', json_extract(state, '$.journey.chapter'),
  'life_day', json_extract(state, '$.journey.life_day'),
  'wallet', json_extract(state, '$.journey.wallet'),
  'in_debt', json_extract(state, '$.journey.in_debt'),
  'iv', json_array(json_extract(state, '$.journey.invest.coin.trades'), json_extract(state, '$.journey.invest.coin.units'),
                   json_extract(state, '$.journey.invest.saving.balance'), json_extract(state, '$.journey.invest.saving.earned'),
                   json_extract(state, '$.journey.invest.stats.lost'), json_extract(state, '$.journey.invest.stats.joined')),
  'life', CASE WHEN json_type(state, '$.journey.life') = 'object' THEN json_object(
            'spirit', json_extract(state, '$.journey.life.spirit'), 'stats', json_extract(state, '$.journey.life.stats')) END,
  'board', CASE WHEN json_type(state, '$.journey.board') = 'object' THEN json_object(
            'posts', json_array_length(state, '$.journey.board.posts'), 'stats', json_extract(state, '$.journey.board.stats')) END,
  'careers', (SELECT json_group_object(key, json_array(json_extract(value, '$.started'), json_extract(value, '$.day'), json_extract(value, '$.xp')))
              FROM json_each(state, '$.careers'))
)"""
_SAMPLE_SQL = f"SELECT {_COMPACT} FROM (SELECT state FROM sessions WHERE revision > 0 ORDER BY updated_at DESC LIMIT ?)"


# PostgreSQL twin of _COMPACT over `j` (the save as jsonb): one jsonb parse per save. JSON
# booleans stay booleans (SQLite's json_extract turns them into 1/0); play_stats reads both
# the same way.
_COMPACT_PG = """jsonb_build_object(
  'lang', j #> '{settings,lang}', 'theme', j #> '{settings,uiTheme}', 'ai', j #> '{settings,aiConsent}',
  'music', j #> '{settings,music}', 'track', j #> '{settings,musicTrack}',
  'story', j #> '{journey,story}', 'chapter', j #> '{journey,chapter}', 'life_day', j #> '{journey,life_day}',
  'wallet', j #> '{journey,wallet}', 'in_debt', j #> '{journey,in_debt}',
  'iv', jsonb_build_array(j #> '{journey,invest,coin,trades}', j #> '{journey,invest,coin,units}',
                          j #> '{journey,invest,saving,balance}', j #> '{journey,invest,saving,earned}',
                          j #> '{journey,invest,stats,lost}', j #> '{journey,invest,stats,joined}'),
  'life', CASE WHEN jsonb_typeof(j #> '{journey,life}') = 'object' THEN jsonb_build_object(
            'spirit', j #> '{journey,life,spirit}', 'stats', j #> '{journey,life,stats}') END,
  'board', CASE WHEN jsonb_typeof(j #> '{journey,board}') = 'object' THEN jsonb_build_object(
            'posts', CASE jsonb_typeof(j #> '{journey,board,posts}') WHEN 'array' THEN jsonb_array_length(j #> '{journey,board,posts}') ELSE 0 END,
            'stats', j #> '{journey,board,stats}') END,
  'careers', (SELECT jsonb_object_agg(key, jsonb_build_array(value -> 'started', value -> 'day', value -> 'xp'))
              FROM jsonb_each(CASE WHEN jsonb_typeof(j -> 'careers') = 'object' THEN j -> 'careers' END))
)::text"""
_SAMPLE_PG = (f"SELECT {_COMPACT_PG} FROM (SELECT state::jsonb AS j FROM sessions WHERE revision > 0 AND state <> '' "
              "ORDER BY updated_at DESC LIMIT %s) s")


def compact(state: dict) -> dict:
    """Pure Python twin of _COMPACT (fallback and tests)."""
    s = state if isinstance(state, dict) else {}
    st = s.get('settings') if isinstance(s.get('settings'), dict) else {}
    j = s.get('journey') if isinstance(s.get('journey'), dict) else {}
    iv = j.get('invest') if isinstance(j.get('invest'), dict) else {}
    get = lambda d, *path: _dig(d, path)
    L, bd = j.get('life'), j.get('board')
    cs = s.get('careers') if isinstance(s.get('careers'), dict) else {}
    return dict(
        lang=st.get('lang'), theme=st.get('uiTheme'), ai=st.get('aiConsent'), music=st.get('music'), track=st.get('musicTrack'),
        story=j.get('story'), chapter=j.get('chapter'), life_day=j.get('life_day'), wallet=j.get('wallet'), in_debt=j.get('in_debt'),
        iv=[get(iv, 'coin', 'trades'), get(iv, 'coin', 'units'), get(iv, 'saving', 'balance'), get(iv, 'saving', 'earned'),
            get(iv, 'stats', 'lost'), get(iv, 'stats', 'joined')],
        life=dict(spirit=L.get('spirit'), stats=L.get('stats')) if isinstance(L, dict) else None,
        board=dict(posts=len(bd['posts']) if isinstance(bd.get('posts'), list) else None, stats=bd.get('stats')) if isinstance(bd, dict) else None,
        careers={cid: [c.get('started'), c.get('day'), c.get('xp')] for cid, c in cs.items() if isinstance(c, dict)})


def _dig(d, path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def sample(db, limit: int = SAMPLE) -> tuple[list[dict], str]:
    """(compact rows, engine) for the `limit` most recently active saves, in ONE statement.
    Reference computation for tests and tools only: it reads every sampled save, so no
    request path calls it (the background job reads saves incrementally, see _Job)."""
    if _is_pg(db):
        try:
            db.set_local('statement_timeout', os.environ.get('ADMIN_STATS_TIMEOUT', '120s'))
            rows = [json.loads(r[0]) for r in db.pg(_SAMPLE_PG, (int(limit),))]
            db.commit()
            return rows, 'sql'
        except dbm.Error:  # e.g. a save jsonb refuses (\u0000): read them in Python
            db.rollback()
    else:
        try:
            return [json.loads(r[0]) for r in db.execute(_SAMPLE_SQL, (int(limit),))], 'sql'
        except sqlite3.OperationalError:  # no JSON1 in this SQLite
            pass
    out = []
    for r in db.execute('SELECT state FROM sessions WHERE revision > 0 ORDER BY updated_at DESC LIMIT ?', (int(limit),)):
        try:
            out.append(compact(json.loads(r[0])))
        except ValueError:
            continue
    return out, 'python'


def play_stats(rows: list[dict]) -> dict:
    """Aggregate compact rows into the play, economy and life/board sections."""
    n = len(rows)
    langs, themes, chapters, levels = {}, {}, {}, {}
    ai_on = music_on = story_on = 0
    life_days, wallets = [], []
    debt = investors = scam_joined = scam_victims = 0
    scam_lost = 0
    careers: dict[str, dict] = {}
    life = dict(saves=0, spirit=[], outings=0, scams=0, rumours=0, warm=0, hard=0, given=0)
    board = dict(saves=0, posts=0, player_posts=0, player_replies=0, reacts=0, active=0)
    for r in rows:
        lang = r.get('lang') if r.get('lang') in ('vi', 'en') else 'khác'
        langs[lang] = langs.get(lang, 0) + 1
        theme = r.get('theme') if isinstance(r.get('theme'), str) else 'khác'
        themes[theme[:20]] = themes.get(theme[:20], 0) + 1
        ai_on += _truthy(r.get('ai'))
        music_on += _truthy(r.get('music')) and r.get('track') != 'off'
        story = _truthy(r.get('story'))
        story_on += story
        if story:
            ch = _int(r.get('chapter'), 1)
            chapters[ch] = chapters.get(ch, 0) + 1
        ld = r.get('life_day')
        if isinstance(ld, (int, float)) and not isinstance(ld, bool):
            life_days.append(int(ld))
        w = r.get('wallet')
        if isinstance(w, (int, float)) and not isinstance(w, bool):
            wallets.append(int(w))
            debt += w < 0 or _truthy(r.get('in_debt'))
        elif _truthy(r.get('in_debt')):
            debt += 1
        iv = r.get('iv') if isinstance(r.get('iv'), list) else []
        iv = (iv + [None] * 6)[:6]
        if _int(iv[0]) > 0 or _int(iv[1]) > 0 or _int(iv[2]) > 0 or _int(iv[3]) > 0:
            investors += 1
        lost = _int(iv[4])
        scam_lost += max(0, lost)
        scam_victims += lost > 0
        scam_joined += max(0, _int(iv[5]))
        top = 0
        for cid, v in (r.get('careers') or {}).items():
            if not isinstance(v, list) or len(v) < 3:
                continue
            started, day, xp = _truthy(v[0]), _int(v[1], 1), max(0, _int(v[2]))
            played = max(0, day - 1)
            if not started and not played:
                continue
            c = careers.setdefault(str(cid)[:40], dict(players=0, days=0, levels=0))
            lv = 1 + xp // 90
            c['players'] += 1
            c['days'] += played
            c['levels'] += lv
            top = max(top, lv)
        if top:
            k = min(top, LEVEL_CAP)
            levels[k] = levels.get(k, 0) + 1
        L = r.get('life')
        if isinstance(L, dict):
            life['saves'] += 1
            sp = L.get('spirit')
            if isinstance(sp, (int, float)) and not isinstance(sp, bool):
                life['spirit'].append(sp)
            ls = L.get('stats') if isinstance(L.get('stats'), dict) else {}
            for k in ('outings', 'scams', 'rumours', 'warm', 'hard', 'given'):
                life[k] += max(0, _int(ls.get(k)))
        B = r.get('board')
        if isinstance(B, dict):
            board['saves'] += 1
            board['posts'] += max(0, _int(B.get('posts')))
            bs = B.get('stats') if isinstance(B.get('stats'), dict) else {}
            mine = max(0, _int(bs.get('player_posts'))) + max(0, _int(bs.get('player_replies')))
            board['player_posts'] += max(0, _int(bs.get('player_posts')))
            board['player_replies'] += max(0, _int(bs.get('player_replies')))
            board['reacts'] += max(0, _int(bs.get('reacts')))
            board['active'] += mine > 0
    career_rows = [dict(id=cid, players=c['players'], days=c['days'], avg_level=round(c['levels'] / c['players'], 1))
                   for cid, c in careers.items()]
    career_rows.sort(key=lambda x: (-x['players'], -x['days'], x['id']))
    spirit = life.pop('spirit')
    life['avg_spirit'] = round(sum(spirit) / len(spirit), 1) if spirit else None
    buckets = []
    for lo, hi, label in WALLET_BUCKETS:
        buckets.append(dict(label=label, n=sum(1 for w in wallets if (lo is None or w >= lo) and (hi is None or w < hi))))
    return dict(
        play=dict(
            sample=n, careers=career_rows[:TOP_CAREERS], careers_total=len(career_rows),
            levels=[dict(key=f'{k}+' if k == LEVEL_CAP else str(k), n=levels[k]) for k in sorted(levels)],
            life_day=dict(avg=round(sum(life_days) / len(life_days), 1) if life_days else None, median=_pct(life_days, .5), p90=_pct(life_days, .9)),
            chapters=[dict(key=str(k), n=chapters[k]) for k in sorted(chapters)],
            story=story_on, lang=_share(langs), theme=_share(themes), ai_on=ai_on, music_on=music_on),
        economy=dict(
            sample=n, wallet=dict(median=_pct(wallets, .5), p90=_pct(wallets, .9), avg=round(sum(wallets) / len(wallets), 1) if wallets else None),
            buckets=buckets, debt=debt, investors=investors, scam_lost=scam_lost, scam_victims=scam_victims, scam_joined=scam_joined),
        life=dict(life, sample=n),
        board=dict(board, sample=n))


# ---------------------------------------------------------------- SQL sections
# A save "has played" when a command of its player changed it. revision > 0 alone is not
# enough: reading a save migrates it (a release that adds a career) and bumps its revision
# without a command, so never-played saves of a new release looked played. Since the day log
# exists (stat_births), a save born under it counts only with a logged active day (stat_active,
# or stat_players once those days are past KEEP_DAYS); older saves keep the revision test.
_GHOST = ('SELECT COUNT(*), SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM accounts c WHERE c.sid = b.sid) THEN 1 ELSE 0 END) '
          'FROM stat_births b JOIN sessions s ON s.sid = b.sid WHERE s.revision > 0 '
          'AND NOT EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = b.sid) '
          'AND NOT EXISTS (SELECT 1 FROM stat_players p WHERE p.sid = b.sid)')


def ghosts(db) -> tuple[int, int]:
    """(saves, of which guests) with revision > 0 that never had a command (see _GHOST)."""
    r = db.execute(_GHOST).fetchone()
    return int(r[0] or 0), int(r[1] or 0)


def tracked_since(db) -> str | None:
    """First Vietnam day of the day log (stat_births / stat_active), or None before it."""
    return db.execute('SELECT MIN(day) FROM stat_births').fetchone()[0]


def players(db, days: int, today: datetime.date) -> dict:
    span = _days(today, days)
    start = span[0]
    since = (datetime.datetime.combine(today - datetime.timedelta(days=max(days, 30) + 1), datetime.time()) - datetime.timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
    tracked = tracked_since(db)
    # The saves' own last change only fills the days before the day log existed: after that the
    # log has every command, and a save's updated_at may be its creation (never played, migrated).
    until = kpi.utc_of(tracked) if tracked else '9999-12-31 00:00:00'
    total = db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
    ghost, ghost_guests = ghosts(db)
    played = db.execute('SELECT COUNT(*) FROM sessions WHERE revision > 0').fetchone()[0] - ghost
    accounts = db.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]
    owned = db.execute('SELECT COUNT(*) FROM sessions WHERE sid IN (SELECT sid FROM accounts)').fetchone()[0]
    guests = db.execute('SELECT COUNT(*) FROM sessions WHERE revision > 0 AND sid NOT IN (SELECT sid FROM accounts)').fetchone()[0] - ghost_guests
    # Activity: the day log, plus each save's last change for the days before the log.
    pg = _is_pg(db)
    if pg:
        run = db.pg
        act = ("WITH act AS (SELECT day, sid FROM stat_active WHERE day >= %(from)s UNION "
               "SELECT to_char(updated_at::timestamp + interval '7 hours', 'YYYY-MM-DD'), sid FROM sessions "
               "WHERE updated_at >= %(since)s AND updated_at < %(until)s AND revision > 0) ")
        mark = '%(start)s'
    else:
        run = db.execute
        act = (f"WITH act AS (SELECT day, sid FROM stat_active WHERE day >= :from UNION "
               f"SELECT date(updated_at, '{TZ}'), sid FROM sessions WHERE updated_at >= :since AND updated_at < :until AND revision > 0) ")
        mark = ':start'
    args = dict(since=since, until=until, **{'from': (today - datetime.timedelta(days=max(days, 30) - 1)).isoformat()})
    dau = _series(span, run(act + f'SELECT day, COUNT(*) FROM act WHERE day >= {mark} GROUP BY day', dict(args, start=start)))
    # 7 and 30 days in one pass over the union (it is the heaviest read of the summary).
    w7, m30 = ('%(w7)s', '%(start)s') if pg else (':w7', ':start')
    wau, mau = (int(x or 0) for x in run(act + f'SELECT COUNT(DISTINCT CASE WHEN day >= {w7} THEN sid END), COUNT(DISTINCT sid) '
                                                f'FROM act WHERE day >= {m30}',
                                                dict(args, w7=(today - datetime.timedelta(days=6)).isoformat(),
                                                     start=(today - datetime.timedelta(days=29)).isoformat())).fetchone())
    new_sessions = _series(span, db.execute('SELECT day, COUNT(*) FROM stat_births WHERE day >= ? GROUP BY day', (start,)))
    # New players of a day: saves born that day that also played that day (the cohort of the
    # retention numbers; a save that plays first a week later does not change an old day).
    new_players = _series(span, db.execute('SELECT b.day, COUNT(*) FROM stat_births b WHERE b.day >= ? AND EXISTS '
                                           '(SELECT 1 FROM stat_active a WHERE a.sid = b.sid AND a.day = b.day) GROUP BY b.day', (start,)))
    # created_at is UTC text: the range starts at Vietnam midnight of `start` (an index range, not a scan).
    utc_start = (datetime.datetime.fromisoformat(start) - datetime.timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
    day_of = "to_char(created_at::timestamp + interval '7 hours', 'YYYY-MM-DD')" if pg else f"date(created_at, '{TZ}')"
    new_accounts = _series(span, db.execute(f'SELECT {day_of} AS d, COUNT(*) FROM accounts WHERE created_at >= ? GROUP BY d', (utc_start,)))
    return dict(days=span, total=total, played=played, accounts=accounts, guests=guests, account_saves=owned,
                dau=dau, new_sessions=new_sessions, new_players=new_players, new_accounts=new_accounts,
                wau=wau, mau=mau, retention=retention(db, today, max(days, COHORT_DAYS)), tracked_since=tracked,
                unplayed_migrated=ghost)


_RETENTION_SQL = """
  WITH c AS (SELECT b.sid, b.day FROM stat_births b WHERE b.day >= :start
             AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = b.sid AND a.day = b.day))
  SELECT COUNT(*),
    SUM(CASE WHEN date(day, '+1 day') < :t THEN 1 ELSE 0 END),
    SUM(CASE WHEN date(day, '+1 day') < :t AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = c.sid AND a.day = date(c.day, '+1 day')) THEN 1 ELSE 0 END),
    SUM(CASE WHEN date(day, '+7 day') < :t THEN 1 ELSE 0 END),
    SUM(CASE WHEN date(day, '+7 day') < :t AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = c.sid AND a.day = date(c.day, '+7 day')) THEN 1 ELSE 0 END)
  FROM c"""
_PLUS = "to_char({}::date + {}, 'YYYY-MM-DD')"
_RETENTION_PG = f"""
  WITH c AS (SELECT b.sid, b.day FROM stat_births b WHERE b.day >= %(start)s
             AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = b.sid AND a.day = b.day))
  SELECT COUNT(*),
    SUM(CASE WHEN {_PLUS.format('day', 1)} < %(t)s THEN 1 ELSE 0 END),
    SUM(CASE WHEN {_PLUS.format('day', 1)} < %(t)s AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = c.sid AND a.day = {_PLUS.format('c.day', 1)}) THEN 1 ELSE 0 END),
    SUM(CASE WHEN {_PLUS.format('day', 7)} < %(t)s THEN 1 ELSE 0 END),
    SUM(CASE WHEN {_PLUS.format('day', 7)} < %(t)s AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = c.sid AND a.day = {_PLUS.format('c.day', 7)}) THEN 1 ELSE 0 END)
  FROM c"""


def retention(db, today: datetime.date, window: int) -> dict:
    """Classic D1/D7 over players who started in the window: a save counts when it
    did something on its first day; it is kept when it did something again exactly
    1 (or 7) days later. Only cohorts whose day 1 / day 7 is over count."""
    args = dict(start=(today - datetime.timedelta(days=window - 1)).isoformat(), t=today.isoformat())
    row = (db.pg(_RETENTION_PG, args) if _is_pg(db) else db.execute(_RETENTION_SQL, args)).fetchone()
    cohort, n1, k1, n7, k7 = (int(x or 0) for x in row)
    pct = lambda k, n: round(100 * k / n, 1) if n else None
    return dict(window=window, cohort=cohort, d1=pct(k1, n1), d1_n=n1, d7=pct(k7, n7), d7_n=n7)


def feedback(db, days: int, now: float) -> dict:
    kinds, statuses = ('bug', 'idea', 'praise', 'hard'), ('new', 'seen', 'done')
    table = {k: {s: 0 for s in statuses} for k in kinds}
    for r in db.execute('SELECT kind, status, COUNT(*) FROM player_feedback GROUP BY kind, status'):
        if r[0] in table and r[1] in statuses:
            table[r[0]][r[1]] = r[2]
    # "The last N days" = from Vietnam midnight N-1 days ago, as every other card (not now - N×24 h).
    today = datetime.datetime.fromtimestamp(now, VN).date()
    from_t = kpi.epoch_of((today - datetime.timedelta(days=days - 1)).isoformat())
    in_range = db.execute('SELECT COUNT(*) FROM player_feedback WHERE created_at >= ?', (from_t,)).fetchone()[0]
    # First time a note left "new": the trigger's exact time, else the best guess from older rows.
    least = 'LEAST' if _is_pg(db) else 'MIN'  # SQLite's MIN(a, b) is PostgreSQL's LEAST(a, b)
    ack_from = kpi.epoch_of((today - datetime.timedelta(days=max(days, 30) - 1)).isoformat())
    waits = [r[0] for r in db.execute(
        f"SELECT COALESCE(a.at, {least}(p.updated_at, COALESCE(p.replied_at, p.updated_at))) - p.created_at FROM player_feedback p "
        'LEFT JOIN stat_fb_ack a ON a.id = p.id WHERE p.status != ? AND p.created_at >= ?', ('new', ack_from)) if r[0] is not None]
    waits = [max(0.0, w) for w in waits]
    # The median above only knows the notes already read: the ones still waiting are told apart
    # (how many, the oldest), so a backlog cannot hide behind a fast median.
    w = db.execute('SELECT COUNT(*), MIN(created_at) FROM player_feedback WHERE status = ? AND created_at >= ?', ('new', ack_from)).fetchone()
    waiting, oldest = int(w[0] or 0), w[1]
    asked = len(waits) + waiting
    newest = [dict(id=r[0], kind=r[1], status=r[2], text=(r[3] or '').split('\n')[0][:90], created_at=r[4])
              for r in db.execute('SELECT id, kind, status, text, created_at FROM player_feedback ORDER BY id DESC LIMIT 5')]
    open_n = sum(table[k]['new'] + table[k]['seen'] for k in kinds)
    return dict(kinds=[dict(kind=k, **table[k]) for k in kinds], open=open_n, unread=sum(table[k]['new'] for k in kinds),
                total=sum(sum(v.values()) for v in table.values()), in_range=in_range, range_from=round(from_t, 3),
                ack=dict(n=len(waits), median_h=round(_pct(waits, .5) / 3600, 1) if waits else None,
                         avg_h=round(sum(waits) / len(waits) / 3600, 1) if waits else None,
                         waiting=waiting, oldest_wait_h=round(max(0.0, now - float(oldest)) / 3600, 1) if oldest is not None else None,
                         read_pct=round(100 * len(waits) / asked, 1) if asked else None, window_days=max(days, 30)),
                newest=newest)


def _file_bytes(store) -> int:
    size = 0
    for suffix in ('', '-wal'):
        try:
            size += os.path.getsize(store.path + suffix)
        except OSError:
            pass
    return size


def server_light(store) -> dict:
    """The server facts the first screen shows. SQLite: two stat() calls; PostgreSQL: the
    size measured by the job (no query here)."""
    pg = _store_pg(store)
    return dict(version=__version__, uptime=int(time.time() - STARTED), started=round(STARTED, 3),
                db_bytes=None if pg else _file_bytes(store), python='.'.join(map(str, sys.version_info[:3])),
                sqlite=None if pg else sqlite3.sqlite_version, database='PostgreSQL' if pg else 'SQLite ' + sqlite3.sqlite_version,
                backend='PostgreSQL' if pg else 'SQLite', story=bool(getattr(store, 'story', False)))


SIZE_EDGES = (10_000, 25_000, 50_000, 100_000, 200_000, 400_000)   # bytes


def save_sizes(store, sids: list) -> dict | None:
    """Stored size of the given saves (the job's sample): median, p90, max and a histogram.
    PostgreSQL: pg_column_size (the stored, compressed bytes; no detoasting). SQLite:
    octet_length (3.43+, read from the record header), else None. 100 saves per statement."""
    pg = _store_pg(store)
    if not pg and sqlite3.sqlite_version_info < (3, 43, 0):
        return None
    expr = 'pg_column_size(state)' if pg else 'octet_length(state)'
    sizes = []
    for i in range(0, len(sids), 100):
        part = sids[i:i + 100]
        with _read(store, 2000) as db:
            sizes += [int(r[0] or 0) for r in db.execute(
                f"SELECT {expr} FROM sessions WHERE sid IN ({','.join('?' * len(part))})", tuple(part))]
    if not sizes:
        return dict(n=0, median=None, p90=None, max=None, hist=[], edges=list(SIZE_EDGES), stored='compressed' if pg else 'raw')
    hist = [0] * (len(SIZE_EDGES) + 1)
    for b in sizes:
        hist[bisect.bisect_right(SIZE_EDGES, b)] += 1
    return dict(n=len(sizes), median=_pct(sizes, .5), p90=_pct(sizes, .9), max=max(sizes), avg=round(sum(sizes) / len(sizes)),
                hist=hist, edges=list(SIZE_EDGES), stored='compressed' if pg else 'raw')


def career_names() -> dict:
    """{career id: short name} as the catalogue shows it, so the operator page needs no catalogue."""
    from .content import CATALOG, CAREER_META
    out = {}
    for c in CATALOG:
        m = dict(c, **CAREER_META.get(c['id'], {}))
        out[c['id']] = m.get('short') or m.get('name') or c['id']
    return out


# ---------------------------------------------------------------- reads with a budget
class Busy(OSError):
    """An admin read ran out of its time budget (the server answers 503-like, players unaffected)."""


def _timed_out(exc) -> bool:
    return 'interrupted' in str(exc) or getattr(exc, 'sqlstate', None) == '57014'


class _PgBudget:
    """A PostgreSQL connection whose statements share one deadline: before each, the
    transaction's statement_timeout is set to what is left (at most `cap`)."""
    dialect = 'pg'

    def __init__(self, db, deadline: float, cap: int):
        self.db, self.deadline, self.cap = db, deadline, cap

    def _arm(self) -> None:
        left = int((self.deadline - time.monotonic()) * 1000)
        if left <= 0:
            raise Busy('admin stats: over the time budget')
        self.db.set_local('statement_timeout', str(max(50, min(left, self.cap))))

    def execute(self, sql, params=()):
        self._arm()
        return self.db.execute(sql, params)

    def pg(self, sql, params=()):
        self._arm()
        return self.db.pg(sql, params)

    def __getattr__(self, name):
        return getattr(self.db, name)


class _read:
    """`with _read(store, ms) as db:` a connection that cannot write and gives up after `ms`
    in all (one statement: at most `statement_ms` on PostgreSQL).
    SQLite: its own read-only connection (never pooled, closed at the end); every statement
    is its own snapshot, aborted by a progress handler at the deadline. PostgreSQL: a pooled
    connection in a READ ONLY transaction, each statement under statement_timeout = the time
    left, rolled back at the end."""

    def __init__(self, store, ms: int = REQUEST_MS, statement_ms: int | None = None):
        self.store, self.ms = store, int(ms)
        self.statement_ms = int(statement_ms) if statement_ms else min(self.ms, STATEMENT_MS)

    def __enter__(self):
        if _store_pg(self.store):
            db = self.db = self.store.connect()
            try:
                db.begin()
                db.pg('SET TRANSACTION READ ONLY')
            except BaseException:
                db.close()
                raise
            return _PgBudget(db, time.monotonic() + self.ms / 1000, self.statement_ms)
        uri = Path(self.store.path).resolve().as_uri() + '?mode=ro'
        db = self.db = sqlite3.connect(uri, uri=True, timeout=1.0, check_same_thread=False)
        db.row_factory = sqlite3.Row
        deadline = time.monotonic() + self.ms / 1000
        db.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 5000)
        db.execute('PRAGMA query_only=1')
        return db

    def __exit__(self, exc_type, exc, tb):
        db = self.db  # the raw connection (not the _PgBudget wrapper)
        try:
            if _store_pg(self.store):
                try:
                    db.rollback()
                except Exception:  # noqa: BLE001 - closing matters more
                    pass
        finally:
            db.close()
        if exc is not None and isinstance(exc, _db_errors()) and _timed_out(exc):
            raise Busy('admin stats: over the time budget') from exc
        return False


def _db_errors() -> tuple:
    return dbm.Error if dbm is not None else (sqlite3.Error,)


def _brief(exc) -> str:
    """`Type: message` of an error, one line, short, without a connection URL."""
    msg = ' '.join(str(exc).split())
    if '://' in msg:
        msg = ' '.join(w for w in msg.split() if '://' not in w)
    return f'{type(exc).__name__}: {msg[:200]}' if msg else type(exc).__name__


def _log(where: str, exc) -> None:
    try:
        sys.stderr.write(f'[admin-stats] {where}: {_brief(exc)}\n')
    except Exception:  # noqa: BLE001 - a closed stderr must not stop the job
        pass


# ---------------------------------------------------------------- live counters (cheap, on request)
def live(store) -> dict:
    """Sessions active in the last 5 min / 1 h / 24 h, new players today, the database size
    and the backend, plus the command rate and latency. Index range reads only (a few ms on
    production), read-only, under LIVE_MS; never a save."""
    t0 = time.perf_counter()
    now = time.time()
    today = datetime.datetime.now(VN).date()
    since = lambda s: time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now - s))   # the TEXT form of updated_at (UTC)
    midnight = (datetime.datetime.combine(today, datetime.time()) - datetime.timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
    pg = _store_pg(store)
    with _read(store, LIVE_MS) as db:
        # Text against text in the same format: the range is read from stat_sessions_seen (a cast would scan).
        m5, h1, d1 = (int(x or 0) for x in db.execute(
            'SELECT SUM(CASE WHEN updated_at >= ? THEN 1 ELSE 0 END), SUM(CASE WHEN updated_at >= ? THEN 1 ELSE 0 END), COUNT(*) '
            'FROM sessions WHERE updated_at >= ?', (since(300), since(3600), since(86400))).fetchone())
        born = db.execute('SELECT COUNT(*) FROM stat_births WHERE day = ?', (today.isoformat(),)).fetchone()[0]
        played = db.execute('SELECT COUNT(*) FROM stat_births b WHERE b.day = ? AND EXISTS '
                            '(SELECT 1 FROM stat_active a WHERE a.sid = b.sid)', (today.isoformat(),)).fetchone()[0]
        accounts_today = db.execute('SELECT COUNT(*) FROM accounts WHERE created_at >= ?', (midnight,)).fetchone()[0]
        if pg:
            size, version = db.pg("SELECT pg_database_size(current_database()), current_setting('server_version')").fetchone()
            database = 'PostgreSQL ' + str(version).split()[0]
        else:
            size, database = _file_bytes(store), 'SQLite ' + sqlite3.sqlite_version
    out = dict(active=dict(m5=m5, h1=h1, h24=d1), new_today=dict(sessions=int(born), players=int(played), accounts=int(accounts_today)),
               commands=command_stats(store, now), db_bytes=int(size or 0), database=database,
               backend='PostgreSQL' if pg else 'SQLite', today=today.isoformat())
    return _stamp(out, t0)


# ---------------------------------------------------------------- play time ("Thời gian chơi")
# stat_play holds one row per save per Vietnam day it sent a command, kept by the trigger
# stat_play_cmd on receipts (see SCHEMA; game/pg_schema.py on PostgreSQL): secs played,
# sessions, commands, the first/last command, the hours of the day it played (bit mask), the
# start of its current session and the lengths of its closed sessions ("lens", "90,300,").
# Days seeded from receipts by backfill_play() are listed in stat_play_est: their numbers are
# estimates (receipts keep only the newest RECEIPTS_PER_SAVE per save).
# The section reads only these two tables and stat_births. A finished day never changes, so
# each worker keeps its summary (a few histograms, ~15 KB) for PLAY_DAY_TTL; only today is
# read again when the PLAY_TTL cache runs out.
PLAY_TTL = 60.0
PLAY_MS = int(os.environ.get('ADMIN_STATS_PLAY_MS', '2500') or 2500)   # all reads of one section request
PLAY_DAY_TTL = 6 * 3600.0
PLAY_DAYS_KEPT = 64          # day summaries kept per worker (all databases together)
PLAY_BANDS = ((0, 5, '< 5'), (5, 15, '5–15'), (15, 30, '15–30'), (30, 60, '30–60'), (60, None, '> 60'))  # minutes a day
NEW_OVER = 600               # first day: the share of new players who played longer than this (seconds)
PLAY_BUCKETS = 1200          # histogram of seconds: exact to the second below 10 min, then 10 s, 1 min, 10 min


def _bucket(secs) -> int:
    s = max(0, int(secs))
    if s < 600:
        return s
    if s < 3600:
        return 600 + (s - 600) // 10
    if s < 14400:
        return 900 + (s - 3600) // 60
    return 1080 + min((s - 14400) // 600, 119)


def _bucket_span(b: int) -> tuple[int, int]:
    if b < 600:
        return b, 1
    if b < 900:
        return 600 + (b - 600) * 10, 10
    if b < 1080:
        return 3600 + (b - 900) * 60, 60
    return 14400 + (b - 1080) * 600, 600


def _hist() -> array:
    return array('I', bytes(4 * PLAY_BUCKETS))


def _hist_add(into: array, other: array) -> None:
    for i, n in enumerate(other):
        if n:
            into[i] += n


def _quantile(hist: array, q: float):
    """The q-quantile (seconds) of a PLAY_BUCKETS histogram, interpolated like _pct: exact where a
    bucket is one second wide, the items of a wider bucket taken as spread evenly inside it."""
    n = sum(hist)
    if not n:
        return None
    want = (n - 1) * q
    lo_i, frac = int(want), want - int(want)

    def value(k):
        seen = 0
        for b, c in enumerate(hist):
            if c and seen + c > k:
                start, width = _bucket_span(b)
                return start if width == 1 else start + (k - seen + 0.5) * width / c
            seen += c
        return None
    a = value(lo_i)
    return a if not frac else a + (value(min(lo_i + 1, n - 1)) - a) * frac


def _lens(text) -> list[int]:
    return [int(x) for x in str(text or '').split(',') if x.strip().lstrip('-').isdigit()]


def play_day(db, day: str) -> dict:
    """One day of stat_play (and the first day of that day's new players), summed up."""
    players = secs = sessions = cmds = 0
    first = None
    per_player, per_session, hours = _hist(), _hist(), [0] * 24
    for r in db.execute('SELECT secs, sessions, cmds, first_at, last_at, hours, sess_at, lens FROM stat_play WHERE day = ?', (day,)):
        s = int(r[0])
        players += 1
        secs += s
        sessions += int(r[1])
        cmds += int(r[2])
        first = r[3] if first is None else min(first, r[3])
        per_player[_bucket(s)] += 1
        for length in _lens(r[7]):
            per_session[_bucket(length)] += 1
        per_session[_bucket(round(r[4] - r[6]) + PLAY_IDLE_TAIL)] += 1   # the session still open at the day's end
        h = int(r[5] or 0) & 0xFFFFFF
        while h:
            low = h & -h
            hours[low.bit_length() - 1] += 1
            h ^= low
    new, new_secs, new_over, new_hist = 0, 0, 0, _hist()
    for (s,) in db.execute('SELECT p.secs FROM stat_births b JOIN stat_play p ON p.day = b.day AND p.sid = b.sid WHERE b.day = ?', (day,)):
        s = int(s)
        new += 1
        new_secs += s
        new_over += s > NEW_OVER
        new_hist[_bucket(s)] += 1
    return dict(day=day, players=players, secs=secs, sessions=sessions, cmds=cmds, first_at=first, per_player=per_player,
                per_session=per_session, hours=hours, new=dict(n=new, secs=new_secs, over=new_over, hist=new_hist))


_play_lock = threading.Lock()
_play_days: dict[tuple, tuple] = {}   # (db path, day) -> (monotonic time, stat_play_est.at of that day, summary)


def _play_day_cached(store, db, day: str, mark) -> dict:
    """A finished day's summary: from this worker's memory, read again after PLAY_DAY_TTL or when
    the backfill marked the day since (its stat_play_est.at moved)."""
    key, at = (store.path, day), (mark or {}).get('at')
    now = time.monotonic()
    with _play_lock:
        hit = _play_days.get(key)
    if hit and hit[1] == at and now - hit[0] < PLAY_DAY_TTL:
        return hit[2]
    out = play_day(db, day)
    with _play_lock:
        _play_days.pop(key, None)
        _play_days[key] = (now, at, out)
        while len(_play_days) > PLAY_DAYS_KEPT:   # the oldest entry first (insertion order)
            _play_days.pop(next(iter(_play_days)))
    return out


def _mins(secs) -> float | None:
    return None if secs is None else round(secs / 60, 1)


def _play_period(key: str, span: list[str], roll: dict, est: dict, first_day) -> dict:
    have = [roll[d] for d in span if d in roll]
    n = sum(r['players'] for r in have)
    secs = sum(r['secs'] for r in have)
    sess = sum(r['sessions'] for r in have)
    pp, ps, nh = _hist(), _hist(), _hist()
    new = dict(n=0, secs=0, over=0)
    for r in have:
        _hist_add(pp, r['per_player'])
        _hist_add(ps, r['per_session'])
        _hist_add(nh, r['new']['hist'])
        for k in new:
            new[k] += r['new'][k]
    bands = []
    for lo, hi, label in PLAY_BANDS:
        a, b = _bucket(lo * 60), (_bucket(hi * 60) if hi is not None else PLAY_BUCKETS)
        c = sum(pp[a:b])
        bands.append(dict(label=label, n=c, pct=round(100 * c / n, 1) if n else None))
    estimated = [d for d in span if d in est]
    partial = len(have) < len(span) or (first_day in span and first_day not in est)
    return dict(key=key, start=span[0], end=span[-1], days=len(span), tracked=len(have), player_days=n,
                players=round(n / len(have), 1) if have else 0,
                avg_min=_mins(secs / n) if n else None, median_min=_mins(_quantile(pp, .5)), p90_min=_mins(_quantile(pp, .9)),
                session_avg_min=_mins(secs / sess) if sess else None, session_median_min=_mins(_quantile(ps, .5)),
                sessions_per_player=round(sess / n, 2) if n else None, sessions=sess, hours=round(secs / 3600, 1),
                cmds=sum(r['cmds'] for r in have), bands=bands,
                new=dict(n=new['n'], avg_min=_mins(new['secs'] / new['n']) if new['n'] else None, median_min=_mins(_quantile(nh, .5)),
                         over_pct=round(100 * new['over'] / new['n'], 1) if new['n'] else None),
                exact=not estimated and not partial, estimated=estimated, partial=partial)


def playtime(store) -> dict:
    """"Thời gian chơi": minutes per player per day, sessions, the minutes' distribution, the
    hours of the day, new players' first day, for today, yesterday, 7 and 30 days. Reads
    stat_play / stat_play_est / stat_births only (read-only, under PLAY_MS), never a save."""
    t0 = time.perf_counter()
    today = datetime.datetime.now(VN).date()
    span = _days(today, 30)
    with _read(store, PLAY_MS) as db:
        est = {r[0]: dict(saves=int(r[1]), capped=int(r[2]), at=r[3])
               for r in db.execute('SELECT day, saves, capped, at FROM stat_play_est WHERE day >= ?', (span[0],))}
        first_day = db.execute('SELECT MIN(day) FROM stat_play').fetchone()[0]
        roll = {}
        for day in span:
            if first_day is None or day < first_day:
                continue
            roll[day] = play_day(db, day) if day == span[-1] else _play_day_cached(store, db, day, est.get(day))
    yesterday = span[-2]
    periods = [_play_period(k, days, roll, est, first_day) for k, days in
               (('today', span[-1:]), ('yesterday', [yesterday]), ('d7', span[-7:]), ('d30', span))]
    # Hours of the day: the 7 finished days before today (today alone on the first day of tracking).
    hour_days = [d for d in span[-8:-1] if d in roll] or [d for d in span[-1:] if d in roll]
    per_hour = [round(sum(roll[d]['hours'][h] for d in hour_days) / len(hour_days), 1) if hour_days else 0 for h in range(24)]
    since = roll[first_day]['first_at'] if first_day in roll else None
    out = dict(today=today.isoformat(), periods=periods,
               hours=dict(avg=per_hour, days=len(hour_days), start=hour_days[0] if hour_days else None,
                          end=hour_days[-1] if hour_days else None),
               since=dict(day=first_day, at=round(since, 3) if since else None, estimated=first_day in est),
               estimated=[dict(day=d, **{k: v for k, v in m.items() if k != 'at'}) for d, m in sorted(est.items())],
               rule=dict(gap_min=PLAY_GAP // 60, tail_min=PLAY_IDLE_TAIL // 60, new_over_min=NEW_OVER // 60))
    return _stamp(out, t0)


def get_playtime(store, fresh: bool = False) -> dict:
    """The play time section, cached PLAY_TTL per worker; it neither wakes nor waits for the job."""
    try:
        return dict(_serve(('playtime', store.path), lambda: playtime(store), PLAY_TTL, fresh))
    except Busy:  # over PLAY_MS (a cold worker reading 30 days): the finished days read so far stay cached
        return dict(pending=True, retry_ms=2000)


# ---------------------------------------------------------------- play time: seeding from receipts
def _utc_epoch(text: str) -> int:
    return int(datetime.datetime.strptime(text[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=datetime.timezone.utc).timestamp())


def _vn_day(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, VN).date().isoformat()


def _play_from(ts: list[int]) -> dict:
    """A stat_play row (without day and sid) for one save's command times of one day (sorted),
    by the trigger's rule."""
    runs = []   # [start, last]
    hours = 0
    for t in ts:
        hours |= 1 << ((t + 7 * 3600) // 3600 % 24)
        if runs and t - runs[-1][1] <= PLAY_GAP:
            runs[-1][1] = t
        else:
            runs.append([t, t])
    lens = [b - a + PLAY_IDLE_TAIL for a, b in runs]
    return dict(secs=sum(lens), sessions=len(runs), cmds=len(ts), first_at=float(ts[0]), last_at=float(ts[-1]),
                hours=hours, sess_at=float(runs[-1][0]), lens=lens[:-1], last_len=lens[-1])


def _play_merge(e: dict, row) -> dict:
    """Estimated commands `e` (all before the tracked row `row`'s first command) joined to it."""
    first_at, last_at, secs, sessions, cmds, hours, sess_at, lens = (row['first_at'], row['last_at'], int(row['secs']), int(row['sessions']),
                                                                     int(row['cmds']), int(row['hours'] or 0), row['sess_at'], _lens(row['lens']))
    gap = first_at - e['last_at']
    joined = gap <= PLAY_GAP
    if not joined:
        new_lens, new_sess = e['lens'] + [e['last_len']] + lens, sess_at
    elif lens:   # the tracked first session is closed: it grows by the time from the estimated session's start
        new_lens, new_sess = e['lens'] + [lens[0] + round(first_at - e['sess_at'])] + lens[1:], sess_at
    else:        # the tracked first session is the open one: it now starts at the estimated session's start
        new_lens, new_sess = list(e['lens']), e['sess_at']
    return dict(secs=secs + e['secs'] + (round(gap) - PLAY_IDLE_TAIL if joined else 0), sessions=sessions + e['sessions'] - joined,
                cmds=cmds + e['cmds'], first_at=e['first_at'], hours=hours | e['hours'], sess_at=new_sess,
                lens=''.join(f'{x},' for x in new_lens), last_at=last_at)


def backfill_play(store, days: int = 2, cap: int | None = None, batch: int = 100, pause: float = 0.05,
                  dry_run: bool = False, now: float | None = None, log=None) -> dict:
    """Seed stat_play for the last `days` Vietnam days (today included) from the receipts the
    database still holds, for the commands sent before tracking began; run by hand once after the
    release that adds the trigger (scripts/playtime_backfill.py). Idempotent: for a (day, save)
    that already has a row, only receipts older than its first command are used, and a row it
    seeded starts at its oldest receipt, so a second run finds nothing to add.
    Receipts are kept 2 days and at most `cap` (RECEIPTS_PER_SAVE, 200) per save: a busy save's
    older commands are gone, so the seeded days are listed in stat_play_est (the page says
    "ước tính"), with how many seeded saves were at the cap. Reads receipts by save through their
    primary key, `batch` saves per short transaction; never changes a receipt or a save."""
    now = time.time() if now is None else now
    cap = int(cap if cap is not None else os.environ.get('RECEIPTS_PER_SAVE', '200') or 200)
    today = datetime.datetime.fromtimestamp(now, VN).date()
    span = _days(today, max(1, int(days)))
    since = (datetime.datetime.combine(datetime.date.fromisoformat(span[0]), datetime.time()) - datetime.timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
    with store.connect() as db:   # every save that wrote on those days (stat_active: its primary key serves the range)
        sids = [r[0] for r in db.execute('SELECT DISTINCT sid FROM stat_active WHERE day >= ? ORDER BY sid', (span[0],))]
    out = dict(days=span, saves=len(sids), receipts=0, inserted=0, merged=0, capped=0, covered=0, dry_run=bool(dry_run),
               per_day={d: dict(saves=0, capped=0) for d in span})
    for i in range(0, len(sids), max(1, int(batch))):
        part = sids[i:i + max(1, int(batch))]
        marks = ','.join('?' * len(part))
        with store.connect() as db:
            got = db.execute(f'SELECT sid, created_at FROM receipts WHERE sid IN ({marks}) AND created_at >= ? ORDER BY sid, created_at',
                             (*part, since)).fetchall()
            total = {r[0]: int(r[1]) for r in db.execute(f'SELECT sid, COUNT(*) FROM receipts WHERE sid IN ({marks}) GROUP BY sid', part)}
        out['receipts'] += len(got)
        by = {}
        for sid, created in got:
            t = _utc_epoch(created)
            day = _vn_day(t)
            if day in out['per_day']:
                by.setdefault((day, sid), []).append(t)
        if not by:
            continue

        def write(db, by=by, part=part, marks=marks):
            rows = {(r['day'], r['sid']): r for r in db.execute(
                f"SELECT day, sid, secs, sessions, cmds, first_at, last_at, hours, sess_at, lens FROM stat_play "
                f"WHERE day IN ({','.join('?' * len(span))}) AND sid IN ({marks})" + (dbm.for_update(db) if dbm else ''), (*span, *part))}
            seeded = {d: [0, 0] for d in span}
            for (day, sid), ts in by.items():
                row = rows.get((day, sid))
                if row is not None:   # tracked since its first command: only what came before that second
                    ts = [t for t in ts if t < int(row['first_at'])]
                if not ts:
                    out['covered'] += 1
                    continue
                e = _play_from(ts)
                if row is None:
                    if not dry_run:
                        n = db.execute('INSERT OR IGNORE INTO stat_play(day, sid, secs, sessions, cmds, first_at, last_at, hours, sess_at, lens) '
                                       'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                       (day, sid, e['secs'], e['sessions'], e['cmds'], e['first_at'], e['last_at'], e['hours'], e['sess_at'],
                                        ''.join(f'{x},' for x in e['lens']))).rowcount
                        if n != 1:   # the trigger wrote it meanwhile: the next run joins these commands to it
                            continue
                    out['inserted'] += 1
                else:
                    m = _play_merge(e, row)
                    if not dry_run:
                        db.execute('UPDATE stat_play SET secs = ?, sessions = ?, cmds = ?, first_at = ?, hours = ?, sess_at = ?, lens = ? '
                                   'WHERE day = ? AND sid = ?',
                                   (m['secs'], m['sessions'], m['cmds'], m['first_at'], m['hours'], m['sess_at'], m['lens'], day, sid))
                    out['merged'] += 1
                full = total.get(sid, 0) >= cap
                seeded[day][0] += 1
                seeded[day][1] += full
                out['capped'] += full
            for day, (n, full) in seeded.items():
                out['per_day'][day]['saves'] += n
                out['per_day'][day]['capped'] += full
                if n and not dry_run:
                    db.execute('INSERT INTO stat_play_est(day, saves, capped, at) VALUES (?, ?, ?, ?) ON CONFLICT(day) DO UPDATE SET '
                               'saves = stat_play_est.saves + excluded.saves, capped = stat_play_est.capped + excluded.capped, at = excluded.at',
                               (day, n, full, round(time.time(), 3)))
        if dry_run:
            with store.connect() as db:
                write(db)
                db.rollback()
        else:
            store.transaction(write)
        if log:
            log(f'{min(i + len(part), len(sids))}/{len(sids)} lượt chơi')
        if pause:
            time.sleep(pause)
    return out


# ---------------------------------------------------------------- the background job
def _paths(store) -> dict:
    base = str(store.path) + '-adminstats'
    return dict(result=base + '.json', rows=base + '-rows.json', lock=base + '.lock', want=base + '.want')


def _write_json(path: str, data) -> None:
    tmp = f'{path}.{os.getpid()}.{threading.get_ident()}.tmp'
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    for i in range(5):  # Windows: a reader may hold the target open for a moment
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.05 * (i + 1))
    os.unlink(tmp)


def _load_json(path: str, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


_result_cache: dict[str, tuple] = {}


def _result(store) -> dict:
    """The job's last result file, re-read only when it changed."""
    path = _paths(store)['result']
    try:
        st = os.stat(path)
    except OSError:
        return {}
    key = (st.st_mtime_ns, st.st_size)
    hit = _result_cache.get(path)
    if hit and hit[0] == key:
        return hit[1]
    data = _load_json(path, {}) or {}
    _result_cache[path] = (key, data)
    return data


def _load() -> float:
    """The 1-minute load average per core (0 where the OS has none)."""
    try:
        return os.getloadavg()[0] / (os.cpu_count() or 1)
    except (AttributeError, OSError):
        return 0.0


def _try_lock(path: str):
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except OSError:
        os.close(fd)
        return None


def _unlock(fd) -> None:
    try:
        if os.name == 'nt':
            import msvcrt
            os.lseek(fd, 0, 0)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    finally:
        os.close(fd)


def _write_beat(fd, data: dict) -> None:
    """The job's heartbeat, written into the lock file it holds (see the module doc)."""
    raw = json.dumps(data, separators=(',', ':')).encode()
    try:
        os.ftruncate(fd, 0)
        if hasattr(os, 'pwrite'):
            os.pwrite(fd, raw, 0)
        else:  # pragma: no cover - Windows
            os.lseek(fd, 0, 0)
            os.write(fd, raw)
    except OSError:
        pass


def job_state(store) -> dict:
    """Who computes the snapshot now: {state, pid?, phase?, beat_at?}.
    running: a job (this process, or another one with a fresh heartbeat);
    held:    the lock is taken but nobody beats (an operator hold, or a stuck job): the
             result file stays as it is until the lock is released;
    idle:    nobody holds the lock (no operator looked lately: the next request starts it)."""
    with _jobs_lock:
        job = _jobs.get(store.path)
        mine = job is not None and job.thread is not None and job.thread.is_alive()
    if mine:
        return dict(state='running', pid=os.getpid(), phase=job.phase, beat_at=round(job.beat_at, 3))
    path = _paths(store)['lock']
    beat = _load_json(path, {}) or {}
    beat = beat if isinstance(beat, dict) else {}
    at = float(beat.get('at') or 0)
    if time.time() - at <= BEAT_STALE and _alive(beat.get('pid')):
        return dict(state='running', pid=beat.get('pid'), phase=beat.get('phase'), beat_at=at)
    if not os.path.exists(path):
        return dict(state='idle', beat_at=None)
    fd = _try_lock(path)  # a crashed holder's flock() is gone with it: then the lock is free
    if fd is not None:
        _unlock(fd)
        return dict(state='idle', beat_at=at or None)
    return dict(state='held', beat_at=at or None)


def _alive(pid) -> bool:
    """Is process `pid` (same machine: the lock file is in the data directory) still there?"""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if pid == os.getpid() or os.name == 'nt':  # Windows: os.kill would END the process
        return True
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except (OSError, ValueError, OverflowError):
        return False
    return True


def snapshot_info(store, generated_at, period: float = 0.0, deferred=None) -> dict:
    """{computed_at, age, old, job, held, reason}: how current a snapshot is. `old` once it is
    STALE_AFTER past its normal refresh period; `held` when the lock is held without a job
    (reason 'hold') or when the job itself waits for the players to thin out (reason 'busy')."""
    now = time.time()
    js = job_state(store)
    age = round(max(0.0, now - float(generated_at)), 1) if generated_at else None
    reason = 'hold' if js['state'] == 'held' else ('busy' if deferred else None)
    return dict(computed_at=generated_at, age=age, old=age is None or age > period + STALE_AFTER,
                job=js['state'], held=reason is not None, reason=reason)


class _Job:
    """Save-derived numbers and table sizes, refreshed in the background (see the module doc).
    `lock_fd` None: a one-off synchronous run (refresh_now) without pauses."""

    def __init__(self, store, lock_fd=None, pause: float = PAUSE):
        self.store, self.lock_fd, self.pause = store, lock_fd, pause
        self.p = _paths(store)
        self.event = threading.Event()
        self.thread = None
        self.saves_at = self.sys_at = self.summary_at = 0.0
        self.purged_at = self.kpi_at = 0.0
        self.phase, self.beat_at = 'start', 0.0
        loaded = _load_json(self.p['rows'], {})
        self.rows = loaded if isinstance(loaded, dict) else {}   # sid -> [revision, compact row or None]
        self.out = dict(_result(store))
        self.out.pop('deferred', None)
        self.errors = {}   # pass -> {error, at}: the last failure of each pass, until it succeeds again

    def beat(self, phase: str | None = None, force: bool = False) -> None:
        """Heartbeat into the lock file (background job only), at most every BEAT_EVERY s
        unless the phase changes."""
        if phase and phase != self.phase:
            self.phase, force = phase, True
        now = time.time()
        if self.lock_fd is None or (not force and now - self.beat_at < BEAT_EVERY):
            return
        self.beat_at = now
        _write_beat(self.lock_fd, dict(pid=os.getpid(), at=round(now, 3), phase=self.phase))

    # ---- one chunk of saves: [(sid, revision, compact row or None)]
    def _chunk(self, part: list) -> list:
        store = self.store
        try:
            with _read(store, CHUNK_MS) as db:
                if _is_pg(db):
                    sql = (f"SELECT sid, revision, {_COMPACT_PG} FROM (SELECT sid, revision, state::jsonb AS j "
                           f"FROM sessions WHERE sid = ANY(%s) AND state <> '') s")
                    return [(r[0], r[1], json.loads(r[2])) for r in db.pg(sql, (list(part),))]
                marks = ','.join('?' * len(part))
                return [(r[0], r[1], json.loads(r[2])) for r in
                        db.execute(f'SELECT sid, revision, {_COMPACT} FROM sessions WHERE sid IN ({marks})', part)]
        except Busy:
            raise
        except _db_errors():  # malformed JSON, no JSON1, or jsonb refuses a save: read these in Python
            out = []
            with _read(store, CHUNK_MS) as db:
                marks = ','.join('?' * len(part))
                for r in db.execute(f'SELECT sid, revision, state FROM sessions WHERE sid IN ({marks})', part):
                    try:
                        out.append((r[0], r[1], compact(json.loads(r[2]))))
                    except ValueError:
                        out.append((r[0], r[1], None))
            self.engine = 'python'
            return out

    def pass_saves(self) -> None:
        t0 = time.perf_counter()
        self.engine = 'sql'
        with _read(self.store, 5000) as db:
            got = db.execute('SELECT sid, revision, updated_at FROM sessions WHERE revision > 0 ORDER BY updated_at DESC LIMIT ?', (SAMPLE,)).fetchall()
        head = [(r[0], r[1]) for r in got]
        # The sample is not random: it is the SAMPLE saves changed last, i.e. every player active
        # since `covers` (a census of the recent players, which the page says).
        covers = min((r[2] for r in got), default=None)
        rev = dict(head)
        todo = [sid for sid, r in head if (self.rows.get(sid) or [None])[0] != r]
        i, batch, skipped, shown = 0, CHUNK, 0, time.monotonic()
        while i < len(todo):
            if self.lock_fd is not None and not self.may_go():
                self.out.pop('progress', None)
                if i:  # keep what was read: the next pass goes on from there
                    _write_json(self.p['rows'], self.rows)
                return
            self.beat('saves')
            part = todo[i:i + batch]
            t = time.monotonic()
            try:
                got = self._chunk(part)
            except Busy:
                if batch > 1:
                    batch = max(1, batch // 2)
                    continue
                got = [(part[0], rev[part[0]], None)]  # one save alone is over budget: skip it until it changes
                skipped += 1
            for sid, r, row in got:
                self.rows[sid] = [r, row]
            i += len(part)
            if self.lock_fd is not None and time.monotonic() - shown > 2:  # progress for the page
                shown = time.monotonic()
                self.out['progress'] = dict(done=i, total=len(todo), at=round(time.time(), 3))
                _write_json(self.p['result'], self.out)
            if self.pause:
                time.sleep(max(0.02, (time.monotonic() - t) * self.pause))
        for sid in [s for s in self.rows if s not in rev]:  # deleted, or fell out of the window
            del self.rows[sid]
        rows = [self.rows[sid][1] for sid, _ in head if sid in self.rows and self.rows[sid][1] is not None]
        skipped = sum(1 for sid, _ in head if sid in self.rows and self.rows[sid][1] is None)
        out = dict(play_stats(rows), sample=dict(size=len(rows), limit=SAMPLE, engine=self.engine, reread=len(todo), skipped=skipped,
                                                 covers_since=covers, kind='recent'))
        try:
            out['sizes'] = save_sizes(self.store, [sid for sid, _ in head])
        except (Busy,) + _db_errors() as exc:
            _log('save sizes', exc)
        try:  # the day's median wallet of the sample, kept (the history of the economy card)
            w = out['economy']['wallet']
            if w.get('median') is not None:
                kpi.set_daily(self.store, 'wallet_median', w['median'])
                kpi.set_daily(self.store, 'wallet_p90', w['p90'])
                kpi.set_daily(self.store, 'wallet_n', len(rows))
        except Exception as exc:  # noqa: BLE001 - a missing history point is not worth a failed pass
            _log('wallet history', exc)
        out['generated_at'] = round(time.time(), 3)
        out['took_ms'] = round((time.perf_counter() - t0) * 1000, 1)
        self.out['saves'] = out
        if self.out.get('invest'):   # the overview's sample parts follow the new sample (no other read)
            from . import admin_kpi
            admin_kpi.with_saves(self.out['invest'], out)
        self.out.pop('progress', None)
        self.out.pop('deferred', None)
        self.saves_at = time.time()
        if todo or not os.path.exists(self.p['rows']):
            _write_json(self.p['rows'], self.rows)

    def pass_kpi(self) -> None:
        """The investor overview (game/admin_kpi.py): first the finished days are frozen (short
        writes, in order), then the payload is computed under its own budgets."""
        from . import admin_kpi
        self.beat('kpi')
        if self.lock_fd is None or self.may_go():
            self.out['kpi_freeze'] = kpi.freeze(self.store, pause=0.05 if self.pause else 0)
        self.beat('kpi')
        self.out['invest'] = admin_kpi.compute(self.store, self.out.get('saves'))
        self.kpi_at = time.time()

    def may_go(self) -> bool:
        """Background pass only, before each chunk: False once the operator left the page, or
        after the machine stayed busy for BUSY_WAIT seconds. Players come first."""
        waited = 0.0
        while True:
            want = _load_json(self.p['want'], {}) or {}
            if time.time() - float(want.get('at') or 0) > IDLE:
                return False
            load = _load()
            if load <= BUSY_LOAD:
                return True
            if waited >= BUSY_WAIT:
                # The page says so ("held for the players"); the next loop turn tries again.
                self.out['deferred'] = dict(reason='busy', at=round(time.time(), 3), load=round(load, 2))
                return False
            self.beat('saves-wait')
            time.sleep(5)
            waited += 5

    def pass_system(self) -> None:
        t0 = time.perf_counter()
        store, tables = self.store, []
        pg = _store_pg(store)
        with _read(store, 3000) as db:
            if pg:
                names = [r[0] for r in db.pg("SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                                             "WHERE c.relkind = 'r' AND n.nspname = current_schema() AND c.relname <> 'mnl_meta' ORDER BY c.relname")]
                size = db.pg('SELECT pg_database_size(current_database())').fetchone()[0]   # as the live counter
                engine = 'PostgreSQL ' + db.pg('SHOW server_version').fetchone()[0].split()[0]
            else:
                names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
                size, engine = _file_bytes(store), 'SQLite ' + sqlite3.sqlite_version
        for name in names:
            rows, approx = None, False
            try:
                with _read(store, COUNT_MS) as db:
                    rows = db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            except Busy:  # a big table: estimate instead of scanning it
                approx = True
                try:
                    with _read(store, COUNT_MS) as db:
                        rows = (db.pg('SELECT GREATEST(reltuples, 0)::bigint FROM pg_class WHERE oid = to_regclass(%s)', (name,)) if pg else
                                db.execute(f'SELECT MAX(rowid) FROM "{name}"')).fetchone()[0]
                except (Busy,) + _db_errors():
                    rows = None
            tables.append(dict(name=name, rows=int(rows or 0), approx=approx or rows is None))
            if self.pause:
                time.sleep(0.01)
        self.out['system'] = dict(tables=tables, db_bytes=int(size), database=engine, generated_at=round(time.time(), 3),
                                  took_ms=round((time.perf_counter() - t0) * 1000, 1))
        self.sys_at = time.time()

    def pass_summary(self) -> None:
        """The first screen for every range, with a long budget: a request whose own read runs
        out of time (a cold disk) serves this copy instead (see get_summary)."""
        out = dict(self.out.get('summary') or {})
        for days in RANGES:
            self.beat('summary')
            out[str(days)] = summary(self.store, days, JOB_SUMMARY_MS)
            self.out['summary'] = out
            if self.pause:
                time.sleep(0.05)
        self.summary_at = time.time()

    def purge(self) -> None:
        upkeep(self.store)
        self.purged_at = time.time()

    def write(self) -> None:
        self.out['job'] = dict(pid=os.getpid(), at=round(time.time(), 3))
        self.out['errors'] = dict(self.errors)
        _write_json(self.p['result'], self.out)

    def step(self, name: str, fn) -> bool:
        """One pass. A failure is logged with its message, kept in the result (`errors`) and
        does not stop the other passes; the caller retries it after its period."""
        self.beat(name)
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - one pass failing must not starve the others
            _log(f'job {name}', exc)
            self.errors[name] = dict(error=_brief(exc), at=round(time.time(), 3))
            return False
        self.errors.pop(name, None)
        return True

    # ---- the loop (only in the process that holds the lock file)
    def run(self) -> None:
        try:
            self.beat('start', force=True)
            while True:
                want = _load_json(self.p['want'], {}) or {}
                now = time.time()
                with _jobs_lock:
                    if now - float(want.get('at') or 0) > IDLE:  # nobody is looking: stop
                        _jobs.pop(self.store.path, None)
                        break
                fresh = float(want.get('fresh') or 0)
                # Cheapest first: the first screen, the table sizes, then the saves. A pass that
                # failed waits its normal period (the saves: SAVES_RETRY) before the next try.
                if now - self.summary_at >= SUMMARY_EVERY:
                    if not self.step('summary', self.pass_summary):
                        self.summary_at = time.time()
                    self.write()
                if now - self.sys_at >= SYSTEM_EVERY or fresh > self.sys_at:
                    if not self.step('system', self.pass_system):
                        self.sys_at = time.time()
                    self.write()
                # The investor overview before the saves (small tables only; it reuses the last
                # saves result for the wallet and size cards).
                if now - self.kpi_at >= KPI_EVERY or fresh > self.kpi_at:
                    if not self.step('kpi', self.pass_kpi):
                        self.kpi_at = time.time()
                    self.write()
                if now - self.saves_at >= SAVES_EVERY or fresh > self.saves_at:
                    if not self.step('saves', self.pass_saves):
                        self.saves_at = time.time() - SAVES_EVERY + SAVES_RETRY
                    self.write()
                if now - self.purged_at >= PURGE_EVERY:
                    if not self.step('purge', self.purge):
                        self.purged_at = time.time()
                self.beat('wait')
                self.event.wait(2)
                self.event.clear()
        except Exception as exc:  # noqa: BLE001 - never take the worker down
            _log('job stopped', exc)
            with _jobs_lock:
                if _jobs.get(self.store.path) is self:
                    _jobs.pop(self.store.path, None)
        finally:
            if self.lock_fd is not None:
                _write_beat(self.lock_fd, dict(pid=os.getpid(), at=0, phase='stopped'))
                _unlock(self.lock_fd)
                self.lock_fd = None


PURGE_EVERY = 6 * 3600
PURGE_ROWS = 2000          # stat_play rows per delete


def _sparse(hist) -> dict:
    return {str(i): int(n) for i, n in enumerate(hist) if n}


def play_rollup(store, day: str) -> bool:
    """One day of stat_play summed into stat_play_daily (players, seconds, sessions, commands and the
    histograms of play_day, sparse), once; True when the day has its row (written now or before)."""
    with _read(store, 10000, 10000) as db:
        if db.execute('SELECT 1 FROM stat_play_daily WHERE day = ?', (day,)).fetchone():
            return True
        d = play_day(db, day)
    data = json.dumps(dict(per_player=_sparse(d['per_player']), per_session=_sparse(d['per_session']), hours=d['hours'],
                           first_at=d['first_at'], new=dict(d['new'], hist=_sparse(d['new']['hist'])), buckets=PLAY_BUCKETS),
                      separators=(',', ':'))
    with store.connect() as db:
        db.execute('INSERT OR IGNORE INTO stat_play_daily(day, players, secs, sessions, cmds, data, at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (day, d['players'], d['secs'], d['sessions'], d['cmds'], data, time.time()))
    return True


def upkeep(store, now: float | None = None, force: bool = False) -> dict:
    """Bounded stat tables, in short writes: stat_active days older than KEEP_DAYS (one day per
    write); stat_play days older than PLAY_KEEP_DAYS, each first summed into stat_play_daily (kept),
    PURGE_ROWS rows per write; then the Giữ chân tables (game/retention.py maintain: rollups and
    pruning). Never at the peak hours (unless `force`). Run by the admin job and by the server's
    housekeeping."""
    from . import retention
    out = dict(active=0, play=0)
    if not force and retention._peak(time.time() if now is None else now):
        out['skipped'] = 'peak'
        return out
    today = datetime.datetime.now(VN).date()
    cut = (today - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    # The finished days are frozen first (daily KPIs, stat_players): a stat_active day is only
    # dropped once it is frozen, so no number loses its history.
    try:
        out['freeze'] = kpi.freeze(store, now)
    except Exception as exc:  # noqa: BLE001
        _log('freeze', exc)
    with _read(store, 1000) as db:
        done = db.execute("SELECT MAX(day) FROM stat_kpi_daily WHERE key = '_done'").fetchone()[0]
    cut = min(cut, kpi.plus(done, 1) if done else '0000-00-00')
    with _read(store, 1000) as db:
        days = [r[0] for r in db.execute('SELECT DISTINCT day FROM stat_active WHERE day < ? ORDER BY day LIMIT 30', (cut,))]
    for day in days:
        with store.connect() as db:
            out['active'] += db.execute('DELETE FROM stat_active WHERE day = ?', (day,)).rowcount
        time.sleep(0.05)
    cut = (today - datetime.timedelta(days=PLAY_KEEP_DAYS)).isoformat()
    with _read(store, 1000) as db:
        days = [r[0] for r in db.execute('SELECT DISTINCT day FROM stat_play WHERE day < ? ORDER BY day LIMIT 30', (cut,))]
    for day in days:
        if not play_rollup(store, day):
            continue
        while True:
            with store.connect() as db:
                n = db.execute('DELETE FROM stat_play WHERE day = ? AND sid IN (SELECT sid FROM stat_play WHERE day = ? ORDER BY sid LIMIT ?)',
                               (day, day, PURGE_ROWS)).rowcount
            out['play'] += n
            time.sleep(0.05)
            if n < PURGE_ROWS:
                break
    with store.connect() as db:
        db.execute('DELETE FROM stat_play_est WHERE day < ?', (cut,))
    out['retention'] = retention.maintain(store, now, force=force)
    return out
_jobs: dict[str, _Job] = {}
_jobs_lock = threading.Lock()


def wake(store, fresh: bool = False) -> None:
    """An operator is looking: keep the job running (start it here if no process runs it)."""
    p = _paths(store)
    now = round(time.time(), 3)
    old = _load_json(p['want'], {}) or {}
    if fresh or now - float(old.get('at') or 0) > 5:  # one small file write per few seconds at most
        _write_json(p['want'], dict(at=now, fresh=now if fresh else old.get('fresh', 0)))
    with _jobs_lock:
        job = _jobs.get(store.path)
        if job is not None and job.thread is not None and job.thread.is_alive():
            job.event.set()
            return
        fd = _try_lock(p['lock'])
        if fd is None:  # another worker process runs it
            return
        job = _jobs[store.path] = _Job(store, fd)
        job.thread = threading.Thread(target=job.run, daemon=True, name='admin-stats-job')
        job.thread.start()


def refresh_now(store) -> dict:
    """The job's work once, synchronously and without pauses (tests, tools)."""
    job = _Job(store, None, pause=0)
    job.pass_summary()
    job.pass_system()
    job.pass_saves()
    job.pass_kpi()
    job.write()
    return job.out


def stop_jobs(timeout: float = 5.0, store=None) -> None:
    """Stop the background jobs of this process (or only `store`'s) and release their lock
    files: server shutdown and tests."""
    with _jobs_lock:
        keys = [k for k in _jobs if store is None or k == store.path]
        jobs = [_jobs.pop(k) for k in keys]
    for job in jobs:
        _write_json(job.p['want'], dict(at=0, fresh=0))
        job.event.set()
        if job.thread is not None:
            job.thread.join(timeout)


# ---------------------------------------------------------------- the payloads
def _stamp(out: dict, t0: float) -> dict:
    out['generated_at'] = round(time.time(), 3)
    out['took_ms'] = round((time.perf_counter() - t0) * 1000, 1)
    return out


def summary(store, days: int, ms: int | None = None) -> dict:
    """First screen: players, activity, retention, feedback, AI, light server facts. SQL on
    small tables and indexes, read-only, under REQUEST_MS on a request (`ms` in the job);
    no save is read."""
    t0 = time.perf_counter()
    today = datetime.datetime.now(VN).date()
    with _read(store, ms or REQUEST_MS, statement_ms=ms) as db:
        who = players(db, days, today)
        fb = feedback(db, days, time.time())
    srv = server_light(store)
    sysd = _result(store).get('system') or {}
    if srv['db_bytes'] is None:
        srv['db_bytes'] = sysd.get('db_bytes')
    if sysd.get('database', '').startswith('PostgreSQL'):
        srv['database'] = sysd['database']
    return _stamp(dict(range=days, today=today.isoformat(), players=who, feedback=fb, ai=ai_usage(store),
                       server=srv, names=career_names()), t0)


_live_off: dict[str, float] = {}   # db path -> no live summary read before this time
LIVE_OFF = 20.0                    # after a live read ran out of time, the job's copy for this long


def _summary_now(store, days: int) -> dict:
    """The summary read live within REQUEST_MS; past it (a cold or busy disk), the job's copy
    (`stale`: computed in the background with a longer budget), and no live read is tried for
    LIVE_OFF seconds, so a slow disk is not asked twice. Busy when there is no copy yet."""
    if time.monotonic() >= _live_off.get(store.path, 0.0):
        try:
            return summary(store, days)
        except Busy:
            _live_off[store.path] = time.monotonic() + LIVE_OFF
    got = (_result(store).get('summary') or {}).get(str(days))
    if not got:
        raise Busy('admin stats: the first summary is still being computed')
    return dict(got, ai=ai_usage(store), stale=True)


def _with_age(data: dict, store=None) -> dict:
    """The summary as served: `computed_at` (when its numbers were read), `age` (seconds),
    `old` (older than STALE_AFTER: the page warns), and for the job's copy the job's state."""
    at = data.get('generated_at')
    age = round(max(0.0, time.time() - float(at)), 1) if at else None
    out = dict(data, computed_at=at, age=age, old=age is None or age > STALE_AFTER)
    if data.get('stale') and store is not None:
        out['job'] = job_state(store)['state']
    return out


def _empty_saves() -> dict:
    return dict(play_stats([]), sample=dict(size=0, limit=SAMPLE, engine='sql', reread=0, skipped=0))


def saves_section(store) -> dict:
    """The job's save-derived numbers, or {pending, progress} before its first pass."""
    r = _result(store)
    sv = r.get('saves')
    if not sv:
        info = snapshot_info(store, None, SAVES_EVERY, r.get('deferred'))
        return dict(pending=True, retry_ms=3000, progress=r.get('progress'), snapshot=info, errors=r.get('errors') or {})
    out = dict(sv, cached=True, age=round(max(0.0, time.time() - sv['generated_at']), 1),
               snapshot=snapshot_info(store, sv['generated_at'], SAVES_EVERY, r.get('deferred')), errors=r.get('errors') or {})
    if r.get('progress'):
        out['progress'] = r['progress']
    return out


def system_section(store) -> dict:
    r = _result(store)
    sysd = r.get('system')
    if not sysd:
        return dict(pending=True, retry_ms=3000)
    srv = dict(server_light(store), tables=sysd['tables'], db_bytes=sysd['db_bytes'], database=sysd['database'])
    return dict(server=srv, generated_at=sysd['generated_at'], took_ms=sysd['took_ms'], cached=True,
                age=round(max(0.0, time.time() - sysd['generated_at']), 1), ai=ai_usage(store),
                snapshot=snapshot_info(store, sysd['generated_at'], SYSTEM_EVERY), errors=r.get('errors') or {})


def _full(store, days: int) -> dict:
    """Everything in one payload (GET /api/admin/stats, the in-game "Thống kê" tab),
    from the summary and the job's result: no save is read here either."""
    t0 = time.perf_counter()
    top = _summary_now(store, days)
    sv = saves_section(store)
    pending = bool(sv.get('pending'))
    if pending:
        sv = _empty_saves()
    srv = dict(top['server'], tables=(_result(store).get('system') or {}).get('tables', []))
    out = dict(range=days, today=top['today'], players=top['players'], **{k: sv[k] for k in ('play', 'economy', 'life', 'board')},
               feedback=top['feedback'], ai=ai_usage(store), server=srv, sample={k: sv['sample'][k] for k in ('size', 'limit', 'engine')},
               pending=pending, saves_at=sv.get('generated_at'))
    return _stamp(out, t0)


def compute(store, days: int) -> dict:
    """Everything, computed now: the job's work run synchronously, then the full payload
    (tests and tools; the request path uses get(), which never reads saves)."""
    refresh_now(store)
    _result_cache.pop(_paths(store)['result'], None)
    return _full(store, days)


# ---------------------------------------------------------------- in-memory cache, single flight
_cache: dict[tuple, tuple[float, dict]] = {}
_cache_lock = threading.Lock()
_running: set = set()
_done: dict[tuple, threading.Event] = {}
WAIT = 5.0  # a request for a cold entry that another thread is computing waits this long


def _refresh(key, produce) -> dict:
    """Caller has claimed `key`."""
    try:
        data = produce()
        with _cache_lock:
            _cache[key] = (time.monotonic(), data)
        return data
    except Busy:
        raise
    except _db_errors() as exc:  # the server answers OSError with a plain 500
        _log('read', exc)
        raise OSError('admin stats unavailable') from exc
    finally:
        with _cache_lock:
            _running.discard(key)
            ev = _done.pop(key, None)
        if ev:
            ev.set()


def _claim(key) -> None:
    """Caller holds _cache_lock and saw `key not in _running`."""
    _running.add(key)
    _done[key] = threading.Event()


def _background(key, produce) -> None:
    try:
        _refresh(key, produce)
    except Exception as exc:  # keep serving the stale copy
        _log('refresh', exc)


def _serve(key, produce, ttl: float, fresh: bool = False) -> dict:
    """Fresh entry: served. Stale: served, one thread refreshes it. Cold (or `fresh` and
    older than 10 s): computed by this request; concurrent requests wait for that one."""
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        age = now - hit[0] if hit else None
        busy = key in _running
        if hit and not busy and age >= ttl and not fresh:
            _claim(key)
            threading.Thread(target=_background, args=(key, produce), daemon=True, name='admin-stats').start()
        want = hit is None or (fresh and age >= 10)
        inline = want and not busy
        if inline:
            _claim(key)
        done = _done.get(key) if want and not inline else None
    if inline:
        return dict(_refresh(key, produce), cached=False, age=0)
    if not want:
        return dict(hit[1], cached=True, age=round(age, 1))
    if done is not None:
        done.wait(WAIT)
    with _cache_lock:
        hit = _cache.get(key)
    if hit is None:
        raise Busy('admin stats: still computing')
    return dict(hit[1], cached=True, age=round(time.monotonic() - hit[0], 1))


def parse_range(value) -> int:
    try:
        days = int(value or 7)
    except (TypeError, ValueError):
        days = 0
    if days not in RANGES:
        raise ValueError('range')
    return days


def get(store, value=None, fresh: bool = False) -> dict:
    """GET /api/admin/stats: the full payload, cached per range for TTL."""
    days = parse_range(value)
    wake(store, fresh)
    return dict(_serve((store.path, days), lambda: _full(store, days), TTL, fresh), ai=ai_usage(store))


def get_summary(store, value=None, fresh: bool = False) -> dict:
    """GET /api/admin/stats/summary: all the first screen needs, in one call (and the job
    is woken up, since the operator scrolls to the saves cards next)."""
    days = parse_range(value)
    wake(store)
    try:
        return _with_age(dict(_serve(('summary', store.path, days), lambda: _summary_now(store, days), SUMMARY_TTL, fresh), ai=ai_usage(store)), store)
    except Busy:  # nothing to show yet: the page keeps its placeholders and asks again
        return dict(pending=True, retry_ms=3000, range=days)


SECTIONS = ('saves', 'system', 'live', 'playtime', 'retention', 'invest')


def invest_section(store) -> dict:
    """"Tổng quan đầu tư" (game/admin_kpi.py): the job's copy (computed every KPI_EVERY while
    an operator looks), or {pending} before its first pass. AI calls are read fresh."""
    r = _result(store)
    inv = r.get('invest')
    if not inv:
        return dict(pending=True, retry_ms=3000, errors=r.get('errors') or {})
    out = dict(inv, cached=True, age=round(max(0.0, time.time() - float(inv.get('generated_at') or 0)), 1),
               errors=r.get('errors') or {})
    out['next_in'] = round(max(0.0, KPI_EVERY - out['age']), 0)
    return out


def get_live(store) -> dict:
    """The live counters, cached LIVE_TTL per worker; they neither wake nor wait for the job."""
    try:
        return dict(_serve(('live', store.path), lambda: live(store), LIVE_TTL))
    except Busy:  # over LIVE_MS (a very busy database): the page keeps what it shows and asks again
        return dict(pending=True, retry_ms=5000)


def get_section(store, name, fresh: bool = False) -> dict:
    """GET /api/admin/stats/section?name=saves|system|live|playtime|retention: the job's result file
    (instant), the live counters, the play time or "Giữ chân" (small stat tables, cached)."""
    if name not in SECTIONS:
        raise ValueError('section')
    if name == 'live':
        return get_live(store)
    if name == 'playtime':
        return get_playtime(store, fresh)
    if name == 'retention':
        from . import admin_retention
        return admin_retention.get(store, fresh)
    wake(store, fresh)
    if name == 'invest':
        return invest_section(store)
    return saves_section(store) if name == 'saves' else system_section(store)


def clear_cache() -> None:
    from . import admin_retention
    admin_retention.clear_cache()
    with _cache_lock:
        _cache.clear()
    with _play_lock:
        _play_days.clear()
    _result_cache.clear()
    _live_off.clear()
