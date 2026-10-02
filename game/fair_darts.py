"""🎯 Phóng phi tiêu at the fair (owner 03/10): a small-stake luck stall. Pure functions; the command, the wallet, the
points and the save are in game/fair.py (fair_dart), the stall in public/js/v4/fair-darts.js.

The player picks a stake (STAKES), aims a swinging crosshair at the board and throws. The aim only says where the dart
heads: whether it sticks in the coloured rings (WIN_R, a win: the stake back plus as much again) or in the straw ring
or off the board (the stake is lost) is decided on the server from game.fair._rng with win_p(today's fair net):
generous while the player is not far ahead today, less so once they are (owner: "~70 % while the day's net is under
+2000 xu, down to 45 % at +5000 and beyond"). Nothing the client sends decides a result; the landing point is then
drawn near the aim and pushed in or out of the coloured rings to match ("gió hội chợ thổi lệch").

Board units: the centre is (0, 0), the board's edge is at BOARD_R; the client draws the same rings.
"""
from __future__ import annotations

import math

STAKES = (2, 5, 10, 20, 50)
BULL_R = 6                     # hồng tâm
RINGS = (6, 20, 40, 60)        # hồng tâm, vàng, đỏ, xanh: the coloured rings, a win
WIN_R = 60
BOARD_R = 100                  # 60..100: the straw ring, a miss; beyond: off the board, a miss too
OFF_R = 116                    # the farthest a dart is drawn
AIM_MAX = 120                  # the aim the client may send, per axis
SPREAD = 14                    # the throw's scatter around the aim (a gauss sigma, board units)
# the odds by today's fair net: the shared taper (game.fair.odds) with darts' own, lower ends
P_HI, P_LO = 0.40, 0.30         # owner 03/10 01:20: "phi tiêu khó trúng hơn" (was 0.70, 0.45)
PT_HIT = 1                     # fair points for a dart in the coloured rings


def win_p(net: int) -> float:
    """The odds of a win given the player's fair net today: the taper of bầu cua and xóc đĩa (game.fair.odds), from P_HI
    down to P_LO."""
    from .fair import odds
    return odds(net, P_HI, P_LO)


def aim_ok(aim: object) -> bool:
    return (isinstance(aim, list) and len(aim) == 2 and all(type(v) is int for v in aim)
            and all(-AIM_MAX <= v <= AIM_MAX for v in aim))


def ring_of(x: float, y: float) -> int:
    """0: hồng tâm, 1..3: the coloured rings, 4: the straw ring, 5: off the board."""
    r = math.hypot(x, y)
    for i, edge in enumerate(RINGS):
        if r <= edge:
            return i
    return 4 if r <= BOARD_R else 5


def land(aim: list, win: bool, rng) -> tuple[float, float]:
    """Where the dart sticks: near the aim, then in the coloured rings for a win, outside them for a miss."""
    x, y = aim[0] + rng.gauss(0, SPREAD), aim[1] + rng.gauss(0, SPREAD)
    r = math.hypot(x, y)
    a = math.atan2(y, x) if r > 0.5 else rng.uniform(-math.pi, math.pi)
    if win and r > WIN_R - 2:
        r = rng.uniform(WIN_R * 0.55, WIN_R - 3)      # the wind blew it in
    elif not win and r < WIN_R + 2:
        r = rng.uniform(WIN_R + 4, BOARD_R + 10)      # and out
    r = min(r, OFF_R)
    x, y = round(r * math.cos(a), 1), round(r * math.sin(a), 1)
    ring = ring_of(x, y)
    if win != (ring <= 3):   # rounding on an edge: nudge it back to the side drawn
        k = (WIN_R - 4 if win else WIN_R + 4) / max(1.0, math.hypot(x, y))
        x, y = round(x * k, 1), round(y * k, 1)
    return x, y
