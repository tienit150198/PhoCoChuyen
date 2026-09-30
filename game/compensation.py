"""Tiền đền: one knob for what the player pays out as compensation or penalty.

COMPENSATION_FACTOR scales every amount the player (or their shop) must pay
for damage they caused, a customer's loss they answer for, or walking off work
mid-job (bỏ dở việc). comp() applies it where the amount is decided, so the
number shown to the player is the number charged.

Scaled: happenings you must pay for (comp, and the wallet part of kind 'den'),
the abandon fine, incident lines of category 'compensation' (built by F/W in
incident_content), and career đền / bồi thường (a wallet handed to the wrong
person, a broken parcel, a scooter bump, dead bees, a lost-and-found mix-up, a
data leak).
Not scaled: money the player receives (someone paying you back, refunds from a
supplier, tips, pay), refunds of a price or deposit the customer paid, the
voluntary review-reply offers (quà / voucher / hoàn), paying off an extortion
demand, regulatory fines (inspections, tax, police tickets), office mistake
penalties, and bank fees / late fees.
"""
from __future__ import annotations

COMPENSATION_FACTOR = 0.8


def comp(amount: int) -> int:
    """`amount` xu of đền after the factor: rounded half up, never negative,
    at least 1 xu when the original was at least 1."""
    amount = int(amount)
    if amount <= 0:
        return 0
    return max(1, int(amount * COMPENSATION_FACTOR + 0.5))
