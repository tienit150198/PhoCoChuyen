"""Tour guide v2 trip ("Chuyến đi"): a mixed group with their own wishes,
weather and closures, a route where the order changes walking time, a small
group fund, a story angle at every stop and on-the-road situations with
trade-offs (lost guest, overcharging stall, flat e-bus, festival, souvenir
commission, heat, allergy, ...).

Like game/teach_lesson.py, the v1 task keeps its fixed fields and the v2 layer
lives under t['trip']. Fixed facts are rolled from (day, slot) only so that
validation can regenerate them. v1 route fields stay empty on v2 trips.
"""
from __future__ import annotations

import copy
import functools
import itertools
import math
import random

STAGES = ('plan', 'gather', 'stop', 'ready')
MIN_STOPS, MAX_STOPS = 3, 5
BASE_FEE = 70
GATE = dict(id='gate', name='Bến Mây', emoji='⛵', x=10, y=80)

PLACES = [
    dict(id='museum', name='Nhà Gốm Kể Chuyện', emoji='🏺', x=26, y=24, minutes=20, fee=6, indoor=True, tags=('culture',),
         lines=dict(history='Lò gốm đầu tiên của phố đỏ lửa ba ngày ba đêm. Chiếc bình ba lá là mẻ còn nguyên vẹn duy nhất.',
                    fun='Đố cả đoàn: người thợ gốm ký tên bằng gì? Bằng dấu vân tay in dưới đáy bình!',
                    photo='Đứng sau khung cửa tròn, ánh nắng rọi đúng dãy bình men lam.')),
    dict(id='garden', name='Vườn Lá Nhỏ', emoji='🌳', x=58, y=12, minutes=15, fee=0, indoor=False, tags=('nature', 'photo'),
         lines=dict(history='Vườn do các cụ trong phố trồng từ ngày lập chợ, mỗi nhà góp một cây.',
                    fun='Ai tìm được chiếc lá hình trái tim trước, cả đoàn vỗ tay chúc may mắn!',
                    photo='Ghế vàng cạnh cây trái tim, chụp ngược sáng rất đẹp.')),
    dict(id='market', name='Chợ Mây Sớm', emoji='🏮', x=86, y=48, minutes=15, fee=2, indoor=True, tags=('food', 'shop'),
         lines=dict(history='Chợ họp từ thời thuyền buôn còn cập bến, đèn lồng sao là của các tiệm cùng làm.',
                    fun='Thử đoán giá một bó rau muống, ai đoán sát nhất được chọn quà vặt đầu tiên!',
                    photo='Dãy đèn lồng sao chụp từ bậc thềm là đẹp nhất.')),
    dict(id='river', name='Lối Bờ Mây', emoji='🌊', x=50, y=86, minutes=20, fee=0, indoor=False, tags=('nature', 'photo'),
         lines=dict(history='Cây cầu gỗ được dựng lại sau trận lũ năm nào, biển cá cam là quà của học sinh.',
                    fun='Đếm xem có bao nhiêu con cá vẽ trên thành cầu, ai đếm đúng được đi đầu đoàn!',
                    photo='Giữa cầu nhìn về bến, mặt nước phản chiếu mây rất rõ.')),
    dict(id='cafe', name='Hiên Trà Nghỉ Chân', emoji='☕', x=44, y=50, minutes=10, fee=3, indoor=True, tags=('rest', 'food'),
         lines=dict(history='Hiên Trà vốn là chỗ người chèo đò nghỉ chân chờ khách.',
                    fun='Thử đoán chú mèo ngủ trên quầy tên gì. Gợi ý: tên một loại trà!',
                    photo='Góc cửa sổ có chú mèo ngủ, ánh sáng dịu, rất hợp ảnh chân dung.')),
    dict(id='temple', name='Chùa Gió Lành', emoji='🛕', x=10, y=46, minutes=15, fee=0, indoor=False, tags=('culture', 'rest'),
         lines=dict(history='Chuông chùa được đúc bằng đồng do dân làng góp, tiếng chuông vang tới tận bến.',
                    fun='Đố vui: sân chùa có bao nhiêu bậc thềm? Đi chậm, đếm nhỏ thôi nhé!',
                    photo='Hàng cau trước cổng tam quan, chụp từ xa để thấy cả mái cong.')),
    dict(id='craft', name='Xưởng Nón Lá', emoji='👒', x=26, y=64, minutes=20, fee=5, indoor=True, tags=('culture', 'shop'),
         lines=dict(history='Một chiếc nón có mười sáu vành tre, người thợ khâu bằng sợi cước mảnh như tóc.',
                    fun='Mỗi người thử khâu một mũi, ai khâu thẳng nhất được đội nón chụp ảnh đầu tiên!',
                    photo='Soi chiếc nón bài thơ lên nắng, hình vẽ ẩn hiện ra rất đẹp.')),
    dict(id='hill', name='Đồi Ngắm Mây', emoji='⛰️', x=88, y=14, minutes=25, fee=4, indoor=False, tags=('nature', 'photo'),
         lines=dict(history='Ngày xưa người đi biển lên đồi này xem mây để đoán thời tiết.',
                    fun='Nhìn mây đoán hình: đám mây kia giống con gì? Cả đoàn thi nhau đoán!',
                    photo='Đỉnh đồi nhìn xuống cả phố, đợi mây trôi qua là có ảnh đẹp.')),
    dict(id='food', name='Phố Ăn Vặt', emoji='🍢', x=66, y=32, minutes=15, fee=3, indoor=False, tags=('food',),
         lines=dict(history='Con phố nổi tiếng với bánh tráng nướng do một bà cụ bán từ năm mươi năm trước.',
                    fun='Thử thách: mỗi người nếm một món chưa từng ăn, rồi chấm điểm cho vui!',
                    photo='Chụp cận chiếc bánh tráng đang phồng trên bếp than, nhìn là thèm.')),
]
PLACE = {p['id']: p for p in PLACES}
PLACE_IDS = [p['id'] for p in PLACES]

TAGS = dict(culture=('🏛️', 'Văn hóa, lịch sử'), nature=('🌿', 'Thiên nhiên'), food=('🍜', 'Món ăn địa phương'),
            shop=('🛍️', 'Mua quà'), photo=('📸', 'Chụp ảnh đẹp'), rest=('🪑', 'Chỗ nghỉ chân'))
ANGLES = [dict(id='history', emoji='📜', label='Chuyện xưa'), dict(id='fun', emoji='🎈', label='Trò vui'), dict(id='photo', emoji='📸', label='Góc ảnh')]
ANGLE_IDS = [a['id'] for a in ANGLES]
BEST_ANGLE = dict(culture='history', nature='fun', food='fun', shop='fun', photo='photo', rest='history')

