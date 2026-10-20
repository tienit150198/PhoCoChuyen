"""🛎️ Lễ tân Khách sạn Hoa Sứ: a fictional six-room hotel on Phố Hoa Sứ. Rooms, prices, rules and guests are game
content only. The shift is the front desk: take the guest in, understand what they need, put each party in a room
that fits, hand the right key, load the luggage cart, plan the cleaning and the morning services, settle complaints,
find lost things and check people out. The awkward situations around the desk live in DESK (kit desk scripts)."""

PEOPLE = [
    ('Chị Quyên', 'Trưởng ca lễ tân', 'Nói ít, nhớ hết; sổ giao ca phải rõ từng dòng.', 'picky'),
    ('Khoa', 'Lễ tân ca chiều', 'Làm nhanh, khoe còn nhanh hơn; hay nhận luôn việc của người khác.', 'genz'),
    ('Na', 'Lễ tân mới vào', 'Hăng hái, hay lẫn chìa 103 với 108 y như bạn hồi mới vào.', 'genz'),
    ('Cô Lài', 'Buồng phòng', 'Một mình lo sáu phòng, hay báo “xong rồi” hơi sớm.', 'quiet'),
    ('Ông Tư Bến', 'Khách quen tháng nào cũng về', 'Xin phòng nhìn cây sứ, kể chuyện bến sông ngày xưa.', 'warm'),
    ('Chị Diễm', 'Khách khó tính', 'Muốn rẻ, rộng, đẹp, yên tĩnh, nhìn ra phố cùng một lúc.', 'picky'),
    ('Anh Tài', 'Trưởng đoàn khách', 'Đặt phòng hai người mà dắt cả đoàn tới.', 'warm'),
    ('Bé Su', 'Khách nhí', 'Ôm gấu bông Mơ không rời nửa bước.', 'genz'),
    ('Mèo Bơ', 'Mèo của khách sạn', 'Ngồi quầy như quản lý, nhưng không phải quản lý.', 'quiet'),
    ('Khách lưu trú', 'Khách ghé Hoa Sứ', 'Mỗi người một chuyện; ai cũng muốn được nhớ tên.', 'warm'),
    ('Ông Khang', 'Khách đeo kính râm trong nhà', 'Câu nào cũng mở đầu bằng “anh quen giám đốc”.', 'picky'),
    ('Anh Duy', 'Khách đặt phòng cầu hôn', 'Tay cầm hộp nhẫn, mắt dán vào cửa thang bộ.', 'warm'),
]
GUEST_NPC = 9      # a passing guest of a job (its own name and face ride on the task: reception.guest_of)
VIP_NPC, PROPOSE_NPC = 10, 11
CAST = ('quyen', 'khoa', 'na', 'lai', 'tu')            # relations kept in the career data (0..100, start 50)
CAST_NAME = dict(quyen='Chị Quyên', khoa='Khoa', na='Na', lai='Cô Lài', tu='Ông Tư Bến')
CAST_ROLE = dict(quyen='Trưởng ca', khoa='Đồng nghiệp ca chiều', na='Lễ tân mới', lai='Buồng phòng', tu='Khách quen')
CAST_NPC = dict(quyen=0, khoa=1, na=2, lai=3, tu=4)
REL_START, REL_MIN, REL_MAX = 50, 0, 100

# ---------------------------------------------------------------- the six rooms (two floors, no lift)
# beds: 'd' giường đôi, 's' giường đơn. quiet: inner side; street: window on the street; bag: a nook for big luggage.
ROOMS = [
    dict(no='101', beds='ss', cap=2, quiet=False, street=False, bag=True, price=32, note='Cạnh sảnh, có hốc để vali'),
    dict(no='102', beds='d', cap=2, quiet=True, street=False, bag=False, price=38, note='Cửa sổ nhìn cây sứ sân sau'),
    dict(no='103', beds='ds', cap=3, quiet=False, street=True, bag=True, price=46, note='Góc phố, rộng, có hốc để vali'),
    dict(no='201', beds='d', cap=2, quiet=False, street=True, bag=False, price=42, note='Ban công nhìn ra phố đi bộ'),
    dict(no='202', beds='ss', cap=2, quiet=True, street=False, bag=False, price=30, note='Phòng trong, yên nhất nhà'),
    dict(no='203', beds='dd', cap=4, quiet=True, street=True, bag=True, price=58, note='Phòng gia đình, cửa kính dày'),
]
ROOM = {r['no']: r for r in ROOMS}
NEAR = (('101', '102'), ('102', '103'), ('201', '202'), ('202', '203'))   # sát vách, cùng tầng
CHEAP = 35   # "giá rẻ": at most this a night

TAGS = {   # need id: (label on the need step, room test)
    'twin': ('Hai giường riêng', lambda r: len(r['beds']) >= 2),
    'double': ('Có giường đôi', lambda r: 'd' in r['beds']),
    'quiet': ('Phòng yên tĩnh', lambda r: r['quiet']),
    'street': ('Nhìn ra phố', lambda r: r['street']),
    'bag': ('Chỗ để hành lý lớn', lambda r: r['bag']),
    'cheap': (f'Giá rẻ (từ {CHEAP} xu/đêm trở xuống)', lambda r: r['price'] <= CHEAP),
    'ground': ('Tầng trệt, khỏi leo cầu thang', lambda r: r['no'][0] == '1'),
    'near': ('Các phòng sát vách nhau', None),
}
TAG_IDS = tuple(TAGS)
BEDS = dict(ss='2 giường đơn', d='1 giường đôi', ds='1 giường đôi + 1 giường đơn', dd='2 giường đôi')
STATUS = dict(clean='Sạch, trống', dirty='Chưa dọn', busy='Đang có khách')
# What a guest says for each need (said indirectly on purpose: the need step reads through it). Each line: (words, who
# may say it: '' anyone, 'f' a woman, 'm' a man; the party it fits: fewest and most people on the card). Every need has a
# line for one person of either voice, so no card ever hears a "vợ chồng" line from someone alone.
SAYS = {
    'twin': (('Phòng hai giường riêng nha, một giường tôi ngủ, một giường bày đồ nghề.', '', 1, 1),
             ('Hai anh em tôi ngủ riêng giường nha, thằng nhỏ đạp như đá bóng.', '', 2, 3),
             ('Hai đồng nghiệp đi công tác, không ngủ chung giường đâu em.', '', 2, 2),
             ('Tôi với bà bạn già, mỗi người một giường cho thoải mái.', 'f', 2, 2),
             ('Nhà tôi mỗi người quen một giường, đừng dồn chung nha.', '', 3, 4)),
    'double': (('Vợ chồng mới cưới, một giường to là đủ rồi.', '', 2, 2),
               ('Tôi quen nằm giường rộng, giường đơn là lăn xuống đất.', '', 1, 4),
               ('Hai mẹ con ngủ chung một giường cho ấm.', 'f', 2, 2),
               ('Hai cha con ngủ chung một giường cho vui.', 'm', 2, 2)),
    'quiet': (('Tôi ngủ nông lắm, xe máy rồ ga là thức tới sáng.', '', 1, 4),
              ('Mai tôi thi chứng chỉ, cần chỗ thật yên để ôn bài.', '', 1, 4),
              ('Em bé nhà tôi mới ngủ được, có tiếng động là khóc cả đêm.', '', 2, 4)),
    'street': (('Mở cửa sổ phải thấy phố đi bộ cho tôi quay clip nha.', '', 1, 4),
               ('Ông nhà tôi thích ngồi ngắm người qua lại ngoài đường.', 'f', 2, 4),
               ('Em làm vlog, cần khung cửa nhìn ra phố đêm.', '', 1, 4)),
    'bag': (('Tôi mang theo bộ gậy golf với hai vali to đùng.', '', 1, 4),
            ('Tụi tôi chở theo thùng đồ nghề, để ngoài hành lang sợ mất.', '', 2, 4),
            ('Có cái xe đẩy em bé với ba vali, phòng chật là khỏi bước.', '', 2, 4)),
    'cheap': (('Ngân sách eo hẹp lắm, phòng nào rẻ nhất cho tôi.', '', 1, 4),
              ('Sinh viên đi thực tập, em xin phòng rẻ thôi ạ.', '', 1, 2),
              ('Công ty khoán tiền phòng, quá 35 xu là tôi bù túi.', '', 1, 4)),
    'ground': (('Bà cụ nhà tôi đau gối, không leo nổi cầu thang đâu.', '', 2, 4),
               ('Tôi mới mổ chân, đi nạng đó em.', '', 1, 4),
               ('Ông nhà tôi sợ độ cao, ở tầng trệt cho lành.', 'f', 2, 4),
               ('Tôi sợ độ cao, ở tầng trệt cho lành.', '', 1, 4)),
    'near': (('Phòng của mẹ tôi phải sát vách phòng tôi, đêm còn sang xem.', '', 1, 4),
             ('Hai nhà đi chung, cho ở sát nhau để tối qua lại.', '', 1, 4),
             ('Tụi nhỏ ở phòng bên cạnh bố mẹ, chứ xa là không yên tâm.', '', 1, 4)),
}
# Small talk at the desk (never a need): (words, who may say it)
CHATTER = (('Khách sạn mình có wifi không em?', ''), ('Cây sứ ngoài kia nở đẹp ghê.', ''), ('Ủa con mèo này của ai mà ngồi trên quầy vậy?', ''),
           ('Hồi xưa chỗ này là tiệm may đó em biết không.', ''), ('Cho chị xin cái kẹo trong hũ nha.', 'f'), ('Cho anh xin cái kẹo trong hũ nha.', 'm'),
           ('Trời hôm nay nóng muốn xỉu.', ''), ('Em ơi, phố này tối có chợ đêm không?', ''),
           ('Ghi tên anh rõ giùm, lần trước ghi sai chữ Đ.', 'm'), ('Ghi tên chị rõ giùm, lần trước ghi sai dấu.', 'f'))


