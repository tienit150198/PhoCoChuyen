"""v0.3 authored, fictional content. No scraped characters, art or real itinerary.
Definitions are separate from executable rules in experiences.py.
"""
from __future__ import annotations
import copy

NEW_CAREERS = ('teacher', 'tour_guide', 'milk_tea')
META = {
 'teacher':dict(short='Một ngày làm giáo viên',place='Lớp học Mầm Nắng',tagline='Một cách giảng mới. Một ánh mắt hiểu bài.',icon='book',color='#779e72',light='#edf3dd',weather='Sân trường nắng',work='Tiết học',station='Bảng và góc học tập',greeting='Soạn tiết học, điểm danh và giúp từng bạn hiểu bài theo cách riêng.',caption='Dạy học là tìm một cách giải thích khác',map_label='05 · LỚP HỌC MẦM NẮNG'),
 'tour_guide':dict(short='Hướng dẫn viên du lịch',place='Chuyến đi Mây Lang Thang',tagline='Đi cùng nhau. Mang về một câu chuyện.',icon='compass',color='#418d94',light='#e0f3f0',weather='Gió trên bến',work='Đoàn tham quan',station='Bản đồ hành trình',greeting='Hỏi sở thích đoàn, chọn lộ trình và kiểm đủ người trước khi đi nhé.',caption='Chuyến đi vui không chỉ là tới đủ điểm',map_label='06 · MÂY LANG THANG'),
 'milk_tea':dict(short='Tiệm trà sữa',place='Trà Mây & Trân Châu',tagline='Một chút trà. Một chút chuyện dễ thương.',icon='coffee',color='#df7196',light='#fff0e8',weather='Nắng bên hiên',work='Ly nước',station='Quầy pha chế',greeting='Đọc món khách gọi, chọn trà, thêm topping rồi chỉnh đường và đá nhé.',caption='Pha một ly vui, nghe một chuyện nhỏ',map_label='07 · TRÀ MÂY & TRÂN CHÂU'),
}
CATALOG = [dict(id=cid,title=m['short'],name=m['short'],status='playable',core_loop=m['tagline'],**m) for cid,m in META.items()]
PEOPLE={
 'teacher':[('Cô Hạ','Đồng nghiệp','Thích cùng tìm cách giảng rõ ràng.'),('Minh','Học sinh','Thích nhìn hình mẫu trước khi thử.'),('An','Học sinh','Thích tự thử với thẻ và đồ vật.'),('Vy','Học sinh','Thích nghe ví dụ rồi trao đổi.'),('Bảo','Học sinh','Thường cần một lượt thử ngắn.'),('Cô Lan','Phụ huynh','Quan tâm tiến bộ cụ thể, không so sánh điểm với bạn khác.')],
 'tour_guide':[('Linh','Trưởng nhóm','Muốn biết lộ trình trước khi lên đường.'),('Bác Bình','Du khách','Thích nhịp đi có chỗ nghỉ.'),('Trúc','Người mê ảnh','Thích ánh sáng và chi tiết nhỏ.'),('Nam','Bạn đồng hành','Hay để ý biển chỉ dẫn.'),('Cô Gốm','Chủ xưởng gốm','Thích kể chuyện về những hoa văn tự sáng tác.'),('Hải','Điều phối','Luôn hỏi lại số người trước khi di chuyển.')],
 'milk_tea':[('Linh','Khách quen','Thích ít đường và hỏi rõ topping.'),('Bác Tư','Hàng xóm','Thích trà nhẹ, thường mang một câu chuyện vui.'),('Miu','Người chụp ảnh','Thích một góc quán yên tĩnh.'),('Hân','Người làm nội dung','Có thể hợp tác khi hai bên thống nhất rõ.'),('Bình','Bạn giao nguyên liệu','Giao theo phiếu và hỗ trợ kiểm lô.'),('Nhi','Bạn phụ quầy','Thích công thức có bước rõ ràng.')],
}
from .careers import PLUGINS as _PLUGINS
for _cid,_mod in _PLUGINS.items():PEOPLE[_cid]=[tuple(r[:3]) for r in _mod.SPEC['people']]
NPCS=[]
for cid,rows in PEOPLE.items():
 for i,(name,role,personality) in enumerate(rows):
  NPCS.append(dict(id=f'{cid}_npc_{i+1:02d}',career_id=cid,display_name=name,role=role,personality=personality,appearance=dict(hair=['brown','black','auburn'][i%3],outfit=['mint','rose','blue'][i%3]),likes=['Những câu chuyện có thật'],memory_policy='Chỉ ghi sự kiện có nguồn.'))

