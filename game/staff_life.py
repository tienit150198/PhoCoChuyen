"""Bounded NPC employee events and deterministic customer quality.

Events advance on completed work, never on a page load or elapsed wall time.
Only explicit owner choices cost money. Supplements keep legacy candidate data
unchanged; human players hired through the separate shift system are excluded.
"""
from __future__ import annotations

import copy
import hashlib

GAP = 64
RECENT = 12
CYCLE = ('raise', 'wedding', 'quit')
KINDS = CYCLE + ('raise_double',)
TITLES = dict(raise_='Xin tăng lương', raise_double='Đề nghị lương gấp đôi', wedding='Thiệp cưới của nhân viên', quit='Nhân viên xin nghỉ')
REVIEWS = {1:'Khách không hài lòng: xử lý sai và phục vụ thiếu chú ý.',
           2:'Khách góp ý: còn sai sót, cần kiểm tra kỹ và quan tâm khách hơn.',
           3:'Khách thấy tạm ổn, vẫn còn điểm cần cải thiện.',
           4:'Khách hài lòng: làm việc cẩn thận và phục vụ chu đáo.',
           5:'Khách khen: làm rất tốt, tận tâm và đáng tin cậy.'}


def _hash(value):
    return int.from_bytes(hashlib.sha256(str(value).encode()).digest()[:8], 'big')


def wage(container, employee):
    return min(10000, employee['wage'] + container.get('staff_life', {}).get('raises', {}).get(employee['id'], 0))


