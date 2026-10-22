"""The fair's ordinary before-police return, exact fresh maxima and real-draw Monte Carlo.

    python scripts/sim_fair_odds.py [rounds per stall, default 1000000] [--side]

exact(): one ordinary round at today's net 0 (fair.BASES, .60 since 22/10) before streak cooling, enforcement or fines, with and
without Lộc as if its hourly server gate were always open; `back` the same round winning back a small loss
(fair.P_BACK, .63 since 22/10). Owner 16/10: chiếu trong pays 0.75× on a win, lô tô 1.8×, vé cào's won tickets 1.775×, bầu cua's
bão 20:1. No police enforcement is simulated: actual xd raids require bm.arrest_p(f, stake) > 0, so adding an
unconditional raid to these small-stake rounds would misstate their before-police returns.
scripts/sim_bm_strategies.py plays whole Vietnam days (net bands, pace, strategies).

play() uses real draws (fair._draw_luck, fair.luck_p) and payouts (bc_fair_roll / bc_back,
xd_toss, prize_of, scratch.prize_mult, fair_dog.lineup / draw / back):
  fresh   a pause > RUN_GAP before each round, 100 xu flat (today's net stays 0: luck_p gets no fair state)
  spam    one round a second at one stall, 100 xu flat (the pace penalty: −.12 from the 16th round in a minute)
  press   fresh, 1000 xu while the streak is warm, 10 xu (lt/xs: 2) while cooled
All patterns retain the four-win streak cap, so repeated fresh Monte Carlo is lower than exact()'s single round. The simulation also checks real loto
cards through loto_rs / round_view. It excludes the temporary golden-days event.
--side: why public minute calls made the now-closed loto side bets exploitable.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game import fair as fh            # noqa: E402
from game import fair_scratch as xs    # noqa: E402
from game import fair_dog as dg        # noqa: E402

LOC = fh.LOC_P * fh.LOC_MULT


def _bc_rows(bao: int = fh.BAO):
    """(probability, back per xu) of one face bet: 0, 1, 2 or 3 dice on it."""
    out = []
    for k, n in ((0, 125), (1, 75), (2, 15), (3, 1)):
        back = 0 if k == 0 else (1 + bao if k == 3 else 1 + k)
        out.append((n / 216, back))
    return out


def exact() -> dict:
    """Single fresh ordinary round before police/streak cooling, with/without an always-open Lộc gate."""
    out = {}
    # 🦀 bầu cua: three honest dice, each face bet on its own (several faces: the sum of single bets, the same return)
    rows = _bc_rows()
    rtp = sum(p * b for p, b in rows)
    loc = sum(p * fh.LOC_P * max(0, fh.LOC_MULT - (b - 1)) for p, b in rows if b > 1)
    out['bc'] = dict(rtp=rtp, loc=rtp + loc, low=sum(p * b for p, b in _bc_rows(fh.BAO_LOW)))
    # 🕯️ chiếu trong: a win pays 1 + XD_PAY_PCT / 100 of the stake, before all enforcement.
    p, pay = fh.BASES['xd'], 1 + fh.XD_PAY_PCT / 100
    out['xd'] = dict(rtp=p * pay, loc=p * pay + p * fh.LOC_P * (fh.LOC_MULT - (pay - 1)), back=fh.P_BACK * pay)
    # 🎱 lô tô: the round goes the player's way with BASES['lt'], a Kinh pays prize_of (the best tier and tờ count)
    p = fh.BASES['lt']
    best = max(fh.prize_of(m, pr, n) / (pr * n) for m in fh.LOTO_MODES for pr in fh.LOTO_TIERS.values()
               for n in range(1, fh.LOTO_CARDS + 1))
    low = min(fh.prize_of(m, pr, n) / (pr * n) for m in fh.LOTO_MODES for pr in fh.LOTO_TIERS.values()
              for n in range(1, fh.LOTO_CARDS + 1))
    out['lt'] = dict(rtp=p * best, loc=p * best + p * fh.LOC_P * (fh.LOC_MULT - (best - 1)), low=p * low,
                     back=fh.P_BACK * best)
    # 🎟️ vé cào: BASES['xs'] tickets win, a won one pays scratch.PRIZES (Lộc only on a gain, never past ×LOC_MULT)
    p, total = fh.BASES['xs'], sum(w for _, w in xs.PRIZES)
    mean = sum(m * w for m, w in xs.PRIZES) / total
    loc = sum(w / total * max(0, fh.LOC_MULT - (m - 1)) for m, w in xs.PRIZES if m > 1)
    out['xs'] = dict(rtp=p * mean, loc=p * mean + p * fh.LOC_P * loc, back=fh.P_BACK * mean)
    # 🐕 đua chó: fixed odds, the winner drawn from the classes' weights; the best dog to back (the outsider), and
    # `fresh`: the mean of a dog picked at random (what play() bets); Lộc only on a gain below LOC_MULT× the stake
    rows = [(w / 1000, m / 10) for w, m in dg.CLASSES]
    out['dg'] = dict(rtp=max(p * b for p, b in rows),
                     loc=max(p * (b + fh.LOC_P * max(0, fh.LOC_MULT - (b - 1))) for p, b in rows),
                     low=min(p * b for p, b in rows), fresh=sum(p * b for p, b in rows) / len(rows))
    return out


# ---------------------------------------------------------------- Monte-Carlo
class _Play:
    """One player's journey bits the draw keeps (fair_balance, fair_cool, the run keys), a clock, the totals."""

    def __init__(self, game: str, how: str, rng: random.Random, loc: bool):
        self.game, self.how, self.rng, self.loc = game, how, rng, loc
        self.j, self.t = {}, 1_800_000_000.0
        self.staked = self.back = 0

    def stake(self, lo: int, hi: int) -> tuple[int, float]:
        """The round's stake and its draw (fair.luck_p: counts the round in the run)."""
        self.t += 1 if self.how == 'spam' else fh.RUN_GAP + 1
        if self.how == 'press':
            cooled = self.j.get('fair_balance', {}).get(self.game, 0) >= fh.STREAK
            st = lo if cooled else hi
        else:
            st = 100
        return st, fh.luck_p(self.j, None, self.game, self.t, stake=st)

    def lucky(self, st: int, gain: int) -> int:
        """🍀 with the gate always open: a won round pays LOC_MULT× instead, LOC_P of the time (fair._loc)."""
        if self.loc and gain > 0 and self.rng.random() < fh.LOC_P and fh.LOC_MULT * st > gain:
            return fh.LOC_MULT * st - gain
        return 0


