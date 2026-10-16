"""Khách sạn Sông Mây: a fictional mid-size city hotel. Rooms, rules, prices and guests are game content only."""
from datetime import date, timedelta

PEOPLE = [
    ('Chị Hằng', 'Trưởng ca lễ tân', 'Nhớ mặt khách quen, dặn từng việc nhỏ.', 'warm'),
    ('Anh Bảo', 'Tổ trưởng bảo trì', 'Hộp đồ nghề lúc nào cũng gọn, việc quá tay thì gọi thợ.', 'quiet'),
    ('Cô Tư', 'Trưởng buồng phòng', 'Gấp góc ga giường vuông như thước.', 'picky'),
    ('Bác Khải', 'Khách quen tầng 3', 'Năm nào cũng về ở một tuần, xin phòng yên tĩnh.', 'warm'),
    ('Vy', 'Khách đi du lịch một mình', 'Hay hỏi đường ra bến sông, quay clip mọi góc.', 'genz'),
    ('Anh Toàn', 'Khách công tác', 'Đi sớm về khuya, chỉ cần phòng yên và bữa sáng nhanh.', 'quiet'),
    ('Chị Ngân', 'Khách đi cùng gia đình', 'Hai bé nhỏ, một bé dị ứng đậu phộng.', 'picky'),
]

KINDS = ('checkin', 'housekeeping', 'laundry', 'breakfast', 'repair', 'decor')
POSTS = {
    'checkin': ('Lễ tân', '🛎️', 'Nhận khách'),
    'housekeeping': ('Buồng phòng', '🧹', 'Dọn phòng trả'),
    'laundry': ('Giặt là', '🧺', 'Giặt chăn gối'),
    'breakfast': ('Bữa sáng', '🍳', 'Sắp bữa sáng'),
    'repair': ('Bảo trì', '🔧', 'Sửa trong phòng'),
    'decor': ('Trang trí', '🎀', 'Trang trí theo dịp'),
}
BONUS = dict(checkin=6, housekeeping=6, laundry=5, breakfast=6, repair=7, decor=7)

# Room board: 4 floors x 4 rooms. bed: double / twin / family; view: river / street / garden.
# lift = next to the lift; quiet = far end of the corridor; access = wide door, grab bars, roll-in shower.
ROOMS = [
    ('101', 'double', 'street', 'lift', True), ('102', 'twin', 'garden', '', True),
    ('103', 'double', 'garden', 'quiet', False), ('104', 'family', 'street', '', False),
    ('201', 'double', 'street', 'lift', False), ('202', 'twin', 'river', '', False),
    ('203', 'double', 'river', 'quiet', False), ('204', 'family', 'river', '', False),
    ('301', 'twin', 'street', 'lift', False), ('302', 'double', 'river', '', False),
    ('303', 'twin', 'river', 'quiet', False), ('304', 'family', 'garden', 'quiet', False),
    ('401', 'double', 'street', 'lift', False), ('402', 'family', 'river', '', False),
    ('403', 'double', 'river', 'quiet', False), ('404', 'twin', 'garden', 'quiet', False),
]
BEDS = dict(double='Giường đôi', twin='Hai giường đơn', family='Phòng gia đình (1 đôi + 1 đơn)')
VIEWS = dict(river='Nhìn sông', street='Nhìn phố', garden='Nhìn vườn')
SPOTS = dict(lift='Cạnh thang máy', quiet='Cuối hành lang, yên tĩnh')
CAPACITY = dict(double=2, twin=2, family=4)
STATUS = dict(clean='Sạch, sẵn sàng', dirty='Chưa dọn', occupied='Có khách', maintenance='Đang bảo trì')

# id, what the guest asks, test on (no, bed, view, spot, access)
REQUESTS = [
    ('access', 'Ông đi xe lăn: cần phòng tiếp cận được (cửa rộng, tay vịn, sàn tắm không bậc).', lambda r: r[4]),
    ('river_double', 'Giường đôi, nhìn ra sông.', lambda r: r[1] == 'double' and r[2] == 'river'),
    ('quiet_twin', 'Hai giường đơn, phòng yên tĩnh xa thang máy.', lambda r: r[1] == 'twin' and r[3] == 'quiet'),
    ('family', 'Phòng gia đình cho bốn người.', lambda r: r[1] == 'family'),
    ('lift_double', 'Bà cụ đi lại chậm: giường đôi, gần thang máy.', lambda r: r[1] == 'double' and r[3] == 'lift'),
    ('garden_quiet', 'Phòng nhìn vườn, thật yên tĩnh để làm việc.', lambda r: r[2] == 'garden' and r[3] == 'quiet'),
    ('river_family', 'Phòng gia đình nhìn sông cho cả nhà ngắm pháo hoa.', lambda r: r[1] == 'family' and r[2] == 'river'),
    ('high_river', 'Tầng cao (tầng 3 hoặc 4), giường đôi, nhìn sông.', lambda r: r[0][0] in '34' and r[1] == 'double' and r[2] == 'river'),
]
# Look-alike guest names (same first letters, one mark apart) and booking codes (same digits, shuffled).
NAMES = [
    ('Nguyễn Thị Lan', 'Nguyễn Thị Lân', 'Nguyễn Thu Lan'),
    ('Trần Minh Quân', 'Trần Minh Quang', 'Trần Mạnh Quân'),
    ('Lê Hoàng Yến', 'Lê Hoàng Yên', 'Lê Hoài Yến'),
    ('Phạm Đức Anh', 'Phạm Đức Ánh', 'Phạm Đắc Anh'),
    ('Võ Thanh Hà', 'Võ Thanh Hải', 'Võ Thành Hà'),
    ('Đặng Bảo Ngọc', 'Đặng Bảo Ngân', 'Đặng Bá Ngọc'),
]
BOOKERS = ('Mai Văn Phúc', 'Hồ Thị Thu', 'Bùi Quốc Bình', 'Lý Minh Châu')
BREAKFAST = [
    ('wk', '6:30–9:30 · Nhà hàng tầng 1'),
    ('we', '6:30–10:00 · Nhà hàng tầng 1'),
    ('roof', '6:00–9:00 · Sân thượng'),
    ('none', 'Phòng không kèm bữa sáng: báo giá 12 xu/suất nếu khách muốn'),
]
WEEKDAYS = ('Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ nhật')

