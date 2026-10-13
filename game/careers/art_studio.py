"""Màu Nắng: commission painting, layered work and an earned exhibition record."""
from __future__ import annotations
import copy
from . import kit

ID='art_studio'
GEN=1
OPTIONS={
    'layout':{'portrait':'Khổ đứng, chủ thể ở giữa','landscape':'Khổ ngang, đường chân trời thấp','poster':'Khổ đứng, chừa khoảng chữ','series':'Bộ ba, điểm nhìn liên tục'},
    'palette':{'warm':'Cam đất – vàng mật','cool':'Xanh lam – xanh ngọc','muted':'Nâu nhạt – xám ấm','bright':'Hồng san hô – vàng – lam'},
    'medium':{'watercolor':'Màu nước trên giấy dày','acrylic':'Acrylic trên toan','ink':'Mực nét trên giấy','gouache':'Gouache phủ mờ'},
}
LAYERS={'background':'Nền và khoảng trống','wash':'Mảng màu nhạt','subject':'Hình chính','detail':'Nét và điểm sáng','lettering':'Chữ và nhãn','seal':'Lớp bảo vệ'}
PEOPLE=[('Chị Miên','Người hướng dẫn xưởng','Chỉ ra đúng chỗ tranh cần thở.','warm'),('Bác Tùng','Chủ quán trà','Thích bức tranh giữ được chuyện của phố.','quiet'),
        ('Cô Hạ','Thủ thư','Đặt tranh cho góc đọc và luôn ghi rõ kích thước.','careful'),('Anh Nam','Nhạc công','Muốn áp phích sáng mà vẫn đọc rõ tên buổi diễn.','warm'),
        ('Chị Vân','Người làm gốm','Mê màu đất, không thích bóng lóa.','quiet'),('Bé Mai','Học sinh','Có cả một quyển sổ những khu vườn tưởng tượng.','warm'),
        ('Bà Liên','Người giữ ảnh cũ','Muốn con cháu nhận ra ngôi nhà xưa.','quiet'),('Anh Phúc','Phụ trách triển lãm','Kiểm cả ánh sáng, tên tranh và mép khung.','careful')]


def commission(name,day,subject,layout,palette,medium,story):
    return dict(name=name,day=day,subject=subject,layout=layout,palette=palette,medium=medium,story=story)


