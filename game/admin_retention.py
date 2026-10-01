"""Admin "Giữ chân" (GET /api/admin/stats/section?name=retention[&format=csv]): where and how
players drop off, from the stat tables of game/retention.py plus stat_births / stat_active /
stat_play (game/admin_stats.py). Never a save. Read-only, under RET_MS, cached RET_TTL per worker
(served stale while one thread refreshes, like the other sections).

Parts (all aggregates; no sid, name or free text leaves this module):
* cohorts   new players per start day (stat_births with a command that day) and the share who came
            back exactly 1/3/7/14/30 days later (stat_active); None while that day is not over.
* funnel    for players who opened the game today / yesterday / in 7 / 30 days: the share reaching
            each step of retention.MILESTONES and the median time from opening the game.
* by_day    the same shares per start day (14 days), and the 30/09 cohort (before the 0.9.16
            onboarding) against 01/10 onwards. Steps seeded by scripts/milestones_backfill.py
            have no time (`est`).
* churn     players whose last command was 3-30 days ago, grouped by their last leave beacon
            (screen/popup, workplace, life day, onboarding step, last tap) and by their last step;
            and new players who never came back after their first session.
* careers   per workplace: players who served their first customer there (30 days), D3/D7 of new
            players whose first customer was there, and the actions rejected most (7 days).
* sources   new players per source (utm_source, else the referrer's site) over 7 / 30 days with
            their D1 / D7 and the share reaching the first customer.
* loads     time to first byte / DOMContentLoaded / first game frame, p50/p75/p90 per day and by
            network and new vs returning players (7 days).
* errors    the most frequent client errors today and over 7 days.
* sizes     disk size of every stat table ("Dung lượng log").
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import os
import threading
import time

from . import admin_stats as st
from . import retention as rt

RET_TTL = 300.0
RET_MS = int(os.environ.get('ADMIN_STATS_RETENTION_MS', '8000') or 8000)   # all reads of one section request
RET_STATEMENT_MS = 4000
COHORT_DAYS = 30
COHORT_KS = (1, 3, 7, 14, 30)
BY_DAY = 14
BY_DAY_KEYS = ('picked', 'served1', 'served3', 'served10', 'day1', 'day3', 'day7', 'account')
ONBOARDING_DAY = '2026-10-01'      # 0.9.16 (the new first session) went live in the night to 01/10
BEFORE_DAY = '2026-09-30'
CHURN_MIN, CHURN_MAX = 3, 30       # "rớt": last command between 30 and 3 days ago
TOP = 12
PERIODS = (('today', 0, 0), ('yesterday', 1, 1), ('d7', 6, 0), ('d30', 29, 0))
STAT_TABLES = ('stat_births', 'stat_active', 'stat_play', 'stat_play_est', 'stat_play_daily', 'stat_fb_ack') + rt.TABLES


def _plus_sql(db, col: str, n: int) -> str:
    return f"to_char({col}::date + {int(n)}, 'YYYY-MM-DD')" if st._is_pg(db) else f"date({col}, '+{int(n)} day')"


def _day(today: datetime.date, back: int) -> str:
    return (today - datetime.timedelta(days=back)).isoformat()


def _pct(k, n):
    return round(100 * k / n, 1) if n else None


def _utc(t: float) -> str:
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t))


# ---------------------------------------------------------------- cohorts
_cohort_lock = threading.Lock()
_cohort_cache: dict = {}   # (db path, cohort day, today) -> row; a finished cohort day's numbers do not move during a day
COHORT_KEPT = 128


def _cohort(db, day: str, today: str) -> dict:
    ks = [k for k in COHORT_KS]
    sub = 'SUM(CASE WHEN EXISTS (SELECT 1 FROM stat_active a WHERE a.day = ? AND a.sid = b.sid) THEN 1 ELSE 0 END)'
    r = db.execute(f'SELECT COUNT(*), {", ".join([sub] * len(ks))} FROM stat_births b WHERE b.day = ? AND EXISTS '
                   '(SELECT 1 FROM stat_active a WHERE a.day = b.day AND a.sid = b.sid)',
                   (*[rt._plus(day, k) for k in ks], day)).fetchone()
    n = int(r[0] or 0)
    out = dict(day=day, n=n)
    for i, k in enumerate(ks):
        ready = rt._plus(day, k) < today
        out[f'd{k}'] = _pct(int(r[1 + i] or 0), n) if ready else None
        out[f'k{k}'] = int(r[1 + i] or 0) if ready else None
    return out


def cohorts(store, db, today: datetime.date) -> list:
    t = today.isoformat()
    rows = []
    for back in range(COHORT_DAYS):
        day = _day(today, back)
        key = (store.path, day, t)
        hit = _cohort_cache.get(key) if back else None
        if hit is None:
            hit = _cohort(db, day, t)
            if back:
                with _cohort_lock:
                    _cohort_cache[key] = hit
                    while len(_cohort_cache) > COHORT_KEPT:
                        _cohort_cache.pop(next(iter(_cohort_cache)))
        rows.append(hit)
    return rows


def cohort_summary(rows: list) -> dict:
    """D1/D3/D7 over every cohort old enough for it (players-weighted)."""
    out = {}
    for k in COHORT_KS:
        have = [r for r in rows if r.get(f'k{k}') is not None]
        n = sum(r['n'] for r in have)
        out[f'd{k}'] = _pct(sum(r[f'k{k}'] for r in have), n)
        out[f'd{k}_n'] = n
    return out


# ---------------------------------------------------------------- funnel
def _median(values):
    if not values:
        return None
    v = sorted(values)
    i = (len(v) - 1) / 2
    lo, hi = int(i), min(int(i) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def funnel_period(db, start: str, end: str) -> dict:
    """Players born (stat_births) between start and end whose `created` step was recorded: per step,
    how many reached it, how many of those rows are seeded estimates (no time), the median minutes."""
    base = ("FROM stat_births b JOIN stat_milestones c ON c.sid = b.sid AND c.key = 'created' "
            "JOIN stat_milestones m ON m.sid = b.sid WHERE b.day >= ? AND b.day <= ? AND m.key NOT LIKE 'start:%'")
    got = {}
    if st._is_pg(db):
        for key, n, est, med in db.execute(
                'SELECT m.key, COUNT(*), SUM(CASE WHEN m.at IS NULL OR c.at IS NULL THEN 1 ELSE 0 END), '
                'percentile_cont(0.5) WITHIN GROUP (ORDER BY m.at - c.at) FILTER (WHERE m.at IS NOT NULL AND c.at IS NOT NULL) '
                + base + ' GROUP BY m.key', (start, end)):
            got[key] = (int(n), int(est or 0), med)
    else:
        acc = {}
        for key, m_at, c_at in db.execute('SELECT m.key, m.at, c.at ' + base, (start, end)):
            a = acc.setdefault(key, [0, 0, []])
            a[0] += 1
            if m_at is None or c_at is None:
                a[1] += 1
            else:
                a[2].append(m_at - c_at)
        got = {k: (a[0], a[1], _median(a[2])) for k, a in acc.items()}
    n = got.get('created', (0, 0, None))[0]
    steps = []
    for key, label in rt.MILESTONES:
        c, est, med = got.get(key, (0, 0, None))
        steps.append(dict(key=key, label=label, n=c, pct=_pct(c, n), est=est,
                          median_min=None if med is None else round(max(0.0, float(med)) / 60, 1)))
    return dict(start=start, end=end, n=n, est=any(s['est'] for s in steps), steps=steps)


def by_day(db, today: datetime.date) -> dict:
    start = _day(today, BY_DAY - 1)
    first = min(start, BEFORE_DAY)
    keys = ('created',) + BY_DAY_KEYS
    marks = ','.join('?' * len(keys))
    cells = {}
    for day, key, n, est in db.execute(
            f'SELECT b.day, m.key, COUNT(*), SUM(CASE WHEN m.at IS NULL THEN 1 ELSE 0 END) FROM stat_births b '
            f'JOIN stat_milestones m ON m.sid = b.sid WHERE b.day >= ? AND m.key IN ({marks}) GROUP BY b.day, m.key',
            (first, *keys)):
        cells[(day, key)] = (int(n), int(est or 0))

    def row(days):
        n = sum(cells.get((d, 'created'), (0, 0))[0] for d in days)
        est = sum(cells.get((d, 'created'), (0, 0))[1] for d in days)
        pct = {k: _pct(sum(cells.get((d, k), (0, 0))[0] for d in days), n) for k in BY_DAY_KEYS}
        return dict(n=n, est=bool(est), pct=pct)
    rows = [dict(day=d, **row([d])) for d in (_day(today, i) for i in range(BY_DAY))]
    after = [d for d in (_day(today, i) for i in range(0, 400)) if d >= ONBOARDING_DAY]   # today included: "so far"
    compare = dict(before=dict(day=BEFORE_DAY, **row([BEFORE_DAY])),
                   after=dict(start=ONBOARDING_DAY, end=today.isoformat(), **row(after)) if after else None)
    return dict(keys=list(BY_DAY_KEYS), labels={k: v for k, v in rt.MILESTONES}, rows=rows, compare=compare)


# ---------------------------------------------------------------- churn ("Rớt ở đâu")
def _leave(payload) -> dict:
    try:
        d = json.loads(payload)
        return d if type(d) is dict else {}
    except (TypeError, ValueError):
        return {}


def _life_band(d) -> str:
    if type(d) is not int:
        return '?'
    if d <= 3:
        return f'Ngày {d}'
    return 'Ngày 4–7' if d <= 7 else ('Ngày 8–14' if d <= 14 else 'Ngày 15+')


def _screen(p: dict) -> str:
    v, pop = p.get('v') or '?', p.get('p')
    return f'{v} › {pop}' if pop else v


def _top(counter: dict, total: int, n: int = TOP) -> list:
    rows = sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0])))
    return [dict(label=str(k), n=c, pct=_pct(c, total)) for k, c in rows[:n]]


def _group_leaves(payloads: list) -> dict:
    groups = dict(screen={}, career={}, life={}, step={}, tap={})
    for p in payloads:
        for name, value in (('screen', _screen(p)), ('career', p.get('c') or '—'), ('life', _life_band(p.get('d'))),
                            ('step', p.get('t') or '—'), ('tap', (p.get('a') or ['—'])[-1])):
            g = groups[name]
            g[value] = g.get(value, 0) + 1
    n = len(payloads)
    out = {k: _top(v, n) for k, v in groups.items()}
    order = ['Ngày 1', 'Ngày 2', 'Ngày 3', 'Ngày 4–7', 'Ngày 8–14', 'Ngày 15+', '?']
    out['life'].sort(key=lambda r: order.index(r['label']) if r['label'] in order else 99)   # life days in their own order
    return out


def _last_steps(rows) -> dict:
    """{sid: key} of each save's newest timed step (ties: the later step of the funnel)."""
    order = {k: i for i, k in enumerate(rt.KEYS)}
    best = {}
    for sid, key, at in rows:
        if at is None or key.startswith('start:'):
            continue
        cur = best.get(sid)
        if cur is None or (at, order.get(key, -1)) > (cur[1], order.get(cur[0], -1)):
            best[sid] = (key, at)
    return {sid: v[0] for sid, v in best.items()}


