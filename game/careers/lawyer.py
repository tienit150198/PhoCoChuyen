"""Bình An: fictional evidence-led case preparation, with supplied game rules."""
from __future__ import annotations
import copy
from . import kit
from .. import consequences as cq

ID='lawyer'
GEN=1
FIXED=('needs','_key','kind','gen')
PEOPLE=[('Chị An','Luật sư hướng dẫn','Đọc cả chứng cứ bất lợi trước khi đề xuất.','picky'),
        ('Cô Liên','Khách hàng','Giữ giấy tờ cẩn thận, muốn hiểu từng khoản.','warm'),
        ('Anh Hòa','Khách hàng','Muốn giải quyết bằng chứng cứ rõ ràng.','quiet'),
        ('Chị Thu','Thư ký hồ sơ','Đánh số tài liệu, bảo vệ thông tin riêng.','warm')]
# title, subject, recorded fact, conflicting allegation, contractual remedy, hearing issue
CASES=[
 ('Chiếc bàn giao thiếu','bộ bàn ghế cho lớp vẽ','Biên bản ký nhận ghi còn thiếu hai ghế.','Bên bán nói đã giao đủ ghế.','Giao phần thiếu hoặc hoàn khoản chưa thực hiện','Bên bán chỉ đưa ảnh xe chở hàng, không có chữ ký nhận đủ.'),
 ('Máy ảnh thuê bị tính thêm','máy ảnh thuê cho buổi diễn','Phiếu trả ghi 17 giờ, trước mốc 18 giờ đã thỏa thuận.','Cửa hàng tính phí trả muộn.','Hoàn khoản thu ngoài thỏa thuận','Cửa hàng đưa bảng phí mới, ban hành sau lúc thuê.'),
 ('Bản in sai màu','áp phích cho thư viện','Mẫu màu đã duyệt là xanh; biên bản giao ghi bản in đỏ.','Xưởng nói khách đã duyệt màu đỏ.','In lại đúng mẫu hoặc hoàn khoản chưa thực hiện','Xưởng viện dẫn ảnh chụp màn hình không có xác nhận của khách.'),
 ('Giỏ rau đã hoàn một phần','giỏ rau đặt theo tuần','Phiếu kiểm đếm ghi hai giỏ không giao; sổ đã hoàn một khoản.','Nhà cung cấp nói không còn khoản phải giải quyết.','Hoàn khoản chưa thực hiện sau khi trừ số đã nhận','Khách muốn tính lại cả khoản đã được hoàn.'),
 ('Tiền đặt chỗ hội trường','đặt hội trường sinh hoạt','Biên bản ghi đơn vị cho thuê hủy lịch, khách không đổi lịch.','Đơn vị cho thuê nói khách tự hủy.','Hoàn phần đặt chỗ theo điều khoản đã ký','Đơn vị cho thuê gửi lịch nội bộ khác với lịch hai bên đã ký.'),
 ('Xe đạp sửa chưa xong','sửa phanh xe đạp','Phiếu thử có chữ ký ghi phanh chưa đạt yêu cầu.','Tiệm nói đã nghiệm thu đạt.','Khắc phục theo phiếu hoặc hoàn khoản chưa thực hiện','Tiệm nêu tiền công thay lốp không có trong phiếu việc.'),
 ('Khóa học đổi lịch','lớp làm gốm cuối tuần','Thông báo đổi sang thứ hai do trung tâm gửi.','Trung tâm nói học viên tự bỏ buổi cuối tuần.','Hoàn các buổi chưa học sau khi trừ số đã nhận','Trung tâm đưa danh sách điểm danh của lớp khác.'),
 ('Tấm rèm sai kích thước','rèm cửa phòng đọc','Phiếu đo được hai bên ký ghi chiều rộng khác hàng giao.','Bên may nói làm đúng phiếu đo.','Sửa đúng kích thước hoặc hoàn khoản chưa thực hiện','Bên may đưa một bản nháp phiếu đo chưa được ký.'),
 ('Tủ sách vận chuyển trầy','chuyển tủ sách tới nhà mới','Biên bản giao nhận ghi vết trầy phát sinh trong chuyến đi.','Đơn vị vận chuyển nói không có ghi nhận vết trầy.','Thanh toán chi phí khắc phục trong giới hạn thỏa thuận','Đơn vị vận chuyển hỏi vì sao hóa đơn mới có số cao hơn báo giá.'),
 ('Tranh mượn triển lãm','mượn tranh cho triển lãm phố','Sổ bàn giao ghi một khung tranh chưa được trả.','Bên mượn nói đã trả đủ cả khung.','Trả khung hoặc thanh toán phần được chứng minh','Người làm chứng chỉ nhớ màu tranh, không nhớ khung đã trả hay chưa.'),
 ('Đơn bánh bị hủy một phần','bánh cho buổi họp dân phố','Biên bản nhận ghi một khay đã hủy theo xác nhận hai bên.','Tiệm vẫn tính đủ khay đã hủy.','Điều chỉnh tiền theo phần thực hiện và khoản đã hoàn','Khách đề nghị thêm khoản buồn phiền không ghi trong thỏa thuận.'),
 ('Bản thu âm chưa bàn giao','thu âm truyện cho thư viện','Danh mục bàn giao có chữ ký thiếu tệp đã thỏa thuận.','Phòng thu nói đã gửi đủ tệp.','Bàn giao tệp thiếu hoặc hoàn khoản chưa thực hiện','Phòng thu cung cấp đường dẫn đã hết hạn, chưa có xác nhận nhận tệp.'),
]
DISCLAIMER='Tất cả hồ sơ và quy tắc dưới đây thuộc trò chơi hư cấu; không mô phỏng luật hay thời hạn pháp lý ngoài đời.'
RULE='Dùng thỏa thuận đã ký cùng biên bản có xác nhận; lời kể hoặc bản nháp cần kiểm chứng. Chỉ yêu cầu khoản có chứng từ, trừ tiền đã nhận và tuân giới hạn ghi trong phiếu.'


