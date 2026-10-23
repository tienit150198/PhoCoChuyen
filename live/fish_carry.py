"""🎣 The fish a walker carries on the walk maps (game/fishing.py jr_fish_carry, owner 24/10: "càng hiếm càng to, mang được
trên người"): the client sends `fh` = {sp, kg} (journey.fish.wear) with walk_in / town_in / isl_in (and town_mv when it
changes); everyone draws it (public/js/v4/fish-art.js drawFish) in the hands of that character.

Kept honest without reading the save: the species must be one this build knows, of 🟣 Hiếm or rarer (fishing_content
CARRY_MIN), the weight inside its band, and the player must have caught a fish of that rarity: their 📖 collection row
(fish_dex.rc, game/fish_lb.py), read once per player per TTL seconds and cached on the player. What is drawn (the family,
colours, pattern) comes from this build's own catalogue, never from the client. Anything odd: no fish, never an error.
"""
from __future__ import annotations

import json
import math
import time

from game import fishing_content as C

TTL = 120.0


def clean(fh) -> dict | None:
    """{sp, kg} from a client: the public carried fish {sp, r, kg, fam, body, belly, fin, pat}, or None."""
    if not isinstance(fh, dict) or set(fh) - {'sp', 'kg', 'r'}:
        return None
    sp = C.SPECIES.get(fh.get('sp')) if isinstance(fh.get('sp'), str) else None
    kg = fh.get('kg')
    if not sp or sp['r'] < C.CARRY_MIN or type(kg) not in (int, float) or not math.isfinite(kg):
        return None
    lo, hi = sp['w']
    if not lo * 0.99 <= kg <= hi * 1.01:
        return None
    return public(sp, kg)


def public(sp: dict, kg: float) -> dict:
    return dict(sp=sp['id'], r=sp['r'], kg=round(float(kg), 2), fam=sp['fam'], body=sp['body'], belly=sp['belly'], fin=sp['fin'],
                pat=sp['pat'])


async def best(db, player) -> int:
    """The rarest rarity this player has in the 📖 collection (-1: none or no database), cached on the player."""
    got = player.ext.get('fish_rc') if hasattr(player, 'ext') else None
    t = time.monotonic()
    if got and got[1] > t:
        return got[0]
    if db is None or not getattr(player, 'sid', None):
        return -1
    top = -1
    try:
        rows = await db.fetch('SELECT rc FROM fish_dex WHERE sid=?', (player.sid,))
    except Exception:  # noqa: BLE001 - a busy database or a build before the table: no fish this time
        return -1
    for r in rows:
        try:
            rc = json.loads(r['rc'] or '[]')
        except (TypeError, ValueError):
            continue
        if isinstance(rc, list):
            top = max([i for i, n in enumerate(rc[:C.NR]) if type(n) is int and n > 0] + [top])
    player.ext['fish_rc'] = (top, t + TTL)
    return top


async def keep(db, player, fh: dict | None) -> dict | None:
    """`fh` (already clean) when this player has caught a fish of its rarity, else None."""
    if not fh:
        return None
    return fh if await best(db, player) >= fh['r'] else None