def quality(employee, seq, seed, *, quay=False):
    ability = (90 if employee.get('g') else 65) if quay else employee.get('precision', 60)
    morale = employee.get('mo' if quay else 'morale', 60)
    experience = min(100, employee.get('d' if quay else 'jobs', 0) // (2 if quay else 20))
    score = (ability * 55 + morale * 30 + experience * 15) // 100
    score += _hash(f"quality|{seed}|{employee['id']}|{seq}") % 31 - 15
    stars = 1 + (score >= 30) + (score >= 50) + (score >= 65) + (score >= 82)
    return dict(stars=stars, text=REVIEWS[stars], employee=employee['id'], name=employee['name'])


def _members(container, quay):
    return [e for e in container.get('staff', []) if quay or e.get('status') == 'hired']


def _progress(c, quay):
    return c.get('business', {}).get('sold', 0) if quay else c['ops'].get('work_ticks', 0) + c['ops'].get('business', {}).get('served', 0)


def _tick(c, owner, quay):
    container = c if quay else c['ops']
    employees = _members(container, quay)
    state = container.get('staff_life')
    progress = _progress(c, quay)
    if state is None:
        if not employees:return False
        container['staff_life'] = dict(v=1, seq=0, next=progress+GAP, pending=None, recent=[], spent=0, raises={})
        return True
    changed = False
    ids = {e['id'] for e in employees}
    for key in list(state['raises']):
        if key not in ids:del state['raises'][key];changed = True
    if state['pending'] and state['pending']['employee'] not in ids:
        state['pending'] = None;state['next'] = progress + GAP;changed = True
    if not employees or state['pending'] or progress < state['next']:return changed
    state['seq'] += 1
    seq = state['seq']
    employee = sorted(employees, key=lambda e:e['id'])[_hash(f'{owner}|{seq}') % len(employees)]
    kind = CYCLE[(_hash(owner) + seq) % len(CYCLE)]
    current = wage(container, employee)
    # 20% of raise slots (~1/15 events), stable across reloads; no wall-time catch-up.
    if kind == 'raise' and current < 10000 and _hash(f'double-wage|{owner}|{seq}') % 5 == 0:
        kind = 'raise_double'
    state['pending'] = dict(id=f'staff-{owner}-{seq}', kind=kind, employee=employee['id'], name=employee['name'],
                            wage=current, raise_by=min(current,10000-current) if kind=='raise_double' else max(1, (employee['wage']+9)//10))
    return True


def tick_career(s, c, career):
    return _tick(c, career, False)


def tick_quay(s, st):
    return _tick(st, st['id'], True)


def _raise_quote(container, p, employee):
    """Manual quay wages can change while an event waits. Quote and apply alike."""
    if p['kind'] not in ('raise', 'raise_double'):return p
    current = wage(container, employee)
    return dict(p, wage=current, raise_by=min(current,10000-current) if p['kind']=='raise_double' else p['raise_by'])


def _choices(p, base=None):
    if p['kind'] in ('raise', 'raise_double'):
        limit = 10000 if p['kind']=='raise_double' or base is None else min(10000,base*2)
        target = max(p['wage'],min(limit,p['wage']+p['raise_by']))
        return [dict(id='approve', label='Đồng ý tăng lương', cost=0, effect=f"Lương mới {target} xu (hiện tại {p['wage']} xu); áp dụng cho công việc mới sau khi đồng ý."),
                dict(id='decline', label='Chưa tăng lúc này', cost=0, effect='Giảm 8 điểm tinh thần; vẫn tiếp tục làm.')]
    if p['kind'] == 'wedding':
        return [dict(id='gift', label='Gửi phong bì chúc mừng', cost=p['wage']*2, effect='Chi từ quỹ kinh doanh, tăng 12 điểm tinh thần.'),
                dict(id='decline', label='Gửi lời chúc', cost=0, effect='Chúc mừng không kèm tiền; không phạt tinh thần.')]
    return [dict(id='retain', label='Thưởng để giữ nhân viên', cost=p['wage']*2, effect='Nhân viên ở lại, tăng 15 điểm tinh thần.'),
            dict(id='release', label='Đồng ý cho nghỉ', cost=0, effect='Kết thúc hợp tác sau khi khách đã nhận được phục vụ; giữ lương đã làm.')]


def public(c, quay=False):
    container = c if quay else c['ops']
    state = container.get('staff_life')
    out = dict(pending=None, recent=copy.deepcopy(state['recent']) if state else [], spent=state['spent'] if state else 0,
               employees=[dict(id=e['id'], name=e['name'], wage=wage(container,e), raise_amount=wage(container,e)-e['wage'],
                   morale=e.get('mo' if quay else 'morale',60)) for e in _members(container,quay)])
    if state and state['pending']:
        employee = next(e for e in _members(container,quay) if e['id']==state['pending']['employee'])
        p = out['pending'] = dict(_raise_quote(container,state['pending'],employee))
        p['title'] = TITLES['raise_' if p['kind']=='raise' else p['kind']]
        p['text'] = p['name'] + ': ' + {'raise':'Mình muốn được tăng lương sau những công việc vừa qua.',
             'raise_double':'Mình đề nghị mức lương gấp đôi hiện tại, tối đa 10.000 xu. Chủ tiệm cân nhắc nhé.',
             'wedding':'Mình sắp cưới, mời chủ tiệm chung vui.', 'quit':'Mình đang tính nghỉ việc. Chủ tiệm cân nhắc giúp mình nhé.'}[p['kind']]
        cash = c['fund']+c['till'] if quay else c['money']
        p['choices'] = [dict(row, affordable=cash>=row['cost']) for row in _choices(p,employee['wage'])]
    return out


def _choose(s,c,owner,p,quay):
    from .engine import need
    container = c if quay else c['ops']
    need(isinstance(p,dict) and set(p)<=({'stall','event','choice','confirm'} if quay else {'event','choice','confirm'}), 'Thông tin nhân viên không hợp lệ.')
    need(p.get('confirm') is True, 'Xác nhận xử lý việc của nhân viên.')
    state = container.get('staff_life');pending = state and state['pending']
    need(pending and pending['id']==p.get('event'), 'Việc của nhân viên đã được xử lý hoặc không còn chờ.', 'no_event')
    employee = next((e for e in _members(container,quay) if e['id']==pending['employee']),None)
    need(employee, 'Nhân viên đã nghỉ; tải lại sổ tiệm.', 'no_employee')
    pending = _raise_quote(container,pending,employee)
    choice = next((row for row in _choices(pending,employee['wage']) if row['id']==p.get('choice')),None)
    need(choice, 'Lựa chọn không hợp lệ.')
    cost = choice['cost'];cash = c['fund']+c['till'] if quay else c['money']
    need(cash>=cost, 'Quỹ không đủ; bạn có thể chọn phương án không tốn xu.', 'no_money')
    if choice['id']=='release':
        if quay:
            need(len(c['staff'])>1 or not any(r['status']=='queued' for r in c.get('business',{}).get('visitor_orders',[])), 'Phục vụ nốt khách đã nhận trước khi nhân viên cuối nghỉ.', 'staff_busy')
        else:
            from . import operations
            need(not any(r['staff']==employee['id'] and r['status']=='queued' for r in c.get('player_service_jobs',[])), 'Phục vụ nốt khách đã nhận trước khi cho nghỉ.', 'staff_busy')
            need(not operations.paused(container,employee), 'Xử lý xong sự cố của nhân viên trước khi cho nghỉ.', 'staff_busy')
    if choice['id']=='approve':
        old = state['raises'].get(employee['id'],0)
        limit = 10000-employee['wage'] if pending['kind']=='raise_double' else min(employee['wage'],10000-employee['wage'])
        extra = min(limit,old+pending['raise_by'])
        need(extra>old, 'Lương đã đạt mức tăng tối đa; chọn chưa tăng.', 'wage_cap')
    label = public(c,quay)['pending']['title'] + ' · ' + employee['name'] + ': ' + choice['label']
    if choice['id']=='approve':label += f" · Lương mới {employee['wage']+extra} xu"
    if quay:
        from . import quay as qy, quay_business as qb
        if cost:
            qy._from_till_fund(c,cost)
            c['business']['expenses']['loss'] += cost
            qb._profit_state(c)['costs'] += cost
            if 'income_tax' in c['business']:c['business']['income_tax']['loss'] += cost
        qy._log(c,s['journey']['life_day'],label,-cost)
    else:
        from . import operations, engine
        if cost:
            c['money']-=cost;c['costs']+=cost
            operations.record_money(c,-cost,label,pending['id'],'staff_life')
        engine.log(s,c,'staff',label,ref=pending['id'])
    mood = 'mo' if quay else 'morale'
    if choice['id']=='approve':state['raises'][employee['id']]=extra;employee[mood]=min(100,employee[mood]+10)
    elif choice['id'] in ('gift','retain'):employee[mood]=min(100,employee[mood]+(12 if choice['id']=='gift' else 15))
    elif pending['kind'] in ('raise','raise_double'):employee[mood]=max(0,employee[mood]-8)
    if choice['id']=='release':
        if quay:c['staff']=[e for e in c['staff'] if e['id']!=employee['id']]
        else:
            operations._payroll(c,c['day'],employee['id'])
            employee.update(status='former',on_shift=False)
            container.get('business',{}).get('pending',{}).pop(employee['id'],None)
        state['raises'].pop(employee['id'],None)
    row=dict(id=pending['id'],kind=pending['kind'],employee=employee['id'],name=employee['name'],choice=choice['id'],cost=cost,text=label)
    state['recent']=(state['recent']+[row])[-RECENT:];state['spent']+=cost
    state['pending']=None;state['next']=_progress(c,quay)+GAP
    if not quay:
        from . import workplace_business
        workplace_business.refresh(c,owner)
    return dict(message=label,staff_event=dict(row))


def choose_career(s,c,career,p):
    return _choose(s,c,career,p,False)


def choose_quay(s,st,p):
    return _choose(s,st,st['id'],p,True)


def validate(container,owner,quay=False):
    from .engine import need
    state=container.get('staff_life')
    if state is None:return
    def check(ok):need(ok,'Dữ liệu đời sống nhân viên không hợp lệ.','invalid_save')
    def integer(v,lo=0,hi=10**16):return type(v) is int and lo<=v<=hi
    check(isinstance(state,dict) and set(state)=={'v','seq','next','pending','recent','spent','raises'})
    check(type(state['v']) is int and state['v']==1)
    check(all(integer(state[k]) for k in ('seq','next','spent')))
    roster={e['id']:e for e in container.get('staff',[])}
    check(isinstance(state['raises'],dict) and len(state['raises'])<=4)
    for sid,extra in state['raises'].items():check(sid in roster and integer(extra,0,10000-roster[sid]['wage']))
    prefix='staff-'+owner+'-'
    def valid_id(ref):return isinstance(ref,str) and ref.startswith(prefix) and ref[len(prefix):].isdigit() and 0<int(ref[len(prefix):])<=state['seq']
    p=state['pending']
    if p is not None:
        check(isinstance(p,dict) and set(p)=={'id','kind','employee','name','wage','raise_by'})
        check(valid_id(p['id']) and p['kind'] in KINDS and p['employee'] in roster)
        check(p['name']==roster[p['employee']]['name'] and integer(p['wage'],1,10000) and integer(p['raise_by'],1,5000 if p['kind']=='raise_double' else 1000))
        if p['kind']=='raise_double':check(p['raise_by']==min(p['wage'],10000-p['wage']))
    check(isinstance(state['recent'],list) and len(state['recent'])<=RECENT)
    ids=set()
    for row in state['recent']:
        check(isinstance(row,dict) and set(row)=={'id','kind','employee','name','choice','cost','text'})
        check(valid_id(row['id']) and row['id'] not in ids and row['kind'] in KINDS);ids.add(row['id'])
        check(all(isinstance(row[k],str) and 0<len(row[k])<=500 for k in ('employee','name','text')))
        check(row['choice'] in {'raise':('approve','decline'),'raise_double':('approve','decline'),'wedding':('gift','decline'),'quit':('retain','release')}[row['kind']] and integer(row['cost'],0,20000))
    check(sum(row['cost'] for row in state['recent'])<=state['spent'])
    check(p is None or p['id'] not in ids)