def initial():
    return dict(v=1,jobs=0,qualified=0,active_days=0,last_active_day=0,earned=0,
                today=dict(day=0,jobs=0,clean=0,earned=0),milestone=False)


def _choice(sid,title,question,options,answer,why):
    return dict(id=sid,type='choice',title=title,question=question,options=[dict(id=k,label=v) for k,v in options],why=why),answer


def make_task(day,slot,serial):
    r=kit.rng(ID,day,slot)
    idx=(day-1+(slot-1)*5)%len(CASES)
    title,subject,fact,allegation,remedy,hearing=CASES[idx]
    costs=[r.randint(3,12)*10 for _ in range(3 if day>=10 else 2)]
    credit=r.randint(1,4)*10
    cap=r.randint(12,20)*10 if day>=10 else sum(costs)
    total=max(0,min(sum(costs),cap)-credit)
    docs=[dict(id='signed',title='A · Thỏa thuận hai bên đã ký',text=f'Đối tượng: {subject}. Cách xử lý đã thỏa thuận: {remedy}. Giới hạn khoản được tính: {cap} xu.'),
          dict(id='record',title='B · Biên bản có xác nhận',text=fact),
          dict(id='claim',title='C · Lời trình bày cần kiểm chứng',text=allegation)]
    events=[dict(id='agreement',label='Ký thỏa thuận',stamp='Ngày 02'),dict(id='delivery',label='Lập biên bản giao nhận',stamp='Ngày 06'),dict(id='request',label='Gửi yêu cầu đối chiếu',stamp='Ngày 08')]
    # Dates are dossier-local labels, never asserted statutory deadlines.
    start=r.randint(1,16)
    for i,event in enumerate(events):event['stamp']=f'Ngày {start+i*3:02d} trong hồ sơ'
    order=[e['id'] for e in events];r.shuffle(events)
    steps=[(dict(id='evidence',type='multi',title='Lập cặp chứng cứ',question='Chọn hai tài liệu làm căn cứ đối chiếu chính. Lời kể vẫn lưu riêng để kiểm chứng.',options=[dict(id=d['id'],label=d['title']) for d in docs],why='Đối chiếu thỏa thuận đã ký với biên bản có xác nhận; lời kể một phía chưa đủ.'),['signed','record']),
           (dict(id='timeline',type='order',title='Dựng dòng thời gian',question='Chạm ba sự kiện theo ngày từ sớm đến muộn.',options=[dict(id=e['id'],label=e['label']+' · '+e['stamp']) for e in events],why='Đọc ngày trên từng sự kiện, xếp từ ngày nhỏ đến ngày lớn.'),order),
           _choice('discrepancy','Đánh dấu mâu thuẫn','Điểm nào cần làm rõ với tài liệu B?', [('a',allegation),('b','Tên người tiếp nhận hồ sơ ở văn phòng'),('c','Màu bìa đựng hồ sơ')],'a',f'Biên bản B ghi: {fact} So với lời trình bày C để chỉ đúng mâu thuẫn.'),
           (dict(id='amount',type='amount',title='Tính khoản yêu cầu',question=f'Cộng các chứng từ, lấy tối đa {cap} xu theo phiếu, rồi trừ {credit} xu đã nhận. Không cộng lần nữa bản sao hóa đơn.',options=[],why='Công thức của hồ sơ: max(0, min(tổng chứng từ gốc, giới hạn) − tiền đã nhận).'),total),
           _choice('filing','Soạn phương án','Phương án nào bám đúng thỏa thuận của hồ sơ?', [('a',remedy+'; gửi đề nghị đối chiếu kèm chứng cứ'),('b','Cam kết chắc chắn thắng và yêu cầu thêm gấp đôi'),('c','Công khai giấy tờ riêng của các bên lên bảng phố')],'a','Đọc cách xử lý trong tài liệu A; chỉ nêu yêu cầu được chứng minh, không hứa kết quả.')]
    if day>=4:
        steps.append(_choice('hearing','Buổi đối chiếu',hearing,[('a','Ghi nhận ý kiến; yêu cầu tài liệu gốc, đối chiếu hồ sơ trước khi kết luận'),('b','Bỏ qua tài liệu bất lợi cho khách'),('c','Đồng ý ngay vì người nói rất tự tin')],'a','Ghi nhận cả ý kiến bất lợi, yêu cầu căn cứ và giữ kết luận trong phạm vi đã kiểm chứng.'))
    if day>=20:
        scope=r.choice(('private','conflict'))
        steps.append(_choice('scope','Phạm vi đại diện','Khách gửi thêm danh sách người ngoài hồ sơ.' if scope=='private' else 'Sổ tiếp nhận cho thấy văn phòng đang hỗ trợ cả bên còn lại.',
            [('a','Chỉ giữ dữ liệu cần cho hồ sơ; che phần không liên quan'),('b','Dừng tiếp nhận phần xung đột; báo người hướng dẫn để chuyển người độc lập'),('c','Chuyển toàn bộ cho cả hai bên mà không hỏi')],
            'a' if scope=='private' else 'b','Bảo vệ dữ liệu không liên quan; nếu đang hỗ trợ hai phía thì báo xung đột và chuyển người độc lập.'))
    if day>=40:
        steps.append(_choice('audit','Soát bộ hồ sơ cuối','Có bản sao hóa đơn cùng mã và bản bổ sung chưa ký. Chốt thế nào?', [('a','Giữ dấu vết tài liệu; tính hóa đơn gốc một lần, xin xác nhận bản bổ sung'),('b','Cộng bản sao để tăng số tiền yêu cầu'),('c','Xóa tài liệu bất lợi khỏi hồ sơ')],'a','Một mã hóa đơn chỉ được tính một lần. Bản bổ sung chưa ký cần xác nhận và vẫn được lưu dấu vết.'))
    for st,key in steps:r.shuffle(st['options'])
    needs=dict(variant=f'case-{idx:02d}',rule=RULE,disclaimer=DISCLAIMER,documents=docs,events=events,
               invoices=[dict(code=f'HD-{i+1}',amount=n) for i,n in enumerate(costs)],credit=credit,cap=cap,
               duplicate='Bản sao HD-1 (cùng mã, cùng khoản; lưu đối chiếu, không tính thêm).' if day>=10 else '',steps=[x for x,_ in steps])
    return kit.base_task(ID,day,slot,serial,1+(idx%2),title,f'Khách nhờ xem hồ sơ {subject}. {allegation}',
                         kind='case',gen=GEN,needs=needs,_key={x['id']:key for x,key in steps},stage='work',at=0,work={},failed=[],last_feedback='')