COMMISSIONS={
 'tea':commission('Góc trà buổi sớm',1,'Ấm trà cạnh cửa sổ','landscape','warm','watercolor','Bác Tùng muốn khách nhìn tranh thấy một buổi sáng thong thả.'),
 'cat':commission('Chân dung Mướp',1,'Mèo Mướp ngồi trên ghế','portrait','muted','gouache','Chị Vân dặn giữ màu lông thật, không thêm chiếc nơ không có trong ảnh.'),
 'garden':commission('Vườn của bé Mai',1,'Vườn hoa trước sân trường','landscape','bright','gouache','Mai đã đánh dấu cây phượng phải nằm bên trái khoảng sân.'),
 'books':commission('Góc sách yên tĩnh',4,'Chồng sách và cành lá','portrait','cool','ink','Cô Hạ cần đường nét sạch để tranh không làm góc đọc rối mắt.'),
 'river':commission('Khúc sông Bến Mây',4,'Thuyền giấy trên khúc sông','landscape','cool','watercolor','Khoảng trời cần thoáng, thuyền chỉ chiếm một góc nhỏ.'),
 'pottery':commission('Bàn tay làm gốm',4,'Bàn tay bên chiếc bình đất','portrait','warm','acrylic','Chị Vân muốn chất đất hiện rõ và nền không lấn bàn tay.'),
 'music':commission('Áp phích đêm nhạc',10,'Sân khấu âm nhạc ngoài sân','poster','bright','gouache','Anh Nam cần chừa phần trên cho tiêu đề, không đặt chữ lên hình chính.'),
 'fair':commission('Ngày hội sách',10,'Những cuốn sách mở','poster','cool','ink','Tên hội sách phải rõ dù người xem đứng cách xa bảng.'),
 'oldhome':commission('Màu của căn nhà cũ',10,'Căn nhà trong tấm ảnh bạc','landscape','muted','watercolor','Bà Liên muốn giữ màu ký ức; không tự thêm chi tiết không có trong mẫu.'),
 'seasons':commission('Ba mùa bên cửa',20,'Một cửa sổ qua ba mùa','series','warm','acrylic','Ba tấm phải nối đường bậu cửa cùng cao độ khi treo cạnh nhau.'),
 'tides':commission('Bộ tranh con nước',20,'Bến sông ở ba thời điểm','series','cool','watercolor','Đường chân trời liền nhau nhưng hình thuyền đổi theo thời điểm.'),
 'craft':commission('Người thợ trong phố',20,'Ba đôi tay làm nghề','series','muted','ink','Mỗi tấm có nghề riêng, cùng một tỷ lệ hình và nét mực.'),
 'square':commission('Tranh sảnh cộng đồng',40,'Quảng trường với người đi bộ','landscape','bright','acrylic','Tranh lớn cần đọc rõ hình từ xa và có lớp bảo vệ bề mặt.'),
 'heritage':commission('Bộ ký ức khu phố',40,'Những mái nhà nối tiếp','series','muted','acrylic','Nhãn ghi nguồn ảnh được người cung cấp đồng ý; không nhận tranh sao chép là tác phẩm riêng.'),
 'opening':commission('Áp phích khai mạc',45,'Tác phẩm giữa gian triển lãm','poster','warm','gouache','Khoảng chữ, tên tác giả và thời gian phải tách rõ trên áp phích.'),
 'exhibition':commission('Bộ tranh Màu Nắng',45,'Ba khoảnh khắc của khu phố','series','bright','acrylic','Bộ tranh cuối kỳ cần liền mạch, ký tên và khung sạch để đem trưng bày.'),
}
MILESTONES=[('hocviec','Sổ phác thảo đầu tiên',1,6,2),('vungtay','Người giữ đúng lời hẹn',10,30,8),
            ('bosuutap','Bộ sưu tập của phố',20,70,18),('trienlam','Gian tranh Màu Nắng',45,140,35)]
FIXED=('gen','needs','_key','kind')


def make_task(day,slot,serial):
    available=[k for k,v in COMMISSIONS.items() if v['day']<=day]
    r=kit.rng(ID,day,'commissions');r.shuffle(available)
    cid=available[(slot+day-1)%len(available)];v=COMMISSIONS[cid]
    phase=sum(day>=n for n in (4,10,20,40))
    who=1+kit.rng(ID,day,slot).randrange(len(PEOPLE)-1)
    layers=['background','wash','subject','detail']
    if v['layout']=='poster':layers.append('lettering')
    if v['medium']=='acrylic' or day>=40:layers.append('seal')
    cost=6+phase;gross=28+phase*2
    needs=dict(commission=cid,subject=v['subject'],brief=v['story'],recipient=PEOPLE[who][0],
               layout=OPTIONS['layout'][v['layout']],palette=OPTIONS['palette'][v['palette']],medium=OPTIONS['medium'][v['medium']],
               rule='Làm nền trước, màu nhạt trước hình chính, chi tiết sau cùng; chữ sau hình, bảo vệ sau khi hoàn thiện.',
               layers=[dict(id=k,label=LAYERS[k]) for k in layers],gross=gross,cost=cost,phase=phase)
    kit.rng(ID,'buttons',day,slot).shuffle(needs['layers'])
    return kit.base_task(ID,day,slot,serial,who,v['name'],f'{PEOPLE[who][0]} mang tới một đơn đặt tranh mới.',
                         kind='commission',gen=GEN,needs=needs,_key=dict(layout=v['layout'],palette=v['palette'],medium=v['medium'],layers=layers),
                         stage='plan',plan={},painted=[],checked=[],result=None)


def initial():
    return dict(v=1,today=dict(day=0,jobs=0,good=0,net=0),stats=dict(jobs=0,good=0,active_days=0,net=0,last_good_day=0),last_closed=0,portfolio=[])


def _data(c):return c['ext']['data']


def _today(c):
    d=_data(c)
    if d['today']['day']!=c['day']:d['today']=dict(day=c['day'],jobs=0,good=0,net=0)
    return d['today']


def on_start(s,c):_today(c)


def daily_task_count(day):return 3 if day<10 else 4