# Housekeeping (a checked-out room).
HK_ORDER = [('linen', 'Thay ga, áo gối'), ('bath', 'Vệ sinh phòng tắm'), ('amenity', 'Bổ sung tiện nghi'),
            ('minibar', 'Kiểm minibar, tính tiền dùng'), ('lost', 'Kiểm đồ khách để quên'), ('report', 'Báo lễ tân phòng sẵn sàng')]
LINEN = [('d', '1 ga giường đôi + 2 áo gối'), ('t', '2 ga giường đơn + 2 áo gối'),
         ('f', '1 ga đôi + 1 ga đơn + 3 áo gối'), ('dd', '2 ga giường đôi + 4 áo gối')]
LINEN_OF = dict(double='d', twin='t', family='f')
BATH = [('top', 'Lau từ cao xuống thấp, bồn cầu sau cùng, khăn màu riêng cho từng khu'),
        ('toilet', 'Cọ bồn cầu trước, dùng chung khăn lau cả bồn rửa mặt'),
        ('spray', 'Xịt thơm, lau qua gương cho nhanh')]
AMENITY = [('2', '2 bộ (khăn, bàn chải, dép, 2 chai nước)'), ('3', '3 bộ (khăn, bàn chải, dép, 3 chai nước)'),
           ('4', '4 bộ (khăn, bàn chải, dép, 4 chai nước)'), ('1', '1 bộ dùng chung cho cả phòng')]
# minibar item: label, price per unit in xu (water is free)
MINIBAR = [('water', 'Nước suối', 0), ('soda', 'Nước ngọt', 3), ('beer0', 'Bia không cồn', 4), ('snack', 'Snack khoai', 2), ('noodle', 'Mì ly', 3)]
LOST = [
    ('none', 'Không thấy gì', 'none'),
    ('charger', 'Một sợi sạc điện thoại cắm ở đầu giường', 'log'),
    ('book', 'Một cuốn sách kẹp vé tàu dưới gối', 'log'),
    ('shirt', 'Một chiếc áo khoác treo sau cửa phòng tắm', 'log'),
    ('passport', 'Một cuốn hộ chiếu trong ngăn kéo bàn', 'call'),
    ('medicine', 'Một hộp thuốc huyết áp còn nửa vỉ trên bồn rửa', 'call'),
]
LOST_OPTIONS = [('none', 'Không có đồ để quên'), ('log', 'Ghi sổ đồ thất lạc, niêm túi, gửi lễ tân giữ'),
                ('call', 'Báo lễ tân gọi khách ngay (giấy tờ, thuốc) rồi ghi sổ'), ('keep', 'Cất tạm vào tủ đồ của mình')]
ISSUES = [('', ''), ('', ''), ('drip', 'Vòi bồn rửa mặt nhỏ giọt dù đã vặn chặt.'), ('lamp', 'Đèn ngủ bên trái bật không sáng.')]
REPORT = [('ready', 'Báo phòng sạch, sẵn sàng đón khách'), ('maint', 'Báo phòng sạch nhưng chờ bảo trì, chưa bán'),
          ('later', 'Báo sẵn sàng, chuyện hỏng ghi chú sau')]

# Laundry (sheets and pillowcases, or towels and bath mats, from several rooms).
LOADS = {
    'linen': ('Mẻ ga gối', [('sheet', 'Ga giường'), ('case', 'Áo gối')], 'white60'),
    'towel': ('Mẻ khăn', [('towel', 'Khăn tắm'), ('mat', 'Thảm chân')], 'towel60'),
}
PROGRAMS = [('white60', 'Đồ trắng cotton · 60°C · vắt vừa'), ('towel60', 'Khăn bông · 60°C · sấy vừa'),
            ('quick30', 'Giặt nhanh · 30°C'), ('hot90', 'Giặt sôi · 90°C · vắt mạnh'), ('wool20', 'Len · 20°C, không vắt')]