INGREDIENTS=[
 dict(id='milk',name='Trà sữa',group='base',emoji='🥛',color='#c39b74',cost=4,life=3,level=1),
 dict(id='black',name='Hồng trà',group='base',emoji='🫖',color='#a7734d',cost=3,life=3,level=1),
 dict(id='matcha',name='Matcha',group='base',emoji='🍵',color='#98b77b',cost=5,life=3,level=1),
 dict(id='green',name='Lục trà',group='base',emoji='🍃',color='#c9c77a',cost=3,life=3,level=2),
 dict(id='oolong',name='Trà ô long',group='base',emoji='🍂',color='#b8864f',cost=4,life=3,level=3),
 dict(id='thai',name='Trà Thái',group='base',emoji='🧡',color='#e39a5b',cost=4,life=3,level=4),
 dict(id='lychee',name='Vải',group='flavor',emoji='🌸',color='#e9b8ca',cost=2,life=4,level=1),
 dict(id='peach',name='Đào',group='flavor',emoji='🍑',color='#edb187',cost=2,life=4,level=1),
 dict(id='strawberry',name='Dâu',group='flavor',emoji='🍓',color='#dd7e94',cost=3,life=4,level=1),
 dict(id='passion',name='Chanh dây',group='flavor',emoji='💛',color='#f0c64f',cost=2,life=4,level=3),
 dict(id='pearls',name='Trân châu đen',group='topping',emoji='🟤',color='#67503e',cost=2,life=1,level=1),
 dict(id='jelly',name='Thạch mây',group='topping',emoji='🧊',color='#dfdcb4',cost=2,life=3,level=1),
 dict(id='foam',name='Foam sữa',group='topping',emoji='☁️',color='#fff2d9',cost=3,life=1,level=1),
 dict(id='popping',name='Trân châu popping',group='topping',emoji='🟠',color='#e8b576',cost=3,life=2,level=1),
 dict(id='q3',name='Thạch 3Q',group='topping',emoji='🟨',color='#e2cf8c',cost=2,life=3,level=2),
 dict(id='pudding',name='Pudding trứng',group='topping',emoji='🥚',color='#f3d27a',cost=3,life=2,level=2),
 dict(id='white_pearl',name='Trân châu trắng',group='topping',emoji='⚪',color='#eeeae0',cost=2,life=1,level=3),
 dict(id='aloe',name='Nha đam',group='topping',emoji='🌿',color='#cfe5c0',cost=2,life=3,level=3),
 dict(id='cheese',name='Kem cheese',group='topping',emoji='🧀',color='#fbe7a8',cost=4,life=1,level=4),
 dict(id='coconut',name='Thạch dừa',group='topping',emoji='🥥',color='#f4f1e6',cost=2,life=3,level=4),
 dict(id='red_bean',name='Đậu đỏ',group='topping',emoji='🫘',color='#9c4a3c',cost=2,life=2,level=5),
 dict(id='flan',name='Bánh flan',group='topping',emoji='🍮',color='#e7b35c',cost=3,life=2,level=5),
]
INGREDIENT_INDEX={x['id']:x for x in INGREDIENTS}
LESSONS=[
 dict(title='Cộng những điều nhỏ',topic='Toán vui',prompt='3 ngôi sao thêm 4 ngôi sao có tất cả bao nhiêu?',answer=7,choices=[6,7,8],fact='Đếm 3 ngôi sao rồi đếm thêm 4: được 7 ngôi sao.'),
 dict(title='Chia đều giỏ bút',topic='Toán vui',prompt='Có 12 bút, chia đều cho 3 bàn. Mỗi bàn có mấy bút?',answer=4,choices=[3,4,6],fact='Ba nhóm, mỗi nhóm 4 bút: 4 + 4 + 4 = 12.'),
 dict(title='Nhìn nhịp hoa văn',topic='Quan sát',prompt='Hoa – lá – hoa – lá – ... Hình tiếp theo là gì?',answer='Hoa',choices=['Lá','Hoa','Mây'],fact='Hai hình hoa và lá luân phiên; sau lá là hoa.'),
 dict(title='Đọc lời nhắn nhỏ',topic='Đọc hiểu',prompt='Thư viết: “An để sách ở kệ xanh.” Sách đang ở đâu?',answer='Kệ xanh',choices=['Bàn đỏ','Kệ xanh','Cửa sổ'],fact='Dùng chi tiết được viết trong thư: sách ở kệ xanh.'),
 dict(title='Những chiếc lá giấy',topic='Đếm hình',prompt='Có 5 lá giấy, gấp thêm 3 lá. Tổng cộng mấy lá?',answer=8,choices=[7,8,9],fact='5 lá ban đầu cộng 3 lá mới bằng 8 lá.'),
 dict(title='Hình nào khác nhóm?',topic='Phân loại',prompt='Tròn – vuông – tròn – tròn. Hình nào khác ba hình còn lại?',answer='Vuông',choices=['Tròn','Vuông','Tất cả giống nhau'],fact='Chỉ có một hình vuông, ba hình còn lại đều tròn.'),
 dict(title='Lịch trực thư viện',topic='Đọc bảng',prompt='Bảng ghi: thứ hai Minh, thứ ba Vy. Ai trực thứ ba?',answer='Vy',choices=['Minh','Vy','An'],fact='Đối chiếu dòng thứ ba: tên được ghi là Vy.'),
 dict(title='Đo bằng khối gỗ',topic='Đo lường',prompt='Hai dải dài 4 và 6 khối. Dải thứ hai dài hơn mấy khối?',answer=2,choices=[2,4,10],fact='So chiều dài: 6 trừ 4 còn 2 khối.'),
]
METHODS=[dict(id='visual',name='Minh họa bằng hình',emoji='🖼️'),dict(id='hands',name='Cho tự thử bằng thẻ',emoji='🧩'),dict(id='story',name='Kể một ví dụ ngắn',emoji='💬')]
STUDENTS=[dict(id='minh',name='Minh',method='visual',need='Mình muốn nhìn một hình mẫu trước.'),dict(id='an',name='An',method='hands',need='Cho mình tự thử bằng thẻ nhé.'),dict(id='vy',name='Vy',method='story',need='Mình muốn nghe một ví dụ dễ hiểu.'),dict(id='bao',name='Bảo',method='hands',need='Mình thử một lượt ngắn được không?')]
LESSON_STEPS=[dict(id='demo',name='Ví dụ trên bảng',emoji='🖼️'),dict(id='practice',name='Thử theo nhóm',emoji='🧩'),dict(id='reflect',name='Câu hỏi cuối tiết',emoji='💡')]

