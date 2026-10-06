"""Server-clock staff orders, independent of the owner's in-progress tasks.

Each staff member completes a small, explicitly named order. Materials leave the
real warehouse; wages and operating supplies are paid before revenue from the
workplace balance only. This module never completes a player's task or advances
their career day. A bounded catch-up retains its remaining cursor for later calls.
"""
from __future__ import annotations

import copy
import math
import time
from . import staff_life

VERSION = 1
# Keep long offline catch-up responsive while retaining every pending order.
# 1,024 accounting orders with real ledger writes take about 130 ms locally.
MAX_ORDERS = 1024
RECENT = 12
LIMIT = 10**12
TIME_MAX = 10**11
PROFIT_PERCENT = 40

# Authored independent staff orders. Prices are game coins, not salaries or
# rewards for the owner's career tasks. Inventory inputs are real catalogue IDs.
# (label, base revenue, consumables charged from funds, inventory inputs)
ORDERS = {
    'mother_baby': ('Đơn riêng: một món đồ em bé', 75, 1, {'bunny': 1}),
    'pharmacy': ('Đơn riêng: xuất một hộp theo phiếu đã kiểm', 18, 1, {'P-01-A': 1}),
    'accounting': ('Hồ sơ riêng: phân loại và đối chiếu phiếu', 16, 3, {}),
    'customer_care': ('Hồ sơ riêng: xác minh và trả lời một yêu cầu', 15, 2, {}),
    'teacher': ('Buổi riêng: hỗ trợ một bài thực hành', 16, 3, {}),
    'tour_guide': ('Lượt riêng: hướng dẫn khách tại điểm tham quan', 18, 4, {}),
    'milk_tea': ('Đơn riêng: trà sữa size M không topping', 30, 1, {'milk': 1, 'cup_M': 1}),
    'restaurant': ('Đơn riêng: mì kim chi mang về', 35, 1, {'noodle': 1, 'pack_kimchi': 1, 'box': 1}),
    'cafe_bakery': ('Đơn riêng: cà phê đen mang về', 30, 1, {'beans_house': 1, 'cup': 1}),
    'florist': ('Đơn riêng: gói một cành hồng', 18, 1, {'rose_red': 1, 'paper_kraft': 1}),
    'grocery': ('Đơn riêng: một túi gạo', 18, 1, {'rice': 1}),
    'repair': ('Việc riêng: bảo dưỡng xích xe', 12, 1, {'oil': 1}),
    'farm': ('Việc riêng: chuẩn bị luống và gieo hạt thuê', 12, 1, {'seed_muong': 1, 'compost': 1}),
    'delivery': ('Đơn riêng: đóng gói và giao kiện nhỏ', 18, 3, {'bubble': 1, 'tape': 1}),
    'homestay': ('Lượt riêng: thay ga và chuẩn bị phòng thuê', 30, 2, {'linen': 1, 'soap_kit': 1}),
    'pet_care': ('Lượt riêng: vệ sinh và chăm sóc thú cưng', 18, 1, {'sh_normal': 1, 'towel': 1}),
    'salon': ('Lượt riêng: gội và cắt tóc đơn giản', 30, 1, {'shampoo': 1, 'towel': 1}),
    'corp_accounting': ('Hồ sơ riêng: kiểm chứng từ doanh nghiệp', 18, 3, {}),
    'tax_payroll': ('Hồ sơ riêng: rà soát bảng lương', 18, 3, {}),
    'group_accounting': ('Hồ sơ riêng: đối chiếu nội bộ', 20, 4, {}),
    'clothing': ('Đơn riêng: áo thun đúng cỡ', 115, 2, {'tee': 1}),
    'pet_shop': ('Đơn riêng: thức ăn chó trưởng thành', 42, 1, {'dog_adult': 1}),
    'tra_da': ('Đơn riêng: trà nóng và bánh quy', 7, 1, {'che': 1, 'banh_quy': 1}),
    'fruit': ('Đơn riêng: một phần xoài', 14, 1, {'xoai': 1}),
    'garbage': ('Việc riêng: thu gom một bao rác', 14, 2, {'bao': 1}),
    'drain': ('Việc riêng: vệ sinh đoạn thoát nước', 18, 2, {'bot': 1, 'gang_tay': 1}),
    'homemaker': ('Việc riêng: dọn và sắp xếp một phòng', 16, 4, {}),
    # One sealed tub sells as a whole 1.2 kg take-away tub (5 xu/100 g), never at a scoop's price.
    'ice_cream': ('Đơn riêng: hộp kem dừa mang về 1,2 kg', 60, 1, {'dua': 1}),
    'nail': ('Lượt riêng: cắt dũa và sơn móng thường', 12, 1, {'son_nude': 1}),
    'pagoda': ('Việc riêng: chuẩn bị vật phẩm theo đặt hàng', 12, 5, {}),
    'pho': ('Đơn riêng: phở chín mang về', 32, 2, {'banh': 1, 'chin': 1, 'rau': 1, 'hop': 1}),
    'com': ('Đơn riêng: cơm trứng rau mang về', 10, 1, {'gao': 1, 'trung': 1, 'rau': 1, 'hop': 1}),
    'photobooth': ('Đơn riêng: chụp và in một dải ảnh', 14, 1, {'giay_dai': 1}),
    'giupviec': ('Việc riêng: lau kính một phòng', 12, 2, {'chai_kinh': 1}),
    'naucom': ('Việc riêng: chuẩn bị một phần ăn đặt trước', 18, 8, {}),
    'babysitter': ('Lượt riêng: hỗ trợ một buổi trông trẻ', 18, 4, {}),
    'library': ('Việc riêng: bao bìa, dán nhãn một chồng sách cho trường', 16, 2, {'nhan': 1}),
    'pilot': ('Việc riêng: hỗ trợ kiểm tra kế hoạch bay', 22, 5, {}),
    'flight_attendant': ('Việc riêng: chuẩn bị một lượt phục vụ', 18, 4, {}),
    'hr_admin': ('Hồ sơ riêng: kiểm và lưu hồ sơ nhân sự', 16, 3, {}),
    'secretary': ('Việc riêng: chuẩn bị lịch và hồ sơ cuộc họp', 16, 3, {}),
    'it_helpdesk': ('Yêu cầu riêng: kiểm tra và hỗ trợ thiết bị', 20, 4, {}),
}
REASONS = {
    'working': 'Nhân viên đang xử lý đơn riêng.', 'closed': 'Nơi làm việc đã đóng ca.',
    'paused': 'Bạn đã tạm dừng đơn của nhân viên.', 'staff': 'Chưa có nhân viên trong ca.',
    'incident': 'Nhân viên đang nghỉ hoặc chờ xử lý sự cố.',
    'stock': 'Hết nguyên liệu cho đơn riêng; nhập hàng để tiếp tục.',
    'fund': 'Quỹ nơi làm việc không đủ trả lương và vật tư trước đơn tiếp theo.',
    'limit': 'Sổ thu chi đã đạt giới hạn lưu trữ.',
}


