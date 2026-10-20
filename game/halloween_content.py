"""🎃 Lễ hội Ma Phố (Halloween 2026): the words and the numbers players see (game/halloween.py holds the rules).

Places: the town's own amenities (game/town_layout.json ids, the 2.5D signposts are 'place:<id>'), each with two riddles; a
day hides PUMPKINS of them (a hash of the day), the riddle of that day's pick shown in the sheet with CHOICES places.
Shop: 🎨 Phong cách cosmetics (game/spend_content.py HALLOWEEN_TITLES / HALLOWEEN_FRAMES / HALLOWEEN_COLORS, kept for good
through a live_effects row of kind 'hween'), one pet piece of the wardrobe's Halloween set, and a capped bag of xu.
"""
from __future__ import annotations

NAME, ICON = 'Lễ hội Ma Phố', '🎃'

# The six days (Vietnam dates): a name, a line for the sheet and the start card, and one small bonus of the day
# (kind: 'checkin' | 'pump' | 'treat' | 'host', +n candy on each of those).
DAYS = {
    '2026-10-26': dict(icon='🎃', title='Phố treo đèn bí ngô', bonus=('checkin', 5),
                       line='Khai hội! Cả phố treo đèn bí ngô, kẹo điểm danh hôm nay thêm 5 viên.'),
    '2026-10-27': dict(icon='🐈‍⬛', title='Đêm mèo đen', bonus=('pump', 1),
                       line='Mèo đen lượn khắp hẻm, mỗi quả bí ngô tìm được thêm 1 viên kẹo.'),
    '2026-10-28': dict(icon='👻', title='Ngõ ma lém lỉnh', bonus=('host', 1),
                       line='Ma lém lỉnh gõ cửa từng nhà: chủ nhà được thêm 1 viên mỗi lượt khách gõ.'),
    '2026-10-29': dict(icon='🕸️', title='Hẻm mạng nhện', bonus=('pump', 1),
                       line='Mạng nhện giăng đầy hẻm, bí ngô nấp kỹ hơn: mỗi quả thêm 1 viên kẹo.'),
    '2026-10-30': dict(icon='🧙', title='Chợ phù thủy', bonus=('treat', 1),
                       line='Phù thủy mở chợ đêm: đi xin kẹo được bốc thêm 1 viên mỗi nhà.'),
    '2026-10-31': dict(icon='🎭', title='Đêm hội hóa trang', bonus=None,
                       line='Đêm Halloween! Từ 19:00 mọi viên kẹo nhân đôi, bí ngô khổng lồ hiện ra ở công viên.'),
}
GRACE_LINE = 'Lễ hội đã khép lại. Bạn vẫn đổi kẹo lấy quà đến hết ngày 01/11.'

# id (town_layout amenity), name, (riddle, riddle)
PLACES = (
    ('bank', 'Ngân hàng', ('Nơi két sắt to nhất phố, chú bảo vệ đứng cửa cả ngày.',
                           'Gửi tiền, rút tiền, xếp hàng lấy số.')),
    ('temple', 'Chùa Gió Lành', ('Chuông ngân mỗi sáng, khói hương thơm, ai cũng nói khẽ.',
                                 'Nơi người ta tới thắp nén nhang và góp chút công đức.')),
    ('cinema', 'Rạp Mây', ('Tắt hết đèn mà ai cũng nhìn về một phía, tay cầm bắp rang.',
                           'Ghế đỏ xếp hàng, màn trắng thật to, suỵt đừng nói chuyện.')),
    ('cafe', 'Cà phê ngoài trời', ('Ly đen đá, ghế nhựa thấp, ngồi ngắm người qua lại.',
                                   'Tiếng muỗng khuấy leng keng, mùi rang xay thơm cả góc phố.')),
    ('spa', 'Spa Sen', ('Nằm thư giãn, mùi tinh dầu, đá nóng đặt trên lưng.',
                        'Nơi đắp mặt nạ dưa leo mà không ai thấy lạ.')),
    ('karaoke', 'Phòng hát Mây', ('Micro, đèn chớp, ai cũng thành ca sĩ một bài.',
                                  'Phòng kín cách âm, bài nào cũng có lời chạy trên màn hình.')),
    ('walk', 'Công viên Bờ Sen', ('Hồ sen, ghế đá, sáng sớm đầy người chạy bộ.',
                                  'Đi dạo vòng quanh hồ, gió mát rượi, có cả lì xì rơi.')),
    ('date', 'Góc hẹn hò', ('Ghế đôi, đèn dây lấp lánh, ai tới cũng đi thành cặp.',
                            'Nơi người ta hẹn nhau “gặp ở chỗ cũ nhé”.')),
    ('wedding', 'Nhà cưới', ('Cổng hoa, áo dài đỏ, nhạc “Ngày vui” vang cả xóm.',
                             'Nơi cô dâu chú rể nâng ly trăm năm.')),
    ('auction', 'Nhà đấu giá', ('Ai trả cao nhất, búa gõ “cộc” một cái là xong.',
                                'Đồ độc bản xếp hàng chờ người giơ bảng.')),
    ('pets', 'Thú cưng', ('Meo meo, gâu gâu, có cả cát vệ sinh và cần câu mèo.',
                          'Nơi nhận nuôi một bé bốn chân về nhà.')),
    ('garage', 'Gara xe', ('Mùi dầu nhớt, cờ lê, mấy chiếc xe nằm chờ chủ.',
                           'Chỗ cất xe, rửa xe, thay bánh.')),
    ('travel', 'Đại lý vé', ('Vé máy bay, vé tàu, ai muốn đi xa thì ghé.',
                             'Tấm bản đồ thế giới treo tường, cô bán vé hỏi “đi đâu đó?”.')),
    ('board', 'Bảng tin cư dân', ('Giấy dán chi chít: tìm mèo lạc, cho thuê phòng, rao bán xe.',
                                  'Ai có chuyện gì cũng ghim lên đây cho cả xóm đọc.')),
    ('rank', 'Bảng xếp hạng', ('Ai giỏi nhất phố đều có tên ở đây.',
                               'Tên người đứng đầu sáng choang, người thứ hai thì tiếc hùi hụi.')),
    ('gadgets', 'Điện thoại & đồ dùng', ('Ốp lưng, sạc dự phòng, màn hình sáng choang.',
                                         'Máy mới vừa ra là có người xếp hàng từ sáng.')),
)
PLACE = {p[0]: p for p in PLACES}
PUMPKINS = 5            # pumpkins hidden a day
CHOICES = 4             # places offered under a riddle (one right)

