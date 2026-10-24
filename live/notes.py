"""💭 Ghi chú trạng thái (feedback #170 "viết status ở khung chat như mess/tiktok"): a one-line note over a player's
avatar, like Messenger notes. Set and cleared from the chat screen (live/chat.py `note`), at most LEN characters on one
line, gone after TTL seconds (24 h).

* Shown as `nt` {t, at} on: the friends list and DM peers of the chat list, `me` (my own), the player cards of the
  street (`card`), the town (`town_card`) and the fishing lake (`fl_card`); a change goes out live as `noted {pid, nt}`
  to my other tabs and my online friends (nt null: cleared, expired or hidden).
* The chat word filter (live/filters.py clean + mask) runs on it like on a message; what was typed stays in `raw` for
  the admin only. Anyone who can see a note can report it (`note_report {pid, reason}`, reports kind 'note', target
  '<pid>:<at>' so a new note starts clean); HIDE_AFTER distinct reports hide it (hidden=1) until it is replaced.
* 🙈 A player who hides their online status (Chat → Hiện trạng thái online off, `prefs {online}`) shows their note to
  friends only: `pub` keeps that switch beside the note (written with the note and by `prefs`), so a card read while
  they are offline knows it too. Blocks hide it both ways.
* Table chat_notes (SCHEMA_VERSION 94, written by this service only, so the cache is the truth; a row past its 24 h is
  deleted every PRUNE_EVERY seconds by its `at` index). Until the table exists every lookup answers nothing and is
  looked for again every RETRY seconds; `note` answers 'off'. The game server deletes the row with the player's data.
* Memory: an LRU of CACHE players (owner rule: every cache is bounded); expiry is checked on every read.
"""
from __future__ import annotations

import time

from . import filters
from .db import Error as DbError, log
from .limits import LRU

LEN = 60
TTL = 86400.0
CACHE = 20000
RETRY = 300.0
PRUNE_EVERY = 600.0
HIDE_AFTER = 3


def public(row, now: float | None = None) -> dict | None:
    """{t, at} of a chat_notes row still showing, else None."""
    now = time.time() if now is None else now
    if not row or row.get('hidden') or not row.get('text') or float(row.get('at') or 0) <= now - TTL:
        return None
    return dict(t=row['text'], at=round(float(row['at'])))