def _now(now=None):
    return min(TIME_MAX, max(0, int(time.time() if now is None else now)))


def _eligible(c):
    from . import operations as ops
    visiting={r['staff'] for r in c.get('player_service_jobs',[]) if r['status']=='queued'}
    return [e for e in c['ops']['staff'] if e['id'] not in visiting and e['status']=='hired' and e['on_shift']
            and not ops.paused(c['ops'],e) and e['rest_until']<=c['turn']
            and not e.get('strike',False)]


def _seconds(c,e):
    from .work_gear import factor
    from .shop_events import demand_factor
    return max(15, math.ceil(80*60/max(1,e['speed'])/factor(c)/demand_factor(c)))


def _signature(c,e):
    return f"{e['role']}:{staff_life.wage(c['ops'],e)}:{e['precision']}:{e['morale']}:{_seconds(c,e)}"


def _staff_changed(c,e,pending):
    # Equipment is a duration snapshot: new gear affects the next order. A
    # deliberate assignment/training/pay change cancels and reanchors work.
    return pending['signature'].rsplit(':',1)[0]!=_signature(c,e).rsplit(':',1)[0]


def _reason(c,b):
    if not any(e['status']=='hired' and e['on_shift'] for e in c['ops']['staff']):return 'staff'
    if not _eligible(c):return 'incident'
    return 'working'


def _new(now):
    return dict(v=VERSION,paused=False,anchor=now,pending={},served=0,revenue=0,
                expenses=0,wages=0,materials=0,goods=0,net=0,recent=[],reason='staff')


