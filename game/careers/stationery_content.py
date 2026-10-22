"""✏️ Tiệm văn phòng phẩm Bút Mây: the words and tables of the stationery shop (game/careers/stationery.py).

Player #483: "tiệm văn phòng phẩm, bán tập vở, bút thước, bọc vở, photo". A small shop across from the school gate:
students buying a pen with their pocket money, parents with the class list the teacher handed out (lớp 1–5 write in
vở ô li, from lớp 6 vở kẻ ngang), covering and labelling notebooks for the new year, photocopying a teacher's revision
sheets. Prices are the cover prices printed on the goods and the shop's posted service board (fixed, never haggled).

Every table is static: an order is a pure function of (day, slot), so validate_state can rebuild it.
"""
from __future__ import annotations

PLACE = 'Tiệm văn phòng phẩm Bút Mây'
OWNER = 'Chú Hai Bút'

PEOPLE = [
    ('Chú Hai Bút', 'Chủ tiệm', 'Mở tiệm đối diện cổng trường ba mươi năm, thuộc lòng danh sách đồ dùng từng lớp.', 'warm'),
    ('Chị Mai', 'Phụ huynh có con vào lớp Một', 'Lần đầu sắm đồ cho con đi học, cầm tờ danh sách cô giáo phát, hỏi kỹ từng món.', 'parent_worried'),
    ('Anh Tuấn', 'Phụ huynh lớp 7', 'Bận đi làm, ghé tiệm lúc sáng sớm, muốn mua nhanh mà đủ.', 'parent_strict'),
    ('Cô Thu', 'Giáo viên Toán trường Phố Mây', 'Hay nhờ photo đề cương ôn tập cho cả lớp, đếm bộ rất kỹ.', 'picky'),
    ('Bé Su', 'Học sinh lớp 3', 'Mua bút bằng tiền heo đất, đếm từng đồng.', 'warm'),
    ('Long', 'Học sinh lớp 8', 'Hay mua đồ phút chót trước giờ học, nói nhanh.', 'genz'),
    ('Bà Bảy', 'Bà ngoại đi mua đồ cho cháu', 'Mắt kém, nhờ tiệm đọc giùm danh sách, bọc vở giùm cho cháu.', 'parent_kind'),
    ('Chú Hùng', 'Nhân viên văn phòng gần đó', 'Ghé mua bút, giấy, photo giấy tờ lúc trưa.', 'quiet'),
]
MENTOR = 0
STUDENTS = (4, 5)
PARENTS = (1, 2, 6)
TEACHER = 3
OFFICE = 7

WRONG_COST = 10
QUALITY_FLOOR = 40
MILESTONES = (2, 4, 8)   # days: the parents' class lists, covering + labelling, the bigger lists
MASTER = (100, 30)
EXPERT = (180, 45)

# ---------------------------------------------------------------- the counter (inventory items; stationery.GOODS)
GROUPS = (('vo', '📒 Vở, tập'), ('but', '🖊️ Bút'), ('dung_cu', '📐 Dụng cụ học tập'), ('cap', '🎒 Cặp, hộp bút'),
          ('dich_vu', '🖨️ Bọc vở, nhãn, photo'))
