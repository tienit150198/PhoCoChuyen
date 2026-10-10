"""🕶️ Chợ đen: free entry and the police's arrests (owner 10/10: remove the entry fee).

* Entry is free for everyone (owner 10/10): no bảo kê and no refusal robbery. Legacy pay/refuse commands are
  safe no-ops for older clients. Historical paid/robbed saves remain readable; a saved same-day ban still blocks
  entry, then expires at Vietnam midnight. Entry policy does not switch off police enforcement.
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
* Nothing about the rate or the percentages reaches the client (owner 08/10: no odds shown); receipts show fines.

Historical fees/robberies and current fines are fair losses (journey['fair'] net and stats.lost: the Bảng vàng),
Sổ ví rows of kind 'fair'
(rows of at most ROW_MAX xu: the validators' bound on one row, a larger sum takes several). Nothing goes negative.

Save: journey['fair_bm'] {d: the Vietnam date, s: 'paid' | 'robbed' | 'ban'} (optional; legacy paid/robbed
records are kept unchanged; a ban expires next Vietnam day). It sits beside
journey['fair'] because an older server's fair validator refuses unknown keys there, while the journey keeps new
optional blocks (rolling release: a 1.9.26 server simply ignores it and lets the player in).
"""
from __future__ import annotations

import os
import random

KEY = 'fair_bm'
BM_FEE = 0                     # legacy public field: entry is free
FINE_PCT = 30                  # caught: this % of the wallet left after the stake (never shown)
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
FINE_LABEL = '🚨 Công an bắt ở chợ đen · Nộp phạt'
GUARD = ('Đàn em chợ đen', '🕶️')
NEED_IN = 'Hôm nay bạn bị đuổi khỏi chợ đen rồi, mai quay lại nhé.'
BANNED = 'Hôm nay bạn bị đuổi khỏi chợ đen rồi, mai quay lại nhé.'
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
    """Police enforcement and saved bans are in force: always, but MNL_BM_OFF=1 (tests/__init__.py, so the tests of the
    stalls' own rules play their scripted rounds as before; tests/test_black_market.py turns it back on)."""
    return os.environ.get('MNL_BM_OFF', '') != '1'


def _vn_date(t: float) -> str:
    from .fair import vn_date
    return vn_date(t)


def asked(j: dict, t: float) -> bool:
    """Compatibility helper: entry never requires payment."""
    return False


def status(j: dict, t: float) -> str:
    """Free entry, except a historical ban for the current Vietnam date."""
    b = j.get(KEY)
    if isinstance(b, dict) and b.get('s') == 'ban' and b.get('d') == _vn_date(t):
        return 'ban'
    return 'free'


IN = ('paid', 'robbed', 'free')


def inside(j: dict, t: float) -> bool:
    """Free entry unless banned today (always True when enforcement is off)."""
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
    return dict(message='', effects=[], fair=dict(game='bm', bm=public(j, t), again=True))


def arrest(j: dict, f: dict, t: float, game: str, stake: int, pay) -> dict:
    """The police caught this paid round: `pay(-stake)` takes its stake (the stall's own Sổ ví row), then the fine,
    then JAIL_DAYS days in the trại tạm giữ (game/jail.py; 0 when MNL_JAIL_OFF). Returns the receipt (xu and days)."""
    from . import jail
    pay(-stake)
    fine = _take(j, f, max(0, j['wallet']) * FINE_PCT // 100, FINE_LABEL)
    days = jail.arrest(j, 'bm', JAIL_DAYS, t)
    return dict(game=game, stake=stake, fine=fine, wallet=j['wallet'], say=SAY_ARREST, jail=days)


def public(j: dict, t: float) -> dict:
    """api.state.fair.bm: zero legacy fee and today's standing; no police rate or percentage."""
    st = status(j, t) if _gate_on() else 'free'
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
