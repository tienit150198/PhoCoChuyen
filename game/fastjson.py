"""Fast JSON: orjson (a C extension) when it is installed, else the standard library.

The game runs without it (standard library only); production vendors the manylinux wheel
into PYTHONPATH (scripts/vendor_orjson.sh). Every function here gives the same result
with or without orjson, except where noted:

* loads(text): json.loads. Anything orjson refuses (lone surrogates, 1e400, NaN tokens,
  nesting deeper than 1024) is parsed again by json.loads, so it accepts and returns
  exactly what json.loads does. One difference: an integer outside [-2**63, 2**64) comes
  back as a float from orjson. The game never writes one (validated counters stay far
  below; see test_fastjson), and dumps below never produces one through orjson.
* dumps_trusted(obj) -> bytes (= canonical(dumps_raw(obj), obj)): EXACTLY the UTF-8 of json.dumps(obj, ensure_ascii=False,
  separators=(",", ":")), byte for byte (the save text and its per-career digests in
  raw["check"] depend on it, see storage.serialize). Proven by test_fastjson: strings
  (every BMP code point, random astral text), ints, bools, None and floats are written
  identically, EXCEPT floats whose decimal exponent is -5..-9 (Python 1e-05 / 1e-06,
  orjson 0.00001 / 1e-6): those outputs are detected and written by json instead, as are
  ints beyond 64 bits, non-str keys and types orjson does not know. NaN/Infinity are NOT
  refused by orjson (it writes null): only for data already checked finite (a validated
  save, see storage.serialize). Without orjson they raise ValueError, as json does.
* dumps_body(obj) -> bytes: an HTTP response body (compact, UTF-8, non-str keys as json
  would write them). NaN/Infinity become null instead of raising.
* dumps(obj) -> str: json.dumps(obj, ensure_ascii=False) for stored text that is only
  ever parsed back (receipts): compact; NaN/Infinity written as json writes them.
"""
from __future__ import annotations
import json
import math

try:
    import orjson
except ImportError:  # the standard library does it all, only slower
    orjson = None

FAST = orjson is not None
SEPARATORS = (",", ":")
_DIGITS = b"0123456789"
_STD = json.JSONEncoder(ensure_ascii=False, allow_nan=True, separators=SEPARATORS).encode
_STD_STRICT = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=SEPARATORS).encode


def loads(text):
    """json.loads of a str or bytes (see the module doc)."""
    if orjson is not None:
        try:
            return orjson.loads(text)
        except orjson.JSONDecodeError:
            pass  # let json.loads decide: it accepts a few things orjson refuses, and raises the usual error
    return json.loads(text)


def _float_format_differs(out: bytes) -> bool:
    """orjson wrote a float whose text differs from Python's repr: exponent -5 is written
    positionally ("0.0000d..." instead of "d.dde-05") and exponents -6..-9 with one digit
    ("1e-6" instead of "1e-06"). A false alarm (the same bytes inside a string) only means
    json writes it."""
    i = out.find(b"e-")
    while i >= 0:
        if i and out[i - 1] in _DIGITS and out[i + 2:i + 3].isdigit() and not out[i + 3:i + 4].isdigit():
            return True
        i = out.find(b"e-", i + 2)
    i = out.find(b"0.0000")
    while i >= 0:
        if i == 0 or out[i - 1] in b":,[-":
            return True
        i = out.find(b"0.0000", i + 6)
    return False


def dumps_raw(obj) -> bytes:
    """orjson's UTF-8 JSON of obj (json's when orjson is missing or refuses obj): the bytes
    of json.dumps(obj, ensure_ascii=False, separators=(",", ":")) except, possibly, the text
    of floats with a decimal exponent of -5..-9 (see canonical). NaN/Infinity: null with
    orjson, ValueError without it."""
    if orjson is not None:
        try:
            return orjson.dumps(obj)
        except TypeError:  # ints beyond 64 bits, non-str keys, unknown types: json decides
            pass
    return _STD_STRICT(obj).encode()


def canonical(out: bytes, obj) -> bytes:
    """dumps_raw(obj) -> exactly json's bytes (the few floats orjson writes differently)."""
    return _STD_STRICT(obj).encode() if orjson is not None and _float_format_differs(out) else out


def dumps_trusted(obj) -> bytes:
    """UTF-8 of json.dumps(obj, ensure_ascii=False, separators=(",", ":")), byte for byte,
    for data already checked finite (with orjson, NaN/Infinity would be written as null)."""
    return canonical(dumps_raw(obj), obj)


def dumps_body(obj) -> bytes:
    """An HTTP JSON body (UTF-8, compact). NaN/Infinity are written as null."""
    if orjson is not None:
        try:
            return orjson.dumps(obj, option=orjson.OPT_NON_STR_KEYS)
        except TypeError:
            pass  # ints beyond 64 bits, unknown types: json writes them or raises the usual TypeError
    try:
        return _STD_STRICT(obj).encode()
    except ValueError:  # NaN/Infinity: null, as orjson writes them
        return _STD(_nulled(obj)).encode()


def _nulled(x):
    if type(x) is float:
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _nulled(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_nulled(v) for v in x]
    return x


def _finite(x) -> bool:
    """No NaN/Infinity anywhere in x."""
    if isinstance(x, float):
        return math.isfinite(x)
    if isinstance(x, dict):
        return all(_finite(v) for v in x.values())
    if isinstance(x, (list, tuple)):
        return all(_finite(v) for v in x)
    return True


def dumps(obj) -> str:
    """Compact json.dumps(obj, ensure_ascii=False) (NaN/Infinity written as NaN/Infinity, as
    json does by default) for text that is only parsed back with loads (receipts)."""
    if orjson is not None:
        try:
            out = orjson.dumps(obj)
        except TypeError:
            pass
        else:
            if b"null" not in out or _finite(obj):
                return out.decode()
    return _STD(obj)