STAINS = [('coffee', 'vết cà phê', True), ('lipstick', 'vết son môi', True), ('ink', 'vết mực bút bi', True),
          ('sauce', 'vết nước sốt', True), ('clean', 'sạch, chỉ nhàu', False), ('damp', 'hơi ẩm, không vết', False)]

# Breakfast. Dish id, label.
DISHES = [('pho', 'Phở bò'), ('chay', 'Bún chay'), ('banhmi', 'Bánh mì ốp la'), ('chao', 'Cháo gà suất nhỏ'),
          ('haisan', 'Bún hải sản'), ('xoi', 'Xôi đậu phộng')]
# note id, label, the dish that breaks it, the swap the hotel rule says
NOTES = {
    'peanut': ('Bé dị ứng đậu phộng', 'xoi', 'chao'),
    'peanut_adult': ('Dị ứng đậu phộng', 'xoi', 'banhmi'),
    'seafood': ('Dị ứng hải sản', 'haisan', 'pho'),
    'veg': ('Ăn chay', 'pho', 'chay'),
}
TOUR = 'Đi tour sớm 5:30, nhận hộp ăn sáng mang đi'

# Repair. Each fault: symptom, then variants (clues, safety, cause, fix, room status).
SAFETY = [('power', 'Ngắt aptomat / rút điện thiết bị trước'), ('water', 'Khóa van nước của phòng trước'),
          ('sign', 'Báo khách, đặt biển “Đang sửa chữa”, không cần ngắt gì'), ('none', 'Làm luôn cho nhanh, khỏi báo')]
STATUS_AFTER = [('ready', 'Báo lễ tân: phòng dùng lại bình thường'), ('ooo', 'Khóa phòng (OOO), báo lễ tân đổi phòng cho khách'),
                ('wait', 'Phòng dùng tạm được, báo lễ tân hẹn giờ thợ tới')]
FAULTS = {
    'ac': ('Điều hòa chảy nước', [
        ('Nước nhỏ giọt từ dàn lạnh; lưới lọc bám bụi dày; ống thoát nước ngoài ban công bị lá cây nhét kín.', 'power', 'clog', 'clean', 'ready'),
        ('Dàn lạnh đóng tuyết, gió ra không lạnh, có vệt dầu ở đầu ống đồng.', 'power', 'gas', 'contractor', 'ooo')],
        [('clog', 'Lưới lọc bẩn, ống thoát nghẹt'), ('gas', 'Rò gas lạnh'), ('remote', 'Remote hết pin')],
        [('clean', 'Vệ sinh lưới lọc, thông ống thoát nước'), ('gas', 'Tự nạp gas bằng bình mua ngoài'), ('contractor', 'Gọi thợ điện lạnh nhà thầu')]),
    'shower': ('Vòi sen yếu', [
        ('Chỉ vòi sen phòng này yếu, vòi bồn rửa vẫn mạnh; đầu sen đóng cặn trắng.', 'sign', 'scale', 'descale', 'ready'),
        ('Cả tầng 4 vòi nào cũng yếu; bơm tăng áp trên mái kêu lạch cạch.', 'sign', 'pump', 'contractor', 'wait')],
        [('scale', 'Đầu sen đóng cặn'), ('pump', 'Bơm tăng áp của tòa nhà hỏng'), ('heater', 'Bình nóng lạnh hết nóng')],
        [('descale', 'Tháo đầu sen, ngâm giấm, thông lỗ'), ('pump', 'Tự tháo bơm trên mái'), ('contractor', 'Gọi nhà thầu cấp nước')]),
    'lock': ('Khóa thẻ không nhận', [
        ('Quẹt thẻ thì đèn khóa nháy đỏ ba lần; các phòng khác mở bình thường; nhật ký khóa báo “pin yếu”.', 'sign', 'battery', 'battery', 'ready'),
        ('Thẻ của khách được mã hóa cho phòng 302 trong khi khách ở phòng 203.', 'sign', 'card', 'encode', 'ready'),
        ('Thẻ mới mã hóa vẫn không mở; ổ khóa có mùi khét, đèn tắt hẳn.', 'power', 'board', 'contractor', 'ooo')],
        [('battery', 'Pin khóa yếu'), ('card', 'Thẻ mã hóa nhầm phòng'), ('board', 'Bo mạch khóa cháy')],
        [('battery', 'Thay 4 pin AA đúng loại cho khóa'), ('encode', 'Mã hóa lại thẻ đúng phòng ở lễ tân'), ('contractor', 'Gọi nhà thầu khóa từ'),
         ('force', 'Cạy khóa cho khách vào')]),
    'tv': ('TV không lên', [
        ('Màn đen, đèn chờ không sáng; phích cắm tuột ra sau tủ.', 'sign', 'plug', 'replug', 'ready'),
        ('TV có tiếng nhưng màn hình đầy sọc ngang.', 'power', 'panel', 'contractor', 'wait')],
        [('plug', 'Phích cắm tuột'), ('panel', 'Hỏng tấm màn hình'), ('signal', 'Mất tín hiệu truyền hình')],
        [('replug', 'Cắm lại phích, thử remote'), ('open', 'Tự mở vỏ TV ra xem'), ('contractor', 'Gọi trung tâm bảo hành')]),
    'toilet': ('Bồn cầu rò nước', [
        ('Két nước chảy rỉ rả liên tục; mở nắp két thấy phao bị kẹt.', 'water', 'float', 'float', 'ready'),
        ('Nước rỉ ra sàn từ chân bồn cầu; gạch quanh chân ố vàng, có mùi.', 'water', 'seal', 'contractor', 'ooo')],
        [('float', 'Phao két nước kẹt'), ('seal', 'Gioăng chân bồn hỏng, phải tháo bồn'), ('crack', 'Nứt két nước')],
        [('float', 'Chỉnh và thay phao, gioăng xả'), ('silicone', 'Bơm keo quanh chân bồn cho kín'), ('contractor', 'Gọi thợ nước nhà thầu')]),
    'bulb': ('Bóng đèn cháy', [
        ('Đèn đầu giường không sáng; bóng đen đầu; công tắc vẫn kêu tách bình thường.', 'power', 'bulb', 'led', 'ready'),
        ('Đèn cả dãy chập chờn; ổ cắm cạnh bàn ấm nóng, có mùi khét.', 'power', 'wiring', 'contractor', 'ooo')],
        [('bulb', 'Bóng đèn cháy'), ('wiring', 'Dây điện quá tải, chập'), ('switch', 'Công tắc hỏng')],
        [('led', 'Thay bóng LED cùng đuôi, cùng công suất'), ('big', 'Thay bóng 100 W cho sáng hơn'), ('contractor', 'Gọi thợ điện nhà thầu')]),
}

