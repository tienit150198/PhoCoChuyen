"""Warehouse convenience: purchased tiers change units, never trading income."""
from .progression_prices import PRICES, MAX_TIER

COUNT = (1, 2, 3, 5, 8, 12, 20, 30, 45, 65, 100)
# Mẹ & bé / Nhà thuốc (the LEGACY stock rooms) order and shelve on the same ladder as every other shop (#424, owner
# 18/10 "theo hướng của bạn"): LINE = order_progression.LIMITS, CAPACITY = capacity_progression.units(80, tier).
# Was LINE (6, 8, 12, 16, 24, 32, 48, 64, 96, 128, 200) and CAPACITY (12, 24, 36, 48, 72, 96, 144, 192, 288, 384, 600):
# a tier already bought keeps its place on the ladder and only grows. A save holding more than 600 of an item or a
# crate over 200 is refused by 2.4.50 and older (SAVE_STOCK / SAVE_LINE below).
LINE = (80, 120, 200, 350, 550, 800, 1200, 1800, 2500, 3200, 4000)
CAPACITY = (80, 120, 180, 260, 380, 550, 800, 1200, 1800, 2600, 4000)
LEGACY = ('mother_baby', 'pharmacy')
SAVE_LINE = LINE[-1]
SAVE_STOCK = CAPACITY[-1]
AUTO_TIER = 5   # 🤖 Tự nhận hàng from this Bộ đếm kho tier (game/auto_stock.py TIER)


def item_id(career, group, tier):
    return f'warehouse_{group}_{career}_{tier}'


def countable(career):
    from .inventory import catalogue as stock_catalogue
    return career != 'pagoda' and (career in LEGACY or bool(stock_catalogue(career)))


def tier(c, career, group):
    owned = set(c.get('upgrades', []))
    return max((n for n in range(1, MAX_TIER + 1) if item_id(career, group, n) in owned), default=0)


def capacity(c, career, property_cap=None):
    from .operations import PROPERTY_INDEX
    base = property_cap if property_cap is not None else PROPERTY_INDEX[c['ops']['property']['tier']]['stock_cap']
    return max(base, 24 if 'shelf' in c.get('upgrades', []) else 12, CAPACITY[tier(c, career, 'logistics')])


def reserved(c, career):
    """Registry gifts are off the shelf but can return if the party is missed."""
    out = {}
    if career == 'mother_baby':
        from .careers import mother_baby as mb
        care = mb.raw(c)
        if care and care['reg']['state'] == 'open':
            for lid, line in care['reg']['lines'].items():
                if line['aside']:
                    item = mb._reg_item(care, lid)
                    out[item] = out.get(item, 0) + mb.REG_LINES[lid][2]
    return out


def room(c, career, item, ceiling=None):
    incoming = sum(x['qty'] for x in c.get('shipments', []) if x['item'] == item and x['status'] != 'received')
    return max(0, (capacity(c, career) if ceiling is None else ceiling) - c['stock'].get(item, 0) - incoming - reserved(c, career).get(item, 0))


def public(c, career):
    if not countable(career):
        return None
    count_tier = tier(c, career, 'count')
    out = dict(count_tier=count_tier, count_step=COUNT[count_tier], max_tier=MAX_TIER)
    if career in LEGACY:
        logistics = tier(c, career, 'logistics')
        out.update(logistics_tier=logistics, line_max=LINE[logistics], capacity=capacity(c, career), reserved=reserved(c, career))
    from . import auto_stock
    out['auto'] = auto_stock.public(c, career)   # 🤖 Tự nhận hàng (Bậc 5 trở lên)
    return out


def catalogue(careers):
    out = []
    for career in careers:
        if not countable(career):
            continue
        for group in (('count', 'logistics') if career in LEGACY else ('count',)):
            for n, price in enumerate(PRICES, 1):
                count = group == 'count'
                name = 'Bộ đếm kho' if count else 'Kho & đơn nhập'
                description = ((f'Đếm {COUNT[n]} món mỗi lần hoặc nhịp giữ. Mở 🤖 Tự nhận hàng: hàng tới tự đếm và lên kệ.'
                                if n == AUTO_TIER else f'Đếm {COUNT[n]} món mỗi lần hoặc nhịp giữ. Vẫn tự kiểm và xác nhận nhận hàng.') if count else
                               f'Mỗi dòng đặt tối đa {LINE[n]} món; sức chứa ít nhất {CAPACITY[n]} món mỗi mã, gồm cả hàng đang về.')
                out.append(dict(id=item_id(career, group, n), name=f'{name} · Bậc {n}', icon='box',
                                kind='equipment', careers=[career], price=price, min_level=1,
                                gear_group='warehouse_' + group, gear_tier=n,
                                effect_units=COUNT[n] if count else LINE[n],
                                effect_previous=COUNT[n-1] if count else LINE[n-1],
                                effect_capacity=None if count else CAPACITY[n],
                                effect_previous_capacity=None if count else CAPACITY[n-1],
                                effect_label='món / nhịp đếm' if count else 'món / dòng đặt',
                                total_price=sum(PRICES), description=description,
                                requires=item_id(career, group, n-1) if n > 1 else None))
    from . import capacity_progression, order_progression
    out.extend(capacity_progression.catalogue(careers))
    out.extend(order_progression.catalogue(careers))
    return out