def says(tag: str, gender: str, people: int) -> list:
    """The lines a guest of `gender` ('male' / 'female') with `people` on the card may say for need `tag`."""
    g = 'f' if gender == 'female' else 'm'
    return [x[0] for x in SAYS[tag] if x[1] in ('', g) and x[2] <= people <= x[3]]


def chatter(gender: str) -> list:
    g = 'f' if gender == 'female' else 'm'
    return [x[0] for x in CHATTER if x[1] in ('', g)]


GUESTS = ('Lê Thị Hạnh', 'Trần Văn Lộc', 'Phạm Minh Thư', 'Nguyễn Gia Bảo', 'Đỗ Thu Trang', 'Hoàng Quốc Việt', 'Vũ Ngọc Ánh',
          'Bùi Thanh Tâm', 'Đặng Hữu Phước', 'Mai Khánh Linh', 'Tạ Văn Hùng', 'Lý Mỹ Duyên', 'Châu Bảo Ngọc', 'Hồ Đức Thịnh')
GUEST_GENDER = {'Lê Thị Hạnh': 'female', 'Trần Văn Lộc': 'male', 'Phạm Minh Thư': 'female', 'Nguyễn Gia Bảo': 'male', 'Đỗ Thu Trang': 'female',
                'Hoàng Quốc Việt': 'male', 'Vũ Ngọc Ánh': 'female', 'Bùi Thanh Tâm': 'female', 'Đặng Hữu Phước': 'male',
                'Mai Khánh Linh': 'female', 'Tạ Văn Hùng': 'male', 'Lý Mỹ Duyên': 'female', 'Châu Bảo Ngọc': 'female', 'Hồ Đức Thịnh': 'male',
                'Ông Tư Bến': 'male'}

# ---------------------------------------------------------------- the key board
KEY_DECOYS = [('k108', '🔑 108 · móc đỏ · kho khăn'), ('k301', '🔑 301 · móc vàng · sân thượng'),
              ('k101o', '🔑 101 · móc xám · ổ cũ đã thay'), ('k230', '🔑 230 · chìa nhà xe')]

# ---------------------------------------------------------------- the luggage cart
# kind: heavy (bottom shelf), fragile (top shelf), tall (the upright frame), plain (anywhere with room)
LUGGAGE = [
    ('vali', 'Vali lớn 23 kg', 'heavy'), ('thung', 'Thùng sách', 'heavy'), ('xelan', 'Xe lăn gấp', 'heavy'),
    ('gom', 'Bình gốm Bát Tràng', 'fragile'), ('banh', 'Hộp bánh kem', 'fragile'), ('dan', 'Hộp đàn violin', 'fragile'),
    ('lan', 'Chậu lan hồ điệp', 'fragile'), ('golf', 'Túi gậy golf', 'tall'), ('vest', 'Túi áo vest treo', 'tall'),
    ('balo', 'Ba lô', 'plain'), ('tui', 'Túi vải', 'plain'), ('non', 'Hộp nón lá', 'plain'),
]
LUGGAGE_INDEX = {k: (label, kind) for k, label, kind in LUGGAGE}
SHELVES = [('bottom', 'Tầng dưới (đồ nặng)', 3), ('top', 'Tầng trên (đồ nhẹ, dễ vỡ)', 3), ('frame', 'Khung dựng (đồ dài, đồ treo)', 2)]
SHELF_CAP = {k: n for k, _, n in SHELVES}
SHELF_OF = dict(heavy='bottom', fragile='top', tall='frame')

# ---------------------------------------------------------------- the handover (sổ giao ca)
ASKS = [   # a pending job a guest asks for at the desk (id, what the guest says, the handover line)
    ('wake', 'Mai gọi báo thức giùm lúc 5 giờ 30 nha.', 'Gọi báo thức 5:30 cho khách {name}'),
    ('pillow', 'Cho xin thêm một cái gối, cổ tôi đau.', 'Mang thêm 1 gối lên cho khách {name}'),
    ('deposit', 'Tiền cọc để chiều tôi chuyển khoản nha.', 'Khách {name} chưa đóng cọc, chiều nhắc lại'),
    ('taxi', 'Sáng mai đặt giùm xe ra bến lúc 7 giờ.', 'Đặt xe ra bến 7:00 cho khách {name}'),
    ('safe', 'Gửi tạm cái máy ảnh vào két ở quầy giùm.', 'Máy ảnh của khách {name} đang ở két quầy, trả khi khách hỏi'),
    ('cake', 'Tối nay sinh nhật tôi, 9 giờ mang bánh kem lên phòng giùm nha.', 'Mang bánh sinh nhật lên phòng khách {name} lúc 21:00'),
]
ASK_INDEX = {a[0]: a for a in ASKS}
DONE_LINES = [   # handover decoys: things already done at the desk, or never asked
    ('d_chia', 'Đã giao chìa phòng cho khách {name}'), ('d_ids', 'Đã khai báo lưu trú cho khách {name}'),
    ('d_wifi', 'Khách {name} hỏi mật khẩu wifi'), ('d_map', 'Đưa bản đồ phố cho khách {name}'),
]

# ---------------------------------------------------------------- the cleaning plan (điều phối dọn phòng)
HK_NOTES = [   # a dirty room's next arrival: (id, label, minutes from 06:00 or None)
    ('lobby', 'Khách đang ngồi chờ ở sảnh', -1),
    ('t10', 'Khách tới 10:00', 240), ('t11', 'Khách tới 11:30', 330), ('t13', 'Khách tới 13:00', 420),
    ('t14', 'Khách tới 14:00', 480), ('t16', 'Khách tới 16:00', 600), ('none', 'Hôm nay chưa có khách đặt', 99999),
]
LAI_REPORT = [
    ('towel', 'Kiểm nhanh thấy khăn tắm còn là khăn cũ, thùng rác chưa đổ.', 'redo'),
    ('fine', 'Kiểm nhanh: ga phẳng, khăn mới, thùng rác sạch, minibar đủ.', 'accept'),
    ('hair', 'Kiểm nhanh: ga mới nhưng gối còn tóc, ly chưa thay.', 'redo'),
]
LAI_OPTIONS = [('accept', 'Nhận phòng, cảm ơn cô Lài, báo phòng sẵn sàng'),
               ('redo', 'Nói riêng với cô Lài chỗ còn sót, phụ mang khăn lên, chưa giao phòng'),
               ('scold', 'Nhắc cô Lài ngay ở sảnh cho khách nghe để lần sau nhớ'),
               ('self', 'Bỏ quầy, tự lên dọn lại cả phòng')]
HELP_OPTIONS = [('na', 'Nhờ Na mang khăn sạch lên phụ cô Lài 20 phút, ghi vào sổ giao ca'),
                ('khoa', 'Gọi Khoa ca chiều vào sớm, không báo chị Quyên'),
                ('wait', 'Để cô Lài làm một mình, khách chờ thì xin lỗi'),
                ('sell', 'Giao trước phòng chưa kiểm cho khách đang chờ')]

