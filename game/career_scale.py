"""Optional ownership and prospective real-day management progression."""
import copy

from . import career_scale_content as content
from . import career_scale_quota as quota
from . import career_scale_resources as resources
from . import career_scale_finance as finance

MAX = 10**9
DAY_MAX = 10000
ACTIONS = frozenset(('scale_upgrade','scale_crew_hire','scale_crew_fire','scale_resource_assign',
                     'scale_resource_unassign','scale_resource_maintain','scale_site_open','scale_site_public'))
KEYS = {'v','tier','revision','clean','inherited_clean','qualified_days','start_day','today',
        'capital_history','sites','resources','crew','next_crew','recent_ids'}


def _need(ok, message='Dữ liệu quy mô nghề không hợp lệ.'):
    from .engine import need
    need(ok, message)


def _int(x, lo=0, hi=MAX):
    _need(type(x) is int and lo<=x<=hi)


def _today(day, tier):
    return dict(day=day,total=0,clean=0,accepted=False,requires_contract=tier>0,ids=[],overflow=False)


def _inherited(c,cid):
    if 'mastery' not in c:
        return 0
    from . import career_mastery
    from .engine import GameError
    try:
        career_mastery.validate(c,cid)
    except (GameError, KeyError, TypeError):
        return 0
    return c['mastery']['clean']


def _qualified(today):
    return (not today['overflow'] and today['clean']>=3 and today['clean']*100>=today['total']*80
            and (not today['requires_contract'] or today['accepted']))


def _roll(r, now):
    day = quota.day(now)
    if day > r['today']['day']:
        r['qualified_days'] += int(_qualified(r['today']))
        r['today'] = _today(day,r['tier'])
    return day


def ensure(c,cid,now=None):
    if 'scale' not in c:
        inherited = _inherited(c,cid); day=quota.day(now)
        c['scale']=dict(v=1,tier=0,revision=0,clean=inherited,inherited_clean=inherited,
                        qualified_days=0,start_day=day,today=_today(day,0),capital_history=[],
                        sites=[],resources=[],crew=[],next_crew=1,recent_ids=[])
    r=c['scale']; _roll(r,now)
    return r


def completed(c,cid,task,now=None):
    """Called only after authoritative manual completion, never NPC settlement."""
    if (not c.get('open') or task.get('status')!='completed' or task.get('career')!=cid
            or task.get('day')!=c['day'] or task.get('player_order') or task.get('staff')
            or task.get('staff_id') or task.get('managed') or task.get('management')
            or task.get('id') not in c.get('completed_ids',())
            or not any(x is task for x in c.get('tasks',()))):
        return False
    tid=task.get('id')
    if type(tid) is not str or not 1<=len(tid)<=150:
        return False
    first='scale' not in c
    r=ensure(c,cid,now); today=r['today']
    if quota.day(now)<today['day'] or tid in r['recent_ids']:
        return False
    if len(today['ids'])>=DAY_MAX or r['clean']>=MAX:
        # Exhaustion cannot award a day whose later errors were not retained.
        today['overflow']=True
        return False
    clean=type(task.get('mistakes')) is int and task['mistakes']==0
    if first and clean and r['inherited_clean'] and any(
            x.get('id')==tid and x.get('clean') is True
            for x in c.get('mastery',{}).get('today',{}).get('jobs',())):
        r['inherited_clean']-=1; r['clean']-=1
    today['ids'].append(tid); today['total']+=1; today['clean']+=int(clean)
    r['recent_ids'].append(tid)
    del r['recent_ids'][:-DAY_MAX]
    r['clean']+=int(clean)
    return True


def accepted(c,cid,now=None):
    """A successful authoritative management acceptance, not merely a booking."""
    r=ensure(c,cid,now)
    if quota.day(now)==r['today']['day']:
        r['today']['accepted']=True


def external_slots(s):
    """Secondary BUSINESS sites only; shared quay guards add their own stalls."""
    return sum(max(0,len(c.get('scale',{}).get('sites',()))-1)
               for cid,c in s.get('careers',{}).items()
               if cid in content.PROFILES and content.profile(cid).kind=='business')


