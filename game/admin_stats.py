"""Operator statistics ("Thống kê"): one cheap, cached summary for the admin dashboard.

GET /api/admin/stats?range=7|30|90 (server.py) returns `get(store, range)`. Only
aggregate numbers leave this module: no sid, token, csrf, password, e-mail,
player name or free text other than the operator's own feedback previews.

How it stays cheap
* SQL does the counting. `ensure()` adds, once, an index on sessions(updated_at,
  revision, sid) and three small triggers that keep day-level activity:
  `stat_births` (the day each save was created) and `stat_active` (one row per
  save per day it changed). Rows follow the save: deleting a save deletes them.
  History before `ensure()` ran falls back to each save's last `updated_at`.
* State-derived numbers read only the SAMPLE most recent saves that did at
  least one action, and SQLite's JSON functions pull out a few small fields in
  C (sqlite releases the GIL while it steps). A pure Python reader is the
  fallback for a SQLite without JSON1.
* The result is cached per range for TTL seconds. A stale entry is served at
  once while one background thread refreshes it; only a cold cache computes
  inline.
* AI usage has no stored log, so `install_ai_counters()` wraps ai.chat,
  ai.clean_reply and ai.abusive with in-memory per-day counters ("since
  restart"). The wrappers only count; arguments and results pass through.

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

from . import __version__

RANGES = (7, 30, 90)
TTL = 60.0
SAMPLE = max(100, int(os.environ.get('ADMIN_STATS_SAMPLE', '5000') or 5000))
KEEP_DAYS = 120            # stat_active history kept
COHORT_DAYS = 30           # retention looks at players who started in the last 30 days (or the range, if longer)
TZ = '+7 hours'
VN = datetime.timezone(datetime.timedelta(hours=7))
STARTED = time.time()
TOP_CAREERS = 20
WALLET_BUCKETS = ((None, 0, 'Nợ (< 0)'), (0, 100, '0–99'), (100, 500, '100–499'), (500, 2000, '500–1.999'), (2000, None, '≥ 2.000'))
LEVEL_CAP = 6              # "6+"
AI_DAYS = 14

SCHEMA = f"""
CREATE INDEX IF NOT EXISTS stat_sessions_seen ON sessions(updated_at, revision, sid);
CREATE TABLE IF NOT EXISTS stat_births (sid TEXT PRIMARY KEY, day TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS stat_births_day ON stat_births(day);
CREATE TABLE IF NOT EXISTS stat_active (day TEXT NOT NULL, sid TEXT NOT NULL, PRIMARY KEY(day, sid)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS stat_active_sid ON stat_active(sid);
CREATE TABLE IF NOT EXISTS stat_fb_ack (id INTEGER PRIMARY KEY, at REAL NOT NULL);
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


def ensure(store) -> None:
    """Idempotent: index, day tables and triggers (see the module doc)."""
    with store.connect() as db:
        db.executescript(SCHEMA)
    install_ai_counters()


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
_SAMPLE_SQL = """
SELECT json_object(
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
) FROM (SELECT state FROM sessions WHERE revision > 0 ORDER BY updated_at DESC LIMIT ?)
"""


def compact(state: dict) -> dict:
    """Pure Python twin of _SAMPLE_SQL (fallback and tests)."""
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
    """(compact rows, engine) for the `limit` most recently active saves."""
    try:
        rows = [json.loads(r[0]) for r in db.execute(_SAMPLE_SQL, (int(limit),))]
        return rows, 'sql'
    except sqlite3.OperationalError:  # no JSON1 in this SQLite
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
    act = (f"WITH act AS (SELECT day, sid FROM stat_active WHERE day >= :from UNION "
           f"SELECT date(updated_at, '{TZ}'), sid FROM sessions WHERE updated_at >= :since AND revision > 0) ")
    args = dict(since=since, **{'from': (today - datetime.timedelta(days=max(days, 30) - 1)).isoformat()})
    dau = _series(span, db.execute(act + 'SELECT day, COUNT(*) FROM act WHERE day >= :start GROUP BY day', dict(args, start=start)))
    window = lambda n: db.execute(act + 'SELECT COUNT(DISTINCT sid) FROM act WHERE day >= :start',
                                  dict(args, start=(today - datetime.timedelta(days=n - 1)).isoformat())).fetchone()[0]
    wau, mau = window(7), window(30)
    new_sessions = _series(span, db.execute('SELECT day, COUNT(*) FROM stat_births WHERE day >= ? GROUP BY day', (start,)))
    new_players = _series(span, db.execute('SELECT b.day, COUNT(*) FROM stat_births b WHERE b.day >= ? AND EXISTS '
                                           '(SELECT 1 FROM stat_active a WHERE a.sid = b.sid) GROUP BY b.day', (start,)))
    new_accounts = _series(span, db.execute(f"SELECT date(created_at, '{TZ}') AS d, COUNT(*) FROM accounts WHERE d >= ? GROUP BY d", (start,)))
    tracked = db.execute('SELECT MIN(day) FROM stat_births').fetchone()[0]
    return dict(days=span, total=total, played=played, accounts=accounts, guests=guests, account_saves=owned,
                dau=dau, new_sessions=new_sessions, new_players=new_players, new_accounts=new_accounts,
                wau=wau, mau=mau, retention=retention(db, today, max(days, COHORT_DAYS)), tracked_since=tracked)


def retention(db, today: datetime.date, window: int) -> dict:
    """Classic D1/D7 over players who started in the window: a save counts when it
    did something on its first day; it is kept when it did something again exactly
    1 (or 7) days later. Only cohorts whose day 1 / day 7 is over count."""
    start = (today - datetime.timedelta(days=window - 1)).isoformat()
    t = today.isoformat()
    row = db.execute("""
      WITH c AS (SELECT b.sid, b.day FROM stat_births b WHERE b.day >= :start
                 AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = b.sid AND a.day = b.day))
      SELECT COUNT(*),
        SUM(CASE WHEN date(day, '+1 day') < :t THEN 1 ELSE 0 END),
        SUM(CASE WHEN date(day, '+1 day') < :t AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = c.sid AND a.day = date(c.day, '+1 day')) THEN 1 ELSE 0 END),
        SUM(CASE WHEN date(day, '+7 day') < :t THEN 1 ELSE 0 END),
        SUM(CASE WHEN date(day, '+7 day') < :t AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = c.sid AND a.day = date(c.day, '+7 day')) THEN 1 ELSE 0 END)
      FROM c""", dict(start=start, t=t)).fetchone()
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
    waits = [r[0] for r in db.execute(
        "SELECT COALESCE(a.at, MIN(p.updated_at, COALESCE(p.replied_at, p.updated_at))) - p.created_at FROM player_feedback p "
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


def server_info(store, db) -> dict:
    size = 0
    for suffix in ('', '-wal'):
        try:
            size += os.path.getsize(store.path + suffix)
        except OSError:
            pass
    tables = []
    for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        tables.append(dict(name=name, rows=db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]))
    return dict(version=__version__, uptime=int(time.time() - STARTED), started=round(STARTED, 3), db_bytes=size, tables=tables,
                python='.'.join(map(str, sys.version_info[:3])), sqlite=sqlite3.sqlite_version, story=bool(getattr(store, 'story', False)))


# ---------------------------------------------------------------- compute + cache
def compute(store, days: int) -> dict:
    t0 = time.perf_counter()
    now = time.time()
    today = datetime.datetime.now(VN).date()
    with store.connect() as db:  # short write, committed before the long reads
        db.execute('DELETE FROM stat_active WHERE day < ?', ((today - datetime.timedelta(days=KEEP_DAYS)).isoformat(),))
    with store.connect() as db:
        who = players(db, days, today)
        rows, engine = sample(db)
        fb = feedback(db, days, now)
        srv = server_info(store, db)
    out = dict(range=days, today=today.isoformat(), players=who, **play_stats(rows), feedback=fb, ai=ai_usage(), server=srv,
               sample=dict(size=len(rows), limit=SAMPLE, engine=engine))
    out['generated_at'] = round(time.time(), 3)
    out['took_ms'] = round((time.perf_counter() - t0) * 1000, 1)
    return out


_cache: dict[tuple, tuple[float, dict]] = {}
_cache_lock = threading.Lock()
_running: set = set()


def _refresh(store, days: int) -> dict:
    key = (store.path, days)
    try:
        data = compute(store, days)
        with _cache_lock:
            _cache[key] = (time.monotonic(), data)
        return data
    except sqlite3.Error as exc:  # the server answers OSError with a plain 500
        raise OSError('admin stats unavailable') from exc
    finally:
        with _cache_lock:
            _running.discard(key)


def _background(store, days: int) -> None:
    try:
        _refresh(store, days)
    except Exception as exc:  # keep serving the stale copy
        sys.stderr.write(f'[admin-stats] {type(exc).__name__}\n')


def parse_range(value) -> int:
    try:
        days = int(value or 7)
    except (TypeError, ValueError):
        days = 0
    if days not in RANGES:
        raise ValueError('range')
    return days


def get(store, value=None, fresh: bool = False) -> dict:
    """Cached summary. Stale data is served while one thread recomputes;
    `fresh` recomputes inline when the cached copy is older than 10 s."""
    days = parse_range(value)
    key = (store.path, days)
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(key)
        age = now - hit[0] if hit else None
        busy = key in _running
        if hit and not busy and age >= TTL and not fresh:
            _running.add(key)
            threading.Thread(target=_background, args=(store, days), daemon=True, name='admin-stats').start()
        cold = hit is None or (fresh and age >= 10)
        if cold:
            _running.add(key)
    if cold:
        data = _refresh(store, days)
        return dict(data, cached=False, age=0, ai=ai_usage())
    data = hit[1]
    return dict(data, cached=True, age=round(age, 1), ai=ai_usage())


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
