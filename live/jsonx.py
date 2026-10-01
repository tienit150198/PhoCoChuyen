"""JSON for frames: orjson when it is installed (production vendors it), else the standard library.
dumps() returns UTF-8 bytes (sent as a text frame), loads() accepts str or bytes."""
from __future__ import annotations

import json

try:
    import orjson
except ImportError:  # pragma: no cover - the standard library does it, only slower
    orjson = None

_STD = json.JSONEncoder(ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode


def dumps(obj) -> bytes:
    if orjson is not None:
        return orjson.dumps(obj)
    return _STD(obj).encode()


def loads(data):
    if orjson is not None:
        return orjson.loads(data)
    return json.loads(data)
