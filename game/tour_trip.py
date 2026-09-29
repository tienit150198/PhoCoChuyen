"""Tour guide v2 trip ("Chuyến đi"): a mixed group with their own wishes,
weather and closures, a route where the order changes walking time, a small
group fund, a story angle at every stop and on-the-road situations with
trade-offs (lost guest, overcharging stall, flat e-bus, festival, souvenir
commission, heat, allergy, ...).

Like game/teach_lesson.py, the v1 task keeps its fixed fields and the v2 layer
lives under t['trip']. Fixed facts are rolled from (day, slot) only so that
validation can regenerate them. v1 route fields stay empty on v2 trips.

Care loop (docs/superpowers/specs/2026-09-29-tour-guide-care-design.md): from
day 3 a seeded calendar brings multi-day groups whose slot-0 trip each day is a
leg with the same people. The career keeps c['life']['tour']: the group's
energy and who is sick, local partners' trust, place knowledge, the kit and the
booking page's reviews. Trips made before the care loop (no 'group' key) keep
the old roll and rules.
"""
from __future__ import annotations

import bisect
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


def away(trip: dict) -> str | None:
    """The sick guest who stays at the homestay today (a group leg only)."""
    care = trip.get('care')
    return care['sick'] if care and care.get('call') == 'rest' else None


def present(trip: dict) -> list[str]:
    gone = away(trip)
    return [m for m in trip['members'] if m != gone]


def happy(trip: dict, route) -> list[str]:
    tags = set()
    for p in route:
        tags.update(PLACE[p]['tags'])
    return [m for m in present(trip) if MEMBER[m]['wish'] in tags]


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
    miss = len(present(trip)) - ok
    elders = sum(1 for m in present(trip) if MEMBER[m].get('elder')) if 'hill' in route else 0
    return max(40, min(100, 85 + 3 * ok - 8 * miss - 5 * elders))


def _perfect(trip: dict) -> bool:
    """True when some allowed route makes every member happy."""
    wishes = {MEMBER[m]['wish'] for m in present(trip)}
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


def roll(day: int, slot: int, v1_weather: str, legacy: bool = False) -> dict:
    """Fixed facts of one trip. Depends on (day, slot) and the day's weather.
    `legacy` rolls a trip made before the care loop (no multi-day groups, no 'group' key)."""
    return copy.deepcopy(_roll(day, slot, v1_weather, legacy))


# ------------------------------------------------------------------ multi-day groups (calendar)
FIRST_GROUP = 3
GROUP_SIZE = {2: 5, 3: 6}
_STARTS, _LENS = [FIRST_GROUP], []


def group_of(day) -> dict | None:
    """The multi-day group whose leg is slot 0 of `day`: {start, days, leg}, or None on a free day."""
    if type(day) is not int or not FIRST_GROUP <= day <= 99999:
        return None
    while _STARTS[-1] <= day:
        d = _STARTS[-1]
        r = random.Random(f'mnl-tour-group|{d}')
        n = r.choice((2, 3, 3))
        _LENS.append(n)
        _STARTS.append(d + n + (1 if r.random() < .4 else 0))
    i = bisect.bisect_right(_STARTS, day) - 1
    start, n = _STARTS[i], _LENS[i]
    return dict(start=start, days=n, leg=day - start) if day < start + n else None


@functools.lru_cache(maxsize=256)
def crew(start: int) -> tuple:
    """The people of the group that arrives on `start` (the leader Linh first)."""
    r = random.Random(f'mnl-tour-crew|{start}')
    size = GROUP_SIZE[tier_for(start)]
    return tuple(['linh'] + sorted(r.sample(OTHERS, size - 1), key=OTHERS.index))


@functools.lru_cache(maxsize=256)
def _roll(day: int, slot: int, v1_weather: str, legacy: bool = False) -> dict:
    r = random.Random(f'mnl-tour-trip|{day}|{slot}')
    tier = tier_for(day)
    group = None if legacy or slot != 0 else group_of(day)
    weather = dict(rain='rain', breeze='wind').get(v1_weather, 'heat' if tier >= 2 and r.random() < .5 else 'sun')
    closed = [dict(place=p, reason='Tạm đóng vì thời tiết') for p in WEATHER[weather]['closed']]
    options = []
    if tier >= 2:
        # Never close the last place that offers some wish (rain + garden would leave no nature/photo stop).
        shut = set(WEATHER[weather]['closed'])
        options = [x for x in sorted(CLOSE_REASONS)
                   if {tag for q in PLACES if q['id'] not in shut | {x} for tag in q['tags']} == set(TAGS)]
        p = r.choice(options)
        closed.append(dict(place=p, reason=CLOSE_REASONS[p]))
    size = {1: 4, 2: 6, 3: 7}[tier]
    fund = {1: 22, 2: 20, 3: 18}[tier]
    limit = {1: 130, 2: 120, 3: 115}[tier]
    trip = None
    if group:
        # The same people every leg: move the day's closure until a route can still please everyone.
        trip = dict(v=2, tier=tier, weather=weather, closed=closed, members=list(crew(group['start'])), fund=fund, limit=limit)
        if options and not _perfect(trip):
            first = options.index(closed[-1]['place'])
            for q in options[first:] + options[:first]:
                trip['closed'] = closed[:-1] + [dict(place=q, reason=CLOSE_REASONS[q])]
                if _perfect(trip):
                    break
            else:
                trip['closed'] = closed[:-1]
        closed = trip['closed']
    else:
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
    if not legacy:
        trip['group'] = group
    return trip


FIXED = ('v', 'tier', 'weather', 'closed', 'members', 'fund', 'limit', 'late', 'events', 'dress', 'group')
STATE = ('stage', 'route', 'at', 'told', 'calls', 'clock', 'spent', 'fund_left', 'wallet', 'commission', 'base', 'stamps', 'notes', 'reward', 'tips')


def fresh(day: int, slot: int, v1_weather: str) -> dict:
    trip = roll(day, slot, v1_weather)
    trip.update(stage='plan', route=[], at=-1, told={}, calls={}, clock=0, spent=0, fund_left=trip['fund'], wallet=0,
                commission=0, base=0, stamps=[], notes=[], reward=0, tips=0,
                care=dict(sick=None, call=None) if trip['group'] else None)
    return trip


def slot_of(t: dict) -> int:
    return int(t['id'].rsplit('-', 1)[1])


def eligible(t: dict) -> bool:
    return (t.get('career') == 'tour_guide' and 'trip' not in t and t.get('stage') == 'plan' and not t.get('route')
            and not t.get('counted') and not t.get('stamps') and t.get('status') not in ('completed', 'referred', 'cancelled'))


