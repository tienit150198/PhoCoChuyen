"""⏰ Giờ vàng (owner 15/10): "mỗi ngày 10p hoặc 1h ngẫu nhiên là khung giờ vàng, hoặc theo ngày ấy, tại thời điểm đó
lãi tăng cao hơn".

* Each VN calendar day is drawn once from its date (nothing is stored; every worker and test computes the same):
  about one day in seven is a Ngày vàng (the whole day ×1.5); every other day has one Giờ vàng window of 10, 30 or 60
  minutes, starting between 07:00 and 23:00 on a 5-minute mark (×2).
* What it multiplies: the profit of shops and counters, at the moment the sale happens (an order's own time), so a
  staff order finished while the owner was away inside the window counts too, and polling cannot move it:
  - staff orders (game/staff_market.py x(): the margin after shaping, like the market and the hot career);
  - counter sales (game/quay_business.py sale(): the owner's take, margin + profit bonus, ×mult).
  A loss is never multiplied (both paths only scale a positive margin).
* ⚔️ A bang's own Giờ vàng (game/bang.py, set by its leader) is ×2 too: where both are on, the larger applies, never both.
* MNL_GOLDEN_OFF=1 turns it off (tests/__init__.py sets it, so a test's money does not depend on the hour it runs).
"""
from __future__ import annotations

import datetime
import functools
import os
import random
import time

VN = datetime.timezone(datetime.timedelta(hours=7))
DAY_ODDS = 7                        # one day in DAY_ODDS (on average) is a Ngày vàng
DAY_MULT, HOUR_MULT = 150, 200      # hundredths
LENGTHS = ((10, 40), (30, 35), (60, 25))   # minutes, weight
OPEN, CLOSE = 7 * 60, 23 * 60       # the window starts and ends inside 07:00–23:00, VN time
SALT = 'golden-hour-1'


def off() -> bool:
    return os.environ.get('MNL_GOLDEN_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')


def _midnight(day: datetime.date) -> float:
    return datetime.datetime(day.year, day.month, day.day, tzinfo=VN).timestamp()


def plan(day: datetime.date) -> dict:
    """The day's draw: {kind: 'day'|'hour', start, end (epoch seconds), mult (hundredths), minutes}."""
    return dict(_plan(day))


@functools.lru_cache(maxsize=16)
def _plan(day: datetime.date) -> dict:
    """plan(), drawn once per date and process (a pure function of the date): a settlement asks it for every
    staff order. Read only: plan() hands out copies."""
    rng = random.Random(f'{SALT}:{day.isoformat()}')
    base = _midnight(day)
    if rng.randrange(DAY_ODDS) == 0:
        return dict(kind='day', start=base, end=base + 86400, mult=DAY_MULT, minutes=24 * 60)
    minutes = rng.choices([m for m, _ in LENGTHS], weights=[w for _, w in LENGTHS])[0]
    start = OPEN + 5 * rng.randrange((CLOSE - minutes - OPEN) // 5 + 1)
    return dict(kind='hour', start=base + start * 60, end=base + (start + minutes) * 60, mult=HOUR_MULT, minutes=minutes)


def _day(t: float) -> datetime.date:
    return datetime.datetime.fromtimestamp(t, VN).date()


def mult(t: float | None = None) -> int:
    """The profit multiplier at time t, in hundredths (100 outside a window or when switched off)."""
    if off():
        return 100
    t = time.time() if t is None else t
    p = _plan(_day(t))
    return p['mult'] if p['start'] <= t < p['end'] else 100


def scale_take(percent: int, t: float, other: int = 100) -> int:
    """A profit-bonus percent such that the owner's take (margin × (100 + percent)) is ×mult(t) inside a window.
    `other`: another window's multiplier at t (⚔️ the bang's Giờ vàng, game/bang.py): the larger of the two applies."""
    g = max(mult(t), other)
    return percent if g == 100 else (100 + percent) * g // 100 - 100


def public(t: float | None = None) -> dict | None:
    """The page's line while a window is on: {kind, mult, ends, minutes}; None otherwise (it is a surprise until then)."""
    if off():
        return None
    t = time.time() if t is None else t
    p = _plan(_day(t))
    if not p['start'] <= t < p['end']:
        return None
    return dict(kind=p['kind'], mult=p['mult'], ends=p['end'], minutes=p['minutes'])


def news_line(t: float | None = None) -> str | None:
    """The town ticker's line while a window is on."""
    g = public(t)
    if not g:
        return None
    x = f"×{g['mult'] // 100}" if g['mult'] % 100 == 0 else f"×{g['mult'] / 100:.1f}".replace('.', ',')
    if g['kind'] == 'day':
        return f'🌟 Hôm nay là Ngày vàng: lãi tiệm và quầy {x} cả ngày!'
    return f"⏰ Giờ vàng đang diễn ra: lãi tiệm và quầy {x} trong {g['minutes']} phút!"
