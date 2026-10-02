"""🍡 Hàng ăn vặt hội chợ: the two food carts of the walkable fairground (public/js/scenes/fair-place.js 'candy' and
'cane') sell a few folk snacks for a little xu (owner 03/10: "người ta mua đồ ăn, uống nước mía được nữa nhé").

Eating works like the work day's Ăn thêm (game/needs.py, jr_needs_snack): the price comes from the wallet (refused
when the wallet does not hold it: food never makes debt) and no bụng / tỉnh táo go up (at most 100). Unlike Ăn thêm
it is never refused for a full belly: a treat at the fair is bought for the fun of it (owner 03/10: "kẹo bông, nước
mía… hội chợ không mua được, sửa cho mua nhé": a save fresh from breakfast sits at FULL_CAP, so every cart was shut).
Eaten when already full, it only says so. No tinh thần, no daily cap, no new state: the needs
record is created like on any first story action (needs.ensure). Bought only while the fair is open (game/fair.py
checks it), also in the evening: what is eaten then counts towards tomorrow morning like the dinner does.
Sổ ví: one row a life day (kind 'fair', "🍡 Ăn vặt hội chợ · N món"), updated in place like the stalls' rows.
"""
from __future__ import annotations

import re

from . import needs as nd

COMMANDS = ('fair_snack',)
LABEL = '🍡 Ăn vặt hội chợ'
CARTS = ('candy', 'cane')       # fair-place.js spots: cô Út's kẹo bông cart, chú Năm's nước mía cart
# id → the cart that sells it, what it is, its price (xu), no bụng / tỉnh táo added, the line when it is eaten
MENU = {
    'keo_bong': dict(cart='candy', emoji='🍭', name='Kẹo bông gòn', price=2, full=5, wake=0,
                     say='Xốp xốp, ngọt lịm, dính cả mép luôn!'),
    'bap_nuong': dict(cart='candy', emoji='🌽', name='Bắp nướng mỡ hành', price=3, full=15, wake=0,
                      say='Thơm lừng mỡ hành, gặm từng hàng hạt nóng hổi!'),
    'banh_trang': dict(cart='candy', emoji='🍘', name='Bánh tráng nướng', price=4, full=20, wake=0,
                       say='Giòn rụm, trứng cút với hành phi, thơm phức!'),
    'nuoc_mia': dict(cart='cane', emoji='🥤', name='Ly nước mía tắc', price=2, full=5, wake=8,
                     say='Mát rượi cả cổ họng, tỉnh hẳn người!'),
    'che': dict(cart='cane', emoji='🍧', name='Ly chè ba màu', price=3, full=12, wake=0,
                say='Đậu xanh, đậu đỏ, nước cốt dừa béo ngậy, mát lạnh!'),
    'tau_hu': dict(cart='cane', emoji='🍮', name='Chén tàu hũ nước đường', price=2, full=10, wake=0,
                   say='Tàu hũ mềm mịn, nước đường gừng ấm bụng!'),
}


def _jr():
    from . import journey as jr
    return jr


def _n(s: dict) -> dict:
    """The needs numbers as they are (a save without them: the fresh record's)."""
    return nd.get(s) or nd.initial(s['journey']['life_day'])


def _room(s: dict, x: dict) -> bool:
    """Whether eating it still moves a bar (else it is eaten just for the taste)."""
    n = _n(s)
    return bool((x['full'] and n['full'] < 100) or (x['wake'] and n['wake'] < 100))


def why(s: dict, x: dict) -> str:
    """Why this snack cannot be bought now ('' = it can): only a wallet short of its price."""
    if int(s['journey'].get('wallet', 0)) < x['price']:
        return 'Chưa đủ xu'
    return ''


def _row(j: dict, price: int) -> None:
    """Pay `price` into today's snack row (one a life day, looked for among the day's last rows), else a new row."""
    for row in reversed(j['history'][-12:]):
        if not isinstance(row, dict) or row.get('day') != j['life_day']:
            break
        label = str(row.get('label', ''))
        m = re.fullmatch(re.escape(LABEL) + r' · (\d{1,6}) món', label)
        if row.get('kind') == 'fair' and row.get('career') is None and m and abs(row['amount'] - price) <= 10**7:
            j['wallet'] -= price
            row['amount'] -= price
            row['label'] = f'{LABEL} · {int(m.group(1)) + 1} món'
            return
    _jr()._wallet(j, -price, 'fair', f'{LABEL} · 1 món')


def apply(s: dict, p: dict) -> dict:
    """fair_snack {item} (game/fair.py checked the story, the command and that the fair is open)."""
    from .engine import need
    need(set(p) == {'item'} and isinstance(p['item'], str) and p['item'] in MENU, 'Chọn một món nha.')
    j = s['journey']
    x = MENU[p['item']]
    need(not why(s, x), f'Ví còn {max(0, j["wallet"])} xu, chưa đủ {x["price"]} xu.', 'not_enough')
    room = _room(s, x)
    n = nd.ensure(s)
    _row(j, x['price'])
    n['full'] = nd._clamp(n['full'] + x['full'])
    n['wake'] = nd._clamp(n['wake'] + x['wake'])
    gain = ', '.join(([f'no bụng {n["full"]}'] if x['full'] else []) + ([f'tỉnh táo {n["wake"]}'] if x['wake'] else []))
    say = x['say'] if room else f'{x["say"]} No căng rồi mà vẫn ráng ăn cho vui!'
    msg = f'{x["emoji"]} {x["name"]} ({x["price"]} xu): {say}'
    return dict(message=msg, effects=[], fair=dict(game='food', item=p['item'], price=x['price'], say=say,
                                                   full=n['full'], wake=n['wake'], gain=gain))


def public(s: dict) -> list:
    """api.state.fair.food: the carts' menus, each item with why it cannot be bought now (the server decides)."""
    out = []
    for k, x in MENU.items():
        w = why(s, x)
        out.append(dict(id=k, cart=x['cart'], emoji=x['emoji'], name=x['name'], price=x['price'], full=x['full'],
                        wake=x['wake'], ok=not w, why=w))
    return out