PLACES=[
 dict(id='gate',name='Bến Mây',emoji='⛵',x=12,y=70,minutes=0,fee=0,indoor=False,fact='Bến có một chiếc thuyền giấy màu xanh trong câu chuyện của phố.',question='Chiếc thuyền giấy ở bến có màu gì?',answers=['Xanh','Đỏ','Tím'],answer='Xanh',target='boat'),
 dict(id='museum',name='Nhà Gốm Kể Chuyện',emoji='🏺',x=29,y=27,minutes=20,fee=6,indoor=True,fact='Biểu tượng của Nhà Gốm là một chiếc bình có ba chiếc lá.',question='Chiếc bình biểu tượng có mấy chiếc lá?',answers=['Hai','Ba','Bốn'],answer='Ba',target='vase'),
 dict(id='garden',name='Vườn Lá Nhỏ',emoji='🌳',x=67,y=18,minutes=15,fee=0,indoor=False,fact='Trong vườn, ghế vàng nằm cạnh cây hình trái tim.',question='Ghế cạnh cây trái tim có màu gì?',answers=['Vàng','Xanh','Trắng'],answer='Vàng',target='tree'),
 dict(id='market',name='Chợ Mây Sớm',emoji='🏮',x=82,y=56,minutes=15,fee=2,indoor=True,fact='Chợ Mây treo đèn lồng hình ngôi sao do các tiệm cùng làm.',question='Đèn lồng của chợ có hình gì?',answers=['Sao','Tròn','Thỏ'],answer='Sao',target='lantern'),
 dict(id='river',name='Lối Bờ Mây',emoji='🌊',x=50,y=77,minutes=20,fee=0,indoor=False,fact='Cầu nhỏ có một biển chỉ hình con cá màu cam.',question='Biển trên cầu vẽ con gì?',answers=['Cá','Mèo','Chim'],answer='Cá',target='fish'),
 dict(id='cafe',name='Hiên Trà Nghỉ Chân',emoji='☕',x=45,y=47,minutes=10,fee=3,indoor=True,fact='Hiên Trà dùng con mèo ngủ làm biểu tượng góc nghỉ.',question='Biểu tượng góc nghỉ là gì?',answers=['Mèo ngủ','Chó chạy','Chim bay'],answer='Mèo ngủ',target='cat'),
]
PLACE_INDEX={x['id']:x for x in PLACES}
PHOTO_OBJECTS=[dict(id=x,emoji=y,name=z) for x,y,z in [('boat','⛵','Thuyền giấy'),('vase','🏺','Bình lá'),('tree','🌳','Cây trái tim'),('lantern','🏮','Đèn lồng sao'),('fish','🐟','Biển cá'),('cat','🐈','Mèo ngủ')]]
VISITORS=[dict(id='linh',name='Linh'),dict(id='binh',name='Bác Bình'),dict(id='truc',name='Trúc'),dict(id='nam',name='Nam')]
WEATHERS=[dict(id='sun',name='Nắng nhẹ',emoji='☀️',description='Một ngày sáng, hợp đi dạo và chụp ảnh.'),dict(id='rain',name='Mưa rào',emoji='🌦️',description='Lối Bờ Mây tạm đóng; chọn điểm có mái che.'),dict(id='breeze',name='Gió mát',emoji='🍃',description='Đi theo nhịp vừa phải, ghé một góc nghỉ.')]
MODES=[dict(id='calm',name='Một ngày thư thả',description='Hai công việc mở đầu, không giảm kiên nhẫn.'),dict(id='normal',name='Một ngày đời thường',description='Ba công việc, thêm chuyện nhỏ ở khu phố.'),dict(id='festival',name='Ngày hội khu phố',description='Bốn công việc và một nhiệm vụ ngày hội tự chọn.')]

