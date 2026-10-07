"""💹 Chỉ số giá: one place for what the street charges a player (owner 07/10: "tăng giá tất cả mọi thứ trong game lên
... tăng 10% mọi thứ ... hiện tại mọi người nhiều tiền quá rồi").

Every catalogue of things a PLAYER PAYS for writes its prices as they were before 07/10 (the "base" price) and passes
them through `price()` when the catalogue is built (at import). The next adjustment is one line here.

* INDEX_PCT: everything a player pays (homes' tax, vehicles, gadgets, clothes, food, outings, courses, fees, tickets).
* LUXURY: progressive tiers by base price, for the big-ticket toys only the richest buy (the 💰 Tài phú board of 07/10:
  the top 1 % hold 57 % of all net worth; their spending is cars, villas, gold phones). A median player (net worth ~470
  xu) never meets these tiers.
* Never indexed: what a player EARNS (wages, tips, rent from a tenant, what NPC customers pay), a workplace's wholesale
  and supply costs (shop careers keep their margin against salaried ones), prices a player sets (quầy), stakes a
  player chooses (fair), loans and their schedules, and anything a save stores and an older build pins to the
  catalogue (each module says which; game/housing.py charges a home's index as a separate tax for that reason).

Rounding (`nice()`): the result is rounded to a step that suits its size, never below the base price, and a base of 5
xu or more always rises by at least 1 xu. Prices under 5 xu stay (+10 % of 2 xu is not a price).

Pure functions, no state. Other modules import this one; it imports nothing from the game.
"""
from __future__ import annotations

INDEX_PCT = 110                                  # 07/10: +10 % on everything a player pays
LUXURY = ((60000, 130), (20000, 120))            # base price from -> percent (07/10: +30 % / +20 % on the top tiers)
SINCE = '07/10'                                  # shown in the guide line about prices


def pct_for(base: int) -> int:
    """The percent applied to a base price: the luxury tier it falls in, else INDEX_PCT."""
    return next((pct for low, pct in LUXURY if base >= low), INDEX_PCT)


def _step(x: int) -> int:
    if x < 100:
        return 1
    if x < 1000:
        return 5
    if x < 5000:
        return 10
    if x < 20000:
        return 50
    if x < 100000:
        return 100
    return 500


def nice(base: int, pct: int) -> int:
    """base × pct / 100, rounded half up to a step that suits its size; never below base, +1 xu at least from 5 xu."""
    base = int(base)
    if base <= 0 or pct == 100:
        return base
    raw = base * pct / 100
    step = _step(int(raw))
    out = int(raw / step + 0.5) * step
    if base >= 5 and pct > 100:
        out = max(out, base + 1)
    return max(out, base)


def price(base: int, *, luxury: bool = True) -> int:
    """Today's price of something whose base (pre-07/10) price is `base`. luxury=False: INDEX_PCT only (a fee or a
    consumable whose base happens to be large, never a luxury good)."""
    return nice(base, pct_for(base) if luxury else INDEX_PCT)


def extra(base: int, *, luxury: bool = True) -> int:
    """What the index adds to `base` (price(base) − base): charged as its own line where the save pins the base."""
    return price(base, luxury=luxury) - int(base)


def index(table: dict, key: str = 'price', *, luxury: bool = True) -> dict:
    """Index `table[*][key]` in place (catalogue dicts of dicts) and return the table. Rows without the key, or whose
    value is not a positive int, are left alone."""
    for row in table.values():
        if isinstance(row, dict) and type(row.get(key)) is int and row[key] > 0:
            row[key] = price(row[key], luxury=luxury)
    return table
