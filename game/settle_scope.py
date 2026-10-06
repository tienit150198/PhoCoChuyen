"""Which parts of a career a command changed, so serialize re-validates only those (phase-0 W0a).

storage.serialize(known=...) re-validates every career whose digest moved. Server-time settlement
(business.settle: staff orders, wages, the cash book) moves many careers on every command, even a
no-op `settings`, and validate_career walks the whole record each time: every task regenerated
from content, every review, chat, journal line, album photo and cash-book row.

Before the command (snapshot), the JSON of every candidate career is cut into pieces: each
top-level value, each value of c["ops"] as "ops.<key>" and each value of c["ops"]["finance"] as
"ops.finance.<key>". The pieces put back together are the career's JSON exactly (orjson writes a
dict as {"key":value,...}), so the snapshot of a career is used only if that JSON has the career's
stored digest (check.careers: the record that passed validation with this build). After the
command (serialize), a moved career is cut again (its JSON for the save is that assembled text,
byte for byte fj.dumps_raw(c)) and validate_career gets a Same:
* the pieces that are byte for byte the same: the checks that read only them are skipped
  (engine.validate_career, operations.validate);
* prefix["ops.finance.ledger"] = n when the cash book only grew: its first n rows are byte for
  byte the stored ones (the old list's text without its "]", then a ","), so only the new rows
  are checked;
* nullfree: top-level keys (and "ops.<key>") whose JSON has no `null`. orjson writes NaN and
  Infinity as null, so those values cannot hold one and _finite skips them.
A career without a usable snapshot is validated in full, as before.

Byte equality of the JSON is the proof the storage layer already uses for a whole career (a
career whose text did not move is not validated at all): the stored text of those pieces is
exactly the text that passed.

Candidates: the acting and current careers, and the careers whose staff work is due now (the
ones business.settle changes). Without orjson nothing is snapshotted.
"""
from __future__ import annotations

import hashlib
import time

from . import fastjson as fj

LEDGER = 'ops.finance.ledger'
_COUNT = '#' + LEDGER
_KEY: dict = {}


class Same(frozenset):
    """Piece names of a career that did not change (see the module doc)."""
    __slots__ = ('prefix', 'nullfree')

    def __new__(cls, names=(), prefix=None, nullfree=frozenset()):
        out = super().__new__(cls, names)
        out.prefix = prefix or {}
        out.nullfree = nullfree
        return out


def _key(k: str) -> bytes:
    b = _KEY.get(k)
    if b is None:
        b = fj.dumps_raw(k) + b':'
        if len(_KEY) < 4096:
            _KEY[k] = b
    return b


def _join(parts) -> bytes:
    return b'{' + b','.join(parts) + b'}'


def _cut(d) -> bool:
    """A dict whose keys are text that cannot be mistaken for a piece name ("a.b", "#a")."""
    return type(d) is dict and all(type(k) is str and '.' not in k and k[:1] != '#' for k in d)


def pieces(c) -> tuple[dict, bytes] | None:
    """({piece name: JSON bytes}, the career's JSON assembled from them = fj.dumps_raw(c)), or None
    when the record cannot be cut (not a dict, a key that is not text, a value json refuses)."""
    if not _cut(c):
        return None
    out = {}
    parts = []
    try:
        for k, v in c.items():
            if k == 'ops' and _cut(v):
                sub = []
                for x, y in v.items():
                    if x == 'finance' and _cut(y):
                        fin = []
                        for f, z in y.items():
                            b = out['ops.finance.' + f] = fj.dumps_raw(z)
                            fin.append(_key(f) + b)
                        b = _join(fin)
                        if type(y.get('ledger')) is list:
                            out[_COUNT] = len(y['ledger'])
                    else:
                        b = fj.dumps_raw(y)
                    out['ops.' + x] = b
                    sub.append(_key(x) + b)
                b = _join(sub)
            else:
                b = fj.dumps_raw(v)
            out[k] = b
            parts.append(_key(k) + b)
    except ValueError:  # NaN/Infinity next to something orjson refuses: serialize raises it as before
        return None
    return out, _join(parts)


def _candidate(c, cid, acting, now) -> bool:
    """The acting or current career, or one whose staff work is due: workplace_business.due on that
    career alone (what makes business.settle change it). A career that moves anyway (a staff
    event, a reconcile) is validated in full, as before: only a little slower, never less."""
    if cid in acting:
        return True
    from . import workplace_business as wb
    try:
        return wb.due({'careers': {cid: c}}, now)
    except Exception:  # noqa: BLE001 - a malformed record: no snapshot, the full validation decides
        return False


def snapshot(raw: dict, known: dict, career=None) -> dict:
    """{cid: pieces} of the candidate careers whose current JSON has their stored, validated digest."""
    if not fj.FAST or type(known) is not dict:
        return {}
    careers = raw.get('careers')
    if type(careers) is not dict:
        return {}
    acting = {career, raw.get('current')}
    now = time.time()
    snap = {}
    for cid, c in careers.items():
        d = known.get(cid)
        if type(d) is not str or type(c) is not dict or not _candidate(c, cid, acting, now):
            continue
        cut = pieces(c)
        if cut is None:
            continue
        out, whole = cut
        if hashlib.blake2b(whole, digest_size=10).hexdigest() != d:
            # the stored digest is of json's text: orjson writes a few floats differently (fj.canonical)
            if not fj._float_format_differs(whole):
                continue
            try:
                exact = fj.canonical(whole, c)
            except ValueError:
                continue
            if hashlib.blake2b(exact, digest_size=10).hexdigest() != d:
                continue
        snap[cid] = out
    return snap


def same(before: dict, c) -> tuple[Same, bytes | None]:
    """(what of c is byte for byte `before`, c's JSON = fj.dumps_raw(c)), or (Same(), None) if c
    cannot be cut."""
    cut = pieces(c)
    if cut is None:
        return Same(), None
    out, whole = cut
    names = frozenset(k for k, b in out.items() if k[0] != '#' and before.get(k) == b)
    prefix = {}
    old, new = before.get(LEDGER), out.get(LEDGER)
    if LEDGER not in names and old and new and len(old) > 2 and before.get(_COUNT) \
            and new.startswith(old[:-1]) and new[len(old) - 1:len(old)] == b',':
        prefix[LEDGER] = before[_COUNT]
    nullfree = frozenset(k for k, b in out.items() if k[0] != '#' and k.count('.') < 2 and b'null' not in b)
    return Same(names, prefix, nullfree), whole