def ensure(t: dict, c: dict | None = None) -> dict:
    """The trip of a task, made on first use. With the career, a group leg learns who woke up sick."""
    if 'trip' not in t:
        t['trip'] = fresh(t['day'], slot_of(t), t['weather'])
        if c is not None and t['trip']['group']:
            G = _group_for(c, t['trip']['group'])
            sick = G['sick'] if G and G['sick_day'] == t['day'] and G['sick'] in t['trip']['members'] else None
            t['trip']['care'] = dict(sick=sick, call=None)
    return t['trip']


def _mood(t: dict, delta: int) -> None:
    t['patience'] = max(25, min(100, t.get('patience', 100) + delta))


def events_at(trip: dict, stop: int | None) -> list[dict]:
    """Situations due at a stop (None = gather point). Includes the temple dress check."""
    gone = away(trip)
    if stop is None:
        return [trip['late']] if trip['late'] and trip['late']['who'] != gone else []
    out = [dict(id=e['id'], who=e['who']) for e in trip['events'] if e['stop'] == stop and (e['who'] is None or e['who'] != gone)]
    if trip['dress'] and trip['dress'] != gone and stop < len(trip['route']) and trip['route'][stop] == 'temple':
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
    trip = ensure(t, c)
    stage = trip['stage']
    care = trip.get('care')
    if name == 'care':
        need(stage == 'plan', 'Việc chăm người ốm quyết định trước khi chốt lộ trình.')
        need(care and care['sick'], 'Hôm nay trong đoàn không ai bị ốm.')
        need(care['call'] is None, 'Đã quyết định cho người ốm rồi.')
        opt = CARE.get(p.get('option'))
        need(opt, 'Cách chăm người ốm không hợp lệ.')
        who, x = care['sick'], state(c)
        extra = ''
        if opt['id'] == 'rest':
            if x['kit']['aid'] > 0:
                x['kit']['aid'] -= 1
            else:
                e.money(s, c, -3, 'Thuốc hạ sốt cho khách (túi sơ cứu hết)', t['id'], category='tour_cost')
                extra = ' Túi sơ cứu trống nên phải mua thuốc ở hiệu thuốc, 3 xu.'
        elif opt['cost']:
            e.money(s, c, -opt['cost'], 'Khám ở trạm y tế cho khách', t['id'], category='tour_cost')
        care['call'] = opt['id']
        if opt['mistake']:
            t['mistakes'] += 1
        G = _group_for(c, trip['group'])
        if G and G['sick'] == who:
            G['call'] = opt['id']
            if opt['id'] == 'push':
                G['pushes'] = min(9, G['pushes'] + 1)
            _diary(G, t['day'], opt['diary'].replace('{name}', MEMBER[who]['name']))
        t['status'] = 'understood'
        e.metric(c, 'tour_care')
        return dict(message=_fmt(opt['text'], who) + extra, correct=not opt['mistake'])
    if name == 'plan':
        need(stage == 'plan', 'Đoàn đã chốt lộ trình rồi.')
        need(not (care and care['sick'] and care['call'] is None),
             f'Sáng nay {MEMBER[care["sick"]]["name"] if care and care["sick"] else ""} bị ốm: quyết định cách chăm trước khi chốt lộ trình.')
        route = p.get('route')
        reason = check_route(trip, route)
        need(reason is None, reason or '')
        trip.update(route=list(route), base=mood_base(trip, route), stage='gather')
        left, wallet = _cost(trip)
        trip.update(fund_left=left, wallet=wallet)
        delta, notes = _plan_mods(c, trip, route)
        t['patience'] = max(25, min(100, trip['base'] + delta))
        t['known'] = True
        t['status'] = 'understood'
        ok, n = len(happy(trip, route)), len(present(trip))
        return dict(message=f'Đã chốt {len(route)} điểm · {route_minutes(route)} phút · {ok}/{n} người có điều mình mong.' + ''.join(' ' + x for x in notes),
                    celebrate=ok == n and not notes)
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
        tail = ''
        if (key, opt['id']) in AID_CALLS:
            kit = state(c)['kit']
            if kit['aid'] > 0:
                kit['aid'] -= 1
                tail = ' 🩹 Dầu gió và gói bù nước lấy ngay từ túi sơ cứu.'
            else:
                _mood(t, -3)
                tail = ' 🩹 Túi sơ cứu trống, phải chạy đi mua dầu gió, cả đoàn chờ thêm.'
        if opt['note'] and opt['note'] not in trip['notes']:
            trip['notes'].append(opt['note'])
        if opt['mistake']:
            t['mistakes'] += 1
        t['status'] = 'in_progress'
        e.metric(c, 'tour_moments')
        return dict(message=_fmt(opt['text'], ev['who']) + tail, correct=not opt['mistake'])
    if name == 'depart':
        need(stage == 'gather', 'Đoàn không ở điểm hẹn.')
        need(all(x['id'] in trip['calls'] for x in events_at(trip, None)), 'Đoàn chưa đủ người ở điểm hẹn.')
        trip.update(stage='stop', at=0)
        trip['clock'] += leg('gate', trip['route'][0]) + PLACE[trip['route'][0]]['minutes']
        left, wallet = _cost(trip)
        trip.update(fund_left=left, wallet=wallet)
        t['status'] = 'in_progress'
        delta, notes = _depart_mods(c, t, trip)
        _mood(t, delta)
        n = len(present(trip))
        head = f'Đủ {n}/{n} người' + (f' ({MEMBER[away(trip)]["name"]} nghỉ ở homestay)' if away(trip) else '')
        return dict(message=f'{head}. Đoàn tới {PLACE[trip["route"][0]]["name"]}!' + ''.join(' ' + x for x in notes))
    if name == 'tell':
        need(stage == 'stop', 'Đến một điểm rồi mới kể chuyện.')
        key = str(trip['at'])
        need(key not in trip['told'], 'Đã kể chuyện ở điểm này rồi.')
        angle = p.get('angle')
        need(angle in ANGLE_IDS, 'Cách kể không hợp lệ.')
        place = PLACE[trip['route'][trip['at']]]
        fans = [m for m in present(trip) if MEMBER[m]['angle'] == angle]
        delta = _tell_delta(trip, trip['at'], angle)
        trip['told'][key] = angle
        _mood(t, delta)
        who = ', '.join(MEMBER[m]['name'] for m in fans[:3])
        tail = f' {who} nghe say sưa.' if fans else ' Cả đoàn nghe lơ đãng.'
        return dict(message='“' + place['lines'][angle] + '”' + tail + _tell_care(c, t, place['id'], delta), correct=delta > 0)
    if name == 'next':
        need(stage == 'stop', 'Đoàn chưa tới điểm nào.')
        need(str(trip['at']) in trip['told'], 'Kể chuyện ở điểm này trước đã.')
        need(all(x['id'] in trip['calls'] for x in events_at(trip, trip['at'])), 'Còn chuyện ở điểm này chưa xử lý.')
        here = trip['route'][trip['at']]
        trip['stamps'].append(here)
        from . import experiences as life
        life._sticker(c, 'place-' + here, PLACE[here]['name'], PLACE[here]['emoji'])
        n = len(present(trip))
        if trip['at'] + 1 == len(trip['route']):
            trip['stage'] = 'ready'
            over = max(0, trip['clock'] - trip['limit'])
            if over:
                _mood(t, -2 * math.ceil(over / 5))
            return dict(message='Đủ người, đủ điểm. Về bến thôi!' + (f' Trễ {over} phút so với lịch.' if over else ''))
        trip['at'] += 1
        nxt = trip['route'][trip['at']]
        trip['clock'] += leg(here, nxt) + PLACE[nxt]['minutes']
        return dict(message=f'Đếm đủ {n}/{n} người. Đoàn tới {PLACE[nxt]["name"]}.')
    if name == 'complete':
        need(stage == 'ready', 'Chuyến đi chưa xong.')
        need(p.get('confirm') is True, 'Xác nhận khép chuyến.')
        return _finish(s, c, t, trip)
    raise e.GameError('Thao tác dẫn đoàn không hợp lệ.')


