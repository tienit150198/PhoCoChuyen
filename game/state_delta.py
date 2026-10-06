"""Smaller state answers: what the player's page already holds is not sent again.

Every command answer used to carry the whole public state (game/engine.py public_state: ~150 KB of JSON,
40-70 KB gzipped), although a tap changes a few parts of it. A page that says so (header X-Game-Delta: 1,
public/js/api.js) gets its state as a tree of parts named by a hash of their JSON, and on /api/command
it lists the hashes of the parts it holds (`known`): those parts come back as a 0 placeholder plus a
reference, and the page puts its own copy there.

The tree. The state is split into its members, and so is every member whose JSON is longer than SPLIT
(dicts with text keys, lists), down to MAX_DEPTH levels. A part of at least MIN bytes is named by
digest() of its JSON (48 bits of BLAKE2b, 8 url-safe base64 characters); smaller parts are always sent.
A named part the page holds is not looked into (one reference for the whole of it); one it does not
hold is split again or sent whole.

The answer (encode): the state's JSON with each reused part written as 0, and
  delta = {"refs": [[path, hash], ...],   the 0 at `path` is the page's part named `hash`
           "keys": [[path, hash], ...]}   the named parts sent in this answer (split ones included)
paths being lists of keys and list indexes from the state's root, in document order.

Content-addressed, so nothing on the server remembers a page: a restart, another tab, an import or a
409 cannot leave the page with a stale part, as a part is reused only when its JSON is byte for byte
what the page holds under that hash. A page that sends no header (older pages during a rolling release)
gets exactly the answer of before; an older server ignores the header and `known` and answers in full,
which the page takes as before (no `delta` member).
"""
from __future__ import annotations

import binascii
import hashlib
import json

from . import fastjson as fj

SPLIT = 2048      # a dict or list whose JSON is longer is split into its members
MIN = 128         # parts at least this long are named by a hash (smaller ones are always sent)
MAX_DEPTH = 6     # levels below the state's root that may be split
HASH_LEN = 8      # characters per hash in `known` (48 bits)
MAX_KNOWN = 8192  # hashes taken from one request (a real page holds a few hundred)


_URLSAFE = bytes.maketrans(b"+/", b"-_")


def digest(data: bytes) -> str:
    """48 bits of BLAKE2b as 8 url-safe base64 characters."""
    return binascii.b2a_base64(hashlib.blake2b(data, digest_size=6).digest(), newline=False).translate(_URLSAFE).decode()


def parse_known(raw) -> frozenset:
    """The `known` of a command body: the page's hashes, concatenated (8 characters each). Anything
    else (absent, wrong type, cut short) is an empty set: the answer is then whole."""
    if not isinstance(raw, str) or not raw or len(raw) % HASH_LEN or len(raw) > MAX_KNOWN * HASH_LEN:
        return frozenset()
    return frozenset(raw[i:i + HASH_LEN] for i in range(0, len(raw), HASH_LEN))


_KEYS: dict = {}


def _key(k: str) -> bytes:
    """A member name's JSON (most names come back on every answer: kept, up to a bound)."""
    b = _KEYS.get(k)
    if b is None:
        b = json.dumps(k, ensure_ascii=False).encode()
        if len(_KEYS) < 4096:
            _KEYS[k] = b
    return b


def _splittable(value) -> bool:
    t = type(value)
    if t is dict:
        return bool(value) and all(type(k) is str for k in value)
    return (t is list or t is tuple) and bool(value)


def _part(value, path: list, depth: int, known: frozenset, refs: list, keys: list) -> bytes:
    data = fj.dumps_body(value)
    h = digest(data) if len(data) >= MIN else None
    if h is not None and h in known:
        refs.append([path, h])
        return b"0"
    if h is not None:
        keys.append([path, h])
    if len(data) > SPLIT and depth < MAX_DEPTH and _splittable(value):
        return _members(value, path, depth + 1, known, refs, keys)
    return data


def _members(value, path: list, depth: int, known: frozenset, refs: list, keys: list) -> bytes:
    if type(value) is dict:
        return b"{" + b",".join(_key(k) + b":" + _part(v, path + [k], depth, known, refs, keys) for k, v in value.items()) + b"}"
    return b"[" + b",".join(_part(v, path + [i], depth, known, refs, keys) for i, v in enumerate(value)) + b"]"


def encode(state: dict, known: frozenset = frozenset()) -> tuple[bytes, dict]:
    """(JSON bytes of `state` with the parts in `known` written as 0, the `delta` member)."""
    # Module-level helpers avoid a recursive closure cycle retaining each request's
    # known hashes and delta paths until cyclic garbage collection runs.
    refs: list = []
    keys: list = []

    if not (type(state) is dict and _splittable(state)):
        return fj.dumps_body(state), dict(refs=refs, keys=keys)
    return _members(state, [], 1, known, refs, keys), dict(refs=refs, keys=keys)


# ---- the page's side, in Python (tests and scripts; public/js/api.js inflate() is the real one) ----------

class Holder:
    """What a page keeps between answers: hash -> part, and the named parts inside each split part
    (so a part reused whole still lends its own named parts to a later answer)."""

    def __init__(self):
        self.parts: dict = {}
        self.kids: dict = {}

    def known(self) -> str:
        return "".join(self.parts)

    def take(self, state, delta: dict | None):
        """Fill the 0 placeholders of an answer's state from this holder and keep the new parts.
        Returns the whole state. A full answer (no delta) empties the holder."""
        if delta is None:
            self.parts, self.kids = {}, {}
            return state
        parts, kids = {}, {}

        def carry(h):
            if h in parts:
                return
            parts[h] = self.parts[h]
            for k in self.kids.get(h, ()):
                carry(k)
            if h in self.kids:
                kids[h] = self.kids[h]

        def at(path):
            node = state
            for k in path:
                node = node[k]
            return node

        for path, h in delta["refs"]:
            if h not in self.parts:
                raise KeyError(h)
            parent = at(path[:-1])
            if parent[path[-1]] != 0:
                raise ValueError(path)
            parent[path[-1]] = self.parts[h]
            carry(h)
        named = {}
        for path, h in delta["keys"]:
            parts[h] = at(path)
            named[tuple(path)] = h
        for path, h in [*delta["refs"], *delta["keys"]]:
            p = tuple(path)[:-1]
            while p and p not in named:
                p = p[:-1]
            if p:
                kids.setdefault(named[p], []).append(h)
        self.parts, self.kids = parts, kids
        return state