# Decor: item id, label, price (xu), themes it fits, what it is (flower / food / balloon / other).
ITEMS = [
    ('rose', 'Bó hồng đỏ', 12, ('valentine', 'honeymoon', 'anniversary'), 'flower'),
    ('petal', 'Cánh hồng rải giường', 8, ('valentine', 'honeymoon'), 'flower'),
    ('swan', 'Thiên nga gấp khăn', 4, ('honeymoon', 'anniversary'), 'other'),
    ('candle', 'Nến LED', 6, ('valentine', 'honeymoon', 'anniversary', 'noel'), 'other'),
    ('heart', 'Bóng bay trái tim', 5, ('valentine',), 'balloon'),
    ('age', 'Bóng bay số tuổi', 6, ('birthday',), 'balloon'),
    ('cake', 'Bánh kem nhỏ', 15, ('birthday', 'anniversary'), 'food'),
    ('banner', 'Băng chữ “Chúc mừng sinh nhật”', 4, ('birthday',), 'other'),
    ('peach', 'Cành đào', 20, ('tet',), 'flower'),
    ('couplet', 'Câu đối đỏ', 6, ('tet',), 'other'),
    ('lixi', 'Bao lì xì để bàn', 3, ('tet',), 'other'),
    ('mut', 'Khay mứt Tết', 10, ('tet',), 'food'),
    ('tree', 'Cây thông nhỏ', 18, ('noel',), 'other'),
    ('wreath', 'Vòng nguyệt quế treo cửa', 9, ('noel',), 'other'),
    ('cookie', 'Hộp bánh quy gừng', 7, ('noel',), 'food'),
    ('stars', 'Dây đèn ngôi sao', 7, ('noel', 'birthday'), 'other'),
    ('frame', 'Khung ảnh cưới in sẵn', 7, ('anniversary',), 'other'),
    ('card', 'Thiệp chúc viết tay', 2, ('valentine', 'honeymoon', 'anniversary', 'birthday', 'tet', 'noel'), 'other'),
]
THEMES = {
    'honeymoon': ('Phòng trăng mật', '💞', 'room'), 'birthday': ('Sinh nhật bất ngờ', '🎂', 'room'),
    'anniversary': ('Kỷ niệm ngày cưới', '💍', 'room'),
    'valentine': ('Sảnh Valentine', '💘', 'lobby'), 'tet': ('Sảnh đón Tết', '🧧', 'lobby'), 'noel': ('Sảnh Giáng sinh', '🎄', 'lobby'),
}
YEAR_ROUND = ('honeymoon', 'birthday', 'anniversary')
LIMITS = {
    'pollen': ('Khách dị ứng phấn hoa: không dùng hoa tươi.', 'flower'),
    'sugar': ('Khách đang ăn kiêng đường: không đặt đồ ăn ngọt.', 'food'),
    'balloon': ('Có bé sợ tiếng bóng nổ: không bóng bay.', 'balloon'),
    'none': ('Không có lưu ý riêng.', ''),
}
PLACES = [('room', 'Trên giường và bàn trà trong phòng khách đặt'), ('lobby', 'Góc sảnh, chừa lối đi và lối thoát hiểm'),
          ('exit', 'Chắn trước cửa thoát hiểm cho nổi bật'), ('corridor', 'Dọc hành lang, che tạm bình chữa cháy')]

