"""🎲 Chợ đen: xóc đĩa's 3 s gap (owner 15/10: "Với chỗ xóc đĩa thì cho delay 3s mỗi lần mở nhé để tránh spam").

Owner 16/10 (the rebalance, game/fair.py luck_p): the 15/10 boosts are gone. The day's first round of chiếu trong /
lô tô / vé cào no longer draws 65%, and the 3–4 secret ~3-minute windows a day no longer draw 70%: rate() is always
None (kept for older callers). The saved key stays readable: journey[KEY]['d'] (the date the first round was used, an
older save or an older server's) is still validated and simply no longer read.

* Xóc đĩa: a new round XD_GAP_MS after the player's previous one at the earliest (journey[KEY]['xd'], ms). Always on.
"""
from __future__ import annotations

import datetime

KEY = 'fair_bm_day'            # journey[KEY] {d: 'YYYY-MM-DD' (legacy, 15/10), xd: ms of the last xóc đĩa}
XD_GAP_MS = 3000


def rate(j: dict, game: str, t: float, stake: int | None, big_from: int, net: int = 0) -> None:
    """The 15/10 boosted draw: gone since 16/10 (always None, nothing saved)."""
    return None


def xd_wait_ms(j: dict, t: float) -> int:
    """How long before this player's next xóc đĩa round may start (0: now). A clock gone back waits nothing."""
    r = j.get(KEY)
    last = r.get('xd') if isinstance(r, dict) else None
    if type(last) is not int:
        return 0
    gone = int(t * 1000) - last
    return XD_GAP_MS - gone if 0 <= gone < XD_GAP_MS else 0


def xd_mark(j: dict, t: float) -> None:
    r = j.get(KEY)
    if not isinstance(r, dict):
        r = j[KEY] = {}
    r['xd'] = int(t * 1000)


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