MEMBERS = [
    dict(id='linh', name='Linh', emoji='🧑‍💼', role='Trưởng đoàn', wish='culture', angle='history', note='Giữ lịch của cả đoàn'),
    dict(id='binh', name='Bác Bình', emoji='👴', role='Người lớn tuổi', wish='culture', angle='history', note='Đi chậm, ngại leo dốc', elder=True),
    dict(id='sau', name='Bà Sáu', emoji='👵', role='Người lớn tuổi', wish='food', angle='history', note='Đi gậy, cần chỗ ngồi', elder=True),
    dict(id='na', name='Bé Na', emoji='👧', role='Bé 7 tuổi', wish='nature', angle='fun', note='Đi cùng mẹ, mau chán', kid=True),
    dict(id='bin', name='Bé Bin', emoji='👦', role='Bé 9 tuổi', wish='food', angle='fun', note='Hiếu động, hay chạy trước', kid=True),
    dict(id='tom', name='Tom', emoji='🧔', role='Khách từ Úc', wish='food', angle='fun', note='Dị ứng đậu phộng · nói tiếng Anh', foreign=True),
    dict(id='yuki', name='Yuki', emoji='👩', role='Khách từ Nhật', wish='culture', angle='photo', note='Nói ít tiếng Việt, mê chụp ảnh', foreign=True),
    dict(id='truc', name='Trúc', emoji='📷', role='Người mê ảnh', wish='photo', angle='photo', note='Luôn cầm máy ảnh'),
    dict(id='nam', name='Nam', emoji='🧑', role='Sinh viên', wish='nature', angle='fun', note='Mặc quần đùi, áo ba lỗ'),
    dict(id='hoa', name='Chị Hoa', emoji='🙋‍♀️', role='Mê ăn uống', wish='food', angle='fun', note='Hay đòi đổi lịch'),
    dict(id='tu', name='Cô Tư', emoji='🛍️', role='Mê mua quà', wish='shop', angle='history', note='Hay đeo túi hở'),
]
MEMBER = {m['id']: m for m in MEMBERS}
OTHERS = [m['id'] for m in MEMBERS if m['id'] != 'linh']
# Carrier NPCs for member posts (the tour NPCs exist; others post through the coordinator).
CARRIER = dict(linh='tour_guide_npc_01', binh='tour_guide_npc_02', truc='tour_guide_npc_03', nam='tour_guide_npc_04')
COORD_NPC = 'tour_guide_npc_06'

WEATHER = dict(
    sun=dict(emoji='☀️', name='Nắng đẹp', text='Trời đẹp, đi đâu cũng hợp.', closed=()),
    heat=dict(emoji='🥵', name='Nắng gắt', text='Nắng gắt: tối đa 2 điểm ngoài trời.', closed=(), outdoor_max=2),
    rain=dict(emoji='🌧️', name='Mưa rào', text='Mưa: Lối Bờ Mây và Đồi Ngắm Mây tạm đóng.', closed=('river', 'hill')),
    wind=dict(emoji='🍃', name='Gió mạnh', text='Gió mạnh: Đồi Ngắm Mây tạm đóng.', closed=('hill',)),
)
CLOSE_REASONS = dict(museum='Đóng cửa kiểm kê hiện vật', garden='Đang phun thuốc cho cây', market='Chợ nghỉ phiên hôm nay',
                     craft='Xưởng nhận một đoàn đặt trước', food='Phố đang sửa đường ống', temple='Chùa có lễ riêng, không đón khách')


def _o(id, label, text, mood=0, minutes=0, cost=0, mistake=False, commission=0, note=None):
    return dict(id=id, label=label, text=text, mood=mood, minutes=minutes, cost=cost, mistake=mistake, commission=commission, note=note)