def churn(db, now: float, today: datetime.date) -> dict:
    lo, hi = _utc(now - CHURN_MAX * 86400), _utc(now - CHURN_MIN * 86400)
    total = int(db.execute('SELECT COUNT(*) FROM sessions WHERE updated_at >= ? AND updated_at < ? AND revision > 0', (lo, hi)).fetchone()[0])
    payloads = [_leave(r[0]) for r in db.execute(
        'SELECT l.payload FROM sessions s JOIN stat_leave_last l ON l.sid = s.sid '
        'WHERE s.updated_at >= ? AND s.updated_at < ? AND s.revision > 0', (lo, hi))]
    steps = _last_steps(db.execute(
        "SELECT m.sid, m.key, m.at FROM sessions s JOIN stat_milestones m ON m.sid = s.sid "
        "WHERE s.updated_at >= ? AND s.updated_at < ? AND s.revision > 0 AND EXISTS "
        "(SELECT 1 FROM stat_milestones c WHERE c.sid = s.sid AND c.key = 'created' AND c.at IS NOT NULL)", (lo, hi)))
    labels = dict(rt.MILESTONES)
    counts = {}
    for key in steps.values():
        counts[labels.get(key, key)] = counts.get(labels.get(key, key), 0) + 1
    out = dict(window=dict(min_days=CHURN_MIN, max_days=CHURN_MAX), players=total, with_leave=len(payloads),
               tracked=len(steps), by_step=_top(counts, len(steps), 30), **_group_leaves(payloads))
    out['first_session'] = first_session(db, today)
    return out


