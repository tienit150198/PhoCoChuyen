"""Since 05/10, new rounds use server chance draws in fair.apply. These timing
functions animate the aim and judge only legacy rounds already in progress.

💍 Ném vòng cổ chai at the fair: a timing game that earns xu without a stake. Pure functions; the commands, the
reward and the save are in game/fair.py, the stall in public/js/v4/fair.js (which draws the same numbers).

A round: BOTTLES bottles stand on a shelf at x (0..100); a ring swings over them, back and forth, x(t) a triangle wave
of period `period` ms starting at `phase`. The player has RINGS throws: each lands where the ring is at that moment
(milliseconds since the round started, on the player's clock). A throw within TOL of a bottle rings it (owner 03/10:
one bottle can take several rings).

The server draws the round from a seed and judges the throw times the client sends, against the same formula; they
must be increasing, at least GAP ms apart and not later than the time the server has seen pass (plus a little for the
network). A script could still aim perfectly: the reward is small (game/fair.py), like any
timing game in a browser.
"""
from __future__ import annotations

import random

BOTTLES = 5
RINGS = 5
TOL = 4.5            # in the 0..100 track: the bottle neck's half width
GAP = 250            # ms between two throws at least
SLACK = 1500         # ms: the client's clock may run this much ahead of what the server has seen
TTL = 3 * 60 * 1000  # ms: a round can be finished this long after it started
PERIOD = (2300, 2900)


def params(rs: int) -> dict:
    """The round drawn from its seed: bottle positions, the swing's period (ms) and phase (0..1)."""
    r = random.Random(f'fair-ring|{rs}')
    xs = [round(10 + 20 * i + r.uniform(-4, 4), 1) for i in range(BOTTLES)]
    return dict(xs=xs, period=r.randint(*PERIOD), phase=round(r.random(), 3))


def x_at(p: dict, t: int) -> float:
    """Where the ring is at `t` ms (0..100): the same arithmetic as ringX in public/js/v4/fair.js."""
    u = (t / p['period'] + p['phase']) % 1.0
    return 100.0 * (1.0 - abs(2.0 * u - 1.0))


def judge(p: dict, taps: list[int]) -> list[int]:
    """For each throw: the bottle it rang (index), or -1. A bottle can be rung more than once."""
    out = []
    for t in taps:
        x = x_at(p, t)
        out.append(next((i for i, bx in enumerate(p['xs']) if abs(x - bx) <= TOL), -1))
    return out


def taps_ok(taps: object, elapsed_ms: int) -> bool:
    """RINGS increasing throw times, GAP apart, none later than the server allows."""
    if not isinstance(taps, list) or len(taps) != RINGS or not all(type(t) is int for t in taps):
        return False
    if taps[0] < 0 or any(b - a < GAP for a, b in zip(taps, taps[1:])):
        return False
    return taps[-1] <= min(TTL, elapsed_ms + SLACK)


def land(p: dict, taps: list[int], n: int) -> list[int]:
    """A chance round's n rings, placed where they can be drawn honestly: the n throws aimed closest to a bottle ring
    that nearest bottle, the others miss. The count n is the server's draw; this only decides which rings and bottles,
    so the animation lands each ring next to where the player let it go (players: "ném trúng mà không vào")."""
    near = []
    for i, t in enumerate(taps):
        x = x_at(p, t)
        b = min(range(len(p['xs'])), key=lambda k: abs(x - p['xs'][k]))
        near.append((abs(x - p['xs'][b]), i, b))
    out = [-1] * len(taps)
    for _, i, b in sorted(near)[:max(0, min(n, len(taps)))]:
        out[i] = b
    return out
