"""🛡️ Rủi ro & bảo hiểm, 💰 Tiệm vàng (docs/ECONOMY_RISKS.md): 60 life days of plausible players, through the game's
own code (game/rui.py, game/vang.py and the mornings of the bank, the homes and the month's bills).

    python scripts/sim_risks.py [saves per archetype]

Archetypes (what they earn a life day, what they own, how they keep their money):
  new        a newcomer from life day 1: 60 xu a day, a rented room from day 10, cash in the wallet, no bank
  average    the median player from life day 20: 120 a day, a xe số, a bank account, 600 saved, a few hundred in cash
  rich       from life day 40: 3 000 a day, the riverside villa + a penthouse + a nhà có sân, 5 vehicles (rides the jet),
             60 000 saved, 5 000 in cash
  x3 farmer  from life day 30: plays only the career of the day's 🔥 x3 (about 1 500 a day, a 3 000 cap day now and
             then), a xe tay ga and a small car, rents, keeps most of it in cash
Behaviours: careless (never prevents, never insures, picks the first choice of a card if it can pay, else waits),
careful (prevents what is warned, insures what it owns, buys the gear, banks the cash when told), mixed (half the
warnings, BHYT only). Each save is its own journey seed.

Prints, per archetype and behaviour: what the 60 days earned, what the risks cost (events, prevention, premiums,
gear; money the police found back counted against it), that as a % of the earnings, the events a save met, and the
distribution of the single losses (p50 / p90 / max of each event's xu). Then gold: a player who buys on day 1 and sells
on day 60 (≈ 20 real days, 3 life days a real day), over many salts (= many possible price walks).
"""
from __future__ import annotations

import os
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('MNL_X3_OFF', '1')

from game import bank as bk        # noqa: E402
from game import garage as gr      # noqa: E402
from game import housing as hs     # noqa: E402
from game import journey as jr     # noqa: E402
from game import reno as rn        # noqa: E402
from game import rui               # noqa: E402
from game import upkeep as up      # noqa: E402
from game import vang              # noqa: E402
from game.engine import new_state  # noqa: E402

DAYS = 60
ARCH = {
    'new': dict(start=1, pay=60, living=11, cars=[], homes=[], save=0, cash=60, bank=False, rent_from=10, ch=lambda d: 1 + (d >= 4) + (d >= 12)),
    'average': dict(start=20, pay=120, living=16, cars=['xe_so'], homes=[], save=600, cash=250, bank=True, keep=400),
    'rich': dict(start=40, pay=3000, living=36, cars=['xe_ga', 'o_to_suv', 'mui_tran', 'du_thuyen', 'phan_luc'], ride='phan_luc',
                 homes=['biet_thu_song', 'penthouse', 'nha_san'], save=60000, cash=5000, bank=True, keep=5000),
    'x3 farmer': dict(start=30, pay=1500, living=20, cars=['xe_ga', 'o_to_mini'], ride='o_to_mini', homes=[], save=2000,
                      cash=3000, bank=True, keep=10**9, rent=True, x3=True),
}
BEHAVIOURS = ('careless', 'mixed', 'careful')


def make(a: dict, seed: int) -> dict:
    s = new_state()
    jr.enable_story(s, seed)
    j = s['journey']
    j['gender'] = 'female'
    j['intro'] = True
    j['life_day'] = a['start']
    j['chapter'] = a.get('ch', lambda d: 4)(a['start'])
    j['done'] = list(range(1, j['chapter']))
    j['wallet'] = a['cash']
    if a['bank']:
        j['bank'] = bk.initial(seed, a['start'])
        j['bank']['balance'] = a['save']
    if a['cars']:
        g = j['garage'] = gr.initial()
        for vid in a['cars']:
            g['cars'][vid] = dict(c=gr.VEHICLES[vid]['paint'], n='', d=1, p=gr.VEHICLES[vid]['price'])
        g['ride'] = a.get('ride', a['cars'][0])
    if a['homes']:
        h = j['home'] = hs.initial(1)
        mk = lambda i, k: dict(id=f'h{i}', kind=k, price=hs.HOMES[k]['price'], day=1, down=hs.HOMES[k]['price'],
                               fee=hs.buy_fee(hs.HOMES[k]['price']), joint=0, loan=None, mv=0, let=None, keep=None)
        h['own'] = mk(1, a['homes'][0])
        h['props'] = [mk(i + 2, k) for i, k in enumerate(a['homes'][1:])]
    if a.get('rent'):
        j['home'] = hs.initial(1)
        j['home']['rent'] = dict(kind='tro_moi', since=1, deposit=hs.HOMES['tro_moi']['deposit'])
    return s