def first_session(db, today: datetime.date) -> dict:
    """New players (started 3-30 days ago, played on their first day) whose whole play was one
    session: how many, how long it lasted, where they left and their last step."""
    start, end = _day(today, CHURN_MAX), _day(today, CHURN_MIN)
    cohort = int(db.execute('SELECT COUNT(*) FROM stat_births b JOIN stat_play p ON p.sid = b.sid AND p.day = b.day '
                            'WHERE b.day >= ? AND b.day <= ?', (start, end)).fetchone()[0])
    one = ('FROM stat_births b JOIN stat_play p ON p.sid = b.sid AND p.day = b.day WHERE b.day >= ? AND b.day <= ? AND p.sessions = 1 '
           'AND NOT EXISTS (SELECT 1 FROM stat_play q WHERE q.sid = b.sid AND q.day > b.day)')
    rows = list(db.execute('SELECT b.sid, p.secs, l.payload ' + one.replace('WHERE', 'LEFT JOIN stat_leave_last l ON l.sid = b.sid WHERE', 1),
                           (start, end)))
    secs = [int(r[1] or 0) for r in rows]
    payloads = [_leave(r[2]) for r in rows if r[2]]
    steps = _last_steps(db.execute('SELECT m.sid, m.key, m.at ' + one.replace('WHERE', 'JOIN stat_milestones m ON m.sid = b.sid WHERE', 1),
                                   (start, end)))
    labels = dict(rt.MILESTONES)
    counts = {}
    for key in steps.values():
        counts[labels.get(key, key)] = counts.get(labels.get(key, key), 0) + 1
    med = _median(secs)
    return dict(start=start, end=end, cohort=cohort, n=len(rows), pct=_pct(len(rows), cohort), with_leave=len(payloads),
                median_min=None if med is None else round(med / 60, 1), by_step=_top(counts, len(steps), 30),
                **_group_leaves(payloads))


