"""Fictional shared property news on the real Vietnam calendar.

``quote(kind, day=None)`` returns value/rent multipliers in basis points
(10000 = neutral), plus optional public news. The date may be a date object
or ISO date string; omitted dates use the Vietnam clock, never a life day.
Historical dates through 2026-10-05 stay neutral. Reads cannot advance or
reroll an event, and there is no player state or real-world news input.

Each 28-day window may contain an event lasting 3–6 days, followed by 5–9
days of gradual recovery. Windows cannot overlap. A single window lookup
works even for distant dates; cached windows are immutable and bounded.

Housing keeps fixed purchase prices. To avoid immediate resale windfalls,
capture the acquisition multiplier for new purchases and normalize resale
as ``base_value * current_multiplier_bp // acquisition_multiplier_bp``.
Older homes can use 10000 as their acquisition multiplier. Rental demand
uses ``rent_bp`` directly, independently of the acquisition multiplier.
"""
from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from functools import lru_cache
import random
import time


VN = dt.timezone(dt.timedelta(hours=7))
START = dt.date(2026, 10, 6)
WINDOW = 28
NEUTRAL_BP = 10000
MIN_BP, MAX_BP = 5500, 16500

# (id, fictional headline, value change, rental-demand change), basis points.
# Stable IDs and order keep an already-observed calendar reproducible.
EVENTS = (
    ('haunted_rumor', 'Lời đồn nhà có ma trong game khiến người mua và khách thuê e ngại.', -4300, -4500),
    ('spiritual_rumor', 'Tin đồn tâm linh quanh khu nhà trong game làm khách xem nhà thưa vắng.', -3800, -4200),
    ('flooding', 'Mưa lớn làm ngập lối vào khu nhà trong game, nhu cầu mua và thuê giảm.', -3200, -3600),
    ('construction_noise', 'Công trình bên cạnh trong game gây bụi và tiếng ồn, khách thuê chuyển đi.', -1800, -2800),
    ('road_closure', 'Đường vào khu nhà trong game tạm đóng để sửa, việc đi lại bất tiện.', -2200, -2500),
    ('oversupply', 'Nhiều căn nhà trong game cùng rao bán và cho thuê, chủ nhà phải cạnh tranh.', -2400, -3000),
    ('development_plan', 'Khu nhà trong game được chọn cho dự án quy hoạch mới, nhu cầu tăng mạnh.', 5500, 4200),
    ('infrastructure', 'Tuyến đường và bến xe mới trong game giúp khu nhà kết nối thuận tiện.', 4800, 3500),
    ('school', 'Trường học mới mở gần khu nhà trong game, nhiều gia đình tìm chỗ ở.', 2800, 3800),
    ('tourism', 'Lễ hội du lịch trong game thu hút khách, khu nhà gần đó được săn đón.', 2400, 4500),
    ('park', 'Công viên mới trong game làm khu nhà thoáng đẹp, nhu cầu mua và thuê tăng.', 3400, 2500),
    ('new_jobs', 'Khu văn phòng trong game đón doanh nghiệp mới, người đi làm tìm nhà gần hơn.', 3100, 4000),
)


@dataclass(frozen=True)
class _Episode:
    start: int
    active_days: int
    recovery_days: int
    event: int


def now() -> float:
    return time.time()


def today() -> dt.date:
    """Current real date in Vietnam (UTC+7)."""
    return dt.datetime.fromtimestamp(now(), VN).date()


@lru_cache(maxsize=1024)
def _window(kind: str, block: int) -> _Episode | None:
    rng = random.Random(f'property-news-v1|{kind}|{block}')
    if rng.random() >= .7:
        return None
    return _Episode(block * WINDOW + rng.randint(2, 7), rng.randint(3, 6),
                    rng.randint(5, 9), rng.randrange(len(EVENTS)))


def quote(kind: str, day: dt.date | str | None = None) -> dict:
    """Return a fresh quote shared by all players for this kind and date.

    ``news`` is None on neutral days. Otherwise it has id, title,
    direction (up/down), active (True while effects remain), and phase
    (active/recovery). It never exposes an event's future end date.
    """
    if day is None:
        day = today()
    elif isinstance(day, str):
        day = dt.date.fromisoformat(day)
    if type(day) is not dt.date:
        raise TypeError('day must be a date or ISO date string')
    result = dict(multiplier_bp=NEUTRAL_BP, rent_bp=NEUTRAL_BP, news=None)
    offset = (day - START).days
    if offset < 0:
        return result
    event = _window(kind, offset // WINDOW)
    if event is None:
        return result
    elapsed = offset - event.start
    duration = event.active_days + event.recovery_days
    if not 0 <= elapsed < duration:
        return result
    key, title, value_delta, rent_delta = EVENTS[event.event]
    recovering = elapsed >= event.active_days
    # Keep full effect for several days, then approach neutral without
    # reversing direction or accumulating an unbounded price trend.
    denominator = event.recovery_days + 1 if recovering else 1
    numerator = duration - elapsed if recovering else 1
    for field, delta in (('multiplier_bp', value_delta), ('rent_bp', rent_delta)):
        magnitude = abs(delta) * numerator // denominator
        value = NEUTRAL_BP + (magnitude if delta > 0 else -magnitude)
        result[field] = max(MIN_BP, min(MAX_BP, value))
    result['news'] = dict(id=f'{kind}:{event.start}:{key}', title=title,
                          direction='up' if value_delta > 0 else 'down', active=True,
                          phase='recovery' if recovering else 'active')
    return result