def prepare(c,now):
    """Lazy compatibility marker: legacy closed/paused time never becomes work.

    Keep business v1 and its receipts byte-shape compatible with older releases;
    the optional operations sidecar owns bonus carry and the continuous clock.
    """
    o=c['ops'];b=o.get('business');changed=False
    if b is None:
        if not any(e['status']=='hired' for e in o['staff']):return False
        b=o['business']=_new(now);changed=True
    first='business_profit' not in o
    if first:
        o['business_profit']=dict(v=1,anchor=now,positive=0,total=0,carry=0,recent={},visitor_total=0,visits={})
        changed=True
    profit=o['business_profit']
    if 'visitor_total' not in profit:
        profit.update(visitor_total=0,visits={});changed=True
    if b['paused'] or b['reason']=='closed' or first and not c['open']:
        b.update(paused=False,anchor=now,pending={},reason='staff')
        for r in c.get('player_service_jobs',[]):
            if r['status']=='queued':r['due_at']=min(TIME_MAX,now+r['seconds'])
        changed=True
    return changed


def refresh(c,career,now=None):
    """Anchor new/changed staff at now. Never invent work before their first clock."""
    now=_now(now);o=c['ops'];changed=prepare(c,now);b=o.get('business')
    if b is None:return changed
    reason=_reason(c,b)
    if reason!='working':
        if b['pending']:b['pending']={};changed=True
        if b['reason']!=reason:b['reason']=reason;changed=True
        return changed
    employees={e['id']:e for e in _eligible(c)}
    if not b['pending'] and b['reason'] in ('stock','fund','limit') and all(_blocked(c,career,e,b) for e in employees.values()):
        return changed
    for sid in list(b['pending']):
        if sid not in employees:del b['pending'][sid];changed=True
    for sid,e in employees.items():
        pending=b['pending'].get(sid)
        if pending is None or _staff_changed(c,e,pending):
            seconds=_seconds(c,e)
            b['pending'][sid]=dict(at=min(TIME_MAX,now+seconds),seconds=seconds,signature=_signature(c,e))
            changed=True
    if b['reason']!='working':b['reason']='working';changed=True
    return changed


def _reserved(c,item):
    # Legacy shopping baskets reserve stock before checkout. Plugin recipes
    # consume inventory at their own action step and must remain untouched.
    return sum(t.get('basket',{}).get(item,0) for t in c['tasks']
               if t['status'] not in ('completed','referred','cancelled'))


def _stock_ok(c,career,inputs):
    if career=='milk_tea':
        from . import boba
        return boba.view(c)['cups']['M']>=inputs['cup_M'] and boba.stock(c)['milk']>=inputs['milk']
    from . import inventory as inv
    if c.get('ext',{}).get('inv') is not None:
        if career=='grocery':
            from .careers import grocery
            return all(grocery._available(c,item)>=qty for item,qty in inputs.items())
        if career=='clothing':
            return all(_clothing_size(c,item) is not None and inv.count(c,item)>=qty for item,qty in inputs.items())
        return all(inv.count(c,item)>=qty for item,qty in inputs.items())
    from . import engine
    for item,qty in inputs.items():
        if c['stock'].get(item,0)-_reserved(c,item)<qty:return False
        if career=='pharmacy':
            from .content import LOT_INDEX
            lot=LOT_INDEX[item]
            if lot['status']!='available' or lot['valid_until']<c['day'] or item in c['held_lots'] or engine.ph_shelf_block(c,item):return False
    return True


def _clothing_size(c,item):
    from .careers import clothing
    return clothing.staff_size(c,item)


def _cash(c,career,e):
    return math.ceil(staff_life.wage(c['ops'],e)/4)+ORDERS[career][2]


def _order(c,career,visitor=False,e=None):
    """The next staff order. Shops with a menu (game/staff_orders.py) sell across their
    real catalogue at shelf prices, only what is in stock and still earns after the
    wage; visiting players keep buying the single authored order."""
    if visitor:return ORDERS[career]
    served=c['ops'].get('business',{}).get('served',0)
    if career=='clothing':
        from .careers import clothing
        return clothing.staff_order(c,served)
    from . import staff_orders
    if career in staff_orders.MENUS and e is not None:
        return staff_orders.pick(c,career,served,_cash(c,career,e),ORDERS[career][2])
    return ORDERS[career]


def _receipt_key(career):
    from . import staff_orders
    return 'business_clothing_receipts' if career=='clothing' else 'business_receipts' if career in staff_orders.MENUS else None