def play(game: str, how: str, n: int, seed: int = 1, loc: bool = False) -> float:
    """Return per xu staked over n rounds of `game` played `how` (see the module's docstring)."""
    rng = random.Random(f'{seed}|{game}|{how}')
    old = fh._rng
    fh._rng = rng
    try:
        pl = _Play(game, how, rng, loc)
        for _ in range(n):
            if game == 'bc':
                st, _ = pl.stake(10, 1000)
                face = fh.FACES[rng.randrange(6)]
                back = fh.bc_back({face: st}, fh.bc_fair_roll(), fh.bc_bao(None, fh.pace_now(pl.j, 'bc', pl.t), pl.t))
            elif game == 'xd':
                st, p = pl.stake(10, 1000)
                side = 'chan' if rng.random() < .5 else 'le'
                coins = fh.xd_toss(side, fh._draw_luck(pl.j, 'xd', p))
                back = st + fh.xd_win(st) if (side == 'chan') == (sum(coins) % 2 == 0) else 0
            elif game == 'dg':   # a random dog of a random race; 100 xu (press: 1000, it never cools)
                pl.t += 1 if how == 'spam' else fh.RUN_GAP + 1
                st = 1000 if how == 'press' else 100
                lanes = dg.lineup(rng.randrange(10**6))
                lane = rng.randrange(dg.LANES)
                slow = fh.slow_odds(None, fh._pace(pl.j, 'dg', pl.t), pl.t)   # spam: the old prices
                back = dg.back(st, lanes[lane][1], slow) if dg.draw(lanes, rng)[0] == lane else 0
            elif game == 'lt':
                st, p = pl.stake(2, 1000)   # a 100-xu tờ (trăm); press: 1000 / 2
                back = fh.prize_of('thuong', st, 1) if fh._draw_luck(pl.j, 'lt', p) else 0
            else:   # xs
                st, p = pl.stake(2, 1000)   # a 100-xu vé; press: 1000 / 2
                back = xs.amount(st, xs.prize_mult(rng)) if fh._draw_luck(pl.j, 'xs', p) else 0
            back += pl.lucky(st, back - st)
            pl.staked += st
            pl.back += back
        return pl.back / pl.staked
    finally:
        fh._rng = old


