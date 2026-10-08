"""Mutual family consent; one shared child, VN calendar care, personal custody copies.

Personal journey.household children/pets are never changed. On separation each
parent keeps an independent copy here; deleting an account removes only its copy.
Home ownership, mortgages and furniture remain with their original owners.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re

from . import household as hh, housing as hs, marriage as mr, archive as ar, cradle as cr
from .engine import GameError, migrate_state, validate_state

VN = datetime.timezone(datetime.timedelta(hours=7))
BIRTH_WAIT_DAYS = 1


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def today():
    return datetime.datetime.fromtimestamp(mr.now(), VN).date().isoformat()


def _need(ok, message, code='bad_family', status=400):
    mr.need(ok, message, code, status)


def _name(value):
    try:
        return hh._name(value)
    except GameError as e:
        raise mr.MarriageError(e.message, e.code, 400) from None


def _ready(state):
    j = state.get('journey') or {}
    return bool(j.get('story')) and int(j.get('life_day') or 0) >= 10


def _child(name, origin):
    born = datetime.date.fromisoformat(today()) + datetime.timedelta(days=BIRTH_WAIT_DAYS if origin == 'birth' else 0)
    return dict(name=name, origin=origin, born=born.isoformat(), day='', did=[], care_days=0,
                bond=0, food=65, clean=65, joy=65, outfit='basic', owned=['basic'])


def _public(data, child_id, personal=False):
    m = dict(data)
    days = m['care_days']
    waiting = today() < m['born']
    done = m['did'] if m['day'] == today() else []
    age = 0 if waiting else cr.calendar_age(m['born'], today())   # 👶 how the baby is drawn (game/cradle.py)
    return dict(id=child_id, name=m['name'], kind='child', emoji='👶', origin=m['origin'], born=m['born'], waiting=waiting,
                age=age, grow=cr.grow(age),
                personal=personal, care_days=days, stage='Chờ đón bé' if waiting else 'Em bé' if days < 5 else 'Bé tập đi' if days < 20 else 'Bé đi học',
                bond=m['bond'], needs={k:m[k] for k in ('food','clean','joy')}, outfit=m['outfit'], owned=m['owned'],
                acts=[dict(id=k, **x, done=waiting or x['slot'] in done) for k,x in hh.ACTS.items() if 'child' in x['kinds']])


def view(db, sid, c, state):
    out = dict(day=today(), clock='Ngày lịch Việt Nam (UTC+7)', child=None, copies=[], requests=[], together=False,
               can_invite=False, can_leave=False, ready=False, home_name='', partner_can_invite=False, partner_home_name='',
               eligibility=dict(self_day=(state.get('journey') or {}).get('life_day',0), partner_day=0, min_day=10,
                                self_story=bool((state.get('journey') or {}).get('story')),partner_story=False),
               outfits=[dict(id=k, **v) for k,v in hh.OUTFITS.items()])
    for r in db.execute('SELECT child,state FROM family_custody WHERE sid=? ORDER BY child', (sid,)):
        out['copies'].append(_public(json.loads(r['state']), f'copy:{r["child"]}', True))
    if not c or c['status'] != 'married':
        return out
    child = db.execute('SELECT state FROM family_children WHERE couple=?', (c['id'],)).fetchone()
    if child:
        out['child'] = _public(json.loads(child['state']), 'shared')
    for r in db.execute("SELECT id,kind,data,from_sid FROM family_requests WHERE couple=? AND status='pending' ORDER BY id", (c['id'],)):
        payload = json.loads(r['data'])
        out['requests'].append(dict(id=r['id'], kind=r['kind'], mine=r['from_sid']==sid, name=payload.get('name',''),
                                    origin=payload.get('origin'), home=hs.HOMES.get(payload.get('kind'),{}).get('name','')))
    home = hs.get(state)
    own = home and home['own']
    out['can_invite'] = bool(own)
    out['can_leave'] = bool(home and home['shared'] and home['shared']['couple']==c['id'])
    out['home_name'] = hs.HOMES[own['kind']]['name'] if own else ''
    other = db.execute('SELECT state FROM sessions WHERE sid=?', (mr._other(c,sid),)).fetchone()
    if other:
        from .deco_mate import same_home
        partner=json.loads(other['state']); pj=partner.get('journey') or {}
        out['eligibility'].update(partner_day=pj.get('life_day',0),partner_story=bool(pj.get('story')))
        out['ready']=_ready(state) and _ready(partner)
        ph=hs.get(partner); po=ph and ph['own']
        out['partner_can_invite']=bool(po)
        out['partner_home_name']=hs.HOMES[po['kind']]['name'] if po else ''
        out['together'] = same_home(state.get('journey') or {}, pj, c['id'])
    return out


def babies(store, token) -> dict:
    """GET /api/family/baby: the shared child and the custody copies as the home room draws them (👶 game/cradle.py),
    {child, copies, day}. Light (no save is read or written); {} without a session. Never raises: a home never blocks."""
    try:
        sid = store.key(token) if token else None
        if not sid:
            return {}
        out = dict(day=today(), child=None, copies=[], acts=cr.catalog())
        with store.connect() as db:
            for r in db.execute('SELECT child,state FROM family_custody WHERE sid=? ORDER BY child', (sid,)):
                out['copies'].append(_public(json.loads(r['state']), f'copy:{r["child"]}', True))
            c = mr._bond(db, sid)
            if c and c['status'] == 'married':
                row = db.execute('SELECT state FROM family_children WHERE couple=?', (c['id'],)).fetchone()
                if row:
                    out['child'] = _public(json.loads(row['state']), 'shared')
        return out
    except Exception:  # noqa: BLE001
        return {}


def _save(db, sid, state, cut):
    from .storage import serialize, _write_archive
    validate_state(state)
    mr.validate_save(state)
    from . import rentals
    old = db.execute('SELECT state FROM sessions WHERE sid=?', (sid,)).fetchone()
    if old:
        rentals.command_commit(db, sid, json.loads(old['state']), state, 'family')
    db.execute('UPDATE sessions SET state=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE sid=?', (serialize(state,None,True),sid))
    _write_archive(db,sid,cut)


def act(store, sid, op, p):
    rid = p.get('rid')
    _need(isinstance(rid,str) and re.fullmatch(r'[A-Za-z0-9_-]{8,64}',rid), 'Thiếu mã thao tác. Tải lại rồi thử nhé.', 'bad_rid')
    fingerprint = hashlib.sha256(_json({k:v for k,v in p.items() if k!='rid'}).encode()).hexdigest()
    with store.connect() as db:
        snapshot = mr._bond(db,sid)
    shared = p.get('child','shared') == 'shared'
    needs_couple = op in ('family_child_request','family_home_request','family_answer','family_cancel','family_home_leave') or shared
    if needs_couple:
        _need(snapshot and snapshot['status']=='married', 'Cần kết hôn để dùng gia đình chung.', 'not_married',409)
    members = sorted({sid, mr._other(snapshot,sid)} if snapshot and snapshot['status']=='married' else {sid})

    def run(db):
        from .storage import _archive_rows
        states, before, cuts = {}, {}, {}
        for who in members:
            row = db.execute('SELECT state FROM sessions WHERE sid=? FOR UPDATE',(who,)).fetchone()
            _need(row, 'Không tìm thấy tiến trình.', 'session_missing',404)
            with ar.collect() as box:
                raw = store.parse_state(row['state'],who)
                before[who] = dict(raw.get('careers') or {})
                states[who] = migrate_state(raw,owned=True)
            cuts[who] = _archive_rows(box,before[who],states[who],'')
        receipt = db.execute('SELECT op,fingerprint,result FROM family_receipts WHERE sid=? AND rid=?',(sid,rid)).fetchone()
        if receipt:
            _need(receipt['op']==op and receipt['fingerprint']==fingerprint, 'Mã thao tác đã dùng cho việc khác.', 'request_conflict',409)
            return json.loads(receipt['result'])
        c = mr._row(db,'SELECT * FROM couples WHERE id=? FOR UPDATE',(snapshot['id'],)) if snapshot else None
        if needs_couple:
            _need(c and c['status']=='married' and mr._bond(db,sid) and mr._bond(db,sid)['id']==c['id'], 'Hai bạn không còn là vợ chồng.', 'not_married',409)
        changed = set()
        with ar.collect() as box:
            message = _apply(db,sid,c,states,op,p,rid,changed)
        cuts[sid].extend(_archive_rows(box,before[sid],states[sid],''))
        for who in sorted(changed): _save(db,who,states[who],cuts[who])
        result = dict(message=message,changed=bool(changed))
        if op=='family_child_moment': result['quiet'] = True   # 👶 the room reloads /api/family/baby: no heavy marriage view
        db.execute('INSERT INTO family_receipts(sid,rid,op,fingerprint,result,at) VALUES(?,?,?,?,?,?)',(sid,rid,op,fingerprint,_json(result),mr.now()))
        return result
    return store.transaction(run)


def _apply(db,sid,c,states,op,p,rid,changed):
    state = states[sid]
    if op in ('family_child_request','family_home_request'):
        other = mr._other(c,sid)
        kind = 'child' if op=='family_child_request' else 'home'
        _need(all(bool((s.get('journey') or {}).get('story')) for s in states.values()),'Cả hai cần mở hành trình.','locked')
        if kind=='child':
            _need(_ready(state) and _ready(states[other]), 'Cả hai mở hành trình đến ngày sống 10 trước nhé.', 'locked')
        _need(not db.execute("SELECT 1 FROM family_requests WHERE couple=? AND kind=? AND status='pending'",(c['id'],kind)).fetchone(), 'Đã có lời mời đang chờ trả lời.', 'pending',409)
        if kind=='child':
            _need(not db.execute('SELECT 1 FROM family_children WHERE couple=?',(c['id'],)).fetchone(), 'Hai bạn đã có con chung.', 'already_owned',409)
            origin = p.get('origin','adopt')
            _need(origin in ('adopt','birth'), 'Chọn nhận nuôi hoặc đón bé mới sinh.')
            data = dict(name=_name(p.get('name')),origin=origin)
        else:
            home = hs.get(state)
            own = home and home['own']
            _need(own, 'Dọn vào căn nhà của bạn trước khi mời người ấy.', 'no_home')
            data = dict(id=own['id'],kind=own['kind'],mv=own.get('mv',0),name=state.get('name') or mr._display(db,sid))
        db.execute('INSERT INTO family_requests(couple,from_sid,to_sid,kind,data,at) VALUES(?,?,?,?,?,?)',(c['id'],sid,other,kind,_json(data),mr.now()))
        mr._notice(db,other,'🏡 Có lời mời đang chờ bạn trả lời. Mở Nhà & Gia đình để xem nhé.')
        return 'Đã gửi lời mời. Chỉ thay đổi khi người ấy đồng ý.'
    if op in ('family_answer','family_cancel'):
        ident = p.get('id')
        _need(type(ident) is int, 'Chọn lời mời hợp lệ.')
        request = mr._row(db,'SELECT * FROM family_requests WHERE id=? AND couple=? FOR UPDATE',(ident,c['id']))
        _need(request and request['status']=='pending','Lời mời đã được trả lời hoặc hủy.','stale',409)
        if op=='family_cancel':
            _need(request['from_sid']==sid,'Chỉ người gửi được hủy lời mời.','forbidden',403)
            db.execute("UPDATE family_requests SET status='cancelled' WHERE id=?",(ident,))
            return 'Đã hủy lời mời.'
        _need(request['to_sid']==sid,'Chỉ người được mời mới trả lời.','forbidden',403)
        answer = p.get('answer')
        _need(answer in ('accept','decline'),'Chọn đồng ý hoặc từ chối.')
        if answer=='accept':
            _need(all(bool((s.get('journey') or {}).get('story')) for s in states.values()),'Cả hai cần mở hành trình.','locked')
            data = json.loads(request['data'])
            if request['kind']=='child':
                _need(all(_ready(s) for s in states.values()),'Cả hai cần hành trình từ ngày sống 10.','locked')
                _need(not db.execute('SELECT 1 FROM family_children WHERE couple=?',(c['id'],)).fetchone(),'Hai bạn đã có con chung.','already_owned',409)
                db.execute('INSERT INTO family_children(couple,state) VALUES(?,?)',(c['id'],_json(_child(data['name'],data['origin']))))
            else:
                sender = states[request['from_sid']]
                home = hs.get(sender)
                own = home and home['own']
                _need(own and own['id']==data['id'] and own['kind']==data['kind'] and own.get('mv',0)==data['mv'],'Căn nhà đã thay đổi. Nhờ người ấy gửi lời mời mới.','stale_home',409)
                hs.accept_shared(state, dict(data,couple=c['id']))
                changed.add(sid)
        db.execute('UPDATE family_requests SET status=? WHERE id=?',(answer,ident))
        mr._notice(db,request['from_sid'],'🏡 Người ấy đã '+('đồng ý' if answer=='accept' else 'từ chối')+' lời mời gia đình.')
        return 'Đã đồng ý lời mời.' if answer=='accept' else 'Đã từ chối. Tiến trình và tiền của bạn không thay đổi.'
    if op=='family_home_leave':
        home = hs.get(state)
        _need(home and home['shared'] and home['shared']['couple']==c['id'],'Bạn chưa ở nhà chung.','no_shared')
        hs.leave_shared(state)
        changed.add(sid)
        return 'Đã dọn khỏi nhà chung. Nhà và đồ cá nhân vẫn thuộc về mỗi người.'
    _need(op in ('family_child_care','family_child_style','family_child_rename','family_child_moment'),'Không có thao tác gia đình này.','not_found',404)
    target = p.get('child','shared')
    if target=='shared':
        row = db.execute('SELECT state FROM family_children WHERE couple=? FOR UPDATE',(c['id'],)).fetchone()
        table,where,args = 'family_children','couple=?',(c['id'],)
    else:
        _need(isinstance(target,str) and re.fullmatch(r'copy:[1-9][0-9]*',target),'Chọn em bé hợp lệ.')
        child = int(target.split(':')[1])
        row = db.execute('SELECT state FROM family_custody WHERE child=? AND sid=? FOR UPDATE',(child,sid)).fetchone()
        table,where,args = 'family_custody','child=? AND sid=?',(child,sid)
    _need(row,'Chưa có em bé này.','not_found',404)
    data = json.loads(row['state'])
    _need(today()>=data['born'],'Gia đình đang chờ đón bé. Quay lại vào '+data['born']+'.','waiting')
    cost,label = 0,''
    if op=='family_child_moment':   # 👶 a free moment at home (game/cradle.py): the player's tinh thần, the baby's gắn bó
        try:
            out = cr.moment(state, target, p.get('act'), data['name'], cr.grow(cr.calendar_age(data['born'], today())))
        except GameError as e:
            raise mr.MarriageError(e.message, e.code, 409 if e.code=='already_done' else 400) from None
        changed.add(sid)
        data['bond']=min(100,data['bond']+1)
        db.execute(f'UPDATE {table} SET state=?,revision=revision+1 WHERE {where}',(_json(data),*args))
        return out['message']
    if op=='family_child_rename':
        data['name']=_name(p.get('name'))
    elif op=='family_child_style':
        item = p.get('item')
        _need(isinstance(item,str) and item in hh.OUTFITS,'Chọn bộ đồ cho bé.')
        if item not in data['owned']:
            cost,label = hh.OUTFITS[item]['cost'],hh.OUTFITS[item]['name']
            data['owned'].append(item)
        data['outfit']=item
    else:
        aid = p.get('act')
        _need(isinstance(aid,str) and aid in hh.ACTS and 'child' in hh.ACTS[aid]['kinds'],'Chọn việc chăm bé hợp lệ.')
        x = hh.ACTS[aid]
        done = data['did'] if data['day']==today() else []
        _need(x['slot'] not in done,'Hôm nay đã chăm phần này rồi.','already_done',409)
        if not done: data['care_days']+=1
        data['day'],data['did']=today(),done+[x['slot']]
        data[x['slot']]=min(100,data[x['slot']]+35)
        data['bond']=min(100,data['bond']+2)
        cost,label=x['cost'],x['name']
    if cost:
        how=p.get('pay','auto')
        _need(how in ('auto','cash','account','card'),'Chọn tiền mặt, tài khoản hoặc thẻ cá nhân. Quỹ chung dùng ở mục Quỹ chung.','bad_payment')
        how=cr.no_credit(state,cost,how)   # 👶 a baby never goes on credit
        effect_id='family:'+hashlib.sha256(f'{sid}:{rid}'.encode()).hexdigest()[:48]
        eff=mr._effect(effect_id,sid,'wallet',-cost,label)
        _need(mr._can_spend(state,cost,how),'Chưa đủ tiền chăm bé.','not_enough')
        mr._spend(state,eff,how)
        changed.add(sid)
    db.execute(f'UPDATE {table} SET state=?,revision=revision+1 WHERE {where}',(_json(data),*args))
    return 'Đã chăm sóc '+data['name']+'.' if op=='family_child_care' else 'Đã cập nhật '+data['name']+'.'


def end(db,c,deleted=None):
    """Inside the relationship-end transaction: preserve each surviving parent's private copy."""
    child=db.execute('SELECT state FROM family_children WHERE couple=? FOR UPDATE',(c['id'],)).fetchone()
    if child:
        for sid in (c['a'],c['b']):
            if sid!=deleted:
                db.execute('INSERT INTO family_custody(child,sid,state) VALUES(?,?,?) ON CONFLICT DO NOTHING',(c['id'],sid,child['state']))
        db.execute('DELETE FROM family_children WHERE couple=?',(c['id'],))
    db.execute("UPDATE family_requests SET status='cancelled' WHERE couple=? AND status='pending'",(c['id'],))
    if deleted:
        forget(db, deleted)


def forget(db, sid):
    db.execute('DELETE FROM family_custody WHERE sid=?',(sid,))
    db.execute('DELETE FROM family_requests WHERE from_sid=? OR to_sid=?',(sid,sid))
    db.execute('DELETE FROM family_receipts WHERE sid=?',(sid,))


ACTIONS={name:(lambda store,sid,display,p,op=name:act(store,sid,op,p)) for name in (
    'family_child_request','family_home_request','family_answer','family_cancel','family_home_leave',
    'family_child_care','family_child_style','family_child_rename','family_child_moment')}
