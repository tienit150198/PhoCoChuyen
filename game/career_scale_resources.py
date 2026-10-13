"""Separate management equipment and crews; legacy staff keep their own jobs."""
import copy
import math
import re

from . import career_scale_content as content


def _need(ok, message='Dữ liệu tài nguyên quy mô không hợp lệ.'):
    from .engine import need
    need(ok, message)


def per_site(c, cid):
    tier = c.get('scale', {}).get('tier', 0)
    if not tier:
        return 0
    st = content.stage(cid, tier)
    return math.ceil(st.resources / st.sites)


def ensure(c, cid):
    """Allocate purchased equipment only. New sites and crews remain explicit."""
    r = c['scale']; tier = r['tier']
    if not tier:
        return r
    st = content.stage(cid, tier)
    if not r['sites']:
        r['sites'].append(dict(id='base', name='Cơ sở gốc', public=False))
    cap = per_site(c, cid)
    assigned = sum(x['site'] == 'base' for x in r['resources'])
    for n in range(len(r['resources']) + 1, st.resources + 1):
        site = 'base' if assigned < cap else None
        assigned += int(site is not None)
        r['resources'].append(dict(id=f'r{n}', label=f'{content.profile(cid).resource_name} {n}',
                                   site=site, crew=None, busy=None, condition=100))
    return r


def candidates(c, cid):
    from . import operations
    r = c['scale']; p = content.profile(cid)
    if not r['tier']:
        return []
    quote = content.quote(cid, r['tier'])
    # A one-time onboarding fee, distinct from recurring wages included in each quote.
    fee = max(1, math.ceil(quote['wages'] / quote['resources'])) if p.kind == 'business' else 0
    return [dict(candidate=i, name=n, role=p.roles[i % len(p.roles)],
                 precision=precision, speed=speed, fee=fee,
                 wage=fee if p.kind == 'business' else 0)
            for i, (n, _role, _bio, speed, precision) in enumerate(operations.PEOPLE[cid])]


def available(c, cid):
    r = c.get('scale')
    if not r or not r['tier']:
        return []
    sites = {x['id'] for x in r['sites']}
    crew = {x['id']: x for x in r['crew']}
    return [x for x in r['resources'] if x['site'] in sites and x['crew'] in crew
            and crew[x['crew']]['role'] in content.profile(cid).roles
            and not x['busy'] and x['condition'] > 0]


def lock(c, cid, job, ids):
    _need(type(job) is str and re.fullmatch(rf'{cid}-[1-9][0-9]{{0,11}}', job), 'Mã hợp đồng không hợp lệ.')
    _need(type(ids) is list and 0 < len(ids) <= 50 and all(type(x) is str for x in ids)
          and len(ids) == len(set(ids)), 'Chọn mỗi tài nguyên đúng một lần.')
    choices = {x['id']: x for x in available(c, cid)}
    _need(set(ids) <= choices.keys(), 'Tài nguyên thiếu người, đang bận hoặc cần bảo trì.')
    for rid in ids:
        choices[rid]['busy'] = job
    c['scale']['revision'] += 1


def release(c, cid, job):
    for x in c.get('scale', {}).get('resources', ()):
        if x['busy'] == job:
            x['busy'] = None
    if 'scale' in c:
        c['scale']['revision'] += 1


def _action(name, label, revision, payload=None, fields=None, reason=''):
    return dict(command=name, label=label, payload=dict(expected_revision=revision, **(payload or {})),
                fields=fields or [], disabled=bool(reason), reason=reason)


