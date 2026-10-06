"""Owner 05/10 follow-up: new knife levels use real collisions again. Both client
and server replay the same schedule/tap times; no chance draw can turn a clean
board into a loss. New levels use the gentler 135% schedule. The simulation figures
below describe the original 100% schedule, not the current 135% setting.

🗡️ Phóng dao at the fair (owner 03/10, replacing the 🎯 phi tiêu stall: "càng ngày càng khó, chơi 1 màn xong chọn chơi
tiếp hoặc dừng, chơi tiếp mà thua thì thua hết, dừng thì nhận thưởng hiện tại. Lâu lâu thì hiển thị "màn sau x2""). Pure
functions; the commands, the wallet, the Sổ ví row and the save are in game/fair.py (fair_kn_*), the stall in
public/js/v4/fair-knife.js (which draws the same numbers).

A run: the player pays a STAKES stake, then plays level 1. A wooden board turns (schedule: drawn from a seed the
server picks when the level starts); each tap throws a knife from the bottom (IMPACT) that sticks where the board is
FLY_MS later. A knife closer than GAP degrees to a knife already in the board (DIFF's pre-stuck ones or the player's)
bounces off: the level, the stake and the prize so far are lost. All `need` knives in: the level is cleared, and
the player chooses: "Dừng" (prize(): LADDER tenths of the stake, plus the 🔥 x2 bonus) or "Chơi tiếp" (the next,
harder level, everything riding on it). From level 2 on, X2_P of the levels (never two in a row) are 🔥 x2, told
before the choice: that level's step of the ladder pays twice. Level LEVELS cleared: paid by itself (phá đảo).

The ladder (× the stake, "Dừng" after level k): 1.1 1.2 1.6 2.1 2.8 3.6 4.6 6 7.8 10 (in xu: prizes(); every level
and every x2 is worth at least 1 xu more, also at the 2 and 5 xu stakes). Until 03/10 its top was 3.9 5.4 8 12 19: a
practised thumb got 11.6× back for clearing all ten levels; the xu sinks (docs/ECONOMY_SINKS.md) trimmed levels 6..10
only, so the sensible play below (stop after 2..5) pays the same. Harder each level: more knives,
a faster board that more and more often speeds up, slows down, stops short or turns back (DIFF). On a day the
player's fair net is far up the board is up to HEAT_MAX levels harder (heat(), like the luck stalls' taper).

Honesty: the server draws each level's seed when the level starts, so nothing of a level is known before. The client
gets the schedule, draws angle_at() and sends the throw times (ms since the level started on its clock: increasing,
MIN_TAP apart, not after LEVEL_MS nor later than the server has seen pass plus SLACK); the server throws them again
with judge() and decides (nothing the client says about a result counts). A level is lost if its throws do not come
within LEVEL_MS (+ SLACK): a client cannot hold back a losing throw to keep the prize. A cleared level's choice waits
until the end of that Vietnam day (a closed page, a reload: the run is still there); after that the prize is paid as
if "Dừng" (game/fair.py settle). A script could still throw perfectly, as in any timing game in a browser.

The table: scripts/sim_fair_knife.py (3 000 levels a level, 30 000 runs a stake for the returns). Its simulated
players watch the board REACT ms late, wait for a clear spot and are off by a gauss of `sigma` ms; "average" is
sigma 38 ms, "weak" 45, "good" 22 (a practised thumb).
  Clear rate by level (heat 0):  1    2    3    4    5    6    7    8    9    10
    weak                         75%  72%  67%  67%  66%  60%  58%  52%  54%  49%
    average                      85%  82%  78%  77%  73%  71%  69%  66%  63%  60%
    good                        100%  98%  97%  96%  94%  94%  93%  91%  87%  86%
  Return per xu staked (the 4 stakes' rounding and the x2 levels included), "Dừng" after level K:
    K =                          1    2    3    4    5    6    7    8    9    10
    average                     .94  .89  .95  .99  .97  .90  .81  .70  .57  .45
    weak                        .83  .68  .63  .57  .51  .40  .31  .22  .15  .09
    good                       1.11 1.25 1.64 2.14 2.71 3.30 3.97 4.78 5.47 6.04
  A sensible player (stops after 2..5 levels, plays on into a 🔥 x2 one): average .98, weak .61, good 2.00 (a skill
  game: a good thumb wins); one who goes deep (stops after 5..8): average .86, good 3.79 (was .99 and 4.53). On a hot day (heat 1 / 2 / 3) the sensible average player gets .84 / .74 / .69 back and
  the good one 1.89 / 1.79 / 1.76.
"""
from __future__ import annotations

import bisect
import random