def tips_for(t: dict, trip: dict) -> int:
    mood = t.get('patience', 100)
    n = len(present(trip))
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
    people = present(trip)
    fans = sum(1 for m in people if MEMBER[m]['angle'] == angle)
    fit = any(BEST_ANGLE[tag] == angle for tag in place['tags'])
    return 3 * fans - (len(people) - fans) + (2 if fit else 0)


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
    care = trip.get('care')
    if care and care['sick'] and care['call'] == 'push':
        cq.slip(t, 'sick_push', 3, f'{MEMBER[care["sick"]]["name"]} ốm từ sáng mà vẫn bị giục đi cùng cả ngày, tới trưa thì lả đi.',
                'ép khách đang ốm đi tiếp', True)
    missed = sorted((m for m in present(trip) if m not in happy(trip, trip['route'])), key=lambda m: m == 'linh')
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
    e.task_done(s, c, t, r['pay'], f'Dẫn đoàn {len(present(trip))} người qua {len(trip["stamps"])} điểm.')
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
    tail = _after_trip(s, c, t, trip)
    if tail:
        msg += ' ' + tail
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
    care, gone = trip.get('care'), away(trip)
    members = [dict(id=m, name=MEMBER[m]['name'], emoji=MEMBER[m]['emoji'], role=MEMBER[m]['role'], note=MEMBER[m]['note'],
                    wish=MEMBER[m]['wish'], angle=MEMBER[m]['angle'], elder=bool(MEMBER[m].get('elder')), kid=bool(MEMBER[m].get('kid')),
                    sick=bool(care and care['sick'] == m), away=m == gone) for m in trip['members']]
    view = dict(v=2, tier=trip['tier'], stage=stage, weather=dict(id=trip['weather'], emoji=w['emoji'], name=w['name'], text=w['text'], outdoor_max=w.get('outdoor_max')),
                gate=GATE, places=places, members=members, fund=trip['fund'], limit=trip['limit'], route=trip['route'], at=trip['at'],
                clock=trip['clock'], fund_left=trip['fund_left'], wallet=trip['wallet'], commission=trip['commission'], stamps=trip['stamps'],
                base=trip['base'], reward=trip['reward'] or None, tips=trip['tips'] or None, tags={k: dict(emoji=v[0], label=v[1]) for k, v in TAGS.items()},
                angles=ANGLES, legs={f'{a}>{b}': leg(a, b) for a in ['gate'] + PLACE_IDS for b in PLACE_IDS if a != b},
                group=copy.deepcopy(trip.get('group')), care=_care_view(care), away=gone, present=len(present(trip)))
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
    legacy = 'group' not in trip  # made before the care loop: the old roll, no care
    fixed = [k for k in FIXED if not (legacy and k == 'group')]
    keys = set(fixed) | set(STATE) | (set() if legacy else {'care'})
    need(set(trip) == keys, 'Dữ liệu chuyến đi thiếu hoặc lạ.')
    base = roll(t['day'], slot_of(t), t['weather'], legacy)
    for k in fixed:
        need(trip[k] == base[k], 'Dữ kiện gốc của chuyến đi bị thay đổi: ' + k)
    need(trip['stage'] in STAGES, 'Bước dẫn đoàn không hợp lệ.')
    if not legacy:
        care = trip['care']
        if trip['group'] is None:
            need(care is None, 'Chuyến đi trong ngày không có việc chăm đoàn nhiều ngày.')
        else:
            need(isinstance(care, dict) and set(care) == {'sick', 'call'}, 'Việc chăm đoàn không hợp lệ.')
            need(care['sick'] is None or care['sick'] in trip['members'][1:], 'Người ốm không có trong đoàn.')
            need(care['call'] is None or (care['sick'] and care['call'] in CARE), 'Cách chăm người ốm không hợp lệ.')
            need(trip['stage'] == 'plan' or not care['sick'] or care['call'], 'Đoàn đã đi khi chưa lo cho người ốm.')
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
        need(all(k in trip['calls'] for k in (['late'] if trip['late'] and trip['late']['who'] != away(trip) else [])), 'Đoàn xuất phát khi chưa đủ người.')
    if order == 3:
        need(trip['at'] == len(route) - 1, 'Chuyến đi chưa tới điểm cuối.')
    done = trip['at'] + 1 if order == 3 else max(0, trip['at'])
    need(trip['stamps'] == route[:done], 'Dấu điểm đến không khớp.')
    need(isinstance(trip['told'], dict) and all(k.isdigit() and int(k) <= max(trip['at'], 0) and v in ANGLE_IDS for k, v in trip['told'].items()), 'Cách kể chuyện không hợp lệ.')
    need(all(str(i) in trip['told'] for i in range(done)), 'Có điểm chưa kể chuyện.')
    allowed, gone = {}, away(trip)
    if trip['late'] and trip['late']['who'] != gone:
        allowed['late'] = None
    for ev in trip['events']:
        if ev['who'] is None or ev['who'] != gone:
            allowed[ev['id']] = ev['stop']
    if trip['dress'] and trip['dress'] != gone and 'temple' in route:
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
    g = trip.get('group')
    head = f'Đoàn {g["days"]} ngày · ngày {g["leg"] + 1}/{g["days"]}: {len(trip["members"])} người, trời {w["name"].lower()}.' if g else \
        f'Đoàn {len(trip["members"])} người, trời {w["name"].lower()}.'
    return (f'{head} Mỗi người mong một điều khác nhau. '
            f'Tối đa {trip["limit"]} phút, quỹ vé {trip["fund"]} xu, nhớ có chỗ nghỉ chân.')