def morning(s: dict) -> list:
    out = []
    for f in (bk.on_life_day, hs.on_life_day, rn.on_life_day, up.on_life_day, rui.on_life_day):
        try:
            out += f(s) or []
        except Exception as err:   # a hand-made fixture the real game would not hold: say so, keep going
            raise RuntimeError(f'{f.__module__}: {err}')
    return out


def run(name: str, a: dict, how: str, seed: int, events: list) -> dict:
    s = make(a, seed)
    j = s['journey']
    rng = random.Random(f'sim|{seed}|{how}')
    up.on_life_day(s)
    rui.on_life_day(s)
    earned = 0
    if how == 'careful':
        for pid in rui.POLICIES:
            if rui.insurable(s, pid):
                rui.action(s, 'jr_rui_pol', dict(id=pid, on=True))
    elif how == 'mixed':
        rui.action(s, 'jr_rui_pol', dict(id='yte', on=True))
    for _ in range(DAYS):
        pay = a['pay']
        if a.get('x3') and rng.random() < .15:
            pay += 1500                                  # a day the x3 bonus hits its cap
        pay = int(pay * rng.uniform(.8, 1.2))
        earned += pay
        jr._wallet(j, pay, 'salary', 'Lương')
        jr._wallet(j, -a['living'], 'living', 'Cơm nước')
        if a.get('rent_from') and j['life_day'] == a['rent_from'] and j['wallet'] > 80:
            j['home'] = hs.initial(j['life_day'])
            j['home']['rent'] = dict(kind='tro_moi', since=j['life_day'], deposit=hs.HOMES['tro_moi']['deposit'])
        if j['chapter'] < 3 and a.get('ch'):
            j['chapter'] = a['ch'](j['life_day'])
            j['done'] = list(range(1, j['chapter']))
        b = bk.get(s)
        if b and j['wallet'] > a.get('keep', 10**9):                 # the habit of banking what is above `keep`
            x = j['wallet'] - a['keep']
            j['wallet'] -= x
            b['balance'] += x
        j['life_day'] += 1
        morning(s)
        r = rui.get(s)
        if r and r['warn'] and (how == 'careful' or how == 'mixed' and rng.random() < .5):
            if how == 'careful' and r['warn']['kind'] in ('moc', 'trom'):
                for g in ('tui', 'khoa', 'ket'):
                    if g not in r['gear'] and rui._have(s) > rui.GEAR[g]['price'] * 20:
                        rui.action(s, 'jr_rui_gear', dict(id=g))
            opts = [o for o in rui.warn_options(s, r) if o['ok']]
            if opts and r['warn']:
                rui.action(s, 'jr_rui_prevent', dict(opt=opts[0]['id']))
        r = rui.get(s)
        if r and r['card']:
            c = r['card']
            events.append((name, how, c['kind'], c['sub'], c['loss']))
            opts = rui.options(s, r)
            pick = next((o for o in opts if o['ok'] and (how != 'careless' or o['cost'] <= j['wallet'] + 10**9)), None)
            if how == 'careless' and rng.random() < .3:
                pick = None                              # left for later: the default after CARD_DAYS
            if pick:
                rui.action(s, 'jr_rui_choose', dict(id=c['id'], choice=pick['id']))
        for fix in list((rui.get(s) or {}).get('broken', {}).get('xe', {})):
            if how != 'careless' and rui._have(s) > rui.broken_cost(s, 'xe', fix) * 5:
                rui.action(s, 'jr_rui_fix', dict(kind='xe', ref=fix))
    r = rui.get(s)
    st = r['stats']
    cost = st.get('paid', 0) + st.get('lost', 0) + st.get('premiums', 0) + st.get('gear', 0) - st.get('back', 0)
    return dict(earned=earned, cost=cost, events=st.get('events', 0), warned=st.get('warned', 0),
                prevented=st.get('prevented', 0), premiums=st.get('premiums', 0), waived=st.get('waived', 0))


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else 0


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    print(f'{DAYS} life days, {n} saves per archetype and behaviour. xu.\n')
    print(f'{"archetype":10} {"behaviour":9} {"earned":>9} {"risk cost":>10} {"% earned":>8} {"events":>6} {"warned":>6} '
          f'{"prevented":>9} {"premiums":>8} {"p90 cost":>9} {"worst":>7}')
    for name, a in ARCH.items():
        for how in BEHAVIOURS:
            events: list = []
            # each save's events and their own losses: the single events' xu come from the stats of one-event saves
            rows = [run(name, a, how, 1000 + i, events) for i in range(n)]
            earned = statistics.mean(r['earned'] for r in rows)
            costs = [r['cost'] for r in rows]
            print(f'{name:10} {how:9} {earned:>9,.0f} {statistics.mean(costs):>10,.0f} {statistics.mean(costs) * 100 / earned:>7.1f}% '
                  f'{statistics.mean(r["events"] for r in rows):>6.1f} {statistics.mean(r["warned"] for r in rows):>6.1f} '
                  f'{statistics.mean(r["prevented"] for r in rows):>9.1f} {statistics.mean(r["premiums"] for r in rows):>8,.0f} '
                  f'{pct(costs, .9):>9,} {max(costs):>7,}'.replace(',', ' '))
            kinds: dict = {}
            for _, _, k, sub, loss in events:
                kinds[k] = kinds.get(k, 0) + 1
            print(' ' * 21 + 'events by kind: ' + ', '.join(f'{k} {v / n:.2f}' for k, v in sorted(kinds.items())))
    # Gold: bought on life day 1, sold on life day 60 (20 real days); many walks (salts) from many start dates.
    import datetime
    outs = []
    for i in range(400):
        os.environ['MNL_GOLD_SALT'] = f'sim-{i}'
        vang._walk.cache_clear()
        d0 = vang.EPOCH + datetime.timedelta(days=30 + i % 60)
        p0, p1 = vang.price(d0), vang.price(d0 + datetime.timedelta(days=20))
        outs.append((vang.sell_price(p1) - vang.buy_price(p0)) * 100 / vang.buy_price(p0))
    outs.sort()
    print(f'\ngold, held 20 real days (400 walks): mean {statistics.mean(outs):+.1f} %, p10 {pct(outs, .1):+.1f} %, '
          f'median {pct(outs, .5):+.1f} %, p90 {pct(outs, .9):+.1f} %, a gain in {sum(x > 0 for x in outs) * 100 // len(outs)} % of the walks')
    outs = []
    for i in range(400):
        os.environ['MNL_GOLD_SALT'] = f'sim-{i}'
        vang._walk.cache_clear()
        d0 = vang.EPOCH + datetime.timedelta(days=30 + i % 60)
        p0, p1 = vang.price(d0), vang.price(d0 + datetime.timedelta(days=60))
        outs.append((vang.sell_price(p1) - vang.buy_price(p0)) * 100 / vang.buy_price(p0))
    outs.sort()
    print(f'gold, held 60 real days: mean {statistics.mean(outs):+.1f} %, p10 {pct(outs, .1):+.1f} %, median {pct(outs, .5):+.1f} %, '
          f'p90 {pct(outs, .9):+.1f} %, a gain in {sum(x > 0 for x in outs) * 100 // len(outs)} % of the walks')


if __name__ == '__main__':
    main()