# ---------------------------------------------------------------- the morning services (lịch dịch vụ sáng mai)
SLOT_FROM, SLOT_TO, SLOT_STEP = 5 * 60, 9 * 60, 15      # 05:00 … 09:00, every 15 minutes
FEES = dict(wake=0, tray=8, air=30, bus=15)
SERVICE_NAMES = dict(wake='Báo thức', tray='Khay ăn sáng', air='Xe ra sân bay', bus='Xe ra bến xe', wake2='Báo thức')
SERVICE_RULES = ('Báo thức: đúng giờ khách dặn.', 'Khay ăn sáng lên phòng: 15 phút sau giờ báo thức của phòng đó.',
                 'Xe ra sân bay: đón trước giờ bay đúng thời gian đi đường cộng 1 tiếng 30 làm thủ tục.',
                 'Xe ra bến xe khách: đón trước giờ xe chạy đúng thời gian đi đường cộng 15 phút.',
                 'Anh Phát (xe đối tác) chỉ có một xe: hai chuyến cách nhau dưới 80 phút thì chuyến sau gọi hãng xe Sông Mây.')
CLASH_OPTIONS = [('second', 'Giữ anh Phát cho chuyến sớm, gọi hãng xe Sông Mây cho chuyến sau, báo giá trước cho khách'),
                 ('share', 'Dồn hai khách đi chung một xe cho tiện'),
                 ('early', 'Bảo khách chuyến sau đi sớm thêm một tiếng'),
                 ('none', 'Không trùng giờ: giữ anh Phát cho cả hai chuyến')]

# ---------------------------------------------------------------- complaints (phàn nàn)
RATES = (30, 40, 50, 60)
COMPLAINTS = {   # id: (what is really wrong, rant, verify option id, (fault evidence, no-fault evidence), % of a night if at fault, unit to call)
    'noise': ('Phòng bên ồn tới 1 giờ sáng', 'Khách sạn gì mà như cái chợ! Cả đêm không ngủ được, cái thang bộ cũng xấu nữa!',
              'log', ('Sổ ca đêm: 23:40 phòng bên có khách gọi phản ánh ồn, chưa ai lên nhắc.', 'Sổ ca đêm: phòng bên trống cả đêm; tiếng ồn từ quán nhậu đầu hẻm.'),
              10, 'Báo ca đêm nhắc giờ yên tĩnh 22:00'),
    'water': ('Không có nước nóng sáng nay', 'Tắm nước lạnh run cầm cập! Mấy người làm ăn kiểu gì vậy, đòi gặp quản lý!',
              'tech', ('Sổ kỹ thuật: bình nóng lạnh tầng 2 nhảy aptomat lúc 5:50, chưa ai bật lại.', 'Sổ kỹ thuật: bình chạy bình thường; khách vặn nhầm vòi lạnh (nút xanh bên phải).'),
              20, 'Báo kỹ thuật kiểm bình nóng lạnh'),
    'charge': ('Bị tính 2 lon nước ngọt minibar', 'Tôi không uống lon nào hết! Tính tiền láo vậy, tôi đăng lên mạng đó!',
               'count', ('Đếm minibar cùng khách: 2 lon vẫn còn nguyên trong tủ, phiếu buồng phòng ghi nhầm.', 'Đếm minibar cùng khách: tủ thiếu 2 lon, vỏ lon trong thùng rác phòng.'),
               0, 'Báo buồng phòng sửa phiếu minibar'),
    'towel': ('Khăn tắm cũ, có vết ố', 'Khăn gì mà vàng khè như khăn lau bàn! Đi khách sạn mà như ở nhà trọ!',
              'room', ('Lên phòng xem: khăn có vết ố thật, nằm lẫn chồng khăn sạch.', 'Lên phòng xem: khăn trắng mới, vết là màu son của khách.'),
              10, 'Báo buồng phòng thay khăn, kiểm chồng khăn'),
    'wifi': ('Wifi chập chờn cả tối', 'Họp online mà rớt mạng năm lần! Mất hợp đồng là tại khách sạn đó!',
             'tech', ('Sổ kỹ thuật: bộ phát tầng 2 treo từ 20:00, khởi động lại lúc 23:00.', 'Sổ kỹ thuật: mạng ổn; máy khách đang bắt nhầm wifi quán cà phê bên cạnh.'),
             10, 'Báo kỹ thuật kiểm bộ phát wifi'),
}
VERIFY_OPTIONS = [('log', 'Xem sổ ca đêm, hỏi người trực'), ('tech', 'Xem sổ kỹ thuật, nhờ kỹ thuật kiểm'),
                  ('count', 'Đếm lại minibar cùng khách'), ('room', 'Lên phòng xem tận mắt cùng khách'),
                  ('trust', 'Tin lời khách, bù luôn cho nhanh')]
RESULT_OPTIONS = [('fault', 'Lỗi có thật: xin lỗi, sửa ngay, bù đúng chính sách'), ('nofault', 'Không phải lỗi khách sạn: giải thích nhẹ nhàng, giúp khách, không bù'),
                  ('free', 'Cho ở miễn phí đêm nay cho khách khỏi đăng mạng')]
LOG_OPTIONS = [('log', 'Ghi sổ phản ánh (giờ, phòng, việc, cách xử lý) và báo bộ phận liên quan'),
               ('skip', 'Xong rồi thì thôi, khỏi ghi'), ('blame', 'Ghi sổ là lỗi của ca trước')]

# ---------------------------------------------------------------- lost things (đồ thất lạc)
LOST = {   # id: (name, colour words, hidden detail asked, visible detail)
    'gau': ('Gấu bông', ('màu kem', 'màu nâu', 'màu hồng'), 'Gấu tên gì, sau lưng thêu chữ gì?', 'Gấu màu gì?'),
    'vi': ('Ví da', ('màu nâu', 'màu đen', 'màu đỏ đô'), 'Trong ví có thẻ gì, tên ai?', 'Ví màu gì?'),
    'kinh': ('Kính râm', ('gọng đen', 'gọng vàng', 'gọng trong'), 'Hộp kính in tên tiệm nào?', 'Kính gọng màu gì?'),
    'sac': ('Sạc dự phòng', ('màu trắng', 'màu xanh', 'màu đen'), 'Sạc có dán sticker hình gì?', 'Sạc màu gì?'),
    'mu': ('Mũ cói', ('vành rộng', 'có nơ xanh', 'có dây da'), 'Trong lót mũ có ghi chữ gì?', 'Mũ kiểu gì?'),
}
PLACES = [('sanh', 'Sảnh'), ('nhahang', 'Nhà hàng'), ('hoca', 'Hồ cá sân sau'), ('cauthang', 'Cầu thang'),
          ('phong', 'Hành lang phòng'), ('quay', 'Quầy lễ tân'), ('cong', 'Cổng, chỗ đón xe')]
OWNER_OPTIONS = [('hidden', 'Hỏi một chi tiết không nhìn thấy từ ngoài: {hidden}'), ('visible', 'Hỏi: {visible}'),
                 ('give', 'Khách nói mất là đưa luôn')]

# ---------------------------------------------------------------- check-out
KEY_BACK = [('ok', 'Khách đưa lại đúng chìa phòng {no}, móc xanh.', 'take'),
            ('wrong', 'Khách đưa chìa móc đỏ số 108 (chìa kho khăn), không phải chìa {no}.', 'ask'),
            ('none', 'Khách nói “để chìa trên giường rồi”, ở quầy không có chìa {no}.', 'call')]
KEY_OPTIONS = [('take', 'Nhận chìa, treo lại đúng móc'), ('ask', 'Đối số chìa: nhờ khách xem lại túi áo, đây là chìa kho'),
               ('call', 'Gọi cô Lài kiểm phòng có chìa trên giường không, rồi mới trả cọc'), ('fine', 'Phạt mất chìa luôn cho chắc')]
HOLD_OPTIONS = [('tag', 'Ghi thẻ gửi đồ hai nửa: nửa đưa khách, nửa buộc vali, cất kho có khóa'),
                ('desk', 'Để vali sau quầy, khách về thì lấy'), ('no', 'Đã trả phòng thì không giữ đồ')]
MINIBAR = [('nuoc', 'Nước suối', 0), ('ngot', 'Nước ngọt', 4), ('snack', 'Snack', 3), ('mi', 'Mì ly', 5)]
LATE_FEE = 50     # trả phòng sau 14:00: phụ thu 50% một đêm

# ---------------------------------------------------------------- the shift's job kinds
KINDS = ('arrival', 'checkout', 'rooms', 'services', 'complaint', 'lost')
ROTA = ('arrival', 'checkout', 'rooms', 'arrival', 'services', 'complaint', 'arrival', 'lost')
POSTS = {
    'arrival': ('Nhận khách', '🛎️', 'Hiểu nhu cầu, xếp phòng, giao chìa'),
    'checkout': ('Trả phòng', '🧾', 'Nhận chìa, tính tiền, giữ đồ'),
    'rooms': ('Điều phối dọn phòng', '🧹', 'Phòng nào dọn trước'),
    'services': ('Lịch dịch vụ', '⏰', 'Báo thức, khay ăn, xe'),
    'complaint': ('Phàn nàn', '😤', 'Nghe, kiểm, bù cho đúng'),
    'lost': ('Đồ thất lạc', '🧸', 'Lần theo đường khách đi'),
}
BONUS = dict(arrival=8, checkout=6, rooms=6, services=7, complaint=7, lost=6)