def _take_stock(c,career,inputs):
    if career=='milk_tea':
        from . import boba
        boba.state(c)['cups']['M']-=inputs['cup_M']
        cost,_=boba._use(c,'milk')
        c['life']['consumed_cost']+=cost
        return cost
    from . import inventory as inv
    if c.get('ext',{}).get('inv') is not None:
        if career=='clothing':
            from .careers import clothing
            clothing._sync(c)
            return sum(clothing._sell(c,item,_clothing_size(c,item)) for item,qty in inputs.items() for _ in range(qty))
        return sum(inv.take(c,item,qty) for item,qty in inputs.items())
    from . import engine
    from .content import PRODUCTS,LOT_INDEX
    costs={p['id']:p['cost'] for p in PRODUCTS} if career=='mother_baby' else {i:l['cost'] for i,l in LOT_INDEX.items()}
    for item,qty in inputs.items():c['stock'][item]-=qty
    if career=='pharmacy':
        care=engine.ph_care(c,create=False)
        if care:engine._ph_sync(c,care)
    return sum(costs.get(item,0)*qty for item,qty in inputs.items())


def _blocked(c,career,e,b,visitor=False,order=False):
    if c['money']<_cash(c,career,e):return 'fund'
    if order is False:order=_order(c,career,visitor,e)
    if order is None:return 'stock'
    _,_,supplies,inputs=order
    if not _stock_ok(c,career,inputs):return 'stock'
    if b['served']>=LIMIT or c['earnings']>10**9-1000 or c['money']>10**9-1000:return 'limit'
    return None


def _finish(s,c,career,e,at,order=None):
    from . import operations as ops
    b=c['ops']['business'];label,base,supplies,inputs=order or _order(c,career,e=e)
    seq=b['served']+1
    quality=staff_life.quality(e,seq,career)['stars']
    revenue=base*(80+quality*4)//100
    wage=math.ceil(staff_life.wage(c['ops'],e)/4);cash=wage+supplies
    goods=_take_stock(c,career,inputs)
    ref=f'staff-order-{career}-{seq}'
    # Customer revenue retains the normal deferred tax. Stock cost was already
    # paid on purchase; its basis belongs in the margin, never another cash debit.
    for amount,category,reason in ((-wage,'wage','Lương đơn riêng'),(-supplies,'materials','Vật tư đơn riêng'),(revenue,'revenue',label)):
        c['money']+=amount
        c['earnings']+=max(0,amount);c['costs']+=max(0,-amount)
        ops.record_money(c,amount,reason+' · '+e['name'],ref,category)
    expenses=cash+goods
    b['served']=seq;b['revenue']+=revenue;b['expenses']+=expenses
    b['wages']+=wage;b['materials']+=supplies;b['goods']+=goods;b['net']+=revenue-expenses
    receipt=dict(id=ref,at=at,employee=e['id'],name=e['name'],label=label,stars=quality,
                 items=dict(inputs),revenue=revenue,wage=wage,materials=supplies,goods=goods,
                 expenses=expenses,cash_expenses=cash,net=revenue-expenses)
    key=_receipt_key(career)
    if key:
        # Older servers only accept the original single-item receipt in b['recent'];
        # catalogue receipts live in a sidecar they ignore.
        c['ops'][key]=(_recent(c)+[receipt])[-RECENT:]
        b['recent']=[]
    else:b['recent']=(b['recent']+[receipt])[-RECENT:]
    credit_profit_bonus(c,revenue-expenses,ref,e['name'])
    e['jobs']=min(10**9,e['jobs']+1);e['last_work']=f'{label} · {quality}/5 sao · thu {revenue} xu, lương {wage} xu.'
    if quality<4:e['errors']=min(10**9,e['errors']+1)



def _recent(c):
    legacy=c['ops']['business']['recent']
    actual=c['ops'].get('business_clothing_receipts',c['ops'].get('business_receipts'))
    if actual is None:return legacy
    ids={r['id'] for r in legacy}
    return ([r for r in actual if r['id'] not in ids]+legacy)[-RECENT:]


