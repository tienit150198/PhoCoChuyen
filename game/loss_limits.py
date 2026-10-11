"""Small compulsory monetary losses, capped against the affected liquid pocket.

Apply protection discounts after this ceiling. Savings, investments, and other
pockets are never fallback payment sources for a compulsory incident.
"""

RESERVE = 100
THEFT_PCT, THEFT_MAX = 1, 1000
FINE_PCT, FINE_MAX = 2, 2000


def bounded_loss(balance: int, requested: int, *, fine: bool = False) -> int:
    cash = max(0, int(balance))
    pct, maximum = (FINE_PCT, FINE_MAX) if fine else (THEFT_PCT, THEFT_MAX)
    return min(max(0, int(requested)), cash * pct // 100, maximum, max(0, cash - RESERVE))
