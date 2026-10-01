"""Bounded rate limits and caches (owner rule: every in-memory cache is bounded)."""
from __future__ import annotations

import time
from collections import OrderedDict, deque


class Bucket:
    """Token bucket: `burst` tokens, refilled at `rate` per second."""
    __slots__ = ('rate', 'burst', 'tokens', 'at')

    def __init__(self, rate: float, burst: float):
        self.rate, self.burst, self.tokens, self.at = rate, burst, burst, time.monotonic()

    def take(self, n: float = 1.0) -> bool:
        now = time.monotonic()
        self.tokens = min(self.burst, self.tokens + (now - self.at) * self.rate)
        self.at = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


class Window:
    """At most `limit` events per `seconds` (sliding). wait() says how long until the next one is allowed."""
    __slots__ = ('limit', 'seconds', 'times')

    def __init__(self, limit: int, seconds: float):
        self.limit, self.seconds, self.times = limit, seconds, deque()

    def _trim(self, now: float) -> None:
        while self.times and self.times[0] <= now - self.seconds:
            self.times.popleft()

    def hit(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        self._trim(now)
        if len(self.times) >= self.limit:
            return False
        self.times.append(now)
        return True

    def wait(self, now: float | None = None) -> float:
        now = time.monotonic() if now is None else now
        self._trim(now)
        return 0.0 if len(self.times) < self.limit else self.times[0] + self.seconds - now


class LRU(OrderedDict):
    """A dict that keeps at most `cap` keys (least recently used out first). get() refreshes a key."""

    def __init__(self, cap: int):
        super().__init__()
        self.cap = cap

    def get(self, key, default=None):
        if key in self:
            self.move_to_end(key)
            return self[key]
        return default

    def put(self, key, value):
        self[key] = value
        self.move_to_end(key)
        while len(self) > self.cap:
            self.popitem(last=False)
        return value


class Keyed:
    """Window per key (per IP, per player...), at most `cap` keys."""

    def __init__(self, limit: int, seconds: float, cap: int = 20000):
        self.limit, self.seconds, self.keys = limit, seconds, LRU(cap)

    def hit(self, key) -> bool:
        w = self.keys.get(key)
        if w is None:
            w = self.keys.put(key, Window(self.limit, self.seconds))
        return w.hit()

    def wait(self, key) -> float:
        w = self.keys.get(key)
        return 0.0 if w is None else w.wait()