# 🍬 Cho kẹo hay bị ghẹo: what the visitor gets ({host} is the host's name)
TREATS = (
    '{host} bốc cho bạn một nắm kẹo 🍬',
    '{host} mở cửa, cười tít mắt, dúi vào túi bạn mấy viên kẹo dẻo 🍬',
    'Nhà {host} có cả rổ kẹo bí ngô, bạn được lấy một nắm 🎃',
    '{host} đang hóa trang ma cà rồng, vẫn nhớ chia kẹo cho bạn 🧛',
    '{host} tặng bạn túi kẹo gừng nhà làm 🍬',
    '{host} rắc kẹo vào túi bạn như rắc phép thuật ✨',
)
TRICKS = (
    'Nhà {host} hết kẹo! Bạn ghẹo lại bằng cách vẽ râu mèo lên cửa 🐈‍⬛ (được 1 viên an ủi)',
    '{host} giả làm ma nhát bạn một phen 👻, rồi đền 1 viên kẹo',
    'Bạn bị {host} đố một câu khó quá, chỉ được 1 viên 🤔',
    'Cửa nhà {host} phát ra tiếng cười ma quái… bạn chạy mất dép, nhặt được 1 viên 😱',
    '{host} lén dán mạng nhện giả lên vai bạn 🕸️ (kèm 1 viên kẹo xin lỗi)',
)
TRICK_PCT = 30          # % of knocks that are a trick

# 🎁 Đổi kẹo: id, candy, kind (style | pet | xu), what (a style id, a wardrobe piece id, or xu), emoji, name, line
SHOP = (
    dict(id='t_hw_san_bi_ngo', cost=40, kind='style', emoji='🎃', name='Thợ săn bí ngô', line='Danh hiệu trọn đời'),
    dict(id='pet_vong_keo', cost=60, kind='pet', piece='vong_keo', emoji='🍬', name='Vòng kẹo Halloween cho thú cưng',
         line='Món tủ đồ thú cưng (bậc D), thuộc Bộ Halloween'),
    dict(id='f_hw_doi', cost=100, kind='style', emoji='🦇', name='Khung dơi đêm', line='Khung hồ sơ trọn đời'),
    dict(id='t_hw_ma_lem', cost=150, kind='style', emoji='👻', name='Ma lém lỉnh', line='Danh hiệu trọn đời'),
    dict(id='c_hw_bi_ngo', cost=220, kind='style', emoji='🟠', name='Màu tên Bí ngô ma mị', line='Màu tên trọn đời, cam sang tím'),
    dict(id='f_hw_nhen', cost=300, kind='style', emoji='🕸️', name='Khung mạng nhện', line='Khung hồ sơ trọn đời'),
    dict(id='t_hw_ba_tuoc', cost=450, kind='style', emoji='🧛', name='Bá tước Phố Mây', line='Danh hiệu trọn đời, khó nhất mùa'),
    dict(id='xu', cost=50, kind='xu', coins=20_000, emoji='💰', name='Túi kẹo đổi 20.000 xu',
         line='Tối đa 3 lần cả mùa. Tài khoản từ 3 ngày tuổi, nhân vật từ ngày sống thứ 3.'),
)
SHOP_ITEM = {x['id']: x for x in SHOP}

# 🏆 Bảng kẹo (candy earned over the season, never what was spent): granted when the season closes
TOP_ITEMS = ((1, 3, ('t_hw_vua_keo', 'f_hw_bi_ngo_vang')), (4, 10, ('t_hw_top_keo',)))
# every 🎨 id this event may grant (game/spend_content.py defines them; tests keep the two in step)
STYLE_IDS = frozenset([x['id'] for x in SHOP if x['kind'] == 'style'] + [i for _, _, ids in TOP_ITEMS for i in ids])
PET_PIECES = frozenset(x['piece'] for x in SHOP if x['kind'] == 'pet')