def credit_profit_bonus(c,margin,ref,name,visitor=False):
    """Credit 40% of positive pre-tax margin; callers own the durable receipt."""
    from . import operations as ops
    profit=c['ops']['business_profit'];bucket='visits' if visitor else 'recent'
    if ref in profit[bucket]:return 0
    margin=max(0,margin)
    bonus,profit['carry']=divmod(profit['carry']+margin*PROFIT_PERCENT,100)
    profit['positive']+=margin;profit['total']+=bonus
    if bonus:
        c['money']+=bonus;c['earnings']+=bonus
        ops.record_money(c,bonus,'Thưởng 40% lợi nhuận '+('đơn khách' if visitor else 'đơn riêng')+' · '+name,ref,'other_income')
    profit[bucket][ref]=bonus
    if visitor:
        profit['visitor_total']+=bonus
        ids={r['id'] for r in c.get('player_service_jobs',[])}
    else:ids={r['id'] for r in _recent(c)}
    profit[bucket]={key:value for key,value in profit[bucket].items() if key in ids}
    return bonus


def settle(s,now=None):
    """Mutate only an owned transaction state; process at most MAX_ORDERS globally."""
    from .operations import recent_ledger_batch
    with recent_ledger_batch():
        return _settle(s,now)


def _settle(s,now=None):
    now=_now(now);changed=False;remaining=MAX_ORDERS;businesses=[]
    from .player_service_tasks import settle_staff
    from .shop_events import tick_career
    for career,c in s.get('careers',{}).items():
        if career not in ORDERS or 'ops' not in c:continue
        changed=staff_life.tick_career(s,c,career) or changed
        changed=tick_career(s,c,career) or changed
        changed=prepare(c,now) or changed
        changed=settle_staff(c,career,now) or changed
        changed=refresh(c,career,now) or changed
        b=c['ops'].get('business')
        if not b or _reason(c,b)!='working':continue
        businesses.append((career,c,b,{e['id']:e for e in _eligible(c)}))
    # Oldest completion across every workplace: one large offline backlog cannot
    # monopolize the per-call budget while another workplace never gets a turn.
    while remaining:
        ready=[(p['at'],career,sid,c,b,p,employees[sid])
               for career,c,b,employees in businesses for sid,p in b['pending'].items() if p['at']<=now]
        if not ready:break
        at,career,sid,c,b,pending,e=min(ready,key=lambda x:x[:3])
        order=_order(c,career,e=e) if c['money']>=_cash(c,career,e) else None
        reason=_blocked(c,career,e,b,order=order)
        if reason:
            # Discard blocked time: replenishment never pays work performed
            # when the business had no goods or wages available.
            b['pending']={};b['reason']=reason;changed=True;continue
        _finish(s,c,career,e,at,order);remaining-=1;changed=True
        staff_life.tick_career(s,c,career)
        tick_career(s,c,career)
        pending['seconds']=_seconds(c,e);pending['signature']=_signature(c,e)
        pending['at']=min(TIME_MAX,at+pending['seconds'])
    return changed


def due(s,now=None):
    now=_now(now)
    from .player_service_tasks import staff_due
    for career,c in s.get('careers',{}).items():
        if career not in ORDERS or 'ops' not in c:continue
        if staff_due(c,now):return True
        b=c['ops'].get('business')
        if b is None:
            if any(e['status']=='hired' for e in c['ops']['staff']):return True
            continue
        if 'visitor_total' not in c['ops'].get('business_profit',{}) or b['paused'] or b['reason']=='closed':return True
        reason=_reason(c,b)
        if reason!='working':
            if b['pending'] or b['reason']!=reason:return True
            continue
        employees={e['id']:e for e in _eligible(c)}
        if set(b['pending'])!=set(employees):
            # Stopped businesses need no recurring writes until their resources
            # change enough to perform another order.
            if any(not _blocked(c,career,e,b) for e in employees.values()):return True
            continue
        if any(_staff_changed(c,employees[sid],p) or p['at']<=now for sid,p in b['pending'].items()):return True
    return False


