"""Giờ trong ngày: one time-of-day view for every career.

Each career already keeps a shop clock of its own kind:

* most careers: `inventory.clock` (opening time + 20 minutes per ticking action, capped at closing);
* milk tea: the boba counter (`boba.clock_minutes`, overtime until 23:00);
* repair: its own 10-minute clock; delivery: the evening route clock (17:00 + minutes ridden);
* the three office careers: the office clock (08:00 → 17:30, overtime until 20:00).

This module reads them (never writes) and gives the client one shape: the time, the part of day
(Sáng / Trưa / Chiều / Tối / Đêm), the shift's opening and closing hours, how far into the shift we
are and the closing warnings. Nothing here is stored: a warning fires on the action whose clock step
crosses its threshold, and a clock only moves forward within a day, so each warning fires once a day.

Closing rule (the same for every career):
* at closing time no new customer is taken (`more_work` and walk-ins stop);
* the customers already inside are served to the end (làm nốt, no extra cost);
* closing the day (`end_day`) is always fine: unfinished work is kept and those customers come back
  when the shop opens tomorrow. Closing is not walking off: `abandon.py` never charges a proper close.
"""
from __future__ import annotations

from . import inventory as inv

DAY_MIN = inv.DAY_MIN
PREP = 30  # before opening: the morning prep shown while the shop is still closed

# (from minute, id, label, icon)
PARTS = (
    (0, 'dem', 'Đêm', '🌙'),
    (5 * 60, 'sang', 'Sáng', '🌤️'),
    (11 * 60, 'trua', 'Trưa', '☀️'),
    (13 * 60, 'chieu', 'Chiều', '🌇'),
    (18 * 60, 'toi', 'Tối', '🌙'),
    (22 * 60, 'dem', 'Đêm', '🌙'),
)
# Closing warnings: minutes left → level, toast ({left}: the time really left after this step).
WARNINGS = (
    (60, 'soon60', '⏰ Còn {left} là tới giờ đóng cửa.'),
    (30, 'soon30', '⏰ Sắp đóng cửa: còn {left}. Khách mới nên là khách cuối nhé.'),
    (0, 'closing', '🔔 Đến giờ đóng cửa. Không đón thêm khách: làm nốt việc dở rồi khép ca nhé.'),
)
CLOSING_TEXT = {
    'milk_tea': '🔔 Đến giờ đóng cửa. Ngày đông thì bán nốt khách đang đợi, muộn nhất 23:00, rồi khép ca nhé.',
}
OFFICE = ('corp_accounting', 'tax_payroll', 'group_accounting', 'hr_admin', 'secretary', 'it_helpdesk')
REPAIR_HOURS = (8 * 60, 19 * 60)
BOBA_HOURS = (8 * 60, 20 * 60)
BOBA_LATE = 23 * 60
OFFICE_HOURS = (8 * 60, 17 * 60 + 30)
OFFICE_LOCK = 20 * 60
DELIVERY_HOURS = inv.HOURS['delivery']
# Shifts with their own evening: a note under the hours in the status sheet.
NOTES = {
    'delivery': 'Ca tối: đơn đồ ăn dồn vào giờ cơm tối.',
    'garbage': 'Ca tối: mỗi ngõ có giờ đổ rác, tới muộn là rác bị bới tung.',
    'homemaker': 'Đi chợ từ sáng sớm, 8 giờ hết cá tươi; 11:30 cả nhà ăn trưa, 16:30 đón bé Su.',
    'ice_cream': 'Tiệm mở sau giờ cơm trưa; 16:30 trường tan học là đông nhất.',
    'com': 'Quán cơm mở từ sáng sớm; 11:30 dân văn phòng ra mua cơm hộp là đông nhất.',
    'nail': 'Trưa đông dân văn phòng tranh thủ giờ nghỉ; tối thứ sáu, cuối tuần kín lịch.',
    'pho': 'Quán mở từ 5:30 sáng; 6:30 người đi làm ghé đông nhất, gần trưa là vãn.',
    'pagoda': 'Bốn giờ sáng thỉnh chuông, 11:00 cúng ngọ; ngày rằm tối có lễ cầu an.',
    'photobooth': 'Tiệm mở từ trưa; 17:00 học sinh tan trường, tối cuối tuần chợ đêm đông nhất.',
    'giupviec': 'Lịch hẹn từ 7:00; khách đi làm để chìa khóa, chiều tối khách về đi kiểm nhà.',
    'homestay': 'Quầy lễ tân trực tới 22:00; khách tới muộn gọi chuông, sáng mai bàn giao.',
    'milk_tea': 'Ngày đông khách có thể bán quá giờ, muộn nhất 23:00.',
    'corp_accounting': 'Tăng ca được tới 20:00 nếu xin phép trưởng phòng.',
    'tax_payroll': 'Tăng ca được tới 20:00 nếu xin phép trưởng phòng.',
    'group_accounting': 'Tăng ca được tới 20:00 nếu xin phép trưởng phòng.',
    'hr_admin': 'Tăng ca được tới 20:00 nếu xin phép trưởng phòng.',
    'secretary': 'Tăng ca được tới 20:00 nếu xin phép giám đốc.',
    'it_helpdesk': 'Tăng ca được tới 20:00 nếu xin phép trưởng nhóm.',
}
# An extended evening on some days: career → (day-mode id, closing minute, note).
LATE_DAYS = {
    'tra_da': ('football', 22 * 60, '⚽ Tối nay có trận: quán bán tới 22:00.'),
}


