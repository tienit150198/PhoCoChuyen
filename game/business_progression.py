"""Owner-wide business rights. Evaluation is pure; only owner access delivers notice."""
import os
import time
from . import certificates

CERTS = ('business_basics', 'business_advanced', 'business_chain')
GRACE_SECONDS = 72 * 3600
KEY = 'business_license'
REASON = 'Cần hoàn thành chứng chỉ kinh doanh để nhận đơn mới tại quầy này.'


def enabled():
    return os.environ.get('MNL_BUSINESS_INSPECTIONS_OFF') != '1'


def _quay(s):
    return (s.get('journey') or {}).get('quay') or {}


def level(s):
    return max((i for i, gid in enumerate(CERTS, 1) if certificates.earned(s.get('journey'), gid)), default=0)


def required(stalls):
    kiots = sum(st['place'] == 'kiot' for st in stalls)
    return 3 if kiots >= 3 else 2 if kiots else 1 if len(stalls) > 1 or any(st['place'] == 'sap' for st in stalls) else 0


def open_requirement(s, place, replace_id=None):
    stalls = [st for st in _quay(s).get('stalls', []) if st['id'] != replace_id] + [dict(place=place)]
    need = required(stalls)
    held = level(s)
    allowed = held >= need or os.environ.get('MNL_BUSINESS_LICENSES_OFF') == '1'
    next_cert = CERTS[held] if held < need else None
    reason = '' if allowed else 'Cần ' + certificates.INDEX[CERTS[need-1]]['name'] + ' trước khi mở hoặc mở rộng quầy.'
    return dict(allowed=allowed, required_level=need, next_cert=next_cert, reason=reason)


def snapshot(s):
    q = _quay(s)
    if not q or KEY in q:
        return False
    q[KEY] = dict(v=1, legacy_ids=sorted(st['id'] for st in q.get('stalls', [])),
                  preferred_ids=[], issued_at=None, deadline=None)
    return True


def _eligible(stalls, held, case):
    ids = {st['id'] for st in stalls}
    preferred = [sid for sid in case.get('preferred_ids', []) if sid in ids]
    order = preferred + sorted(ids - set(preferred))
    byid = {st['id']: st for st in stalls}
    if held >= 3:
        return order
    small = [sid for sid in order if byid[sid]['place'] != 'kiot']
    kiots = [sid for sid in order if byid[sid]['place'] == 'kiot']
    allowed = small + (kiots[:2] if held >= 2 else []) if held >= 1 else []
    if not allowed:
        legacy = set(case.get('legacy_ids', []))
        # Prefer a cart within level-zero rights, then one existing livelihood.
        suitable = [sid for sid in order if byid[sid]['place'] == 'xe'] if held == 0 else []
        allowed = suitable[:1] or [sid for sid in order if sid in legacy][:1]
    return allowed


def evaluate(s, now=None):
    at = int((time.time() if now is None else now) * 1000)
    q = _quay(s); stalls = q.get('stalls', [])
    case = q.get(KEY) or {}; held = level(s); need = required(stalls)
    ids = sorted(st['id'] for st in stalls)
    eligible = _eligible(stalls, held, case)
    issued = case.get('issued_at'); deadline = case.get('deadline')
    live = enabled()
    status = ('compliant' if held >= need else 'not_required')
    if live and issued is not None:
        status = 'compliant' if set(eligible) == set(ids) else 'grace' if at < deadline else 'restricted'
    blocked = sorted(set(ids)-set(eligible)) if status == 'restricted' else []
    courses = [dict(id=gid, name=certificates.INDEX[gid]['name'],
                    fee=certificates.tuition(gid), enrol_fee=certificates.fee(s.get('journey') or {},gid,'class'),
                    earned=certificates.earned(s.get('journey'),gid)) for gid in CERTS]
    return dict(level=held, required_level=need, required_cert=CERTS[need-1] if need else None,
                next_cert=CERTS[held] if held < need else None, courses=courses, status=status,
                issued_at=issued/1000 if issued is not None else None,
                deadline=deadline/1000 if deadline is not None else None,
                allowed_ids=[sid for sid in ids if sid not in blocked], blocked_ids=blocked,
                preferred_ids=list(case.get('preferred_ids', [])), grace_seconds=GRACE_SECONDS,
                enabled=live, reason=REASON if blocked else 'Hoàn thành chứng chỉ trong 72 giờ kể từ thông báo.' if status == 'grace' else '')