# Situations. `who` = members who can be at the centre; `weather` limits when it happens.
INCIDENTS = [
    dict(id='late', emoji='⏰', title='Chưa ra điểm hẹn', who=OTHERS, gather=True,
         text='Đã quá giờ hẹn 5 phút, {name} vẫn chưa ra điểm tập trung.',
         options=[_o('call', 'Gọi cho {name}, hẹn thêm 5 phút, đoàn chờ trong bóng râm', '{name} chạy ra, xin lỗi rối rít. Đoàn xuất phát chỉ trễ một chút.', minutes=5),
                  _o('leave', 'Cho đoàn đi luôn, ai trễ tự bắt xe theo', '{name} lạc đường, gọi điện hoảng hốt. Không bao giờ bỏ lại khách.', mood=-8, minutes=10, mistake=True),
                  _o('wait', 'Cả đoàn đứng chờ, không hẹn giờ', 'Hai mươi phút sau {name} mới ra. Cả đoàn đứng nắng, mặt ai cũng mệt.', mood=-6, minutes=20)]),
    dict(id='lost', emoji='🧭', title='Lạc khỏi đoàn', who=('yuki', 'tom'),
         text='Đếm lại đoàn thì thiếu {name}. Tin nhắn cuối cùng là một tấm ảnh chụp cái cổng sơn đỏ.',
         options=[_o('point', 'Giữ đoàn ở điểm hẹn, nhờ điều phối Hải, đi tìm theo ảnh cổng đỏ', 'Tìm thấy {name} ở cổng đỏ ngay góc phố, đang chụp ảnh. {name} cảm ơn mãi.', mood=-2, minutes=10, note='lost_found'),
                  _o('split', 'Cả đoàn tản ra đi tìm cho nhanh', 'Tìm được {name}, nhưng lại lạc thêm một người khác. Mất nửa tiếng mới gom đủ.', mood=-10, minutes=25, mistake=True),
                  _o('go', 'Đi tiếp, nhắn {name} tự bắt taxi theo', '{name} không đọc được tiếng Việt, loay hoay một mình. Lời nhắn trả lời đầy lo lắng.', mood=-15, mistake=True, note='lost_alone')]),
    dict(id='coconut', emoji='🥥', title='Sạp dừa hét giá', who=('tom', 'yuki', 'hoa', 'tu'),
         text='{name} mua dừa. Chủ sạp báo 50 nghìn một trái, gấp đôi bảng giá dán ngay trên sạp.',
         options=[_o('board', 'Lịch sự chỉ bảng giá niêm yết, trả đúng giá, cảm ơn', 'Chủ sạp cười trừ, tính đúng giá. {name} thấy yên tâm hẳn.', mood=3),
                  _o('pay', 'Kệ, để khách trả cho đỡ phiền', 'Lát sau {name} thấy bảng giá, buồn ra mặt: “Sao hướng dẫn viên không nói?”', mood=-6, note='overpaid'),
                  _o('fight', 'Lớn tiếng cãi với chủ sạp', 'Hai bên to tiếng giữa chợ, cả đoàn ngượng ngùng đứng nhìn.', mood=-8, minutes=5)]),
    dict(id='bus', emoji='🛺', title='Xe điện hết pin', who=(),
         text='Xe điện chở đoàn đứng khựng giữa đường: hết pin. Điểm tiếp theo cách chừng mười phút đi bộ.',
         options=[_o('walk', 'Dẫn đoàn đi bộ đường có bóng cây, gọi xe khác đón ở điểm sau', 'Đoàn đi bộ, vừa đi vừa nghe kể chuyện phố. Xe mới chờ sẵn ở điểm sau.', minutes=10),
                  _o('taxi', 'Gọi hai xe taxi, trả từ quỹ đoàn', 'Taxi tới sau năm phút. Nhanh, nhưng quỹ đoàn vơi đi kha khá.', minutes=5, cost=12),
                  _o('wait', 'Cả đoàn đứng chờ thợ tới sạc xe', 'Nửa tiếng đứng bên đường. Bé nhỏ trong đoàn bắt đầu mè nheo.', mood=-10, minutes=30)]),
    dict(id='parade', emoji='🐉', title='Gặp đám rước lân', who=(),
         text='Tiếng trống rộn ràng: một đám rước lân bất ngờ đi qua, phố chật kín người xem.',
         options=[_o('watch', 'Dừng mười phút, đứng gọn một góc, giải thích ý nghĩa múa lân', 'Cả đoàn xem lân, trẻ con được xoa đầu lân lấy may. Ai cũng thích!', mood=8, minutes=10, note='parade'),
                  _o('push', 'Chen qua đám đông cho kịp giờ', 'Đoàn bị kẹt giữa dòng người, bé nhỏ suýt tuột tay mẹ.', mood=-6, minutes=5, mistake=True),
                  _o('detour', 'Đi đường vòng tránh đông', 'Đường vòng xa hơn một chút, đoàn chỉ nghe tiếng trống vọng lại.', minutes=10)]),
    dict(id='commission', emoji='🎁', title='Phong bì “hoa hồng”', who=(),
         text='Chủ tiệm lưu niệm kéo riêng bạn ra: “Dẫn khách vào tiệm em, mỗi món bán được anh chị ăn 20 phần trăm.” Kèm một phong bì.',
         options=[_o('decline', 'Cảm ơn và từ chối, để khách tự chọn nơi mua, nói rõ không bắt buộc', 'Khách thong thả mua quà ở chợ, giá mềm hơn hẳn. Linh gật gù: “Đi với em yên tâm.”', mood=4, note='honest'),
                  _o('push', 'Nhận phong bì, dẫn cả đoàn vào tiệm và giục mua', 'Túi bạn dày thêm 15 xu. Tối đó, một người trong đoàn phát hiện giá ở đây gấp rưỡi ngoài chợ.', mood=-10, minutes=15, mistake=True, commission=15, note='commission'),
                  _o('quiet', 'Nhận phong bì, không nói gì, để khách tự vào', 'Bạn nhận 8 xu. Không ai biết, nhưng lúc khách hỏi “Chỗ này có rẻ không?”, bạn chỉ ậm ừ.', mood=-4, mistake=True, commission=8, note='commission')]),
    dict(id='heat', emoji='🥵', title='Choáng vì nắng', who=('binh', 'sau'), weather=('sun', 'heat'),
         text='{name} mặt đỏ bừng, xin ngồi xuống, bảo hơi chóng mặt.',
         options=[_o('shade', 'Đưa vào bóng râm, mua nước từ quỹ, cả đoàn nghỉ mười phút', '{name} uống nước mát, lau mặt, lát sau cười được. Cả đoàn cũng được nghỉ.', mood=2, minutes=10, cost=2, note='elder_thanks'),
                  _o('push', 'Động viên cố thêm chút nữa là tới', '{name} gắng đi thêm rồi phải ngồi thụp xuống. Cả đoàn hoảng.', mood=-10, minutes=10, mistake=True),
                  _o('alone', 'Để {name} ngồi nghỉ một mình, đoàn đi trước', 'Để người lớn tuổi đang mệt ngồi một mình là không an toàn. Cả đoàn phải quay lại.', mood=-8, minutes=10, mistake=True)]),
    dict(id='peanut', emoji='🥜', title='Món có đậu phộng?', who=('tom',),
         text='Tom cầm một chiếc bánh xin nếm thử. Trên bánh rắc thứ gì đó giòn giòn. Tom hỏi: “Is there peanut?”',
         options=[_o('ask', 'Hỏi kỹ người bán thành phần, chọn món khác không đậu phộng cho Tom', 'Bánh có mè và đậu phộng. Tom đổi sang chè bắp, giơ ngón cái: “Thank you!”', mood=3, note='tom_safe'),
                  _o('guess', '“No, no peanut!” cho Tom vui', 'Tom cắn một miếng rồi ngứa họng. May mà có thuốc mang theo, nhưng cả đoàn một phen hú vía.', mood=-15, minutes=15, mistake=True),
                  _o('skip', 'Bảo Tom thôi đừng ăn gì cả', 'Tom tiu nghỉu đứng nhìn cả đoàn ăn.', mood=-4)]),
    dict(id='shower', emoji='🌦️', title='Mưa rào bất chợt', who=(), weather=('rain', 'wind'),
         text='Mây kéo đen kịt, mưa rào đổ ào xuống. Đoàn đang ở ngoài trời.',
         options=[_o('shelter', 'Dẫn đoàn vào mái hiên gần nhất, mua áo mưa từ quỹ, kể chuyện chờ tạnh', 'Mưa tạnh sau mười phút. Cả đoàn khoác áo mưa màu, chụp được tấm ảnh rất vui.', mood=2, minutes=10, cost=4),
                  _o('run', 'Hô cả đoàn chạy ra xe', 'Đường trơn, Bà Sáu suýt ngã. Ai cũng ướt sũng.', mood=-6, mistake=True),
                  _o('keep', 'Cứ đi tiếp dưới mưa cho kịp lịch', 'Cả đoàn ướt như chuột lột, không ai còn tâm trí nghe kể chuyện.', mood=-10)]),
    dict(id='flash', emoji='📸', title='Đèn flash chỗ cấm chụp', who=('truc', 'yuki'),
         text='Có biển “Không dùng đèn flash”, nhưng {name} vẫn bật flash chụp liên tục.',
         options=[_o('quiet', 'Nhắc nhỏ riêng, chỉ góc có ánh sáng tự nhiên đẹp hơn', '{name} tắt flash, chụp ở góc cửa sổ. Ảnh còn đẹp hơn!', mood=1),
                  _o('loud', 'Nhắc to trước cả đoàn', '{name} ngượng đỏ mặt, cất máy luôn.', mood=-5),
                  _o('ignore', 'Làm ngơ cho khách vui', 'Bảo vệ ra nhắc cả đoàn, yêu cầu ra ngoài sớm.', mood=-4, minutes=5, mistake=True)]),
    dict(id='toilet', emoji='🚻', title='Bé cần đi vệ sinh gấp', who=('na', 'bin'),
         text='{name} kéo tay mẹ: cần đi vệ sinh gấp. Nhà vệ sinh gần nhất ở cuối dãy phố.',
         options=[_o('escort', 'Nhờ mẹ bé đi cùng, cả đoàn chờ ở chỗ dễ thấy', 'Năm phút sau hai mẹ con quay lại. Đoàn vẫn đứng đủ ở chỗ hẹn.', minutes=5),
                  _o('alone', 'Chỉ đường cho bé tự chạy đi', 'Không để trẻ nhỏ đi một mình giữa chỗ đông người. Mẹ bé hốt hoảng chạy theo.', mood=-6, mistake=True),
                  _o('hold', 'Bảo bé ráng nhịn tới điểm sau', '{name} khóc suốt quãng đường.', mood=-6)]),
    dict(id='threat', emoji='⭐', title='Dọa đánh giá một sao', who=('hoa', 'nam', 'tu'), tier=2,
         text='{name} kéo bạn ra: “Bỏ điểm tiếp theo, dẫn qua quán ốc quen của chị đi. Không thì chị cho một sao.”',
         options=[_o('firm', 'Nhẹ nhàng giữ lịch cả đoàn đã chốt, gợi ý quán ốc cho buổi tối', '{name} hơi phụng phịu, nhưng cả đoàn vẫn được đi đúng lịch.', minutes=0),
                  _o('give', 'Đổi lịch theo ý {name} cho yên chuyện', 'Cả đoàn bị kéo vào quán ốc. Linh hỏi: “Sao lịch lại đổi mà không ai hỏi ý?”', mood=-8, minutes=20, mistake=True),
                  _o('argue', 'Tranh cãi đúng sai với {name}', 'Hai bên to tiếng. Không khí cả đoàn chùng xuống.', mood=-6)]),
    dict(id='wallet', emoji='👜', title='Người lạ lảng vảng', who=('tu', 'hoa', 'sau'), tier=2,
         text='Chỗ đông người, túi của {name} mở hờ. Một người lạ cứ bám sát ngay phía sau.',
         options=[_o('warn', 'Nhắc khéo cả đoàn đeo túi ra trước, đứng sát nhau', '{name} kéo khóa túi. Người lạ lảng đi chỗ khác.', mood=1),
                  _o('shout', 'Quát người lạ trước đám đông', 'Người lạ bỏ đi, nhưng cả đoàn giật mình, có người sợ ra mặt.', mood=-4, minutes=5),
                  _o('none', 'Chắc không sao, làm ngơ', '{name} mất ví. Cả đoàn mất nửa tiếng ở đồn công an.', mood=-12, minutes=30, mistake=True)]),
    dict(id='dress', emoji='🧣', title='Trang phục ở cổng chùa', who=('nam', 'tom'), place='temple',
         text='Tới cổng chùa, {name} đang mặc quần đùi, áo ba lỗ. Người trông cổng nhìn theo.',
         options=[_o('scarf', 'Mượn khăn choàng ở cổng, giải thích nhẹ nhàng lý do', '{name} quấn khăn, vui vẻ vào chùa. Người trông cổng gật đầu cảm ơn.', mood=2),
                  _o('wait', 'Để {name} đứng chờ ngoài một mình', '{name} lủi thủi đứng ngoài cổng suốt mười lăm phút.', mood=-5),
                  _o('sneak', 'Kệ, cứ dẫn vào', 'Người trông cổng nhắc cả đoàn. {name} ngượng chín mặt.', mood=-6, mistake=True)]),
]
INCIDENT = {x['id']: x for x in INCIDENTS}
ROAD = [x['id'] for x in INCIDENTS if not x.get('gather') and not x.get('place')]