# Four interactive puzzle families per profession; theme changes the actual cards/rules.
THEMES={
 'mother_baby':('🎁','Quà và kệ xinh',[('Thỏ bông','Đồ chơi'),('Khăn Lá','Đồ mềm'),('Gấu nhỏ','Đồ chơi'),('Áo Mây','Đồ mềm')],['Hỏi nhu cầu','Chọn đúng món','Gói quà','Kiểm và giao']),
 'pharmacy':('🧰','Mã hộp cẩn thận',[('P-01 · đủ điều kiện','Kệ sẵn sàng'),('P-02 · tạm giữ','Khu kiểm lại'),('P-03 · đủ điều kiện','Kệ sẵn sàng'),('P-04 · quá hạn','Khu kiểm lại')],['Đọc phiếu','Đọc mã lô','Đối chiếu số lượng','Kiểm rồi bàn giao']),
 'accounting':('📒','Bàn số có nguồn',[('Phiếu gốc 120','Nguồn gốc'),('Bản nháp tổng','Chờ kiểm'),('Sao kê đã xác nhận','Nguồn gốc'),('Lời kể chưa đối chiếu','Chờ kiểm')],['Nhận nguồn','Kiểm tham chiếu','Ghép giao dịch','Giải thích kết quả']),
 'customer_care':('🎧','Lắng nghe tới nơi',[('Yêu cầu vừa tới','Cần xác minh'),('Kho đã xác nhận thực hiện','Có kết quả'),('Khách đang mô tả','Cần xác minh'),('Biên nhận đã đối chiếu','Có kết quả')],['Hiểu vấn đề','Kiểm chứng cứ','Phối hợp thực hiện','Kiểm rồi đóng']),
 'teacher':('🏫','Góc lớp học vui',[('Bút màu','Góc vẽ'),('Thẻ hình','Góc ghép'),('Giấy vẽ','Góc vẽ'),('Khối gỗ','Góc ghép')],['Ví dụ dễ hiểu','Làm thử cùng nhau','Thử độc lập','Phản hồi cụ thể']),
 'tour_guide':('🧭','Hộ chiếu khu phố',[('Bình nước','Mang theo'),('Lịch hẹn đoàn','Mang theo'),('Cốc gốm trưng bày','Để tại điểm'),('Biển chỉ đường','Để tại điểm')],['Hỏi nhu cầu đoàn','Chốt lộ trình','Kiểm đủ người','Cùng khởi hành']),
 'milk_tea':('🧋','Bàn trà ngọt ngào',[('Hồng trà','Trà nền'),('Matcha','Trà nền'),('Trân châu','Topping'),('Thạch mây','Topping')],['Đọc món khách','Chọn trà nền','Thêm và chỉnh vị','Kiểm rồi giao']),
}
for _cid,_mod in _PLUGINS.items():
 if _mod.SPEC.get('activity'):THEMES[_cid]=tuple(_mod.SPEC['activity'])
ACTIVITIES=[]
for cid,(em,label,cards,steps) in THEMES.items():
 for kind,title,desc in [('sort','Xếp đúng góc','Bấm chọn thẻ rồi chọn ngăn; có thể kéo thả trên máy tính.'),('pairs','Ghép đôi nhãn','Mở từng cặp thẻ và tìm những hình giống nhau.'),('sequence','Xếp nhịp công việc','Chọn các bước theo thứ tự; có hoàn tác trước khi kiểm.'),('match','Nối hai nửa','Đọc dấu hiệu và nối hai thẻ có liên quan.')]:
  ACTIVITIES.append(dict(id=cid+'-'+kind,career=cid,type=kind,title=title+' · '+label,emoji=em,description=desc,cards=cards,steps=steps))
ACTIVITY_INDEX={x['id']:x for x in ACTIVITIES}
ACHIEVEMENTS=[
 dict(id='first',title='Việc đầu tiên',emoji='🌱',metric='served',goal=1),dict(id='regular',title='Người quen trong phố',emoji='🤝',metric='served',goal=8),
 dict(id='master',title='Bàn tay quen việc',emoji='🌟',metric='served',goal=20),dict(id='play',title='Thử một trò nhỏ',emoji='🧩',metric='activities',goal=1),
 dict(id='play_more',title='Thích khám phá',emoji='🎲',metric='activities',goal=8),dict(id='perfect',title='Một lượt thật gọn',emoji='✨',metric='perfect',goal=3),
 dict(id='reply',title='Tiệm biết lắng nghe',emoji='💬',metric='replies',goal=3),dict(id='plant',title='Góc nhỏ của mình',emoji='🪴',metric='decorations',goal=1),
 dict(id='story',title='Chuyện có hồi kết',emoji='📔',metric='chapters',goal=1),dict(id='week',title='Bảy ngày làm nghề',emoji='🗓️',metric='days_closed',goal=7),
 dict(id='fair',title='Hẹn ở ngày hội',emoji='🎏',metric='festivals',goal=1),dict(id='passport',title='Dấu chân khu phố',emoji='🧭',metric='town_visits',goal=4),
]
STORY_TITLES={
 'mother_baby':['Hộp quà của bác Tư','Một clip, hai lời kể','Buổi gói quà khu phố'],
 'pharmacy':['Lan mang phiếu đủ','Khoa kiểm thêm một lần','Góc vật dụng cộng đồng'],
 'accounting':['Huy tự tìm được lỗi','Sổ cô Hoa gọn hơn','Không sửa số chỉ để khớp'],
 'customer_care':['Không phải kể lại lần nữa','Lời hẹn được giữ','Từ review tới việc đã xong'],
 'teacher':['Minh tìm được cách học','Một buổi trò chuyện với phụ huynh','Ngày trưng bày của lớp'],
 'tour_guide':['Chuyến đi của bác Bình','Cơn mưa không làm mất vui','Album gửi lại cả đoàn'],
 'milk_tea':['Ly ít đường của Linh','Hân xin quay một chiếc clip','Một bàn trà cho khu phố'],
}
for _cid,_mod in _PLUGINS.items():
 if _mod.SPEC.get('stories'):STORY_TITLES[_cid]=[x[0] for x in _mod.SPEC['stories']]
