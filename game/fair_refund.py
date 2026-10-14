"""💸 Chợ đen fines the operator paid back, counted back on the 🏆 Bảng vàng (Top lời).

A fine is a Chợ đen loss in the save (journey['fair'].stats.lost: game/fair_bm.py _take, take_total, game/fair_hai.py
_take_parked), so the Bảng vàng score (game/fair.py money_of) went down by it. When the operator refunds a wrong fine,
it does so with a 🎁 Quà từ Phố Có Chuyện (game/system_gift.py) whose id starts with PREFIX (11/10: the fines of 16:49–
17:26, "refund-cd-20261011-…", 8 players, 18,538,100 xu): the wallet got the money back, but the save still counts
the fine as lost, so the board showed those players up to 8.6M xu lower than they really won (owner 14/10: "cái xếp
hạng của chợ đen phần thắng đang hơi không đúng").

The save is never changed for this: the board's row (game/leaderboard.py summary, `fair_extra`) adds the refunds paid
into that save during this edition (status applied or seen, created since the edition opened), read from
`system_gifts`. One small indexed read per process every TTL seconds (the map holds a handful of rows, at most MAX),
never on a request that has it already. A refund still pending is not counted (its xu are not in the wallet yet).
The player's own strip (fair.public money) still reads the save alone.
"""
from __future__ import annotations

import threading
import time

PREFIX = 'refund-cd-'   # a system gift that pays back a Chợ đen fine (scripts/grant_gift.py --id refund-cd-<date>-…)
TTL = 300               # seconds a process keeps the map
MAX = 10_000            # rows read at most (bounded memory; there are 8)

_lock = threading.Lock()
_maps: dict = {}        # store key -> (loaded at, edition, {sid: xu})


def _key(store) -> str:
    return str(getattr(store, 'path', None) or id(store))


def load(db) -> dict:
    """{sid: xu} of the Chợ đen fine refunds paid into saves during this edition."""
    from . import fair as fh
    rows = db.execute("SELECT sid,SUM(coins) AS xu FROM system_gifts WHERE id LIKE ? AND status IN ('applied','seen') "
                      'AND created>=? GROUP BY sid LIMIT ?', (PREFIX + '%', fh.window()[0], MAX)).fetchall()
    return {r[0]: int(r[1]) for r in rows if r[1] and int(r[1]) > 0}


def of(store, sid: str | None, now: float | None = None) -> int:
    """The xu to add back to this save's Bảng vàng score (0: none, or no database to ask). Never raises."""
    if store is None or not sid:
        return 0
    from . import fair as fh
    t = time.monotonic() if now is None else now
    key, ed = _key(store), fh.edition()
    hit = _maps.get(key)
    if hit is None or hit[1] != ed or t - hit[0] >= TTL:
        try:
            with store.connect() as db:
                got = load(db)
        except Exception:  # noqa: BLE001 - a board row never fails a command; keep what we had
            got = hit[2] if hit is not None and hit[1] == ed else {}
        with _lock:
            if len(_maps) > 8:
                _maps.clear()
            _maps[key] = hit = (t, ed, got)
    return hit[2].get(sid, 0)


def sids(store) -> list:
    """The saves with a refund this edition (scripts/fair_board_recompute.py)."""
    with store.connect() as db:
        return sorted(load(db))


def clear_cache() -> None:
    with _lock:
        _maps.clear()