# ------------------------------------------------------------------ care loop: groups, partners, kit, knowledge
CARE_OPTIONS = [
    dict(id='rest', label='Để {name} nghỉ ở homestay, nhờ cô Hạnh trông, để lại thuốc hạ sốt', note='1 món trong túi sơ cứu',
         cost=0, mood=0, mistake=False,
         text='{name} ngủ một giấc dài ở homestay. Trưa cô Hạnh nhắn: “Hạ sốt rồi, đang ăn cháo.”',
         diary='{name} ốm, được nghỉ ở homestay.'),
    dict(id='clinic', label='Đưa {name} ra trạm y tế khám trước giờ đi, rồi cho đi nhẹ cùng đoàn', note='4 xu tiền khám',
         cost=4, mood=-3, mistake=False,
         text='Bác sĩ dặn {name} uống thuốc, đi chậm, uống nhiều nước. Cả đoàn chờ thêm một lúc.',
         diary='{name} ốm, được đưa đi khám rồi đi nhẹ cùng đoàn.'),
    dict(id='push', label='Động viên {name} cố đi cho trọn chuyến', note='',
         cost=0, mood=-6, mistake=True,
         text='{name} gật đầu cho cả đoàn vui, nhưng mặt tái đi. Người đang ốm cần được nghỉ.',
         diary='{name} ốm mà vẫn bị giục đi cùng đoàn.'),
]
CARE = {o['id']: o for o in CARE_OPTIONS}
AID_CALLS = {('heat', 'shade')}  # good calls that take something from the first-aid bag

PARTNERS = [
    dict(id='homestay', name='Homestay Nhà Mít', who='Cô Hạnh', emoji='🏡', ask='Báo cô Hạnh số khách, giờ về, ai ăn kiêng',
         perk='Đêm nghỉ hồi sức thêm 2 mỗi bậc'),
    dict(id='restaurant', name='Quán cơm Dì Năm', who='Dì Năm', emoji='🍚', ask='Đặt cơm trưa cho đoàn trước giờ đi',
         perk='Bàn giữ sẵn: nhịp đoàn +3, thêm 1 mỗi bậc'),
    dict(id='boat', name='Đò ông Bảy', who='Ông Bảy', emoji='🛶', ask='Đặt đò sớm ngắm sông cho đoàn',
         perk='Rẻ hơn 1 xu mỗi bậc · từ bậc Tin nhau nhận đặt trong ngày'),
]
PARTNER = {x['id']: x for x in PARTNERS}
LEVELS = ('Mới quen', 'Quen mặt', 'Bạn hàng', 'Tin nhau', 'Thân thiết', 'Như người nhà')

# Place notebook: a story few people know (from 2 good tellings) and a hidden spot (from 4).
KNOW = dict(
    museum=('Chiếc bình ba lá từng nứt một đường, người thợ vá bằng sơn ta trộn vàng, nhìn kỹ mới thấy chỉ vàng.',
            'ô cửa sau lò', 'chủ nhà mở ô cửa nhỏ cho đoàn nhìn vào lò gốm cũ còn ám khói.'),
    garden=('Cây trái tim do một đôi vợ chồng trồng ngày cưới, năm nào cũng có người buộc dải lụa đỏ lên cành.',
            'ghế đá sau bụi dâm bụt', 'ngồi đó nghe rõ tiếng chim, trẻ con thi nhau đếm.'),
    market=('Chiếc đèn lồng sao to nhất do cả chợ góp, mỗi nhà một nan tre.',
            'gác dán đèn lồng', 'các cô chú cho đoàn thử dán một nan lên chiếc đèn đang làm dở.'),
    river=('Trên biển cá cam có một con cá vẽ ngược, lỗi của một bạn nhỏ, cả phố giữ lại cho vui.',
           'bậc đá rêu dưới chân cầu', 'sát mặt nước, cả đoàn nhìn thấy đàn cá con bơi ngang.'),
    cafe=('Chú mèo trên quầy tên Trà Sen, tới quán vào một đêm mưa rồi ở luôn.',
          'gác xép nhìn ra bến', 'chủ quán mở riêng cho đoàn quen, gió sông thổi mát rượi.'),
    temple=('Quả chuông có một vết lõm từ trận bão năm xưa, nên tiếng chuông trầm hơn mọi chùa khác.',
            'giếng nước sau chùa', 'các sư cho khách vốc nước giếng rửa mặt, mát lạnh.'),
    craft=('Bài thơ ẩn trong nón do chính các cô thợ tự chép, mỗi chiếc một bài.',
           'bàn khâu của bà Út', 'bà Út chín mươi tuổi vẫn khâu nón, cho khách cầm thử cây kim.'),
    hill=('Trên đỉnh có hòn đá hình rùa, dân chài tin chạm vào thì chuyến biển bình an.',
          'mỏm đá rùa sau rặng thông', 'đứng đó nhìn thấy cả hai bờ sông.'),
    food=('Bà cụ bánh tráng giữ bí quyết: một chút mỡ hành quệt bằng lông gà.',
          'bếp than sau sạp', 'bà cho mỗi người tự nướng một chiếc bánh.'),
)
KIT_MAX = dict(mic=100, aid=6, flag=100)
MIC_USE, FLAG_WORN, FLAG_FIX, AID_PRICE, BOAT_MOOD, TIRED = 8, 30, 3, 1, 8, 50
KNOW_AT = (4, 10)  # good tellings that open the story few people know, then the hidden spot
GROUP_KEYS = {'start', 'days', 'members', 'energy', 'sick', 'sick_day', 'call', 'night', 'legs', 'moods', 'called', 'lunch',
              'boat', 'rode', 'diary', 'reviewed', 'pushes', 'cared'}
DONE = ('completed', 'referred', 'cancelled')


def fresh_care() -> dict:
    return dict(v=1, day=0, group=None, partners={p['id']: 0 for p in PARTNERS}, know={},
                kit=dict(mic=100, charging=False, aid=4, flag=100), reviews=[], featured=0)


def state(c: dict) -> dict:
    """The career's care record (life.tour), created for saves that predate it."""
    x = c['life'].get('tour')
    if not isinstance(x, dict):
        x = c['life']['tour'] = fresh_care()
    return x


