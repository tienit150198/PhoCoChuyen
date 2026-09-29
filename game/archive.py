"""Nothing a player made is ever dropped: rows that leave a capped list go to an archive.

The game keeps its lists short inside the save (journal, cash book, feed, histories,
logs...). Every place that cuts such a list calls one of the helpers below instead
of slicing by hand; the rows cut off are collected while a command runs and the
storage layer writes them to the `archive` table in the same transaction as the
save (game/storage.py). Outside a command (tests, previews on copies) nothing is
collected and the helpers behave exactly like the slices they replace.

    rows = last(rows, 40, "tasks", c)      # rows[-40:]   (oldest rows archived)
    rows = first(rows, 100, "feed", c)     # rows[:100]   (lists kept newest first)
    drop_head(rows, 20, "talk", c)         # del rows[:-20], in place

`owner` names the career the rows belong to: its record `c` (resolved to the
career id by the storage layer), a career id, JOURNEY ("" = the character's own
journey: wallet, board, life, investments), or None for the career the command
acts on.
"""
from __future__ import annotations

import contextvars
from typing import Any

JOURNEY = ""

# Kinds whose recent rows live in the save as a plain list, oldest first unless
# `newest_first`: GET /api/archive pages through the archived rows, then these.
IN_SAVE = {
    "journal": dict(path=("journal",)),
    "ledger": dict(path=("ops", "finance", "ledger")),
    "feed": dict(path=("feed",), newest_first=True),
    "wallet": dict(path=("history",), journey=True),
}

_OUT: contextvars.ContextVar = contextvars.ContextVar("archive_out", default=None)
_ACTING: contextvars.ContextVar = contextvars.ContextVar("archive_acting", default=None)


class Collector:
    """Rows cut off during one command: [(owner, kind, row)] in the order they were cut."""

    def __init__(self):
        self.rows: list = []

    def __enter__(self):
        self._token = _OUT.set(self)
        return self

    def __exit__(self, *exc):
        _OUT.reset(self._token)
        return False

    def add(self, owner: Any, kind: str, rows: list) -> None:
        if owner is None:
            owner = _ACTING.get()
        self.rows.extend((owner, kind, r) for r in rows)


def collect() -> Collector:
    """`with collect() as box:` ... box.rows holds what the code in the block cut off."""
    return Collector()


def acting(career: str | None):
    """Context token: rows cut with owner=None belong to this career (engine.apply_action)."""
    return _ACTING.set(career)


def done_acting(token) -> None:
    _ACTING.reset(token)


FORGET = '!forget:'


def forget(kind: str, owner: Any = None) -> None:
    """The player erased this history on purpose (a cleared chat): its archived rows go too."""
    box = _OUT.get()
    if box is not None:
        box.add(owner, FORGET + kind, [None])


def record(rows: list, kind: str, owner: Any = None) -> None:
    """Archive rows the caller removes by other means (a replaced review, a cleared chat)."""
    box = _OUT.get()
    if box is not None and rows:
        box.add(owner, kind, list(rows))


def last(rows: list, n: int, kind: str, owner: Any = None) -> list:
    """rows[-n:], archiving rows[:-n]."""
    box = _OUT.get()
    if box is not None and n > 0 and len(rows) > n:
        box.add(owner, kind, rows[:-n])
    return rows[-n:]


def first(rows: list, n: int, kind: str, owner: Any = None) -> list:
    """rows[:n], archiving rows[n:] (lists kept newest first)."""
    box = _OUT.get()
    if box is not None and len(rows) > n:
        box.add(owner, kind, rows[n:])
    return rows[:n]


def drop_head(rows: list, n: int, kind: str, owner: Any = None) -> None:
    """del rows[:-n] (in place), archiving what is deleted."""
    box = _OUT.get()
    if box is not None and n > 0 and len(rows) > n:
        box.add(owner, kind, rows[:-n])
    del rows[:-n]


def in_save(state: dict, career: str, kind: str) -> list | None:
    """The rows of `kind` still in the save, oldest first (None: not an IN_SAVE kind)."""
    spec = IN_SAVE.get(kind)
    if spec is None:
        return None
    node: Any = state.get("journey") if spec.get("journey") else (state.get("careers") or {}).get(career)
    if spec.get("journey") and career != JOURNEY:
        return None
    for key in spec["path"]:
        node = node.get(key) if isinstance(node, dict) else None
    if not isinstance(node, list):
        return []
    return list(reversed(node)) if spec.get("newest_first") else list(node)
