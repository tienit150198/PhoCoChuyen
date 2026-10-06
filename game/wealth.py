"""💰 Net worth of a save, for the 💰 Tài phú board (game/leaderboard.py `wealth`).

Two parts, both read from the save itself (never the database, never a live price):

1. What "Tiền của bạn" shows (`pockets()` of public/js/v4/wealth.js: "Tổng tài sản" − "Tổng nợ"), read from the save
   instead of the public view the sheet gets (journey.public, bank.public, housing.public) — `sheet()`:

  assets = max(0, wallet)                                    journey.wallet
         + Σ max(0, fund)    of every workplace you started  careers[cid].money where careers[cid].started
                             (none started: the fund of the workplace on screen, like the sheet)
         + bank account + demand savings + Σ term deposits    journey.bank.balance, .demand, .terms[].amount
         + Σ market value of every home you own              housing.value_of(x, life_day, basis), x in home.own +
                                                             home.props, basis = journey.property_market_basis[x.id]
                                                             (10000 when absent; today's property_market quote, a
                                                             pure function of the Vietnam calendar, like the sheet)
  debt   = max(0, −wallet) + Σ max(0, −fund)
         + Σ what is left on every bank loan                 Σ rows (amount − paid), loans with something left
         + the credit card balance                           journey.bank.card.bal
         + Σ what is left on every home loan                 Σ home loan rows (amount − paid)

2. What the sheet does not list (1.5–1.7) but the save holds as plain numbers, valued the way the game itself would
   pay them out today, or at what was paid for them — `extras()`:

  assets + 🐷 Mây savings book                               journey.invest.saving.balance (the milli-xu interest
                                                             not credited yet is left out)
         + 🪙 Mây Coin at its cost basis (giá vốn)           journey.invest.coin.basis while .units > 0 (xu paid,
                                                             fee included; a sale takes its share off)
         + 💰 gold at its cost basis (giá vốn)               journey.vang.cost while .phan > 0 (xu paid, the shop's
                                                             spread included; a sale takes its share off)
         + 🚗 every vehicle at the garage's buy-back price   garage.sell_price(p), journey.garage.cars[*].p
         + 🏪 every Quầy riêng at its sang nhượng price      quay.sell_back() without its floor: place price ×
                                                             SELL_PCT + upgrades × UPGRADE_BACK + till + fund,
                                                             journey.quay.stalls[*]
  debt   + what is still owed on those counters             stalls[*].due + stalls[*].business.unpaid_fines
         + 💸 Vay nóng hội chợ                                journey.fair_cash.loan.due + journey.fair_cash.debt

  net    = assets − debt (sheet + extras)

Mây Coin and gold are counted at cost, never at a market price (lead 06/10): the price is the shared real-time
market (game/realtime_market.py, a new quote every ten minutes); valuing them at it would be a live market lookup on
every save write and a row that is stale minutes later. At cost, buying moves xu between pockets (net worth stays)
and only a sale moves it, by the realised profit or loss. Said so on the board's rule line.

Left out (the rule line names the Quỹ chung):
* The couple's 💞 Quỹ chung: it lives outside the save (marriage tables) and belongs to two people.
* Money in flight outside the save: a bank transfer not received yet (bank_xfers rows), a hired player's escrowed
  wage (quay_jobs), a rental's prepaid days (rentals rows), a 🎲 scam stake (lost by design).
Free play has no wallet (wealth.js `story`): None.

Dict reads only, plus a few integer operations per home, vehicle and counter (no copy, no upgrade in place, no
database, no live price); never raises (an unreadable save has no row). tests/test_lb_wealth.py checks `sheet()`
against pockets() of wealth.js on real saves and `extras()` against the game's own sell prices.
"""
from __future__ import annotations

INT_MAX = 2**31 - 1     # leaderboard columns are INTEGER (PostgreSQL int4)


def _n(v) -> int:
    """wealth.js `num`: a number or 0 (booleans are not money)."""
    if type(v) is int:
        return v
    if type(v) is float and v == v and abs(v) != float('inf'):
        return int(v)
    return 0


def _d(v) -> dict:
    return v if type(v) is dict else {}


def _l(v) -> list:
    return v if type(v) is list else []


def _rows_left(ln) -> int:
    """What is left to pay on a loan (bank or home): Σ (amount − paid) of its rows."""
    return sum(_n(r.get('amount')) - _n(r.get('paid')) for r in _l(_d(ln).get('rows')) if type(r) is dict)


def _journey(state):
    """The story journey of a save, or None (free play, no journey, not a save)."""
    if type(state) is not dict:
        return None
    j = state.get('journey')
    if type(j) is not dict or j.get('story') is False:
        return None
    return j


