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
    python scripts/build_tile_levels.py --extend   # keeps levels 1–100 as they are, (re)builds 101–200 only

Levels 101–200 (owner 17/10: "mở thêm tới màn 200, khó hơn … càng thêm nhiều item nó sẽ khó hơn"): 20 → 28 item
kinds (every icon of tile_match.ICONS), 8–9 layers, deeper stacks, more 🔒 and 🧊, a bigger board, and a quick player
who wins less and less (6 % → 2 %). Levels 1–100 never change: saves, replays and their difficulty stay.
    python scripts/build_tile_levels.py --check    # rebuilds every level from the table and solves it, writes nothing
    python scripts/build_tile_levels.py --extend2  # keeps levels 1–200 as they are, (re)builds 201–300 only

Levels 201–300 (2.5.7, owner 23/10 "thêm mở tới màn 300 nhé, khó hơn, với có item ẩn … học candy fruits"): the deep
boards of 191–200 with more of everything and the four special tiles (game/tile_match.py), each brought in on its own
level with fewer icons (a breather, like a candy game's new-candy level), then mixed in. `curve_hi2` is the rule; the
table in game/tile_match_levels.py's docstring shows what was built. Every tenth level from 210 holds a 🎁 chest of free
boosters (tile_match.chest); 225, 250, 275 and 300 have a tray of 6.
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
TRIES2 = 64                     # levels 201–300: bigger, slower to check
SOLVE_LIMIT = 150_000           # …and a level the solver has not cleared by then is not kept (the tests allow 400 000)


BASE = 100                      # levels 1–100: the 2.4.7 table, never rebuilt by --extend
HI_LANDMARK = {110: 'house', 120: 'heart', 130: 'pagoda', 140: 'lighthouse', 150: 'lantern', 160: 'boba',
               170: 'hourglass', 180: 'pagoda', 190: 'lighthouse', 200: 'lantern'}
# Mid-size shapes: full, paired layers stand 12–14 high on them within ~240 tiles ('big' is trimmed back to ~5 layers).
HI_SHAPES = ('pagoda', 'lantern', 'hourglass', 'lighthouse', 'house', 'butterfly', 'ring', 'boba', 'pyramid', 'heart')
HI_DEEP = ('pagoda', 'lantern', 'lighthouse', 'hourglass')


HI = 200                        # levels 1–200: kept as they are by --extend2
HI2_LANDMARK = {210: 'house', 220: 'heart', 230: 'pagoda', 240: 'lighthouse', 250: 'lantern', 260: 'boba',
                270: 'hourglass', 280: 'pagoda', 290: 'lighthouse', 300: 'heart'}
INTRO = {201: 'box', 211: 'joker', 221: 'chain', 231: 'bomb'}


def curve_hi2(lv: int) -> dict:
    """Levels 201–300: from where level 200 stands to every icon and every special tile."""
    u = (lv - HI - 1) / 99
    kinds = min(48, 40 + round(8 * u)) - (6 if lv in INTRO else 0)
    cap = 6 if lv % 25 == 0 else 0
    return dict(shape=HI2_LANDMARK.get(lv) or HI_SHAPES[lv % len(HI_SHAPES)], target=3 * round(70 + 6 * u), kinds=kinds,
                layers=12 + round(u), stacks=(12 + round(u),) * 2 + (10 + round(u),), locks=12 + round(4 * u),
                ice=30 + round(10 * u), peak=5 if cap else 6,
                box=4 + round(10 * u), joker=0 if lv < 211 else 1 if lv < 261 else 2,
                chain=0 if lv < 221 else 2 + round(6 * (lv - 221) / 79),
                bomb=0 if lv < 231 else 1 if lv < 261 else 2 if lv < 291 else 3, cap=cap)


def win_rate(lv: int) -> float:
    """The quick player's (greedy_rate) wins wanted at level lv: easy openers, then steadily harder."""
    if lv > HI:
        return max(0.01, 0.02 - 0.01 * (lv - HI - 1) / 99)
    if lv > BASE:
        return max(0.02, 0.06 - 0.04 * (lv - BASE - 1) / 99)
    return 1.0 if lv < 5 else max(0.06, 0.82 - 0.8 * ((lv - 4) / 96) ** 0.5)


def curve_hi(lv: int) -> dict:
    """Levels 101–200: from where level 100 stands to every icon on a full, deep board."""
    u = (lv - BASE - 1) / 99
    target = 3 * round(50 + 20 * u)                   # 150 at 101 … 210 at 200 (level 100: 174 aimed, 114 built)
    shape = HI_LANDMARK.get(lv) or HI_SHAPES[lv % len(HI_SHAPES)]
    kinds = 22 + round(18 * u)                        # 22 … 40 icons (owner 18/10 "thêm 30 40 loại thoải mái"; 100: 20)
    layers = 9 + round(4 * u)                         # 9 … 13 high (built at least one less): some layers straight on the one below
    stacks = (10 + round(2 * u),) * 2 + (8 + round(2 * u),)
    locks = 8 + round(4 * u)
    ice = 16 + round(14 * u)
    return dict(shape=shape, target=target, kinds=kinds, layers=layers, stacks=stacks, locks=locks, ice=ice, peak=6)


def curve(lv: int) -> dict:
    if lv > HI:
        return curve_hi2(lv)
    if lv > BASE:
        return curve_hi(lv)
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
    """Level lv's acceptable rows; past 100, a level with none at the wanted depth takes one layer less, then two,
    then (a landmark) other shapes too."""
    for slack, free in (((1, False), (2, False), (3, False), (3, True)) + (((4, True), (5, True)) if lv > HI else ()) if lv > BASE else ((1, False),)):
        got = list(_candidates(lv, slack, free))
        if got:
            return got
    return []


def _candidates(lv: int, slack: int, free: bool = False):
    c = curve(lv)
    hi = lv > BASE
    hi2 = lv > HI
    fixed = not free and (lv in HI2_LANDMARK if hi2 else lv in HI_LANDMARK if hi else lv in LANDMARK or lv % 5 == 0 or lv < 5)
    shapes = [c['shape']] + ([] if fixed else list(HI_DEEP) if hi else ['big', 'square'])
    low = 0.7 if hi else 0.55 if fixed else 0.65
    for i in range(TRIES2 if hi2 else TRIES):
        seed = (lv * 7919 + i * 104729) % 2_147_483_647
        shape = shapes[0] if i < (TRIES2 if hi2 else TRIES) * 3 // 4 else shapes[i % len(shapes)]
        fill = ((1000, 1000, 1000, 950, 950) if hi else (1000, 900, 800, 700, 600))[i % 5]
        offset = 'dhv'[(i // 5) % 3] if lv > 2 else 'd'
        if hi:   # one straight layer in three to 150, then pairs too (the hardest: fully covered tiles)
            offset += '3' if (lv <= 150 and not hi2) or i % 2 else ''
            offset = offset if offset.endswith('3') else offset.upper()
        layers = c['layers'] + ((0, 1, 2, 4) if hi else (0, 1, 2, -1))[(i // 2) % 4] if lv > 2 else c['layers']
        layers = max(1 if lv == 1 else 2, min(15 if lv > BASE else 9, layers))
        kinds = c['kinds']
        row = (seed, shape, kinds, layers, fill, offset, c['stacks'], c['locks'], c['ice'], c['peak'], c['target'])
        if hi2:
            row += (c['box'], c['joker'], c['chain'], c['bomb'], c['cap'])
        try:
            level = tm.build(lv, row)
        except tm.Gen:
            continue
        n = len(level['tiles'])
        if n < c['target'] * low or n > c['target'] + c.get('joker', 0):   # a 🌈 is not an item: one more tile
            continue
        depth = 1 + max(t[2] for t in level['tiles'][:level['board']])
        if hi and depth < c['layers'] - slack:   # trimmed back to a shallow pile: not what 101–200 are about
            continue
        if len(set(t[3] for t in level['tiles']) - {-1}) != kinds:   # -1: a 🌈
            continue
        if sum(1 for t in level['tiles'] if t[4] & tm.LOCK) != c['locks'] or sum(1 for t in level['tiles'] if t[4] & tm.ICE) != c['ice']:
            continue
        if hi2 and [sum(1 for t in level['tiles'] if t[4] & f) for f in (tm.BOX, tm.JOKER, tm.CHAIN, tm.BOMB)] \
                != [c['box'], c['joker'], c['chain'], c['bomb']]:
            continue
        if tm.solve(level, limit=SOLVE_LIMIT if hi2 else 400_000) is None:
            continue
        rate = tm.greedy_rate(level)
        yield dict(row=row, d=tm.difficulty(level, rate), rate=rate, n=n, depth=depth)


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


def choose(all_cands: list[list[dict]], first: int = 1, low: float = 1.0, kinds: int = 0):
    """Each level's candidate whose quick-player win rate is nearest win_rate(lv); never much easier than the
    hardest level before it (rate), the aimed size and shape and more kinds break ties. `first`, `low`, `kinds`:
    where an --extend run starts (the level after the kept table, its hardest rate and most kinds)."""
    out = []
    for lv, cands in enumerate(all_cands, first):
        want = win_rate(lv)
        cands = [x for x in cands if x['row'][2] >= kinds or lv in INTRO] or cands   # item kinds never go down (an intro: fewer)
        if lv > BASE:   # one quick win in 48 at least, and the deeper stacks first
            cands = [x for x in cands if x['rate'] > 0] or cands
        def miss(x):
            return (abs(x['rate'] - want) * 100 + (30 if x['rate'] > low + 0.12 else 0)
                    + abs(x['n'] - curve(lv)['target']) / 12 + (8 if x['row'][1] != curve(lv)['shape'] else 0)
                    + 2 * (curve(lv)['kinds'] - x['row'][2]) + (2 * max(0, curve(lv)['layers'] - x['depth']) if lv > BASE else 0))
        best = min(cands, key=miss)
        out.append((best, want))
        low = min(low, best['rate']) if lv >= 5 else low
        kinds = kinds if lv in INTRO else max(kinds, best['row'][2])
    return out


def _one(lv: int) -> list[dict]:
    return list(candidates(lv))


def write(rows, scores):
    lines = [f'"""🧩 Ghép ba Phố Mây: the {len(rows)} levels (GENERATED by scripts/build_tile_levels.py; do not edit by hand).',
             '',
             'One row a level: (seed, shape, kinds, layers, fill ‰, layer offset, stack depths, 🔒 locks, 🧊 ice, tray peak of',
             'the intended solution, tile target). game/tile_match.py build() makes the level from its row, deterministically.',
             'SCORES: each level\'s difficulty (tile_match.difficulty) when the table was built; tests check they rise.']
    if len(rows) > HI:
        lines += ['',
                  'Levels 201–300 (2.5.7) carry five more: 🎁 boxes, 🌈 jokers, ⛓️ chains, 💣 bombs, tray (0 = 7). Built, ten by ten',
                  '(tiles and layers as built; a range is min–max; ★ the level that brings a special tile in, with a card):',
                  '',
                  '    levels   tiles    icons  layers  stacks      🔒     🧊     🎁     🌈   ⛓️    💣   tray  quick wins']
        for a in range(HI + 1, len(rows) + 1, 10):
            grp = list(range(a, min(a + 10, len(rows) + 1)))
            built = [tm.build(lv, rows[lv - 1]) for lv in grp]
            rng_ = lambda xs: f'{min(xs)}–{max(xs)}' if min(xs) != max(xs) else f'{min(xs)}'
            col = lambda i: rng_([tm._row(rows[lv - 1])[i] for lv in grp])
            n = rng_([len(b['tiles']) for b in built])
            depth = rng_([1 + max(t[2] for t in b['tiles'][:b['board']]) for b in built])
            stacks = rng_([sum(tm._row(rows[lv - 1])[6]) for lv in grp])
            trays = sorted({b['cap'] for b in built})
            rate = rng_([round(100 * tm.greedy_rate(b)) for b in built])
            star = ''.join(f' ★{lv}' for lv in grp if lv in INTRO)
            lines.append(f'    {a}–{grp[-1]}  {n:8s} {col(2):6s} {depth:7s} {stacks:11s} {col(7):6s} {col(8):6s} {col(11):6s} '
                         f'{col(12):4s} {col(13):5s} {col(14):4s} {"/".join(map(str, trays)):5s} {rate} %{star}')
    lines[-1] += '"""'
    lines += ['',
             'LEVELS = (']
    for i, row in enumerate(rows, 1):
        lines.append(f'    {row!r},   # {i}')
    lines.append(')')
    lines.append('SCORES = (' + ', '.join(f'{d:g}' for d in scores) + ')')
    OUT.write_bytes(('\n'.join(lines) + '\n').encode('utf-8'))   # LF on Windows too


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--upto', type=int, default=BASE)
    ap.add_argument('--extend', action='store_true', help='keep levels 1-100, build 101..200')
    ap.add_argument('--extend2', action='store_true', help='keep levels 1-200, build 201..LEVEL_MAX')
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
    first, rows, scores, low, kinds = 1, [], [], 1.0, 0
    if a.extend:
        from game.tile_match_levels import LEVELS, SCORES
        first, rows, scores = BASE + 1, list(LEVELS[:BASE]), list(SCORES[:BASE])
        kinds = max(r[2] for r in rows)
        low = min(tm.greedy_rate(tm.build(lv, LEVELS[lv - 1])) for lv in range(BASE - 9, BASE + 1))
        a.upto = HI
    if a.extend2:
        from game.tile_match_levels import LEVELS, SCORES
        first, rows, scores = HI + 1, list(LEVELS[:HI]), list(SCORES[:HI])
        kinds = 0   # the 🎁 intro level has fewer icons: no floor from 200
        low = min(tm.greedy_rate(tm.build(lv, LEVELS[lv - 1])) for lv in range(HI - 9, HI + 1))
        a.upto = tm.LEVEL_MAX
    with Pool() as pool:
        all_cands = pool.map(_one, range(first, a.upto + 1), chunksize=1)
    for lv, cands in enumerate(all_cands, first):
        if not cands:
            raise SystemExit(f'level {lv}: no candidate')
        print(f'{lv:3d}: {len(cands)} candidates', flush=True)
    for lv, (x, want) in enumerate(choose(all_cands, first, low, kinds), first):
        row = x['row']
        rows.append(row)
        scores.append(x['d'])
        print(f'{lv:3d} {row[1]:10s} tiles {x["n"]:3d} kinds {row[2]:2d} layers {row[3]} stacks {row[6]} locks {row[7]} '
              f'ice {row[8]} peak {row[9]} {row[11:]}  rate {x["rate"]:.2f} (want {want:.2f})  D {x["d"]:5.1f}', flush=True)
    write(rows, scores)


if __name__ == '__main__':
    main()
