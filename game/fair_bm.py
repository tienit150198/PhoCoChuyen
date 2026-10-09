"""🕶️ Chợ đen: the bảo kê at its gate and the police's arrests (owner 08/10: "k phải là hội chợ, nó là "Chợ đen". Vào
chợ đen phải nộp bảo kê, phí bảo kê là 10k xu, nếu k nộp thì bị trấn lột 30% tiền hiện có. vào chợ đen có thể bị công
an bắt, tỷ lệ bị bắt cực cao").

* Bảo kê, hên xui (owner 09/10: "phí bảo kê k phải khi nào cũng thu, tỷ lệ thu là hên xui 40% /2 ngày"): the Vietnam
  days (UTC+7) go in stretches of ASK_DAYS (2); in a stretch the đàn em stand at the gate BM_ASK_P (40%) of the time,
  fixed by (journey seed, stretch) so a reload never rerolls (asked()). Not asked: the player walks in, nothing to pay.
  Asked: before anything in the Chợ đen (game/fair.py GATED: every stall, the food carts,
  the photobooth, a vay nóng), the player settles it. fair_bm_pay takes BM_FEE xu from the wallet (refused when the
  wallet is short); fair_bm_refuse lets the đàn em take ROB_PCT % of the wallet (cash only, never the bank account, 0
  when the wallet is empty or in debt). Either way the player is in until the stretch ends.
* Arrests (owner 09/10: "với ae ăn tiền nhiều (hơn 300k) thì mới bị bắt nhé, ít quá k bị bắt", "tỷ lệ bị bắt thấp tý
  nhé"): a paid round (bầu cua, chiếu trong, a lô tô tờ, a vé cào, a đua chó bet; not the skill games phóng dao and
  ô ăn quan since 09/10, whose police are game/fair_watch.py) can be raided only while the
  player's Chợ đen net today is above ARREST_FROM xu (at_risk: journey['fair'].net, which game/fair.py _state resets
  at each Vietnam day: every paid stall's wins minus its losses, the bảo kê, robberies and fines included; the free ô
  ăn quan / ném vòng xu are not in it). Then it is raided BM_ARREST_P of the time (_arrest_roll, its own random source
  so the stalls' draws are untouched). Caught: the round's stake is gone (no outcome), a fine of FINE_PCT % of the
  wallet left after the stake, and JAIL_DAYS days in the trại tạm giữ (game/jail.py; rounds already going may still
  finish once out: game/fair.py LATE).
* Big stakes (owner 09/10 "cược mà ai cược nhiều, từ 50k trở lên thì tăng tỷ lệ bị bắt, mỗi 10k tăng 1%"): a round
  staking BIG_STAKE_FROM xu or more can be raided whatever today's net, big_stake_pct % (1 % at 50,000, 1 % more each
  further 10,000), plus BM_ARREST_P while the net is above ARREST_FROM; never above ARREST_CAP (arrest_p). Same
  consequences.
* Nothing about the rate or the percentages reaches the client (owner 08/10: no odds shown); the fee is a price and is
  shown, receipts show the xu taken.

Fee, robbery and fine are fair losses (journey['fair'] net and stats.lost: the Bảng vàng), Sổ ví rows of kind 'fair'
(rows of at most ROW_MAX xu: the validators' bound on one row, a larger sum takes several). Nothing goes negative.

Save: journey['fair_bm'] {d: the Vietnam date, s: 'paid' | 'robbed' | 'ban'} (optional; a 'ban' of an earlier day of
the stretch still means the bảo kê was settled; the stretch and the ask are computed, never saved). It sits beside
journey['fair'] because an older server's fair validator refuses unknown keys there, while the journey keeps new
optional blocks (rolling release: a 1.9.26 server simply ignores it and lets the player in).
"""
from __future__ import annotations

import datetime
import os
import random

