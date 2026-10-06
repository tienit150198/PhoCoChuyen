"""Tip hên xui: career norms, customer voices, gifts and lines (rules in game/tips.py).

Everything here is fixed content. Lines under CAREER_LINES carry no pronoun, so any
voice can say them; VOICE_LINES address the player the way that kind of customer
would ({self} = the elder's own kinship word, {ac} = "anh"/"chị", {gv} = "thầy"/"cô").
"""
from __future__ import annotations

# ---------------------------------------------------------------- career norms
# rate  chance of a tip (money or a gift) after a 5★ job, average customer, ordinary day;
# cash  share of those tips that are money (the rest are thank-you gifts, no money);
# lo/hi bounds in xu of an ordinary cash tip (5–15% of the bill, rounded to a nice number);
# bill  typical price of one job, used when the ledger shows no payment for the task.
NORMS = {
    # hands-on service where tipping is common
    'tour_guide': dict(rate=.34, cash=.85, lo=5, hi=20, bill=90),
    'salon': dict(rate=.36, cash=.85, lo=5, hi=20, bill=120),
    'delivery': dict(rate=.30, cash=.90, lo=2, hi=10, bill=25),
    'homestay': dict(rate=.32, cash=.80, lo=5, hi=20, bill=150),
    'restaurant': dict(rate=.30, cash=.85, lo=3, hi=15, bill=45),
    'cafe_bakery': dict(rate=.28, cash=.80, lo=2, hi=10, bill=40),
    'pet_care': dict(rate=.34, cash=.80, lo=5, hi=20, bill=80),
    # counters where a tip is a nice surprise
    'milk_tea': dict(rate=.20, cash=.80, lo=2, hi=8, bill=35),
    'florist': dict(rate=.22, cash=.75, lo=3, hi=15, bill=80),
    'mother_baby': dict(rate=.20, cash=.70, lo=3, hi=10, bill=60),
    'grocery': dict(rate=.16, cash=.75, lo=2, hi=8, bill=40),
    'repair': dict(rate=.22, cash=.80, lo=3, hi=15, bill=60),
    'farm': dict(rate=.14, cash=.60, lo=2, hi=10, bill=40),
    'tra_da': dict(rate=.16, cash=.80, lo=1, hi=3, bill=6),   # glasses of 3 xu: a tip is a coin or two
    'clothing': dict(rate=.16, cash=.65, lo=2, hi=10, bill=70),
    'pet_shop': dict(rate=.18, cash=.70, lo=2, hi=10, bill=50),
    'fruit': dict(rate=.14, cash=.70, lo=1, hi=5, bill=14),     # a kilo of fruit: the change is the tip
    'drain': dict(rate=.22, cash=.80, lo=2, hi=8, bill=20),     # a household call-out: a little extra for a clean job
    'garbage': dict(rate=.08, cash=0, lo=0, hi=0, bill=25),     # residents thank the crew with a drink, never money
    'homemaker': dict(rate=.10, cash=0, lo=0, hi=0, bill=18),   # the family thanks with food from the kitchen, never money
    'ice_cream': dict(rate=.12, cash=.65, lo=1, hi=4, bill=10),  # a cone or a cup: the coins are the tip
    'com': dict(rate=.08, cash=.60, lo=1, hi=3, bill=14),        # a plate of rice: the small change is the tip
    'nail': dict(rate=.18, cash=.70, lo=1, hi=5, bill=15),       # a regular rounds up for a neat set
    'pho': dict(rate=.10, cash=.60, lo=1, hi=4, bill=10),        # a bowl of phở: the small change stays on the table
    'photobooth': dict(rate=.12, cash=.60, lo=1, hi=4, bill=18),  # a group rounds the bill up after a good strip
    'giupviec': dict(rate=.30, cash=.85, lo=2, hi=8, bill=30),   # a happy client presses a note into your hand at the door
    'naucom': dict(rate=.16, cash=.55, lo=2, hi=6, bill=45),     # a family slips a little extra into the market change
    'babysitter': dict(rate=.10, cash=0, lo=0, hi=0, bill=18),  # the money tip comes with the day's pay; the blocks get thanks
    'pagoda': dict(rate=.06, cash=0, lo=0, hi=0, bill=8),       # visitors thank with fruit or tea, never money
    # rare, and mostly a thank-you gift: money would not be right here
    'accounting': dict(rate=.08, cash=.30, lo=3, hi=10, bill=50),
    'pharmacy': dict(rate=.07, cash=0, lo=0, hi=0, bill=30),
    'teacher': dict(rate=.08, cash=0, lo=0, hi=0, bill=65),
    'customer_care': dict(rate=.06, cash=0, lo=0, hi=0, bill=40),
    'corp_accounting': dict(rate=.05, cash=0, lo=0, hi=0, bill=70),
    'tax_payroll': dict(rate=.05, cash=0, lo=0, hi=0, bill=70),
    'group_accounting': dict(rate=.05, cash=0, lo=0, hi=0, bill=70),
    'hr_admin': dict(rate=.05, cash=0, lo=0, hi=0, bill=60),
    'secretary': dict(rate=.05, cash=0, lo=0, hi=0, bill=60),
    'it_helpdesk': dict(rate=.06, cash=0, lo=0, hi=0, bill=60),
    # ✈️ Hãng bay Cánh Cò: nobody tips the crew; a thank-you now and then
    'pilot': dict(rate=.06, cash=0, lo=0, hi=0, bill=12),
    'flight_attendant': dict(rate=.07, cash=0, lo=0, hi=0, bill=8),
    # 🏥 Bệnh viện Lá Sen: never money (no envelopes on the ward); a letter or a drawing now and then
    'nurse': dict(rate=.06, cash=0, lo=0, hi=0, bill=10),
}
DEFAULT_NORM = dict(rate=.15, cash=.70, lo=2, hi=10, bill=40)
OFFICE = ('corp_accounting', 'tax_payroll', 'group_accounting', 'hr_admin', 'secretary', 'it_helpdesk')

