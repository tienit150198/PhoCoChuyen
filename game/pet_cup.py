"""🏟️ Giải đấu pet tuần (owner 19/10 "thêm thi đua nữa nhé"): a Swiss tournament of the arena's lineups, once a week.

* Sign up (`cup_join`) any time in the Vietnam week before the cup starts (Sunday RUN_HOUR, outside the 17:30–20:00
  peak; PET_CUP_DOW / PET_CUP_HOUR). Who signs up needs what ranked needs (game/pet_arena.py: an account old enough,
  a lineup). At most MAX_ENTRIES.
* At the start (server.py housekeeping, or the first page that looks after it) every entry's lineup is taken as it
  is then (the arena snapshot) and the whole tournament is played at once, on the server, in one transaction under an
  advisory lock (exactly once): ROUNDS Swiss rounds (the same score meets the same score, never twice the same
  opponent while another is free; an odd one out gets a bye = a win), score win 2, draw 1, ties broken by Buchholz
  (the opponents' scores) then the arena rating. Every match is a pet_arena_matches row (kind 'cup', rd its round): a
  replay like any other. Fewer than MIN_ENTRIES: cancelled (nothing lost: nothing was paid).
* Titles (game/lb_titles.py board 'pet_cup', from the latest cup): 👑 Vô địch giải pet tuần, 🥈 Top 3 giải pet tuần,
  🎗️ Top 10 giải pet tuần. No xu, no item: a title, for a week.
"""
from __future__ import annotations

import os

from . import pet_arena as A
from . import pet_battle as B

MAX_ENTRIES = 1024
MIN_ENTRIES = 4
MAX_ROUNDS = 7
LOCK_KEY = 17824


def _env_int(name: str, default: int, lo: int, hi: int) -> int:
    try:
        v = int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
    return v if lo <= v <= hi else default


def run_at(t: float) -> float:
    """When the cup of the Vietnam week of `t` starts (Sunday 21:00 by default)."""
    from .wedding_live import week_start
    return week_start(t) + _env_int('PET_CUP_DOW', 6, 0, 6) * 86400 + _env_int('PET_CUP_HOUR', 21, 0, 23) * 3600


def rounds_for(n: int) -> int:
    r = 1
    while (1 << r) < n:
        r += 1
    return max(1, min(MAX_ROUNDS, max(3, r), n - 1))


# ---------------------------------------------------------------- signing up
def act(store, token, op, data, state, ip=''):
    if op == 'cup_board':
        return board(store, token, data)
    sid, display = A._who(store, token)
    A._gate(state, display)
    t = A.now()
    week = A.vn_week(t)
    A.need(t < run_at(t), 'Giải tuần này đã bắt đầu. Giải tuần sau mở đăng ký từ thứ Hai nhé.', 'closed', 409)

    def run(db):
        if op == 'cup_leave':
            db.execute('DELETE FROM pet_cup_entries WHERE week=? AND sid=?', (week, sid))
            return dict(ok=True, joined=False, message='Đã rút tên khỏi giải tuần.')
        A.need(A._old_enough(db, sid, t), f'Tài khoản cần đủ {A.ACCOUNT_DAYS} ngày mới đăng ký giải được.', 'too_new', 403)
        A._sync(db, sid, state, display, A.ip_tag(ip), t)
        db.execute('SELECT pg_advisory_xact_lock(?, hashtext(?))', (LOCK_KEY, week))
        n = int(db.execute('SELECT COUNT(*) FROM pet_cup_entries WHERE week=?', (week,)).fetchone()[0])
        mine = db.execute('SELECT 1 FROM pet_cup_entries WHERE week=? AND sid=?', (week, sid)).fetchone()
        A.need(mine or n < MAX_ENTRIES, f'Giải tuần đã đủ {MAX_ENTRIES} người rồi.', 'full', 409)
        db.execute('INSERT INTO pet_cup_entries(week, sid, name, at) VALUES(?,?,?,?) ON CONFLICT (week, sid) DO UPDATE SET name=EXCLUDED.name',
                   (week, sid, display[:24], t))
        return dict(ok=True, joined=True, message='🏟️ Đã đăng ký giải tuần! Đội đang xếp sẽ ra sân lúc giải bắt đầu.')
    A.need(op in ('cup_join', 'cup_leave'), 'Thao tác không hợp lệ.', 'unknown', 404)
    return store.transaction(run)


