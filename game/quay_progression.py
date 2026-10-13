"""Finite paid convenience. Existing stock and stalls never imply purchased tiers."""
from .progression_prices import PRICES, MAX_TIER

LIMITS = {
    'storage': (500, 750, 1000, 1500, 2500, 4000, 6000, 9000, 13000, 17000, 20000),
    'restock': (5, 10, 20, 35, 60, 100, 160, 250, 400, 700, 1000),
    'slots': (1, 2, 3, 4, 6, 8, 12, 18, 26, 38, 50),
}
LABELS = {'storage': 'Sức chứa kho quầy', 'restock': 'Nhập hàng mỗi lần', 'slots': 'Số quầy sở hữu'}


def tier(holder, track):
    return holder.get('paid_tier', {}).get(track, 0)


def limit(holder, track):
    return LIMITS[track][tier(holder, track)]


def track_view(holder, track):
    level = tier(holder, track)
    return dict(tier=level, limit=LIMITS[track][level], next_limit=LIMITS[track][level+1] if level < MAX_TIER else None,
                next_cost=PRICES[level] if level < MAX_TIER else None, max_tier=MAX_TIER,
                max_limit=LIMITS[track][-1], total_cost=sum(PRICES), spent=sum(PRICES[:level]))


def slots(q):
    used = len(q.get('stalls', ()))
    allowance = limit(q, 'slots')
    return dict(track_view(q, 'slots'), used=used, remaining=max(0, allowance-used), over_limit=max(0, used-allowance))


def business_view(st):
    from .player_service_tasks import reserved
    b = st.get('business', {})
    capacity, batch = limit(b, 'storage'), limit(b, 'restock')
    held = reserved(st)
    return dict(stock_capacity=capacity, restock_batch=batch, stock_reserved=held,
                stock_room=max(0, capacity-sum(b.get('stock', {}).values())-held),
                convenience={k: track_view(b, k) for k in ('storage', 'restock')})


def validate(holder, allowed, need, integer):
    paid = holder.get('paid_tier', {})
    need(isinstance(paid, dict) and set(paid) <= set(allowed))
    need(all(integer(v, 0, MAX_TIER) for v in paid.values()))


def buy(s, p):
    from . import quay as qy
    need = qy._core().need
    track = p.get('track')
    need(isinstance(track, str) and track in LIMITS, 'Chọn tiện ích cần nâng cấp.')
    allowed = {'track', 'expected_tier'} | ({'stall'} if track != 'slots' else set())
    need(set(p) <= allowed, 'Thông tin nâng cấp không hợp lệ.')
    why = qy.why_locked(s)
    need(not why, why or '', 'locked')
    q = qy.ensure(s)
    st = qy.stall(s, p.get('stall')) if track != 'slots' else None
    holder = st['business'] if st else q
    current = tier(holder, track)
    expected = p.get('expected_tier')
    need(type(expected) is int and expected == current, 'Bậc tiện ích đã thay đổi. Xem lại trước khi mua.', 'stale_tier')
    need(current < MAX_TIER, 'Tiện ích đã đạt bậc tối đa.', 'max_tier')
    price = PRICES[current]
    need(s['journey']['wallet'] >= 0, 'Ví đang nợ. Trả nợ trước rồi nâng cấp nhé.', 'in_debt')
    need(qy._have(s) >= price, f'Cần {qy._fmt(price)} xu trong ví hoặc tài khoản.', 'no_money')
    label = f'{LABELS[track]} · bậc {current+1}'
    qy._take(s, price, label, st['trade'] if st else None)
    holder.setdefault('paid_tier', {})[track] = current+1
    if st:
        qy._log(st, s['journey']['life_day'], label, -price)
    return dict(message=f'{label}: {LIMITS[track][current+1]}.')
