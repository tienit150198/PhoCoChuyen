"""Player customers use canonical career tasks; the order service owns payment.

The metadata is presentation/linkage only. A database order must independently
authorize every fulfillment/payment; imported task metadata is never a receipt.
"""
import copy
import contextvars
import hashlib
import json
import math
from contextlib import contextmanager

DONE = frozenset(('completed', 'cancelled', 'referred'))
_COMMAND = contextvars.ContextVar('player_service_command', default=None)
_GLOBAL = frozenset(('start_day','end_day','more_work','task_select','select_career',
    'reset_career','import_save','settings','buy_upgrade','advance','defer','talk',
    'quest_claim','feed_like','photo','chat_clear'))
_GLOBAL_PREFIXES = ('ops_','inv_','job_','jr_','business_','event_','soc_','fb_','pm_','inc_','hap_')


def _engine():
    from . import engine
    return engine


def validate(t):
    p=t.get('player_order')
    if p is None:return
    e=_engine();need=e.need
    need(isinstance(p,dict) and set(p)=={'v','id','buyer','note','price'},'Đơn khách người chơi không hợp lệ.')
    need(type(p['v']) is int and p['v']==1,'Phiên bản đơn khách không hợp lệ.')
    e.clean_text(p['id'],120)
    e.integer(p['price'],1,1000000)
    e.clean_text(p['note'],500,0)
    b=p['buyer'];need(isinstance(b,dict) and {'name','code','fc'}<=set(b)<={'name','code','fc','av'},'Thông tin khách không hợp lệ.')
    e.clean_text(b['name'],80);e.clean_text(b['code'],64,0);e.clean_text(b['fc'],100,0)
    if 'av' in b:e.clean_text(b['av'],80,0)


def _initialize(s,c,cid,t):
    e=_engine()
    if cid=='milk_tea':e.life.setup_task(s,c,t)
    mod=e.PLUGINS.get(cid)
    if mod and hasattr(mod,'on_task'):mod.on_task(s,c,t)
    if cid=='customer_care':e._cs_task_hook(c,t)


def _candidate(s,cid):
    e=_engine();c=s.get('careers',{}).get(cid)
    if c is None or s.get('current')!=cid or e.more_gate(c,cid) or e.pm.managing(s,c,cid):return None
    for slot in range(e._next_slot(c),e.MORE_DAY):
        t=e.make_task(cid,c['day'],slot,c['turn'])
        if t.get('kind') in ('setup','prep') or t.get('needs',{}).get('setup'):continue
        # Bookings create later NPC room payments outside the task command.
        # Other authored homestay services remain playable without that source.
        if cid=='homestay' and t.get('job')=='booking':continue
        _initialize(s,c,cid,t)
        return t
    return None