def _requirements(s,c,cid,r):
    from . import certificates, accounting_jobs, employment
    st=content.stage(cid,r['tier']+1)
    req=[dict(label=label,got=got,need=need,met=got>=need) for label,got,need in (
        ('Ngày thực đạt chuẩn đã kết thúc',r['qualified_days'],st.days),
        ('Việc tự làm không sai tích lũy',r['clean'],st.clean))]
    req.append(dict(label='Đã bắt đầu nghề',got=int(c.get('started') is True),need=1,met=c.get('started') is True))
    ok,reason=accounting_jobs.can_work(s,cid)
    req.append(dict(label='Điều kiện hành nghề hiện có',got=int(ok),need=1,met=ok,reason=reason))
    if employment.required(cid):
        hired=c.get('job',{}).get('status')=='hired'
        req.append(dict(label='Đang được tuyển dụng theo luật nghề hiện có',got=int(hired),need=1,met=hired))
    if content.profile(cid).kind=='business' and st.tier>=2:
        held=certificates.earned(s.get('journey'),'business_advanced')
        req.append(dict(label='Chứng chỉ kinh doanh nâng cao',got=int(held),need=1,met=held))
    enough=type(c.get('money')) is int and c['money']>=st.fee
    req.append(dict(label='Quỹ nghề (Góp vốn)',got=c['money'] if type(c.get('money')) is int else 0,need=st.fee,met=enough))
    return req


def _revision(r,p):
    _need(type(p.get('expected_revision')) is int and p['expected_revision']==r['revision'],
          'Phân công đã thay đổi. Mở lại bảng quản lý trước khi thao tác.')


def _resource(r,rid):
    _need(type(rid) is str, 'Chọn tài nguyên hợp lệ.')
    x=next((x for x in r['resources'] if x['id']==rid),None)
    _need(x is not None,'Không tìm thấy tài nguyên.')
    _need(not x['busy'],'Tài nguyên đang giữ cho hợp đồng. Hoàn tất hoặc hủy hợp đồng trước.')
    return x


def _free_crew(r,crew,resource=None):
    _need(type(crew) is str and any(x['id']==crew for x in r['crew']),'Chọn người trong đội ngũ quy mô.')
    _need(not any(x['crew']==crew and x is not resource for x in r['resources']),
          'Một người chỉ phụ trách một vị trí. Gỡ phân công cũ trước.')


def _active_site(r,site):
    _need(type(site) is str and any(x['id']==site for x in r['sites']),'Điểm làm việc chưa kích hoạt.')


def _keep_occupied(r,resource,new_site=None):
    old=resource['site']
    if old and old!='base' and old!=new_site:
        _need(any(x is not resource and x['site']==old and x['crew'] and x['condition']>0 for x in r['resources']),
              'Điểm đang mở cần ít nhất một vị trí có người. Phân người thay thế trước.')


