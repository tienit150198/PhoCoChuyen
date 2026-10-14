"""🤖 Tự nhận hàng: deliveries counted and shelved by the server (players #326 #333 #361: "đếm hàng mệt").

Unlocked by 📦 Bộ đếm kho · Bậc 5 of that workplace (game/convenience.py, `warehouse_count_<career>_5`, already sold:
owner 14/10), on by default once unlocked; the player can turn it off in the Kho sheet (c[KEY] = False, the only save
change: an optional career key that older releases ignore; turning it back on removes it).

What it does, server side, for a career where it is on:
* 📦 the stock room (game/inventory.py): every order whose crate is at the door (its `at` reached on the shop clock,
  the same test as the Kho's `ready_now`) is received as a correct count would receive it: the real `actual` units
  onto the shelf as one lot at the order's unit cost (_receive_lot, plugins' on_receive), a merged order all at once
  or not at all (as inv_receive {group}); a crate that does not fit the shelf stays at the door, exactly as the
  manual receive refuses it ("Kệ … chỉ còn chỗ …"). A short delivery is claimed through the same claim path
  (inventory.claim: the refund of the missing share, once, `claimed`).
* 🍼 💊 the older stock desks (mother_baby, pharmacy: c['shipments'], engine.stock_received): parcels that are here.
* 📦 contract stock (game/career_scale_inventory.py) and 🎓 specialism stock (game/career_specialism_stock.py): their
  orders are received at once (they have no transit time), lots keep their unit cost (FIFO stays FIFO).
* One journal row "📦 Tự nhận N món" per pass, an effect line for the player, metric `restocked` per crate.

When: after every command of that workplace (engine._apply_action, the same point where a crate becomes "at the
door": the shop clock moves with the workplace's own commands), and for every workplace on the server's settlement
of a load (business.on_load_result: `due`, then the internal business_sync), so goods that arrived before the player
left are on the shelf when they come back. Task generation is not touched.
"""
from __future__ import annotations

from . import convenience as cv

TIER = cv.AUTO_TIER   # Bộ đếm kho · Bậc 5
KEY = 'auto_stock'   # c[KEY] is False: turned off by the player (absent: on once unlocked)
ACTION = 'stock_auto'


def unlocked(c: dict, career: str) -> bool:
    return isinstance(c, dict) and cv.countable(career) and cv.tier(c, career, 'count') >= TIER


def on(c: dict, career: str) -> bool:
    return unlocked(c, career) and c.get(KEY) is not False


def public(c: dict, career: str) -> dict | None:
    """The Kho sheet's switch (warehouse.auto): {unlocked, on} (the client names Bộ đếm kho · Bậc 5 when locked)."""
    if not cv.countable(career):
        return None
    return dict(unlocked=unlocked(c, career), on=on(c, career))


def toggle(c: dict, career: str, p: dict) -> dict:
    """stock_auto {on: bool}: no shop time, nothing else changes."""
    from .engine import need
    need(unlocked(c, career), f'Mua Bộ đếm kho · Bậc {TIER} (Thiết bị) để mở Tự nhận hàng.')
    value = p.get('on')
    need(type(value) is bool, 'Lựa chọn không hợp lệ.')
    if value:
        c.pop(KEY, None)
    else:
        c[KEY] = False
    return dict(message='🤖 Tự nhận hàng: Bật.' if value else '🤖 Tự nhận hàng: Tắt. Hàng tới chờ bạn đếm.')


# ---------------------------------------------------------------- what is due
def _inv_due(c: dict, career: str) -> list:
    from . import inventory as inv
    x = (c.get('ext') or {}).get('inv')
    if not isinstance(x, dict) or not x.get('orders'):
        return []
    now = None
    out = []
    for o in x['orders']:
        if o.get('status') == 'in_transit' and type(o.get('at')) is int:
            if now is None:
                now = inv.clock(c, career)['abs']
            if now >= o['at']:
                out.append(o)
    return out


def _legacy_due(c: dict, career: str) -> list:
    if career not in cv.LEGACY:
        return []
    from .engine import shipment_here
    return [x for x in c.get('shipments') or [] if x.get('status') == 'in_transit' and shipment_here(c, career, x)]


def _scale_due(c: dict) -> list:
    r = c.get('scale_stock')
    return [o for o in r['orders'] if not o['received']] if isinstance(r, dict) else []


def _special_due(c: dict) -> list:
    r = c.get('special_stock')
    return list(r['orders']) if isinstance(r, dict) else []


def due(state: dict) -> bool:
    """Any workplace where it is on with something to receive now (read only; a load's cheap check)."""
    for cid, c in ((state or {}).get('careers') or {}).items():
        try:
            if on(c, cid) and (_inv_due(c, cid) or _legacy_due(c, cid) or _scale_due(c) or _special_due(c)):
                return True
        except (KeyError, TypeError, ValueError, AttributeError):
            continue   # an odd record: the command path validates it
    return False