def _offer(t):
    from .workplace_business import ORDERS
    price=t.get('quoted_price')
    if type(price) is not int or price<1:price=ORDERS[t['career']][1]
    price=max(1,min(1000000,price))
    # Exclude progress counters from the quote; authored facts and initialized
    # recipe/price still bind the offer when the seller takes another action.
    facts={k:v for k,v in t.items() if k not in ('created_turn','patience')}
    digest=hashlib.sha256(json.dumps([facts,price],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    return dict(offer_id=t['id']+':'+digest[:24],digest=digest,career=t['career'],
                day=t['day'],slot=int(t['id'].rsplit('-',1)[1]),price=price,label=t['title'],
                description='Thực hiện đúng phiếu dịch vụ này. Ghi chú để trao đổi, không thay đổi dữ kiện của phiếu.')


def offers(state,cid):
    """One next authored service, projected without exposing minigame answers."""
    from .jsoncopy import tree_copy
    c=state.get('careers',{}).get(cid)
    if c is None:return []
    # Task initializers own only this career; promotion eligibility reads journey.
    # Never traverse all other careers just to quote one service.
    shadow=dict(current=state.get('current'),careers={cid:tree_copy(c)},
                journey=tree_copy(state.get('journey',{})))
    task=_candidate(shadow,cid)
    rows=[_offer(task)] if task else []
    offer=_staff_offer(shadow,cid)
    if offer:rows.append(offer)
    return rows


def accept(state,cid,order):
    """Append inside the order service's fresh transaction; do not select or pay."""
    e=_engine();available=offers(state,cid)
    e.need(available,'Nơi làm việc chưa thể nhận thêm đơn.','service_unavailable')
    offer=next((o for o in available if o['offer_id']==order.get('offer_id')),available[0]) if isinstance(order,dict) else available[0]
    e.need(isinstance(order,dict) and order.get('offer_id')==offer['offer_id'] and
           type(order.get('price')) is int and order['price']==offer['price'],'Phiếu dịch vụ đã thay đổi. Xem lại trước khi đặt.','stale_offer')
    if order.get('digest') is not None:e.need(order['digest']==offer['digest'],'Phiếu dịch vụ đã thay đổi.','stale_offer')
    meta=dict(v=1,id=order.get('id'),buyer=copy.deepcopy(order.get('buyer')),note=order.get('note',''),price=offer['price'])
    validate({'player_order':meta})
    if offer.get('staffed'):return _accept_staff(state,cid,meta,offer)
    e.need(not any(t.get('player_order',{}).get('id')==meta['id'] for c in state['careers'].values() for t in c['tasks']),
           'Đơn khách này đã được nhận.','duplicate_order')
    c=state['careers'][cid];t=e.make_task(cid,c['day'],offer['slot'],c['turn'])
    _initialize(state,c,cid,t);t['player_order']=meta;c['tasks'].append(t)
    return t['id']


@contextmanager
def command(state,cid,action,payload):
    """Scope incidental NPC tips to the actual task command; always unwind."""
    cid=cid or state.get('current');c=state.get('careers',{}).get(cid,{})
    p=payload if isinstance(payload,dict) else {}
    tid=p.get('task') or c.get('active_task')
    t=next((t for t in c.get('tasks',[]) if t['id']==tid),None)
    active=bool(t and t.get('player_order') and action not in _GLOBAL and not action.startswith(_GLOBAL_PREFIXES))
    token=_COMMAND.set((cid,tid) if active else None)
    try:yield
    finally:_COMMAND.reset(token)


def suppress_money(c,amount,ref):
    if amount<=0:return False
    referenced=next((t for t in c.get('tasks',[]) if t['id']==ref),None)
    if referenced is not None:return bool(referenced.get('player_order'))
    scope=_COMMAND.get()
    return bool(scope and any(t['id']==scope[1] and t['career']==scope[0] and t.get('player_order') for t in c.get('tasks',[])))


def complete(s,c,t,narrative):
    """The minigame finished. Only the database service can pay the real order."""
    e=_engine()
    e.log(s,c,'player_service',f"Đã xử lý đơn của {t['player_order']['buyer']['name']}: {t['title']}. Chờ biên nhận giao dịch.",ref=t['id'])
    e.next_active(c)


def project(t,view):
    if t.get('player_order'):
        view['player_order']=copy.deepcopy(t['player_order'])
        view['customer_name']=t['player_order']['buyer']['name']
        view['customer_note']=t['player_order']['note']
    return view


def transitions(before,after,career=None,action='',result=None):
    """Reducer transitions only; imports are never proof of performed service."""
    if action=='import_save':return []
    old={t['player_order']['id']:t for c in before.get('careers',{}).values() for t in c.get('tasks',[]) if t.get('player_order')}
    new={t['player_order']['id']:t for c in after.get('careers',{}).values() for t in c.get('tasks',[]) if t.get('player_order')}
    out=[]
    for oid,t in old.items():
        if t['status'] in DONE:continue
        n=new.get(oid)
        if n and n['id']==t['id'] and n['career']==t['career'] and n['status'] in DONE:
            status='cancelled' if n['status']=='completed' and n.get('reaction',{}).get('kind') in ('refuse','walkout') else n['status']
            out.append(dict(id=oid,status=status))
        elif n is None and action=='reset_career':out.append(dict(id=oid,status='cancelled'))
    previous={r['id']:r for st in before.get('journey',{}).get('quay',{}).get('stalls',[]) for r in st.get('business',{}).get('visitor_orders',[])}
    current={r['id']:r for st in after.get('journey',{}).get('quay',{}).get('stalls',[]) for r in st.get('business',{}).get('visitor_orders',[])}
    for oid,r in previous.items():
        if r['status']!='queued':continue
        n=current.get(oid)
        if n and n['status'] in DONE:out.append(dict(id=oid,status=n['status']))
        elif n is None and action in ('jr_quay_sell','reset_career'):out.append(dict(id=oid,status='cancelled'))
    old_staff={r['id']:r for c in before.get('careers',{}).values() for r in c.get('player_service_jobs',[])}
    new_staff={r['id']:r for c in after.get('careers',{}).values() for r in c.get('player_service_jobs',[])}
    for oid,r in old_staff.items():
        if r['status']!='queued':continue
        n=new_staff.get(oid)
        if n and n['status'] in DONE:out.append(dict(id=oid,status=n['status']))
        elif n is None and action=='reset_career':out.append(dict(id=oid,status='cancelled'))
    return out


def _staff_offer(s,cid):
    from . import workplace_business as wb
    c=s.get('careers',{}).get(cid)
    if not c or not c.get('started') or 'ops' not in c:return None
    b=c['ops'].get('business',{})
    employees=[e for e in wb._eligible(c) if not wb._blocked(c,cid,e,b or {'served':0},visitor=True)]
    if not employees or sum(not r.get('settled',False) for r in c.get('player_service_jobs',[]))>=8:return None
    label,price,_,inputs=wb.ORDERS[cid]
    digest=hashlib.sha256(json.dumps([cid,label,price,inputs],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return dict(offer_id='staff:'+cid+':'+digest[:24],digest=digest,career=cid,price=price,
                label=label,staffed=True,description='Nhân viên thực hiện đúng dịch vụ này bằng vật tư của nơi làm việc.')


def staff_offers(state,cid):
    """Read-only staff catalog while assigned staff work, even after owner close."""
    offer=_staff_offer(state,cid)
    return [offer] if offer else []


def _accept_staff(s,cid,meta,offer):
    from . import workplace_business as wb,operations as ops
    e=_engine();c=s['careers'][cid];now=wb._now();rows=c.get('player_service_jobs',[])
    wb.prepare(c,now)
    e.need(not any(r['id']==meta['id'] for r in rows),'Đơn này đã được nhận.','duplicate_order')
    b=c['ops'].get('business',{})
    workers=[x for x in wb._eligible(c) if not wb._blocked(c,cid,x,b or {'served':0},visitor=True)]
    e.need(workers,'Nhân viên chưa thể nhận đơn.','service_unavailable')
    worker=min(workers,key=lambda x:x['id']);label,_,supplies,inputs=wb.ORDERS[cid]
    from .staff_life import wage as effective_wage
    wage=math.ceil(effective_wage(c['ops'],worker)/4);goods=wb._take_stock(c,cid,inputs)
    for amount,category,text in ((wage,'wage','Lương đơn khách người chơi'),(supplies,'materials','Vật tư đơn khách người chơi')):
        c['money']-=amount;c['costs']+=amount;ops.record_money(c,-amount,text,meta['id'],category)
    row=dict(meta,career=cid,label=label,staff=worker['id'],status='queued',accepted_at=now,
             due_at=now+wb._seconds(c,worker),seconds=wb._seconds(c,worker),completed_at=None,
             inputs=dict(inputs),wage=wage,materials=supplies,goods=goods,quality=None,
             precision=worker['precision'],morale=worker['morale'],settled=False)
    c['player_service_jobs']=[r for r in rows if not r.get('settled',False)]+[row]
    wb.refresh(c,cid,now)
    return row['id']


def staff_due(c,now):
    from . import operations as ops
    for r in c.get('player_service_jobs',[]):
        if r['status']!='queued':continue
        worker=next((x for x in c.get('ops',{}).get('staff',[]) if x['id']==r['staff'] and x['status']=='hired'),None)
        if worker is None:return True
        working=worker['on_shift'] and not ops.paused(c['ops'],worker) and worker['rest_until']<=c['turn'] and not worker.get('strike',False)
        if working and (r['due_at'] is None or r['due_at']<=now):return True
        if not working and r['due_at'] is not None:return True
    return False


def staff_working(c):
    from . import operations as ops
    for r in c.get('player_service_jobs',[]):
        if r['status']!='queued':continue
        worker=next((x for x in c.get('ops',{}).get('staff',[]) if x['id']==r['staff'] and x['status']=='hired'),None)
        if worker and worker['on_shift'] and not ops.paused(c['ops'],worker) and worker['rest_until']<=c['turn'] and not worker.get('strike',False):return True
    return False


def settle_staff(c,cid,now):
    from . import operations as ops, workplace_business as wb
    changed=wb.prepare(c,now)
    for r in c.get('player_service_jobs',[]):
        if r['status']!='queued':continue
        worker=next((x for x in c.get('ops',{}).get('staff',[]) if x['id']==r['staff'] and x['status']=='hired'),None)
        if worker is None:
            r.update(status='cancelled',completed_at=now,due_at=None);changed=True;continue
        working=worker['on_shift'] and not ops.paused(c['ops'],worker) and worker['rest_until']<=c['turn'] and not worker.get('strike',False)
        if not working:
            if r['due_at'] is not None:r['due_at']=None;changed=True
            continue
        if r['due_at'] is None:r['due_at']=now+r['seconds'];changed=True;continue
        if r['due_at']>now:continue
        roll=int.from_bytes(hashlib.sha256(r['id'].encode()).digest()[:4],'big')%100
        quality=max(1,min(5,3+(r['precision']>=80)+(r['morale']>=75)-(roll>=r['precision'])))
        r.update(status='completed',completed_at=r['due_at'],quality=quality)
        worker['jobs']=min(10**9,worker['jobs']+1)
        worker['last_work']=r['label']+' · đơn khách '+r['buyer']['name']+' · chờ thanh toán theo biên nhận.'
        changed=True
    return changed



def credit_staff_bonus(state,cid,order_id,price):
    """Only the escrow payment transaction may reward a fulfilled staff order."""
    from . import workplace_business as wb
    c=state['careers'][cid]
    row=next((r for r in c.get('player_service_jobs',[]) if r['id']==order_id),None)
    if row is None or row['settled']:return 0
    _engine().need(row['status']=='completed' and row['price']==price,'Biên nhận giao hàng chưa khớp.','invalid_order')
    wb.prepare(c,wb._now())
    return wb.credit_profit_bonus(c,price-row['wage']-row['materials']-row['goods'],order_id,row['label'],visitor=True)


def validate_staff(c,cid):
    e=_engine();rows=c.get('player_service_jobs',[])
    e.need(isinstance(rows,list) and len(rows)<=8,'Sổ đơn khách nhân viên không hợp lệ.')
    from .workplace_business import ORDERS
    seen=set()
    for r in rows:
        e.need(isinstance(r,dict) and set(r)=={'v','id','buyer','note','price','career','label','staff','status','accepted_at','due_at','seconds','completed_at','inputs','wage','materials','goods','quality','precision','morale','settled'},'Đơn khách nhân viên không hợp lệ.')
        e.need(type(r['settled']) is bool and (not r['settled'] or r['status']!='queued'),'Biên nhận thanh toán không hợp lệ.')
        validate({'player_order':{k:r[k] for k in ('v','id','buyer','note','price')}})
        e.need(r['id'] not in seen and r['career']==cid and r['status'] in ('queued','completed','cancelled'),'Đơn khách nhân viên không hợp lệ.')
        seen.add(r['id']);e.clean_text(r['staff'],100)
        e.need(r['label']==ORDERS[cid][0] and r['inputs']==ORDERS[cid][3],'Vật tư dịch vụ không hợp lệ.')
        for k in ('accepted_at','due_at','completed_at'):
            if r[k] is not None:e.integer(r[k],0,10**11)
        e.integer(r['seconds'],15,100000)
        for k in ('wage','materials','goods'):e.integer(r[k],0,10**9)
        for k in ('precision','morale'):e.integer(r[k],0,100)
        if r['quality'] is not None:e.integer(r['quality'],1,5)
        e.need((r['status']=='queued')==(r['completed_at'] is None),'Biên nhận đơn nhân viên không hợp lệ.')


def credit_visit(state,stall_id,order_id,price):
    """Book the real escrow transfer once, after the database claims this order."""
    from . import quay as qy,quay_business as qb
    e=_engine();e.integer(price,1,1000000);qb.settle(state)
    st=qy.stall(state,stall_id);b=st['business']
    row=next((r for r in b.get('visitor_orders',[]) if r['id']==order_id),None)
    e.need(row is None or row['status']=='completed' and row['price']==price and not row['settled'],'Biên nhận giao món chưa khớp.','invalid_order')
    # The durable order status is the exactly-once guard. This function is only
    # called by the transaction committing that status and the actual escrow.
    e.need(st['till']+price<=qy.MONEY_MAX,'Két đã đầy. Thu tiền rồi nhận thanh toán nhé.','till_full')
    st['till']+=price;b['revenue']+=price;b['sold']+=1
    qb.collect_fines(st)
    costs=qb.unit_cost(st,row['dish']) if row is not None else 0
    paid_tax=qb.charge_income_tax(st,price,costs)
    qy._log(st,state['journey']['life_day'],'Khách người chơi thanh toán đơn '+order_id,price)
    if row is not None:
        qb.reward_margin(st,price,costs+paid_tax)
        row['settled']=True
    return price-paid_tax


def acknowledge(state,order_id,outcome=None):
    """Order-service-only acknowledgement after atomic payment or refund."""
    from . import workplace_business as wb
    now=wb._now(None)
    for c in state.get('careers',{}).values():
        for r in c.get('player_service_jobs',[]):
            if r['id']!=order_id or r.get('settled'):continue
            if outcome=='cancelled' and r['status']=='queued':
                # Materials and wages paid at acceptance are already spent.
                r.update(status='cancelled',completed_at=max(now,r['accepted_at']),due_at=None)
            if r['status'] in DONE:r['settled']=True
        if outcome=='cancelled':
            for t in c.get('tasks',[]):
                if t.get('player_order',{}).get('id')==order_id and t['status'] not in DONE:
                    from . import abandon
                    abandon._cancel(state,c,t)
                    if c.get('active_task')==t['id']:_engine().next_active(c)
    for st in state.get('journey',{}).get('quay',{}).get('stalls',[]):
        b=st.get('business',{})
        for r in b.get('visitor_orders',[]):
            if r['id']!=order_id or r.get('settled'):continue
            if outcome=='cancelled' and r['status']=='queued':
                b['stock'][r['dish']]=b['stock'].get(r['dish'],0)+1
                r.update(status='cancelled',completed_at=max(now*1000,r['accepted_at']),due_at=None)
            if r['status'] in DONE:r['settled']=True


def scrub_import(state):
    """Imported saves cannot recreate claims on database-held customer money.

    Keep canonical task progress and saved money/stock; imported reservations
    carry no authority to refund goods or revive an already cancelled order.
    """
    changed=False
    for c in state.get('careers',{}).values():
        if not isinstance(c,dict):continue
        if 'player_service_jobs' in c:del c['player_service_jobs'];changed=True
        tasks=c.get('tasks',[])
        if isinstance(tasks,list):
            for t in tasks:
                if isinstance(t,dict) and 'player_order' in t:del t['player_order'];changed=True
    for st in state.get('journey',{}).get('quay',{}).get('stalls',[]):
        if not isinstance(st,dict):continue
        b=st.get('business',{})
        if isinstance(b,dict) and 'visitor_orders' in b:del b['visitor_orders'];changed=True
    return changed


def _visit_open(st):
    return not (st.get('due') or st.get('business',{}).get('paused') or st.get('economy',{}).get('paused'))


def _visit_fulfillable(st):
    # Closing stops new business, while accepted quotes/reserved stock survive.
    return not (st.get('due') or st.get('economy',{}).get('paused'))


def reserved(st):
    return sum(r['status']=='queued' for r in st.get('business',{}).get('visitor_orders',[]))


def _visit_duration(st):
    return max(5000,round(30000/st['business'].get('speed_factor',1)))


def can_accept_visit(st):
    """An NPC needs existing local funds through the new order's prep time."""
    if not _visit_open(st):return False
    if not st['staff']:return True
    from . import quay_business as qb
    b=st.get('business',{});cash=st['fund']+st['till']
    if cash<=1 or b.get('halted',-1)==cash:return False
    cursor=b.get('cursor',0);tail=cursor
    for row in b.get('visitor_orders',[]):
        if row['status']=='queued':tail=max(tail+_visit_duration(st),row.get('due_at') or cursor)
    elapsed=tail+_visit_duration(st)-cursor
    # Directory snapshots can precede the owner's first post-upgrade settlement.
    cost=sum((b.get('carry',{}).get(k,0)+elapsed*rate)//qb.DEN for k,rate in qb._rates(st).items())
    return cost<=cash-1


def accept_visit(state,stall_id,order,now=None):
    """Reserve one purchased menu item. No NPC sale or customer payment occurs."""
    from . import quay as qy,quay_self as qs,quay_business as qb
    e=_engine();qb.settle(state,now=now);st=qy.stall(state,stall_id);b=st['business'];at=b['cursor']
    e.need(_visit_open(st),'Quầy đang tạm dừng.','service_unavailable')
    e.need(can_accept_visit(st),'Quỹ quầy chưa đủ trả chi phí nhân viên cho đơn này.','service_unavailable')
    e.need(isinstance(order,dict),'Đơn quầy không hợp lệ.')
    dish=order.get('offer_id')
    e.need(isinstance(dish,str) and dish in qs.menu(st)['on'] and order.get('items')==[dish], 'Chọn một món đang bán.')
    e.need(type(order.get('price')) is int and order['price']==qs.price(st,dish),'Giá món đã thay đổi.','stale_offer')
    meta=dict(v=1,id=order.get('id'),buyer=copy.deepcopy(order.get('buyer')),note=order.get('note',''),price=order['price'])
    validate({'player_order':meta})
    rows=b.setdefault('visitor_orders',[])
    e.need(not any(r['id']==meta['id'] for r in rows),'Đơn này đã được nhận.','duplicate_order')
    e.need(sum(not r.get('settled',False) for r in rows)<8,'Quầy đang có đủ đơn khách chờ biên nhận.','service_unavailable')
    e.need(b['stock'].get(dish,0)>=1,'Món này vừa hết hàng.','sold_out')
    b['stock'][dish]-=1
    tail=max([at]+[r['due_at'] for r in rows if r['status']=='queued' and r['due_at'] is not None])
    row=dict(meta,dish=dish,status='queued',accepted_at=at,due_at=tail+_visit_duration(st) if st['staff'] else None,
             completed_at=None,quality=None,staffed=bool(st['staff']),settled=False)
    b['visitor_orders']=[r for r in rows if not r.get('settled',False)]+[row]
    return row['id']


def serve_visit(st,p):
    """The same item/change/courtesy checks as the owner's normal counter."""
    e=_engine();e.need(set(p)<={'stall','visitor_id','items','change','smile'},'Thông tin phục vụ không hợp lệ.')
    e.need(_visit_fulfillable(st),'Xử lý tình trạng quầy trước khi phục vụ.','closed')
    row=next((r for r in st.get('business',{}).get('visitor_orders',[]) if r['id']==p.get('visitor_id')),None)
    e.need(row and row['status']=='queued','Đơn khách không còn chờ.','already_completed')
    e.need(p.get('items')==[row['dish']],'Khách đặt món khác. Chọn đúng món đã giữ cho đơn nhé.')
    e.need(type(p.get('change')) is int and p['change']==0,'Đơn khách đã giữ đúng số tiền; không cần thối thêm.')
    e.need(type(p.get('smile')) is bool,'Chọn cách chào khách.')
    row.update(status='completed',completed_at=st['business']['cursor'],quality=5 if p['smile'] else 4,staffed=False)
    return dict(message='Đã giao đúng món cho '+row['buyer']['name']+'. Thanh toán được ghi trên biên nhận của đơn.',visitor_order=row['id'])


def visit_due(st,at):
    b=st.get('business',{})
    return bool(st['staff'] and _visit_fulfillable(st) and st['fund']+st['till']>1 and
                b.get('halted',-1)!=st['fund']+st['till'] and reserved(st) and at>b.get('cursor',at))


def settle_visits(st,at):
    """Return cursor/blocked/changed; actual prep occupies the NPC counter.

    The caller then settles ordinary NPC customers from the returned cursor,
    so elapsed wages/rent/power are charged once, never once per income source.
    """
    from . import quay_business as qb
    b=st['business'];cursor=b['cursor'];changed=False
    rows=[r for r in b.get('visitor_orders',[]) if r['status']=='queued']
    if not rows:return cursor,False,False
    if not st['staff'] or not _visit_fulfillable(st):
        for r in rows:
            if r['due_at'] is not None:r['due_at']=None;changed=True
        return cursor,False,changed
    if st['fund']+st['till']<1 or b.get('halted',-1)==st['fund']+st['till']:
        for r in rows:
            if r['due_at'] is not None:r['due_at']=None;changed=True
        return at,True,changed
    for row in rows:
        if row['due_at'] is None:
            # A paused/unstaffed interval is never performed retroactively.
            row['due_at']=at+_visit_duration(st);row['staffed']=True
            return at,True,True
        end=min(at,max(cursor,row['due_at']))
        if not qb._charge(st,max(0,end-cursor)) or b.get('halted')==st['fund']+st['till']:
            for r in rows:r['due_at']=None
            return at,True,True
        cursor=end;changed=changed or cursor>b['cursor']
        if row['due_at']>at:return cursor,True,changed
        quality=max(1,min(5,1+sum(x.get('mo',60) for x in st['staff'])//max(1,len(st['staff']))//25))
        row.update(status='completed',completed_at=cursor,quality=quality,staffed=True);changed=True
    return cursor,False,changed


def validate_visits(st):
    e=_engine();rows=st.get('business',{}).get('visitor_orders',[])
    e.need(isinstance(rows,list) and len(rows)<=8,'Hàng đợi khách quầy không hợp lệ.')
    ids=set()
    from .quay_self import DISH
    for r in rows:
        e.need(isinstance(r,dict) and set(r)=={'v','id','buyer','note','price','dish','status','accepted_at','due_at','completed_at','quality','staffed','settled'},'Đơn khách quầy không hợp lệ.')
        e.need(type(r['settled']) is bool and (not r['settled'] or r['status']!='queued'),'Biên nhận thanh toán không hợp lệ.')
        validate({'player_order':{k:r[k] for k in ('v','id','buyer','note','price')}})
        e.need(r['id'] not in ids and r['dish'] in DISH[st['trade']] and r['status'] in ('queued','completed','cancelled'),'Đơn khách quầy không hợp lệ.')
        ids.add(r['id']);e.integer(r['accepted_at'],0,10**15)
        for k in ('due_at','completed_at'):
            if r[k] is not None:e.integer(r[k],0,10**15)
        if r['quality'] is not None:e.integer(r['quality'],1,5)
        e.need(type(r['staffed']) is bool,'Nhân viên phục vụ không hợp lệ.')
        e.need((r['status']=='queued')==(r['completed_at'] is None),'Biên nhận giao món không hợp lệ.')
    from .quay_business import STOCK_MAX
    e.need(sum(st['business']['stock'].values())+reserved(st)<=STOCK_MAX,'Kho quầy vượt sức chứa.')


def public_visits(st):
    rows=copy.deepcopy(st.get('business',{}).get('visitor_orders',[]))
    for r in rows:
        for k in ('accepted_at','due_at','completed_at'):
            if r[k] is not None:r[k]/=1000
    return rows
