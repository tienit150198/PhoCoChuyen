"""🪽 Cánh on the main Bảng xếp hạng (owner 23/10: "có hạng cánh nữa nhé, xếp hạng cánh ấy"), like 🐾 Thú cưng
(game/pet_lb.py) and 🏝️ Đảo đẹp (game/island_lb.py).

Score (điểm cánh): every wing a player owns (journey.wings, game/wings.py) counts POINTS[tier] = 3^tier, D 1 … SSS 729,
🌟 Huyền thoại 2187. Three wings of a tier fuse into one of the next, so a fusion that works keeps the score, a miss from S
up costs the two wings lost, and a higher tier always weighs more than a few lower ones. Ties: the best tier, then who
reached that score first (`at`), then a fixed order. Each row shows the best wing (the worn one among the best tier, else
the dearest style) and how many of each tier.

Table wing_board (SCHEMA_VERSION 91): one row per save owning a wing, written in the save's own transaction by every
jr_pet_* command (game/pets.py command_commit: the wing commands, ⚡ Cường hóa nhanh included, and any other pet command
heals a row an older build left behind); an upsert that changes nothing writes nothing. Players who owned wings before
it: scripts/backfill_wing_board.py (by primary key, from wing_worn). Names follow the boards' privacy
(game/leaderboard.py _VISIBLE). Its weekly titles (top 1 / 2–3 / 4–10, game/lb_titles.py BOARD_TITLES['wings']) are taken
once a day like the other boards, from the same standings.

Reading: one indexed read of the top rows per process every CACHE_SECONDS; the viewer's own row read live.
"""
from __future__ import annotations

import json
import threading
import time

BOARD = 'wings'
POINTS = (1, 3, 9, 27, 81, 243, 729, 2187)   # 3^tier: D C B A S SS SSS Huyền thoại (game/wings_content.py TIERS)
CACHE_SECONDS = 30.0
TOP_READ = 50                                 # rows read for the board (its LIMIT is at most game/leaderboard.py LIMIT)

_SELECT = ('SELECT b.sid, b.pts, b.best, b.k, b.n, b.at, a.display, p.name AS gname, a.uid IS NOT NULL AS acct '
           'FROM wing_board b LEFT JOIN accounts a ON a.sid=b.sid LEFT JOIN leaderboard_players p ON p.sid=b.sid ')
_ORDER = 'ORDER BY b.pts DESC, b.best DESC, b.at, b.sid'


# ---------------------------------------------------------------- the score of a save
def score(s: dict) -> dict | None:
    """{pts, best, k, n} of the wings a save owns (n: how many of each tier, D first), or None without a wing."""
    from . import wings as W
    from .wings_content import INDEX
    w = W.get(s)
    own = w.get('own') if w else None
    if not isinstance(own, list):
        return None
    n = [0] * len(POINTS)
    best = None
    for x in own:
        r = x.get('r') if isinstance(x, dict) else None
        if type(r) is not int or not 0 <= r < len(POINTS) or not isinstance(x.get('k'), str):
            continue
        n[r] += 1
        key = (r, x.get('id') == w.get('on'), (INDEX.get(x['k']) or {}).get('price', 0), -int(str(x.get('id', 'w0'))[1:] or 0))
        if best is None or key > best[0]:
            best = (key, x)
    if best is None:
        return None
    return dict(pts=sum(POINTS[r] * c for r, c in enumerate(n)), best=best[1]['r'], k=best[1]['k'], n=n)


def reached(s: dict) -> float:
    """When the wings last went up (the newest `z`): the `at` of a row written from an old save (the backfill)."""
    from . import wings as W
    w = W.get(s)
    return float(max((x['z'] for x in (w or {}).get('own', ()) if isinstance(x, dict) and type(x.get('z')) is int), default=0))


_UPSERT = ('INSERT INTO wing_board(sid, pts, best, k, n, at) VALUES(?,?,?,?,?,?) ON CONFLICT (sid) DO UPDATE SET '
           'at=CASE WHEN wing_board.pts<>EXCLUDED.pts THEN EXCLUDED.at ELSE wing_board.at END, '
           'pts=EXCLUDED.pts, best=EXCLUDED.best, k=EXCLUDED.k, n=EXCLUDED.n '
           'WHERE (wing_board.pts, wing_board.best, wing_board.k, wing_board.n) IS DISTINCT FROM '
           '(EXCLUDED.pts, EXCLUDED.best, EXCLUDED.k, EXCLUDED.n)')


def write(db, sid: str, s: dict, at: float) -> bool:
    """Sync this save's row (inside the caller's transaction). True when it has one."""
    row = score(s)
    if row is None:
        db.execute('DELETE FROM wing_board WHERE sid=?', (sid,))
        return False
    db.execute(_UPSERT, (sid, row['pts'], row['best'], row['k'], json.dumps(row['n'], separators=(',', ':')), at))
    return True


