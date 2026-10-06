"""Authoritative, inventory-bounded wall-clock business ledger.

One business period is ten real minutes. Expenses carry fractional xu between
settlements; arrivals have absolute timestamps, so polling cannot change income.
Initialization purchases a modest starter shelf from existing business cash only.
Old life-day sales are disabled as soon as this optional runtime exists.
Unpaid traffic fines remain local liabilities and use later till/fund receipts;
they never debit the owner's personal wallet or disappear when a run closes.
"""
from __future__ import annotations

import math
import time
from . import quay as qy
from . import quay_self as qs
from . import quay_market as market
from . import wealth_pricing

PERIOD = 600
DEN = PERIOD * 1000
STOCK_MAX = 20000
PRICE_MAX = 1000000
LEGACY_EXPENSES = ('goods', 'wages', 'rent', 'power', 'online', 'tax', 'loss')
EXPENSES = LEGACY_EXPENSES + ('income_tax', 'environment', 'protection')
TIME_COSTS = ('wages', 'rent', 'power', 'environment', 'protection')   # billed by elapsed open time (_rates)
# Margin bonus, percent of the realized margin after costs and income tax.
# Owner self-serve and player-visitor orders keep 40%. Staff-run sales (settle())
# get 110%: the owner's take, margin x (1 + bonus), goes from 1.4x to 2.1x, i.e. x1.5.
BONUS_PERCENT = 40
STAFF_BONUS_PERCENT = 110


def staff_wage(st, member):
    from .staff_life import wage
    return wage(st, member)


def demand(base, price):
    """Per-item willingness: no positive floor at exploitative prices."""
    return min(1.6, (base / max(1, price)) ** 3)


def unit_cost(st, dish):
    return max(1, math.ceil(qs.cost_of(st['trade'], dish)))


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
        speed_factor=factor(s.get('careers', {}).get(st['trade'], {})))
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
    return changed


def _schedule(st, at):
    b = st['business']
    sig = _signature(st)
    if b['signature'] != sig:
        b['signature'] = sig
        b['arrivals'] = {d: market.advance(at, n) for d, n in _intervals(st).items()}


def status(st):
    b = st.get('business', {})
    if b.get('paused') or st.get('due', 0) or st.get('economy', {}).get('paused'):
        return 'paused'
    if not st['staff']:
        return 'no_staff'
    if not any(b.get('stock', {}).get(d, 0) for d in qs.menu(st)['on']):
        return 'out_of_stock'
    cash = st['fund'] + st['till']
    if cash < 1 or b.get('halted', -1) == cash:
        return 'no_funds'
    return 'running'


def _rates(st):
    p = qy.PLACES[st['place']]
    return dict(wages=sum(staff_wage(st, e) for e in st['staff']), rent=p['rent'] // qy.MONTH_DAYS, power=p['power'],
                environment={'xe': 1, 'sap': 2, 'kiot': 4}[st['place']],
                protection=_protection_plans(st)[st['business'].get('protection', {}).get('level', 'none')]['period_cost'])


def _protection_plans(st):
    wealth = st['business'].get('protection_quote', {}).get('wealth', 0)
    return {k: dict(v, period_cost=wealth_pricing.cost(v['period_cost'], wealth)) for k, v in market.PLANS.items()}


def collect_fines(st):
    """Collect a local liability once, only from existing business cash."""
    b = st.get('business')
    if not b or not b.get('unpaid_fines', 0):
        return 0
    paid = qy._from_till_fund(st, b['unpaid_fines'])
    b['unpaid_fines'] -= paid
    b['expenses']['loss'] += paid
    return paid


def assess_fine(st, amount):
    b = st['business']
    _profit_state(st)['costs'] += amount
    st['business']['income_tax']['loss'] += amount
    b['unpaid_fines'] = b.get('unpaid_fines', 0) + amount
    return collect_fines(st)


