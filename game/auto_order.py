"""🔁 Tự đặt hàng: the stock room orders an item again when it runs low (player feedback #387).

A PAID unlock, one per workplace with a stock room (game/inventory.py), owner 14/10: "mua mất tiền thì mới enable".
PRICE is the shared ladder's tier 5 (game/progression_prices.py), the same step as 📦 Bộ đếm kho · Bậc 5 that opens its
pair 🤖 Tự nhận hàng (game/auto_stock.py). Paid from the workplace fund first, then the wallet (story mode).

Save: one OPTIONAL career key c[KEY] (absent: not owned). Older releases (2.4.11) ignore unknown career keys, while a
new id in c['upgrades'] makes their validate refuse the save, so the unlock is NOT an upgrade id
(tests/test_auto_order.py proves a save holding it loads on `git archive rel-2.4.11`).

    c['auto_order'] = {
        'paid': 100000,              # xu paid (the unlock; 350000 for those who bought before 15/10)
        'on': False,                 # optional: the master switch turned off (absent: on)
        'items': {item: {'on': bool, 'below': int, 'qty': int}},   # the player's own settings (absent: defaults)
        'open': {item: order_id},    # the last automatic order per item (one pending at a time)
        'day': int, 'spent': int,    # today's automatic spend (shop day c['day']), against the daily cap
        'warn': int,                 # the shop day the "fund short" notice was last shown (once a day)
    }

Rule per item ("Còn dưới X thì đặt Y"): when the shelf plus what is on the way falls below X, one order of Y (cut to the
shelf room and the order-line limit) is placed with the item's last-used supplier (else the default one), THROUGH
inventory.action('inv_order'): the same prices, wholesale tiers, shipping, lead time, short packing and FIFO lots as a
manual order. Paid from the fund only, and only while it keeps a floor (jr.RESERVE + unpaid bills + a day of wages)
and today's automatic spend stays within DAY_SHARE % of the fund at the start of the day. At most one pending automatic
order per item, and SLOTS_FREE deliveries on the way are always left for the player's own orders.

When: after every command of that workplace and on the server's settlement of a load (the same points as 🤖 Tự nhận
hàng, which runs first), so it works while the player is away. Task generation is not touched.
"""
from __future__ import annotations

import math

from .progression_prices import PRICES

KEY = 'auto_order'
ACTION = 'stock_reorder'
PRICE = 100_000         # owner 15/10: 100.000 xu (was 350.000, tier 5 of the shared ladder)
LOW_PCT = 20            # default X: 20 % of the shelf
FILL_PCT = 90           # default Y: back to about 90 % of the shelf
DAY_SHARE = 50          # at most this % of the fund at the start of the day, per shop day
SLOTS_FREE = 2          # deliveries on the way kept free for the player's own orders
TEASE_ORDERS = 3        # the locked line shows once the player has placed this many orders (#384: no ads for a newcomer)
NAME = '🔁 Tự đặt hàng'


def _inv():
    from . import inventory
    return inventory


def eligible(career: str) -> bool:
    return career != 'pagoda' and bool(_inv().catalogue(career))


def rec(c: dict) -> dict | None:
    r = c.get(KEY) if isinstance(c, dict) else None
    return r if isinstance(r, dict) else None


def owned(c: dict) -> bool:
    return rec(c) is not None


def on(c: dict) -> bool:
    r = rec(c)
    return r is not None and r.get('on') is not False


# ---------------------------------------------------------------- the rule of an item
def limits(c: dict, career: str) -> tuple[int, int]:
    from . import order_progression
    return _inv().capacity(career, c), order_progression.limit(c, career)


