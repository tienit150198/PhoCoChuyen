"""Stock, suppliers and purchase orders for plugin trade careers (v0.4).

Money is paid when an order is placed. Goods enter stock only after the player
counts the delivery. A short delivery can be claimed back once; every supplier
order can be rated, and the supplier answers in its own voice. Lots expire by
game day at closing time: the value is recorded as waste, never charged twice.
"""
from __future__ import annotations
import copy
import math

DEFAULT_SUPPLIERS = [
    dict(id='market', name='Chợ đầu mối Mây', emoji='🧺', lead=2, factor=0.85, short=22,
         note='Rẻ nhất, đi chợ sớm. Thỉnh thoảng giao thiếu vài phần, cần đếm kỹ.',
         voice=dict(good='Cảm ơn quán nha, mai chị để hàng đẹp cho!', bad='Ờ chợ đông quá chị đếm sót, lần sau chị ghi phiếu kỹ hơn.', claim='Thiếu thì chị bù tiền, mình buôn bán lâu dài mà.')),
    dict(id='partner', name='Nhà phân phối Hạt Nắng', emoji='🚚', lead=1, factor=1.0, short=6,
         note='Giá niêm yết, có phiếu giao rõ ràng. Hầu như giao đủ.',
         voice=dict(good='Hạt Nắng ghi nhận đánh giá, cảm ơn quý khách.', bad='Bên em đã chuyển phản hồi cho bộ phận kho để kiểm lại quy trình.', claim='Đã lập phiếu hoàn cho phần thiếu theo biên bản giao nhận.')),
    dict(id='express', name='Giao hỏa tốc Mây Xanh', emoji='⚡', lead=0, factor=1.35, short=0,
         note='Có ngay trong nhịp này nhưng đắt hơn. Dùng khi cháy hàng giữa ca.',
         voice=dict(good='Mây Xanh luôn sẵn sàng khi quán cần gấp!', bad='Xin lỗi quý khách, tài xế sẽ được nhắc lại quy trình.', claim='Đã hoàn tiền phần thiếu ngay.')),
]
SUPPLIER_INDEX = {x['id']: x for x in DEFAULT_SUPPLIERS}


def _spec(career: str) -> dict | None:
    from .careers import PLUGINS
    mod = PLUGINS.get(career)
    return mod.SPEC.get('inventory') if mod else None


def catalogue(career: str) -> list[dict]:
    spec = _spec(career)
    return spec['items'] if spec else []


def item(career: str, item_id: str) -> dict:
    from .engine import need
    found = next((x for x in catalogue(career) if x['id'] == item_id), None)
    need(found, 'Không có mặt hàng này trong kho của nghề.')
    return found


def capacity(career: str) -> int:
    spec = _spec(career)
    return spec.get('capacity', 40) if spec else 0


def initial(career: str) -> dict | None:
    spec = _spec(career)
    if not spec:
        return None
    lots = []
    for i, x in enumerate(spec['items']):
        qty = x.get('start', 8 if x.get('unlock', 1) <= 1 else 0)
        if qty:
            lots.append(dict(id=f'opening-{x["id"]}', item=x['id'], qty=qty, unit_cost=0,
                             expires=_life(x), received=1, supplier='opening'))
    return dict(lots=lots, orders=[], supplier_ratings={}, seq=0, day_bought=0)


def _life(x: dict) -> int:
    # Non-perishable goods get a long, finite game-day horizon.
    return x.get('life') or 999


def inv(c: dict) -> dict:
    from .engine import need
    x = c.get('ext', {}).get('inv')
    need(x is not None, 'Nghề này không dùng kho nguyên liệu.')
    return x


def count(c: dict, item_id: str) -> int:
    x = c.get('ext', {}).get('inv')
    if not x:
        return 0
    return sum(l['qty'] for l in x['lots'] if l['item'] == item_id and l['expires'] >= c['day'])


def take(c: dict, item_id: str, qty: int = 1) -> int:
    from .engine import need
    x = inv(c)
    name = item_name(item_id)
    need(count(c, item_id) >= qty, f'Hết {name}. Mở Kho để nhập thêm nhé.')
    cost = 0
    for lot in sorted((l for l in x['lots'] if l['item'] == item_id and l['expires'] >= c['day'] and l['qty'] > 0),
                      key=lambda l: (l['expires'], l['received'])):
        used = min(qty, lot['qty'])
        lot['qty'] -= used
        qty -= used
        cost += used * lot['unit_cost']
        if not qty:
            break
    x['lots'] = [l for l in x['lots'] if l['qty'] > 0]
    return cost


