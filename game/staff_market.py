"""📈 Lãi nhân viên theo thị trường + 🔥 Nghề hot hôm nay (owner 09/10).

Owner: "lãi nghề thì xoay chuyển mỗi ngày 1 nghề lãi cao, còn lại bình thường", then "lãi các nghề nên khác nhau,
nhưng có sự biến đổi liên tục". Only staff orders (game/workplace_business.py đơn riêng) are touched; the player's own
sales, a visiting player's order and every price the player sets stay as they are.

* Each staffed career keeps its own margin, shaped once (shape()): margins up to KNEE xu an order stay as they are,
  a quarter of the part above it is kept, never more than CEIL. Until now a clothing staff order netted ~140 xu
  (the full shelf price of a 87 xu piece) against ~13 for an office or care job; now ~33 with the 40% bonus.
* A market multiplier per career drifts with real time (market()): a sum of three slow sines, phases from the
  career's name, sampled every SLOT seconds. 0.60–1.60, mean ≈ 1, never more than ~10% a step. Nothing is stored:
  every worker and every test computes the same value from (career, time).
* 🔥 One career a VN calendar day is hot (hot()): its multiplier is 2× the market's, held between 2.0 and 2.5. The
  careers come in a shuffled cycle (all of them before any repeats), never the same career two days running.
* MNL_MARKET_OFF=1 holds every multiplier at 1.00 and names no hot career (tests/__init__.py sets it, so a test's
  money does not depend on the hour it runs; tests/test_staff_market.py turns it on).
"""
from __future__ import annotations

import datetime
import functools
import math
import os
import random
import time
import zlib

VN = datetime.timezone(datetime.timedelta(hours=7))
SLOT = 1800                          # the market moves every 30 minutes
LOW, HIGH = 60, 160                  # ×0.60 … ×1.60 (in hundredths)
HOT_LOW, HOT_HIGH = 200, 250         # the hot career: 2× the market, held at ×2.0 … ×2.5
# (amplitude, period in slots): 2 days, ~32 h, ~20 h. Incommensurate, so a career's curve does not repeat for weeks.
WAVES = ((0.30, 96), (0.20, 61), (0.10, 37))
KNEE, CEIL = 16, 24                  # margin shaping, xu per order at a 4-star service
SERIES = 96                          # slots in the public curve: the last 48 h
# Day 0 of the hot rotation (VN). The rotation's cycles count from here.
EPOCH = datetime.date(2026, 10, 1).toordinal()


def now() -> float:
    return time.time()


def off() -> bool:
    return os.environ.get('MNL_MARKET_OFF') == '1'


def careers() -> list:
    """The careers with staff orders, in their catalogue order (new ones join at the end)."""
    from .workplace_business import ORDERS
    return list(ORDERS)


def _phase(career: str, i: int) -> float:
    return (zlib.crc32(f'market|{career}|{i}'.encode()) % 10000) / 10000 * 2 * math.pi


def market(career: str, t: float | None = None) -> int:
    """The career's market multiplier at time t, in hundredths (60…160)."""
    if off():
        return 100
    slot = int((now() if t is None else t) // SLOT)
    v = 1 + sum(a * math.sin(2 * math.pi * slot / p + _phase(career, i)) for i, (a, p) in enumerate(WAVES))
    return max(LOW, min(HIGH, round(v * 100)))


def _day(t: float) -> int:
    return datetime.datetime.fromtimestamp(t, VN).date().toordinal() - EPOCH


def _cycle(k: int, ids: list) -> list:
    order = list(ids)
    random.Random(f'hot-career|{k}|{len(ids)}').shuffle(order)
    return order


def hot_on(day: int) -> str | None:
    """The hot career of rotation day `day` (0 = EPOCH): a shuffled pass over every career, then the next pass.
    A pass that would open with the career that closed the previous one swaps its first two."""
    return _hot_on(day, tuple(careers()))


@functools.lru_cache(maxsize=64)
def _hot_on(day: int, ids: tuple) -> str | None:
    if not ids:
        return None
    n = len(ids)
    k, i = divmod(day, n)
    order = _cycle(k, ids)
    if n > 2 and order[0] == _cycle(k - 1, ids)[-1]:
        order[0], order[1] = order[1], order[0]
    return order[i]


def hot(t: float | None = None) -> str | None:
    if off():
        return None
    return hot_on(_day(now() if t is None else t))


def x(career: str, t: float | None = None) -> int:
    """The multiplier staff orders of this career earn at time t, in hundredths: the market, or the hot day's."""
    t = now() if t is None else t
    m = market(career, t)
    if career == hot(t):
        return max(HOT_LOW, min(HOT_HIGH, 2 * m))
    return m


def shape(margin: int, stars: int = 4) -> int:
    """A staff order's margin before the multiplier: as is up to KNEE, a quarter above it, at most CEIL (both scale
    with the service's stars like the price does, 4 stars = as written). A loss stays as it is."""
    if margin <= 0:
        return margin
    scale = 80 + 4 * stars
    knee, ceil = KNEE * scale // 96, CEIL * scale // 96
    return margin if margin <= knee else min(ceil, knee + (margin - knee) // 4)


def staff_revenue(price: int, stars: int, cash: int, goods: int, mult: int = 100) -> int:
    """What one staff order takes in: the shelf price at this service (as before), its margin shaped, then the market.
    `cash`: wage and supplies paid from the fund; `goods`: the stock's cost. A loss is never multiplied."""
    revenue = price * (80 + stars * 4) // 100
    margin = revenue - cash - goods
    if margin <= 0:
        return revenue
    return cash + goods + max(0, shape(margin, stars) * mult // 100)


def series(career: str, t: float | None = None, n: int = SERIES) -> list:
    """The last n slots' multipliers (oldest first, the current slot last): the page's sparkline and the away card."""
    t = now() if t is None else t
    start = (int(t // SLOT) - n + 1) * SLOT
    return [x(career, start + i * SLOT) for i in range(n)]


def public(t: float | None = None) -> dict:
    """public_state['market']: today's hot career and every staffed career's multiplier now (hundredths)."""
    t = now() if t is None else t
    h = hot(t)
    return dict(hot=h, x={c: x(c, t) for c in careers()}, slot=SLOT)


def view(career: str, t: float | None = None) -> dict:
    """The Sổ tiệm card's market line: now, the trend over the last 2 hours, the hot flag and the 48 h curve."""
    t = now() if t is None else t
    curve = series(career, t)
    return dict(x=curve[-1], was=curve[-5], hot=career == hot(t), curve=curve, slot=SLOT)
