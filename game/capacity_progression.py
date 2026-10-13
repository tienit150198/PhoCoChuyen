"""Owned warehouse space; per-order limits and trading rewards stay separate."""
from .progression_prices import PRICES, MAX_TIER

RATIOS = (8, 12, 18, 26, 38, 55, 80, 120, 180, 260, 400)
EXTRA_STORAGE = {
    'farm': (('Kho lạnh', 160, 'đơn vị'), ('Lô trong kho lạnh', 30, 'lô'),
             ('Ổ trứng', 40, 'trứng'), ('Kho vườn mới', 240, 'đơn vị')),
    'cafe_bakery': (('Tủ kính', 30, 'bánh / loại'),),
    'restaurant': (('Nồi nước dùng', 12, 'phần / loại'),),
    'com': (('Giá giữ ấm', 8, 'miếng sườn'), ('Khay món', 16, 'phần / loại')),
}


def item_id(career, n):
    return f'warehouse_storage_{career}_{n}'


def tier(c, career):
    owned = set(c.get('upgrades', []))
    return max((n for n in range(1, MAX_TIER + 1) if item_id(career, n) in owned), default=0)


def limit(c, career, base):
    return units(base, tier(c, career))


def units(base, n):
    return (base * RATIOS[n] + 7) // 8


def catalogue(careers):
    from . import inventory
    out = []
    for career in careers:
        milk = career == 'milk_tea'
        if not milk and not inventory.catalogue(career):
            continue
        base = 60 if milk else inventory.capacity(career)
        for n, price in enumerate(PRICES, 1):
            capacity = units(base, n)
            previous = units(base, n - 1)
            description = (f'Mỗi nguyên liệu chứa tối đa {capacity} phần; mỗi cỡ ly chứa tối đa {(120 * RATIOS[n] + 7) // 8} ly. '
                           if milk else f'Mỗi mã hàng chứa tối đa {capacity} phần. ')
            description += 'Sức chứa gồm hàng đang về và phần giữ cho đơn. Giới hạn mỗi lần đặt giữ nguyên.'
            out.append(dict(id=item_id(career, n), name=f'Sức chứa kho · Bậc {n}', icon='box',
                            kind='equipment', careers=[career], price=price, min_level=1,
                            gear_group='warehouse_storage', gear_tier=n,
                            effect_units=capacity, effect_previous=previous,
                            effect_capacity=None, effect_label='phần / nguyên liệu' if milk else 'phần / mã hàng',
                            effect_resources=[dict(name=name, previous=units(value, n - 1),
                                                   capacity=units(value, n), unit=unit)
                                              for name, value, unit in EXTRA_STORAGE.get(career, ())],
                            total_price=sum(PRICES), description=description,
                            requires=item_id(career, n - 1) if n > 1 else None))
    return out