# ---------------------------------------------------------------- careers
def careers(db, now: float, today: datetime.date) -> list:
    since = now - 30 * 86400
    started = {r[0][6:]: int(r[1]) for r in db.execute(
        "SELECT key, COUNT(*) FROM stat_milestones WHERE key >= 'start:' AND key < 'start;' AND at >= ? GROUP BY key", (since,))}
    t = today.isoformat()
    p3, p7 = _plus_sql(db, 'b.day', 3), _plus_sql(db, 'b.day', 7)
    main = {}
    for career, n, n3, k3, n7, k7 in db.execute(
            f"SELECT m.career, COUNT(*), SUM(CASE WHEN {p3} < ? THEN 1 ELSE 0 END), "
            f"SUM(CASE WHEN {p3} < ? AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = b.sid AND a.day = {p3}) THEN 1 ELSE 0 END), "
            f"SUM(CASE WHEN {p7} < ? THEN 1 ELSE 0 END), "
            f"SUM(CASE WHEN {p7} < ? AND EXISTS (SELECT 1 FROM stat_active a WHERE a.sid = b.sid AND a.day = {p7}) THEN 1 ELSE 0 END) "
            "FROM stat_births b JOIN stat_milestones m ON m.sid = b.sid AND m.key = 'served1' "
            "WHERE b.day >= ? AND m.career IS NOT NULL GROUP BY m.career", (t, t, t, t, _day(today, COHORT_DAYS - 1))):
        main[career] = dict(n=int(n), d3=_pct(int(k3 or 0), int(n3 or 0)), d3_n=int(n3 or 0), d7=_pct(int(k7 or 0), int(n7 or 0)), d7_n=int(n7 or 0))
    errs = action_errors(db, today)
    ids = sorted(set(started) | set(main) | set(errs), key=lambda c: (-(main.get(c) or {}).get('n', 0), -started.get(c, 0), c))
    return [dict(id=c, started=started.get(c, 0), main=main.get(c) or dict(n=0, d3=None, d3_n=0, d7=None, d7_n=0),
                 errors=errs.get(c, [])) for c in ids if c]