def public(c, cid):
    r = c.get('scale')
    if not r:
        return dict(sites=[], resources=[], crew=[], actions=[])
    rev = r['revision']; people = {x['id']: x for x in r['crew']}
    site_names = {x['id']: x['name'] for x in r['sites']}
    used = {x['crew'] for x in r['resources'] if x['crew']}
    free = [x for x in r['crew'] if x['id'] not in used]
    actions = []
    if r['tier']:
        for x in candidates(c, cid):
            actions.append(_action('scale_crew_hire', f'Mời {x["name"]} · {x["role"]} · phí {x["fee"]:,} xu', rev,
                                   dict(candidate=x['candidate']), reason='Đã đủ đội ngũ.' if len(r['crew']) >= len(r['resources']) else ''))
        for x in free:
            actions.append(_action('scale_crew_fire', f'Kết thúc phân công {x["name"]}', rev, dict(crew=x['id'])))
    rows = []
    for x in r['resources']:
        row = copy.deepcopy(x)
        row.update(site_name=site_names.get(x['site'], 'Chưa bố trí'),
                   crew_name=people.get(x['crew'], {}).get('name', 'Chưa có người'), actions=[])
        if not x['busy']:
            options = [dict(value=q['id'], label=f'{q["name"]} · {q["role"]}') for q in free]
            if x['crew']:
                options.insert(0, dict(value=x['crew'], label=row['crew_name']))
            if options:
                row['actions'].append(_action('scale_resource_assign', 'Phân công vị trí', rev, dict(resource=x['id']), [
                    dict(name='crew', label='Người phụ trách', options=options, value=options[0]['value']),
                    dict(name='site', label='Điểm làm việc', options=[dict(value=q['id'],label=q['name']) for q in r['sites']], value=x['site'] or 'base')]))
            if x['crew']:
                row['actions'].append(_action('scale_resource_unassign','Gỡ phân công',rev,dict(resource=x['id'])))
            if x['condition'] < 100:
                fee = maintenance_fee(c, cid, x)
                row['actions'].append(_action('scale_resource_maintain', f'Đại tu về 100% · {fee:,} xu · hiện {x["condition"]}/100',rev,dict(resource=x['id'],expected_condition=x['condition'])))
        rows.append(row)
    sites = []
    for x in r['sites']:
        local = [q for q in r['resources'] if q['site'] == x['id']]
        sites.append(dict(copy.deepcopy(x), resources=len(local),crew_count=sum(q['crew'] is not None for q in local),
                          actions=[_action('scale_site_public', 'Đặt riêng tư' if x['public'] else 'Mở tham quan', rev,
                                           dict(site=x['id'],public=not x['public']))]))
    if r['tier'] and len(sites) < content.stage(cid,r['tier']).sites:
        movable = [x for x in r['resources'] if not x['busy'] and not x['crew']]
        if free and movable:
            actions.append(_action('scale_site_open','Kích hoạt điểm mới · chọn vị trí và người', rev, fields=[
                dict(name='resource',label='Tài nguyên',options=[dict(value=x['id'],label=x['label']) for x in movable],value=movable[0]['id']),
                dict(name='crew',label='Người phụ trách',options=[dict(value=x['id'],label=x['name']) for x in free],value=free[0]['id'])]))
    return dict(sites=sites,resources=rows,crew=copy.deepcopy(r['crew']),actions=actions)


def maintenance_fee(c, cid, resource):
    if content.profile(cid).kind != 'business':
        return 0
    quote = content.quote(cid, c['scale']['tier'])
    return math.ceil(quote['premises'] * (100-resource['condition']) / (100*quote['resources']))


def validate(c, cid):
    if 'scale' not in c:
        return
    r = c['scale']; tier=r['tier']; p=content.profile(cid)
    count = content.stage(cid,tier).resources if tier else 0
    sites, rows, crew = r['sites'], r['resources'], r['crew']
    _need(type(sites) is list and len(sites) <= (content.stage(cid,tier).sites if tier else 0))
    _need(type(rows) is list and len(rows) == count and type(crew) is list and len(crew) <= count)
    site_ids=[]
    for i,x in enumerate(sites):
        _need(type(x) is dict and set(x)=={'id','name','public'})
        _need(x['id']==('base' if i==0 else f'branch-{i}') and type(x['name']) is str and 1<=len(x['name'])<=80 and type(x['public']) is bool)
        site_ids.append(x['id'])
    _need(bool(sites)==bool(tier))
    crew_ids=[]
    for x in crew:
        _need(type(x) is dict and set(x)=={'id','name','role','precision','speed','wage','candidate'})
        _need(type(x['id']) is str and re.fullmatch(rf'scale-{cid}-crew-[1-9][0-9]{{0,8}}',x['id']))
        _need(type(x['candidate']) is int and 0<=x['candidate']<4)
        from . import operations
        n,_,_,speed,precision=operations.PEOPLE[cid][x['candidate']]
        _need(x['name']==n and x['role']==p.roles[x['candidate']%len(p.roles)]
              and type(x['precision']) is int and x['precision']==precision
              and type(x['speed']) is int and x['speed']==speed
              and type(x['wage']) is int and 0<=x['wage']<=10**9)
        crew_ids.append(x['id'])
    _need(len(crew_ids)==len(set(crew_ids)))
    assigned=[]
    for i,x in enumerate(rows,1):
        _need(type(x) is dict and set(x)=={'id','label','site','crew','busy','condition'})
        _need(x['id']==f'r{i}' and x['label']==f'{p.resource_name} {i}')
        _need(x['site'] is None or type(x['site']) is str and x['site'] in site_ids)
        _need(x['crew'] is None or type(x['crew']) is str and x['crew'] in crew_ids)
        _need(type(x['condition']) is int and 0<=x['condition']<=100)
        _need(x['busy'] is None or type(x['busy']) is str and re.fullmatch(rf'{cid}-[1-9][0-9]{{0,11}}',x['busy']))
        _need(not x['crew'] or x['site'] is not None)
        _need(not x['busy'] or x['crew'] is not None)
        if x['crew']: assigned.append(x['crew'])
    _need(len(assigned)==len(set(assigned)))
    # Higher tiers can lower per-point density. Preserve earlier placement;
    # action guards apply the new density only to newly added positions.
    _need(type(r['next_crew']) is int and 1<=r['next_crew']<=10**9)
    _need(all(int(x.rsplit('-',1)[1]) < r['next_crew'] for x in crew_ids))
