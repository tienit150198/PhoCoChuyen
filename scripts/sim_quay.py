"""🏪 Quầy của bạn: what a day earns, staffed (game/quay.py) and with the owner at the counter (game/quay_self.py).

    python scripts/sim_quay.py [days]

For every place (cart, stall, kiosk) and a few trades, over `days` life days (default 400), with the game's own
functions on a bare counter (a big fund, no thieves' luck taken out, x3 off):

  staffed      the 1.5.1 counter: the place's slots filled at what they ask, nobody at the counter
  self alone   no staff, the owner stands at the counter every day (a careful player: right dishes, right change, a
               smile, sensible choices; the tricky moments picked at random among their choices)
  self+staff   the staff and the owner together
  ... online   the same with "Bán online" on (orders packed right, shipped yourself or by a shipper)
  sloppy       no staff, the owner at the counter making mistakes (1 dish in 4 wrong, change wrong 1 in 4, no smile)

Prints the average net a life day (after goods, wages, power and the rent's share), the days with a profit, and the
same for a staffed counter with a dear (120 %) or a cheap (85 %) board of 4 dishes. A milk tea day of the career
pays a player about 60-450 xu (scripts/sim_economy.py PROFILES: work 60 new, 120 median, 450 upper).
"""
from __future__ import annotations

import random
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from game import quay as qy           # noqa: E402
from game import quay_self as qs      # noqa: E402
from game.engine import GameError     # noqa: E402

TRADES = ('milk_tea', 'tra_da', 'florist', 'clothing')


def bare(place, trade, seed=7, staff=True, online=False, board=None):
    s = {'journey': {'seed': seed, 'life_day': 1, 'wallet': 10**6, 'story': True, 'history': [], 'in_debt': False,
                     'stats': {'max_wallet': 0}}, 'careers': {}}
    st = dict(id='q1', trade=trade, place=place, name='X', opened=0, day=0, fund=10**6, till=0, order='vua', due=0, left=0,
              rep=100, items=[], staff=[], case=None, theft=0, hist=[], log=[])
    if staff:
        for c in qy.candidates(s, st)[:qy.PLACES[place]['slots']]:
            st['staff'].append(dict(id=c['id'], name=c['name'], wage=c['ask'], ask=c['ask'], mo=60, d=0, g=c['g']))
    if online:
        st['online'] = True
    if board:
        st['menu'] = board
    return s, st


def play_day(s, st, day, rng, care=1.0):
    """The owner's day at the counter, step by step through game/quay_self.action."""
    s['journey']['life_day'] = day
    qs.action(s, 'jr_quay_start', {'stall': st['id']}, st)
    run = st['run']
    for _ in range(40):
        n = qs.pending_event(run)
        if n is not None:
            from game.quay_events import BY_ID
            picks = BY_ID[run['ev'][n]]['picks']
            if care >= 1:   # a sensible owner: the choice worth most on average (money, customers, name, stars)
                worth = lambda pk: sum(w * (o.get('m', 0) + 0.5 * o.get('b', 0) + 0.3 * o.get('r', 0) + 0.3 * o.get('s', 0)) for w, o in pk[2]) / sum(w for w, _ in pk[2])  # noqa: E731
                pick = max(picks, key=worth)[0]
            else:
                pick = rng.choice(picks)[0]
            qs.action(s, 'jr_quay_choose', {'stall': st['id'], 'pick': pick}, st)
            continue
        for jn, done in enumerate(run['on']):
            o = qs.order(s, st, run, jn)
            if not done and (run['i'] >= o['at'] - 1 or run['i'] >= run['k']) and run['u'] < run['sk']:
                ok = rng.random() < 0.6 + 0.4 * care
                way = 'self' if rng.random() < 0.5 else 'ship'
                qs.action(s, 'jr_quay_ship', {'stall': st['id'], 'order': jn, 'items': o['items'] if ok else o['items'][:1] + o['items'][:1],
                                              'seal': True, 'tool': o['tool'] if ok else not o['tool'], 'note': o['sticker'], 'way': way,
                                              'route': o['route'] if ok else ['L', 'L', 'L']}, st)
        if run['i'] >= run['k'] or run['u'] >= run['sk']:
            break
        c = qs.customer(s, st, run, run['i'])
        right = rng.random() < 0.75 + 0.25 * care
        items = c['items'] if right else [d for d in qs.menu(st)['on'] if d not in c['items']][:1] or c['items']
        change = c['pay'] - c['total']
        if rng.random() > 0.75 + 0.25 * care:
            change += rng.choice((-2, -1, 1, 5))
            change = max(0, change)
        qs.action(s, 'jr_quay_serve', {'stall': st['id'], 'items': items, 'change': change, 'smile': care >= 1 or rng.random() < 0.3}, st)
    try:
        qs.action(s, 'jr_quay_close', {'stall': st['id']}, st)
    except GameError:
        pass


def simulate(place, trade, days, mode, online=False, board=None, staff=None):
    staffed = mode in ('staffed', 'both') if staff is None else staff
    s, st = bare(place, trade, staff=staffed, online=online, board=board)
    rng = random.Random(f'{place}{trade}{mode}{online}')
    nets = []
    with mock.patch.object(qy, '_x3', lambda t: False):
        for d in range(1, days + 1):
            st['left'] = 0
            st['case'] = None
            if mode == 'staffed':
                s['journey']['life_day'] = d + 1
                qy.run_day(s, st, d)
                st['day'] = d
            else:
                play_day(s, st, d, rng, care=0.0 if mode == 'sloppy' else 1.0)
            nets.append(st['hist'][-1]['net'] if st['hist'] and st['hist'][-1]['d'] == d else 0)
    rent = qy.PLACES[place]['rent'] / qy.MONTH_DAYS
    return sum(nets) / len(nets) - rent, sum(n > 0 for n in nets) / len(nets)


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    modes = [('staffed', dict(mode='staffed')), ('self alone', dict(mode='self')), ('self+staff', dict(mode='both')),
             ('self alone online', dict(mode='self', online=True)), ('self+staff online', dict(mode='both', online=True)),
             ('staffed online', dict(mode='staffed', online=True)), ('sloppy alone', dict(mode='sloppy'))]
    print(f'net xu a life day after rent ({days} days), % of days with a profit')
    print(f'{"":22}' + ''.join(f'{p:>16}' for p in qy.PLACE_IDS))
    for trade in TRADES:
        print(trade)
        for label, kw in modes:
            row = [simulate(p, trade, days, **kw) for p in qy.PLACE_IDS]
            print(f'  {label:20}' + ''.join(f'{n:9.1f} ({w:3.0%})' for n, w in row))
        for label, pct in (('staffed dear 120%', 120), ('staffed cheap 85%', 85)):
            rows = qs.MENUS[trade][:4]
            board = dict(on=[d[0] for d in rows], p={d[0]: max(qs.band(d[3])[0], min(qs.band(d[3])[1], round(d[3] * pct / 100))) for d in rows})
            row = [simulate(p, trade, days, 'staffed', board=board) for p in qy.PLACE_IDS]
            print(f'  {label:20}' + ''.join(f'{n:9.1f} ({w:3.0%})' for n, w in row))


if __name__ == '__main__':
    main()
