"""Authoritative, inventory-bounded wall-clock business ledger.

One business period is ten real minutes. Expenses carry fractional xu between
settlements; arrivals have absolute timestamps, so polling cannot change income.
Initialization purchases a modest starter shelf from existing business cash only.
Old life-day sales are disabled as soon as this optional runtime exists.
Traffic fines are bounded immediate local payments. Excess legacy liabilities
are waived once, without charging future receipts or the owner's wallet.
"""
from __future__ import annotations

import contextlib
import contextvars
import math
import time
from . import quay as qy
from . import quay_self as qs
from . import quay_market as market
from . import quay_auto
from . import wealth_pricing
from . import income_gear
from .income_boost import take_percent as take   # 📈 Thu nhập +50% (owner 22/10): the owner's take × 1.5
from . import business_progression as bp
from .loss_limits import bounded_loss

PERIOD = 600
QUIET_MS = 10 * 60 * 1000   # 2.4.20: time costs stop this long after the last sale, until the next one (_busy)
DEN = PERIOD * 1000
STOCK_MAX = 20000
PRICE_MAX = 1000000
LEGACY_EXPENSES = ('goods', 'wages', 'rent', 'power', 'online', 'tax', 'loss')
EXPENSES = LEGACY_EXPENSES + ('income_tax', 'environment', 'protection')
TIME_COSTS = ('wages', 'rent', 'power', 'environment', 'protection')   # billed by elapsed open time (_rates)
# Margin bonus, percent of the realized margin after costs and income tax (2.4.17: ×1.6, see below).
# Owner self-serve and player-visitor orders keep 40%. Staff-run sales (settle())
# get 110%: the owner's take, margin x (1 + bonus), goes from 1.4x to 2.1x, i.e. x1.5.
# Owner 15/10 "cho mọi người tăng 60% lãi": the owner's take ×1.6, (100 + percent) × 1.6 − 100: 40 → 124, 110 → 236.
# No save checks the percent (profit_boost holds only carry/total/costs), so older builds read what these write.
BONUS_PERCENT = 124
STAFF_BONUS_PERCENT = 236
# 📈 Owner 22/10 ("tăng 50% thu nhập … tăng cả tiền quầy"): every sale's percent goes through take(), the owner's take
# × game/income_boost.INCOME_PCT / 100 (124 → 236, 236 → 404 while on); the estimate and the page's percents too.
# 🏬 Chuỗi quầy (owner 18/10: "làm sao cho người giàu tốn tiền nhiều hơn… tăng càng nhiều thì phí nhiều đi", the gentle
# ladder): an owner of more than N counters pays +P points of income tax on every counter's margin (the profit bonus is
# counted after tax, so it shrinks with it), and above RENT_FREE counters each counter's rent grows × n / RENT_FREE.
# ⚡ Owner 19/10 ("điện nước theo chuỗi thì tăng", mức vừa): above POWER_FREE counters each counter's power × n / POWER_FREE.
# The owner's counter count comes from the save being settled (chain_scope); a stall read on its own counts as 1.
# 🌸 Owner 21/10 (a 64-kiosk florist chain fell to ~half from 20/10; "quầy hoa"): the chain's part of every charge, the
# rent and power above the base and the tax points above INCOME_TAX_PERCENT, is paid at face value but never shrinks
# the profit bonus (reward_margin counts the base costs only: _charge, income_tax_parts; their fractions of a xu carry
# in the optional business['chain_carry'] {rent, power, tax}, which older builds ignore), and the rent and power growth
# stop at RENT_MAX / POWER_MAX counters (×1.5 rent, ×2 power): a normal-speed chain of any trade and place keeps ≥ ~70 %
# of its pre-20/10 take per counter (the slowest, a clothing ki-ốt, ~75 %).
CHAIN_TAX = ((50, 20), (30, 15), (20, 10), (10, 5), (5, 2))
RENT_FREE = 10
RENT_MAX = 15          # rent × min(n, RENT_MAX) / RENT_FREE: ×1.5 at most
POWER_FREE = 5
POWER_MAX = 10         # power × min(n, POWER_MAX) / POWER_FREE: ×2 at most
_CHAIN = contextvars.ContextVar('quay_chain', default=1)


def chain_tax(n):
    """Extra income-tax points for an owner of `n` counters."""
    return next((p for k, p in CHAIN_TAX if n > k), 0)


def chain_of(s):
    return len((qy.get(s) or {}).get('stalls', []))


@contextlib.contextmanager
def chain_scope(s):
    from .wealth_fee import START_TS   # from 20/10 (owner 19/10: announced first, then charged)
    token = _CHAIN.set(max(1, chain_of(s)) if time.time() >= START_TS else 1)
    try:
        yield
    finally:
        _CHAIN.reset(token)


def tax_percent():
    return market.INCOME_TAX_PERCENT + chain_tax(_CHAIN.get())


def rent_x(n):
    """Rent multiplier of an n-counter chain, in RENT_FREE-ths."""
    return min(RENT_MAX, max(RENT_FREE, n))


def power_x(n):
    """Power multiplier of an n-counter chain, in POWER_FREE-ths."""
    return min(POWER_MAX, max(POWER_FREE, n))


def staff_wage(st, member):
    from .staff_life import wage
    return wage(st, member)


def demand(base, price):
    """Per-item willingness: no positive floor at exploitative prices."""
    return min(1.6, (base / max(1, price)) ** 3)


def unit_cost(st, dish):
    return max(1, math.ceil(qs.cost_of(st['trade'], dish)))


def _stock_value(st):
    """What the shelf cost to buy (each restock is charged at unit_cost × qty): read-only, for the Lãi line."""
    b = st.get('business') or {}
    rows = qs.DISH.get(st['trade'], {})
    return sum(n * unit_cost(st, d) for d, n in (b.get('stock') or {}).items() if d in rows and n > 0)


def _ms(now=None):
    return int((time.time() if now is None else now) * 1000)


