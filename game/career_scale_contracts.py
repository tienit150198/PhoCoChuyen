"""Authoritative management contracts, explicit resource/stock commitments and receipts."""
from __future__ import annotations

import copy
import hashlib
import time

from . import career_scale_content as content, career_scale_quota as quota
from . import career_scale_inventory as stock, career_scale_resources as resources
from .career_scale_finance import move

KEY = 'scale_contracts'
ACTIONS = frozenset(('scale_offer','scale_plan','scale_allocate','scale_schedule','scale_start',
                     'scale_resolve','scale_accept','scale_settle','scale_cancel'))
PHASES = ('planning','stock','staffing','exception','acceptance')
OFFER_KEYS = {'id','tier','demand','resources','quote','phase','choices','allocated','scheduled',
              'incidents','acceptances','escrow','started','reserved','created'}


def _need(ok, message='Dữ liệu hợp đồng quản lý không hợp lệ.'):
    from .engine import need
    need(ok, message)


def _int(value, lo=0, hi=10**9):
    _need(type(value) is int and lo <= value <= hi)
    return value


def _record(c):
    return c.get(KEY) or dict(v=1, seq=0, offer=None, current=None, history=[])


def project_quote(cid, tier, demand, count, site_count=None):
    """Scale costs once by actual staffed capacity, never by branch count."""
    full = content.quote(cid, tier, demand)
    st = content.stage(cid,tier)
    total = st.resources
    _int(count,1,total)
    sites = st.sites if site_count is None else _int(site_count,1,st.sites)
    from fractions import Fraction
    fraction = min(Fraction(count,total),Fraction(sites,st.sites))
    q = {k:full[k]*fraction.numerator//fraction.denominator for k in ('revenue','materials','wage_variable','wage_fixed','premises','loss','tax')}
    q['wages'] = q['wage_variable'] + q['wage_fixed']
    q['cost_total'] = sum(q[k] for k in ('materials','wages','premises','loss','tax'))
    q['net'] = q['revenue'] - q['cost_total']
    q.update(tier=tier,demand=demand,resources=count,full_resources=total)
    return q


def _snapshots(c,cid):
    people={p['id']:p for p in c['scale']['crew']}
    return [dict(id=r['id'],site=r['site'],crew=r['crew'],role=people[r['crew']]['role'])
            for r in resources.available(c,cid)]


def requirements(c,cid,o):
    m=content.profile(cid).materials[0]
    total=o['quote']['materials']//m.unit_cost if content.profile(cid).kind=='business' else len(o['resources'])*m.batch_units
    sites=sorted({r['site'] for r in o['resources']})
    counts={site:sum(r['site']==site for r in o['resources']) for site in sites}
    amounts={site:total*counts[site]//len(o['resources']) for site in sites}
    amounts[sites[0]]+=total-sum(amounts.values())
    return [dict(site=site,code=m.code,units=amounts[site],name=m.name,unit=m.unit) for site in sites if amounts[site]]


def _choice(cid,phase,option):
    _need(type(option) is str)
    selected=next((x for x in getattr(content.profile(cid).scenario,phase) if x.id==option),None)
    _need(selected is not None,'Lựa chọn không còn trong tình huống này.')
    return selected


def _action(command,label,o,payload=None,fields=None,disabled=False,reason=''):
    return dict(command=command,label=label,payload=dict(id=o['id'],**(payload or {})),
                fields=fields or [],disabled=disabled,reason=reason)


def _check_snapshot(c,cid,o):
    live={r['id']:r for r in _snapshots(c,cid)}
    _need(all(live.get(r['id'])==r for r in o['resources']),
          'Bố trí người hoặc tài nguyên đã đổi. Hủy đề nghị rồi nhận lại để cập nhật bố trí cho ca.')


def action(s,c,cid,name,p,now=None):
    from . import career_scale
    _need(name in ACTIONS and type(p) is dict)
    at=int(time.time() if now is None else now)
    quota.day(at)
    kind=content.profile(cid).kind
    r=_record(c)
    if name=='scale_offer':
        _need(not p)
        tier=c.get('scale',{}).get('tier',0)
        _need(tier>0,'Đạt quy mô đầu tiên rồi nhận ca điều phối nhé.')
        _need(r['current'] is None,'Nghiệm thu ca đang chạy trước khi nhận ca khác.')
        old=r['offer']
        _need(old is None or not old['reserved'],'Bạn đang giữ một đề nghị hợp đồng.')
        if old is None:
            available=_snapshots(c,cid)
            _need(available,'Cần bố trí ít nhất một tài nguyên có người phụ trách và còn hoạt động.')
            _need(r['seq']<10**9)
            seq=r['seq']+1
            digest=hashlib.sha256(f"{s['journey'].get('seed',0)}|{cid}|{seq}".encode()).digest()
            demand=100 if seq==1 else (100,80,60)[digest[0]%3]
            o=dict(id=f'{cid}-{seq}',tier=tier,demand=demand,resources=available,
                   quote=project_quote(cid,tier,demand,len(available),len({x["site"] for x in available})),phase='planning',choices={},
                   allocated={},scheduled=[],incidents={},acceptances={},escrow=0,started=False,reserved=True,created=at)
        else:
            available=_snapshots(c,cid)
            _need(available,'Cần bố trí tài nguyên và người phụ trách trước khi nhận lại ca.')
            o=copy.deepcopy(old)
            o.update(reserved=True,resources=available,tier=tier,
                     quote=project_quote(cid,tier,o['demand'],len(available),len({x['site'] for x in available})))
        if kind!='community':quota.reserve(s,o['id'],at)
        if old is None:r['seq']+=1
        r['offer']=o;c[KEY]=r
        return dict(message='Đã giữ đề nghị và dự toán. Lập phương án trước khi cam kết vốn.')
    _need(type(p.get('id')) is str)
    o=r['current'] or r['offer']
    _need(o is not None and p['id']==o['id'],'Hợp đồng đã thay đổi hoặc đã được đối soát.')
    if name=='scale_cancel':
        _need(set(p)=={'id'} and not o['started'] and o['reserved'],'Chỉ hủy miễn phí trước khi bắt đầu ca.')
        if kind!='community':quota.cancel(s,o['id'],at)
        stock.release(c,o['id'])
        # Preserve customer identity and demand; rebooking may reflect changed capacity.
        o.update(reserved=False,phase='planning',choices={},allocated={},scheduled=[],incidents={},acceptances={})
        return dict(message='Đã trả suất và giải phóng hàng giữ chỗ. Đề nghị này vẫn được lưu để nhận lại.')
    _need(o['reserved'] or o['started'],'Nhận lại đề nghị trước khi tiếp tục.')
    if name=='scale_plan':
        _need(set(p)=={'id','option'} and o['phase']=='planning' and not o['started'])
        picked=_choice(cid,'planning',p['option'])
        o['choices']['planning']=picked.id;o['phase']='stock'
        return dict(message='Đã lưu phương án. Chuẩn bị và phân bổ vật tư cho từng điểm.')
    if name=='scale_allocate':
        _need(set(p)=={'id','site','code','units'} and o['phase']=='stock' and not o['started'])
        _need(type(p['site']) is str and type(p['code']) is str)
        line=next((x for x in requirements(c,cid,o) if x['site']==p['site'] and x['code']==p['code']),None)
        _need(line is not None,'Không có dòng phân bổ này trong hợp đồng.')
        amount=_int(p['units'],1)
        key=p['site'];previous=o['allocated'].get(key,0)
        _need(previous+amount<=line['units'],'Số lượng vượt phần cần phân bổ cho cơ sở.')
        if kind=='business':stock.reserve(c,cid,o['id'],key,p['code'],amount)
        o['allocated'][key]=previous+amount
        if all(o['allocated'].get(x['site'],0)==x['units'] for x in requirements(c,cid,o)):
            o['phase']='staffing'
        return dict(message='Đã ghi nhận vật tư tại cơ sở, chưa xuất dùng hoặc trả thưởng.')
    if name=='scale_schedule':
        _need(set(p)=={'id','resource','role'} and o['phase']=='staffing' and not o['started'])
        row=next((x for x in o['resources'] if x['id']==p['resource']),None)
        _need(row is not None and row['id'] not in o['scheduled'],'Vị trí không thuộc ca hoặc đã xếp lịch.')
        _need(type(p['role']) is str and p['role']==row['role'],'Vai trò chưa khớp chuyên môn của người được phân công.')
        _check_snapshot(c,cid,o)
        o['scheduled'].append(row['id'])
        return dict(message='Đã xác nhận người, vị trí và vai trò trong lịch ca.')
    if name=='scale_start':
        _need(set(p)=={'id','option'} and o['phase']=='staffing' and not o['started'])
        selected=_choice(cid,'allocation',p['option'])
        _need(len(o['scheduled'])==len(o['resources']),'Xác nhận lịch cho từng tài nguyên trước khi bắt đầu.')
        _check_snapshot(c,cid,o)
        amount=o['quote']['cost_total']-o['quote']['materials'] if kind=='business' else 0
        _need(c['money']>=amount,'Quỹ nghề chưa đủ vốn cam kết sau tiền vật tư. Góp vốn trước nhé.')
        if kind=='business':
            _need(stock.held(c,o['id'])==o['quote']['materials']//content.profile(cid).materials[0].unit_cost,
                  'Hàng giữ cho hợp đồng chưa khớp dự toán.')
        if kind!='community':
            _need(quota.public(s,at)['reserved']==o['id'],'Suất giữ hợp đồng đã thay đổi.')
        resources.lock(c,cid,o['id'],[x['id'] for x in o['resources']])
        if kind!='community':quota.start(s,o['id'],at)
        if amount:move(s,c,-amount,'Ký quỹ vận hành ca quản lý',o['id'],category='scale_escrow')
        o.update(escrow=amount,started=True,reserved=False,phase='exception')
        o['choices']['allocation']=selected.id
        r['current']=o;r['offer']=None
        return dict(message='Ca đã bắt đầu. Vốn, vật tư và đội ngũ được giữ riêng cho ca này.')
    if name in ('scale_resolve','scale_accept'):
        _need(set(p)=={'id','site','option'} and o['started'])
        site=p['site'];_need(type(site) is str and site in {x['site'] for x in o['resources']})
        phase='exception' if name=='scale_resolve' else 'acceptance'
        field='incidents' if name=='scale_resolve' else 'acceptances'
        _need(site not in o[field],'Cơ sở này đã gửi kết quả cho bước hiện tại.')
        if name=='scale_accept':_need(site in o['incidents'],'Giải quyết phát sinh của cơ sở trước khi nghiệm thu.')
        picked=_choice(cid,phase,p['option'])
        o[field][site]=picked.id
        o['phase']='acceptance' if len(o['incidents'])==len({x['site'] for x in o['resources']}) else 'exception'
        return dict(message='Đã ghi nhận báo cáo của cơ sở. Kết quả được đối soát khi khép hợp đồng.')
    _need(name=='scale_settle' and set(p)=={'id'} and o['started'])
    sites={x['site'] for x in o['resources']}
    _need(set(o['acceptances'])==sites and set(o['incidents'])==sites,'Cần đủ biên bản nghiệm thu của các cơ sở.')
    answers=[_choice(cid,phase,option) for phase,option in o['choices'].items()]
    answers += [_choice(cid,'exception',x) for x in o['incidents'].values()]
    answers += [_choice(cid,'acceptance',x) for x in o['acceptances'].values()]
    quality=min(x.score for x in answers)
    q=o['quote'];revenue=q['revenue']*quality//100
    taxes=q['tax']*quality//100
    receipt=dict(id=o['id'],tier=o['tier'],demand=o['demand'],quality=quality,resources=len(o['resources']),
                 revenue=revenue,materials=q['materials'],wages=q['wages'],premises=q['premises'],loss=q['loss'],tax=taxes,
                 at=at,message='Ca đạt yêu cầu.' if quality>=80 else 'Có phần nghiệm thu chưa đạt; xem nguyên nhân để cải thiện ca sau.',
                 evidence=[x.evidence for x in answers])
    if kind=='business':
        # Previously purchased lots keep their historical acquisition cost.
        receipt['materials']=stock.consume(c,o['id'])['cost']
        actual=sum(receipt[k] for k in ('wages','premises','loss','tax'))
        _need(actual<=o['escrow'])
        refund=o['escrow']-actual
        receipt['escrow']=o['escrow'];receipt['refund']=refund
        if refund:move(s,c,refund,'Hoàn vốn ký quỹ chưa dùng',o['id'],category='scale_refund')
    if revenue:move(s,c,revenue,'Nghiệm thu ca quản lý' if kind=='business' else 'Phụ cấp điều phối đã nghiệm thu',o['id'],category='scale_settlement')
    receipt['net']=revenue-sum(receipt[k] for k in ('materials','wages','premises','loss','tax'))
    from . import tile_match   # 🧩 Phúc lợi on the contract's profit: its own row; the receipt keeps its own sums
    tile=tile_match.extra(s,max(0,receipt['net']),f"scale|{o['id']}")
    if tile:move(s,c,tile,tile_match.label(s,'Nghiệm thu ca quản lý' if kind=='business' else 'Phụ cấp điều phối'),o['id'],category='scale_settlement')
    for resource in c['scale']['resources']:
        if resource['busy']==o['id']:resource['condition']=max(0,resource['condition']-1)
    resources.release(c,cid,o['id'])
    if quality>=80:
        career_scale.accepted(c,cid,at)
        if kind=='community':
            from . import needs
            receipt['spirit']=needs._spirit(s,3)
    r['history'].append(receipt);del r['history'][:-30]
    r['current']=None
    return dict(message=receipt['message'],receipt=copy.deepcopy(receipt))


def public(s,c,cid,now=None):
    p=content.profile(cid);r=_record(c);o=r['current'] or r['offer']
    out=dict(quota=None if p.kind=='community' else quota.public(s,now),contract=None,history=copy.deepcopy(r['history']),actions=[])
    if not c.get('scale',{}).get('tier'):
        return out
    if o is None or not o['started'] and not o['reserved']:
        out['actions'].append(dict(command='scale_offer',label='Nhận lại đề nghị đã lưu' if o else 'Xem hợp đồng điều phối',payload={}))
        return out
    actions=[];jobs=[];materials=[]
    v=dict(id=o['id'],title=p.scenario.title,description=p.focus,phase=o['phase'],quote=copy.deepcopy(o['quote']),
           working_capital=o['quote']['cost_total']-o['quote']['materials'] if p.kind=='business' else 0,
           progress=f"Nhu cầu {o['demand']}% · {len(o['resources'])}/{content.stage(cid,o['tier']).resources} {p.resource_name}",
           actions=actions,jobs=jobs,materials=materials)
    if not o['started']:actions.append(_action('scale_cancel','Hủy trước khi bắt đầu · trả suất',o))
    if o['phase']=='planning':
        actions.extend(_action('scale_plan',x.label,o,dict(option=x.id)) for x in p.scenario.planning)
    elif o['phase']=='stock':
        for line in requirements(c,cid,o):
            remaining=line['units']-o['allocated'].get(line['site'],0)
            available=stock.units(c,line['code'],line['site'],True) if p.kind=='business' else remaining
            label=next(x['name'] for x in c['scale']['sites'] if x['id']==line['site'])
            materials.append(dict(site=line['site'],name=f"{line['name']} · {label}",unit=line['unit'],available=o['allocated'].get(line['site'],0),required=line['units'],
                detail=f"Còn tự do: {available:,} {line['unit']}" if p.kind=='business' else 'Hiện vật được cấp từ ngân sách đơn vị.',
                actions=[_action('scale_allocate','Giữ vật tư cho điểm này',o,dict(site=line['site'],code=line['code']),
                                 [dict(name='units',label=f"Số {line['unit']}",type='number',min=1,max=remaining,value=min(remaining,available) or 1)],
                                 disabled=remaining<=0 or available<=0)]))
    elif o['phase']=='staffing':
        for row in o['resources']:
            crew=next((x for x in c['scale']['crew'] if x['id']==row['crew']),{'name':'Cần phân công lại'})
            jobs.append(dict(site=row['site'],label=f"{row['id']} · {crew['name']}",detail=f"{row['site']} · Chuyên môn: {row['role']}",
                actions=[] if row['id'] in o['scheduled'] else [_action('scale_schedule','Xác nhận lịch',o,dict(resource=row['id']),
                    [dict(name='role',label='Vai trò trong ca',options=[dict(value=x,label=x) for x in p.roles],value=p.roles[0])])]))
        actions.extend(_action('scale_start',x.label+' · bắt đầu ca',o,dict(option=x.id),disabled=len(o['scheduled'])!=len(o['resources'])) for x in p.scenario.allocation)
    else:
        for site in sorted({x['site'] for x in o['resources']}):
            label=next(x['name'] for x in c['scale']['sites'] if x['id']==site)
            phase='exception' if site not in o['incidents'] else 'acceptance'
            command='scale_resolve' if phase=='exception' else 'scale_accept'
            jobs.append(dict(site=site,label=label,detail='Xử lý phát sinh' if phase=='exception' else 'Nghiệm thu và bàn giao',
                actions=[] if site in o['acceptances'] else [_action(command,x.label,o,dict(site=site,option=x.id)) for x in getattr(p.scenario,phase)]))
        done=len(o['acceptances'])==len({x['site'] for x in o['resources']})
        actions.append(_action('scale_settle','Đối soát và khép hợp đồng',o,disabled=not done))
    out['contract']=v
    return out


def validate(c,cid):
    if KEY not in c:return
    r=c[KEY]
    _need(type(r) is dict and set(r)=={'v','seq','offer','current','history'})
    _need(type(r['v']) is int and r['v']==1);_int(r['seq'])
    _need(type(r['history']) is list and len(r['history'])<=30)
    _need(r['offer'] is None or r['current'] is None)
    for key in ('offer','current'):
        o=r[key]
        if o is None:continue
        _need(type(o) is dict and set(o)==OFFER_KEYS)
        _need(type(o['id']) is str and o['id']==f"{cid}-{r['seq']}")
        _int(o['tier'],1,8);_int(o['demand'],60,100);_int(o['created'],0,10**11);_int(o['escrow'])
        _need(o['demand'] in (60,80,100) and o['phase'] in PHASES)
        _need(type(o['started']) is bool and type(o['reserved']) is bool)
        _need(o['started']==(key=='current') and not(o['started'] and o['reserved']))
        _need(type(o['resources']) is list and 0<len(o['resources'])<=content.stage(cid,o['tier']).resources)
        ids=[];sites=set()
        for row in o['resources']:
            _need(type(row) is dict and set(row)=={'id','site','crew','role'})
            _need(all(type(v) is str for v in row.values()))
            _need(any(x['id']==row['id'] for x in c['scale']['resources']) and any(x['id']==row['site'] for x in c['scale']['sites']))
            _need(row['role'] in content.profile(cid).roles);ids.append(row['id']);sites.add(row['site'])
        _need(len(ids)==len(set(ids)))
        _need(type(o['quote']) is dict and all(type(x) is int for x in o['quote'].values()))
        _need(o['quote']==project_quote(cid,o['tier'],o['demand'],len(ids),len(sites)))
        _need(type(o['choices']) is dict and set(o['choices'])<={'planning','allocation'})
        for phase,option in o['choices'].items():_choice(cid,phase,option)
        _need(type(o['allocated']) is dict and set(o['allocated'])<=sites)
        required={x['site']:x['units'] for x in requirements(c,cid,o)}
        for site,amount in o['allocated'].items():_int(amount,1,required[site])
        _need(type(o['scheduled']) is list and len(o['scheduled'])==len(set(o['scheduled'])) and set(o['scheduled'])<=set(ids))
        for field,phase in (('incidents','exception'),('acceptances','acceptance')):
            _need(type(o[field]) is dict and set(o[field])<=sites)
            for option in o[field].values():_choice(cid,phase,option)
        _need(set(o['acceptances'])<=set(o['incidents']))
        if o['started']:
            _need(set(o['choices'])=={'planning','allocation'} and set(o['scheduled'])==set(ids))
            _need(o['escrow']==(o['quote']['cost_total']-o['quote']['materials'] if content.profile(cid).kind=='business' else 0))
            _need(all(x['busy']==o['id'] for x in c['scale']['resources'] if x['id'] in ids))
        else:
            _need(o['escrow']==0 and not o['incidents'] and not o['acceptances'])
            _need('allocation' not in o['choices'])
        if o['phase']=='planning':
            _need(not o['choices'] and not o['allocated'] and not o['scheduled'])
        else:_need('planning' in o['choices'])
        if o['phase']=='stock':_need(not o['scheduled'])
        if o['phase'] in ('staffing','exception','acceptance'):_need(o['allocated']==required)
        _need(o['started']==(o['phase'] in ('exception','acceptance')))
        if not o['reserved'] and not o['started']:_need(o['phase']=='planning')
        if content.profile(cid).kind=='business':_need(stock.held(c,o['id'])==sum(o['allocated'].values()))
    for row in r['history']:
        _need(type(row) is dict and {'id','tier','demand','quality','resources','revenue','materials','wages','premises','loss','tax','net','at','message','evidence'}<=set(row))
        _need(type(row['id']) is str and stock.JOB.fullmatch(row['id']) is not None and row['id'].startswith(cid+'-'))
        for key in ('revenue','materials','wages','premises','loss','tax'):_int(row[key])
        _int(row['net'],-10**9,10**9);_int(row['at'],0,10**11);_int(row['tier'],1,8);_int(row['demand'],60,100);_int(row['quality'],0,100);_int(row['resources'],1,50)
        _need(row['net']==row['revenue']-sum(row[k] for k in ('materials','wages','premises','loss','tax')))
        _need(type(row['message']) is str and len(row['message'])<=500 and type(row['evidence']) is list and len(row['evidence'])<=30)
        _need(all(type(x) is str and len(x)<=1000 for x in row['evidence']))


def validate_account(s):
    """Cross-career reservation and resource ownership, also checked on imports."""
    reserved=[]
    for cid,c in s['careers'].items():
        special=c.get('specialism',{}).get('job')
        if special and special.get('phase')=='offered' and content.profile(cid).kind!='community':reserved.append(special['id'])
        r=c.get(KEY,{})
        offer,current=r.get('offer'),r.get('current')
        if offer and offer.get('reserved') and content.profile(cid).kind!='community':reserved.append(offer['id'])
        active=[o for o in (offer,current) if o and (o['reserved'] or o['started'])]
        ids={o['id'] for o in active}
        _need(all(job in ids for lot in c.get(stock.KEY,{}).get('lots',[]) for job in lot['reserved']))
        busy={x['busy'] for x in c.get('scale',{}).get('resources',[]) if x['busy']}
        _need(busy==({current['id']} if current else set()))
    _need(sum((c.get('specialism',{}).get('job') or {}).get('phase') in ('working','acceptance') for c in s['careers'].values())<=1, 'Chỉ có một công việc chuyên môn đang trực tiếp thực hiện.')
    held=s.get('journey',{}).get(quota.KEY,{}).get('reserved')
    _need(len(reserved)<=1 and held==(reserved[0] if reserved else None))
