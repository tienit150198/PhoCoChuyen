"""Paid specialist input bundles, transit and FIFO; separate from legacy goods."""
import copy
from . import capacity_progression, order_progression
from .career_scale_finance import move
from .career_specialism_content import pack

KEY = 'special_stock'
ACTIONS = {'special_stock_buy','special_stock_receive'}


def need(ok, message='Dữ liệu kho chuyên môn không hợp lệ.'):
    from .engine import need as check
    check(ok,message)


def integer(n,lo=0,hi=10**9):
    need(type(n) is int and lo<=n<=hi)
    return n


def materials(cid,tier):
    return [dict(m,code=f'sp{tier}_{i}',bundle_cost=m['quantity']*m['unit_cost'])
            for i,m in enumerate(pack(cid,tier)['inputs'])]


def material(cid,code):
    need(type(code) is str)
    for tier in range(1,11):
        for m in materials(cid,tier):
            if m['code']==code:return m
    need(False,'Mã vật tư không thuộc nghề này.')


def record(c):
    return c.get(KEY) or dict(v=1,seq=0,lots=[],orders=[])


def limit(c,cid):
    return dict(capacity=capacity_progression.limit(c,cid,80),order=order_progression.limit(c,cid))


def units(c,code):
    return sum(x['quantity'] for x in record(c)['lots'] if x['code']==code)


def occupied(c,code):
    job=c.get('specialism',{}).get('job') or {}
    return (units(c,code)+sum(x['quantity'] for x in record(c)['orders'] if x['code']==code)
            +sum(x['quantity'] for x in job.get('held',[]) if x['code']==code))


def take(c,requirements):
    """Validate the full bill before removing anything. Held bundles still occupy storage."""
    need(all(units(c,x['code'])>=x['quantity'] for x in requirements),'Chưa nhận đủ vật tư cho đơn này.')
    r=record(c);held=[]
    for req in requirements:
        left=req['quantity']
        for lot in r['lots']:
            if lot['code']!=req['code']:continue
            n=min(left,lot['quantity'])
            if n:held.append(dict(code=lot['code'],quantity=n,unit_cost=lot['unit_cost']))
            lot['quantity']-=n;left-=n
            if not left:break
    r['lots'][:]=[x for x in r['lots'] if x['quantity']]
    return held


def action(s,c,cid,name,p):
    from .career_specialism_jobs import kind
    need(kind(cid)=='business','Đơn vị cấp vật tư hiện vật cho công việc này.')
    r=copy.deepcopy(record(c));rights=limit(c,cid)
    if name=='special_stock_buy':
        need(set(p)=={'code','quantity'})
        m=material(cid,p['code'])
        unlocked={x['code'] for t in range(1,c.get('specialism',{}).get('tier',0)+1) for x in materials(cid,t)}
        need(p['code'] in unlocked,'Học và đạt thực hành trước khi nhập mẫu/vật tư này.')
        qty=integer(p['quantity'],1,rights['order'])
        need(qty+occupied(c,m['code'])<=rights['capacity'],'Kho tính cả hàng đang về và đang dùng. Nâng kho hoặc dùng bớt hàng nhé.')
        need(len(r['orders'])<12 and r['seq']<10**9,'Nhận các kiện đang về trước khi đặt tiếp.')
        cost=integer(qty*m['bundle_cost'],1)
        need(c['money']>=cost,'Quỹ nghề chưa đủ tiền nhập vật tư.')
        r['seq']+=1;oid=f"special-supply-{r['seq']}"
        move(s,c,-cost,f"Nhập chuyên môn: {m['name']}",oid,category='scale_special_stock')
        r['orders'].append(dict(id=oid,code=m['code'],quantity=qty,unit_cost=m['bundle_cost']))
        c[KEY]=r
        return dict(message='Đã đặt vật tư. Kiểm đếm phiếu giao để nhận vào kho.',order=oid)
    need(name=='special_stock_receive' and set(p)=={'order','count'})
    need(type(p['order']) is str)
    o=next((x for x in r['orders'] if x['id']==p['order']),None)
    need(o is not None,'Kiện đã nhận hoặc mã kiện không đúng.')
    integer(p['count'],1,4000);need(p['count']==o['quantity'],'Số đếm chưa khớp phiếu giao.')
    need(len(r['lots'])<400,'Dùng bớt các lô trước khi nhận thêm.')
    r['lots'].append(dict(o));r['orders'].remove(o);c[KEY]=r
    return dict(message='Đã nhận và ghi giá vốn lô vật tư.')


def public(c,cid):
    from .career_specialism_jobs import kind
    if kind(cid)!='business':return None
    rights=limit(c,cid);items=[];actions=[]
    for tier in range(1,c.get('specialism',{}).get('tier',0)+1):
        for m in materials(cid,tier):
            used=occupied(c,m['code']);room=max(0,rights['capacity']-used)
            label=f"{m['name']} · {m['quantity']} {m['unit']}/bộ"
            items.append(dict(code=m['code'],name=label,unit='bộ vật tư',units=used,available=units(c,m['code']),unit_cost=m['bundle_cost'],**rights))
            actions.append(dict(command='special_stock_buy',label=f"Đặt {m['name']}",payload=dict(code=m['code']),
                fields=[dict(name='quantity',label=f"Số bộ · {m['bundle_cost']:,} xu/bộ",type='number',min=1,max=max(1,min(room,rights['order'])),value=1)],disabled=room<=0,reason=f'Còn {room} bộ trống.'))
    for o in record(c)['orders']:
        actions.insert(0,dict(command='special_stock_receive',label=f"Nhận {material(cid,o['code'])['name']}",payload=dict(order=o['id']),
            fields=[dict(name='count',label=f"Phiếu giao: {o['quantity']} bộ",type='number',min=1,max=4000,value=1)]))
    return dict(items=items,actions=actions)


def validate(c,cid):
    if KEY not in c:return
    from .career_specialism_jobs import kind
    r=c[KEY];need(kind(cid)=='business' and type(r) is dict and set(r)=={'v','seq','lots','orders'})
    need(type(r['v']) is int and r['v']==1);integer(r['seq'])
    need(type(r['lots']) is list and len(r['lots'])<=400 and type(r['orders']) is list and len(r['orders'])<=12)
    ids=set();allowed={m['code'] for t in range(1,c.get('specialism',{}).get('tier',0)+1) for m in materials(cid,t)}
    for row in r['lots']+r['orders']:
        need(type(row) is dict and set(row)=={'id','code','quantity','unit_cost'})
        need(type(row['id']) is str and row['id'].startswith('special-supply-'))
        tail=row['id'].removeprefix('special-supply-');need(tail.isascii() and tail.isdigit() and str(int(tail))==tail and 1<=int(tail)<=r['seq'])
        need(row['id'] not in ids and type(row['code']) is str and row['code'] in allowed);ids.add(row['id'])
        integer(row['quantity'],1,4000);integer(row['unit_cost'],1,100000)
    capacity=limit(c,cid)['capacity']
    need(all(occupied(c,code)<=capacity for code in allowed),'Vật tư vượt sức chứa kho đã mở.')