def _sheet(state, j) -> tuple[int, int]:
    """(assets, debt) as "Tiền của bạn" counts them."""
    wallet = _n(j.get('wallet'))
    assets, debt = max(0, wallet), max(0, -wallet)
    cs = _d(state.get('careers'))
    funds = [_n(c.get('money')) for c in cs.values() if type(c) is dict and c.get('started')]
    if not funds and cs:   # wealth.js: nothing started yet (a new player), the workplace on screen: app.js career()
        from .journey import default_career   # = the public view's `focus`; only for saves with nothing started
        c = cs.get(state.get('current') or default_career(state))
        if type(c) is dict and type(c.get('money')) in (int, float):
            funds = [_n(c['money'])]
    for fund in funds:
        if fund > 0:
            assets += fund
        else:
            debt -= fund
    b = j.get('bank')
    if type(b) is dict:
        assets += _n(b.get('balance')) + _n(b.get('demand'))
        assets += sum(_n(t.get('amount')) for t in _l(b.get('terms')) if type(t) is dict)
        debt += sum(left for ln in _l(b.get('loans')) if (left := _rows_left(ln)) > 0)
        debt += _n(_d(b.get('card')).get('bal'))
    h = j.get('home')
    if type(h) is dict:
        owned = [x for x in [h.get('own')] + _l(h.get('props')) if type(x) is dict]
        if owned:
            from .housing import value_of
            day = _n(j.get('life_day'))
            basis = _d(j.get('property_market_basis'))
            for x in owned:
                assets += value_of(x, day, basis.get(x.get('id'), 10000))
                debt += _rows_left(x.get('loan'))
    return assets, debt


def _extras(j) -> tuple[int, int]:
    """(assets, debt) the sheet does not list: Mây savings, Mây Coin and gold at cost, vehicles, Quầy riêng,
    Vay nóng hội chợ."""
    assets = debt = 0
    iv = j.get('invest')
    if type(iv) is dict:
        assets += max(0, _n(_d(iv.get('saving')).get('balance')))
        coin = _d(iv.get('coin'))
        if _n(coin.get('units')) > 0:
            assets += max(0, _n(coin.get('basis')))
    gold = _d(j.get('vang'))
    if _n(gold.get('phan')) > 0:
        assets += max(0, _n(gold.get('cost')))
    cars = _d(_d(j.get('garage')).get('cars'))
    if cars:
        from .garage import sell_price
        assets += sum(sell_price(max(0, _n(c.get('p')))) for c in cars.values() if type(c) is dict)
    stalls = _l(_d(j.get('quay')).get('stalls'))
    if stalls:
        from .quay import ITEMS, PLACES, SELL_PCT, UPGRADE_BACK
        for st in stalls:
            if type(st) is not dict or st.get('place') not in PLACES:
                continue
            place = st['place']
            ups = sum(ITEMS[i]['price'][place] for i in _l(st.get('items')) if i in ITEMS)
            assets += (PLACES[place]['price'] * SELL_PCT // 100 + ups * UPGRADE_BACK // 100
                       + max(0, _n(st.get('till'))) + max(0, _n(st.get('fund'))))
            debt += max(0, _n(st.get('due'))) + max(0, _n(_d(st.get('business')).get('unpaid_fines')))
    fc = j.get('fair_cash')
    if type(fc) is dict:
        debt += max(0, _n(_d(fc.get('loan')).get('due'))) + max(0, _n(fc.get('debt')))
    return assets, debt


def sheet(state) -> tuple[int, int, int] | None:
    """(net, assets, debt) in xu exactly as "Tiền của bạn" shows them (without the Quỹ chung), or None outside the
    story (or a save without a journey)."""
    try:
        j = _journey(state)
        if j is None:
            return None
        assets, debt = _sheet(state, j)
        return assets - debt, assets, debt
    except Exception:  # noqa: BLE001 - summary() runs on every save write: a bad save only loses this row
        return None


def worth(state) -> tuple[int, int, int] | None:
    """(net, assets, debt) in xu for the board: the sheet plus `extras()`, or None outside the story."""
    try:
        j = _journey(state)
        if j is None:
            return None
        a1, d1 = _sheet(state, j)
        a2, d2 = _extras(j)
        assets, debt = a1 + a2, d1 + d2
        return assets - debt, assets, debt
    except Exception:  # noqa: BLE001 - summary() runs on every save write: a bad save only loses this row
        return None


def extras(state) -> tuple[int, int] | None:
    """(assets, debt) the board adds to the sheet, or None outside the story."""
    try:
        j = _journey(state)
        return None if j is None else _extras(j)
    except Exception:  # noqa: BLE001
        return None


def score(state) -> tuple[int, int] | None:
    """(net, assets) for the board, clamped to the INTEGER columns; None when there is no row (outside the story,
    or a net worth of 0 or less)."""
    w = worth(state)
    if w is None or w[0] <= 0:
        return None
    return min(w[0], INT_MAX), min(w[1], INT_MAX)
