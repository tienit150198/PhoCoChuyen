"""Optional neighbourhood activities, with player choices and durable souvenirs.

No external posts or shared-player mutations. A life-day visit charges once and
records the chosen outcome through the normal command receipt transaction.
"""
from __future__ import annotations
import copy
from . import bank, needs, archive as ar


def _place(id, name, emoji, host, cost, intro, choices):
    return dict(id=id,name=name,emoji=emoji,host=host,cost=cost,intro=intro,
                choices=[dict(id=k,name=n,keepsake=m,story=t) for k,n,m,t in choices])


PLACES = [
    _place('books','Hiệu sách cũ Mực Nâu','📚','Cô Mực',12,
           'Trong thùng sách vừa nhận có những lời nhắn chưa gửi. Bạn muốn mang cuốn nào về?',[
        ('letter','Cuốn sách kẹp thư','Lá thư bên trang 42',[
            'Bạn tìm thấy lá thư của một người con cảm ơn mẹ vì những bữa cơm chờ. Cô Mực giữ lại phong bì để tìm người nhận; bạn mang cuốn sách về đọc.',
            'Người gửi thư đã quay lại. Cô Mực kể hai mẹ con vừa cùng ghé tiệm, và gửi bạn chiếc thẻ đánh dấu trang hình bát cơm.',
            'Trang cuối còn trống. Bạn viết vào đó một điều muốn nói với người thân, rồi cất sách lên kệ.']),
        ('map','Tập truyện có bản đồ','Bản đồ tiệm sách nhỏ',[
            'Bản đồ dẫn đến chiếc ghế dưới cây sấu. Ở đó có mẩu chuyện về bác bán báo luôn để dành truyện tranh cho trẻ trong phố.',
            'Bạn theo nét bút chì tìm tới sạp báo cũ. Bác kể ngày mưa mọi người từng chuyền sách qua mái hiên để chúng khỏi ướt.',
            'Bạn bổ sung tiệm Mực Nâu vào bản đồ. Một nơi mới để người sau tìm được câu chuyện của mình.']),
        ('garden','Sổ tay làm vườn','Trang ép hoa đầu mùa',[
            'Giữa trang sách là một bông hoa ép. Dòng chữ nhỏ nhắc rằng cây lớn chậm nhưng người chăm không cần vội.',
            'Bạn thử ghi lại màu lá và buổi tưới đầu tiên, thay vì chỉ đếm ngày ra hoa. Cô Mực tặng thêm một tờ giấy ép lá.',
            'Cuốn sổ có thêm nét chữ của bạn. Bạn để lại một trang trống cho người sẽ cùng chăm cây sau này.'])]),
    _place('art','CLB Mỹ thuật','🎨','Chị Màu',5,'Buổi vẽ góc phố: chọn điều bạn muốn giữ lại trong tranh.',[
        ('light','Vẽ ánh sáng','Tranh Nắng qua mái hiên',['Bạn pha màu vàng dịu rồi chừa khoảng trắng. Chị Màu chỉ cách bóng mái hiên làm vệt nắng nổi hơn.','Bạn thử cùng góc phố lúc chiều xuống: màu cam nhạt, bóng dài hơn. Hai bức tranh kể hai nhịp sống khác nhau.']),
        ('people','Vẽ người trong phố','Phác họa Người hàng xóm',['Bạn xin phép bác bán hoa trước khi phác họa. Bác chọn đứng cạnh thùng cúc đang nở.','Bạn thêm đôi bàn tay đang buộc bó hoa. Chị Màu nhận ra nhân vật qua cử chỉ, dù gương mặt chỉ vài nét.'])]),
    _place('music','CLB Âm nhạc','🎵','Anh Nhịp',5,'Cả nhóm đang tập một đoạn nhạc tự sáng tác. Bạn chọn phần mình muốn thử.',[
        ('beat','Giữ nhịp cùng nhóm','Thẻ nhịp 4 phách',['Bạn gõ đều bốn phách rồi chừa chỗ cho tiếng đàn. Cả nhóm kết thúc cùng nhau.','Bạn thử giữ nhịp nhẹ ở đoạn nhỏ và mạnh hơn ở điệp khúc; cả nhóm nghe nhau rõ hơn.']),
        ('melody','Thử giai điệu','Trang nhạc Chiều bên sông',['Bạn ngân một giai điệu ngắn. Anh Nhịp chép lại để buổi sau cả nhóm thử hòa giọng.','Nhóm hát lại giai điệu bạn góp, rồi thêm một khoảng lặng trước câu cuối.'])]),
    _place('reading','CLB Đọc sách','📖','Cô Trang',0,'Nhóm đọc câu chuyện về một người trở về phố cũ. Bạn muốn chia sẻ điều gì?',[
        ('character','Nói về nhân vật','Ghi chú Người trở về',['Bạn nghĩ nhân vật im lặng vì chưa biết bắt đầu từ đâu. Cô Trang mời mọi người tìm một chi tiết trong truyện để hiểu thêm.','Bạn đọc lại lời chào ngắn ở cuối truyện và nhận ra đôi khi bắt đầu chỉ cần một câu đơn giản.']),
        ('ending','Viết một kết thúc khác','Trang kết của riêng bạn',['Bạn viết cảnh nhân vật gõ cửa tiệm quen. Một tách trà được đặt xuống, không ai hỏi vì sao đi lâu thế.','Cả nhóm đọc các kết thúc khác nhau. Bạn giữ lại phiên bản có bữa cơm đông người nhất.'])]),
    _place('garden','CLB Làm vườn','🌱','Bác Lá',5,'Bồn cây chung cần chăm. Chọn một việc và nghe bác Lá chia sẻ.',[
        ('water','Kiểm đất rồi tưới','Nhật ký bồn cây',['Bạn chạm lớp đất trước khi tưới. Chậu còn ẩm được để nghỉ; chậu khô nhận một ca nước nhỏ.','Bạn thấy mầm mới bên gốc. Bác Lá nhắc xoay chậu về phía sáng và ghi vào nhật ký.']),
        ('seed','Ươm một khay hạt','Khay mầm của nhóm',['Bạn cùng nhóm gieo hạt, ghi tên và ngày lên thẻ. Khay được đặt cạnh cửa có ánh sáng dịu.','Bạn tỉa chỗ quá dày và chia mầm cho nhóm mang về. Khay hạt giờ thành nhiều góc xanh.'])]),
    _place('karaoke','Phòng hát Mây','🎤','Chị Ngân',8,'Chọn tiết mục cho buổi hát. Có thể mở beat YouTube của bạn ở một tab riêng.',[
        ('solo','Hát một mình','Vé hát Solo',['Bạn thử đoạn đầu nhỏ nhẹ rồi hát trọn điệp khúc. Chị Ngân vỗ tay cho một lần dám cầm mic.','Bạn chọn tông vừa giọng, nghe hết đoạn dạo rồi vào câu đầu. Buổi hát thoải mái hơn lần trước.']),
        ('chorus','Hát cùng nhóm nhân vật','Vé hát Hòa giọng',['Cả nhóm chia nhau từng câu, cùng hát phần điệp khúc. Người quên lời được mọi người nhắc bằng nụ cười.','Bạn nhường câu mở đầu cho người mới, rồi hòa vào điệp khúc. Phòng hát rộn lên sau một ngày dài.'])]),
    _place('family','Bữa cơm & chuyện ông bà','🍲','Ông bà trong câu chuyện',6,'Một buổi trở về cùng các nhân vật gia đình. Chọn cách bạn muốn dành thời gian.',[
        ('meal','Chuẩn bị bữa cơm','Công thức cơm nhà',['Bạn nhặt rau, dọn bát và ngồi nghe mọi người kể một điều vui hôm nay. Bữa cơm giản dị nhưng không ai ăn vội.','Bạn nấu lại món rau của bà, bớt một chút muối theo lời dặn. Cả nhà ghi công thức vào sổ để lần sau cùng làm.']),
        ('story','Nghe ông bà kể chuyện','Chuyện dưới mái hiên',['Ông kể ngày phố còn đường đất, bà nhớ quán chè mở muộn mỗi tối. Bạn ghi lại một tên đường cũ trong sổ.','Bạn mang sổ ra hỏi tiếp câu chuyện hôm trước. Ông bà nhận ra bạn vẫn nhớ và kể thêm về người hàng xóm từng giúp cả nhà.'])]),
]
BY_ID={p['id']:p for p in PLACES}
MEMORIES=42


