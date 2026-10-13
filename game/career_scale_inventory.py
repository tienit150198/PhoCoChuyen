"""Bulk contract consumables, preserving physical units and paid storage rights.

A storage carton contains twenty supplier packs. All locations share the same
per-SKU capacity; transit and reservations occupy it. These authored contract
SKUs are distinct from legacy shop goods, which are never silently converted.
"""
from __future__ import annotations

import copy
import re

from . import capacity_progression as capacity, order_progression as ordering
from .career_scale_content import profile

KEY = 'scale_stock'
ACTIONS = frozenset(('scale_stock_buy', 'scale_stock_receive', 'scale_stock_move'))
MAX = 10**9
MAX_ROWS = 400
PACKS_PER_CARTON = 20
JOB = re.compile(r'[a-z_]+-[1-9][0-9]{0,11}')


def _need(ok, message='Dữ liệu vật tư hợp đồng không hợp lệ.'):
    from .engine import need
    need(ok, message)


def _int(x, lo=0, hi=MAX):
    _need(type(x) is int and lo <= x <= hi)
    return x


def material(cid, code):
    _need(type(code) is str)
    row = next((m for m in profile(cid).materials if m.code == code), None)
    _need(row is not None, 'Không có vật tư hợp đồng này.')
    return row


def _record(c):
    return c.get(KEY) or dict(v=1, seq=0, lots=[], orders=[])


def _site(c, site):
    _need(type(site) is str and any(x['id'] == site for x in c.get('scale', {}).get('sites', ())),
          'Cơ sở này chưa được mở.')
    return site


def units(c, code, site=None, available=False):
    return sum(lot['units'] - (sum(lot['reserved'].values()) if available else 0)
               for lot in _record(c)['lots'] if lot['code'] == code and (site is None or lot['site'] == site))


def space(c, cid, code):
    m = material(cid, code)
    size = m.batch_units * PACKS_PER_CARTON
    held = units(c, code) + sum(o['units'] for o in _record(c)['orders'] if o['code'] == code and not o['received'])
    cap = capacity.limit(c, cid, 80)
    return dict(capacity=cap, occupied=(held+size-1)//size, room=max(0, (cap*size-held)//size),
                units=held, carton_units=size, order=ordering.limit(c, cid))


def reserve(c, cid, job, site, code, amount):
    _need(type(job) is str and JOB.fullmatch(job) is not None)
    _site(c, site); material(cid, code); _int(amount, 1)
    _need(units(c, code, site, True) >= amount, 'Chưa đủ vật tư tự do tại cơ sở này.')
    left = amount
    for lot in _record(c)['lots']:
        if lot['code'] != code or lot['site'] != site:
            continue
        take = min(left, lot['units']-sum(lot['reserved'].values()))
        if take:
            lot['reserved'][job] = lot['reserved'].get(job, 0) + take
            left -= take
        if not left:
            break


def held(c, job, code=None):
    return sum(lot['reserved'].get(job, 0) for lot in _record(c)['lots'] if code is None or lot['code'] == code)


def release(c, job):
    for lot in _record(c)['lots']:
        lot['reserved'].pop(job, None)


def held_cost(c, job):
    return sum(lot['reserved'].get(job,0)*lot['unit_cost'] for lot in _record(c)['lots'])


def consume(c, job):
    r = _record(c)
    total = cost = 0
    for lot in r['lots']:
        take = lot['reserved'].pop(job, 0)
        lot['units'] -= take
        total += take
        cost += take * lot['unit_cost']
    r['lots'][:] = [lot for lot in r['lots'] if lot['units']]
    return dict(units=total, cost=cost)