# ---------------------------------------------------------------- receiving
def _inventory(s: dict, c: dict, career: str) -> tuple[int, int, list]:
    """(units, refund, names) received from the stock room's crates at the door."""
    from . import engine as e
    from . import inventory as inv
    arrived = _inv_due(c, career)
    if not arrived:
        return 0, 0, []
    x = c['ext']['inv']
    groups: dict = {}
    for o in arrived:
        groups.setdefault(o.get('group') or o['id'], []).append(o)
    units = refund = 0
    names = []
    for ref, lines in groups.items():
        whole = [o for o in x['orders'] if o.get('group') == ref] if lines[0].get('group') else lines
        mine = {id(o) for o in lines}
        if any(o['status'] == 'in_transit' and id(o) not in mine for o in whole):
            continue   # a merged van not all at the door yet (inv_receive {group} waits for it too)
        # The shelf must take every line (a merged order: all of it, or the crate waits at the door as the manual
        # receive leaves it); lines of one item share its room.
        want: dict = {}
        fits = True
        for o in lines:
            it = inv.item(career, o['item'])
            want[it['id']] = want.get(it['id'], 0) + o['actual']
            if want[it['id']] > inv._receive_room(c, career, o, it['id']):
                fits = False
                break
        if not fits:
            continue
        sup = inv._known(career, lines[0]['supplier'])
        for o in lines:
            it = inv.item(career, o['item'])
            inv._receive_lot(c, career, o, it, sup)
            o['status'] = 'received'
            e.metric(c, 'restocked')
            units += o['actual']
            names.append(f'{o["actual"]} {it["name"]}')
        short = [o for o in lines if o['actual'] < o['qty'] and not o['claimed']]
        if short:
            refund += inv.claim(s, c, career, short, ref)
    if units or names:
        from .careers import PLUGINS
        mod = PLUGINS.get(career)
        if mod and hasattr(mod, 'on_stock'):
            mod.on_stock(s, c, 'inv_receive')   # e.g. a rush customer sees the goods just shelved
    return units, refund, names


def _legacy(s: dict, c: dict, career: str) -> tuple[int, list]:
    from . import engine as e
    units, names = 0, []
    for x in _legacy_due(c, career):
        if c['stock'].get(x['item'], 0) + x['actual'] > cv.SAVE_STOCK:
            continue   # never past what a save may hold: waits at the door
        e.stock_received(s, c, career, x, x['actual'])
        e.metric(c, 'restocked')
        units += x['actual']
        name = (e.PRODUCT_INDEX.get(x['item']) or e.LOT_INDEX.get(x['item']) or {}).get('name', x['item'])
        names.append(f'{x["actual"]} {name}')
    return units, names


def _scale(c: dict, career: str) -> tuple[int, list]:
    from . import career_scale_inventory as si
    r = c.get(si.KEY)
    if not isinstance(r, dict) or not _scale_due(c):
        return 0, []
    units, names = 0, []
    for row in [o for o in r['orders'] if not o['received']]:
        if len(r['lots']) >= si.MAX_ROWS or r['seq'] >= si.MAX:
            break
        r['seq'] += 1
        r['lots'].append(dict(id=f"lot-{r['seq']}", code=row['code'], site=row['site'], units=row['units'],
                              unit_cost=row['unit_cost'], reserved={}))
        row['received'] = True
        units += row['quantity']
        names.append(f'{row["quantity"]} thùng {si.material(career, row["code"]).name}')
    return units, names


def _special(c: dict, career: str) -> tuple[int, list]:
    from . import career_specialism_stock as sp
    r = c.get(sp.KEY)
    if not isinstance(r, dict) or not r['orders']:
        return 0, []
    units, names = 0, []
    for o in list(r['orders']):
        if len(r['lots']) >= 400:
            break
        r['lots'].append(dict(o))
        r['orders'].remove(o)
        units += o['quantity']
        names.append(f'{o["quantity"]} bộ {sp.material(career, o["code"])["name"]}')
    return units, names


def run(s: dict, c: dict, career: str) -> list[str]:
    """Receive what is due in this workplace when it is on. Returns the player's effect lines ([] when nothing)."""
    if not on(c, career):
        return []
    from . import engine as e
    units, refund, names = _inventory(s, c, career)
    for part in (_legacy(s, c, career), _scale(c, career), _special(c, career)):
        units += part[0]
        names += part[1]
    if not names:
        return []
    shown = ', '.join(names[:4]) + (f' và {len(names) - 4} dòng khác' if len(names) > 4 else '')
    tail = f' · giao thiếu, đã khiếu nại hoàn {refund} xu' if refund else ''
    e.log(s, c, 'stock', f'📦 Tự nhận {units} món: {shown}{tail}.'[:300])
    return [f'📦 Tự nhận {units} món' + (f' · hoàn {refund} xu thiếu.' if refund else ' lên kệ.')]   # a toast: ≤ 8 words


def run_all(s: dict) -> list[str]:
    """Every workplace (the load's settlement): its effect lines."""
    out = []
    for cid, c in (s.get('careers') or {}).items():
        out += run(s, c, cid)
    return out