GOODS = {
    'vp_vo_oli': dict(name='Vở ô li 96 trang', emoji='📗', group='vo', price=8, cost=5, unit='quyển', start=40),
    'vp_vo_ke': dict(name='Vở kẻ ngang 200 trang', emoji='📘', group='vo', price=12, cost=7, unit='quyển', start=40),
    'vp_vo_ve': dict(name='Tập vẽ A4', emoji='📙', group='vo', price=10, cost=6, unit='quyển', start=20),
    'vp_but_bi': dict(name='Bút bi xanh', emoji='🖊️', group='but', price=4, cost=2, unit='cây', start=40),
    'vp_but_chi': dict(name='Bút chì 2B', emoji='✏️', group='but', price=3, cost=1, unit='cây', start=40),
    'vp_but_may': dict(name='Bút máy luyện chữ', emoji='🖋️', group='but', price=25, cost=15, unit='cây', start=12),
    'vp_but_mau': dict(name='Hộp bút màu 12 màu', emoji='🖍️', group='but', price=20, cost=12, unit='hộp', start=12),
    'vp_gom': dict(name='Gôm tẩy', emoji='🧽', group='dung_cu', price=3, cost=1, unit='cục', start=30),
    'vp_thuoc': dict(name='Thước kẻ 20 cm', emoji='📏', group='dung_cu', price=4, cost=2, unit='cây', start=30),
    'vp_compa': dict(name='Com-pa', emoji='📐', group='dung_cu', price=15, cost=9, unit='cái', start=12),
    'vp_bang': dict(name='Bảng con kèm phấn', emoji='🪧', group='dung_cu', price=15, cost=9, unit='bộ', start=12),
    'vp_hop_but': dict(name='Hộp bút', emoji='👝', group='cap', price=25, cost=15, unit='cái', start=10),
    'vp_cap': dict(name='Cặp chống gù', emoji='🎒', group='cap', price=150, cost=100, unit='cái', start=10),
    'vp_giay_boc': dict(name='Giấy bọc vở', emoji='🧻', group='dich_vu', price=2, cost=1, unit='tờ', start=60),
    'vp_nhan': dict(name='Nhãn vở', emoji='🏷️', group='dich_vu', price=2, cost=1, unit='cái', start=60),
    'vp_a4': dict(name='Giấy A4 (xấp 10 tờ)', emoji='📄', group='dich_vu', price=2, cost=1, unit='xấp', start=60),
    'vp_boc': dict(name='Bọc vở', emoji='📔', group='dich_vu', price=3, cost=0, unit='quyển', start=0, service=True, uses='vp_giay_boc'),
    'vp_dan_nhan': dict(name='Dán nhãn, ghi tên', emoji='✍️', group='dich_vu', price=3, cost=0, unit='quyển', start=0, service=True, uses='vp_nhan'),
    'vp_photo': dict(name='Photo 10 trang', emoji='🖨️', group='dich_vu', price=5, cost=0, unit='lượt', start=0, service=True, uses='vp_a4'),
}
NOTEBOOKS = ('vp_vo_oli', 'vp_vo_ke')
PENS = ('vp_but_bi', 'vp_but_chi')
SAY = {
    'vp_vo_oli': 'quyển vở ô li', 'vp_vo_ke': 'quyển vở kẻ ngang', 'vp_vo_ve': 'quyển tập vẽ', 'vp_but_bi': 'cây bút bi xanh',
    'vp_but_chi': 'cây bút chì', 'vp_but_may': 'cây bút máy', 'vp_but_mau': 'hộp bút màu', 'vp_gom': 'cục gôm',
    'vp_thuoc': 'cây thước', 'vp_compa': 'cái com-pa', 'vp_bang': 'bộ bảng con', 'vp_hop_but': 'cái hộp bút', 'vp_cap': 'cái cặp',
    'vp_giay_boc': 'tờ giấy bọc', 'vp_nhan': 'cái nhãn vở', 'vp_a4': 'xấp giấy A4',
}
NUM = {1: 'một', 2: 'hai', 3: 'ba', 4: 'bốn', 5: 'năm', 6: 'sáu', 7: 'bảy', 8: 'tám', 9: 'chín', 10: 'mười'}
WALK_IN = ('vp_but_bi', 'vp_but_chi', 'vp_gom', 'vp_thuoc', 'vp_vo_oli', 'vp_vo_ke', 'vp_vo_ve', 'vp_compa', 'vp_but_mau', 'vp_hop_but',
           'vp_but_may', 'vp_a4')

