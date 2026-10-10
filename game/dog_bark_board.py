"""Weekly microphone tug-of-war: indexed ticket totals, immutable prizes, no save scans.

Weeks use ticket ended time in Vietnam, [Monday, next Monday). Only done win/lose/draw
count; a match crossing midnight belongs to its finish week. The first invocation
persists the current week, never earlier weeks. Only matches verified by the upgraded live service qualify. A
60-second grace lets transactions at the boundary finish; snapshots never change.

Meta cursor and winner snapshots commit with dedicated bark_weekly effects. Old
workers defer this kind. Deploy all title-aware workers before the first Monday's
prizes: rolling back to an older strict title registry AFTER payment is unsafe.
"""
from __future__ import annotations

import datetime
from fractions import Fraction
import json
import threading
import time

from . import dog_bark as bark

WEEK = 7 * 86400
MINIMUM = 30
GRACE = 60
LIMIT = 20
FX = 'bark_weekly'
META = 'bark-weekly:'
CURSOR = META + 'cursor'
COINS = (2_000_000, 1_000_000, 500_000, 250_000, 100_000)
TITLE_IDS = ('bark_king', 'bark_silver', 'bark_bronze', 'bark_fourth', 'bark_fifth')
TITLE_NAMES = dict(zip(TITLE_IDS, ('Vua kéo co chó sủa', 'Á quân kéo co chó sủa', 'Đệ tam kéo co chó sủa',
                                 'Cao thủ kéo co chó sủa', 'Tài năng kéo co chó sủa')))
EMOJI = ('👑', '🥈', '🥉', '🏅', '🎖️')
_cache = {}
_due = {}
_lock = threading.Lock()
CACHE_SECONDS = 15


def clear_cache():
    with _lock:
        _cache.clear()
        _due.clear()


def week_label(w):
    return datetime.datetime.fromtimestamp(w, bark.VN).date().isoformat()


def titles(make):
    return [make(tid, 'secret', EMOJI[i], TITLE_NAMES[tid],
                 f'Đạt hạng {i+1} giải kéo co chó sủa tuần, ít nhất {MINIMUM} trận hợp lệ.', lambda x: False, True)
            for i, tid in enumerate(TITLE_IDS)]


def _prize(rank):
    if rank and 1 <= rank <= len(COINS):
        return COINS[rank-1], TITLE_NAMES[TITLE_IDS[rank-1]]
    return 0, ''


# bark_tickets_week is the partial index on ended WHERE status='done'. Account
# created_at is UTC text, as in pg_schema.NOW_TEXT; don't inherit an old account's
# tickets if a sid is registered again. No sessions JSON is read.
_STATS = """SELECT b.sid, COUNT(*) AS played,
    SUM(CASE WHEN b.result='win' THEN 1 ELSE 0 END) AS wins, MAX(b.ended) AS achieved
    FROM bark_tickets b JOIN accounts a ON a.sid=b.sid
    WHERE b.status='done' AND b.competitive=true AND b.result IN ('win','lose','draw')
    AND b.ended>=? AND b.ended<?
    AND b.created >= EXTRACT(EPOCH FROM (a.created_at::timestamp AT TIME ZONE 'UTC'))"""


def _people(db, sids):
    if not sids:
        return {}
    marks = ','.join('?' for _ in sids)
    from .accounts import offensive_name
    result = {}
    for r in db.execute(f'SELECT a.sid,a.display,p.show FROM accounts a LEFT JOIN leaderboard_players p ON p.sid=a.sid WHERE a.sid IN ({marks})', tuple(sids)):
        name = str(r['display'] or '')[:24]
        visible = bool(name) and not offensive_name(name) and r['show'] != 0
        result[r['sid']] = dict(name=name if visible else 'Một người chơi', visible=visible)
    return result


def _standings(db, w):
    rows = [dict(r) for r in db.execute(_STATS + ' GROUP BY b.sid HAVING COUNT(*)>=?', (w, w+WEEK, MINIMUM))]
    # Compare integer fractions, never display-rounded percentages. Totals are
    # grouped in PostgreSQL; memory is proportional to active competitors only.
    rows.sort(key=lambda r: (-Fraction(r['wins'], r['played']), -r['wins'], r['achieved'], r['sid']))
    ranked = []
    # Bounded name queries; a hidden or offensive name cannot take a prize slot.
    for start in range(0, len(rows), 200):
        people = _people(db, [r['sid'] for r in rows[start:start+200]])
        for r in rows[start:start+200]:
            if people.get(r['sid'], {}).get('visible'):
                ranked.append(dict(r, rank=len(ranked)+1))
                if len(ranked) == LIMIT:
                    return ranked
    return ranked


def _public(r, name):
    reward, title = _prize(r.get('rank'))
    return dict(rank=r.get('rank'), name=name, wins=int(r['wins']), played=int(r['played']),
                rate=round(100 * int(r['wins']) / int(r['played']), 4) if r['played'] else 0,
                reward=reward, title=title)


