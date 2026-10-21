"""🤖 Tự nhập hàng: a player's counters restock themselves "như lần trước" (player feedback #461, owner 21/10: "làm sao
để chuỗi quầy của mình tự nhập hàng được vậy").

One switch for all of a player's counters, off by default. While it is on, a counter whose shelf falls under LOW_PCT %
of its storage capacity buys its last manual order again (business['again'], the 🔁 Nhập lại như lần trước plan), cut
to the room left in the stock room and the 'Nhập hàng mỗi lần' batch limit, and only the dishes on its board (staff
sell nothing else). It is paid exactly as a manual restock without the wallet flag: quay_business.goods_cost (the same
unit costs), quay_business.shelve (the till, then the fund; one goods expense, the Lãi line adds the shelf back).
Never the wallet, the bank account or a loan: a counter whose till + fund cannot pay is skipped ("Thiếu vốn").

Daily cap, per counter and per Vietnam day: at most DAY_SHARE % of the counter's till + fund at its first automatic
restock of that day (`base`); an order that does not fit what is left of it is cut down to fit (as 🔁 Tự đặt hàng
does in game/auto_order.py, #411), nothing when nothing fits ("Hết mức tự nhập hôm nay").

When (quay_business._settle, the staff sales loop): after each staff sale at that sale's own time; for an empty counter
at the settlement's cursor and again at each Vietnam midnight before now. Sales have absolute timestamps and an empty
counter's money does not move, so a catch-up after days offline buys what live polling would have bought, and settling
the same time twice buys nothing twice (the cursor has moved).

Save (all OPTIONAL keys; 2.5.0.1 and older ignore them: journey quay and business validators only require their own
keys, tests/test_quay_auto.py):
    journey.quay['auto_restock'] = True         # the switch (absent: off)
    business['auto'] = {'day', 'base', 'spent', # today's (Vietnam day) cap and spend
                        'at',                   # optional: ms of the last automatic restock
                        'why', 'cash'}          # optional: the last attempt bought nothing ('cash' | 'cap' | 'idle'),
                                                #   with the till + fund then (the load settlement skips it till they move)
"""
from __future__ import annotations

KEY = 'auto_restock'   # journey.quay[KEY] is True: on
STATE = 'auto'         # business[STATE]
LOW_PCT = 20           # restock under this % of the storage capacity
DAY_SHARE = 30         # at most this % of the counter's till + fund, per Vietnam day
VN = 7 * 3600          # UTC+7
DAY_MS = 86400 * 1000
WHY = ('cash', 'cap', 'idle')
LOG = 'Tự nhập hàng như lần trước'