# The class list a teacher hands out (grade → [(item | 'vo', qty range)]): 'vo' is the class's notebook — lớp 1–5 vở ô li,
# from lớp 6 vở kẻ ngang (RULES). The parent reads the list out; the shop knows which notebook a grade writes in.
LISTS = {
    1: [('vo', (4, 6)), ('vp_but_chi', (2, 3)), ('vp_gom', (1, 1)), ('vp_bang', (1, 1)), ('vp_but_mau', (1, 1))],
    2: [('vo', (6, 8)), ('vp_but_may', (1, 1)), ('vp_but_chi', (1, 2)), ('vp_thuoc', (1, 1)), ('vp_gom', (1, 1))],
    3: [('vo', (6, 8)), ('vp_but_may', (1, 1)), ('vp_thuoc', (1, 1)), ('vp_but_mau', (1, 1))],
    4: [('vo', (8, 10)), ('vp_but_bi', (2, 3)), ('vp_thuoc', (1, 1)), ('vp_vo_ve', (1, 1))],
    5: [('vo', (8, 10)), ('vp_but_bi', (2, 3)), ('vp_thuoc', (1, 1)), ('vp_gom', (1, 1))],
    6: [('vo', (8, 10)), ('vp_but_bi', (3, 4)), ('vp_compa', (1, 1)), ('vp_thuoc', (1, 1))],
    7: [('vo', (9, 12)), ('vp_but_bi', (3, 4)), ('vp_compa', (1, 1)), ('vp_but_chi', (1, 2))],
    8: [('vo', (10, 12)), ('vp_but_bi', (3, 5)), ('vp_thuoc', (1, 1)), ('vp_vo_ve', (1, 1))],
    9: [('vo', (10, 12)), ('vp_but_bi', (3, 5)), ('vp_compa', (1, 1)), ('vp_gom', (1, 1))],
}

# ---------------------------------------------------------------- the day (kit.daily)
MODS = [
    dict(id='normal', emoji='✏️', label='Ngày thường', hint='Học trò ghé mua lẻ, thỉnh thoảng phụ huynh cầm danh sách tới.', weight=4),
    dict(id='school_year', emoji='🎒', label='Mùa tựu trường', hint='Phụ huynh cầm danh sách đồ dùng của lớp tới đông, nhiều người nhờ bọc vở, dán nhãn.', weight=3, min_day=2),
    dict(id='exams', emoji='📝', label='Mùa ôn thi', hint='Thầy cô, học trò nhờ photo đề cương liên tục. Coi chừng hết giấy A4.', weight=2, min_day=3),
    dict(id='rain', emoji='🌧️', label='Trời mưa', hint='Khách ghé ít, ai vào cũng ướt: để vở, giấy xa cửa kẻo ẩm.', weight=1, min_day=2),
]

RULES = [
    'Bán đúng giá in trên bao bì, đúng bảng giá dịch vụ dán ở quầy: không nâng giá mùa tựu trường.',
    'Lớp 1 đến lớp 5 viết vở ô li; từ lớp 6 trở lên dùng vở kẻ ngang. Danh sách ghi “vở” thì đưa đúng loại của lớp đó.',
    'Bọc vở: mỗi quyển một tờ giấy bọc. Dán nhãn, ghi tên: mỗi quyển một cái nhãn.',
    'Photo tính theo lượt 10 trang: một bộ 20 trang là 2 lượt. Nhân số bộ khách cần.',
    'Không photo nguyên cuốn sách đang bán ngoài tiệm: tôn trọng bản quyền tác giả.',
    'Học trò trả bằng tiền tiêu vặt: cộng giá cho vừa số tiền bé mang theo.',
    'Đếm lại món trong túi trước mặt khách, đưa hóa đơn khi khách cần.',
]

