"""🏅 The rank of the pet walking beside a player (game/pet_tiers.py, owner 19/10): the client sends `pt.r` (0 D … 6 SSS)
and `pt.x` (an SSS coat effect), and everyone draws its aura, so the service keeps a rank only up to the best one
this player really has: their 💪 lực chiến row (pet_board, week 'LC', acc {top, lg}: game/pets.py _power_row), read
once per player per TTL seconds and cached on the player. A 🌟 legendary breed walks only with someone who has one.
👗 Its outfit likewise (acc {wt, wl}): piece ranks no higher than the best piece owned, a luxury piece only with one.
Anything odd: the pet walks on without its aura, never an error.
"""
from __future__ import annotations

import json
import time

from .street_data import PET_LUX

TTL = 120.0
LEGENDS = frozenset({'linh_khuyen', 'than_tai'})


async def best(db, player) -> tuple:
    """(the highest rank kept, whether a legendary is kept, the best wardrobe piece's rank, whether a luxury piece is owned),
    cached on the player; no database: (0, False, 0, False)."""
    got = player.ext.get('pet_rank')
    t = time.monotonic()
    if got and got[1] > t:
        return got[0]
    if db is None or not getattr(player, 'sid', None):
        return (0, False, 0, False)
    try:
        rows = await db.fetch("SELECT acc FROM pet_board WHERE sid=? AND week='LC'", (player.sid,))
    except Exception:  # noqa: BLE001 - a busy database: no aura this time, never a refused walk
        return (0, False, 0, False)
    out = (0, False, 0, False)
    for r in rows:
        try:
            a = json.loads(r['acc'] or '{}')
        except (TypeError, ValueError):
            continue
        if isinstance(a, dict):
            top = a.get('top')
            wt = a.get('wt')
            out = (top if type(top) is int and 0 <= top <= 6 else 0, a.get('lg') is True,
                   wt if type(wt) is int and 0 <= wt <= 6 else 0, a.get('wl') is True)
    player.ext['pet_rank'] = (out, t + TTL)
    return out


def cap(pt: dict | None, top: tuple) -> dict | None:
    """`pt` with its rank no higher than `top` allows (an SSS coat only on an SSS)."""
    if not pt:
        return pt
    r, lg = top[0], top[1]
    wt, wl = (top[2], top[3]) if len(top) >= 4 else (0, False)
    if pt['b'] in LEGENDS and not lg:
        return None
    out = dict(pt)
    if out.get('lg') and not lg:
        out.pop('lg')
    if out.get('a'):   # 👗 pieces: ranks up to the best owned, luxury pieces only with one owned
        ar = list(out.get('ar') or [0] * len(out['a']))
        keep = [(k, min(ar[i] if i < len(ar) else 0, wt)) for i, k in enumerate(out['a']) if wl or k not in PET_LUX]
        out['a'] = [k for k, _ in keep]
        if any(v for _, v in keep):
            out['ar'] = [v for _, v in keep]
        else:
            out.pop('ar', None)
        if not wl and out.get('st') == 'hoang_gia':
            out.pop('st')
    if out.get('r', 0) > r:
        out.pop('r', None)
        out.pop('x', None)
    if out.get('x') and out['x'] != 'dot_bien' and out.get('r', 0) < 6:
        out.pop('x')
    return out


async def keep(db, player, pt: dict | None) -> dict | None:
    return cap(pt, await best(db, player)) if pt else pt


def cached(player, pt: dict | None) -> dict | None:
    """Without a database call (a handler that may not wait): the cached best, or the pet as sent when none is cached."""
    got = player.ext.get('pet_rank') if hasattr(player, 'ext') else None
    return cap(pt, got[0]) if pt and got else pt
