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
  so the stalls' draws are untouched). Caught: the unplayed stake stays in the wallet, a bounded wallet-only fine,
  and JAIL_DAYS days in the trại tạm giữ (game/jail.py; rounds already going may still
  finish once out: game/fair.py LATE).
* Big stakes (owner 09/10 "cược mà ai cược nhiều, từ 50k trở lên thì tăng tỷ lệ bị bắt, mỗi 10k tăng 1%"): a round
  staking BIG_STAKE_FROM xu or more can be raided whatever today's net, big_stake_pct %, plus BM_ARREST_P while the
  net is above ARREST_FROM; never above ARREST_CAP (arrest_p). Same consequences. Owner 11/10 "giảm nhẹ lại vì bị bắt
  nhiều quá": reduce both terms by 15% and the cap from 30% to 25%. Compulsory fines now use loss_limits.
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
FINE_PCT = 30                  # owner 11/10 (later): caught, the round's stake and FINE_PCT % of that stake (round_fine)
BM_ARREST_P = 0.02             # owner 11/10 (later) "tỷ lệ bị bắt giảm thấp"; never shown
ARREST_FROM = 300000           # ... only while today's Chợ đen net is above this (owner 09/10 "hơn 300k"; never shown)
# Owner 11/10 (later) "cho chơi thoải mái, cho ăn vui vẻ, nhưng nếu ăn lời nhiều thì có cơ chế xử lý, mọi trò": the
# police's eye grows with today's Chợ đen winnings, on every paid round of every stall (profit_pct): (net above, %).
PROFIT_CURVE = ((ARREST_FROM, 2), (1_000_000, 5), (3_000_000, 10), (10_000_000, 20))
BIG_STAKE_FROM = 50000         # a round staking this much can be raided whatever the net (owner 09/10 "từ 50k trở lên")
# Owner 11/10 (later): "chơi từ 300k trở lên thì bị bắt nhiều", "cược nhiều thì tỷ lệ bị bắt cực cao" so that no stake
# is worth it: (stake from, % at that stake, stake to, % reached there), linear in between; never shown.
STAKE_CURVE = ((50_000, 2, 300_000, 10), (300_000, 30, 1_000_000, 50), (1_000_000, 50, 10_000_000, 80))
STAKE_TOP_PCT = 90             # from the last step's end
ARREST_CAP = 0.90              # whole-round cap; never shown
JAIL_DAYS = 3                  # caught: jail days in the trại tạm giữ (owner 09/10 "chơi cờ bạc bị bắt 3 ngày")
STATES = ('paid', 'robbed', 'ban')
ROW_MAX = 10**7                # one Sổ ví row's |amount| (journey.validate)
COMMANDS = ('fair_bm_pay', 'fair_bm_refuse')
FINE_LABEL = '🚨 Công an bắt ở chợ đen · Nộp phạt'
GUARD = ('Đàn em chợ đen', '🕶️')
NEED_IN = 'Hôm nay bạn bị đuổi khỏi chợ đen rồi, mai quay lại nhé.'
BANNED = 'Hôm nay bạn bị đuổi khỏi chợ đen rồi, mai quay lại nhé.'
SAY_ARREST = 'Tất cả đứng im! Ván này hủy, giữ lại tiền cược rồi nộp phạt nhẹ thôi nha!'
SAY_SEIZE = 'Tất cả đứng im! Đánh bạc ăn tiền hả? Tiền cược tịch thu, nộp phạt đi!'
SAY_CHEAT = 'Tay gì mà nhanh dữ vậy? Chơi kiểu này là gian rồi, về đồn làm việc!'

_rng = random.SystemRandom()   # the arrests' own draws: the stalls' _rng (and the tests' scripted draws) stay as they were


def at_risk(f: dict | None) -> bool:
    """The police only come for the big winners: today's Chợ đen net (journey['fair'].net, already reset for this
    Vietnam day by game/fair.py _state) above ARREST_FROM."""
    return isinstance(f, dict) and type(f.get('net')) is int and f['net'] > ARREST_FROM


def big_stake_pct(stake) -> float:
    """The big stakes draw the police's eye (STAKE_CURVE, owner 11/10): 0 below BIG_STAKE_FROM, 2 % → 10 % up to
    300,000 xu, 30 % → 50 % up to 1,000,000, 50 % → 80 % up to 10,000,000, then STAKE_TOP_PCT."""
    if type(stake) is not int or stake < BIG_STAKE_FROM:
        return 0.0
    for lo, lo_pct, hi, hi_pct in STAKE_CURVE:
        if stake < hi:
            return lo_pct + (hi_pct - lo_pct) * (stake - lo) / (hi - lo)
    return float(STAKE_TOP_PCT)