# ---------------------------------------------------------------- ca thử việc (the probation trial, in the career)
TRIALS = {
    'normal': ('Nhận một khách bình thường', 'Một khách, đủ chỗ, đúng nhu cầu, giao đúng chìa, ghi sổ giao ca.'),
    'early': ('Khách tới sớm, phòng chưa dọn', 'Khách tới sớm 4 tiếng: giữ phòng sắp dọn, mời chờ cho đàng hoàng, dặn ca sau.'),
    'group': ('Một nhóm hai yêu cầu cùng lúc', 'Hai phòng sát nhau, mỗi phòng một yêu cầu riêng, không quên việc dở.'),
}
TRIAL_IDS = tuple(TRIALS)
PRACTICE = {   # what a failed part of the trial says to practise
    'cap': 'Đếm đủ số người của từng nhóm và xem sức chứa phòng trước khi xếp.',
    'need': 'Đọc kỹ lời khách: mỗi câu nói là một yêu cầu (ồn → yên tĩnh, vali to → chỗ để hành lý…).',
    'note': 'Sổ giao ca chỉ ghi việc CÒN DỞ cho ca sau, đủ từng việc khách nhờ.',
}
EARLY_OPTIONS = [('hold', 'Giữ hành lý, mời ngồi uống trà, báo cô Lài dọn phòng đó trước, hẹn giờ gọi khách'),
                 ('dirty', 'Giao luôn phòng chưa dọn, khách tự dọn cũng được'),
                 ('out', 'Bảo khách ra ngoài đi chơi, 14 giờ quay lại'),
                 ('fee', 'Thu phụ thu nhận phòng sớm 100% trước rồi tính')]

# ---------------------------------------------------------------- branches (after the second promotion)
BRANCH_FROM = 2
BRANCHES = {
    'care': ('💗', 'Chăm sóc khách', 'Trưởng bộ phận trải nghiệm khách', 'Phàn nàn và đồ thất lạc thưởng ×1.25.', ('complaint', 'lost')),
    'ops': ('🗂️', 'Điều hành', 'Trưởng ca → Quản lý khách sạn', 'Dọn phòng và lịch dịch vụ thưởng ×1.25.', ('rooms', 'services')),
    'event': ('🎪', 'Sự kiện', 'Điều phối đoàn và sự kiện của phố', 'Nhận khách và trả phòng thưởng ×1.25.', ('arrival', 'checkout')),
    'self': ('🏡', 'Tự kinh doanh', 'Mở homestay của riêng mình', 'Học cách làm chủ: mọi việc thưởng ×1.1, mở lối sang nghề Homestay.', KINDS),
}
BRANCH_IDS = ('none',) + tuple(BRANCHES)
BRANCH_RATE = dict(care=1.25, ops=1.25, event=1.25, self=1.1)

# ---------------------------------------------------------------- keepsakes kept in the Sổ nghề
KEEPS = {
    'gau_drawing': ('🖍️', 'Tranh cảm ơn của bé Su', 'Bé Su vẽ bạn đứng cạnh gấu Mơ, chữ nguệch ngoạc: “Cảm ơn cô chú lễ tân tìm Mơ.”'),
    'tu_photo': ('🖼️', 'Ảnh bến sông năm 1975', 'Ông Tư Bến tặng tấm ảnh bến sông cũ, sau lưng ghi: “Cho người giữ phòng 102 của tôi.”'),
    'cat_badge': ('🐈', 'Thẻ tên “Bơ – không phải quản lý”', 'Thẻ tên ép nhựa khách làm tặng mèo Bơ, giờ dán ở góc quầy.'),
    'hook_labels': ('🏷️', 'Bảng móc chìa dán màu', 'Bạn với Na dán nhãn màu cho từng móc chìa: không ai lẫn 103 với 108 nữa.'),
    'plant_card': ('🌿', 'Thiệp của nhà nghiên cứu cây', 'Tấm thiệp ép lá kèm lời cảm ơn vì đã giữ cây giùm ở sân sau.'),
    'quyen_note': ('📒', 'Trang sổ giao ca chị Quyên ký', 'Chị Quyên ký dưới trang sổ của bạn: “Ghi thế này là ca sau khỏi hỏi.”'),
}
KEEP_MAX = 12

# ---------------------------------------------------------------- the awkward situations at the desk (kit desk scripts)
# Effects: the kit's own (review, xp, patience, money, mark, unmark) plus this career's hook:
#   rel  {cast id: change}   a colleague's or the regular's feeling about you (kept, changes later situations)
#   house int                what the choice cost the hotel (xu), summed in the day's summary
#   keep keepsake id         a keepsake kept in the Sổ nghề
# A script may need relations: rel_min / rel_max {cast id: n} (filtered by the plugin, kit marks stay as they are).
def _o(oid, label, outcome, good, **effects):
    row = dict(id=oid, label=label, hint='', effects=effects, outcome=outcome, good=good)
    return row


def _x(sid, title, emoji, npc, text, options, default, min_day=2, weight=3, tone='gentle', **more):
    row = dict(id=sid, title=title, emoji=emoji, npc=npc, min_day=min_day, tone=tone, at='between', weight=weight, mods=None,
               text=text, options=options, default=default)
    row.update(more)
    return row