# Round a tip to what people actually hand over.
NICE = (1, 2, 3, 5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100)
BIG_SHARE = .5          # a surprise tip is about half the bill…
BIG_LO, BIG_HI = 20, 100  # …at least 20 xu (or twice the usual top tip at a cheap stall), at most 100

# How the quality of the job moves the chance (fair stars, before any twist).
STARS = {5: 1.0, 4: .5, 3: .12}
# A customer who grumbled at the counter rarely tips; any cut, refund or walkout never does.
REACTION = {'accept': 1.0, 'grumble': .25}

# Luck of the day: days when people are softer with their money.
GENEROUS_DAYS = {'payday': 1.35, 'tet': 1.5, 'festival': 1.3, 'wedding': 1.2, 'weekend': 1.15,
                 'holiday': 1.2, 'market': 1.1, 'fair': 1.1}
FESTIVAL_MODE = 1.3     # the street's "Ngày hội" (journey luck of the day)

# Per-customer generosity: a seeded trait of each person (see tips.generosity).
GENEROSITY = ((.55, 25), (1.0, 50), (1.6, 20), (2.2, 5))   # (factor, weight)
PERSONA_GENEROSITY = {'warm': 1.25, 'parent_kind': 1.2, 'genz': 1.05, 'quiet': .95,
                      'sour': .8, 'picky': .8, 'bossy': .85, 'parent_strict': .8, 'parent_worried': .95}
HARSH_DAY = .25         # the reviewer is having a bad day (rude, entitled, drama…)

# ---------------------------------------------------------------- voices
ELDER_WORDS = ('ông', 'bà', 'cụ', 'bác', 'cô', 'chú', 'dì', 'thím', 'mợ', 'dượng')
KID_WORDS = ('bé', 'nhóc', 'cháu')
TOURISTS = (
    ('Anh Mark', 'Úc'), ('Chị Emma', 'Anh'), ('Chị Yuki', 'Nhật'), ('Anh Min-jun', 'Hàn'),
    ('Bà Claire', 'Pháp'), ('Anh Lukas', 'Đức'), ('Chị Sofia', 'Tây Ban Nha'), ('Ông Robert', 'Mỹ'),
)

