"""👶 Bế bé đi chơi (feedback #252): a player carrying their baby on a stroll, at a wedding party or at the fair.

* On the wire the baby is `bb` {n: name, g: stage ('so_sinh' | 'biet_bo' | 'chap_chung', game/cradle.py), o: outfit
  ('basic' | 'yem' | 'flower', game/household.py OUTFITS), sh?: 1 for the couple's shared child}. A client sends it on
  `walk_in` / `wed_in` / `fair_in` (public/js/v4/baby.js); a public entry carries it back while set. Optional
  everywhere: an older client sends none and ignores it, an older service drops it (nobody sees the baby).
* Never refused: anything odd shows no baby. The name goes through the chat filter (heavy words masked, links and
  contacts dropped), unknown keys are left out.
* 💑 The shared child is in one pair of arms at a time: when the husband or wife already carries it (any stroll, the
  fair), the one coming in walks without it and is told so (`bb_taken {by, name}` in the room reply). The check and
  the entry happen with no await between them (one event loop: atomic), like live/coride.py's vehicles.
"""
from __future__ import annotations

from . import coride, filters

STAGES = frozenset({'so_sinh', 'biet_bo', 'chap_chung'})
OUTFITS = frozenset({'basic', 'yem', 'flower'})


def clean_baby(bb) -> dict | None:
    """{n, g, o[, sh]} or None (no baby)."""
    if not isinstance(bb, dict) or bb.get('g') not in STAGES:
        return None
    n = filters.clean(bb.get('n'), 16, 1)
    n = filters.mask(n) if n else None
    out = dict(g=bb['g'], o=bb.get('o') if bb.get('o') in OUTFITS else 'basic')
    if n:
        out['n'] = n
    if bb.get('sh') in (1, True):
        out['sh'] = 1
    return out


def carrying_shared(hub, pid: str) -> bool:
    """pid carries the couple's shared child now, on a stroll (or a wedding) or at the fair."""
    pl = hub.players.get(pid)
    if pl is None:
        return False
    for key in ('walk', 'fair'):
        rid = pl.ext.get(key)
        room = hub.rooms.get(rid) if rid else None
        w = room.data['people'].get(pid) if room is not None else None
        bb = getattr(w, 'bb', None) if w is not None else None
        if isinstance(bb, dict) and bb.get('sh'):
            return True
    return False


async def spouse_of(db, p, bb: dict | None) -> str | None:
    """The spouse to check (only for the shared child; an await: call it before the entry's last await)."""
    if not bb or not bb.get('sh'):
        return None
    sp = await coride.spouse(db, p)
    return sp if sp and sp != p.pid else None


def claim(hub, bb: dict | None, sp: str | None) -> tuple:
    """(the baby p may carry now or None, the spouse's pid when they carry the shared child now or None).
    Synchronous: the caller enters the room right after, with no await in between."""
    if bb and sp and carrying_shared(hub, sp):
        return None, sp
    return bb, None


def taken_frame(hub, sp: str) -> dict:
    pl = hub.players.get(sp)
    return dict(by=sp, name=(pl.name if pl else '') or 'Người ấy')