DESK = [
    _x('overbook', 'Ca trước bán trùng phòng', '📕', 0,
       'Khách cầm xác nhận đặt phòng 102, nhưng sổ ghi ca trước đã giao 102 cho người khác. Khoa nhún vai: “Hệ thống báo trống mà.” Khách bắt đầu đỏ mặt.',
       [_o('upgrade', 'Nâng hạng lên 203 không thu thêm, xin lỗi đàng hoàng', 'Khách vào 203, khen cửa kính dày. Khách sạn mất một đêm giá cao.', True,
           house=20, review=[5, 'Bị trùng phòng mà lễ tân xử lý êm, còn được lên phòng to.'], rel={'quyen': 3}),
        _o('same', 'Xếp phòng tương đương còn trống, tặng bữa sáng', 'Khách nhận 202, ăn sáng xong thì hết giận.', True,
           house=8, review=[4, 'Trùng phòng thì hơi bực, nhưng được bù bữa sáng.'], rel={'quyen': 5}),
        _o('partner', 'Gửi sang khách sạn đối tác đầu phố, khách sạn trả tiền xe', 'Khách đi taxi sang đối tác, gửi lại một câu “lần sau khỏi”.', None,
           house=35, mark='partner', review=[3, 'Đặt một nơi, ngủ một nẻo.']),
        _o('blame', 'Nói thẳng là lỗi của Khoa ca trước', 'Khách cười khẩy, Khoa đứng hình. Cả sảnh nghe hết.', False,
           review=[2, 'Lễ tân đổ lỗi qua lại ngay trước mặt khách.'], rel={'khoa': -12, 'quyen': -4})],
       'partner', min_day=2),
    _x('rehearsal', 'Phòng bên tập văn nghệ', '🎻', 5,
       '20 giờ, chị Diễm ở 202 gọi xuống: “Tôi cần ngủ sớm!” Phòng 203 là đoàn văn nghệ phường, đang tập trống cơm cho hội diễn mai.',
       [_o('hall', 'Mượn sảnh tầng trệt cho đoàn tập tới 21 giờ, cảm ơn cả hai bên', 'Đoàn xuống sảnh tập, chị Diễm ngủ ngon. Mèo Bơ ngồi xem tới cuối.', True,
           xp=6, review=[5, 'Gọi một cái là yên, lễ tân khéo ghê.']),
        _o('move', 'Đổi chị Diễm sang phòng 102 phía sau, mang đồ giúp', 'Chị Diễm đổi phòng, càm ràm một câu rồi ngủ.', None,
           rel={'lai': -3}, review=[4, 'Phải đổi phòng giữa tối, nhưng được giúp mang đồ.']),
        _o('plugs', 'Tặng nút bịt tai, bảo cố chịu', 'Chị Diễm ném nút bịt tai vào thùng rác.', False,
           review=[2, 'Khách sạn đưa nút bịt tai thay vì xử lý.']),
        _o('police', 'Gọi công an phường lên nhắc đoàn', 'Cả tầng mở cửa ra xem, đoàn văn nghệ giận cả khách sạn.', False,
           review=[2, 'Có chút chuyện mà làm ầm ĩ.', 6])],
       'plugs'),
    _x('crowd', 'Đặt hai người mà tới cả nhóm', '👨‍👩‍👧‍👦', 6,
       'Anh Tài đặt phòng 2 người. Sau lưng anh: vợ, mẹ, hai đứa nhỏ, em vợ, và một con chó cỏ tên Ủn. “Chen chút là được mà em.”',
       [_o('rooms', 'Đếm đủ người, mở thêm phòng trống theo giá đoàn, khai báo lưu trú đủ cả nhóm', 'Cả nhóm có hai phòng sát vách, khai báo đủ. Ủn ngủ ở sân sau.', True,
           xp=6, mark='crowd_ok', review=[5, 'Lễ tân tính giá đoàn cho tụi tôi, khỏi chen chúc.']),
        _o('cram', 'Cho cả 7 người vào một phòng, thêm nệm dưới sàn', 'Nửa đêm có người vấp ngã ở lối thoát hiểm. Chị Quyên gọi bạn lên nói chuyện.', False,
           review=[2, 'Chen chúc như cá mòi.'], rel={'quyen': -8}),
        _o('refuse', 'Từ chối cả nhóm vì đặt sai số người', 'Anh Tài kéo cả đoàn đi, Ủn sủa một tràng.', False,
           review=[1, 'Tới nơi bị đuổi về giữa đêm.'])],
       'refuse'),
    _x('plant', 'Nhà nghiên cứu mang cây khổng lồ', '🌴', GUEST_NPC,
       'Một nhà nghiên cứu khệ nệ ôm chậu cây cao 2 mét: “Mẫu cây quý, phải để trong phòng với tôi!” Cầu thang hẹp, chậu nặng như cối đá.',
       [_o('yard', 'Gửi cây ở sân sau có mái che, ghi thẻ gửi, tưới giùm sáng mai', 'Sáng ra cây tươi rói. Nhà nghiên cứu để lại một tấm thiệp ép lá.', True,
           xp=5, keep='plant_card', review=[5, 'Cây của tôi được chăm như khách VIP.']),
        _o('stairs', 'Khiêng cây lên phòng giùm', 'Chậu vỡ ở chiếu nghỉ, đất vương đầy cầu thang. Cô Lài lau tới khuya.', False,
           rel={'lai': -8}, house=6, review=[2, 'Chậu vỡ, cây gãy ngọn.']),
        _o('no', 'Từ chối, cây để ngoài cổng', 'Nhà nghiên cứu ngồi canh cây ngoài cổng tới khuya.', None,
           review=[3, 'Khách sạn không nhận đồ cồng kềnh.'])],
       'no'),
    _x('demands', 'Rẻ, rộng, đẹp, yên tĩnh, nhìn ra phố', '🧾', 5,
       'Chị Diễm gõ móng lên quầy: “Cho chị phòng rẻ nhất, rộng nhất, đẹp nhất, yên tĩnh nhất, nhìn ra phố. Không có là chị đánh giá 1 sao.”',
       [_o('rank', 'Hỏi chị chọn hai điều quan trọng nhất, cho xem hai phòng hợp nhất rồi để chị chốt', 'Chị Diễm chọn yên tĩnh và giá: lấy 202. “Ừ, vậy cũng được.”', True,
           xp=6, mark='diem_ok', review=[4, 'Không có phòng hoàn hảo, nhưng được chọn đúng cái mình cần.']),
        _o('promise', 'Hứa có đủ cả năm cho chị vui', 'Tối đó chị Diễm phát hiện phòng nhìn phố thì ồn. Đánh giá tới liền.', False,
           mark='diem_angry', review=[1, 'Hứa đủ thứ, giao một phòng ồn ào.']),
        _o('best', 'Đưa luôn phòng đắt nhất cho xong', 'Chị Diễm nhận 203, vừa trả vừa cằn nhằn giá.', None,
           review=[3, 'Phòng đẹp nhưng đâu có rẻ.'])],
       'best'),
    _x('towels', 'Báo đã dọn mà còn khăn cũ', '🧺', 3,
       'Cô Lài báo phòng 201 xong. Khách lên rồi gọi xuống: khăn tắm vẫn là khăn cũ. Hôm nay cô Lài một mình lo cả sáu phòng.',
       [_o('help', 'Nói riêng với cô Lài, tự mang khăn lên, xin chị Quyên thêm người giờ cao điểm', 'Khách có khăn mới trong 5 phút. Cô Lài lí nhí cảm ơn.', True,
           xp=5, rel={'lai': 8, 'quyen': 2}, review=[4, 'Gọi xuống là có khăn mới liền.']),
        _o('report', 'Báo chị Quyên là cô Lài làm ẩu', 'Cô Lài bị nhắc trước cả ca. Từ hôm đó cô ít nói hẳn.', False,
           rel={'lai': -12}, mark='lai_hurt'),
        _o('quiet', 'Lặng lẽ tự thay khăn, không nói ai', 'Khách có khăn, nhưng mai cô Lài vẫn quá tải như cũ.', None,
           patience=-3)],
       'quiet'),
    _x('threat', 'Dọa đánh giá thấp để ở miễn phí', '📱', GUEST_NPC,
       'Một khách giơ điện thoại: “Phòng có con kiến! Miễn phí cho anh đêm nay, không là 1 sao kèm clip 200 nghìn view.”',
       [_o('check', 'Lên phòng xem cùng khách, xử lý con kiến, bù đúng chính sách nếu có lỗi, ghi sổ', 'Có một con kiến thật. Xịt, lau, tặng nước. Khách hết lý do, ở bình thường.', True,
           xp=6, rel={'quyen': 4}, review=[4, 'Nhân viên lên kiểm ngay, xử lý gọn.']),
        _o('free', 'Cho ở miễn phí cho êm chuyện', 'Khách ở free, còn khoe với bạn bè “cứ dọa là được”.', False,
           house=40, mark='freeloader', rel={'quyen': -6}),
        _o('argue', 'Cãi tay đôi: “Kiến thì ở đâu chả có!”', 'Clip lên mạng: “Lễ tân thách khách.”', False,
           review=[1, 'Lễ tân cãi tay đôi với khách.'])],
       'free'),
    _x('teddy', 'Bé mất gấu bông trước giờ lên xe', '🧸', 7,
       'Xe đón đoàn còn 10 phút nữa chạy. Bé Su khóc nấc: gấu Mơ mất rồi. Sáng nay bé đi nhà hàng, ra hồ cá, rồi xuống sảnh.',
       [_o('route', 'Nhờ Na giữ xe 5 phút, đi lại đường bé đi: nhà hàng → hồ cá → sảnh', 'Gấu Mơ nằm úp mặt cạnh hồ cá. Bé Su ôm gấu, chìa ra một bức tranh vẽ vội.', True,
           xp=8, keep='gau_drawing', rel={'na': 4}, review=[5, 'Lễ tân tìm được gấu cho con tôi kịp giờ xe chạy.', 7]),
        _o('post', 'Hứa tìm được thì gửi bưu điện về nhà', 'Xe chạy, bé khóc suốt đường. Tuần sau gấu mới tới nơi.', None,
           review=[3, 'Con tôi khóc cả đường về.', 7]),
        _o('buy', 'Bảo mẹ bé mua con gấu khác', 'Bé Su gào to hơn. Mẹ bé nhìn bạn như nhìn người ngoài hành tinh.', False,
           review=[1, 'Gấu của con là duy nhất mà.', 7])],
       'post'),
    _x('surprise', 'Tổ chức bất ngờ, người yêu cứ đứng ở quầy', '💍', PROPOSE_NPC,
       'Anh khách nhờ trang trí phòng 203 để cầu hôn. Khổ nỗi cô bạn gái cứ đứng ở quầy hỏi chuyện, không chịu lên phòng.',
       [_o('stall', 'Nhờ cô “kiểm giúp chữ ký trên phiếu đăng ký” lâu một chút, Na lên trang trí', 'Mười phút sau cửa 203 mở ra, nến điện, cánh hoa. Cô gật đầu.', True,
           xp=6, rel={'na': 5}, review=[5, 'Lễ tân diễn còn hay hơn diễn viên, cảm ơn cả khách sạn.']),
        _o('tell', 'Nói nhỏ “đang có bất ngờ đó” cho cô đỡ sốt ruột', 'Cô cười: “Em biết rồi.” Anh khách mặt xị như bánh bao.', False,
           review=[2, 'Bất ngờ bị lộ ngay ở quầy.']),
        _o('leave', 'Bỏ quầy lên phòng trang trí cùng anh khách', 'Quầy trống 15 phút, hai khách check-in đứng chờ.', None,
           patience=-4)],
       'leave'),
    _x('cat', 'Con mèo “không phải quản lý”', '🐈', 8,
       'Khách đòi “gặp quản lý”. Khoa chỉ vào mèo Bơ đang nằm trên sổ đăng ký: “Quản lý đây ạ.” Khách không cười.',
       [_o('real', 'Xin lỗi khách, mời ngồi, gọi chị Quyên ra ngay; bế Bơ xuống khỏi sổ', 'Chị Quyên ra, chuyện xong trong 5 phút. Khách vuốt Bơ trước khi về.', True,
           xp=5, keep='cat_badge', review=[4, 'Hỏi quản lý thì có quản lý thật, mèo cũng dễ thương.']),
        _o('joke', 'Phụ họa: “Dạ quản lý đang ngủ trưa”', 'Khách đập quầy bỏ đi, đánh giá về con mèo.', False,
           rel={'khoa': 3}, review=[1, 'Hỏi quản lý thì chỉ con mèo.']),
        _o('shoo', 'Đuổi mèo Bơ ra ngoài cho nghiêm túc', 'Bơ dỗi, nằm chắn cửa thang bộ cả buổi.', None,
           patience=-2)],
       'shoo'),
    _x('passport', 'Khách quên hộ chiếu ở két quầy', '🛂', GUEST_NPC,
       'Khách vừa ra sân bay, hộ chiếu còn nằm trong két quầy. Còn 70 phút nữa đóng quầy thủ tục.',
       [_o('rider', 'Gọi khách xác nhận, gửi xe ôm công nghệ có mã giao, chụp biên nhận', 'Hộ chiếu tới tay khách trước giờ đóng quầy 20 phút. Khách gửi lời cảm ơn.', True,
           xp=6, house=6, review=[5, 'Tôi suýt lỡ chuyến bay, lễ tân cứu tôi.']),
        _o('back', 'Gọi bảo khách tự quay về lấy', 'Khách quay xe về, lỡ chuyến bay, phải đổi vé.', False,
           review=[2, 'Lễ tân bảo tôi tự quay về lấy.']),
        _o('mail', 'Gửi chuyển phát nhanh tới sân bay', 'Gói hàng tới sân bay sau khi máy bay đã cất cánh.', False,
           review=[2, 'Gửi gì mà chậm như rùa.'])],
       'back'),
    _x('blackout', 'Mất điện giữa ca tối', '🔦', 0,
       '21 giờ, cả phố tắt phụt. Sảnh tối om, có tiếng ai gọi ở cầu thang, máy quẹt thẻ thanh toán tắt ngấm.',
       [_o('round', 'Bật đèn sự cố, đi từng tầng hỏi han, phát đèn pin, gọi điện lực, ghi sổ', 'Không ai bị ngã. 40 phút sau có điện, khách khen “nhân viên đi từng phòng”.', True,
           xp=8, rel={'quyen': 5}, review=[5, 'Mất điện mà lễ tân lên tận phòng hỏi han.']),
        _o('wait', 'Ngồi yên ở quầy chờ có điện lại', 'Một bà cụ lần mò cầu thang, trật chân. Chị Quyên phải chở đi băng bó.', False,
           house=10, rel={'quyen': -6}, review=[2, 'Mất điện mà không ai lên hỏi một câu.']),
        _o('candle', 'Thắp nến ở hành lang cho lãng mạn', 'Một ngọn nến đổ, cháy sém thảm. May mà dập kịp.', False,
           house=12, review=[2, 'Thắp nến trong hành lang, sợ muốn xỉu.'])],
       'wait', tone='tense', min_day=3),
    _x('drunk', 'Khách say về khuya', '🍺', 1,
       '1 giờ sáng, một khách loạng choạng vào sảnh, hát to, đòi “chìa tổng” vì quên số phòng mình.',
       [_o('care', 'Đưa nước, nhìn sổ tìm đúng phòng, nhờ bảo vệ đưa lên, không đưa chìa tổng', 'Khách ngủ ngon, sáng ra xuống xin lỗi cả ca.', True,
           xp=5, review=[4, 'Say quá mà vẫn được đưa lên tận phòng.']),
        _o('master', 'Đưa chìa tổng cho khách tự tìm', 'Khách mở nhầm cửa phòng 202 lúc 1 giờ 15. Chị Diễm hét toáng.', False,
           rel={'quyen': -10}, review=[1, 'Nửa đêm có người lạ mở cửa phòng tôi!', 5]),
        _o('clip', 'Quay clip đăng nhóm nhân viên cho vui', 'Clip lọt ra ngoài. Khách say tỉnh dậy, đòi gặp quản lý.', False,
           rel={'khoa': 2, 'quyen': -6})],
       'master', tone='tense', min_day=3),
    _x('early4h', 'Đoàn tới sớm 4 tiếng', '🚌', 6,
       'Đoàn 12 người của anh Tài tới lúc 10 giờ, giờ nhận phòng là 14 giờ. Ba phòng còn chưa dọn, cô Lài một mình.',
       [_o('plan', 'Gửi hành lý vào kho, mời nước, ưu tiên dọn phòng cho người già, gợi ý dạo chợ phố', 'Đoàn đi chợ về thì có phòng. Bà cụ được vào phòng đầu tiên.', True,
           xp=6, rel={'lai': 2}, review=[5, 'Tới sớm mà được lo chu đáo từng người.', 6]),
        _o('dirty', 'Giao luôn phòng chưa dọn, dọn sau', 'Khách vào thấy ga cũ, gọi xuống liên tục. Cô Lài phải dọn khi khách đang ở.', False,
           rel={'lai': -6}, review=[2, 'Vào phòng còn ga của người trước.', 6]),
        _o('lobby', 'Cho cả đoàn ngồi sảnh chờ, không nước, không gửi đồ', 'Sảnh chật cứng vali, khách khác không lối đi.', None,
           patience=-4)],
       'lobby', min_day=3),
    _x('switch3', 'Khách đòi đổi phòng lần thứ ba', '🔄', 5,
       'Chị Diễm xuống quầy lần thứ ba: phòng đầu “ồn”, phòng thứ hai “tối”, giờ phòng thứ ba “điều hòa kêu tạch tạch”.',
       [_o('ask', 'Hỏi rõ chị thấy khó chịu nhất điều gì, cho xem hai phòng trống còn lại rồi chốt lần cuối', 'Chị Diễm chọn 102, ở yên tới sáng. Sáng ra chị chào bạn trước.', True,
           xp=6, rel={'lai': 2}, review=[4, 'Khó tính vậy mà lễ tân vẫn kiên nhẫn.']),
        _o('again', 'Đổi tiếp lần bốn, không hỏi gì', 'Cô Lài dọn thêm phòng thứ tư trong ngày, mặt nặng như chì.', None,
           rel={'lai': -6}),
        _o('refuse', 'Nói thẳng: “Hết đổi rồi chị”', 'Chị Diễm gọi đường dây nóng của chủ khách sạn.', False,
           review=[1, 'Khách đổi phòng có lý do mà bị từ chối thẳng.'])],
       'again', min_day=3),
    _x('vip', 'VIP tự nhận quen giám đốc', '🕶️', VIP_NPC,
       'Một ông khách đeo kính râm trong nhà: “Anh là bạn thân giám đốc. Giảm 50% với cho anh phòng đẹp nhất, nhanh lên.”',
       [_o('proc', 'Lịch sự làm thủ tục như mọi khách, đề nghị gọi giám đốc xác nhận ưu đãi', 'Giám đốc không bắt máy. Ông khách trả đủ, lẩm bẩm “làm việc đúng ghê”.', True,
           xp=5, rel={'quyen': 4}),
        _o('discount', 'Giảm 50% luôn cho chắc ăn', 'Hôm sau giám đốc hỏi: “Ai là bạn tôi vậy?” Chị Quyên nhìn bạn.', False,
           house=25, rel={'quyen': -8}),
        _o('mock', 'Mỉa: “Ai vào đây cũng quen giám đốc hết á anh”', 'Ông khách đập quầy, đánh giá 1 sao kèm chữ “láo”.', False,
           review=[1, 'Lễ tân mỉa khách.'])],
       'discount'),
    _x('suitcase', 'Vali nhầm giữa hai khách giống nhau', '🧳', GUEST_NPC,
       'Hai khách cùng vali xanh, cùng hiệu, cùng sticker Đà Lạt. Một người vừa kéo vali ra xe, người kia hét: “Vali của tôi!”',
       [_o('tags', 'Nhờ xe dừng lại, đối số thẻ hành lý hai nửa, mở cùng lúc có mặt hai bên', 'Thẻ số 14 và 41. Đổi lại đúng chủ, ai cũng thở phào.', True,
           xp=6, review=[5, 'Nhờ thẻ gửi đồ mà khỏi lạc vali.']),
        _o('peek', 'Tự mở vali ra xem đồ bên trong để đoán chủ', 'Khách phát hiện vali bị lục, giận tím mặt.', False,
           review=[1, 'Nhân viên tự ý mở vali của tôi.']),
        _o('swap', 'Đổi đại vali cho hai người rồi tính', 'Đổi sai. Người thứ nhất đã lên xe ra bến.', False,
           house=15, review=[2, 'Về tới nhà mới biết cầm nhầm vali.'])],
       'swap'),
    _x('credit', 'Đồng nghiệp tranh công', '🏅', 1,
       'Họp đầu ca, chị Quyên khen Khoa “xử lý khéo vụ khách quên hộ chiếu hôm qua”. Vụ đó là bạn làm. Khoa cười tươi rói.',
       [_o('book', 'Sau họp nói riêng với chị Quyên, đưa trang sổ giao ca có ghi giờ, tên', 'Chị Quyên gật: “Chị nhớ rồi.” Khoa hơi ngượng, mai mời bạn ly cà phê.', True,
           xp=5, rel={'quyen': 6, 'khoa': -2}, mark='credit_spoken', keep='quyen_note'),
        _o('public', 'Cãi ngay giữa buổi họp', 'Buổi họp thành buổi cãi. Chị Quyên ghi cả hai vào sổ nhắc nhở.', False,
           rel={'quyen': -5, 'khoa': -10}),
        _o('silent', 'Thôi im lặng cho êm', 'Khoa được khen tiếp. Lần sau anh ta còn nhận nhiều hơn.', None,
           rel={'khoa': 4}, mark='credit_silent')],
       'silent', min_day=3),
    _x('rookie', 'Nhân viên mới mắc lỗi mình từng mắc', '🔑', 2,
       'Na đưa khách chìa 108 (kho khăn) thay vì 103, y như bạn hồi tuần đầu. Khách đang đứng trước cửa kho khăn.',
       [_o('teach', 'Đổi chìa cho khách, rồi kể Na nghe lần mình nhầm y vậy; cùng dán nhãn màu móc chìa', 'Na bật cười rồi ghi vào sổ tay. Bảng móc chìa giờ có màu.', True,
           xp=6, rel={'na': 10}, keep='hook_labels'),
        _o('scold', 'Mắng Na ngay trước mặt khách', 'Na mắt đỏ hoe, cả buổi không dám đụng vào bảng chìa.', False,
           rel={'na': -12}),
        _o('do', 'Tự làm hết, khỏi cho Na đụng vào chìa', 'Khách xong việc, nhưng Na chẳng học được gì.', None,
           rel={'na': -3})],
       'do', min_day=2),
    # --- the regular guest's arc (ông Tư Bến): what you did is remembered
    _x('tu_room', 'Ông Tư xin phòng nhìn cây sứ', '🌸', 4,
       'Ông Tư Bến về như mọi tháng, xin phòng 102 nhìn cây sứ, chỗ ông với bà hay ngồi. Hôm nay 102 đã có khách đặt trước.',
       [_o('swap', 'Gọi khách đặt 102 xin đổi sang 202 cùng giá, tặng bữa sáng; giữ 102 cho ông', 'Khách kia vui vẻ đổi. Ông Tư ngồi bên cửa sổ, kể chuyện bà cả buổi.', True,
           xp=6, house=8, rel={'tu': 12}, mark='tu_happy', review=[5, 'Khách sạn nhớ cả cái cửa sổ của tôi.', 4]),
        _o('other', 'Xin lỗi ông, xếp phòng khác yên tĩnh', 'Ông Tư gật, nhưng tối ông ngồi ngoài sân nhìn cây sứ một mình.', None,
           rel={'tu': -4}),
        _o('rule', 'Nói: “Ai đặt trước thì được trước ông ơi”', 'Ông Tư lặng lẽ nhận phòng, sáng ra đi sớm không chào.', False,
           rel={'tu': -10}, mark='tu_sad')],
       'other', min_day=2, weight=4, no_mark='tu_happy'),
    _x('tu_photo', 'Ông Tư mang quà', '🖼️', 4,
       'Ông Tư về, tay cầm gói giấy báo: “Tấm ảnh bến sông năm bảy lăm. Ông giữ lâu rồi, giờ cho người giữ phòng 102 của ông.”',
       [_o('take', 'Nhận bằng hai tay, hỏi ông kể chuyện tấm ảnh', 'Ông kể tới trưa. Tấm ảnh giờ treo trong Sổ nghề của bạn.', True,
           xp=6, keep='tu_photo', rel={'tu': 6}),
        _o('decline', 'Từ chối khéo vì nội quy không nhận quà', 'Ông Tư cất ảnh lại, cười buồn: “Ừ, quà của ông già thôi mà.”', None,
           rel={'tu': -3})],
       'take', min_day=4, weight=4, need_mark='tu_happy', rel_min={'tu': 60}),
    _x('tu_away', 'Ông Tư ở bên kia sông', '🌉', 4,
       'Na kể: tháng này ông Tư Bến đặt phòng ở khách sạn bên kia sông. “Ông bảo bên này không còn ai nhớ ông.”',
       [_o('call', 'Gọi hỏi thăm ông, xin lỗi chuyện lần trước, mời tháng sau về 102', 'Ông im một lúc rồi cười: “Tháng sau ông về.”', True,
           xp=5, rel={'tu': 10}, unmark='tu_sad', mark='tu_happy'),
        _o('let', 'Thôi kệ, khách đi khách tới', 'Phòng 102 tháng đó trống mấy đêm liền.', None, rel={'tu': -2})],
       'let', min_day=4, need_mark='tu_sad', rel_max={'tu': 45}),
    # --- consequences that come back
    _x('freeloader_back', 'Khách “cứ dọa là được” quay lại', '🎭', GUEST_NPC,
       'Ông khách từng dọa đánh giá để ở miễn phí quay lại, dắt theo ba người bạn: “Lần trước em cho anh free rồi, lần này cả nhóm nha.”',
       [_o('policy', 'Lịch sự: lần trước là ngoại lệ, lần này giá như mọi khách; có lỗi thật mới bù', 'Nhóm bạn nhìn nhau, trả tiền đủ. Ông khách hết dọa.', True,
           xp=6, unmark='freeloader', rel={'quyen': 5}),
        _o('again', 'Lại cho free cả nhóm cho êm', 'Bốn người ở free. Chị Quyên đọc sổ, gọi bạn vào phòng.', False,
           house=80, rel={'quyen': -10})],
       'again', min_day=3, weight=4, need_mark='freeloader'),
    _x('partner_bill', 'Khách sạn đối tác gửi hóa đơn', '🧾', 0,
       'Khách sạn đầu phố gửi hóa đơn đêm khách bị chuyển sang hôm trước, kèm lời nhờ: “Mai bên em kẹt một đoàn, bên chị nhận giùm hai phòng nha.”',
       [_o('help', 'Trả hóa đơn đúng hạn, nhận giùm hai phòng nếu còn trống, ghi sổ hai chiều', 'Hai bên giữ mối. Lần sau trùng phòng, bên kia nhận giùm không lấy phí xe.', True,
           xp=5, unmark='partner', rel={'quyen': 4}),
        _o('stall', 'Để hóa đơn đó, nói “sếp đi vắng”', 'Bên kia không nhận khách giùm nữa.', False,
           unmark='partner', rel={'quyen': -4})],
       'stall', min_day=3, weight=4, need_mark='partner'),
    _x('lai_off', 'Cô Lài dỗi, xin nghỉ ngang', '😶', 3,
       'Cô Lài nhắn chị Quyên xin nghỉ hôm nay, “ở đây chẳng ai coi mình ra gì”. Sáu phòng chưa ai dọn.',
       [_o('visit', 'Gọi hỏi thăm cô Lài, nhận lỗi phần mình, chia nhau dọn với Na và Khoa', 'Chiều cô Lài quay lại phụ hai phòng cuối. Cả ca ăn chung hộp xôi.', True,
           xp=6, rel={'lai': 14, 'na': 2}, unmark='lai_hurt'),
        _o('replace', 'Đề nghị chị Quyên tìm người khác thay cô Lài', 'Chị Quyên lắc đầu: “Người ta làm ở đây tám năm rồi em.”', False,
           rel={'lai': -6, 'quyen': -4})],
       'replace', min_day=3, weight=5, rel_max={'lai': 38}),
    _x('diem_back', 'Chị Diễm quay lại với bản in 1 sao', '🧾', 5,
       'Chị Diễm quay lại, tay cầm bản in đánh giá 1 sao của chính chị: “Lần trước hứa yên tĩnh mà ồn cả đêm. Lần này bù cho chị đi.”',
       [_o('fix', 'Xin lỗi chuyện lần trước, xếp phòng 202 yên nhất, ghi “khách cần yên” vào sổ giao ca', 'Chị Diễm ngủ một mạch tới sáng, sửa đánh giá thành 4 sao.', True,
           xp=6, unmark='diem_angry', mark='diem_ok', review=[4, 'Lần này lễ tân nhớ mình cần yên tĩnh. Sửa lại đánh giá.']),
        _o('discount', 'Giảm luôn 50% cho êm', 'Chị Diễm nhận giảm giá, vẫn chê như cũ.', None, house=25),
        _o('argue', 'Nói lần trước chị tự chọn phòng đó mà', 'Chị Diễm đăng thêm một bài dài, gắn tên khách sạn.', False,
           review=[1, 'Lễ tân còn cãi lại khách.'])],
       'discount', min_day=3, weight=4, need_mark='diem_angry'),
    _x('diem_friends', 'Chị Diễm dắt hội bạn tới', '👯', 5,
       'Chị Diễm dẫn bốn chị bạn tới: “Lễ tân ở đây hiểu ý lắm. Mấy bà này còn khó hơn chị.” Mỗi người một yêu cầu, ai cũng nói cùng lúc.',
       [_o('list', 'Ghi yêu cầu từng người, xếp ba phòng sát vách theo điều mỗi chị cần nhất', 'Cả hội ở trọn tuần, để lại đánh giá 5 sao chung.', True,
           xp=8, rel={'quyen': 4}, review=[5, 'Năm bà khó tính mà lễ tân chiều được hết.']),
        _o('same', 'Xếp cả hội vào hai phòng cho gọn', 'Hai chị cãi nhau giành giường cạnh cửa sổ tới nửa đêm.', False,
           review=[2, 'Xếp chung chẳng hỏi ý ai.']),
        _o('rush', 'Bảo cả hội tự chia phòng với nhau', 'Bốn mươi phút sau cả hội mới chia xong, sảnh ồn như chợ.', None, patience=-3)],
       'rush', min_day=4, weight=3, need_mark='diem_ok'),
    _x('tai_big', 'Anh Tài quay lại với cả xe khách', '🚌', 6,
       'Anh Tài nhớ lần trước được giá đoàn, lần này dắt cả xe 16 người, gọi trước đúng 10 phút: “Em xếp giùm anh như lần trước nha.”',
       [_o('plan', 'Đếm phòng trống, nhờ khách sạn đối tác nhận phần dư, chốt giá đoàn và giờ tới', 'Đoàn tới là có danh sách phòng; phần dư sang đối tác có xe đưa.', True,
           xp=8, rel={'quyen': 5}, review=[5, 'Gọi trước 10 phút mà lễ tân lo xong cả đoàn.', 6]),
        _o('cram', 'Nhận hết 16 người vào sáu phòng', 'Hành lang trải đầy nệm, cô Lài khóc thầm trong kho khăn.', False,
           rel={'lai': -8, 'quyen': -6}),
        _o('no', 'Từ chối vì báo gấp quá', 'Anh Tài buồn, nhưng hiểu. Lần sau anh gọi sớm hơn.', None, unmark='crowd_ok')],
       'no', min_day=4, weight=3, need_mark='crowd_ok'),
    _x('credit_again', 'Khoa lại nhận công', '🏅', 1,
       'Lần thứ hai: Khoa báo chị Quyên rằng anh “đã xếp lịch dọn phòng khoa học”. Bảng đó là bạn làm sáng nay.',
       [_o('book', 'Lần này nói rõ trước cả ca, đưa sổ giao ca có tên và giờ', 'Chị Quyên đọc sổ, nhắc Khoa trước cả ca. Khoa đỏ mặt.', True,
           xp=5, rel={'quyen': 5, 'khoa': -6}, unmark='credit_silent', mark='credit_spoken', keep='quyen_note'),
        _o('silent', 'Lại im lặng', 'Khoa được đề xuất thưởng tháng. Bạn thì không.', False, rel={'khoa': 3, 'quyen': -2})],
       'silent', min_day=4, weight=4, need_mark='credit_silent'),
    _x('khoa_coffee', 'Khoa mời cà phê', '☕', 1,
       'Khoa đặt ly cà phê sữa lên quầy: “Vụ hộ chiếu hôm trước… là của bạn. Mình xin lỗi. Tuần này ca tối khó, mình đổi ca giùm bạn nha.”',
       [_o('ok', 'Nhận ly cà phê, cảm ơn, rủ Khoa cùng ghi sổ giao ca cho rõ', 'Từ đó sổ giao ca của hai người ghi tên rành mạch.', True,
           xp=4, rel={'khoa': 10}),
        _o('cold', 'Nhận cà phê nhưng nhắc lại chuyện cũ', 'Khoa gãi đầu, ly cà phê nguội dần.', None, rel={'khoa': -2})],
       'ok', min_day=4, need_mark='credit_spoken', rel_min={'khoa': 30}),
]