def action_errors(db, today: datetime.date, days: int = 7) -> dict:
    """{career: [top rejected actions]} over the last `days` days: rolled-up days from
    stat_actions_daily, the others (today, a day not rolled yet) summed from stat_actions."""
    span = [_day(today, i) for i in range(days)]
    rolled = {r[0] for r in db.execute("SELECT day FROM stat_rollups WHERE kind = 'actions' AND day >= ?", (span[-1],))}
    acc = {}

    def add(career, action, n, errors, err):
        a = acc.setdefault((career, action), [0, 0, None])
        a[0] += int(n or 0)
        a[1] += int(errors or 0)
        if err and int(errors or 0):
            a[2] = err
    for r in db.execute('SELECT career, action, SUM(n), SUM(errors), MAX(err) FROM stat_actions_daily WHERE day >= ? GROUP BY career, action',
                        (span[-1],)):
        add(*r)
    for day in span:
        if day not in rolled:
            for r in db.execute('SELECT career, action, SUM(n), SUM(errors), MAX(err) FROM stat_actions WHERE day = ? AND errors > 0 '
                                'GROUP BY career, action', (day,)):
                add(*r)
            for career, action, n in db.execute('SELECT career, action, SUM(n) FROM stat_actions WHERE day = ? AND errors = 0 '
                                                'GROUP BY career, action', (day,)):
                add(career, action, n, 0, None)
    out = {}
    for (career, action), (n, e, err) in acc.items():
        if e:
            out.setdefault(career or '', []).append(dict(action=action, n=n, errors=e, rate=_pct(e, n), err=err))
    return {c: sorted(v, key=lambda x: (-x['errors'], x['action']))[:3] for c, v in out.items()}