def action(s, c, cid, name, p):
    from .career_scale_finance import move
    _need(profile(cid).kind == 'business', 'Vật tư công vụ được cấp hiện vật trong ca.')
    _need(c.get('scale', {}).get('tier', 0) > 0, 'Mở quy mô đầu tiên trước khi đặt vật tư hợp đồng.')
    _need(type(p) is dict and name in ACTIONS)
    r = copy.deepcopy(_record(c))
    _need(r['seq'] < MAX)
    if name == 'scale_stock_buy':
        _need(set(p) == {'site', 'code', 'quantity'})
        site = _site(c, p['site']); m = material(cid, p['code'])
        qty = _int(p['quantity'], 1, ordering.limit(c, cid))
        room = space(c, cid, m.code)
        _need(qty <= room['room'], 'Kho đã tính cả hàng đang về và hàng giữ cho hợp đồng. Cần nâng sức chứa hoặc dùng bớt hàng.')
        _need(sum(not x['received'] for x in r['orders']) < 12, 'Nhận các kiện đang về trước khi đặt tiếp.')
        quantity = qty * room['carton_units']; price = quantity * m.unit_cost
        _int(price, 1)
        _need(c['money'] >= price, 'Quỹ nghề chưa đủ tiền nhập. Góp vốn vào nghề trước nhé.')
        r['seq'] += 1
        oid = f"supply-{r['seq']}"
        move(s, c, -price, f'Nhập vật tư hợp đồng: {m.name}', oid, category='scale_stock')
        r['orders'] = [o for o in r['orders'] if not o['received']] + [o for o in r['orders'] if o['received']][-30:]
        r['orders'].append(dict(id=oid, code=m.code, site=site, quantity=qty, units=quantity,
                                unit_cost=m.unit_cost, cost=price, received=False))
        c[KEY] = r
        return dict(message=f'Đã trả {price:,} xu. Kiểm đếm để nhận {qty} thùng vào kho.', order=oid, quantity=qty)
    if name == 'scale_stock_receive':
        _need(set(p) == {'order', 'count'})
        row = next((o for o in r['orders'] if o['id'] == p['order']), None)
        _need(row is not None and not row['received'], 'Kiện này đã nhận hoặc không còn trong đơn đang về.')
        _int(p['count'], 1, 4000)
        _need(p['count'] == row['quantity'], 'Số thùng chưa khớp phiếu giao. Kiểm đếm lại trước khi nhận nhé.')
        _need(len(r['lots']) < MAX_ROWS, 'Dùng bớt các lô nhỏ trước khi nhận thêm hàng.')
        r['seq'] += 1
        r['lots'].append(dict(id=f"lot-{r['seq']}", code=row['code'], site=row['site'], units=row['units'],
                              unit_cost=row['unit_cost'], reserved={}))
        row['received'] = True
        c[KEY] = r
        return dict(message='Đã kiểm đếm và nhận vật tư theo đúng giá vốn trên phiếu.')
    _need(set(p) == {'source', 'site', 'code', 'units'})
    source = _site(c, p['source']); target = _site(c, p['site']); material(cid, p['code'])
    _need(source != target, 'Chọn hai cơ sở khác nhau.')
    amount = _int(p['units'], 1)
    _need(units(c, p['code'], source, True) >= amount, 'Không thể chuyển hàng đã giữ cho hợp đồng hoặc vượt tồn tự do.')
    left = amount
    incoming = []
    for lot in r['lots']:
        if lot['site'] != source or lot['code'] != p['code']:
            continue
        take = min(left, lot['units']-sum(lot['reserved'].values()))
        if take:
            r['seq'] += 1
            incoming.append(dict(id=f"lot-{r['seq']}", code=lot['code'], site=target,
                                 units=take, unit_cost=lot['unit_cost'], reserved={}))
            lot['units'] -= take
            left -= take
        if not left:
            break
    r['lots'] = [lot for lot in r['lots'] if lot['units']] + incoming
    _need(len(r['lots'])<=MAX_ROWS, 'Dùng bớt lô vật tư trước khi điều chuyển thêm.')
    c[KEY] = r
    from .engine import log
    log(s,c,'stock',f'Điều chuyển {amount:,} {material(cid,p["code"]).unit}: {source} → {target}; giá vốn {sum(x["units"]*x["unit_cost"] for x in incoming):,} xu')
    return dict(message='Đã chuyển vật tư giữa hai cơ sở, giữ nguyên số lượng và giá vốn.')


