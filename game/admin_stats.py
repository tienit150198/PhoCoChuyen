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

Days are Vietnam days (UTC+7), matching the players.
"""
from __future__ import annotations
import datetime
import hashlib
import json
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path

from . import __version__

try:  # PostgreSQL backend (game/db.py); a tree without it is SQLite only
    from . import db as dbm
except ImportError:  # pragma: no cover
    dbm = None

RANGES = (7, 30, 90)
TTL = 60.0                 # full payload (in-game tab)
# The saves section is expensive (each save is parsed whole): it is refreshed rarely, from a
# small sample, and never while the machine is busy serving players (see _Job.may_go).
SAVES_EVERY = float(os.environ.get('ADMIN_STATS_SAVES_EVERY', '1800') or 1800)  # seconds between two passes over the saves
BUSY_LOAD = 0.7            # the job waits while the 1-minute load average is over BUSY_LOAD per core
BUSY_WAIT = 60.0           # ... and gives the pass up after waiting this long (the next one tries again)
SUMMARY_TTL = 30.0
SYSTEM_EVERY = 120.0       # table sizes
SUMMARY_EVERY = 60.0       # the job's copy of the first screen (served when a live read runs out of time)
IDLE = 600.0               # the job stops this long after the last admin request
SAMPLE = max(100, int(os.environ.get('ADMIN_STATS_SAMPLE', '400') or 400))
KEEP_DAYS = 120            # stat_active history kept
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
    """Idempotent: indexes, day tables and triggers (see the module doc)."""
    if _store_pg(store):
        _ensure_pg(store)
    else:
        with store.connect() as db:
            db.executescript(SCHEMA)
    install_ai_counters()


def _ensure_pg(store) -> None:
    """The admin indexes, skipped when present. Several workers start at once, and two
    concurrent CREATE INDEX IF NOT EXISTS can still collide: the loser just moves on (the
    admin queries work without the index, only slower)."""
    for name, sql in PG_INDEXES:
        try:
            with store.connect() as db:
                if not db.execute('SELECT 1 FROM pg_indexes WHERE schemaname = current_schema() AND indexname = ?', (name,)).fetchone():
                    db.execute(sql)
        except dbm.Error:
            pass


# ---------------------------------------------------------------- AI counters (in memory)
_ai_lock = threading.Lock()
_ai: dict[str, dict] = {}
_blocked: dict[str, set] = {}
AI_KEYS = ('calls', 'ok', 'failed', 'busy', 'rejected', 'guard')


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


def install_ai_counters() -> None:
    from . import ai
    for name, wrap in (('chat', _counted_chat), ('clean_reply', _counted_clean), ('abusive', _counted_abusive)):
        fn = getattr(ai, name, None)
        if callable(fn) and not getattr(fn, '_counted', False):
            setattr(ai, name, wrap(fn))


def ai_usage() -> dict:
    with _ai_lock:
        days = [dict(day=d, **row) for d, row in sorted(_ai.items())]
    total = {k: sum(r[k] for r in days) for k in AI_KEYS}
    from . import ai
    return dict(since=round(STARTED, 3), configured=bool(ai.available()), total=total, days=days[-AI_DAYS:])


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
def players(db, days: int, today: datetime.date) -> dict:
    span = _days(today, days)
    start = span[0]
    since = (datetime.datetime.combine(today - datetime.timedelta(days=max(days, 30) + 1), datetime.time()) - datetime.timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
    total = db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
    played = db.execute('SELECT COUNT(*) FROM sessions WHERE revision > 0').fetchone()[0]
    accounts = db.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]
    owned = db.execute('SELECT COUNT(*) FROM sessions WHERE sid IN (SELECT sid FROM accounts)').fetchone()[0]
    guests = db.execute('SELECT COUNT(*) FROM sessions WHERE revision > 0 AND sid NOT IN (SELECT sid FROM accounts)').fetchone()[0]
    # Activity: the day log, plus each save's last change (covers days before the log existed).
    pg = _is_pg(db)
    if pg:
        run = db.pg
        act = ("WITH act AS (SELECT day, sid FROM stat_active WHERE day >= %(from)s UNION "
               "SELECT to_char(updated_at::timestamp + interval '7 hours', 'YYYY-MM-DD'), sid FROM sessions "
               "WHERE updated_at >= %(since)s AND revision > 0) ")
        mark = '%(start)s'
    else:
        run = db.execute
        act = (f"WITH act AS (SELECT day, sid FROM stat_active WHERE day >= :from UNION "
               f"SELECT date(updated_at, '{TZ}'), sid FROM sessions WHERE updated_at >= :since AND revision > 0) ")
        mark = ':start'
    args = dict(since=since, **{'from': (today - datetime.timedelta(days=max(days, 30) - 1)).isoformat()})
    dau = _series(span, run(act + f'SELECT day, COUNT(*) FROM act WHERE day >= {mark} GROUP BY day', dict(args, start=start)))
    window = lambda n: run(act + f'SELECT COUNT(DISTINCT sid) FROM act WHERE day >= {mark}',
                           dict(args, start=(today - datetime.timedelta(days=n - 1)).isoformat())).fetchone()[0]
    wau, mau = window(7), window(30)
    new_sessions = _series(span, db.execute('SELECT day, COUNT(*) FROM stat_births WHERE day >= ? GROUP BY day', (start,)))
    new_players = _series(span, db.execute('SELECT b.day, COUNT(*) FROM stat_births b WHERE b.day >= ? AND EXISTS '
                                           '(SELECT 1 FROM stat_active a WHERE a.sid = b.sid) GROUP BY b.day', (start,)))
    # created_at is UTC text: the range starts at Vietnam midnight of `start` (an index range, not a scan).
    utc_start = (datetime.datetime.fromisoformat(start) - datetime.timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S')
    day_of = "to_char(created_at::timestamp + interval '7 hours', 'YYYY-MM-DD')" if pg else f"date(created_at, '{TZ}')"
    new_accounts = _series(span, db.execute(f'SELECT {day_of} AS d, COUNT(*) FROM accounts WHERE created_at >= ? GROUP BY d', (utc_start,)))
    tracked = db.execute('SELECT MIN(day) FROM stat_births').fetchone()[0]
    return dict(days=span, total=total, played=played, accounts=accounts, guests=guests, account_saves=owned,
                dau=dau, new_sessions=new_sessions, new_players=new_players, new_accounts=new_accounts,
                wau=wau, mau=mau, retention=retention(db, today, max(days, COHORT_DAYS)), tracked_since=tracked)


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
    in_range = db.execute('SELECT COUNT(*) FROM player_feedback WHERE created_at >= ?', (now - days * 86400,)).fetchone()[0]
    # First time a note left "new": the trigger's exact time, else the best guess from older rows.
    least = 'LEAST' if _is_pg(db) else 'MIN'  # SQLite's MIN(a, b) is PostgreSQL's LEAST(a, b)
    waits = [r[0] for r in db.execute(
        f"SELECT COALESCE(a.at, {least}(p.updated_at, COALESCE(p.replied_at, p.updated_at))) - p.created_at FROM player_feedback p "
        'LEFT JOIN stat_fb_ack a ON a.id = p.id WHERE p.status != ? AND p.created_at >= ?', ('new', now - max(days, 30) * 86400)) if r[0] is not None]
    waits = [max(0.0, w) for w in waits]
    newest = [dict(id=r[0], kind=r[1], status=r[2], text=(r[3] or '').split('\n')[0][:90], created_at=r[4])
              for r in db.execute('SELECT id, kind, status, text, created_at FROM player_feedback ORDER BY id DESC LIMIT 5')]
    open_n = sum(table[k]['new'] + table[k]['seen'] for k in kinds)
    return dict(kinds=[dict(kind=k, **table[k]) for k in kinds], open=open_n, unread=sum(table[k]['new'] for k in kinds),
                total=sum(sum(v.values()) for v in table.values()), in_range=in_range,
                ack=dict(n=len(waits), median_h=round(_pct(waits, .5) / 3600, 1) if waits else None,
                         avg_h=round(sum(waits) / len(waits) / 3600, 1) if waits else None),
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
                story=bool(getattr(store, 'story', False)))


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


class _Job:
    """Save-derived numbers and table sizes, refreshed in the background (see the module doc).
    `lock_fd` None: a one-off synchronous run (refresh_now) without pauses."""

    def __init__(self, store, lock_fd=None, pause: float = PAUSE):
        self.store, self.lock_fd, self.pause = store, lock_fd, pause
        self.p = _paths(store)
        self.event = threading.Event()
        self.thread = None
        self.saves_at = self.sys_at = self.summary_at = 0.0
        self.purged_at = 0.0
        loaded = _load_json(self.p['rows'], {})
        self.rows = loaded if isinstance(loaded, dict) else {}   # sid -> [revision, compact row or None]
        self.out = dict(_result(store))

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
            head = [(r[0], r[1]) for r in db.execute(
                'SELECT sid, revision FROM sessions WHERE revision > 0 ORDER BY updated_at DESC LIMIT ?', (SAMPLE,))]
        rev = dict(head)
        todo = [sid for sid, r in head if (self.rows.get(sid) or [None])[0] != r]
        i, batch, skipped, shown = 0, CHUNK, 0, time.monotonic()
        while i < len(todo):
            if self.lock_fd is not None and not self.may_go():
                self.out.pop('progress', None)
                if i:  # keep what was read: the next pass goes on from there
                    _write_json(self.p['rows'], self.rows)
                return
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
        out = dict(play_stats(rows), sample=dict(size=len(rows), limit=SAMPLE, engine=self.engine, reread=len(todo), skipped=skipped))
        out['generated_at'] = round(time.time(), 3)
        out['took_ms'] = round((time.perf_counter() - t0) * 1000, 1)
        self.out['saves'] = out
        self.out.pop('progress', None)
        self.saves_at = time.time()
        if todo or not os.path.exists(self.p['rows']):
            _write_json(self.p['rows'], self.rows)

    def may_go(self) -> bool:
        """Background pass only, before each chunk: False once the operator left the page, or
        after the machine stayed busy for BUSY_WAIT seconds. Players come first."""
        waited = 0.0
        while True:
            want = _load_json(self.p['want'], {}) or {}
            if time.time() - float(want.get('at') or 0) > IDLE:
                return False
            if _load() <= BUSY_LOAD:
                return True
            if waited >= BUSY_WAIT:
                return False
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
                size = db.pg("SELECT COALESCE(SUM(pg_total_relation_size(c.oid)), 0) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                             "WHERE c.relkind = 'r' AND n.nspname = current_schema()").fetchone()[0]
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
            out[str(days)] = summary(self.store, days, JOB_SUMMARY_MS)
            self.out['summary'] = out
            if self.pause:
                time.sleep(0.05)
        self.summary_at = time.time()

    def purge(self) -> None:
        """Drop stat_active days older than KEEP_DAYS, one day per short write."""
        cut = (datetime.datetime.now(VN).date() - datetime.timedelta(days=KEEP_DAYS)).isoformat()
        with _read(self.store, 1000) as db:
            days = [r[0] for r in db.execute('SELECT DISTINCT day FROM stat_active WHERE day < ? ORDER BY day LIMIT 30', (cut,))]
        for day in days:
            with self.store.connect() as db:
                db.execute('DELETE FROM stat_active WHERE day = ?', (day,))
            time.sleep(0.05)
        self.purged_at = time.time()

    def write(self) -> None:
        self.out['job'] = dict(pid=os.getpid(), at=round(time.time(), 3))
        _write_json(self.p['result'], self.out)

    # ---- the loop (only in the process that holds the lock file)
    def run(self) -> None:
        try:
            while True:
                want = _load_json(self.p['want'], {}) or {}
                now = time.time()
                with _jobs_lock:
                    if now - float(want.get('at') or 0) > IDLE:  # nobody is looking: stop
                        _jobs.pop(self.store.path, None)
                        break
                fresh = float(want.get('fresh') or 0)
                try:  # cheapest first: the first screen, the table sizes, then the saves
                    if now - self.summary_at >= SUMMARY_EVERY:
                        self.pass_summary()
                        self.write()
                    if now - self.sys_at >= SYSTEM_EVERY or fresh > self.sys_at:
                        self.pass_system()
                        self.write()
                    if now - self.saves_at >= SAVES_EVERY or fresh > self.saves_at:
                        self.pass_saves()
                        self.write()
                    if now - self.purged_at >= PURGE_EVERY:
                        self.purge()
                except (Busy,) + _db_errors() as exc:
                    sys.stderr.write(f'[admin-stats] job: {type(exc).__name__}\n')
                self.event.wait(2)
                self.event.clear()
        except Exception as exc:  # noqa: BLE001 - never take the worker down
            sys.stderr.write(f'[admin-stats] job stopped: {type(exc).__name__}\n')
            with _jobs_lock:
                if _jobs.get(self.store.path) is self:
                    _jobs.pop(self.store.path, None)
        finally:
            if self.lock_fd is not None:
                _unlock(self.lock_fd)
                self.lock_fd = None


PURGE_EVERY = 6 * 3600
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
    return _stamp(dict(range=days, today=today.isoformat(), players=who, feedback=fb, ai=ai_usage(),
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
    return dict(got, ai=ai_usage(), stale=True)


def _empty_saves() -> dict:
    return dict(play_stats([]), sample=dict(size=0, limit=SAMPLE, engine='sql', reread=0, skipped=0))


def saves_section(store) -> dict:
    """The job's save-derived numbers, or {pending, progress} before its first pass."""
    r = _result(store)
    sv = r.get('saves')
    if not sv:
        return dict(pending=True, retry_ms=3000, progress=r.get('progress'))
    out = dict(sv, cached=True, age=round(max(0.0, time.time() - sv['generated_at']), 1))
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
                age=round(max(0.0, time.time() - sysd['generated_at']), 1), ai=ai_usage())


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
               feedback=top['feedback'], ai=ai_usage(), server=srv, sample={k: sv['sample'][k] for k in ('size', 'limit', 'engine')},
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
        sys.stderr.write(f'[admin-stats] {type(exc).__name__}\n')


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
    return dict(_serve((store.path, days), lambda: _full(store, days), TTL, fresh), ai=ai_usage())


def get_summary(store, value=None, fresh: bool = False) -> dict:
    """GET /api/admin/stats/summary: all the first screen needs, in one call (and the job
    is woken up, since the operator scrolls to the saves cards next)."""
    days = parse_range(value)
    wake(store)
    try:
        return dict(_serve(('summary', store.path, days), lambda: _summary_now(store, days), SUMMARY_TTL, fresh), ai=ai_usage())
    except Busy:  # nothing to show yet: the page keeps its placeholders and asks again
        return dict(pending=True, retry_ms=3000, range=days)


SECTIONS = ('saves', 'system')


def get_section(store, name, fresh: bool = False) -> dict:
    """GET /api/admin/stats/section?name=saves|system: from the job's result file (instant)."""
    if name not in SECTIONS:
        raise ValueError('section')
    wake(store, fresh)
    return saves_section(store) if name == 'saves' else system_section(store)


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
    _result_cache.clear()
    _live_off.clear()