NOTES = {
    'lost_found': ('lost', '{name}', 'Mình mải chụp cổng đỏ nên lạc đoàn. Hướng dẫn viên tìm ra mình chỉ sau mười phút. Rất cảm ơn!'),
    'lost_alone': ('lost', '{name}', 'Mình bị lạc, chỉ nhận được một tin nhắn bảo tự bắt taxi. Mình đã rất sợ.'),
    'overpaid': ('coconut', '{name}', 'Chuyến đi vui, nhưng mình mua dừa giá gấp đôi mà hướng dẫn viên đứng ngay đó không nói gì.'),
    'parade': (None, 'Linh', 'Đang đi thì gặp múa lân, được giải thích tận tình. Tụi nhỏ nhắc mãi!'),
    'honest': (None, 'Linh', 'Hướng dẫn viên nói thẳng: không bắt ai mua gì. Hiếm có lắm, lần sau đoàn mình lại đặt.'),
    'commission': (None, 'Linh', 'Tiệm lưu niệm hướng dẫn viên dẫn vào bán đắt gấp rưỡi ngoài chợ. Hơi buồn.'),
    'elder_thanks': ('heat', '{name}', 'Già rồi, đi nắng hơi mệt. Cảm ơn cháu đã cho cả đoàn nghỉ chờ bác.'),
    'tom_safe': ('peanut', 'Tom', 'Guide checked every snack for peanuts. I felt safe the whole day. Cảm ơn!'),
}


def tier_for(day: int) -> int:
    return 1 if day <= 2 else 2 if day <= 5 else 3


def leg(a: str, b: str) -> int:
    pa = GATE if a == 'gate' else PLACE[a]
    pb = GATE if b == 'gate' else PLACE[b]
    return max(3, round(math.hypot(pa['x'] - pb['x'], pa['y'] - pb['y']) / 5))


def route_minutes(route) -> int:
    total, prev = 0, 'gate'
    for pid in route:
        total += leg(prev, pid) + PLACE[pid]['minutes']
        prev = pid
    return total


def route_fee(route) -> int:
    return sum(PLACE[p]['fee'] for p in route)


def closed_ids(trip: dict) -> list[str]:
    return [x['place'] for x in trip['closed']]


def happy(trip: dict, route) -> list[str]:
    tags = set()
    for p in route:
        tags.update(PLACE[p]['tags'])
    return [m for m in trip['members'] if MEMBER[m]['wish'] in tags]


def check_route(trip: dict, route) -> str | None:
    """Return None when the route is allowed, else the reason (Vietnamese)."""
    if not isinstance(route, list) or not all(isinstance(p, str) for p in route):
        return 'Lộ trình không hợp lệ.'
    if not MIN_STOPS <= len(route) <= MAX_STOPS or len(set(route)) != len(route):
        return f'Chọn {MIN_STOPS}–{MAX_STOPS} điểm khác nhau.'
    if not all(p in PLACE for p in route):
        return 'Có điểm không nằm trên bản đồ.'
    shut = [p for p in route if p in closed_ids(trip)]
    if shut:
        return PLACE[shut[0]]['name'] + ' hôm nay đóng cửa.'
    if not any('rest' in PLACE[p]['tags'] for p in route):
        return 'Cần một chỗ nghỉ chân: Hiên Trà hoặc Chùa Gió Lành.'
    cap = WEATHER[trip['weather']].get('outdoor_max')
    if cap is not None and sum(not PLACE[p]['indoor'] for p in route) > cap:
        return f'Nắng gắt: tối đa {cap} điểm ngoài trời.'
    if route_fee(route) > trip['fund']:
        return f'Vé vượt quỹ đoàn ({trip["fund"]} xu).'
    if route_minutes(route) > trip['limit']:
        return f'Lộ trình dài hơn {trip["limit"]} phút.'
    return None


def mood_base(trip: dict, route) -> int:
    ok = len(happy(trip, route))
    miss = len(trip['members']) - ok
    elders = sum(1 for m in trip['members'] if MEMBER[m].get('elder')) if 'hill' in route else 0
    return max(40, min(100, 85 + 3 * ok - 8 * miss - 5 * elders))


