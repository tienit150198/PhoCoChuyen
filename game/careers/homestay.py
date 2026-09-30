"""Homestay Mây Đà Lạt — a five-room mountain homestay (plugin career).

Real work of the job: a front desk and a small booking calendar.
* Take a booking by phone/chat: dates, who is coming (children under six who
  share a bed do not count toward room capacity), rooms that are free for every
  night (no overbooking), a 30% deposit — or honestly refer the guest to the
  neighbour homestay when nothing fits.
* Check a guest in: find the right reservation on the platform list (look-alike
  names and swapped digits exist), look at ID papers without ever photographing
  or writing numbers down, count who actually arrived, decide about extra
  people (surcharge with an extra mattress or politely refuse above capacity),
  give a clean room free for every night, light the gas heater on cold nights.
* Turn a room over: strip bed with the windows open → bathroom → fresh linen →
  towels/amenities/minibar → inspect for damage and forgotten things → close the
  windows and mark it clean. Too short airing leaves the Đà Lạt damp smell, too
  long makes the room cold (real seconds).
* Cook breakfast (eggs by real seconds: runny or well done), suggest places that
  fit the guests (ask about mobility, budget, transport, weather), and settle an
  itemised check-out bill: minibar beyond the free bottles, laundry, late
  check-out, damage. Guests refuse a bill that charges more than they used.

Booked guests arrive by themselves when the shift closes: their room must be
clean. Stays end in the morning and leave rooms dirty.
"""
from __future__ import annotations
import copy
from ..jsoncopy import tree_copy
import itertools
import math
from . import kit
from . import till
from .. import consequences as cq
from .. import archive as ar
from .. import compensation as cf

ID = 'homestay'
FREE_WATER = 2            # bottles of water per stay that are a gift of the house
EXTRA_GUEST = 8           # xu per extra person per night (extra mattress)
KID_FREE_AGE = 6          # children younger than this who share a bed are not counted
DEPOSIT_PCT = 30
AIR = dict(damp=15, cold=90)             # seconds with windows open during turnover
EGG = dict(raw=5, runny=11, well=18)     # <5 raw, 5–11 runny yolk, 11–18 well done, >18 burnt
HORIZON = 7
REPAIR_COST = 12
RENOVATION_COST = 25

ROOMS = [
    dict(id='thong', no=3, name='Đồi Thông', emoji='🌲', cap=2, beds='1 giường đôi', floor='Tầng trệt', stairs=False, unlock=1, view='rừng thông'),
    dict(id='suong', no=1, name='Sương Sớm', emoji='🌁', cap=2, beds='2 giường đơn', floor='Tầng trệt', stairs=False, unlock=1, view='vườn cải'),
    dict(id='gac', no=5, name='Gác Mái', emoji='🛖', cap=3, beds='1 đôi + 1 đơn', floor='Gác gỗ · cầu thang dốc', stairs=True, unlock=1, view='mái ngói'),
    dict(id='quy', no=2, name='Dã Quỳ', emoji='🌼', cap=4, beds='2 giường đôi', floor='Tầng trệt', stairs=False, unlock=1, view='đồi dã quỳ'),
    dict(id='ho', no=4, name='Ban Công Hồ', emoji='🌅', cap=2, beds='1 giường đôi · bồn tắm', floor='Lầu 1 · cầu thang', stairs=True, unlock=3, view='hồ'),
]
ROOM_INDEX = {r['id']: r for r in ROOMS}
ROOM_STATUS = ('clean', 'dirty', 'occupied', 'maintenance')

HK_STEPS = [
    dict(id='strip', name='Mở cửa sổ, tháo ga gối', emoji='🪟', use={}),
    dict(id='bath', name='Cọ phòng tắm', emoji='🚿', use={}),
    dict(id='bed', name='Trải ga gối mới', emoji='🛏️', use={'linen': 1}),
    dict(id='amenity', name='Khăn, bộ tắm, nước, minibar', emoji='🧴', use={'towel': 2, 'soap_kit': 1, 'water': 2, 'coffee': 2}),
    dict(id='inspect', name='Kiểm hư hỏng & đồ bỏ quên', emoji='🔍', use={}),
    dict(id='ready', name='Đóng cửa sổ, báo phòng sạch', emoji='✅', use={}),
]
HK_INDEX = {x['id']: x for x in HK_STEPS}
MIDDLE = ('bath', 'bed', 'amenity', 'inspect')
SLIP_TEXT = {
    ('bed', 'bath'): 'Trải ga trước khi cọ phòng tắm: nước bẩn bắn lên ga mới.',
    ('amenity', 'bath'): 'Đặt bộ tắm trước khi cọ: xà phòng bị ướt, phải bỏ một bộ.',
    ('amenity', 'bed'): 'Xếp khăn lên giường chưa trải ga, phải xếp lại.',
    ('inspect', 'bath'): 'Kiểm phòng khi phòng tắm còn bẩn dễ sót chỗ hỏng.',
    ('inspect', 'bed'): 'Kiểm phòng khi giường còn bừa dễ sót đồ khách quên.',
    ('inspect', 'amenity'): 'Kiểm phòng trước khi bổ sung đồ nên phải kiểm lại minibar.',
}
FOUND_ITEMS = ['Sạc điện thoại', 'Kẹp tóc hình mây', 'Khăn quàng len đỏ', 'Tai nghe không dây', 'Sổ tay vẽ ký họa']
ISSUES = ['Vòi sen rỉ nước', 'Bóng đèn đầu giường chập chờn', 'Ổ khóa cửa bị kẹt', 'Máy sưởi báo lỗi đánh lửa']

BILL_LINES = [
    dict(id='water', name='Nước suối (ngoài 2 chai tặng)', emoji='💧', price=3, unit='chai'),
    dict(id='noodles', name='Mì ly minibar', emoji='🍜', price=6, unit='ly'),
    dict(id='snack', name='Bánh quy bơ minibar', emoji='🍪', price=5, unit='gói'),
    dict(id='laundry', name='Giặt ủi', emoji='👕', price=8, unit='túi'),
    dict(id='late', name='Trả phòng muộn (tới 14h)', emoji='🕑', price=10, unit='lần'),
    dict(id='damage', name='Bồi thường đồ hư hỏng', emoji='🏺', price=12, unit='món'),
]
BILL_INDEX = {x['id']: x for x in BILL_LINES}

PLACES = [
    dict(id='vuon_dau', name='Vườn dâu Cô Mận', emoji='🍓', tags=['kids', 'flat', 'outdoor', 'near'], blurb='Tự hái dâu, lối đi bằng phẳng, cách 1 km.'),
    dict(id='bao_tang', name='Bảo tàng Gỗ Thông', emoji='🏛️', tags=['indoor', 'rain', 'flat', 'kids', 'elder', 'quiet', 'near'], blurb='Trong nhà, có thang máy và ghế nghỉ.'),
    dict(id='cho_dem', name='Chợ đêm Phố Núi', emoji='🏮', tags=['night', 'food', 'free', 'flat', 'crowd', 'near'], blurb='Đồ nướng, len, đông vui từ 18h.'),
    dict(id='thac', name='Thác Mây Rơi', emoji='💦', tags=['stairs', 'outdoor', 'far', 'photo', 'adventure', 'pricey'], blurb='300 bậc đá xuống chân thác, vé khá đắt.'),
    dict(id='doi_che', name='Đồi chè Sương Mai', emoji='🍵', tags=['outdoor', 'photo', 'far', 'slope', 'free', 'quiet'], blurb='Dốc thoai thoải, đẹp lúc sương sớm, 18 km.'),
    dict(id='ho_xuan', name='Hồ Xuân Nhỏ', emoji='🦢', tags=['flat', 'free', 'elder', 'kids', 'outdoor', 'near', 'quiet'], blurb='Đi dạo bờ hồ, ghế đá, xe đạp đôi.'),
    dict(id='trail', name='Đường mòn Rừng Thông Đỏ', emoji='🥾', tags=['adventure', 'slope', 'free', 'outdoor', 'far'], blurb='Trekking 3 tiếng, dốc và trơn khi mưa.'),
    dict(id='cafe_may', name='Cà phê Mây Lưng Đồi', emoji='☕', tags=['indoor', 'rain', 'photo', 'near', 'night', 'stairs'], blurb='Ban công ngắm mây, 40 bậc thang, mở tới 22h.'),
    dict(id='lang_hoa', name='Làng hoa Cẩm Tú', emoji='🌷', tags=['photo', 'flat', 'outdoor', 'kids'], blurb='Nhà kính hoa, lối đi bằng, chụp ảnh đẹp.'),
    dict(id='suoi_nong', name='Nhà tắm khoáng Suối Ấm', emoji='♨️', tags=['indoor', 'rain', 'elder', 'quiet', 'pricey', 'far'], blurb='Ngâm khoáng ấm, yên tĩnh, vé cao, 15 km.'),
]
PLACE_INDEX = {x['id']: x for x in PLACES}
TAG_NAMES = dict(kids='hợp trẻ nhỏ', elder='hợp người lớn tuổi', flat='đường bằng', stairs='nhiều bậc thang', slope='dốc',
                 indoor='trong nhà', outdoor='ngoài trời', rain='đi được khi mưa', night='buổi tối', food='ăn uống', free='miễn phí',
                 pricey='vé đắt', far='xa', near='gần', photo='chụp ảnh đẹp', adventure='khám phá', crowd='đông người', quiet='yên tĩnh')
PROBES = [
    dict(id='who', label='Đi cùng những ai?', emoji='👨‍👩‍👧'),
    dict(id='move', label='Có ai đi lại khó khăn không?', emoji='🦵'),
    dict(id='budget', label='Ngân sách hôm nay?', emoji='👛'),
    dict(id='ride', label='Mình di chuyển bằng gì?', emoji='🛵'),
    dict(id='weather', label='Xem dự báo thời tiết', emoji='🌦️'),
]
PROBE_IDS = [x['id'] for x in PROBES]

ITEMS = [
    dict(id='linen', name='Bộ ga gối sạch', emoji='🛏️', group='buồng phòng', unit='bộ', cost=4, start=10),
    dict(id='towel', name='Khăn tắm', emoji='🧺', group='buồng phòng', unit='chiếc', cost=2, start=20),
    dict(id='soap_kit', name='Bộ dầu gội + xà phòng', emoji='🧴', group='buồng phòng', unit='bộ', cost=1, start=16),
    dict(id='water', name='Nước suối chai', emoji='💧', group='minibar', unit='chai', cost=1, start=24),
    dict(id='coffee', name='Gói cà phê hòa tan', emoji='☕', group='minibar', unit='gói', cost=1, start=24),
    dict(id='noodles', name='Mì ly minibar', emoji='🍜', group='minibar', unit='ly', cost=2, life=30, start=10),
    dict(id='snack', name='Bánh quy bơ', emoji='🍪', group='minibar', unit='gói', cost=2, life=20, start=8),
    dict(id='bread', name='Bánh mì', emoji='🥖', group='bữa sáng', unit='ổ', cost=1, life=2, start=10),
    dict(id='egg', name='Trứng gà', emoji='🥚', group='bữa sáng', unit='quả', cost=1, life=6, start=12),
    dict(id='milk', name='Sữa tươi hộp', emoji='🥛', group='bữa sáng', unit='hộp', cost=2, life=3, start=8),
    dict(id='heater_gas', name='Bình gas máy sưởi', emoji='🔥', group='sưởi ấm', unit='bình', cost=6, start=4),
]
ITEM_INDEX = {x['id']: x for x in ITEMS}

PEOPLE = [
    ('Chị Thu Hà', 'Khách đặt qua app', 'Đi cùng chồng, mê phòng có view, hỏi rất kỹ.', 'picky'),
    ('Anh Bảo', 'Phượt thủ', 'Đi một mình, ví mỏng, thích đường mòn và bánh mì.', 'genz'),
    ('Cô Diệp', 'Khách lớn tuổi', 'Đi cùng chú ngoài 70, sợ lạnh, dậy từ 5 giờ.', 'warm'),
    ('Anh Tuấn', 'Khách gia đình', 'Hai bé nhỏ, hay quên đồ, thích dạy người khác cách làm.', 'bossy'),
    ('Mai Chi', 'Sinh viên', 'Đi theo nhóm bạn, săn ảnh, hay thức khuya.', 'genz'),
    ('Ông Lâm', 'Hàng xóm kiêm khách quen', 'Hay qua uống trà, nói thẳng, ghét ồn.', 'sour'),
    ('Anh Kiệt', 'Khách công tác', 'Ít nói, cần hóa đơn rõ ràng, đi sớm về khuya.', 'quiet'),
    # v0.5 — the channel manager, the ward, the neighbours and a few more guests
    ('Chị Hạnh', 'Quản lý kênh Mây Travel', 'Gọi điện nhanh như gió, câu cửa miệng: “đồng bộ lịch nha em”.', 'bossy'),
    ('Khách đặt qua app', 'Khách OTA', 'Chỉ biết homestay qua ảnh và điểm đánh giá trên app.', 'picky'),
    ('Chị Yến', 'Khách cũ', 'Ở phòng Sương Sớm tuần trước, nói chuyện nhỏ nhẹ.', 'warm'),
    ('Anh Khoa', 'Khách đặt qua điện thoại', 'Nói nhanh, hay mặc cả, làm việc từ xa.', 'genz'),
    ('Chú Thành', 'Tổ kiểm tra lưu trú & PCCC phường', 'Làm việc theo biên bản, không nhận quà.', 'sour'),
    ('Cô Ba', 'Chủ Nhà Gỗ Cô Ba', 'Hàng xóm, hay nhận giúp khách khi nhà Mây kín phòng.', 'warm'),
    ('Thảo Vi', 'Blogger du lịch', 'Hơn 200 nghìn người theo dõi, thích “trải nghiệm miễn phí”.', 'genz'),
    ('Cô Tư', 'Khách lớn tuổi', 'Đi cùng con gái, sợ cầu thang, thích trà gừng.', 'warm'),
]
# Name written on platform reservations and a look-alike name (for the check-in list).
BOOKING_NAMES = [('Nguyễn Thu Hà', 'Nguyễn Thị Hà'), ('Lê Quốc Bảo', 'Lê Quốc Bửu'), ('Phạm Ngọc Diệp', 'Phạm Ngọc Điệp'),
                 ('Trần Minh Tuấn', 'Trần Minh Tuân'), ('Đỗ Mai Chi', 'Đỗ Mai Thi'), ('Hồ Văn Lâm', 'Hồ Văn Lam'), ('Vũ Tuấn Kiệt', 'Vũ Tuấn Kiên'),
                 ('Đinh Mỹ Hạnh', 'Đinh Mỹ Hạ'), ('Lý Gia Hân', 'Lý Gia Hằng'), ('Trần Thị Yến', 'Trần Thị Yên'), ('Nguyễn Đăng Khoa', 'Nguyễn Đăng Khôi'),
                 ('Bùi Văn Thành', 'Bùi Văn Thanh'), ('Lương Thị Ba', 'Lương Thị Bá'), ('Hồ Thảo Vi', 'Hồ Thảo Vy'), ('Quách Thị Tư', 'Quách Thị Từ')]

JOB_ORDER = ('checkin', 'breakfast', 'checkout', 'booking', 'recommend')
JOB_NAMES = dict(checkin='Nhận phòng', breakfast='Bữa sáng', checkout='Trả phòng', booking='Đặt phòng', recommend='Gợi ý đi chơi', claim='Đồ thất lạc')

# (npc, platform, code, booked adults, booked kids, arrived adults, arrived kids, nights, room size, rate, paid %, cold, id, note, min_day)
CHECKINS = [
    (0, 'Mây Travel', 'MT-4821', 2, (), 2, (), 2, 2, 30, 0, False, 'ok', 'Cho chị phòng yên tĩnh nhé, chị ngủ tỉnh lắm.', 1),
    (3, 'Đi Đâu', 'DD-1507', 2, (4, 8), 2, (4, 8), 1, 4, 48, 30, True, 'ok', 'Bé út ngủ chung với bố mẹ được không em?', 1),
    (4, 'Mây Travel', 'MT-7730', 2, (), 3, (), 1, 2, 30, 0, False, 'ok', 'Tụi em đặt 2 người… à mà có thêm một bạn tới sau nha!', 1),
    (2, 'Gọi điện', 'GD-0312', 2, (), 2, (), 3, 2, 30, 30, True, 'app', 'Cô chú già rồi, sợ lạnh lắm con ơi.', 1),
    (6, 'Đi Đâu', 'DD-9044', 1, (), 1, (), 1, 2, 28, 30, False, 'ok', 'Cho tôi nhận phòng nhanh, 8 giờ sáng mai tôi họp.', 1),
    (1, 'Mây Travel', 'MT-3368', 1, (), 1, (), 2, 2, 28, 0, True, 'ok', 'Em đi phượt một mình, có chỗ dựng xe máy không anh?', 2),
    (3, 'Đi Đâu', 'DD-2210', 2, (3,), 2, (3, 7), 2, 3, 36, 30, True, 'ok', 'À quên, hôm đặt anh chỉ ghi bé út, bé lớn đi cùng nữa.', 2),
    (5, 'Gọi điện', 'GD-0808', 2, (), 2, (), 1, 2, 30, 30, True, 'ok', 'Con gái tôi từ Sài Gòn lên, cho hai mẹ con phòng ấm nhất.', 3),
]
# (npc, nights, water, noodles, snack, coffee, damage, lost, laundry, late, claim, min_day)
CHECKOUTS = [
    (6, 1, 3, 1, 0, 2, None, 'Sạc laptop', 0, False, 'Tôi trả phòng. Có dùng minibar chút đỉnh, em tính giúp.', 1),
    (0, 2, 2, 0, 1, 4, None, None, 1, True, 'Chị có gửi giặt một túi hôm qua. Cho chị trả phòng lúc 13 giờ nha.', 1),
    (3, 2, 4, 2, 2, 2, 'Cốc sứ bị mẻ miệng', 'Gấu bông hình thỏ', 0, False, 'Mấy đứa nhỏ quậy quá, có gì em cứ tính đủ nhé.', 1),
    (4, 1, 5, 1, 1, 3, None, None, 0, True, 'Tụi em dậy trễ, cho trả phòng 13 giờ 30 được không ạ?', 2),
    (2, 3, 1, 0, 0, 2, None, 'Kính lão', 2, False, 'Cô chú về đây, cảm ơn con mấy hôm nay nhé. Có gửi giặt hai túi.', 1),
    (1, 2, 2, 2, 0, 2, None, None, 1, False, 'Em trả phòng nha, hôm qua gửi giặt một túi đồ phượt.', 2),
]
# (npc, people, runny, well, bread, milk, coffee, allergy, where, note, min_day)
BREAKFASTS = [
    (2, 2, 0, 2, 2, 0, 2, None, 'Mang lên phòng', 'Trứng chín kỹ giúp cô, chú không ăn lòng đào.', 1),
    (3, 4, 1, 1, 4, 2, 2, None, 'Bàn sân vườn', 'Hai bé uống sữa, bố mẹ cà phê. Trứng: một lòng đào, một chín kỹ.', 1),
    (4, 2, 2, 0, 2, 0, 2, None, 'Bàn sân vườn', 'Lòng đào hết nha anh ơi, để tụi em chụp hình!', 1),
    (0, 2, 1, 0, 2, 1, 1, 'egg', 'Mang lên phòng', 'Chồng chị dị ứng trứng: phần anh ấy tuyệt đối không có trứng.', 1),
    (6, 1, 0, 1, 1, 0, 1, None, 'Mang lên phòng', 'Tôi ăn nhanh, 7 giờ phải đi.', 1),
    (1, 1, 1, 0, 2, 0, 1, None, 'Bàn sân vườn', 'Cho em hai ổ bánh mì, đi phượt đói lắm.', 2),
]
# (npc, channel, offset days, nights, adults, kids, stairs ok, preferred rooms, note, min_day)
BOOKINGS = [
    (0, 'Mây Chat', 1, 2, 2, (), True, ('thong', 'ho'), 'Cho chị phòng nhìn ra rừng thông hoặc hồ nha.', 1),
    (3, 'Gọi điện', 2, 2, 4, (5, 9), True, (), 'Nhà anh 4 người lớn, thêm 2 bé 5 tuổi và 9 tuổi.', 1),
    (1, 'Mây Chat', 1, 1, 1, (), True, ('suong',), 'Một đêm thôi anh, phòng nào rẻ nhất cũng được.', 1),
    (2, 'Gọi điện', 1, 3, 2, (), False, (), 'Cô chú lớn tuổi, đừng xếp phòng phải leo cầu thang nhé.', 1),
    (4, 'Mây Chat', 3, 1, 5, (), True, (), 'Nhóm tụi em 5 đứa, ở chung một phòng cho vui!', 2),
    (6, 'Email', 2, 1, 1, (), True, (), 'Đặt giúp tôi một phòng, cần hóa đơn công ty.', 1),
    (5, 'Gọi điện', 0, 1, 2, (), False, (), 'Tối nay bà con dưới quê lên, còn phòng không cháu? Đầu gối bà yếu.', 3),
]
# (npc, title, request, stated wants, stated avoid, {probe: (answer, avoid, want)}, picks, min_day)
RECOMMENDS = [
    (3, 'Chiều nay cho hai bé đi đâu?', 'Chiều nay nhà anh đi đâu cho hai bé vui?', ('kids',), (),
     dict(who=('Hai bé 4 và 7 tuổi, thêm bà nội 68 tuổi.', (), ('elder',)), move=('Bé út còn ngồi xe đẩy, bà nội đi chậm.', ('stairs', 'slope'), ()),
          budget=('Thoải mái, miễn vui.', (), ()), ride=('Nhà đi taxi 7 chỗ.', (), ()), weather=('Chiều nay 60% có mưa rào.', (), ('rain',))), 2, 1),
    (2, 'Đi dạo nhẹ buổi sáng', 'Hai cô chú muốn đi dạo nhẹ nhàng, chỗ nào yên yên.', ('quiet',), (),
     dict(who=('Chỉ hai cô chú thôi.', (), ('elder',)), move=('Chú mới thay khớp gối, không leo dốc được.', ('stairs', 'slope'), ()),
          budget=('Vừa phải thôi con.', (), ()), ride=('Cô chú đi bộ, không đi xa được.', ('far',), ('near',)), weather=('Sáng nắng đẹp, chiều se lạnh.', (), ())), 2, 1),
    (1, 'Chỗ nào chất mà rẻ?', 'Có chỗ nào “chất” mà không tốn tiền không anh?', ('adventure',), (),
     dict(who=('Đi một mình thôi.', (), ()), move=('Chân khỏe re!', (), ()), budget=('Còn đúng 60 nghìn cho cả ngày, hehe.', ('pricey',), ('free',)),
          ride=('Em thuê xe máy rồi.', (), ()), weather=('Mai trời nắng ráo, đường mòn khô.', (), ())), 2, 1),
    (4, 'Tối nay đi đâu chụp ảnh?', 'Tối nay tụi em muốn đi chỗ nào vui, chụp ảnh đẹp mà rẻ.', ('night', 'photo'), (),
     dict(who=('Nhóm 5 bạn nữ.', (), ()), move=('Không ai sao cả.', (), ()), budget=('Mỗi đứa tầm 100 nghìn thôi.', ('pricey',), ()),
          ride=('Tụi em đi bộ từ homestay.', ('far',), ('near',)), weather=('Tối nay 14 độ, không mưa.', (), ())), 2, 2),
    (0, 'Một buổi thật chill', 'Vợ chồng chị muốn một buổi thật chill, ít người.', ('photo', 'quiet'), ('crowd',),
     dict(who=('Hai vợ chồng.', (), ()), move=('Chị vừa bong gân cổ chân tuần trước.', ('slope', 'stairs'), ()), budget=('Thoải mái.', (), ()),
          ride=('Anh chị thuê xe máy.', (), ()), weather=('Sáng mai sương mù dày tới 9 giờ.', (), ())), 2, 1),
    (6, 'Ba tiếng trước giờ bay', 'Tôi còn 3 tiếng trước giờ ra sân bay, nên đi đâu gần?', ('near',), ('far',),
     dict(who=('Một mình.', (), ()), move=('Bình thường.', (), ()), budget=('Không thành vấn đề.', (), ()),
          ride=('Tôi không đi xe máy, sẽ gọi taxi.', (), ()), weather=('Trưa nay có mưa giông.', (), ('rain',))), 2, 1),
]
TEMPLATES = dict(checkin=CHECKINS, checkout=CHECKOUTS, breakfast=BREAKFASTS, booking=BOOKINGS, recommend=RECOMMENDS)


def _counted(adults: int, kids) -> int:
    return adults + sum(1 for k in kids if k >= KID_FREE_AGE)


def _code_twist(code: str) -> str:
    return code[:-2] + code[-1] + code[-2] if code[-1] != code[-2] else code[:-1] + str((int(code[-1]) + 3) % 10)


def _make_v1(day: int, slot: int, serial: int) -> dict:
    """First generator — kept word for word so saved tasks still validate."""
    rng = kit.rng(ID, day, slot)
    job = JOB_ORDER[(slot + (day - 1) * 2) % len(JOB_ORDER)]
    pool = [x for x in TEMPLATES[job] if x[-1] <= day]
    tpl = pool[((day - 1) * 3 + slot + rng.randrange(len(pool))) % len(pool)]
    return BUILD[job](day, slot, serial, tpl, rng)


def _checkin_task(day, slot, serial, tpl, rng):
    npc, platform, code, ba, bk, aa, ak, nights, size, rate, pct, cold, idst, note, _ = tpl
    real, similar = BOOKING_NAMES[npc]
    booked = _counted(ba, bk)
    rows = [dict(name=real, code=code, start=day, nights=nights, guests=booked),
            dict(name=real, code=_code_twist(code), start=day + 7, nights=nights, guests=booked),
            dict(name=similar, code=code[:3] + str((int(code[3:]) + 1111) % 10000).zfill(4), start=day, nights=nights + 1, guests=booked + 1)]
    order = [0, 1, 2]
    rng.shuffle(order)
    listing = [dict(rows[k], id='ABC'[i]) for i, k in enumerate(order)]
    match = 'ABC'[order.index(0)]
    paid = math.ceil(rate * nights * pct / 100)
    needs = dict(platform=platform, code=code, name=real, adults=ba, kids=list(bk), nights=nights, size=size, rate=rate, paid=paid,
                 cold=cold, note=note, list=listing)
    hidden = dict(match=match, adults=aa, kids=list(ak), id=idst)
    title = f'Nhận phòng · {PEOPLE[npc][0]}'
    return kit.base_task(ID, day, slot, serial, npc, title, f'Chào em, mình có đặt phòng trên {platform}.', job='checkin', needs=needs, _x=hidden,
                         ci=dict(verified=False, ids=False, counted=False, extra=None, could_fit=None, rooms=[], heater=False, q=0, paid=0, cost=0))


def _checkout_task(day, slot, serial, tpl, rng):
    npc, nights, water, noodles, snack, coffee, damage, lost, laundry, late, claim, _ = tpl
    needs = dict(nights=nights, laundry=laundry, late=late, claim=claim)
    hidden = dict(water=water, noodles=noodles, snack=snack, coffee=coffee, damage=damage, lost=lost)
    return kit.base_task(ID, day, slot, serial, npc, f'Trả phòng · {PEOPLE[npc][0]}', 'Em ơi, cho mình trả phòng với.', job='checkout',
                         needs=needs, _x=hidden, room=None, bound=False, checked=False, returned=False,
                         bill={x['id']: 0 for x in BILL_LINES}, disputes=0)


def _breakfast_task(day, slot, serial, tpl, rng):
    npc, people, runny, well, bread, milk, coffee, allergy, where, note, _ = tpl
    needs = dict(people=people, eggs=dict(runny=runny, well=well), bread=bread, milk=milk, coffee=coffee, allergy=allergy, where=where, note=note)
    return kit.base_task(ID, day, slot, serial, npc, f'Bữa sáng · {PEOPLE[npc][0]}', 'Cho mình gọi bữa sáng nhé!', job='breakfast', needs=needs, _x={},
                         tray=_empty_tray(), quoted_price=None, bound=False, refused=0)


def _booking_task(day, slot, serial, tpl, rng):
    npc, channel, offset, nights, adults, kids, stairs_ok, prefer, note, _ = tpl
    needs = dict(channel=channel, start=day + offset, nights=nights, adults=adults, kids=list(kids), stairs_ok=stairs_ok,
                 prefer=list(prefer), note=note)
    return kit.base_task(ID, day, slot, serial, npc, f'Đặt phòng · {PEOPLE[npc][0]}', f'Alo, homestay Mây phải không? Mình muốn đặt phòng ({channel}).',
                         job='booking', needs=needs, _x={}, hold=[], quote=None, decline_ok=None)


def _recommend_task(day, slot, serial, tpl, rng):
    npc, title, request, wants, avoid, probes, picks, _ = tpl
    needs = dict(request=request, wants=list(wants), avoid=list(avoid), count=picks)
    hidden = dict(probes={k: dict(answer=a, avoid=list(av), want=list(w)) for k, (a, av, w) in probes.items()})
    return kit.base_task(ID, day, slot, serial, npc, f'Gợi ý · {title}', request, job='recommend', needs=needs, _x=hidden, picks=[])


BUILD = dict(checkin=_checkin_task, checkout=_checkout_task, breakfast=_breakfast_task, booking=_booking_task, recommend=_recommend_task)

# ======================================================================== v0.5 — a busier hill town
# Tasks saved before v0.5 keep the first generator (kit.legacy serials); new ones carry gen=2.
GEN = 2
AIR_RAIN = dict(damp=25, cold=90)          # a wet day needs the windows open longer
TODAY = [
    dict(id='steady', title='Ngày thường', emoji='🌤️', weight=3, text='Khách đều đều, giá niêm yết là vừa.'),
    dict(id='festival', title='Tuần lễ hội hoa', emoji='🌸', min_day=2, weight=2,
         text='Cả phố kín phòng: thêm đơn OTA, khách chịu giá lễ hội; trung tâm đông nghẹt.'),
    dict(id='rain', title='Mưa dầm, sương ẩm', emoji='🌧️', min_day=2, weight=2,
         text=f'Phòng lâu hết mùi ẩm: khi dọn, mở cửa sổ ít nhất {AIR_RAIN["damp"]} giây. Khách hỏi chỗ đi được khi mưa.'),
    dict(id='cold', title='Rét đậm 8°C', emoji='🥶', min_day=3, weight=2, text='Đêm nay phòng nào nhận khách cũng cần máy sưởi.'),
    dict(id='low', title='Mùa thấp điểm', emoji='🍂', min_day=3, weight=2, text='Ít đơn OTA, khách so giá từng đồng: giá niêm yết dễ bị chê đắt.'),
    dict(id='weekend', title='Cuối tuần', emoji='🎒', min_day=2, weight=2, text='Khách trẻ đổ về: thêm đơn OTA, ai cũng vội hơn một chút.'),
]
TODAY_INDEX = {x['id']: x for x in TODAY}
SPECIAL_P = (0.3, 0.4, 0.5, 0.6)           # chance a later slot is a special case, by difficulty tier
RATES = [dict(id='low', name='Giá thấp điểm', short='−15%', pct=85, emoji='🍂'),
         dict(id='std', name='Giá niêm yết', short='giá gốc', pct=100, emoji='🏷️'),
         dict(id='peak', name='Giá lễ hội', short='+30%', pct=130, emoji='🌸')]
RATE_IDS = [x['id'] for x in RATES]
RATE_INDEX = {x['id']: x for x in RATES}
# Highest rate (index in RATES) a guest accepts: by budget, shifted by the market of the day.
BUDGET_BASE = dict(tight=1, normal=1, flex=2)
BUDGET_SHIFT = dict(tight=dict(low=0), normal=dict(festival=2), flex=dict(low=1))
PUSHBACK = dict(tight='Giá này quá sức em rồi, chỗ khác rẻ hơn nhiều…', normal='Sao cao hơn giá trên trang vậy? Hôm nay đâu có gì đặc biệt.',
                flex='Mùa này chỗ nào cũng giảm giá mà, bớt chút đi.')
DIRECT = ('Gọi điện', 'Mây Chat')          # deposits sent by bank transfer, proven only by a screenshot
OTAS = ('Mây Travel', 'Đi Đâu')
OTA_NAMES = ['Lý Gia Hân', 'Tô Minh Nhật', 'Ngô Bảo Vy', 'Đặng Quốc Huy', 'Châu Ngọc Lan', 'Mạc Thanh Tùng', 'Kha Mỹ Duyên', 'Phan Đức Trí',
             'Lâm Tú Anh', 'Hà Gia Bảo']
OTA_COUNT = (1, 1, 2, 2)                   # new app orders per morning, by tier
OTA_CONFLICT = (0.35, 0.45, 0.55, 0.65)    # chance an order lands on a room that is already taken
OTA_COMMISSION = 15                        # % the platform keeps
OTA_STATUS = ('new', 'synced', 'auto', 'walked')
OTA_KEYS = ('id', 'ota', 'name', 'room', 'start', 'nights', 'guests', 'total', 'net', 'status', 'rooms', 'day')
WALK_FEE = 15                              # neighbour's price difference + taxi when a guest has to be moved
CLAIM_QS = [dict(id='describe', label='Tả giúp món đồ?', emoji='🔎'), dict(id='room', label='Hôm đó ở phòng nào?', emoji='🚪'),
            dict(id='date', label='Trả phòng ngày nào?', emoji='📅'), dict(id='booking', label='Đặt phòng tên gì, qua kênh nào?', emoji='🧾')]
