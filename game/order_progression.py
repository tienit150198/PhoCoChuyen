"""Purchased per-line order limits, independent of warehouse shelf capacity."""
from .progression_prices import PRICES, MAX_TIER

LIMITS = (80, 120, 200, 350, 550, 800, 1200, 1800, 2500, 3200, 4000)


def item_id(career, n):
    return f'warehouse_order_{career}_{n}'


def tier(c, career):
    owned = set(c.get('upgrades', []))
    return max((n for n in range(1, MAX_TIER + 1) if item_id(career, n) in owned), default=0)


def limit(c, career):
    return LIMITS[tier(c, career)]


def public(c, career):
    n = tier(c, career)
    return dict(tier=n, max_tier=MAX_TIER,
                next_id=item_id(career, n + 1) if n < MAX_TIER else None,
                next_limit=LIMITS[n + 1] if n < MAX_TIER else None,
                next_price=PRICES[n] if n < MAX_TIER else None,
                total_price=sum(PRICES))


def catalogue(careers):
    from . import inventory
    out = []
    for career in careers:
        if not inventory.catalogue(career):
            continue
        for n, price in enumerate(PRICES, 1):
            out.append(dict(id=item_id(career, n), name=f'Hạn mức nhập hàng · Bậc {n}', icon='box',
                            kind='equipment', careers=[career], price=price, min_level=1,
                            gear_group='warehouse_order', gear_tier=n,
                            effect_units=LIMITS[n], effect_previous=LIMITS[n - 1],
                            effect_capacity=None, effect_label='món / dòng đặt',
                            total_price=sum(PRICES),
                            description=f'Mỗi dòng đặt tối đa {LIMITS[n]} món. Sức chứa kho được nâng riêng; '
                                        'hàng đang về, các đơn dự thảo và hàng giữ chỗ vẫn tính vào sức chứa.',
                            requires=item_id(career, n - 1) if n > 1 else None))
    return out