VOICE_LINES = {
    'plain': (
        'Em làm khéo ghê!',
        'Cảm ơn em nha, làm kỹ quá.',
        'Chút tiền cà phê cho em nhé.',
        'Làm chu đáo vậy thì phải cảm ơn chứ.',
        'Giữ lấy mua ly nước nha em.',
        'Hôm nay gặp được người làm có tâm, vui ghê.',
        'Em cầm lấy, làm vậy là xứng đáng lắm.',
    ),
    'shy': (
        'Ừm… em cầm giúp nhé.',
        'Cái này… cho em. Cảm ơn nha.',
        'Không nhiều đâu… em nhận nhé.',
        'Làm tốt lắm… cảm ơn em.',
        'Cảm ơn… lần sau lại nhờ em.',
    ),
    'cheerful': (
        'Trời ơi ưng quá, cầm lấy nè!',
        'Vui ghê, hôm nay gặp đúng người khéo tay!',
        'Cảm ơn em nhiều nhiều nha, mai ghé nữa!',
        'Nè nè, tip cho người dễ thương!',
        'Làm đẹp vậy thì phải thưởng chứ!',
        'Hí hí, lần sau lại nhờ em nha!',
    ),
    'elder': (
        'Cháu cầm lấy, {self} cho uống nước.',
        'Làm cẩn thận vậy {self} mừng lắm, cháu cất đi.',
        'Có chút đỉnh thôi, con nhận đi.',
        'Hồi trẻ {self} cũng làm nghề, thấy cháu làm kỹ là quý.',
        'Cầm lấy, đừng ngại, {self} cho mà.',
        'Giỏi quá, cháu cất đi mà mua bánh.',
    ),
    'busy': (
        'Cảm ơn em, mình chạy đi họp đây!',
        'Nhanh gọn quá, giữ lấy nhé, mình trễ giờ rồi!',
        'Cầm lấy nha, mình đi đây, cảm ơn nhiều!',
        'Làm lẹ mà chuẩn, đúng thứ mình cần. Cảm ơn nha!',
        'Deadline dí mà được việc thế này là mừng. Tip nhé!',
    ),
    'genz': (
        'Xịn xò quá, tip nè!',
        'Đỉnh thiệt sự, nhận tip đi bạn ơi ✨',
        'Mê ghê, lần sau ghé tiếp nha!',
        'Cảm ơn bạn nha, mười điểm không có nhưng!',
        'Ưng xỉu, gửi bạn chút tip nè 🫶',
        'Chill ghê, cảm ơn bạn nhiều!',
    ),
    'kid': (
        'Mẹ dặn con gửi {ac} ạ!',
        'Ba bảo con đưa {ac} tiền uống nước ạ!',
        'Con cảm ơn {ac} nhiều ạ!',
    ),
    'tourist': (
        'Thank you so much! Cảm ơn nhiều!',
        'Wonderful! Cảm ơn nha!',
        'Best day in Vietnam! Cảm ơn!',
        'Very kind, very good. Tip for you!',
        'Xin cảm ơn! Thank you, thank you!',
    ),
    'parent': (
        'Nhà mình cảm ơn {gv} nhiều ạ.',
    ),
}