def hm(minute: int) -> str:
    return inv.hm(minute)


def part(minute: int) -> dict:
    m = int(minute) % DAY_MIN
    row = PARTS[0]
    for r in PARTS:
        if m >= r[0]:
            row = r
    return dict(id=row[1], label=row[2], icon=row[3])


def left_text(minutes: int) -> str:
    minutes = max(0, int(minutes))
    if minutes <= 60:  # "Còn 60 phút", not "Còn 1 giờ" 
        return f'{minutes} phút'
    h, m = divmod(minutes, 60)
    return f'{h} giờ' + (f' {m} phút' if m else '')


# ---------------------------------------------------------------- hours
def _late_day(c: dict, career: str) -> tuple | None:
    row = LATE_DAYS.get(career)
    if not row:
        return None
    from .careers import PLUGINS
    mod = PLUGINS.get(career)
    try:
        today = mod.mod_of(c['day'])['id'] if mod and hasattr(mod, 'mod_of') else None
    except Exception:  # a day mode is optional; the plain hours stand
        today = None
    return row if today == row[0] else None


def late_close(c: dict, career: str) -> int | None:
    """Today's extended closing minute (e.g. tra_da on a football night), else None."""
    row = _late_day(c, career)
    return row[1] if row else None


def hours(c: dict, career: str) -> tuple[int, int]:
    """Opening and closing minute of today's shift."""
    if career == 'milk_tea':
        return BOBA_HOURS
    if career == 'repair':
        return REPAIR_HOURS
    if career in OFFICE:
        return OFFICE_HOURS
    return inv.day_hours(c, career)


def _office(c: dict) -> dict | None:
    o = ((c.get('ext') or {}).get('data') or {}).get('office')
    return o if isinstance(o, dict) else None


def _minute(c: dict, career: str) -> tuple[int, int]:
    """(time of day, latest minute the clock can reach) while the shift is open."""
    op, cl = hours(c, career)
    if career == 'milk_tea':
        from . import boba
        return boba.clock_minutes(c), BOBA_LATE
    if career == 'repair':
        from .careers import PLUGINS
        mod = PLUGINS.get('repair')
        return (mod._clock(c) if mod else op), cl
    if career == 'delivery':
        d = (c.get('ext') or {}).get('data') or {}
        ck = d.get('clock') if isinstance(d.get('clock'), int) else 0
        return op + max(0, ck), DAY_MIN - 1
    if career in OFFICE:
        o = _office(c)
        if not o:
            return op, cl
        clock = o.get('clock') if o.get('day') == c['day'] else op
        lock = OFFICE_LOCK if o.get('day') == c['day'] and o.get('ot') else cl
        return int(clock or op), lock
    from . import engine
    return engine._clock(c, career)['minute'], cl


def minute_now(c: dict, career: str) -> int | None:
    """Time of day while the shift is open (None when closed)."""
    if not c.get('open'):
        return None
    try:
        return int(_minute(c, career)[0])
    except Exception:  # a career clock never blocks play
        return None