def summary(store, sid: str, t: float) -> dict:
    """The arena home's card: this week's cup (when, how many, joined) and the last one's result for this player."""
    week = A.vn_week(t)
    with store.connect() as db:
        n = int(db.execute('SELECT COUNT(*) FROM pet_cup_entries WHERE week=?', (week,)).fetchone()[0])
        joined = bool(db.execute('SELECT 1 FROM pet_cup_entries WHERE week=? AND sid=?', (week, sid)).fetchone())
        last = db.execute('SELECT * FROM pet_cup ORDER BY week DESC LIMIT 1').fetchone()
        mine = db.execute('SELECT rank, score FROM pet_cup_entries WHERE week=? AND sid=?', (last['week'], sid)).fetchone() if last else None
    at = run_at(t)
    return dict(week=week, at=at, open=t < at, n=n, joined=joined, min=MIN_ENTRIES,
                last=dict(week=last['week'], status=last['status'], n=last['n'], rounds=last['rounds'],
                          rank=mine['rank'] if mine and last['status'] == 'done' else None) if last else None)


# ---------------------------------------------------------------- the tournament
def run_due(store, t: float | None = None) -> bool:
    """Play this week's cup when its time has come and it was not played yet (cheap otherwise: one read)."""
    t = A.now() if t is None else t
    if t < run_at(t):
        return False
    week = A.vn_week(t)
    with store.connect() as db:
        if db.execute('SELECT 1 FROM pet_cup WHERE week=?', (week,)).fetchone():
            return False
    return bool(store.transaction(lambda db: play(db, week, t)))


PAIR_TRIES = 20_000


def pair_round(order: list) -> list:
    """Swiss pairs of `order` (best first): each player meets the best one below them they have not met, backtracking
    when a greedy choice would force a rematch further down (at most PAIR_TRIES steps; then greedy, a rematch allowed)."""
    budget = [PAIR_TRIES]

    def rec(free):
        if not free:
            return []
        p = free[0]
        for j in range(1, len(free)):
            q = free[j]
            if q['sid'] in p['opps']:
                continue
            budget[0] -= 1
            if budget[0] < 0:
                return None
            rest = rec(free[1:j] + free[j + 1:])
            if rest is not None:
                return [(p, q)] + rest
        return None
    got = rec(list(order)) if len(order) <= 2 * 400 else None
    if got is not None:
        return got
    pairs, free = [], list(order)
    while free:
        p = free.pop(0)
        q = next((x for x in free if x['sid'] not in p['opps']), free[0])
        free.remove(q)
        pairs.append((p, q))
    return pairs


def play(db, week: str, t: float) -> bool:
    """The whole Swiss tournament of `week`, once (the advisory lock and the pet_cup row)."""
    db.execute('SELECT pg_advisory_xact_lock(?, hashtext(?))', (LOCK_KEY, week))
    if db.execute('SELECT 1 FROM pet_cup WHERE week=?', (week,)).fetchone():
        return False
    rows = db.execute('SELECT e.sid, e.name, p.snap, p.rating FROM pet_cup_entries e JOIN pet_arena p ON p.sid=e.sid '
                      'WHERE e.week=? AND p.size>0 ORDER BY e.at, e.sid LIMIT ?', (week, MAX_ENTRIES)).fetchall()
    ps = []
    for r in rows:
        snap = [f for f in (B.clean(x) for x in A._j(r['snap'], [])) if f]
        if snap:
            ps.append(dict(sid=r['sid'], name=r['name'] or 'Người chơi', snap=snap, rating=A.season_peek(db, week, r['sid'], int(r['rating'])),
                           score=0, opps=[], bye=False))
    if len(ps) < MIN_ENTRIES:
        db.execute("INSERT INTO pet_cup(week, status, n, rounds, at) VALUES(?, 'cancelled', ?, 0, ?)", (week, len(ps), t))
        return True
    rounds = rounds_for(len(ps))
    for rd in range(1, rounds + 1):
        order = sorted(ps, key=lambda p: (-p['score'], -p['rating'], p['sid']))
        if len(order) % 2:
            bye = next(p for p in reversed(order) if not p['bye'])
            bye['bye'] = True
            bye['score'] += 2
            order.remove(bye)
        pairs = pair_round(order)
        for i, (p, q) in enumerate(pairs):
            mid = f'c{week}-{rd}-{i}'
            res = B.battle(p['snap'], q['snap'], B.seed_of(mid))
            p['opps'].append(q['sid'])
            q['opps'].append(p['sid'])
            p['score'] += (2, 0, 1)[res['w']]
            q['score'] += (0, 2, 1)[res['w']]
            A.record(db, 'cup', mid, dict(sid=p['sid'], name=p['name']), dict(sid=q['sid'], name=q['name']), p['snap'], q['snap'], res, t,
                     p['rating'], q['rating'], rd=rd)
    by = {p['sid']: p for p in ps}
    for p in ps:
        p['tb'] = sum(by[o]['score'] for o in p['opps'])
    final = sorted(ps, key=lambda p: (-p['score'], -p['tb'], -p['rating'], p['sid']))
    for i, p in enumerate(final):
        db.execute('UPDATE pet_cup_entries SET rating=?, snap=?, score=?, tb=?, rank=? WHERE week=? AND sid=?',
                   (p['rating'], A._dump(p['snap']), p['score'], p['tb'], i + 1, week, p['sid']))
    db.execute("INSERT INTO pet_cup(week, status, n, rounds, at) VALUES(?, 'done', ?, ?, ?)", (week, len(ps), rounds, t))
    return True


