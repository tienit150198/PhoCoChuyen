"""Loa báo tiền: bank transfers that reach the player's own shop account.

Careers call `transfer(amount)` (or kit.bank) at the moment a customer's
transfer / QR payment lands in the shop's account: the grocery's bank app
showing the money, an OTA payout, an office paying its catering order. The
command result then carries `bank=[amounts]` and the browser plays the
"ting ting · Đã nhận N xu" announcement (public/js/v4/sounds.js).

Only the announcement is collected here: money itself is still booked by
engine.money where each career always booked it. Outside a command (tests
calling career helpers directly) the call does nothing.
"""
from __future__ import annotations

import contextvars

_EVENTS: contextvars.ContextVar = contextvars.ContextVar('bank_speaker', default=None)
MAX_EVENTS = 20


def transfer(amount) -> None:
    events = _EVENTS.get()
    if events is not None and type(amount) is int and amount > 0 and len(events) < MAX_EVENTS:
        events.append(amount)


def collect(run):
    """Run one command (`run() -> (state, result)`) and attach its transfers to the result."""
    token = _EVENTS.set([])
    try:
        state, result = run()
        events = _EVENTS.get()
        if events and isinstance(result, dict):
            result = dict(result, bank=list(events))
        return state, result
    finally:
        _EVENTS.reset(token)