STORIES=[]
for cid,titles in STORY_TITLES.items():
 for i,title in enumerate(titles):
  STORIES.append(dict(id=f'{cid}-chapter-{i+1}',career=cid,title=title,goal=(i+1)*2,reward=25,
    beats=[dict(text=f'Có lời nhắn về “{title}”. Người gửi muốn nghe cách bạn dự định làm.',choices=[dict(id='listen',label='Hỏi thêm và lắng nghe'),dict(id='plan',label='Cùng chốt một việc nhỏ')]),
           dict(text='Một lời hứa nhỏ cần được thực hiện, không chỉ nói trong chat. Hoàn thành một công việc mới kể từ cuộc trò chuyện để tiếp tục.',choices=[dict(id='show',label='Cho xem việc đã làm'),dict(id='explain',label='Giải thích điều đã thay đổi')]),
           dict(text='Việc đã có kết quả. Bạn muốn lưu lại điều gì?',choices=[dict(id='memory',label='Lưu một tấm thiệp kỷ niệm'),dict(id='share',label='Kể chuyện lên bảng tin')])]))

STORY_TEXT = {'mother_baby': [('Bác Tư đặt tấm thiệp chưa viết gì lên quầy: “Bác chọn được quà rồi, nhưng muốn cháu giúp bác nghĩ cách trao cho thật vui.”', 'Bác ghé lại xem cách bạn chuẩn bị món quà. Hai bác cháu thử kể chuyện về người nhận, không cần nói điều riêng tư.', 'Bác giữ một thiệp, gửi tiệm một thiệp: “Quà nhỏ nhưng cháu chịu nghe bác kể.”'), ('Bảo xin quay ở góc cửa sổ. Một khách khác không muốn lọt vào hình. Cùng thống nhất một góc quay chỉ có đồ trưng bày nhé.', 'Bảo trở lại sau ca phục vụ để xem góc quay đã thống nhất. Bạn chọn cho xem cách phục vụ hoặc giải thích quy tắc hình ảnh.', 'Một buổi quay có ranh giới rõ ràng được lưu thành thiệp hậu trường, không hứa hẹn lượt xem hay doanh số.'), ('Mai hỏi: “Cuối ca có thể chỉ mình gói một hộp quà không?” Bạn đề nghị cả phố mang hộp đã dùng để cùng thử.', 'Bạn hoàn thành công việc tiếp theo và mang kinh nghiệm gói gọn, kiểm đúng món ra bàn chung.', 'Mỗi người giữ một chiếc nơ. Tiệm có thêm một thiệp “Buổi quà nhỏ”, không phải một cuộc thi bán hàng.')], 'pharmacy': [('Lan cầm phiếu rõ mã: “Lần trước mình chỉ nhớ màu, hôm nay mình mang đúng phiếu rồi.”', 'Bạn cùng Lan nhìn lại cách đối chiếu thông tin trước khi lấy hộp, không phỏng đoán nội dung chuyên môn.', 'Lan gửi một chậu cây giấy để cảm ơn việc giải thích rõ ràng.'), ('Khoa nhận ra hai bao bì quá giống nhau. Bạn ấy muốn cùng làm nhãn vị trí thay vì cố nhớ bằng màu.', 'Sau một công việc kiểm phiếu nữa, hai người trao đổi điều cần so sánh: mã, số lượng và trạng thái lô.', 'Khoa ghim lời nhắc “Đọc mã trước” ở góc bàn. Chậm một nhịp giúp tránh nhầm.'), ('Vy muốn chụp một góc phục vụ của khu phố. Cô Thu nhắc không để phiếu của khách xuất hiện trong ảnh.', 'Bạn chọn một cách trình bày không có thông tin riêng: góc ghế chờ hoặc bảng hướng dẫn quy trình.', 'Bộ ảnh chỉ kể về không gian và cách giao nhận cẩn thận; không đưa lời khuyên dùng thuốc.')], 'accounting': [('Huy đẩy sang một thẻ sai lệch: “Cứ nhìn tổng không khớp là mình rối.” Bạn đề nghị bắt đầu từ một nguồn nhỏ.', 'Sau một vụ đã kiểm xong, bạn chỉ ra đường đi từ phiếu tới giao dịch, thay vì đưa sẵn con số cuối.', 'Huy tự viết được ba bước kiểm nguồn. Một thiệp “Từng số một” được ghim lên bàn.'), ('Cô Hoa có một túi phiếu: “Cô chỉ muốn biết số nào đã nhận, số nào đang chờ.”', 'Bạn dùng một công việc đã hoàn tất để cùng chọn cách giải thích, tách điều có bằng chứng khỏi phần cần hỏi thêm.', 'Cô Hoa cất một tờ hướng dẫn tự chuẩn bị tài liệu. Không cần nhiều thuật ngữ mới hiểu được sổ.'), ('Chị Vân hỏi trước giờ chốt: “Mình có thể ghi rõ phần đang chờ thay vì sửa cho khớp không?”', 'Bạn trình lại một kết quả có nguồn và các bước xác minh; phần chưa rõ tiếp tục mang nhãn chờ.', 'Nhóm giữ bản cũ và cách giải thích, không âm thầm thay số. Kỷ niệm của lần chốt minh bạch.')], 'customer_care': [('Phúc mở đầu: “Mình đã kể việc này nhiều lần rồi.” Bạn nhận đọc lại thông tin trước khi hỏi thêm.', 'Sau một hồ sơ được xử lý đến nơi, bạn cùng trưởng ca trao đổi cách không bắt khách kể lại dữ kiện đã có.', 'Phúc nhận một lời cập nhật có bước tiếp theo rõ ràng. Thiệp ghi điều quan trọng: đọc trước khi hỏi.'), ('Ca sắp đổi, Ngọc nhắc: “Đừng để lời hẹn nằm riêng trong đầu một người nhé.”', 'Bạn đem một công việc vừa hoàn tất ra rà soát: vấn đề, bằng chứng, việc đã làm và mốc cập nhật.', 'Nhóm lưu mẫu bàn giao. Khách không cần kể lại từ đầu.'), ('Hà góp ý: “Xin lỗi là tốt, nhưng điều gì sẽ khác ở lần sau?” Bạn đề nghị cùng xem một ví dụ đã xử lý.', 'Bạn trình kết quả được kiểm chứng, chỉ rõ việc có thể cải tiến; không hứa rằng mọi sự cố sẽ biến mất.', 'Một thiệp “Lời nhắn thành việc làm” xuất hiện. Review gốc không bị mua hoặc tự xóa.')], 'teacher': [('Minh nhìn hình ngôi sao, rồi giơ tay: “Cho mình nhìn một ví dụ trước khi trả lời được không?”', 'Sau một tiết học nữa, cô Hạ cùng bạn nhìn những phản hồi đã làm và thử một cách diễn đạt rõ hơn.', 'Lớp giữ tấm thiệp ngôi sao. Tiến bộ là thử lại, không phải so điểm của Minh với ai khác.'), ('An và Vy muốn làm góc kể chuyện bằng thẻ. Một bạn thích tự xếp, một bạn thích nói thành lời.', 'Bạn mang một điều đã học trong tiết mới vào cuộc trao đổi: cùng mục tiêu nhưng có thể dùng cách diễn đạt khác.', 'Hai chiếc thẻ đứng cạnh nhau trên bảng. Lớp có chỗ cho cả người nói nhiều lẫn người muốn quan sát.'), ('Cô Lan hỏi trong buổi trao đổi: “Hôm nay lớp đã hiểu thêm điều gì?” Bạn muốn trả lời bằng ví dụ cụ thể.', 'Sau tiết kế tiếp, bạn chọn cách giải thích quá trình thử và sửa. Không công bố bảng xếp hạng hay thông tin riêng của các bạn nhỏ.', 'Cô Lan nhận một thiệp về hoạt động của lớp. Câu chuyện kết thúc bằng lời nhắn cùng hỗ trợ.')], 'tour_guide': [('Bác Bình thích nghe chuyện nhưng muốn có chỗ ngồi giữa chuyến. Linh nhờ bạn cùng cân nhắc nhịp đi.', 'Sau một chuyến đã hoàn thành, bạn cùng đoàn trao đổi về những điểm dừng nghỉ và việc kiểm đủ người.', 'Bưu thiếp cuối chuyến ghi: đi ít hơn một chút vẫn có thể mang về nhiều chuyện.'), ('Trúc muốn một bộ ảnh không chỉ có khuôn mặt: “Mình chụp những dấu hiệu nhỏ của phố nhé?”', 'Sau chuyến tiếp theo, cả nhóm xem lại cách dùng chi tiết trên bảng chuyện để tìm đúng chủ thể ảnh.', 'Mỗi bạn giữ một bưu thiếp, kỷ niệm của hành trình cùng nhau.'), ('Mưa tới, Hải mở bản đồ: “Đổi đường được, nhưng đừng bỏ quên điều đoàn muốn trải nghiệm.”', 'Bạn hoàn thành một chuyến nữa rồi cùng xem cách chọn điểm có mái che, thời gian và nơi nghỉ phù hợp.', 'Bộ thiệp Ngày mưa được lưu. Không cần chạy qua tất cả điểm mới gọi là một chuyến đi tốt.')], 'milk_tea': [('Bác Tư chỉ vào menu: “Hôm nay bác muốn ít ngọt, còn chuyện thì kể hơi nhiều có được không?”', 'Bạn pha tiếp một ly đúng yêu cầu rồi quay lại nghe bác kể về góc quán ngày đầu.', 'Bác để lại một thiệp chiếc ly làm kỷ niệm.'), ('Miu xin ngồi góc cửa sổ để chụp bộ ảnh ly nước. Hân muốn quay clip nhưng cần hỏi những khách đang ngồi gần.', 'Sau một đơn mới được hoàn thành, bạn và hai người thống nhất chỉ quay góc đã được phép, không quay dữ liệu hay khách khác.', 'Tiệm có thiệp hậu trường. Chất lượng ly nước vẫn theo đơn, không theo việc người nhận có nhiều người theo dõi.'), ('Nhi xếp phiếu lên quầy: “Ngày hội mình pha vài ly thật cẩn thận, đừng nhận quá sức nhé?”', 'Bạn làm thêm một đơn, cùng trao đổi các bước kiểm topping, đường, đá và nguyên liệu theo lô.', 'Nhi treo thiệp Một quầy vừa đủ. Niềm vui là mọi người được phục vụ rõ ràng, không phải nhiều lượt nhất.')]}
for _pid,_mod in _PLUGINS.items():
 if _mod.SPEC.get('stories'):STORY_TEXT[_pid]=[tuple(x[1]) for x in _mod.SPEC['stories']]
