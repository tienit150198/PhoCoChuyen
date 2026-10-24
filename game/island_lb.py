"""🏝️ Đảo đẹp nhất tuần on the main Bảng xếp hạng (owner 19/10: buildings on the islands, a weekly board, a TITLE only).

Each player's most beautiful island: game/island_build.py score() of the island_builds rows (status 'up') at the time
of reading — every standing level × its kind's points, plus points for each different kind; scaffolding counts nothing
yet. Names follow the boards' privacy (game/leaderboard.py _VISIBLE). Its weekly titles (top 1 / 2–3 / 4–10,
game/lb_titles.py BOARD_TITLES['island']) are taken once a day like the other boards, from the same standings, and
frozen on Monday: a title, never xu (no building and no board pays anything).

🏝️ 24/10 (Thiết kế đảo, game/island_design.py): an island's decorations and lấn biển add their points (island_layout.pts,
written with the save) to its buildings' — never taking any away: an island's points before 24/10 are what its
buildings give, the same as before. An island with decorations and no building is on the board too.

Nothing is stored here and the `leaderboard` table is not touched: one read of the 'up' rows (few: islands cost 30M+)
per process every CACHE_SECONDS.
"""
from __future__ import annotations

import threading
import time

BOARD = 'island'
CACHE_SECONDS = 30.0

_SELECT = ('SELECT b.owner AS sid, b.island, b.kind, b.lvl, b.next_lvl, b.ready_at, b.at, a.display, p.name AS gname, '
           'a.uid IS NOT NULL AS acct FROM island_builds b LEFT JOIN accounts a ON a.sid=b.owner '
           "LEFT JOIN leaderboard_players p ON p.sid=b.owner WHERE b.status='up'")
_LSELECT = ('SELECT l.owner AS sid, l.island, l.pts, l.at, a.display, p.name AS gname, a.uid IS NOT NULL AS acct '
            "FROM island_layout l LEFT JOIN accounts a ON a.sid=l.owner LEFT JOIN leaderboard_players p ON p.sid=l.owner "
            "WHERE l.status='up' AND l.pts>0")


def now() -> float:
    return time.time()


def _ranked(rows, t: float, lays=()) -> list:
    """[(sid, score, island, built, reached, row)] best island per player, best first (a tie: who got there first).
    `lays`: island_layout rows (🏝️ the decorations' and lấn biển's points, added to the buildings')."""
    from . import island_build as ib
    by: dict = {}
    for r in rows:
        if not ib.known(r['kind']):
            continue
        e = dict(k=r['kind'], l=int(r['lvl']), b=int(r['next_lvl']), t=float(r['ready_at']))
        by.setdefault((r['sid'], r['island']), dict(rows=[], row=r, extra=0, at=0.0))['rows'].append(e)
    for r in lays:
        x = by.setdefault((r['sid'], r['island']), dict(rows=[], row=r, extra=0, at=0.0))
        x['extra'], x['at'] = int(r['pts']), float(r['at'])
    best: dict = {}
    for (sid, iid), x in by.items():
        sc = ib.score(x['rows'], t) + x['extra']
        if sc <= 0:
            continue
        built = sum(1 for e in x['rows'] if ib.standing(e, t))
        reached = max([x['at'], *((e['t'] if e['b'] and e['t'] <= t else 0.0) for e in x['rows'])]) or float(x['row']['at'])
        cand = (sid, sc, iid, built, reached, x['row'])
        if sid not in best or (sc, -reached) > (best[sid][1], -best[sid][4]):
            best[sid] = cand
    return sorted(best.values(), key=lambda c: (-c[1], c[4], c[0]))


def _rows(db, visible: bool) -> list:
    from .leaderboard import _VISIBLE
    return db.execute(_SELECT + (f' AND {_VISIBLE}' if visible else '')).fetchall()


def _lays(db, visible: bool, sid: str | None = None) -> list:
    """🏝️ island_layout rows with points (game/island_design.py)."""
    from .leaderboard import _VISIBLE
    sql = _LSELECT + (f' AND {_VISIBLE}' if visible else '') + (' AND l.owner=?' if sid else '')
    return db.execute(sql, (sid,) if sid else ()).fetchall()


def standings(db, n: int, t: float | None = None) -> list:
    """[(board, rank, sid, score)] of the top `n` now (game/lb_titles.py)."""
    t = now() if t is None else t
    return [(BOARD, i + 1, c[0], c[1]) for i, c in enumerate(_ranked(_rows(db, True), t, _lays(db, True))[:n])]


_cache: dict = {}
_lock = threading.Lock()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _public_row(c) -> dict:
    from . import island as isl
    sid, sc, iid, built, _, r = c
    guest = not r['acct']
    it = isl.ISLAND.get(iid) or {}
    return dict(name=r['gname'] if guest else r['display'], guest=guest, score=sc, built=built,
                island=dict(id=iid, name=it.get('name', 'Đảo riêng'), emoji=it.get('emoji', '🏝️'), look=it.get('look', 'dua')))


def _board(store) -> list:
    key = id(store)
    mono = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and mono - hit[0] < CACHE_SECONDS:
            return hit[1]
    with store.connect() as db:
        ranked = _ranked(_rows(db, True), now(), _lays(db, True))
    out = [(c[0], c[1], _public_row(c)) for c in ranked]
    with _lock:
        if len(_cache) > 8:
            _cache.clear()
        _cache[key] = (mono, out)
    return out


def view(store, limit: int, token: str | None = None) -> dict:
    """GET /api/leaderboard?board=island: like game/leaderboard.py view(): the top `limit`, the viewer's own place (also
    when hidden) and the weekly titles."""
    from . import lb_titles as lbt
    from .leaderboard import _privacy, _viewer
    lbt.ensure(store)
    board = _board(store)
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
            own = _ranked(db.execute(_SELECT + ' AND b.owner=?', (sid,)).fetchall(), now(), _lays(db, False, sid))
        if own:
            ahead = sum(1 for s_, sc, _ in board if s_ != sid and sc > own[0][1])
            me.update(score=own[0][1], rank=1 + ahead, **{k: v for k, v in _public_row(own[0]).items() if k in ('built', 'island')})
        else:
            me['rank'] = None
        me.pop('show', None)
        me['titles'] = [dict(emoji=h['emoji'], name=h['name'], board=h['board'], label=h['label']) for h in holders.get(sid, ())]
    try:
        weekly = lbt.board_view(store, BOARD, sid)
    except Exception:  # noqa: BLE001 - the board still shows without its weekly block
        weekly = None
    return dict(board=BOARD, total=len(board), rows=rows, me=me, weekly=weekly)