STAKES = (2, 5, 10, 20, 50, 100, 200, 500, 1000)
LEVELS = 10
# After clearing level k (1..LEVELS), "Dừng" pays LADDER[k - 1] tenths of the stake (rounded, half up), and at least
# 1 xu more than after level k - 1 (prizes(): at 2 and 5 xu the rounding would make a step worth nothing).
LADDER = (11, 12, 16, 21, 28, 36, 46, 60, 78, 100)   # 03/10: levels 6..10 were 39 54 80 120 190
X2_P = .25                     # the next level (2..LEVELS) is a 🔥 x2 one: its step pays double; never two in a row
GAP = 10.0                     # degrees: two knives whose centres are closer than this on the rim touch (a loss)
DRAW_W = 11.0                  # degrees: how wide a blade is drawn at the rim (wider than GAP: a near miss looks close)
FLY_MS = 80                    # a tap at t ms sticks where the board is at t + FLY_MS
IMPACT = 90.0                  # where knives hit, degrees on the screen (0: right, 90: the bottom, clockwise)
MIN_TAP = 120                  # ms between two throws at least (the knife in the air sticks first)
LEVEL_MS = 60_000              # a level is finished within this (taps later than this do not count)
SLACK = 4000                   # ms: the network's share between the player's last tap and the server seeing it
PRE_SEP = 3 * GAP              # the knives already in the board at a level's start are this far apart at least
CHANCE_DIFFICULTY = 135        # previous chance release; its saved boards still replay exactly
SKILL_DIFFICULTY = 135         # keep the gentle speed/count when restoring skill play
# A level by its difficulty d (the level number, plus today's heat, see heat()): knives to throw, knives already
# stuck, the board's base speed (degrees a second) and how often a stretch of its turning is a 'wave' (speeds up or
# slows down smoothly), a 'rev' (turns back abruptly) or a 'stut' (stops short, then bursts on, sometimes the other
# way); the other stretches keep about the same speed.
DIFF = {
    1: (7, 1, 160, (0, 0, 0)),
    2: (7, 1, 170, (.45, .05, 0)),
    3: (7, 1, 175, (.4, .15, .03)),
    4: (7, 1, 175, (.35, .18, .05)),
    5: (7, 1, 180, (.35, .22, .06)),
    6: (7, 2, 165, (.3, .2, .08)),
    7: (7, 2, 165, (.3, .22, .1)),
    8: (7, 2, 175, (.3, .27, .11)),
    9: (6, 2, 200, (.25, .38, .17)),
    10: (6, 2, 210, (.25, .42, .2)),
    11: (7, 3, 205, (.25, .4, .2)),      # 11..13: the last levels on a hot day (heat)
    12: (7, 3, 215, (.2, .45, .2)),
    13: (7, 3, 225, (.2, .5, .22)),
}
HEAT_MAX = 3


