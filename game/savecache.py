"""Parsed saves kept between commands, per worker process (Store.saves).

A command parses its whole save (json.loads, ~1 ms per 100 KB of text), changes the dict
and writes its text back. When the next command of that save lands on the same process,
the dict it left behind is exactly what the database holds at that revision, so the
command skips fetching and parsing the text. The rules (Store.command relies on them):

- An entry is (revision, raw, text length, tag). take() REMOVES it: the thread that took it
  owns the dict alone and may change it in place. No other thread can reach it, and
  read-only paths (GET /api/state, bootstrap, replays...) never use the cache.
- A command gives its dict back (put) only after the new revision is committed and once
  nothing else uses it: public_state() shares a few lists with the save, so the view is
  either detached (copied) first, or the put waits until the response is encoded
  (Store.command(hold=True) + Store.release(), used by the HTTP command route).
- A command that fails never gives its dict back: the reducer may have changed it half way.
- Every writer of a save bumps its revision (commands, migrate-on-read, AI rewrites of a
  line, marriage, admin scripts, imports): a cached revision equal to the stored one means
  the same text. Anything else (older, newer, deleted save) is a miss and the entry goes.
  On PostgreSQL the tag is also the row version (xmin) written by the command, so even an
  edit that keeps the revision (by hand, in SQL) is seen. SQLite has no row version: there
  the cache is off unless SAVE_CACHE_MB is set.
- Bounded: SAVE_CACHE_MB (default 300, 0 = off: the kill switch) counting about 5 bytes
  of memory per character of save text, and SAVE_CACHE_ENTRIES (default 5000). The least
  recently used entry goes first.
- SAVE_CACHE_VERIFY (default 0.01): that share of hits also fetch the stored text and
  compare it with the cached dict. A difference is logged once and turns the cache off in
  this process. "strict" (tests): every hit is compared and every put checked for a dict
  that is plain JSON owned by nobody else; any problem raises AssertionError.
"""
from __future__ import annotations

import os
import random
import sys
import threading
from collections import OrderedDict

BYTES_PER_CHAR = 5  # a parsed save takes ~4-5x the memory of its JSON text


def _env_float(name: str, default: float) -> float:
    try:
        return float((os.environ.get(name) or "").strip() or default)
    except ValueError:
        return default


