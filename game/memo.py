"""Bounded memos for pure functions of fixed content (the public view's hot helpers).

Each Memo is an LRU with a maximum number of rows AND an approximate byte budget, shared
by the threads of one process (one worker): memory stays bounded however long the
worker runs. Keys are content (a post id and round, a career and day), never a save or
a session, so nothing is kept per player. Values are handed out as they are stored:
callers copy them before giving them to anyone who may change them.
"""
from __future__ import annotations

import sys
import threading
from collections import OrderedDict


class Memo:
    def __init__(self, entries: int, budget: int):
        self.entries = entries   # most rows kept
        self.budget = budget     # about this many bytes (each row's size as the caller estimates it)
        self.rows: OrderedDict = OrderedDict()
        self.bytes = 0
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            row = self.rows.get(key)
            if row is None:
                return None
            self.rows.move_to_end(key)
            return row[0]

    def put(self, key, value, size: int) -> None:
        if size > self.budget:
            return
        with self.lock:
            old = self.rows.pop(key, None)
            if old is not None:
                self.bytes -= old[1]
            self.rows[key] = (value, size)
            self.bytes += size
            while len(self.rows) > self.entries or self.bytes > self.budget:
                _, (_, gone) = self.rows.popitem(last=False)
                self.bytes -= gone

    def clear(self) -> None:
        with self.lock:
            self.rows.clear()
            self.bytes = 0

    def __len__(self) -> int:
        return len(self.rows)


def size_of(x, depth: int = 6) -> int:
    """Rough bytes held by a JSON-shaped value (containers and their leaves; shared
    constants are counted too, so this errs on the large side)."""
    n = sys.getsizeof(x)
    if depth <= 0:
        return n
    if isinstance(x, dict):
        for k, v in x.items():
            n += sys.getsizeof(k) + size_of(v, depth - 1)
    elif isinstance(x, (list, tuple)):
        for v in x:
            n += size_of(v, depth - 1)
    return n
