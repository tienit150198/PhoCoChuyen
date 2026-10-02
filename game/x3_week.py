"""🔥 Nghề x3 trong tuần.

Owner 03/10: "cho sự kiện tăng thu nhập x3 … kiểu mỗi ngày x3 cho 2 - 3 trò bất kì", "làm liên tiếp, đầu tuần thông báo
và tự áp dụng, mấy trò mà chia ra 1 tuần là đủ tất cả trò, k bắt buộc 2 hay 3 trò", "x3 đây là x3 công việc người ta
trải nghiệm ấy, k phải trò chơi".

* Every week (Monday to Sunday, VN time) the careers are shuffled (seeded by that Monday's date) and dealt over the 7
  days, so each career has exactly one day a week (35 careers: 5 a day).
* On a career's day, closing its shift (journey._end_of_day, story mode) pays a bonus of (X - 1) × the day's net (what
  the shift made after its costs, the day's salary included; never below 0, at most CAP) into the wallet as a
  'salary' row "🔥 Thưởng ngày x3 · …", so the day earns X times.
* MNL_X3_OFF=1 turns the bonus off (the tests set it; also a switch for the server).
* Nothing in the save: the week and the day come from the clock (now). public() goes out as public_state['x3']
  (not in the journey, whose size has a budget): the client shows today's careers, a chip on them, and pops the
  week's list once a week.
"""
from __future__ import annotations

import datetime
import os
import random
import time

from .content import CAREERS

VN = datetime.timezone(datetime.timedelta(hours=7))
X = 3
CAP = 3000          # the most one shift's bonus pays


def now() -> float:
    return time.time()


def _date(t: float) -> datetime.date:
    return datetime.datetime.fromtimestamp(t, VN).date()


def week(t: float | None = None) -> tuple[str, list]:
    """(this week's Monday 'YYYY-MM-DD', the careers of each day Monday..Sunday)."""
    t = now() if t is None else t
    d = _date(t)
    monday = d - datetime.timedelta(days=d.weekday())
    ids = list(CAREERS)
    random.Random(f'x3-week|{monday.isoformat()}').shuffle(ids)
    return monday.isoformat(), [sorted(ids[i::7], key=CAREERS.index) for i in range(7)]


def today(t: float | None = None) -> list:
    t = now() if t is None else t
    return week(t)[1][_date(t).weekday()]


def on(career: str, t: float | None = None) -> bool:
    return os.environ.get('MNL_X3_OFF') != '1' and career in today(t)


def bonus(net: int) -> int:
    """What a boosted shift adds on top of its day's net."""
    return min(CAP, (X - 1) * max(0, int(net)))


def public(t: float | None = None) -> dict:
    t = now() if t is None else t
    w, days = week(t)
    return dict(x=X, week=w, days=days, day=_date(t).weekday(), today=days[_date(t).weekday()])