DESK = [
    dict(id='fake_pens', title='Mối hàng chào bút giá rẻ không hóa đơn', emoji='📦', npc=0, min_day=2, tone='tense', at='open', weight=2, mods=None,
         text='Một người lạ chở thùng bút bi tới chào giá chỉ bằng nửa đại lý, không hóa đơn, nhãn in nhòe.',
         options=[dict(id='no', label='Từ chối, chỉ nhập hàng có hóa đơn của đại lý', hint='', effects=dict(xp=5), good=True,
                       outcome='Chú Hai gật gù: “Bút nhái viết hai bữa là tắt mực, mất khách cả năm.”'),
                  dict(id='yes', label='Nhập hai hộp bán thử', hint='',
                       effects=dict(money=10, review=[2, 'Bút mua ở tiệm viết được hai ngày là hết mực.', 2]), good=False,
                       outcome='Tuần sau có phụ huynh mang bút trả lại.')],
         default='no'),
    dict(id='book_copy', title='Khách nhờ photo nguyên cuốn sách', emoji='📚', npc=5, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Long đặt lên quầy cuốn sách tham khảo mới mua của bạn: “Chú photo nguyên cuốn giùm con cho rẻ.”',
         options=[dict(id='no', label='Từ chối photo nguyên cuốn, gợi ý mượn thư viện hoặc photo vài trang cần học', hint='',
                       effects=dict(xp=6), good=True, outcome='Long gãi đầu, chép lại mấy trang công thức cần thiết.'),
                  dict(id='yes', label='Photo luôn, kiếm thêm chút', hint='',
                       effects=dict(money=15, review=[2, 'Tiệm photo lậu sách của tác giả.', 3]), good=False,
                       outcome='Cô Thu thấy xấp photo, nhắc nhở tiệm.')],
         default='no'),
    dict(id='paper_jam', title='Máy photo kẹt giấy', emoji='🖨️', npc=0, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Máy photo kêu rè rè rồi đứng im, đèn đỏ nhấp nháy: kẹt giấy ở khay sau.',
         options=[dict(id='fix', label='Tắt máy, mở khay sau, kéo nhẹ tờ giấy theo chiều chạy rồi mới bật lại', hint='', effects=dict(xp=5), good=True,
                       outcome='Máy chạy lại êm ru.'),
                  dict(id='yank', label='Giật mạnh tờ giấy ra cho nhanh', hint='', effects=dict(patience=-4, stock={'vp_a4': -2}), good=False,
                       outcome='Giấy rách vụn kẹt trong trục, mất cả buổi mới gỡ xong.')],
         default='yank'),
    dict(id='wrong_vo', title='Phụ huynh mang vở mua nhầm tới đổi', emoji='🔁', npc=1, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Chị Mai quay lại: hôm qua mua nhầm vở kẻ ngang cho bé lớp Một, cô giáo dặn phải vở ô li. Vở còn nguyên, chưa viết.',
         options=[dict(id='swap', label='Đổi ngay sang vở ô li, chỉ cho chị cách nhận biết', hint='', effects=dict(xp=6, review=[5, 'Tiệm đổi vở cho con nhanh gọn, chỉ kỹ.', 1]), good=True,
                       outcome='Chị Mai cảm ơn rối rít, hứa năm sau lại ghé.'),
                  dict(id='no', label='Hàng bán rồi miễn đổi', hint='', effects=dict(review=[2, 'Vở còn nguyên mà tiệm không cho đổi.', 1]), good=False,
                       outcome='Chị Mai buồn bã ra về.')],
         default='swap'),
    dict(id='ink_spill', title='Bé làm đổ lọ mực lên quầy', emoji='🫗', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Bé Su thử bút máy, lỡ tay làm đổ lọ mực tím loang ra quầy, sát chồng vở mới.',
         options=[dict(id='calm', label='Dời vở ra trước, lau mực, dặn bé không sao', hint='', effects=dict(xp=4), good=True,
                       outcome='Chồng vở khô ráo, Bé Su hết sợ, còn cười toe.'),
                  dict(id='scold', label='La bé một trận, bắt đền', hint='', effects=dict(stock={'vp_vo_oli': -2}, review=[2, 'Bé lỡ tay mà tiệm la con tôi quá trời.', 1]), good=False,
                       outcome='Trong lúc la, mực thấm hư hai quyển vở.')],
         default='scold'),
    dict(id='rain_paper', title='Mưa tạt vào kệ giấy', emoji='🌧️', npc=0, min_day=2, tone='gentle', at='open', weight=2, mods=('rain',),
         text='Mưa tạt xiên, mấy giọt nước bắn tới kệ giấy A4 gần cửa.',
         options=[dict(id='move', label='Dời kệ giấy vào trong, kéo rèm che cửa', hint='', effects=dict(xp=4), good=True,
                       outcome='Giấy khô ráo, máy photo không kẹt giấy ẩm.'),
                  dict(id='leave', label='Mưa nhỏ, kệ', hint='', effects=dict(stock={'vp_a4': -3}), good=None,
                       outcome='Ba xấp giấy bị ẩm, phải bỏ.')],
         default='leave'),
    dict(id='list_read', title='Bà Bảy nhờ đọc giùm danh sách', emoji='👓', npc=6, min_day=2, tone='gentle', at='between', weight=2, mods=('school_year',),
         text='Bà Bảy quên kính, đưa tờ danh sách nhòe chữ: “Con đọc giùm bà coi cháu lớp mấy, cần những gì.”',
         options=[dict(id='help', label='Đọc từng dòng, gom đủ đồ, ghi giá từng món vào tờ giấy cho bà', hint='', effects=dict(xp=6, review=[5, 'Tiệm đọc danh sách giùm bà, gom đồ đủ cả.', 6]), good=True,
                       outcome='Bà Bảy cười móm mém, dúi cho bạn viên kẹo gừng.'),
                  dict(id='rush', label='Đưa đại một bộ đồ dùng có sẵn cho nhanh', hint='', effects=dict(review=[3, 'Tiệm đưa đồ không đúng danh sách của cháu.', 6]), good=False,
                       outcome='Hôm sau cháu bà phải ra đổi hai món.')],
         default='rush'),
    dict(id='exam_rush', title='Cô Thu cần gấp 40 bộ đề', emoji='📝', npc=3, min_day=3, tone='tense', at='between', weight=2, mods=('exams',),
         text='Cô Thu chạy vào: “Mai kiểm tra rồi, em photo gấp 40 bộ đề, chiều cô lấy được không?”',
         options=[dict(id='plan', label='Nhận, kiểm giấy A4 trong kho trước, hẹn giờ lấy rõ ràng', hint='', effects=dict(xp=6, money=20), good=True,
                       outcome='Chiều cô Thu lấy đủ 40 bộ, thẳng thớm từng xấp.'),
                  dict(id='promise', label='Hứa đại cho vui lòng khách', hint='', effects=dict(review=[2, 'Hứa có mà tới giờ chưa photo xong.', 3]), good=False,
                       outcome='Hết giấy giữa chừng, cô Thu phải chờ.')],
         default='promise'),
]