# Pronoun-free lines about the job itself (any adult voice can say them).
CAREER_LINES = {
    'salon': ('Tóc lên form đẹp ghê!', 'Màu này lên ảnh chắc xinh lắm.', 'Gội đầu êm quá, suýt ngủ quên luôn.',
              'Cắt đúng kiểu mình muốn luôn!', 'Tóc nhẹ hẳn cả đầu.'),
    'restaurant': ('Tô mì hôm nay chuẩn vị!', 'Nước dùng đậm đà, ăn sạch tô luôn.', 'Món ra nóng hổi, ưng ghê.',
                   'Ăn xong muốn gọi thêm tô nữa.'),
    'cafe_bakery': ('Bánh còn ấm, thơm lừng.', 'Cà phê đậm vừa đúng khẩu vị.', 'Chữ trên bánh viết đẹp quá!',
                    'Bánh su kem ngon như hồi xưa.'),
    'milk_tea': ('Ly trà sữa chuẩn vị luôn!', 'Đường đá vừa y chang đã dặn.', 'Trân châu dẻo ngon quá trời.',
                 'Nắp dán đẹp ghê.'),
    'florist': ('Bó hoa này chắc người ta mê lắm.', 'Gói hoa khéo quá, không nỡ mở.', 'Hoa tươi rói, cảm ơn nhiều.',
                'Thiệp viết đúng ý luôn.'),
    'grocery': ('Tính tiền nhanh gọn, cảm ơn nha.', 'Xếp đồ vào túi gọn ghê.', 'Nhớ cả món quen, dễ thương quá.',
                'Mua ở đây yên tâm ghê.'),
    'delivery': ('Hàng tới nguyên vẹn, cảm ơn nha!', 'Giao đúng giờ luôn, mát ruột.', 'Trời nắng vậy mà vẫn tới kịp.',
                 'Hộp đồ ăn còn nóng hổi nè.'),
    'homestay': ('Phòng thơm tho sạch sẽ quá.', 'Ngủ ngon như ở nhà.', 'Chỉ chỗ ăn sáng ngon ghê.',
                 'Ly trà chào khách ấm lòng lắm.'),
    'pet_care': ('Bé cưng thơm phức luôn!', 'Móng tỉa gọn mà bé không sợ.', 'Bé quấn quá, chưa chịu về.',
                 'Lông mượt như nhung.'),
    'repair': ('Máy chạy êm re như mới.', 'Sửa nhanh mà giải thích dễ hiểu.', 'Không bắt thay đồ lung tung, quý ghê.',
               'Tưởng phải bỏ rồi, ai dè sống lại.'),
    'farm': ('Rau tươi xanh mướt!', 'Trứng gà còn ấm tay.', 'Cà chua chín đỏ đẹp quá.', 'Hái đúng độ chín luôn.'),
    'tra_da': ('Chè đậm, đá mát, uống đã khát!', 'Cốc sạch bong, ngồi yên tâm.', 'Pha chè có tay rồi đấy.',
               'Ngồi gốc bàng gió mát, không muốn về.'),
    'clothing': ('Tìm đúng size, mặc vừa như đo.', 'Phối đồ khéo ghê, mặc lên sáng hẳn.', 'Cho thử thoải mái, không hối.',
                 'Tư vấn thật lòng, không nói quá.'),
    'pet_shop': ('Tư vấn thức ăn kỹ ghê, bé ăn ngon.', 'Bể cá lên đẹp, cá khỏe re.', 'Dặn dò kỹ, nuôi yên tâm hẳn.',
                 'Không bán bừa, quý tiệm ghê.'),
    'fruit': ('Trái ngọt lịm, cân đủ luôn.', 'Lựa trái giùm khéo ghê.', 'Cân nhanh, tính gọn.', 'Mua ở đây yên tâm, không sợ trái dập.'),
    'garbage': ('Ngõ sạch bong, cảm ơn tổ thu gom.', 'Tối nào cũng đúng giờ, quý lắm.', 'Nhắc phân loại dễ nghe ghê.',
                'Làm cực mà lúc nào cũng vui vẻ.'),
    'drain': ('Thông một phát nước rút ào ào.', 'Báo giá rõ ràng, làm đúng giá.', 'Dọn sạch sẽ, không một vết bẩn.',
              'Giải thích dễ hiểu, cảm ơn thợ.'),
    'homemaker': ('Cơm nấu vừa miệng cả nhà.', 'Nhà cửa sạch bong, gọn gàng.', 'Sổ chợ rõ ràng từng xu.',
                  'Bà với các cháu quý lắm.'),
    'nail': ('Mười móng đều tăm tắp, y ảnh mẫu.', 'Dụng cụ hấp sạch, dũa mới bóc trước mặt.', 'Gel bóng, hai tuần chưa bong.',
             'Nhẹ tay, không đau chút nào.'),
    'com': ('Cơm dẻo, sườn thơm mùi than.', 'Nước mắm vừa miệng, chan là mê.', 'Nhớ cả lời dặn ăn chay của mẹ tôi.',
            'Dĩa cơm đầy đặn, xới nhanh tay.'),
    'photobooth': ('Ô nào cũng mở mắt, cười tươi.', 'Nhớ đúng từng sticker tụi mình dặn.', 'Cắt thẳng tắp, có bao kiếng đàng hoàng.',
                   'Canh bấm máy đúng lúc, không phải chụp lại.'),
    'giupviec': ('Nóc tủ vuốt tay không dính bụi.', 'Bình hoa đặt lại y chỗ cũ.', 'Nhớ đúng lời dặn, bàn làm việc không ai động.',
                 'Sàn lau nước sạch, thơm mà không nồng.'),
    'naucom': ('Cơm nhà nóng hổi, vừa miệng cả nhà.', 'Nhớ cả lời dặn kiêng muối của ông.', 'Đi chợ khéo, tiền chợ còn dư.',
               'Sổ chợ rõ ràng, hóa đơn đủ cả.'),
    'babysitter': ('Bé về nhà vui, kể về cô suốt bữa tối.', 'Nhớ từng dòng giấy dặn, không phải nhắc.', 'Nhật ký trong ngày rõ ràng, kể thật.',
                   'Bé ăn ngoan, ngủ ngon.'),
    'ice_cream': ('Viên kem tròn xoe, đủ gam luôn.', 'Kem lạnh mịn, không chảy giọt nào.', 'Nhớ cả lời dặn dị ứng của bé.',
                  'Múc nhanh, cười tươi, bé nhà mê lắm.'),
    'pho': ('Nước dùng trong, ngọt xương.', 'Tái chín hồng, bánh tơi mềm.', 'Nhớ cả lời dặn không mì chính.',
            'Bưng ra nóng hổi, húp cạn tô.'),
    'pagoda': ('Sân chùa sạch, mát quá.', 'Thầy nói chuyện nhẹ nhàng, dễ nghe.', 'Chỉ dẫn tận tình, không làm khách ngượng.',
               'Cơm chay ngon, đúng là chay.'),
    'mother_baby': ('Món quà đúng ý bé luôn.', 'Tư vấn kỹ, không bán thừa món nào.', 'Gói quà xinh quá trời.',
                    'Tìm đúng món cho bé rồi.'),
    'tour_guide': ('Chuyến đi đáng nhớ lắm!', 'Kể chuyện hay, cả đoàn mê.', 'Ảnh chụp đẹp ghê, về khoe liền.',
                   'Đi cả ngày mà không ai bị lạc, giỏi thiệt.'),
    'accounting': ('Sổ sách rõ ràng, đọc là hiểu.', 'Nhờ vậy mà khỏi lo cuối tháng.'),
    'pharmacy': ('Dặn kỹ cách dùng, yên tâm hẳn.', 'Hỏi han kỹ lưỡng quá.'),
    'teacher': ('Bé về kể chuyện lớp suốt buổi tối.', 'Bé tự làm bài được rồi, mừng ghê.'),
    'customer_care': ('Giải quyết gọn gàng, cảm ơn nhiều.', 'Nghe máy dễ chịu ghê.'),
    'corp_accounting': ('Hồ sơ gọn gàng, sếp khen.', 'Số liệu khớp từng dòng.'),
    'tax_payroll': ('Bảng lương khớp từng đồng.', 'Nhờ vậy mà kịp hạn nộp.'),
    'group_accounting': ('Sổ hợp nhất khớp từng dòng.', 'Báo cáo gọn, họp nhẹ cả người.'),
    'hr_admin': ('Hồ sơ của em được giải quyết nhanh ghê.', 'Bảng công rõ ràng, lương về đủ.'),
    'secretary': ('Lịch gọn gàng, không ai phải chờ.', 'Lời nhắn ghi đủ, gọi lại đúng giờ.'),
    'it_helpdesk': ('Máy chạy lại rồi, cứu một bàn thua trông thấy.', 'Giảng dễ hiểu, lần sau tự làm được.'),
    'pilot': ('Hạ cánh êm ru, cả khoang vỗ tay.', 'Thông báo rõ ràng, nghe là yên tâm.'),
    'flight_attendant': ('Tiếp viên chu đáo quá, cảm ơn nhiều.', 'Chuyến bay dễ chịu ghê.'),
    'nurse': ('Hỏi tên, ngày sinh kỹ lưỡng, yên tâm ghê.', 'Giải thích từng bước, cả nhà bớt lo.', 'Báo bác sĩ kịp lúc, cảm ơn nhiều.'),
}