def _charge(st, elapsed):
    b, rates = st['business'], _rates(st)
    # Keep the last coin reserved. A zero balance otherwise stops small polls
    # earlier than a catch-up that reaches the next fractional expense boundary.
    cash = max(0, st['till'] + st['fund'] - 1)
    def cost(dt):
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
    for k, rate in rates.items():
        charge, b['carry'][k] = divmod(b['carry'][k] + dt * rate, DEN)
        qy._from_till_fund(st, charge)
        b['expenses'][k] += charge
        _profit_state(st)['costs'] += charge
        b['income_tax']['loss'] += charge
    if dt < elapsed:
        b['halted'] = st['till'] + st['fund']
    return dt == elapsed


def _profit_state(st):
    return st['business'].setdefault('profit_boost', dict(carry=0, total=0,
        costs=st['business'].get('unpaid_fines', 0)))


def reward_margin(st, revenue, costs, percent=BONUS_PERCENT):
    """Credit `percent` of realized margin after uncovered operating costs/losses.

    Inventory is expensed here only when consumed. Funding and unsold stock
    never earn a bonus; fractional xu survive small orders and polling.
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
    return bonus


def charge_income_tax(st, revenue, costs):
    """One margin ledger for counter, online, and actual visitor receipts."""
    b = st['business']
    tax = b['income_tax']
    margin = revenue - costs - tax['loss']
    tax['loss'] = max(0, -margin)
    charge, tax['carry'] = divmod(tax['carry'] + max(0, margin) * market.INCOME_TAX_PERCENT, 100)
    paid = qy._from_till_fund(st, charge)
    b['expenses']['income_tax'] += paid
    return paid


def sale(st, items, at, *, channel='counter', stars=None, total=None, extra_fee=0, extra_loss=0, employee=None):
    """Book only a real fulfilled order; stock was purchased before this point."""
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
    costs += charge_income_tax(st, amount, costs)
    bonus = reward_margin(st, amount, costs, BONUS_PERCENT if employee is None else STAFF_BONUS_PERCENT)
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
    return any(not isinstance(st.get('business'), dict) or
               (wealth_pricing.ENABLED and st['business'].get('protection_quote', {}).get('day') != s['journey']['life_day']) or
               'profit_boost' not in st['business'] or 'market_epoch' not in st['business'] or
               visit_due(st,at) or
               (st['business'].get('unpaid_fines', 0) > 0 and st['fund'] + st['till'] > 0) or
               (at > st['business']['cursor'] and (status(st) == 'running' or
                (not st['business']['paused'] and isinstance(st.get('run'), dict) and st['run'].get('continuous') and not st['run'].get('x'))))
               for st in (qy.get(s) or {}).get('stalls', []))


def settle(s, now=None):
    from .player_service_tasks import settle_visits
    from .shop_events import tick_quay
    from .staff_life import tick_quay as tick_staff
    at, changed = _ms(now), False
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
        if collect_fines(st):
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
        manual = isinstance(run, dict) and run.get('continuous') and not run.get('x') and not b['paused']
        intervals = _intervals(st)
        if not st['staff'] and manual:
            _charge(st, at - cursor)
        while status(st) == 'running':
            arrivals = [(max(cursor, when), d) for d, when in b['arrivals'].items() if b['stock'].get(d, 0)]
            when, dish = min(arrivals)
            end = min(when, at)
            if not _charge(st, end - cursor):
                break
            cursor = end
            if when > at or status(st) == 'no_funds':
                break
            qs.settle_queue(s, st, when)
            channel = 'online' if st.get('online') and b['seq'] % 3 == 2 else 'counter'
            employee = st['staff'][b['seq'] % len(st['staff'])]
            sale(st, [dish], when, channel=channel, employee=employee)
            tick_staff(s, st)
            b['arrivals'][dish] = market.advance(when, intervals[dish])
        market.enter_epoch(st, at)
        if status(st) != 'running':
            # Time while closed never becomes deferred sales after restocking.
            b['arrivals'] = {d: market.advance(at, n) for d, n in intervals.items()}
        qs.settle_queue(s, st, at)
        b['cursor'] = at
        tick_quay(s, st)
    for st in renew:
        st['business']['protection_quote'] = dict(quote)
        changed = True
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
                b['arrivals'] = {d: market.advance(b['cursor'], n) for d, n in _intervals(st).items()}
                qs.reopen_queue(st)
        return dict(message='Đã đóng quầy, xử lý nốt đơn đã nhận.' if p['on'] else 'Đã mở quầy, bắt đầu nhận khách mới.')
    if name == 'jr_quay_protection':
        need(set(p) <= {'stall', 'level'} and isinstance(p.get('level'), str) and p['level'] in market.PLANS, 'Gói bảo vệ không hợp lệ.')
        b['protection']['level'] = p['level']
        return dict(message='Đã chọn ' + market.PLANS[p['level']]['label'].lower() + '.')
    need(set(p) <= {'stall', 'items'}, 'Thông tin nhập hàng không hợp lệ.')
    items = p.get('items')
    rows = qs.DISH[st['trade']]
    need(isinstance(items, dict) and items and all(d in rows and type(n) is int and 1 <= n <= STOCK_MAX for d, n in items.items()), 'Chọn số lượng hàng cần nhập.')
    from .player_service_tasks import reserved
    need(sum(b['stock'].values()) + reserved(st) + sum(items.values()) <= STOCK_MAX, f'Kho chứa tối đa {STOCK_MAX} món.')
    cost = sum(unit_cost(st, d) * n for d, n in items.items())
    need(st['till'] + st['fund'] >= cost, f'Cần {cost} xu trong két hoặc vốn quầy.', 'no_money')
    qy._from_till_fund(st, cost)
    for d, n in items.items():
        b['stock'][d] = b['stock'].get(d, 0) + n
    b['expenses']['goods'] += cost
    b['halted'] = -1
    qy._log(st, s['journey']['life_day'], 'Nhập hàng vào kho', -cost)
    return dict(message=f'Đã nhập {sum(items.values())} món, hết {cost} xu.')


def income(st, at):
    """Read-only (#19, "how xem được thu nhập 1h"): what the staffed counter makes at its current setup, worked out from
    the same arrival intervals, market calendar, prices, costs, tax and staff bonus settle() uses. `hour` is the hour at
    the market of now; `day` is one full market cycle (24 h) if the stock and the money last. Nothing is written."""
    if not st['staff'] or not isinstance(st.get('business'), dict):
        return None
    iv = _intervals(st)
    if not iv:
        return None
    rates = _rates(st)
    online = qs.ONLINE_FEE if st.get('online') else 0

    def run(ms, work):   # work: the market's demand over that time, in percent-milliseconds
        sold = {d: work / (100 * n) for d, n in iv.items()}
        revenue = sum(q * qs.price(st, d) for d, q in sold.items())
        costs = sum(q * unit_cost(st, d) for d, q in sold.items()) + sum(rates.values()) * ms / DEN \
            + revenue / 3 * online / 100
        margin = revenue - costs
        tax = max(0, margin) * market.INCOME_TAX_PERCENT / 100
        bonus = max(0, margin - tax) * STAFF_BONUS_PERCENT / 100
        return dict(sold=round(sum(sold.values()), 1), revenue=round(revenue), costs=round(costs + tax),
                    bonus=round(bonus), net=round(margin - tax + bonus))
    hour_ms = 3600 * 1000
    now = market.snapshot(at)
    hour = run(hour_ms, now['demand_factor'] * 100 * hour_ms)
    day = run(market._CYCLE_MS, market._CYCLE_WORK)
    stock = sum(st['business']['stock'].get(d, 0) for d in iv)
    return dict(hour=hour, day=day, market=now['label'], stock_hours=round(stock / hour['sold'], 1) if hour['sold'] else None)


def public(st):
    from .player_service_tasks import public_visits,visit_due
    b = st.get('business')
    if not b:
        return None
    code = status(st)
    reasons = dict(running='Nhân viên đang bán', paused='Quầy tạm dừng', no_staff='Chủ tự phục vụ hoặc thuê nhân viên', out_of_stock='Hết hàng trong menu đang bán', no_funds='Hết vốn trả lương và chi phí')
    rows = qs.DISH[st['trade']]
    next_at = min((v for d, v in b['arrivals'].items() if b['stock'].get(d, 0)), default=0)
    visitors=public_visits(st)
    plans = _protection_plans(st)
    if not b['paused'] and visit_due(st,b['cursor']+1):
        code='running'
        pending=[r['due_at'] for r in visitors if r['status']=='queued' and r['due_at'] is not None]
        next_at=round(min(pending)*1000) if pending else b['cursor']
    rates = _rates(st)
    run = st.get('run')
    manual = isinstance(run, dict) and run.get('continuous') and not run.get('x') and not b['paused']
    # Time costs (wages, rent, power, environment, protection) accrue per real second while the
    # counter is open and working, sales or not: the same rule as _charge in settle().
    running = dict(per_period=sum(rates.values()), spent=sum(b['expenses'].get(k, 0) for k in TIME_COSTS),
                   accruing=bool(code == 'running' or (not st['staff'] and manual and code != 'paused')))
    return dict(v=1, status=code, reason=reasons[code], paused=b['paused'], running_cost=running,
        market=market.snapshot(b['cursor']), protection=dict(level=b.get('protection', {}).get('level', 'none'), options=[dict(level=k, **v) for k,v in plans.items()], **plans[b.get('protection', {}).get('level', 'none')], quote=dict(b.get('protection_quote', {}))),
        protection_plans=[dict(level=k, **v) for k,v in plans.items()],
        rates=rates, income_tax_percent=market.INCOME_TAX_PERCENT,
        bonus_percent=BONUS_PERCENT, staff_bonus_percent=STAFF_BONUS_PERCENT,
        visitor_orders=visitors,
        stock_total=sum(b['stock'].values()), stock=[dict(id=d, qty=b['stock'].get(d, 0), cost=unit_cost(st, d), price=qs.price(st, d)) for d in rows],
        period_seconds=PERIOD, wage=sum(staff_wage(st, e) for e in st['staff']), revenue=b['revenue'], sold=b['sold'],
        speed_factor=b.get('speed_factor', 1),
        profit_bonus=b.get('profit_boost', {}).get('total', 0),
        net=b['revenue'] + b.get('profit_boost', {}).get('total', 0) - sum(b['expenses'].values()) - b.get('unpaid_fines', 0),
        unpaid_fines=b.get('unpaid_fines', 0), expenses=dict(b['expenses']), recent=[dict(x) for x in b['recent']],
        next_at=next_at / 1000 if code == 'running' else None, server_now=b['cursor'] / 1000,
        income=income(st, b['cursor']))


def validate(st, need, integer):
    b = st.get('business')
    if b is None:
        return
    need(isinstance(b, dict) and b.get('v') == 1)
    need(all(k in b for k in ('cursor', 'paused', 'stock', 'arrivals', 'signature', 'carry', 'expenses', 'revenue', 'sold', 'recent', 'halted', 'seq', 'manual_seq')))
    need(integer(b['cursor'], 0, 10**15) and type(b['paused']) is bool and integer(b.get('owner_next', b['cursor']), 0, 10**18))
    need(type(b.get('speed_factor', 1)) in (int, float) and b.get('speed_factor', 1) in (1, 1.15, 1.35, 1.6))
    need(integer(b.get('unpaid_fines', 0), 0, 10**16))
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
    if 'market_epoch' in b:
        need(integer(b['market_epoch'], 0, 10**12))
    if 'closed_at' in b:
        need(integer(b['closed_at'], 0, b['cursor']))
    if 'protection' in b:
        need(isinstance(b['protection'], dict) and set(b['protection']) == {'level'} and isinstance(b['protection']['level'], str) and b['protection']['level'] in market.PLANS)
    if 'protection_quote' in b:
        q = b['protection_quote']
        need(isinstance(q, dict) and set(q) == {'day', 'wealth'} and integer(q['day'], 1, 10**12) and wealth_pricing.valid_wealth(q['wealth']))
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
