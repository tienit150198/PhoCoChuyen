"""🗡️ Phóng dao at the fair: a simulation of game/fair_knife.py (dev tool, the numbers in that module's docstring).

A simulated player watches the board as it was REACT ms ago, guesses where a knife thrown now would stick by carrying
that angle on at the speed it saw (right while the board keeps its speed, wrong when it turns back or stops in
between), throws when the guess is at least `calm` degrees clear of every knife (less picky the longer they wait),
and their thumb is off by a gauss of `sigma` ms. Each level is judged by fair_knife.judge, like the server does.

    python scripts/sim_fair_knife.py [levels per difficulty] [runs]
    python scripts/sim_fair_knife.py --table [levels per difficulty] [runs]   (docs/FAIR_HOUSE_EDGE.md's table)

Boards (BOARDS): 'old' (the 100% schedule this module's docstring describes), 'soft' (1.9.31: 115%, SOFT_GAP), 'ramp'
(1.9.32: soft + 5% a level), 'twist' (since: twist_schedule). The players see the board slow down or speed up (the
change of speed over the last SEE_ACC ms) and carry it on, stopping where a slowing board would stop.

Prints the clear rate per difficulty for each kind of player, then the return per xu staked (ladder, 🔥 x2 levels and
the rounding of each stake included) of a few ways to play: stop after level K, stop after K unless the next level is
x2, and the "sensible" player who stops somewhere in 2..5 and plays on into an x2 level.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game import fair_knife as kn   # noqa: E402

PLAYERS = {   # name: (sigma ms, react ms, calm degrees, patience ms)
    'weak': (45, 190, 6, 3000),
    'average': (38, 170, 7, 3500),
    'good': (22, 130, 10, 5000),
}
FRAME = 16
SEE_ACC = 80
BOARDS = {
    'old': lambda seed, lv, hot: kn.schedule(seed, lv, hot),
    'soft': lambda seed, lv, hot: kn.schedule(seed, lv, hot, kn.SOFT_DIFFICULTY),
    'ramp': lambda seed, lv, hot: kn.schedule(seed, lv, hot, kn.SOFT_DIFFICULTY, True),
    'twist': lambda seed, lv, hot: kn.twist_schedule(seed, lv, hot),
}


def guess_turn(sc: dict, seen: float, h: float) -> float:
    """Degrees the board will turn in the h ms after `seen`, as a player who saw its speed and its change of speed
    guesses it (a slowing board stops; what it does after that cannot be seen yet)."""
    w = kn.speed_at(sc, seen)
    a = (w - kn.speed_at(sc, seen - SEE_ACC)) / SEE_ACC if seen >= SEE_ACC else 0.0
    if a and w * a < 0 and -w / a < h:   # slowing down: it stops before the knife lands
        return -w * w / (2 * a)
    return w * h + a * h * h / 2


def play_level(sc: dict, who: tuple, rng: random.Random) -> bool:
    sigma, react, calm, patience = who
    taps: list[int] = []
    t = rng.randint(300, 900)
    ready = t
    while len(taps) < sc['need']:
        if t > kn.LEVEL_MS - 200:
            return False
        seen = t - react
        guess = (kn.IMPACT - (kn.angle_at(sc, seen) + guess_turn(sc, seen, react + kn.FLY_MS))) % 360.0
        stuck, _ = kn.judge(sc, taps)
        room = min((kn.dist(guess, b) for b in sc['pre'] + stuck), default=180.0) - sc.get('gap', kn.GAP)
        want = calm * max(.25, 1 - (t - ready) / patience)
        if room >= want:
            tap = max(round(t + rng.gauss(0, sigma)), (taps[-1] + kn.MIN_TAP) if taps else 0)
            taps.append(tap)
            _, hit = kn.judge(sc, taps)
            if hit >= 0:
                return False
            t = tap + kn.MIN_TAP + rng.randint(120, 400)
            ready = t
            continue
        t += FRAME
    return True


def clear_rates(n: int, hot: int = 0, seed: int = 1, board: str = 'old') -> dict:
    rng = random.Random(seed)
    make = BOARDS[board]
    out = {}
    for name, who in PLAYERS.items():
        row = []
        for lv in range(1, kn.LEVELS + 1):
            ok = sum(play_level(make(rng.getrandbits(31), lv, hot), who, rng) for _ in range(n))
            row.append(ok / n)
        out[name] = row
    return out


def returns(p: list[float], runs: int, rule, seed: int = 2) -> float:
    """Return per xu staked over `runs` runs per stake, with the clear rates p (per level) and a stop rule
    rule(cleared, next_is_x2, rng) -> True to stop."""
    rng = random.Random(seed)
    back = staked = 0
    for stake in kn.STAKES:
        for _ in range(runs):
            staked += stake
            cleared, bonus, x2 = 0, 0, False
            while True:
                if rng.random() >= p[cleared]:
                    break   # lost the level: everything goes
                cleared += 1
                if x2:
                    bonus += kn.x2_bonus(stake, cleared)
                if cleared == kn.LEVELS:
                    back += kn.prize(stake, cleared, bonus)
                    break
                x2 = not x2 and cleared + 1 >= 2 and rng.random() < kn.X2_P
                if rule(cleared, x2, rng):
                    back += kn.prize(stake, cleared, bonus)
                    break
    return back / staked


def script_return() -> float:
    """A script that clears every level (and so every x2 level it meets) and stops after the last."""
    p = [1.0] * kn.LEVELS
    return returns(p, 20000, lambda c, x, r: False)


def table(n: int, runs: int) -> None:
    """Per board: the clear rates (heat 0) and the returns of a player who stops after 2..5 or 5..8 levels."""
    for board in ('soft', 'ramp', 'twist'):
        rates = clear_rates(n, 0, board=board)
        print(f'board {board}')
        for name, p in rates.items():
            a = returns(p, runs, lambda c, x, r: c >= r.randint(2, 5) and not x)
            b = returns(p, runs, lambda c, x, r: c >= r.randint(5, 8) and not x)
            print(f'  {name:8}', ' '.join(f'{x:4.0%}' for x in p), f'| 2-5: {a:.2f}  5-8: {b:.2f}')
    print(f'script (clears every level): {script_return():.2f}')


def main() -> None:
    if sys.argv[1:2] == ['--table']:
        table(int(sys.argv[2]) if len(sys.argv) > 2 else 600, int(sys.argv[3]) if len(sys.argv) > 3 else 20000)
        return
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    for hot in range(kn.HEAT_MAX + 1):
        rates = clear_rates(n, hot)
        print(f'heat {hot}: clear rate by level')
        for name, row in rates.items():
            print(f'  {name:8}', ' '.join(f'{x:4.0%}' for x in row))
        for name, p in rates.items():
            stop = [returns(p, runs, lambda c, x, r, k=k: c >= k) for k in range(1, kn.LEVELS + 1)]
            on = [returns(p, runs, lambda c, x, r, k=k: c >= k and not x) for k in range(1, kn.LEVELS + 1)]
            sensible = returns(p, runs * 2, lambda c, x, r: c >= r.randint(2, 5) and not x)
            print(f'  {name:8} stop after K      ', ' '.join(f'{v:.2f}' for v in stop))
            print(f'  {name:8} ... unless next x2', ' '.join(f'{v:.2f}' for v in on), f'| sensible {sensible:.2f}')


if __name__ == '__main__':
    main()