class SaveCache:
    def __init__(self, mb: float | None = None, entries: int | None = None, verify=None):
        self.cap = int(max(0.0, _env_float("SAVE_CACHE_MB", 300) if mb is None else mb) * 1024 * 1024)
        self.max_entries = max(1, int(_env_float("SAVE_CACHE_ENTRIES", 5000) if entries is None else entries))
        raw = (os.environ.get("SAVE_CACHE_VERIFY") or "0.01").strip().lower() if verify is None else str(verify)
        self.strict = raw == "strict"
        try:
            self.verify = 1.0 if self.strict else min(1.0, max(0.0, float(raw)))
        except ValueError:
            self.verify = 0.01
        self.on = self.cap > 0
        self.lock = threading.Lock()
        self.entries: OrderedDict = OrderedDict()  # sid -> (revision, raw, text length, tag, bytes)
        self.bytes = 0
        self.pid = os.getpid()
        self.hits = self.misses = self.stale = self.puts = self.evicted = self.checked = self.mismatches = 0

    def _forked(self) -> None:
        if self.pid != os.getpid():  # a forked worker starts empty (never shares the parent's dicts)
            self.entries.clear()
            self.bytes = 0
            self.pid = os.getpid()

    def take(self, sid: str):
        """(revision, raw, text length, tag) of this save, now owned by the caller alone, or None."""
        if not self.on:
            return None
        with self.lock:
            self._forked()
            e = self.entries.pop(sid, None)
            if e is None:
                return None
            self.bytes -= e[4]
        return e[:4]

    def put(self, sid: str, revision: int, raw: dict, length: int, tag=None) -> None:
        """Keep `raw`, the parsed text (of `length` characters) stored at `revision` (row version
        `tag`). The caller must not touch raw afterwards, nor let anything else keep a reference
        to its parts."""
        if not self.on or type(raw) is not dict:
            return
        size = max(1, length) * BYTES_PER_CHAR
        if size > self.cap:
            return
        if self.strict:
            problem = impure(raw)
            if problem:
                raise AssertionError(f"save cache: {problem}")
        with self.lock:
            self._forked()
            old = self.entries.pop(sid, None)
            if old is not None:
                self.bytes -= old[4]
                if old[0] > revision:  # a newer revision was put meanwhile: keep that one
                    revision, raw, length, tag, size = old
            self.entries[sid] = (revision, raw, length, tag, size)
            self.bytes += size
            self.puts += 1
            while self.entries and (self.bytes > self.cap or len(self.entries) > self.max_entries):
                _, e = self.entries.popitem(last=False)
                self.bytes -= e[4]
                self.evicted += 1

    def drop(self, sid: str) -> None:
        with self.lock:
            e = self.entries.pop(sid, None)
            if e is not None:
                self.bytes -= e[4]

    def clear(self) -> None:
        with self.lock:
            self.entries.clear()
            self.bytes = 0

    def should_check(self) -> bool:
        return self.verify > 0 and (self.verify >= 1 or random.random() < self.verify)

    def mismatch(self, sid: str, detail: str) -> None:
        """The cached dict was not the stored save: stop using the cache in this process."""
        self.mismatches += 1
        if self.strict:
            raise AssertionError(f"save cache: cached save differs from the stored one ({detail})")
        if self.on:
            self.on = False
            self.clear()
            sys.stderr.write(f"[save-cache] a cached save differed from the stored one ({detail}); cache off in pid={os.getpid()}\n")

    def stats(self) -> dict:
        n = self.hits + self.misses
        return dict(on=self.on, hits=self.hits, misses=self.misses, stale=self.stale,
                    hit_rate=round(self.hits / n, 3) if n else None, entries=len(self.entries),
                    mb=round(self.bytes / 1048576, 1), cap_mb=round(self.cap / 1048576), evicted=self.evicted,
                    checked=self.checked, mismatches=self.mismatches)


def same(a, b) -> bool:
    """Equal JSON values of the same types all the way down (1 is not 1.0 nor True)."""
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return len(a) == len(b) and all(k in b and same(v, b[k]) for k, v in a.items()) and list(a) == list(b)
    if type(a) is list:
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b or (a != a and b != b)


_JSON = (str, int, float, bool, type(None))


def impure(raw: dict) -> str | None:
    """Why `raw` is not a plain JSON tree referenced by nobody else (None when it is): a
    tuple, a set or another type, a non-str key, a list or dict reached twice, or one that
    something outside the tree still references (a module constant, an lru_cache value, a
    view that was not detached...). With any of those the next command could change what
    is not its own, or see something json.loads would not have given it."""
    containers = []
    edges: dict = {}
    stack = [(raw, "$")]
    while stack:
        o, path = stack.pop()
        t = type(o)
        if t is dict:
            for k, v in o.items():
                if type(k) is not str:
                    return f"non-str key {k!r} at {path}"
                if type(v) in (dict, list):
                    n = edges.get(id(v), 0)
                    if n:
                        return f"{path}.{k} is also reached elsewhere in the save"
                    edges[id(v)] = 1
                    containers.append((v, f"{path}.{k}"))
                    stack.append((v, f"{path}.{k}"))
                elif type(v) not in _JSON:
                    return f"{type(v).__name__} at {path}.{k}"
        else:
            for i, v in enumerate(o):
                if type(v) in (dict, list):
                    if edges.get(id(v)):
                        return f"{path}[{i}] is also reached elsewhere in the save"
                    edges[id(v)] = 1
                    containers.append((v, f"{path}[{i}]"))
                    stack.append((v, f"{path}[{i}]"))
                elif type(v) not in _JSON:
                    return f"{type(v).__name__} at {path}[{i}]"
    stack = o = v = None  # (loop variables would count as references)
    for v, path in containers:
        # references: its parent, the `containers` tuple, the loop variable, getrefcount's argument
        if sys.getrefcount(v) > 4:
            return f"{path} is also referenced outside the save"
    return None
