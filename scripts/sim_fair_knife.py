"""🗡️ Phóng dao at the fair: a simulation of game/fair_knife.py (dev tool, the numbers in that module's docstring).

A simulated player watches the board as it was REACT ms ago, guesses where a knife thrown now would stick by carrying
that angle on at the speed it saw (right while the board keeps its speed, wrong when it turns back or stops in
between), throws when the guess is at least `calm` degrees clear of every knife (less picky the longer they wait),
and their thumb is off by a gauss of `sigma` ms. Each level is judged by fair_knife.judge, like the server does.

    python scripts/sim_fair_knife.py [levels per difficulty] [runs]

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


def play_level(sc: dict, who: tuple, rng: random.Random) -> bool:
    sigma, react, calm, patience = who
    taps: list[int] = []
    t = rng.randint(300, 900)
    ready = t
    while len(taps) < sc['need']:
        if t > kn.LEVEL_MS - 200:
            return False
        seen = t - react
        guess = (kn.IMPACT - (kn.angle_at(sc, seen) + kn.speed_at(sc, seen) * (react + kn.FLY_MS))) % 360.0
        stuck, _ = kn.judge(sc, taps)
        room = min((kn.dist(guess, b) for b in sc['pre'] + stuck), default=180.0) - kn.GAP
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


def clear_rates(n: int, hot: int = 0, seed: int = 1) -> dict:
    rng = random.Random(seed)
    out = {}
    for name, who in PLAYERS.items():
        row = []
        for lv in range(1, kn.LEVELS + 1):
            ok = sum(play_level(kn.schedule(rng.getrandbits(31), lv, hot), who, rng) for _ in range(n))
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


def main() -> None:
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