def action(s,c,cid,name,p,now=None):
    _need(name in ACTIONS and type(p) is dict,'Thao tác quy mô không hợp lệ.')
    # Read/roll privately: rejected actions never write a new ownership sidecar.
    shadow=dict(c); shadow['scale']=copy.deepcopy(c['scale']) if 'scale' in c else None
    if shadow['scale'] is None: del shadow['scale']
    r=ensure(shadow,cid,now)
    if name=='scale_upgrade':
        _need(set(p)=={'expected_tier'},'Thông tin nâng quy mô không hợp lệ.')
        _need(type(p['expected_tier']) is int and p['expected_tier']==r['tier'],'Bậc quy mô đã thay đổi.')
        _need(r['tier']<8,'Đã đạt quy mô tối đa.')
        req=_requirements(s,c,cid,r)
        _need(all(x['met'] for x in req),'Chưa đủ ngày thực, việc sạch, chứng chỉ hoặc quỹ nghề.')
        _need(not any(x['busy'] for x in r['resources']),'Hoàn tất hợp đồng đang giữ tài nguyên trước khi nâng quy mô.')
        st=content.stage(cid,r['tier']+1)
        r['tier']=st.tier; r['revision']+=1
        # A day spanning the first upgrade must meet the management requirement.
        r['today']['requires_contract']=True
        resources.ensure(shadow,cid)
        c['scale']=r
        if st.fee: finance.move(s,c,-st.fee,f'Nâng quy mô: {st.title}',f'scale-{cid}-tier-{st.tier}')
        return dict(message=f'Đã mở {st.title}. Bố trí đội ngũ và kích hoạt từng điểm trong bảng quản lý.')
    _need(r['tier']>0,'Mở bậc quy mô đầu tiên trước.')
    _revision(r,p)
    payload=set(p)-{'expected_revision'}; fee=0; label=''; ref=f'scale-{cid}-{r["revision"]+1}'
    if name=='scale_crew_hire':
        _need(payload=={'candidate'} and type(p['candidate']) is int,'Chọn ứng viên hợp lệ.')
        candidates=resources.candidates(shadow,cid)
        _need(0<=p['candidate']<len(candidates),'Không tìm thấy ứng viên.')
        _need(len(r['crew'])<len(r['resources']),'Đã đủ nhân sự cho tổng vị trí quy mô.')
        chosen=dict(candidates[p['candidate']]); fee=chosen.pop('fee')
        chosen['id']=f'scale-{cid}-crew-{r["next_crew"]}'
        r['next_crew']+=1; r['crew'].append(chosen)
        label=f'Tiếp nhận đội ngũ: {chosen["name"]}'
    elif name=='scale_crew_fire':
        _need(payload=={'crew'},'Chọn người kết thúc phân công.')
        _free_crew(r,p['crew'])
        r['crew']=[x for x in r['crew'] if x['id']!=p['crew']]
    elif name in ('scale_resource_assign','scale_resource_unassign','scale_resource_maintain'):
        expected={'resource','crew','site'} if name.endswith('_assign') else {'resource','expected_condition'} if name.endswith('_maintain') else {'resource'}
        _need(payload==expected,'Thông tin tài nguyên không hợp lệ.')
        x=_resource(r,p['resource'])
        if name.endswith('_assign'):
            _free_crew(r,p['crew'],x); _active_site(r,p['site']); _keep_occupied(r,x,p['site'])
            _need(x['site']==p['site'] or sum(q['site']==p['site'] for q in r['resources'])<resources.per_site(shadow,cid),
                  'Điểm đã đủ vị trí của bậc quy mô này.')
            x.update(crew=p['crew'],site=p['site'])
        elif name.endswith('_unassign'):
            _keep_occupied(r,x)
            x['crew']=None
        else:
            _need(type(p['expected_condition']) is int and p['expected_condition']==x['condition'],'Tình trạng thiết bị đã thay đổi.')
            _need(x['condition']<100,'Thiết bị chưa cần bảo trì.')
            fee=resources.maintenance_fee(shadow,cid,x); label=f'Đại tu khôi phục thiết bị: {x["label"]}'
            x['condition']=100
    elif name=='scale_site_open':
        from . import quay_progression, certificates
        _need(payload=={'resource','crew'},'Chọn tài nguyên và người cho điểm mới.')
        st=content.stage(cid,r['tier']); _need(len(r['sites'])<st.sites,'Đã dùng đủ điểm của bậc quy mô.')
        x=_resource(r,p['resource']); _free_crew(r,p['crew'],x); _keep_occupied(r,x)
        _need(x['condition']>0,'Bảo trì tài nguyên trước khi mở điểm.')
        if content.profile(cid).kind=='business':
            q=s.get('journey',{}).get('quay') or {}
            _need(external_slots(s)+len(q.get('stalls',()))<quay_progression.limit(q,'slots'),
                  'Hết quyền địa điểm dùng chung. Nâng Số quầy sở hữu trước.')
            if len(r['sites'])>=2:
                _need(certificates.earned(s.get('journey'),'business_chain'),'Cần chứng chỉ quản lý chuỗi để kích hoạt từ ba điểm.')
        index=len(r['sites']); sid=f'branch-{index}'
        r['sites'].append(dict(id=sid,name=f'Điểm {index+1}',public=False))
        x.update(site=sid,crew=p['crew'])
    else:
        _need(payload=={'site','public'} and type(p['public']) is bool,'Thiết lập điểm không hợp lệ.')
        _active_site(r,p['site'])
        next(x for x in r['sites'] if x['id']==p['site'])['public']=p['public']
    _need(type(c.get('money')) is int and c['money']>=fee,'Quỹ nghề chưa đủ xu. Góp vốn trước nhé.')
    r['revision']+=1; c['scale']=r
    if fee: finance.move(s,c,-fee,label,ref)
    return dict(message=label or 'Đã cập nhật phân công quy mô.')