def handle(s,c,name,p):
    kit.need(name=='lw_submit','Thao tác hồ sơ không hợp lệ.')
    t=kit.task(c,p)
    kit.need(t['career']==ID and t['known'],'Hỏi khách về hồ sơ trước khi làm.')
    kit.need(t['stage']=='work' and t['at']<len(t['needs']['steps']),'Hồ sơ đã khép.')
    st=t['needs']['steps'][t['at']]
    kit.need(p.get('step')==st['id'],'Làm đúng bước hiện tại của hồ sơ.')
    value=_valid_value(st,p.get('value'))
    key=t['_key'][st['id']]
    good=set(value)==set(key) if st['type']=='multi' else value==key
    kit.start_work(t)
    if not good:
        if st['id'] not in t['failed']:
            t['failed'].append(st['id']);t['mistakes']+=1
            cq.slip(t,'law:'+st['id'],1,st['why'],note=st['title'])
        t['last_feedback']=st['why']+' Sửa lại bước này để tiếp tục.'
        return dict(correct=False,message=t['last_feedback'])
    t['work'][st['id']]=copy.deepcopy(value);t['at']+=1;t['last_feedback']='Đã đối chiếu bước này; tiếp tục theo hồ sơ.'
    if t['at']<len(t['needs']['steps']):return dict(correct=True,message=t['last_feedback'])
    d=c['ext']['data'];_today(c)
    clean=not t['failed'];bonus=max(2,len(t['needs']['steps'])-1-len(t['failed']))
    d['jobs']+=1;d['qualified']+=int(clean);d['earned']+=bonus
    if d['last_active_day']!=c['day']:d['active_days']+=1;d['last_active_day']=c['day']
    d['today']['jobs']+=1;d['today']['clean']+=int(clean);d['today']['earned']+=bonus
    d['milestone']=d['qualified']>=120 and d['active_days']>=30 and d['last_active_day']>=40
    t['stage']='done'
    kit.complete(s,c,t,bonus,'Hồ sơ có căn cứ, khoản yêu cầu được đối chiếu; người hướng dẫn tiếp nhận phương án.')
    return dict(correct=clean,celebrate=clean,message=f'Đã bàn giao hồ sơ. Thưởng hồ sơ {bonus} xu; lương ngày trả khi khép ca.')


