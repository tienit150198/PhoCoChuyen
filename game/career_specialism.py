"""Sequential paid learning and executable authored specialist commissions."""
import copy
import hashlib
import random
import time
from .career_specialism_content import packs,pack
from . import career_specialism_stock as stock, career_specialism_jobs as jobs
from . import career_scale as scale, career_scale_quota as quota
from .career_scale_finance import move

KEY='specialism'
FEES=(3000,9000,30000,100000,350000,1200000,4000000,12000000,35000000,100000000)
LEVELS=(5,12,25,50,90,150,250,400,650,1000)
CLEAN=(10,30,70,140,260,450,750,1200,1900,3000)
DAYS=(2,7,14,24,40,65,95,140,200,280)
ACTIONS={'special_enrol','special_practice'}|jobs.ACTIONS|stock.ACTIONS


def need(ok,message='Dữ liệu chuyên môn không hợp lệ.'):stock.need(ok,message)


def record(c):
    return c.get(KEY) or dict(v=1,tier=0,study=None,tuition=[],seq=0,job=None,history=[])


def fee(cid,tier):return 0 if jobs.kind(cid)=='community' else FEES[tier-1]


def exercise(cid,tier,step,quantity,salt=''):
    """The answer key stays server-side; lesson notes deliberately teach the method."""
    p=pack(cid,tier);stock.integer(step,0,4);stock.integer(quantity,1,1000)
    if step==0:
        m=p['inputs'][0]
        return dict(type='number',prompt=f"Mỗi {p['output_unit']} cần {m['quantity']} {m['unit']} {m['name']}. Đơn {quantity} {p['output_unit']} cần bao nhiêu {m['unit']}?",
            answer=m['quantity']*quantity,why=f"Định lượng {m['name']}: {m['quantity']} × {quantity} = {m['quantity']*quantity} {m['unit']}.")
    if step<4:
        choices=list(enumerate(p['procedure']));correct=step-1
        prompt=f"{p['title']}: thao tác thứ {step} trong quy trình là gì?"
        why=f"Bước {step}: {p['procedure'][step-1]}"
    else:
        choices=[(0,p['check']['good']),(1,p['check']['bad'])];correct=0
        prompt=p['check']['prompt'];why=p['check']['why']
    seed=hashlib.sha256(f'{cid}|{tier}|{step}|{quantity}|{salt}'.encode()).digest()
    random.Random(seed).shuffle(choices)
    options=[dict(value=chr(97+i),label=text) for i,(_,text) in enumerate(choices)]
    return dict(type='select',prompt=prompt,options=options,answer=next(chr(97+i) for i,(index,_) in enumerate(choices) if index==correct),why=why)


def validate_answer(q,answer):
    if q['type']=='number':stock.integer(answer,0,10**9)
    else:need(type(answer) is str and answer in {o['value'] for o in q['options']},'Chọn một phương án trên phiếu.')