# Thank-you gifts that carry no money: (emoji, what).
GIFTS = {
    'salon': (('🧋', 'một ly trà sữa'), ('🍰', 'hộp bánh bông lan'), ('💌', 'tấm thiệp viết tay'), ('🍊', 'mấy trái quýt ngọt')),
    'restaurant': (('🌶️', 'hũ tương ớt nhà làm'), ('🍋', 'bịch chanh vườn nhà'), ('💌', 'lời khen viết vội trên khăn giấy')),
    'cafe_bakery': (('🎨', 'bức vẽ nguệch ngoạc trên khăn giấy'), ('🌼', 'một nhành cúc nhỏ'), ('🍬', 'mấy viên kẹo dừa')),
    'milk_tea': (('🍬', 'một nắm kẹo'), ('📝', 'tờ giấy note vẽ ly trà sữa'), ('🍌', 'nải chuối nhà trồng')),
    'florist': (('🍪', 'hộp bánh quy'), ('💌', 'tấm thiệp cảm ơn'), ('🍵', 'gói trà sen')),
    'grocery': (('🍈', 'trái bưởi Năm Roi'), ('🥭', 'mấy trái xoài cát'), ('🍠', 'bịch khoai lang luộc')),
    'delivery': (('🥤', 'chai nước mát'), ('🥖', 'ổ bánh mì nóng'), ('🍬', 'mấy viên kẹo gừng')),
    'homestay': (('☕', 'gói cà phê rang từ quê'), ('📖', 'dòng cảm ơn trong sổ lưu bút'), ('🍪', 'hộp bánh đặc sản')),
    'pet_care': (('🦴', 'túi bánh thưởng cho các bé ở tiệm'), ('📸', 'tấm ảnh bé cưng có chữ “cảm ơn”'), ('🍩', 'hộp bánh donut')),
    'repair': (('☕', 'ly cà phê sữa đá'), ('🍌', 'nải chuối'), ('🍊', 'bịch cam')),
    'farm': (('🌱', 'gói hạt giống quý'), ('🍯', 'hũ mật ong rừng'), ('🥚', 'rổ trứng gà ta')),
    'tra_da': (('🍙', 'nắm xôi xéo còn nóng'), ('🍌', 'nải chuối chín'), ('🥜', 'gói lạc rang nhà làm')),
    'clothing': (('🧋', 'một ly trà sữa'), ('💌', 'tấm ảnh mặc đồ mới kèm lời cảm ơn'), ('🍊', 'mấy trái quýt')),
    'pet_shop': (('📸', 'tấm ảnh bé cưng ở nhà mới'), ('🍪', 'hộp bánh quy'), ('🌼', 'chậu sen đá nhỏ')),
    'fruit': (('🥖', 'ổ bánh mì nóng'), ('🍵', 'ly trà đá mát'), ('💌', 'lời cảm ơn viết trên giấy gói')),
    'garbage': (('🥤', 'chai nước mát'), ('🍌', 'nải chuối chín'), ('🍰', 'gói bánh bông lan')),
    'drain': (('☕', 'ly cà phê sữa đá'), ('🍲', 'tô bún bò nóng'), ('💌', 'tấm thiệp cảm ơn')),
    'homemaker': (('🥒', 'hũ dưa cải bà Lành muối'), ('🎨', 'bức tranh bé Su vẽ'), ('🍊', 'túi cam quê anh Dũng')),
    'nail': (('🌸', 'chậu sen đá nhỏ để bàn làm móng'), ('🍯', 'hũ mứt gừng nhà làm'), ('💌', 'tấm thiệp cảm ơn vẽ bàn tay')),
    'com': (('🍋', 'bịch chanh nhà trồng của chú Bình'), ('🌿', 'bó húng quế bà Sương trồng'), ('🥬', 'bó rau muống non của chị Lụa')),
    'photobooth': (('🎞️', 'một dải ảnh cả nhóm tặng lại'), ('🍬', 'bịch kẹo dẻo hội bạn chia'), ('💌', 'tấm thiệp vẽ cái máy ảnh')),
    'giupviec': (('🍵', 'gói trà bà Xuân gói sẵn'), ('🍰', 'hộp bánh anh Tùng để trên bàn'), ('🐟', 'túi bánh cá chị Hà mua cho bạn')),
    'naucom': (('🐟', 'bịch khô cá cô Lệ phơi'), ('🎨', 'bức tranh mâm cơm bé Bin vẽ'), ('📜', 'bài thơ ông Toàn chép tay')),
    'babysitter': (('🎨', 'bức tranh bé vẽ bằng bút sáp'), ('🍘', 'túi bánh gạo bé chia cho'), ('💌', 'tấm thiệp mẹ bé viết tay')),
    'ice_cream': (('🎨', 'bức tranh cây kem bé vẽ bằng bút sáp'), ('🍬', 'nắm kẹo me trong túi áo học sinh'), ('💌', 'tấm thiệp cảm ơn của lớp 2A')),
    'pho': (('🍙', 'gói xôi xéo chị Nguyệt để phần'), ('🎨', 'bức tranh nồi phở bé Bống vẽ'), ('🫙', 'chai tương đen anh Sáu mang từ Sài Gòn')),
    'pagoda': (('🍊', 'túi cam Phật tử biếu'), ('🍵', 'gói trà mạn ông Bảy gửi'), ('💌', 'tấm thiệp bé Na vẽ quả chuông')),
    'mother_baby': (('🍬', 'gói kẹo mừng đầy tháng'), ('🍰', 'hộp bánh bông lan'), ('💌', 'tấm thiệp bé nhà vẽ')),
    'tour_guide': (('🔑', 'móc khóa lưu niệm từ quê khách'), ('💌', 'tấm bưu thiếp có chữ ký cả đoàn'), ('🍫', 'thanh sô-cô-la ngoại')),
    'accounting': (('🍯', 'hũ mứt gừng nhà làm'), ('🍊', 'bịch cam sành'), ('💌', 'lời cảm ơn viết tay')),
    'pharmacy': (('💌', 'mẩu giấy cảm ơn viết tay'), ('🍊', 'mấy trái quýt'), ('🌼', 'nhành hoa cúc')),
    'teacher': (('🎨', 'tấm thiệp bé tự vẽ'), ('🌸', 'bông hoa bé hái ở vườn'), ('💌', 'lá thư cảm ơn của phụ huynh'),
                ('🍪', 'hộp bánh quy bé nướng cùng mẹ')),
    'customer_care': (('💌', 'email cảm ơn gửi riêng'), ('⭐', 'lời khen gửi lên quản lý'), ('📝', 'tin nhắn cảm ơn thật dài')),
    'corp_accounting': (('🍰', 'hộp bánh mời cả phòng'), ('☕', 'ly cà phê đặt trên bàn'), ('💌', 'tin nhắn khen gửi sếp')),
    'tax_payroll': (('🍰', 'hộp bánh mời cả phòng'), ('☕', 'ly cà phê đặt trên bàn'), ('🍊', 'túi cam để trên bàn')),
    'group_accounting': (('🍰', 'hộp bánh mời cả phòng'), ('☕', 'ly cà phê đặt trên bàn'), ('💌', 'tin nhắn khen gửi sếp')),
    'hr_admin': (('🍰', 'hộp bánh mời cả phòng'), ('🧋', 'ly trà sữa đặt trên bàn'), ('💌', 'tấm thiệp cảm ơn của bạn mới vào')),
    'secretary': (('☕', 'ly cà phê đặt trên bàn'), ('🍊', 'túi cam khách biếu'), ('💌', 'tin nhắn khen gửi sếp')),
    'it_helpdesk': (('☕', 'ly cà phê sữa đá'), ('🍪', 'hộp bánh quy'), ('💌', 'mẩu giấy “cảm ơn anh IT” dán trên màn hình')),
    'pilot': (('✏️', 'bức vẽ chiếc máy bay của một em nhỏ'), ('🥭', 'mấy trái xoài cát'), ('💌', 'tấm thiệp gửi tổ bay')),
    'flight_attendant': (('💌', 'mẩu giấy cảm ơn kẹp trong túi ghế'), ('🍬', 'gói kẹo dừa Bến Tre'), ('🥭', 'trái xoài chín')),
    'nurse': (('💌', 'lá thư cảm ơn viết tay'), ('📝', 'vài dòng khen trong sổ góp ý của khoa'), ('🎨', 'bức tranh cháu người bệnh vẽ tặng khoa')),
}
DEFAULT_GIFTS = (('💌', 'tấm thiệp cảm ơn'), ('🍊', 'mấy trái quýt'))