def vn_day(at):
    """The Vietnam day number of `at` (ms)."""
    return (at // 1000 + VN) // 86400


def next_midnight(at):
    """The first Vietnam midnight after `at` (ms)."""
    return ((vn_day(at) + 1) * 86400 - VN) * 1000


def on(s):
    from . import quay as qy
    return (qy.get(s) or {}).get(KEY) is True


def _low(st):
    from .quay_progression import limit
    b = st['business']
    return sum(b['stock'].values()) * 100 < limit(b, 'storage') * LOW_PCT


def _plan(st):
    """{dish: portions}: the last manual order cut to the room left and the batch limit, dishes on the board only."""
    from . import quay_self as qs
    from .quay_progression import limit
    from .player_service_tasks import reserved
    b = st['business']
    board = set(qs.menu(st)['on'])
    room = max(0, min(limit(b, 'restock'), limit(b, 'storage') - sum(b['stock'].values()) - reserved(st)))
    items = {}
    for d, n in (b.get('again') or {}).items():
        q = min(n, room)
        if d in board and q > 0:
            items[d] = q
            room -= q
    return items


def _today(st, at):
    b = st['business']
    a = b.get(STATE)
    if not a or a['day'] != vn_day(at):
        a = b[STATE] = dict(day=vn_day(at), base=st['till'] + st['fund'], spent=0, **({'at': a['at']} if a and 'at' in a else {}))
    return a


def attempt(s, st, at):
    """One check of one counter at `at` (ms): restock it if it is under the threshold. True when it bought."""
    from . import quay as qy
    from . import quay_business as qb
    b = st['business']
    if not b.get('again') or not _low(st):
        return False
    a = _today(st, at)
    items = _plan(st)
    cost = qb.goods_cost(st, items)
    left = max(0, a['base'] * DAY_SHARE // 100 - a['spent'])
    why = 'idle' if not items else None
    if items and cost > left:   # cut to what is left of today's cap, each dish in proportion
        items = {d: n * left // cost for d, n in items.items() if n * left // cost > 0}
        cost = qb.goods_cost(st, items)
        why = None if items else 'cap'
    cash = st['till'] + st['fund']
    if why is None and cost > cash:
        why = 'cash'
    if why:
        a.update(why=why, cash=cash)
        return False
    a.pop('why', None)
    a.pop('cash', None)
    qb.shelve(st, items, cost)
    a['spent'] += cost
    a['at'] = int(at)
    day = int(s['journey']['life_day'])
    last = st['log'][-1] if st['log'] else None
    if last and last['t'] == LOG and last['d'] == day and last['a'] - cost >= -qy.MONEY_MAX:
        last['a'] -= cost   # one line a day in the counter's book, not one per sale
    else:
        qy._log(st, day, LOG, -cost)
    return True


def due(st, at):
    """An empty counter the load settlement should try again: something moved since its last attempt bought nothing."""
    from .quay_business import status
    b = st.get('business')
    if not isinstance(b, dict) or not b.get('again') or status(st) != 'out_of_stock' or not _low(st):
        return False
    a = b.get(STATE)
    return not (a and a['day'] == vn_day(at) and a.get('why') and a.get('cash') == st['till'] + st['fund'])


def toggle(s, p):
    """jr_quay_auto {on: bool}. Turning it on checks the empty counters at once (their cursor is now)."""
    from . import quay as qy
    from .quay_business import status
    need = qy._core().need
    need(set(p) <= {'on'} and type(p.get('on')) is bool, 'Lựa chọn không hợp lệ.')
    q = qy.get(s)
    if not p['on']:
        q.pop(KEY, None)
        return dict(message='🤖 Tự nhập hàng: Tắt.')
    q[KEY] = True
    n = sum(attempt(s, st, st['business']['cursor']) for st in q['stalls']
            if isinstance(st.get('business'), dict) and status(st) == 'out_of_stock')
    return dict(message='🤖 Tự nhập hàng: Bật.' + (f' Đã nhập cho {n} quầy hết hàng.' if n else ''))


def stall_public(st):
    """business.auto for the counter card: {why, spent, at} (why: 'none' without a last order; today's 'cash' / 'cap')."""
    b = st['business']
    a = b.get(STATE) or {}
    today = a.get('day') == vn_day(b['cursor'])
    why = 'none' if not b.get('again') else a.get('why') if today and a.get('why') in ('cash', 'cap') else None
    return dict(why=why, spent=a.get('spent', 0) if today else 0, at=a['at'] / 1000 if 'at' in a else None)


def public(s, q, now):
    """quay.auto: the switch and today's automatic restocks over all counters (now: seconds)."""
    day = vn_day(int(now * 1000))
    rows = [st['business'][STATE] for st in q.get('stalls', ()) if isinstance(st.get('business'), dict) and st['business'].get(STATE)]
    done = [a for a in rows if a['day'] == day and a['spent'] > 0]
    last = max((a['at'] for a in rows if 'at' in a), default=None)
    return dict(on=q.get(KEY) is True, low=LOW_PCT, share=DAY_SHARE, n=len(done), xu=sum(a['spent'] for a in done),
                at=last / 1000 if last is not None else None)


def validate_root(q, need):
    if KEY in q:
        need(q[KEY] is True)


def validate(b, need, integer, money):
    if STATE not in b:
        return
    a = b[STATE]
    need(isinstance(a, dict) and {'day', 'base', 'spent'} <= set(a) <= {'day', 'base', 'spent', 'at', 'why', 'cash'})
    need(integer(a['day'], 0, 10**7) and integer(a['base'], 0, 2 * money) and integer(a['spent'], 0, 10**16))
    need(integer(a.get('at', 0), 0, 10**15) and a.get('why', 'idle') in WHY and integer(a.get('cash', 0), 0, 2 * money))
    need(('why' in a) == ('cash' in a))