MILESTONES = [
    dict(id='desk', label='Đứng vững quầy Hoa Sứ', jobs=15, days=5, kinds=3),
    dict(id='host', label='Thạo cả sáu việc của quầy', jobs=60, days=20, kinds=6),
    dict(id='soul', label='Người giữ chìa khóa Hoa Sứ', jobs=160, days=40, kinds=6),
]
NOTEBOOK = [
    'Mọi nội quy, giá và phòng ở đây là quy tắc hư cấu chỉ dùng trong trò chơi.',
    'Sáu phòng: 101 (2 đơn, có hốc vali, tầng trệt), 102 (đôi, yên, nhìn cây sứ), 103 (đôi + đơn, 3 người, nhìn phố, hốc vali), '
    '201 (đôi, nhìn phố), 202 (2 đơn, yên nhất, rẻ nhất), 203 (2 đôi, 4 người, yên, nhìn phố, hốc vali). Không có thang máy.',
    f'Giá rẻ là từ {CHEAP} xu một đêm trở xuống (101, 202). Sát vách: 101–102, 102–103, 201–202, 202–203.',
    'Nhận khách: nghe hết lời khách, mỗi câu là một yêu cầu; chỉ xếp phòng sạch, trống, đủ người, đủ mọi yêu cầu; nhóm đi chung cần sát vách thì xếp phòng sát vách.',
    'Chìa: mỗi phòng một chìa đúng số, móc xanh. Móc đỏ 108 là kho khăn, móc xám là ổ cũ đã thay.',
    'Xe hành lý: đồ nặng tầng dưới, đồ dễ vỡ tầng trên, đồ dài và đồ treo ở khung dựng; tầng dưới và tầng trên mỗi tầng 3 món, khung dựng 2 món.',
    'Sổ giao ca: chỉ ghi việc còn dở cho ca sau (báo thức, gối, cọc chưa đóng, xe, đồ gửi két, bánh sinh nhật…), việc đã xong thì không ghi.',
    'Dọn phòng: phòng có khách đang chờ ở sảnh dọn trước, rồi theo giờ khách tới, phòng chưa có khách dọn sau cùng. Báo xong thì kiểm nhanh khăn, ga, thùng rác.',
    *SERVICE_RULES,
    f'Phí dịch vụ: báo thức miễn phí, khay ăn sáng {FEES["tray"]} xu, xe sân bay {FEES["air"]} xu, xe bến xe {FEES["bus"]} xu.',
    'Phàn nàn: nghe ra điều thật sự sai, kiểm bằng sổ hoặc tận mắt; lỗi có thật thì bù theo chính sách (ồn 10%, nước nóng 20%, khăn 10%, wifi 10% một đêm; tính sai minibar thì sửa phiếu, không bù thêm); không phải lỗi thì không bù. Luôn ghi sổ phản ánh.',
    'Đồ thất lạc: tìm từ chỗ cuối cùng khách còn thấy đồ trở đi; đối chiếu màu, chỗ, giờ trong sổ đồ thất lạc; trả đồ thì hỏi chi tiết người ngoài không nhìn thấy.',
    f'Trả phòng: tiền = số đêm × giá + minibar + phụ thu trả trễ ({LATE_FEE}% một đêm sau 14:00) − tiền cọc. Nhận chìa thì đối đúng số.',
    'Ca thử việc gồm ba phần: một khách bình thường, khách tới sớm khi phòng chưa dọn, một nhóm hai yêu cầu cùng lúc. Phần nào đạt thì giữ, phần chưa đạt làm lại hôm sau.',
    'Lương ca theo hợp đồng trả khi khép ca; thưởng nhỏ theo từng việc, sai bước thì sửa tại chỗ và thưởng giảm.',
]