# What a customer says with a gift (no money).
GIFT_LINES = {
    'plain': ('Có chút quà, em nhận cho vui nhé.', 'Không nhiều đâu, cảm ơn em.', 'Cầm lấy, coi như lời cảm ơn.'),
    'shy': ('Cái này… cho em.', 'Em nhận giúp nhé… cảm ơn.'),
    'cheerful': ('Quà nhỏ xíu nè, nhận đi mà!', 'Cho em nè, cảm ơn nhiều nha!'),
    'elder': ('Của nhà làm được, cháu cầm lấy.', 'Cháu cầm về ăn cho vui, {self} còn nhiều lắm.'),
    'busy': ('Để đây nha, cảm ơn em nhiều!', 'Chút quà cảm ơn, mình chạy đây!'),
    'genz': ('Quà nè, không nhận là buồn á!', 'Tặng bạn nè, cảm ơn nha 🫶'),
    'kid': ('Con tặng {ac} nè!', 'Cái này con làm đó, tặng {ac} ạ!'),
    'tourist': ('Small gift from my country. Cảm ơn!', 'For you! Cảm ơn nhiều!'),
    'parent': ('Bé nhà mình gửi {gv} ạ, cảm ơn {gv} đã kèm bé.', 'Bé cứ đòi gửi bằng được, {gv} nhận giúp bé nhé.',
               'Nhà mình cảm ơn {gv} nhiều ạ.'),
}

