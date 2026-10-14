#!/usr/bin/env python3
"""🧩 Ghép ba Phố Mây: rebuild game/tile_match_levels.py (100 levels as a seed plus parameters).

For each level the curve below gives the parameters (item kinds, layers, stacks, 🔒 locks, 🧊 ice, the intended
solution's tray peak, a tile count to aim at, a shape). Pass 1 tries seeds (and fill / layer / offset / kind variants)
and keeps the candidates whose tile count is near the aim and that game.tile_match.solve clears on its own, each with
its difficulty (game.tile_match.difficulty) and the quick player's win rate (greedy_rate). Pass 2 keeps, for every
level, the candidate whose win rate is nearest WIN_RATE(lv) (2.4.7, owner 14/10 "quá dễ": from level 5 on more kinds,
layers and stacks and a tighter tray; mid and late levels usually need careful play or a booster), never much easier
than the level before. Deterministic: the same code gives the same table (the levels run in parallel processes).

    python scripts/build_tile_levels.py            # writes the table (about 3 minutes)
    python scripts/build_tile_levels.py --check    # rebuilds every level from the table and solves it, writes nothing
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game import tile_match as tm  # noqa: E402

OUT = ROOT / 'game' / 'tile_match_levels.py'
EARLY = {1: ('o3', 9), 2: ('bar', 12), 3: ('diamond', 15), 4: ('plus', 18), 5: ('pyramid', 36), 6: ('square', 42),
         7: ('x', 45), 8: ('hourglass', 48), 9: ('butterfly', 54)}
LANDMARK = {10: 'house', 20: 'heart', 30: 'pagoda', 40: 'lighthouse', 50: 'lantern', 60: 'boba', 70: 'bridge',
            80: 'pagoda', 90: 'lighthouse', 100: 'heart'}
FIVES = ('pyramid', 'butterfly', 'x', 'heart', 'hourglass', 'house', 'lantern', 'boba', 'bridge')
GENERAL = ('diamond', 'square', 'plus', 'ring', 'lantern', 'pyramid', 'x', 'hourglass', 'butterfly', 'heart', 'house', 'lantern')
TRIES = 160


def win_rate(lv: int) -> float:
    """The quick player's (greedy_rate) wins wanted at level lv: easy openers, then steadily harder."""
    return 1.0 if lv < 5 else max(0.06, 0.82 - 0.8 * ((lv - 4) / 96) ** 0.5)