INTRO = dict(
    title='Một ngày ở tiệm văn phòng phẩm',
    lead='Tiệm Bút Mây đối diện cổng trường. Mọi món bày hết trên quầy: vở, bút, thước, cặp, cùng dịch vụ bọc vở, dán nhãn, photo. '
         'Nghe khách cần gì, chạm từng món vào giỏ, đủ rồi bấm Giao.',
    work=[['📒', 'Vở ô li cho lớp 1–5, kẻ ngang từ lớp 6'], ['📋', 'Gom đủ danh sách đồ dùng của lớp'],
          ['📔', 'Bọc vở, dán nhãn ghi tên'], ['🖨️', 'Photo đề cương theo lượt 10 trang']],
    meet=[['🧔', 'Chú Hai Bút chủ tiệm'], ['👩', 'Phụ huynh đầu năm học'], ['👩‍🏫', 'Cô Thu dạy Toán'], ['🧒', 'Học trò mua lẻ']],
    stars=[['✅', 'Đủ món, đúng loại vở'], ['🧮', 'Tính đúng lượt photo'], ['💰', 'Vừa tiền tiêu vặt']],
    short=[['📒', 'Đúng loại vở theo lớp'], ['📋', 'Gom đủ danh sách lớp'], ['🖨️', 'Bọc vở, dán nhãn, photo']],   # the intro card's three rows
)