def requirements(s,c,cid,tier,now):
    projected=copy.deepcopy(c);r=scale.ensure(projected,cid,now)
    from . import employment,accounting_jobs,promotion
    allowed,reason=accounting_jobs.can_work(s,cid)
    hired=not employment.required(cid) or c.get('job',{}).get('status')=='hired'
    banned=promotion.banned(s,cid)
    work=allowed and hired and not banned
    reason=reason if not allowed else 'Cần được tuyển dụng vào nghề trước.' if not hired else 'Đang bị đình chỉ; chờ được phép hành nghề lại.' if banned else ''
    values=[('Cấp kinh nghiệm nghề',1+c['xp']//90,LEVELS[tier-1]),('Việc tự làm không lỗi',r['clean'],CLEAN[tier-1]),
            None,('Đã bắt đầu nghề',int(c.get('started') is True),1),
            ('Đủ điều kiện hành nghề',int(work),1),('Quỹ nghề cho học phí',c['money'],fee(cid,tier))]
    rows=[scale.days_row(r,DAYS[tier-1],projected) if v is None else dict(label=v[0],got=v[1],need=v[2],met=v[1]>=v[2]) for v in values]
    if reason:rows[4]['reason']=reason
    return rows


def action(s,c,cid,name,p,now=None):
    need(name in ACTIONS and type(p) is dict)
    at=int(time.time() if now is None else now);quota.day(at)
    if name in stock.ACTIONS:return stock.action(s,c,cid,name,p)
    if name in jobs.ACTIONS:return jobs.action(s,c,cid,name,p,at)
    r=record(c)
    if name=='special_enrol':
        need(set(p)=={'tier'});tier=stock.integer(p['tier'],1,10)
        need(tier==r['tier']+1 and r['study'] is None,'Học tuần tự và hoàn thành khóa đang học trước nhé.')
        need(all(x['met'] for x in requirements(s,c,cid,tier,at)),'Chưa đủ cấp nghề, việc sạch, ngày thực hoặc quỹ học phí.')
        charge=fee(cid,tier)
        if charge:move(s,c,-charge,f"Học chuyên môn: {pack(cid,tier)['title']}",f'{cid}_learn-{tier}',category='scale_special_tuition')
        scale.ensure(c,cid,at)
        r['tuition'].append(dict(tier=tier,fee=charge));r['study']=dict(tier=tier,step=0,answers=[],attempt=1,feedback='')
        c[KEY]=r
        return dict(message='Đã đăng ký khóa học. Đọc hướng dẫn và thực hành; thử lại không mất thêm học phí.')
    need(set(p)=={'tier','step','answer'})
    study=r['study'];need(study is not None,'Không có khóa đang học.')
    stock.integer(p['tier'],1,10);stock.integer(p['step'],0,4)
    need(p['tier']==study['tier'] and p['step']==study['step'],'Bài thực hành đã chuyển bước.')
    q=exercise(cid,study['tier'],study['step'],1);validate_answer(q,p['answer'])
    need(study['attempt']<10**9)
    study['answers'].append(p['answer']);study['step']+=1
    study['feedback']=('Đúng. ' if p['answer']==q['answer'] else 'Cần sửa. ')+q['why']
    if study['step']==5:
        passed=jobs.score(cid,study['tier'],study['answers'],1,'')>=80
        if passed:r['tier']=study['tier'];r['study']=None
        else:study.update(step=0,answers=[],attempt=study['attempt']+1,feedback='Chưa đạt. Kiểm lại định lượng và bước nghiệm thu bắt buộc; thực hành lại miễn phí.')
        return dict(message='Đã mở nội dung chuyên môn và đơn khách tương ứng.' if passed else study['feedback'])
    return dict(message=study['feedback'])


def button(command,label,payload=None,fields=None,**extra):
    return dict(command=command,label=label,payload=payload or {},fields=fields or [],**extra)


def question_button(command,payload,q):
    f=dict(name='answer',label=q['prompt'],type=q['type'])
    if q['type']=='number':f.update(min=0,max=10**9,value=0)
    else:f.update(options=copy.deepcopy(q['options']),value=q['options'][0]['value'])
    return button(command,'Ghi nhận thao tác',payload,[f])


def public(s,c,cid,now=None):
    r=record(c);k=jobs.kind(cid)
    out=dict(tier=r['tier'],kind=k,quota=None if k=='community' else quota.public(s,now),
        catalog=[dict(tier=p['tier'],title=p['title'],fee=fee(cid,p['tier']),unlocked=p['tier']<=r['tier']) for p in packs(cid)],
        next=None,study=None,job=None,stock=stock.public(c,cid),history=copy.deepcopy(r['history']),actions=[])
    if r['tier']<10 and r['study'] is None:
        tier=r['tier']+1;p=pack(cid,tier);req=requirements(s,c,cid,tier,now);ready=all(x['met'] for x in req)
        out['next']=dict(title=p['title'],fee=fee(cid,tier),requirements=req,can_enrol=ready,
            reason=next((scale._block(x) for x in req if not x['met']),''),
            benefit=f"Mở đơn {p['title']} gồm {jobs.QUANTITIES[tier-1]:,} {p['output_unit']}, vật tư và 5 bước thực hành/thi công.",
            quote=jobs.quote(cid,tier,jobs.QUANTITIES[tier-1]),action=button('special_enrol','Đăng ký học' if k!='community' else 'Học công quả',dict(tier=tier),disabled=not ready))
    if r['study']:
        st=r['study'];p=pack(cid,st['tier']);q=exercise(cid,st['tier'],st['step'],1)
        out['study']=dict(title=p['title'],instructions=[f"Định lượng một {p['output_unit']}: "+', '.join(f"{x['quantity']} {x['unit']} {x['name']}" for x in p['inputs'])]+p['procedure'],
            feedback=st['feedback'],progress=f"Bước {st['step']+1}/5 · lần {st['attempt']}",
            actions=[question_button('special_practice',dict(tier=st['tier'],step=st['step']),q)])
    out['job'],out['actions']=jobs.public(s,c,cid,now)
    return out


def validate(c,cid):
    if KEY not in c:
        need(stock.KEY not in c)
        return
    r=c[KEY];need(type(r) is dict and set(r)=={'v','tier','study','tuition','seq','job','history'})
    need(type(r['v']) is int and r['v']==1);stock.integer(r['tier'],0,10);stock.integer(r['seq'])
    need(type(r['tuition']) is list and len(r['tuition'])==r['tier']+int(r['study'] is not None))
    for i,row in enumerate(r['tuition']):
        need(type(row) is dict and set(row)=={'tier','fee'} and type(row['tier']) is int and row['tier']==i+1 and type(row['fee']) is int and row['fee']==fee(cid,i+1))
    st=r['study']
    if st is not None:
        need(type(st) is dict and set(st)=={'tier','step','answers','attempt','feedback'})
        stock.integer(st['tier'],1,10);need(st['tier']==r['tier']+1)
        stock.integer(st['step'],0,4);stock.integer(st['attempt'],1)
        need(type(st['feedback']) is str and len(st['feedback'])<=2000 and type(st['answers']) is list and len(st['answers'])==st['step'])
        for i,a in enumerate(st['answers']):validate_answer(exercise(cid,st['tier'],i,1),a)
    need(type(r['history']) is list and len(r['history'])<=30)
    ids=set()
    base={'id','tier','title','quantity','quality','revenue','materials','wages','premises','loss','tax','net','escrow','refund','at','message','evidence'}
    for row in r['history']:
        need(type(row) is dict and base<=set(row)<=base|{'spirit'})
        stock.integer(row['tier'],1,r['tier']);stock.integer(row['quantity'],1,jobs.QUANTITIES[row['tier']-1]);stock.integer(row['quality'],0,100)
        need(row['quality'] in (0,20,40,60,80,100))
        need(type(row['id']) is str and row['id'].startswith(cid+'_special-') and row['id'] not in ids);ids.add(row['id'])
        tail=row['id'].removeprefix(cid+'_special-');need(tail.isascii() and tail.isdigit() and str(int(tail))==tail and 1<=int(tail)<=r['seq'])
        need(row['id']!=(r['job'] or {}).get('id'))
        for key in ('revenue','materials','wages','premises','loss','tax','escrow','refund','at'):stock.integer(row[key],0,10**11 if key=='at' else 10**9)
        stock.integer(row['net'],-10**9,10**9)
        q=jobs.quote(cid,row['tier'],row['quantity']);business=jobs.kind(cid)=='business'
        need(row['revenue']==q['revenue']*row['quality']//100 and row['wages']==q['wages'] and row['premises']==row['loss']==0)
        need(row['tax']==((row['revenue']*4+99)//100 if business else 0))
        need(row['escrow']==(q['wages']+q['tax'] if business else 0) and row['refund']==row['escrow']-row['wages']-row['tax'])
        need(row['net']==row['revenue']-row['materials']-row['wages']-row['tax'])
        need(business or row['materials']==0)
        need(type(row['title']) is str and row['title']==pack(cid,row['tier'])['title'] and type(row['message']) is str and len(row['message'])<=500)
        need(type(row['evidence']) is list and len(row['evidence'])==5 and all(type(x) is str and len(x)<=2000 for x in row['evidence']))
        if 'spirit' in row:need(jobs.kind(cid)=='community');stock.integer(row['spirit'],0,3)
    jobs.validate(c,cid);stock.validate(c,cid)
