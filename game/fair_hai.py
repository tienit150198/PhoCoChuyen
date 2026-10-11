"""👴 Ông Hai's table and the police (owner 09/10: "ông Hai tăng lên để k cho người dùng thắng nữa, hạn chế cho người ta
thắng đi nhé. nếu thắng nhiều thì cho công an bắt thu tiền là được"). Ông Hai himself is game/fair_oaq.py; the
commands are in game/fair.py. Nothing here reaches the client before it happens (no count, no threshold shown).

* Games: no limit (owner 11/10; HAI_DAY is only the legacy day counter's name).
* Wins keep their prize. The DEVICE_WINS + 1-th win (count_win, journey[WINS_KEY]) brings the police: "thiết bị hỗ
  trợ", DEVICE_PCT % of the wallet and the bank (device_fine) and the jail, while police enforcement is on. Legacy streak/window records remain readable; legacy collection uses the same small ceiling
  and does not stack another arrest fine. Bank accounts and savings never fund these fines.

Save: journey['fair_hai'] {d: the Vietnam date of `n`, n: games started with him that day, s: wins in a row,
w: [[epoch s, xu], ...] his wins not taken yet, within WINDOW} (optional: an older server keeps the journey's unknown
blocks as they are and never reads it; absent = nothing counted yet).
"""
from __future__ import annotations
from .loss_limits import bounded_loss

KEY = 'fair_hai'
HAI_DAY = 30             # legacy: games a day were capped here until 11/10 (owner: "không giới hạn số ván"); a counter only
# Owner 11/10 (later): "ô ăn quan nếu thắng trên 50 ván thì bị bắt vì sử dụng thiết bị hỗ trợ, và phạt 50% ví (tổng
# tiền, có trừ cả ví ngân hàng)". Wins against him are counted in journey[WINS_KEY] {n} (optional: an older server keeps
# the journey's unknown blocks); the DEVICE_WINS + 1-th brings the police, then the count starts again.
WINS_KEY = 'fair_hai_w'
DEVICE_WINS = 50
DEVICE_PCT = 50
STREAK = 2               # wins in a row that bring the police
WINDOW, WINDOW_WINS = 86400, 3   # ... or this many wins within a day (24 h)
W_MAX = 10               # the save's bound on w (a raid clears it at WINDOW_WINS)
TIRED = 'Hôm nay Ông Hai đánh nhiều ván quá, ông mệt rồi. Mai cháu ghé nha!'
SEIZE_LABEL = '🚨 Công an kiểm tra bàn Ông Hai · Nộp phạt'
# Owner 10/10: "nếu chơi thắng ông Hai thì bị bắt và phạt vì tội sử dụng thiết bị thứ 3, bỏ tù luôn và phạt 30 - 50% tiền;
# còn ai thắng vẫn thắng bình thường". The nominal percentage is now bounded by loss_limits;
# the prize and the existing trại tạm giữ (fair_bm.JAIL_DAYS) remain.
FINE_LO, FINE_HI = 30, 50
FINE_LABEL = '🚨 Công an phạt: dùng thiết bị hỗ trợ khi chơi với Ông Hai'
SAY_DEVICE = 'Thắng Ông Hai nhiều cỡ này thì chỉ có máy giúp thôi! Dùng thiết bị hỗ trợ là gian lận, nộp phạt rồi về đồn!'
SAY = 'Thắng Ông Hai liền mấy ván rồi nha. Nộp phạt nhẹ rồi về đồn làm việc!'


def _of(j: dict) -> dict:
    h = j.get(KEY)
    if not isinstance(h, dict):
        h = j[KEY] = dict(d='', n=0, s=0, w=[])
    return h


def can_start(j: dict, today: str) -> bool:
    """A new game with Ông Hai: always (owner 11/10, no limit on games)."""
    return True


def count_win(j: dict) -> bool:
    """A won game against him: True when it is past DEVICE_WINS (the police come; the count starts again)."""
    w = j.get(WINS_KEY)
    n = (w['n'] if isinstance(w, dict) and type(w.get('n')) is int else 0) + 1
    caught = n > DEVICE_WINS
    j[WINS_KEY] = dict(n=0 if caught else n)
    return caught


def started(j: dict, today: str) -> None:
    h = _of(j)
    if h['d'] != today:
        h['d'], h['n'] = today, 0
    h['n'] = min(10**6, h['n'] + 1)


def lost(j: dict) -> None:
    """A game with him lost, drawn or given up: the run of wins is broken (the day's wins stay counted)."""
    h = j.get(KEY)
    if isinstance(h, dict):
        h['s'] = 0


def won(j: dict, t: float, xu: int) -> int:
    """A won game paying `xu`: the xu the police take back now (0: none). A raid clears the run."""
    h = _of(j)
    now = int(t)
    h['w'] = [w for w in h['w'] if 0 <= now - w[0] < WINDOW][-(W_MAX - 1):] + [[now, max(0, int(xu))]]
    h['s'] = min(10**6, h['s'] + 1)
    if h['s'] < STREAK and len(h['w']) < WINDOW_WINS:
        return 0
    due = sum(x for _, x in h['w'])
    h['s'], h['w'] = 0, []
    return due


def device_fine(s: dict, j: dict, f: dict, pct: int = DEVICE_PCT) -> int:
    """The prize stays; pct % of the wallet and the bank together (fair_bm.total_money), taken from both, no ceiling."""
    from . import fair_bm as bm
    return bm.take_total(j, f, bm.total_money(j) * pct // 100, FINE_LABEL)


def seize(s: dict, j: dict, f: dict, due: int, label: str = SEIZE_LABEL) -> int:
    """Legacy collection: one bounded wallet-only loss, recorded at its actual amount."""
    from . import fair_bm as bm
    return bm._take(j, f, bounded_loss(j['wallet'], due, fine=True), label)


def validate(j: dict) -> None:
    if WINS_KEY in j:
        from .engine import need, integer
        w = j[WINS_KEY]
        need(isinstance(w, dict) and set(w) == {'n'}, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
        integer(w['n'], 0, DEVICE_WINS)
    if KEY not in j:
        return
    from .engine import need, integer
    bad = 'Dữ liệu chợ đen không hợp lệ.'
    h = j[KEY]
    need(isinstance(h, dict) and set(h) == {'d', 'n', 's', 'w'} and isinstance(h['d'], str) and len(h['d']) <= 10
         and isinstance(h['w'], list) and len(h['w']) <= W_MAX, bad, 'invalid_save')
    integer(h['n'], 0, 10**6)
    integer(h['s'], 0, 10**6)
    for w in h['w']:
        need(isinstance(w, list) and len(w) == 2, bad, 'invalid_save')
        integer(w[0], 0, 10**11)
        integer(w[1], 0, 10**7)