def standings(db, n: int, week_max: str | None = None) -> list:
    """[(board, rank, sid, score)] of the latest cup played (of a week up to `week_max`: game/lb_titles.py heal), in the
    boards' privacy."""
    from .leaderboard import _VISIBLE
    last = (db.execute("SELECT week FROM pet_cup WHERE status='done' AND week<=? ORDER BY week DESC LIMIT 1", (week_max,)).fetchone() if week_max
            else db.execute("SELECT week FROM pet_cup WHERE status='done' ORDER BY week DESC LIMIT 1").fetchone())
    if not last:
        return []
    rows = db.execute('SELECT e.sid, e.score FROM pet_cup_entries e LEFT JOIN accounts a ON a.sid=e.sid LEFT JOIN leaderboard_players p ON p.sid=e.sid '
                      f'WHERE e.week=? AND e.rank>0 AND {_VISIBLE} ORDER BY e.rank LIMIT ?', (last['week'], n)).fetchall()
    return [('pet_cup', i + 1, r['sid'], int(r['score'])) for i, r in enumerate(rows)]


def board(store, token, data) -> dict:
    """A cup's table (the latest by default, or `week`): the top, the viewer's place and matches, the titles block."""
    sid = store.resolve(token)[0] if isinstance(token, str) else None
    week = data.get('week') if isinstance(data.get('week'), str) and len(data.get('week')) <= 10 else None
    with store.connect() as db:
        cup = db.execute('SELECT * FROM pet_cup WHERE week=?', (week,)).fetchone() if week else \
            db.execute('SELECT * FROM pet_cup ORDER BY week DESC LIMIT 1').fetchone()
        if not cup:
            return dict(ok=True, cup=None)
        rows = [dict(r) for r in db.execute('SELECT sid, rank, score, tb, rating, snap FROM pet_cup_entries WHERE week=? AND rank>0 ORDER BY rank LIMIT 50',
                                            (cup['week'],)).fetchall()]
        names = A._names(db, [r['sid'] for r in rows])
        me = db.execute('SELECT rank, score, tb FROM pet_cup_entries WHERE week=? AND sid=?', (cup['week'], sid)).fetchone() if sid else None
        mine = [dict(r) for r in db.execute("SELECT * FROM pet_arena_matches WHERE week=? AND kind='cup' AND (a=? OR b=?) ORDER BY rd",
                                            (cup['week'], sid, sid)).fetchall()] if sid else []
    from . import lb_titles as lbt
    try:
        weekly = lbt.board_view(store, lbt.PET_CUP, sid)
    except Exception:  # noqa: BLE001 - the table shows without its titles block
        weekly = None
    top = []
    for r in rows:
        snap = A._j(r['snap'], [])
        top.append(dict(rank=r['rank'], name=names.get(r['sid'], 'Một người chơi'), score=r['score'] / 2, tb=r['tb'] / 2,
                        rating=r['rating'], me=r['sid'] == sid, pets=[A.pet_view(f) for f in snap[:3]]))
    return dict(ok=True, cup=dict(week=cup['week'], status=cup['status'], n=cup['n'], rounds=cup['rounds']), top=top,
                me=dict(rank=me['rank'], score=me['score'] / 2) if me and me['rank'] else None,
                matches=[dict(A._summary(m, sid), rd=m['rd']) for m in mine], weekly=weekly)