def owner_due(s, now=None):
    q=_quay(s)
    return bool(q and (KEY not in q or (enabled() and len(q.get('stalls', [])) >= 3
                and q[KEY].get('issued_at') is None and level(s) < required(q['stalls']))))


def owner_access(s, now=None):
    changed=snapshot(s);q=_quay(s)
    if not q or not enabled():return changed
    case=q[KEY]
    if len(q.get('stalls', [])) >= 3 and case['issued_at'] is None and level(s) < required(q['stalls']):
        at=int((time.time() if now is None else now)*1000)
        case.update(issued_at=at, deadline=at+GRACE_SECONDS*1000)
        changed=True
    return changed


def due(s, now=None):
    policy=evaluate(s,now)
    blocked=set(policy['blocked_ids'])
    return any(bool(st.get('business',{}).get('certificate_block')) != (st['id'] in blocked)
               for st in _quay(s).get('stalls',[]))


def reconcile(s, now=None):
    from . import quay_business as qb, quay_self as qs
    at=int((time.time() if now is None else now)*1000)
    policy=evaluate(s,at/1000);blocked=set(policy['blocked_ids']);changed=False
    for st in _quay(s).get('stalls',[]):
        b=st.get('business')
        if b is None:continue
        was=bool(b.get('certificate_block'));new=st['id'] in blocked
        if was == new:continue
        b['certificate_block']=new;changed=True
        if new:
            # Settlement stops at the original deadline on first expiry. A later
            # priority change settles the previously allowed stall up to now;
            # never backdate that transition and erase its accepted orders.
            b['certificate_closed_at']=min(at,max(b['cursor'],int(policy['deadline']*1000)))
        else:
            old=b.pop('certificate_closed_at',b['cursor'])
            b['cursor']=max(b['cursor'],at)
            b['arrivals']=qb._fresh(b['cursor'],qb._intervals(st))
            qs.reopen_queue(st,closed_at=old-1)
    return changed


def cutoff(st):
    """Last eligible arrival millisecond (license deadline is exclusive)."""
    b=st.get('business',{});limits=[]
    if b.get('paused'):limits.append(b.get('closed_at',0))
    if b.get('certificate_block'):limits.append(b.get('certificate_closed_at',0)-1)
    return min(limits) if limits else None


def can_arrive(st, at=None):
    stop=cutoff(st)
    return stop is None or (at is not None and at <= stop)


def choose(s,p):
    from .engine import need
    ids={st['id'] for st in _quay(s).get('stalls',[])}
    rows=p.get('stalls')
    need(set(p)=={'stalls'} and isinstance(rows,list) and all(isinstance(x,str) for x in rows)
         and len(rows)==len(set(rows)) and set(rows)<=ids,'Chọn các quầy đang sở hữu, mỗi quầy một lần.')
    snapshot(s)
    _quay(s)[KEY]['preferred_ids']=list(rows)
    return dict(message='Đã lưu thứ tự ưu tiên quầy trong phạm vi chứng chỉ hiện có.')


def validate(q, need, integer):
    if KEY not in q:return
    c=q[KEY]
    need(isinstance(c,dict) and set(c)=={'v','legacy_ids','preferred_ids','issued_at','deadline'} and c['v']==1)
    import re
    for key in ('legacy_ids','preferred_ids'):
        rows=c[key]
        need(isinstance(rows,list) and all(isinstance(x,str) and re.fullmatch(r'q[0-9]+',x) for x in rows) and len(rows)==len(set(rows)))
    need((c['issued_at'] is None and c['deadline'] is None) or
         (integer(c['issued_at'],0,10**15) and integer(c['deadline'],0,10**15)
          and c['deadline']==c['issued_at']+GRACE_SECONDS*1000))
