"""🕶️ Chợ đen: the bảo kê at its gate and the police's arrests (owner 08/10: "k phải là hội chợ, nó là "Chợ đen". Vào
chợ đen phải nộp bảo kê, phí bảo kê là 10k xu, nếu k nộp thì bị trấn lột 30% tiền hiện có. vào chợ đen có thể bị công
an bắt, tỷ lệ bị bắt cực cao").

* Bảo kê, once a Vietnam day (UTC+7): before anything in the Chợ đen (game/fair.py GATED: every stall, the food carts,
  the photobooth, a vay nóng), the player settles it. fair_bm_pay takes BM_FEE xu from the wallet (refused when the
  wallet is short); fair_bm_refuse lets the đàn em take ROB_PCT % of the wallet (cash only, never the bank account, 0
  when the wallet is empty or in debt). Either way the player is in until the Vietnam day ends.
* Arrests: every paid round (game/fair.py ARREST_ACTIONS: bầu cua, chiếu trong, a lô tô tờ, a vé cào, a phóng dao run)
  is raided BM_ARREST_P of the time (_arrest_roll, its own random source so the stalls' draws are untouched). Caught:
  the round's stake is gone (no outcome), a fine of FINE_PCT % of the wallet left after the stake, and the player is
  thrown out of the Chợ đen until the Vietnam day ends (rounds already going may still finish: game/fair.py LATE).
* Nothing about the rate or the percentages reaches the client (owner 08/10: no odds shown); the fee is a price and is
  shown, receipts show the xu taken.

Fee, robbery and fine are fair losses (journey['fair'] net and stats.lost: the Bảng vàng), Sổ ví rows of kind 'fair'
(rows of at most ROW_MAX xu: the validators' bound on one row, a larger sum takes several). Nothing goes negative.

Save: journey['fair_bm'] {d: the Vietnam date, s: 'paid' | 'robbed' | 'ban'} (optional). It sits beside
journey['fair'] because an older server's fair validator refuses unknown keys there, while the journey keeps new
optional blocks (rolling release: a 1.9.26 server simply ignores it and lets the player in).
"""
from __future__ import annotations

import os
import random

KEY = 'fair_bm'
BM_FEE = 10000                 # the bảo kê, a Vietnam day (shown: it is a price)
ROB_PCT = 30                   # refusing: the đàn em take this % of the wallet (never shown)
FINE_PCT = 30                  # caught: this % of the wallet left after the stake (never shown)
BM_ARREST_P = 0.20             # a paid round raided by the police ("tỷ lệ bị bắt cực cao"; never shown)
STATES = ('paid', 'robbed', 'ban')
ROW_MAX = 10**7                # one Sổ ví row's |amount| (journey.validate)
COMMANDS = ('fair_bm_pay', 'fair_bm_refuse')
FEE_LABEL = '🕶️ Nộp bảo kê chợ đen'
ROB_LABEL = '🕶️ Bị trấn lột ở chợ đen'
FINE_LABEL = '🚨 Công an bắt ở chợ đen · Nộp phạt'
GUARD = ('Đàn em chợ đen', '🕶️')
SHORT = 'Ví không đủ 10.000 xu tiền bảo kê.'
NEED_IN = 'Vào chợ đen phải nộp bảo kê trước đã. Tải lại trang nếu chưa thấy đàn em ở cổng nha.'
BANNED = 'Hôm nay bạn bị đuổi khỏi chợ đen rồi, mai quay lại nhé.'
SAY_ROB = 'Không nộp hả? Vậy anh em lục ví chút nha.'
SAY_EMPTY = 'Ví trống trơn à? Thôi vô đi, lần sau nhớ nộp.'
SAY_PAID = 'Nộp đủ rồi, hôm nay cứ ra vô thoải mái.'
SAY_ARREST = 'Tất cả đứng im! Đánh bạc ăn tiền hả? Tiền cược tịch thu, nộp phạt rồi ra khỏi chợ.'

_rng = random.SystemRandom()   # the arrests' own draws: the stalls' _rng (and the tests' scripted draws) stay as they were


def _arrest_roll() -> bool:
    """True when the police raid this paid round. Tests patch it."""
    return _rng.random() < BM_ARREST_P


def _gate_on() -> bool:
    """The bảo kê gate and the arrests are in force: always, but MNL_BM_OFF=1 (tests/__init__.py, so the tests of the
    stalls' own rules play their scripted rounds as before; tests/test_black_market.py turns it back on)."""
    return os.environ.get('MNL_BM_OFF', '') != '1'