# ---------------------------------------------------------------- sources
def sources(db, today: datetime.date) -> dict:
    start, t = _day(today, 29), today.isoformat()
    p1, p7 = _plus_sql(db, 'a.day', 1), _plus_sql(db, 'a.day', 7)
    src = "COALESCE(a.source, a.ref_domain, 'direct')"
    rows = list(db.execute(
        f"SELECT {src}, a.day, COUNT(*), "
        "SUM(CASE WHEN EXISTS (SELECT 1 FROM stat_active x WHERE x.sid = a.sid AND x.day = a.day) THEN 1 ELSE 0 END), "
        f"SUM(CASE WHEN EXISTS (SELECT 1 FROM stat_active x WHERE x.sid = a.sid AND x.day = {p1}) THEN 1 ELSE 0 END), "
        f"SUM(CASE WHEN EXISTS (SELECT 1 FROM stat_active x WHERE x.sid = a.sid AND x.day = {p7}) THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN EXISTS (SELECT 1 FROM stat_milestones m WHERE m.sid = a.sid AND m.key = 'served1') THEN 1 ELSE 0 END) "
        f"FROM stat_acquisition a WHERE a.day >= ? GROUP BY {src}, a.day", (start,)))
    out = {}
    for key, back in (('d7', 6), ('d30', 29)):
        first = _day(today, back)
        acc = {}
        for name, day, n, played, r1, r7, s1 in rows:
            if day < first:
                continue
            a = acc.setdefault(name, dict(n=0, played=0, n1=0, r1=0, n7=0, r7=0, s1=0))
            a['n'] += int(n)
            a['played'] += int(played or 0)
            a['s1'] += int(s1 or 0)
            if rt._plus(day, 1) < t:
                a['n1'] += int(played or 0)
                a['r1'] += int(r1 or 0)
            if rt._plus(day, 7) < t:
                a['n7'] += int(played or 0)
                a['r7'] += int(r7 or 0)
        total = sum(a['n'] for a in acc.values())
        out[key] = [dict(source=name, n=a['n'], share=_pct(a['n'], total), played=a['played'], d1=_pct(a['r1'], a['n1']), d1_n=a['n1'],
                         d7=_pct(a['r7'], a['n7']), d7_n=a['n7'], served1=_pct(a['s1'], a['n']))
                    for name, a in sorted(acc.items(), key=lambda kv: (-kv[1]['n'], kv[0]))][:TOP]
        out[key + '_total'] = total
    return out


# ---------------------------------------------------------------- load times
def _hist_q(hist: dict, q: float):
    n = sum(hist.values())
    if not n:
        return None
    rank, seen = q * n, 0
    for b in sorted(hist):
        c = hist[b]
        if seen + c >= rank:
            lo, hi = rt.bucket_span(b)
            return int(lo + (hi - lo) * max(0.0, rank - seen) / c)
        seen += c
    return None


def _qs(hist: dict) -> dict:
    return dict(n=sum(hist.values()), p50=_hist_q(hist, .5), p75=_hist_q(hist, .75), p90=_hist_q(hist, .9))


def loads(db, today: datetime.date) -> dict:
    start, week = _day(today, 13), _day(today, 6)
    days, nets, who, cache, tier, other = {}, {}, {}, {}, {}, {'ttfb': {}, 'dcl': {}}
    cores = {}
    for day, metric, net, w, c, tr, b, n in db.execute(
            'SELECT day, metric, net, who, cache, tier, bucket, n FROM stat_loads WHERE day >= ?', (start,)):
        n = int(n)
        if metric == 'cores':
            if day >= week:
                cores[int(b)] = cores.get(int(b), 0) + n
            continue
        if metric == 'frame':
            h = days.setdefault(day, {})
            h[b] = h.get(b, 0) + n
            if day >= week:
                for into, k in ((nets, net), (who, w), (cache, c), (tier, tr)):
                    h = into.setdefault(k, {})
                    h[b] = h.get(b, 0) + n
        elif metric in other and day >= week:
            h = other[metric]
            h[b] = h.get(b, 0) + n
    frame7 = {}
    for d, h in days.items():
        if d >= week:
            for b, n in h.items():
                frame7[b] = frame7.get(b, 0) + n
    split = lambda m: [dict(key=k, **_qs(h)) for k, h in sorted(m.items(), key=lambda kv: -sum(kv[1].values()))]
    return dict(days=[dict(day=d, **_qs(days.get(d, {}))) for d in (_day(today, i) for i in range(14))],
                week=dict(frame=_qs(frame7), ttfb=_qs(other['ttfb']), dcl=_qs(other['dcl'])),
                by_net=split(nets), by_who=split(who), by_cache=split(cache), by_tier=split(tier),
                cores=[dict(key=k, n=v) for k, v in sorted(cores.items())])


