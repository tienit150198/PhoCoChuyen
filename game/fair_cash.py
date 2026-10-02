"""🎁 Tiền vốn hội chợ and 💸 Vay nóng hội chợ (owner 03/10: "hội chợ cho vay khoản tiền nhanh cho tất cả mọi người,
lãi 20%, và vào thì thưởng tất cả 500 xu tiền vốn" — the fair's own exception to "no loans at the fair").

* The gift: GIFT xu into the wallet once per save and fair edition, claimed by the newer client when the player first
  opens the fair while it is open (fair_gift). Not fair winnings: not in today's net, not in points.
* The loan (Bà Sáu cho vay nóng): one at a time, LOAN_MIN..LOAN_MAX xu from the LOAN_STEPS, owed ×(100 + RATE) %
  rounded up, flat. fair_borrow pays it into the wallet, fair_repay pays it all back from the wallet. Once the fair
  has closed, settle() (run before every command, engine._apply_action) takes what is owed from the wallet, then from
  the bank account (like game/garage.py pays), never below zero; what is still missing stays as `debt`, taken from the
  wallet at later commands (so from later income) until it is paid. Not winnings either (not in net, caps or points).

Save: journey['fair_cash'] (optional, created on first use) {v, gift: the edition claimed or '', loan: None or
{ed, p, due}, debt}. It sits beside journey['fair'] (not inside it) because an older server's fair validator refuses
unknown keys there, while the journey tolerates new optional blocks (rolling release). Wallet rows: kind 'fair'.
"""
from __future__ import annotations

import math

VERSION = 1
GIFT = 500
RATE = 20                       # % flat
LOAN_STEPS = (50, 100, 200, 300, 500)
LOAN_MIN, LOAN_MAX = LOAN_STEPS[0], LOAN_STEPS[-1]
COMMANDS = ('fair_gift', 'fair_borrow', 'fair_repay')
LATE = ('fair_repay',)          # paying back still works after the close
KEYS = ('v', 'gift', 'loan', 'debt')
LOAN_KEYS = ('ed', 'p', 'due')
LENDER = 'Bà Sáu cho vay nóng'


def owed(amount: int) -> int:
    return math.ceil(amount * (100 + RATE) / 100)


def _state(j: dict) -> dict:
    c = j.get('fair_cash')
    if not isinstance(c, dict):
        c = j['fair_cash'] = dict(v=VERSION, gift='', loan=None, debt=0)
    return c


def _jr():
    from . import journey as jr
    return jr


def apply(s: dict, name: str, p: dict, t: float, ed: str, is_open: bool) -> dict:
    """fair_gift / fair_borrow / fair_repay (the fair module checked the story and the command name)."""
    from .engine import need
    j = s['journey']
    c = _state(j)
    result = dict(message='', effects=[])
    if name == 'fair_gift':
        need(not p, 'Dữ liệu thao tác không hợp lệ.')
        need(is_open, 'Hội chợ đang đóng.', 'fair_closed')
        need(c['gift'] != ed, 'Bạn đã nhận tiền vốn hội chợ rồi nha.', 'fair_gift_done')
        c['gift'] = ed
        _jr()._wallet(j, GIFT, 'fair', '🎁 Tiền vốn hội chợ (ban tổ chức tặng)')
        result['fair'] = dict(game='cash', gift=GIFT)
        result['message'] = f'Ban tổ chức tặng {GIFT} xu làm vốn chơi hội!'
    elif name == 'fair_borrow':
        need(set(p) == {'amount'} and type(p['amount']) is int and p['amount'] in LOAN_STEPS,
             f'Vay {", ".join(map(str, LOAN_STEPS))} xu thôi nha.')
        need(is_open, 'Hội chợ đang đóng.', 'fair_closed')
        need(c['loan'] is None, 'Trả hết khoản đang vay rồi mới vay tiếp nha.', 'fair_loan_open')
        need(c['debt'] == 0, 'Còn nợ vay nóng kỳ trước, trả xong rồi vay tiếp nha.', 'fair_loan_open')
        amount = p['amount']
        c['loan'] = dict(ed=ed, p=amount, due=owed(amount))
        _jr()._wallet(j, amount, 'fair', f'💸 Vay nóng hội chợ (trả {owed(amount)} xu)')
        result['fair'] = dict(game='cash', borrowed=amount, due=owed(amount))
        result['message'] = f'Đã vay {amount} xu, trả lại {owed(amount)} xu nha.'
    elif name == 'fair_repay':
        need(not p, 'Dữ liệu thao tác không hợp lệ.')
        due = (c['loan'] or {}).get('due', 0) + c['debt']
        need(due > 0, 'Bạn không nợ gì cả.', 'fair_loan_none')
        need(j['wallet'] >= due, f'Ví cần đủ {due} xu để trả hết nha.', 'fair_wallet')
        c['loan'], c['debt'] = None, 0
        _jr()._wallet(j, -due, 'fair', '💸 Trả vay nóng hội chợ')
        result['fair'] = dict(game='cash', repaid=due)
        result['message'] = f'Đã trả {due} xu, hết nợ rồi!'
    return result