def _vn_date(t: float) -> str:
    from .fair import vn_date
    return vn_date(t)


def status(j: dict, t: float) -> str:
    """Today's standing: '' (nothing settled today), 'paid', 'robbed' or 'ban'."""
    b = j.get(KEY)
    if not isinstance(b, dict) or b.get('d') != _vn_date(t) or b.get('s') not in STATES:
        return ''
    return b['s']


def inside(j: dict, t: float) -> bool:
    """Bảo kê settled today and not thrown out (always True when the gate is off)."""
    return not _gate_on() or status(j, t) in ('paid', 'robbed')


def _set(j: dict, t: float, st: str) -> None:
    j[KEY] = dict(d=_vn_date(t), s=st)


def _take(j: dict, f: dict, amount: int, label: str) -> int:
    """Take `amount` xu from the wallet (never below zero: what it does not hold is let go), Sổ ví rows of at most
    ROW_MAX each; a fair loss (net, stats.lost). Returns what was taken."""
    from . import journey as jr
    amount = max(0, min(int(amount), j['wallet']))
    left = amount
    while left > 0:
        part = min(left, ROW_MAX)
        jr._wallet(j, -part, 'fair', label)
        left -= part
    if amount:
        f['net'] = max(-10**9, f['net'] - amount)
        f['stats']['lost'] = min(10**9, f['stats']['lost'] + amount)
    return amount


def apply(s: dict, name: str, p: dict, f: dict, t: float) -> dict:
    """fair_bm_pay / fair_bm_refuse (game/fair.py checked the story, the command and that the Chợ đen is open)."""
    from .engine import need
    j = s['journey']
    need(not p, 'Dữ liệu thao tác không hợp lệ.')
    st = status(j, t)
    need(st != 'ban', BANNED, 'fair_bm_ban')
    if st:   # already settled today (another tab, a retry): nothing more to pay
        return dict(message='', effects=[], fair=dict(game='bm', bm=public(j, t), again=True))
    if name == 'fair_bm_pay':
        need(j['wallet'] >= BM_FEE, SHORT, 'fair_bm_short')
        _take(j, f, BM_FEE, FEE_LABEL)
        _set(j, t, 'paid')
        out = dict(paid=BM_FEE, wallet=j['wallet'], say=SAY_PAID)
        msg = f'Đã nộp bảo kê {BM_FEE:,} xu. Hôm nay ra vô chợ đen thoải mái.'.replace(',', '.')
    else:
        took = _take(j, f, max(0, j['wallet']) * ROB_PCT // 100, ROB_LABEL)
        _set(j, t, 'robbed')
        out = dict(robbed=took, wallet=j['wallet'], say=SAY_ROB if took else SAY_EMPTY)
        msg = f'Bị trấn lột {took:,} xu.'.replace(',', '.') if took else 'Ví trống trơn, đàn em cho qua.'
    return dict(message=msg, effects=[], fair=dict(game='bm', bm=public(j, t), **out))


def arrest(j: dict, f: dict, t: float, game: str, stake: int, pay) -> dict:
    """The police caught this paid round: `pay(-stake)` takes its stake (the stall's own Sổ ví row), then the fine,
    then the ban for the rest of the Vietnam day. Returns the receipt (xu only)."""
    pay(-stake)
    fine = _take(j, f, max(0, j['wallet']) * FINE_PCT // 100, FINE_LABEL)
    _set(j, t, 'ban')
    return dict(game=game, stake=stake, fine=fine, wallet=j['wallet'], say=SAY_ARREST)


def public(j: dict, t: float) -> dict:
    """api.state.fair.bm: the fee (a price), today's standing; no rate, no percentage."""
    st = status(j, t) if _gate_on() else 'paid'
    return dict(fee=BM_FEE, st=st, inside=st in ('paid', 'robbed'), ban=st == 'ban', who=list(GUARD))


def validate(j: dict) -> None:
    if KEY not in j:
        return
    from .engine import need
    import datetime
    b = j[KEY]
    need(isinstance(b, dict) and set(b) == {'d', 's'} and b['s'] in STATES and isinstance(b['d'], str)
         and len(b['d']) == 10, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
    try:
        datetime.date.fromisoformat(b['d'])
    except ValueError:
        need(False, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
