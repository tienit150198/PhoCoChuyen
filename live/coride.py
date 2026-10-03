"""🛵 Vợ chồng chung xe (owner, feedback #136): a married couple share their vehicles on the strolls and at the fair.

* A vehicle on the wire is `r` {v, c, o?}: `o` is its owner's pid when it is not the rider's own (live/street.py
  clean_ride). Only the rider or their spouse (game/marriage.py: couples.status 'married') may own what they ride;
  anything else rides on foot, never an error.
* First come drives: a vehicle the spouse is riding now (on a stroll or at the fair, any room) cannot be ridden by
  the other; the frame that asked is answered `<feature>_taken {by, name}` and the asker stays on foot. The check and
  the change happen with no await between them (one event loop: atomic).
* The other spouse may sit behind the driver ("Ngồi sau": `back {to}` on a stroll, `fair_back {to}` at the fair):
  only their own spouse, in the same room, riding, with the seat behind free. The passenger's entry carries `b` (the
  driver's pid) and follows the driver's every walk; their own walks are ignored until they get off (`to: null`), the
  driver gets off the vehicle, sits / plays a stall, leaves or drops. Older clients ignore `b`: they see two people
  walking the same way.
"""
from __future__ import annotations

import re
import time

from .auth import pid_of

SPOUSE_TTL = 60.0
PID = re.compile(r'[0-9a-f]{16}')


async def spouse(db, p) -> str | None:
    """The pid of p's husband or wife (married, not engaged), or None. Cached on the player for a minute."""
    got = p.ext.get('spouse')
    t = time.monotonic()
    if got and got[1] > t:
        return got[0]
    row = await db.fetchrow("SELECT c.a AS a, c.b AS b FROM marriage_bonds m JOIN couples c ON c.id=m.couple "
                            "WHERE m.sid=? AND c.status='married'", (p.sid,))
    sp = pid_of(row['b'] if row['a'] == p.sid else row['a']) if row else None
    p.ext['spouse'] = (sp, t + SPOUSE_TTL)
    return sp


def _riding(hub, pid: str) -> dict | None:
    """What pid rides now on a stroll or at the fair (None: on foot, or not there)."""
    pl = hub.players.get(pid)
    if pl is None:
        return None
    for key, attr in (('walk', 'ride'), ('fair', 'r')):
        rid = pl.ext.get(key)
        room = hub.rooms.get(rid) if rid else None
        w = room.data['people'].get(pid) if room is not None else None
        if w is not None and getattr(w, attr, None):
            return getattr(w, attr)
    return None


def owner(r: dict, pid: str) -> str:
    return r.get('o') or pid


async def check(db, hub, p, r: dict | None) -> tuple:
    """(the vehicle p may ride now or None, the spouse's pid when they drive this very vehicle now or None).
    Someone else's vehicle: on foot. The caller sets the ride right after, with no await in between (atomic)."""
    if not r:
        return None, None
    sp = await spouse(db, p)
    o = r.get('o')
    if o and o != p.pid and o != sp:
        return None, None
    r = dict(v=r['v'], c=r['c'], o=o) if o and o != p.pid else dict(v=r['v'], c=r['c'])
    theirs = _riding(hub, sp) if sp else None
    if theirs and theirs['v'] == r['v'] and owner(theirs, sp) == owner(r, p.pid):
        return None, sp
    return r, None


def taken_frame(kind: str, hub, sp: str) -> dict:
    pl = hub.players.get(sp)
    return dict(t=kind, by=sp, name=(pl.name if pl else '') or 'Người ấy')
