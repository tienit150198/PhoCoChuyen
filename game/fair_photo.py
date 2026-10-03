"""📸 Buồng chụp ảnh hội chợ: the photobooth of the walkable fairground (public/js/scenes/fair-place.js 'pb', the stall
page public/js/v4/fair-booth.js; owner 03/10: "photoboth thì rủ bạn bè tới chụp với nhau ở trong hội chợ nhé").

The shoot itself happens in the players' browsers (alone, or with a stranger or friends in a short-lived room of the
live service, live/booth.py): their characters on the booth's backdrop, four shots, a strip each player saves as a PNG.
Nothing of it reaches the game server or the save. This file only takes the ticket: PRICE xu a shoot, paid by each
player from the journey wallet (refused when the wallet does not hold it: a photo never makes debt), one Sổ ví row a
life day (kind 'fair', "📸 Chụp ảnh hội chợ · N lượt"), updated in place like the food carts' row. Not a game: no net,
not on the Bảng vàng, nothing in journey['fair'], no new state at all (an older server refuses `fair_photo` as an
unknown fair command; its public state has no `photo`, so the newer client leaves the booth out). Bought only while
the fair is open (game/fair.py checks it).
"""
from __future__ import annotations

import re

COMMANDS = ('fair_photo',)
PRICE = 5                       # xu a shoot (four shots), each player pays their own (owner: "xu sinks")
SHOTS = 4
LABEL = '📸 Chụp ảnh hội chợ'
MODES = ('solo', 'stranger', 'friends')


def _jr():
    from . import journey as jr
    return jr


def why(s: dict) -> str:
    """Why a ticket cannot be bought now ('' = it can): only a wallet short of the price."""
    if int(s['journey'].get('wallet', 0)) < PRICE:
        return 'Chưa đủ xu'
    return ''


def _row(j: dict, price: int) -> int:
    """Pay `price` into today's photo row (one a life day, looked for among the day's last rows), else a new row;
    returns the shoots counted on it."""
    for row in reversed(j['history'][-12:]):
        if not isinstance(row, dict) or row.get('day') != j['life_day']:
            break
        m = re.fullmatch(re.escape(LABEL) + r' · (\d{1,6}) lượt', str(row.get('label', '')))
        if row.get('kind') == 'fair' and row.get('career') is None and m and abs(row['amount'] - price) <= 10**7:
            n = min(10**6, int(m.group(1)) + 1)
            j['wallet'] -= price
            row['amount'] -= price
            row['label'] = f'{LABEL} · {n} lượt'
            return n
    _jr()._wallet(j, -price, 'fair', f'{LABEL} · 1 lượt')
    return 1


def apply(s: dict, p: dict) -> dict:
    """fair_photo {mode?} (game/fair.py checked the story, the command and that the fair is open). `mode` only says
    how the player shoots (solo / stranger / friends); the price is the same."""
    from .engine import need
    need(set(p) <= {'mode'} and p.get('mode', 'solo') in MODES, 'Dữ liệu thao tác không hợp lệ.')
    j = s['journey']
    need(not why(s), f'Ví còn {max(0, j["wallet"])} xu, chưa đủ {PRICE} xu chụp ảnh.', 'not_enough')
    n = _row(j, PRICE)
    return dict(message='', effects=[], fair=dict(game='photo', price=PRICE, shots=SHOTS, n=n))


def public(s: dict) -> dict:
    """api.state.fair.photo: the price and whether a ticket can be bought now (the server decides)."""
    w = why(s)
    return dict(price=PRICE, shots=SHOTS, ok=not w, why=w)