def handle(s,c,name,p):
    allowed={'art_plan':{'task','field','value'},'art_begin':{'task'},'art_layer':{'task','layer'},'art_proof':{'task','checks'},'art_deliver':{'task','recipient'}}
    kit.need(name in allowed and set(p)<=allowed[name],'Thao tác xưởng vẽ không hợp lệ.')
    t=kit.task(c,p);kit.need(t['known'],'Đọc yêu cầu đặt tranh trước nhé.')
    if name=='art_plan':
        kit.need(t['stage']=='plan','Đã bắt đầu vẽ, không đổi chất liệu của tranh đang làm.')
        field=kit.one_of(p.get('field'),OPTIONS)
        value=kit.one_of(p.get('value'),OPTIONS[field]);t['plan'][field]=value
        return dict(message=f'Đã chọn: {OPTIONS[field][value]}.')
    if name=='art_begin':
        kit.need(t['stage']=='plan' and set(t['plan'])==set(OPTIONS),'Chọn đủ bố cục, bảng màu và chất liệu.')
        kit.start_work(t);t['stage']='paint'
        bad=[k for k in OPTIONS if t['plan'][k]!=t['_key'][k]]
        t['mistakes']+=len(bad)
        return dict(message='Bắt đầu dựng tranh.' if not bad else 'Phác thảo khác yêu cầu ở: '+', '.join({'layout':'bố cục','palette':'màu','medium':'chất liệu'}[k] for k in bad)+'. Khi giao, khách sẽ đánh giá phần khác này.')
    if name=='art_layer':
        kit.need(t['stage']=='paint','Chưa tới bước vẽ các lớp.')
        layer=kit.one_of(p.get('layer'),t['_key']['layers'])
        kit.need(layer not in t['painted'],'Lớp này đã hoàn thành.')
        correct=layer==t['_key']['layers'][len(t['painted'])]
        t['painted'].append(layer)
        if not correct:t['mistakes']+=1
        if len(t['painted'])==len(t['_key']['layers']):t['stage']='proof'
        return dict(message=f'Đã làm {LAYERS[layer].lower()}.'+(' Lớp này bị lệch trình tự, bề mặt chưa đều.' if not correct else ''),correct=correct)
    if name=='art_proof':
        kit.need(t['stage']=='proof','Hoàn thiện các lớp tranh trước khi kiểm.')
        checks=kit.id_list(p.get('checks'),('brief','surface','signature'),3)
        kit.need(set(checks)=={'brief','surface','signature'},'Kiểm đủ yêu cầu, bề mặt và chữ ký trước khi giao.')
        t['checked']=checks;t['stage']='deliver'
        return dict(message='Đã kiểm yêu cầu, bề mặt và ký tên. Chọn đúng người nhận để bàn giao.')
    kit.need(t['stage']=='deliver','Kiểm hoàn thiện trước khi giao tranh.')
    recipient=kit.one_of(p.get('recipient'),[x[0] for x in PEOPLE])
    kit.need(recipient==t['needs']['recipient'],'Phiếu không đúng người nhận; xem lại tên trên đơn.')
    n=t['needs'];gross=max(n['cost']+5,n['gross']-4*t['mistakes']);net=gross-n['cost']
    t['stage']='done';t['result']=dict(gross=gross,cost=n['cost'],net=net)
    good=t['mistakes']==0;d=_data(c);today=_today(c)
    for counters in (today,d['stats']):
        counters['jobs']+=1;counters['good']+=int(good);counters['net']+=net
    if good:d['stats']['last_good_day']=max(d['stats']['last_good_day'],t['day'])
    d['portfolio'].append(dict(day=t['day'],name=t['title'],good=good))
    d['portfolio']=d['portfolio'][-12:]
    kit.complete(s,c,t,gross,'Tranh được bàn giao đúng phiếu.' if good else 'Khách nhận tranh và góp ý những phần khác yêu cầu.',bonus_base=net)
    # Settle materials from the customer's receipt, so an empty fund never blocks delivery.
    # Both rows live inside the engine transaction; a retry cannot collect either twice.
    kit.money(s,c,-n['cost'],'Giấy/toan, màu và hoàn thiện tranh',t['id'],'materials')
    return dict(message=f'Giao tranh: {gross} xu, vật tư {n["cost"]} xu, còn {net} xu trước thưởng thiết bị.',gross=gross,cost=n['cost'],net=net,correct=good)