def loto_rounds(n: int, seed: int = 3) -> tuple[float, float]:
    """(share of rounds drawn for the player, share whose cards then really fill first): loto_rs + round_view."""
    rng = random.Random(seed)
    old = fh._rng
    fh._rng = rng
    try:
        drawn = ok = 0
        slot = 29_500_000
        for i in range(n):
            want = rng.random() < fh.BASES['lt']
            mode = ('thuong', 'nguoc', 'doi', 'dem')[i % 4]
            lt = dict(slot=slot + i, rs=0, at=0, stage='play', mode=mode, tier='vua', n=1 + i % 3, fk=0)
            lt['rs'] = fh.loto_rs(lt, want)
            rv = fh.round_view(lt)
            drawn += want
            ok += (rv['mine'] <= rv['npc_done']) == want   # a tie is the player's ("hai người cùng lúc thì bạn được")
        return drawn / n, ok / n
    finally:
        fh._rng = old


def side_peek(slots: int = 40, rounds: int = 600, seed: int = 4) -> tuple[float, float]:
    """The lô tô side bets once the minute's calls are seen (a first tờ that minute): the average over minutes of the
    best chẵn/lẻ and the best cột return per xu (2× / 8.5×). Above 1: why they are closed (SIDE_OPEN)."""
    rng = random.Random(seed)
    cl = cot = 0.0
    for s in range(slots):
        slot = 29_600_000 + s * 7
        even = odd = 0
        cols = [0] * 9
        for _ in range(rounds):
            x = fh.round_view(dict(slot=slot, rs=rng.getrandbits(31), at=0, stage='play'))['chot_n']
            if x not in fh.BAY_NUMS:
                even += x % 2 == 0
                odd += x % 2 == 1
            cols[0 if x < 10 else min(8, x // 10)] += 1
        cl += 2 * max(even, odd) / rounds
        cot += fh.COT_PAY_HALF / 2 * max(cols) / rounds
    return cl / slots, cot / slots


def main() -> None:
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 1_000_000)
    print('Ordinary draws, before all police enforcement; exact = one fresh round, MC retains streak cooling.')
    names = dict(bc='🦀 bầu cua', xd='🕯️ chiếu trong', lt='🎱 lô tô', xs='🎟️ vé cào', dg='🐕 đua chó')
    ex = exact()
    print(f'{"stall":16} {"exact":>7} {"+Lộc":>7} | {n:,} rounds each: {"fresh":>7} {"spam":>7} {"press":>7} {"fresh+Lộc":>9}')
    for g, name in names.items():
        mc = [play(g, how, n) for how in ('fresh', 'spam', 'press')] + [play(g, 'fresh', n, loc=True)]
        print(f'{name:16} {ex[g]["rtp"]:7.2%} {ex[g]["loc"]:7.2%} | {"":>{len(f"{n:,}") + 15}}'
              + ' '.join(f'{v:7.2%}' for v in mc[:3]) + f' {mc[3]:9.2%}')
    print(f'winning back a small loss ({fh.P_BACK:.2f}): chiếu trong {ex["xd"]["back"]:.2%}, lô tô {ex["lt"]["back"]:.2%}, '
          f'vé cào {ex["xs"]["back"]:.2%}; bầu cua with the bão at {fh.BAO_LOW}: {ex["bc"]["low"]:.2%}')
    print(f'lô tô 2-xu tờ (pays 3): {ex["lt"]["low"]:.2%}')
    print(f'đua chó: the favourite {ex["dg"]["low"]:.2%}, a dog picked at random {ex["dg"]["fresh"]:.2%}')
    drawn, ok = loto_rounds(min(n, 20_000))
    print(f'lô tô rounds through loto_rs/round_view: drawn for the player {drawn:.2%}, cards agree {ok:.2%}')
    if '--side' in sys.argv:
        cl, cot = side_peek()
        print(f'side bets after seeing the minute\'s calls: best chẵn/lẻ {cl:.2%}, best cột {cot:.2%} back per xu')


if __name__ == '__main__':
    main()