KEY = 'fair_bm'
BM_FEE = 10000                 # the bảo kê, a Vietnam day (shown: it is a price)
ROB_PCT = 30                   # refusing: the đàn em take this % of the wallet (never shown)
FINE_PCT = 30                  # caught: this % of the wallet left after the stake (never shown)
BM_ASK_P = 0.40                # the đàn em ask for bảo kê in a stretch (owner 09/10 "hên xui 40% /2 ngày"; never shown)
ASK_DAYS = 2                   # Vietnam days in a stretch
BM_ARREST_P = 0.05             # a paid round raided by the police (owner 09/10 "tỷ lệ bị bắt thấp tý"; never shown)
ARREST_FROM = 300000           # ... only while today's Chợ đen net is above this (owner 09/10 "hơn 300k"; never shown)
BIG_STAKE_FROM = 50000         # a round staking this much can be raided whatever the net (owner 09/10 "từ 50k trở lên")
BIG_STAKE_STEP = 10000         # ... BIG_STAKE_PCT % at BIG_STAKE_FROM, BIG_STAKE_PCT % more each further step
BIG_STAKE_PCT = 1              # (owner 09/10 "mỗi 10k tăng 1%"; never shown)
ARREST_CAP = 0.30              # a round's whole raid chance never goes above this (never shown; owner 09/10 "tỷ lệ bị bắt khi chơi max 30%")
JAIL_DAYS = 3                  # caught: jail days in the trại tạm giữ (owner 09/10 "chơi cờ bạc bị bắt 3 ngày")
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
SAY_PAID = 'Nộp đủ rồi, cứ ra vô thoải mái.'
SAY_ARREST = 'Tất cả đứng im! Đánh bạc ăn tiền hả? Tiền cược tịch thu, nộp phạt đi!'
SAY_CHEAT = 'Tay gì mà nhanh dữ vậy? Chơi kiểu này là gian rồi, về đồn làm việc!'

_rng = random.SystemRandom()   # the arrests' own draws: the stalls' _rng (and the tests' scripted draws) stay as they were


def at_risk(f: dict | None) -> bool:
    """The police only come for the big winners: today's Chợ đen net (journey['fair'].net, already reset for this
    Vietnam day by game/fair.py _state) above ARREST_FROM."""
    return isinstance(f, dict) and type(f.get('net')) is int and f['net'] > ARREST_FROM


