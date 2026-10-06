"""Fictional xu business rules. Rates and allowances are game balance, not tax advice.

Every charge belongs to an operating-day row. No wall clock or personal wallet
debits. Owner totals share one allowance across locations; incidents affect at
most one counter per owner/life day. Legacy saves start with safe operating habits.
"""
from __future__ import annotations

PERIOD = 30
REVENUE_ALLOWANCE = 1000
PROFIT_ALLOWANCE = 200
VAT_PCT, INCOME_PCT = 2, 5
# Packaging, routine cleaning and supplies, calibrated at default menus/full staffing.
# Fixed rates on sales, never a post-hoc cap on the player's profit.
SUPPLIES = {
    'xe': dict(tra_da=9, fruit=0, ice_cream=7, cafe_bakery=2, milk_tea=6, florist=2, grocery=0, clothing=0),
    'sap': dict(tra_da=10, fruit=1, ice_cream=7, cafe_bakery=4, milk_tea=6, florist=2, grocery=0, clothing=2),
    'kiot': dict(tra_da=14, fruit=4, ice_cream=10, cafe_bakery=7, milk_tea=10, florist=5, grocery=0, clothing=3),
}
FOOD = frozenset({'tra_da','fruit','ice_cream','cafe_bakery','milk_tea','grocery'})
EVENTS = ('theft','robbery','food_check','police_check','extortion')


def config(st):
    return st.setdefault('economy', dict(hygiene=True, invoices=True, security=False, paused=False, incident=None))


def activate(s, st):
    if 'economy' not in st:
        st['day']=max(st['day'],s['journey']['life_day']-1)
    return config(st)


