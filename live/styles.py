"""🎨 Status for a week (game/spend.py): a name colour, a profile frame and a title, read from `chat_style`.

The game server writes the row with the save (only what was paid for; nothing a client sends), and announces a change
with pg_notify {op: 'style', pid}. This service shows it as an optional `st` = {c?, f?, t?} (catalogue ids,
game/spend_content.py) beside the name: on chat messages, on walkers and on a player's card. It is never inside `look`
(clean_look of an older service refuses keys it does not know), and an older client ignores `st`.

* The table comes with SCHEMA_VERSION 25. Until it exists every lookup answers {} and the table is looked for again
  every RETRY seconds, so this service and the game server roll out in any order.
* Memory: an LRU of CACHE players (owner rule: every cache is bounded), each entry refreshed after TTL seconds; a
  NOTIFY drops the player's entry at once. Expiry is checked on every read (the row keeps the `_until` times).
"""
from __future__ import annotations

import time

from game.spend_content import STYLE_ITEMS, TITLE_TEXT

from .db import Error as DbError, log
from .limits import LRU

CACHE = 20000
TTL = 300.0
RETRY = 300.0
_KEYS = (('c', 'color'), ('f', 'frame'), ('t', 'title'))


def public(row, now: float | None = None) -> dict:
    """{c, f, t} of a chat_style row: ids this build knows, of the right kind, not expired."""
    if not row:
        return {}
    now = time.time() if now is None else now
    out = {}
    for key, kind in _KEYS:
        x, until = row.get(kind), row.get(kind + '_until')
        it = STYLE_ITEMS.get(x) if isinstance(x, str) else None
        if it and it['kind'] == kind and not it.get('gone') and isinstance(until, (int, float)) and until > now:
            out[key] = x
    return out


def title_text(st: dict) -> str | None:
    """The name tag's text of a bought title ("☕ Tín đồ cà phê"), or None."""
    return TITLE_TEXT.get(st.get('t')) if st else None


class Styles:
    def __init__(self, app):
        self.app = app             # its db is read at each query (the service opens it after the features exist)
        self.rows = LRU(CACHE)     # pid -> (fetched monotonic, row dict | None)
        self.off_until = 0.0

    def forget(self, pid: str) -> None:
        self.rows.pop(pid, None)

    async def of(self, pids, now: float | None = None) -> dict:
        """{pid: st} for these players ({} for nobody styled); one primary-key query per 500 missing players."""
        mono = time.monotonic()
        ids = [p for p in dict.fromkeys(pids) if isinstance(p, str) and p]
        out, miss = {}, []
        for pid in ids:
            hit = self.rows.get(pid)
            if hit is not None and mono - hit[0] < TTL:
                out[pid] = public(hit[1], now)
            else:
                miss.append(pid)
        if miss and mono < self.off_until:
            return {**out, **{p: {} for p in miss}}
        for i in range(0, len(miss), 500):
            part = miss[i:i + 500]
            try:
                got = {r['pid']: dict(r) for r in await self.app.db.fetch(
                    'SELECT pid, color, color_until, frame, frame_until, title, title_until FROM chat_style '
                    f"WHERE pid IN ({','.join('?' * len(part))})", part)}
            except DbError as e:   # a database from before SCHEMA_VERSION 25: nobody is styled yet
                log('styles:', type(e).__name__)
                self.off_until = mono + RETRY
                return {**out, **{p: {} for p in miss}}
            for pid in part:
                row = got.get(pid)
                self.rows.put(pid, (mono, row))
                out[pid] = public(row, now)
        return out

    async def one(self, pid: str) -> dict:
        return (await self.of([pid])).get(pid) or {}


def of_app(app) -> Styles:
    """The service's one Styles (made on first use)."""
    st = getattr(app, '_styles', None)
    if st is None:
        st = app._styles = Styles(app)
    return st


async def with_styles(app, frames: list, key: str = 'pid') -> list:
    """The frames with their authors' `st` now (copies where it changes; buffered frames are never mutated)."""
    if not frames:
        return frames
    sx = await of_app(app).of(f.get(key) for f in frames)
    out = []
    for f in frames:
        st = sx.get(f.get(key)) or None
        if f.get('st') != st:
            f = dict(f)
            if st:
                f['st'] = st
            else:
                f.pop('st', None)
        out.append(f)
    return out