# ---------------------------------------------------------------- client errors
def client_errors(db, today: datetime.date) -> dict:
    out = {}
    for key, since in (('today', today.isoformat()), ('d7', _day(today, 6))):
        out[key] = [dict(kind=r[0], message=r[1], screen=r[2], n=int(r[3]), last_at=r[4], sample=r[5]) for r in db.execute(
            'SELECT kind, message_key, screen, SUM(count) AS c, MAX(last_at), MAX(sample) FROM stat_client_errors WHERE day >= ? '
            'GROUP BY kind, message_key, screen ORDER BY c DESC, kind, message_key LIMIT ?', (since, TOP))]
        out[key + '_total'] = int(db.execute('SELECT COALESCE(SUM(count), 0) FROM stat_client_errors WHERE day >= ?', (since,)).fetchone()[0])
    return out


# ---------------------------------------------------------------- table sizes
def sizes(db) -> dict:
    rows = []
    if st._is_pg(db):
        rows = [(r[0], int(r[1])) for r in db.pg(
            "SELECT c.relname, pg_total_relation_size(c.oid) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = current_schema() AND c.relkind = 'r' AND c.relname = ANY(%s)", (list(STAT_TABLES),))]
    else:
        try:
            owner = {r[0]: r[1] for r in db.execute("SELECT name, tbl_name FROM sqlite_master WHERE type IN ('table', 'index')")}
            acc = {}
            for name, size in db.execute('SELECT name, SUM(pgsize) FROM dbstat GROUP BY name'):
                t = owner.get(name)
                if t in STAT_TABLES:
                    acc[t] = acc.get(t, 0) + int(size or 0)
            rows = list(acc.items())
        except st._db_errors():
            rows = []   # this SQLite has no dbstat: sizes are shown on PostgreSQL only
    rows.sort(key=lambda r: -r[1])
    return dict(tables=[dict(name=n, bytes=b) for n, b in rows], total=sum(b for _, b in rows) if rows else None)


# ---------------------------------------------------------------- the section
def compute(store, now: float | None = None) -> dict:
    t0 = time.perf_counter()
    now = time.time() if now is None else now
    today = datetime.datetime.fromtimestamp(now, st.VN).date()
    timing = {}

    def part(name, fn):
        t = time.perf_counter()
        out = fn()
        timing[name] = round((time.perf_counter() - t) * 1000, 1)
        return out
    with st._read(store, RET_MS, RET_STATEMENT_MS) as db:
        coh = part('cohorts', lambda: cohorts(store, db, today))
        fun = part('funnel', lambda: [dict(key=k, **funnel_period(db, _day(today, a), _day(today, b))) for k, a, b in PERIODS])
        bd = part('by_day', lambda: by_day(db, today))
        ch = part('churn', lambda: churn(db, now, today))
        ca = part('careers', lambda: careers(db, now, today))
        so = part('sources', lambda: sources(db, today))
        lo = part('loads', lambda: loads(db, today))
        er = part('errors', lambda: client_errors(db, today))
        sz = part('sizes', lambda: sizes(db))
        since = db.execute("SELECT MIN(at) FROM stat_milestones WHERE key = 'created' AND at IS NOT NULL").fetchone()[0]
    out = dict(today=today.isoformat(), since=since, cohorts=coh, cohort_summary=cohort_summary(coh), funnel=fun, by_day=bd,
               churn=ch, careers=ca, sources=so, loads=lo, errors=er, sizes=sz, names=st.career_names(), timing=timing,
               rules=dict(actions_days=rt.ACTIONS_KEEP_DAYS, leaves_days=rt.LEAVES_KEEP_DAYS, errors_days=rt.ERRORS_KEEP_DAYS,
                          onboarding_day=ONBOARDING_DAY, before_day=BEFORE_DAY), buffered=rt.buffered())
    return st._stamp(out, t0)