def on_close(s,c):
    d=_data(c);today=_today(c)
    if c['day']>d['last_closed']:
        if today['jobs']>=2:d['stats']['active_days']+=1
        d['last_closed']=c['day']
    return dict(lines=[f'Xưởng hoàn thành {today["jobs"]} tranh, {today["good"]} tranh đúng yêu cầu.'],jobs=today['jobs'],earned=today['net'],
                note='Ngày làm ít nhất hai tranh mới tính vào hành trình triển lãm; khép ca rỗng không tăng mốc.')


def public_data(c):
    d=copy.deepcopy(_data(c));stats=d['stats']
    d['milestones']=[dict(id=i,name=n,day=day,good=good,active_days=active,
                         done=stats['last_good_day']>=day and stats['good']>=good and stats['active_days']>=active) for i,n,day,good,active in MILESTONES]
    return d


def public_task(t):
    v={k:copy.deepcopy(x) for k,x in t.items() if not k.startswith('_')}
    if not t['known']:v['needs']=None
    return v


def content():
    return dict(options=OPTIONS,layers=LAYERS,recipients=[p[0] for p in PEOPLE],
                guide='Đọc đơn → chọn bố cục, màu, chất liệu → dựng từng lớp → kiểm yêu cầu, bề mặt, chữ ký → giao đúng phiếu.',
                progression=[dict(day=d,title=n) for d,n in ((1,'Tranh nhỏ và chất liệu cơ bản'),(4,'Nét mực, mặt nước và chất đất'),(10,'Áp phích và phục dựng màu'),(20,'Bộ ba tranh liên tục'),(40,'Tranh sảnh và ký ức phố'),(45,'Bộ tranh triển lãm'))])


def known_request(c,t):return t['needs']['brief']
def hint(c,t):return 'Xem lại ba dòng trên phiếu. Nền → màu nhạt → hình chính → chi tiết → chữ nếu có → bảo vệ nếu có.'
def feedback(c,t):return dict(criteria=[dict(key='craft',label='Đúng yêu cầu và trình tự',score=max(1,5-t['mistakes']),note='Khách đối chiếu tranh với phiếu đặt.')])


def validate_task(t,original):
    for field in FIXED:kit.need(t.get(field)==original.get(field),'Dữ kiện tranh đã bị thay đổi.')
    kit.need(t['stage'] in ('plan','paint','proof','deliver','done'),'Bước vẽ không hợp lệ.')
    kit.need(isinstance(t['plan'],dict) and set(t['plan'])<=set(OPTIONS),'Phác thảo không hợp lệ.')
    for k,v in t['plan'].items():kit.need(isinstance(v,str) and v in OPTIONS[k],'Lựa chọn phác thảo không hợp lệ.')
    kit.id_list(t['painted'],original['_key']['layers'],6)
    kit.id_list(t['checked'],('brief','surface','signature'),3)
    kit.need(t['stage']=='plan' or set(t['plan'])==set(OPTIONS),'Thiếu phác thảo.')
    kit.need(t['stage']!='plan' or not t['painted'],'Phác thảo chưa được phép có lớp vẽ.')
    kit.need(t['stage'] not in ('proof','deliver','done') or len(t['painted'])==len(original['_key']['layers']),'Thiếu lớp vẽ.')
    kit.need(t['stage'] not in ('deliver','done') or len(t['checked'])==3,'Thiếu kiểm tranh.')
    kit.need((t['stage']=='done')==(t['status']=='completed'),'Trạng thái tranh không khớp.')
    kit.need(t['stage']!='paint' or len(t['painted'])<len(original['_key']['layers']),'Tranh đủ lớp phải chuyển sang kiểm.')
    kit.need(t['stage'] not in ('plan','paint') or not t['checked'],'Chưa tới bước kiểm tranh.')
    kit.need((t['stage']=='done')==(t['result'] is not None),'Phiếu tiền không khớp bước.')
    mistakes=0 if t['stage']=='plan' else sum(t['plan'][k]!=original['_key'][k] for k in OPTIONS)
    mistakes+=sum(layer!=original['_key']['layers'][i] for i,layer in enumerate(t['painted']))
    kit.need(t['mistakes']==mistakes,'Số lỗi không khớp phác thảo và các lớp tranh.')
    if t['stage']!='plan':kit.need(t['known'],'Đọc yêu cầu đặt tranh trước nhé.')
    if t['result'] is not None:
        r=t['result'];kit.need(isinstance(r,dict) and set(r)=={'gross','cost','net'},'Phiếu tiền không hợp lệ.')
        for v in r.values():kit.integer(v,0,100)
        kit.need(r['cost']==original['needs']['cost'] and r['gross']==max(r['cost']+5,original['needs']['gross']-4*t['mistakes']) and r['net']==r['gross']-r['cost'],'Tiền tranh không khớp.')