def settle(store, t=None, best_effort_ms=None):
    """Settle up to 8 missed weeks per call, atomically. Subsequent ticks catch up.

    Persistent cursor locks serialize workers. In-process due memo avoids a write
    transaction on every lobby poll; losing it on restart is harmless.
    """
    t = bark.now() if t is None else t
    key = store.path
    with _lock:
        if _due.get(key, 0) > t:
            return 0
    w = int(bark.week_start(t))

    def run(db):
        db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING',
                   (CURSOR, json.dumps(dict(first=w, next=w))))
        cursor = json.loads(db.execute('SELECT v FROM leaderboard_meta WHERE k=? FOR UPDATE', (CURSOR,)).fetchone()['v'])
        nxt, count = int(cursor['next']), 0
        for _ in range(8):
            if t < nxt + WEEK + GRACE:
                break
            mark = META + week_label(nxt)
            if db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING', (mark, '[]')).rowcount == 1:
                winners = _standings(db, nxt)[:len(COINS)]
                for r in winners:
                    rank, sid = r['rank'], r['sid']
                    data = dict(week=week_label(nxt), rank=rank, title=TITLE_IDS[rank-1])
                    db.execute("INSERT INTO live_effects(id,sid,kind,amount,data,status,at) VALUES(?,?,?,?,?,'pending',?) ON CONFLICT(id) DO NOTHING",
                               (f'{META}{data["week"]}:{sid}', sid, FX, COINS[rank-1], json.dumps(data), t))
                db.execute('UPDATE leaderboard_meta SET v=? WHERE k=?', (json.dumps(winners), mark))
                count += 1
            nxt += WEEK
        cursor['next'] = nxt
        db.execute('UPDATE leaderboard_meta SET v=? WHERE k=?', (json.dumps(cursor), CURSOR))
        return count, nxt + WEEK + GRACE

    result = store.transaction(run, best_effort_ms)
    if result is None:
        return 0
    with _lock:
        if len(_due) >= 16:
            _due.clear()
        _due[key] = result[1]
    return result[0]


def view(store, sid=None, t=None):
    t = bark.now() if t is None else t
    w = int(bark.week_start(t))
    settle(store, t, best_effort_ms=250)
    key = (store.path, w)
    with _lock:
        cached = _cache.get(key)
    with store.connect() as db:
        if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
            rows = cached[1]
        else:
            rows = _standings(db, w)
            with _lock:
                if len(_cache) >= 16:
                    _cache.clear()
                _cache[key] = (time.monotonic(), rows)
        # Re-read privacy even for cached statistics: hiding a name is immediate.
        people = _people(db, [r['sid'] for r in rows] + ([sid] if sid else []))
        public = [_public(r, people[r['sid']]['name']) for r in rows if people.get(r['sid'], {}).get('visible')]
        me = None
        if sid and sid in people:
            own = db.execute(_STATS + ' AND b.sid=? GROUP BY b.sid', (w, w+WEEK, sid)).fetchone()
            rank = next((r['rank'] for r in rows if r['sid'] == sid), None)
            own = dict(own) if own else dict(wins=0, played=0)
            visible = people[sid]['visible']
            me = _public(dict(own, rank=rank if visible else None), 'Bạn')
            me.update(eligible=visible and own['played']>=MINIMUM, remaining=max(0, MINIMUM-own['played']), visible=visible)
        prev = db.execute('SELECT v FROM leaderboard_meta WHERE k=?', (META+week_label(w-WEEK),)).fetchone()
        previous = None
        if prev:
            won = json.loads(prev['v'])
            names = _people(db, [r['sid'] for r in won])
            previous = dict(week=week_label(w-WEEK), rows=[_public(r, names.get(r['sid'], {}).get('name', 'Một người chơi')) for r in won])
    return dict(week=week_label(w), ends=w+WEEK, minimum=MINIMUM,
                prizes=[dict(rank=i+1, coins=coins, title=TITLE_NAMES[TITLE_IDS[i]]) for i, coins in enumerate(COINS)],
                rows=public, me=me, previous=previous)


def apply_fx(s, p, amount):
    from . import engine as e, journey as jr
    data = p.get('data') if isinstance(p.get('data'), dict) else {}
    rank, week = data.get('rank'), data.get('week')
    e.need(type(rank) is int and 1<=rank<=len(COINS), 'Hạng giải kéo co không hợp lệ.')
    tid = TITLE_IDS[rank-1]
    try:
        day = datetime.date.fromisoformat(week)
        valid_week = day.weekday() == 0 and day.isoformat() == week
    except (TypeError, ValueError):
        valid_week = False
    e.need(valid_week and data.get('title') == tid and amount == COINS[rank-1], 'Giải kéo co không hợp lệ.')
    j = s['journey']
    jr._wallet(j, amount, 'life', f'🐕 Giải kéo co tuần {week} · hạng {rank}')
    if tid not in j['titles']:
        j['titles'][tid] = j['life_day']
        jr._news(j, 'titles', 'titles', [tid])
    return f'🏆 Hạng {rank} kéo co tuần: +{bark.fmt(amount)} xu và danh hiệu {TITLE_NAMES[tid]}.'


def forget(db, sid):
    """Keep final numbers but erase the deleted account's link to past trophies."""
    # Serialize with settlement, so a deleting account cannot receive a new
    # weekly effect between cleanup and account removal in Store.delete.
    db.execute('SELECT v FROM leaderboard_meta WHERE k=? FOR UPDATE', (CURSOR,)).fetchone()
    db.execute('DELETE FROM live_effects WHERE sid=? AND kind=?', (sid, FX))
    rows = db.execute('SELECT k,v FROM leaderboard_meta WHERE k LIKE ? AND v LIKE ? FOR UPDATE',
                      (META+'____-__-__', '%'+sid+'%')).fetchall()
    for r in rows:
        winners = json.loads(r['v'])
        for winner in winners:
            if winner.get('sid') == sid:
                winner['sid'] = ''
        db.execute('UPDATE leaderboard_meta SET v=? WHERE k=?', (json.dumps(winners), r['k']))
    clear_cache()