def big_stake_pct(stake) -> int:
    """The big stakes draw the police's eye (owner 09/10 "cược mà ai cược nhiều, từ 50k trở lên thì tăng tỷ lệ bị bắt,
    mỗi 10k tăng 1% (từ mốc 50k)"): BIG_STAKE_PCT % for a round staking BIG_STAKE_FROM, BIG_STAKE_PCT % more for each
    further BIG_STAKE_STEP xu (59,999 → 1, 60,000 → 2, 100,000 → 6); nothing below BIG_STAKE_FROM."""
    if type(stake) is not int or stake < BIG_STAKE_FROM:
        return 0
    return BIG_STAKE_PCT * (1 + (stake - BIG_STAKE_FROM) // BIG_STAKE_STEP)


def arrest_p(f: dict | None, stake) -> float:
    """This paid round's raid chance: BM_ARREST_P while today's net is above ARREST_FROM (at_risk), plus the big
    stake's big_stake_pct, never above ARREST_CAP. 0: the police are not even rolled for. Never shown."""
    pct = big_stake_pct(stake)
    p = pct / 100 + (BM_ARREST_P if at_risk(f) else 0)
    return min(ARREST_CAP, p) if p > 0 else 0.0


def _arrest_roll(p: float = BM_ARREST_P) -> bool:
    """True when the police raid this paid round (p: arrest_p). Tests patch it."""
    return _rng.random() < p


def _gate_on() -> bool:
    """The bảo kê gate and the arrests are in force: always, but MNL_BM_OFF=1 (tests/__init__.py, so the tests of the
    stalls' own rules play their scripted rounds as before; tests/test_black_market.py turns it back on)."""
    return os.environ.get('MNL_BM_OFF', '') != '1'


def _vn_date(t: float) -> str:
    from .fair import vn_date
    return vn_date(t)


def _stretch(d: str) -> int:
    """The stretch of ASK_DAYS Vietnam days a date (YYYY-MM-DD) is in."""
    return datetime.date.fromisoformat(d).toordinal() // ASK_DAYS


def asked(j: dict, t: float) -> bool:
    """Do the đàn em ask this player for bảo kê in this stretch? Fixed by (journey seed, stretch): reloads, retries and
    other tabs see the same answer. Tests patch it."""
    return random.Random(f"bm|{j.get('seed', 0)}|{_stretch(_vn_date(t))}").random() < BM_ASK_P


def status(j: dict, t: float) -> str:
    """The standing now: 'ban' (thrown out today), 'paid' / 'robbed' (bảo kê settled in this stretch), 'free' (the đàn
    em are not asking this stretch) or '' (asked, not settled yet)."""
    b = j.get(KEY)
    today = _vn_date(t)
    if isinstance(b, dict) and b.get('s') in STATES and isinstance(b.get('d'), str):
        if b['d'] == today:   # no ban any more (owner 09/10 "bỏ cấm"): an arrest today still means settled
            return 'paid' if b['s'] == 'ban' else b['s']
        try:
            same = _stretch(b['d']) == _stretch(today)
        except ValueError:
            same = False
        if same:   # settled earlier in the stretch (a ban then: they had come in, so it was settled)
            return 'paid' if b['s'] == 'ban' else b['s']
    return '' if asked(j, t) else 'free'


IN = ('paid', 'robbed', 'free')


def inside(j: dict, t: float) -> bool:
    """In the Chợ đen: bảo kê settled or not asked, and not thrown out (always True when the gate is off)."""
    return not _gate_on() or status(j, t) in IN


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
    if st:   # settled in this stretch, or not asked (another tab, a retry, an old page): nothing to pay
        return dict(message='', effects=[], fair=dict(game='bm', bm=public(j, t), again=True))
    if name == 'fair_bm_pay':
        need(j['wallet'] >= BM_FEE, SHORT, 'fair_bm_short')
        _take(j, f, BM_FEE, FEE_LABEL)
        _set(j, t, 'paid')
        out = dict(paid=BM_FEE, wallet=j['wallet'], say=SAY_PAID)
        msg = f'Đã nộp bảo kê {BM_FEE:,} xu. Cứ ra vô chợ đen thoải mái.'.replace(',', '.')
    else:
        took = _take(j, f, max(0, j['wallet']) * ROB_PCT // 100, ROB_LABEL)
        _set(j, t, 'robbed')
        out = dict(robbed=took, wallet=j['wallet'], say=SAY_ROB if took else SAY_EMPTY)
        msg = f'Bị trấn lột {took:,} xu.'.replace(',', '.') if took else 'Ví trống trơn, đàn em cho qua.'
    return dict(message=msg, effects=[], fair=dict(game='bm', bm=public(j, t), **out))


def arrest(j: dict, f: dict, t: float, game: str, stake: int, pay) -> dict:
    """The police caught this paid round: `pay(-stake)` takes its stake (the stall's own Sổ ví row), then the fine,
    then JAIL_DAYS days in the trại tạm giữ (game/jail.py; 0 when MNL_JAIL_OFF). Returns the receipt (xu and days)."""
    from . import jail
    pay(-stake)
    fine = _take(j, f, max(0, j['wallet']) * FINE_PCT // 100, FINE_LABEL)
    days = jail.arrest(j, 'bm', JAIL_DAYS, t)
    return dict(game=game, stake=stake, fine=fine, wallet=j['wallet'], say=SAY_ARREST, jail=days)


def public(j: dict, t: float) -> dict:
    """api.state.fair.bm: the fee (a price), today's standing; no rate, no percentage."""
    st = status(j, t) if _gate_on() else 'paid'
    return dict(fee=BM_FEE, st=st, inside=st in IN, ban=st == 'ban', who=list(GUARD))


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