CLAIM_Q_IDS = [x['id'] for x in CLAIM_QS]
CLAIM_CHOICES = ('give', 'channel', 'deny')
CLAIM_RIGHT = dict(owner=('give', 'channel'), imposter=('deny', 'channel'), friend=('channel',))
DIET_NONE = 'Không kiêng gì đâu, cảm ơn đã hỏi nha!'
HOUSE_RULES = [
    'Nhận phòng 14h, trả phòng 12h. Giờ yên tĩnh 22h–6h.',
    'Cọc chuyển khoản: mở app ngân hàng đối chiếu — ảnh chụp màn hình chưa phải là tiền.',
    'Đơn OTA phải đồng bộ vào lịch trước khi khách tới. Trùng phòng: xếp phòng khác đủ chỗ; hết phòng mới chuyển sang Nhà Gỗ Cô Ba.',
    'Giá theo mùa: thấp điểm −15%, niêm yết, lễ hội +30%. Khách chê đắt thì báo lại mức khác.',
    'Đồ thất lạc chỉ giao cho người đặt phòng, hoặc người được họ xác nhận qua kênh đặt phòng.',
    'Hỏi dị ứng, ăn kiêng trước khi nấu bữa sáng.',
    'Mỗi ngày thử chuông báo khói, bình chữa cháy, van gas và ký sổ an toàn.',
]
NEUTRAL = {   # v2 copies of lines that assumed the player's gender
    'Em đi phượt một mình, có chỗ dựng xe máy không anh?': 'Em đi phượt một mình, có chỗ dựng xe máy không ạ?',
    'Lòng đào hết nha anh ơi, để tụi em chụp hình!': 'Lòng đào hết nha, để tụi em chụp hình!',
    'Một đêm thôi anh, phòng nào rẻ nhất cũng được.': 'Một đêm thôi ạ, phòng nào rẻ nhất cũng được.',
    'Có chỗ nào “chất” mà không tốn tiền không anh?': 'Có chỗ nào “chất” mà không tốn tiền không ạ?',
}


def _neutral(text: str) -> str:
    return NEUTRAL.get(text, text)


def _ci2(row, **over):
    npc, platform, code, ba, bk, aa, ak, nights, size, rate, pct, cold, idst, note, min_day = row
    x = dict(npc=npc, platform=platform, code=code, ba=ba, bk=tuple(bk), aa=aa, ak=tuple(ak), nights=nights, size=size, rate=rate, pct=pct,
             cold=cold, idst=idst, note=_neutral(note), min_day=min_day, case=None, received=True)
    x.update(over)
    return x


def _co2(row, **over):
    npc, nights, water, noodles, snack, coffee, damage, lost, laundry, late, claim, min_day = row
    x = dict(npc=npc, nights=nights, water=water, noodles=noodles, snack=snack, coffee=coffee, damage=damage, lost=lost, laundry=laundry,
             late=late, claim=claim, min_day=min_day, case=None, package=None)
    x.update(over)
    return x


def _bf2(row, **over):
    npc, people, runny, well, bread, milk, coffee, allergy, where, note, min_day = row
    x = dict(npc=npc, people=people, runny=runny, well=well, bread=bread, milk=milk, coffee=coffee, allergy=allergy, where=where,
             note=_neutral(note), min_day=min_day, case=None, hidden=None, fix=None, diet=None)
    x.update(over)
    return x


def _bk2(row, budget, say, **over):
    npc, channel, offset, nights, adults, kids, stairs_ok, prefer, note, min_day = row
    x = dict(npc=npc, channel=channel, offset=offset, nights=nights, adults=adults, kids=tuple(kids), stairs_ok=stairs_ok, prefer=tuple(prefer),
             note=_neutral(note), min_day=min_day, case=None, budget=budget, say=say)
    x.update(over)
    return x


def _rc2(row, **over):
    npc, title, request, wants, avoid, probes, picks, min_day = row
    x = dict(npc=npc, title=title, request=_neutral(request), wants=tuple(wants), avoid=tuple(avoid), probes=probes, picks=picks,
             min_day=min_day, case=None)
    x.update(over)
    return x


CHECKINS2 = [_ci2(r) for r in CHECKINS] + [
    # Special: the deposit is proven only by a screenshot. Some days the money really came, some days it went to a
    # mistyped account number — the screenshot looks fine either way, only the bank app tells.
    _ci2((9, 'Mây Chat', 'MC-5512', 1, (), 1, (), 2, 2, 28, 30, False, 'ok', 'Chị chuyển cọc qua ngân hàng rồi nha, ảnh chụp đây.', 2),
         case='transfer', received=True),
    _ci2((10, 'Gọi điện', 'GD-2741', 2, (), 2, (), 2, 2, 30, 30, False, 'ok', 'Tụi em chuyển cọc hôm qua rồi nha, ảnh chụp màn hình đây nè.', 2),
         case='transfer', received=False),
    _ci2((14, 'Gọi điện', 'GD-1190', 2, (), 2, (), 1, 2, 30, 50, True, 'app', 'Con gái cô chuyển khoản cọc rồi, có ảnh tin nhắn ngân hàng đây con.', 4),
         case='transfer', received=False),
]
CHECKOUTS2 = [_co2(r) for r in CHECKOUTS] + [
    _co2((0, 2, 3, 2, 1, 4, None, None, 1, False, 'Tụi chị trả phòng nha, hai hôm nay vui lắm!', 2), case='package',
         package=dict(name='Gói trăng mật', text='đã gồm minibar (nước, mì, bánh) và giặt ủi', free=['water', 'noodles', 'snack', 'laundry'], water_free=None)),
    _co2((3, 2, 7, 1, 2, 2, None, 'Bình sữa em bé', 0, True, 'Nhà anh trả phòng, cho xin trễ một chút nha.', 3), case='package',
         package=dict(name='Gói gia đình', text='tặng 4 chai nước mỗi đêm; mì, bánh minibar tính riêng', free=[], water_free=8)),
]
BREAKFASTS2 = [_bf2(r) for r in BREAKFASTS] + [
    # Special: someone at the table cannot eat eggs, and only says so when asked.
    _bf2((14, 2, 0, 2, 2, 0, 2, None, 'Mang lên phòng', 'Hai phần như nhau nha con: trứng chín kỹ, bánh mì, cà phê.', 3), case='allergy',
         hidden='egg', fix=dict(runny=0, well=1), diet='À, con gái cô dị ứng trứng — phần nó chỉ bánh mì với cà phê thôi con.'),
    _bf2((3, 4, 2, 2, 4, 2, 2, None, 'Bàn sân vườn', 'Bố mẹ hai trứng lòng đào, hai bé hai trứng chín kỹ, thêm sữa cho hai bé.', 4), case='allergy',
         hidden='egg', fix=dict(runny=2, well=1), diet='À quên, bé út dị ứng trứng! Phần bé bỏ trứng, chỉ bánh mì với sữa thôi.'),
]
BUDGETS = [('flex', 'Phòng đẹp là được, giá không thành vấn đề.'), ('normal', 'Giá như trên trang là ổn.'),
           ('tight', 'Em đi phượt, rẻ được chút nào hay chút đó.'), ('normal', 'Giá bình thường là được con.'),
           ('tight', 'Tụi em chia tiền năm đứa, đắt quá là tụi em đi chỗ khác.'), ('flex', 'Công ty thanh toán, chỉ cần hóa đơn đúng giá.'),
           ('normal', 'Giá phải chăng thôi cháu.')]
BOOKINGS2 = [_bk2(r, *b) for r, b in zip(BOOKINGS, BUDGETS)] + [
    _bk2((10, 'Mây Chat', 1, 5, 1, (), True, (), 'Em ở 5 đêm làm việc từ xa, phòng nào yên tĩnh là được.', 3), 'tight',
         'Ở dài ngày nên em mong giá mềm; chỗ khác họ giảm 15% cho khách ở lâu.', case='long'),
    _bk2((4, 'Mây Chat', 2, 2, 6, (), True, (), 'Nhóm sáu đứa tụi em đi chơi, cần hai phòng gần nhau.', 3), 'normal',
         'Giá như trên trang thì tụi em ok; mùa lễ hội thì chịu giá lễ hội luôn.', case='group'),
    _bk2((0, 'Email', 3, 2, 2, (), True, ('thong', 'ho'), 'Kỷ niệm ngày cưới, cho chị phòng đẹp nhất nha.', 4), 'flex',
         'Dịp đặc biệt mà, phòng đẹp nhất là được, giá không sao.', case='flex'),
]
RECOMMENDS2 = [_rc2(r) for r in RECOMMENDS] + [
    _rc2((14, 'Chỗ nào có ghế ngồi nghỉ?', 'Cô với con gái muốn đi đâu đó nhẹ nhàng, cô đi chậm lắm.', ('elder',), (),
          dict(who=('Hai mẹ con thôi.', (), ('elder',)), move=('Cô chống gậy, không leo bậc được.', ('stairs', 'slope'), ('flat',)),
               budget=('Con gái cô bao, thoải mái.', (), ()), ride=('Con gái cô lái xe hơi.', (), ()), weather=('Chiều nắng nhẹ.', (), ())), 2, 3)),
]
# Lost-and-found calls. The ticket belongs to the owner written in the book; the caller may be someone else.
CLAIMS = [
    dict(key='buds', npc=9, kind='owner', min_day=3, item='Tai nghe không dây', emoji='🎧', room='suong', ago=2,
         detail='Màu trắng, hộp sạc dán sticker mèo cam, nắp hơi xước.', booker='Trần Thị Yến · Mây Travel',
         note='Chị để quên tai nghe không dây, nhờ em xem giúp.',
         say=dict(describe='Tai nghe màu trắng, hộp sạc có dán con mèo màu cam, nắp bị xước một chút.',
                  room='Phòng Sương Sớm, hai giường đơn đó em.', date='Chị trả phòng sáng hôm kia.',
                  booking='Tên Trần Thị Yến, đặt trên Mây Travel.')),
    dict(key='charger', npc=6, kind='imposter', min_day=3, item='Sạc laptop', emoji='🔌', room='thong', ago=1,
         detail='Sạc 65W đầu USB-C, dây quấn băng keo xanh gần đầu cắm.', booker='Vũ Tuấn Kiệt · Đi Đâu',
         note='Tôi để quên cục sạc laptop hôm qua, gửi xe ôm qua lấy liền được không?',
         say=dict(describe='Sạc laptop màu đen, đầu tròn, dây trắng. Loại thường thôi.',
                  room='Phòng tầng trệt gần cổng ấy.', date='Hôm qua.',
                  booking='Đặt tên… à, tên Kiệt. Cứ đưa xe ôm giúp nhé, tôi trả tiền xe.')),
    dict(key='sketch', npc=4, kind='friend', min_day=3, item='Sổ tay vẽ ký họa', emoji='📓', room='quy', ago=3,
         detail='Bìa giấy kraft, trang đầu vẽ đồi dã quỳ, góc có chữ ký “Chi”.', booker='Đỗ Mai Chi · Mây Travel',
         note='Em ghé lấy giúp cuốn sổ vẽ của nhóm tụi em nha.',
         say=dict(describe='Sổ bìa giấy kraft, trang đầu vẽ đồi hoa vàng, có chữ ký của Chi.',
                  room='Phòng Dã Quỳ, tụi em ở bốn đứa.', date='Trả phòng ba hôm trước ạ.',
                  booking='Đặt tên Đỗ Mai Chi trên Mây Travel. Em là Nhi, bạn đi cùng; Chi về Sài Gòn rồi.')),
    dict(key='glasses', npc=2, kind='owner', min_day=3, item='Kính lão', emoji='👓', room='thong', ago=1,
         detail='Gọng đồng mảnh, hộp da nâu in chữ “Kính Hòa Bình”.', booker='Phạm Ngọc Diệp · Gọi điện',
         note='Con ơi, chú để quên cặp kính lão ở phòng, con xem giúp cô với.',
         say=dict(describe='Kính của chú, gọng mảnh màu đồng, để trong hộp da nâu có in chữ Hòa Bình đó con.',
                  room='Phòng Đồi Thông, tầng trệt, cô chú không leo cầu thang được mà.', date='Cô chú về hôm qua.',
                  booking='Cô gọi điện đặt, tên Phạm Ngọc Diệp.')),
    dict(key='scarf', npc=0, kind='imposter', min_day=3, item='Khăn quàng len đỏ', emoji='🧣', room='thong', ago=2,
         detail='Len đỏ đô, thêu chữ “T.H” ở góc, một đầu tua bị sút chỉ.', booker='Nguyễn Thu Hà · Mây Travel',
         note='Mình để quên cái khăn len đỏ, ship về Sài Gòn giúp nha.',
         say=dict(describe='Khăn len màu đỏ tươi, trơn, không có gì đặc biệt đâu.',
                  room='Phòng Dã Quỳ hay Đồi Thông gì đó, mình không nhớ.', date='Hình như tuần trước.',
                  booking='Tên Thu Hà. Mà sao hỏi nhiều vậy, cái khăn thôi mà!')),
    dict(key='teddy', npc=3, kind='owner', min_day=4, item='Gấu bông hình thỏ', emoji='🐰', room='quy', ago=1,
         detail='Thỏ hồng, tai trái có miếng vá hình ngôi sao, cổ đeo nơ xanh.', booker='Trần Minh Tuấn · Đi Đâu',
         note='Bé út nhà anh khóc cả đêm vì quên con thỏ bông ở phòng!',
         say=dict(describe='Con thỏ hồng, tai trái vá miếng hình ngôi sao, cổ có cái nơ xanh.',
                  room='Phòng Dã Quỳ, phòng gia đình hai giường đôi.', date='Nhà anh trả phòng trưa hôm qua.',
                  booking='Tên Trần Minh Tuấn, đặt trên Đi Đâu.')),
    dict(key='camera', npc=1, kind='imposter', min_day=6, item='Máy ảnh film', emoji='📷', room='gac', ago=2,
         detail='Canon AE-1 chạy phim, dây đeo thổ cẩm; trong máy còn cuộn phim chụp dở.', booker='Lê Quốc Bảo · Mây Travel',
         note='Mình để quên máy ảnh ở Gác Mái, gửi giúp mình qua địa chỉ mới nha.',
         say=dict(describe='Máy ảnh Canon, dây đeo thổ cẩm. Máy kỹ thuật số, thẻ nhớ 64 GB.',
                  room='Gác Mái, cầu thang gỗ dốc.', date='Trả phòng sáng hôm kia.',
                  booking='Lê Quốc Bảo, đặt trên Mây Travel.')),
]
TEMPLATES2 = dict(checkin=CHECKINS2, checkout=CHECKOUTS2, breakfast=BREAKFASTS2, booking=BOOKINGS2, recommend=RECOMMENDS2, claim=CLAIMS)


def today(day: int) -> dict:
    return kit.daily(ID, day, TODAY)


def _job2(day: int, slot: int) -> str:
    job = JOB_ORDER[(slot + (day - 1) * 2) % len(JOB_ORDER)]
    if day >= 3 and slot == 2 and (day == 3 or kit.rng(ID, 'claim-slot', day).random() < 0.45):
        return 'claim'
    if today(day)['id'] == 'festival' and job == 'recommend' and slot >= 1:
        return 'booking'
    return job


def _special2(day: int, slot: int, job: str) -> bool:
    if job == 'claim':
        return False
    has = any(x['case'] and x['min_day'] <= day for x in TEMPLATES2[job])
    return slot > 0 and has and kit.rng(ID, 'pick2', day, slot).random() < SPECIAL_P[kit.tier(day)]


PLAN_SLOTS = 12        # tickets per day that get a hand-planned guest; later ones fall back to the plain walk
SEEN_SLOTS = 6         # yesterday's first tickets: the same guest does not come back for the same job next morning
_PLAN: dict = {}


def _walk2(day: int, slot: int, job: str, flip: bool = False) -> list:
    """Days walk a shuffled pool in steps, so everyone takes a turn. Returns the pool in the order to try."""
    special = _special2(day, slot, job) != flip
    pool = [x for x in TEMPLATES2[job] if x['min_day'] <= day and bool(x.get('case')) == special]
    kit.rng(ID, 'perm2', job, special, len(pool)).shuffle(pool)
    if not pool:
        return []
    k = sum(1 for sl in range(slot) if _job2(day, sl) == job and _special2(day, sl, job) == special)
    step = next(x for x in (3, 2, 5, 7) if math.gcd(x, len(pool)) == 1)
    return [pool[((day - 1) * step + k + j) % len(pool)] for j in range(len(pool))]


def _plan_build(day: int, prev: list | None) -> list:
    yesterday = {}
    for sl, x in enumerate((prev or [])[:SEEN_SLOTS]):
        yesterday.setdefault(_job2(day - 1, sl), set()).add(x['npc'])
    picks = []
    for slot in range(PLAN_SLOTS):
        job = _job2(day, slot)
        order = _walk2(day, slot, job)
        fresh = [x for x in order if all(x is not y for y in picks)] or order
        other = [x for x in _walk2(day, slot, job, flip=True) if all(x is not y for y in picks)]
        # Nobody checks in, checks out and books on one morning, and nobody leaves twice in two days.
        # A tiny special-case pool gives way to the plain one rather than repeat a guest.
        today_ = {x['npc'] for x in picks}
        seen = today_ | yesterday.get(job, set())
        picks.append(next((x for x in fresh if x['npc'] not in seen), None) or next((x for x in other if x['npc'] not in seen), None)
                     or next((x for x in fresh + other if x['npc'] not in today_), fresh[0]))
    return picks


def _plan(day: int) -> list:
    """Guests of a day, decided from the day before; walked forward once and remembered (no deep recursion)."""
    if day not in _PLAN:
        start = max((d for d in _PLAN if d < day), default=0)
        for d in range(start + 1, day + 1):
            _PLAN[d] = _plan_build(d, _PLAN.get(d - 1))
    return _PLAN[day]


def _pick2(day: int, slot: int, job: str) -> dict:
    if slot < PLAN_SLOTS:
        return _plan(day)[slot]
    return (_walk2(day, slot, job) or _walk2(day, slot, job, flip=True))[0]


def _checkin_task2(day, slot, serial, tpl, mod, rng):
    real, similar = BOOKING_NAMES[tpl['npc']]
    booked = _counted(tpl['ba'], tpl['bk'])
    code = tpl['code']
    later = day if kit.tier(day) >= 2 else day + 7      # seasoned days: the look-alike code is booked for today too
    rows = [dict(name=real, code=code, start=day, nights=tpl['nights'], guests=booked),
            dict(name=real, code=_code_twist(code), start=later, nights=tpl['nights'], guests=booked),
            dict(name=similar, code=code[:3] + str((int(code[3:]) + 1111) % 10000).zfill(4), start=day, nights=tpl['nights'] + 1, guests=booked + 1)]
    order = [0, 1, 2]
    rng.shuffle(order)
    listing = [dict(rows[k], id='ABC'[i]) for i, k in enumerate(order)]
    paid = math.ceil(tpl['rate'] * tpl['nights'] * tpl['pct'] / 100)
    proof = None if not paid else 'bank' if tpl['platform'] in DIRECT else 'app'
    needs = dict(platform=tpl['platform'], code=code, name=real, adults=tpl['ba'], kids=list(tpl['bk']), nights=tpl['nights'], size=tpl['size'],
                 rate=tpl['rate'], paid=paid, cold=tpl['cold'] or mod == 'cold', note=tpl['note'], list=listing, proof=proof, today=mod)
    received = tpl['received'] if tpl['case'] != 'transfer' else rng.random() < 0.4
    hidden = dict(match='ABC'[order.index(0)], adults=tpl['aa'], kids=list(tpl['ak']), id=tpl['idst'], received=received, case=tpl['case'])
    opening = (f'Chào em, mình có đặt phòng trên {tpl["platform"]}.' if tpl['platform'] not in DIRECT
               else 'Chào em, mình đặt phòng trước rồi, có chuyển cọc.' if paid else 'Chào em, mình có đặt phòng trước.')
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Nhận phòng · {PEOPLE[tpl["npc"]][0]}', opening, job='checkin', needs=needs, _x=hidden,
                         ci=dict(verified=False, ids=False, counted=False, extra=None, could_fit=None, rooms=[], heater=False, q=0, paid=0, cost=0),
                         bank=None, gen=GEN)


def _checkout_task2(day, slot, serial, tpl, mod, rng):
    needs = dict(nights=tpl['nights'], laundry=tpl['laundry'], late=tpl['late'], claim=tpl['claim'], package=copy.deepcopy(tpl['package']), today=mod)
    hidden = dict(water=tpl['water'], noodles=tpl['noodles'], snack=tpl['snack'], coffee=tpl['coffee'], damage=tpl['damage'], lost=tpl['lost'], case=tpl['case'])
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Trả phòng · {PEOPLE[tpl["npc"]][0]}', 'Em ơi, cho mình trả phòng với.', job='checkout',
                         needs=needs, _x=hidden, room=None, bound=False, checked=False, returned=False,
                         bill={x['id']: 0 for x in BILL_LINES}, disputes=0, gen=GEN)


def _breakfast_task2(day, slot, serial, tpl, mod, rng):
    needs = dict(people=tpl['people'], eggs=dict(runny=tpl['runny'], well=tpl['well']), bread=tpl['bread'], milk=tpl['milk'], coffee=tpl['coffee'],
                 allergy=tpl['allergy'], where=tpl['where'], note=tpl['note'], today=mod)
    hidden = dict(allergy=tpl['hidden'], fix=copy.deepcopy(tpl['fix']), diet=tpl['diet'], case=tpl['case'])
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Bữa sáng · {PEOPLE[tpl["npc"]][0]}', 'Cho mình gọi bữa sáng nhé!', job='breakfast',
                         needs=needs, _x=hidden, tray=_empty_tray(), quoted_price=None, bound=False, refused=0, diet=False, gen=GEN)


def _booking_task2(day, slot, serial, tpl, mod, rng):
    needs = dict(channel=tpl['channel'], start=day + tpl['offset'], nights=tpl['nights'], adults=tpl['adults'], kids=list(tpl['kids']),
                 stairs_ok=tpl['stairs_ok'], prefer=list(tpl['prefer']), note=tpl['note'], today=mod)
    hidden = dict(budget=tpl['budget'], say=tpl['say'], case=tpl['case'])
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Đặt phòng · {PEOPLE[tpl["npc"]][0]}',
                         f'Alo, homestay Mây phải không? Mình muốn đặt phòng ({tpl["channel"]}).', job='booking', needs=needs, _x=hidden,
                         hold=[], quote=None, decline_ok=None, rate='std', asked_budget=False, haggles=0, gen=GEN)


def _recommend_task2(day, slot, serial, tpl, mod, rng):
    probes = {k: dict(answer=a, avoid=list(av), want=list(w)) for k, (a, av, w) in tpl['probes'].items()}
    # The day itself changes what the guests will face outside.
    if mod == 'rain':
        probes['weather'] = dict(answer='Hôm nay mưa dầm cả ngày, đường đất trơn trượt.', avoid=['slope'], want=['rain'])
    elif mod == 'cold':
        probes['weather'] = dict(answer='Rét đậm 8 độ, gió lùa mạnh — ở ngoài trời lâu là cóng tay.', avoid=[], want=['indoor'])
    elif mod == 'festival':
        ride = probes['ride']
        probes['ride'] = dict(answer=ride['answer'] + ' Mà tuần lễ hội, nghe nói trung tâm kẹt cứng.', avoid=sorted(set(ride['avoid']) | {'crowd'}),
                              want=ride['want'])
    needs = dict(request=tpl['request'], wants=list(tpl['wants']), avoid=list(tpl['avoid']), count=tpl['picks'], today=mod)
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Gợi ý · {tpl["title"]}', tpl['request'], job='recommend', needs=needs,
                         _x=dict(probes=probes, case=tpl['case']), picks=[], gen=GEN)


def _claim_task(day, slot, serial, tpl, mod, rng):
    entry = dict(item=tpl['item'], emoji=tpl['emoji'], room=tpl['room'], day=max(1, day - tpl['ago']), detail=tpl['detail'], booker=tpl['booker'])
    needs = dict(entry=entry, note=tpl['note'], today=mod)
    return kit.base_task(ID, day, slot, serial, tpl['npc'], f'Đồ thất lạc · {tpl["item"]}', '📞 Có người gọi hỏi món đồ khách để quên.',
                         job='claim', needs=needs, _x=dict(kind=tpl['kind'], say=dict(tpl['say']), case='claim'), asked=[], choice=None, gen=GEN)


BUILD2 = dict(checkin=_checkin_task2, checkout=_checkout_task2, breakfast=_breakfast_task2, booking=_booking_task2, recommend=_recommend_task2,
              claim=_claim_task)


def _make_v2(day: int, slot: int, serial: int) -> dict:
    job = _job2(day, slot)
    return BUILD2[job](day, slot, serial, _pick2(day, slot, job), today(day)['id'], kit.rng(ID, 'v2', day, slot))


def make_task(day: int, slot: int, serial: int) -> dict:
    if kit.legacy(serial):
        return _make_v1(day, slot, serial)
    return _make_v2(day, slot, serial)


FIXED = ('job', 'needs', '_x', 'gen')


def _air(c: dict) -> dict:
    return AIR_RAIN if today(c['day'])['id'] == 'rain' else AIR


def _cap(t: dict) -> int:
    """Highest rate index this guest accepts today (budget shifted by the market)."""
    b = t['_x']['budget']
    return BUDGET_SHIFT[b].get(t['needs'].get('today'), BUDGET_BASE[b])