def _valid_value(st,value):
    ids=[o['id'] for o in st['options']]
    if st['type'] in ('multi','order'):
        value=kit.id_list(value,ids,3)
        kit.need(len(value)==(2 if st['type']=='multi' else 3),'Chọn đủ số tài liệu hoặc sự kiện trước khi gửi.')
    elif st['type']=='amount':value=kit.integer(value,0,10000)
    else:value=kit.one_of(value,ids)
    return value


def _today(c):
    d=c['ext']['data']
    if d['today']['day']!=c['day']:d['today']=dict(day=c['day'],jobs=0,clean=0,earned=0)


def on_start(s,c):_today(c)


def on_close(s,c):
    d=c['ext']['data'];_today(c)
    return dict(lines=[f"Hồ sơ hoàn tất hôm nay: {d['today']['jobs']}; hồ sơ không phải sửa: {d['today']['clean']}."],note='Giữ bản gốc và nhật ký đối chiếu.',**{k:d['today'][k] for k in ('jobs','clean','earned')})


def known_request(c,t):return t['opening']+' '+RULE


def public_task(t):
    v=copy.deepcopy(t)
    for k in list(v):
        if k.startswith('_'):del v[k]
    if not t['known']:v['needs']=None
    return v


def public_data(c):
    d=copy.deepcopy(c['ext']['data'])
    d['milestone']=dict(title='Hồ sơ vững vàng',qualified=d['qualified'],required_cases=120,active_days=d['active_days'],required_days=30,required_day=40,earned=d['qualified']>=120 and d['active_days']>=30 and d['last_active_day']>=40)
    return d


def content():
    return dict(intro=DISCLAIMER,notebook=[dict(emoji='⚖️',who='Quy tắc của trò chơi',text=RULE)],kinds={'case':'Hồ sơ tranh chấp'},kind_emoji={'case':'⚖️'},
                pay_note='Lương ngày theo hợp đồng; thưởng hồ sơ 4–7 xu trước hệ số, giảm khi phải sửa. Mốc dài hạn: 120 hồ sơ không phải sửa, 30 ngày có hoàn tất hồ sơ và hoàn tất ít nhất một hồ sơ từ ngày nghề 40.')


def hint(c,t):
    if not t['known']:return 'Hỏi khách để mở tài liệu và quy tắc hồ sơ.'
    return t['needs']['steps'][min(t['at'],len(t['needs']['steps'])-1)]['why']


def feedback(c,t):return dict(criteria=[dict(key='accuracy',label='Chứng cứ và tính toán',score=max(1,5-len(t['failed'])),note='Đối chiếu đầy đủ' if not t['failed'] else 'Có bước cần sửa theo tài liệu')])


