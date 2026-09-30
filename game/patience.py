"""Customer patience: one knob for how long waiting customers put up with waiting.

PATIENCE_FACTOR 1.2 = about +20% more waiting before a patience bar empties or a
customer gives up. It is applied in two ways, both never harsher than before:

* `waits(c, t)` thins the per-turn waiting drain: on about 1 turn in 6 (factor 1.2)
  a waiting customer does not mind, so that turn costs no patience. The pick is a
  stable hash of (task, turn): no new saved field, same answer on every replay.
* `longer(n)` stretches a waiting budget counted in turns or minutes (a reply SLA,
  a queue slot, a cancel grace), rounded up.

One-off patience hits for a mistake, a rude reply or an event choice stay as they are.
The first-jobs learning freeze lives in engine.apply_action (LEARNING_TASKS), unchanged.
"""
from __future__ import annotations
import hashlib
import math
import os


def _factor(raw: str | None) -> float:
    try:
        v = float(raw) if raw else 1.2
    except ValueError:
        v = 1.2
    return min(2.0, max(1.0, v))  # never less patient than the original tuning


PATIENCE_FACTOR = _factor(os.environ.get('PATIENCE_FACTOR'))


def longer(n: int) -> int:
    """A waiting budget (turns or minutes), stretched by the factor and rounded up: never shorter."""
    return max(n, math.ceil(n * PATIENCE_FACTOR - 1e-9))


def waits(c: dict, t: dict) -> bool:
    """True when this turn's waiting drain applies to task `t` (False = the customer lets it slide)."""
    rest = 1 - 1 / PATIENCE_FACTOR
    if rest <= 0:
        return True
    h = int(hashlib.sha256(f'{t.get("id")}|{c.get("turn", 0)}'.encode()).hexdigest()[:8], 16)
    return h / 0x100000000 >= rest


def drain(c: dict, t: dict, loss: int) -> int:
    """The waiting loss for `t` this turn: `loss`, or 0 on a turn the customer lets slide."""
    return loss if loss > 0 and waits(c, t) else 0