for _cid, _rows in STORY_TEXT.items():
 for _i, _texts in enumerate(_rows):
  _st=next(v for v in STORIES if v["id"]==f"{_cid}-chapter-{_i+1}")
  for _j, _text in enumerate(_texts):_st["beats"][_j]["text"]=_text
STORY_INDEX={x['id']:x for x in STORIES}
TOWN=[dict(id='square',name='Quảng trường Mây',emoji='🎏',x=50,y=42,description='Nhận lời mời ngày hội của khu phố.'),dict(id='library',name='Thư viện góc phố',emoji='📚',x=20,y=28,description='Một trò xếp bước và những mẩu chuyện nghề.'),dict(id='garden',name='Vườn nghỉ nhỏ',emoji='🌳',x=78,y=22,description='Một trò lật thẻ, một khoảng nghỉ không tốn xu.'),dict(id='studio',name='Xưởng đồ xinh',emoji='🎨',x=23,y=72,description='Thử trò nối nhãn, rồi chăm chút góc của mình.'),dict(id='market',name='Chợ cuối phố',emoji='🏡',x=77,y=73,description='Thử xếp món và khám phá bảng tin khu phố.')]


def make_task(career:str,day:int,slot:int,serial:int)->dict:
 n=(day-1)*3+slot
 t=dict(id=f'{career}-{day:04d}-{slot:02d}',career=career,day=day,status='new',created_turn=serial,known=False,inspected=[],notes=[],mistakes=0,chat=[],kind=career,deferred=False,npc=f'{career}_npc_{n%3+1:02d}')
 if career=='teacher':
  lesson=copy.deepcopy(LESSONS[n%len(LESSONS)]);students=copy.deepcopy(STUDENTS)
  for i,st in enumerate(students):
   st['present']=not (day%3==0 and i==3)
   st['submission']=lesson['answer'] if (n+i)%3 else next(v for v in lesson['choices'] if v!=lesson['answer'])
  t.update(title=lesson['title'],opening='Lớp sẵn sàng rồi. Mình cùng làm một tiết '+lesson['topic'].lower()+' nhé.',lesson=lesson,students=students,attendance={},plan=[],taught={},grades={},feedback={},stage='plan')
 elif career=='tour_guide':
  weather=WEATHERS[(day-1)%3]['id'];required=(['museum','market'] if n%2==0 or weather=='rain' else ['garden','river'])
  t.update(title=['Theo dấu chuyện gốm','Một vòng phố xanh','Chuyến đi chậm rãi'][n%3],opening='Đoàn muốn một chuyến đi vừa sức, có góc nghỉ và vài tấm ảnh kỷ niệm.',weather=weather,required=required,budget=30,limit=110,visitors=copy.deepcopy(VISITORS),route=[],at=-1,counted=[],located=False,quiz_done=False,photo_done=False,stamps=[],stage='plan',plan_cost=0)
 elif career=='milk_tea':
  from . import boba
  t.update(boba.task_fields(day,slot))
 return t