def public(c, cid):
    if profile(cid).kind != 'business' or not c.get('scale', {}).get('tier'):
        return dict(items=[], actions=[])
    r = _record(c); sites = c['scale']['sites']
    options = [dict(value=s['id'], label=s['name']) for s in sites]
    actions = []
    items = []
    for m in profile(cid).materials:
        room = space(c, cid, m.code)
        items.append(dict(code=m.code, name=m.name, unit=m.unit, **room,
                          locations=[dict(site=s['id'], name=s['name'], units=units(c,m.code,s['id']),
                                          available=units(c,m.code,s['id'],True)) for s in sites]))
        actions.append(dict(command='scale_stock_buy', label=f'Đặt {m.name}', payload=dict(code=m.code),
            fields=[dict(name='site',label='Nhận tại',options=options,value='base'),
                    dict(name='quantity',label=f"Số thùng · {room['carton_units']:,} {m.unit}/thùng · {room['carton_units']*m.unit_cost:,} xu/thùng",
                         type='number',min=1,max=min(room['order'],room['room']),value=1)],
            disabled=room['room']<=0,reason=f"Còn {room['room']} thùng trống / {room['capacity']}; mỗi lần tối đa {room['order']} thùng."))
        if len(sites)>1:
            actions.append(dict(command='scale_stock_move',label=f'Chuyển {m.name}',payload=dict(code=m.code),
                fields=[dict(name='source',label='Từ cơ sở',options=options,value='base'),
                        dict(name='site',label='Đến cơ sở',options=options,value=sites[1]['id']),
                        dict(name='units',label=f'Số {m.unit}',type='number',min=1,max=MAX,value=1)],primary=False))
    for o in r['orders']:
        if not o['received']:
            actions.insert(0,dict(command='scale_stock_receive',label=f"Kiểm đếm kiện {o['id']}",payload=dict(order=o['id']),
                fields=[dict(name='count',label=f"Phiếu giao: {o['quantity']} thùng",type='number',min=1,max=4000,value=1)]))
    return dict(items=items,actions=actions)


def validate(c, cid):
    if KEY not in c:
        return
    r = c[KEY]
    _need(profile(cid).kind == 'business' and type(r) is dict and set(r) == {'v','seq','lots','orders'})
    _need(type(r['v']) is int and r['v'] == 1); _int(r['seq'])
    _need(type(r['lots']) is list and len(r['lots']) <= MAX_ROWS)
    _need(type(r['orders']) is list and len(r['orders']) <= 43)
    ids = set()
    for lot in r['lots']:
        _need(type(lot) is dict and set(lot) == {'id','code','site','units','unit_cost','reserved'})
        _need(type(lot['id']) is str and re.fullmatch(r'lot-[1-9][0-9]{0,11}',lot['id']) is not None and lot['id'] not in ids)
        ids.add(lot['id']); material(cid,lot['code']); _site(c,lot['site'])
        _int(lot['units'],1); _int(lot['unit_cost'],1)
        _need(type(lot['reserved']) is dict and len(lot['reserved']) <= 12)
        for job, amount in lot['reserved'].items():
            _need(type(job) is str and JOB.fullmatch(job) is not None); _int(amount,1)
        _need(sum(lot['reserved'].values()) <= lot['units'])
    for o in r['orders']:
        _need(type(o) is dict and set(o) == {'id','code','site','quantity','units','unit_cost','cost','received'})
        _need(type(o['id']) is str and re.fullmatch(r'supply-[1-9][0-9]{0,11}',o['id']) is not None and o['id'] not in ids)
        ids.add(o['id']);m=material(cid,o['code']);_site(c,o['site'])
        _int(o['quantity'],1,4000);_int(o['units'],1);_int(o['unit_cost'],1);_int(o['cost'],1)
        _need(o['units']==o['quantity']*m.batch_units*PACKS_PER_CARTON and o['cost']==o['units']*o['unit_cost'] and type(o['received']) is bool)