def validate_task(t,original):
    for k in FIXED:kit.need(t.get(k)==original.get(k),'Dữ kiện hồ sơ đã bị thay đổi.')
    steps=t['needs']['steps'];ids=[st['id'] for st in steps]
    at=kit.integer(t.get('at'),0,len(steps))
    kit.need(t.get('stage')==('done' if at==len(steps) else 'work'),'Trạng thái hồ sơ sai.')
    kit.need(isinstance(t.get('work'),dict) and set(t['work'])==set(ids[:at]),'Tiến trình hồ sơ sai.')
    for st in steps[:at]:
        value=_valid_value(st,t['work'][st['id']]);key=t['_key'][st['id']]
        kit.need(set(value)==set(key) if st['type']=='multi' else value==key,'Bước hồ sơ chưa được đối chiếu.')
    kit.id_list(t.get('failed'),ids,8)
    kit.need(all(ids.index(sid)<=at for sid in t['failed']),'Nhật ký sửa hồ sơ sai.')
    kit.need(t['mistakes']==len(t['failed']),'Số bước sửa hồ sơ sai.')
    kit.need(isinstance(t.get('last_feedback'),str) and len(t['last_feedback'])<=1000,'Phản hồi hồ sơ sai.')
    kit.need((t['stage']=='done')==(t['status']=='completed'),'Hồ sơ chưa bàn giao.')
    if at:kit.need(t['known'],'Hỏi khách về hồ sơ trước khi làm.')


def validate_data(c):
    d=c['ext']['data'];base=initial()
    kit.need(isinstance(d,dict) and set(d)==set(base),'Sổ hồ sơ sai.')
    for k in ('v','jobs','qualified','active_days','last_active_day','earned'):kit.integer(d.get(k),0,10**9)
    kit.need(d['v']==1 and d['qualified']<=d['jobs'] and d['active_days']<=d['jobs'] and d['last_active_day']<=c['day'],'Thống kê hồ sơ sai.')
    kit.need(type(d['milestone']) is bool and d['milestone']==(d['qualified']>=120 and d['active_days']>=30 and d['last_active_day']>=40),'Mốc hồ sơ sai.')
    kit.need(isinstance(d['today'],dict) and set(d['today'])==set(base['today']),'Sổ ca sai.')
    for value in d['today'].values():kit.integer(value,0,10**9)
    kit.need(d['today']['clean']<=d['today']['jobs']<=d['jobs'] and d['today']['day']<=c['day'],'Sổ ca sai.')


SPEC=dict(id=ID,prefix='lw_',category='office',
 meta=dict(short='Luật sư',place='Văn phòng luật Bình An',tagline='Lắng nghe, đối chiếu và trình bày có căn cứ.',icon='book',color='#345b74',light='#e9f1f5',weather='Ánh sáng dịu trên chồng hồ sơ',work='Hồ sơ',station='Bàn đối chiếu',greeting='Mở hồ sơ, đọc quy tắc và giữ mọi kết luận trong phạm vi chứng cứ nhé.',caption='Bình An từ những điều rõ ràng',map_label='VĂN PHÒNG LUẬT BÌNH AN'),
 people=PEOPLE,staff=[('Minh','records','Sắp tài liệu theo mã, giữ nguyên bản gốc.',80,88),('Lan','records','Nhắc đối chiếu cả khoản đã nhận.',76,92)],roles={'records':'Trợ lý hồ sơ'},tip=0,physical=(),free_actions=(),no_tick=(),waste_items=(),
 employment=dict(postings=[dict(id='law-binh-an',org='Văn phòng luật Bình An',kind='firm',title='Chuyên viên hồ sơ tập sự',salary=(50,75),probation_days=3,wants=['careful','communication','learning'],perks=['Có luật sư hướng dẫn','Thưởng nhỏ theo hồ sơ'],culture='Đọc cả chứng cứ bất lợi, không hứa chắc kết quả.',questions=['mistake','conflict'],reference=False)],questions={}),
 activity=('⚖️','Bảng quy tắc hồ sơ',[('Chứng cứ','Có nguồn và xác nhận'),('Tính tiền','Trừ khoản đã nhận'),('Bảo mật','Chỉ dùng phần cần thiết')],['Đọc chứng cứ','Dựng dòng thời gian','Tính yêu cầu','Soạn phương án']),
 stories=[('Tờ biên bản cũ',('Cô Liên mang tới một tờ giấy gấp làm tư.','Bạn tìm ra chữ ký xác nhận dưới nếp gấp.','Cô cất bản gốc vào túi, giữ bản sao để cùng đối chiếu.'))],review_asides=['Giải thích căn cứ rõ ràng.','Tính cả khoản đã hoàn.','Giữ kín giấy tờ riêng.'],situations=[],more_line='Có hồ sơ mới cần đối chiếu.',open_line='Văn phòng mở cửa, người hướng dẫn đã chuẩn bị hồ sơ.',guide='Hỏi khách → chọn chứng cứ → xếp diễn biến → chỉ mâu thuẫn → tính yêu cầu → soạn phương án. Ngày 4 thêm buổi đối chiếu; ngày 10 thêm giới hạn và bản sao; ngày 20 thêm phạm vi đại diện; ngày 40 thêm soát cuối. '+DISCLAIMER)