def level(x: dict, pid: str) -> int:
    return min(5, x['partners'].get(pid, 0) // 2)


def _trust(x: dict, pid: str, delta: int) -> None:
    x['partners'][pid] = max(0, min(10, x['partners'][pid] + delta))


def boat_price(x: dict) -> int:
    return max(3, 8 - level(x, 'boat'))


def sick_text(m: str) -> str:
    who = MEMBER[m]
    return ('sốt nhẹ, người mệt lả' if who.get('kid') else 'đau lưng, chóng mặt' if who.get('elder')
            else 'đau bụng vì chưa quen đồ ăn' if who.get('foreign') else 'cảm nắng, sốt nhẹ')


def leg_weather(day: int) -> str:
    """The weather of `day`'s slot-0 trip (the group's leg), as the forecast shows it."""
    from . import extra_content as data
    return roll(day, 0, data.WEATHERS[(day - 1) % 3]['id'])['weather']


def _new_group(g: dict) -> dict:
    members = list(crew(g['start']))
    return dict(start=g['start'], days=g['days'], members=members,
                energy={m: 75 if MEMBER[m].get('elder') else 90 for m in members}, sick=None, sick_day=0, call=None,
                night=g['start'], legs=[], moods=[], called=[], lunch=[], boat=[], rode=[],
                diary=[f'Ngày {g["start"]}: đoàn {len(members)} người tới Bến Mây, ở {g["days"]} ngày.'],
                reviewed=False, pushes=0, cared=0)


def _group_for(c: dict, g: dict | None) -> dict | None:
    """The career's record of group `g`. A newer group replaces an older record; a leg of an older group is stale (None)."""
    if not g:
        return None
    x = state(c)
    G = x['group']
    if G and G['start'] == g['start']:
        return G
    if G and G['start'] > g['start']:
        return None
    x['group'] = _new_group(dict(start=g['start'], days=g['days']))
    return x['group']


def _diary(G: dict, day: int, text: str) -> None:
    G['diary'] = (G['diary'] + [f'Ngày {day}: {text}'])[-8:]


def hard(trip: dict, route) -> bool:
    """A tiring route: the hill, more than 100′ on foot, or more than one outdoor stop in the heat."""
    outdoor = sum(not PLACE[p]['indoor'] for p in route)
    return 'hill' in route or route_minutes(route) > 100 or (trip['weather'] == 'heat' and outdoor > 1)


def leg_cost(trip: dict, m: str) -> int:
    """Energy a leg takes from one guest."""
    route, who = trip['route'], MEMBER[m]
    mins = route_minutes(route)
    cost = mins // 5 + (6 if who.get('elder') else 0)
    if trip['weather'] == 'heat':
        cost += 5 * sum(not PLACE[p]['indoor'] for p in route)
    if 'hill' in route:
        cost += 16 if who.get('elder') else 6 if who.get('kid') else 4
    if who.get('kid') and mins > 100:
        cost += 4
    cost += max(0, trip['clock'] - trip['limit']) // 4
    if any('rest' in PLACE[p]['tags'] for p in route):
        cost -= 6
    return max(4, cost)


def _names(ids) -> str:
    return ', '.join(MEMBER[m]['name'] for m in ids)


def _plan_mods(c: dict, trip: dict, route) -> tuple[int, list]:
    care = trip.get('care')
    if not care or not trip.get('group'):
        return 0, []
    delta, notes = (CARE[care['call']]['mood'] if care['call'] else 0), []
    G = _group_for(c, trip['group'])
    if G and hard(trip, route):
        tired = [m for m in present(trip) if G['energy'].get(m, 100) < TIRED]
        if tired:
            delta -= 5 * len(tired)
            notes.append(f'😮‍💨 {_names(tired)} đang mệt mà lộ trình nặng: nhịp đoàn −{5 * len(tired)}.')
    return delta, notes


def _departed(c: dict, day: int) -> bool:
    t = next((x for x in c['tasks'] if x['id'] == f'tour_guide-{day:04d}-00'), None)
    return bool(t) and (t['status'] in DONE or (t.get('trip') or {}).get('stage') in ('stop', 'ready'))


def _depart_mods(c: dict, t: dict, trip: dict) -> tuple[int, list]:
    x = state(c)
    delta, notes = 0, []
    if x['kit']['flag'] < FLAG_WORN:
        delta -= 4
        notes.append('🚩 Cờ dẫn đoàn bạc màu, khách phải ngó nghiêng tìm: nhịp đoàn −4.')
    G = _group_for(c, trip['group']) if trip.get('group') and trip.get('care') is not None else None
    if G:
        d = t['day']
        if d in G['lunch']:
            k = 3 + level(x, 'restaurant')
            delta += k
            notes.append(f'🍚 Dì Năm giữ sẵn bàn cơm trưa: +{k}.')
            _trust(x, 'restaurant', 1)
        else:
            delta -= 4
            notes.append('🍚 Không đặt cơm trưa, đoàn đứng chờ bàn: −4.')
            _trust(x, 'restaurant', -1)
        if d in G['boat'] and d not in G['rode']:
            G['rode'].append(d)
            delta += BOAT_MOOD
            notes.append(f'🛶 Sáng sớm ông Bảy chèo đò đưa đoàn ngắm sông: +{BOAT_MOOD}.')
            _trust(x, 'boat', 1)
            _diary(G, d, 'đi đò sớm với ông Bảy.')
    return delta, notes


def _tell_care(c: dict, t: dict, pid: str, delta: int) -> str:
    """Loudspeaker battery and the place notebook, after a telling."""
    x = state(c)
    kit, tail = x['kit'], ''
    if kit['mic'] >= MIC_USE:
        kit['mic'] -= MIC_USE
    else:
        _mood(t, -4)
        tail += ' 🔋 Loa hết pin, phía sau đoàn nghe không rõ: −4.'
    if delta > 0:
        n = x['know'].get(pid, 0)
        secret, spot, line = KNOW[pid]
        if n >= KNOW_AT[1]:
            _mood(t, 4)
            tail += f' 🗝️ Góc ẩn: dẫn đoàn vào {spot}, {line} +4.'
        elif n >= KNOW_AT[0]:
            _mood(t, 2)
            tail += f' 📖 Chuyện ít ai biết: “{secret}” +2.'
        x['know'][pid] = min(50, n + 1)
        if n + 1 in KNOW_AT:
            tail += f' ✨ Sổ tay mở {"chuyện ít ai biết" if n + 1 == KNOW_AT[0] else "góc ẩn"} ở {PLACE[pid]["name"]}.'
    return tail


def _after_trip(s: dict, c: dict, t: dict, trip: dict) -> str:
    x = state(c)
    kit = x['kit']
    kit['flag'] = max(0, kit['flag'] - (18 if trip['weather'] in ('rain', 'wind') else 10))
    post = next((f for f in c['feed'] if f.get('source') == t['id'] and f.get('kind') == 'review' and f.get('stars')), None)
    if post:
        x['reviews'] = (x['reviews'] + [post['stars']])[-12:]
    tail = []
    if trip.get('group') and trip.get('care') is not None:
        tail += _leg_done(s, c, t, trip)
    if kit['flag'] < FLAG_WORN:
        tail.append('🚩 Cờ dẫn đoàn đã bạc, nhớ khâu lại.')
    return ' '.join(tail)


def _leg_done(s: dict, c: dict, t: dict, trip: dict) -> list:
    G = _group_for(c, trip['group'])
    if not G or t['day'] in G['legs']:
        return []
    who, call = trip['care']['sick'], trip['care']['call']
    for m in G['members']:
        if m == who and call == 'rest':
            G['energy'][m] = min(100, G['energy'][m] + 30)
            continue
        cost = leg_cost(trip, m)
        if m == who and call == 'clinic':
            cost //= 2
        elif m == who and call == 'push':
            cost = cost * 3 // 2
        G['energy'][m] = max(0, G['energy'][m] - cost)
    if who and call in ('rest', 'clinic'):
        G['cared'] = min(9, G['cared'] + 1)
    G['legs'].append(t['day'])
    G['moods'].append(t['patience'])
    tired = [m for m in G['members'] if G['energy'][m] < TIRED]
    _diary(G, t['day'], f'đi {len(trip["route"])} điểm, nhịp đoàn {t["patience"]}%.' + (f' {_names(tired)} mệt.' if tired else ''))
    out = []
    if t['day'] >= G['start'] + G['days'] - 1 or len(G['legs']) >= G['days']:
        out.append(_group_review(s, c, G))
    else:
        if tired:
            out.append(f'😮‍💨 {_names(tired)} đã mệt, mai nên đi nhẹ.')
        if c['day'] == t['day'] and c['day'] not in G['called']:
            out.append('🏡 Tối nay nhớ báo homestay.')
    return out


def _group_review(s: dict, c: dict, G: dict) -> str:
    from . import engine as e
    G['reviewed'] = True
    if not G['legs']:
        return ''
    avg = sum(G['moods']) / len(G['moods'])
    stars = 5 if avg >= 85 else 4 if avg >= 72 else 3 if avg >= 58 else 2
    good, bad = [], []
    skipped = G['days'] - len(G['legs'])
    if skipped:
        stars -= 1
        bad.append(f'{skipped} ngày đoàn chờ mà không ai dẫn đi')
    if G['pushes']:
        stars -= 1
        bad.append('có người ốm mà vẫn bị giục đi')
    elif G['cared']:
        good.append('người ốm được chăm chu đáo')
    nights = range(G['start'], G['start'] + G['days'] - 1)
    if any(n not in G['called'] for n in nights):
        stars -= 1
        bad.append('tối về homestay phải chờ dọn phòng')
    elif len(nights):
        good.append('tối nào về homestay cũng có phòng sẵn')
    if G['rode']:
        good.append('sáng đi đò ông Bảy ai cũng thích')
    if G['lunch'] and len(G['lunch']) >= len(G['legs']):
        good.append('bữa trưa có bàn sẵn')
    stars = max(1, min(5, stars))
    text = (f'Đoàn {len(G["members"])} người, {G["days"]} ngày cùng Mây Lang Thang. '
            + (('Thích nhất: ' + ', '.join(good) + '. ') if good else '')
            + (('Chưa vui: ' + ', '.join(bad) + '.') if bad else 'Lần sau cả nhà lại đặt!'))
    post = e.add_feed(s, c, CARRIER['linh'], text, f'tour-group-{G["start"]}', stars, 'review')
    post['author'] = 'Linh · trưởng đoàn'
    x = state(c)
    x['reviews'] = (x['reviews'] + [stars])[-12:]
    _diary(G, c['day'], f'đoàn chia tay, đánh giá {stars}★ trên trang đặt tour.')
    return f'👥 Đoàn {G["days"]} ngày chia tay: {stars}★ trên trang đặt tour.'


def _overnight(x: dict, G: dict, d: int) -> None:
    night = d - 1
    lvl = level(x, 'homestay')
    gain = 6 + 2 * lvl
    if G['start'] <= night <= G['start'] + G['days'] - 2:
        called = night in G['called']
        gain += 6 if called else -4
        _trust(x, 'homestay', 1 if called else -2)
        if not called:
            _diary(G, night, 'không báo trước, tối về homestay phải chờ dọn phòng.')
    for m in G['members']:
        G['energy'][m] = max(0, min(100, G['energy'][m] + gain))
    if G['sick'] and G['sick_day'] == night and G['call'] == 'push':
        G.update(sick_day=d, call=None)  # pushed while sick: still sick today
    else:
        # Someone cared for yesterday is on the mend today and is not rolled again.
        mended = G['sick'] if G['sick'] and G['sick_day'] == night and G['call'] in ('rest', 'clinic') else None
        G.update(sick=None, call=None)
        rng = random.Random(f'mnl-tour-sick|{G["start"]}|{d}')
        for m in sorted(G['members'][1:], key=lambda m: (G['energy'][m], OTHERS.index(m))):
            if m == mended:
                continue
            if G['energy'][m] >= 45:
                break
            if G['energy'][m] < 30 or rng.random() < .6:
                G.update(sick=m, sick_day=d)
                break
    if G['sick']:
        _diary(G, d, f'sáng dậy {MEMBER[G["sick"]]["name"]} {sick_text(G["sick"])}.')
    G['night'] = d


def _featured(s: dict, c: dict, x: dict) -> None:
    """Good reviews bring the next groups: a featured guide gets one extra booking in the morning."""
    from . import engine as e
    from .content import make_task
    rev = x['reviews']
    if len(rev) < 5 or sum(rev) / len(rev) < 4.5 or x['featured'] == c['day']:
        return
    slot = max((slot_of(t) for t in c['tasks'] if t['day'] == c['day']), default=-1) + 1
    if sum(t['status'] not in DONE for t in c['tasks']) >= 4 or slot >= 12:
        return
    c['tasks'].append(make_task('tour_guide', c['day'], slot, c['turn']))
    x['featured'] = c['day']
    e.log(s, c, 'day', '⭐ Trang đặt tour đề xuất bạn: thêm một đoàn đặt chuyến hôm nay.')


def on_start(s: dict, c: dict) -> None:
    """Morning: the group's night, who woke up sick, a featured booking, and today's leg made ready."""
    x = state(c)
    d = c['day']
    if x['day'] != d:
        x['day'] = d
        G, g = x['group'], group_of(d)
        if G and not G['reviewed'] and d > G['start'] + G['days'] - 1:
            _group_review(s, c, G)
        if g and (not G or G['start'] < g['start']):
            x['group'] = _new_group(g)
        elif g and G and G['start'] == g['start'] and G['night'] < d:
            _overnight(x, G, d)
        _featured(s, c, x)
    for t in c['tasks']:
        if t['career'] == 'tour_guide' and t['day'] == d and slot_of(t) == 0 and eligible(t) and group_of(d):
            ensure(t, c)


def on_close(s: dict, c: dict) -> None:
    x = state(c)
    d, kit, G = c['day'], x['kit'], x['group']
    if kit['charging']:
        kit.update(mic=100, charging=False)
    if G:
        if d in G['boat'] and d not in G['rode']:
            _trust(x, 'boat', -2)
            _diary(G, d, 'đặt đò mà đoàn không tới, ông Bảy chờ cả sáng.')
        if not G['reviewed'] and d >= G['start'] + G['days'] - 1:
            _group_review(s, c, G)


CARE_ACTIONS = ('partner', 'kit')


def care_action(s: dict, c: dict, name: str, p: dict) -> dict:
    """Career-level care: call a partner, look after the kit. No task needed."""
    from . import engine as e
    need = e.need
    need(c['open'], 'Mở ca trước khi lo việc cho đoàn nhé.')
    x = state(c)
    d = c['day']
    if name == 'kit':
        item = p.get('item')
        need(item in KIT_MAX, 'Không có món đồ nghề này.')
        kit = x['kit']
        if item == 'mic':
            need(not kit['charging'], 'Loa đang cắm sạc, sáng mai đầy pin.')
            need(kit['mic'] < KIT_MAX['mic'], 'Loa còn đầy pin.')
            kit['charging'] = True
            return dict(message='🔋 Đã cắm sạc loa. Sáng mai loa đầy pin.')
        if item == 'aid':
            missing = KIT_MAX['aid'] - kit['aid']
            need(missing > 0, 'Túi sơ cứu còn đủ đồ.')
            e.money(s, c, -missing * AID_PRICE, 'Bổ sung túi sơ cứu', f'tour-kit-{d}', category='tour_cost')
            kit['aid'] = KIT_MAX['aid']
            return dict(message=f'🩹 Đã bổ sung {missing} món: dầu gió, gói bù nước, băng dán, thuốc hạ sốt.')
        need(kit['flag'] < KIT_MAX['flag'], 'Cờ dẫn đoàn vẫn còn mới.')
        e.money(s, c, -FLAG_FIX, 'Khâu lại cờ dẫn đoàn', f'tour-kit-{d}', category='tour_cost')
        kit['flag'] = KIT_MAX['flag']
        return dict(message='🚩 Cờ dẫn đoàn đã khâu lại, màu tươi như mới.')
    if name == 'partner':
        pid = p.get('partner')
        need(pid in PARTNER, 'Không có bạn hàng này.')
        G, g = x['group'], group_of(d)
        need(G and g and g['start'] == G['start'], 'Hôm nay không có đoàn nhiều ngày.')
        if pid == 'homestay':
            need(g['leg'] < g['days'] - 1, 'Tối nay đoàn đã về, không ở lại homestay.')
            need(d not in G['called'], 'Đã báo homestay tối nay rồi.')
            G['called'].append(d)
            diet = ' Tom không ăn đậu phộng.' if 'tom' in G['members'] else ''
            return dict(message=f'🏡 Cô Hạnh: “Cô dọn sẵn {len(G["members"])} chỗ, nấu nồi cháo nóng chờ đoàn.”{diet}')
        if pid == 'restaurant':
            need(d not in G['lunch'], 'Đã đặt cơm trưa hôm nay rồi.')
            need(not _departed(c, d), 'Đoàn đã đi rồi, đặt cơm phải trước giờ xuất phát.')
            G['lunch'].append(d)
            extra = ' Dì dặn bếp không cho đậu phộng vào phần của Tom.' if 'tom' in G['members'] else ''
            return dict(message=f'🍚 Dì Năm giữ một bàn {len(G["members"])} người lúc mười một rưỡi.{extra}')
        when = p.get('when', 'tomorrow')
        need(when in ('today', 'tomorrow'), 'Chọn đặt đò cho hôm nay hay ngày mai.')
        day = d + 1 if when == 'tomorrow' else d
        if when == 'tomorrow':
            g2 = group_of(day)
            need(g2 and g2['start'] == G['start'], 'Ngày mai đoàn đã về rồi.')
        else:
            need(level(x, 'boat') >= 3, 'Ông Bảy chỉ nhận đặt trong ngày cho bạn hàng thân (bậc Tin nhau).')
            need(not _departed(c, d), 'Đoàn đã đi rồi.')
        need(day not in G['boat'], 'Đã đặt đò cho ngày này rồi.')
        w = leg_weather(day)
        need(w not in ('rain', 'wind'), f'Ông Bảy: “Trời {WEATHER[w]["name"].lower()}, đò không chạy đâu cháu.”')
        price = boat_price(x)
        e.money(s, c, -price, 'Đặt đò ông Bảy cho đoàn', f'tour-boat-{day}', category='tour_cost')
        G['boat'].append(day)
        return dict(message=f'🛶 Ông Bảy: “Sáu giờ {"sáng mai" if when == "tomorrow" else "này"} đò chờ ở bến nhé.” −{price} xu.')
    raise e.GameError('Thao tác chăm đoàn không hợp lệ.')


# ------------------------------------------------------------------ care projection
FORECAST_TIP = dict(
    sun='Trời đẹp: hợp đi đò sớm và lên đồi (người lớn tuổi vẫn ngại dốc).',
    heat='Nắng gắt: tối đa 2 điểm ngoài trời, đổ đầy túi sơ cứu, đặt đò đi sớm cho mát.',
    rain='Mưa: đò nghỉ, Lối Bờ Mây và Đồi đóng. Chọn điểm có mái che.',
    wind='Gió mạnh: đò nghỉ, Đồi Ngắm Mây đóng.',
)


def forecast(day: int) -> dict:
    w = leg_weather(day)
    W = WEATHER[w]
    return dict(day=day, id=w, emoji=W['emoji'], name=W['name'], tip=FORECAST_TIP[w], boat=w not in ('rain', 'wind'))


def energy_word(n: int) -> tuple[str, str]:
    return ('Khỏe', 'good') if n >= 70 else ('Hơi mệt', '') if n >= TIRED else ('Mệt', 'warn') if n >= 30 else ('Kiệt sức', 'bad')


def _care_view(care: dict | None) -> dict | None:
    if not care:
        return None
    out = dict(sick=care['sick'], call=care['call'])
    m = care['sick']
    if m:
        out.update(name=MEMBER[m]['name'], emoji=MEMBER[m]['emoji'], text=f'Sáng nay {MEMBER[m]["name"]} {sick_text(m)}.',
                   options=[dict(id=o['id'], label=_fmt(o['label'], m), note=o['note'], cost=o['cost']) for o in CARE_OPTIONS])
        if care['call']:
            o = CARE[care['call']]
            out.update(outcome=_fmt(o['text'], m), mistake=o['mistake'], mood=o['mood'])
    return out


def public_care(c: dict) -> dict:
    """What the guide knows: the group's condition, partners, notebook, kit, reviews and tomorrow."""
    x = copy.deepcopy((c.get('life') or {}).get('tour') or fresh_care())
    d = c['day']
    G, g = x['group'], group_of(d)
    group = None
    if G:
        active = bool(g and g['start'] == G['start'])
        today = G['sick_day'] == d
        g2 = group_of(d + 1)
        members = []
        for m in G['members']:
            word, tone = energy_word(G['energy'][m])
            members.append(dict(id=m, name=MEMBER[m]['name'], emoji=MEMBER[m]['emoji'], energy=G['energy'][m], word=word, tone=tone,
                                elder=bool(MEMBER[m].get('elder')), kid=bool(MEMBER[m].get('kid')),
                                sick=today and G['sick'] == m, away=today and G['sick'] == m and G['call'] == 'rest'))
        group = dict(start=G['start'], days=G['days'], leg=g['leg'] if active else None, active=active,
                     ended=d > G['start'] + G['days'] - 1, reviewed=G['reviewed'], members=members,
                     sick=G['sick'] if today else None, sick_text=sick_text(G['sick']) if today and G['sick'] else '',
                     call=G['call'] if today else None, night=active and g['leg'] < G['days'] - 1,
                     called=d in G['called'], lunch=d in G['lunch'], departed=_departed(c, d) if active else False,
                     boat_today=d in G['boat'], boat_tomorrow=d + 1 in G['boat'],
                     tomorrow=bool(g2 and g2['start'] == G['start']), legs=len(G['legs']), diary=list(G['diary']))
    upcoming = None
    if not (group and group['active']):
        k = next((k for k in range(d, d + 8) if (group_of(k) or {}).get('leg') == 0), None)
        if k:
            upcoming = dict(start=k, days=group_of(k)['days'])
    partners = []
    for p in PARTNERS:
        pts = x['partners'][p['id']]
        lv = min(5, pts // 2)
        partners.append(dict(id=p['id'], name=p['name'], who=p['who'], emoji=p['emoji'], ask=p['ask'], perk=p['perk'],
                             pts=pts, level=lv, label=LEVELS[lv]))
    know = []
    for p in PLACES:
        n = x['know'].get(p['id'], 0)
        lv = 2 if n >= KNOW_AT[1] else 1 if n >= KNOW_AT[0] else 0
        know.append(dict(id=p['id'], name=p['name'], emoji=p['emoji'], n=n, level=lv, need=KNOW_AT[lv] - n if lv < 2 else 0,
                         spot=KNOW[p['id']][1] if lv == 2 else None))
    rev = x['reviews']
    avg = round(sum(rev) / len(rev), 1) if rev else None
    return dict(group=group, upcoming=upcoming, partners=partners, know=know, know_at=list(KNOW_AT),
                kit=dict(x['kit'], aid_max=KIT_MAX['aid'], mic_use=MIC_USE, flag_worn=FLAG_WORN, flag_fix=FLAG_FIX, aid_price=AID_PRICE),
                rating=dict(stars=list(rev), avg=avg, n=len(rev), featured=x['featured'] == d, thin=len(rev) >= 5 and avg < 3.5, goal=4.5),
                forecast=forecast(d + 1), boat_price=boat_price(x), boat_same_day=level(x, 'boat') >= 3)


# ------------------------------------------------------------------ care validation and saves
def validate_care(c: dict) -> None:
    from .engine import need, integer, clean_text
    x = c['life'].get('tour')
    need(isinstance(x, dict) and set(x) == set(fresh_care()) and x.get('v') == 1, 'Dữ liệu chăm đoàn không hợp lệ.')
    integer(x['day'], 0, 10 ** 6)
    integer(x['featured'], 0, 10 ** 6)
    kit = x['kit']
    need(isinstance(kit, dict) and set(kit) == {'mic', 'charging', 'aid', 'flag'} and type(kit['charging']) is bool, 'Đồ nghề không hợp lệ.')
    for k, top in KIT_MAX.items():
        integer(kit[k], 0, top)
    need(isinstance(x['partners'], dict) and set(x['partners']) == set(PARTNER), 'Bạn hàng không hợp lệ.')
    for v in x['partners'].values():
        integer(v, 0, 10)
    need(isinstance(x['know'], dict) and set(x['know']) <= set(PLACE), 'Sổ tay điểm đến không hợp lệ.')
    for v in x['know'].values():
        integer(v, 0, 50)
    need(isinstance(x['reviews'], list) and len(x['reviews']) <= 12 and all(type(v) is int and 1 <= v <= 5 for v in x['reviews']),
         'Đánh giá trang đặt tour không hợp lệ.')
    G = x['group']
    if G is None:
        return
    need(isinstance(G, dict) and set(G) == GROUP_KEYS, 'Đoàn nhiều ngày không hợp lệ.')
    integer(G['start'], FIRST_GROUP, 99999)
    g = group_of(G['start'])
    need(g and g['leg'] == 0 and g['days'] == G['days'], 'Lịch đoàn nhiều ngày không khớp.')
    need(G['members'] == list(crew(G['start'])), 'Thành viên đoàn nhiều ngày bị thay đổi.')
    need(isinstance(G['energy'], dict) and set(G['energy']) == set(G['members']), 'Sức của đoàn không hợp lệ.')
    for v in G['energy'].values():
        integer(v, 0, 100)
    start, end = G['start'], G['start'] + G['days'] - 1
    integer(G['night'], start, end)
    integer(G['sick_day'], 0, end)
    need(G['sick'] is None or (G['sick'] in G['members'][1:] and start < G['sick_day']), 'Người ốm không hợp lệ.')
    need(G['call'] is None or (G['sick'] and G['call'] in CARE), 'Cách chăm người ốm không hợp lệ.')
    days = set(range(start, end + 1))
    for k, allowed in (('legs', days), ('lunch', days), ('boat', days), ('rode', days), ('called', days - {end})):
        need(isinstance(G[k], list) and len(G[k]) == len(set(G[k])) and all(type(v) is int and v in allowed for v in G[k]),
             'Lịch chăm đoàn không hợp lệ.')
    need(set(G['rode']) <= set(G['boat']), 'Chuyến đò không khớp lịch đặt.')
    need(isinstance(G['moods'], list) and len(G['moods']) == len(G['legs']), 'Nhịp đoàn từng ngày không khớp.')
    for v in G['moods']:
        integer(v, 25, 100)
    need(isinstance(G['diary'], list) and len(G['diary']) <= 8, 'Nhật ký đoàn quá dài.')
    for v in G['diary']:
        clean_text(v, 300)
    need(type(G['reviewed']) is bool, 'Đánh giá đoàn không hợp lệ.')
    integer(G['pushes'], 0, 9)
    integer(G['cared'], 0, 9)


def upgrade(c: dict) -> None:
    """Old saves: an empty care record. Old trips keep their legacy roll (see validate)."""
    life = c.get('life')
    if isinstance(life, dict) and not isinstance(life.get('tour'), dict):
        life['tour'] = fresh_care()