# 🏷️ Bảng giá (life_price): names for SPEC price keys a career's own tables do not name.
PRICE_NAMES = dict(them='Thêm', com_tam='Cơm tấm', com_trang='Cơm trắng', vien='Kem viên', vien_bo='Kem viên bơ', top='Topping',
                   cake='Bánh kem', breakfast='Bữa sáng', guide='Dẫn đường', patch='Thử dị ứng', room='Dọn phòng',
                   groom_s='Tắm tỉa thú nhỏ', groom_m='Tắm tỉa thú vừa', groom_l='Tắm tỉa thú lớn', groom_cat='Tắm tỉa mèo',
                   board_dog='Trông chó', board_cat='Trông mèo', care='Chăm sóc', adopt='Nhận nuôi', ship_bike='Giao xe máy',
                   ship_van='Giao xe tải', cat_dua='Cắt dũa', son_thuong='Sơn thường', son_gel='Sơn gel', thao_gel='Tháo gel',
                   noi='Nối móng', french='Vẽ French', hoa='Vẽ hoa', cham_da='Chấm đá')


def price_board() -> dict:
 """{career: [{id, name, emoji, base}]} for every plugin career with SPEC['prices'] (life_price's 75–125% band)."""
 from .careers import PLUGINS
 out = {}
 for cid, mod in PLUGINS.items():
  prices = mod.SPEC.get('prices') or {}
  if not prices:
   continue
  names = {}
  for attr in sorted(dir(mod)):
   if attr.startswith('_') or attr == 'SPEC':
    continue
   v = getattr(mod, attr)
   rows = v.items() if isinstance(v, dict) else ((x.get('id'), x) for x in v if isinstance(x, dict)) if isinstance(v, (list, tuple)) else ()
   for k, x in rows:
    if isinstance(k, str) and k in prices and k not in names and isinstance(x, dict) and isinstance(x.get('name'), str):
     names[k] = (x['name'], x.get('emoji') if isinstance(x.get('emoji'), str) else None)
  out[cid] = [dict(id=k, name=(names.get(k) or (PRICE_NAMES.get(k) or k.replace('_', ' ').capitalize(), None))[0][:60],
                   emoji=(names.get(k) or (None, None))[1] or '🏷️', base=int(v)) for k, v in prices.items()]
 return out