def public(s,c,cid,now=None):
    from . import inventory, capacity_progression, order_progression
    shadow=dict(c)
    if 'scale' in c: shadow['scale']=copy.deepcopy(c['scale'])
    r=ensure(shadow,cid,now); p=content.profile(cid); out=resources.public(shadow,cid)
    nxt=None
    if r['tier']<8:
        st=content.stage(cid,r['tier']+1); req=_requirements(s,c,cid,r)
        busy=any(x['busy'] for x in r['resources'])
        reason=next((x.get('reason') or x['label'] for x in req if not x['met']),'')
        reason=reason or ('Hoàn tất hợp đồng đang giữ tài nguyên.' if busy else '')
        nxt=dict(tier=st.tier,title=st.title,fee=st.fee,
                 benefit=f'{st.resources} vị trí toàn mạng · tối đa {st.sites} điểm · {p.focus}',
                 requirements=req,can_buy=not reason,reason=reason,quote=content.quote(cid,st.tier))
        out['actions'].insert(0,dict(command='scale_upgrade',label=f'Mở {st.title} · {st.fee:,} xu',
                                    payload=dict(expected_tier=r['tier']),fields=[],disabled=bool(reason),reason=reason))
    base=inventory.capacity(cid) if inventory.catalogue(cid) else 80
    out.update(cid=cid,tier=r['tier'],title=content.stage(cid,r['tier']).title if r['tier'] else 'Nghề hiện có',
               kind=p.kind,focus=p.focus,resource_name=p.resource_name,
               stages=[content.stage_dict(cid,n) for n in range(1,9)],next=nxt,
               limits=dict(stock=capacity_progression.limit(c,cid,base),order=order_progression.limit(c,cid)),
               quota=quota.public(s,now),progress=dict(clean=r['clean'],inherited_clean=r['inherited_clean'],
                    qualified_days=r['qualified_days'],today=dict(day=r['today']['day'],clean=r['today']['clean'],
                    total=r['today']['total'],accepted=r['today']['accepted'],qualified=_qualified(r['today']),
                    pending=True,requires_contract=r['today']['requires_contract'])),
               revision=r['revision'],capital_history=copy.deepcopy(r['capital_history']))
    return out


def validate(c,cid):
    if 'scale' not in c: return
    r=c['scale']; _need(type(r) is dict and set(r)==KEYS)
    _int(r['v'],1,1); _int(r['tier'],0,8); _int(r['revision'])
    _int(r['clean']); _int(r['inherited_clean'],0,r['clean'])
    _int(r['start_day'],0,1199999); _int(r['qualified_days'],0, min(1200000,r['clean']//3))
    t=r['today']; _need(type(t) is dict and set(t)=={'day','total','clean','accepted','requires_contract','ids','overflow'})
    _int(t['day'],r['start_day'],1199999); _int(t['total'],0,DAY_MAX); _int(t['clean'],0,min(t['total'],r['clean']))
    _need(r['qualified_days']<=t['day']-r['start_day'])
    _need(all(type(t[k]) is bool for k in ('accepted','requires_contract','overflow')))
    _need(t['requires_contract']==(r['tier']>0))
    _need(type(t['ids']) is list and len(t['ids'])==t['total'] and all(type(x) is str and 1<=len(x)<=150 for x in t['ids']))
    _need(len(t['ids'])==len(set(t['ids'])))
    _need(type(r['recent_ids']) is list and len(r['recent_ids'])<=DAY_MAX
          and all(type(x) is str and 1<=len(x)<=150 for x in r['recent_ids']))
    _need(len(r['recent_ids'])==len(set(r['recent_ids'])))
    rows=r['capital_history']; _need(type(rows) is list and len(rows)<=80)
    for x in rows:
        _need(type(x) is dict and set(x)=={'amount','label','ref'})
        _int(x['amount'],-10**12,10**12)
        _need(type(x['label']) is str and len(x['label'])<=300 and type(x['ref']) is str and len(x['ref'])<=150)
    resources.validate(c,cid)