def past_close(c: dict, career: str) -> bool:
    """The shift is open and its closing time has come (no new customers)."""
    m = minute_now(c, career)
    if m is None:
        return False
    op, cl = hours(c, career)
    if career in OFFICE:
        o = _office(c) or {}
        if o.get('day') == c['day'] and o.get('ot'):
            cl = OFFICE_LOCK
    if career == 'milk_tea':
        return False  # the counter has its own evening (quota, overtime to 23:00)
    return m >= cl


# ---------------------------------------------------------------- view
def _level(left: int) -> str:
    if left <= 0:
        return 'closing'
    if left <= 30:
        return 'soon30'
    if left <= 60:
        return 'soon60'
    return ''


def view(c: dict, career: str) -> dict:
    """The clock for the HUD, the status sheet and the scene's light."""
    op, cl = hours(c, career)
    late = _late_day(c, career)
    note = late[2] if late else NOTES.get(career, '')
    base = dict(open=op, close=cl, open_time=hm(op), close_time=hm(cl), hours=f'Mở {hm(op)} – Đóng {hm(cl)}', note=note,
                step=inv.STEP if career not in ('milk_tea', 'repair', 'delivery', *OFFICE) else (10 if career == 'repair' else None))
    if not c.get('open'):
        m = max(0, op - PREP)
        return dict(base, is_open=False, minute=m, time=hm(m), part=part(m), progress=0, left=cl - op, level='prep',
                    label=f'Chuẩn bị · mở cửa lúc {hm(op)}')
    m, limit = _minute(c, career)
    if career in OFFICE:
        o = _office(c) or {}
        if o.get('day') == c['day'] and o.get('ot'):
            cl = OFFICE_LOCK
            base.update(close=cl, close_time=hm(cl), hours=f'Mở {hm(op)} – Tăng ca tới {hm(cl)}')
    left = cl - m
    over = max(0, m - cl)
    level = _level(left)
    if over:
        label = f'Quá giờ đóng cửa {left_text(over)} · làm nốt rồi khép ca'
    elif left <= 0:
        label = 'Đến giờ đóng cửa'
    elif level:
        label = f'Còn {left_text(left)} là đóng cửa'
    else:
        label = f'Đóng cửa lúc {hm(cl)}'
    span = max(1, cl - op)
    return dict(base, is_open=True, minute=m, time=hm(m), part=part(m), progress=round(max(0, min(1, (m - op) / span)), 3),
                left=max(0, left), over=over, level=level, label=label, limit=limit)


def warning(before: int | None, after: int | None, c: dict, career: str) -> dict | None:
    """The one warning whose threshold this step crossed (the nearest to closing wins)."""
    if before is None or after is None or after <= before:
        return None
    cl = hours(c, career)[1]
    if career in OFFICE:
        o = _office(c) or {}
        if o.get('day') == c['day'] and o.get('ot'):
            cl = OFFICE_LOCK
    hit = None
    for mins, lvl, text in WARNINGS:
        at = cl - mins
        if before < at <= after:
            if lvl == 'closing':
                text = CLOSING_TEXT.get(career, text)
            hit = dict(level=lvl, text=text.format(left=left_text(cl - after)), time=hm(after))
    return hit


def close_summary(c: dict, career: str, s: dict | None = None) -> dict:
    """For the day summary (called at end_day while the shift is still open)."""
    op, cl = hours(c, career)
    m = minute_now(c, career)
    m = op if m is None else m
    nxt = dict(c, day=c['day'] + 1)
    nop, ncl = hours(nxt, career)
    early = max(0, cl - m)
    if s is not None:
        from . import days
        tomorrow = f'Ngày {days.today(s, c) + 1} (ngày mai)'
    else:
        tomorrow = 'Ngày mai'
    over = max(0, m - cl)
    if over:
        how = f'Khép ca lúc {hm(m)}, quá giờ {left_text(over)}.'
    elif early >= 30:
        how = f'Khép ca lúc {hm(m)}, sớm hơn giờ đóng cửa {left_text(early)}.'
    else:
        how = f'Khép ca lúc {hm(m)}, đúng giờ đóng cửa.'
    return dict(finish=hm(m), part=part(m), open=hm(op), close=hm(cl), early=early, over=over, text=how,
                next_open=hm(nop), next_close=hm(ncl), next_text=f'{tomorrow} mở cửa lúc {hm(nop)} (chuẩn bị từ {hm(max(0, nop - PREP))}).')