def curve(lv: int) -> dict:
    t = (lv - 1) / 99
    if lv in EARLY:
        shape, target = EARLY[lv]
    else:
        target = 3 * round(15 + 43 * t ** 0.85)         # 51 at level 10 … 174 at level 100
        shape = LANDMARK.get(lv) or (FIVES[(lv // 5) % len(FIVES)] if lv % 5 == 0 else GENERAL[lv % len(GENERAL)])
    kinds = 3 if lv < 3 else 4 if lv < 5 else 7 if lv < 7 else 8 if lv < 13 else min(20, max(9, 5 + round(15 * t ** 0.65)))
    kinds = max(3, min(kinds, target // 3))
    layers = 1 if lv == 1 else 2 if lv < 5 else max(3, min(8, 2 + math.ceil(6 * t ** 0.5)))
    stacks = () if lv < 5 else (3,) if lv < 10 else (3 + round(5 * t),) * 2 if lv < 40 \
        else (4 + round(6 * t),) * 2 + ((3 + round(5 * t),) if lv >= 60 else ())
    locks = 0 if lv < 30 else 1 + (lv - 30) // 10
    ice = 0 if lv < 45 else 2 + (lv - 45) // 4
    peak = 3 if lv < 5 else 4 if lv < 7 else 5 if lv < 25 else 6
    return dict(shape=shape, target=target, kinds=kinds, layers=layers, stacks=stacks, locks=locks, ice=ice, peak=peak)


def candidates(lv: int):
    c = curve(lv)
    fixed = lv in LANDMARK or lv % 5 == 0 or lv < 5
    shapes = [c['shape']] + ([] if fixed else ['big', 'square'])
    low = 0.55 if fixed else 0.65
    for i in range(TRIES):
        seed = (lv * 7919 + i * 104729) % 2_147_483_647
        shape = shapes[0] if i < TRIES * 3 // 4 else shapes[i % len(shapes)]
        fill = (1000, 900, 800, 700, 600)[i % 5]
        offset = 'dhv'[(i // 5) % 3] if lv > 2 else 'd'
        layers = c['layers'] + (0, 1, 2, -1)[(i // 2) % 4] if lv > 2 else c['layers']
        layers = max(1 if lv == 1 else 2, min(9, layers))
        kinds = c['kinds']
        row = (seed, shape, kinds, layers, fill, offset, c['stacks'], c['locks'], c['ice'], c['peak'], c['target'])
        try:
            level = tm.build(lv, row)
        except tm.Gen:
            continue
        n = len(level['tiles'])
        if n < c['target'] * low or n > c['target']:
            continue
        if len(set(t[3] for t in level['tiles'])) != kinds:
            continue
        if sum(1 for t in level['tiles'] if t[4] & tm.LOCK) != c['locks'] or sum(1 for t in level['tiles'] if t[4] & tm.ICE) != c['ice']:
            continue
        if tm.solve(level) is None:
            continue
        rate = tm.greedy_rate(level)
        yield dict(row=row, d=tm.difficulty(level, rate), rate=rate, n=n)


def monotone(xs: list[float]) -> list[float]:
    """Isotonic (non-decreasing) fit, pool-adjacent-violators, then a light moving average."""
    blocks = []
    for x in xs:
        blocks.append([x, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            v2, n2 = blocks.pop()
            v1, n1 = blocks.pop()
            blocks.append([(v1 * n1 + v2 * n2) / (n1 + n2), n1 + n2])
    fit = [v for v, n in blocks for _ in range(n)]
    return [sum(fit[max(0, i - 2):i + 3]) / len(fit[max(0, i - 2):i + 3]) for i in range(len(fit))]


def choose(all_cands: list[list[dict]]):
    """Each level's candidate whose quick-player win rate is nearest win_rate(lv); never much easier than the
    hardest level before it (rate), the aimed size and shape and more kinds break ties."""
    out, low, kinds = [], 1.0, 0
    for lv, cands in enumerate(all_cands, 1):
        want = win_rate(lv)
        cands = [x for x in cands if x['row'][2] >= kinds] or cands   # item kinds never go down
        def miss(x):
            return (abs(x['rate'] - want) * 100 + (30 if x['rate'] > low + 0.12 else 0)
                    + abs(x['n'] - curve(lv)['target']) / 12 + (8 if x['row'][1] != curve(lv)['shape'] else 0)
                    + 2 * (curve(lv)['kinds'] - x['row'][2]))
        best = min(cands, key=miss)
        out.append((best, want))
        low = min(low, best['rate']) if lv >= 5 else low
        kinds = max(kinds, best['row'][2])
    return out


def _one(lv: int) -> list[dict]:
    return list(candidates(lv))


def write(rows, scores):
    lines = ['"""🧩 Ghép ba Phố Mây: the 100 levels (GENERATED by scripts/build_tile_levels.py; do not edit by hand).',
             '',
             'One row a level: (seed, shape, kinds, layers, fill ‰, layer offset, stack depths, 🔒 locks, 🧊 ice, tray peak of',
             'the intended solution, tile target). game/tile_match.py build() makes the level from its row, deterministically.',
             'SCORES: each level\'s difficulty (tile_match.difficulty) when the table was built; tests check they rise."""',
             '',
             'LEVELS = (']
    for i, row in enumerate(rows, 1):
        lines.append(f'    {row!r},   # {i}')
    lines.append(')')
    lines.append('SCORES = (' + ', '.join(f'{d:g}' for d in scores) + ')')
    OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--upto', type=int, default=tm.LEVEL_MAX)
    a = ap.parse_args()
    if a.check:
        from game.tile_match_levels import LEVELS, SCORES
        bad = 0
        for lv in range(1, len(LEVELS) + 1):
            level = tm.build(lv, LEVELS[lv - 1])
            ok = tm.solve(level) is not None
            bad += not ok
            print(lv, LEVELS[lv - 1][1], len(level['tiles']), len(level['icons']), SCORES[lv - 1], 'OK' if ok else 'UNSOLVED')
        raise SystemExit(1 if bad else 0)
    from multiprocessing import Pool
    with Pool() as pool:
        all_cands = pool.map(_one, range(1, a.upto + 1), chunksize=1)
    for lv, cands in enumerate(all_cands, 1):
        if not cands:
            raise SystemExit(f'level {lv}: no candidate')
        print(f'{lv:3d}: {len(cands)} candidates', flush=True)
    rows, scores = [], []
    for lv, (x, want) in enumerate(choose(all_cands), 1):
        row = x['row']
        rows.append(row)
        scores.append(x['d'])
        print(f'{lv:3d} {row[1]:10s} tiles {x["n"]:3d} kinds {row[2]:2d} layers {row[3]} stacks {row[6]} locks {row[7]} '
              f'ice {row[8]} peak {row[9]}  rate {x["rate"]:.2f} (want {want:.2f})  D {x["d"]:5.1f}', flush=True)
    write(rows, scores)


if __name__ == '__main__':
    main()
