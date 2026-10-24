"""🦉 Cú đêm của phố: the weekly board of time online (owner 18/10: "thống kê thêm thời gian online nhiều và cho top
các bạn online nhiều nữa nhé, top 1 khung này, còn các top khác bạn tự thêm, top 10 tối đa nhé").

The time is the play time the database already keeps per save and Vietnam day (table stat_play, trigger
stat_play_cmd on receipts, game/pg_schema.py PLAY_GAP / PLAY_IDLE_TAIL): a command within 10 minutes of the previous
one counts the gap as played, so a tab left open with nobody playing does not climb the board. The week is Monday to
Sunday, Vietnam time (game/wedding_live.py), and starts again from zero.

What the board shows is SHOWN_OFF less than the real time (owner 18/10: "giảm thời gian thực tế xuống 1h nhé, kiểu
onl 5 tiếng thì hiển thị 4 tiếng thôi"); a player shows once that is at least SHOWN_MIN. The order is the same.
Below that, the viewer's own card (view() `me`) tells how much more play puts the name up (F#434), never a bare zero.
Names follow the boards' privacy (game/leaderboard.py _VISIBLE). Its weekly titles (top 1 / 2–3 / 4–10,
game/lb_titles.py BOARD_TITLES['online']) are taken once a day like the other boards; the Monday freeze uses the
totals of the week that ended (standings()).

Nothing is stored here: one grouped read of the week's stat_play rows (its primary key starts with the day) per
process every CACHE_SECONDS.
"""
from __future__ import annotations

import threading
import time

from .wedding_live import vn_day, week_start

ONLINE = 'online'
SHOWN_OFF = 3600          # seconds taken off what the board shows
SHOWN_MIN = 60            # shown seconds needed to be on the board
CACHE_SECONDS = 60.0


def week_days(t: float) -> tuple[str, str]:
    """The first and last Vietnam day ('YYYY-MM-DD') of the week of `t`."""
    ws = week_start(t)
    return vn_day(ws), vn_day(ws + 6 * 86400 + 3600)


def shown(secs) -> int:
    """The seconds the board shows for a real total."""
    return max(0, int(secs or 0) - SHOWN_OFF)


def _ranked(db, t: float) -> list:
    """Every player the board shows for the week of `t`, best first: rows of sid, secs (real), display, gname, acct."""
    from .leaderboard import _VISIBLE
    lo, hi = week_days(t)
    return db.execute(
        'WITH w AS (SELECT sid, SUM(secs) AS secs, MIN(first_at) AS first FROM stat_play WHERE day>=? AND day<=? '
        'GROUP BY sid HAVING SUM(secs)>=?) '
        'SELECT w.sid, w.secs, a.display, p.name AS gname, a.uid IS NOT NULL AS acct '
        'FROM w LEFT JOIN accounts a ON a.sid=w.sid LEFT JOIN leaderboard_players p ON p.sid=w.sid '
        f'WHERE {_VISIBLE} ORDER BY w.secs DESC, w.first, w.sid',
        (lo, hi, SHOWN_OFF + SHOWN_MIN)).fetchall()


def standings(db, t: float, n: int) -> list:
    """[(board, rank, sid, shown seconds)] of the top `n` of the week of `t` (game/lb_titles.py)."""
    return [(ONLINE, i + 1, r['sid'], shown(r['secs'])) for i, r in enumerate(_ranked(db, t)[:n])]


_cache: dict = {}
_lock = threading.Lock()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _board(store, t: float) -> list:
    """[(sid, real secs, public row)] of this week, cached CACHE_SECONDS per process."""
    key = (id(store), week_days(t)[0])
    mono = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and mono - hit[0] < CACHE_SECONDS:
            return hit[1]
    with store.connect() as db:
        rows = _ranked(db, t)
    out = []
    for r in rows:
        guest = not r['acct']
        out.append((r['sid'], int(r['secs']), dict(name=r['gname'] if guest else r['display'], guest=guest, score=shown(r['secs']))))
    with _lock:
        if len(_cache) > 8:
            _cache.clear()
        _cache[key] = (mono, out)
    return out


def view(store, limit: int, token: str | None = None, t: float | None = None) -> dict:
    """GET /api/leaderboard?board=online: like game/leaderboard.py view(): the top `limit`, the viewer's own place
    (also when hidden) and the weekly titles."""
    from . import lb_titles as lbt
    from .leaderboard import _privacy, _viewer
    t = time.time() if t is None else t
    lbt.ensure(store)
    board = _board(store, t)
    sid = _viewer(store, token)
    holders = lbt.holders(store)
    from . import exclusive
    ex = exclusive.holders(store)   # 🌧️ an exclusive honour beside the name (game/exclusive.py)
    rows = []
    for i, (row_sid, _, r) in enumerate(board[:limit]):
        row = dict(r, rank=i + 1, me=row_sid == sid)
        mine = [h for h in holders.get(row_sid, ()) if h['board'] == ONLINE]
        if mine:
            row['title'] = dict(emoji=mine[0]['emoji'], name=mine[0]['name'])
        exclusive.mark(row, row_sid, ex)
        rows.append(row)
    me = None
    if sid:
        lo, hi = week_days(t)
        with store.connect() as db:
            me = _privacy(db, sid)
            secs = int(db.execute('SELECT COALESCE(SUM(secs),0) FROM stat_play WHERE day>=? AND day<=? AND sid=?', (lo, hi, sid)).fetchone()[0])
        if secs >= SHOWN_OFF + SHOWN_MIN:
            me.update(score=shown(secs), rank=1 + sum(1 for s, v, _ in board if v > secs and s != sid))
        else:
            # F#434 (minnie, Monday 01:37–01:55): 18 minutes of a new week show nothing (shown = real − SHOWN_OFF), and the
            # card only said "not on the board yet", read as "my minutes are not counted". The card now says the time is
            # counted and how much more play puts the name up: `need` real seconds left, `counted` some time this week.
            me.update(rank=None, need=SHOWN_OFF + SHOWN_MIN - secs, counted=secs > 0)
        me.pop('show', None)
        me['titles'] = [dict(emoji=h['emoji'], name=h['name'], board=h['board'], label=h['label']) for h in holders.get(sid, ())]
    try:
        weekly = lbt.board_view(store, ONLINE, sid)
    except Exception:  # noqa: BLE001 - a database from before the weekly titles: the board still shows
        weekly = None
    return dict(board=ONLINE, total=len(board), rows=rows, me=me, weekly=weekly)
