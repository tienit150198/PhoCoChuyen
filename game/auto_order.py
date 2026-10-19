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

Player feedback #411 ("cài dưới 52 đặt 182 mà nó cứ để tuột xuống 0 mới bổ sung"): when what is left of the fund or of
today's cap covers only part of Y, a smaller order (the most it covers, at least Y / PART_MIN) is placed instead of
none, so a shelf is topped up a little rather than left to run dry until the next day. The view tells "hết mức hôm
nay" (the daily cap) apart from "quỹ thiếu" (the fund floor), `reorder.why`.

📦 Gộp thùng tự đặt (owner 16/10, player feedback #391: "bật 18 món là 18 lần mở thùng rồi 18 lần kiểm hàng"; "mất
10k xu để mua"): a second paid unlock, BOX_PRICE, once 🔁 Tự đặt hàng is owned. Every automatic order at the door then
shows as ONE crate (inventory.public tags it `box: 'auto'`) and is received in ONE inv_receive {box: 'auto', counts}
(one shop step instead of one per crate; each line still counted, a short line claimed as before). The orders
themselves are not changed (still one per item, its own supplier and van), so nothing new is saved on them. Save: an
OPTIONAL career key c[BOX_KEY] = {'paid': int} (absent: not owned), outside c[KEY] whose keys an older release checks.

When: after every command of that workplace and on the server's settlement of a load (the same points as 🤖 Tự nhận
hàng, which runs first), so it works while the player is away. Task generation is not touched.