def _perfect(trip: dict) -> bool:
    """True when some allowed route makes every member happy."""
    wishes = {MEMBER[m]['wish'] for m in trip['members']}
    open_places = [p for p in PLACE_IDS if p not in closed_ids(trip)]
    for n in range(MIN_STOPS, MAX_STOPS + 1):
        for combo in itertools.combinations(open_places, n):
            tags = set()
            for p in combo:
                tags.update(PLACE[p]['tags'])
            if not wishes <= tags:
                continue
            first = list(combo)
            reason = check_route(trip, first)
            if reason is None:
                return True
            if route_fee(first) > trip['fund'] or 'phút' not in reason:
                continue
            if any(route_minutes(order) <= trip['limit'] for order in itertools.permutations(combo)):
                return True
    return False


def roll(day: int, slot: int, v1_weather: str) -> dict:
    """Fixed facts of one trip. Depends on (day, slot) and the day's weather."""
    return copy.deepcopy(_roll(day, slot, v1_weather))


@functools.lru_cache(maxsize=256)
def _roll(day: int, slot: int, v1_weather: str) -> dict:
    r = random.Random(f'mnl-tour-trip|{day}|{slot}')
    tier = tier_for(day)
    weather = dict(rain='rain', breeze='wind').get(v1_weather, 'heat' if tier >= 2 and r.random() < .5 else 'sun')
    closed = [dict(place=p, reason='Tạm đóng vì thời tiết') for p in WEATHER[weather]['closed']]
    if tier >= 2:
        # Never close the last place that offers some wish (rain + garden would leave no nature/photo stop).
        shut = set(WEATHER[weather]['closed'])
        p = r.choice([x for x in sorted(CLOSE_REASONS)
                      if {tag for q in PLACES if q['id'] not in shut | {x} for tag in q['tags']} == set(TAGS)])
        closed.append(dict(place=p, reason=CLOSE_REASONS[p]))
    size = {1: 4, 2: 6, 3: 7}[tier]
    fund = {1: 22, 2: 20, 3: 18}[tier]
    limit = {1: 130, 2: 120, 3: 115}[tier]
    trip = None
    for _ in range(40):
        members = ['linh'] + sorted(r.sample(OTHERS, size - 1), key=OTHERS.index)
        trip = dict(v=2, tier=tier, weather=weather, closed=closed, members=members, fund=fund, limit=limit)
        if _perfect(trip):
            break
    members = trip['members']
    late = None
    if tier >= 2:
        who = r.choice(members[1:])
        late = dict(id='late', who=who)
    pool = []
    for iid in ROAD:
        inc = INCIDENT[iid]
        if inc.get('tier', 1) > tier or (inc.get('weather') and weather not in inc['weather']):
            continue
        who = [m for m in inc['who'] if m in members]
        if inc['who'] and not who:
            continue
        pool.append((iid, r.choice(who) if who else None))
    r.shuffle(pool)
    count = {1: 1, 2: 2, 3: 3}[tier]
    stops = sorted(r.sample(range(MIN_STOPS), count))
    events = [dict(id=iid, stop=s, who=who) for (iid, who), s in zip(pool[:count], stops)]
    dress = next((m for m in INCIDENT['dress']['who'] if m in members), None)
    trip.update(late=late, events=events, dress=dress)
    return trip


FIXED = ('v', 'tier', 'weather', 'closed', 'members', 'fund', 'limit', 'late', 'events', 'dress')


def fresh(day: int, slot: int, v1_weather: str) -> dict:
    trip = roll(day, slot, v1_weather)
    trip.update(stage='plan', route=[], at=-1, told={}, calls={}, clock=0, spent=0, fund_left=trip['fund'], wallet=0,
                commission=0, base=0, stamps=[], notes=[], reward=0, tips=0)
    return trip


def slot_of(t: dict) -> int:
    return int(t['id'].rsplit('-', 1)[1])


def eligible(t: dict) -> bool:
    return (t.get('career') == 'tour_guide' and 'trip' not in t and t.get('stage') == 'plan' and not t.get('route')
            and not t.get('counted') and not t.get('stamps') and t.get('status') not in ('completed', 'referred', 'cancelled'))


def ensure(t: dict) -> dict:
    if 'trip' not in t:
        t['trip'] = fresh(t['day'], slot_of(t), t['weather'])
    return t['trip']


def _mood(t: dict, delta: int) -> None:
    t['patience'] = max(25, min(100, t.get('patience', 100) + delta))


def events_at(trip: dict, stop: int | None) -> list[dict]:
    """Situations due at a stop (None = gather point). Includes the temple dress check."""
    if stop is None:
        return [trip['late']] if trip['late'] else []
    out = [dict(id=e['id'], who=e['who']) for e in trip['events'] if e['stop'] == stop]
    if trip['dress'] and stop < len(trip['route']) and trip['route'][stop] == 'temple':
        out.append(dict(id='dress', who=trip['dress']))
    return out


def _fmt(text: str, who: str | None) -> str:
    return text.replace('{name}', MEMBER[who]['name'] if who else '')


def _cost(trip: dict) -> tuple[int, int]:
    """(fund_left, wallet) after tickets and situation costs."""
    total = route_fee(trip['route']) + trip['spent']
    return max(0, trip['fund'] - total), max(0, total - trip['fund'])