def add_lot(c: dict, item_id: str, qty: int, unit_cost: int, life_left: int, supplier: str) -> dict:
    x = inv(c)
    x['seq'] += 1
    lot = dict(id=f'lot-{x["seq"]}', item=item_id, qty=qty, unit_cost=unit_cost,
               expires=c['day'] + max(1, life_left) - 1, received=c['day'], supplier=supplier)
    x['lots'].append(lot)
    return lot


def item_name(item_id: str) -> str:
    from .careers import PLUGINS
    for mod in PLUGINS.values():
        for x in (mod.SPEC.get('inventory') or {}).get('items', []):
            if x['id'] == item_id:
                return x['name']
    return item_id


def _in_transit(x: dict, item_id: str) -> int:
    return sum(o['qty'] for o in x['orders'] if o['item'] == item_id and o['status'] == 'in_transit')


def _trim_orders(x: dict, limit: int = 40) -> None:
    """Keep the order book short without ever dropping a paid order still on
    the way: only the oldest received orders are forgotten."""
    extra = len(x['orders']) - limit
    if extra <= 0:
        return
    drop = set()
    for o in x['orders']:
        if len(drop) >= extra:
            break
        if o['status'] == 'received':
            drop.add(id(o))
    x['orders'] = [o for o in x['orders'] if id(o) not in drop]


