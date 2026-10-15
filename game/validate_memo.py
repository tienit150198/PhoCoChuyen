"""Career checks this worker already ran on the very same JSON (perf 15/10, next to game/settle_scope.py).

storage.serialize_bytes(known=...) re-validates every career a command moved (engine.validate_career), in
full unless SCOPED_CAREER_VALIDATION=1. Server-time settlement moves each career with working staff on
almost every command and on every staff poll (business_sync), yet most of such a record is the same JSON
as at the previous command: the jobs on the desk, the reviews, the journal, the memories, the chats. On a
large save those loops are about half of the validation of a moved career.

The checks of one task, of one post (both loops over c["feed"]), and of the whole journal, memories and
chats read only that value, its career id and the fixed content: no clock, no randomness, nothing else of
the save, and they change nothing. So a value whose JSON is byte for byte one that passed those checks with
this build passes them again: the proof the storage layer already uses for a whole career (check.careers)
and settle_scope for a piece of one. This module remembers, per process, a keyed BLAKE2b digest of such
JSON (orjson's bytes), per career id and kind, once its checks passed.

Safety:
* used only while active() (storage.serialize_bytes validating the careers a command moved). validate_state
  never uses it: imports, a build's first command on a save and the periodic full check (FULL_EVERY) run
  every check, as before;
* a value is remembered only after its checks passed and only if its JSON did not change while they ran;
* NaN/Infinity (orjson writes null) are still refused by the career's _finite check; whenever validation
  with the memo raises, storage runs the full validation again, so a refused command gives exactly the
  message it gave before;
* bounded: at most LIMIT digests (two generations, the older one dropped as a whole), about 80 bytes each.
VALIDATE_MEMO=0 turns it off; VALIDATE_MEMO_ENTRIES sets LIMIT. Without orjson it is off.
"""
from __future__ import annotations

import contextlib
import contextvars
import hashlib
import os
import secrets

from . import fastjson as fj

try:
    LIMIT = max(0, int(os.environ.get('VALIDATE_MEMO_ENTRIES', '200000') or 0))
except ValueError:
    LIMIT = 200000
ON = fj.FAST and LIMIT > 0 and os.environ.get('VALIDATE_MEMO', '1').strip().lower() not in ('0', 'false', 'no', 'off')
_KEY = secrets.token_bytes(16)   # per process: nobody can make two JSON texts share a digest on purpose
_ACTIVE = contextvars.ContextVar('validate_memo', default=False)
_new: dict = {}                  # (career id, kind) -> set of digests (current generation)
_old: dict = {}                  # the previous generation
_count = [0]


@contextlib.contextmanager
def active():
    """Within: engine.validate_career skips the checks of values it finds here (storage.serialize_bytes)."""
    token = _ACTIVE.set(ON)
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def on() -> bool:
    return _ACTIVE.get() is True


def digest(value) -> bytes | None:
    """Keyed digest of value's JSON; None when orjson cannot write it (it is then checked as usual)."""
    try:
        data = fj.orjson.dumps(value)
    except TypeError:
        return None
    return hashlib.blake2b(data, digest_size=16, key=_KEY).digest()


def digests(values) -> list:
    return [digest(v) for v in values]


def known(cid: str, kind: str, d) -> bool:
    if d is None:
        return False
    k = (cid, kind)
    s = _new.get(k)
    if s is not None and d in s:
        return True
    s = _old.get(k)
    return s is not None and d in s


def remember(cid: str, kind: str, pairs) -> None:
    """Remember values that just passed their checks: pairs of (digest taken before the checks, value).
    A value whose JSON moved while they ran is left out."""
    global _new, _old
    add = [d for d, v in pairs if d is not None and digest(v) == d and not known(cid, kind, d)]
    if not add:
        return
    if _count[0] + len(add) > LIMIT // 2:
        _old, _new = _new, {}
        _count[0] = 0
    _new.setdefault((cid, kind), set()).update(add)
    _count[0] += len(add)


def clear() -> None:
    global _new, _old
    _new, _old = {}, {}
    _count[0] = 0