# 🗓️ Seasons by the real Vietnam date (UTC+7). Tết Nguyên Đán (mùng 1) by solar date; the window opens three weeks
# before and closes a week after. Valentine 1–14/2 (on an overlap Tết wins, except 14/2 itself); Noel 1–25/12.
TET = {2026: date(2026, 2, 17), 2027: date(2027, 2, 6), 2028: date(2028, 1, 26), 2029: date(2029, 2, 13), 2030: date(2030, 2, 3)}
TET_BEFORE, TET_AFTER = timedelta(days=21), timedelta(days=7)
SEASONS = {
    'valentine': ('Mùa Valentine', '💘', 'Sảnh trang trí Valentine; cặp đôi đặt phòng nhiều hơn.'),
    'tet': ('Mùa Tết', '🧧', 'Sảnh đón Tết; khách về quê và khách du xuân đông hơn.'),
    'noel': ('Mùa Giáng sinh', '🎄', 'Sảnh Giáng sinh; khách đi chơi lễ cuối năm đông hơn.'),
}
SEASON_BONUS = 1.5   # quality bonus x1.5 on tasks taken in season (tips from holiday guests)

DESK = [
    dict(id='duck', title='Khách mang theo con vịt', emoji='🦆', npc=4, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Một vị khách ôm con vịt đeo nơ tới quầy: “Bé Vàng có hai chục nghìn người theo dõi đó, cho bé ngủ cùng một đêm thôi.” Nội quy khách sạn không nhận vật nuôi.',
         options=[dict(id='policy', label='Giải thích nhẹ nhàng nội quy, gợi ý chỗ gửi thú cưng gần đó, giữ phòng cho khách', hint='',
                       effects=dict(xp=5, review=[5, 'Nhân viên từ chối mà dễ thương ghê, còn chỉ chỗ gửi bé Vàng.']), good=True,
                       outcome='Khách gửi bé Vàng ở tiệm thú cưng cuối phố, tối quay về nhận phòng, còn quay clip khen quầy lễ tân.'),
                  dict(id='sneak', label='Cho vịt lên phòng, dặn đừng để kêu', hint='',
                       effects=dict(review=[2, 'Đêm qua phòng bên có tiếng vịt kêu tới sáng.', 3]), good=False,
                       outcome='Nửa đêm bé Vàng kêu cạp cạp, phòng bên gọi xuống quầy ba lần.'),
                  dict(id='photo', label='Xin chụp chung với bé Vàng rồi mới giải thích', hint='', effects=dict(patience=-3), good=None,
                       outcome='Ảnh đẹp, nhưng khách phía sau chờ hơi lâu.')],
         default='photo'),
    dict(id='room8', title='Đòi phòng số 8 cho hợp phong thủy', emoji='🔢', npc=5, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Khách nhất quyết muốn “phòng số 8”. Khách sạn chỉ có phòng 101 tới 404.',
         options=[dict(id='sum', label='Gợi ý phòng 404 còn trống: 4 + 0 + 4 = 8, lại nhìn vườn yên tĩnh', hint='',
                       effects=dict(xp=5, review=[5, 'Lễ tân nhanh trí, phòng 404 cộng lại đúng số 8!']), good=True,
                       outcome='Khách bật cười, chụp tấm thẻ phòng gửi cả nhóm: “Số 8 xịn.”'),
                  dict(id='sticker', label='Dán tạm số 8 lên cửa phòng 203', hint='',
                       effects=dict(review=[2, 'Số phòng dán tạm, đi tìm mãi không ra.']), good=False,
                       outcome='Ca đêm giao nhầm đồ ăn cho “phòng 8”, mất nửa tiếng mới gỡ rối.'),
                  dict(id='no', label='Nói thẳng là không có phòng số 8', hint='', effects=dict(patience=-2), good=None,
                       outcome='Khách nhận phòng nhưng mặt hơi buồn.')],
         default='no'),
    dict(id='wrong_hotel', title='Đặt nhầm khách sạn bên kia sông', emoji='🌉', npc=4, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Khách đưa điện thoại có xác nhận đặt phòng, nhưng là của “Khách sạn Sóng Mây” ở bờ bên kia sông. Trời sắp mưa.',
         options=[dict(id='help', label='Gọi bên kia giữ phòng giúp, chỉ bến đò và mời ngồi chờ hết mưa', hint='',
                       effects=dict(xp=6, review=[5, 'Mình đặt nhầm mà lễ tân vẫn gọi giúp, cho ngồi chờ mưa. Lần sau mình đặt bên này.']), good=True,
                       outcome='Khách qua sông kịp giờ nhận phòng, còn lưu số khách sạn cho chuyến sau.'),
                  dict(id='sell', label='Mời ở luôn bên mình với giá cao hơn', hint='', effects=dict(patience=-2), good=None,
                       outcome='Khách lưỡng lự rồi đi, vẫn phải tự gọi bên kia.'),
                  dict(id='shrug', label='Bảo khách tự tìm đường', hint='',
                       effects=dict(review=[2, 'Hỏi đường mà nhân viên chỉ lắc đầu.']), good=False,
                       outcome='Khách đội mưa đi, vừa đi vừa quay clip than.')],
         default='sell'),
    dict(id='couple', title='Cặp đôi cãi nhau đòi đổi phòng giữa đêm', emoji='🌙', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='23 giờ 40, một vị khách xuống quầy, mắt đỏ hoe: “Cho tôi một phòng khác, tôi không ở chung với người đó nữa.” Người kia gọi xuống đòi “đừng đưa”.',
         options=[dict(id='calm', label='Mời ngồi sảnh uống trà gừng; còn phòng trống thì xếp riêng, ghi chú, không phán xét', hint='',
                       effects=dict(xp=6), good=True,
                       outcome='Sáng hôm sau hai người xuống ăn sáng chung, gửi lời cảm ơn ca đêm.'),
                  dict(id='side', label='Khuyên giải, đứng về một bên cho nhanh', hint='',
                       effects=dict(review=[2, 'Nhân viên xen vào chuyện riêng của khách.']), good=False,
                       outcome='Người còn lại xuống quầy cự nự, sảnh ồn tới gần sáng.'),
                  dict(id='later', label='Hết giờ rồi, sáng mai tính', hint='', effects=dict(patience=-3), good=None,
                       outcome='Khách ngủ gà gật trên sofa sảnh tới sáng.')],
         default='later'),
    dict(id='live', title='Khách livestream ngay giữa sảnh', emoji='📱', npc=4, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Một khách bật loa livestream “đập hộp” ngay giữa sảnh, khung hình có cả khách khác đang làm thủ tục.',
         options=[dict(id='corner', label='Mời sang góc cửa sổ sáng đẹp, nhờ không quay khách khác', hint='',
                       effects=dict(xp=5, review=[4, 'Góc sảnh khách sạn lên hình đẹp, nhân viên chỉ chỗ tận tình.']), good=True,
                       outcome='Buổi live đẹp hơn hẳn, khách khác làm thủ tục yên ổn.'),
                  dict(id='join', label='Nhảy vào chào hàng cho khách sạn', hint='', effects={},
                       luck=dict(p=0.4, win=dict(effects=dict(xp=3), outcome='Người xem khen nhân viên duyên, vài người hỏi giá phòng.', good=None),
                                 lose=dict(effects=dict(patience=-3), outcome='Hàng chờ ở quầy dài ra, có người phàn nàn.', good=False))),
                  dict(id='stop', label='Đòi tắt ngay trước mặt mọi người', hint='',
                       effects=dict(review=[2, 'Bị nhắc to giữa sảnh, ngại muốn độn thổ.']), good=False,
                       outcome='Khách tắt live nhưng giận, lên phòng đóng cửa cái rầm.')],
         default='corner'),
    dict(id='remote', title='Khách tìm remote mất', emoji='📺', npc=3, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Phòng 303 gọi: “Cái remote biến đâu mất rồi, sắp tới giờ thời sự.”',
         options=[dict(id='spare', label='Mang remote dự phòng lên, nhờ khách xem thử khe sofa và ngăn kéo', hint='',
                       effects=dict(xp=4, review=[5, 'Gọi cái là có remote mới lên tận phòng, kịp thời sự.']), good=True,
                       outcome='Remote cũ nằm trong túi áo khoác của chính khách. Cả hai cùng cười.'),
                  dict(id='fine', label='Báo sẽ tính phí làm mất remote', hint='',
                       effects=dict(review=[2, 'Chưa tìm đã đòi phạt.']), good=False,
                       outcome='Khách bực, lục tung phòng mới thấy remote trong túi áo.'),
                  dict(id='later', label='Hẹn hết ca sẽ lên xem', hint='', effects=dict(patience=-2), good=None,
                       outcome='Khách lỡ bản tin, xem tạm trên điện thoại.')],
         default='later'),
    dict(id='durian', title='Khách mang sầu riêng lên phòng', emoji='🍈', npc=5, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Hành lang tầng 2 thơm nức mùi sầu riêng. Khách vừa mua cả trái lên phòng, phòng bên gọi xuống hỏi “có gì cháy không”.',
         options=[dict(id='garden', label='Mời khách mang ra bàn ngoài vườn, mượn dao và đĩa của bếp', hint='',
                       effects=dict(xp=5), good=True,
                       outcome='Khách ăn ngoài vườn, còn mời luôn bác bảo vệ một múi.'),
                  dict(id='ignore', label='Kệ, mùi rồi sẽ bay', hint='', effects=dict(patience=-3), good=None,
                       outcome='Tới tối hành lang vẫn còn mùi, ca buồng phòng phải khử mùi cả tầng.'),
                  dict(id='take', label='Thu giữ trái sầu riêng tới khi khách trả phòng', hint='',
                       effects=dict(review=[2, 'Đồ mình mua mà bị giữ như hàng cấm.']), good=False,
                       outcome='Khách giận, đòi gặp quản lý.')],
         default='ignore'),
    dict(id='stairs', title='Cầu thang thành điểm check-in', emoji='📸', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một nhóm bạn trẻ tạo dáng kín cầu thang xoắn ở sảnh, khách kéo vali không qua được.',
         options=[dict(id='spot', label='Chỉ sang góc tường hoa đẹp hơn, chừa lối cầu thang', hint='',
                       effects=dict(xp=4, review=[5, 'Được chỉ góc chụp xịn hơn, mà không ai bị chắn đường.']), good=True,
                       outcome='Nhóm bạn chụp ở tường hoa, còn gắn thẻ khách sạn.'),
                  dict(id='shoo', label='Đuổi cả nhóm ra ngoài', hint='', effects=dict(review=[2, 'Bị đuổi như đuổi gà.']), good=False,
                       outcome='Nhóm bạn đi, buông một câu chê trên mạng.'),
                  dict(id='wait', label='Đứng chờ cả nhóm chụp xong', hint='', effects=dict(patience=-2), good=None,
                       outcome='Mười lăm phút sau cầu thang mới thông.')],
         default='wait'),
    dict(id='cake', title='Nhờ giấu bánh sinh nhật', emoji='🎂', npc=6, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Một vị khách thì thầm: “Gửi chiếc bánh vào tủ lạnh bếp, 22 giờ mang lên phòng 204 giúp, đừng để vợ biết nha.”',
         options=[dict(id='slip', label='Dán phiếu tên, số phòng, giờ mang lên; dặn lại ca đêm', hint='',
                       effects=dict(xp=5, review=[5, 'Bánh lên đúng 22 giờ, vợ mình bất ngờ khóc luôn.', 6]), good=True,
                       outcome='Đúng 22 giờ, bánh lên phòng, cả hành lang nghe tiếng hát chúc mừng.'),
                  dict(id='word', label='Nhận lời miệng, nhớ là được', hint='', effects={},
                       luck=dict(p=0.5, win=dict(effects=dict(xp=2), outcome='May mà vẫn nhớ, bánh lên kịp giờ.', good=None),
                                 lose=dict(effects=dict(review=[2, 'Bánh sinh nhật nằm quên trong tủ tới sáng.', 6]), outcome='Đổi ca, không ai nhớ chiếc bánh.', good=False))),
                  dict(id='no', label='Từ chối vì tủ lạnh bếp không nhận đồ ngoài', hint='', effects=dict(patience=-2), good=None,
                       outcome='Khách phải giấu bánh trong xe.')],
         default='no'),
    dict(id='karaoke', title='Phòng bên hát karaoke lúc 23 giờ', emoji='🎤', npc=3, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Bác Khải ở 302 gọi xuống: phòng 303 mở loa hát karaoke, đã quá giờ yên tĩnh 22:00.',
         options=[dict(id='knock', label='Lên gõ cửa nhắc nhẹ giờ yên tĩnh, gợi ý phòng hát gần đó', hint='',
                       effects=dict(xp=5, review=[5, 'Gọi một cái là yên, nhân viên nói chuyện khéo.']), good=True,
                       outcome='Nhóm 303 xin lỗi, tắt loa, hẹn mai đi hát ở quán.'),
                  dict(id='police', label='Gọi công an phường ngay', hint='', effects=dict(review=[3, 'Chuyện nhỏ mà ầm ĩ quá.', 4]), good=False,
                       outcome='Chuyện nhỏ thành to, cả tầng mở cửa ra xem.'),
                  dict(id='ignore', label='Mặc kệ, khuya rồi', hint='', effects=dict(review=[2, 'Gọi xuống quầy mà chẳng ai lên.']), good=False,
                       outcome='Bác Khải thức tới một giờ sáng.')],
         default='ignore'),
    dict(id='swan', title='Khách xin quay clip gấp thiên nga khăn', emoji='🦢', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Khách thấy thiên nga khăn trên giường, xin quay clip bạn gấp lại từ đầu “để dạy người xem”.',
         options=[dict(id='teach', label='Gấp chậm hai phút cho khách quay tay, không quay mặt đồng nghiệp', hint='',
                       effects=dict(xp=4, review=[5, 'Học được gấp thiên nga, clip lên xu hướng luôn.']), good=True,
                       outcome='Clip “thiên nga khăn” của khách được chia sẻ khắp nơi.'),
                  dict(id='busy', label='Đang bận, hẹn dịp khác', hint='', effects=dict(patience=-1), good=None,
                       outcome='Khách tự xem mạng gấp, ra con vịt hơi méo.'),
                  dict(id='fee', label='Đòi tiền “học phí”', hint='', effects=dict(review=[2, 'Hỏi gấp khăn mà bị đòi tiền.']), good=False,
                       outcome='Khách bỏ qua, chê keo kiệt.')],
         default='busy'),
    dict(id='ghost', title='Khách báo phòng có tiếng gõ cửa sổ lúc 2 giờ sáng', emoji='👻', npc=6, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='2 giờ sáng, phòng 104 gọi run run: “Có ai gõ cửa sổ… mà đây là tầng 1, ngoài kia là vườn.”',
         options=[dict(id='check', label='Lên cùng bảo vệ, soi đèn ra vườn và kiểm cửa sổ', hint='',
                       effects=dict(xp=5, review=[5, 'Hóa ra cành cây gõ cửa, nhân viên lên ngay lúc nửa đêm.']), good=True,
                       outcome='Thủ phạm là cành mít gõ vào kính. Sáng ra anh Bảo cắt tỉa ngay.'),
                  dict(id='joke', label='Đùa: “Chắc ma khách sạn chào đó”', hint='', effects=dict(review=[1, 'Sợ muốn xỉu mà còn bị đùa.']), good=False,
                       outcome='Cả nhà thức trắng tới sáng.'),
                  dict(id='swap', label='Đổi ngay sang phòng khác, không kiểm', hint='', effects=dict(patience=-2), good=None,
                       outcome='Khách dọn đồ giữa đêm, tiếng gõ vẫn còn đó cho khách sau.')],
         default='swap'),
]