# A workplace whose thank-you gifts have their own words (adult voices; kids and tourists keep theirs).
# At the pagoda nobody "tips": visitors bring fruit or tea for everyone (game/pagoda_voice.py).
CAREER_GIFT_LINES = {
    'pagoda': ('Biếu chùa ít trái cây nhà trồng, nhận cho bà con vui nhé.', 'Có gói trà, pha mời khách thập phương nhé.',
               'Chút lòng thành của nhà, nhận giúp nha.'),
}

# The rare surprise tip.
BIG_LINES = (
    'Hôm nay nhà có chuyện vui, cứ giữ hết đi!',
    'Lâu lắm mới gặp người làm tận tâm vậy. Nhận đi, đừng từ chối nha.',
    'Con gái vừa đậu đại học, hôm nay ai cũng có phần!',
    'Coi như lì xì sớm, lấy hên nha!',
    'Làm vậy còn xứng đáng hơn nhiều, nhận đi.',
    'Mai đi xa rồi, cảm ơn vì mấy lần qua nha.',
    'Vừa được thưởng dự án, chia vui chút xíu!',
)

# The line a happy customer adds to the review.
# A brand-new player's very first customer (tips.welcome): a warm "wow", a small tip and one of these.
WELCOME_LINES = (
    'Người mới hả? Làm khéo ghê, chúc {ac} ngày đầu thật vui nha!',
    'Ngày đầu mà làm ngon vậy! Chút tip mừng {ac} nè.',
    'Lần đầu ghé mà thấy thương quán rồi. Cố lên nha {ac}!',
)
CAREER_WELCOME = {
    'pagoda': ('Lần đầu thấy mặt ở chùa mà làm việc chu đáo ghê. A Di Đà Phật.', 'Hôm đầu mà đã quen việc, bà con lên chùa vui lắm.'),
}
WELCOME_SHARE = .15     # of the bill, rounded to what people hand over, within the career's lo..hi

REVIEW_CASH = ('Có để lại chút tip cảm ơn 💝', 'Tip nhẹ cho người làm có tâm 💝', 'Xứng đáng được tip, sẽ quay lại 💝')
REVIEW_BIG = ('Tip hơi nhiều nhưng xứng đáng lắm 🌟',)
REVIEW_GIFT = 'Có gửi {gift} để cảm ơn 🎁'

# How it reads on screen and in the journal.
TEXT = dict(
    cash='💝 {who} để lại {n} xu tip: “{line}”',
    big='🌟 {who} để lại hẳn {n} xu tip: “{line}”',
    team='💝 {who} gửi {n} xu tip cho cả đội: “{line}”',
    gift='{emoji} {who} gửi {gift}: “{line}”',
)
WHERE = dict(
    till='Tip vào két tiệm.',
    wallet='Tip là tiền riêng của bạn: đã vào ví.',
    team='Cả đội chia nhau, không qua két tiệm.',
    gift='Một món quà cảm ơn, không phải tiền.',
)
LEDGER = 'Tip của khách'
LEDGER_WALLET = 'Tip chuyển về ví'
WALLET_LABEL = 'Tip của khách · {place}'
TOURIST_WHO = '{name} (khách {country} trong đoàn)'
