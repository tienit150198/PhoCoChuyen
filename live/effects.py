"""Rewards the live service grants (phase 2: a lucky red envelope; phase 3: a date's spirit boost). The live
service never writes a save: it inserts a `live_effects` row, and the game server applies pending rows to the
save on the player's next load (phase 3 adds game/live_effects.py on_load, the system_gift pattern: one
internal command per row with the fixed request id `live-<id>`, so it is paid once).

    ok = await grant(db, sid, 'coins', 5, key=f'env:{room}:{n}', cap=30, cap_like='env:%')

`key` makes it idempotent (a retry inserts nothing); `cap` is the most of that kind per player per Vietnam
day (amounts summed), None for no cap; `cap_like` (an id pattern) counts only those rows toward it (the street's lì
xì: not the wedding's minute money or the envelopes guests give). A 'spirit' row may also take a little away (SPIRIT_DOWN..-1: a beer at a
wedding party, live/wedding.py); every other kind only gives."""
from __future__ import annotations

import json
import time

from .auth import vn_today
from datetime import datetime, timedelta, timezone

KINDS = ('coins', 'spirit', 'closeness', 'title')
AMOUNT_MAX = 2000                # game/live_effects.py AMOUNT_MAX (the 1000-day anniversary is 1,500 xu)
SPIRIT_DOWN = -10               # game/live_effects.py SPIRIT_DOWN: the most a 'spirit' row may take away


def _day_start(t: float) -> float:
    day = datetime.strptime(vn_today(t), '%Y-%m-%d').replace(tzinfo=timezone(timedelta(hours=7)))
    return day.timestamp()


async def grant(db, sid: str, kind: str, amount: int, key: str, data: dict | None = None, cap: int | None = None,
                cap_like: str | None = None) -> bool:
    low = SPIRIT_DOWN if kind == 'spirit' else 1
    if kind not in KINDS or type(amount) is not int or not low <= amount <= AMOUNT_MAX or amount == 0 or not key or len(key) > 120:
        raise ValueError('bad effect')
    t = time.time()
    payload = json.dumps(data or {}, ensure_ascii=False, separators=(',', ':'))

    async def run(tx):
        if cap is not None:
            if cap_like:
                rows = await tx.fetch('SELECT amount FROM live_effects WHERE sid=? AND kind=? AND at>=? AND id LIKE ?',
                                      (sid, kind, _day_start(t), cap_like))
            else:
                rows = await tx.fetch('SELECT amount FROM live_effects WHERE sid=? AND kind=? AND at>=?', (sid, kind, _day_start(t)))
            if sum(int(r['amount']) for r in rows) + amount > cap:
                return False
        n = await tx.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?, ?, ?, ?, ?, 'pending', ?) "
                             'ON CONFLICT(id) DO NOTHING', (key, sid, kind, amount, payload, t))
        return n == 1
    return await db.transaction(run)
