"""tree_copy: deep copy of JSON-shaped data (saves, public views), without imports of
the game modules so that any of them can use it."""
from __future__ import annotations
import copy

_SCALARS = (str, int, float, bool, type(None))


def tree_copy(x):
    """Deep copy of a JSON-shaped save (dicts, lists, scalars), about 4x faster than
    copy.deepcopy. Anything else (tuples, sets...) still goes through copy.deepcopy.
    Unlike deepcopy it does not keep two references to one object shared: saves
    parsed from JSON never have any."""
    t = type(x)
    if t is dict:
        return {k: (v if type(v) in _SCALARS else tree_copy(v)) for k, v in x.items()}
    if t is list:
        return [v if type(v) in _SCALARS else tree_copy(v) for v in x]
    if t in _SCALARS:
        return x
    return copy.deepcopy(x)
