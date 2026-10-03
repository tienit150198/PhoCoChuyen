"""💰 The xu sinks of 03/10 (docs/ECONOMY_SINKS.md): a replay of plausible players over 14 life days, before and after.

    python scripts/sim_economy.py [knife runs]

Each profile is a player of the prod sample (admin stats, 291 saves, early 10/2026: wallet median 70, p90 997, average
7 048, 11 saves ≥ 2 000): what they earn a life day, what they own, what they keep in savings and how they play the fair
(open 5 of the 14 days). The sinks are computed with the game's own functions: game/upkeep.py (vehicles, homes),
game/invest.py accrual (the savings tier), the vé số cào's prize table and odds, the phóng dao's ladder through
scripts/sim_fair_knife.py returns() with the clear rates of game/fair_knife.py's docstring, and the 📸 photobooth of the
fair (another branch, about PHOTO xu a session). Work income, living costs and the home's rent are the same before and
after (inputs, not sinks). Voluntary purchases (the new luxury vehicles) are left out: they are the player's choice.

Prints, per profile, xu in / out / net per group over the 14 days, before -> after, then the whole sample weighted by
how many saves each profile stands for (WEIGHT), and the change of the economy's net inflow.

The run of 03/10 (20 000 knife runs), net xu over the 14 days, before -> after:
  new (161 saves)          +683 ->    +656        (-4 %: the photobooth and the scratch card edge)
  median (90)            +1 487 ->  +1 439        (-3 %)
  upper (29)             +6 383 ->  +6 194        (-3 %)
  rich_assets (6)       +51 484 -> +42 903        (-17 %: bills 5 664, savings tier -1 142, fair -1 775)
  rich_saver (5)        +59 520 -> +50 957        (-14 %: savings tier -6 536, fair -1 775)
  sample, per save       +3 558 ->  +3 185        (-10 % of the net inflow; 87 % of the cut paid by the 11 rich saves)
  ... with one rich player in 3 buying the Trực thăng riêng: +2 416 (-32 %)
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from game import fair_knife as kn            # noqa: E402
from game import fair_scratch as xs          # noqa: E402
from game import garage as gr                # noqa: E402
from game import housing as hs               # noqa: E402
from game import invest as iv                # noqa: E402
from game import upkeep as up                # noqa: E402
import sim_fair_knife as simk                # noqa: E402

DAYS = 14
FAIR_DAYS = 5
PHOTO = 5                                    # 📸 photobooth, xu a session (fair, another branch)
OLD_LADDER = (11, 12, 16, 21, 28, 39, 54, 80, 120, 190)
OLD_P_HI = .42
KNIFE_RATES = {   # heat 0, game/fair_knife.py docstring
    'weak': [.75, .72, .67, .67, .66, .60, .58, .52, .54, .49],
    'average': [.85, .82, .78, .77, .73, .71, .69, .66, .63, .60],
    'good': [1.0, .98, .97, .96, .94, .94, .93, .91, .87, .86],
}
GROUPS = ('work', 'living', 'home rent', 'savings interest', 'fair', 'bills (new)')

# name: work (net xu a life day from careers, x3 included), living (rent + meals + điện nước a day), cars, homes
# [(kind, let?)], saving (Mây savings balance), fair a fair day: scratch (tickets, price), knife (runs, stake, thumb,
# 'sensible'|'deep'), photo (sessions); WEIGHT: saves of the sample it stands for.
PROFILES = {
    'new': dict(work=60, living=11, cars=[], homes=[], saving=0, scratch=(3, 2), knife=(1, 2, 'weak', 'sensible'), photo=1),
    'median': dict(work=120, living=16, cars=['xe_so'], homes=[], saving=600, scratch=(10, 5), knife=(4, 5, 'average', 'sensible'),
                   photo=1),
    'upper': dict(work=450, living=20, cars=['xe_ga', 'o_to_mini'], homes=[('can_ho_mini', False)], saving=8000,
                  scratch=(20, 10), knife=(8, 10, 'average', 'sensible'), photo=2),
    'rich_assets': dict(work=3000, living=36, cars=['xe_ga', 'o_to_suv', 'mui_tran', 'du_thuyen', 'phan_luc'],
                        homes=[('biet_thu_song', False), ('penthouse', True), ('nha_san', False)], saving=60000,
                        scratch=(40, 20), knife=(20, 20, 'good', 'deep'), photo=2),
    'rich_saver': dict(work=3000, living=20, cars=['mui_tran'], homes=[('can_ho_1pn', False)], saving=250000,
                       scratch=(40, 20), knife=(20, 20, 'good', 'deep'), photo=2),
}
WEIGHT = dict(new=161, median=90, upper=29, rich_assets=6, rich_saver=5)
BUY, BUYERS = 'truc_thang', 3   # the voluntary-purchase scenario (see main)

_knife_cache: dict = {}


def knife_back(ladder, thumb, way, runs):
    """xu back per xu staked for that ladder, thumb and way of playing (cached)."""
    key = (ladder, thumb, way)
    if key not in _knife_cache:
        kn.LADDER = ladder
        kn._PRIZES.clear()
        lo, hi = (2, 5) if way == 'sensible' else (5, 8)
        _knife_cache[key] = simk.returns(KNIFE_RATES[thumb], runs, lambda c, x, r: c >= r.randint(lo, hi) and not x)
    return _knife_cache[key]


def scratch_back(p):
    return p * sum(m * w for m, w in xs.PRIZES) / sum(w for _, w in xs.PRIZES)


def play(P, after: bool, runs: int) -> dict:
    """{group: [in, out]} over DAYS life days."""
    g = {k: [0, 0] for k in GROUPS}
    g['work'][0] = P['work'] * DAYS
    g['living'][1] = P['living'] * DAYS
    for kind, let in P['homes']:
        if let:
            g['home rent'][0] += hs.rent_of(kind) * DAYS // up.MONTH_DAYS
    # savings: daily accrual, credited every 7 days (iv.TERM); before = the flat 0,3 %, after = the tier
    bal, pending = P['saving'], 0
    for d in range(1, DAYS + 1):
        pending += iv.accrual(bal, flat=not after)
        if d % iv.TERM == 0:
            bal += pending // 1000
            g['savings interest'][0] += pending // 1000
            pending %= 1000
    # the fair, FAIR_DAYS of the 14
    n, price = P['scratch']
    staked = n * price * FAIR_DAYS
    g['fair'][1] += staked
    g['fair'][0] += round(staked * scratch_back(xs.P_HI if after else OLD_P_HI))
    runs_n, stake, thumb, way = P['knife']
    staked = runs_n * stake * FAIR_DAYS
    g['fair'][1] += staked
    g['fair'][0] += round(staked * knife_back(kn_new if after else OLD_LADDER, thumb, way, runs))
    if after:
        g['fair'][1] += P['photo'] * PHOTO * FAIR_DAYS
        # the bills: one day's share of everything owned, DAYS mornings
        milli = sum(up.daily_milli(gr.VEHICLES[v]['price'], up.car_bp(v, gr.VEHICLES[v]['price'])) for v in P['cars'])
        milli += sum(up.daily_milli(hs.HOMES[k]['price'], up.home_bp(k)) for k, _ in P['homes'])
        g['bills (new)'][1] = milli * DAYS // 1000
    return g


def net(g):
    return sum(i - o for i, o in g.values())


def fmt(n):
    return f'{n:+,}'.replace(',', ' ')


def main():
    global kn_new
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    kn_new = tuple(kn.LADDER)
    random.seed(1)
    tot = {False: {k: [0, 0] for k in GROUPS}, True: {k: [0, 0] for k in GROUPS}}
    print(f'{DAYS} life days, the fair open {FAIR_DAYS} of them. xu in / out per group, before -> after.\n')
    for name, P in PROFILES.items():
        b, a = play(P, False, runs), play(P, True, runs)
        print(f'{name} (stands for {WEIGHT[name]} saves)')
        for k in GROUPS:
            if b[k] == [0, 0] and a[k] == [0, 0]:
                continue
            print(f'  {k:18} in {b[k][0]:>8,} / out {b[k][1]:>8,}  ->  in {a[k][0]:>8,} / out {a[k][1]:>8,}'.replace(',', ' '))
        nb, na = net(b), net(a)
        print(f'  {"net":18} {fmt(nb):>10} -> {fmt(na):>10}  ({(na - nb) * 100 / nb:+.0f} %)\n')
        for side, g in ((False, b), (True, a)):
            for k in GROUPS:
                tot[side][k][0] += g[k][0] * WEIGHT[name]
                tot[side][k][1] += g[k][1] * WEIGHT[name]
    n = sum(WEIGHT.values())
    print(f'the sample ({n} saves weighted), per save on average:')
    for k in GROUPS:
        b, a = tot[False][k], tot[True][k]
        print(f'  {k:18} in {b[0] // n:>7,} / out {b[1] // n:>7,}  ->  in {a[0] // n:>7,} / out {a[1] // n:>7,}'.replace(',', ' '))
    nb, na = net(tot[False]), net(tot[True])
    print(f'  {"net":18} {fmt(nb // n):>9} -> {fmt(na // n):>9}  ({(na - nb) * 100 / nb:+.0f} % of the net inflow)')
    rich = ('rich_assets', 'rich_saver')
    cut = {nm: net(play(PROFILES[nm], False, runs)) - net(play(PROFILES[nm], True, runs)) for nm in PROFILES}
    share = sum(cut[nm] * WEIGHT[nm] for nm in rich) * 100 / sum(cut[nm] * WEIGHT[nm] for nm in PROFILES)
    print(f'  share of the cut paid by the rich profiles ({sum(WEIGHT[r] for r in rich)} saves): {share:.0f} %')
    # A scenario, not a forecast: one rich player in BUYERS buys one of the new models halfway through (its price
    # leaves the economy, plus its bills for the days left). Prod's last two days had 101k of vehicles and 330k of
    # homes bought, so the rich do buy what is offered.
    buyers = sum(WEIGHT[r] for r in rich) / BUYERS
    V = gr.VEHICLES[BUY]
    extra = buyers * (V['price'] + up.daily_milli(V['price'], up.car_bp(BUY, V['price'])) * (DAYS // 2) // 1000)
    print(f'  ... and if one rich player in {BUYERS} buys the {V["name"]} ({V["price"]:,} xu) on day {DAYS // 2}: '
          f'{fmt(int(na - extra) // n)} ({(na - extra - nb) * 100 / nb:+.0f} %)'.replace(',', ' '))


kn_new = tuple(kn.LADDER)
if __name__ == '__main__':
    main()
