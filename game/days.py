"""Ngày N: one day counter for the player and concrete words for "hôm sau".

The story counts life days (`s['journey']['life_day']`, +1 each time a shift is closed anywhere);
the free sandbox counts the career's own days (`c['day']`). The HUD shows this one number as
"Ngày N" and every wait or deadline is worded against it, so "phỏng vấn lại hôm sau" becomes
"từ Ngày 5 (còn 1 ngày · sau khi khép ca hôm nay)", or "bây giờ" once it is open.
"""
from __future__ import annotations


def story(s: dict) -> bool:
    return bool((s.get('journey') or {}).get('story'))


def today(s: dict, c: dict | None = None) -> int:
    """The player's day: the life day in the story, the career's day elsewhere."""
    j = s.get('journey') or {}
    life = j.get('life_day')
    if j.get('story') and type(life) is int:
        return life
    if c is None:
        cur = s.get('current')
        c = (s.get('careers') or {}).get(cur) if cur else None
    return int((c or {}).get('day') or 1)


def day_info(s: dict, target: int, c: dict | None = None) -> dict:
    """{day, left, open, text} for a wait that ends on day `target` (a player day number)."""
    now = today(s, c)
    target = int(target)
    left = max(0, target - now)
    return dict(day=target, today=now, left=left, open=left == 0, text=when_day(s, target, c))


def when_day(s: dict, target: int, c: dict | None = None) -> str:
    """'bây giờ' · 'từ Ngày 5 (còn 1 ngày · sau khi khép ca hôm nay)' · 'từ Ngày 7 (còn 3 ngày)'."""
    now = today(s, c)
    target = int(target)
    left = target - now
    if left <= 0:
        return 'bây giờ'
    if left == 1:
        return f'từ Ngày {target} (còn 1 ngày · sau khi khép ca hôm nay)'
    return f'từ Ngày {target} (còn {left} ngày)'


def on_day(s: dict, target: int, c: dict | None = None) -> str:
    """A date rather than an opening: 'hôm nay (Ngày 4)' · 'Ngày 5 (ngày mai)' · 'Ngày 9 (còn 5 ngày)' · 'Ngày 2 (đã qua)'."""
    now = today(s, c)
    target = int(target)
    left = target - now
    if left == 0:
        return f'hôm nay (Ngày {target})'
    if left == 1:
        return f'Ngày {target} (ngày mai)'
    if left < 0:
        return f'Ngày {target} (đã qua)'
    return f'Ngày {target} (còn {left} ngày)'
