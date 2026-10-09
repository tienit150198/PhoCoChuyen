"""👴 Ông Hai's table and the police (owner 09/10: "ông Hai tăng lên để k cho người dùng thắng nữa, hạn chế cho người ta
thắng đi nhé. nếu thắng nhiều thì cho công an bắt thu tiền là được"). Ông Hai himself is game/fair_oaq.py; the
commands are in game/fair.py. Nothing here reaches the client before it happens (no count, no threshold shown).

* A day's games: HAI_DAY games with Ông Hai a Vietnam day at most; one more is refused (TIRED), nothing changes.
* Winning a lot: a won game that makes STREAK wins in a row at his table (no lost, drawn or given-up game with him in
  between), or WINDOW_WINS wins within WINDOW seconds, brings the police at once. They take back the xu of every win
  in that run (those still within WINDOW, never twice the same: a raid clears them), from the wallet first, then the
  bank account, never below zero (what neither holds is let go, no debt), then the Chợ đen arrest (fair_bm.arrest:
  the fine, fair_bm.FINE_PCT of the wallet left, and the trại tạm giữ). Only while the Chợ đen's police are on
  (fair_bm._gate_on). The 30% raid and the 10% asset check of the paid stalls are untouched (ô ăn quan is no paid round).

Save: journey['fair_hai'] {d: the Vietnam date of `n`, n: games started with him that day, s: wins in a row,
w: [[epoch s, xu], ...] his wins not taken yet, within WINDOW} (optional: an older server keeps the journey's unknown
blocks as they are and never reads it; absent = nothing counted yet).
"""
from __future__ import annotations

KEY = 'fair_hai'
HAI_DAY = 30             # games with Ông Hai a Vietnam day
STREAK = 2               # wins in a row that bring the police
WINDOW, WINDOW_WINS = 86400, 3   # ... or this many wins within a day (24 h)
W_MAX = 10               # the save's bound on w (a raid clears it at WINDOW_WINS)
TIRED = 'Hôm nay Ông Hai đánh nhiều ván quá, ông mệt rồi. Mai cháu ghé nha!'
SEIZE_LABEL = '🚨 Công an tịch thu tiền thắng Ông Hai'
SAY = 'Thắng Ông Hai liền mấy ván, tiền vô như nước hả? Bàn này là sòng bạc trá hình. Tiền thắng tịch thu, về đồn làm việc!'


def _of(j: dict) -> dict:
    h = j.get(KEY)
    if not isinstance(h, dict):
        h = j[KEY] = dict(d='', n=0, s=0, w=[])
    return h


def can_start(j: dict, today: str) -> bool:
    """A new game with Ông Hai today (read only)."""
    h = j.get(KEY)
    return not (isinstance(h, dict) and h.get('d') == today and h.get('n', 0) >= HAI_DAY)


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


def seize(s: dict, j: dict, f: dict, due: int) -> int:
    """Take `due` xu back: the wallet first, then the bank account, never below zero; a Chợ đen loss (the Bảng vàng
    counts it). Returns what was taken."""
    from . import bank as bk
    from . import fair_bm as bm
    cash = bm._take(j, f, due, SEIZE_LABEL)
    b = bk.get(s)
    bank = min(max(0, b['balance']), due - cash) if b and type(b.get('balance')) is int else 0
    if bank:
        b['balance'] -= bank
        bk._log(b, j['life_day'], 'acc', 'Công an tịch thu tiền thắng Ông Hai', -bank)
        f['net'] = max(-10**9, f['net'] - bank)
        f['stats']['lost'] = min(10**9, f['stats']['lost'] + bank)
    return cash + bank


def validate(j: dict) -> None:
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