def validate_data(c):
    d=_data(c);kit.need(isinstance(d,dict) and set(d)==set(initial()) and d['v']==1,'Sổ xưởng vẽ không hợp lệ.')
    for k in ('today','stats'):
        kit.need(isinstance(d[k],dict) and set(d[k])==set(initial()[k]),'Số liệu xưởng không hợp lệ.')
        for v in d[k].values():kit.integer(v,0,10**9)
        kit.need(d[k]['good']<=d[k]['jobs'],'Số tranh đạt không hợp lệ.')
    kit.integer(d['last_closed'],0,10**7)
    kit.need(d['last_closed']<=c['day'] and d['today']['day']<=c['day'],'Ngày ghi sổ xưởng không hợp lệ.')
    kit.need(d['stats']['active_days']<=d['stats']['jobs']//2,'Ngày làm triển lãm chưa đủ tranh.')
    kit.need(d['stats']['last_good_day']<=c['day'] and (d['stats']['last_good_day']>0)==(d['stats']['good']>0),'Ngày tranh đạt không khớp sổ.')
    kit.need(all(d['today'][k]<=d['stats'][k] for k in ('jobs','good','net')),'Sổ ca vượt tổng số của xưởng.')
    kit.need(isinstance(d['portfolio'],list) and len(d['portfolio'])<=12,'Sổ tranh quá dài.')
    for r in d['portfolio']:
        kit.need(isinstance(r,dict) and set(r)=={'day','name','good'} and type(r['good']) is bool,'Dòng sổ tranh sai.')
        kit.integer(r['day'],1,10**7);kit.need(r['name'] in {v['name'] for v in COMMISSIONS.values()},'Tên tranh không hợp lệ.')


SPEC=dict(id=ID,prefix='art_',category='service',meta=dict(short='Xưởng vẽ',place='Xưởng vẽ Màu Nắng',tagline='Giữ lời hẹn bằng màu và nét.',icon='palette',
 color='#b66a46',light='#fff1d9',weather='Nắng xiên qua cửa kính',work='Đơn đặt tranh',station='Bàn vẽ',greeting='Đọc phiếu trước khi mở hộp màu nhé.',caption='Một khu phố, nhiều cách nhìn',map_label='XƯỞNG VẼ MÀU NẮNG'),
 people=PEOPLE,staff=[('Minh','frame','Cắt khung và giữ mép tranh sạch.',80,85),('Linh','colors','Soạn màu theo phiếu đặt.',75,90)],roles={'frame':'Làm khung','colors':'Soạn màu'},
 physical=('art_begin','art_layer','art_proof','art_deliver'),no_tick=('art_plan',),free_actions=(),tip=0,
 activity=('🎨','Thứ tự hoàn thiện tranh',[('Nền','Trước hình'),('Chi tiết','Sau hình'),('Chữ ký','Trước giao')],['Đọc phiếu','Phác thảo','Dựng lớp','Kiểm và giao']),
 stories=[('Màu của phố',('Miên đưa bạn một hộp màu nhỏ.','Khách đầu tiên treo tranh bên ô cửa.','Cả phố nhận ra câu chuyện của mình trên tường xưởng.'))],
 situations=[],review_asides=['Tranh đúng yêu cầu, mép sạch và tên rõ.'],more_line='Xưởng nhận thêm một phiếu đặt tranh.',open_line='Mở cửa xưởng, đọc các phiếu đặt hôm nay.',guide=content()['guide'])