def get(store, fresh: bool = False) -> dict:
    """The section, cached RET_TTL per worker; it neither wakes nor waits for the admin job."""
    try:
        return dict(st._serve(('retention', store.path), lambda: compute(store), RET_TTL, fresh))
    except st.Busy:
        return dict(pending=True, retry_ms=3000)


def clear_cache() -> None:
    with _cohort_lock:
        _cohort_cache.clear()


# ---------------------------------------------------------------- CSV export
def to_csv(d: dict) -> str:
    """The section's tables as one CSV text: a `# table` line, a header row, the rows, a blank line."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')

    def table(name, head, rows):
        w.writerow([f'# {name}'])
        w.writerow(head)
        for r in rows:
            w.writerow(['' if v is None else v for v in r])
        w.writerow([])
    if d.get('pending'):
        w.writerow(['# pending'])
        return buf.getvalue()
    table('cohorts', ['day', 'players'] + [f'd{k}_pct' for k in COHORT_KS],
          [[r['day'], r['n']] + [r[f'd{k}'] for k in COHORT_KS] for r in d['cohorts']])
    for p in d['funnel']:
        table(f'funnel_{p["key"]}', ['step', 'label', 'players', 'pct', 'median_min', 'estimated'],
              [[s['key'], s['label'], s['n'], s['pct'], s['median_min'], s['est']] for s in p['steps']])
    bd = d['by_day']
    table('funnel_by_start_day', ['day', 'players', 'estimated'] + list(bd['keys']),
          [[r['day'], r['n'], r['est']] + [r['pct'][k] for k in bd['keys']] for r in bd['rows']])
    ch = d['churn']
    for name in ('screen', 'career', 'life', 'step', 'tap', 'by_step'):
        table(f'churn_{name}', ['value', 'players', 'pct'], [[r['label'], r['n'], r['pct']] for r in ch[name]])
    fs = ch['first_session']
    for name in ('screen', 'by_step'):
        table(f'first_session_{name}', ['value', 'players', 'pct'], [[r['label'], r['n'], r['pct']] for r in fs[name]])
    table('careers', ['career', 'started_30d', 'new_main', 'd3_pct', 'd7_pct', 'top_error_action', 'errors', 'error_rate', 'error'],
          [[c['id'], c['started'], c['main']['n'], c['main']['d3'], c['main']['d7']] +
           ([c['errors'][0]['action'], c['errors'][0]['errors'], c['errors'][0]['rate'], c['errors'][0]['err']] if c['errors'] else ['', '', '', ''])
           for c in d['careers']])
    for key in ('d7', 'd30'):
        table(f'sources_{key}', ['source', 'players', 'share_pct', 'd1_pct', 'd7_pct', 'first_customer_pct'],
              [[s['source'], s['n'], s['share'], s['d1'], s['d7'], s['served1']] for s in d['sources'][key]])
    table('load_first_frame_ms', ['day', 'loads', 'p50', 'p75', 'p90'], [[r['day'], r['n'], r['p50'], r['p75'], r['p90']] for r in d['loads']['days']])
    for key in ('by_net', 'by_who', 'by_cache', 'by_tier'):
        table(f'load_{key}_7d', ['key', 'loads', 'p50', 'p75', 'p90'], [[r['key'], r['n'], r['p50'], r['p75'], r['p90']] for r in d['loads'][key]])
    for key in ('today', 'd7'):
        table(f'client_errors_{key}', ['kind', 'message', 'screen', 'count'], [[e['kind'], e['message'], e['screen'], e['n']] for e in d['errors'][key]])
    table('log_sizes', ['table', 'bytes'], [[t['name'], t['bytes']] for t in d['sizes']['tables']])
    return buf.getvalue()