def public(c,now=None):
    from .player_service_tasks import staff_working
    b=c['ops'].get('business')
    if b is None:return None
    out=copy.deepcopy(b);out['recent']=copy.deepcopy(_recent(c));now=_now(now)
    profit=c['ops'].get('business_profit',{});bonuses=profit.get('recent',{})
    own_bonus=profit.get('total',0)-profit.get('visitor_total',0)
    out.update(profit_bonus=own_bonus,visitor_profit_bonus=profit.get('visitor_total',0),base_net=b['net'],net=b['net']+own_bonus,profit_percent=PROFIT_PERCENT)
    for r in out['recent']:
        r.update(base_net=r['net'],profit_bonus=bonuses.get(r['id'],0),net=r['net']+bonuses.get(r['id'],0))
        r['text']=r['review']=staff_life.REVIEWS[r['stars']]
    out['review_count']=len(out['recent'])
    out['rating_average']=round(sum(r['stars'] for r in out['recent'])/len(out['recent']),1) if out['recent'] else None
    next_at=min((p['at'] for p in b['pending'].values()),default=None)
    out.update(status='running' if b['reason']=='working' else 'paused',reason_text=REASONS[b['reason']],
               next_at=next_at,server_now=now,catching_up=next_at is not None and next_at<=now,
               rate_per_hour=round(sum(3600/p['seconds'] for p in b['pending'].values()),1),
               wage_basis='Mỗi đơn trả 1/4 lương ca, làm tròn lên; vật tư trừ quỹ nơi làm việc.',fund=c['money'])
    _explain(c,b,out)
    if staff_working(c):
        out.update(status='running',reason='working',reason_text='Nhân viên đang phục vụ khách người chơi.',visitor_working=True)
        times=[r['due_at'] for r in c.get('player_service_jobs',[]) if r['status']=='queued' and r['due_at'] is not None]
        if times:out['next_at']=min(times+[next_at] if next_at is not None else times)
    out.pop('pending');return out


def _item_names(career):
    from . import staff_orders
    if career=='mother_baby':
        from .content import PRODUCT_INDEX
        return {k:p['name'] for k,p in PRODUCT_INDEX.items()}
    if career=='pharmacy':
        from .content import LOT_INDEX
        return {k:l['name']+' · '+k for k,l in LOT_INDEX.items()}
    from . import inventory as inv
    return {x['id']:x['name'] for x in inv.catalogue(career)}


def _explain(c,b,out):
    """Read-only: what the next staff order sells, earns and costs, and why a stop happened."""
    career=next((e.get('career') for e in c['ops']['staff'] if e.get('career') in ORDERS),None)
    if career is None:return
    team=_eligible(c) or [e for e in c['ops']['staff'] if e['status']=='hired']
    if not team:return
    e=min(team,key=lambda x:x['id']);cash=_cash(c,career,e);wage=cash-ORDERS[career][2]
    names=_item_names(career) if any(ORDERS[career][3].values()) or career=='clothing' else {}
    order=_order(c,career,e=e)
    if order is not None and _stock_ok(c,career,order[3]):
        from . import staff_orders
        label,base,supplies,inputs=order
        unit=staff_orders.costs(career) if names else {}
        goods=sum(unit.get(i,0)*q for i,q in inputs.items())
        typical=base*96//100
        out['next_order']=dict(label=label,revenue=base,revenue_low=base*84//100,wage=wage,materials=supplies,goods=goods,
                               margin=typical-wage-supplies-goods,
                               items=[dict(item=i,name=names.get(i,i),qty=q) for i,q in inputs.items()])
    if b['reason']=='stock':
        from . import staff_orders
        if career in staff_orders.MENUS:out['reason_text']=staff_orders.why(c,career,cash)
        else:
            if career=='clothing':gone=['quần áo còn size bán được']
            elif career=='milk_tea':
                from . import boba
                gone=[name for name,ok in (('sữa tươi',boba.stock(c)['milk']>=1),('ly size M',boba.view(c)['cups']['M']>=1)) if not ok]
            else:gone=[names.get(i,i) for i,q in ORDERS[career][3].items() if not _stock_ok(c,career,{i:q})]
            if gone:out['reason_text']='Hết '+', '.join(gone)+' cho đơn riêng; nhập hàng để đội làm tiếp.'
    out['money_note']=('Tiền đơn riêng vào quỹ nghề (Sổ thu chi), không vào ví. Mỗi đơn: thu theo giá kệ, trả lương '
                       f'{wage} xu và vật tư {ORDERS[career][2]} xu từ quỹ; giá vốn hàng đã trả lúc nhập.')