🍼 💊 The older stock desks (Mẹ & bé, Nhà thuốc: game/convenience.py LEGACY, c['stock'] and c['shipments'], player
feedback #433 "Sao trong tiệm mẹ và bé lại ko có nút nhập hàng tự động vậy?"): the same unlock (PRICE, fund then
wallet, the same Thiết bị card and Kho line), the same rule per item, floor, daily cap, partial order (#411) and one
pending order per item, placed THROUGH engine.order_stock (the desk's own prices, suppliers, schedule, van limit and
shelf check). The desk merges orders by itself (F#194: one van, one payment), so the lines a pass orders from one
supplier go as one merged order and 📦 Gộp thùng tự đặt is not sold there (`box` None). Save: c[DESK_KEY], the same
shape as c[KEY]. Not c[KEY]: 2.4.58 and older validate c[KEY] only where game/inventory.py's stock room is and would
refuse it on these careers, while they ignore an unknown career key.
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
PART_MIN = 4            # #411: when the money left covers only part of Y, order what it covers, at least Y / PART_MIN
NAME = '🔁 Tự đặt hàng'
BOX_KEY = 'auto_box'
BOX_PRICE = 10_000      # owner 16/10: "mất 10k xu để mua"
BOX_NAME = '📦 Gộp thùng tự đặt'
DESK_KEY = 'auto_order_desk'            # 🍼 💊 the older stock desks: the same shape as c[KEY]
DESK = ('mother_baby', 'pharmacy')      # game/convenience.py LEGACY: c['stock'], c['shipments'], engine.order_stock


def _inv():
    from . import inventory
    return inventory


def desk(career: str) -> bool:
    """🍼 💊 an older stock desk (c['stock'], c['shipments'], engine.order_stock) rather than the stock room."""
    return career in DESK


def eligible(career: str) -> bool:
    return career != 'pagoda' and (desk(career) or bool(_inv().catalogue(career)))


def key_of(career: str) -> str:
    return DESK_KEY if desk(career) else KEY


def rec(c: dict) -> dict | None:
    if not isinstance(c, dict):
        return None
    r = c.get(KEY)
    if r is None:
        r = c.get(DESK_KEY)   # one or the other: validate allows each only on its own kind of workplace
    return r if isinstance(r, dict) else None


def catalogue(career: str) -> list[dict]:
    """What an automatic order may place: the stock room's catalogue, or the desk's products / valid lots."""
    if not desk(career):
        return _inv().catalogue(career)
    from .content import PRODUCTS, LOT_INDEX
    if career == 'mother_baby':
        return PRODUCTS
    return [x for x in LOT_INDEX.values() if x['status'] == 'available']


def _item(career: str, item_id) -> dict:
    if not desk(career):
        return _inv().item(career, item_id)
    from .engine import need
    it = next((x for x in catalogue(career) if x['id'] == item_id), None)
    need(it is not None, 'Mã hàng không hợp lệ.')
    return it


def owned(c: dict) -> bool:
    return rec(c) is not None


def box_owned(c: dict) -> bool:
    return isinstance(c, dict) and isinstance(c.get(BOX_KEY), dict)


def box_ids(c: dict) -> set:
    """The automatic orders that ride in the one crate (📦 Gộp thùng tự đặt owned), else none."""
    r = rec(c)
    return set((r.get('open') or {}).values()) if r is not None and box_owned(c) else set()


def on(c: dict) -> bool:
    r = rec(c)
    return r is not None and r.get('on') is not False


# ---------------------------------------------------------------- the rule of an item
def limits(c: dict, career: str) -> tuple[int, int]:
    if desk(career):   # what engine.order_stock checks: Kho & đơn nhập (logistics) sets the shelf and the line
        from . import convenience as cv
        return cv.capacity(c, career), cv.LINE[cv.tier(c, career, 'logistics')]
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


def _total(it: dict, qty: int, sup: dict) -> int:
    inv = _inv()
    cost = inv.line_price(it, qty, sup)['cost']
    return cost + inv.ship_fee(sup, cost)


def _most(it: dict, qty: int, sup: dict, money: int, least: int, total=None) -> tuple[int, int] | None:
    """(qty, total) of the largest order below `qty`, at least `least`, whose total fits `money`; None when none does.
    `total`: the price of a quantity (default the stock room's _total; the desk passes _desk_total)."""
    total = total or _total
    lo, hi, best = least, qty - 1, None
    while lo <= hi:   # the total grows with the quantity (a wholesale tier may dip it: the found one is checked)
        mid = (lo + hi) // 2
        t = total(it, mid, sup)
        if t <= money:
            best, lo = (mid, t), mid + 1
        else:
            hi = mid - 1
    return best


def _pending(x: dict, oid) -> bool:
    return bool(oid) and any(o['id'] == oid and o['status'] == 'in_transit' for o in x['orders'])


def _waiting(c: dict, career: str, oid) -> bool:
    """The automatic order `oid` is still on the way (the stock room's order, or the desk's shipment)."""
    if desk(career):
        return bool(oid) and any(x['id'] == oid and x['status'] == 'in_transit' for x in c.get('shipments') or ())
    return _pending(c['ext']['inv'], oid)


# ---------------------------------------------------------------- 🍼 💊 the older stock desks
def _desk_supplier(c: dict, career: str, item_id: str) -> dict | None:
    """The item's last-used supplier (if it still delivers), else the desk's default one."""
    from . import engine as e
    for x in reversed(c.get('shipments') or []):
        if x['item'] == item_id:
            sup = e._stock_supplier(career, x.get('supplier'))
            if sup:
                return sup
            break
    return e._stock_supplier(career, e.STOCK_DEFAULT)


def _desk_total(it: dict, qty: int, sup: dict) -> int:
    return max(1, math.ceil(it['cost'] * qty * sup['factor']))   # engine.order_stock's price (no shipping fee)


def _desk_plan(s: dict, c: dict, career: str) -> tuple[list, str | None]:
    """plan() for an older stock desk. The lines one supplier gets in a pass ride in one merged order (one van, at
    most STOCK_LINES lines); SLOTS_FREE vans stay free for the player's own orders."""
    from . import convenience as cv
    from . import engine as e
    r = rec(c)
    line = limits(c, career)[1]
    slots = e.STOCK_VANS - SLOTS_FREE - e.stock_vans(c)
    held = set(c.get('held_lots') or ())   # 💊 a lot the player held back is not ordered again
    fund = c['money'] - floor(s, c)
    left = budget(c) - spent(c)
    low = []
    for it in catalogue(career):
        if it['id'] in held or _waiting(c, career, (r.get('open') or {}).get(it['id'])):
            continue
        ru = rule(c, career, it['id'])
        have = c['stock'].get(it['id'], 0)
        coming = sum(x['qty'] for x in c['shipments'] if x['item'] == it['id'] and x['status'] != 'received')
        if ru['on'] and have + coming < ru['below']:
            low.append(((have + coming) / ru['below'], it, ru))
    low.sort(key=lambda t: t[0])   # the emptiest shelf first: the free vans go to it
    out, why, lines = [], None, {}
    for _, it, ru in low:
        qty = min(ru['qty'], cv.room(c, career, it['id']), line)
        sup = _desk_supplier(c, career, it['id']) if qty >= 1 else None
        if not sup:
            continue
        n = lines.get(sup['id'], 0)
        if n % e.STOCK_LINES == 0 and slots <= 0:
            continue   # this supplier would need one more van: none is left for an automatic order
        total = _desk_total(it, qty, sup)
        if total > min(fund, left):
            # #411: what is left covers part of it: order that part (at least Y / PART_MIN) rather than nothing
            part = _most(it, qty, sup, min(fund, left), max(1, math.ceil(ru['qty'] / PART_MIN)), _desk_total)
            if not part:
                why = why or ('fund' if total > fund else 'cap')
                continue
            qty, total = part
        out.append((it, qty, sup, total))
        fund -= total
        left -= total
        if n % e.STOCK_LINES == 0:
            slots -= 1
        lines[sup['id']] = n + 1
    return out, why


def _desk_place(s: dict, c: dict, career: str, got: list) -> tuple[int, int]:
    """Place the planned lines through engine.order_stock: one merged order per supplier (≤ STOCK_LINES lines).
    Returns (lines placed, xu paid)."""
    from . import engine as e
    r = rec(c)
    groups: dict = {}
    for row in got:
        groups.setdefault(row[2]['id'], []).append(row)
    n = paid = 0
    for sid, rows in groups.items():
        for k in range(0, len(rows), e.STOCK_LINES):
            part = rows[k:k + e.STOCK_LINES]
            before = c['money']
            try:
                res = e.order_stock(s, c, career, dict(supplier=sid, lines=[dict(item=it['id'], qty=qty) for it, qty, _, _ in part]))
            except e.GameError:
                continue   # refused as the player's own order would be: nothing was paid
            cost = before - c['money']
            r['spent'] += cost
            paid += cost
            eta = (res.get('eta') or {}).get('eta_label', '')
            for (it, qty, sup, _), x in zip(part, c['shipments'][-len(part):]):
                r['open'][it['id']] = x['id']
                n += 1
                e.log(s, c, 'stock', f'🔁 Tự đặt {qty} món {it["name"]} ({sup["name"]}, {eta}).'[:300], ref=x['id'])
    return n, paid


def plan(s: dict, c: dict, career: str) -> tuple[list, str | None]:
    """([(item, qty, supplier, total xu)], why) the orders a pass would place now (read only).
    why: 'fund' (the fund is below its floor for one of them), 'cap' (today's cap reached) or None."""
    if not on(c) or not eligible(career):
        return [], None
    if desk(career):
        return _desk_plan(s, c, career)
    x = (c.get('ext') or {}).get('inv')
    if not isinstance(x, dict):
        return [], None
    inv = _inv()
    r = rec(c)
    level = 1 + c['xp'] // 90
    cap, line = limits(c, career)
    slots = inv.TRANSIT_CAP - SLOTS_FREE - inv._shipments(x, c)
    # #400 (18 items on auto, 10 ordered): with 📦 Gộp thùng every automatic line rides in the one crate, one van for all
    boxed = box_owned(c)
    van = boxed and any(o['id'] in box_ids(c) for o in x['orders'] if o['status'] == 'in_transit')
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
        if (slots <= 0 and not van) or lines <= 0:
            break
        room = cap - have - inv.reserved(c, career, it['id']) - coming - inv._drafted(x, it['id'])
        qty = min(ru['qty'], room, line)
        sup = supplier_for(c, career, it['id']) if qty >= 1 else None
        if not sup:
            continue
        total = _total(it, qty, sup)
        if total > min(fund, left):
            # #411: what is left covers part of it: order that part (at least Y / PART_MIN) rather than nothing
            part = _most(it, qty, sup, min(fund, left), max(1, math.ceil(ru['qty'] / PART_MIN)))
            if not part:
                why = why or ('fund' if total > fund else 'cap')
                continue
            qty, total = part
        out.append((it, qty, sup, total))
        fund -= total
        left -= total
        if not van:
            slots -= 1
            van = boxed
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
    got, why = plan(s, c, career)
    r = rec(c)
    if r.get('day') != c['day']:
        r['day'], r['spent'] = c['day'], 0
    r['open'] = {k: v for k, v in (r.get('open') or {}).items() if _waiting(c, career, v)}
    n, paid = (_desk_place if desk(career) else _place)(s, c, career, got)
    out = [f'🔁 Tự đặt {n} món · {paid:,} xu.'.replace(',', '.')] if n else []
    if why and not got and r.get('warn') != c['day']:
        r['warn'] = c['day']
        text = '🔁 Quỹ không đủ để tự đặt.' if why == 'fund' else '🔁 Hết mức tự đặt hôm nay.'
        e.log(s, c, 'stock', text)
        out.append(text)
    if not r['open']:
        r.pop('open', None)
    return out


def _place(s: dict, c: dict, career: str, got: list) -> tuple[int, int]:
    """Place the planned lines through inventory's inv_order, one order per item. Returns (lines placed, xu paid)."""
    from . import engine as e
    inv = _inv()
    r = rec(c)
    x = c['ext']['inv']
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
    return n, paid


def run_all(s: dict) -> list[str]:
    """Every workplace (the load's settlement): its effect lines."""
    out = []
    for cid, c in (s.get('careers') or {}).items():
        if on(c) and c.get('started'):
            out += run(s, c, cid)
    return out


# ---------------------------------------------------------------- the command
def _pay(s: dict, c: dict, career: str, price: int, name: str) -> int:
    """Pay `price` from the workplace fund first, then the wallet (story mode). Returns what the wallet paid."""
    from . import engine as e
    from . import journey as jr
    j = s.get('journey') or {}
    from_fund = min(max(0, c['money']), price)
    from_wallet = price - from_fund
    if from_wallet:
        wallet = j.get('wallet', 0) if j.get('story') else 0
        e.need(wallet >= from_wallet, f'Thiếu {max(0, from_wallet - max(0, wallet)):,} xu (quỹ + ví).'.replace(',', '.'))
        jr._transfer(s, c, from_wallet, f'Góp vốn từ ví · {name}', 'owner_capital')
        jr._wallet(j, -from_wallet, 'invest', f'Góp vốn cho {jr._place(career)}', career)
        j['stats']['invested'] += from_wallet
    e.money(s, c, -price, f'Mua {name}', category='upgrade')
    return from_wallet


def _buy(s: dict, c: dict, career: str, p: dict) -> dict:
    from . import engine as e
    need = e.need
    need(not owned(c), f'{NAME} đã mở ở nơi này rồi.')
    need(p.get('confirm') is True, f'Xác nhận mua {NAME} trước nhé.')
    from_wallet = _pay(s, c, career, PRICE, NAME)
    c[key_of(career)] = dict(paid=PRICE)
    e.log(s, c, 'upgrade', f'Đã mở {NAME}: kho tự đặt khi sắp hết.')
    return dict(message=f'{NAME} đã mở.' + (f' Ví trả {from_wallet:,} xu.'.replace(',', '.') if from_wallet else ''),
                celebrate=True)


def _buy_box(s: dict, c: dict, career: str, p: dict) -> dict:
    from . import engine as e
    need = e.need
    need(not desk(career), 'Kho này tự gộp hàng tự đặt của một nhà cung cấp vào một chuyến rồi.')
    need(owned(c), f'Mua {NAME} trước, rồi mới gộp thùng được nhé.')
    need(not box_owned(c), f'{BOX_NAME} đã mở ở nơi này rồi.')
    need(p.get('confirm') is True, f'Xác nhận mua {BOX_NAME} trước nhé.')
    from_wallet = _pay(s, c, career, BOX_PRICE, BOX_NAME)
    c[BOX_KEY] = dict(paid=BOX_PRICE)
    e.log(s, c, 'upgrade', f'Đã mở {BOX_NAME}: hàng tự đặt về tới cửa gom chung một thùng, kiểm một lần.')
    return dict(message=f'{BOX_NAME} đã mở: hàng tự đặt về tới cửa gom chung một thùng.'
                + (f' Ví trả {from_wallet:,} xu.'.replace(',', '.') if from_wallet else ''), celebrate=True)


def action(s: dict, c: dict, career: str, p: dict) -> dict:
    """stock_reorder: {buy: true, confirm: true} · {buy_box: true, confirm: true} · {on: bool} (all items) ·
    {item, on?, below?, qty?}. No shop time."""
    from . import engine as e
    need = e.need
    need(eligible(career), 'Nơi này không có kho hàng.')
    if p.get('buy') is True:
        return _buy(s, c, career, p)
    if p.get('buy_box') is True:
        return _buy_box(s, c, career, p)
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
    it = _item(career, p.get('item'))
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
                    tease=_orders_placed(c, career) >= TEASE_ORDERS)
    level = 1 + c['xp'] // 90
    cap, line = limits(c, career)
    items = [dict(id=it['id'], **rule(c, career, it['id']), auto=_waiting(c, career, (r.get('open') or {}).get(it['id'])))
             for it in catalogue(career) if it.get('unlock', 1) <= level]
    return dict(owned=True, price=PRICE, on=on(c), items=items, cap=cap, line=line, floor=floor(s, c),
                budget=budget(c), spent=spent(c), warn=r.get('warn') == c['day'],
                why=plan(s, c, career)[1] if r.get('warn') == c['day'] else None,
                box=None if desk(career) else dict(owned=box_owned(c), price=BOX_PRICE,
                         short=0 if box_owned(c) else max(0, BOX_PRICE - max(0, c['money']) - _wallet_of(s))))


def _orders_placed(c: dict, career: str) -> int:
    """Orders the player has placed (the locked line's tease). The desk keeps no `purchases` metric: its parcels on the
    way and received count instead (the 40 newest received are kept, enough for TEASE_ORDERS)."""
    if desk(career):
        return max(c['metrics'].get('restocked', 0), len(c.get('shipments') or ()))
    return c['metrics'].get('purchases', 0)


def _wallet_of(s: dict) -> int:
    j = s.get('journey') or {}
    return max(0, j.get('wallet', 0)) if j.get('story') else 0


def validate(c: dict, career: str) -> None:
    from .engine import need, integer, clean_text
    b = c.get(BOX_KEY)
    if b is not None:
        need(eligible(career) and not desk(career) and c.get(KEY) is not None and isinstance(b, dict) and set(b) == {'paid'},
             'Gộp thùng tự đặt không hợp lệ.')
        integer(b['paid'], 0, 10**9)
    # each kind of workplace keeps its own key (DESK_KEY: an older release refuses c[KEY] on a desk career)
    need(c.get(DESK_KEY if not desk(career) else KEY) is None, 'Tự đặt hàng không hợp lệ.')
    r = c.get(key_of(career))
    if r is None:
        return
    need(eligible(career) and isinstance(r, dict) and set(r) <= {'paid', 'on', 'items', 'open', 'day', 'spent', 'warn'}
         and 'paid' in r, 'Tự đặt hàng không hợp lệ.')
    integer(r['paid'], 0, 10**9)
    need(r.get('on', False) is False, 'Tự đặt hàng không hợp lệ.')
    for k in ('day', 'spent', 'warn'):
        if k in r:
            integer(r[k], 0, 10**9)
    ids = {it['id'] for it in catalogue(career)}
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