def commit(db, sid: str, after: dict, wing_command: bool) -> None:
    """A jr_pet_* command, in the save's transaction (game/pets.py command_commit). A save that never had a wing writes
    nothing; else one upsert that writes only when a number moved (or one delete when the last wing went)."""
    from . import wings as W
    if not wing_command and W.get(after) is None:
        return
    from . import pets
    write(db, sid, after, pets.now())


def forget(db, sid: str) -> None:
    db.execute('DELETE FROM wing_board WHERE sid=?', (sid,))


# ---------------------------------------------------------------- reading
def _ranked(db, n: int) -> list:
    from .leaderboard import _VISIBLE
    return db.execute(_SELECT + f'WHERE {_VISIBLE} {_ORDER} LIMIT ?', (n,)).fetchall()


def standings(db, n: int) -> list:
    """[(board, rank, sid, points)] of the top `n` now (game/lb_titles.py)."""
    return [(BOARD, i + 1, r['sid'], int(r['pts'])) for i, r in enumerate(_ranked(db, n))]


def _counts(raw) -> list:
    try:
        n = json.loads(raw or '[]')
    except (TypeError, ValueError):
        n = []
    n = [v if type(v) is int and v > 0 else 0 for v in n][:len(POINTS)] if isinstance(n, list) else []
    return n + [0] * (len(POINTS) - len(n))


def _wing(r) -> dict:
    """The wing part of a row: the best wing {k, r} and the counts per tier."""
    return dict(wg=dict(k=str(r['k'] or ''), r=int(r['best'] or 0)), n=_counts(r['n']))


_cache: dict = {}
_lock = threading.Lock()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _board(store) -> tuple[list, int]:
    """([(sid, points, public row)], visible total), cached CACHE_SECONDS per process."""
    key = id(store)
    mono = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and mono - hit[0] < CACHE_SECONDS:
            return hit[1], hit[2]
    from .leaderboard import _VISIBLE
    with store.connect() as db:
        rows = _ranked(db, TOP_READ)
        total = int(db.execute('SELECT COUNT(*) FROM wing_board b LEFT JOIN accounts a ON a.sid=b.sid '
                               f'LEFT JOIN leaderboard_players p ON p.sid=b.sid WHERE {_VISIBLE}').fetchone()[0])
    out = []
    for r in rows:
        guest = not r['acct']
        out.append((r['sid'], int(r['pts']), dict(name=r['gname'] if guest else r['display'], guest=guest, score=int(r['pts']), **_wing(r))))
    with _lock:
        if len(_cache) > 8:
            _cache.clear()
        _cache[key] = (mono, out, total)
    return out, total


def view(store, limit: int, token: str | None = None) -> dict:
    """GET /api/leaderboard?board=wings: like game/leaderboard.py view(): the top `limit`, the viewer's own place
    (also when hidden) and the weekly titles."""
    from . import lb_titles as lbt
    from .leaderboard import _privacy, _viewer, _VISIBLE
    lbt.ensure(store)
    board, total = _board(store)
    sid = _viewer(store, token)
    holders = lbt.holders(store)
    from . import exclusive
    ex = exclusive.holders(store)   # 🌧️ an exclusive honour beside the name (game/exclusive.py)
    rows = []
    for i, (row_sid, _, r) in enumerate(board[:limit]):
        row = dict(r, rank=i + 1, me=row_sid == sid)
        mine = [h for h in holders.get(row_sid, ()) if h['board'] == BOARD]
        if mine:
            row['title'] = dict(emoji=mine[0]['emoji'], name=mine[0]['name'])
        exclusive.mark(row, row_sid, ex)
        rows.append(row)
    me = None
    if sid:
        with store.connect() as db:
            me = _privacy(db, sid)
            own = db.execute(_SELECT + 'WHERE b.sid=?', (sid,)).fetchone()
            if own:
                ahead = db.execute('SELECT COUNT(*) FROM wing_board b LEFT JOIN accounts a ON a.sid=b.sid '
                                   f'LEFT JOIN leaderboard_players p ON p.sid=b.sid WHERE {_VISIBLE} AND b.sid<>? '
                                   'AND (b.pts>? OR b.pts=? AND (b.best>? OR b.best=? AND (b.at<? OR b.at=? AND b.sid<?)))',
                                   (sid, own['pts'], own['pts'], own['best'], own['best'], own['at'], own['at'], sid)).fetchone()[0]
                me.update(score=int(own['pts']), rank=1 + int(ahead), **_wing(own))
            else:
                me['rank'] = None
        me.pop('show', None)
        me['titles'] = [dict(emoji=h['emoji'], name=h['name'], board=h['board'], label=h['label']) for h in holders.get(sid, ())]
    try:
        weekly = lbt.board_view(store, BOARD, sid)
    except Exception:  # noqa: BLE001 - the board still shows without its weekly block
        weekly = None
    return dict(board=BOARD, total=total, rows=rows, me=me, weekly=weekly)
