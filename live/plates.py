"""🔨 Biển đẹp on the live maps (owner 16/10): a ride may carry `p`, the text of a plate won at the auction house
(game/auction.py; the client sends the plate attached to the vehicle it rides, public/js/v4/ride.js wire). Others draw
it in gold, so the service keeps it only when this player really won that plate: auction_lots rows they won (status
'sold', a plate kind), read once per player per TTL seconds and cached on the player (a small table: a few lots a day).
A free "biển tên" never travels. Anything odd: the ride goes on without a plate, never an error.
"""
from __future__ import annotations

import re
import time

KINDS = ('plate', 'reg', 'hull')    # game/auction_content.py PLATE_KINDS
TTL = 300.0
MAX = 24
_CTRL = re.compile(r'[\x00-\x1f\x7f]')


def clean(p) -> str:
    """A plate text off the wire ('' when there is none or it looks wrong)."""
    if not isinstance(p, str) or len(p) > MAX or _CTRL.search(p):
        return ''
    return p.strip()


async def won(db, player) -> frozenset:
    """The plate texts this player won (cached TTL seconds on the player; no database: none)."""
    got = player.ext.get('uq_plates')
    t = time.monotonic()
    if got and got[1] > t:
        return got[0]
    if db is None:
        return frozenset()
    try:
        rows = await db.fetch("SELECT name FROM auction_lots WHERE winner_sid=? AND status='sold' AND kind IN (?,?,?)",
                              (player.sid, *KINDS))
    except Exception:  # noqa: BLE001 - a busy database: no plate this time, never a refused ride
        return frozenset()
    out = frozenset(str(r['name']) for r in rows)
    player.ext['uq_plates'] = (out, t + TTL)
    return out


async def keep(db, player, r: dict | None) -> dict | None:
    """`r` with its `p` only when the player won that plate (and rides their own vehicle)."""
    if not r or not r.get('p'):
        return r
    if r.get('o') or r['p'] not in await won(db, player):
        r = {k: v for k, v in r.items() if k != 'p'}
    return r