def settle(s: dict, ed: str, closed: bool) -> None:
    """Before every command: a loan of a fair that has closed (or of an older edition) is collected from the wallet,
    then the bank account; what is missing becomes `debt`, taken from the wallet whenever there is some."""
    j = s.get('journey')
    c = j.get('fair_cash') if isinstance(j, dict) else None
    if not isinstance(c, dict):
        return
    ln = c['loan']
    if ln and (closed or ln['ed'] != ed):
        c['loan'] = None
        due = ln['due']
        cash = min(max(0, j['wallet']), due)
        if cash:
            _jr()._wallet(j, -cash, 'fair', '💸 Hội chợ tàn: thu vay nóng')
        rest = due - cash
        if rest:
            from . import bank as bk
            b = bk.get(s)
            take = min(max(0, b['balance']), rest) if b else 0
            if take:
                b['balance'] -= take
                bk._log(b, j['life_day'], 'acc', 'Hội chợ thu vay nóng', -take)
                rest -= take
        if rest:
            c['debt'] += rest
            _jr()._history(j, 0, 'fair', f'💸 Còn nợ vay nóng hội chợ {rest} xu (trừ dần khi có tiền vào ví)')
    if c['debt'] and j['wallet'] > 0:
        take = min(j['wallet'], c['debt'])
        c['debt'] -= take
        _jr()._wallet(j, -take, 'fair', '💸 Trả dần nợ vay nóng hội chợ' + ('' if c['debt'] else ' (hết nợ)'))


def public(j: dict, ed: str, is_open: bool) -> dict:
    c = j.get('fair_cash') if isinstance(j.get('fair_cash'), dict) else {}
    ln = c.get('loan')
    return dict(gift=GIFT, gift_ready=is_open and c.get('gift', '') != ed, rate=RATE, steps=list(LOAN_STEPS),
                loan=dict(p=ln['p'], due=ln['due']) if ln else None, debt=c.get('debt', 0), lender=LENDER)


def validate(j: dict) -> None:
    if 'fair_cash' not in j:
        return
    from .engine import need, integer
    bad = 'Dữ liệu vay nóng hội chợ không hợp lệ.'
    c = j['fair_cash']
    need(isinstance(c, dict) and set(c) == set(KEYS) and c['v'] == VERSION and isinstance(c['gift'], str)
         and len(c['gift']) <= 12, bad, 'invalid_save')
    integer(c['debt'], 0, 10**7)
    ln = c['loan']
    if ln is not None:
        need(isinstance(ln, dict) and set(ln) == set(LOAN_KEYS) and isinstance(ln['ed'], str) and len(ln['ed']) <= 12
             and ln['p'] in LOAN_STEPS and ln['due'] == owed(ln['p']), bad, 'invalid_save')