MILESTONES = [
    dict(id='desk', label='Đứng vững một quầy', jobs=15, days=5, posts=3),
    dict(id='rota', label='Thạo cả năm vị trí', jobs=60, days=20, posts=6),
    dict(id='host', label='Người giữ lửa Sông Mây', jobs=160, days=40, posts=6),
]
NOTEBOOK = [
    'Mọi nội quy, giá và phòng ở đây là quy tắc hư cấu chỉ dùng trong trò chơi.',
    'Lễ tân: tìm đặt phòng theo đủ họ tên và mã đặt (tên gần giống, mã đảo số là chuyện thường).',
    'Đối chiếu giấy tờ: khớp tên và số khách thì nhận; thêm khách thì cập nhật phiếu, báo phụ thu giường phụ; giấy tờ khác tên người đặt thì gọi người đặt xác nhận.',
    'Chọn phòng: chỉ phòng “Sạch, sẵn sàng” và đáp ứng đủ yêu cầu (giường, hướng nhìn, tầng, yên tĩnh/gần thang, tiếp cận).',
    'Thẻ phòng: 1 khách 1 thẻ, từ 2 khách giao 2 thẻ. Bữa sáng: ngày thường 6:30–9:30, sáng Thứ Bảy và Chủ nhật tới 10:00, đều ở nhà hàng tầng 1.',
    'Buồng phòng: ga gối → phòng tắm (cao xuống thấp, bồn cầu sau cùng) → tiện nghi theo sức chứa → minibar → đồ để quên → báo lễ tân.',
    'Minibar: nước suối miễn phí; nước ngọt 3 xu, bia không cồn 4 xu, snack 2 xu, mì ly 3 xu. Tiền dùng = số đã dùng × giá.',
    'Đồ để quên: ghi sổ, niêm túi, gửi lễ tân; giấy tờ tùy thân và thuốc thì báo lễ tân gọi khách ngay. Phòng có đồ hỏng thì báo chờ bảo trì, chưa bán.',
    'Giặt là: đếm thực tế, không chép phiếu; lệch phiếu thì ghi chênh lệch. Đồ có vết bẩn tách ra xử lý trước. Ga gối: đồ trắng 60°C; khăn và thảm: khăn bông 60°C.',
    'Bữa sáng: dị ứng đậu phộng đổi xôi sang cháo gà (trẻ em) hoặc bánh mì ốp la (người lớn); dị ứng hải sản đổi bún hải sản sang phở bò; ăn chay đổi phở bò sang bún chay. Phòng đi tour sớm nhận hộp mang đi, không nấu tại bàn. Bàn có người dị ứng đặt thẻ dị ứng.',
    'Bảo trì: đồ điện ngắt aptomat trước, đường nước khóa van trước; việc của tòa nhà, gas lạnh, bo mạch, tháo bồn, dây điện thì gọi nhà thầu và báo lễ tân tình trạng phòng.',
    'Trang trí: chọn mọi món hợp dịp, bỏ món trái lưu ý của khách; tổng tiền vượt ngân sách thì bỏ món đắt nhất trong số đó. Đồ trang trí không bao giờ chắn lối thoát hiểm hay bình chữa cháy.',
    'Mùa lễ (giờ Việt Nam): Valentine 1–14/2, Tết từ ba tuần trước tới một tuần sau mùng 1, Giáng sinh 1–25/12. Mùa lễ đông khách hơn, thưởng ×1.5.',
    'Lương ca trả theo hợp đồng khi khép ca; thưởng chất lượng nhỏ theo từng việc, sai bước thì sửa tại chỗ và thưởng giảm.',
]