def defaults(c: dict, career: str) -> tuple[int, int]:
    cap, line = limits(c, career)
    below = max(1, math.ceil(cap * LOW_PCT / 100))
    return below, max(1, min(line, cap * FILL_PCT // 100 - below))


def rule(c: dict, career: str, item_id: str) -> dict:
    """{on, below, qty} of one item: the player's settings over the defaults."""
    below, qty = defaults(c, career)
    mine = ((rec(c) or {}).get('items') or {}).get(item_id) or {}
    return dict(on=mine.get('on', True), below=mine.get('below', below), qty=mine.get('qty', qty))


# ---------------------------------------------------------------- money
def floor(s: dict, c: dict) -> int:
    """What the fund keeps: the withdrawal reserve, unpaid bills and a day of wages for the hired staff."""
    from . import journey as jr
    from .staff_life import wage
    staff = sum(wage(c['ops'], e) for e in c['ops'].get('staff') or () if isinstance(e, dict) and e.get('status') == 'hired')
    return jr.RESERVE + jr._unpaid(c) + staff


def budget(c: dict) -> int:
    return max(0, c.get('day_start_money', 0)) * DAY_SHARE // 100


def spent(c: dict) -> int:
    r = rec(c) or {}
    return r.get('spent', 0) if r.get('day') == c['day'] else 0


def supplier_for(c: dict, career: str, item_id: str) -> dict | None:
    """The item's last-used supplier (if it still sells it), else the default one, else the first that sells it."""
    inv = _inv()
    x = c['ext']['inv']
    for o in reversed(x['orders']):
        if o['item'] == item_id:
            sup = inv.supplier(career, o['supplier'])
            if sup and inv.sells(sup, item_id):
                return sup
            break
    sup = inv.supplier(career, 'partner')
    if sup and inv.sells(sup, item_id):
        return sup
    return next((sp for sp in inv.suppliers(career) if inv.sells(sp, item_id)), None)


def _pending(x: dict, oid) -> bool:
    return bool(oid) and any(o['id'] == oid and o['status'] == 'in_transit' for o in x['orders'])


def plan(s: dict, c: dict, career: str) -> tuple[list, str | None]:
    """([(item, qty, supplier, total xu)], why) the orders a pass would place now (read only).
    why: 'fund' (the fund is below its floor for one of them), 'cap' (today's cap reached) or None."""
    if not on(c) or not eligible(career):
        return [], None
    x = (c.get('ext') or {}).get('inv')
    if not isinstance(x, dict):
        return [], None
    inv = _inv()
    r = rec(c)
    level = 1 + c['xp'] // 90
    cap, line = limits(c, career)
    slots = inv.TRANSIT_CAP - SLOTS_FREE - inv._shipments(x)
    lines = inv.TRANSIT_LINES - SLOTS_FREE - inv._transit_lines(x)
    fund = c['money'] - floor(s, c)
    left = budget(c) - spent(c)
    low = []
    for it in inv.catalogue(career):
        if it.get('unlock', 1) > level or _pending(x, (r.get('open') or {}).get(it['id'])):
            continue
        ru = rule(c, career, it['id'])
        have, coming = inv.count(c, it['id']), inv._in_transit(x, it['id'])
        if ru['on'] and have + coming < ru['below']:
            low.append(((have + coming) / ru['below'], it, ru, have, coming))
    low.sort(key=lambda t: t[0])   # the emptiest shelf first: the free delivery slots go to it
    out, why = [], None
    for _, it, ru, have, coming in low:
        if slots <= 0 or lines <= 0:
            break
        room = cap - have - inv.reserved(c, career, it['id']) - coming - inv._drafted(x, it['id'])
        qty = min(ru['qty'], room, line)
        sup = supplier_for(c, career, it['id']) if qty >= 1 else None
        if not sup:
            continue
        price = inv.line_price(it, qty, sup)
        total = price['cost'] + inv.ship_fee(sup, price['cost'])
        if total > fund:
            why = why or 'fund'
            continue
        if total > left:
            why = why or 'cap'
            continue
        out.append((it, qty, sup, total))
        fund -= total
        left -= total
        slots -= 1
        lines -= 1
    return out, why


def _skip(s: dict, career: str) -> bool:
    j = s.get('journey') or {}
    return career in (j.get('paused') or {})


def due(state: dict) -> bool:
    """Any workplace where a pass would order now, or owes today's notice (read only; a load's cheap check)."""
    for cid, c in ((state or {}).get('careers') or {}).items():
        try:
            if not on(c) or not c.get('started') or _skip(state, cid):
                continue
            got, why = plan(state, c, cid)
            if got or (why and rec(c).get('warn') != c['day']):
                return True
        except (KeyError, TypeError, ValueError, AttributeError):
            continue   # an odd record: the command path validates it
    return False


# ---------------------------------------------------------------- placing
def run(s: dict, c: dict, career: str) -> list[str]:
    """Place what is due in this workplace. Returns the player's effect lines ([] when nothing)."""
    if not on(c) or _skip(s, career):
        return []
    from . import engine as e
    inv = _inv()
    got, why = plan(s, c, career)
    r = rec(c)
    if r.get('day') != c['day']:
        r['day'], r['spent'] = c['day'], 0
    x = c['ext']['inv']
    r['open'] = {k: v for k, v in (r.get('open') or {}).items() if _pending(x, v)}
    n = paid = 0
    for it, qty, sup, _ in got:
        before = c['money']
        try:
            inv.action(s, c, career, 'inv_order', dict(item=it['id'], qty=qty, supplier=sup['id'], confirm=True))
        except e.GameError:
            continue   # refused as a manual order would be: nothing was paid
        o = x['orders'][-1]
        cost = before - c['money']
        r['open'][it['id']] = o['id']
        r['spent'] += cost
        n += 1
        paid += cost
        clk = inv.clock(c, career)
        eta = inv._eta(o, clk['abs'], c, career, clk)['eta_label']
        e.log(s, c, 'stock', f'🔁 Tự đặt {qty} {it.get("unit", "phần")} {it["name"]} ({sup["name"]}, {eta}).'[:300], ref=o['id'])
    out = [f'🔁 Tự đặt {n} món · {paid:,} xu.'.replace(',', '.')] if n else []
    if why and not got and r.get('warn') != c['day']:
        r['warn'] = c['day']
        text = '🔁 Quỹ không đủ để tự đặt.' if why == 'fund' else '🔁 Hết mức tự đặt hôm nay.'
        e.log(s, c, 'stock', text)
        out.append(text)
    if not r['open']:
        r.pop('open', None)
    return out


def run_all(s: dict) -> list[str]:
    """Every workplace (the load's settlement): its effect lines."""
    out = []
    for cid, c in (s.get('careers') or {}).items():
        if on(c) and c.get('started'):
            out += run(s, c, cid)
    return out


# ---------------------------------------------------------------- the command
def _buy(s: dict, c: dict, career: str, p: dict) -> dict:
    from . import engine as e
    from . import journey as jr
    need = e.need
    need(not owned(c), f'{NAME} đã mở ở nơi này rồi.')
    need(p.get('confirm') is True, f'Xác nhận mua {NAME} trước nhé.')
    j = s.get('journey') or {}
    from_fund = min(max(0, c['money']), PRICE)
    from_wallet = PRICE - from_fund
    if from_wallet:
        wallet = j.get('wallet', 0) if j.get('story') else 0
        need(wallet >= from_wallet, f'Thiếu {max(0, from_wallet - max(0, wallet)):,} xu (quỹ + ví).'.replace(',', '.'))
        jr._transfer(s, c, from_wallet, f'Góp vốn từ ví · {NAME}', 'owner_capital')
        jr._wallet(j, -from_wallet, 'invest', f'Góp vốn cho {jr._place(career)}', career)
        j['stats']['invested'] += from_wallet
    e.money(s, c, -PRICE, f'Mua {NAME}', category='upgrade')
    c[KEY] = dict(paid=PRICE)
    e.log(s, c, 'upgrade', f'Đã mở {NAME}: kho tự đặt khi sắp hết.')
    return dict(message=f'{NAME} đã mở.' + (f' Ví trả {from_wallet:,} xu.'.replace(',', '.') if from_wallet else ''),
                celebrate=True)


def action(s: dict, c: dict, career: str, p: dict) -> dict:
    """stock_reorder: {buy: true, confirm: true} · {on: bool} (all items) · {item, on?, below?, qty?}. No shop time."""
    from . import engine as e
    need = e.need
    need(eligible(career), 'Nơi này không có kho hàng.')
    if p.get('buy') is True:
        return _buy(s, c, career, p)
    need(owned(c), f'Mua {NAME} trước nhé.')
    r = rec(c)
    if 'item' not in p:
        value = p.get('on')
        need(type(value) is bool, 'Lựa chọn không hợp lệ.')
        if value:
            r.pop('on', None)
        else:
            r['on'] = False
        return dict(message=f'{NAME}: {"Bật" if value else "Tắt"}.')
    it = _inv().item(career, p.get('item'))
    cap, line = limits(c, career)
    mine = dict((r.get('items') or {}).get(it['id']) or {})
    if 'on' in p:
        need(type(p['on']) is bool, 'Lựa chọn không hợp lệ.')
        mine['on'] = p['on']
    if 'below' in p:
        mine['below'] = e.integer(p['below'], 1, cap)
    if 'qty' in p:
        mine['qty'] = e.integer(p['qty'], 1, line)
    below, qty = defaults(c, career)
    if mine.get('on') is True:
        mine.pop('on')   # on is the default
    for k, v in (('below', below), ('qty', qty)):
        if mine.get(k) == v:
            mine.pop(k)
    items = r.setdefault('items', {})
    if mine:
        items[it['id']] = mine
    else:
        items.pop(it['id'], None)
    if not items:
        r.pop('items')
    ru = rule(c, career, it['id'])
    return dict(message=f'{it["name"]}: còn dưới {ru["below"]} thì đặt {ru["qty"]}.' if ru['on'] else f'{it["name"]}: không tự đặt.')


# ---------------------------------------------------------------- view and checks
def public(s: dict, c: dict, career: str) -> dict | None:
    """warehouse.reorder for the Kho sheet and Thiết bị (None: no stock room)."""
    if not eligible(career):
        return None
    r = rec(c)
    if r is None:
        j = s.get('journey') or {}
        wallet = max(0, j.get('wallet', 0)) if j.get('story') else 0
        return dict(owned=False, price=PRICE, short=max(0, PRICE - max(0, c['money']) - wallet),
                    tease=c['metrics'].get('purchases', 0) >= TEASE_ORDERS)
    inv = _inv()
    x = c['ext']['inv']
    level = 1 + c['xp'] // 90
    cap, line = limits(c, career)
    items = [dict(id=it['id'], **rule(c, career, it['id']), auto=_pending(x, (r.get('open') or {}).get(it['id'])))
             for it in inv.catalogue(career) if it.get('unlock', 1) <= level]
    return dict(owned=True, price=PRICE, on=on(c), items=items, cap=cap, line=line, floor=floor(s, c),
                budget=budget(c), spent=spent(c), warn=r.get('warn') == c['day'])


def validate(c: dict, career: str) -> None:
    from .engine import need, integer, clean_text
    r = c.get(KEY)
    if r is None:
        return
    need(eligible(career) and isinstance(r, dict) and set(r) <= {'paid', 'on', 'items', 'open', 'day', 'spent', 'warn'}
         and 'paid' in r, 'Tự đặt hàng không hợp lệ.')
    integer(r['paid'], 0, 10**9)
    need(r.get('on', False) is False, 'Tự đặt hàng không hợp lệ.')
    for k in ('day', 'spent', 'warn'):
        if k in r:
            integer(r[k], 0, 10**9)
    ids = {it['id'] for it in _inv().catalogue(career)}
    items = r.get('items', {})
    need(isinstance(items, dict) and set(items) <= ids, 'Tự đặt hàng không hợp lệ.')
    for v in items.values():
        need(isinstance(v, dict) and set(v) <= {'on', 'below', 'qty'} and type(v.get('on', True)) is bool, 'Tự đặt hàng không hợp lệ.')
        for k in ('below', 'qty'):
            if k in v:
                integer(v[k], 1, 10**6)
    opened = r.get('open', {})
    need(isinstance(opened, dict) and set(opened) <= ids, 'Tự đặt hàng không hợp lệ.')
    for v in opened.values():
        clean_text(v, 80)