def heat(net: int) -> int:
    """How many levels harder the board is given the player's fair net today (the stall's taper, like game.fair.odds
    for the luck stalls: "người ta thắng khoảng 2000 xu thì cho thua dần bớt đi"): 0 up to TAPER_FROM, then one more
    every 1000 xu, at most HEAT_MAX."""
    from .fair import TAPER_FROM
    return 0 if net <= TAPER_FROM else min(HEAT_MAX, 1 + (net - TAPER_FROM - 1) // 1000)


_PRIZES: dict[int, tuple[int, ...]] = {}


def prizes(stake: int) -> tuple[int, ...]:
    """The ladder in xu for a stake: LADDER tenths rounded half up, each level at least 1 xu over the one before
    (2 xu: 2 3 4 5 6 7 9 12 16 20; 5 xu: 6 7 8 11 14 18 23 30 39 50; 10 and 20 xu: exactly the tenths)."""
    if stake not in _PRIZES:
        out, p = [], 0
        for m in LADDER:
            p = max((stake * m + 5) // 10, p + 1)
            out.append(p)
        _PRIZES[stake] = tuple(out)
    return _PRIZES[stake]


def prize(stake: int, cleared: int, bonus: int = 0) -> int:
    """What "Dừng" pays after `cleared` levels (0: nothing, the stake was lost or the run never cleared a level), plus
    the x2 levels' bonus."""
    if cleared <= 0:
        return 0
    return prizes(stake)[cleared - 1] + bonus


def x2_bonus(stake: int, level: int) -> int:
    """A 🔥 x2 level's extra: its step once more (level ≥ 2; at least 1 xu, see prizes())."""
    return prize(stake, level) - prize(stake, level - 1)


# ---------------------------------------------------------------- the board's turning
def schedule(seed: int, level: int, hot: int = 0, difficulty: int = 100) -> dict:
    """A level drawn from its seed: the knives to throw (need), the ones already stuck (pre, board degrees), the
    starting angle th0 and the turning, segs: [[ms, degrees a second, ramp ms], …] covering LEVEL_MS. The client gets
    exactly this and draws angle_at(); the server judges taps with the same."""
    d = max(1, min(max(DIFF), level + hot))
    need, n_pre, v, (p_wave, p_rev, p_stut) = DIFF[d]
    r = random.Random(f'fair-knife|{seed}|{level}|{hot}')
    sign = r.choice((1, -1))
    segs, total = [], 0
    while total < LEVEL_MS + SLACK:
        x = r.random()
        if x < p_rev:   # turns back (most of the time) abruptly
            if r.random() < .75:
                sign = -sign
            seg = [r.randint(1200, 2800), sign * round(v * r.uniform(.85, 1.25)), r.randint(110, 180)]
        elif x < p_rev + p_stut:   # a short stop, then a burst, sometimes the other way
            segs.append([r.randint(220, 500), sign * round(v * .06), 140])
            total += segs[-1][0]
            if r.random() < .4:
                sign = -sign
            seg = [r.randint(900, 1800), sign * round(v * r.uniform(1.0, 1.35)), 160]
        elif x < p_rev + p_stut + p_wave:   # faster or slower, smoothly
            seg = [r.randint(1100, 2400), sign * round(v * r.uniform(.45, 1.5)), r.randint(450, 700)]
        else:   # about the same speed
            seg = [r.randint(1500, 3000), sign * round(v * r.uniform(.9, 1.1)), 500]
        segs.append(seg)
        total += seg[0]
    pre: list[float] = []
    while len(pre) < n_pre:
        a = round(r.uniform(0, 360), 1)
        if all(dist(a, b) >= PRE_SEP for b in pre):
            pre.append(a)
    if difficulty in (135, 150):
        need = (need * difficulty + 99) // 100
        segs = [[ms, speed * (difficulty / 100), ramp] for ms, speed, ramp in segs]
    return dict(lv=level, hot=hot, d=d, need=need, pre=pre, th0=round(r.uniform(0, 360), 1), segs=segs)


def _table(sc: dict) -> list:
    """Per segment: (start ms, angle there, speed there deg/ms) — cached on the schedule."""
    tab = sc.get('_tab')
    if tab is None:
        tab, t, th, u = [], 0, float(sc['th0']), 0.0
        first = True
        for ms, w, ramp in sc['segs']:
            w = w / 1000.0
            if first:   # the board is already turning at its first speed when the level starts
                u, first = w, False
            tab.append((t, th, u, w, min(ramp, ms)))
            th += _turn(u, w, min(ramp, ms), ms)
            t += ms
            u = w
        sc['_tab'] = tab
        sc['_starts'] = [x[0] for x in tab]
    return tab


def _turn(u: float, w: float, ramp: int, tau: float) -> float:
    """Degrees turned tau ms into a segment whose speed goes from u to w (deg/ms) over `ramp` ms, then stays."""
    if ramp <= 0:
        return w * tau
    if tau <= ramp:
        return u * tau + (w - u) * tau * tau / (2 * ramp)
    return u * ramp + (w - u) * ramp / 2 + w * (tau - ramp)


def angle_at(sc: dict, t: float) -> float:
    """The board's angle (degrees, any size) t ms after the level started: the same arithmetic as angleAt in
    public/js/v4/fair-knife.js."""
    tab = _table(sc)
    i = max(0, bisect.bisect_right(sc['_starts'], t) - 1)
    t0, th, u, w, ramp = tab[i]
    return th + _turn(u, w, ramp, t - t0)


def speed_at(sc: dict, t: float) -> float:
    """The board's speed (deg/ms, signed) at t ms (the simulated player watches it; the game does not need it)."""
    tab = _table(sc)
    i = max(0, bisect.bisect_right(sc['_starts'], t) - 1)
    t0, _, u, w, ramp = tab[i]
    tau = t - t0
    return w if ramp <= 0 or tau >= ramp else u + (w - u) * tau / ramp


def dist(a: float, b: float) -> float:
    """Degrees between two places on the rim (0..180)."""
    x = abs(a - b) % 360.0
    return 360.0 - x if x > 180.0 else x


def lands(sc: dict, tap: int) -> float:
    """Where on the board (board degrees 0..360) a knife thrown at `tap` ms sticks."""
    return (IMPACT - angle_at(sc, tap + FLY_MS)) % 360.0


def chance_positions(need: int, count: int) -> list[float]:
    """Display positions for chance mode; no collision is judged from the player's aim."""
    return [round(360 * i / need, 2) for i in range(min(need, count))]


def judge(sc: dict, taps: list[int]) -> tuple[list[float], int]:
    """Throw the taps in order: (the knives stuck, board degrees; the index of the throw that hit a knife, or -1).
    Throws after a hit or after the level's `need` do not count."""
    stuck: list[float] = []   # compared unrounded, like judge() in public/js/v4/fair-knife.js
    for i, t in enumerate(taps[:sc['need']]):
        a = lands(sc, t)
        if any(dist(a, b) < GAP for b in sc['pre'] + stuck):
            return [round(x, 2) for x in stuck], i
        stuck.append(a)
    return [round(x, 2) for x in stuck], -1


def taps_ok(taps: object, need: int, elapsed_ms: int) -> bool:
    """1..need increasing throw times (ms since the level started), MIN_TAP apart, none after LEVEL_MS nor later than
    the server has seen pass (plus SLACK for the network)."""
    if not isinstance(taps, list) or not 1 <= len(taps) <= need or not all(type(t) is int for t in taps):
        return False
    if taps[0] < 0 or any(b - a < MIN_TAP for a, b in zip(taps, taps[1:])):
        return False
    return taps[-1] <= min(LEVEL_MS, elapsed_ms + SLACK)


def public_schedule(sc: dict) -> dict:
    """What the client draws a level from (no cache keys)."""
    return {k: sc[k] for k in ('lv', 'need', 'pre', 'th0', 'segs')}