def _fresh():
    return dict(v=1,visits={},last={},memories=[])


def public(s):
    d=copy.deepcopy(s['journey'].get('community_outings') or _fresh())
    d['day']=s['journey']['life_day']
    return d


def action(s,p):
    from .engine import need
    need(isinstance(p,dict) and set(p)<={'place','choice','pay'},'Chọn một hoạt động trong phố.')
    place=BY_ID.get(p.get('place')) if isinstance(p.get('place'),str) else None
    choice=next((x for x in place['choices'] if x['id']==p.get('choice')),None) if place else None
    need(place and choice,'Hoạt động hoặc lựa chọn không còn hợp lệ.')
    method=p.get('pay','auto')
    need(isinstance(method,str) and method in bank.PREFS,'Chọn nguồn thanh toán hợp lệ.')
    j=s['journey'];day=j['life_day'];d=j.get('community_outings') or _fresh();key=place['id']
    if d['last'].get(key)==day:
        return dict(message='Buổi ghé hôm nay đã lưu trong sổ kỷ niệm, không thu thêm xu.',duplicate=True)
    visit=d['visits'].get(key,0)
    if place['cost']:bank.pay(s,place['cost'],place['name'],method=method,kind='life')
    d=j.setdefault('community_outings',_fresh())
    text=choice['story'][visit%len(choice['story'])]
    d['visits'][key]=visit+1;d['last'][key]=day
    d['memories'].append(dict(place=key,choice=choice['id'],day=day,visit=visit+1))
    d['memories']=ar.last(d['memories'],MEMORIES,'community.memories',ar.JOURNEY)
    needs._spirit(s,2)
    return dict(message=text,celebrate=True)


def validate(s):
    from .engine import need
    d=s['journey'].get('community_outings')
    if d is None:return
    bad='Sổ sinh hoạt trong phố không hợp lệ.';day=s['journey']['life_day']
    need(isinstance(d,dict) and set(d)=={'v','visits','last','memories'} and type(d['v']) is int and d['v']==1,bad)
    for key in ('visits','last'):
        need(isinstance(d[key],dict) and set(d[key])<=set(BY_ID),bad)
        need(all(type(x) is int and 1<=x<=day for x in d[key].values()),bad)
    need(set(d['visits'])==set(d['last']),bad)
    need(isinstance(d['memories'],list) and len(d['memories'])<=MEMORIES,bad)
    seen=set()
    for m in d['memories']:
        need(isinstance(m,dict) and set(m)=={'place','choice','day','visit'},bad)
        need(isinstance(m['place'],str) and m['place'] in d['visits'],bad)
        need(isinstance(m['choice'],str) and m['choice'] in {x['id'] for x in BY_ID[m['place']]['choices']},bad)
        need(type(m['day']) is int and 1<=m['day']<=d['last'][m['place']],bad)
        need(type(m['visit']) is int and 1<=m['visit']<=d['visits'][m['place']],bad)
        identity=(m['place'],m['day']);need(identity not in seen,bad);seen.add(identity)
