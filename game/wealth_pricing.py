"""Pure asset valuation and bounded, progressive security prices.

No database access or public-state construction. Callers save a quote before
charging so market changes and repeated reads cannot reprice an existing bill.
"""
import random

# Compatible-reader releases disable new quote writes until all workers accept them.
ENABLED = True
ALLOWANCE = 10000
STEP = 100000
MAX_MULTIPLIER = 1000
MAX_WEALTH = 10**16
MAX_EVENT_COST = 10**9


def total(s):
    from . import housing, garage, gadgets, invest, vang, journey
    j = s.get('journey') or {}
    bank = j.get('bank') or {}
    wealth = max(0, j.get('wallet', 0))
    wealth += sum(max(0, bank.get(k, 0)) for k in ('balance', 'demand'))
    wealth += sum(max(0, t.get('amount', 0)) for t in bank.get('terms', []))
    iv = j.get('invest') or {}
    wealth += max(0, (iv.get('saving') or {}).get('balance', 0))
    if iv.get('coin'):
        wealth += invest.value(s)
    wealth += vang.value(s)
    home = j.get('home') or {}
    owned = ([home['own']] if home.get('own') else []) + list(home.get('props', []))
    seen = set()
    for house in owned:
        if house.get('id') in seen:
            continue
        seen.add(house.get('id'))
        wealth += housing.value_of(house, j.get('life_day', 1), j.get('property_market_basis', {}).get(house.get('id'), 10000))
    wealth += sum(garage.sell_price(car['p']) for car in (j.get('garage') or {}).get('cars', {}).values())
    wealth += sum(gadgets.sell_price(x['p']) for x in (j.get('gadgets') or {}).get('own', {}).values())
    wealth += sum(max(0, st.get('fund', 0)) + max(0, st.get('till', 0))
                  for st in (j.get('quay') or {}).get('stalls', []))
    wealth += sum(max(0, c.get('money', 0)) for cid, c in s.get('careers', {}).items()
                  if c.get('started') and not journey._employed(cid))
    return min(MAX_WEALTH, max(0, wealth))


def cost(base, wealth):
    if base <= 0:
        return 0
    numerator = min(STEP * MAX_MULTIPLIER, STEP + max(0, wealth - ALLOWANCE))
    return (base * numerator + STEP - 1) // STEP


def valid_wealth(value):
    return type(value) is int and 0 <= value <= MAX_WEALTH


def protection_quote(s):
    return dict(day=s['journey']['life_day'], wealth=total(s))


def event_quote(s, event_id, wealth=None):
    """One deterministic server draw per event; callers persist this quote."""
    seed = s.get('journey', {}).get('seed', 0)
    percent = random.Random(f'security-percent-v1|{seed}|{event_id}').randint(1, 20)
    return dict(wealth=total(s) if wealth is None else wealth, percent=percent)


def valid_event_quote(row):
    return valid_wealth(row.get('wealth')) and type(row.get('percent')) is int and 1 <= row['percent'] <= 20


def event_cost(row):
    return min(MAX_EVENT_COST, (row['wealth'] * row['percent'] + 99) // 100)