def action(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    """inv_order / inv_receive / inv_claim / inv_rate / inv_discard."""
    from . import engine as e
    need = e.need
    x = inv(c)
    level = 1 + c['xp'] // 90
    if name == 'inv_order':
        it = item(career, p.get('item'))
        qty = e.integer(p.get('qty'), 1, 30)
        sup = SUPPLIER_INDEX.get(p.get('supplier', 'partner'))
        need(sup, 'Nhà cung cấp không tồn tại.')
        need(it.get('unlock', 1) <= level, f'Mở khóa {it["name"]} ở cấp {it.get("unlock", 1)}.')
        need(p.get('confirm') is True, 'Xác nhận đơn nhập và số tiền trước nhé.')
        cap = capacity(career)
        need(count(c, it['id']) + _in_transit(x, it['id']) + qty <= cap,
             f'Kho chứa tối đa {cap} phần mỗi loại (tính cả hàng đang giao).')
        need(len([o for o in x['orders'] if o['status'] == 'in_transit']) < 8, 'Đang có nhiều đơn chờ giao. Nhận bớt rồi đặt tiếp nhé.')
        cost = max(1, math.ceil(it['cost'] * qty * sup['factor']))
        x['seq'] += 1
        oid = f'po-{x["seq"]}'
        e.money(s, c, -cost, f'Nhập {qty} {it.get("unit", "phần")} {it["name"]} · {sup["name"]}', oid, category='stock')
        roll = (c['day'] * 37 + x['seq'] * 11 + sum(map(ord, it['id']))) % 100
        short = min(qty - 1, 1 + roll % 3) if qty > 1 and roll < sup['short'] else 0
        x['orders'].append(dict(id=oid, item=it['id'], qty=qty, actual=qty - short, supplier=sup['id'], cost=cost,
                                unit_cost=math.ceil(it['cost'] * sup['factor']), ready=c['turn'] + sup['lead'],
                                status='in_transit', day=c['day'], claimed=False, rating=None, reply=None))
        _trim_orders(x)
        x['day_bought'] += cost
        e.metric(c, 'purchases')
        when = 'ngay trong nhịp này' if sup['lead'] == 0 else f'sau {sup["lead"]} nhịp làm việc'
        return dict(message=f'Đã đặt {qty} {it.get("unit", "phần")} {it["name"]} · {cost} xu. Hàng tới {when}; đếm rồi mới nhập kho.')
    order = next((o for o in x['orders'] if o['id'] == p.get('order')), None)
    if name == 'inv_receive':
        need(order and order['status'] == 'in_transit', 'Đơn đã nhận hoặc không tồn tại.')
        # The engine has already counted this action's own beat (turn + 1), so
        # "arrived" means it was ready before this action, matching public()'s
        # ready_now: a 1-beat delivery cannot be received straight after ordering.
        need(c['turn'] > order['ready'], 'Hàng chưa tới. Làm việc khác một nhịp rồi quay lại nhé.')
        counted = e.integer(p.get('count'), 0, 60)
        need(counted == order['actual'], 'Số đếm chưa khớp số hàng thực có trong thùng. Đếm lại nhé.')
        it = item(career, order['item'])
        # Stock can grow after ordering (market buys, returns, gifts); say so
        # plainly instead of failing on the generic capacity check.
        room = capacity(career) - count(c, it['id'])
        need(order['actual'] <= room, f'Kệ {it["name"]} chỉ còn chỗ cho {max(0, room)} {it.get("unit", "phần")}. '
             'Bán hoặc bỏ bớt lô cũ rồi nhận thùng này nhé.')
        if order['actual']:
            add_lot(c, it['id'], order['actual'], order['unit_cost'], _life(it), order['supplier'])
        order['status'] = 'received'
        e.metric(c, 'restocked')
        e.log(s, c, 'stock', f'Kiểm nhận {order["actual"]}/{order["qty"]} {it["name"]} từ {SUPPLIER_INDEX[order["supplier"]]["name"]}.', ref=order['id'])
        msg = f'Đã nhập kho {order["actual"]} {it.get("unit", "phần")} {it["name"]}.'
        if order['actual'] < order['qty']:
            msg += f' Thiếu {order["qty"] - order["actual"]} so với đơn — có thể khiếu nại nhà cung cấp.'
        return dict(message=msg)
    if name == 'inv_claim':
        need(order and order['status'] == 'received', 'Chỉ khiếu nại sau khi đã kiểm nhận.')
        need(order['actual'] < order['qty'] and not order['claimed'], 'Đơn này giao đủ hoặc đã được giải quyết.')
        # Refund the paid share of the missing units (rounded), never more than was paid.
        missing = order['qty'] - order['actual']
        refund = max(1, (2 * order['cost'] * missing + order['qty']) // (2 * order['qty']))
        order['claimed'] = True
        sup = SUPPLIER_INDEX[order['supplier']]
        e.money(s, c, refund, f'Hoàn tiền giao thiếu · {sup["name"]}', order['id'], category='refund')
        order['reply'] = sup['voice']['claim']
        return dict(message=f'{sup["name"]}: “{sup["voice"]["claim"]}” · +{refund} xu.')
    if name == 'inv_rate':
        need(order and order['status'] == 'received' and order['rating'] is None, 'Chỉ đánh giá một lần sau khi nhận hàng.')
        stars = e.integer(p.get('stars'), 1, 5)
        note = e.clean_text(p.get('note', ''), 200, 0)
        order['rating'] = stars
        order['note'] = note
        sup = SUPPLIER_INDEX[order['supplier']]
        order['reply'] = sup['voice']['good' if stars >= 4 else 'bad']
        rated = x['supplier_ratings'].setdefault(sup['id'], dict(total=0, count=0))
        rated['total'] += stars
        rated['count'] += 1
        e.metric(c, 'supplier_reviews')
        return dict(message=f'{sup["name"]} phản hồi: “{order["reply"]}”')
    if name == 'inv_discard':
        lot = next((l for l in x['lots'] if l['id'] == p.get('lot')), None)
        need(lot, 'Lô hàng không còn trong kho.')
        need(p.get('confirm') is True, 'Xác nhận bỏ lô này; giá trị được ghi là hao hụt.')
        value = lot['qty'] * lot['unit_cost']
        c['life']['day_waste'] += value
        c['life']['waste'] = (c['life']['waste'] + [dict(day=c['day'], item=lot['item'], qty=min(60, lot['qty']), value=value, reason='Bỏ lô không đạt')])[-120:]
        x['lots'] = [l for l in x['lots'] if l['id'] != lot['id']]
        return dict(message='Đã bỏ lô hàng và ghi hao hụt.')
    raise e.GameError('Thao tác kho chưa được hỗ trợ.')


def on_close(s: dict, c: dict, career: str) -> int:
    """Expire lots at the end of the game day. Returns wasted value."""
    x = c.get('ext', {}).get('inv')
    if not x:
        return 0
    wasted = 0
    keep = []
    for lot in x['lots']:
        if lot['expires'] <= c['day'] and lot['qty']:
            value = lot['qty'] * lot['unit_cost']
            wasted += value
            c['life']['waste'] = (c['life']['waste'] + [dict(day=c['day'], item=lot['item'], qty=min(60, lot['qty']), value=value, reason='Hết hạn sử dụng')])[-120:]
        else:
            keep.append(lot)
    x['lots'] = keep[-300:]
    x['day_bought'] = 0
    c['life']['day_waste'] += wasted
    return wasted


def public(c: dict, career: str) -> dict | None:
    x = c.get('ext', {}).get('inv')
    if x is None:
        return None
    v = copy.deepcopy(x)
    level = 1 + c['xp'] // 90
    v['stock'] = {i['id']: count(c, i['id']) for i in catalogue(career)}
    v['expiring'] = {i['id']: sum(l['qty'] for l in x['lots'] if l['item'] == i['id'] and l['expires'] == c['day']) for i in catalogue(career)}
    v['locked'] = [i['id'] for i in catalogue(career) if i.get('unlock', 1) > level]
    v['capacity'] = capacity(career)
    # Derived numbers for the stock screen: what is on the way, room left on
    # each shelf and how many game days the oldest lot still has.
    v['arriving'] = {i['id']: _in_transit(x, i['id']) for i in catalogue(career)}
    v['room'] = {k: max(0, v['capacity'] - v['stock'][k] - v['arriving'][k]) for k in v['stock']}
    v['expiring_soon'] = {i['id']: sum(l['qty'] for l in x['lots'] if l['item'] == i['id'] and c['day'] <= l['expires'] <= c['day'] + 1)
                          for i in catalogue(career)}
    v['days_left'] = {}
    for l in x['lots']:
        if l['expires'] >= c['day'] and l['qty'] > 0:
            left = l['expires'] - c['day'] + 1
            v['days_left'][l['item']] = min(left, v['days_left'].get(l['item'], left))
    for o in v['orders']:
        o['ready_now'] = o['ready'] <= c['turn']
        # The count is discovered by opening the box, as with v0.2 shipments.
        o['count_hint'] = o['actual'] if o['ready_now'] and o['status'] == 'in_transit' else None
        if o['status'] == 'in_transit':
            o.pop('actual', None)
    v['suppliers'] = [dict(s, rating=(round(x['supplier_ratings'][s['id']]['total'] / x['supplier_ratings'][s['id']]['count'], 1)
                                     if x['supplier_ratings'].get(s['id'], {}).get('count') else None)) for s in DEFAULT_SUPPLIERS]
    return v


def validate(c: dict, career: str) -> None:
    from .engine import need, integer, clean_text
    x = c['ext'].get('inv')
    spec = _spec(career)
    if not spec:
        need(x is None, 'Nghề này không có kho nguyên liệu.')
        return
    need(isinstance(x, dict) and all(k in x for k in ('lots', 'orders', 'supplier_ratings', 'seq', 'day_bought')), 'Kho thiếu dữ liệu.')
    integer(x['seq'], 0, 10**9)
    integer(x['day_bought'], 0, 10**9)
    ids = {i['id'] for i in spec['items']}
    need(isinstance(x['lots'], list) and len(x['lots']) <= 300, 'Danh sách lô không hợp lệ.')
    for lot in x['lots']:
        need(isinstance(lot, dict) and lot.get('item') in ids, 'Lô hàng lạ.')
        clean_text(lot.get('id'), 80)
        integer(lot.get('qty'), 0, 999)
        integer(lot.get('unit_cost'), 0, 10000)
        integer(lot.get('expires'), 0, 10**7)
        integer(lot.get('received'), 1, 10**7)
    need(len({l['id'] for l in x['lots']}) == len(x['lots']), 'Trùng mã lô.')
    cap = capacity(career)
    for i in ids:
        need(count(c, i) <= cap, 'Tồn vượt sức chứa.')
    need(isinstance(x['orders'], list) and len(x['orders']) <= 40, 'Đơn nhập không hợp lệ.')
    for o in x['orders']:
        need(isinstance(o, dict) and o.get('item') in ids and o.get('supplier') in SUPPLIER_INDEX, 'Đơn nhập sai.')
        integer(o.get('qty'), 1, 30)
        integer(o.get('actual'), 0, o['qty'])
        integer(o.get('cost'), 0, 10**6)
        integer(o.get('unit_cost'), 0, 10000)
        integer(o.get('ready'), 0, 10**9)
        need(o.get('status') in ('in_transit', 'received'), 'Trạng thái đơn nhập sai.')
        need(type(o.get('claimed')) is bool and o.get('rating') in (None, 1, 2, 3, 4, 5), 'Đánh giá đơn nhập sai.')
    need(isinstance(x['supplier_ratings'], dict) and all(k in SUPPLIER_INDEX for k in x['supplier_ratings']), 'Đánh giá nhà cung cấp sai.')


def content() -> dict:
    from .careers import PLUGINS
    return dict(suppliers=DEFAULT_SUPPLIERS,
                items={cid: mod.SPEC['inventory']['items'] for cid, mod in PLUGINS.items() if mod.SPEC.get('inventory')})