def profit_pct(f: dict | None) -> float:
    """PROFIT_CURVE's % for today's Chợ đen net: 0 up to ARREST_FROM (at_risk), then 2 %, 5 % past 1M, 10 % past 3M,
    20 % past 10M."""
    if not at_risk(f):
        return 0.0
    return float(max(pct for lo, pct in PROFIT_CURVE if f['net'] > lo))


def arrest_p(f: dict | None, stake) -> float:
    """This paid round's raid chance: today's winnings' profit_pct plus the stake's big_stake_pct, never above
    ARREST_CAP. 0: the police are not even rolled for. Never shown."""
    p = (big_stake_pct(stake) + profit_pct(f)) / 100
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


def total_money(j: dict) -> int:
    """The wallet and the bank (current account, demand pot, term deposits): what a heavy fine counts."""
    b = j.get('bank') if isinstance(j.get('bank'), dict) else None
    bank = (max(0, b['balance']) + b['demand'] + sum(t['amount'] for t in b['terms'])) if b else 0
    return max(0, j['wallet']) + bank


def take_total(j: dict, f: dict, amount: int, label: str) -> int:
    """Take `amount` xu from the wallet, then the bank's current account, its demand pot and its term deposits (closed
    early, principal only, the rest back to the account); never below zero. A fair loss (net, stats.lost). Owner 11/10:
    a Chợ đen arrest or a "thiết bị hỗ trợ" fine counts the bank too (no loss_limits ceiling). Returns what was taken."""
    from . import bank as bk
    from . import bank_content as K
    taken = _take(j, f, min(int(amount), max(0, j['wallet'])), label)
    left = int(amount) - taken
    b = j.get('bank') if isinstance(j.get('bank'), dict) else None
    if left > 0 and b is not None:
        day = j['life_day']
        x = min(left, max(0, b['balance']))
        if x:
            b['balance'] -= x
            left -= x
            bk._log(b, day, 'acc', label, -x)
        x = min(left, b['demand'])
        if x:
            b['demand'] -= x
            if not b['demand']:
                b['pend'] = 0
            left -= x
            bk._log(b, day, 'sav', label + ' (sổ không kỳ hạn)', -x)
        for t in sorted(list(b['terms']), key=lambda t: t['start'] + t['term']):
            if left <= 0:
                break
            b['terms'].remove(t)   # closed early, principal only
            x = min(left, t['amount'])
            left -= x
            rest = t['amount'] - x
            bk._log(b, day, 'sav', f'{label}: tất toán sổ {K.TERMS[t["term"]].lower()}', -t['amount'])
            if rest:
                b['balance'] += rest
                bk._log(b, day, 'acc', 'Phần còn lại của sổ bị tất toán', rest)
        from_bank = int(amount) - taken - left
        if from_bank:
            f['net'] = max(-10**9, f['net'] - from_bank)
            f['stats']['lost'] = min(10**9, f['stats']['lost'] + from_bank)
            taken += from_bank
    return taken


def round_fine(stake: int) -> int:
    """FINE_PCT % of the caught round's own stake (owner 11/10 "phải tính tiền phạt của 1 trận": a 10k round is
    never fined for the rest of the day's play)."""
    return max(0, int(stake)) * FINE_PCT // 100


def arrest(j: dict, f: dict, t: float, game: str, stake: int, pay, *, charge: bool = True, seize: bool = False) -> dict:
    """The police caught this round, then JAIL_DAYS days in the trại tạm giữ. seize (owner 11/10, the Chợ đen's own
    arrest roll): the round's stake is taken (`pay(-stake)`, the stall's Sổ ví row) and round_fine(stake) from the
    wallet and the bank (take_total). Otherwise (the skill stalls' watch) the stake is not charged and only
    round_fine(stake) is, from the wallet."""
    from . import jail
    if seize:
        due = round_fine(stake) if charge else 0
        if stake:
            pay(-stake)
        fine = take_total(j, f, due, FINE_LABEL) if due else 0
    else:   # owner 11/10: the round's own stake, never the wallet
        due = min(max(0, j['wallet']), round_fine(stake)) if charge else 0
        fine = _take(j, f, due, FINE_LABEL)
    days = jail.arrest(j, 'bm', JAIL_DAYS, t)
    return dict(game=game, stake=stake, fine=fine, wallet=j['wallet'], say=SAY_ARREST if not seize else SAY_SEIZE,
                jail=days, canceled=not seize, seized=stake if seize else 0)


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
