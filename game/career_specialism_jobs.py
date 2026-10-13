"""One commissioned specialist job, sharing the management start allowance."""
import copy
import hashlib
from . import career_specialism_stock as stock, career_scale_quota as quota
from .career_scale_finance import move
from .career_scale_content import profile
from .career_specialism_content import pack

NET=(200,400,800,1500,3000,8000,18000,40000,100000,250000)
QUANTITIES=(1,2,4,8,20,50,100,200,500,1000)
ACTIONS={'special_offer','special_cancel','special_start','special_work','special_settle'}
JOB_KEYS={'id','tier','quantity','quote','step','answers','held','escrow','phase','created'}


def kind(cid):return profile(cid).kind


def need(ok,message='Dữ liệu đơn chuyên môn không hợp lệ.'):stock.need(ok,message)


def quote(cid,tier,quantity):
    k=kind(cid);net=NET[tier-1]*quantity//QUANTITIES[tier-1]
    material_cost=sum(m['bundle_cost']*quantity for m in stock.materials(cid,tier)) if k=='business' else 0
    # Authored material bill plus labor/subcontracting; the target is per whole order.
    wages=max(quantity*5,net//5) if k=='business' else 0
    revenue=(100*(material_cost+wages+net)+95)//96 if k=='business' else net if k=='agency' else 0
    tax=(revenue*4+99)//100 if k=='business' else 0
    return dict(revenue=revenue,materials=material_cost,wages=wages,premises=0,loss=0,tax=tax,net=revenue-material_cost-wages-tax)


def score(cid,tier,answers,quantity,salt):
    from .career_specialism import exercise
    correct=[answer==exercise(cid,tier,i,quantity,salt)['answer'] for i,answer in enumerate(answers)]
    return sum(correct)*20 if len(correct)==5 and correct[0] and correct[4] else 0


def action(s,c,cid,name,p,now):
    from . import career_specialism as sp
    r=sp.record(c);o=r['job'];k=kind(cid)
    if name=='special_offer':
        need(set(p)=={'tier'});tier=stock.integer(p['tier'],1,r['tier'])
        need(o is None or o['phase']=='cancelled','Hoàn tất hoặc tiếp tục đơn đang giữ trước nhé.')
        if o is not None:
            need(tier==o['tier'],'Khách đã giữ yêu cầu; nhận lại đúng gói đang lưu.')
            o=copy.deepcopy(o);o['phase']='offered'
        else:
            need(r['seq']<10**9);seq=r['seq']+1
            # Stable quantity/demand survives cancellation; no free customer reroll.
            digest=hashlib.sha256(f"{s['journey'].get('seed',0)}|{cid}|special|{seq}".encode()).digest()
            demand=100 if seq==1 else (100,80,60)[digest[0]%3]
            quantity=max(1,QUANTITIES[tier-1]*demand//100)
            o=dict(id=f'{cid}_special-{seq}',tier=tier,quantity=quantity,quote=quote(cid,tier,quantity),
                step=0,answers=[],held=[],escrow=0,phase='offered',created=now)
        if k!='community':quota.reserve(s,o['id'],now)
        if r['job'] is None:r['seq']+=1
        r['job']=o;c[sp.KEY]=r
        return dict(message='Đã giữ yêu cầu khách và suất chung. Kiểm vật tư trước khi bắt đầu.')
    need(o is not None and type(p.get('id')) is str and p['id']==o['id'],'Đơn đã thay đổi hoặc đã quyết toán.')
    if name=='special_cancel':
        need(set(p)=={'id'} and o['phase']=='offered','Chỉ hủy miễn phí trước khi bắt đầu.')
        if k!='community':quota.cancel(s,o['id'],now)
        o['phase']='cancelled'
        return dict(message='Đã trả suất; giữ nguyên yêu cầu khách để nhận lại.')
    if name=='special_start':
        need(set(p)=={'id'} and o['phase']=='offered')
        need(not any((x.get('specialism',{}).get('job') or {}).get('phase') in ('working','acceptance') for x in s['careers'].values()),'Hoàn tất đơn chuyên môn đang trực tiếp làm trước nhé.')
        requirements=[dict(code=m['code'],quantity=o['quantity']) for m in stock.materials(cid,o['tier'])]
        if k=='business':
            need(all(stock.units(c,x['code'])>=x['quantity'] for x in requirements),'Chưa nhận đủ vật tư cho đơn.')
        escrow=o['quote']['wages']+o['quote']['tax'] if k=='business' else 0
        need(c['money']>=escrow,'Quỹ nghề chưa đủ tiền công và thuế dự phòng.')
        if k!='community':need(quota.public(s,now)['reserved']==o['id'],'Suất đã thay đổi.')
        if k=='business':o['held']=stock.take(c,requirements)
        if k!='community':quota.start(s,o['id'],now)
        if escrow:move(s,c,-escrow,'Cam kết tiền công và thuế đơn chuyên môn',o['id'],category='scale_special_escrow')
        o.update(escrow=escrow,phase='working')
        return dict(message='Đã giữ vật tư và vốn. Làm theo yêu cầu khách trước khi bàn giao.')
    if name=='special_work':
        need(set(p)=={'id','step','answer'} and o['phase']=='working')
        step=stock.integer(p['step'],0,4);need(step==o['step'],'Bước công việc đã thay đổi.')
        question=sp.exercise(cid,o['tier'],step,o['quantity'],o['id']);sp.validate_answer(question,p['answer'])
        o['answers'].append(p['answer']);o['step']+=1
        if o['step']==5:o['phase']='acceptance'
        return dict(message='Đã lưu bằng chứng thao tác. Kết quả được đối soát khi bàn giao.')
    need(name=='special_settle' and set(p)=={'id'} and o['phase']=='acceptance')
    quality=score(cid,o['tier'],o['answers'],o['quantity'],o['id']);q=o['quote']
    revenue=q['revenue']*quality//100;tax=(revenue*4+99)//100 if k=='business' else 0
    materials=sum(x['quantity']*x['unit_cost'] for x in o['held'])
    refund=o['escrow']-q['wages']-tax;need(refund>=0)
    if refund:move(s,c,refund,'Hoàn thuế dự phòng chưa dùng',o['id'],category='scale_special_refund')
    if revenue:move(s,c,revenue,'Nghiệm thu đơn chuyên môn' if k=='business' else 'Phụ cấp chuyên môn',o['id'],category='scale_special_settlement')
    receipt=dict(id=o['id'],tier=o['tier'],title=pack(cid,o['tier'])['title'],quantity=o['quantity'],quality=quality,
        revenue=revenue,materials=materials,wages=q['wages'],premises=0,loss=0,tax=tax,
        net=revenue-materials-q['wages']-tax,escrow=o['escrow'],refund=refund,at=now,
        message=f'Nghiệm thu {quality}%. '+('Hoàn thành đủ yêu cầu.' if quality==100 else 'Có bước sai; tiền trả theo phần nghiệm thu, vật tư và công đã dùng vẫn mất.'),
        evidence=[('Đúng. ' if o['answers'][i]==sp.exercise(cid,o['tier'],i,o['quantity'],o['id'])['answer'] else 'Sai. ')+sp.exercise(cid,o['tier'],i,o['quantity'],o['id'])['why'] for i in range(5)])
    if quality>=80:
        from . import career_scale,needs
        career_scale.accepted(c,cid,now)
        if k=='community':receipt['spirit']=needs._spirit(s,3)
    r['history'].append(receipt);del r['history'][:-30];r['job']=None
    return dict(message=receipt['message'],receipt=copy.deepcopy(receipt))


def public(s,c,cid,now):
    from . import career_specialism as sp
    r=sp.record(c);o=r['job'];actions=[]
    if not o or o['phase']=='cancelled':
        tiers=[o['tier']] if o else range(1,r['tier']+1)
        for tier in tiers:
            actions.append(sp.button('special_offer',('Nhận lại: ' if o else 'Khách đặt: ')+pack(cid,tier)['title'],dict(tier=tier)))
        return None,actions
    p=pack(cid,o['tier']);q=o['quote']
    v=dict(title=p['title'],description=f"Khách yêu cầu {o['quantity']:,} {p['output_unit']}. Đơn {o['id']}",quantity=o['quantity'],unit=p['output_unit'],
        phase=o['phase'],quote=copy.deepcopy(q),instructions=[],detail='',actions=actions)
    if o['phase']=='offered':
        v['instructions']=[f"{m['name']}: {o['quantity']*m['quantity']:,} {m['unit']} ({o['quantity']:,} bộ vật tư)" for m in stock.materials(cid,o['tier'])]
        v['detail']=f"Cam kết thêm {q['wages']+q['tax']:,} xu tiền công/thuế sau khi nhập hàng." if kind(cid)=='business' else 'Vật tư do đơn vị cấp; chỉ phụ cấp nghiệm thu là thu nhập cá nhân.'
        if kind(cid)=='business':
            revenue80=q['revenue']*80//100;net80=revenue80-q['materials']-q['wages']-(revenue80*4+99)//100
            v['detail']+=f" Dự toán giả định đúng 100%. Nghiệm thu 80% còn {net80:+,} xu sau chi phí; sai định lượng hoặc kiểm bàn giao thì không có doanh thu, mất vật tư và công. Giá vốn thực tế theo lô đã nhập."
        actions.extend([sp.button('special_start','Bắt đầu thực hiện',dict(id=o['id'])),sp.button('special_cancel','Hủy trước bắt đầu · trả suất',dict(id=o['id']))])
    elif o['phase']=='working':
        question=sp.exercise(cid,o['tier'],o['step'],o['quantity'],o['id'])
        v['detail']=f"Bước {o['step']+1}/5 · {question['prompt']}"
        actions.append(sp.question_button('special_work',dict(id=o['id'],step=o['step']),question))
    else:actions.append(sp.button('special_settle','Nghiệm thu và quyết toán',dict(id=o['id'])))
    return v,[]


def validate(c,cid):
    from . import career_specialism as sp
    r=c[sp.KEY];o=r['job']
    if o is None:return
    need(type(o) is dict and set(o)==JOB_KEYS)
    need(type(o['id']) is str and o['id']==f"{cid}_special-{r['seq']}")
    stock.integer(o['tier'],1,r['tier']);stock.integer(o['quantity'],1,QUANTITIES[o['tier']-1]);stock.integer(o['created'],0,10**11)
    need(type(o['quote']) is dict and all(type(v) is int for v in o['quote'].values()) and o['quote']==quote(cid,o['tier'],o['quantity']))
    need(o['phase'] in ('offered','cancelled','working','acceptance'))
    stock.integer(o['step'],0,5);need(type(o['answers']) is list and len(o['answers'])==o['step'])
    for i,answer in enumerate(o['answers']):sp.validate_answer(sp.exercise(cid,o['tier'],i,o['quantity'],o['id']),answer)
    need(type(o['held']) is list and len(o['held'])<=400);stock.integer(o['escrow'])
    totals={};allowed={m['code'] for m in stock.materials(cid,o['tier'])}
    for row in o['held']:
        need(type(row) is dict and set(row)=={'code','quantity','unit_cost'} and type(row['code']) is str and row['code'] in allowed)
        stock.integer(row['quantity'],1,4000);stock.integer(row['unit_cost'],1,100000)
        totals[row['code']]=totals.get(row['code'],0)+row['quantity']
    if o['phase'] in ('offered','cancelled'):need(o['step']==0 and not o['held'] and o['escrow']==0)
    else:
        need((o['step']==5)==(o['phase']=='acceptance'))
        need(totals==({code:o['quantity'] for code in allowed} if kind(cid)=='business' else {}))
        need(o['escrow']==(o['quote']['wages']+o['quote']['tax'] if kind(cid)=='business' else 0))


def validate_account(s):
    """Used by the joint account validator: no separate specialist quota exists."""
    from .career_scale_contracts import validate_account as joint
    joint(s)