def tax_due(amount, allowance, rate):
    return max(0, ((amount-allowance)*rate+50)//100)


def _event(s, st, day):
    from . import quay as qy
    stalls = (qy.get(s) or {}).get('stalls') or [st]
    rng = qy._rng(s, dict(id='owner'), day, 'business-risk')
    chosen = stalls[rng.randrange(len(stalls))]['id']
    if chosen != st['id'] or day - st['opened'] < 5 or rng.random() >= .30:
        return None
    event = EVENTS[rng.randrange(len(EVENTS))]
    if event in ('theft','robbery') and st['theft'] and day-st['theft'] < qy.THEFT_GAP:
        return None
    # Camera, chuông, két and bảo vệ cut the odds exactly as their labels say (the
    # same factors as shop_events.theft_probability, relative to its 20% base).
    if event in ('theft','robbery') and rng.random() >= theft_factor(st):
        return None
    return event


def protection_level(st):
    """The protection that counts against theft: the paid plan, or the daily 'Bảo vệ quầy' toggle (basic)."""
    level = (st.get('business') or {}).get('protection', {}).get('level', 'none')
    if level == 'none' and (st.get('economy') or {}).get('security'):
        level = 'basic'
    return level


def theft_factor(st):
    """0..1: what is left of the theft/robbery odds after the counter's items and protection."""
    from .shop_events import theft_probability
    return theft_probability(st.get('items') or [], protection_level(st)) / .20


def theft_risk(s, st):
    """Percent chance (one decimal) that a given sales day here ends with a theft or robbery."""
    from . import quay as qy
    n = max(1, len((qy.get(s) or {}).get('stalls') or [st]))
    return round(100 * .30 / n * 2 / len(EVENTS) * theft_factor(st), 1)


def _tax(s, day, revenue, profit):
    from . import quay as qy
    q = qy.ensure(s)
    period = max(0, (day - 1) // PERIOD)
    tax = q.get('economy')
    if tax:period=max(period,tax['period'])  # delayed sales/receipts cannot reopen an earlier allowance
    if not tax or tax['period'] != period:
        tax = q['economy'] = dict(period=period, revenue=0, profit=0, vat=0, income=0)
    tax['revenue'] += revenue
    vat = tax_due(tax['revenue'],REVENUE_ALLOWANCE,VAT_PCT) - tax['vat']
    tax['profit'] += profit-vat
    # Losses offset profits in the same period. A refund never exceeds tax paid.
    income = tax_due(tax['profit'],PROFIT_ALLOWANCE,INCOME_PCT) - tax['income']
    tax['vat'] += vat
    tax['income'] += income
    return vat, income


def settle(s, st, day):
    """Hook after a manual/passive sales row. Returns the final net, once only."""
    from . import quay as qy
    if not st['hist'] or st['hist'][-1]['d'] != day:
        return None
    h = st['hist'][-1]
    if 'costs' in h:
        return h['net']
    c = activate(s,st)
    revenue, original = h['rev'], h['net']
    rent = qy.PLACES[st['place']]['rent'] // qy.MONTH_DAYS
    supplies = round(revenue * SUPPLIES[st['place']][st['trade']] / 100)
    # Skipping routine checks saves a little now but creates a real compliance violation.
    if not c['hygiene']: supplies = max(0, supplies - 2)
    security = 2 if c['security'] else 0
    incident = 0
    q=qy.ensure(s)
    event = _event(s, st, day) if q.get('risk_day',-1)<day else None
    if event:q['risk_day']=day
    if event in ('theft', 'robbery'):
        protected = c['security'] or 'ket' in st['items']
        loss = max(20, round(revenue * (.45 if protected else 1.5)))
        # A két sắt: a thief never gets more than half of the till.
        incident = min(max(0,st['till']//2 if 'ket' in st['items'] else st['till']-(1 if protected else 0)), loss)
        st['till'] -= incident
        if incident:
            st['theft'] = day
            st['case'] = dict(day=day,lost=incident,all=st['till']==0,rep=False,due=0)
        label = 'Trộm lấy tiền trong két' if event == 'theft' else 'Cướp tiền bán hàng'
        qy._log(st,day,label,-incident)
        c['incident'] = dict(kind=event,day=day,status='open',loss=incident)
    elif event in ('food_check', 'police_check'):
        violation = (st['trade'] in FOOD and not c['hygiene']) if event == 'food_check' else not c['invoices']
        if violation:
            incident = max(20, revenue)
            c['paused'] = event == 'food_check'
            label = 'Hàng không đạt vệ sinh: tiêu hủy, tạm dừng' if event == 'food_check' else 'Thiếu chứng từ: xử lý vi phạm'
            qy._log(st,day,label,-incident)
        else:
            qy._log(st,day,'Kiểm tra đạt: không phạt',0)
        c['incident'] = dict(kind=event,day=day,status='violation' if violation else 'clear',loss=incident)
    elif event == 'extortion':
        c['incident'] = dict(kind=event,day=day,status='open',loss=0)
        qy._log(st,day,'Bị đòi tiền bảo kê: giữ bằng chứng và báo công an',0)
    vat, income = _tax(s,day,revenue,original-rent-supplies-security-incident)
    charged = rent + supplies + security + vat + income + (incident if event not in ('theft','robbery') else 0)
    paid = qy._from_till_fund(st,max(0,charged))
    if charged < 0: st['till'] = min(qy.MONEY_MAX,st['till']-charged)
    # Any unpaid operating bill stays local and pauses this counter. Never draw
    # from other counters, a personal wallet, bank, or credit.
    unpaid = max(0,charged-paid)
    st['due'] = min(qy.MONEY_MAX,st['due']+unpaid)
    h['costs'] = dict(base=revenue-original,rent=rent,supplies=supplies,security=security,
                      vat=vat,income=income,incident=incident,unpaid=unpaid)
    h['net'] = original-rent-supplies-security-vat-income-incident
    run = st.get('run')
    if isinstance(run,dict) and run.get('d') == day and isinstance(run.get('sum'),dict):
        run['sum']['net'] = h['net']
    qy._log(st,day,'Thuê chỗ, vật tư, an ninh, thuế (mức xu trong game)',-(rent+supplies+security+vat+income))
    return h['net']


def action(s, st, name, p):
    from . import quay as qy
    need = qy._core().need
    c = activate(s,st)
    day = s['journey']['life_day']
    if name == 'jr_quay_prepare':
        need(set(p) <= {'stall','kind','enabled'} and p.get('kind') in ('hygiene','invoices','security') and type(p.get('enabled')) is bool,
             'Chọn việc chuẩn bị hợp lệ.')
        kind = p['kind']; c[kind] = p['enabled']
        if kind == 'hygiene' and p['enabled']:
            c['paused'] = False
            if c['incident'] and c['incident']['kind'] == 'food_check': c['incident']['status'] = 'repaired'
        qy._log(st,day,('Bật ' if p['enabled'] else 'Tắt ')+dict(hygiene='kiểm hàng và vệ sinh',invoices='lưu chứng từ',security='bảo vệ quầy')[kind])
        return dict(message='Đã cập nhật chuẩn bị cho quầy.')
    need(set(p) <= {'stall','choice'} and p.get('choice') in ('report','refuse'), 'Chọn cách xử lý hợp lệ.')
    need(c['incident'] and c['incident']['kind']=='extortion' and c['incident']['status']=='open','Không có vụ bảo kê đang chờ xử lý.')
    c['incident']['status'] = 'reported' if p['choice']=='report' else 'refused'
    qy._log(st,day,'Lưu bằng chứng, báo công an về bảo kê' if p['choice']=='report' else 'Từ chối đưa tiền bảo kê')
    return dict(message='Đã báo công an và giữ bằng chứng. Không mất xu.' if p['choice']=='report' else 'Đã từ chối. Không mất xu.')


def recovery(s, st, day, amount):
    """Recovered money is visible even on a closed day; it never accrues rent."""
    from . import quay as qy
    if not st['hist'] or st['hist'][-1]['d'] != day:
        st['hist']=qy.ar.last(st['hist']+[dict(d=day,n=0,rev=0,net=0,w='',p='')],qy.HIST_MAX,'quay.hist',qy.ar.JOURNEY)
    h=st['hist'][-1]
    c=h.setdefault('costs',dict(base=h['rev']-h['net'],rent=0,supplies=0,security=0,vat=0,income=0,incident=0,unpaid=0))
    vat,income=_tax(s,day,0,amount)
    paid=qy._from_till_fund(st,max(0,vat+income))
    if vat+income < 0:st['till']=min(qy.MONEY_MAX,st['till']-vat-income)
    c['incident']-=amount;c['vat']+=vat;c['income']+=income
    c['unpaid']+=max(0,vat+income-paid)
    st['due']+=max(0,vat+income-paid)
    h['net']+=amount-vat-income
    run=st.get('run')
    if isinstance(run,dict) and run.get('d')==day and isinstance(run.get('sum'),dict):run['sum']['net']=h['net']


def shift_receipt(s, st, stall_id, revenue, wage, source, label):
    """Recognize hired income and escrow expense without paying that wage twice.

    Separate from daily sales: arrival order must not overwrite today's own sale
    or start another operating-day charge. Receipt remains after a counter sale.
    live_effects' stable effect ID/save transaction supplies exactly-once delivery.
    """
    from . import quay as qy
    day=s['journey']['life_day']
    q=qy.ensure(s)
    if st:activate(s,st)
    vat,income=_tax(s,day,revenue,revenue-wage)
    cash=revenue-vat-income
    if st:
        # Taxes come from this receipt; no debit to the earlier wage's funding pocket.
        qy._core().need(st['till']+cash<=qy.MONEY_MAX,'Két chưa đủ chỗ nhận tiền ca. Thu két rồi thử lại.','till_full')
        st['till']+=cash
        qy._log(st,day,label+' · sau thuế',cash)
    else:
        qy._jr()._wallet(s['journey'],cash,qy.KIND_OUT,label[:120])
    row=dict(d=day,stall=stall_id,label=label[:120],rev=revenue,wage=wage,source=source,
             vat=vat,income=income,net=cash-wage,cash_net=cash,pocket='till' if st else 'wallet')
    q['receipts']=qy.ar.last(q.get('receipts',[])+[row],20,'quay.receipts',qy.ar.JOURNEY)
    return row


def public(st):
    c = st.get('economy') or dict(hygiene=True,invoices=True,security=False,paused=False,incident=None)
    h = st['hist'][-1] if st['hist'] else {}
    return dict(c, costs=h.get('costs'), revenue=h.get('rev',0), net=h.get('net',0),
                supplies_pct=SUPPLIES[st['place']][st['trade']],security_fee=2)


def validate_owner(q, need, integer):
    if 'risk_day' in q:need(integer(q['risk_day'],0,10**6))
    if 'receipts' in q:
        rows=q['receipts'];need(isinstance(rows,list) and len(rows)<=20)
        for r in rows:
            need(isinstance(r,dict) and integer(r.get('d'),0,10**6)
                 and isinstance(r.get('stall'),str) and 1<len(r['stall'])<=100
                 and isinstance(r.get('label'),str) and len(r['label'])<=120
                 and r.get('source') in ('stall','cash','account','joint') and r.get('pocket') in ('till','wallet')
                 and integer(r.get('rev'),1,10**8) and integer(r.get('wage'),1,10**4)
                 and all(integer(r.get(k),-10**8,10**8) for k in ('vat','income','net','cash_net')))
            need(r['cash_net']==r['rev']-r['vat']-r['income'] and r['net']==r['cash_net']-r['wage'])
    if 'economy' not in q:return
    t=q['economy']
    limit=10**18  # aggregate ledger arithmetic bound, not a counter-count limit
    need(isinstance(t,dict) and integer(t.get('period'),0,10**6)
         and integer(t.get('revenue'),0,limit) and integer(t.get('profit'),-limit,limit)
         and integer(t.get('vat'),0,limit) and integer(t.get('income'),0,limit))
    need(t['vat']==tax_due(t['revenue'],REVENUE_ALLOWANCE,VAT_PCT)
         and t['income']==tax_due(t['profit'],PROFIT_ALLOWANCE,INCOME_PCT))


def validate(q, st, need, integer):
    if 'economy' in st:
        c=st['economy']
        need(isinstance(c,dict) and all(type(c.get(k)) is bool for k in ('hygiene','invoices','security','paused')))
        x=c.get('incident')
        need(x is None or (isinstance(x,dict) and x.get('kind') in EVENTS and x.get('status') in ('open','violation','clear','repaired','reported','refused')
                           and integer(x.get('day'),0,10**6) and integer(x.get('loss'),0,10**8)))
    for h in st['hist']:
        if 'costs' in h:
            c=h['costs']
            need(isinstance(c,dict) and all(integer(c.get(k),-10**8,10**8) for k in ('base','rent','supplies','security','vat','income','incident','unpaid')))