def handle(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    from . import engine as e
    need = e.need
    trip = ensure(t)
    stage = trip['stage']
    if name == 'plan':
        need(stage == 'plan', 'Đoàn đã chốt lộ trình rồi.')
        route = p.get('route')
        reason = check_route(trip, route)
        need(reason is None, reason or '')
        trip.update(route=list(route), base=mood_base(trip, route), stage='gather')
        left, wallet = _cost(trip)
        trip.update(fund_left=left, wallet=wallet)
        t['patience'] = trip['base']
        t['known'] = True
        t['status'] = 'understood'
        ok = len(happy(trip, route))
        return dict(message=f'Đã chốt {len(route)} điểm · {route_minutes(route)} phút · {ok}/{len(trip["members"])} người có điều mình mong.',
                    celebrate=ok == len(trip['members']))
    if name == 'call':
        where = None if stage == 'gather' else trip['at'] if stage == 'stop' else -1
        need(where != -1, 'Lúc này đoàn không có chuyện gì cần xử lý.')
        due = events_at(trip, where)
        ev = next((x for x in due if x['id'] == p.get('event')), None)
        need(ev, 'Chuyện này không xảy ra ở đây.')
        key = ev['id']
        need(key not in trip['calls'], 'Chuyện này đã xử lý xong.')
        inc = INCIDENT[key]
        opt = next((o for o in inc['options'] if o['id'] == p.get('option')), None)
        need(opt, 'Cách xử lý không hợp lệ.')
        before_left, before_wallet = _cost(trip)
        trip['spent'] += opt['cost']
        left, wallet = _cost(trip)
        extra = wallet - before_wallet
        if extra:
            need(c['money'] >= extra, f'Quỹ đoàn đã hết, cần {extra} xu tiền túi mà ví chưa đủ. Chọn cách khác nhé.')
            e.money(s, c, -extra, 'Bù quỹ đoàn: ' + inc['title'], t['id'], category='tour_cost')
        if opt['commission']:
            e.money(s, c, opt['commission'], 'Hoa hồng tiệm lưu niệm', t['id'], category='commission')
            trip['commission'] += opt['commission']
        trip.update(fund_left=left, wallet=wallet)
        trip['calls'][key] = opt['id']
        trip['clock'] += opt['minutes']
        _mood(t, opt['mood'])
        if opt['note'] and opt['note'] not in trip['notes']:
            trip['notes'].append(opt['note'])
        if opt['mistake']:
            t['mistakes'] += 1
        t['status'] = 'in_progress'
        e.metric(c, 'tour_moments')
        return dict(message=_fmt(opt['text'], ev['who']), correct=not opt['mistake'])
    if name == 'depart':
        need(stage == 'gather', 'Đoàn không ở điểm hẹn.')
        need(all(x['id'] in trip['calls'] for x in events_at(trip, None)), 'Đoàn chưa đủ người ở điểm hẹn.')
        trip.update(stage='stop', at=0)
        trip['clock'] += leg('gate', trip['route'][0]) + PLACE[trip['route'][0]]['minutes']
        left, wallet = _cost(trip)
        trip.update(fund_left=left, wallet=wallet)
        t['status'] = 'in_progress'
        return dict(message=f'Đủ {len(trip["members"])}/{len(trip["members"])} người. Đoàn tới {PLACE[trip["route"][0]]["name"]}!')
    if name == 'tell':
        need(stage == 'stop', 'Đến một điểm rồi mới kể chuyện.')
        key = str(trip['at'])
        need(key not in trip['told'], 'Đã kể chuyện ở điểm này rồi.')
        angle = p.get('angle')
        need(angle in ANGLE_IDS, 'Cách kể không hợp lệ.')
        place = PLACE[trip['route'][trip['at']]]
        fans = [m for m in trip['members'] if MEMBER[m]['angle'] == angle]
        fit = any(BEST_ANGLE[tag] == angle for tag in place['tags'])
        delta = 3 * len(fans) - (len(trip['members']) - len(fans)) + (2 if fit else 0)
        trip['told'][key] = angle
        _mood(t, delta)
        who = ', '.join(MEMBER[m]['name'] for m in fans[:3])
        tail = f' {who} nghe say sưa.' if fans else ' Cả đoàn nghe lơ đãng.'
        return dict(message='“' + place['lines'][angle] + '”' + tail, correct=delta > 0)
    if name == 'next':
        need(stage == 'stop', 'Đoàn chưa tới điểm nào.')
        need(str(trip['at']) in trip['told'], 'Kể chuyện ở điểm này trước đã.')
        need(all(x['id'] in trip['calls'] for x in events_at(trip, trip['at'])), 'Còn chuyện ở điểm này chưa xử lý.')
        here = trip['route'][trip['at']]
        trip['stamps'].append(here)
        from . import experiences as life
        life._sticker(c, 'place-' + here, PLACE[here]['name'], PLACE[here]['emoji'])
        if trip['at'] + 1 == len(trip['route']):
            trip['stage'] = 'ready'
            over = max(0, trip['clock'] - trip['limit'])
            if over:
                _mood(t, -2 * math.ceil(over / 5))
            return dict(message='Đủ người, đủ điểm. Về bến thôi!' + (f' Trễ {over} phút so với lịch.' if over else ''))
        trip['at'] += 1
        nxt = trip['route'][trip['at']]
        trip['clock'] += leg(here, nxt) + PLACE[nxt]['minutes']
        return dict(message=f'Đếm đủ {len(trip["members"])}/{len(trip["members"])} người. Đoàn tới {PLACE[nxt]["name"]}.')
    if name == 'complete':
        need(stage == 'ready', 'Chuyến đi chưa xong.')
        need(p.get('confirm') is True, 'Xác nhận khép chuyến.')
        return _finish(s, c, t, trip)
    raise e.GameError('Thao tác dẫn đoàn không hợp lệ.')


def tips_for(t: dict, trip: dict) -> int:
    mood = t.get('patience', 100)
    n = len(trip['members'])
    return n if mood >= 85 else n // 2 if mood >= 70 else 0


def saving(trip: dict) -> int:
    return min(10, trip['fund_left'] // 2)


# What the group says about a call that went wrong: (code, severity, text, note, safety).
# Safety-critical: a guest left alone or lost, an allergy ignored, a child sent off alone,
# an elder pushed on through heatstroke.
CALL_SLIPS = {
    ('late', 'leave'): ('left_behind', 3, 'Đoàn bỏ {name} lại ở điểm hẹn, {name} lạc đường phải gọi điện hoảng hốt.', 'bỏ khách lại điểm hẹn', True),
    ('lost', 'go'): ('lost_alone', 3, '{name} lạc đoàn mà chỉ nhận được tin nhắn bảo tự bắt taxi theo, một mình giữa phố lạ.', 'để khách lạc một mình', True),
    ('lost', 'split'): ('lost_split', 2, 'Lạc một người, cả đoàn tản ra tìm rồi lạc thêm người nữa, mất nửa tiếng mới gom đủ.', 'cho cả đoàn tản ra tìm người', False),
    ('peanut', 'guess'): ('allergy', 3, 'Tom dị ứng đậu phộng, hỏi kỹ mà vẫn được bảo không có, cắn một miếng là ngứa họng.', 'bỏ qua dị ứng của khách', True),
    ('toilet', 'alone'): ('kid_alone', 3, '{name} bị để tự chạy đi vệ sinh một mình giữa chỗ đông người.', 'để trẻ nhỏ đi một mình', True),
    ('heat', 'push'): ('heat_push', 3, '{name} choáng nắng mà vẫn bị giục đi tiếp, đến lúc ngồi thụp xuống giữa đường.', 'giục người say nắng đi tiếp', True),
    ('heat', 'alone'): ('heat_alone', 3, '{name} đang choáng nắng mà bị để ngồi một mình, cả đoàn đi trước.', 'để người say nắng ngồi một mình', True),
    ('parade', 'push'): ('crowd_push', 2, 'Chen qua đám rước lân cho kịp giờ, bé nhỏ trong đoàn suýt tuột tay mẹ.', 'chen đoàn qua chỗ đông', False),
    ('shower', 'run'): ('rain_run', 2, 'Đường mưa trơn mà hô cả đoàn chạy, Bà Sáu suýt ngã.', 'cho đoàn chạy dưới mưa trơn', False),
    ('wallet', 'none'): ('wallet', 2, '{name} bị móc mất ví giữa chỗ đông, cả đoàn mất nửa tiếng ở đồn công an.', 'không nhắc giữ đồ chỗ đông', False),
    ('commission', 'push'): ('commission', 2, 'Bị dẫn vào tiệm lưu niệm và giục mua, về mới biết giá gấp rưỡi ngoài chợ.', 'dẫn khách vào tiệm ăn hoa hồng', False),
    ('commission', 'quiet'): ('commission', 1, 'Hỏi tiệm lưu niệm có rẻ không thì hướng dẫn viên chỉ ậm ừ, về mới biết bị bán đắt.', 'im lặng khi khách bị bán đắt', False),
    ('coconut', 'pay'): ('overpaid', 1, '{name} mua dừa giá gấp đôi bảng niêm yết mà hướng dẫn viên đứng ngay đó không nói.', 'để khách bị hét giá', False),
    ('threat', 'give'): ('schedule', 1, 'Lịch cả đoàn bị đổi theo ý một người mà không ai được hỏi.', 'đổi lịch theo ý một người', False),
    ('flash', 'ignore'): ('flash', 1, 'Chỗ cấm đèn flash mà cứ để chụp, bảo vệ mời cả đoàn ra sớm.', 'làm ngơ biển cấm flash', False),
    ('dress', 'sneak'): ('dress', 1, 'Dẫn khách mặc quần đùi vào chùa, người trông cổng phải nhắc cả đoàn.', 'không nhắc trang phục ở chùa', False),
}


WISH_TEXT = dict(culture='nghe chuyện văn hóa, lịch sử', food='ăn món địa phương', nature='ra chỗ thiên nhiên', photo='chụp ảnh đẹp', shop='mua quà')


def _tell_delta(trip: dict, stop: int, angle: str) -> int:
    place = PLACE[trip['route'][stop]]
    fans = sum(1 for m in trip['members'] if MEMBER[m]['angle'] == angle)
    fit = any(BEST_ANGLE[tag] == angle for tag in place['tags'])
    return 3 * fans - (len(trip['members']) - fans) + (2 if fit else 0)


def judge(t: dict, trip: dict) -> None:
    """At the end of the trip: record what the group will hold against the guide."""
    from . import consequences as cq
    for key, opt in trip['calls'].items():
        row = CALL_SLIPS.get((key, opt))
        if row:
            code, sev, text, note, safety = row
            cq.slip(t, code, sev, _fmt(text, _who(trip, key)), note, safety)
    over = max(0, trip['clock'] - trip['limit'])
    if over:
        cq.slip(t, 'late_return', 1 if over <= 15 else 2, f'Hẹn về bến đúng giờ mà đoàn về trễ {over} phút, lỡ cả việc sau.',
                f'về trễ {over} phút')
    dull = sum(1 for k, a in trip['told'].items() if _tell_delta(trip, int(k), a) <= 0)
    if dull >= 2:
        whole = dull >= len(trip['route'])
        cq.slip(t, 'story', 2 if whole else 1,
                'Cả chuyến kể chuyện chẳng hợp ai, đoàn nghe lơ đãng từ đầu tới cuối.' if whole else 'Mấy điểm liền kể chuyện chẳng hợp ai, cả đoàn nghe lơ đãng.',
                'kể chuyện không hợp đoàn')
    missed = sorted((m for m in trip['members'] if m not in happy(trip, trip['route'])), key=lambda m: m == 'linh')
    if missed and (len(missed) >= 3 or _perfect(trip)):
        m = MEMBER[missed[0]]
        cq.slip(t, 'wishes', 2 if len(missed) >= 3 else 1,
                f'{"Mình" if m["id"] == "linh" else m["name"]} mong được {WISH_TEXT.get(m["wish"], "đi chỗ mình thích")} mà cả chuyến không ghé chỗ nào như vậy.',
                'lộ trình bỏ qua mong muốn của khách')
    if cq.slips(t) and t['mistakes'] == 0:
        t['mistakes'] = 1


def _finish(s: dict, c: dict, t: dict, trip: dict) -> dict:
    from . import engine as e
    from . import consequences as cq
    bonus = saving(trip)
    reward = BASE_FEE + bonus
    tips = tips_for(t, trip)
    judge(t, trip)
    pts = cq.points(t)
    if cq.safety(t) or pts >= 2:
        tips = 0
    elif pts:
        tips //= 2
    trip.update(reward=reward, tips=tips)
    e.metric(c, 'tour_trips')
    r = cq.react(s, c, t, reward, who='Trưởng đoàn Linh')
    e.task_done(s, c, t, r['pay'], f'Dẫn đoàn {len(trip["members"])} người qua {len(trip["stamps"])} điểm.')
    if tips:
        e.money(s, c, tips, 'Tip của đoàn', t['id'], category='tip')
    for key in trip['notes'][:2]:
        src, author, text = NOTES[key]
        who = next((x['who'] for x in trip['events'] if x['id'] == src), None) if src else None
        name = MEMBER[who]['name'] if who else author
        npc = CARRIER.get(who or 'linh', COORD_NPC)
        post = e.add_feed(s, c, npc, text.replace('{name}', name), t['id'] + ':' + key, kind='post')
        post['author'] = name if who else author
    msg = f'Khép chuyến: +{r["pay"]} xu' + (f' (tiết kiệm quỹ +{bonus})' if bonus and not r['cut'] else '') + (f' · tip {tips} xu' if tips else '') + '.'
    if r['message']:
        msg += ' ' + r['message']
    return dict(message=msg, celebrate=t['mistakes'] == 0)


# ------------------------------------------------------------------ projection
def _event_view(trip: dict, ev: dict) -> dict:
    inc = INCIDENT[ev['id']]
    out = dict(id=inc['id'], emoji=inc['emoji'], title=inc['title'], text=_fmt(inc['text'], ev['who']), who=ev['who'],
               options=[dict(id=o['id'], label=_fmt(o['label'], ev['who']), cost=o['cost']) for o in inc['options']])
    chosen = trip['calls'].get(ev['id'])
    if chosen:
        o = next(x for x in inc['options'] if x['id'] == chosen)
        out.update(chosen=chosen, outcome=_fmt(o['text'], ev['who']), mood=o['mood'], mistake=o['mistake'], minutes=o['minutes'])
    return out


def public(t: dict) -> dict:
    trip = copy.deepcopy(t['trip']) if 'trip' in t else fresh(t['day'], slot_of(t), t['weather'])
    stage = trip['stage']
    w = WEATHER[trip['weather']]
    closed = {x['place']: x['reason'] for x in trip['closed']}
    places = [dict(id=p['id'], name=p['name'], emoji=p['emoji'], x=p['x'], y=p['y'], minutes=p['minutes'], fee=p['fee'], indoor=p['indoor'],
                   tags=list(p['tags']), closed=closed.get(p['id'])) for p in PLACES]
    members = [dict(id=m, name=MEMBER[m]['name'], emoji=MEMBER[m]['emoji'], role=MEMBER[m]['role'], note=MEMBER[m]['note'],
                    wish=MEMBER[m]['wish'], angle=MEMBER[m]['angle'], elder=bool(MEMBER[m].get('elder')), kid=bool(MEMBER[m].get('kid'))) for m in trip['members']]
    view = dict(v=2, tier=trip['tier'], stage=stage, weather=dict(id=trip['weather'], emoji=w['emoji'], name=w['name'], text=w['text'], outdoor_max=w.get('outdoor_max')),
                gate=GATE, places=places, members=members, fund=trip['fund'], limit=trip['limit'], route=trip['route'], at=trip['at'],
                clock=trip['clock'], fund_left=trip['fund_left'], wallet=trip['wallet'], commission=trip['commission'], stamps=trip['stamps'],
                base=trip['base'], reward=trip['reward'] or None, tips=trip['tips'] or None, tags={k: dict(emoji=v[0], label=v[1]) for k, v in TAGS.items()},
                angles=ANGLES, legs={f'{a}>{b}': leg(a, b) for a in ['gate'] + PLACE_IDS for b in PLACE_IDS if a != b})
    if stage == 'gather':
        view['events'] = [_event_view(trip, ev) for ev in events_at(trip, None)]
    elif stage == 'stop':
        pid = trip['route'][trip['at']]
        place = PLACE[pid]
        told = trip['told'].get(str(trip['at']))
        view['here'] = dict(id=pid, name=place['name'], emoji=place['emoji'], tags=list(place['tags']), told=told, line=place['lines'][told] if told else None)
        view['events'] = [_event_view(trip, ev) for ev in events_at(trip, trip['at'])]
    else:
        view['events'] = []
    if stage == 'ready':
        view.update(estimate=BASE_FEE + saving(trip), saving=saving(trip), tips_estimate=tips_for(t, trip), over=max(0, trip['clock'] - trip['limit']))
    view['log'] = [_event_view(trip, dict(id=k, who=_who(trip, k))) for k in trip['calls']]
    return view


def _who(trip: dict, key: str) -> str | None:
    if key == 'late':
        return trip['late']['who'] if trip['late'] else None
    if key == 'dress':
        return trip['dress']
    return next((x['who'] for x in trip['events'] if x['id'] == key), None)


# ------------------------------------------------------------------ validation
def validate(t: dict) -> None:
    from .engine import need, integer
    trip = t['trip']
    need(isinstance(trip, dict), 'Chuyến đi không hợp lệ.')
    keys = set(FIXED) | {'stage', 'route', 'at', 'told', 'calls', 'clock', 'spent', 'fund_left', 'wallet', 'commission', 'base', 'stamps', 'notes', 'reward', 'tips'}
    need(set(trip) == keys, 'Dữ liệu chuyến đi thiếu hoặc lạ.')
    base = roll(t['day'], slot_of(t), t['weather'])
    for k in FIXED:
        need(trip[k] == base[k], 'Dữ kiện gốc của chuyến đi bị thay đổi: ' + k)
    need(trip['stage'] in STAGES, 'Bước dẫn đoàn không hợp lệ.')
    for k in ('clock', 'spent', 'fund_left', 'wallet', 'commission', 'base', 'reward', 'tips'):
        integer(trip[k], 0, 1000)
    integer(trip['at'], -1, MAX_STOPS - 1)
    route = trip['route']
    order = STAGES.index(trip['stage'])
    if order == 0:
        need(route == [] and trip['at'] == -1 and not trip['told'] and not trip['stamps'] and trip['clock'] == 0 and trip['base'] == 0, 'Chuyến đi chưa chốt lộ trình.')
        need(not trip['calls'] and trip['spent'] == 0 and trip['fund_left'] == trip['fund'] and trip['wallet'] == 0, 'Chuyến đi chưa bắt đầu.')
    else:
        need(check_route(trip, route) is None, 'Lộ trình không hợp lệ.')
        need(trip['base'] == mood_base(trip, route), 'Nhịp đoàn ban đầu không khớp.')
    if order == 1:
        need(trip['at'] == -1 and not trip['told'] and not trip['stamps'], 'Đoàn chưa xuất phát.')
    if order >= 2:
        need(0 <= trip['at'] < len(route), 'Điểm đang tới không có trên lộ trình.')
        need(all(k in trip['calls'] for k in (['late'] if trip['late'] else [])), 'Đoàn xuất phát khi chưa đủ người.')
    if order == 3:
        need(trip['at'] == len(route) - 1, 'Chuyến đi chưa tới điểm cuối.')
    done = trip['at'] + 1 if order == 3 else max(0, trip['at'])
    need(trip['stamps'] == route[:done], 'Dấu điểm đến không khớp.')
    need(isinstance(trip['told'], dict) and all(k.isdigit() and int(k) <= max(trip['at'], 0) and v in ANGLE_IDS for k, v in trip['told'].items()), 'Cách kể chuyện không hợp lệ.')
    need(all(str(i) in trip['told'] for i in range(done)), 'Có điểm chưa kể chuyện.')
    allowed = {}
    if trip['late']:
        allowed['late'] = None
    for ev in trip['events']:
        allowed[ev['id']] = ev['stop']
    if trip['dress'] and 'temple' in route:
        allowed['dress'] = route.index('temple')
    need(isinstance(trip['calls'], dict), 'Cách xử lý không hợp lệ.')
    reached = trip['at'] if order >= 2 else -1
    for k, v in trip['calls'].items():
        need(k in allowed and v in [o['id'] for o in INCIDENT[k]['options']], 'Cách xử lý không hợp lệ.')
        need(allowed[k] is None or allowed[k] <= reached, 'Chuyện này chưa xảy ra.')
    for k, stop in allowed.items():
        if stop is not None and stop < done:
            need(k in trip['calls'], 'Có chuyện chưa xử lý mà đoàn đã đi tiếp.')
    opts = {k: next(o for o in INCIDENT[k]['options'] if o['id'] == v) for k, v in trip['calls'].items()}
    need(trip['spent'] == sum(o['cost'] for o in opts.values()), 'Chi quỹ đoàn không khớp.')
    need(trip['commission'] == sum(o['commission'] for o in opts.values()), 'Hoa hồng không khớp.')
    if order >= 1:
        total = route_fee(route) + trip['spent']
        need(trip['fund_left'] == max(0, trip['fund'] - total) and trip['wallet'] == max(0, total - trip['fund']), 'Quỹ đoàn không khớp.')
    minutes = sum(o['minutes'] for o in opts.values())
    if order >= 2:
        walked, prev = 0, 'gate'
        for pid in route[:trip['at'] + 1]:
            walked += leg(prev, pid) + PLACE[pid]['minutes']
            prev = pid
        need(trip['clock'] == walked + minutes, 'Đồng hồ chuyến đi không khớp.')
    else:
        need(trip['clock'] == minutes, 'Đồng hồ chuyến đi không khớp.')
    need(isinstance(trip['notes'], list) and len(trip['notes']) <= 10 and all(n in NOTES for n in trip['notes']), 'Lời nhắn của đoàn không hợp lệ.')
    expect = []
    for o in opts.values():
        if o['note'] and o['note'] not in expect:
            expect.append(o['note'])
    need(trip['notes'] == expect, 'Lời nhắn của đoàn không khớp với chuyến đi.')
    need(trip['tips'] <= len(trip['members']), 'Tip của đoàn không hợp lệ.')
    if t.get('status') == 'completed':
        need(trip['stage'] == 'ready' and trip['reward'] == BASE_FEE + saving(trip), 'Tiền công chuyến đi không khớp.')
    else:
        need(trip['reward'] == 0 and trip['tips'] == 0, 'Chuyến đi chưa khép mà đã có tiền công.')


def known_request(t: dict) -> str:
    trip = t.get('trip') or roll(t['day'], slot_of(t), t['weather'])
    w = WEATHER[trip['weather']]
    return (f'Đoàn {len(trip["members"])} người, trời {w["name"].lower()}. Mỗi người mong một điều khác nhau. '
            f'Tối đa {trip["limit"]} phút, quỹ vé {trip["fund"]} xu, nhớ có chỗ nghỉ chân.')