def _signature(st):
    board = qs.menu(st)
    return repr((board, [(e['id'], staff_wage(st, e)) for e in st['staff']],
                 bool(st.get('online')), st['items'], qs.look(st), st['rep']))


def _intervals(st):
    board = qs.menu(st)
    p, t = qy.PLACES[st['place']], qy.TRADES[st['trade']]
    capacity = max(1, len(st['staff'])) * p['cap'] * t['mult'] / 100
    reach = (1.12 if st.get('online') else 1) * (1 + qs.look(st)['t'] * .02)
    reach *= 1 + (.08 if 'bang' in st['items'] else 0) + (.04 if 'tu' in st['items'] else 0)
    normal = min(capacity / 1.6, p['base'] * t['mult'] / 100 * reach)
    normal *= st.get('business', {}).get('speed_factor', 1)
    normal *= 1 + income_gear.cached(st,'demand') / 100
    normal *= (200 + income_gear.online_rate(st)) / 300
    from .shop_events import demand_factor
    normal *= demand_factor(st, quay=True)
    return {d: max(1000, math.ceil(DEN * len(board['on']) /
             (normal * demand(qs.DISH[st['trade']][d]['base'], board['p'][d])))) for d in board['on']}


def initialize(s, st, now=None):
    if isinstance(st.get('business'), dict):
        b = st['business']
        changed = 'profit_boost' not in b
        _profit_state(st)
        return market.migrate(st) or changed
    at = _ms(now)
    from .work_gear import factor
    b = st['business'] = dict(v=1, cursor=at, paused=False, stock={}, arrivals={},
        signature='', carry={k: 0 for k in ('wages', 'rent', 'power', 'online', 'tax')},
        expenses={k: 0 for k in EXPENSES}, revenue=0, sold=0, recent=[], halted=-1,
        seq=0, manual_seq=0, owner_next=at, unpaid_fines=0,
        speed_factor=factor(s.get('careers', {}).get(st['trade'], {})),
        income_gear=income_gear.effects(s.get('careers', {}).get(st['trade'], {})))
    _profit_state(st)
    market.migrate(st)
    if wealth_pricing.ENABLED:
        b['protection_quote'] = wealth_pricing.protection_quote(s)
    # Purchase a small shelf without consuming the opening cash needed for a
    # human shift escrow. Established shops also retain one NPC wage period.
    reserve = max(math.ceil(qy.start_fund(st['place']) * .8),
                  max(sum(e['wage'] for e in st['staff']), qy.PLACES[st['place']]['wage']) + qy.PLACES[st['place']]['power'])
    budget = max(0, st['fund'] + st['till'] - reserve)
    board = qs.menu(st)['on']
    for _ in range(max(2, qy.PLACES[st['place']]['base'] // len(board))):
        for d in board:
            cost = unit_cost(st, d)
            if budget >= cost:
                b['stock'][d] = b['stock'].get(d, 0) + 1
                qy._from_till_fund(st, cost)
                b['expenses']['goods'] += cost
                budget -= cost
    if b['expenses']['goods']:
        qy._log(st, s['journey']['life_day'], 'Nhập lô hàng đầu từ vốn quầy', -b['expenses']['goods'])
    _schedule(st, at)
    from .shop_events import tick_quay
    tick_quay(s, st)
    return True


def reconcile(s):
    """After a gear purchase, snapshot new throughput without moving arrivals.

    The caller must settle the old configuration before the purchase. Already
    pending customers retain their due time; subsequent arrivals use this speed.
    No money, inventory, timestamps or accrued fractional expenses move here.
    """
    from .work_gear import factor
    changed = False
    for st in (qy.get(s) or {}).get('stalls', []):
        b = st.get('business')
        speed = factor(s.get('careers', {}).get(st['trade'], {}))
        if b is not None and b.get('speed_factor', 1) != speed:
            b['speed_factor'] = speed
            changed = True
        growth=income_gear.effects(s.get('careers', {}).get(st['trade'], {}))
        if b is not None and b.get('income_gear',dict.fromkeys(income_gear.RATES,0)) != growth:
            b['income_gear']=growth
            changed=True
    return changed


def _fresh(at, intervals):
    """First arrivals of a (re)scheduled board, staggered: the k-th of n dishes comes after k/n of its interval, so a
    full board sells one dish at a time instead of all of them at once (F#232, 12 dishes). The last dish keeps the
    whole interval and each dish then repeats on its own interval: the same number of sales as before, spread out."""
    k = len(intervals)
    return {d: market.advance(at, max(1, n * (i + 1) // k)) for i, (d, n) in enumerate(intervals.items())}


def _schedule(st, at):
    b = st['business']
    sig = _signature(st)
    if b['signature'] != sig:
        b['signature'] = sig
        b['arrivals'] = _fresh(at, _intervals(st))


# "Giữ lại cho ca của tôi" at a counter: an optional floor per dish, business['keep'] = {dish: 1..KEEP_MAX}. Staff
# walk-in sales stop at it; the owner's own shift and deliveries still sell every portion. Absent = no floor (as before);
# 1.9.17 and older accept the extra key (validate checks only the keys it knows) and leave it alone.
KEEP_MAX = 999


def keep(st, dish):
    k = st.get('business', {}).get('keep')
    return k.get(dish, 0) if k else 0


def _for_staff(st, dish):
    """Portions the staff may sell: the stock above the owner's floor."""
    return st['business']['stock'].get(dish, 0) - keep(st, dish)


def kept(st):
    """[[dish, portions held back]] for each floor that stops the staff now (some stock left, none above it)."""
    b = st.get('business', {})
    return [[d, b['stock'].get(d, 0)] for d, n in sorted((b.get('keep') or {}).items()) if 0 < b['stock'].get(d, 0) <= n]


def status(st):
    b = st.get('business', {})
    if b.get('certificate_block'):
        return 'restricted'
    if b.get('paused') or st.get('due', 0) or st.get('economy', {}).get('paused'):
        return 'paused'
    if not st['staff']:
        return 'no_staff'
    if not any(b.get('stock', {}).get(d, 0) - keep(st, d) > 0 for d in qs.menu(st)['on']):
        return 'out_of_stock'
    cash = st['fund'] + st['till']
    if cash < 1 or b.get('halted', -1) == cash:
        return 'no_funds'
    return 'running'


def _rates(st, chain=None):
    """Time costs per PERIOD. `chain`: the counter count to price rent and power for (default: the chain in scope;
    1 gives the base rates the profit bonus counts, see _charge)."""
    p = qy.PLACES[st['place']]
    n = _CHAIN.get() if chain is None else chain
    return dict(wages=sum(staff_wage(st, e) for e in st['staff']), rent=p['rent'] // qy.MONTH_DAYS * rent_x(n) // RENT_FREE, power=p['power'] * power_x(n) // POWER_FREE,
                environment={'xe': 1, 'sap': 2, 'kiot': 4}[st['place']],
                protection=_protection_plans(st)[st['business'].get('protection', {}).get('level', 'none')]['period_cost'])


def _protection_plans(st):
    wealth = st['business'].get('protection_quote', {}).get('wealth', 0)
    return {k: dict(v, period_cost=wealth_pricing.cost(v['period_cost'], wealth)) for k, v in market.PLANS.items()}


def collect_fines(st):
    """Forgive old uncollected fines once; never seize future operating cash."""
    b = st.get('business')
    if not b or not b.get('unpaid_fines', 0):
        return 0
    waived = b['unpaid_fines']
    profit = _profit_state(st)
    profit['costs'] = max(0, profit['costs']-waived)
    if 'income_tax' in b:
        b['income_tax']['loss'] = max(0, b['income_tax']['loss']-waived)
    b['waived_fines'] = min(10**16, b.get('waived_fines', 0)+waived)
    b['unpaid_fines'] = 0
    return 0


def assess_fine(st, amount):
    collect_fines(st)
    b = st['business']
    amount = bounded_loss(st['till']+st['fund'], amount, fine=True)
    paid = qy._from_till_fund(st, amount)
    _profit_state(st)['costs'] += amount
    st['business']['income_tax']['loss'] += amount
    b['expenses']['loss'] += paid
    return paid


def _busy(st, start, dt):
    """2.4.20 (owner 15/10, chi phí cố định khi quầy vắng khách): of [start, start + dt) ms, the part within QUIET_MS of
    the last sale. Time costs accrue only there: QUIET_MS after a sale with no next one the counter stops paying
    rent, power, wages… until it sells again. Measured from the last sale's own time, so polling or a catch-up books
    the same. A counter that never sold pays as before."""
    recent = st['business'].get('recent') or []
    if start is None or not recent:
        return dt
    last = int(round(recent[-1]['at'] * 1000))
    return max(0, min(start + dt, last + QUIET_MS) - start)


def _charge(st, elapsed, *, direct=False, start=None):
    blocked = st.get('business', {}).get('certificate_block')
    if blocked and not direct:
        return True
    b, rates, base = st['business'], _rates(st), _rates(st, chain=1)
    if blocked:
        rates = {'wages': rates['wages']}
    # Keep the last coin reserved. A zero balance otherwise stops small polls
    # earlier than a catch-up that reaches the next fractional expense boundary.
    cash = max(0, st['till'] + st['fund'] - 1)
    def cost(dt):
        dt = _busy(st, start, dt)
        return sum((b['carry'][k] + dt * rate) // DEN for k, rate in rates.items())
    dt = elapsed
    if cost(dt) > cash:
        lo, hi = 0, dt
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if cost(mid) <= cash:
                lo = mid
            else:
                hi = mid - 1
        dt = lo
    paid = _busy(st, start, dt)
    for k, rate in rates.items():
        charge, b['carry'][k] = divmod(b['carry'][k] + paid * rate, DEN)
        qy._from_till_fund(st, charge)
        b['expenses'][k] += charge
        counted = charge
        if rate != base[k]:   # 🌸 the chain's extra rent / power is paid in full; the profit bonus counts the base rate
            cc = b.setdefault('chain_carry', {})
            counted, cc[k] = divmod(cc.get(k, 0) + paid * base[k], DEN)
        _profit_state(st)['costs'] += counted
        b['income_tax']['loss'] += counted   # the tax, like the bonus, sees the base costs (as before 20/10)
    if dt < elapsed:
        b['halted'] = st['till'] + st['fund']
    return dt == elapsed


def _profit_state(st):
    return st['business'].setdefault('profit_boost', dict(carry=0, total=0,
        costs=st['business'].get('unpaid_fines', 0)))


def reward_margin(st, revenue, costs, percent=BONUS_PERCENT, owner=None):
    """Credit `percent` of realized margin after uncovered operating costs/losses.

    Inventory is expensed here only when consumed. Funding and unsold stock
    never earn a bonus; fractional xu survive small orders and polling.
    `owner`: the stall owner's save; its 🧩 Phúc lợi (game/tile_match.py) adds its ‰ of the margin and this bonus to
    the till as well (not to the profit bonus's total: older builds keep validating that).
    """
    p = _profit_state(st)
    margin = revenue - costs - p['costs']
    p['costs'] = max(0, -margin)
    if margin <= 0:
        return 0
    bonus, p['carry'] = divmod(margin * percent + p['carry'], 100)
    bonus = min(bonus, qy.MONEY_MAX - st['till'])
    st['till'] += bonus
    p['total'] += bonus
    if owner is not None:
        from .tile_match import extra
        tile = min(extra(owner, margin + bonus, f"quay|{st['id']}|{st['business']['seq']}"), qy.MONEY_MAX - st['till'])
        st['till'] += tile
        bonus += tile
    return bonus


def charge_income_tax(st, revenue, costs):
    """One margin ledger for counter, online, and actual visitor receipts."""
    return sum(income_tax_parts(st, revenue, costs))


def income_tax_parts(st, revenue, costs):
    """Charge the income tax on one receipt: (base, chain). The base INCOME_TAX_PERCENT keeps income_tax.carry exactly as
    before 20/10 and is what the profit bonus counts; the chain's extra points (chain_tax) carry their own fraction in
    chain_carry['tax'] and are paid at face value only (🌸 owner 21/10). Two carries, so that small receipts round
    neither part away."""
    b = st['business']
    tax = b['income_tax']
    margin = revenue - costs - tax['loss']
    tax['loss'] = max(0, -margin)
    taxed = max(0, margin)
    charge, tax['carry'] = divmod(tax['carry'] + taxed * market.INCOME_TAX_PERCENT, 100)
    base = qy._from_till_fund(st, charge)
    chain, extra = 0, chain_tax(_CHAIN.get())
    if extra:
        cc = b.setdefault('chain_carry', {})
        charge, cc['tax'] = divmod(cc.get('tax', 0) + taxed * extra, 100)
        chain = qy._from_till_fund(st, charge)
    b['expenses']['income_tax'] += base + chain
    return base, chain


def sale(st, items, at, *, channel='counter', stars=None, total=None, extra_fee=0, extra_loss=0, employee=None, owner=None):
    """Book only a real fulfilled order; stock was purchased before this point. `owner`: the stall owner's save
    (🧩 Phúc lợi on the margin, reward_margin)."""
    b = st['business']
    amount = sum(qs.price(st, d) for d in items) if total is None else total
    for d in items:
        b['stock'][d] -= 1
    b['revenue'] += amount
    b['sold'] += len(items)
    st['till'] = min(qy.MONEY_MAX, st['till'] + amount)
    collect_fines(st)
    costs = sum(unit_cost(st, d) for d in items)
    for key, rate in (('online', qs.ONLINE_FEE if channel == 'online' else 0),):
        charge, b['carry'][key] = divmod(b['carry'][key] + amount * rate, 100)
        paid = qy._from_till_fund(st, charge)
        b['expenses'][key] += paid
        costs += paid
    if extra_fee:
        paid = qy._from_till_fund(st, extra_fee)
        b['expenses']['online'] += paid
        costs += paid
    if extra_loss:
        paid = qy._from_till_fund(st, extra_loss)
        b['expenses']['loss'] += paid
        costs += paid
    costs += income_tax_parts(st, amount, costs)[0]   # 🌸 the chain's tax points are paid, not taken off the bonus
    from . import golden_hour   # ⏰ Giờ vàng / Ngày vàng (owner 15/10): the owner's take ×2 / ×1.5 at the sale's own time
    from . import bang   # ⚔️ ⏰ Giờ vàng của bang (game/bang.py): ×2 at the sale's own time, the larger of it and the street's
    percent = golden_hour.scale_take(income_gear.profit_percent(st,BONUS_PERCENT if employee is None else STAFF_BONUS_PERCENT), at / 1000,
                                     bang.gold_mult(at / 1000) if owner is not None else 100)
    if owner is not None:   # 📺 ⏰ Giờ vàng riêng (game/ads.py): the owner's take ×1,5 more at the sale's own time
        from . import ads
        percent = ads.scale_take(owner, percent, at / 1000)
    percent = take(percent)   # 📈 Thu nhập +50% (owner 22/10 "tăng cả tiền quầy"): the owner's take × 1.5, as 15/10's ×1.6
    bonus = reward_margin(st, amount, costs, percent, owner)
    ratio = sum(qs.price(st, d) / qs.DISH[st['trade']][d]['base'] for d in items) / len(items)
    price_stars = 5 if ratio <= .9 else 4 if ratio < 1.15 else 3 if ratio < 1.5 else 2 if ratio < 2 else 1
    review = None
    if employee is not None:
        from .staff_life import quality
        review = quality(employee, b['seq'] + 1, st['id'], quay=True)
        stars = min(stars or 5, review['stars'])
        employee['d'] = min(10**6, employee.get('d', 0) + 1)
    stars = min(stars or price_stars, price_stars)
    qs._rate(st, stars)
    b['seq'] += 1
    b['recent'].append(dict(id=b['seq'], at=at / 1000, dish=items[0], qty=len(items), total=amount, channel=channel, stars=stars))
    if review:
        from .staff_life import REVIEWS
        b['recent'][-1].update(employee=review['employee'], name=review['name'], text=REVIEWS[stars])
    b['recent'] = b['recent'][-12:]
    return bonus


def due(s, now=None):
    from .player_service_tasks import visit_due
    at = _ms(now)
    auto = quay_auto.on(s)
    return bp.due(s, now=now) or any(not isinstance(st.get('business'), dict) or
               (wealth_pricing.ENABLED and st['business'].get('protection_quote', {}).get('day') != s['journey']['life_day']) or
               'profit_boost' not in st['business'] or 'market_epoch' not in st['business'] or
               visit_due(st,at) or
               st['business'].get('unpaid_fines', 0) > 0 or
               (auto and quay_auto.due(st, at)) or
               (at > st['business']['cursor'] and (status(st) == 'running' or
                (not st['business']['paused'] and isinstance(st.get('run'), dict) and st['run'].get('continuous') and not st['run'].get('x'))))
               for st in (qy.get(s) or {}).get('stalls', []))


CATCHUP_STEP_MS = 10 * 60 * 1000   # 22/10 lag: a long catch-up is booked in steps from the oldest cursor (doubling while cheap)
CATCHUP_BUDGET = 1.5               # seconds one request may spend on it; the rest waits for the next request (due() stays true)


def settle(s, now=None, *, _policy=True, _exclusive=False):
    with chain_scope(s):
        at = _ms(now)
        start = min((st['business']['cursor'] for st in (qy.get(s) or {}).get('stalls', [])
                     if isinstance(st.get('business'), dict) and isinstance(st['business'].get('cursor'), int)), default=at)
        if not _policy or _exclusive or not CATCHUP_BUDGET or at - start <= CATCHUP_STEP_MS:
            return _settle(s, now, _policy=_policy, _exclusive=_exclusive)
        # 22/10 (owner: lag, "mất kết nối"): a big chain coming back after an hour books ~67 000 staff sales one by
        # one (16–28 s), holding a worker and every request queued on it. Book it as polling would have: up to
        # successive past times, each a complete settle, stopping after CATCHUP_BUDGET; polling equals offline
        # (test_polling_equals_offline_and_idempotent), so the rest booked by the next requests sums to the same.
        t0, changed, t, step = time.monotonic(), False, start, CATCHUP_STEP_MS
        while t < at:
            t = min(at, t + step)
            t1 = time.monotonic()
            changed = _settle(s, None, _at=t) or changed
            if t < at and time.monotonic() - t0 > CATCHUP_BUDGET:
                break
            if time.monotonic() - t1 < .05:
                step *= 2
        return changed


def _settle(s, now=None, *, _policy=True, _exclusive=False, _at=None):
    from .player_service_tasks import settle_visits
    from .shop_events import tick_quay
    from .staff_life import tick_quay as tick_staff
    at, changed = (_ms(now) if _at is None else _at), False
    if _policy:
        policy = bp.evaluate(s, at / 1000)
        deadline = int(policy['deadline'] * 1000) if policy['deadline'] is not None else None
        if policy['blocked_ids'] and deadline is not None:
            # Book the whole old interval first, excluding arrivals at the cutoff.
            if any(st.get('business', {}).get('cursor', at) < deadline for st in (qy.get(s) or {}).get('stalls', [])):
                changed = settle(s, now=deadline / 1000, _policy=False, _exclusive=True) or changed
            changed = bp.reconcile(s, now=at / 1000) or changed
    # Capture once before settling any counter; publish only after old elapsed
    # service has been billed. All counters share this day's valuation.
    renew = [st for st in (qy.get(s) or {}).get('stalls', [])
             if wealth_pricing.ENABLED and st.get('business', {}).get('protection_quote', {}).get('day') != s['journey']['life_day']]
    quote = wealth_pricing.protection_quote(s) if renew else None
    for st in (qy.get(s) or {}).get('stalls', []):
        fresh = initialize(s, st, now=at / 1000)
        fresh = tick_quay(s, st) or fresh
        fresh = tick_staff(s, st) or fresh
        b = st['business']
        if b.get('unpaid_fines', 0):
            collect_fines(st)
            changed = True
        if at <= b['cursor']:
            changed |= fresh
            continue
        visit_cursor,visit_blocked,visit_changed=settle_visits(st,at)
        changed |= visit_changed
        if visit_blocked:
            qs.settle_queue(s, st, at)
            b['cursor']=at
            continue
        changed = True
        _schedule(st, b['cursor'])
        cursor = visit_cursor
        run = st.get('run')
        manual = isinstance(run, dict) and run.get('continuous') and not run.get('x') and not b['paused'] and not b.get('certificate_block')
        intervals = _intervals(st)
        if not st['staff'] and manual:
            _charge(st, at - cursor, start=cursor)
        # 🤖 Tự nhập hàng (game/quay_auto.py): after each staff sale that leaves the shelf under the threshold, at its
        # own time; an empty shelf at the cursor and again at each Vietnam midnight before `at` (a new day's limit), so
        # a catch-up after days offline buys what live polling would have bought.
        auto = quay_auto.on(s)
        if auto and status(st) == 'out_of_stock':
            quay_auto.attempt(s, st, cursor)
        while True:
            while status(st) == 'running':
                arrivals = [(max(cursor, when), d) for d, when in b['arrivals'].items() if _for_staff(st, d) > 0]
                when, dish = min(arrivals)
                end = min(when, at)
                if not _charge(st, end - cursor, start=cursor):
                    break
                cursor = end
                if when > at or (_exclusive and when == at) or status(st) == 'no_funds':
                    break
                qs.settle_queue(s, st, when)
                channel = income_gear.channel(st,b['seq'])
                employee = st['staff'][b['seq'] % len(st['staff'])]
                sale(st, [dish], when, channel=channel, employee=employee, owner=s)
                tick_staff(s, st)
                b['arrivals'][dish] = market.advance(when, intervals[dish])
                if auto:
                    quay_auto.attempt(s, st, when)
            midnight = quay_auto.next_midnight(cursor) if auto and status(st) == 'out_of_stock' else at
            if midnight >= at:
                break
            cursor = midnight   # an empty counter accrues no time costs: nothing to bill up to here
            b['arrivals'] = _fresh(cursor, intervals)
            quay_auto.attempt(s, st, cursor)
        market.enter_epoch(st, at)
        if status(st) != 'running':
            # Time while closed never becomes deferred sales after restocking.
            b['arrivals'] = _fresh(at, intervals)
        qs.settle_queue(s, st, at - (1 if _exclusive else 0))
        b['cursor'] = at
        tick_quay(s, st)
    for st in renew:
        st['business']['protection_quote'] = dict(quote)
        changed = True
    if _policy:
        changed = bp.reconcile(s, now=at / 1000) or changed
    return changed


def action(s, st, name, p):
    need = qy._core().need
    b = st['business']
    if name == 'jr_quay_sync':
        need(set(p) <= {'stall'}, 'Thao tác không hợp lệ.')
        return dict(message='Đã cập nhật hoạt động quầy.')
    if name == 'jr_quay_pause':
        need(set(p) <= {'stall', 'on'} and type(p.get('on')) is bool, 'Thao tác không hợp lệ.')
        if b['paused'] != p['on']:
            b['paused'] = p['on']
            if p['on']:
                b['closed_at'] = b['cursor']
            else:
                market.enter_epoch(st, b['cursor'])
                b['arrivals'] = _fresh(b['cursor'], _intervals(st))
                qs.reopen_queue(st)
        return dict(message='Đã đóng quầy, xử lý nốt đơn đã nhận.' if p['on'] else 'Đã mở quầy, bắt đầu nhận khách mới.')
    if name == 'jr_quay_keep':
        need(set(p) <= {'stall', 'dish', 'qty'} and p.get('dish') in qs.DISH[st['trade']], 'Chọn một món của quầy.')
        need(type(p.get('qty')) is int and 0 <= p['qty'] <= KEEP_MAX, f'Số giữ lại từ 0 đến {KEEP_MAX}.')
        k = b.setdefault('keep', {})
        if p['qty']:
            k[p['dish']] = p['qty']
        else:
            k.pop(p['dish'], None)
        if not k:
            b.pop('keep')
        return dict(message=f'🔒 Giữ {p["qty"]} cho ca của bạn.' if p['qty'] else 'Đã bỏ giữ: nhân viên bán tiếp.')
    if name == 'jr_quay_protection':
        need(set(p) <= {'stall', 'level'} and isinstance(p.get('level'), str) and p['level'] in market.PLANS, 'Gói bảo vệ không hợp lệ.')
        b['protection']['level'] = p['level']
        return dict(message='Đã chọn ' + market.PLANS[p['level']]['label'].lower() + '.')
    need(set(p) <= {'stall', 'items', 'wallet', 'credit'} and type(p.get('wallet', False)) is bool
         and p.get('credit') in (None, 'card', 'loan'), 'Thông tin nhập hàng không hợp lệ.')
    items = p.get('items')
    rows = qs.DISH[st['trade']]
    need(isinstance(items, dict) and items and all(d in rows and type(n) is int and 1 <= n <= STOCK_MAX for d, n in items.items()), 'Chọn số lượng hàng cần nhập.')
    from .player_service_tasks import reserved
    from .quay_progression import limit
    capacity, batch = limit(b, 'storage'), limit(b, 'restock')
    need(sum(items.values()) <= batch, f'Mỗi lần nhập tối đa {batch} phần, tính chung tất cả món.')
    need(sum(b['stock'].values()) + reserved(st) + sum(items.values()) <= capacity, f'Kho chứa tối đa {capacity} phần, gồm hàng giữ cho khách.')
    cost = goods_cost(st, items)
    # F#295 (2) "tự trừ từ tài khoản của mình mà không cần nhập tiền qua góp vốn": `wallet: true` pays what the till and
    # the fund lack from the wallet, then the bank account (as 💼 Góp vốn does, quay._take), in this same command.
    # Never into debt; without the flag a short counter is refused exactly as before.
    j = s['journey']
    short = max(0, cost - st['till'] - st['fund'])
    paid = f' Lấy {short} xu từ ví.' if short else ''
    if short and p.get('credit'):
        # 📦 owner 22/10 (F#481 "nhập hàng khi ví không đủ tiền"): `credit` 'card' | 'loan' pays the whole shortfall by a card
        # swipe or a vay nhập hàng (game/bank_plus.py cover), the wallet untouched; the bank says no -> nothing happens.
        from .bank_plus import cover
        paid = ' ' + cover(s, short, p['credit'], f'Nhập hàng {st["name"]}', dict(k='quay', id=st['id']))
        st['fund'] += short   # fund + short = cost - till <= cost: within MONEY_MAX
    elif short:
        need(p.get('wallet') is True, f'Cần {cost} xu trong két hoặc vốn quầy.', 'no_money')
        need(j['wallet'] >= 0, 'Ví đang nợ. Trả nợ trước rồi nhập hàng nhé.', 'in_debt')
        need(qy._have(s) >= short, f'Thiếu {short} xu: ví và tài khoản chưa đủ.', 'no_money')
        qy._take(s, short, f'Nhập hàng {st["name"]}', st['trade'])
        st['fund'] += short   # fund + short = cost - till <= cost: within MONEY_MAX
    shelve(st, items, cost)
    # 🔁 Nhập lại như lần trước (F#295 (1)): the last order, an optional key (1.9.35 and older accept and ignore it).
    b['again'] = {d: items[d] for d in sorted(items)}
    qy._log(st, s['journey']['life_day'], 'Nhập hàng vào kho', -cost)
    # F#232: staff sell only the board. Restocking a dish that is off it turns it on (not during an old-style run,
    # whose walk-ins come from the board as it was at the start; the 📦 tab then shows "Chưa bật ở Menu").
    added = [] if qs.board_locked(st, int(s['journey']['life_day'])) else qs.turn_on(st, items)
    tail = f' Đã bật ở Menu: {", ".join(rows[d]["name"] for d in added)}.' if added else ''
    return dict(message=f'Đã nhập {sum(items.values())} món, hết {cost} xu.{paid}{tail}')


def goods_cost(st, items):
    """What a restock of {dish: portions} costs (unit_cost × qty): jr_quay_restock and 🤖 Tự nhập hàng (game/quay_auto.py)."""
    return sum(unit_cost(st, d) * n for d, n in items.items())


def shelve(st, items, cost):
    """Pay a restock from the till, then the fund (the caller checked they hold `cost`), put it on the shelf and book
    it once as a goods expense (the Lãi line adds the shelf back at cost, public())."""
    b = st['business']
    qy._from_till_fund(st, cost)
    for d, n in items.items():
        b['stock'][d] = b['stock'].get(d, 0) + n
    b['expenses']['goods'] += cost
    b['halted'] = -1


def income(st, at):
    """Read-only (#19, "how xem được thu nhập 1h"): what the staffed counter makes at its current setup, worked out from
    the same arrival intervals, market calendar, prices, costs, tax and staff bonus settle() uses. `hour` is the hour at
    the market of now; `day` is one full market cycle (24 h) if the stock and the money last. Nothing is written."""
    if not st['staff'] or not isinstance(st.get('business'), dict):
        return None
    iv = _intervals(st)
    if not iv:
        return None
    rates, base = _rates(st), _rates(st, chain=1)
    online = qs.ONLINE_FEE if st.get('online') else 0

    def run(ms, work):   # work: the market's demand over that time, in percent-milliseconds
        sold = {d: work / (100 * n) for d, n in iv.items()}
        revenue = sum(q * qs.price(st, d) for d, q in sold.items())
        costs = sum(q * unit_cost(st, d) for d, q in sold.items()) + sum(rates.values()) * ms / DEN \
            + revenue * income_gear.online_rate(st) / (200 + income_gear.online_rate(st)) * online / 100
        margin = revenue - costs
        chain = (sum(rates.values()) - sum(base.values())) * ms / DEN   # 🌸 paid, but neither taxed off nor taken off the bonus
        taxed = max(0, margin + chain)
        tax = taxed * tax_percent() / 100
        bonus = max(0, taxed - taxed * market.INCOME_TAX_PERCENT / 100) * take(income_gear.profit_percent(st,STAFF_BONUS_PERCENT)) / 100
        return dict(sold=round(sum(sold.values()), 1), revenue=round(revenue), costs=round(costs + tax),
                    bonus=round(bonus), net=round(margin - tax + bonus))
    hour_ms = 3600 * 1000
    now = market.snapshot(at)
    hour = run(hour_ms, now['demand_factor'] * 100 * hour_ms)
    day = run(market._CYCLE_MS, market._CYCLE_WORK)
    stock = sum(max(0, _for_staff(st, d)) for d in iv)
    return dict(hour=hour, day=day, market=now['label'], stock_hours=round(stock / hour['sold'], 1) if hour['sold'] else None)


def price_effect(st):
    """F#263: how the board's prices move the walk-ins, percent of the reference price (the average of demand() over
    the dishes on sale, the factor _intervals uses). 100 at the reference prices, up to 160 cheaper, below when dearer.
    Separate from the market phase, which is the same for every counter in town."""
    board = qs.menu(st)
    on = board['on']
    if not on:
        return 100
    rows = qs.DISH[st['trade']]
    return round(100 * sum(demand(rows[d]['base'], board['p'][d]) for d in on) / len(on))


def public(st):
    from .player_service_tasks import public_visits,visit_due
    b = st.get('business')
    if not b:
        return None
    code = status(st)
    reasons = dict(restricted=bp.REASON, running='Nhân viên đang bán', paused='Quầy tạm dừng', no_staff='Chủ tự phục vụ hoặc thuê nhân viên', out_of_stock='Hết hàng trong menu đang bán', no_funds='Hết vốn trả lương và chi phí')
    rows = qs.DISH[st['trade']]
    held = kept(st)
    if code == 'out_of_stock' and held:
        reasons['out_of_stock'] = '🔒 Giữ ' + ', '.join(f'{n} {rows[d]["name"].lower()}' for d, n in held[:3]) + \
            (f', +{len(held) - 3} món' if len(held) > 3 else '') + ' cho ca của bạn'
    next_at = min((v for d, v in b['arrivals'].items() if _for_staff(st, d) > 0), default=0)
    visitors=public_visits(st)
    plans = _protection_plans(st)
    if not b['paused'] and not b.get('certificate_block') and visit_due(st,b['cursor']+1):
        code='running'
        pending=[r['due_at'] for r in visitors if r['status']=='queued' and r['due_at'] is not None]
        next_at=round(min(pending)*1000) if pending else b['cursor']
    rates = _rates(st)
    run = st.get('run')
    manual = isinstance(run, dict) and run.get('continuous') and not run.get('x') and not b['paused'] and not b.get('certificate_block')
    # Time costs (wages, rent, power, environment, protection) accrue per real second while the
    # counter is open and working, sales or not: the same rule as _charge in settle().
    running = dict(per_period=sum(rates.values()), spent=sum(b['expenses'].get(k, 0) for k in TIME_COSTS),
                   accruing=bool(code == 'running' or (not st['staff'] and manual and code not in ('paused', 'restricted'))))
    from .quay_progression import business_view
    return dict(**business_view(st), v=1, status=code, reason=reasons[code], paused=b['paused'], running_cost=running,
        market=dict(market.snapshot(b['cursor']), town=True, runs=market.outlook(b['cursor']), day_percent=market.DAY_PERCENT,
                    down_minutes=market.DOWN_MINUTES),
        price_effect=price_effect(st), protection=dict(level=b.get('protection', {}).get('level', 'none'), options=[dict(level=k, **v) for k,v in plans.items()], **plans[b.get('protection', {}).get('level', 'none')], quote=dict(b.get('protection_quote', {}))),
        protection_plans=[dict(level=k, **v) for k,v in plans.items()],
        rates=rates, income_tax_percent=tax_percent(), chain=_CHAIN.get(), chain_tax=chain_tax(_CHAIN.get()),
        rent_x=round(rent_x(_CHAIN.get()) / RENT_FREE, 1), power_x=round(power_x(_CHAIN.get()) / POWER_FREE, 1),
        bonus_percent=take(income_gear.profit_percent(st,BONUS_PERCENT)), staff_bonus_percent=take(income_gear.profit_percent(st,STAFF_BONUS_PERCENT)),
        visitor_orders=visitors,
        stock_total=sum(b['stock'].values()), stock=[dict(id=d, qty=b['stock'].get(d, 0), cost=unit_cost(st, d), price=qs.price(st, d), keep=keep(st, d)) for d in rows],
        kept=held, again=[dict(id=d, qty=n) for d, n in (b.get('again') or {}).items() if d in rows],
        auto=quay_auto.stall_public(st),
        period_seconds=PERIOD, wage=sum(staff_wage(st, e) for e in st['staff']), revenue=b['revenue'], sold=b['sold'],
        speed_factor=b.get('speed_factor', 1),
        profit_bonus=b.get('profit_boost', {}).get('total', 0),
        # 2.4.19 (chat 15/10 "kinh doanh mà k có lãi"): a restock is booked as a goods expense when it is bought, so the
        # Lãi line fell by every lot still on the shelf (a counter holding 200 phần showed −57k). The shelf at cost is
        # added back: goods count when sold, spoiled or lost. Money and the bonus are unchanged; stock_value is shown too.
        stock_value=_stock_value(st),
        net=b['revenue'] + b.get('profit_boost', {}).get('total', 0) - sum(b['expenses'].values()) - b.get('unpaid_fines', 0) + _stock_value(st),
        unpaid_fines=b.get('unpaid_fines', 0), expenses=dict(b['expenses']), recent=[dict(x) for x in b['recent']],
        next_at=next_at / 1000 if code == 'running' else None, server_now=b['cursor'] / 1000,
        income=None if code == 'restricted' else income(st, b['cursor']))


def validate(st, need, integer):
    b = st.get('business')
    if b is None:
        return
    need(isinstance(b, dict) and b.get('v') == 1)
    from .quay_progression import validate as validate_paid
    validate_paid(b, ('storage', 'restock'), need, integer)
    need(all(k in b for k in ('cursor', 'paused', 'stock', 'arrivals', 'signature', 'carry', 'expenses', 'revenue', 'sold', 'recent', 'halted', 'seq', 'manual_seq')))
    need(integer(b['cursor'], 0, 10**15) and type(b['paused']) is bool and integer(b.get('owner_next', b['cursor']), 0, 10**18))
    need(type(b.get('speed_factor', 1)) in (int, float) and b.get('speed_factor', 1) in (1, 1.15, 1.35, 1.6))
    growth=b.get('income_gear',dict.fromkeys(income_gear.RATES,0))
    need(isinstance(growth,dict) and set(growth)==set(income_gear.RATES))
    need(all(type(growth[k]) is int and growth[k] in rates for k,rates in income_gear.RATES.items()))
    need(integer(b.get('unpaid_fines', 0), 0, 10**16))
    need(integer(b.get('waived_fines', 0), 0, 10**16))
    if 'profit_boost' in b:
        p = b['profit_boost']
        need(isinstance(p, dict) and set(p) == {'carry', 'total', 'costs'})
        need(integer(p['carry'], 0, 99) and integer(p['total'], 0, 10**16) and integer(p['costs'], 0, 10**16))
    need(isinstance(b['stock'], dict) and set(b['stock']) <= set(qs.DISH[st['trade']]))
    need(all(integer(v, 0, STOCK_MAX) for v in b['stock'].values()) and sum(b['stock'].values()) <= STOCK_MAX)
    from .player_service_tasks import validate_visits
    validate_visits(st)
    need(isinstance(b['arrivals'], dict) and set(b['arrivals']) <= set(qs.DISH[st['trade']]) and all(integer(v, 0, 10**30) for v in b['arrivals'].values()))
    need(isinstance(b['signature'], str) and len(b['signature']) <= 10000)
    need(isinstance(b['expenses'], dict) and set(LEGACY_EXPENSES) <= set(b['expenses']) <= set(EXPENSES) and all(integer(v, 0, 10**16) for v in b['expenses'].values()))
    need(isinstance(b['carry'], dict) and {'wages', 'rent', 'power', 'online', 'tax'} <= set(b['carry']) <= {'wages', 'rent', 'power', 'online', 'tax', 'environment', 'protection'} and all(integer(v, 0, 99 if k in ('online', 'tax') else DEN - 1) for k, v in b['carry'].items()))
    if 'again' in b:
        need(isinstance(b['again'], dict) and len(b['again']) > 0 and set(b['again']) <= set(qs.DISH[st['trade']])
             and all(integer(v, 1, STOCK_MAX) for v in b['again'].values()))
    quay_auto.validate(b, need, integer, qy.MONEY_MAX)
    if 'keep' in b:
        need(isinstance(b['keep'], dict) and set(b['keep']) <= set(qs.DISH[st['trade']]) and all(integer(v, 0, KEEP_MAX) for v in b['keep'].values()))
    if 'market_epoch' in b:
        need(integer(b['market_epoch'], 0, 10**12))
    if 'certificate_block' in b:
        need(type(b['certificate_block']) is bool)
    if 'certificate_closed_at' in b:
        need(integer(b['certificate_closed_at'], 0, b['cursor']))
    if 'closed_at' in b:
        need(integer(b['closed_at'], 0, b['cursor']))
    if 'protection' in b:
        need(isinstance(b['protection'], dict) and set(b['protection']) == {'level'} and isinstance(b['protection']['level'], str) and b['protection']['level'] in market.PLANS)
    if 'protection_quote' in b:
        q = b['protection_quote']
        need(isinstance(q, dict) and set(q) == {'day', 'wealth'} and integer(q['day'], 1, 10**12) and wealth_pricing.valid_wealth(q['wealth']))
    if 'chain_carry' in b:
        cc = b['chain_carry']
        need(isinstance(cc, dict) and set(cc) <= {'rent', 'power', 'tax'}
             and all(integer(v, 0, 99 if k == 'tax' else DEN - 1) for k, v in cc.items()))
    if 'income_tax' in b:
        need(isinstance(b['income_tax'], dict) and set(b['income_tax']) == {'loss', 'carry'} and integer(b['income_tax']['loss'], 0, 10**16) and integer(b['income_tax']['carry'], 0, 99))
    need(all(integer(b[k], 0, 10**16) for k in ('revenue', 'sold', 'seq', 'manual_seq')) and integer(b['halted'], -1, 2 * qy.MONEY_MAX))
    need(isinstance(b['recent'], list) and len(b['recent']) <= 12)
    for row in b['recent']:
        need(isinstance(row, dict) and {'id', 'at', 'dish', 'qty', 'total', 'channel', 'stars'} <= set(row) <= {'id', 'at', 'dish', 'qty', 'total', 'channel', 'stars', 'employee', 'name', 'text'})
        if 'employee' in row:
            need(all(isinstance(row.get(k), str) and 0 < len(row[k]) <= 500 for k in ('employee', 'name', 'text')))
        need(row['dish'] in qs.DISH[st['trade']] and integer(row['id'], 1, 10**16) and integer(row['qty'], 1, 6) and integer(row['total'], 0, 6 * PRICE_MAX))
        need(type(row['at']) in (int, float) and math.isfinite(row['at']) and 0 <= row['at'] <= 10**12 and row['channel'] in ('counter', 'online') and integer(row['stars'], 1, 5))