def _quote(c: dict, rooms: list, nights: int, rate: str = 'std') -> dict:
    base = sum(kit.price(c, r, SPEC['prices'][r]) for r in rooms) * nights
    total = -(-base * RATE_INDEX[rate]['pct'] // 100)
    return dict(total=total, deposit=math.ceil(total * DEPOSIT_PCT / 100))


def _eggs_want(t: dict) -> dict:
    """Eggs the table really wants (a hidden allergy removes one plate's egg)."""
    fix = t['_x'].get('fix') if t.get('gen') else None
    return dict(fix) if fix else dict(t['needs']['eggs'])


def _lost_deposit(t: dict) -> bool:
    return bool(t.get('gen')) and t['needs'].get('proof') == 'bank' and not t['_x'].get('received', True) and t.get('bank') is None


def _empty_tray() -> dict:
    return dict(eggs=[], pan=None, bread=0, milk=0, coffee=0, cost=0)


def _room_state(status: str, guest=None, until=0, q=0, wear=100) -> dict:
    return dict(status=status, guest=guest, task=None, until=until, q=q, mini=0, note=None, hk=None, wear=wear, snag=None)


def initial() -> dict:
    rooms = dict(thong=_room_state('clean', q=5, wear=90), suong=_room_state('occupied', 'Khách đêm qua (ca đêm nhận)', 1, wear=80),
                 gac=_room_state('dirty', wear=75), quy=_room_state('clean', q=4, wear=85), ho=_room_state('maintenance'))
    rooms['gac']['mini'] = 1
    rooms['ho']['note'] = 'Đang sửa ban công — mở ở cấp 3'
    bookings = [dict(id='bk-0', rooms=['quy'], start=2, nights=2, guests=4, name='Đoàn cô Liên (gọi điện)', total=96, deposit=29, task=None)]
    d = dict(rooms=rooms, bookings=bookings, lost=[], nights_sold=0, walked=0, cleaned=0, arrivals=0, seq=0,
             desk=kit.desk_initial(), **copy.deepcopy(DATA_V2))
    return _migrate(d, 1)


DATA_V2 = dict(ota=[], safety_day=0, synced=0, ota_walked=0, strikes=0, claims_ok=0, claims_bad=0, lost_deposit=0, day_synced=0, day_walked=0)


def _migrate(d: dict, day: int) -> dict:
    """v0.5 fields, the desk book and the care loop (room upkeep, stays, guest book, garden, firewood, rating) — idempotent.
    Stays follow the rooms: an occupied room without a stay gets a neutral one, any other room loses its stay."""
    for k, v in {**DATA_V2, **DATA_CARE}.items():
        if k not in d:
            d[k] = copy.deepcopy(v)
    if 'desk' not in d:
        d['desk'] = kit.desk_initial()
    rooms = d.get('rooms')
    if isinstance(rooms, dict):
        for r in rooms.values():
            if isinstance(r, dict):
                r.setdefault('wear', 100)
                r.setdefault('snag', None)
        _sync_stays(d, day)
    return d


def _data(c: dict) -> dict:
    """Career data with the v0.5 fields, the desk book and the care loop (old saves get them on first touch)."""
    return _migrate(kit.data(c), c['day'])


def _npc_index(t: dict) -> int:
    return int(t['npc'].rsplit('_', 1)[1]) - 1


def _guest(t: dict) -> str:
    return PEOPLE[_npc_index(t)][0]


def _overlap(a: int, an: int, b: int, bn: int) -> bool:
    return a < b + bn and b < a + an


def _blocked(c: dict, rid: str, start: int, nights: int) -> str | None:
    """Why a room cannot be sold for [start, start+nights) — None when free."""
    d = kit.data(c)
    r = d['rooms'][rid]
    if ROOM_INDEX[rid]['unlock'] > kit.level(c):
        return f'Phòng {ROOM_INDEX[rid]["name"]} mở ở cấp {ROOM_INDEX[rid]["unlock"]}.'
    if r['status'] == 'maintenance':
        return f'Phòng {ROOM_INDEX[rid]["name"]} đang bảo trì.'
    # A guest bound to a pending check-out still holds the room tonight; later nights are free once they leave.
    if r['status'] == 'occupied' and (r['until'] > start or (r['task'] and start <= c['day'])):
        return f'Phòng {ROOM_INDEX[rid]["name"]} còn khách ở tới ngày {r["until"]}.'
    for b in d['bookings']:
        if rid in b['rooms'] and _overlap(b['start'], b['nights'], start, nights):
            return f'Phòng {ROOM_INDEX[rid]["name"]} đã có khách đặt từ ngày {b["start"]} ({b["nights"]} đêm).'
    return None


def _ready_now(c: dict, rid: str, nights: int) -> str | None:
    why = _blocked(c, rid, c['day'], nights)
    if why:
        return why
    r = kit.data(c)['rooms'][rid]
    if r['status'] != 'clean':
        return f'Phòng {ROOM_INDEX[rid]["name"]} chưa dọn xong.'
    return None


def _combos(c: dict):
    ids = [r['id'] for r in ROOMS if r['unlock'] <= kit.level(c)]
    for i, a in enumerate(ids):
        yield [a]
        for b in ids[i + 1:]:
            yield [a, b]


def _can_book(c: dict, n: dict) -> bool:
    if n['start'] < c['day']:
        return False
    need = _counted(n['adults'], n['kids'])
    for rooms in _combos(c):
        if sum(ROOM_INDEX[r]['cap'] for r in rooms) < need:
            continue
        if not n['stairs_ok'] and any(ROOM_INDEX[r]['stairs'] for r in rooms):
            continue
        if all(_blocked(c, r, n['start'], n['nights']) is None for r in rooms):
            return True
    return False


def _can_fit_now(c: dict, people: int, nights: int) -> bool:
    for rooms in _combos(c):
        if sum(ROOM_INDEX[r]['cap'] for r in rooms) >= people and all(_ready_now(c, r, nights) is None for r in rooms):
            return True
    return False


def _free_tonight(c: dict, rid: str, nights: int) -> bool:
    """Sellable from tonight once today's check-out (if any) is done and the room is cleaned."""
    d = kit.data(c)
    r = d['rooms'][rid]
    if r['status'] == 'occupied' and r['task'] and r['until'] <= c['day']:
        return not any(rid in b['rooms'] and _overlap(b['start'], b['nights'], c['day'], nights) for b in d['bookings'])
    return _blocked(c, rid, c['day'], nights) is None


def _could_seat(c: dict, people: int, nights: int) -> str | None:
    """Name of a room (or pair) that can still take this party tonight — None when the house is truly full."""
    for rooms in _combos(c):
        if sum(ROOM_INDEX[r]['cap'] for r in rooms) >= people and all(_free_tonight(c, r, nights) for r in rooms):
            return ' + '.join(ROOM_INDEX[r]['name'] for r in rooms)
    return None


def _bind_checkout(c: dict, t: dict) -> None:
    """Find the room this departing guest slept in (rooms are shared state)."""
    d = kit.data(c)
    name = _guest(t)
    rooms = d['rooms']
    free = [rid for rid in ROOM_INDEX if rooms[rid]['status'] == 'occupied' and not rooms[rid]['task']]
    stays = _data(c)['stays']
    pick = (next((r for r in free if rooms[r]['guest'] == name), None)
            or next((r for r in free if rooms[r]['until'] <= c['day']), None)
            # the couple of room 3 are never mistaken for someone else's departure
            or next((r for r in free if not (stays.get(r) or {}).get('anniv')), None))
    if pick is None:
        # The night shift checked this guest into a clean room that nobody booked for tonight.
        pick = next((rid for rid in ROOM_INDEX if rooms[rid]['status'] == 'clean' and not rooms[rid]['task']
                     and ROOM_INDEX[rid]['unlock'] <= kit.level(c) and _blocked(c, rid, c['day'], 1) is None), None)
    if pick:
        r = rooms[pick]
        st = _data(c)['stays'].get(pick)
        if st:
            st.update(guest=name, npc=_npc_index(t))
        r.update(status='occupied', guest=name, task=t['id'], until=max(r['until'], c['day']))
    t['room'] = pick
    t['bound'] = True


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['job'] == 'breakfast' and t.get('quoted_price') is None:
        t['quoted_price'] = kit.price(c, 'breakfast', SPEC['prices']['breakfast']) * t['needs']['people']
        t['bound'] = True
    if t['job'] == 'checkout' and not t['bound']:
        _bind_checkout(c, t)
    if t.get('gen') and t['status'] == 'new' and t.get('patience') == 100:
        # Later days and busy markets make guests a little less patient.
        t['patience'] = max(60, 100 - 4 * kit.tier(t['day']) - (6 if t['needs'].get('today') in ('festival', 'weekend') else 0))


def on_start(s: dict, c: dict) -> None:
    d = kit.data(c)
    day = c['day']
    left = []
    for rid, r in d['rooms'].items():
        if r['status'] == 'occupied' and not r['task'] and r['until'] <= day:
            left.append(ROOM_INDEX[rid]['name'])
            _depart(s, c, rid)
            r.update(status='dirty', guest=None, until=0, mini=min(6, r['mini'] + (day + len(rid)) % 2))
    if left:
        kit.log(s, c, 'homestay', 'Sáng nay khách trả phòng ' + ', '.join(left) + ' (đã thanh toán trước). Phòng cần dọn.')
    if day % 5 == 0:
        pool = [rid for rid in ROOM_INDEX if ROOM_INDEX[rid]['unlock'] <= kit.level(c) and d['rooms'][rid]['status'] in ('clean', 'dirty')
                and not d['rooms'][rid]['task']]
        if pool:
            rid = pool[(day // 5) % len(pool)]
            issue = ISSUES[(day // 5) % len(ISSUES)]
            d['rooms'][rid].update(status='maintenance', note=issue, hk=None)
            kit.log(s, c, 'homestay', f'Phòng {ROOM_INDEX[rid]["name"]}: {issue.lower()}. Gọi thợ sửa trước khi bán phòng.')
    for t in c['tasks']:
        if t['career'] == ID and t['status'] not in ('completed', 'cancelled', 'referred'):
            on_task(s, c, t)
    d = _data(c)
    _care_start(s, c)
    mod = today(day)
    if day >= 2:
        kit.log(s, c, 'homestay', f'{mod["emoji"]} Hôm nay: {mod["title"]}. {mod["text"]}')
        _ota_new(s, c, mod['id'])
    kit.desk_start(s, c, ID, d['desk'], DESK, mod['id'], mod['id'] == 'festival')


def on_close(s: dict, c: dict) -> dict:
    """Guests who booked ahead arrive in the evening: their room must be clean."""
    d = _data(c)
    day = c['day']
    lines = [f'Hôm nay xong {c.get("day_completed", 0)} việc.']
    lines += _ota_close(s, c)
    lines += _care_close(s, c)
    arrived, walked, moved = [], [], []
    keep = []
    for b in d['bookings']:
        if b['start'] > day:
            keep.append(b)
            continue
        if b['start'] + b['nights'] <= day:
            continue  # stale entry; nothing to do
        nights = b['start'] + b['nights'] - day
        chosen = []
        for rid in b['rooms']:
            ok = d['rooms'][rid]['status'] == 'clean' and not d['rooms'][rid]['task'] and ROOM_INDEX[rid]['unlock'] <= kit.level(c) and rid not in chosen
            if not ok:
                alt = next((x['id'] for x in ROOMS if x['id'] not in chosen and x['id'] not in b['rooms'] and x['cap'] >= ROOM_INDEX[rid]['cap']
                            and d['rooms'][x['id']]['status'] == 'clean' and not d['rooms'][x['id']]['task'] and x['unlock'] <= kit.level(c)
                            and all(not (x['id'] in o['rooms'] and o is not b and _overlap(o['start'], o['nights'], day, nights)) for o in d['bookings'])), None)
                if alt:
                    moved.append(f'{b["name"]}: {ROOM_INDEX[rid]["name"]} → {ROOM_INDEX[alt]["name"]}')
                    rid = alt
                else:
                    chosen = None
                    break
            chosen.append(rid)
        if chosen:
            for rid in chosen:
                d['rooms'][rid].update(status='occupied', guest=b['name'], task=None, until=day + nights)
                _stay_open(c, rid, b['name'], b.get('npc', -1) if not b.get('ota') else -1, b.get('anniv', 0) if rid == chosen[0] else 0)
            if b.get('anniv'):
                there = 'phòng số 3 như mọi năm' if chosen[0] == ANNIV_ROOM else f'phòng {ROOM_INDEX[chosen[0]]["name"]} — năm nay không được phòng số 3'
                lines.append(f'🗝️ {ANNIV_NAME} lên tới nơi, nhận {there}.')
            due = max(0, b['total'] - b['deposit'])
            if due:
                label = (f'{b["ota"]} chuyển tiền phòng (đã trừ {OTA_COMMISSION}% hoa hồng) · {b["name"]}' if b.get('ota')
                         else f'Khách đặt trước nhận phòng · {b["name"]}')
                kit.money(s, c, due, label, b['id'], category='room')
                if b.get('ota'):
                    kit.bank(due)   # the platform's payout lands in the account
            d['arrivals'] += 1
            d['nights_sold'] += nights * len(chosen)
            arrived.append(b['name'])
            kit.log(s, c, 'homestay', f'Tối nay {b["name"]} nhận phòng {", ".join(ROOM_INDEX[r]["name"] for r in chosen)}; thu nốt {due} xu.')
        else:
            if b.get('ota'):
                # App guests paid the platform: the house pays the neighbour's difference and the taxi.
                refund = min(WALK_FEE, c['money'])
                if refund:
                    kit.money(s, c, -refund, f'Chuyển khách {b["ota"]} sang Nhà Gỗ Cô Ba · {b["name"]}', b['id'], category='refund')
                d['ota_walked'] += 1
                d['strikes'] += 1
                d['desk']['marks']['ota_walk'] = day
                kit.log(s, c, 'homestay', f'Không có phòng sạch cho {b["name"]}: phải xin lỗi, trả {refund} xu chênh lệch và taxi sang Nhà Gỗ Cô Ba.')
            else:
                refund = min(b['deposit'], c['money'])
                if refund:
                    kit.money(s, c, -refund, f'Hoàn cọc, chuyển khách sang Nhà Gỗ Cô Ba · {b["name"]}', b['id'], category='refund')
                kit.log(s, c, 'homestay', f'Không có phòng sạch cho {b["name"]}: phải xin lỗi, hoàn {refund} xu cọc và đưa khách sang Nhà Gỗ Cô Ba.')
            d['walked'] += 1
            d['day_walked'] += 1
            walked.append(b['name'])
            if b.get('anniv'):
                _anniv_page(d, b['anniv'], day, None, None)
    d['bookings'] = ar.last(keep, 60, 'homestay.bookings', c)
    lines += _care_night(s, c)
    if d['day_synced'] or d['day_walked']:
        lines.append(f'Đơn OTA đã đồng bộ hôm nay: {d["day_synced"]}. Khách phải chuyển sang nhà hàng xóm: {d["day_walked"]}.')
    waiting = [o for o in d['ota'] if o['status'] == 'new']
    if waiting:
        lines.append(f'Còn {len(waiting)} đơn OTA chờ đồng bộ cho những ngày tới.')
    if d['safety_day'] != day and day >= 3:
        lines.append('Hôm nay chưa ký sổ kiểm tra an toàn — tổ kiểm tra phường có thể ghé bất cứ lúc nào.')
    note = kit.desk_close(s, c, ID, d['desk'], DESK, _desk_hook)
    if note:
        lines.append(note)
    nxt = today(day + 1)
    lines.append(f'Dự báo ngày mai: {nxt["emoji"]} {nxt["title"]} — {nxt["text"]}')
    d['day_synced'] = d['day_walked'] = 0
    return dict(arrived=arrived, walked=walked, moved=moved,
                dirty=[ROOM_INDEX[k]['name'] for k, r in d['rooms'].items() if r['status'] == 'dirty'], lines=lines)


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    job = t['job']
    if job == 'claim':
        e = n['entry']
        return (f'Người gọi nói: “{n["note"]}” Sổ đồ thất lạc ghi: {e["item"]} — {e["detail"]} Tìm thấy ở phòng {ROOM_INDEX[e["room"]]["name"]} '
                f'ngày {e["day"]}, khách đặt phòng: {e["booker"]}. Hỏi để xác minh trước khi giao.')
    if job == 'checkin':
        kids = f', {len(n["kids"])} bé ({", ".join(str(k) for k in n["kids"])} tuổi)' if n['kids'] else ''
        text = f'Mã đặt phòng {n["code"]} trên {n["platform"]}, tên {n["name"]}: {n["adults"]} người lớn{kids}, {n["nights"]} đêm. '
        text += f'Đã trả trước {n["paid"]} xu.' if n['paid'] else 'Thanh toán tại quầy.'
        return text + ' ' + n['note']
    if job == 'checkout':
        extra = []
        if n['laundry']:
            extra.append(f'gửi giặt {n["laundry"]} túi')
        if n['late']:
            extra.append('xin trả phòng sau 12 giờ')
        return f'Ở {n["nights"]} đêm' + (', ' + ', '.join(extra) if extra else '') + '. “' + n['claim'] + '”'
    if job == 'breakfast':
        eggs = []
        if n['eggs']['runny']:
            eggs.append(f'{n["eggs"]["runny"]} trứng ốp lòng đào')
        if n['eggs']['well']:
            eggs.append(f'{n["eggs"]["well"]} trứng ốp chín kỹ')
        parts = eggs + [f'{n["bread"]} bánh mì']
        if n['milk']:
            parts.append(f'{n["milk"]} sữa tươi')
        if n['coffee']:
            parts.append(f'{n["coffee"]} cà phê')
        text = f'Bữa sáng {n["people"]} người ({n["where"].lower()}): ' + ', '.join(parts) + '. ' + n['note']
        return text + (' ⚠️ Dị ứng trứng.' if n['allergy'] == 'egg' else '')
    if job == 'booking':
        kids = f' và {len(n["kids"])} bé ({", ".join(str(k) for k in n["kids"])} tuổi)' if n['kids'] else ''
        when = 'tối nay' if n['start'] == t['day'] else f'ngày {n["start"]}'
        return f'Nhận phòng {when}, ở {n["nights"]} đêm, {n["adults"]} người lớn{kids}. {n["note"]}'
    return n['request'] + ' Hỏi thêm vài câu để gợi ý cho đúng nhé.'


def _task(s: dict, c: dict, p: dict) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc homestay.')
    kit.need(t['known'], 'Nghe khách nói trước đã nhé (bấm “Nghe khách”).')
    if not t.get('bound', True):
        on_task(s, c, t)
    return t


DESK_FREE = ('hs_plate',)     # an egg already in the pan can always be lifted out


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'hs_desk':
        return kit.desk_choose(s, c, ID, d['desk'], DESK, p.get('option'), _desk_hook)
    if not (name in DESK_FREE or (name == 'hs_clean' and p.get('step') == 'ready')):
        kit.desk_block(d['desk'], 'Có chuyện ở quầy cần quyết trước (trứng trong chảo, cửa sổ đang mở vẫn xử lý được).')
    out = _handle(s, c, name, p)
    had = d['desk']['ev']
    kit.desk_tick(s, c, ID, d['desk'], DESK, today(c['day'])['id'])
    ev = d['desk']['ev']
    if ev is not None and had is None:
        x = kit.desk_script(DESK, ev['script'])
        out = dict(out, message=(out.get('message') or '') + f' 🔔 {x["emoji"]} {x["title"]} — ra quầy quyết giúp nhé.', surprise=True)
    return out


def _handle(s: dict, c: dict, name: str, p: dict) -> dict:
    if name == 'hs_clean':
        return _clean(s, c, p)
    if name == 'hs_repair':
        return _repair(s, c, p)
    if name == 'hs_safety':
        return _safety(s, c, p)
    if name == 'hs_sync':
        return _ota_sync(s, c, p)
    if name == 'hs_walk':
        return _ota_walk(s, c, p)
    care = dict(hs_deep=_deep, hs_fix=_fix, hs_garden=_garden, hs_wood=_wood, hs_stay=_stay_act).get(name)
    if care:
        return care(s, c, p)
    t = _task(s, c, p)
    job = t['job']
    prefix = {'hs_hold': 'booking', 'hs_release': 'booking', 'hs_book': 'booking', 'hs_decline': 'booking', 'hs_rate': 'booking', 'hs_budget': 'booking',
              'hs_verify': 'checkin', 'hs_ids': 'checkin', 'hs_count': 'checkin', 'hs_extra': 'checkin', 'hs_assign': 'checkin',
              'hs_heater': 'checkin', 'hs_welcome': 'checkin', 'hs_bank': 'checkin', 'hs_relocate': 'checkin', 'hs_diet': 'breakfast', 'hs_quiz': 'claim', 'hs_claim': 'claim',
              'hs_inspect': 'checkout', 'hs_return': 'checkout', 'hs_line': 'checkout', 'hs_settle': 'checkout',
              'hs_egg': 'breakfast', 'hs_plate': 'breakfast', 'hs_bread': 'breakfast', 'hs_milk': 'breakfast', 'hs_coffee': 'breakfast',
              'hs_serve': 'breakfast', 'hs_toss': 'breakfast',
              'hs_probe': 'recommend', 'hs_pick': 'recommend', 'hs_advise': 'recommend'}.get(name)
    if prefix is None:
        raise kit.eng().GameError('Thao tác homestay không hợp lệ.')
    kit.need(prefix == job, f'Thao tác này dành cho việc “{JOB_NAMES[prefix]}”, không phải “{JOB_NAMES[job]}”.')
    return dict(booking=_booking, checkin=_checkin, checkout=_checkout, breakfast=_breakfast, recommend=_recommend, claim=_claim)[job](s, c, t, name, p)


# ---------------------------------------------------------------- v0.5: safety log, app orders, lost-and-found calls
def _safety(s: dict, c: dict, p: dict) -> dict:
    d = _data(c)
    kit.need(d['safety_day'] != c['day'], 'Hôm nay đã kiểm tra an toàn rồi.')
    d['safety_day'] = c['day']
    kit.metric(c, 'hs_safety')
    return dict(message=f'Đã bấm thử chuông báo khói, xem kim bình chữa cháy, khóa van gas tổng, dọn lối thoát hiểm; ký sổ an toàn ngày {c["day"]}.')


def _desk_hook(s: dict, c: dict, key: str, v) -> str | None:
    d = _data(c)
    if key == 'safety':
        d['safety_day'] = c['day']
        return 'Chuông báo khói kêu to, bình chữa cháy đủ áp — ký sổ an toàn.'
    if key == 'inspect':
        if d['safety_day'] == c['day']:
            c['xp'] += 10
            return 'Sổ khai báo lưu trú và sổ an toàn hôm nay đầy đủ — đạt.'
        fine = min(15, c['money'])
        if fine:
            kit.money(s, c, -fine, 'Phạt thiếu sổ kiểm tra an toàn', None, 'event_cost')
        return f'Hôm nay chưa kiểm tra an toàn — bị nhắc nhở, phạt {fine} xu.'
    return None


def _ota_score(c: dict) -> float:
    """What the apps show: the average of the latest reviews of the house."""
    stars = [p['stars'] for p in c.get('feed', []) if p.get('kind') == 'review' and type(p.get('stars')) is int][:12]
    return round(sum(stars) / len(stars), 1) if stars else 4.6


def _pending_overlap(d: dict, rid: str, start: int, nights: int) -> bool:
    return any(o['status'] == 'new' and o['room'] == rid and _overlap(o['start'], o['nights'], start, nights) for o in d['ota'])


def _ota_new(s: dict, c: dict, mod: str) -> None:
    """Morning inbox: the apps already sold these rooms without looking at the house calendar."""
    d = _data(c)
    day = c['day']
    tier = kit.tier(day)
    n = (OTA_COUNT[tier] + (1 if mod in ('festival', 'weekend') else 0) - (1 if mod == 'low' else 0) - (1 if _ota_score(c) < 3.5 else 0)
         + (1 if _featured(c) else 0))
    warn = d['desk']['marks'].get('ota_warn')
    if warn is not None and day - warn <= 2:
        n -= 1
    r = kit.rng(ID, 'ota', day)
    names = list(OTA_NAMES)
    r.shuffle(names)
    rooms = [x['id'] for x in ROOMS if x['unlock'] <= kit.level(c)]
    made = 0
    for i in range(max(0, min(3, n))):
        conflict = r.random() < OTA_CONFLICT[tier]
        start = day + r.choice((0, 1, 1, 2, 3))
        nights = r.choice((1, 1, 2, 2, 3))
        order = list(rooms)
        r.shuffle(order)
        busy = [rid for rid in order if _blocked(c, rid, start, nights) or _pending_overlap(d, rid, start, nights)]
        free = [rid for rid in order if rid not in busy]
        pick = busy[0] if busy and (conflict or not free) else free[0] if free else None
        if pick is None:
            continue
        guests = max(1, min(ROOM_INDEX[pick]['cap'], r.choice((1, 2, 2, 2, 3, 4))))
        pct = RATE_INDEX['peak']['pct'] if mod == 'festival' else 100
        gross = -(-kit.price(c, pick, SPEC['prices'][pick]) * nights * pct // 100)
        net = gross - -(-gross * OTA_COMMISSION // 100)
        d['seq'] += 1
        d['ota'].append(dict(id=f'ota-{d["seq"]}', ota=OTAS[r.randrange(len(OTAS))], name=names[i % len(names)], room=pick, start=start,
                             nights=nights, guests=guests, total=gross, net=net, status='new', rooms=[], day=day))
        made += 1
    d['ota'] = ar.last([o for o in d['ota'] if o['status'] == 'new' or o['day'] >= day - 2], 30, 'homestay.ota', c)
    if made:
        kit.log(s, c, 'homestay', f'📥 {made} đơn OTA mới trong hộp thư — đồng bộ vào lịch trước khi khách tới.')


def _ota_find(d: dict, oid) -> dict:
    o = next((o for o in d['ota'] if o['id'] == oid), None) if isinstance(oid, str) else None
    kit.need(o, 'Không có đơn OTA này.')
    return o


def _ota_fits(c: dict, o: dict) -> bool:
    for rooms in _combos(c):
        if sum(ROOM_INDEX[r]['cap'] for r in rooms) >= o['guests'] and all(_blocked(c, r, o['start'], o['nights']) is None for r in rooms):
            return True
    return False


def _ota_book(c: dict, o: dict, rooms: list, status: str) -> None:
    d = _data(c)
    d['bookings'].append(dict(id=o['id'], rooms=list(rooms), start=o['start'], nights=o['nights'], guests=o['guests'],
                              name=f'{o["name"]} ({o["ota"]})', total=o['net'], deposit=0, task=None, ota=o['ota']))
    d['bookings'] = ar.last(d['bookings'], 60, 'homestay.bookings', c)
    o.update(status=status, rooms=list(rooms))


def _ota_walk_apply(s: dict, c: dict, o: dict, arranged: bool) -> int:
    d = _data(c)
    fee = min(WALK_FEE, c['money'])
    if fee:
        kit.money(s, c, -fee, f'Chuyển khách {o["ota"]} sang Nhà Gỗ Cô Ba · {o["name"]}', o['id'], category='refund')
    o['status'] = 'walked'
    d['walked'] += 1
    d['ota_walked'] += 1
    d['day_walked'] += 1
    d['desk']['marks']['ota_walk'] = c['day']
    if not arranged:
        kit.review(s, c, kit.npc_id(ID, 8), 1, 'Tới nơi mới biết phòng đã có người, bị chuyển sang nhà khác lúc tối muộn.', o['id'])
    return fee


def _ota_sync(s: dict, c: dict, p: dict) -> dict:
    d = _data(c)
    o = _ota_find(d, p.get('order'))
    kit.need(o['status'] == 'new', 'Đơn này đã xử lý rồi.')
    rooms = kit.id_list(p.get('rooms'), ROOM_INDEX, 2, 'Chọn 1–2 phòng trong lịch.')
    kit.need(rooms, 'Chọn ít nhất một phòng.')
    for rid in rooms:
        why = _blocked(c, rid, o['start'], o['nights'])
        kit.need(why is None, (why or '') + ' Chọn phòng khác, hoặc chuyển khách sang nhà hàng xóm.')
    cap = sum(ROOM_INDEX[r]['cap'] for r in rooms)
    kit.need(cap >= o['guests'], f'{len(rooms)} phòng chỉ ngủ được {cap} người, đơn có {o["guests"]} khách.')
    want = kit.price(c, o['room'], SPEC['prices'][o['room']])
    got = sum(kit.price(c, r, SPEC['prices'][r]) for r in rooms)
    _ota_book(c, o, rooms, 'synced')
    d['synced'] += 1
    d['day_synced'] += 1
    kit.metric(c, 'ota_synced')
    names = ' + '.join(ROOM_INDEX[r]['name'] for r in rooms)
    if rooms == [o['room']]:
        return dict(message=f'Đã đồng bộ đơn của {o["name"]} vào phòng {names}. Hai kênh cùng khóa phòng, không lo bán trùng.', celebrate=True)
    if got < want:
        refund = min(math.ceil((want - got) * o['nights'] * (100 - OTA_COMMISSION) / 100), c['money'])
        if refund:
            kit.money(s, c, -refund, f'Hoàn chênh lệch đổi phòng · {o["name"]}', o['id'], category='refund')
        return dict(message=f'Xếp {o["name"]} sang {names} (rẻ hơn phòng đã đặt): nhắn xin lỗi qua {o["ota"]}, hoàn chênh {refund} xu.')
    return dict(message=f'Xếp {o["name"]} sang {names} — nâng hạng miễn phí. Nhắn trước qua {o["ota"]} để khách yên tâm.', celebrate=True)


def _ota_walk(s: dict, c: dict, p: dict) -> dict:
    kit.confirm(p, 'Xác nhận chuyển khách sang Nhà Gỗ Cô Ba và trả phần chênh.')
    d = _data(c)
    o = _ota_find(d, p.get('order'))
    kit.need(o['status'] == 'new', 'Đơn này đã xử lý rồi.')
    could = _ota_fits(c, o)
    fee = _ota_walk_apply(s, c, o, arranged=True)
    if could:
        d['strikes'] += 1
    return dict(message=f'Đã gọi Cô Ba giữ phòng, trả {fee} xu chênh lệch và taxi, nhắn {o["ota"]} hủy đơn miễn phí cho {o["name"]}.'
                        + (' (Thật ra lịch vẫn còn phòng đủ chỗ…)' if could else ''))


def _ota_close(s: dict, c: dict) -> list:
    """Orders nobody synced: the guests arrive anyway — fine if the room was free, a walk if it was sold twice."""
    d = _data(c)
    day = c['day']
    lines = []
    for o in d['ota']:
        if o['status'] != 'new' or o['start'] > day:
            continue
        rid = o['room']
        if ROOM_INDEX[rid]['unlock'] <= kit.level(c) and _blocked(c, rid, o['start'], o['nights']) is None and ROOM_INDEX[rid]['cap'] >= o['guests']:
            _ota_book(c, o, [rid], 'auto')
            lines.append(f'Đơn {o["ota"]} của {o["name"]} chưa đồng bộ, may mà phòng {ROOM_INDEX[rid]["name"]} vẫn trống.')
        else:
            fee = _ota_walk_apply(s, c, o, arranged=False)
            d['strikes'] += 1
            lines.append(f'Đơn {o["ota"]} của {o["name"]} chưa đồng bộ và trùng phòng {ROOM_INDEX[rid]["name"]}: khách tới nơi phải chuyển sang Nhà Gỗ Cô Ba (−{fee} xu, 1★).')
    return lines


def _claim(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n, x = t['needs'], t['_x']
    e = n['entry']
    if name == 'hs_quiz':
        q = kit.one_of(p.get('q'), CLAIM_Q_IDS, 'Câu hỏi không có trong sổ.')
        kit.need(q not in t['asked'], 'Đã hỏi câu này rồi.')
        t['asked'].append(q)
        kit.start_work(t)
        return dict(message=f'Người gọi: “{x["say"][q]}”')
    kit.confirm(p, 'Xác nhận cách xử lý món đồ.')
    choice = kit.one_of(p.get('choice'), CLAIM_CHOICES, 'Chọn giao đồ, xác minh qua kênh đặt phòng hoặc từ chối.')
    kind = x['kind']
    right = choice in CLAIM_RIGHT[kind]
    t['choice'] = choice
    if not right:
        t['mistakes'] += 1
    if choice == 'give' and 'describe' not in t['asked']:
        t['mistakes'] += 1
    d = _data(c)
    d['seq'] += 1
    back = choice == 'give' or (choice == 'channel' and kind != 'imposter')
    d['lost'] = ar.last(d['lost'] + [dict(id=f'lf-{d["seq"]}', item=e['item'], room=e['room'], day=e['day'], status='returned' if back else 'kept')], 40, 'homestay.lost', c)
    if choice == 'give' and kind == 'imposter':
        d['claims_bad'] += 1
        d['desk']['marks']['lost_wrong'] = c['day']
    elif right:
        d['claims_ok'] += 1
    kit.metric(c, 'claims')
    text = {('give', 'owner'): 'Gói kỹ, gửi chuyển phát tới địa chỉ khách xác nhận. Chủ đồ mừng rỡ!',
            ('give', 'imposter'): 'Đã giao đồ… Tối đó chủ thật nhắn hỏi đúng món đồ ấy — người vừa nhận không phải chủ!',
            ('give', 'friend'): 'Bạn đi cùng nhận giúp. Lần này ổn, nhưng chưa ai hỏi lại người đặt phòng.',
            ('channel', 'owner'): 'Nhắn qua kênh đặt phòng: khách xác nhận ngay, mai gửi đồ. Chắc chắn, chỉ chậm một chút.',
            ('channel', 'imposter'): 'Nhắn qua kênh đặt phòng: chủ thật trả lời “tôi không nhờ ai cả!”. Đồ vẫn nằm yên trong tủ khóa.',
            ('channel', 'friend'): 'Nhắn qua kênh đặt phòng: người đặt phòng xác nhận có nhờ bạn lấy giúp. Giao đồ kèm biên nhận.',
            ('deny', 'owner'): 'Từ chối giao… nhưng người gọi chính là chủ đồ, đành mất công gọi lại.',
            ('deny', 'imposter'): 'Từ chối lịch sự: chỉ giao khi người đặt phòng xác nhận. Người gọi cúp máy luôn.',
            ('deny', 'friend'): 'Từ chối giao. Người đặt phòng phải tự gọi lại để nhờ lần nữa.'}[(choice, kind)]
    if choice == 'give' and kind == 'imposter':
        cq.slip(t, 'wrong_person', 3, f'{e["item"]} của mình để quên mà homestay giao cho người lạ gọi tới, không hỏi lại mình một câu.',
                'giao đồ thất lạc cho người lạ')
    elif choice == 'give' and kind == 'friend':
        cq.slip(t, 'unconfirmed', 1, 'Bạn mình tới lấy hộ mà homestay chẳng hỏi lại mình, lỡ là người khác thì sao.', 'giao đồ khi chưa xác nhận')
    elif choice == 'deny' and kind == 'owner':
        cq.slip(t, 'denied_owner', 2, 'Mình là chủ món đồ, tả đúng hết mà vẫn bị từ chối, phải gọi lại lần nữa.', 'từ chối cả chủ thật')
    note = _settle_free(s, c, t)
    kit.complete(s, c, t, 0, f'Bạn đã xử lý cuộc gọi hỏi {e["item"].lower()}.')
    return dict(message=text + (' ' + note if note else ''), celebrate=right)


# ---------------------------------------------------------------- housekeeping
def _clean(s: dict, c: dict, p: dict) -> dict:
    d = kit.data(c)
    rid = kit.one_of(p.get('room'), ROOM_INDEX, 'Phòng không tồn tại.')
    step = kit.one_of(p.get('step'), HK_INDEX, 'Bước dọn phòng không tồn tại.')
    r = d['rooms'][rid]
    kit.need(r['status'] == 'dirty', f'Phòng {ROOM_INDEX[rid]["name"]} không cần dọn lúc này.')
    hk = r['hk']
    if step == 'strip':
        kit.need(hk is None, 'Đã tháo ga phòng này rồi.')
        r['hk'] = dict(done=['strip'], start=round(kit.now(), 3), slips=0, cost=0)
        kit.metric(c, 'hk_steps')
        lim = _air(c)
        return dict(message=f'Mở toang cửa sổ cho thoáng, gom ga gối và khăn bẩn đi giặt. Cửa sổ nên mở {lim["damp"]}–{lim["cold"]} giây.')
    kit.need(hk, 'Mở cửa sổ và tháo ga gối trước đã.')
    kit.need(step not in hk['done'], 'Bước này đã làm rồi.')
    if step == 'ready':
        kit.need(all(x in hk['done'] for x in MIDDLE), 'Còn bước chưa làm, chưa thể báo phòng sạch.')
        air = max(0.0, kit.now() - hk['start'])
        lim = _air(c)
        worn = 2 if r['wear'] < WEAR_BAD else 1 if r['wear'] < WEAR_LOW else 0
        q = 5 - hk['slips'] - (1 if air < lim['damp'] else 0) - (1 if air > lim['cold'] else 0) - worn - (1 if r['snag'] else 0)
        r.update(status='clean', q=max(1, q), hk=None, mini=0, note=None)
        d['cleaned'] += 1
        kit.metric(c, 'rooms_cleaned')
        air_note = ('phòng còn mùi ẩm vì mở cửa sổ quá ngắn' if air < lim['damp'] else
                    'phòng hơi lạnh vì mở cửa sổ quá lâu' if air > lim['cold'] else 'phòng thơm mùi gỗ thông')
        care = (' Rèm bụi, góc tường ẩm lâu ngày — nên tổng vệ sinh.' if worn else '') + (f' Còn “{r["snag"].lower()}” chưa sửa.' if r['snag'] else '')
        return dict(message=f'Phòng {ROOM_INDEX[rid]["name"]} sạch: {air_note} ({air:.0f} giây).{care} Điểm buồng phòng {max(1, q)}/5.', celebrate=q >= 5)
    msgs = []
    rank = MIDDLE.index(step)
    for earlier in MIDDLE[:rank]:
        if earlier not in hk['done']:
            hk['slips'] += 1
            msgs.append(SLIP_TEXT.get((step, earlier), 'Làm sai thứ tự nên phải làm lại một phần.'))
            if (step, earlier) == ('amenity', 'bath'):
                kit.need(kit.stock(c, 'soap_kit') >= 2, 'Cần 2 bộ tắm (một bộ sẽ bị ướt).')
                wasted = kit.take(c, 'soap_kit', 1)
                kit.waste(c, 'soap_kit', 1, wasted, 'Bộ tắm bị ướt do dọn sai thứ tự')
            break
    use = dict(HK_INDEX[step]['use'])
    if step == 'amenity' and r['mini']:
        use['noodles'] = r['mini']
    for item, q in use.items():
        kit.need(kit.stock(c, item) >= q, f'Thiếu {ITEM_INDEX[item]["name"]} (cần {q}). Mở Kho để nhập thêm.')
    for item, q in use.items():
        hk['cost'] += kit.take(c, item, q)
    hk['done'].append(step)
    kit.metric(c, 'hk_steps')
    base = {'bath': 'Cọ bồn cầu, lavabo, lau gương, thay giấy vệ sinh.', 'bed': 'Trải ga mới căng phẳng, bọc gối, gấp chăn kiểu khách sạn.',
            'amenity': '2 khăn tắm, 1 bộ dầu gội, 2 chai nước tặng, 2 gói cà phê' + (f', thêm {r["mini"]} ly mì vào minibar.' if r['mini'] else '.'),
            'inspect': 'Soi gầm giường, ngăn kéo, ổ điện, rèm, cốc chén.'}[step]
    if step == 'inspect':
        idx = [x['id'] for x in ROOMS].index(rid)
        if (c['day'] * 7 + idx * 3 + d['cleaned']) % 4 == 0:
            item = FOUND_ITEMS[(c['day'] + idx + d['cleaned']) % len(FOUND_ITEMS)]
            d['seq'] += 1
            d['lost'] = ar.last(d['lost'] + [dict(id=f'lf-{d["seq"]}', item=item, room=rid, day=c['day'], status='kept')], 40, 'homestay.lost', c)
            kit.metric(c, 'lost_found')
            base += f' Tìm thấy “{item}” — ghi sổ đồ thất lạc, cất tủ khóa, chờ liên hệ khách qua kênh đặt phòng.'
    return dict(message=' '.join(msgs + [base]))


def _repair(s: dict, c: dict, p: dict) -> dict:
    d = kit.data(c)
    rid = kit.one_of(p.get('room'), ROOM_INDEX, 'Phòng không tồn tại.')
    r = d['rooms'][rid]
    kit.need(r['status'] == 'maintenance', 'Phòng này không cần sửa.')
    info = ROOM_INDEX[rid]
    kit.need(info['unlock'] <= kit.level(c), f'Sửa phòng {info["name"]} khi đạt cấp {info["unlock"]} nhé.')
    kit.confirm(p, 'Xác nhận gọi thợ và trả tiền sửa.')
    cost = RENOVATION_COST if info['unlock'] > 1 and (r['note'] or '').startswith('Đang sửa ban công') else REPAIR_COST
    kit.money(s, c, -cost, f'Thợ sửa phòng {info["name"]}', rid, category='repair')
    r.update(status='dirty', note=None, hk=None, snag=None)
    kit.metric(c, 'repairs')
    return dict(message=f'Thợ đã sửa xong phòng {info["name"]} (−{cost} xu). Bụi sửa chữa còn đầy, cần dọn lại trước khi đón khách.')


# ---------------------------------------------------------------- booking
def _booking(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n = t['needs']
    need = _counted(n['adults'], n['kids'])
    if name == 'hs_hold':
        kit.need(n['start'] >= c['day'], 'Ngày khách hỏi đã qua. Khách đã tìm chỗ khác — hãy báo lại lịch sự.')
        rooms = kit.id_list(p.get('rooms'), ROOM_INDEX, 2, 'Chọn 1–2 phòng trong lịch.')
        kit.need(rooms, 'Chọn ít nhất một phòng.')
        for rid in rooms:
            why = _blocked(c, rid, n['start'], n['nights'])
            kit.need(why is None, (why or '') + ' Chọn phòng khác để không bị trùng lịch.')
        cap = sum(ROOM_INDEX[r]['cap'] for r in rooms)
        kit.need(cap >= need, f'{len(rooms)} phòng chỉ ngủ được {cap} người, khách có {need} người tính chỗ (bé dưới {KID_FREE_AGE} tuổi ngủ chung không tính).')
        rate = kit.one_of(p.get('rate', t.get('rate') or 'std'), RATE_IDS, 'Mức giá không hợp lệ.') if t.get('gen') else 'std'
        t['hold'] = rooms
        t['quote'] = _quote(c, rooms, n['nights'], rate)
        if t.get('gen'):
            t['rate'] = rate
        kit.start_work(t)
        total = t['quote']['total']
        label = f' ({RATE_INDEX[rate]["name"].lower()})' if t.get('gen') else ''
        return dict(message=f'Đã giữ chỗ {", ".join(ROOM_INDEX[r]["name"] for r in rooms)}: {n["nights"]} đêm = {total} xu{label}, cọc {DEPOSIT_PCT}% = {t["quote"]["deposit"]} xu.')
    if name == 'hs_rate':
        kit.need(t.get('gen'), 'Việc này tính theo giá niêm yết.')
        kit.need(t['hold'] and t['quote'], 'Giữ phòng trên lịch trước rồi mới báo giá.')
        rate = kit.one_of(p.get('rate'), RATE_IDS, 'Mức giá không hợp lệ.')
        kit.need(rate != t['rate'], 'Đang báo mức giá này rồi.')
        t['rate'] = rate
        t['quote'] = _quote(c, t['hold'], n['nights'], rate)
        return dict(message=f'Báo {RATE_INDEX[rate]["name"].lower()}: {t["quote"]["total"]} xu, cọc {t["quote"]["deposit"]} xu.')
    if name == 'hs_budget':
        kit.need(t.get('gen'), 'Khách đã nói rõ trong tin nhắn.')
        kit.need(not t['asked_budget'], 'Đã hỏi ngân sách rồi.')
        t['asked_budget'] = True
        kit.start_work(t)
        return dict(message=f'Khách: “{t["_x"]["say"]}”')
    if name == 'hs_release':
        kit.need(t['hold'], 'Chưa giữ phòng nào.')
        t['hold'] = []
        t['quote'] = None
        return dict(message='Đã bỏ giữ chỗ. Chọn lại phòng khác nhé.')
    if name == 'hs_book':
        kit.confirm(p, 'Xác nhận nhận cọc và gửi tin xác nhận đặt phòng.')
        kit.need(t['hold'] and t['quote'], 'Giữ phòng trên lịch trước khi nhận cọc.')
        kit.need(n['start'] >= c['day'], 'Ngày khách hỏi đã qua.')
        for rid in t['hold']:
            why = _blocked(c, rid, n['start'], n['nights'])
            kit.need(why is None, (why or '') + ' Bỏ giữ và chọn lại nhé.')
        if t.get('gen') and RATE_IDS.index(t['rate']) > _cap(t):
            say = PUSHBACK[t['_x']['budget']]
            t['haggles'] += 1
            t['patience'] = max(25, t['patience'] - 10)
            kit.log(s, c, 'refused', f'Khách chê giá: {say}', t['npc'], t['id'])
            return dict(message=f'Khách: “{say}” Báo lại mức giá khác nhé.', refused=True)
        if not n['stairs_ok'] and any(ROOM_INDEX[r]['stairs'] for r in t['hold']):
            t['mistakes'] += 1
        _booking_slips(c, t)
        dep = t['quote']['deposit']
        # The guest reads the confirmation: a discount comes off the deposit and off the stay, never twice.
        said = cq.react(s, c, t, dep, who=_guest(t))
        cut = dep - said['pay']
        d = kit.data(c)
        d['seq'] += 1
        d['bookings'].append(dict(id=f'bk-{d["seq"]}', rooms=list(t['hold']), start=n['start'], nights=n['nights'], guests=need,
                                  name=_guest(t), total=t['quote']['total'] - cut, deposit=dep - cut, task=t['id']))
        d['bookings'] = ar.last(d['bookings'], 60, 'homestay.bookings', c)
        kit.metric(c, 'bookings')
        kit.complete(s, c, t, said['pay'], f'Bạn đã nhận đặt phòng cho {_guest(t)} từ ngày {n["start"]}.')
        if said['message']:
            return dict(message=f'Đã nhận cọc {said["pay"]} xu và gửi xác nhận kèm nội quy. Lịch đã ghi. {said["message"]}')
        return dict(message=f'Đã nhận cọc {dep} xu và gửi xác nhận kèm nội quy (nhận phòng 14h, trả phòng 12h). Lịch đã ghi.', celebrate=True)
    # hs_decline
    kit.confirm(p, 'Xác nhận báo khách hết phòng và giới thiệu Nhà Gỗ Cô Ba.')
    feasible = _can_book(c, n)
    t['decline_ok'] = not feasible
    t['hold'] = []
    t['quote'] = None
    note = ''
    if feasible:
        t['mistakes'] += 1
        cq.slip(t, 'said_full', 2, 'Nhà còn phòng hợp mà lại báo hết phòng, mình phải đi tìm chỗ khác.', 'còn phòng mà báo hết')
        note = _settle_free(s, c, t)
    kit.complete(s, c, t, 0, f'Bạn đã báo {_guest(t)} hết phòng phù hợp và giới thiệu homestay hàng xóm.', status='referred')
    return dict(message='Đã giới thiệu khách sang Nhà Gỗ Cô Ba.' + ('' if not feasible else ' (Thật ra lịch vẫn còn chỗ phù hợp…)')
                + (' ' + note if note else ''))


def _booking_slips(c: dict, t: dict) -> None:
    n = t['needs']
    if not n['stairs_ok'] and any(ROOM_INDEX[r]['stairs'] for r in t['hold']):
        cq.slip(t, 'stairs', 2, 'Đã dặn đừng xếp phòng phải leo cầu thang mà vẫn xếp phòng trên lầu.', 'phải leo cầu thang dù đã dặn')
    if n['prefer'] and not any(r in n['prefer'] for r in t['hold']):
        # Only when a room they asked for was really free on those nights.
        free = [r for r in n['prefer'] if _blocked(c, r, n['start'], n['nights']) is None]
        if free and n['prefer'] == ['suong']:
            cq.slip(t, 'wish', 1, 'Mình xin phòng rẻ nhất mà lại được xếp phòng đắt hơn, dù phòng rẻ còn trống.', 'không xếp phòng khách xin')
        elif free:
            names = ' hoặc '.join(ROOM_INDEX[r]['name'] for r in n['prefer'])
            cq.slip(t, 'wish', 1, f'Mình xin phòng {names} mà lại được xếp phòng khác, dù phòng đó còn trống.', 'không xếp phòng khách xin')


# ---------------------------------------------------------------- check-in
def _checkin(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n, x, ci = t['needs'], t['_x'], t['ci']
    booked = _counted(n['adults'], n['kids'])
    arrived = _counted(x['adults'], x['kids'])
    if name == 'hs_verify':
        kit.need(not ci['verified'], 'Đã khớp mã đặt phòng rồi.')
        entry = kit.one_of(p.get('entry'), [e['id'] for e in n['list']], 'Chọn một dòng đặt phòng trên app.')
        kit.start_work(t)
        if entry != x['match']:
            t['mistakes'] += 1
            _oops(ci, 'entry')
            row = next(e for e in n['list'] if e['id'] == entry)
            why = 'sai ngày nhận phòng' if row['start'] != t['day'] else 'sai mã hoặc sai tên'
            return dict(message=f'Không khớp: dòng {entry} {why}. So lại mã {n["code"]} và ngày hôm nay.', refused=True)
        ci['verified'] = True
        return dict(message=f'Khớp đặt phòng {n["code"]}: {n["nights"]} đêm, phòng {n["size"]} người, giá {n["rate"]} xu/đêm.')
    if name == 'hs_ids':
        kit.need(ci['verified'], 'Khớp mã đặt phòng trước đã.')
        mode = kit.one_of(p.get('mode', 'look'), ('look', 'photo'), 'Cách kiểm giấy tờ không hợp lệ.')
        if mode == 'photo':
            t['mistakes'] += 1
            _oops(ci, 'photo')
            return dict(message='Không chụp hay lưu giấy tờ của khách vào điện thoại. Chỉ xem để khai báo lưu trú, rồi trả lại ngay.', refused=True)
        kit.need(not ci['ids'], 'Đã xem giấy tờ rồi.')
        ci['ids'] = True
        text = ('Có ứng dụng định danh điện tử hợp lệ thay cho thẻ giấy.' if x['id'] == 'app' else 'Người lớn đều có giấy tờ tùy thân.')
        return dict(message=text + ' Đã khai báo lưu trú. Không ghi lại số giấy tờ vào sổ hay máy của homestay.')
    if name == 'hs_count':
        kit.need(ci['verified'], 'Khớp mã đặt phòng trước đã.')
        kit.need(not ci['counted'], 'Đã đếm khách rồi.')
        ci['counted'] = True
        kids = f', {len(x["kids"])} bé ({", ".join(str(k) for k in x["kids"])} tuổi)' if x['kids'] else ''
        extra = arrived - booked
        if extra <= 0:
            ci['extra'] = 'none'
        msg = f'Có mặt: {x["adults"]} người lớn{kids} → {arrived} người tính chỗ (đặt {booked}).'
        return dict(message=msg + (f' Dư {extra} người so với đặt phòng — cần báo phụ thu hoặc từ chối.' if extra > 0 else ' Khớp với đặt phòng.'))
    if name == 'hs_extra':
        kit.need(ci['counted'], 'Đếm khách trước đã.')
        kit.need(arrived > booked, 'Số khách khớp đặt phòng, không cần phụ thu.')
        choice = kit.one_of(p.get('choice'), ('surcharge', 'refuse'), 'Chọn phụ thu hoặc từ chối.')
        ci['extra'] = choice
        ci['could_fit'] = _can_fit_now(c, arrived, n['nights'])
        ci['rooms'] = []
        if choice == 'surcharge':
            return dict(message=f'Khách đồng ý phụ thu {EXTRA_GUEST} xu/người/đêm kèm nệm phụ. Nhớ chọn phòng đủ chỗ cho {arrived} người.')
        return dict(message=f'Đã giải thích nội quy: phòng chỉ nhận đúng số người đặt ({booked}). Người đi cùng cần tìm chỗ khác.')
    if name == 'hs_assign':
        kit.need(ci['counted'] and ci['extra'], 'Đếm khách và chốt số người ở trước khi giao phòng.')
        rooms = kit.id_list(p.get('rooms'), ROOM_INDEX, 2, 'Chọn 1–2 phòng.')
        kit.need(rooms, 'Chọn ít nhất một phòng.')
        for rid in rooms:
            # A room still waiting for housekeeping can be handed over — the guest will notice.
            why = _blocked(c, rid, c['day'], n['nights'])
            kit.need(why is None, why or '')
        staying = booked if ci['extra'] == 'refuse' else arrived
        cap = sum(ROOM_INDEX[r]['cap'] for r in rooms)
        kit.need(cap >= staying, f'Phòng chỉ đủ {cap} người, cần chỗ cho {staying} người. Vượt sức chứa là không an toàn.')
        ci['rooms'] = rooms
        d = kit.data(c)
        if any(d['rooms'][r]['status'] == 'dirty' for r in rooms):
            return dict(message=f'Giao phòng {", ".join(ROOM_INDEX[r]["name"] for r in rooms)} cho {n["nights"]} đêm. Phòng này chưa dọn xong đâu nhé.')
        return dict(message=f'Giao phòng {", ".join(ROOM_INDEX[r]["name"] for r in rooms)} cho {n["nights"]} đêm.')
    if name == 'hs_heater':
        kit.need(n['cold'], 'Đêm nay không lạnh, không cần máy sưởi.')
        kit.need(ci['rooms'], 'Giao phòng trước rồi mới chuẩn bị máy sưởi.')
        kit.need(not ci['heater'], 'Đã lắp bình gas máy sưởi rồi.')
        ci['cost'] += kit.take(c, 'heater_gas', len(ci['rooms']))
        ci['heater'] = True
        return dict(message='Đã lắp bình gas mới, thử đánh lửa, mở hé cửa thông gió và dặn khách không phơi đồ lên máy sưởi.')
    if name == 'hs_bank':
        kit.need(t.get('gen') and n.get('proof') == 'bank', 'Khoản này trả qua app đặt phòng, không cần đối chiếu ngân hàng.')
        kit.need(t['bank'] is None, 'Đã đối chiếu sao kê rồi.')
        kit.start_work(t)
        if x['received']:
            t['bank'] = 'ok'
            return dict(message=f'Sao kê có khoản {n["paid"]} xu ghi mã {n["code"]} — đã nhận đủ cọc.')
        t['bank'] = 'missing'
        return dict(message=f'Sao kê không có khoản {n["paid"]} xu nào mang mã {n["code"]}. Soi lại ảnh: số tài khoản nhận bị gõ nhầm hai số cuối. '
                            'Khách hốt hoảng gọi ngân hàng, xin trả đủ tại quầy.')
    if name == 'hs_relocate':
        # A confirmed guest with nowhere to sleep: apologise, pay the neighbour's difference + taxi, refund what was paid here.
        kit.confirm(p, 'Xác nhận xin lỗi khách và chuyển sang Nhà Gỗ Cô Ba.')
        kit.need(ci['verified'], 'Khớp mã đặt phòng trước đã.')
        kit.need(ci['counted'] and ci['extra'], 'Đếm khách và chốt số người ở trước đã.')
        staying = booked if ci['extra'] == 'refuse' else arrived
        seat = _could_seat(c, staying, n['nights'])
        if seat:
            t['mistakes'] += 1
            return dict(message=f'Khoan đã: {seat} vẫn nhận được {staying} người suốt {n["nights"]} đêm (xong trả phòng, dọn lại là giao được). '
                                'Khách đã đặt thì ưu tiên giữ ở nhà mình.', refused=True)
        credit = 0 if t.get('bank') == 'missing' else n['paid']
        fee = min(WALK_FEE + credit, c['money'])
        if fee:
            kit.money(s, c, -fee, f'Chuyển {_guest(t)} sang Nhà Gỗ Cô Ba (hoàn cọc + chênh lệch, taxi)', t['id'], category='refund')
        d = _data(c)
        d['walked'] += 1
        d['day_walked'] += 1
        ci['rooms'] = []
        kit.complete(s, c, t, 0, f'Bạn đã xin lỗi {_guest(t)} vì hết phòng và chuyển khách sang Nhà Gỗ Cô Ba.', status='referred')
        return dict(message=f'Gọi Cô Ba giữ phòng, hoàn {credit} xu cọc, trả {WALK_FEE} xu chênh lệch và taxi. '
                            'Lần sau nhớ chừa phòng cho khách sắp đến trước khi nhận đơn mới.')
    # hs_welcome
    kit.confirm(p, 'Xác nhận trao chìa khóa và thu tiền.')
    kit.need(ci['verified'] and ci['ids'] and ci['counted'] and ci['extra'] and ci['rooms'], 'Còn bước nhận phòng chưa xong.')
    for rid in ci['rooms']:
        why = _blocked(c, rid, c['day'], n['nights'])
        kit.need(why is None, (why or '') + ' Chọn lại phòng.')
    extra = max(0, arrived - booked) if ci['extra'] == 'surcharge' else 0
    lost = _lost_deposit(t)
    credit = 0 if t.get('bank') == 'missing' else n['paid']
    due = n['rate'] * n['nights'] - credit + EXTRA_GUEST * extra * n['nights']
    d = _data(c)
    if lost:
        t['mistakes'] += 1
        d['lost_deposit'] += n['paid']
    dirty = [r for r in ci['rooms'] if d['rooms'][r]['status'] == 'dirty']
    ci['q'] = 1 if dirty else min(d['rooms'][r]['q'] for r in ci['rooms'])
    _checkin_slips(t, dirty)
    _regular(c, t)
    # The deposit was paid earlier; only tonight's balance is at stake at the counter.
    said = cq.react(s, c, t, due, who=_guest(t))
    ci['paid'] = said['pay']
    if said['kind'] == 'walkout':
        # Too much went wrong: the guest takes the deposit back and leaves for another house.
        back = min(0 if lost else credit, c['money'])      # a deposit that never arrived is not paid back
        if back:
            kit.money(s, c, -back, f'Hoàn cọc, khách bỏ đi · {_guest(t)}', t['id'], category='refund')
        kit.metric(c, 'checkins')
        kit.complete(s, c, t, 0, f'{_guest(t)} không nhận phòng và bỏ sang nhà khác.')
        return dict(message=f'{said["message"]} Khách lấy lại {back} xu cọc rồi kéo vali đi.', refused=True)
    for rid in ci['rooms']:
        d['rooms'][rid].update(status='occupied', guest=_guest(t), task=None, until=c['day'] + n['nights'], hk=None)
        _stay_open(c, rid, _guest(t), _npc_index(t))
    d['nights_sold'] += n['nights'] * len(ci['rooms'])
    kit.metric(c, 'checkins')
    kit.complete(s, c, t, said['pay'], f'Bạn đã đón {_guest(t)} nhận phòng {", ".join(ROOM_INDEX[r]["name"] for r in ci["rooms"])}.')
    return dict(message=f'Đã trao chìa khóa, giới thiệu wifi, giờ ăn sáng và giờ yên tĩnh 22h. Thu {said["pay"]} xu.'
                        + (' (Cuối ngày đối soát mới thấy: khoản cọc trong ảnh chụp chưa từng về tài khoản…)' if lost else '')
                        + (' ' + said['message'] if said['message'] else ''), celebrate=not lost and not cq.slips(t))


OOPS = ('entry', 'photo')


def _regular(c: dict, t: dict) -> None:
    """A guest the book remembers: was the room they liked given back to them (when it was free)?"""
    if not t.get('gen'):
        return
    rec = _data(c)['book'].get(str(_npc_index(t)))
    if not rec or not rec['visits']:
        return
    fav, ci, n, x = rec['fav'], t['ci'], t['needs'], t['_x']
    staying = _counted(n['adults'], n['kids']) if ci['extra'] == 'refuse' else _counted(x['adults'], x['kids'])
    free = (fav is not None and fav not in ci['rooms'] and ROOM_INDEX[fav]['cap'] >= staying and ROOM_INDEX[fav]['unlock'] <= kit.level(c)
            and _blocked(c, fav, c['day'], n['nights']) is None and _data(c)['rooms'][fav]['status'] == 'clean')
    t['regular'] = dict(score=4 if free else 5, fav=fav, visits=rec['visits'])
ELDERS = (2, 14)          # guests whose profile says they cannot climb stairs


def _oops(ci: dict, code: str) -> None:
    """Remember a slip made in front of the guest; it is only judged when the keys are handed over."""
    rows = ci.setdefault('oops', [])
    if code not in rows:
        rows.append(code)


def _checkin_slips(t: dict, dirty: list) -> None:
    n, ci = t['needs'], t['ci']
    q = ci['q']
    if dirty:
        cq.slip(t, 'dirty_room', 3, 'Phòng giao cho mình chưa dọn: ga gối cũ, phòng tắm còn bẩn.', 'giao phòng chưa dọn')
    elif q <= 2:
        cq.slip(t, 'sloppy_room', 2, 'Phòng dọn qua loa: ga nhăn, còn mùi ẩm, mình phải tự lau lại.', 'phòng dọn qua loa')
    elif q == 3:
        cq.slip(t, 'sloppy_room', 1, 'Phòng dọn chưa kỹ, vào còn ngửi thấy mùi ẩm.', 'phòng dọn chưa kỹ')
    cap = sum(ROOM_INDEX[r]['cap'] for r in ci['rooms'])
    if cap < n['size']:
        cq.slip(t, 'small_room', 2, f'Đặt phòng {n["size"]} người mà được xếp phòng nhỏ hơn, chen chúc chật chội.', 'xếp phòng nhỏ hơn phòng đã đặt')
    elder = _npc_index(t) in ELDERS
    if elder and any(ROOM_INDEX[r]['stairs'] for r in ci['rooms']):
        cq.slip(t, 'stairs', 1, 'Cô lớn tuổi rồi mà phải leo cầu thang dốc lên phòng.', 'người lớn tuổi phải leo cầu thang')
    if n['cold'] and not ci['heater']:
        if elder:
            cq.slip(t, 'no_heater', 3, 'Cô lớn tuổi rồi, trời lạnh thế này mà phòng không có máy sưởi, vào là lạnh buốt.', 'đêm lạnh không có máy sưởi')
        else:
            cq.slip(t, 'no_heater', 2, 'Đêm nay lạnh mà phòng không có máy sưởi, vào là lạnh buốt.', 'đêm lạnh không có máy sưởi')
    if ci['extra'] == 'refuse' and ci['could_fit']:
        cq.slip(t, 'turned_away', 1, 'Nhà còn phòng rộng mà vẫn mời bạn mình đi chỗ khác.', 'còn phòng mà mời người đi cùng đi chỗ khác')
    oops = ci.get('oops') or []
    if 'entry' in oops:
        cq.slip(t, 'wrong_booking', 1, 'Dò nhầm sang đặt phòng của người khác, mình phải đứng chờ.', 'dò nhầm đặt phòng')
    if 'photo' in oops:
        cq.slip(t, 'id_photo', 1, 'Đòi chụp giấy tờ tùy thân của mình vào điện thoại, nghe mà ngại.', 'đòi chụp giấy tờ tùy thân')


def _said(t: dict) -> str:
    """What the guest says when no money changes hands: the worst slip, in their words."""
    rows = sorted(cq.slips(t), key=lambda r: -r['sev'])
    return f'{_guest(t)}: “{rows[0]["text"]}”' if rows else ''


def _settle_free(s: dict, c: dict, t: dict) -> str:
    """A phone call or a referral: nothing to pay or refund, but a serious mistake still reaches the app."""
    if not cq.slips(t):
        return ''
    notes = cq._escalate(s, c, t)
    return ' '.join([_said(t)] + notes)


# ---------------------------------------------------------------- check-out
def _truth_bill(t: dict) -> dict:
    n, x = t['needs'], t['_x']
    pkg = n.get('package') or {}
    free = set(pkg.get('free') or ())
    water_free = pkg.get('water_free') or FREE_WATER
    return dict(water=0 if 'water' in free else max(0, x['water'] - water_free), noodles=0 if 'noodles' in free else x['noodles'],
                snack=0 if 'snack' in free else x['snack'], laundry=0 if 'laundry' in free else n['laundry'],
                late=1 if n['late'] else 0, damage=1 if x['damage'] else 0)


def _bill_total(bill: dict) -> int:
    return sum(BILL_INDEX[k]['price'] * q for k, q in bill.items())


CASH_SHARE = 55   # % of guests who settle the checkout bill in cash (the rest transfer)


def _pays_cash(t: dict) -> bool:
    """How this guest pays the checkout bill: a pure roll of the task id, so it never changes."""
    return kit.rng(ID, 'checkout-pay', t['id']).random() * 100 < CASH_SHARE


def _cash_rec(t: dict, total: int) -> dict:
    """The guest's notes for this bill total (rolled from the task id). A bill edited after they
    asked for the rest of the change gets new notes, and they keep counting carefully."""
    rec = t.get('cash')
    if not rec or rec['price'] != total:
        asked = rec['asked'] if rec else 0
        rec = t['cash'] = till.new(total, t['id'])
        rec['asked'] = asked
    return rec


def _checkout(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    x = t['_x']
    if name == 'hs_inspect':
        kit.need(not t['checked'], 'Đã kiểm phòng rồi.')
        t['checked'] = True
        kit.start_work(t)
        parts = [f'{x["water"]} chai nước', f'{x["noodles"]} ly mì', f'{x["snack"]} gói bánh', f'{x["coffee"]} gói cà phê (miễn phí)']
        msg = 'Buồng phòng báo: minibar dùng ' + ', '.join(parts) + '.'
        msg += f' Hư hỏng: {x["damage"].lower()}.' if x['damage'] else ' Không có hư hỏng.'
        if x['lost']:
            msg += f' Khách để quên: {x["lost"].lower()}!'
        return dict(message=msg)
    if name == 'hs_return':
        kit.need(t['checked'], 'Kiểm phòng trước đã.')
        kit.need(x['lost'] and not t['returned'], 'Không có đồ nào cần trả.')
        t['returned'] = True
        return dict(message=f'Đã chạy lên phòng lấy “{x["lost"]}” trả tận tay khách. Khách mừng rỡ!')
    if name == 'hs_line':
        kit.need(t['checked'], 'Kiểm phòng (minibar, hư hỏng) trước khi lập hóa đơn.')
        line = kit.one_of(p.get('line'), BILL_INDEX, 'Dòng hóa đơn không tồn tại.')
        kit.need(type(p.get('delta')) is int, 'Chỉ tăng hoặc giảm 1.')
        delta = kit.one_of(p.get('delta'), (1, -1), 'Chỉ tăng hoặc giảm 1.')
        q = t['bill'][line] + delta
        kit.need(0 <= q <= 9, 'Số lượng không hợp lệ.')
        t['bill'][line] = q
        return dict(message=f'{BILL_INDEX[line]["name"]}: {q} {BILL_INDEX[line]["unit"]}.')
    # hs_settle
    kit.confirm(p, 'Xác nhận in hóa đơn và thu tiền.')
    kit.need(t['checked'], 'Kiểm phòng trước khi tính tiền.')
    who = _guest(t)
    truth = _truth_bill(t)
    total = _bill_total(t['bill'])
    over = [k for k, q in t['bill'].items() if q > truth[k]]
    gap = sum((t['bill'][k] - truth[k]) * BILL_INDEX[k]['price'] for k in over)
    # The guest reads the bill: a careful one (or one who already caught a mistake) points out the extra line.
    if over and (t['disputes'] or till.careful(c, t, gap, _bill_total(truth))):
        t['disputes'] += 1
        t['mistakes'] += 1
        k = over[0]
        pkg = t['needs'].get('package') or {}
        if k in (pkg.get('free') or ()):
            say = f'{pkg["name"]} của mình {pkg["text"]} mà?'
        elif k == 'water' and pkg.get('water_free'):
            say = f'{pkg["name"]}: {pkg["text"]} mà? Mình uống {x["water"]} chai thôi.'
        else:
            say = {'water': f'Mình uống {x["water"]} chai, 2 chai đầu là quà của homestay mà?',
                   'noodles': f'Mình chỉ ăn {x["noodles"]} ly mì thôi.', 'snack': f'Mình chỉ lấy {x["snack"]} gói bánh.',
                   'laundry': f'Mình gửi {t["needs"]["laundry"]} túi giặt thôi.', 'late': 'Mình trả phòng trước 12 giờ mà?',
                   'damage': 'Phòng có gì hư đâu?'}[k]
        kit.log(s, c, 'refused', f'Khách không đồng ý hóa đơn: {say}', t['npc'], t['id'])
        # Caught at the counter before paying: no money moves. The review names it later (after the
        # reaction, so pointing it out once does not also take money off the corrected bill).
        return dict(message=f'Khách chỉ vào dòng “{BILL_INDEX[k]["name"]}”: “{say}” Sửa hóa đơn cho đúng.', refused=True)
    rec = None
    if total and _pays_cash(t):
        rec = _cash_rec(t, total)
        change = p.get('change')
        chk = till.check(s, c, t, rec, [] if change is None else change, who)
        if chk['stop']:
            return dict(message='💵 ' + chk['message'], refused=True)
    if over:
        t['mistakes'] += 1       # nobody read the bill: they pay it and find the extra line at home
    under = [k for k in ('water', 'noodles', 'snack', 'laundry', 'late') if t['bill'][k] < truth[k]]
    t['mistakes'] += len(under)
    if x['lost'] and not t['returned']:
        t['mistakes'] += 1
        d = kit.data(c)
        d['seq'] += 1
        d['lost'] = ar.last(d['lost'] + [dict(id=f'lf-{d["seq"]}', item=x['lost'], room=t['room'] or 'thong', day=c['day'], status='kept')], 40, 'homestay.lost', c)
        cq.slip(t, 'forgot_item', 1, f'Về tới nhà mới nhớ để quên {x["lost"].lower()}, lúc trả phòng không ai nhắc.', 'không trả đồ khách để quên')
    # Forgetting a line is the house's loss, not the guest's complaint: only real slips reach react().
    said = cq.react(s, c, t, total, who=who)
    gone = said['kind'] in ('refuse', 'walkout')
    if t['disputes']:
        cq.slip(t, 'overcharge', 1, 'Hóa đơn tính dư, mình phải chỉ ra mới được sửa.', 'hóa đơn tính dư')
        if t['disputes'] > 1:
            cq.slip(t, 'overcharge_again', 1, 'Sửa rồi mà hóa đơn vẫn tính dư, phải cãi thêm lần nữa.', 'hóa đơn tính dư nhiều lần')
    if over and not gone:
        t['overpaid'] = gap
        cq.slip(t, 'overcharge_home', 2, f'Về xem lại hóa đơn mới thấy bị tính dư {gap} xu, phải nhắn homestay đòi lại.', f'tính dư {gap} xu')
    cash = till.settle(s, c, t, rec, said, who) if rec else dict(loss=0, tip=0, message='')
    d = kit.data(c)
    if t['room'] and d['rooms'][t['room']]['task'] == t['id']:
        stay = _depart(s, c, t['room'], t)
        if stay:
            t['stay'] = stay
        r = d['rooms'][t['room']]
        r.update(status='dirty', guest=None, task=None, until=0, mini=min(6, x['noodles'] + x['snack']), hk=None)
    kit.metric(c, 'checkouts')
    kit.complete(s, c, t, max(0, said['pay'] - cash['loss']), f'Bạn đã làm thủ tục trả phòng cho {who}.')
    extra = ''
    if t.get('overpaid'):
        back = min(gap, c['money'])
        if back:
            kit.money(s, c, -back, f'Trả lại tiền tính dư cho {who}'[:120], t['id'], 'refund')
        extra = f' Tối {who} nhắn: hóa đơn tính dư {gap} xu. Homestay chuyển trả lại.'
    if cash['message']:
        extra += ' ' + cash['message']
    how = '' if not total or gone else ' Khách trả tiền mặt.' if rec else ' Khách chuyển khoản.'
    note = f' (quên tính {len(under)} dòng — homestay chịu thiệt)' if under else ''
    if said['message']:
        return dict(message=f'Hóa đơn {total} xu{note}.{how} {said["message"]}{extra} Phòng chuyển sang “cần dọn”.', celebrate=False)
    return dict(message=f'Hóa đơn {total} xu, khách thanh toán và cảm ơn{note}.{how}{extra} Phòng chuyển sang “cần dọn”.',
                celebrate=not under and not over and not t['mistakes'])


# ---------------------------------------------------------------- breakfast
def _doneness(seconds: float) -> str:
    if seconds < EGG['raw']:
        return 'raw'
    if seconds <= EGG['runny']:
        return 'runny'
    if seconds <= EGG['well']:
        return 'well'
    return 'burnt'


def _breakfast(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n, tray = t['needs'], t['tray']
    if name == 'hs_egg':
        kit.need(tray['pan'] is None, 'Chảo đang có trứng. Nhấc trứng ra trước.')
        kit.need(len(tray['eggs']) < 6, 'Khay đủ trứng rồi.')
        tray['cost'] += kit.take(c, 'egg', 1)
        tray['pan'] = round(kit.now(), 3)
        kit.start_work(t)
        return dict(message=f'Đập trứng vào chảo. Lòng đào: nhấc trong {EGG["raw"]}–{EGG["runny"]} giây; chín kỹ: {EGG["runny"]}–{EGG["well"]} giây.')
    if name == 'hs_plate':
        kit.need(tray['pan'] is not None, 'Chảo đang trống.')
        sec = max(0.0, kit.now() - tray['pan'])
        done = _doneness(sec)
        tray['eggs'].append(done)
        tray['pan'] = None
        if done in ('raw', 'burnt'):
            t['mistakes'] += 1
        return dict(message={'raw': 'Trứng còn sống, lòng trắng chưa đông.', 'runny': 'Trứng ốp lòng đào, lòng trắng đông, lòng đỏ sánh.',
                             'well': 'Trứng ốp chín kỹ, lòng đỏ chín đều.', 'burnt': 'Trứng cháy cạnh rồi…'}[done] + f' ({sec:.1f} giây)')
    if name == 'hs_diet':
        kit.need(t.get('gen'), 'Khách đã dặn rõ trong phiếu.')
        kit.need(not t['diet'], 'Đã hỏi rồi.')
        t['diet'] = True
        kit.start_work(t)
        return dict(message='Khách: “' + (t['_x'].get('diet') or DIET_NONE) + '”')
    simple = dict(hs_bread=('bread', 'bread', 6, 'Nướng giòn một ổ bánh mì.'), hs_milk=('milk', 'milk', 4, 'Rót một ly sữa tươi, hâm ấm.'),
                  hs_coffee=('coffee', 'coffee', 4, 'Pha một ly cà phê nóng.'))
    if name in simple:
        key, item, cap, msg = simple[name]
        kit.need(tray[key] < cap, 'Khay đủ rồi.')
        tray['cost'] += kit.take(c, item, 1)
        tray[key] += 1
        kit.start_work(t)
        if tray[key] > n[key]:
            t['mistakes'] += 1
        return dict(message=msg)
    if name == 'hs_toss':
        kit.confirm(p, 'Xác nhận bỏ khay này; nguyên liệu đã dùng ghi vào hao hụt.')
        kit.need(tray['eggs'] or tray['bread'] or tray['milk'] or tray['coffee'] or tray['pan'], 'Khay đang trống.')
        kit.waste(c, 'tray', 1, tray['cost'], 'Bỏ khay ăn sáng làm lại')
        t['tray'] = _empty_tray()
        t['mistakes'] += 1
        return dict(message='Đã dọn khay. Làm lại từ đầu nhé.')
    # hs_serve
    kit.confirm(p, 'Xác nhận mang bữa sáng ra cho khách.')
    kit.need(tray['pan'] is None, 'Còn trứng trong chảo.')
    kit.need(tray['bread'] or tray['eggs'], 'Khay chưa có gì để ăn.')
    want_eggs = sum(_eggs_want(t).values())
    problem = None
    hidden = t.get('gen') and t['_x'].get('allergy') == 'egg'
    told = n['allergy'] == 'egg' or (hidden and t.get('diet'))
    if 'raw' in tray['eggs']:
        problem = 'Có trứng còn sống — không an toàn. Dọn khay và làm lại.'
        cq.slip(t, 'raw_egg', 1, 'Trứng mang ra còn sống, phải trả khay cho làm lại.', 'trứng còn sống')
    elif told and len(tray['eggs']) > want_eggs:
        # The guest said it out loud (or was asked): an egg on that plate is a real danger, not a remake.
        return _allergy_served(s, c, t)
    elif hidden and len(tray['eggs']) > want_eggs:
        t['diet'] = True
        problem = t['_x']['diet'] + ' Dọn khay làm lại, tách riêng dụng cụ — lần sau hỏi dị ứng trước khi nấu.'
        cq.slip(t, 'no_ask_allergy', 2, 'Không ai hỏi dị ứng trước khi nấu, suýt nữa người nhà mình ăn phải trứng.', 'không hỏi dị ứng trước khi nấu')
    if problem:
        t['refused'] += 1
        t['mistakes'] += 1
        kit.log(s, c, 'refused', 'Khách trả lại khay ăn sáng: ' + problem, t['npc'], t['id'])
        return dict(message='Khách không nhận: ' + problem, refused=True)
    _breakfast_slips(t)
    price = t['quoted_price'] or 0
    fresh = any(r['code'] not in TRAY_BACK for r in cq.slips(t))
    said = cq.react(s, c, t, price, remake=fresh, who=_guest(t))
    if said['kind'] == 'remake':
        # Sent back to the kitchen: the tray is wasted and the guest waits a little longer.
        kit.waste(c, 'tray', 1, tray['cost'], 'Khách trả khay ăn sáng, làm lại')
        t['tray'] = _empty_tray()
        t['patience'] = max(25, t.get('patience', 100) - 10)
        t['mistakes'] += 1
        rows = cq.slips(t)
        keep = [r for r in rows if r['code'] in TRAY_BACK]
        worst = max((r for r in rows if r not in keep), key=lambda r: r['sev'])
        cq.downgrade(t, 'returned', f"{worst['text']} Phải làm lại.", 'phải làm lại')
        for r in keep:
            cq.slip(t, r['code'], r['sev'], r['text'], r['note'])
        kit.log(s, c, 'refused', f'Khách trả lại khay ăn sáng: {worst["text"]}', t['npc'], t['id'])
        return dict(message=f'{said["message"]} Dọn khay, làm lại khay mới nhé.', refused=True)
    t['served'] = copy.deepcopy(tray)
    kit.metric(c, 'breakfasts')
    kit.complete(s, c, t, said['pay'], f'Bạn đã làm bữa sáng cho {_guest(t)}.')
    if said['message']:
        return dict(message=f'Bữa sáng đã lên bàn · +{said["pay"]} xu. {said["message"]}')
    return dict(message=f'Bữa sáng đã lên bàn · +{price} xu.', celebrate=True)


def _allergy_served(s: dict, c: dict, t: dict) -> dict:
    """An egg reached the table of someone who said they are allergic: the guest refuses, pays nothing and reports it."""
    cq.slip(t, 'allergy', 3, 'Đã báo có người dị ứng trứng mà khay vẫn có thêm trứng, suýt nữa ăn phải.', 'đã báo dị ứng mà vẫn cho trứng',
            safety=True)
    t['mistakes'] += 1
    t['served'] = copy.deepcopy(t['tray'])
    said = cq.react(s, c, t, t['quoted_price'] or 0, who=_guest(t))
    kit.log(s, c, 'refused', 'Khách trả lại khay ăn sáng vì có trứng dù đã báo dị ứng.', t['npc'], t['id'])
    kit.metric(c, 'breakfasts')
    kit.complete(s, c, t, said['pay'], f'Bạn đã làm bữa sáng cho {_guest(t)}, nhưng khay có trứng dù khách đã báo dị ứng.')
    return dict(message=f'Khách không ăn: khay có trứng mà có người dị ứng trứng! {said["message"]}', refused=True)


BF_NAMES = dict(bread='bánh mì', milk='sữa', coffee='cà phê')
TRAY_BACK = ('raw_egg', 'no_ask_allergy')      # trays the guest already sent back before tasting


def _breakfast_slips(t: dict) -> None:
    """Compare the tray with the order: doneness, burnt eggs, missing items (extras are the kitchen's loss)."""
    n, tray = t['needs'], t['tray']
    want = _eggs_want(t)
    eggs = tray['eggs']
    got = dict(runny=eggs.count('runny'), well=eggs.count('well'))
    short = {k: max(0, want[k] - got[k]) for k in got}
    over = {k: max(0, got[k] - want[k]) for k in got}
    as_well = min(short['runny'], over['well'])        # asked runny, got well done
    as_runny = min(short['well'], over['runny'])       # asked well done, got runny
    swapped = as_well + as_runny
    burnt = eggs.count('burnt')
    if swapped:
        text = 'Dặn trứng chín kỹ mà mang ra trứng lòng đào.' if as_runny else 'Dặn trứng lòng đào mà mang ra trứng chín kỹ.'
        cq.slip(t, 'doneness', 1 if swapped == 1 else 2, text, 'sai độ chín của trứng')
    if burnt:
        cq.slip(t, 'burnt', 1 if burnt == 1 else 2, 'Trứng cháy cạnh, ăn đắng nghét.', 'trứng bị cháy')
    missing = []
    total_want, total_got = sum(want.values()), len(eggs)
    if total_got < total_want:
        missing.append((total_want - total_got, f'Gọi {total_want} trứng mà chỉ mang ra {total_got}.'))
    for key, name in BF_NAMES.items():
        if tray[key] < n[key]:
            missing.append((n[key] - tray[key], f'Gọi {n[key]} {name} mà chỉ mang ra {tray[key]}.'))
    if missing:
        count = sum(k for k, _ in missing)
        cq.slip(t, 'short', 1 if count == 1 else 2, missing[0][1], 'thiếu món đã gọi')


# ---------------------------------------------------------------- recommendations
def _recommend(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n = t['needs']
    if name == 'hs_probe':
        q = kit.one_of(p.get('q'), PROBE_IDS, 'Câu hỏi không có trong sổ.')
        kit.need(q not in t['inspected'], 'Đã hỏi câu này rồi.')
        t['inspected'].append(q)
        kit.start_work(t)
        return dict(message=t['_x']['probes'][q]['answer'])
    if name == 'hs_pick':
        place = kit.one_of(p.get('place'), PLACE_INDEX, 'Địa điểm không có trong bản đồ.')
        if place in t['picks']:
            t['picks'].remove(place)
            return dict(message=f'Bỏ {PLACE_INDEX[place]["name"]} khỏi lịch trình.')
        kit.need(len(t['picks']) < 3, 'Gợi ý tối đa 3 nơi thôi, nhiều quá khách rối.')
        t['picks'].append(place)
        kit.start_work(t)
        return dict(message=f'Thêm {PLACE_INDEX[place]["name"]} vào lịch trình.')
    kit.confirm(p, 'Xác nhận gửi lịch trình cho khách.')
    kit.need(len(t['picks']) >= n['count'], f'Gợi ý ít nhất {n["count"]} nơi.')
    viol, _, _ = _fit(t)
    t['mistakes'] += viol
    _recommend_slips(t)
    kit.metric(c, 'recommendations')
    said = cq.react(s, c, t, kit.price(c, 'guide', SPEC['prices']['guide']), who=_guest(t))
    kit.complete(s, c, t, said['pay'], f'Bạn đã gợi ý lịch trình cho {_guest(t)}.')
    if said['message']:
        return dict(message=f'Đã vẽ bản đồ tay, ghi giờ mở cửa và số taxi. {said["message"]}')
    return dict(message='Đã vẽ bản đồ tay, ghi giờ mở cửa và số taxi. Khách lên đường!', celebrate=viol == 0)


def _recommend_slips(t: dict) -> None:
    """A place that does not suit someone in the group (stairs for a knee, a far trip without a ride…), or nothing they wanted."""
    n, probes = t['needs'], t['_x']['probes']
    told = set(n['avoid']) | {a for q, pr in probes.items() if q in t['inspected'] for a in pr['avoid']}
    avoid = set(n['avoid']) | {a for pr in probes.values() for a in pr['avoid']}
    bad = [(p, next(x for x in PLACE_INDEX[p]['tags'] if x in avoid)) for p in t['picks'] if set(PLACE_INDEX[p]['tags']) & avoid]
    if bad:
        place, tag = bad[0]
        name, why = PLACE_INDEX[place]['name'], TAG_NAMES.get(tag, tag)
        sev = 2 if len(bad) == 1 else 3
        if tag in told:
            cq.slip(t, 'unsuitable', sev, f'Mình đã nói rồi mà vẫn chỉ tới {name} — {why}, không hợp với nhà mình chút nào.', 'gợi ý nơi không hợp cả nhóm')
        else:
            cq.slip(t, 'unsuitable', sev, f'Chỉ tới {name} — {why} — mà không hỏi nhà mình có ai đi được không.', 'gợi ý nơi không hợp cả nhóm')
    _, _, unmet = _fit(t)
    if unmet and _coverable(t):
        cq.slip(t, 'unmet', 1, f'Mình muốn chỗ {TAG_NAMES.get(unmet[0], unmet[0])} mà lịch trình không có nơi nào như vậy.', 'thiếu điều khách mong muốn')


def _coverable(t: dict) -> bool:
    """Could 2–3 suitable places have covered every wish? (Some days nothing can.)"""
    n, probes = t['needs'], t['_x']['probes']
    avoid = set(n['avoid']) | {a for pr in probes.values() for a in pr['avoid']}
    wants = set(n['wants']) | {w for pr in probes.values() for w in pr['want']}
    ok = [set(p['tags']) for p in PLACES if not set(p['tags']) & avoid]
    return any(all(any(w in tg for tg in combo) for w in wants)
               for k in range(max(1, n['count']), 4) for combo in itertools.combinations(ok, k))


def _fit(t: dict) -> tuple[int, list, list]:
    n = t['needs']
    avoid = set(n['avoid'])
    wants = list(n['wants'])
    for pr in t['_x']['probes'].values():
        avoid |= set(pr['avoid'])
        wants += [w for w in pr['want'] if w not in wants]
    tags = [set(PLACE_INDEX[p]['tags']) for p in t['picks']]
    bad = [PLACE_INDEX[p]['name'] for p, tg in zip(t['picks'], tags) if tg & avoid]
    unmet = [w for w in wants if not any(w in tg for tg in tags)]
    return len(bad), bad, unmet


# ---------------------------------------------------------------- feedback
def _speed(t: dict) -> tuple[int, str]:
    p = t.get('patience', 100)
    return (5 if p >= 90 else 4 if p >= 70 else 3 if p >= 50 else 2), f'kiên nhẫn còn {p}%'


def feedback(c: dict, t: dict) -> dict:
    job = t['job']
    sp, spn = _speed(t)
    rows = []
    cap = None
    if job == 'booking':
        n = t['needs']
        if t['status'] == 'referred':
            ok = t['decline_ok']
            rows.append(dict(key='honesty', label='Báo đúng tình trạng phòng', score=5 if ok else 3,
                             note='lịch kín thật, được giới thiệu chỗ khác' if ok else 'lịch vẫn còn phòng phù hợp'))
        else:
            stairs = not n['stairs_ok'] and any(ROOM_INDEX[r]['stairs'] for r in t['hold'])
            pref = not n['prefer'] or any(r in n['prefer'] for r in t['hold'])
            fit = 3 if stairs else 5 if pref else 4
            rows.append(dict(key='fit', label='Phòng hợp nhu cầu', score=fit,
                             note='phải leo cầu thang dù đã dặn' if stairs else 'đúng phòng mong muốn' if pref else 'không phải phòng mình thích'))
            rows.append(dict(key='clarity', label='Báo giá & cọc rõ ràng', score=5, note=f'tổng {t["quote"]["total"]} xu, cọc {t["quote"]["deposit"]} xu'))
            if t.get('gen'):
                top, r = _cap(t), RATE_IDS.index(t['rate'])
                score = 5 if r >= top else 4 if r == top - 1 else 3
                note = 'đúng giá thị trường hôm nay' if r >= top else 'bán rẻ hơn mức khách sẵn lòng trả'
                if t['haggles']:
                    score = max(2, score - t['haggles'])
                    note += f' · khách phải chê giá {t["haggles"]} lần'
                rows.append(dict(key='price', label='Chốt giá', score=score, note=note))
    elif job == 'checkin' and t['status'] == 'referred':
        rows.append(dict(key='promise', label='Giữ phòng cho khách đã đặt', score=2, note='bán mất chỗ của khách sắp đến, phải chuyển sang nhà bên'))
        rows.append(dict(key='recover', label='Xử lý khi hết phòng', score=4, note='xin lỗi, hoàn cọc, trả taxi, có chỗ ở ngay'))
    elif job == 'checkin':
        ci, n = t['ci'], t['needs']
        lost = _lost_deposit(t)
        wrong = t['mistakes'] - (1 if lost else 0)
        rows.append(dict(key='welcome', label='Thủ tục nhận phòng', score=max(2, 5 - wrong),
                         note='nhầm mã đặt phòng hoặc đòi chụp giấy tờ' if wrong else 'nhanh gọn, đúng đặt phòng'))
        q = ci['q'] or 3
        rows.append(dict(key='room', label='Phòng sạch thơm', score=q, note={5: 'phòng thơm mùi gỗ thông', 4: 'sạch, còn chút sơ sót',
                                                                            3: 'phòng hơi ẩm mùi', 2: 'dọn chưa kỹ', 1: 'phòng bừa bộn'}[q]))
        if n['cold']:
            rows.append(dict(key='warmth', label='Ấm áp đêm lạnh', score=5 if ci['heater'] else 2,
                             note='máy sưởi chạy sẵn' if ci['heater'] else 'đêm 12 độ không có máy sưởi'))
        if ci['extra'] in ('surcharge', 'refuse'):
            if ci['extra'] == 'surcharge':
                rows.append(dict(key='fair', label='Xử lý người đi thêm', score=5, note='phụ thu rõ ràng, có nệm phụ'))
            else:
                rows.append(dict(key='fair', label='Xử lý người đi thêm', score=3 if ci['could_fit'] else 4,
                                 note='còn phòng mà vẫn mời bạn mình đi' if ci['could_fit'] else 'đúng nội quy an toàn'))
        reg = t.get('regular')
        if reg:
            given = reg['fav'] in ci['rooms']
            rows.append(dict(key='regular', label='Nhớ khách quen', score=reg['score'],
                             note='lại được phòng quen' if given else 'phòng quen hôm nay đã kín' if reg['score'] == 5 else 'phòng quen còn trống mà xếp phòng khác'))
        if t.get('gen') and n.get('proof') == 'bank':
            if t.get('bank'):
                rows.append(dict(key='deposit', label='Đối chiếu tiền cọc', score=5,
                                 note='xem sao kê trước khi trừ cọc' + (' — phát hiện chuyển nhầm' if t['bank'] == 'missing' else '')))
            elif lost:
                rows.append(dict(key='deposit', label='Đối chiếu tiền cọc', score=1, note=f'trừ cọc theo ảnh chụp — nhà mất {n["paid"]} xu'))
    elif job == 'checkout':
        truth = _truth_bill(t)
        under = [k for k in ('water', 'noodles', 'snack', 'laundry', 'late') if t['bill'][k] < truth[k]]
        # Lines the house forgot to charge are its own loss; the guest does not mark that down.
        score = 2 if t['disputes'] or t.get('overpaid') else 5
        rows.append(dict(key='bill', label='Hóa đơn chính xác', score=score,
                         note='tính dư, về nhà mới thấy' if t.get('overpaid') else 'tính dư phải sửa lại' if t['disputes']
                         else 'hóa đơn còn rẻ hơn mình nghĩ' if under else 'từng dòng rõ ràng, đúng'))
        cash = t.get('cash')
        if cash and cash['outcome'] in ('exact', 'keep', 'missed', 'returned', 'kept'):
            rows.append(dict(key='cash', label='Tiền thối', score=2 if cash['outcome'] == 'missed' else 4 if cash['asked'] or cash['over'] else 5,
                             note='thối thiếu, về nhà mới thấy' if cash['outcome'] == 'missed' else 'thối thiếu, khách phải nhắc' if cash['asked']
                             else 'thối dư' if cash['over'] else 'thối tiền chính xác'))
        lost = t['_x']['lost']
        if lost:
            rows.append(dict(key='care', label='Đồ bỏ quên', score=5 if t['returned'] else 2,
                             note=f'được trả lại {lost.lower()}' if t['returned'] else f'về tới nhà mới nhớ {lost.lower()}'))
        if t['_x']['damage'] and t['bill']['damage'] == 0:
            rows.append(dict(key='goodwill', label='Cách xử lý hư hỏng', score=5, note='homestay bỏ qua chiếc cốc mẻ'))
        stay = t.get('stay')
        if stay:
            rows.append(dict(key='stay', label='Mấy ngày lưu trú', score=stay['stars'],
                             note={5: 'được chăm như ở nhà', 4: 'thoải mái, có người để ý', 3: 'ổn, nhưng ít được hỏi han'}.get(stay['stars'])
                             or (stay['low'] or 'ở dài ngày không ai lo').rstrip('.').lower()))
    elif job == 'breakfast':
        tray = t['served']
        n = t['needs']
        want = _eggs_want(t)
        taste = 2 if 'burnt' in tray['eggs'] else 5
        got = dict(runny=tray['eggs'].count('runny'), well=tray['eggs'].count('well'))
        miss = sum(max(0, want[k] - got[k]) for k in got) + max(0, n['bread'] - tray['bread']) + max(0, n['milk'] - tray['milk']) + max(0, n['coffee'] - tray['coffee'])
        extra = sum(max(0, got[k] - want[k]) for k in got) + max(0, tray['bread'] - n['bread']) + max(0, tray['milk'] - n['milk']) + max(0, tray['coffee'] - n['coffee'])
        rows.append(dict(key='taste', label='Trứng ốp', score=taste, note='có trứng bị cháy' if taste < 5 else 'đúng độ chín'))
        rows.append(dict(key='accuracy', label='Đúng món đã gọi', score=max(1, 5 - miss - (1 if extra else 0)),
                         note=(f'thiếu {miss} món' if miss else '') + (' · dư món không gọi' if extra else '') or 'đủ món'))
        if n['allergy']:
            rows.append(dict(key='care', label='Cẩn thận dị ứng', score=1 if cq.safety(t) else 2 if t['refused'] else 5,
                             note='khay có trứng dù đã báo dị ứng' if cq.safety(t) else 'phải trả lại khay' if t['refused'] else 'phần không trứng riêng biệt'))
        elif t.get('gen') and t['_x'].get('allergy'):
            rows.append(dict(key='care', label='Hỏi dị ứng trước khi nấu', score=1 if cq.safety(t) else 2 if t['refused'] else 5,
                             note='khay có trứng dù đã báo dị ứng' if cq.safety(t) else 'khay có trứng phải trả lại' if t['refused'] else 'phần không trứng riêng biệt'))
    elif job == 'claim':
        kind, choice, asked = t['_x']['kind'], t['choice'], t['asked']
        careful = 'describe' in asked
        table = {('owner', 'give'): (5 if careful else 4, 'hỏi kỹ rồi giao đúng người' if careful else 'chưa hỏi tả món đồ đã giao — may mà đúng người'),
                 ('owner', 'channel'): (4, 'chắc chắn, chỉ chậm một chút'), ('owner', 'deny'): (2, 'từ chối cả chủ thật'),
                 ('imposter', 'give'): (1, 'giao đồ cho người lạ'), ('imposter', 'channel'): (5, 'hỏi lại người đặt phòng nên giữ được đồ'),
                 ('imposter', 'deny'): (5, 'nhận ra người nhận vơ, giữ đồ an toàn'), ('friend', 'give'): (2, 'giao cho người chưa được xác nhận'),
                 ('friend', 'channel'): (5, 'xác nhận với người đặt phòng rồi mới giao'), ('friend', 'deny'): (3, 'đúng quy trình nhưng không giúp được')}
        score, note = table.get((kind, choice), (3, 'chưa quyết'))
        rows.append(dict(key='verify', label='Giao đồ đúng người', score=score, note=note))
        n_ask = len(asked)
        rows.append(dict(key='listening', label='Hỏi han xác minh', score=5 if n_ask >= 3 else 4 if n_ask == 2 else 3 if n_ask == 1 else 2,
                         note=f'hỏi {n_ask}/{len(CLAIM_QS)} câu'))
        if kind == 'imposter' and choice == 'give':
            cap = 1
    else:
        viol, bad, unmet = _fit(t)
        rows.append(dict(key='fit', label='Hợp với cả nhóm', score=max(1, 5 - 2 * viol), note=('không hợp: ' + ', '.join(bad)) if bad else 'nơi nào cũng đi được'))
        rows.append(dict(key='coverage', label='Đúng điều mình muốn', score=max(1, 5 - len(unmet)),
                         note=('thiếu: ' + ', '.join(TAG_NAMES.get(w, w) for w in unmet)) if unmet else 'đủ điều mong muốn'))
        relevant = [q for q, pr in t['_x']['probes'].items() if pr['avoid'] or pr['want']]
        missed = [q for q in relevant if q not in t['inspected']]
        rows.append(dict(key='listening', label='Chịu hỏi han', score=max(2, 5 - len(missed)),
                         note='hỏi kỹ trước khi gợi ý' if not missed else 'chưa hỏi: ' + ', '.join(next(x['label'] for x in PROBES if x['id'] == q).lower() for q in missed)))
    rows.append(dict(key='speed', label='Thời gian chờ', score=sp, note=spn))
    out = dict(criteria=rows)
    if cap:
        out['cap'] = cap
    return out


# ---------------------------------------------------------------- projection & validation
def public_task(t: dict) -> dict:
    v = tree_copy(t)
    x = v.pop('_x', {})
    if not t['known']:
        v['needs'] = None
        return v
    if t['job'] == 'checkin':
        if t['ci']['counted']:
            v['arrived'] = dict(adults=x['adults'], kids=x['kids'])
        if t['ci']['ids']:
            v['id_status'] = x['id']
    elif t['job'] == 'checkout':
        if t['checked']:
            v['check'] = {k: val for k, val in x.items() if k != 'case'}
            v['truth_hint'] = dict(free_water=(t['needs'].get('package') or {}).get('water_free') or FREE_WATER)
            total = _bill_total(t['bill'])
            v['pay'] = 'cash' if _pays_cash(t) else 'transfer'
            rec = t.get('cash')
            if t['status'] in ('completed', 'cancelled', 'referred'):
                v['cash'] = till.public(rec)
            elif v['pay'] == 'cash' and total:
                # The notes the guest hands over for the bill as it stands now (the same roll the server uses).
                v['cash'] = till.public(rec if rec and rec['price'] == total else dict(till.new(total, t['id']), asked=rec['asked'] if rec else 0))
            else:
                v['cash'] = None
    elif t['job'] == 'recommend':
        v['answers'] = {q: x['probes'][q] for q in t['inspected'] if q in x['probes']}
    elif t['job'] == 'breakfast':
        v['egg_windows'] = EGG
        if t.get('gen') and t.get('diet'):
            v['diet_say'] = x.get('diet') or DIET_NONE
            if x.get('fix'):
                v['eggs_fix'] = x['fix']
    elif t['job'] == 'booking':
        if t.get('gen') and t.get('asked_budget'):
            v['budget_say'] = x['say']
    elif t['job'] == 'claim':
        v['answers'] = {q: x['say'][q] for q in t['asked'] if q in x['say']}
    return v


def public_data(c: dict) -> dict:
    d = tree_copy(_data(c))
    desk = d.pop('desk', None) or kit.desk_initial()
    for k, v in DATA_V2.items():
        d.setdefault(k, tree_copy(v))
    day = c['day']
    grid = {}
    for rid, r in d['rooms'].items():
        row = []
        for k in range(HORIZON):
            night = day + k
            cell = dict(day=night, kind='free', label='')
            if r['status'] == 'occupied' and (night < r['until'] or (k == 0 and r['task'])):
                cell.update(kind='occ', label=r['guest'] or 'Có khách', anniv=bool((d['stays'].get(rid) or {}).get('anniv')))
            elif r['status'] == 'maintenance' and k == 0:
                cell.update(kind='maint', label=r['note'] or 'Bảo trì')
            for b in d['bookings']:
                if rid in b['rooms'] and b['start'] <= night < b['start'] + b['nights']:
                    cell.update(kind='book', label=b['name'], anniv=bool(b.get('anniv')))
            row.append(cell)
        grid[rid] = row
    d['grid'] = grid
    d['today'] = day
    d['level'] = kit.level(c)
    mod, nxt = today(day), today(day + 1)
    d['mod'] = dict(id=mod['id'], title=mod['title'], emoji=mod['emoji'], text=mod['text'])
    d['tomorrow'] = dict(id=nxt['id'], title=nxt['title'], emoji=nxt['emoji'])
    d['desk'] = kit.desk_public(desk, DESK, ID)
    if d['desk']['ev']:
        # Options come in a shuffled order so the careful answer is not always the first button.
        kit.rng(ID, 'desk-order', d['desk']['ev']['id'], day).shuffle(d['desk']['ev']['options'])
    d['tier'] = kit.tier(day)
    d['score'] = _ota_score(c)
    d['safe_today'] = d['safety_day'] == day
    d['air'] = _air(c)
    d['ota'] = [o for o in d['ota'] if o['status'] == 'new' or o['day'] >= day - 1]
    _care_public(c, d)
    return d


def _bool(v, msg='Trạng thái không hợp lệ.'):
    kit.need(type(v) is bool, msg)


def validate_task(t: dict, original: dict) -> None:
    job = t['job']
    kit.integer(t.get('mistakes', 0), 0, 100000)
    if job == 'checkin':
        ci = t['ci']
        kit.need(isinstance(ci, dict) and set(original['ci']) <= set(ci), 'Phiếu nhận phòng thiếu dữ liệu.')
        for k in ('verified', 'ids', 'counted', 'heater'):
            _bool(ci[k])
        kit.need(ci['extra'] in (None, 'none', 'surcharge', 'refuse') and ci['could_fit'] in (None, True, False), 'Lựa chọn phụ thu sai.')
        kit.need(isinstance(ci['rooms'], list) and len(ci['rooms']) <= 2 and len(set(ci['rooms'])) == len(ci['rooms'])
                 and all(r in ROOM_INDEX for r in ci['rooms']), 'Phòng giao sai.')
        kit.integer(ci['q'], 0, 5)
        kit.integer(ci['paid'], 0, 100000)
        kit.integer(ci['cost'], 0, 100000)
        if 'oops' in ci:
            kit.need(isinstance(ci['oops'], list) and len(set(ci['oops'])) == len(ci['oops']) and all(x in OOPS for x in ci['oops']), 'Ghi chú quầy sai.')
        if t.get('gen'):
            kit.need(t.get('bank') in (None, 'ok', 'missing'), 'Đối chiếu cọc sai.')
        reg = t.get('regular')
        if reg is not None:
            kit.need(isinstance(reg, dict) and set(reg) == {'score', 'fav', 'visits'} and reg['score'] in (4, 5)
                     and (reg['fav'] is None or reg['fav'] in ROOM_INDEX), 'Ghi chú khách quen sai.')
            kit.integer(reg['visits'], 1, 99)
    elif job == 'checkout':
        kit.need(t['room'] is None or t['room'] in ROOM_INDEX, 'Phòng trả sai.')
        for k in ('bound', 'checked', 'returned'):
            _bool(t[k])
        kit.need(isinstance(t['bill'], dict) and set(t['bill']) == set(BILL_INDEX), 'Hóa đơn sai.')
        for q in t['bill'].values():
            kit.integer(q, 0, 9)
        kit.integer(t['disputes'], 0, 1000)
        kit.integer(t.get('overpaid', 0), 0, 10 ** 5)
        till.validate(t.get('cash'), t)
        kit.need(t.get('cash') is None or t['cash']['tender'] == till.tender(t['cash']['price'], t['id']), 'Tiền khách đưa sai.')
        stay = t.get('stay')
        if stay is not None:
            kit.need(isinstance(stay, dict) and set(stay) == {'mood', 'nights', 'stars', 'low'} and stay['stars'] in (2, 3, 4, 5)
                     and (stay['low'] is None or (isinstance(stay['low'], str) and len(stay['low']) <= 200)), 'Ghi chú lưu trú sai.')
            kit.integer(stay['mood'], MOOD_MIN, 100)
            kit.integer(stay['nights'], 0, 60)
    elif job == 'breakfast':
        tray = t['tray']
        kit.need(isinstance(tray, dict) and set(_empty_tray()) <= set(tray), 'Khay ăn sáng thiếu dữ liệu.')
        kit.need(isinstance(tray['eggs'], list) and len(tray['eggs']) <= 6 and all(e in ('raw', 'runny', 'well', 'burnt') for e in tray['eggs']), 'Trứng sai.')
        kit.need(tray['pan'] is None or (isinstance(tray['pan'], (int, float)) and not isinstance(tray['pan'], bool) and 0 <= tray['pan'] < 10**11), 'Chảo sai.')
        kit.integer(tray['bread'], 0, 6)
        kit.integer(tray['milk'], 0, 4)
        kit.integer(tray['coffee'], 0, 4)
        kit.integer(tray['cost'], 0, 10000)
        kit.integer(t['refused'], 0, 1000)
        _bool(t['bound'])
        kit.need(t['quoted_price'] is None or 1 <= kit.integer(t['quoted_price'], 1, 5000), 'Giá sai.')
        if 'served' in t:
            kit.need(isinstance(t['served'], dict) and isinstance(t['served'].get('eggs'), list), 'Khay đã phục vụ sai.')
        if t.get('gen'):
            _bool(t.get('diet'))
    elif job == 'booking':
        kit.need(isinstance(t['hold'], list) and len(t['hold']) <= 2 and len(set(t['hold'])) == len(t['hold'])
                 and all(r in ROOM_INDEX for r in t['hold']), 'Phòng giữ sai.')
        q = t['quote']
        kit.need(q is None or (isinstance(q, dict) and set(q) == {'total', 'deposit'}), 'Báo giá sai.')
        if q:
            kit.integer(q['total'], 0, 100000)
            kit.integer(q['deposit'], 0, q['total'])
        kit.need(t['decline_ok'] in (None, True, False), 'Trạng thái từ chối sai.')
        if t.get('gen'):
            kit.need(t.get('rate') in RATE_IDS, 'Mức giá sai.')
            _bool(t.get('asked_budget'))
            kit.integer(t.get('haggles'), 0, 1000)
    elif job == 'recommend':
        kit.need(isinstance(t['picks'], list) and len(t['picks']) <= 3 and len(set(t['picks'])) == len(t['picks'])
                 and all(p in PLACE_INDEX for p in t['picks']), 'Lịch trình sai.')
        kit.need(all(q in PROBE_IDS for q in t['inspected']) and len(set(t['inspected'])) == len(t['inspected']), 'Câu hỏi sai.')
    elif job == 'claim':
        kit.need(isinstance(t.get('asked'), list) and len(set(t['asked'])) == len(t['asked']) and all(q in CLAIM_Q_IDS for q in t['asked']),
                 'Câu hỏi xác minh sai.')
        kit.need(t.get('choice') in (None,) + CLAIM_CHOICES, 'Cách xử lý đồ thất lạc sai.')
    else:
        raise kit.eng().GameError('Loại việc homestay không hợp lệ.')


def validate_data(c: dict) -> None:
    d = _data(c)
    kit.mark_legacy(c, ID)
    kit.need(isinstance(d.get('rooms'), dict) and set(d['rooms']) == set(ROOM_INDEX), 'Sơ đồ phòng sai.')
    for rid, r in d['rooms'].items():
        kit.need(isinstance(r, dict) and set(_room_state('clean')) <= set(r), 'Phòng thiếu dữ liệu.')
        kit.need(r['status'] in ROOM_STATUS, 'Trạng thái phòng sai.')
        kit.need(r['guest'] is None or (isinstance(r['guest'], str) and len(r['guest']) <= 80), 'Tên khách phòng sai.')
        kit.need(r['task'] is None or (isinstance(r['task'], str) and len(r['task']) <= 80), 'Liên kết phòng sai.')
        kit.need(r['note'] is None or (isinstance(r['note'], str) and len(r['note']) <= 120), 'Ghi chú phòng sai.')
        kit.integer(r['until'], 0, 10**7)
        kit.integer(r['q'], 0, 5)
        kit.integer(r['mini'], 0, 6)
        kit.integer(r['wear'], 0, 100)
        kit.need(r['snag'] is None or r['snag'] in SNAGS, 'Việc sửa vặt sai.')
        hk = r['hk']
        if hk is not None:
            kit.need(r['status'] == 'dirty' and isinstance(hk, dict) and set(hk) == {'done', 'start', 'slips', 'cost'}, 'Tiến độ dọn phòng sai.')
            kit.need(isinstance(hk['done'], list) and hk['done'][:1] == ['strip'] and len(set(hk['done'])) == len(hk['done'])
                     and all(x in HK_INDEX and x != 'ready' for x in hk['done']), 'Bước dọn phòng sai.')
            kit.need(isinstance(hk['start'], (int, float)) and not isinstance(hk['start'], bool) and 0 <= hk['start'] < 10**11, 'Đồng hồ dọn phòng sai.')
            kit.integer(hk['slips'], 0, 20)
            kit.integer(hk['cost'], 0, 10000)
    kit.need(isinstance(d.get('bookings'), list) and len(d['bookings']) <= 60, 'Lịch đặt phòng sai.')
    for b in d['bookings']:
        kit.need(isinstance(b, dict) and set(('id', 'rooms', 'start', 'nights', 'guests', 'name', 'total', 'deposit', 'task')) <= set(b), 'Đặt phòng thiếu dữ liệu.')
        kit.text(b['id'], 40)
        kit.text(b['name'], 80)
        kit.need(isinstance(b['rooms'], list) and 1 <= len(b['rooms']) <= 2 and len(set(b['rooms'])) == len(b['rooms'])
                 and all(r in ROOM_INDEX for r in b['rooms']), 'Phòng đặt sai.')
        kit.integer(b['start'], 1, 10**7)
        kit.integer(b['nights'], 1, 14)
        kit.integer(b['guests'], 1, 12)
        kit.integer(b['total'], 0, 100000)
        kit.integer(b['deposit'], 0, b['total'])
        kit.need(b['task'] is None or (isinstance(b['task'], str) and len(b['task']) <= 80), 'Liên kết đặt phòng sai.')
        kit.need(b.get('ota') in (None,) + OTAS, 'Kênh đặt phòng sai.')
        kit.need(type(b.get('npc', -1)) is int and -1 <= b.get('npc', -1) < len(PEOPLE), 'Khách đặt phòng sai.')
        kit.need(type(b.get('anniv', 0)) is int and 0 <= b.get('anniv', 0) <= 10**4, 'Đặt phòng số 3 sai.')
    kit.need(isinstance(d.get('lost'), list) and len(d['lost']) <= 40, 'Sổ đồ thất lạc sai.')
    for x in d['lost']:
        kit.need(isinstance(x, dict) and x.get('room') in ROOM_INDEX and x.get('status') in ('kept', 'returned'), 'Đồ thất lạc sai.')
        kit.text(x.get('id'), 40)
        kit.text(x.get('item'), 80)
        kit.integer(x.get('day'), 1, 10**7)
    for k in ('nights_sold', 'walked', 'cleaned', 'arrivals', 'seq'):
        kit.integer(d.get(k), 0, 10**9)
    for k, v in DATA_V2.items():
        if k != 'ota':
            kit.integer(d[k], 0, 10**9)
    kit.need(isinstance(d['ota'], list) and len(d['ota']) <= 40, 'Hộp đơn OTA sai.')
    for o in d['ota']:
        kit.need(isinstance(o, dict) and set(OTA_KEYS) <= set(o) and o['ota'] in OTAS and o['room'] in ROOM_INDEX and o['status'] in OTA_STATUS,
                 'Đơn OTA sai.')
        kit.text(o['id'], 40)
        kit.text(o['name'], 80)
        kit.integer(o['start'], 1, 10**7)
        kit.integer(o['nights'], 1, 14)
        kit.integer(o['guests'], 1, 12)
        kit.integer(o['total'], 0, 100000)
        kit.integer(o['net'], 0, o['total'])
        kit.integer(o['day'], 1, 10**7)
        kit.need(isinstance(o['rooms'], list) and len(o['rooms']) <= 2 and len(set(o['rooms'])) == len(o['rooms'])
                 and all(r in ROOM_INDEX for r in o['rooms']), 'Phòng của đơn OTA sai.')
    kit.desk_validate(d['desk'], DESK)
    _validate_care(d)


def _validate_care(d: dict) -> None:
    kit.need(isinstance(d['stays'], dict) and set(d['stays']) <= set(ROOM_INDEX), 'Sổ khách ở tiếp sai.')
    for rid, st in d['stays'].items():
        kit.need(isinstance(st, dict) and set(st) == set(STAY_KEYS), 'Phiếu khách ở tiếp thiếu dữ liệu.')
        kit.need(d['rooms'][rid]['status'] == 'occupied', 'Phòng trống mà còn phiếu khách ở tiếp.')
        kit.text(st['guest'], 80)
        kit.need(type(st['npc']) is int and -1 <= st['npc'] < len(PEOPLE), 'Khách ở tiếp sai.')
        for k in ('since', 'rolled'):
            kit.integer(st[k], 0, 10**7)
        kit.integer(st['mood'], MOOD_MIN, 100)
        kit.integer(st['nights'], 0, 60)
        kit.integer(st['scored'], 0, 60)
        kit.integer(st['anniv'], 0, 10**4)
        for k in ('dnd', 'cold', 'regular'):
            _bool(st[k])
        kit.need(st['tidy'] in (None,) + TIDY and st['warmed'] in (None, 'wood', 'gas') and st['asked'] in (None, 'ok', 'bad'), 'Việc chăm khách sai.')
        kit.need(st['ask'] in (None,) + tuple(ASK_INDEX) and st['trip'] in (None,) + tuple(TRIP_INDEX) and (st['trip'] is None) == (st['ask'] != 'trip'),
                 'Lời nhờ của khách sai.')
        kit.need(isinstance(st['opts'], list) and len(st['opts']) <= 4 and len(set(st['opts'])) == len(st['opts'])
                 and all(x in PLACE_INDEX for x in st['opts']) and (st['place'] is None or st['place'] in st['opts']), 'Gợi ý đi chơi sai.')
        kit.need(st['low'] is None or (isinstance(st['low'], str) and len(st['low']) <= 200), 'Ghi chú khách sai.')
        kit.need(isinstance(st['log'], list) and len(st['log']) <= STAY_LOG and all(isinstance(x, str) and len(x) <= 200 for x in st['log']),
                 'Nhật ký khách sai.')
    kit.need(isinstance(d['book'], dict) and len(d['book']) <= BOOK_MAX, 'Sổ lưu bút sai.')
    for key, b in d['book'].items():
        kit.need(key in {str(n) for n in BOOK_NPCS} and isinstance(b, dict) and set(b) == set(BOOK_KEYS), 'Trang sổ lưu bút sai.')
        kit.integer(b['visits'], 0, 99)
        kit.integer(b['first'], 1, 10**7)
        kit.integer(b['last'], b['first'], 10**7)
        kit.need(b['room'] in ROOM_INDEX and (b['fav'] is None or b['fav'] in ROOM_INDEX) and b['stars'] in (None, 2, 3, 4, 5), 'Trang sổ lưu bút sai.')
    a = d['anniv']
    kit.need(isinstance(a, dict) and set(a) == {'next', 'year', 'pages'} and isinstance(a['pages'], list) and len(a['pages']) <= 12,
             'Sổ phòng số 3 sai.')
    kit.integer(a['next'], 1, 10**7)
    kit.integer(a['year'], 1, 10**4)
    for pg in a['pages']:
        kit.need(isinstance(pg, dict) and set(pg) == {'year', 'day', 'room', 'stars'} and (pg['room'] is None or pg['room'] in ROOM_INDEX)
                 and pg['stars'] in (None, 2, 3, 4, 5), 'Trang sổ phòng số 3 sai.')
        kit.integer(pg['year'], 1, 10**4)
        kit.integer(pg['day'], 1, 10**7)
    kit.integer(d['garden'], 0, 100)
    kit.integer(d['wood'], 0, WOOD_MAX)
    kit.integer(d['wood_order'], 0, 2 * WOOD_PACK)
    for k in ('deep', 'fixed', 'stay_reviews'):
        kit.integer(d[k], 0, 10**9)
    kit.need(isinstance(d['rating'], list) and len(d['rating']) <= RATING_DAYS
             and all(isinstance(x, list) and len(x) == 2 for x in d['rating']), 'Nhật ký điểm app sai.')
    for day, v in d['rating']:
        kit.integer(day, 1, 10**7)
        kit.integer(v, 10, 50)


# ======================================================================== care loop (sub-project 3)
# Rooms age with every night slept in them, guests who stay have small daily needs, regulars remember the house,
# the hydrangeas and the woodpile need tending, and the app rating follows how people felt. See
# docs/superpowers/specs/2026-09-29-homestay-care-design.md.
WEAR_NIGHT = 10            # upkeep lost per occupied night …
WEAR_RAIN = 4              # … more on a damp, rainy day …
WEAR_BALCONY = 4           # … and on the wooden lake balcony
WEAR_LOW = 50              # a turnover loses a quality point below this …
WEAR_BAD = 25              # … and two below this
WEAR_STAY = 40             # a staying guest notices a worn room below this
SNAG_AT = 60               # crossing below this at night brings a small repair
DEEP_COST = 3
FIX_COST = 4
SNAGS = ['Bản lề cửa kêu cót két', 'Vòi lavabo nhỏ giọt', 'Rèm cửa sổ tuột móc', 'Ổ cắm đầu giường lỏng', 'Chân ghế ban công lung lay']
MOOD_START = 70
MOOD_MIN = 25
REGULAR_MOOD = 5           # per earlier visit, up to two
DND_P = 0.25
ASK_P = 0.6
STAY_LOG = 3
DELTA = dict(full=8, tidy_miss=-10, basket=-4, intrude=-15, cold_miss=-18, warm=4, ask_miss=-8, ask_bad=-10, ask_ok=4,
             bloom=3, wilt=-4, worn=-5, snag=-5)
LOW = dict(tidy_miss='Ở mấy hôm mà phòng không ai dọn, khăn ướt để nguyên cả ngày.',
           intrude='Đã treo biển xin đừng làm phiền mà vẫn có người mở cửa vào phòng.',
           cold_miss='Đêm rét buốt mà phòng không sưởi, không ai mang thêm chăn.',
           ask_bad='Nhờ gợi ý chỗ đi chơi mà được chỉ tới nơi chẳng hợp với nhà mình.',
           ask_miss='Nhờ một việc nhỏ mà cả ngày không thấy ai làm.',
           worn='Phòng ở lâu mới thấy ẩm mốc, rèm bám bụi.',
           snag='Đồ trong phòng hỏng lặt vặt mà mấy hôm không ai sửa.')
ASKS = [dict(id='trip', emoji='🗺️', label='Gợi ý một nơi đi chơi hôm nay', act='Gợi ý', use={}),
        dict(id='box', emoji='🥡', label='Gói phần ăn sáng mang đi săn mây', act='Gói phần ăn sáng', use={'bread': 1, 'milk': 1},
             say='Sáng mai đi săn mây từ 4 giờ, gói giúp một phần ăn sáng mang theo nhé.'),
        dict(id='tea', emoji='🫖', label='Pha ấm trà gừng nóng buổi tối', act='Pha trà gừng', use={},
             say='Tối nay pha giúp một ấm trà gừng nóng nhé, trời se lạnh quá.'),
        dict(id='umbrella', emoji='☂️', label='Cho mượn ô và áo mưa', act='Đưa ô, áo mưa', use={}, mods=('rain',),
             say='Mưa quá, nhà mình có ô với áo mưa cho mượn không?')]
ASK_INDEX = {x['id']: x for x in ASKS}
TRIPS = [dict(id='gentle', say='Hôm nay đi dạo chỗ nào nhẹ nhàng, không leo dốc, không bậc thang?', want=['flat'], avoid=['stairs', 'slope']),
         dict(id='indoor', say='Mưa thế này, có chỗ nào trong nhà mà vẫn vui không?', want=['indoor'], avoid=[], mods=('rain',)),
         dict(id='cheap', say='Có chỗ nào miễn phí mà chụp ảnh đẹp không?', want=['free', 'photo'], avoid=[]),
         dict(id='kids', say='Có bé nhỏ đi cùng, chỗ nào gần mà hợp trẻ con?', want=['kids', 'near'], avoid=[]),
         dict(id='night', say='Tối nay đi đâu ăn uống cho vui?', want=['night', 'food'], avoid=[]),
         dict(id='quiet', say='Muốn một chỗ yên tĩnh, không đông người.', want=['quiet'], avoid=['crowd'])]
TRIP_INDEX = {x['id']: x for x in TRIPS}
TRIP_BY = {0: 'quiet', 1: 'cheap', 2: 'gentle', 3: 'kids', 4: 'night', 5: 'quiet', 14: 'gentle'}
TIDY = ('tidy', 'door', 'basket', 'intrude')
WOOD_PACK = 5
WOOD_COST = 6
WOOD_MAX = 30
GARDEN_TEND = 35
GARDEN_BLOOM = 70
GARDEN_WILT = 35
GARDEN_DECAY = dict(rain=0, cold=6)        # other days: 10
RATING_DAYS = 7
FEATURE_AT = 4.8
FEATURE_MIN = 6
ANNIV_FIRST = 6            # the couple of room 3 first arrive on this day …
ANNIV_EVERY = 12           # … and come back every 12 days (their “year”)
ANNIV_LEAD = 2             # they call this many days ahead
ANNIV_NIGHTS = 2
ANNIV_NPC = 2
ANNIV_NAME = 'Cô Diệp & Chú Khang'
ANNIV_ROOM = 'thong'       # door number 3, the window over the pine hill
BOOK_NPCS = (0, 1, 2, 3, 4, 5, 6, 9, 10, 14)
BOOK_MAX = 20
GUEST_NOTES = {
    0: [('🤫', 'Ngủ tỉnh: xếp phòng yên, xa cầu thang gỗ.'), ('🌅', 'Mê view: thích Đồi Thông hoặc Ban Công Hồ.')],
    1: [('🛵', 'Đi xe máy: cần chỗ dựng xe qua đêm.'), ('🥖', 'Ăn sáng nhiều bánh mì, ví mỏng.')],
    2: [('🥶', 'Sợ lạnh: đêm lạnh nhớ sưởi, thêm chăn.'), ('🗝️', 'Năm nào cũng xin phòng số 3 (Đồi Thông).')],
    3: [('🧸', 'Hai bé hay để quên đồ chơi: kiểm phòng thật kỹ.'), ('🥛', 'Hai bé uống sữa ấm buổi sáng.')],
    4: [('📸', 'Săn ảnh: hỏi giờ mây đẹp, thích chỗ miễn phí.'), ('🌙', 'Hay về khuya: nhắc giờ yên tĩnh thật nhẹ nhàng.')],
    5: [('🍵', 'Thích trà, ghét ồn.'), ('🌸', 'Hay khen vườn cẩm tú cầu.')],
    6: [('🧾', 'Cần hóa đơn công ty rõ ràng.'), ('⏰', 'Đi sớm: bữa sáng trước 7 giờ.')],
    9: [('🎧', 'Hay để quên tai nghe.'), ('🛏️', 'Thích phòng Sương Sớm, hai giường đơn.')],
    10: [('💻', 'Làm việc từ xa: cần bàn và wifi mạnh.'), ('💬', 'Hay mặc cả, thích giá ở dài ngày.')],
    14: [('🪜', 'Sợ cầu thang: chỉ xếp tầng trệt.'), ('🫚', 'Thích trà gừng.')],
}
MOOD_WORDS = [(85, 'Rất vui'), (70, 'Vui vẻ'), (50, 'Tạm ổn'), (0, 'Không vui')]
WEAR_WORDS = [(80, 'Sạch thơm'), (50, 'Hơi cũ'), (25, 'Cần tổng vệ sinh'), (0, 'Ẩm mốc')]
STAY_KEYS = ('guest', 'npc', 'since', 'mood', 'rolled', 'dnd', 'tidy', 'cold', 'warmed', 'ask', 'trip', 'opts', 'asked', 'place',
             'nights', 'scored', 'regular', 'anniv', 'low', 'log')
BOOK_KEYS = ('visits', 'first', 'last', 'room', 'fav', 'stars')
DATA_CARE = dict(stays={}, book={}, anniv=dict(next=ANNIV_FIRST, year=12, pages=[]), garden=80, wood=4, wood_order=0, rating=[],
                 deep=0, fixed=0, stay_reviews=0)
REVIEW_TEXT = {5: 'Mấy ngày ở nhà Mây như ở nhà mình: phòng ấm, khăn thơm, nhờ gì cũng có người lo.',
               4: 'Ở mấy hôm thoải mái, chủ nhà để ý tới khách.',
               3: 'Phòng ổn, nhưng ở dài ngày thì thấy chưa được chăm lắm.'}


def _word(words: list, v: int) -> str:
    return next(w for top, w in words if v >= top)


def _guest_npc(name) -> int:
    return next((i for i, p in enumerate(PEOPLE) if p[0] == name), -1)


def _stay_new(guest: str, npc: int, since: int, visits: int = 0, anniv: int = 0) -> dict:
    return dict(guest=guest, npc=npc, since=since, mood=min(100, MOOD_START + REGULAR_MOOD * min(2, visits)), rolled=0, dnd=False, tidy=None,
                cold=False, warmed=None, ask=None, trip=None, opts=[], asked=None, place=None, nights=0, scored=0, regular=visits > 0,
                anniv=anniv, low=None, log=[])


def _sync_stays(d: dict, day: int) -> None:
    stays = d.get('stays')
    if not isinstance(stays, dict):
        return
    for rid in list(stays):
        r, st = d['rooms'].get(rid), stays[rid]
        if (rid not in ROOM_INDEX or not isinstance(r, dict) or r.get('status') != 'occupied' or not isinstance(st, dict)
                or st.get('guest') != r.get('guest')):
            del stays[rid]
    for rid, r in d['rooms'].items():
        if rid in ROOM_INDEX and isinstance(r, dict) and r.get('status') == 'occupied' and rid not in stays and isinstance(r.get('guest'), str):
            stays[rid] = _stay_new(r['guest'][:80], _guest_npc(r['guest']), day)


def _stay_open(c: dict, rid: str, guest: str, npc: int, anniv: int = 0) -> dict:
    """A guest moves in (check-in at the desk or a booked arrival in the evening)."""
    d = _data(c)
    rec = d['book'].get(str(npc)) if npc in BOOK_NPCS else None
    st = _stay_new(guest[:80], npc, c['day'], rec['visits'] if rec else 0, anniv)
    d['stays'][rid] = st
    return st


def _stay_log(st: dict, text: str) -> None:
    st['log'] = ar.last(st['log'] + [text], STAY_LOG, 'homestay.stay_log', None)


def _stars(mood: int) -> int:
    return 5 if mood >= 85 else 4 if mood >= 70 else 3 if mood >= 50 else 2


def _trip_fits(trip: dict, place: dict) -> bool:
    tags = set(place['tags'])
    return all(w in tags for w in trip['want']) and not tags & set(trip['avoid'])


def _roll_stays(c: dict) -> None:
    """Morning: what each guest who sleeps here again tonight will need today (seeded by room, guest and day)."""
    d = _data(c)
    day, mod = c['day'], today(c['day'])['id']
    for rid in ROOM_INDEX:
        st, r = d['stays'].get(rid), d['rooms'][rid]
        if not st or r['task'] or r['until'] <= day or st['since'] >= day or st['rolled'] == day:
            continue
        rng = kit.rng(ID, 'stay', rid, st['guest'], day)
        st.update(rolled=day, dnd=rng.random() < DND_P, tidy=None, warmed=None, ask=None, trip=None, opts=[], asked=None, place=None)
        st['cold'] = mod == 'cold' or (mod == 'rain' and rng.random() < 0.5)
        if rng.random() < ASK_P:
            ask = rng.choice([a for a in ASKS if mod in a.get('mods', (mod,))])
            st['ask'] = ask['id']
            if ask['id'] == 'trip':
                pool = [x for x in TRIPS if mod in x.get('mods', (mod,))]
                pick = TRIP_BY.get(st['npc'])
                trip = TRIP_INDEX['indoor'] if mod == 'rain' and rng.random() < 0.5 else TRIP_INDEX[pick] if pick else rng.choice(pool)
                fits = [p['id'] for p in PLACES if _trip_fits(trip, p)]
                other = [p['id'] for p in PLACES if p['id'] not in fits]
                opts = [rng.choice(fits)] + rng.sample(other, 3)
                rng.shuffle(opts)
                st.update(trip=trip['id'], opts=opts)


def _stay_todo(st: dict, day: int) -> int:
    if st['rolled'] != day:
        return 0
    return (st['tidy'] is None) + bool(st['cold'] and not st['warmed']) + bool(st['ask'] and not st['asked'])


def _score_stays(c: dict) -> tuple[int, int]:
    """Evening: each staying guest's day becomes mood. Returns (guests scored, needs missed)."""
    d = _data(c)
    day = c['day']
    garden = d['garden']
    scored = missed = 0
    for rid, st in d['stays'].items():
        if st['rolled'] != day:
            continue
        r = d['rooms'][rid]
        rows, words = [], []
        tidy = st['tidy']
        if tidy in ('tidy', 'door'):
            words.append('phòng gọn' if tidy == 'tidy' else 'khăn để ở cửa')
        elif tidy == 'basket':
            rows.append((DELTA['basket'], None))
            words.append('chỉ để khăn ở cửa')
        elif tidy == 'intrude':
            rows.append((DELTA['intrude'], LOW['intrude']))
            words.append('bị làm phiền')
        else:
            rows.append((DELTA['tidy_miss'], LOW['tidy_miss']))
            words.append('không ai dọn')
            missed += 1
        if st['cold']:
            if st['warmed']:
                rows.append((DELTA['warm'], None))
                words.append('ấm áp')
            else:
                rows.append((DELTA['cold_miss'], LOW['cold_miss']))
                words.append('lạnh buốt')
                missed += 1
        if st['ask']:
            if st['asked'] == 'ok':
                rows.append((DELTA['ask_ok'], None))
                words.append('được giúp')
            elif st['asked'] == 'bad':
                rows.append((DELTA['ask_bad'], LOW['ask_bad']))
                words.append('đi nhầm chỗ')
            else:
                rows.append((DELTA['ask_miss'], LOW['ask_miss']))
                words.append('nhờ không ai làm')
                missed += 1
        if tidy in ('tidy', 'door') and (not st['cold'] or st['warmed']) and (not st['ask'] or st['asked'] == 'ok'):
            rows.append((DELTA['full'], None))
        if garden >= GARDEN_BLOOM:
            rows.append((DELTA['bloom'], None))
        elif garden < GARDEN_WILT:
            rows.append((DELTA['wilt'], None))
            words.append('vườn héo')
        if r['wear'] < WEAR_STAY:
            rows.append((DELTA['worn'], LOW['worn']))
            words.append('phòng ẩm')
        if r['snag']:
            rows.append((DELTA['snag'], f'{r["snag"]} mà mấy hôm không ai sửa.'))
            words.append(r['snag'].lower())
        delta = sum(x for x, _ in rows)
        worst = min(rows, key=lambda x: x[0]) if rows else (0, None)
        if worst[1] and worst[0] <= -5:
            st['low'] = worst[1]
        st['mood'] = max(MOOD_MIN, min(100, st['mood'] + delta))
        st['scored'] += 1
        _stay_log(st, f'Ngày {day}: {", ".join(words)} → {_word(MOOD_WORDS, st["mood"]).lower()} ({delta:+d})')
        scored += 1
    for st in d['stays'].values():
        st['nights'] = min(60, st['nights'] + 1)
    return scored, missed


def _depart(s: dict, c: dict, rid: str | None, t: dict | None = None) -> dict | None:
    """A guest leaves: the guest book remembers them, and a stay that was looked after (or not) becomes a review.
    Leaving through a check-out ticket, the stay becomes a row of that ticket's review instead."""
    if not rid:
        return None
    d = _data(c)
    st = d['stays'].pop(rid, None)
    if not st:
        return None
    npc = _npc_index(t) if t else st['npc']
    stars = _stars(st['mood']) if st['scored'] else None
    if npc in BOOK_NPCS:
        b = d['book'].setdefault(str(npc), dict(visits=0, first=c['day'], last=c['day'], room=rid, fav=None, stars=None))
        b.update(visits=min(99, b['visits'] + 1), last=c['day'], room=rid)
        if stars:
            b['stars'] = stars
        if st['mood'] >= 70:
            b['fav'] = rid
        if len(d['book']) > BOOK_MAX:
            del d['book'][min(d['book'], key=lambda k: d['book'][k]['last'])]
    if st['anniv']:
        _anniv_page(d, st['anniv'], c['day'], rid, stars)
    if stars is None:
        return None
    if t is None:
        text = REVIEW_TEXT.get(stars) or f'Ở dài ngày mới thấy: {(st["low"] or "chẳng ai hỏi han gì").lower()}'
        if stars == 3 and st['low']:
            text += ' ' + st['low']
        kit.review(s, c, kit.npc_id(ID, npc if 0 <= npc < len(PEOPLE) else 8), stars, text, f'stay-{rid}-{c["day"]}')
        d['stay_reviews'] += 1
    return dict(mood=st['mood'], nights=st['nights'], stars=stars, low=st['low'])


def _anniv_page(d: dict, year: int, day: int, rid: str | None, stars) -> None:
    pages = d['anniv']['pages']
    if not any(p['year'] == year for p in pages):
        d['anniv']['pages'] = ar.last(pages + [dict(year=year, day=day, room=rid, stars=stars)], 12, 'homestay.anniv', None)


def _anniv_call(s: dict, c: dict) -> None:
    """Two days ahead, Cô Diệp calls for room 3 — as every year."""
    d = _data(c)
    a, day = d['anniv'], c['day']
    if day < a['next'] - ANNIV_LEAD:
        return
    start, year = max(a['next'], day + 1), a['year']
    a.update(next=start + ANNIV_EVERY, year=year + 1)
    ground = [ANNIV_ROOM] + [r['id'] for r in ROOMS if r['id'] != ANNIV_ROOM and not r['stairs'] and r['cap'] >= 2]
    rid = next((x for x in ground if ROOM_INDEX[x]['unlock'] <= kit.level(c) and _blocked(c, x, start, ANNIV_NIGHTS) is None), None)
    if rid is None:
        _anniv_page(d, year, day, None, None)
        kit.log(s, c, 'homestay', f'📞 {ANNIV_NAME} gọi xin phòng số 3 cho ngày {start}, nhưng lịch kín hết phòng tầng trệt. Cô hẹn năm sau.')
        return
    total = kit.price(c, rid, SPEC['prices'][rid]) * ANNIV_NIGHTS
    deposit = math.ceil(total * DEPOSIT_PCT / 100)
    d['bookings'] = ar.last(d['bookings'] + [dict(id=f'anniv-{year}', rooms=[rid], start=start, nights=ANNIV_NIGHTS, guests=2,
                                          name=f'{ANNIV_NAME} (năm thứ {year})', total=total, deposit=deposit, task=None, npc=ANNIV_NPC,
                                          anniv=year)], 60, 'homestay.bookings', c)
    kit.money(s, c, deposit, f'{ANNIV_NAME} chuyển cọc phòng ngày {start}', f'anniv-{year}', category='room')
    kit.bank(deposit)
    where = 'phòng số 3 như mọi năm' if rid == ANNIV_ROOM else f'phòng {ROOM_INDEX[rid]["name"]} (phòng số 3 đã có khách)'
    kit.log(s, c, 'homestay', f'📞 {ANNIV_NAME} gọi đặt {where} từ ngày {start}, {ANNIV_NIGHTS} đêm — năm thứ {year}. Đã nhận {deposit} xu cọc.')


def _wear_night(c: dict) -> list:
    """The night passes: occupied rooms age; a room slipping under the line gets a small repair."""
    d = _data(c)
    rain = today(c['day'])['id'] == 'rain'
    found = []
    for i, r in enumerate(ROOMS):
        room = d['rooms'][r['id']]
        if room['status'] != 'occupied':
            continue
        before = room['wear']
        room['wear'] = max(0, before - WEAR_NIGHT - (WEAR_RAIN if rain else 0) - (WEAR_BALCONY if r['id'] == 'ho' else 0))
        if before >= SNAG_AT > room['wear'] and not room['snag']:
            room['snag'] = SNAGS[4] if r['id'] == 'ho' and c['day'] % 2 == 0 else SNAGS[(c['day'] + i) % 4]
            found.append(f'{r["name"]}: {room["snag"].lower()}')
    return found


def _featured(c: dict) -> bool:
    stars = [p['stars'] for p in c.get('feed', []) if p.get('kind') == 'review' and type(p.get('stars')) is int][:12]
    return len(stars) >= FEATURE_MIN and sum(stars) / len(stars) >= FEATURE_AT


def _care_close(s: dict, c: dict) -> list:
    """Evening chores of the care loop, before the arrivals: stays scored, the garden dries, the rating is logged."""
    d = _data(c)
    lines = []
    n, missed = _score_stays(c)
    if n:
        lines.append(f'Khách ở tiếp: {n} phòng' + (f' · {missed} việc chăm bị bỏ lỡ.' if missed else ' · chăm đủ cả.'))
    mod = today(c['day'])['id']
    d['garden'] = max(0, d['garden'] - GARDEN_DECAY.get(mod, 10))
    if d['garden'] < GARDEN_WILT:
        lines.append(f'🌸 Vườn cẩm tú cầu đang héo ({d["garden"]}%) — mai nhớ tưới, tỉa.')
    return lines


def _care_night(s: dict, c: dict) -> list:
    """After the arrivals: rooms age overnight, the rating is logged, tomorrow's cold is announced."""
    d = _data(c)
    lines = []
    found = _wear_night(c)
    if found:
        lines.append('🔧 Cần sửa vặt: ' + '; '.join(found) + '.')
    score = _ota_score(c)
    if not d['rating'] or d['rating'][-1][0] != c['day']:
        d['rating'] = ar.last(d['rating'] + [[c['day'], int(round(score * 10))]], RATING_DAYS, 'homestay.rating', c)
    nxt = today(c['day'] + 1)['id']
    staying = sum(1 for rid, r in d['rooms'].items() if r['status'] == 'occupied' and r['until'] > c['day'] + 1)
    if nxt in ('cold', 'rain') and staying:
        lines.append(f'🪵 Mai {"rét đậm" if nxt == "cold" else "mưa lạnh"}: {staying} phòng có khách ở tiếp, còn {d["wood"]} bó củi'
                     + (f' (+{d["wood_order"]} bó sáng mai tới).' if d['wood_order'] else '.'))
    return lines


def _care_start(s: dict, c: dict) -> None:
    """Morning: the woodpile delivery, the room-3 call, today's needs of the guests who stay."""
    d = _data(c)
    if d['wood_order']:
        d['wood'] = min(WOOD_MAX, d['wood'] + d['wood_order'])
        kit.log(s, c, 'homestay', f'🪵 Chú Tư chở {d["wood_order"]} bó củi khô lên dốc, xếp dưới mái hiên.')
        d['wood_order'] = 0
    _anniv_call(s, c)
    _roll_stays(c)


# ---------------------------------------------------------------- care commands
def _room_arg(c: dict, p: dict) -> tuple[str, dict]:
    rid = kit.one_of(p.get('room'), ROOM_INDEX, 'Phòng không tồn tại.')
    kit.need(ROOM_INDEX[rid]['unlock'] <= kit.level(c), f'Phòng {ROOM_INDEX[rid]["name"]} mở ở cấp {ROOM_INDEX[rid]["unlock"]}.')
    return rid, _data(c)['rooms'][rid]


def _deep(s: dict, c: dict, p: dict) -> dict:
    rid, r = _room_arg(c, p)
    name = ROOM_INDEX[rid]['name']
    kit.need(r['status'] in ('clean', 'dirty') and not r['hk'] and not r['task'],
             f'Phòng {name} đang có khách, đang sửa hoặc đang dọn dở — tổng vệ sinh khi phòng trống.')
    kit.need(r['wear'] < 100, f'Phòng {name} vừa tổng vệ sinh, còn tươm tất lắm.')
    kit.confirm(p, 'Xác nhận tổng vệ sinh phòng (vật tư chống ẩm, dầu lau gỗ).')
    kit.money(s, c, -DEEP_COST, f'Vật tư tổng vệ sinh phòng {name}', rid, category='repair')
    r['wear'] = 100
    d = _data(c)
    d['deep'] += 1
    kit.metric(c, 'hs_deep')
    extra = ' Lau lan can gỗ ban công, quét lá, tưới giàn hoa ngoài lan can.' if rid == 'ho' else ''
    return dict(message=f'Tổng vệ sinh phòng {name}: giặt rèm, lau gầm giường, xịt chống ẩm góc tường, phơi nệm.{extra} Phòng thơm lại mùi gỗ thông (−{DEEP_COST} xu).',
                celebrate=True)


def _fix(s: dict, c: dict, p: dict) -> dict:
    rid, r = _room_arg(c, p)
    name = ROOM_INDEX[rid]['name']
    kit.need(r['snag'], f'Phòng {name} không có gì cần sửa vặt.')
    kit.need(r['status'] != 'maintenance', f'Phòng {name} đang chờ thợ sửa lớn — thợ sẽ sửa luôn.')
    kit.confirm(p, 'Xác nhận mua đồ sửa vặt.')
    kit.money(s, c, -FIX_COST, f'Sửa vặt phòng {name}: {r["snag"].lower()}', rid, category='repair')
    snag, r['snag'] = r['snag'], None
    d = _data(c)
    d['fixed'] += 1
    kit.metric(c, 'hs_fix')
    st = d['stays'].get(rid)
    if st:
        _stay_log(st, f'Ngày {c["day"]}: đã sửa {snag.lower()}')
    return dict(message=f'Đã sửa xong: {snag.lower()} (−{FIX_COST} xu).' + (' Khách đi chơi về không còn phải phiền.' if st else ''))


def _garden(s: dict, c: dict, p: dict) -> dict:
    d = _data(c)
    kit.need(d['garden'] < 100, 'Vườn cẩm tú cầu đang đẹp nhất rồi.')
    before = d['garden']
    d['garden'] = min(100, before + GARDEN_TEND)
    kit.metric(c, 'hs_garden')
    word = 'nở rộ' if d['garden'] >= GARDEN_BLOOM else 'tươi lại dần'
    return dict(message=f'Tưới gốc, ngắt hoa tàn, tỉa lá úa quanh lối đi. Vườn cẩm tú cầu {word} ({before}% → {d["garden"]}%).')


def _wood(s: dict, c: dict, p: dict) -> dict:
    d = _data(c)
    kit.need(d['wood'] + d['wood_order'] + WOOD_PACK <= WOOD_MAX, f'Mái hiên chỉ chứa {WOOD_MAX} bó củi.')
    kit.need(d['wood_order'] < 2 * WOOD_PACK, 'Đã đặt đủ củi cho chuyến sáng mai rồi.')
    kit.confirm(p, 'Xác nhận đặt củi (sáng mai mới chở tới).')
    kit.money(s, c, -WOOD_COST, f'Đặt {WOOD_PACK} bó củi khô của Chú Tư', None, category='stock')
    d['wood_order'] += WOOD_PACK
    return dict(message=f'Đã đặt {WOOD_PACK} bó củi (−{WOOD_COST} xu). Chú Tư chở lên sáng mai — đêm nay vẫn dùng củi đang có ({d["wood"]} bó) hoặc gas.')


def _stay_act(s: dict, c: dict, p: dict) -> dict:
    d = _data(c)
    rid = kit.one_of(p.get('room'), ROOM_INDEX, 'Phòng không tồn tại.')
    name = ROOM_INDEX[rid]['name']
    st = d['stays'].get(rid)
    kit.need(st and st['rolled'] == c['day'], f'Phòng {name} hôm nay không có khách ở tiếp cần chăm.')
    do = kit.one_of(p.get('do'), ('tidy', 'door', 'warm', 'ask'), 'Việc chăm khách không hợp lệ.')
    if do in ('tidy', 'door'):
        kit.need(st['tidy'] is None, f'Phòng {name} hôm nay đã lo khăn và dọn rồi.')
        kit.need(kit.stock(c, 'towel') >= 2, 'Thiếu khăn tắm (cần 2). Mở Kho để nhập thêm.')
        kit.take(c, 'towel', 2)
        kit.metric(c, 'hs_stay')
        if do == 'tidy' and st['dnd']:
            st['tidy'] = 'intrude'
            _stay_log(st, f'Ngày {c["day"]}: bị gõ cửa dù đã treo biển')
            return dict(message='Gõ cửa bước vào… khách đang nghỉ, biển “Xin đừng làm phiền” treo ngay tay nắm cửa. Khách khó chịu ra mặt.',
                        refused=True)
        if do == 'tidy':
            st['tidy'] = 'tidy'
            return dict(message=f'Phòng {name}: thay khăn, đổ rác, kéo phẳng chăn, lau bàn — gọn như lúc mới nhận.')
        st['tidy'] = 'door' if st['dnd'] else 'basket'
        if st['dnd']:
            return dict(message='Để giỏ khăn sạch và túi rác mới trước cửa, không gõ. Khách nhắn cảm ơn vì được yên tĩnh.', celebrate=True)
        return dict(message='Để giỏ khăn trước cửa. Phòng hôm nay vẫn chưa ai vào dọn, khăn ướt vẫn nằm đó.')
    if do == 'warm':
        kit.need(st['cold'], f'Đêm nay phòng {name} không cần sưởi thêm.')
        kit.need(st['warmed'] is None, 'Đã sưởi phòng này rồi.')
        how = kit.one_of(p.get('how'), ('wood', 'gas'), 'Chọn củi hoặc gas.')
        if how == 'wood':
            kit.need(d['wood'] >= 1, 'Hết củi rồi. Đặt củi hôm nay thì sáng mai mới có — đêm nay dùng gas.')
            d['wood'] -= 1
        else:
            kit.need(kit.stock(c, 'heater_gas') >= 1, 'Hết bình gas máy sưởi. Mở Kho để nhập, hoặc dùng củi.')
            kit.take(c, 'heater_gas', 1)
        st['warmed'] = how
        kit.metric(c, 'hs_stay')
        what = 'Nhóm lò củi nhỏ trong phòng, chắn lưới, mở hé cửa thông gió' if how == 'wood' else 'Lắp bình gas mới cho máy sưởi, thử lửa, mở hé cửa thông gió'
        return dict(message=f'{what}, trải thêm chăn lông. Đêm nay phòng {name} ấm áp.')
    kit.need(st['ask'], 'Hôm nay khách không nhờ gì thêm.')
    kit.need(st['asked'] is None, 'Đã làm việc khách nhờ rồi.')
    ask = ASK_INDEX[st['ask']]
    kit.metric(c, 'hs_stay')
    if st['ask'] == 'trip':
        place = kit.one_of(p.get('place'), st['opts'], 'Chọn một trong bốn nơi trên phiếu.')
        trip, pl = TRIP_INDEX[st['trip']], PLACE_INDEX[place]
        ok = _trip_fits(trip, pl)
        st.update(asked='ok' if ok else 'bad', place=place)
        if ok:
            return dict(message=f'Gợi ý {pl["emoji"]} {pl["name"]}: {pl["blurb"]} Khách gật gù, chụp lại bản đồ.', celebrate=True)
        clash = [TAG_NAMES[x] for x in pl['tags'] if x in trip['avoid']]
        miss = [TAG_NAMES[x] for x in trip['want'] if x not in pl['tags']]
        why = ('chỗ đó ' + ', '.join(clash)) if clash else ('không ' + ', '.join(miss))
        _stay_log(st, f'Ngày {c["day"]}: được chỉ tới {pl["name"]} — {why}')
        return dict(message=f'Khách đi {pl["name"]} về, thở dài: “{why[0].upper() + why[1:]}, không đúng cái mình cần.”', refused=True)
    for item, q in ask['use'].items():
        kit.need(kit.stock(c, item) >= q, f'Thiếu {ITEM_INDEX[item]["name"]} (cần {q}). Mở Kho để nhập thêm.')
    for item, q in ask['use'].items():
        kit.take(c, item, q)
    st['asked'] = 'ok'
    return dict(message={'box': 'Gói ổ bánh mì nướng giòn và hộp sữa ấm vào túi giấy, kèm khăn ướt. Khách hẹn mang ảnh biển mây về khoe.',
                         'tea': 'Đun ấm trà gừng mật ong, mang lên kèm đĩa mứt. Khách ngồi ban công nhâm nhi.',
                         'umbrella': 'Đưa hai cái ô và áo mưa của nhà, dặn đường đất trơn.'}[st['ask']])


# ---------------------------------------------------------------- care: public view
def _care_rows(c: dict, d: dict) -> list:
    day, rows = c['day'], []
    for r in ROOMS:
        st = d['stays'].get(r['id'])
        if not st or st['rolled'] != day:
            continue
        name = f'{r["name"]} (số {r["no"]})'
        tidy = st['tidy']
        rows.append(dict(ok=True if tidy in ('tidy', 'door') else False if tidy in ('intrude', 'basket') else None, icon='🚪' if st['dnd'] else '🧺',
                         label=f'{name}: ' + ('để khăn ở cửa' if st['dnd'] else 'dọn phòng giữa kỳ'),
                         note='biển “Xin đừng làm phiền” — không gõ cửa' if st['dnd'] else '2 khăn tắm',
                         tone='warn' if st['dnd'] and tidy is None else ''))
        if st['cold']:
            rows.append(dict(ok=True if st['warmed'] else None, icon='🔥', label=f'{name}: sưởi đêm lạnh', note='1 bó củi hoặc 1 bình gas',
                             tone='danger' if not st['warmed'] else ''))
        if st['ask']:
            a = ASK_INDEX[st['ask']]
            rows.append(dict(ok=True if st['asked'] == 'ok' else False if st['asked'] == 'bad' else None, icon=a['emoji'], label=f'{name}: {a["label"].lower()}',
                             note=''))
    for r in ROOMS:
        room = d['rooms'][r['id']]
        if r['unlock'] > kit.level(c):
            continue
        if room['snag']:
            rows.append(dict(ok=None, icon='🔧', label=f'Sửa vặt {r["name"]}: {room["snag"].lower()}', note=f'{FIX_COST} xu', tone='warn'))
        if room['wear'] < WEAR_LOW and room['status'] in ('clean', 'dirty'):
            rows.append(dict(ok=None, icon='🧽', label=f'Tổng vệ sinh {r["name"]}', note=f'độ tươm tất {room["wear"]}% · {DEEP_COST} xu', tone='warn'))
    if d['garden'] < 50:
        rows.append(dict(ok=None, icon='🌸', label='Tưới, tỉa vườn cẩm tú cầu', note=f'vườn {d["garden"]}%', tone='warn' if d['garden'] < GARDEN_WILT else ''))
    nxt = today(day + 1)['id']
    staying = sum(1 for x in d['rooms'].values() if x['status'] == 'occupied' and x['until'] > day + 1)
    if nxt in ('cold', 'rain') and staying and d['wood'] + d['wood_order'] < staying:
        rows.append(dict(ok=None, icon='🪵', label='Đặt củi cho đêm mai', note=f'mai {"rét" if nxt == "cold" else "mưa lạnh"}, {staying} phòng ở tiếp · còn {d["wood"]} bó'))
    a = d['anniv']
    booked = any(b.get('anniv') and b['start'] + b['nights'] > day for b in d['bookings'])
    if not booked and a['next'] - ANNIV_LEAD - 2 <= day < a['next'] - ANNIV_LEAD and ROOM_INDEX[ANNIV_ROOM]['unlock'] <= kit.level(c):
        # A heads-up before their call: keep room 3 free for their nights.
        free = _blocked(c, ANNIV_ROOM, a['next'], ANNIV_NIGHTS) is None
        rows.append(dict(ok=True if free else False, icon='🗝️', label=f'Giữ phòng số 3 trống đêm {a["next"]}–{a["next"] + ANNIV_NIGHTS - 1}',
                         note=f'{ANNIV_NAME} sẽ gọi đặt vào ngày {a["next"] - ANNIV_LEAD}' + ('' if free else ' — phòng số 3 đã có khách những đêm đó'),
                         tone='' if free else 'danger'))
    for b in d['bookings']:
        if b.get('anniv') and b['start'] == day:
            ok = all(d['rooms'][x]['status'] == 'clean' for x in b['rooms'])
            rows.append(dict(ok=True if ok else None, icon='🗝️', label=f'Phòng {ROOM_INDEX[b["rooms"][0]]["name"]} sạch trước tối cho {ANNIV_NAME}',
                             note=f'năm thứ {b["anniv"]}', tone='' if ok else 'warn'))
    return rows


def _book_public(d: dict) -> list:
    rows = []
    for key, b in sorted(d['book'].items(), key=lambda kv: -kv[1]['last']):
        npc = int(key)
        notes = GUEST_NOTES.get(npc, [])[:min(2, b['visits'])]
        rows.append(dict(npc=kit.npc_id(ID, npc), name=PEOPLE[npc][0], visits=b['visits'], last=b['last'], stars=b['stars'],
                         fav=b['fav'], room=b['room'], notes=[dict(emoji=e, text=t) for e, t in notes],
                         more=max(0, min(2, len(GUEST_NOTES.get(npc, []))) - b['visits'])))
    return rows


def _care_public(c: dict, d: dict) -> None:
    """Fields the client needs for the care loop (d is already a copy)."""
    day = c['day']
    for rid, st in d['stays'].items():
        st['word'] = _word(MOOD_WORDS, st['mood'])
        st['todo'] = _stay_todo(st, day)
        if st['ask'] and st['ask'] != 'trip':
            st['say'] = ASK_INDEX[st['ask']]['say']
        if st['trip']:
            st['say'] = TRIP_INDEX[st['trip']]['say']
            st['want'], st['avoid'] = TRIP_INDEX[st['trip']]['want'], TRIP_INDEX[st['trip']]['avoid']
    for rid, r in d['rooms'].items():
        r['wear_word'] = _word(WEAR_WORDS, r['wear'])
    d['care'] = _care_rows(c, d)
    d['book'] = _book_public(d)
    rating = d['rating']
    score = _ota_score(c)
    back = next((v for dd, v in rating if dd <= day - 3), rating[0][1] if rating else None)
    d['rating_view'] = dict(score=score, days=rating, trend=round(score - back / 10, 1) if back is not None else 0.0, featured=_featured(c))
    booked = next((b for b in d['bookings'] if b.get('anniv') and b['start'] + b['nights'] > day), None)
    here = next((rid for rid, st in d['stays'].items() if st['anniv']), None)
    d['anniv'] = dict(d['anniv'], booked=dict(start=booked['start'], room=booked['rooms'][0], year=booked['anniv']) if booked else None,
                      here=here, call=d['anniv']['next'] - ANNIV_LEAD)


# ---------------------------------------------------------------- staff, hints, content
def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = _data(c)
    busy = t and t['career'] == ID and t['known'] and t['job'] == 'checkin' and not t['ci']['verified']
    if e['role'] == 'reception' and not busy:
        # Easy app orders (their own room still free) are synced by the receptionist; clashes stay for you.
        o = next((o for o in d['ota'] if o['status'] == 'new' and ROOM_INDEX[o['room']]['unlock'] <= kit.level(c)
                  and _blocked(c, o['room'], o['start'], o['nights']) is None and ROOM_INDEX[o['room']]['cap'] >= o['guests']), None)
        if o:
            _ota_book(c, o, [o['room']], 'synced')
            d['synced'] += 1
            d['day_synced'] += 1
            return f'Đã đồng bộ đơn {o["ota"]} của {o["name"]} vào đúng phòng {ROOM_INDEX[o["room"]]["name"]}. Đơn trùng phòng vẫn chờ bạn xếp.'
    if e['role'] == 'housekeeping':
        for rid, r in d['rooms'].items():
            if r['status'] != 'dirty':
                continue
            done = r['hk']['done'] if r['hk'] else []
            step = next((x['id'] for x in HK_STEPS if x['id'] not in done), None)
            if step in (None, 'ready'):
                continue
            use = dict(HK_INDEX[step]['use'])
            if step == 'amenity' and r['mini']:
                use['noodles'] = r['mini']
            if any(kit.stock(c, k) < q for k, q in use.items()):
                return f'Muốn dọn phòng {ROOM_INDEX[rid]["name"]} nhưng kho thiếu đồ. Nhập thêm giúp em nhé.'
            if step == 'strip':
                r['hk'] = dict(done=['strip'], start=round(kit.now(), 3), slips=0, cost=0)
            else:
                for k, q in use.items():
                    r['hk']['cost'] += kit.take(c, k, q)
                r['hk']['done'].append(step)
            return f'Phòng {ROOM_INDEX[rid]["name"]}: {HK_INDEX[step]["name"].lower()}. Bạn báo phòng sạch khi kiểm lại.'
        for rid, st in d['stays'].items():
            if st['rolled'] == c['day'] and st['tidy'] is None and kit.stock(c, 'towel') >= 2:
                kit.take(c, 'towel', 2)
                st['tidy'] = 'door' if st['dnd'] else 'tidy'
                return f'Phòng {ROOM_INDEX[rid]["name"]}: ' + ('thấy biển “Xin đừng làm phiền”, để giỏ khăn trước cửa.' if st['dnd']
                                                              else 'dọn giữa kỳ, thay khăn, đổ rác.')
        return 'Đã gấp khăn, phân loại đồ giặt và lau hành lang.'
    if not t or t['career'] != ID or not t['known']:
        return None
    if e['role'] == 'reception' and t['job'] == 'checkin' and not t['ci']['verified']:
        t['ci']['verified'] = True
        return f'Đã dò đúng mã {t["needs"]["code"]} trên app. Bạn vẫn xem giấy tờ và đếm khách.'
    if e['role'] == 'kitchen' and t['job'] == 'breakfast' and t['tray']['bread'] < t['needs']['bread'] and kit.stock(c, 'bread'):
        t['tray']['cost'] += kit.take(c, 'bread', 1)
        t['tray']['bread'] += 1
        return 'Đã nướng sẵn một ổ bánh mì cho khay đang làm.'
    return None


def hint(c: dict, t: dict) -> str:
    base = _hint(t)
    if t.get('gen'):
        base += {'booking': ' Giá: lễ hội khách chịu +30%, thấp điểm nên −15%; chưa chắc thì hỏi ngân sách.',
                 'checkin': ' Cọc chuyển khoản thì mở app ngân hàng đối chiếu, đừng tin ảnh chụp.',
                 'breakfast': ' Hỏi dị ứng, ăn kiêng trước khi đập trứng.'}.get(t['job'], '')
    return base


def _hint(t: dict) -> str:
    return {'booking': 'Xem lịch 7 ngày: chọn phòng trống MỌI đêm, đủ chỗ (bé dưới 6 tuổi ngủ chung không tính), nhận cọc 30%. Không có phòng thì nói thật.',
            'claim': 'So từng câu trả lời với sổ đồ thất lạc: món đồ, phòng, ngày, tên đặt phòng. Lệch chi tiết thì không giao; người nhận hộ thì xác minh qua kênh đặt phòng.',
            'checkin': 'Khớp mã + ngày trên app → xem giấy tờ (không chụp) → đếm khách → phụ thu/từ chối người dư → phòng sạch đủ chỗ → máy sưởi nếu lạnh → trao chìa. Hết sạch phòng thật thì xin lỗi, chuyển sang nhà bên (nhà chịu phí).',
            'checkout': 'Kiểm phòng trước (minibar, hư hỏng, đồ bỏ quên) → trả đồ cho khách → hóa đơn từng dòng: 2 chai nước đầu miễn phí, cà phê miễn phí.',
            'breakfast': 'Một chảo: đập trứng, nhấc đúng giây (lòng đào hay chín kỹ) → bánh mì, sữa, cà phê đúng số → mang ra. Dị ứng trứng: không thêm trứng.',
            'recommend': 'Hỏi ai đi cùng, đi lại, ngân sách, phương tiện, thời tiết → chọn 2–3 nơi không vướng điều khách tránh.'}[t['job']]


def content() -> dict:
    return dict(rooms=ROOMS, hk_steps=HK_STEPS, air=AIR, egg=EGG, bill_lines=BILL_LINES, free_water=FREE_WATER, extra_guest=EXTRA_GUEST,
                kid_free_age=KID_FREE_AGE, deposit_pct=DEPOSIT_PCT, places=PLACES, tag_names=TAG_NAMES, probes=PROBES, horizon=HORIZON,
                jobs=JOB_NAMES, repair_cost=REPAIR_COST, renovation_cost=RENOVATION_COST, today=TODAY, rates=RATES, claim_qs=CLAIM_QS,
                rules=HOUSE_RULES, walk_fee=WALK_FEE, commission=OTA_COMMISSION, air_rain=AIR_RAIN, otas=list(OTAS),
                asks=ASKS, trips=TRIPS, wood_pack=WOOD_PACK, wood_cost=WOOD_COST, wood_max=WOOD_MAX, deep_cost=DEEP_COST, fix_cost=FIX_COST,
                wear_low=WEAR_LOW, garden_bloom=GARDEN_BLOOM, garden_wilt=GARDEN_WILT, anniv_name=ANNIV_NAME, anniv_room=ANNIV_ROOM)


def _p(who, emoji, text):
    return dict(who=who, emoji=emoji, text=text)


SITUATIONS = [
    dict(id='HS-S01', title='Đặt 2 người, tới 4 người', npc=4, tone='tense', min_day=1,
         opening='Mai Chi kéo vali vào, phía sau thêm hai bạn nữa: “Chủ nhà ơi, tụi em ngủ chen chút xíu thôi, phòng 2 người mà nhét 4 đứa được mà!”',
         swap='Bạn là sinh viên, đặt phòng đôi cho rẻ, định rủ thêm bạn ngủ ké.',
         facts=[dict(id='rule', title='Nội quy & phòng cháy', source='Bảng nội quy', text='Phòng Đồi Thông tối đa 2 người. Danh sách lưu trú phải khớp số người thật để khai báo và thoát hiểm.'),
                dict(id='free', title='Lịch phòng', source='Lịch 7 ngày', text='Tối nay phòng Dã Quỳ (4 người) còn trống, giá cao hơn 18 xu/đêm.'),
                dict(id='neighbour', title='Khách phòng bên', source='Ông Lâm', text='Ông Lâm ở phòng bên đã dặn: “Tối nay tôi cần ngủ sớm.”')],
         options=[dict(id='upgrade', label='Mời cả nhóm đổi sang phòng Dã Quỳ, bù phần chênh, khai báo đủ 4 người', requires=['rule', 'free'], quality='good', stars=5, reward=18,
                       review='Chủ nhà nói rõ nội quy mà không làm tụi em quê. Đổi phòng to, ngủ thoải mái, đáng tiền!',
                       outcome='Nhóm đổi sang phòng gia đình, khai báo đủ tên. Đêm đó cả nhà yên giấc.',
                       perspectives=[_p('Mai Chi', '🎒', 'Tưởng bị mắng, ai ngờ được gợi ý phòng rộng hơn. Chia 4 ra còn rẻ hơn ở hai phòng.'),
                                     _p('Chị Lành (buồng phòng)', '🧹', 'Khai báo đủ người thì em chuẩn bị đủ khăn, đủ nệm, không bị động.'),
                                     _p('Ông Lâm', '👴', 'Phòng bên không thành cái chợ. Tôi ngủ được.')]),
                  dict(id='squeeze', label='Cho ngủ chen, “thôi kệ, một đêm thôi mà”', quality='bad', stars=2,
                       review='Nhà có vẻ dễ dãi, tối qua phòng bên ồn tới khuya, sáng ra thiếu khăn.',
                       outcome='Bốn người trong phòng đôi, thiếu khăn, ồn đến khuya. Danh sách lưu trú sai số người.',
                       perspectives=[_p('Ông Lâm', '😠', 'Đêm qua tôi đập tường ba lần.'), _p('Mai Chi', '😬', 'Vui thì vui mà chật muốn xỉu.'),
                                     _p('Cán bộ khu phố', '📋', 'Khai báo 2 mà ở 4 là sai quy định lưu trú.')]),
                  dict(id='refuse', label='Chỉ nhận đúng 2 người, mời hai bạn kia đi chỗ khác', requires=['rule'], quality='ok', stars=3,
                       review='Đúng nội quy, nhưng không ai gợi ý cho tụi em cách nào khác cả.',
                       outcome='Hai bạn phải đi tìm nhà nghỉ lúc 9 giờ tối. Nhóm không vui nhưng không cãi được.',
                       perspectives=[_p('Mai Chi', '😕', 'Biết là đúng, nhưng lạnh thế này mà tách nhóm buồn ghê.'), _p('Chị Lành', '🧹', 'Ít ra phòng không quá tải.')])],
         lesson='Nói rõ nội quy an toàn, rồi tìm cách để khách vẫn ở được — đúng số người, đúng phòng.'),
    dict(id='HS-S02', title='Ồn ào lúc 23 giờ', npc=5, tone='tense', min_day=1,
         opening='23 giờ, Ông Lâm gõ cửa quầy: “Phòng Gác Mái hát karaoke! Sáng mai tôi đi xe 5 giờ đấy!”',
         facts=[dict(id='rule', title='Giờ yên tĩnh', source='Nội quy', text='Giờ yên tĩnh từ 22h đến 6h, có ghi trong tin nhắn xác nhận và dán sau cửa.'),
                dict(id='party', title='Phòng Gác Mái', source='Hành lang', text='Nhóm đang tổ chức sinh nhật bất ngờ cho một bạn, có bánh kem và loa bluetooth.'),
                dict(id='garden', title='Chòi sân vườn', source='Sân', text='Chòi sân vườn cách xa phòng ngủ, có mái che và bếp than an toàn ngoài trời.')],
         options=[dict(id='talk', label='Gõ cửa nhẹ nhàng, chúc mừng sinh nhật, nhắc giờ yên tĩnh và mời ra chòi sân vườn thêm 30 phút', requires=['party', 'garden'], quality='good', stars=5,
                       review='Chủ homestay xử lý khéo ghê, mình ngủ ngon mà nhóm trẻ vẫn vui.',
                       outcome='Nhóm xin lỗi, mang bánh ra chòi, 23g40 đã tắt đèn. Ông Lâm nhận thêm một miếng bánh kem sáng hôm sau.',
                       perspectives=[_p('Ông Lâm', '🧓', 'Tôi chỉ cần yên tĩnh, không cần ai bị đuổi.'), _p('Nhóm sinh nhật', '🎂', 'Được chúc mừng rồi mới được nhắc, tụi mình tự giác liền.'),
                                     _p('Bạn được tổ chức sinh nhật', '🥳', 'Chòi sân vườn có sao trời, còn đẹp hơn trong phòng!')]),
                  dict(id='rules', label='Đọc nội quy qua cửa, yêu cầu tắt loa ngay', requires=['rule'], quality='ok', stars=4,
                       review='Nhà có nội quy rõ, nhắc kịp thời. Hơi cứng nhưng hiệu quả.',
                       outcome='Loa tắt, nhóm hơi cụt hứng. Ông Lâm ngủ được.',
                       perspectives=[_p('Ông Lâm', '👍', 'Được việc.'), _p('Nhóm sinh nhật', '😐', 'Tụi mình sai thật, mà nghe như bị đọc biên bản.')]),
                  dict(id='ignore', label='“Thôi ông đeo nút tai, mai chúng nó về rồi”', quality='bad', stars=1,
                       review='Tôi báo ồn lúc 23 giờ mà chủ bảo tôi tự đeo nút tai. Hết nói.',
                       outcome='Karaoke tới 1 giờ sáng. Ông Lâm lỡ chuyến xe sớm, để lại review một sao.',
                       perspectives=[_p('Ông Lâm', '😡', 'Tôi là khách, không phải người phải chịu đựng.'), _p('Khách phòng Sương Sớm', '😴', 'Cả đêm không ai ngủ được.')])],
         lesson='Giờ yên tĩnh là lời hứa với mọi khách — nhắc sớm, nhắc khéo, và có chỗ cho niềm vui đi tiếp.'),
    dict(id='HS-S03', title='Sợi dây chuyền dưới gối', npc=0, tone='gentle', min_day=2,
         opening='Chị Lành dọn phòng Đồi Thông, cầm ra một sợi dây chuyền vàng mảnh: “Của chị Thu Hà, khách vừa ra sân bay 30 phút trước.”',
         facts=[dict(id='log', title='Sổ đồ thất lạc', source='Quầy', text='Quy trình: ghi ngày giờ, phòng, người tìm thấy; chụp ảnh món đồ (không chụp giấy tờ khách); cất tủ khóa.'),
                dict(id='contact', title='Liên hệ khách', source='App đặt phòng', text='Có thể nhắn cho khách qua kênh đặt phòng, không cần đăng thông tin cá nhân lên mạng.'),
                dict(id='caller', title='Cuộc gọi lạ', source='Điện thoại', text='Một người gọi tới nói “đó là dây chuyền của tôi”, nhưng không tả được mặt dây.')],
         options=[dict(id='process', label='Ghi sổ, cất tủ khóa, nhắn khách qua app; chỉ giao khi khách tả đúng món đồ, gửi chuyển phát có bảo hiểm theo yêu cầu khách', requires=['log', 'contact'], quality='good', stars=5,
                       review='Mình tưởng mất luôn rồi. Homestay nhắn ngay, gửi chuyển phát cẩn thận. Cảm ơn nhiều lắm!',
                       outcome='Chị Thu Hà tả đúng mặt dây hình giọt sương, trả phí gửi. Người gọi lạ không liên lạc lại.',
                       perspectives=[_p('Chị Thu Hà', '💛', 'Kỷ vật của mẹ mình. Mình khóc luôn khi nhận tin nhắn.'), _p('Chị Lành', '🧹', 'Ghi sổ có tên em, em thấy mình được tin tưởng.'),
                                     _p('Người gọi lạ', '📞', 'Không tả được thì đành chịu thôi.')]),
                  dict(id='post', label='Đăng ảnh dây chuyền kèm tên, số phòng khách lên trang homestay để tìm chủ', quality='ok', stars=3,
                       review='Cảm ơn đã giữ đồ, nhưng tên mình bị đăng công khai, không vui lắm.',
                       outcome='Tìm được chủ, nhưng lộ tên và thời gian lưu trú của khách lên mạng.',
                       perspectives=[_p('Chị Thu Hà', '😕', 'Mọi người biết mình đi Đà Lạt ngày nào, ở phòng nào.'), _p('Hàng xóm mạng', '👀', 'Hóa ra chị ấy ở phòng Đồi Thông…')]),
                  dict(id='give', label='Đưa luôn cho người gọi điện tới nhận', quality='bad', stars=1, cost=cf.comp(40),
                       review='Homestay giao dây chuyền của tôi cho người lạ! Tôi phải báo công an.',
                       outcome='Đồ giao nhầm người. Homestay phải bồi thường và mất uy tín.',
                       perspectives=[_p('Chị Thu Hà', '😭', 'Chỉ cần hỏi một câu thôi mà.'), _p('Chủ homestay', '😣', 'Bài học đắt giá về xác minh.')])],
         lesson='Đồ thất lạc: ghi sổ, cất khóa, liên hệ qua kênh riêng và xác minh trước khi giao.'),
    dict(id='HS-S04', title='Hai nền tảng, một phòng', npc=3, tone='tense', min_day=2,
         opening='14h, Anh Tuấn và một gia đình khác cùng cầm mã đặt phòng Dã Quỳ cho tối nay — một từ Mây Travel, một từ Đi Đâu.',
         facts=[dict(id='sync', title='Đồng bộ lịch', source='Máy tính', text='Lịch Đi Đâu đồng bộ chậm 2 tiếng; đặt phòng của anh Tuấn tới trước 40 phút.'),
                dict(id='rooms', title='Phòng còn trống', source='Lịch 7 ngày', text='Tối nay còn Gác Mái (3 người) và Đồi Thông (2 người) — gộp lại vừa 5 người.'),
                dict(id='partner', title='Nhà Gỗ Cô Ba', source='Hàng xóm', text='Nhà Gỗ Cô Ba còn một phòng gia đình, giá cao hơn 12 xu, cách 300 m.')],
         options=[dict(id='split', label='Giữ Dã Quỳ cho khách đặt trước; gia đình sau ở Gác Mái + Đồi Thông, homestay chịu phần chênh và tặng bữa sáng', requires=['sync', 'rooms'], quality='good', stars=4, cost=20,
                       review='Có trục trặc lịch nhưng homestay nhận lỗi và lo chỗ ở chu đáo, tặng cả bữa sáng.',
                       outcome='Không ai phải đi đâu. Homestay mất một chút tiền nhưng giữ được hai gia đình vui vẻ.',
                       perspectives=[_p('Anh Tuấn', '🧔', 'Tôi đặt trước, được giữ phòng — đúng.'), _p('Gia đình thứ hai', '👨‍👩‍👧', 'Hai phòng cạnh nhau, còn được bữa sáng, không tệ.'),
                                     _p('Chủ homestay', '🧮', 'Tắt đồng bộ tự động, kiểm lịch bằng tay mỗi sáng.')]),
                  dict(id='walk', label='Đưa gia đình đặt sau sang Nhà Gỗ Cô Ba, homestay trả phần chênh và taxi', requires=['partner'], quality='ok', stars=3, cost=16,
                       review='Bị chuyển sang nhà khác, dù được lo taxi. Hơi mất công.',
                       outcome='Gia đình thứ hai ở nhà hàng xóm. Cô Ba vui vì có khách.',
                       perspectives=[_p('Gia đình thứ hai', '😐', 'Chấp nhận được, nhưng đã chọn nhà Mây vì ảnh đẹp.'), _p('Cô Ba', '👵', 'Có qua có lại mà.')]),
                  dict(id='first', label='“Ai tới trước ở trước”, người còn lại tự lo', quality='bad', stars=1,
                       review='Đặt cọc đàng hoàng mà bị bảo tự lo chỗ ngủ lúc 3 giờ chiều. Tệ.',
                       outcome='Một gia đình kéo vali ra đường, review một sao kèm ảnh chụp mã đặt phòng.',
                       perspectives=[_p('Gia đình thứ hai', '😡', 'Lỗi của homestay mà.'), _p('Anh Tuấn', '😬', 'Tôi có phòng nhưng thấy ngại thay.')])],
         lesson='Trùng phòng là lỗi của nhà: giữ quyền cho người đặt trước và tự lo chỗ tốt cho người kia.'),
    dict(id='HS-S05', title='Xin hóa đơn cao hơn thực tế', npc=6, tone='tense', min_day=3,
         opening='Anh Kiệt nói nhỏ: “Em xuất hóa đơn cho anh 3 đêm thay vì 1 nhé, công ty thanh toán mà, anh bồi dưỡng em.”',
         facts=[dict(id='stay', title='Sổ lưu trú', source='Quầy', text='Anh Kiệt ở 1 đêm, tổng 28 xu, đã thanh toán.'),
                dict(id='rule', title='Quy định hóa đơn', source='Sổ tay kế toán', text='Hóa đơn phải đúng số đêm, số tiền thật; lập khống là gian lận.'),
                dict(id='policy', title='Chính sách công ty khách', source='Email anh Kiệt', text='Công ty anh Kiệt cần hóa đơn có mã số thuế công ty và ghi rõ ngày lưu trú.')],
         options=[dict(id='accurate', label='Từ chối lịch sự; xuất hóa đơn đúng 1 đêm, ghi đủ mã số thuế và ngày lưu trú theo yêu cầu công ty', requires=['stay', 'policy'], quality='good', stars=4,
                       review='Hóa đơn chuẩn chỉnh, đúng thông tin công ty cần. Chủ nhà thẳng thắn.',
                       outcome='Anh Kiệt hơi ngượng, nhận hóa đơn đúng. Tháng sau công ty anh đặt tiếp 3 phòng cho đoàn.',
                       perspectives=[_p('Anh Kiệt', '🧑‍💼', 'Thôi, giấy tờ sạch vẫn hơn.'), _p('Kế toán công ty anh Kiệt', '📑', 'Hóa đơn khớp lịch công tác, duyệt nhanh.'),
                                     _p('Chủ homestay', '🧾', 'Không đánh đổi uy tín lấy vài chục xu.')]),
                  dict(id='fake', label='Xuất hóa đơn 3 đêm, nhận “bồi dưỡng”', quality='bad', cost=30,
                       outcome='Kiểm tra đối chiếu phát hiện hóa đơn khống: homestay bị phạt, anh Kiệt bị kỷ luật.',
                       perspectives=[_p('Kế toán công ty', '🔍', 'Lịch bay chỉ 1 đêm, hóa đơn 3 đêm?'), _p('Anh Kiệt', '😰', 'Tưởng chuyện nhỏ…')]),
                  dict(id='cold', label='Từ chối và nói to “Anh định gian lận à?”', requires=['rule'], quality='ok', stars=2,
                       review='Đúng là không nên, nhưng nói to trước mặt khách khác thì hơi quá.',
                       outcome='Anh Kiệt bẽ mặt, trả phòng không nói lời nào.',
                       perspectives=[_p('Anh Kiệt', '😶', 'Tôi sai, nhưng cần gì làm tôi xấu hổ vậy.'), _p('Khách bên cạnh', '👂', 'Nghe hết cả rồi…')])],
         lesson='Từ chối gian lận một cách riêng tư, và giúp khách đúng cách họ thật sự cần.'),
    dict(id='HS-S06', title='Máy sưởi hỏng lúc 2 giờ sáng', npc=2, tone='tense', min_day=1,
         opening='2 giờ sáng, trời 9 độ. Cô Diệp gọi: “Máy sưởi phòng cô tắt ngấm, chú run cầm cập rồi con ơi!”',
         swap='Bạn là khách lớn tuổi, nửa đêm ở một nơi lạ, rất lạnh.',
         facts=[dict(id='heater', title='Máy sưởi phòng', source='Kiểm tra nhanh', text='Máy sưởi gas báo lỗi đánh lửa, không sửa được lúc nửa đêm.'),
                dict(id='spare', title='Kho dự phòng', source='Kho', text='Có 1 máy sưởi dầu điện dự phòng, 4 chăn lông, túi chườm ấm.'),
                dict(id='charcoal', title='Bếp than', source='Ông Lâm (nhắn)', text='Ông Lâm nhắn: “Mang lò than vào phòng cho ấm, ngày xưa ai cũng làm thế.” (Than đốt trong phòng kín sinh khí CO — rất nguy hiểm.)')],
         options=[dict(id='safe', label='Mang máy sưởi dầu điện, thêm chăn, túi chườm và trà gừng; sáng gọi thợ, giảm giá đêm đó', requires=['heater', 'spare'], quality='good', stars=5, cost=10,
                       review='Nửa đêm mà con chủ nhà chạy lên ngay, chăn ấm, trà gừng nóng. Cô cảm động lắm.',
                       outcome='Chú ấm lại sau 15 phút. Sáng ra thợ thay bộ đánh lửa, homestay giảm 10 xu tiền phòng.',
                       perspectives=[_p('Cô Diệp', '🥰', 'Cô chỉ cần có người nghe máy lúc 2 giờ sáng.'), _p('Chú (chồng cô Diệp)', '🍵', 'Trà gừng ngon hơn cả khách sạn 5 sao.'),
                                     _p('Thợ sửa', '🔧', 'Bộ đánh lửa cũ, nên thay định kỳ.')]),
                  dict(id='charcoal', label='Mang lò than hồng vào phòng cho nhanh ấm', requires=['charcoal'], quality='bad', cost=30,
                       outcome='Nửa tiếng sau chú chóng mặt, buồn nôn. May mà cô Diệp mở cửa kịp và gọi cấp cứu. Tuyệt đối không đốt than trong phòng kín.',
                       perspectives=[_p('Cô Diệp', '😨', 'Tưởng mất chú rồi.'), _p('Nhân viên y tế', '🚑', 'Mỗi mùa lạnh đều có ca ngộ độc khí than trong phòng kín.')]),
                  dict(id='wait', label='“Cô chú đắp tạm chăn, sáng con gọi thợ”', quality='ok', stars=2,
                       review='Cả đêm lạnh run. Chủ nhà không lên xem một lần.',
                       outcome='Cô chú thức tới sáng, chú bị cảm nhẹ.',
                       perspectives=[_p('Cô Diệp', '🥶', 'Người già không chịu lạnh giỏi như con nghĩ đâu.'),
                                     _p('Chị Lành', '🧹', 'Kho có sẵn máy sưởi dầu mà không ai nhớ ra.')])],
         lesson='Sự cố nửa đêm: giải pháp an toàn trước, tiện sau — không bao giờ đốt than trong phòng kín.'),
    dict(id='HS-S07', title='Chú chó không khai báo', npc=1, tone='gentle', min_day=2,
         opening='Anh Bảo nhận phòng, trong ba lô thò ra một cái đầu cún: “Bé Mắm ngoan lắm, cho em gửi ké một đêm nha?”',
         facts=[dict(id='rule', title='Nội quy thú cưng', source='Trang đặt phòng', text='Homestay ghi rõ: không nhận thú cưng trong phòng.'),
                dict(id='allergy', title='Lịch phòng', source='Lịch 7 ngày', text='Ngày mai phòng này đón một bé bị dị ứng lông chó.'),
                dict(id='petcare', title='Lưu trú thú cưng', source='Tờ rơi', text='Pet Care Mèo Mập cách 500 m nhận lưu trú qua đêm, có camera cho chủ xem.')],
         options=[dict(id='boarding', label='Giải thích nội quy và bé dị ứng ngày mai; gọi giúp Pet Care Mèo Mập giữ bé Mắm qua đêm', requires=['rule', 'petcare'], quality='good', stars=4,
                       review='Không được ở cùng cún nhưng chủ nhà gọi giúp chỗ gửi ngay, có camera xem bé ngủ. Ổn áp!',
                       outcome='Bé Mắm ngủ ở Pet Care Mèo Mập, sáng anh Bảo đón đi phượt tiếp. Phòng không có lông chó cho bé khách mai.',
                       perspectives=[_p('Anh Bảo', '🐶', 'Hơi tiếc, nhưng Mắm được chăm kỹ hơn ở phòng.'), _p('Mẹ bé bị dị ứng (khách ngày mai)', '🤧', 'Cảm ơn nhà đã giữ đúng lời hứa không thú cưng.'),
                                     _p('Nhân viên Pet Care', '🐾', 'Bé Mắm ăn hết phần, ngủ ngoan.')]),
                  dict(id='allow', label='Cho ở luôn, sáng mai dọn kỹ là được', quality='bad', stars=2,
                       review='Hôm sau con tôi nổi mẩn ngứa ở phòng “không thú cưng”.',
                       outcome='Dọn kỹ vẫn còn lông. Bé khách ngày mai bị dị ứng, gia đình trả phòng sớm.',
                       perspectives=[_p('Mẹ bé bị dị ứng', '😠', 'Tôi chọn nhà này vì ghi không nhận thú cưng.'), _p('Chị Lành', '🧹', 'Lông chó bám vào rèm, hút ba lần chưa hết.')]),
                  dict(id='reject', label='Từ chối nhận phòng vì vi phạm nội quy', requires=['rule'], quality='ok', stars=2,
                       review='Đúng luật nhưng lạnh lùng, 9 giờ tối tôi và con chó ra đường.',
                       outcome='Anh Bảo đi tìm chỗ khác giữa đêm lạnh.',
                       perspectives=[_p('Anh Bảo', '🥶', 'Tôi sai vì không hỏi trước, nhưng có cách khác mà.'),
                                     _p('Bé Mắm', '🐶', 'Ư ử… lạnh quá, đi đâu bây giờ?')])],
         lesson='Giữ lời hứa với khách sau (dị ứng) nhưng vẫn tìm đường cho khách trước.'),
    dict(id='HS-S08', title='“Tôi bị ngộ độc vì bữa sáng!”', npc=3, tone='tense', min_day=3,
         opening='Anh Tuấn ôm bụng: “Ăn sáng ở đây xong tôi đau bụng cả buổi, chắc trứng hỏng!”',
         facts=[dict(id='log', title='Sổ bếp', source='Bếp', text='Trứng và sữa sáng nay đều trong hạn, lô trứng nhập hôm qua. 6 khách khác ăn cùng không ai sao.'),
                dict(id='night', title='Tối qua', source='Anh Tuấn kể', text='Tối qua anh ăn ốc nướng và uống sữa đậu nành ở chợ đêm.'),
                dict(id='clinic', title='Phòng khám', source='Bản đồ', text='Phòng khám Đa khoa Mây cách 800 m, mở cửa tới 20h.')],
         options=[dict(id='care', label='Hỏi han, gọi taxi đưa đi khám (không tự đoán bệnh, không đưa thuốc), giữ mẫu thức ăn, cho xem sổ bếp, hoàn tiền bữa sáng như thiện chí', requires=['log', 'clinic'], quality='good', stars=4, cost=12,
                       review='Chủ nhà đưa đi khám ngay, cho xem sổ bếp minh bạch. Bác sĩ bảo do đồ ăn tối qua. Cảm ơn nhà.',
                       outcome='Bác sĩ kết luận rối loạn tiêu hóa nhẹ, không liên quan bữa sáng. Anh Tuấn cảm ơn vì được chăm sóc.',
                       perspectives=[_p('Anh Tuấn', '🤢', 'Lúc đau ai cũng muốn đổ cho ai đó. Được đưa đi khám là tôi yên tâm.'), _p('Bếp sáng (bà Sáu)', '🍳', 'Sổ bếp ghi đủ, tôi không sợ.'),
                                     _p('Bác sĩ', '🩺', 'Không nên tự uống thuốc khi chưa rõ nguyên nhân.')]),
                  dict(id='medicine', label='Đưa vỉ thuốc tiêu chảy trong tủ cho anh uống', quality='bad', stars=2,
                       review='Chủ nhà đưa thuốc cho tôi uống bừa. Hôm sau còn mệt hơn.',
                       outcome='Thuốc không phù hợp làm anh Tuấn mệt thêm, phải đi khám. Homestay không phải nơi kê thuốc.',
                       perspectives=[_p('Bác sĩ', '🩺', 'Thuốc cầm tiêu chảy có thể làm nặng thêm một số trường hợp.'),
                                     _p('Anh Tuấn', '😣', 'Tôi tin chủ nhà, uống ngay, ai ngờ…')]),
                  dict(id='deny', label='“Không phải do nhà tôi, 6 người khác có sao đâu”', requires=['log'], quality='ok', stars=2,
                       review='Có thể không phải do bữa sáng, nhưng tôi đau mà không ai hỏi han.',
                       outcome='Đúng dữ kiện nhưng khách thấy bị bỏ mặc.',
                       perspectives=[_p('Anh Tuấn', '😞', 'Tôi cần người giúp, không cần người thắng tranh luận.'),
                                     _p('Bà Sáu (bếp)', '🍳', 'Sổ bếp đúng là sạch, nhưng mình nên hỏi han người ta trước.')])],
         lesson='Khi khách kêu mệt: lo sức khỏe trước (đưa đi khám), minh bạch sổ sách sau — không tự chẩn đoán, không đưa thuốc.'),
]

# ---------------------------------------------------------------- v0.5 surprise desk (kit.desk_*)
# Effects: money / review / patience / xp / mark / unmark are generic; `safety` and `inspect` go to _desk_hook.
DESK = [
    dict(id='karaoke', title='Karaoke lúc 22 giờ 30', emoji='🎤', npc=5, min_day=2, tone='tense', weight=2,
         text='Nhóm khách trẻ trên lầu mở loa kéo hát karaoke. Ông Lâm bên cạnh gọi sang: “Có để ai ngủ không đây?”',
         options=[dict(id='talk', label='Lên gõ cửa, nhắc giờ yên tĩnh, mời đĩa trái cây đổi lấy cái loa', hint='−4 xu',
                       effects=dict(money=-4, review=[5, 'Nhà Mây xử lý khách ồn khéo ghê, mười phút là yên.']), good=True,
                       outcome='Nhóm khách cười xòa, tắt loa, xin thêm đĩa dưa hấu. Ông Lâm nhắn một chữ: “Được.”'),
                  dict(id='police', label='Gọi công an phường tới nhắc', effects=dict(patience=-5, review=[3, 'Yên thì yên, mà xe công an đỗ trước cửa cả xóm nhìn.']),
                       good=None, outcome='Khách tắt loa, nhưng sáng ra trả phòng sớm, mặt không vui.'),
                  dict(id='ignore', label='Kệ, khách trả tiền phòng rồi', effects=dict(review=[1, 'Ồn tới nửa đêm, nhà trọ không nói một lời.']),
                       good=False, outcome='Hát tới một giờ sáng. Ông Lâm đăng bài trong nhóm tổ dân phố.')],
         default='ignore'),
    dict(id='power', title='Cả xóm cúp điện', emoji='🕯️', npc=6, min_day=2, at='any', tone='tense', weight=2,
         text='Máy nước nóng tắt, wifi tắt. Anh Kiệt nhắn: “9 giờ tôi có cuộc họp trực tuyến với khách hàng.”',
         options=[dict(id='generator', label='Thuê máy phát nhỏ, ưu tiên wifi và nước nóng', hint='−20 xu',
                       effects=dict(money=-20, review=[5, 'Cúp điện cả xóm mà homestay vẫn có wifi cho tôi họp.']), good=True,
                       outcome='Máy phát nổ giòn sau nhà. Anh Kiệt họp xong, ra quầy xin thêm cốc cà phê.'),
                  dict(id='candles', label='Thắp nến, pha trà gừng, nhắn xin lỗi từng phòng',
                       luck=dict(p=0.5, win=dict(effects=dict(review=[4, 'Cúp điện mà ấm cúng như đi cắm trại, trà gừng ngon.']), good=True,
                                                 outcome='Điện có lại sau 40 phút. Khách còn chụp ảnh nến đăng mạng.'),
                                 lose=dict(effects=dict(review=[2, 'Không điện, không wifi, lỡ luôn cuộc họp quan trọng.']), good=False,
                                           outcome='Ba tiếng sau mới có điện. Anh Kiệt phải ra quán cà phê đầu dốc để họp.'))),
                  dict(id='wait', label='Chờ điện có lại', effects=dict(patience=-10, review=[2, 'Cúp điện cả buổi, chủ nhà biến mất.']), good=False,
                       outcome='Khách lục tục ra quầy hỏi; không ai biết bao giờ có điện.')],
         default='wait'),
    dict(id='water', title='Bồn nước trên mái cạn khô', emoji='🚿', npc=3, min_day=2, at='open', tone='tense',
         text='Máy bơm nhảy rơ-le từ đêm qua. Anh Tuấn đứng trong phòng tắm, đầu còn đầy dầu gội.',
         options=[dict(id='plumber', label='Gọi thợ thay rơ-le, xách tạm mấy xô nước ấm lên phòng', hint='−12 xu',
                       effects=dict(money=-12, patience=-6, review=[4, 'Mất nước sáng sớm nhưng homestay xách nước ấm lên tận phòng.']), good=True,
                       outcome='Nửa tiếng sau bồn đầy lại. Hai bé nhà anh Tuấn được tắm nước ấm.'),
                  dict(id='bottles', label='Mua nước bình giao tận nơi cho khách dùng tạm', hint='−6 xu',
                       effects=dict(money=-6, review=[3, 'Tắm bằng nước bình, tạm được.']), good=None,
                       outcome='Khách xoay xở được, nhưng máy bơm vẫn chưa ai sửa.'),
                  dict(id='nothing', label='Bảo khách chịu khó chờ', effects=dict(review=[1, 'Mất nước cả sáng, hỏi thì bảo chờ.']), good=False,
                       outcome='Anh Tuấn gội đầu bằng nước suối đóng chai, mặt hằm hằm.')],
         default='nothing'),
    dict(id='inspect', title='Tổ kiểm tra phường ghé bất ngờ', emoji='📋', npc=11, min_day=3, tone='tense', weight=2,
         text='Chú Thành đưa biên bản: “Cho xem sổ khai báo lưu trú và sổ kiểm tra phòng cháy chữa cháy hôm nay.”',
         options=[dict(id='log', label='Đưa sổ an toàn hôm nay', effects=dict(inspect=True), good=None,
                       outcome='Chú Thành lật từng trang sổ.'),
                  dict(id='rush', label='Xin chú chờ, thử chuông báo khói và bình chữa cháy ngay trước mặt', hint='Khách đang chờ sốt ruột hơn',
                       effects=dict(patience=-12, safety=True, inspect=True), good=True, outcome='Kiểm tra lại từng món ngay tại chỗ.'),
                  dict(id='envelope', label='Kẹp phong bì “uống cà phê” vào sổ', hint='−20 xu', effects=dict(money=-20), good=False,
                       outcome='Chú Thành đẩy phong bì lại, ghi thêm một dòng vào biên bản. Nhà bị phạt 20 xu và hẹn kiểm tra lại.')],
         default='log'),
    dict(id='gas', title='Mùi gas ở bếp chung', emoji='🔥', npc=14, min_day=3, tone='tense',
         text='Cô Tư gõ cửa quầy: “Con ơi, bếp chung có mùi gas nồng lắm!”',
         options=[dict(id='valve', label='Khóa van tổng, mở hết cửa, không bật công tắc, gọi thợ', hint='−10 xu',
                       effects=dict(money=-10, review=[5, 'Vừa báo mùi gas là chủ nhà khóa van, mở cửa, gọi thợ liền. Cô yên tâm.']), good=True,
                       outcome='Thợ tìm ra ống dẫn bị chuột cắn, thay ống mới. Cả dãy thở phào.'),
                  dict(id='fan', label='Bật quạt hút cho nhanh bay mùi', hint='−10 xu',
                       effects=dict(money=-10, review=[2, 'Có mùi gas mà nhà lại bật quạt điện, sợ quá.']), good=False,
                       outcome='Công tắc lóe tia lửa nhỏ… may mà chưa đủ nồng độ để bắt lửa. Thợ tới mắng một trận.'),
                  dict(id='later', label='Để lát rảnh rồi xem', effects=dict(review=[1, 'Báo mùi gas mà cả buổi không ai xem.']), good=False,
                       outcome='Tới tối mùi gas vẫn còn. Cả dãy phòng xin đổi chỗ ở.')],
         default='later'),
    dict(id='skip', title='Khách đi sớm, chưa trả đêm thứ hai', emoji='🏃', npc=8, min_day=3, at='open', tone='tense',
         text='6 giờ sáng, phòng của vị khách đặt hai đêm trống trơn, chìa khóa nằm trên bàn. Hóa đơn còn thiếu một đêm, 30 xu.',
         options=[dict(id='message', label='Nhắn tin lịch sự kèm hóa đơn qua app',
                       luck=dict(p=0.6, win=dict(effects=dict(money=30), good=True, outcome='Khách xin lỗi vì vội ra sân bay, chuyển khoản đủ 30 xu.'),
                                 lose=dict(good=None, outcome='Tin nhắn hiện “đã xem” rồi im lặng. Lần sau thu đủ tiền khi nhận phòng.'))),
                  dict(id='post', label='Đăng ảnh khách lên nhóm cư dân để bóc phốt',
                       effects=dict(review=[1, 'Chủ nhà đăng ảnh khách lên mạng, đáng sợ.']), good=False,
                       outcome='Bài đăng bị báo cáo vì lộ ảnh cá nhân. Khách để lại một đánh giá cay đắng.'),
                  dict(id='let', label='Bỏ qua, rút kinh nghiệm thu đủ tiền lúc nhận phòng', effects=dict(xp=4), good=None,
                       outcome='Mất 30 xu. Sổ quầy thêm một dòng: “thu đủ tiền trước”.')],
         default='let'),
    dict(id='blackmail', title='Dọa đánh giá 1★ để đòi giảm giá', emoji='😤', npc=8, min_day=3, no_mark='paid_off', tone='tense',
         text='Một khách vừa trả phòng nhắn qua app: “Hoàn 50% tiền phòng đi, không thì mình cho 1 sao trên app.” Phòng không có sự cố nào.',
         options=[dict(id='refuse', label='Từ chối lịch sự, gửi ảnh bàn giao phòng, báo app về lời đe dọa',
                       luck=dict(p=0.7, win=dict(effects=dict(xp=6), good=True, outcome='App xem ảnh và tin nhắn, gỡ đánh giá vì vi phạm chính sách.'),
                                 lose=dict(effects=dict(review=[2, 'Chủ nhà khó tính, không linh động.']), good=None,
                                           outcome='App chưa xử lý kịp, đánh giá 2★ vẫn nằm đó — nhưng ai đọc tin nhắn cũng hiểu.'))),
                  dict(id='pay', label='Hoàn 50% cho yên chuyện', hint='−15 xu', effects=dict(money=-15, mark='paid_off'), good=False,
                       outcome='Khách nhận tiền… rồi vẫn cho 3★. Tin đồn “dọa là được giảm” bắt đầu lan.'),
                  dict(id='fight', label='Trả lời gay gắt ngay trên app', effects=dict(review=[1, 'Chủ nhà trả lời khách như cãi nhau ngoài chợ.']),
                       good=False, outcome='Màn cãi nhau nằm ngay dưới ảnh bìa homestay.'),
                  dict(id='silent', label='Không trả lời', effects=dict(review=[1, 'Phòng ẩm, nhắn không ai trả lời.']), good=False,
                       outcome='Đánh giá 1★ lên app lúc nửa đêm.')],
         default='silent'),
    dict(id='copycat', title='Nhóm khác cũng đòi giảm 50%', emoji='🗯️', npc=4, min_day=3, need_mark='paid_off', tone='tense',
         text='“Nghe nói ở đây dọa 1 sao là được giảm nửa giá hả?” — nhóm Mai Chi cười, chìa điện thoại ra.',
         options=[dict(id='policy', label='Nói rõ chính sách: chỉ hoàn tiền khi nhà có lỗi thật, kèm ảnh bàn giao',
                       effects=dict(unmark='paid_off', xp=6), good=True, outcome='Cả nhóm gãi đầu cười trừ. Tin đồn dừng ở đây.'),
                  dict(id='pay', label='Lại giảm cho yên', hint='−15 xu', effects=dict(money=-15), good=False,
                       outcome='Thêm 15 xu bay đi. Nhóm chat du lịch truyền tay nhau “mẹo” này.'),
                  dict(id='ignore', label='Làm lơ', effects=dict(unmark='paid_off', review=[1, 'Hỏi chính sách mà chủ nhà làm lơ.']), good=False,
                       outcome='Nhóm để lại 1★ kèm câu “chủ nhà có mặt mũi hai kiểu”.')],
         default='ignore'),
    dict(id='otacall', title='Kênh OTA gọi nhắc vì bán trùng phòng', emoji='☎️', npc=7, min_day=3, need_mark='ota_walk', tone='tense',
         text='Chị Hạnh gọi: “Tuần này nhà em để khách tới nơi không có phòng. Thêm lần nữa là bị hạ hạng tìm kiếm nha em.”',
         options=[dict(id='own', label='Nhận lỗi, cam kết đồng bộ lịch mỗi sáng', effects=dict(unmark='ota_walk', xp=6), good=True,
                       outcome='“Vậy chị ghi nhận thiện chí nha. Nhớ đồng bộ lịch mỗi sáng đó!”'),
                  dict(id='blame', label='Đổ lỗi app đồng bộ chậm', effects=dict(unmark='ota_walk', mark='ota_warn'), good=False,
                       outcome='Chị Hạnh im lặng vài giây: “Để chị ghi nhận.” Mấy hôm sau đơn mới thưa hẳn.'),
                  dict(id='miss', label='Để máy rung, bận quá', effects=dict(unmark='ota_walk', mark='ota_warn'), good=False,
                       outcome='Ba cuộc gọi nhỡ. Homestay tụt xuống trang hai kết quả tìm kiếm.')],
         default='miss'),
    dict(id='bus', title='Cả đoàn khách không đặt trước', emoji='🚌', npc=12, min_day=2, mods=('festival', 'weekend'), tone='gentle', weight=2,
         text='Xe khách đổ xuống 12 người chưa có chỗ ngủ. Cô Ba gọi: “Nhà cô còn hai phòng. Nhà con kín thì gửi qua cô, cô chia hoa hồng!”',
         options=[dict(id='refer', label='Giới thiệu sang Nhà Gỗ Cô Ba, nhận hoa hồng giới thiệu', hint='+10 xu', effects=dict(money=10), good=True,
                       outcome='Đoàn khách có chỗ ngủ, Cô Ba gửi 10 xu kèm túi hồng giòn.'),
                  dict(id='cram', label='Nhận hết, trải nệm ra phòng khách', hint='+30 xu',
                       effects=dict(money=30, patience=-10, review=[1, 'Ngủ nệm ở phòng khách, người đi qua đi lại cả đêm.']), good=False,
                       outcome='Thu thêm 30 xu, nhưng lối thoát hiểm kín nệm và khách phòng khác than phiền.'),
                  dict(id='no', label='Báo nhà đã kín phòng', good=None, outcome='Đoàn khách đứng bơ vơ một lúc rồi kéo vali đi.')],
         default='no'),
    dict(id='street', title='Phố hoa cho bày hàng trước cửa', emoji='🌼', npc=12, min_day=2, at='open', mods=('festival',), tone='gentle',
         text='Phường cho các nhà dọc đường bày hàng dịp lễ hội. Cô Ba rủ: “Bày bàn trà gừng bán cho khách xem hoa, chia đôi tiền lời nha!”',
         options=[dict(id='stall', label='Bày bàn trà gừng gọn trước cổng', hint='+18 xu · khách trong nhà chờ lâu hơn', effects=dict(money=18, patience=-6),
                       good=True, outcome='Trà gừng bán sạch trước trưa. Khách xem hoa hỏi thăm phòng trống.'),
                  dict(id='sprawl', label='Bày tràn ra cả lối thoát hiểm cho rộng', hint='+24 xu',
                       luck=dict(p=0.5, win=dict(effects=dict(money=24), good=None, outcome='Bán đắt hàng, lối thoát hiểm kín bàn ghế cả buổi.'),
                                 lose=dict(effects=dict(money=-6), good=False, outcome='Tổ trật tự nhắc lấn lối thoát hiểm: dẹp hàng, phạt 30 xu, lời chẳng còn bao nhiêu.'))),
                  dict(id='skip', label='Thôi, lo khách trong nhà', good=None, outcome='Nhà Cô Ba bày một mình, cuối ngày gửi sang một ấm trà.')],
         default='skip'),
    dict(id='fog', title='Nhóm khách muốn chạy xe trong sương', emoji='🌁', npc=4, min_day=2, mods=('rain', 'cold'), tone='tense',
         text='4 giờ sáng, nhóm Mai Chi dắt xe máy ra cổng định lên đồi săn mây. Sương dày tới mức không thấy cột điện: “Đi được không ạ?”',
         options=[dict(id='warn', label='Khuyên chờ sương tan, gọi xe jeep hợp tác xã đưa đi', hint='Không tốn xu',
                       effects=dict(review=[5, 'Chủ nhà can đi đường sương mù, gọi xe jeep. An toàn mà vẫn săn được mây!']), good=True,
                       outcome='7 giờ sương mỏng dần, xe jeep đưa cả nhóm lên đồi đúng lúc biển mây tràn qua.'),
                  dict(id='shortcut', label='Chỉ đường tắt cho kịp giờ',
                       luck=dict(p=0.4, win=dict(effects=dict(review=[4, 'Đường tắt hơi ghê nhưng tới kịp biển mây.']), good=None,
                                                 outcome='Cả nhóm tới nơi, tay chân lạnh cóng.'),
                                 lose=dict(effects=dict(review=[1, 'Đường tắt trơn trượt, bạn em té xe trầy cả chân.']), good=False,
                                           outcome='Một bạn trượt bánh ở khúc cua. May chỉ trầy xước.'))),
                  dict(id='shrug', label='Tùy các em thôi', good=None, outcome='Cả nhóm vẫn đi. Tim đập thình thịch tới khi thấy ảnh check-in.')],
         default='shrug'),
    dict(id='lostwrong', title='Chủ thật của món đồ gọi tới', emoji='📞', npc=8, min_day=3, need_mark='lost_wrong', tone='tense',
         text='“Mình là người để quên đồ hôm trước. Sao homestay lại giao cho người khác?” Giọng khách run run.',
         options=[dict(id='own', label='Nhận lỗi, đền giá trị món đồ, báo công an phường', hint=f'−{cf.comp(25)} xu',
                       effects=dict(money=-cf.comp(25), unmark='lost_wrong', review=[3, 'Giao nhầm đồ của tôi, nhưng họ nhận lỗi và đền đủ.']), good=True,
                       outcome='Khách nguôi dần. Từ hôm nay đồ thất lạc chỉ giao sau khi xác minh qua kênh đặt phòng.'),
                  dict(id='excuse', label='Nói người kia tả đúng món đồ mà',
                       effects=dict(unmark='lost_wrong', review=[1, 'Giao đồ của tôi cho người lạ rồi còn đổ lỗi.']), good=False,
                       outcome='Khách cúp máy. Tối đó bài đánh giá 1★ dài ba đoạn xuất hiện.')],
         default='excuse'),
    dict(id='kol', title='Blogger xin ở miễn phí', emoji='📸', npc=13, min_day=3, tone='gentle',
         text='Thảo Vi nhắn: “Cho em ở free 2 đêm phòng đẹp nhất, em review lên kênh hơn 200 nghìn người theo dõi nha!”',
         options=[dict(id='deal', label='Mời ở giá ưu đãi 50%, bài viết trung thực và ghi rõ “được tài trợ”', hint='+14 xu',
                       effects=dict(money=14, review=[5, 'Phòng thơm mùi gỗ thông, chủ nhà rõ ràng sòng phẳng. (Bài có tài trợ)']), good=True,
                       outcome='Bài đăng thật, ảnh đẹp. Tuần sau có ba tin nhắn hỏi phòng.'),
                  dict(id='free', label='Cho ở miễn phí, xin bài 5 sao', hint='−10 xu',
                       luck=dict(p=0.4, win=dict(effects=dict(review=[5, 'Homestay xinh như tranh!']), good=None,
                                                 outcome='Bài đăng hút khách, nhưng không ghi được tài trợ — người xem bắt đầu nghi ngờ.'),
                                 lose=dict(effects=dict(review=[2, 'Phòng tầm tầm, ảnh trên app lung linh hơn thực tế.']), good=False,
                                           outcome='Hai đêm miễn phí, đổi lại một bài chê.')),
                       effects=dict(money=-10)),
                  dict(id='no', label='Cảm ơn, nhà chưa hợp tác quảng cáo lúc này', good=None, outcome='Thảo Vi thả một icon buồn rồi đi.')],
         default='no'),
    dict(id='parking', title='Hết chỗ dựng xe máy', emoji='🛵', npc=1, min_day=2, tone='gentle',
         text='Xe máy khách đậu tràn ra lề dốc. Anh Bảo hỏi: “Để xe ngoài đường qua đêm có sao không?”',
         options=[dict(id='yard', label='Thuê sân nhà Ông Lâm giữ xe qua đêm', hint='−6 xu',
                       effects=dict(money=-6, review=[5, 'Có chỗ giữ xe khô ráo, sáng ra xe không ướt sương.']), good=True,
                       outcome='Ông Lâm mở cổng sân, còn dặn: “Xe dựng thẳng hàng giùm tôi.”'),
                  dict(id='street', label='Dựng tạm ra lề đường',
                       luck=dict(p=0.6, win=dict(good=None, outcome='Đêm yên ổn, sáng ra yên xe ướt đẫm sương.'),
                                 lose=dict(effects=dict(money=-10), good=False, outcome='Tổ trật tự dán giấy nhắc, phạt 10 xu vì lấn lề.'))),
                  dict(id='no', label='Bảo khách tự tìm chỗ gửi', effects=dict(review=[2, 'Hỏi chỗ để xe mà chủ nhà bảo tự lo.']), good=False,
                       outcome='Anh Bảo đẩy xe xuống tận chợ gửi, về muộn, mặt mệt phờ.')],
         default='no'),
    dict(id='early', title='Khách xin nhận phòng lúc 9 giờ sáng', emoji='🧳', npc=2, min_day=2, at='open', tone='gentle',
         text='Cô Diệp và chú xuống xe đêm, mắt thâm quầng: “Phòng chưa tới giờ nhận, cho cô chú nghỉ tạm được không con?”',
         options=[dict(id='lounge', label='Giữ hành lý, mời nghỉ ở phòng khách với trà gừng, ưu tiên dọn phòng', hint='Khách đang chờ sốt ruột hơn chút',
                       effects=dict(patience=-5, review=[5, 'Tới sớm mà được mời trà gừng, nghỉ ghế êm. Chủ nhà chu đáo lắm.']), good=True,
                       outcome='Cô chú chợp mắt trên sofa. 11 giờ phòng xong, cô chú lên nghỉ.'),
                  dict(id='fee', label='Nhận sớm có phụ thu 10 xu', hint='+10 xu', effects=dict(money=10, review=[4, 'Nhận phòng sớm có phụ thu, cũng hợp lý.']),
                       good=None, outcome='Cô chú trả phụ thu, lên phòng ngủ một mạch tới trưa.'),
                  dict(id='later', label='Chưa tới giờ, mời quay lại lúc 14 giờ', effects=dict(review=[2, 'Xuống xe đêm mệt rũ mà phải ngồi ngoài quán chờ.']),
                       good=False, outcome='Cô chú kéo vali ra quán nước đầu dốc ngồi chờ.')],
         default='later'),
]

SPEC = dict(
    id=ID, prefix='hs_', category='service',
    meta=dict(short='Homestay nhỏ', place='Homestay Mây Đà Lạt', tagline='Phòng thơm gỗ thông. Lịch không trùng đêm nào.', icon='bed',
              color='#6f8f6a', light='#eef4e6', weather='Sương lạnh 12°C', work='Khách', station='Quầy lễ tân',
              greeting='Xem lịch phòng, đón khách, dọn phòng đúng thứ tự và tính hóa đơn từng dòng nhé.',
              caption='Năm căn phòng, rất nhiều câu chuyện trên đồi', map_label='10 · HOMESTAY MÂY'),
    people=PEOPLE,
    staff=[('Chị Lành', 'housekeeping', 'Dọn phòng nhanh, nhớ từng góc bụi.', 80, 88), ('Tín', 'reception', 'Nhớ tên khách, dò mã đặt phòng rất nhanh.', 84, 80),
           ('Bà Sáu', 'kitchen', 'Chiên trứng lòng đào đều tay, dậy từ 5 giờ.', 70, 93), ('Nhung', 'housekeeping', 'Cẩn thận, hay tìm ra đồ khách bỏ quên.', 72, 95)],
    roles={'housekeeping': 'Buồng phòng', 'reception': 'Lễ tân', 'kitchen': 'Bếp sáng'},
    inventory=dict(items=ITEMS, capacity=40),
    prices={'thong': 30, 'suong': 28, 'gac': 36, 'quy': 48, 'ho': 44, 'breakfast': 12, 'guide': 8},
    tip=2,
    physical=('hs_clean', 'hs_welcome', 'hs_settle', 'hs_serve', 'hs_egg', 'hs_repair', 'hs_safety', 'hs_deep', 'hs_garden'),
    free_actions=(),
    no_tick=('hs_line', 'hs_pick', 'hs_release', 'hs_plate', 'hs_rate', 'hs_desk'),
    waste_items=('tray',),
    activity=('🏡', 'Homestay gọn gàng', [('Ga gối bẩn', 'Giỏ đồ giặt'), ('Mì ly minibar', 'Kệ minibar'), ('Khăn tắm ướt', 'Giỏ đồ giặt'), ('Nước suối tặng', 'Kệ minibar')],
              ['Mở cửa sổ, tháo ga', 'Cọ phòng tắm', 'Trải ga, xếp khăn', 'Kiểm phòng, báo sạch']),
    stories=[('Cuốn sổ góp ý của Ông Lâm', ('Ông Lâm để lại cuốn sổ bìa da: “Tôi ghi hết những gì nhà cháu làm chưa tới.” Trang đầu dày đặc chữ.',
                                           'Bạn sửa từng điều nhỏ: bản lề cửa kêu, rèm hở sáng, nút tai cho phòng giáp đường. Ông đọc lại, gật gù.',
                                           'Trang cuối ông viết: “Nhà Mây giờ yên như nhà tôi.” Cuốn sổ được đặt ở quầy cho khách sau cùng viết.')),
             ('Bà Sáu và món trứng lòng đào', ('Bà Sáu chiên trứng 30 năm, không cần đồng hồ. Bà muốn dạy bạn “nghe tiếng mỡ”.',
                                              'Hai bà cháu thử từng quả: tiếng xèo nhỏ dần là lúc nhấc. Bạn làm hỏng 3 quả, bà cười.',
                                              'Bữa sáng nhà Mây có thêm dòng “Trứng lòng đào kiểu bà Sáu” — khách chụp ảnh nhiều nhất.')),
             ('Tấm bản đồ vẽ tay', ('Mai Chi thích bản đồ bạn vẽ tay cho khách. Cô muốn vẽ lại thật đẹp để treo ở quầy.',
                                   'Hai người đi thử từng nơi: đo bậc thang, ghi giờ mở cửa, đánh dấu chỗ nào hợp xe đẩy, người lớn tuổi.',
                                   'Tấm bản đồ “Đà Lạt cho mọi người” treo ở quầy, khách nào cũng chụp lại trước khi đi.'))],
    review_asides=['Phòng thơm mùi gỗ thông, chăn ấm như ổ mèo 🐱', 'Hóa đơn ghi rõ từng chai nước, thích sự minh bạch này.',
                   'Trứng lòng đào chuẩn không cần chỉnh!', 'Sáng ra mở cửa sổ thấy mây bay ngang ban công.'],
    situations=SITUATIONS,
    guide='Lịch phòng → nhận/trả phòng → dọn phòng đúng thứ tự → bữa sáng → gợi ý đi chơi.',
)