def validate(c,career):
    from .engine import need
    b=c['ops'].get('business')
    if b is None:return
    def check(ok):need(ok,'Dữ liệu đơn riêng của nhân viên không hợp lệ.','invalid_save')
    def integer(v,lo=0,hi=LIMIT):return type(v) is int and lo<=v<=hi
    profit=c['ops'].get('business_profit')
    if profit is not None:
        check(isinstance(profit,dict) and set(profit) in ({'v','anchor','positive','total','carry','recent'}, {'v','anchor','positive','total','carry','recent','visitor_total','visits'}))
        check(type(profit['v']) is int and profit['v']==1 and integer(profit['anchor'],0,TIME_MAX))
        check(integer(profit['positive']) and integer(profit['total']) and integer(profit['carry'],0,99))
        check(profit['total']*100+profit['carry']==profit['positive']*PROFIT_PERCENT)
        check(isinstance(profit['recent'],dict) and len(profit['recent'])<=RECENT)
        check(all(isinstance(ref,str) and ref.startswith('staff-order-'+career+'-') and integer(value) for ref,value in profit['recent'].items()))
        visitor_total=profit.get('visitor_total',0);visits=profit.get('visits',{})
        check(integer(visitor_total,0,profit['total']))
        check(isinstance(visits,dict) and len(visits)<=8)
        check(all(isinstance(ref,str) and 1<=len(ref)<=120 and integer(value) for ref,value in visits.items()))
        check(sum(visits.values())<=visitor_total)
        check(sum(profit['recent'].values())<=profit['total']-visitor_total)
    check(isinstance(b,dict) and set(b)==set(_new(0)) and type(b['v']) is int and b['v']==VERSION)
    check(type(b['paused']) is bool and integer(b['anchor'],0,TIME_MAX) and b['reason'] in REASONS)
    for key in ('served','revenue','expenses','wages','materials','goods'):check(integer(b[key]))
    check(integer(b['net'],-LIMIT,LIMIT) and b['net']==b['revenue']-b['expenses'])
    check(b['expenses']==b['wages']+b['materials']+b['goods'])
    check(isinstance(b['pending'],dict) and len(b['pending'])<=4)
    ids={e['id'] for e in c['ops']['staff']}
    for sid,p in b['pending'].items():
        check(sid in ids and isinstance(p,dict) and set(p)=={'at','seconds','signature'})
        check(integer(p['at'],0,TIME_MAX) and integer(p['seconds'],15,100000) and isinstance(p['signature'],str) and len(p['signature'])<=100)
    check(isinstance(b['recent'],list) and len(b['recent'])<=min(RECENT,b['served']))
    receipts=b['recent'];actual=None
    for key in ('business_clothing_receipts','business_receipts'):
        if key in c['ops']:
            check(actual is None and _receipt_key(career)==key)
            actual=c['ops'][key]
            check(isinstance(actual,list) and len(actual)<=min(RECENT,b['served']))
    if actual is not None:receipts=receipts+actual
    seen=set()
    for r in receipts:
        check(isinstance(r,dict) and set(r)=={'id','at','employee','name','label','stars','items','revenue','wage','materials','goods','expenses','cash_expenses','net'})
        check(isinstance(r['id'],str) and r['id'].startswith('staff-order-'+career+'-') and r['id'] not in seen);seen.add(r['id'])
        for key in ('employee','name','label'):check(isinstance(r[key],str) and len(r[key])<=200)
        check(integer(r['at'],0,TIME_MAX) and integer(r['stars'],1,5) and isinstance(r['items'],dict))
        if career=='clothing' and actual is not None and any(r is row for row in actual):
            from .careers import clothing
            check(len(r['items'])==1 and all(item in clothing.ITEM and qty==1 for item,qty in r['items'].items()))
            item=next(iter(r['items']))
            check(r['label']=='Đơn riêng: '+clothing.ITEM[item]['name'] or item=='tee' and r['label']==ORDERS[career][0])
        elif actual is not None and any(r is row for row in actual):
            from .staff_orders import known
            items=known(career)
            check(1<=len(r['items'])<=8 and all(item in items and type(qty) is int and 1<=qty<=999 for item,qty in r['items'].items()))
        else:check(r['items']==ORDERS[career][3])
        check(all(type(qty) is int for qty in r['items'].values()))
        for key in ('revenue','wage','materials','goods','expenses','cash_expenses'):check(integer(r[key]))
        check(integer(r['net'],-LIMIT,LIMIT) and r['net']==r['revenue']-r['expenses'])
        check(r['cash_expenses']==r['wage']+r['materials'] and r['expenses']==r['cash_expenses']+r['goods'])
