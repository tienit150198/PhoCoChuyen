"""Chợ đen strategies per Vietnam day under the 16/10 rebalance and the 22/10 +3 points (game/fair.py luck_p), before the police.

    python scripts/sim_bm_strategies.py [days, default 4000] [--seed N]

Each simulated day starts at 08:00 Vietnam time with today's net at 0 (fair._today); the player's streak record
(fair_balance) and pace (fair_pace) carry over as in a real save. Every round goes through the real code: luck_p (net
bands, pace, 50k cap), _draw_luck (four-win cool-off), xd_toss / xd_win, prize_of, fair_scratch.prize_mult / amount,
bc_fair_roll / bc_back / bc_bao, fair_dog.lineup / draw / back with slow_odds. Not simulated: the police (arrests,
dẹp chiếu: they only come for big stakes or a day already 300k up), 🍀 Lộc, late Kinh (lô tô assumes a timely Kinh).

Chiếu trong strategies:
  normal      200 rounds × 1,000 xu, 8 s apart
  martingale  200 rounds 8 s apart: 1,000 xu, doubled after each loss (at most 49,000), back to 1,000 after a win
  smallbig    200 rounds 8 s apart: 10 xu while today's net is ≥ 0, 45,000 xu once it is below 0 (lose small, bet big)
  bot         3,000 rounds × 5,000 xu, 3 s apart (as fast as the 3 s gap allows)
  probe       400 rounds 8 s apart: 10 xu until three wins in a row, then one round of 49,000 xu
Other stalls, normal pace (200 rounds 8 s apart) and fast (bot: 3,000 rounds, 3 s apart; bầu cua 5 s, its bowl):
  vé cào 100-xu tickets, lô tô one 100-xu tờ, bầu cua 1,000 xu on one face, đua chó 1,000 xu on a random dog.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game import fair as fh            # noqa: E402
from game import fair_scratch as xs    # noqa: E402
from game import fair_dog as dg        # noqa: E402

DAY0 = 1_800_000_000 - 1_800_000_000 % 86400 + 86400 + 1 * 3600   # 08:00 Vietnam (01:00 UTC) on a whole day


class Player:
    def __init__(self, rng: random.Random):
        self.rng, self.j = rng, {}
        self.rounds = self.wins = self.staked = self.back = 0
        self.days: list[int] = []

    def day(self, d: int) -> dict:
        t = DAY0 + d * 86400
        return dict(date=fh.vn_date(t), net=0, rounds=0, earn=fh._earn0(), t=t)

    def round(self, f: dict, game: str, st: int) -> int:
        """One round at f['t'] through the real code; returns the round's net."""
        j, t, rng = self.j, f['t'], self.rng
        if game == 'xd':
            p = fh.luck_p(j, f, 'xd', t, stake=st)
            side = 'chan' if rng.random() < .5 else 'le'
            coins = fh.xd_toss(side, fh._draw_luck(j, 'xd', p))
            back = st + fh.xd_win(st) if (side == 'chan') == (sum(coins) % 2 == 0) else 0
        elif game == 'lt':
            p = fh.luck_p(j, f, 'lt', t, stake=st)
            back = fh.prize_of('thuong', st, 1) if fh._draw_luck(j, 'lt', p) else 0
        elif game == 'xs':
            p = fh.luck_p(j, f, 'xs', t, stake=st)
            back = xs.amount(st, xs.prize_mult(rng)) if fh._draw_luck(j, 'xs', p) else 0
        elif game == 'bc':
            fh.luck_p(j, f, 'bc', t, stake=st)
            face = fh.FACES[rng.randrange(6)]
            back = fh.bc_back({face: st}, fh.bc_fair_roll(), fh.bc_bao(f, fh.pace_now(j, 'bc', t), t))
        else:   # dg
            old = fh.slow_odds(f, fh._pace(j, 'dg', t), t)
            lanes = dg.lineup(rng.randrange(10**6))
            lane = rng.randrange(dg.LANES)
            back = dg.back(st, lanes[lane][1], old) if dg.draw(lanes, rng)[0] == lane else 0
        net = back - st
        f['net'] += net
        self.rounds += 1
        self.wins += net > 0
        self.staked += st
        self.back += back
        return net


def run(strategy, days: int, seed: int) -> dict:
    rng = random.Random(f'{seed}|{strategy.__name__}')
    old = fh._rng
    fh._rng = rng
    try:
        pl = Player(rng)
        for d in range(days):
            f = pl.day(d)
            strategy(pl, f)
            pl.days.append(f['net'])
        n = len(pl.days)
        return dict(win=pl.wins / pl.rounds, net=sum(pl.days) / n, rtp=pl.back / pl.staked,
                    up=sum(x > 0 for x in pl.days) / n, rounds=pl.rounds / n)
    finally:
        fh._rng = old


def _steps(pl, f, n, gap, game, stake_of):
    last = 0
    for _ in range(n):
        last = pl.round(f, game, stake_of(f, last))
        f['t'] += gap


def normal(pl, f):
    _steps(pl, f, 200, 8, 'xd', lambda f, last: 1000)


def martingale(pl, f):
    st = [1000]

    def stake(f, last):
        if last < 0:
            st[0] = min(49_000, st[0] * 2)
        elif last > 0:
            st[0] = 1000
        return st[0]
    _steps(pl, f, 200, 8, 'xd', stake)


def smallbig(pl, f):
    _steps(pl, f, 200, 8, 'xd', lambda f, last: 10 if f['net'] >= 0 else 45_000)


def bot(pl, f):
    _steps(pl, f, 3000, 3, 'xd', lambda f, last: 5000)


def probe(pl, f):
    run_ = [0]

    def stake(f, last):
        run_[0] = run_[0] + 1 if last > 0 else 0 if last < 0 else run_[0]
        if run_[0] >= 3:
            run_[0] = 0
            return 49_000
        return 10
    _steps(pl, f, 400, 8, 'xd', stake)


def stall(game: str, stake: int, fast: bool):
    def play(pl, f):
        _steps(pl, f, 3000 if fast else 200, (5 if game == 'bc' else 3) if fast else 8, game, lambda f, last: stake)
    play.__name__ = f'{game}_{"fast" if fast else "normal"}'
    return play


def main() -> None:
    days = next((int(a) for a in sys.argv[1:] if a.isdigit()), 4000)
    seed = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1
    print(f'{days:,} Vietnam days a strategy, before police and Lộc (seed {seed})')
    print(f'{"strategy":22} {"rounds/day":>10} {"won":>7} {"mean day net":>13} {"RTP":>8} {"P(day>0)":>9}')
    rows = [('chiếu trong normal', normal), ('chiếu trong martingale', martingale), ('chiếu trong smallbig', smallbig),
            ('chiếu trong bot', bot), ('chiếu trong probe', probe)]
    names = dict(xs='vé cào', lt='lô tô', bc='bầu cua', dg='đua chó')
    for g, st in (('xs', 100), ('lt', 100), ('bc', 1000), ('dg', 1000)):
        rows += [(f'{names[g]} normal', stall(g, st, False)), (f'{names[g]} fast', stall(g, st, True))]
    for name, strat in rows:
        n = days if 'bot' not in name and 'fast' not in name else max(1, days // 10)
        r = run(strat, n, seed)
        print(f'{name:22} {r["rounds"]:10.0f} {r["win"]:7.2%} {r["net"]:13,.0f} {r["rtp"]:8.2%} {r["up"]:9.2%}')


if __name__ == '__main__':
    main()