def public_content():
 return dict(price_board=price_board(),new_careers=list(NEW_CAREERS),ingredients=INGREDIENTS,methods=METHODS,lesson_steps=LESSON_STEPS,places=[{k:v for k,v in x.items() if k!='answer'} for x in PLACES],photo_objects=PHOTO_OBJECTS,modes=MODES,weather=WEATHERS,activities=[{k:v for k,v in x.items() if k not in ('cards','steps')} for x in ACTIVITIES],achievements=ACHIEVEMENTS,stories=STORIES,town=TOWN)

# Gentle humour appended only after an actually completed, accurate task.
# Never invent health outcomes, failed products or real people reviews.
REVIEW_ASIDES = {
 'mother_baby': ['Định mua một món thôi mà giờ lại muốn giữ luôn chiếc túi gói quà 😄', 'Món nhỏ, nhưng cảm giác được lắng nghe thì không nhỏ.', 'Hôm nay mình chọn quà, không phải chơi trò đoán ý chủ tiệm.', 'Đã nhận hàng. Xin phép giữ lại nụ cười làm quà kèm nhé!'],
 'pharmacy': ['Màu hộp có thể giống, mã hộp thì vẫn phải đọc. Quầy kiểm rất rõ.', 'Không đoán mò theo màu hộp — mình thích sự cẩn thận này.', 'Mình hỏi hơi nhiều, cảm ơn vì đã giải thích từng bước.', 'Một lượt giao nhận rõ ràng, không cần câu trả lời thần kỳ.'],
 'accounting': ['Các con số đã về đúng nhà, mình cũng bớt nhăn trán rồi 😄', 'Hóa ra bảng không cần đẹp hơn, cần đúng nguồn hơn.', 'Tổng có lời giải thích, không còn là một con số bí ẩn.', 'Chứng từ đi theo nhóm, còn mình cuối cùng theo kịp câu chuyện.'],
 'customer_care': ['Mình cần kết quả, không cần sưu tầm thêm lời hẹn. Cảm ơn nhé!', 'Cuối cùng cuộc trò chuyện cũng có một bước tiếp theo rõ ràng.', 'Đã được xử lý tới nơi, không phải chỉ đổi tên trạng thái.', 'Ít nhất hôm nay vấn đề không phải đi du lịch qua nhiều người nữa 😄'],
 'teacher': ['Một lời gợi ý đúng lúc còn quý hơn một dấu tích vội.', 'Hôm nay lớp có nhiều cách thử, không cần tất cả giống nhau.', 'Có ví dụ, có làm thử, rồi có câu hỏi để biết mình hiểu gì.', 'Bài học kết thúc, còn ý muốn thử thêm thì vẫn còn.'],
 'tour_guide': ['Mang về đủ bưu thiếp, và quan trọng nhất là đủ người 😄', 'Có chỗ nghỉ nên chuyến đi không thành cuộc thi bước chân.', 'Mỗi điểm có một câu chuyện, không chỉ một dấu tích trên bản đồ.', 'Ảnh thì nhiều, nhưng cảm ơn vì vẫn nhớ kiểm người trước khi đi.'],
 'milk_tea': ['Đường đúng mức mình chọn, còn niềm vui thì xin phép thêm một chút 😄', 'Ly này không cần đọc suy nghĩ: mình nói gì, tiệm làm đúng vậy.', 'Trân châu trong ly, còn chuyện nhỏ thì để lại trên bảng tin.', 'Gọi một ly thôi, mang về thêm một tâm trạng dễ chịu.'],
}
