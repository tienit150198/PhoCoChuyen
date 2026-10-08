"""🏆 Bảng vàng hội chợ: the fair's leaderboard and its titles after the end (owner 02/10: "event hội chợ mà top thì
nhận danh hiệu vua trò chơi nhé").

* The board: the xu won at the fair this edition (game/fair.py money_of; owner 03/10: "tiền thắng nhiều xếp top",
  before that participation points) on the existing leaderboard table, board `fair.board()` ('fair20261009xu'; only
  players ahead). Its rows come with the save like every board (game/leaderboard.py summary,
  written in the save's own transaction), so the top 20 is one indexed range of `leaderboard_rank`, never a scan
  of the saves; the same privacy rules (accounts under their display name unless hidden, guests only when they
  opted in and named their character). Ties: who reached the score first (`since`).
* The titles: once the fair has closed (+GRACE), `settle()` takes the board as it is shown (TOP visible players) and
  grants 👑 Vua trò chơi to the first and 🎪 Cao thủ hội chợ to the next nine, as `live_effects` rows of kind
  'title' (game/live_effects.py pays them into the save on the player's next load, once, like the wedding titles:
  the row id `<edition>:<title>:<sid>` is the idempotency key). Kept for good, worn next to the name like any title.
  Exactly once: the first process past the end claims leaderboard_meta 'fair:<edition>' (insert-if-absent, in the
  same transaction as the grants) and stores the winners there for the board's view; every other call is a no-op
  (a memo per process: no database read after that). Called from the server's housekeeping loop and, best effort,
  from /api/bootstrap and GET /api/leaderboard of the fair board.

No new table, no schema change: leaderboard, leaderboard_meta and live_effects exist in PostgreSQL.
"""
from __future__ import annotations

import json
import threading
import time

from . import fair as fh

META = 'fair:'                  # leaderboard_meta key: 'fair:<edition>' -> JSON [{rank, sid, score, title}]
GRACE = 60                      # seconds after the close before the standings are final
TOP = 10                        # 1 king + 9 masters
LIMIT = 20                      # rows the fair's board shows
TIERS = (dict(label='Top 1', lo=1, hi=1, title='f_king'), dict(label='Top 2–10', lo=2, hi=TOP, title='f_master'))

_done: set = set()
_lock = threading.Lock()


def now() -> float:
    return time.time()


def _key(store) -> str:
    return str(getattr(store, 'path', None) or id(store))


def title_for(rank: int) -> str | None:
    return next((tr['title'] for tr in TIERS if tr['lo'] <= rank <= tr['hi']), None)


def standings(db, board: str, n: int = TOP) -> list:
    """[(rank, sid, score)] of the board as shown (visible players, the board's order)."""
    from . import leaderboard as lb
    rows = db.execute(f"SELECT l.sid,l.score {lb._FROM} WHERE l.board=? AND {lb._VISIBLE} {lb._ORDER} LIMIT ?", (board, n)).fetchall()
    return [(i + 1, r['sid'], int(r['score'])) for i, r in enumerate(rows)]


def settle(store, t: float | None = None, best_effort_ms: int | None = None) -> list | None:
    """Once the fair is over: grant its titles. Returns the winners when this call did it, else None. Cheap before
    the end (a clock read) and after it is done (a memo). An earlier edition (fair.past(): a server that was not
    running at its end) is settled first, the same way, at most once too."""
    t = now() if t is None else t
    for ed, board, closes in fh.past():
        _settle(store, ed, board, closes, t, best_effort_ms)
    return _settle(store, fh.edition(), fh.board(), fh.window()[1], t, best_effort_ms)


def _settle(store, ed: str, board: str, closes: int, t: float, best_effort_ms: int | None) -> list | None:
    from .wedding_live import grant
    memo = (_key(store), ed)
    if t < closes + GRACE or memo in _done:
        return None
    with _lock:
        if memo in _done:
            return None

        def step(db):
            if db.execute('SELECT 1 FROM leaderboard_meta WHERE k=?', (META + ed,)).fetchone():
                return False
            if db.execute('INSERT INTO leaderboard_meta(k,v) VALUES(?,?) ON CONFLICT(k) DO NOTHING', (META + ed, '[]')).rowcount != 1:
                return False
            winners = []
            for rank, sid, score in standings(db, board):
                tid = title_for(rank)
                grant(db, sid, 'title', 1, f'{ed}:{tid}:{sid}', dict(title=tid, src='fair'))
                winners.append(dict(rank=rank, sid=sid, score=score, title=tid))
            db.execute('UPDATE leaderboard_meta SET v=? WHERE k=?', (json.dumps(winners, separators=(',', ':')), META + ed))
            return winners
        did = store.transaction(step, best_effort_ms)
        if did is None:     # busy (best effort): a later call does it
            return None
        _done.add(memo)
        return did or None


def run_settle(store) -> None:
    """Housekeeping (server.py): never raises."""
    import sys
    try:
        got = settle(store)
        if got is not None:
            sys.stderr.write(f'[fair] {fh.edition()}: titles granted to {len(got)} players\n')
    except Exception as e:  # noqa: BLE001 - housekeeping must never take the server down
        sys.stderr.write(f'[fair] settle: {type(e).__name__}\n')


def ensure(store) -> None:
    """Request path: settle if due and nobody did it yet (waits at most 250 ms for the write lock). Never raises."""
    try:
        settle(store, best_effort_ms=250)
    except Exception:  # noqa: BLE001 - a page never fails because of the fair
        pass


def winners(store) -> list:
    """[{rank, sid, score, title}] once settled, else []."""
    with store.connect() as db:
        row = db.execute('SELECT v FROM leaderboard_meta WHERE k=?', (META + fh.edition(),)).fetchone()
    if not row:
        return []
    try:
        got = json.loads(row[0])
    except (TypeError, ValueError):
        return []
    return got if isinstance(got, list) else []


def board_view(store, viewer: str | None) -> dict:
    """The fair block of GET /api/leaderboard?board=<edition>: the titles at stake, the dates, and the winners
    once settled (names as the board shows them now)."""
    from . import lb_titles as lbt
    from .journey import TITLE_INDEX
    opens, closes = fh.window()
    tiers = [dict(label=tr['label'], lo=tr['lo'], hi=tr['hi'], emoji=TITLE_INDEX[tr['title']]['emoji'],
                  name=TITLE_INDEX[tr['title']]['name']) for tr in TIERS]
    won = winners(store)
    out = []
    if won:
        sids = [w['sid'] for w in won]
        marks = ','.join('?' * len(sids))
        with store.connect() as db:
            rows = {r['sid']: r for r in db.execute(
                'SELECT s.sid AS sid,a.display,p.name AS gname,p.show,a.uid IS NOT NULL AS acct FROM sessions s '
                f'LEFT JOIN accounts a ON a.sid=s.sid LEFT JOIN leaderboard_players p ON p.sid=s.sid WHERE s.sid IN ({marks})', sids)}
        for w in won:
            r = rows.get(w['sid'])
            t = TITLE_INDEX.get(w.get('title'), {})
            out.append(dict(rank=w['rank'], score=w['score'], name=lbt._public(r, viewer) if r else 'Một người chơi',
                            me=w['sid'] == viewer, emoji=t.get('emoji', ''), title=t.get('name', '')))
    return dict(edition=fh.edition(), opens=opens, closes=closes, settled=bool(won) or _settled(store), tiers=tiers, winners=out)


def _settled(store) -> bool:
    with store.connect() as db:
        return bool(db.execute('SELECT 1 FROM leaderboard_meta WHERE k=?', (META + fh.edition(),)).fetchone())