class Notes:
    def __init__(self, app):
        self.app = app
        self.rows = LRU(CACHE)      # pid -> row dict | None (None: no note)
        self.off_until = 0.0
        self._prune_at = 0.0

    @property
    def on(self) -> bool:
        return time.monotonic() >= self.off_until

    def _off(self, e) -> None:
        log('notes:', type(e).__name__)
        self.off_until = time.monotonic() + RETRY

    def forget(self, pid: str) -> None:
        self.rows.put(pid, None)

    async def rows_of(self, pids) -> dict:
        """{pid: row | None} for these players; one primary-key query per 500 missing."""
        ids = [p for p in dict.fromkeys(pids) if isinstance(p, str) and p]
        out, miss = {}, []
        for pid in ids:
            if pid in self.rows:
                out[pid] = self.rows.get(pid)
            else:
                miss.append(pid)
        if miss and not self.on:
            return {**out, **{p: None for p in miss}}
        for i in range(0, len(miss), 500):
            part = miss[i:i + 500]
            try:
                got = {r['pid']: dict(r) for r in await self.app.db.fetch(
                    f"SELECT pid, text, at, hidden, pub FROM chat_notes WHERE pid IN ({','.join('?' * len(part))})", part)}
            except DbError as e:   # a database from before SCHEMA_VERSION 94: nobody has a note yet
                self._off(e)
                return {**out, **{p: None for p in miss}}
            for pid in part:
                out[pid] = self.rows.put(pid, got.get(pid))
        return out

    @staticmethod
    def can_see(row, owner_pid: str, viewer) -> bool:
        """The viewer (a live Player) may see this owner's note: no block either way, and a hidden owner only to friends."""
        if viewer is None:
            return False
        if owner_pid == viewer.pid:
            return True
        if owner_pid in viewer.hidden:
            return False
        if row and not row.get('pub', 1) and owner_pid not in viewer.friends:
            return False
        return True

    async def for_viewer(self, viewer, pids, now: float | None = None) -> dict:
        """{pid: {t, at}} of the notes this viewer may see (players without one left out)."""
        now = time.time() if now is None else now
        hub = getattr(self.app, 'hub', None)
        out = {}
        for pid, row in (await self.rows_of(pids)).items():
            nt = public(row, now)
            if not nt or not self.can_see(row, pid, viewer):
                continue
            o = hub.players.get(pid) if hub else None
            if o is not None and viewer.pid in o.hidden:
                continue
            out[pid] = nt
        return out

    async def one(self, viewer, pid: str) -> dict | None:
        return (await self.for_viewer(viewer, [pid])).get(pid)

    async def store(self, p, text: str, raw: str | None) -> dict | None:
        """Set my note (text already cleaned) or clear it (text ''). Returns the new {t, at} or None."""
        t = time.time()
        if text:
            await self.app.db.execute(
                'INSERT INTO chat_notes(pid, text, raw, at, hidden, reports, pub) VALUES(?, ?, ?, ?, 0, 0, ?) '
                'ON CONFLICT(pid) DO UPDATE SET text=excluded.text, raw=excluded.raw, at=excluded.at, hidden=0, reports=0, pub=excluded.pub',
                (p.pid, text, raw, t, 1 if p.show_online else 0))
            self.rows.put(p.pid, dict(pid=p.pid, text=text, at=t, hidden=0, pub=1 if p.show_online else 0))
            return public(self.rows.get(p.pid), t)
        await self.app.db.execute('DELETE FROM chat_notes WHERE pid=?', (p.pid,))
        self.rows.put(p.pid, None)
        return None

    async def set_pub(self, p) -> None:
        """`prefs {online}` changed: the note follows (a hidden player's note shows to friends only)."""
        row = (await self.rows_of([p.pid])).get(p.pid)
        if not row:
            return
        pub = 1 if p.show_online else 0
        if row.get('pub') == pub:
            return
        try:
            await self.app.db.execute('UPDATE chat_notes SET pub=? WHERE pid=?', (pub, p.pid))
        except DbError as e:
            self._off(e)
            return
        self.rows.put(p.pid, dict(row, pub=pub))

    async def report(self, reporter, owner_pid: str, reason: str) -> bool:
        """One report per reporter and note; True when this report hid it."""
        row = (await self.rows_of([owner_pid])).get(owner_pid)
        if not public(row) or not self.can_see(row, owner_pid, reporter):
            return False
        target = f'{owner_pid}:{int(float(row["at"]))}'
        t = time.time()

        async def run(tx):
            n = await tx.execute("INSERT INTO reports(reporter, kind, target, reason, at) VALUES(?, 'note', ?, ?, ?) "
                                 'ON CONFLICT(reporter, kind, target) DO NOTHING', (reporter.pid, target, reason, t))
            if n != 1:
                return None
            return await tx.fetchrow('UPDATE chat_notes SET reports=reports+1 WHERE pid=? AND at=? RETURNING reports, hidden',
                                     (owner_pid, row['at']))
        upd = await self.app.db.transaction(run)
        if upd and int(upd['reports']) >= HIDE_AFTER and int(upd['hidden']) == 0:
            if await self.app.db.execute('UPDATE chat_notes SET hidden=1 WHERE pid=? AND at=? AND hidden=0', (owner_pid, row['at'])) == 1:
                self.rows.put(owner_pid, dict(row, hidden=1))
                return True
        return False

    async def prune(self, now: float) -> int:
        if now < self._prune_at or not self.on:
            return 0
        self._prune_at = now + PRUNE_EVERY
        try:
            n = await self.app.db.execute('DELETE FROM chat_notes WHERE at<?', (time.time() - TTL,))
        except DbError as e:
            self._off(e)
            return 0
        return n or 0


def clean(text) -> tuple[str, str | None] | None:
    """(what shows, what was typed when the filter changed it) of a note, or None when it is not one line of 1–LEN
    characters. '' clears."""
    if text == '' or text is None:
        return '', None
    c = filters.clean(text, LEN, 1)
    if c is None or '\n' in c:
        return None
    masked = filters.mask(c)
    return masked, (c if masked != c else None)


def of_app(app) -> Notes:
    """The service's one Notes (made on first use)."""
    n = getattr(app, '_notes', None)
    if n is None:
        n = app._notes = Notes(app)
    return n
