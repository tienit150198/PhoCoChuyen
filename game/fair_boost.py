"""🎲 Chợ đen (owner 15/10): "tăng tỷ lệ thắng chợ đen lần đầu lên 65% đi, với lâu lâu mỗi ngày cho khoảng 3p (chia ra
1 ngày khoảng 3 - 4 lần) ngẫu nhiên là tỷ lệ thắng tăng cao nhé. Với chỗ xóc đĩa thì cho delay 3s mỗi lần mở nhé để
tránh spam." Server only: no rate, no window and nothing derived from them reaches the client (the players' notice
only says "Tăng tỷ lệ thắng chợ đen").

* Lần đầu: a player's first luck round of a Vietnam day (UTC+7) at a stall with a drawn rate (GAMES: chiếu trong /
  xóc đĩa, lô tô, vé cào; bầu cua's dice and đua chó's odds are honest and draw nothing) wins FIRST_P. Saved in
  journey[KEY]['d'] (the date it was used; optional: absent = not used yet).
* Giờ vàng (internal name only): WINDOWS_MIN..WINDOWS_MAX windows of WINDOW_S seconds a Vietnam day, the same for every
  player, drawn from the date and the server's secret (property_market._salt: the house-news calendar's salt, which a
  public server sets), so the client code cannot predict them. They are spread over OPEN_H..CLOSE_H (one in each equal
  slice of those hours), never overlapping. A luck round inside one wins WINDOW_P while the player's Chợ đen net today
  is at most NET_STOP (300,000 xu, the golden days' stop).
* Both only below fair.BIG_WIN_FROM (50,000 xu): a 50k+ round still draws at most fair.BIG_WIN_P. The fair's police,
  raids and fines are untouched (they run before the draw, as before).
* Xóc đĩa: a new round XD_GAP_MS after the player's previous one at the earliest (journey[KEY]['xd'], ms).

MNL_BM_BOOST_OFF=1 turns both boosts off (tests/__init__.py sets it, so the other fair tests' odds do not depend on
the hour they run; tests/test_bm_boost_1015.py turns it on). The xóc đĩa gap is always on.
"""
from __future__ import annotations

import datetime
import os
import random
from functools import lru_cache

VN = datetime.timezone(datetime.timedelta(hours=7))
FIRST_P = .65                  # server only; never include in public/status data
WINDOW_P = .70                 # server only; never include in public/status data
GAMES = ('xd', 'lt', 'xs')
KEY = 'fair_bm_day'            # journey[KEY] {d: 'YYYY-MM-DD' the first round was played, xd: ms of the last xóc đĩa}
WINDOW_S = 180
WINDOWS_MIN, WINDOWS_MAX = 3, 4
OPEN_H, CLOSE_H = 8, 24        # Vietnam hours the windows fall in
XD_GAP_MS = 3000
NET_STOP = 300_000             # a window boosts no one already this much up at Chợ đen today (as the golden days' stop)


def off() -> bool:
    return os.environ.get('MNL_BM_BOOST_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')


def _salt() -> str:
    from .property_market import _salt as salt   # the house-news calendar's server secret (read per call)
    return salt()


def vn_day(t: float) -> datetime.date:
    return datetime.datetime.fromtimestamp(t, VN).date()


@lru_cache(maxsize=64)
def _windows(day: str, salt: str) -> tuple[tuple[int, int], ...]:
    rng = random.Random(f'fair-bm-window-v1|{salt}|{day}')
    d = datetime.date.fromisoformat(day)
    base = int(datetime.datetime(d.year, d.month, d.day, tzinfo=VN).timestamp())
    n = rng.randint(WINDOWS_MIN, WINDOWS_MAX)
    lo, hi = OPEN_H * 3600, CLOSE_H * 3600
    size = (hi - lo) // n
    out = []
    for i in range(n):   # one window inside each slice: spread over the day, never overlapping
        start = base + lo + i * size + rng.randrange(size - WINDOW_S + 1)
        out.append((start, start + WINDOW_S))
    return tuple(out)


def windows(day: datetime.date) -> tuple[tuple[int, int], ...]:
    """The day's windows [(start, end) epoch seconds], ordered."""
    return _windows(day.isoformat(), _salt())


def in_window(t: float) -> bool:
    return any(a <= t < b for a, b in windows(vn_day(t)))


def _rec(j: dict) -> dict:
    r = j.get(KEY)
    if not isinstance(r, dict):
        r = j[KEY] = {}
    return r


def rate(j: dict, game: str, t: float, stake: int | None, big_from: int, net: int = 0) -> float | None:
    """The boosted draw of this luck round (None: no boost). The day's first round of GAMES is used up here, whatever
    its stake (a round of big_from xu or more is the day's first round too, at its capped rate). A window boosts only
    while today's Chợ đen net is at most NET_STOP."""
    if off() or game not in GAMES:
        return None
    r = _rec(j)
    today = vn_day(t).isoformat()
    first = r.get('d') != today
    if first:
        r['d'] = today
    if type(stake) is not int or stake >= big_from:
        return None
    if in_window(t) and net <= NET_STOP:
        return WINDOW_P
    return FIRST_P if first else None


def xd_wait_ms(j: dict, t: float) -> int:
    """How long before this player's next xóc đĩa round may start (0: now). A clock gone back waits nothing."""
    r = j.get(KEY)
    last = r.get('xd') if isinstance(r, dict) else None
    if type(last) is not int:
        return 0
    gone = int(t * 1000) - last
    return XD_GAP_MS - gone if 0 <= gone < XD_GAP_MS else 0


def xd_mark(j: dict, t: float) -> None:
    _rec(j)['xd'] = int(t * 1000)


def validate(j: dict) -> None:
    """journey[KEY] (optional: an older save has none, an older server keeps it as is)."""
    if KEY not in j:
        return
    from .engine import need, integer
    r = j[KEY]
    need(isinstance(r, dict) and set(r) <= {'d', 'xd'}, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
    if 'd' in r:
        need(isinstance(r['d'], str) and len(r['d']) == 10, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
        try:
            datetime.date.fromisoformat(r['d'])
        except ValueError:
            need(False, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
    if 'xd' in r:
        integer(r['xd'], 0, 10**14)
