"""Nhà hàng tiệc Hồng Mây: a fictional banquet restaurant (kitchen + event hall). Rules, prices and guests are game content only."""
from datetime import timedelta

from .hotel_content import TET   # Tết Nguyên Đán (mùng 1) by solar date, shared with Khách sạn Sông Mây

PEOPLE = [
    ('Chú Tâm', 'Bếp trưởng', 'Ba mươi năm đứng bếp tiệc, dạy phụ bếp từ cách cầm dao.', 'picky'),
    ('Chị Loan', 'Quản lý nhà hàng', 'Nhớ sơ đồ bàn của cả trăm đám cưới, phát phiếu việc mỗi ca.', 'warm'),
    ('Anh Khoa', 'Kỹ thuật âm thanh ánh sáng', 'Cuộn băng keo điện lúc nào cũng đeo bên hông.', 'quiet'),
    ('Cô Hạnh', 'Đoàn kiểm tra vệ sinh an toàn thực phẩm phường', 'Mang theo nhiệt kế đầu dò và sổ biên bản.', 'picky'),
    ('Duy và Thảo', 'Cặp đôi sắp cưới', 'Cãi nhau vui vẻ về màu khăn trải bàn.', 'genz'),
    ('Bà Sáu', 'Khách quen đặt tiệc', 'Năm nào cũng đặt tiệc mừng thọ cho ông nhà.', 'warm'),
    ('Chị Vân', 'Thư ký công ty đặt tiệc', 'Có bảng tính cho mọi thứ, kể cả số ghế em bé.', 'quiet'),
]
MANAGER = 1        # Chị Loan hands out every job slip
INSPECTOR = 3      # Cô Hạnh, the ward food-safety inspection

# 🍳 two tracks, three roles. 'prep' (Phụ bếp) is the probation; 'chef' (Đầu bếp) opens after it; 'hall' any time.
ROLES = {
    'prep': ('Phụ bếp', '🥕', 'Sơ chế, món đơn giản, chuẩn bị dụng cụ'),
    'chef': ('Đầu bếp', '👨‍🍳', 'Kiểm nguyên liệu, chế biến, trang trí món'),
    'hall': ('Sảnh sự kiện', '🎀', 'Tư vấn tiệc, bày trí sảnh, chạy sự kiện'),
}
KITCHEN = ('prep', 'chef')
TRACKS = {'kitchen': ('Bếp', '🍳'), 'hall': ('Sảnh sự kiện', '🎀')}
JOBS = {
    'prep': ('Sơ chế nguyên liệu', '🔪', 'prep'),
    'salad': ('Làm món salad', '🥗', 'prep'),
    'tools': ('Chuẩn bị dụng cụ', '🥣', 'prep'),
    'check': ('Kiểm tra nguyên liệu', '📋', 'chef'),
    'cook': ('Chế biến món', '🍲', 'chef'),
    'plate': ('Trang trí và hoàn thiện món', '🍽️', 'chef'),
    'event': ('Tổ chức sự kiện ở sảnh', '🎀', 'hall'),
}
ROLE_JOBS = {'prep': ('prep', 'salad', 'tools'), 'chef': ('check', 'cook', 'plate'), 'hall': ('event',)}
BONUS = dict(prep=5, salad=5, tools=5, check=7, cook=7, plate=7, event=11)
PROBATION = 3      # good kitchen shifts as Phụ bếp (hygiene + a good job + closing) before Đầu bếp
WRONG_COST, RUSH_WRONG_COST = 6, 9     # quality lost per redone step; a rush day leaves less room for slips (17/10: was 12, 18)
QUALITY_FLOOR = 60                     # (17/10: was 40)
OLD_WRONG_COST, OLD_RUSH_WRONG_COST, OLD_FLOOR = 12, 18, 40   # a task slipped before 17/10 keeps its quality

# 🔥 Leaving the kitchen without the closing check: some nights a forgotten appliance starts a small fire.
FIRE_CHANCE = 0.15  # only when the closing check was skipped after kitchen work (17/10: was 0.4, owner "dễ chơi hơn")
FIRE_PCT = 8       # the compensation: 8% of the day's contract salary…
FIRE_MIN, FIRE_CAP = 2, 6   # …at least 2 and at most 6 xu, and never more than the wallet holds
INSPECT_CHANCE = 0.3        # a ward food-safety inspection visits on about one kitchen day in three (from day 2)

# ---------------------------------------------------------------- shift checklists (kitchen)
OPEN_STEPS = [('wash', 'Rửa tay bằng xà phòng đủ 20 giây'), ('sanitize', 'Xịt cồn sát khuẩn tay'),
              ('cap', 'Đội mũ trùm tóc, mặc tạp dề sạch'), ('gloves', 'Đeo bao tay dùng một lần'),
              ('stove', 'Kiểm bếp gas, máy hút mùi, nhiệt độ tủ mát')]
CLOSE_ORDER = [('trash', 'Gom rác, buộc túi đem ra điểm tập kết'), ('dishes', 'Rửa, sát khuẩn dụng cụ và úp ráo'),
               ('wipe', 'Lau mặt bếp, bàn sơ chế từ trên xuống'), ('floor', 'Lau sàn bếp, kê biển sàn ướt')]
# Appliances at closing: id, label, state words, must be switched off tonight?
APPLIANCES = [
    ('gas', 'Bếp gas số 2', ('lửa nhỏ vẫn còn xanh', True), ('đã khóa van', False)),
    ('hood', 'Máy hút mùi', ('đang chạy', True), ('đã tắt', False)),
    ('rice', 'Nồi cơm điện lớn', ('đèn hâm còn sáng', True), ('đã rút phích', False)),
    ('oven', 'Lò nướng', ('quạt lò còn quay, 180°C', True), ('đã tắt, nguội', False)),
    ('kettle', 'Ấm đun siêu tốc', ('còn cắm điện', True), ('đã rút phích', False)),
    ('fryer', 'Bếp chiên nhúng', ('dầu còn 160°C, công tắc bật', True), ('đã tắt, dầu nguội', False)),
    ('fridge', 'Tủ mát', ('đang chạy 3°C', False), ('đang chạy 4°C', False)),
    ('freezer', 'Tủ đông', ('đang chạy −18°C', False), ('đang chạy −20°C', False)),
]

# ---------------------------------------------------------------- Phụ bếp: sơ chế
BOARDS = [('green', 'Thớt xanh lá · rau củ quả'), ('red', 'Thớt đỏ · thịt sống'),
          ('blue', 'Thớt xanh dương · hải sản sống'), ('yellow', 'Thớt vàng · đồ đã nấu chín')]
BOARD_OF = dict(veg='green', meat='red', sea='blue')
# id, label, group, grams per portion, the dish it goes into
INGREDIENTS = [
    ('xalach', 'Xà lách và rau thơm', 'veg', 40, 'gỏi cuốn'),
    ('cachua', 'Cà chua và dưa leo', 'veg', 60, 'đĩa rau ăn kèm'),
    ('carot', 'Cà rốt và củ cải', 'veg', 50, 'đồ chua'),
    ('ga', 'Đùi gà', 'meat', 150, 'gà chiên nước mắm'),
    ('suon', 'Sườn heo', 'meat', 120, 'sườn ram'),
    ('bo', 'Thăn bò', 'meat', 100, 'bò lúc lắc'),
    ('tom', 'Tôm sú', 'sea', 80, 'gỏi cuốn tôm thịt'),
    ('ca', 'Phi lê cá lóc', 'sea', 120, 'canh chua cá'),
    ('muc', 'Mực ống', 'sea', 90, 'mực xào thơm'),
]
CLEAN = [('soak', 'Nhặt bỏ phần dập úa, ngâm nước muối loãng 5 phút, xả lại ba lần nước sạch'),
         ('thaw', 'Rã đông trong ngăn mát từ hôm trước, đặt khay hứng nước bên dưới'),
         ('trim', 'Lọc gân, mỡ thừa trên thớt riêng; không rửa chung bồn với rau'),
         ('ice', 'Giữ trên đá, sơ chế nhanh ở bồn riêng của hải sản'),
         ('hot', 'Ngâm nước nóng cho mau rã đông, mau sạch')]
STORE = [('top', 'Hộp có nắp, dán nhãn tên và giờ sơ chế, ngăn trên tủ mát'),
         ('bottom', 'Khay kín, dán nhãn tên và giờ sơ chế, ngăn dưới cùng tủ mát'),
         ('room', 'Để ngoài bàn sơ chế cho tiện lấy'),
         ('mix', 'Chung khay với đồ đã nấu chín cho gọn')]

# ---------------------------------------------------------------- Phụ bếp: salad
TOPPINGS = dict(xalach='Xà lách', cachua='Cà chua bi', dualeo='Dưa leo', hanhtay='Hành tây', trung='Trứng luộc',
                cangu='Cá ngừ', bapcai='Bắp cải bào', carot='Cà rốt bào', rauram='Rau răm', ga='Gà xé',
                dauphong='Đậu phộng rang', ngosen='Ngó sen', tom='Tôm luộc', thit='Thịt ba chỉ luộc',
                raumam='Rau mầm', phomai='Phô mai viên', tao='Táo', xoai='Xoài', nho='Nho', dua='Dưa lưới')
SAUCES = [('mayo', 'Sốt mayonnaise'), ('nuocmam', 'Nước mắm chua ngọt'), ('yogurt', 'Sữa chua'),
          ('giam', 'Sốt dầu giấm'), ('mehat', 'Sốt mè rang')]
# id, name, toppings, sauce, grams per plate
SALADS = [
    ('tuna', 'Salad cá ngừ', ('xalach', 'cachua', 'dualeo', 'hanhtay', 'trung', 'cangu'), 'mayo', 150),
    ('chicken', 'Gỏi gà bắp cải', ('bapcai', 'carot', 'hanhtay', 'rauram', 'ga', 'dauphong'), 'nuocmam', 180),
    ('lotus', 'Gỏi ngó sen tôm thịt', ('ngosen', 'carot', 'tom', 'thit', 'rauram', 'dauphong'), 'nuocmam', 160),
    ('sprout', 'Salad rau mầm trứng', ('raumam', 'xalach', 'cachua', 'trung', 'phomai'), 'mehat', 120),
    ('fruit', 'Salad trái cây', ('tao', 'xoai', 'nho', 'dua'), 'yogurt', 140),
]
# note id, the guest's words, toppings it removes (one must be in the recipe for the note to apply)
SALAD_NOTES = [
    ('onion', 'Khách dặn không hành tây.', ('hanhtay',)),
    ('peanut', 'Bàn có khách dị ứng đậu phộng.', ('dauphong',)),
    ('egg', 'Khách không ăn trứng.', ('trung',)),
    ('seafood', 'Khách dị ứng hải sản: không tôm, không cá.', ('tom', 'cangu')),
    ('cheese', 'Khách không dùng được sữa: không phô mai.', ('phomai',)),
]
SALAD_STEPS = [('pick', 'Nhặt bỏ lá dập úa'), ('soak', 'Ngâm nước muối loãng 5 phút'), ('rinse', 'Xả lại ba lần nước sạch'),
               ('spin', 'Quay ráo rau'), ('cut', 'Cắt, xé vừa ăn rồi mới trộn')]

# ---------------------------------------------------------------- Phụ bếp: dụng cụ
TOOLS = dict(dao_thai='Dao thái', dao_chat='Dao chặt xương', thot_xanh='Thớt xanh lá', thot_do='Thớt đỏ',
             thot_xd='Thớt xanh dương', noi_lon='Nồi lớn', chao='Chảo gang', ray='Rây lọc', vot='Vợt vớt',
             kep='Kẹp gắp', bat_tron='Bát trộn inox', khuon='Khuôn bánh flan', may_danh='Máy đánh trứng',
             xung='Xửng hấp', tho_ga='Thố đựng nước dùng')
# dish id, name, tools, the vessel it is served in, its unit
STATION = [
    ('canhchua', 'Canh chua cá', ('thot_xd', 'dao_thai', 'noi_lon', 'vot'), 'tô', 'tô'),
    ('suonram', 'Sườn ram', ('dao_chat', 'thot_do', 'chao', 'kep'), 'đĩa', 'đĩa'),
    ('goicuon', 'Gỏi cuốn tôm thịt', ('dao_thai', 'thot_xanh', 'thot_xd', 'noi_lon'), 'đĩa', 'đĩa'),
    ('comchien', 'Cơm chiên dương châu', ('chao', 'dao_thai', 'thot_xanh', 'bat_tron'), 'đĩa', 'đĩa'),
    ('cahap', 'Cá hấp xì dầu', ('xung', 'dao_thai', 'thot_xd'), 'đĩa', 'đĩa'),
    ('flan', 'Bánh flan', ('khuon', 'may_danh', 'ray', 'xung'), 'chén', 'chén'),
    ('lau', 'Lẩu nấm', ('noi_lon', 'tho_ga', 'dao_thai', 'thot_xanh'), 'nồi lẩu', 'nồi'),
]
KNIVES = [('chip', 'Dao thái số 2 bị mẻ một vết nhỏ ở lưỡi.', 'swap'),
          ('dull', 'Dao cắt cà chua bị dập, lưỡi trượt trên vỏ.', 'hone'),
          ('loose', 'Cán dao chặt lỏng, cầm lên lắc lư.', 'swap'),
          ('ok', 'Dao sạch, sắc, cán chắc tay.', 'use')]
KNIFE_ACTS = [('use', 'Dùng bình thường'), ('hone', 'Mài lại bằng thanh mài trước ca'),
              ('swap', 'Rút ra, đổi dao khác và ghi sổ báo hỏng'), ('tape', 'Quấn băng keo cho chắc rồi dùng tạm')]
WASH = [('proper', 'Rửa nước rửa chén, tráng sạch, sát khuẩn rồi úp ráo trên giá'),
        ('towel', 'Lau khô bằng khăn vắt vai cho nhanh'), ('soak', 'Ngâm chung chậu với rau đang sơ chế'),
        ('rinse', 'Tráng qua nước lạnh là được')]

# ---------------------------------------------------------------- Đầu bếp: kiểm nguyên liệu
# id, label, kind (chill / frozen / veg / dry)
DELIVERY = [('ga', 'Gà ta làm sẵn', 'chill'), ('ca', 'Cá diêu hồng', 'chill'), ('bo', 'Thịt bò thăn', 'chill'),
            ('sua', 'Sữa tươi thanh trùng', 'chill'), ('tom', 'Tôm đông lạnh', 'frozen'), ('muc', 'Mực đông lạnh', 'frozen'),
            ('rau', 'Rau cải ngọt', 'veg'), ('nam', 'Nấm đông cô tươi', 'veg'), ('gao', 'Gạo tám', 'dry'), ('dau', 'Dầu ăn', 'dry')]
# kind: (ok readings, faulty readings)
READINGS = {
    'chill': (('đo được 3°C, mùi tươi', 'đo được 4°C, thớ thịt chắc'), ('đo được 9°C, thùng xốp không còn đá', 'mặt thịt nhớt, mùi lạ')),
    'frozen': (('đo được −18°C, đá giòn', 'đo được −20°C, bao nguyên'), ('đo được −6°C, tôm dính cục, có dấu rã đông rồi đông lại',
                                                                         'bao rách, đá tuyết bám dày')),
    'veg': (('lá xanh, cuống tươi', 'cây chắc, không dập'), ('dập úng, có mùi chua', 'lá úa vàng, có rệp')),
    'dry': (('bao nguyên, hạn dùng còn 6 tháng', 'chai nguyên tem, hạn dùng còn 1 năm'), ('bao rách, có mọt', 'hạn dùng ghi hôm qua')),
}
RECORD = [('return', 'Lập biên bản trả hàng, chụp ảnh, ký với người giao; báo bếp trưởng đặt bù'),
          ('keep', 'Nhận tạm, dùng hết trong ngày cho đỡ phí'), ('cook', 'Nhận, nấu thật chín là được'),
          ('toss', 'Bỏ thùng rác, khỏi ghi sổ')]
PUTAWAY = [('cold', 'Cất hàng đông và hàng mát vào tủ trước, hàng khô sau; hàng mới xếp sau hàng cũ'),
           ('dry', 'Cất hàng khô trước cho thông lối đi, hàng mát để sau'),
           ('front', 'Xếp hàng mới ra phía trước cho dễ lấy'), ('door', 'Để cả lô ở cửa bếp, cần đâu lấy đó')]

# ---------------------------------------------------------------- Đầu bếp: chế biến
# id, name, ordered steps, the done-ness test (right), wrong tests, vessel, garnishes
DISHES = {
    'cakho': ('Cá kho tộ', [('marinate', 'Ướp cá nước mắm, đường, tiêu 15 phút'), ('caramel', 'Thắng nước màu'),
                           ('lay', 'Xếp cá vào tộ, chan nước màu'), ('simmer', 'Kho lửa nhỏ tới khi nước sệt'),
                           ('finish', 'Rắc tiêu, hành lá')],
              'Nước kho sệt, thịt cá săn, xương sống không còn đỏ', ('Sôi bùng năm phút là tắt bếp', 'Nhìn màu nâu đẹp là được'),
              'nieu', ('tieu', 'hanhla', 'ot')),
    'galuoc': ('Gà luộc lá chanh', [('clean', 'Làm sạch gà, xát muối gừng'), ('boil', 'Thả gà vào nồi nước sôi lăn tăn'),
                                    ('test', 'Xiên đùi kiểm độ chín'), ('ice', 'Vớt gà ngâm nước đá cho da giòn'),
                                    ('chop', 'Chặt miếng, xếp đĩa')],
                'Xiên vào đùi thấy nước trong, nhiệt kế đầu dò từ 75°C', ('Luộc mười phút để thịt còn hồng cho mềm', 'Da vàng là chín'),
                'oval', ('lachanh', 'muoitieu', 'rauram')),
    'canhchua': ('Canh chua cá', [('base', 'Nấu nước me với cà chua, thơm'), ('fish', 'Thả cá khi nước sôi'),
                                  ('season', 'Nêm nước mắm, đường cho vừa'), ('veg', 'Cho bạc hà, giá rồi tắt bếp'),
                                  ('herb', 'Rắc ngò om, ngò gai')],
                  'Cá chín trắng, tách thớ; nước sôi lại mới nêm', ('Thả cá vào nước lạnh rồi đun chung', 'Nấu rau thật nhừ cho ngọt'),
                  'to', ('ngoom', 'ngogai', 'ot', 'toiphi')),
    'bolucac': ('Bò lúc lắc', [('marinate', 'Ướp bò với dầu hào, tỏi, tiêu'), ('heat', 'Làm nóng chảo gang thật nóng'),
                               ('sear', 'Xào bò lửa lớn hai phút'), ('pepper', 'Cho ớt chuông, hành tây đảo nhanh'),
                               ('serve', 'Đổ ra đĩa lót xà lách')],
                'Bề mặt bò xém cạnh, bên trong hồng nhạt đúng phiếu “chín vừa”', ('Xào lửa nhỏ mười lăm phút cho thấm', 'Hấp bò cho mềm rồi mới xào'),
                'gang', ('xalach', 'cachua', 'hanhtay', 'muoitieu')),
    'comchien': ('Cơm chiên dương châu', [('rice', 'Dùng cơm nguội, bóp tơi hạt'), ('garlic', 'Phi tỏi thơm'),
                                          ('egg', 'Xào trứng, đánh tơi'), ('fry', 'Cho cơm, đảo lửa lớn'),
                                          ('mix', 'Thêm lạp xưởng, tôm, đậu Hà Lan, nêm')],
                 'Cơm khô, rời hạt, nóng đều; tôm chín đỏ', ('Cho nước vào cho cơm mềm', 'Đảo lửa nhỏ nửa tiếng'),
                 'dia', ('dualeo', 'cachua', 'ngo')),
    'chagio': ('Chả giò', [('filling', 'Trộn nhân thịt, miến, mộc nhĩ'), ('roll', 'Cuốn chặt tay, dán mép'),
                           ('fry', 'Chiên ngập dầu lửa vừa'), ('drain', 'Vớt ra để ráo dầu'), ('cut', 'Cắt khoanh xéo')],
               'Vỏ vàng giòn, nhân chín, đầu dò từ 75°C', ('Chiên lửa thật lớn cho nhanh vàng', 'Vỏ vàng là được, khỏi đo'),
               'dia', ('rausong', 'dochua', 'ot')),
}
DONE_GENERIC = 'Nếm thấy vừa miệng là được'
TASTE = [('spoon', 'Dùng muỗng nếm riêng, nếm xong bỏ vào khay bẩn'), ('ladle', 'Nếm luôn bằng vá đang khuấy'),
         ('finger', 'Chấm tay nếm cho nhanh'), ('skip', 'Khỏi nếm, theo công thức là được')]

# ---------------------------------------------------------------- Đầu bếp: trang trí và hoàn thiện
VESSELS = dict(nieu='Niêu đất nóng', oval='Đĩa sứ oval dài', to='Tô sứ có đĩa lót', gang='Đĩa gang nóng có đế gỗ',
               dia='Đĩa sứ phẳng tròn')
GARNISH = dict(tieu='Tiêu xay', hanhla='Hành lá', ot='Ớt lát', lachanh='Lá chanh thái chỉ', muoitieu='Chén muối tiêu chanh',
               rauram='Rau răm', ngoom='Ngò om', ngogai='Ngò gai', toiphi='Tỏi phi', xalach='Xà lách', cachua='Cà chua',
               hanhtay='Hành tây', dualeo='Dưa leo', ngo='Ngò rí', rausong='Rau sống', dochua='Đồ chua', mayo='Sốt mayonnaise',
               hoacarot='Hoa cà rốt tỉa', chanh='Chanh cắt múi')
PLATE_NOTES = [('kids', 'Bàn có trẻ nhỏ: không ớt.', ('ot',)), ('onion', 'Khách dặn không hành.', ('hanhla', 'hanhtay')),
               ('none', 'Không có lưu ý riêng.', ())]
RIM = [('wipe', 'Lau mép đĩa bằng khăn giấy sạch, không chạm tay vào phần ăn'), ('cloth', 'Lau mép bằng khăn lau bàn'),
       ('thumb', 'Gạt vết sốt bằng ngón tay đeo bao'), ('leave', 'Để vậy cho nhanh ra món')]
PASS = [('serve', 'Ra món ngay'), ('reheat', 'Hâm lại tới từ 75°C rồi mới ra món'),
        ('discard', 'Bỏ phần này, nấu mẻ mới'), ('fan', 'Quạt cho nguội bớt rồi ra món')]

# ---------------------------------------------------------------- Sảnh sự kiện
# id: name, emoji, guests range, the reserve tables it adds, concepts that suit it
EVENTS = {
    'wedding': ('Tiệc cưới', '💒', (150, 450), 2, ('classic', 'garden', 'pastel', 'ocean', 'modern')),
    'birthday': ('Tiệc sinh nhật bé', '🎂', (30, 90), 0, ('cartoon', 'pastel', 'ocean')),
    'company': ('Tiệc tất niên công ty', '🏢', (80, 300), 0, ('modern', 'retro', 'classic', 'garden')),
    'fullmonth': ('Tiệc đầy tháng', '👶', (30, 100), 0, ('cartoon', 'pastel', 'classic')),
    'longevity': ('Tiệc mừng thọ', '🍑', (50, 150), 0, ('classic', 'garden')),
    'reunion': ('Họp lớp', '🎓', (30, 80), 0, ('retro', 'modern', 'garden')),
}
EVENT_ORDER = ('wedding', 'birthday', 'company', 'wedding', 'fullmonth', 'longevity', 'reunion')
CLIENTS = {
    'wedding': ('Duy và Thảo', 'Anh Phúc và chị Mai', 'Chị Ngọc Ánh'),
    'birthday': ('Chị Hoa, mẹ bé Bin', 'Anh Tùng, bố bé Su'),
    'company': ('Chị Vân, thư ký công ty Cánh Diều', 'Anh Quốc, phòng hành chính'),
    'fullmonth': ('Chị Trang, mẹ bé Mít', 'Anh Lộc, bố bé Na'),
    'longevity': ('Bà Sáu', 'Chú Hai Lâm'),
    'reunion': ('Lớp trưởng Hùng', 'Chị Thu, ban liên lạc lớp'),
}
CLIENT_NPC = dict(wedding=4, birthday=1, company=6, fullmonth=1, longevity=5, reunion=1)
SEATS = 10   # guests per table
# id, name, capacity (tables), rent (xu)
HALLS = [('sen', 'Phòng Sen', 6, 24), ('cuc', 'Phòng Cúc', 12, 42), ('lan', 'Sảnh Lan', 25, 80), ('hong', 'Sảnh Hồng Mây', 50, 150)]
CONCEPTS = {
    'classic': ('Đỏ vàng truyền thống', 'Nhà muốn không khí ấm cúng kiểu xưa: màu đỏ may mắn, ánh vàng.'),
    'garden': ('Vườn xanh', 'Thích cây xanh, hoa trắng, cảm giác như ngồi tiệc ngoài vườn.'),
    'pastel': ('Pastel nhẹ nhàng', 'Muốn màu hồng phấn, xanh mint, nhẹ nhàng dễ thương.'),
    'ocean': ('Biển xanh', 'Mê biển: màu xanh dương, vỏ sò, lưới cá.'),
    'retro': ('Hoài niệm thập niên 90', 'Muốn nhớ lại ngày xưa: băng cát-xét, xe đạp cũ, bảng đen.'),
    'modern': ('Hiện đại tối giản', 'Thích gọn gàng: trắng đen, ánh đèn vàng ấm, không rườm rà.'),
    'cartoon': ('Hoạt hình cho bé', 'Bé mê khủng long và bóng bay đủ màu.'),
}
# id, name, price per table (xu), dishes, tags
MENUS = [
    ('ankhang', 'Thực đơn An Khang', 36, 'Gỏi ngó sen tôm thịt · Gà luộc lá chanh · Canh chua cá · Cơm chiên · Chè hạt sen', ('seafood',)),
    ('phucloc', 'Thực đơn Phúc Lộc', 44, 'Súp cua · Bò lúc lắc · Cá kho tộ · Lẩu thái hải sản · Trái cây', ('seafood', 'beef')),
    ('thoxuan', 'Thực đơn Thọ Xuân', 40, 'Chả giò · Gà luộc lá chanh · Sườn ram · Canh bí đỏ · Bánh flan', ()),
    ('senchay', 'Thực đơn Sen Chay', 34, 'Gỏi cuốn chay · Nấm kho tiêu · Đậu hũ sốt cà · Canh rau củ · Chè', ('veg',)),
    ('songhy', 'Thực đơn Song Hỷ', 52, 'Gỏi tôm · Bò nướng lá lốt · Cá hấp xì dầu · Lẩu nấm · Bánh kem', ('seafood', 'beef')),
    ('doanvien', 'Thực đơn Đoàn Viên', 48, 'Chả giò · Gà quay · Sườn ram · Lẩu nấm, thêm phần chay riêng mỗi bàn · Trái cây', ('veg',)),
    ('anlac', 'Thực đơn An Lạc', 30, 'Nem rán · Thịt kho trứng · Canh chua chay · Rau xào tỏi · Trái cây', ()),
]
MENU_RULES = {
    'noseafood': ('Có khách dị ứng hải sản: thực đơn không được có hải sản.', lambda tags: 'seafood' not in tags),
    'nobeef': ('Nhà không dùng thịt bò.', lambda tags: 'beef' not in tags),
    'veg': ('Nhiều khách ăn chay: thực đơn phải có món chay.', lambda tags: 'veg' in tags),
    'none': ('Không kiêng gì đặc biệt.', lambda tags: True),
}
DRINKS = [('beer', 'Bia và nước ngọt'), ('wine', 'Rượu vang và nước ngọt'), ('soft', 'Nước ngọt và trà (không cồn)'),
          ('juice', 'Nước ép trái cây và sữa cho bé')]
DRINK_WISHES = {
    'wedding': (('Nhà trai dặn: bàn tiệc phải có bia cho các chú nâng ly.', 'beer'),
                ('Cô dâu muốn rượu vang cho buổi tối thêm sang.', 'wine'),
                ('Tiệc trưa, nhiều khách tự lái xe về quê: không dùng đồ có cồn.', 'soft')),
    'birthday': (('Tiệc của các bé: chỉ nước ép và sữa thôi nha.', 'juice'),
                 ('Bố mẹ dặn: không có cồn, các bé uống nước ép và sữa.', 'juice')),
    'company': (('Công ty quy định không rượu bia: ai cũng tự lái xe về.', 'soft'),
                ('Giám đốc muốn bia cho cả công ty nâng ly cuối năm.', 'beer'),
                ('Tiệc tri ân đối tác: dùng rượu vang.', 'wine')),
    'fullmonth': (('Nhiều bé nhỏ đi cùng: mẹ bé muốn nước ép và sữa.', 'juice'),
                  ('Tiệc buổi sáng: nước ngọt, trà, không cồn.', 'soft')),
    'longevity': (('Ông cụ dặn: con cháu được nâng ly rượu vang mừng thọ.', 'wine'),
                  ('Bà kiêng rượu bia, cả nhà chọn trà và nước ngọt không cồn.', 'soft')),
    'reunion': (('Lớp muốn bia cho đúng không khí ngày xưa.', 'beer'),
                ('Nhiều bạn chở con theo: không dùng đồ có cồn.', 'soft')),
}
_ALL = tuple(EVENTS)
# Decoration: id, label, category, events it suits, concepts it suits (empty = every concept)
DECOR = [
    ('hy', 'Backdrop chữ Song Hỷ', 'backdrop', ('wedding',), ('classic',)),
    ('names', 'Backdrop tên cô dâu chú rể', 'backdrop', ('wedding',), ('garden', 'pastel', 'ocean', 'modern')),
    ('bday', 'Backdrop “Chúc mừng sinh nhật”', 'backdrop', ('birthday',), ()),
    ('logo', 'Backdrop logo và tên công ty', 'backdrop', ('company',), ()),
    ('baby', 'Backdrop tên bé và ngày đầy tháng', 'backdrop', ('fullmonth',), ()),
    ('tho', 'Backdrop chữ Thọ', 'backdrop', ('longevity',), ()),
    ('class', 'Backdrop tên lớp và niên khóa', 'backdrop', ('reunion',), ()),
    ('gate_fresh', 'Cổng hoa tươi lối vào', 'fresh', ('wedding',), ('garden', 'pastel', 'classic')),
    ('gate_silk', 'Cổng hoa lụa lối vào', 'silk', ('wedding',), ('garden', 'pastel', 'classic')),
    ('table_fresh', 'Hoa tươi để bàn', 'fresh', ('wedding', 'company', 'longevity', 'reunion'), ('garden', 'pastel', 'classic', 'modern')),
    ('table_silk', 'Hoa lụa để bàn', 'silk', ('wedding', 'company', 'longevity', 'reunion'), ('garden', 'pastel', 'classic', 'modern')),
    ('peach', 'Bình đào và mâm đào tiên', 'fresh', ('longevity',), ('classic', 'garden')),
    ('red_cloth', 'Khăn trải bàn đỏ viền vàng', 'cloth', _ALL, ('classic',)),
    ('white_cloth', 'Khăn trải bàn trắng', 'cloth', _ALL, ('garden', 'modern', 'ocean')),
    ('pink_cloth', 'Khăn trải bàn hồng phấn', 'cloth', _ALL, ('pastel', 'cartoon')),
    ('check_cloth', 'Khăn kẻ ca rô xanh đỏ', 'cloth', _ALL, ('retro',)),
    ('fairy', 'Đèn dây đom đóm', 'light', _ALL, ('garden', 'pastel', 'modern')),
    ('lantern', 'Đèn lồng đỏ', 'light', _ALL, ('classic',)),
    ('led', 'Nến LED trên bàn', 'light', _ALL, ('pastel', 'garden', 'modern', 'ocean')),
    ('fire', 'Nến lửa thật trên bàn', 'flame', _ALL, ('pastel', 'garden', 'modern', 'ocean', 'classic')),
    ('balloon', 'Cổng bóng bay nhiều màu', 'balloon', ('birthday', 'fullmonth'), ('cartoon', 'pastel')),
    ('shell', 'Vỏ sò và lưới cá trên bàn', 'other', _ALL, ('ocean',)),
    ('dino', 'Mô hình khủng long', 'other', ('birthday', 'fullmonth'), ('cartoon',)),
    ('cassette', 'Góc ảnh băng cát-xét và xe đạp cũ', 'other', ('reunion', 'company'), ('retro',)),
]
DECOR_LIMITS = {
    'pollen': 'Có khách dị ứng phấn hoa: thay hoa tươi bằng hoa lụa.',
    'balloon': 'Có cụ già sợ tiếng bóng nổ: không bóng bay.',
    'none': 'Không có lưu ý riêng về trang trí.',
}
# Sound and light: id, what is heard or seen, the fix (the right option's id)
AV = [
    ('feedback', 'Mic kêu hú rít mỗi khi MC đi ngang trước loa.', 'move'),
    ('battery', 'Mic không dây lúc có lúc mất, đèn pin trên mic nháy đỏ.', 'battery'),
    ('cable', 'Màn LED sân khấu chớp tắt mỗi khi có người đi ngang bàn kỹ thuật.', 'cable'),
    ('glare', 'Đèn follow chiếu thẳng vào mắt khách ngồi bàn đầu.', 'aim'),
    ('loud', 'Nhạc nền to tới mức bàn gần loa phải hét mới nghe nhau.', 'level'),
]
AV_FIX = [('move', 'Dời loa ra trước vị trí MC, giảm độ nhạy mic, không chĩa mic vào loa'),
          ('battery', 'Thay pin mới cho mic, để sẵn một mic dự phòng đã thử'),
          ('cable', 'Cắm chắc dây tín hiệu, đi dây sát tường, dán cố định'),
          ('aim', 'Chỉnh góc và độ sáng đèn, ngồi thử ở bàn đầu'),
          ('level', 'Giảm nhạc nền, quay loa về phía sân khấu, đo lại ở bàn gần loa')]
# Electrics walk-round: id, what you see, is it a hazard to fix before guests come in?
POWER = [
    ('stack', 'Ba ổ cắm kéo dài cắm nối chồng nhau cho máy tạo khói, máy chiếu và loa.', True),
    ('frayed', 'Dây đèn trang trí tróc vỏ ở chỗ quấn quanh cột.', True),
    ('smoke', 'Máy tạo khói đặt sát rèm vải sân khấu.', True),
    ('wet', 'Ổ cắm cạnh chậu rửa quầy bar không có nắp chống nước.', True),
    ('hidden', 'Bình chữa cháy bị backdrop che kín phía sau.', True),
    ('covered', 'Dây điện băng qua lối đi đã có máng che, dán băng cảnh báo.', False),
    ('panel', 'Tủ điện sảnh có khóa, sơ đồ aptomat dán ở cửa tủ.', False),
    ('exit', 'Đèn sự cố và biển lối thoát hiểm đều sáng.', False),
]
# Incidents during the event: id, what happens, the right handling, two wrong ones
INCIDENTS = [
    ('blackout', 'Đang cắt bánh thì cúp điện cả sảnh, khách bắt đầu ồn ào.',
     'Bật đèn sự cố, nhờ MC trấn an khách, gọi kỹ thuật chạy máy phát; không đốt nến lửa',
     ('Phát nến lửa cho mỗi bàn tự thắp', 'Mời khách về sớm cho an toàn')),
    ('fall', 'Một cụ bà trượt chân ngã ở bậc sân khấu.',
     'Đỡ cụ ngồi yên tại chỗ, hỏi chỗ đau, gọi người nhà; đau nhiều thì gọi 115, lau khô và chắn bậc',
     ('Kéo cụ đứng dậy ngay cho khỏi ngại', 'Cứ chạy tiếp chương trình, lát hỏi thăm sau')),
    ('drunk', 'Một vị khách đã say, đòi tự lái xe về.',
     'Mời ngồi nghỉ uống trà, báo người nhà hoặc gọi taxi đưa về; không trả chìa khóa khi còn say',
     ('Đưa chìa khóa, dặn đi chậm', 'Mặc kệ, chuyện riêng của khách')),
    ('child', 'Một bé bốn tuổi lạc bố mẹ giữa sảnh đông.',
     'Giữ bé ở quầy lễ tân, nhờ MC mô tả bé để gia đình tới đón; không giao bé cho người lạ',
     ('Dắt bé đi khắp sảnh tìm', 'Giao bé cho vị khách nào nhận là người quen')),
    ('envelope', 'Chủ tiệc báo không thấy hộp mừng ở bàn lễ tân.',
     'Báo bảo vệ giữ lối ra, cùng chủ tiệc xem camera; không tự lục túi khách',
     ('Tự lục túi mấy khách đứng gần bàn', 'Bảo chủ tiệc tự lo')),
    ('spill', 'Một khay nước đổ tràn ra lối đi gần sân khấu.',
     'Đặt biển sàn ướt, lau khô ngay, dẫn khách đi lối bên',
     ('Rải khăn giấy lên rồi để đó', 'Đợi tan tiệc rồi lau một lần')),
    ('mc', 'MC gọi báo kẹt xe, tới trễ 30 phút.',
     'Chạy trình chiếu ảnh và nhạc nhẹ, quản lý sảnh chào khách mở màn, báo chủ tiệc lịch mới',
     ('Để sảnh im chờ MC tới', 'Mời đại một khách lên làm MC')),
    ('cake', 'Bánh kem nhiều tầng bị nghiêng khi đẩy ra sân khấu.',
     'Dừng xe đẩy, đưa bánh vào bếp chỉnh lại, dùng bánh mô hình cho nghi thức cắt bánh',
     ('Cứ đẩy tiếp cho kịp giờ', 'Cắt bỏ tầng nghiêng ngay trên sân khấu')),
]

# 🎉 Holiday rush days by the real Vietnam date (UTC+7): more orders, pay ×1.5, less room for slips.
RUSH = {
    'tet': ('Tết Nguyên Đán', '🧧'),
    'newyear': ('Tết Dương lịch', '🎆'),
    'valentine': ('Lễ Tình nhân 14/2', '💘'),
    'women': ('Quốc tế Phụ nữ 8/3', '🌷'),
    'reunify': ('Lễ 30/4 – 1/5', '🎉'),
    'children': ('Quốc tế Thiếu nhi 1/6', '🎈'),
    'national': ('Quốc khánh 2/9', '🇻🇳'),
    'vnwomen': ('Phụ nữ Việt Nam 20/10', '💐'),
    'teachers': ('Nhà giáo Việt Nam 20/11', '📚'),
    'noel': ('Giáng sinh', '🎄'),
}
RUSH_DATES = {(12, 31): 'newyear', (1, 1): 'newyear', (2, 14): 'valentine', (3, 8): 'women', (4, 30): 'reunify',
              (5, 1): 'reunify', (6, 1): 'children', (9, 2): 'national', (10, 20): 'vnwomen', (11, 20): 'teachers',
              (12, 24): 'noel', (12, 25): 'noel'}
TET_BEFORE, TET_AFTER = timedelta(days=2), timedelta(days=3)   # 28 Tết tới mùng 4: the year-end and new-year feasts
RUSH_BONUS = 1.5

DESK = [
    dict(id='ring', title='Nhờ giấu nhẫn cầu hôn trong bánh flan', emoji='💍', npc=4, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Một anh khách thì thầm ở cửa bếp: “Giấu giúp chiếc nhẫn vào chén flan của bạn gái mình nha, bàn số 7.”',
         options=[dict(id='plate', label='Không bỏ nhẫn vào đồ ăn; đặt nhẫn trong hộp trên đĩa tráng miệng riêng, ra món cùng lúc', hint='',
                       effects=dict(xp=6, review=[5, 'Bếp không cho bỏ nhẫn vào bánh, mà đĩa tráng miệng ra đẹp như phim. Cô ấy gật đầu rồi!']), good=True,
                       outcome='Đĩa flan có chiếc hộp nhung ra đúng lúc bản nhạc đổi. Cả nhà hàng vỗ tay.'),
                  dict(id='inside', label='Ấn nhẫn vào giữa chén flan', hint='',
                       effects=dict(review=[2, 'Suýt cắn trúng chiếc nhẫn, hú hồn.']), good=False,
                       outcome='Cô gái cắn trúng nhẫn, đau răng, buổi cầu hôn thành buổi đi nha sĩ.'),
                  dict(id='no', label='Từ chối, bếp đang bận', hint='', effects=dict(patience=-2), good=None,
                       outcome='Anh khách tự cầu hôn bằng tay không, vẫn được đồng ý nhưng hơi run.')],
         default='no'),
    dict(id='live', title='Khách đòi livestream trong bếp', emoji='📱', npc=4, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Một khách cầm gậy tự sướng đi thẳng tới cửa bếp: “Cho mình quay đầu bếp nấu cho người xem nha!”',
         options=[dict(id='pass', label='Mời đứng ở cửa ra món quay vào, không bước qua vạch khu bếp', hint='',
                       effects=dict(xp=5, review=[5, 'Được quay bếp tiệc mà gọn gàng sạch sẽ, người xem khen nức nở.']), good=True,
                       outcome='Clip “một đêm trong bếp tiệc” được chia sẻ khắp nơi, không ai phải bước vào khu nấu.'),
                  dict(id='in', label='Cho vào tận bếp quay cho đã', hint='', effects=dict(review=[2, 'Khách đi lại trong bếp, chẳng thấy ai đội mũ.']), good=False,
                       outcome='Khách đứng chắn lối chảo nóng, suýt bị dầu bắn vào tay.'),
                  dict(id='shoo', label='Đóng cửa bếp, không nói gì', hint='', effects=dict(patience=-2), good=None,
                       outcome='Khách quay cánh cửa đóng, chú thích “bếp bí ẩn”.')],
         default='shoo'),
    dict(id='rat', title='Bóng chuột chạy qua kho khô', emoji='🐀', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Bạn vừa mở kho khô thì thấy một bóng chuột chạy vụt qua bao gạo. Tiệc tối còn hai tiếng.',
         options=[dict(id='seal', label='Báo bếp trưởng, kiểm từng bao, bỏ bao bị cắn, gọi đội diệt côn trùng, ghi sổ', hint='',
                       effects=dict(xp=6), good=True,
                       outcome='Chỉ một bao gạo bị cắn và đã bỏ. Tối đó đội diệt côn trùng bịt lỗ hổng sau kho.'),
                  dict(id='quiet', label='Lờ đi cho kịp tiệc, mai tính', hint='', effects=dict(review=[2, 'Nghe nói bếp nhà hàng có chuột.', 3]), good=False,
                       outcome='Tuần sau đoàn kiểm tra thấy dấu chuột trong kho, bếp bị nhắc nhở.'),
                  dict(id='trap', label='Đặt tạm một cái bẫy rồi làm tiếp', hint='', effects=dict(patience=-1), good=None,
                       outcome='Bẫy bắt được một con, nhưng chưa ai kiểm bao hàng.')],
         default='trap'),
    dict(id='extra', title='Đám cưới báo thêm ba bàn phút chót', emoji='➕', npc=4, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Chú rể gọi gấp: họ hàng dưới quê lên thêm, cần thêm ba bàn ngay trong tối nay.',
         options=[dict(id='plan', label='Kiểm nguyên liệu với bếp, kê bàn dự phòng, báo giá phát sinh rõ ràng rồi mới nhận', hint='',
                       effects=dict(xp=6, review=[5, 'Báo thêm bàn sát giờ mà nhà hàng xoay kịp, giá nói trước rõ ràng.']), good=True,
                       outcome='Ba bàn dự phòng được kê kịp, bếp còn đủ nguyên liệu, nhà trai cảm ơn rối rít.'),
                  dict(id='yes', label='Cứ nhận hết, tính sau', hint='', effects={},
                       luck=dict(p=0.4, win=dict(effects=dict(xp=2), outcome='May mà kho còn đủ, bếp chạy kịp.', good=None),
                                 lose=dict(effects=dict(review=[2, 'Thêm bàn xong món ra thiếu, bàn cuối chờ mãi.']), outcome='Bếp thiếu cá, ba bàn cuối ăn muộn.', good=False))),
                  dict(id='no', label='Từ chối vì sát giờ', hint='', effects=dict(patience=-2), good=None,
                       outcome='Họ hàng ngồi ghép bàn, hơi chật nhưng vẫn vui.')],
         default='no'),
    dict(id='flicker', title='Đèn bếp chập chờn', emoji='💡', npc=2, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Dãy đèn trên bàn sơ chế nhấp nháy, ổ cắm bên cạnh hơi nóng, có mùi khét nhẹ.',
         options=[dict(id='cut', label='Ngắt aptomat khu đó, dời việc sang bàn khác, gọi anh Khoa xem', hint='',
                       effects=dict(xp=6), good=True,
                       outcome='Anh Khoa tìm ra mối nối lỏng sau tường, thay ổ cắm mới trước giờ tiệc.'),
                  dict(id='fix', label='Tự tháo ổ cắm ra xem', hint='', effects=dict(review=[2, 'Nhân viên bếp tự sửa điện, nhìn mà sợ.', 2]), good=False,
                       outcome='Bạn bị điện giật nhẹ, may mà không sao, nhưng cả bếp phải dừng tay.'),
                  dict(id='ignore', label='Kệ, vẫn còn sáng', hint='', effects=dict(patience=-2), good=None,
                       outcome='Đèn tắt hẳn giữa giờ ra món, cả bếp làm dưới đèn điện thoại.')],
         default='ignore'),
    dict(id='dog', title='Chú cún của cô dâu muốn làm phù dâu', emoji='🐶', npc=4, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Cô dâu ôm chú cún đeo nơ: “Bé Bông phải được đi cùng lúc tụi mình bước vào sảnh!”',
         options=[dict(id='walk', label='Cho Bông đi cùng màn bước vào có người dắt, sau đó ở khu riêng ngoài sân, không vào khu bàn ăn', hint='',
                       effects=dict(xp=5, review=[5, 'Bông đi trước cô dâu dễ thương xỉu, mà không ai phải ngồi ăn cạnh chó.']), good=True,
                       outcome='Màn bước vào có bé Bông được chụp nhiều nhất buổi tiệc.'),
                  dict(id='table', label='Cho Bông ngồi luôn bàn chính', hint='', effects=dict(review=[2, 'Bàn bên cạnh có khách dị ứng lông chó.']), good=False,
                       outcome='Một khách hắt hơi cả buổi, phải đổi chỗ.'),
                  dict(id='no', label='Không cho thú cưng vào sảnh', hint='', effects=dict(patience=-2), good=None,
                       outcome='Cô dâu buồn một chút, Bông xem tiệc qua cửa kính.')],
         default='no'),
    dict(id='leftover', title='Khách xin mang đồ ăn thừa về', emoji='🥡', npc=5, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Tan tiệc, bà Sáu xin gói phần gà và xôi còn dư mang về cho hàng xóm.',
         options=[dict(id='box', label='Gói hộp sạch có nắp, dán giờ, dặn để tủ lạnh và ăn trong ngày', hint='',
                       effects=dict(xp=4, review=[5, 'Gói đồ mang về gọn gàng, còn dặn kỹ cách giữ.']), good=True,
                       outcome='Bà Sáu khen hộp gói gọn, mai còn chia cho cả xóm.'),
                  dict(id='bag', label='Gom chung vào túi ni lông', hint='', effects=dict(review=[3, 'Gói đồ mang về lộn xộn quá.']), good=False,
                       outcome='Nước sốt chảy ra túi, dính cả giỏ xe.'),
                  dict(id='no', label='Từ chối vì sợ trách nhiệm', hint='', effects=dict(patience=-2), good=None,
                       outcome='Bà Sáu tiếc rẻ, đồ dư bị đổ bỏ.')],
         default='no'),
    dict(id='recipe', title='Bà Sáu đưa công thức riêng', emoji='📝', npc=5, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Bà Sáu đưa tờ giấy viết tay: “Gà luộc nhà bà phải có lá chanh non, chấm muối tiêu chanh. Ông nhà chỉ ăn kiểu đó.”',
         options=[dict(id='note', label='Ghi vào phiếu bếp của bàn mừng thọ, báo bếp trưởng, chuẩn bị riêng một đĩa', hint='',
                       effects=dict(xp=5, review=[5, 'Ông nhà ăn gà xong cười tít mắt, đúng vị nhà làm.']), good=True,
                       outcome='Đĩa gà riêng ra bàn ông cụ, bà Sáu dúi tay bạn gói kẹo.'),
                  dict(id='forget', label='Nhận lời rồi để quên tờ giấy trong túi', hint='', effects=dict(review=[2, 'Dặn rồi mà gà vẫn ra như mọi bàn.']), good=False,
                       outcome='Gà ra như mọi bàn, ông cụ ăn ít hẳn.'),
                  dict(id='no', label='Nói nhà hàng chỉ nấu theo thực đơn', hint='', effects=dict(patience=-2), good=None,
                       outcome='Bà Sáu gật đầu nhưng hơi buồn.')],
         default='no'),
    dict(id='singer', title='Ca sĩ khách mời đòi đổi bài phút chót', emoji='🎤', npc=2, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Ca sĩ khách mời muốn đổi bài mở màn, nhưng nhạc nền bài mới chưa có trong máy của anh Khoa.',
         options=[dict(id='check', label='Báo chủ tiệc, nhờ anh Khoa thử nhạc bài mới trước khi lên sân khấu; chưa có thì giữ bài cũ', hint='',
                       effects=dict(xp=5), good=True,
                       outcome='Bài mới thử kịp trong năm phút, mở màn suôn sẻ.'),
                  dict(id='live', label='Cứ lên hát, nhạc tính sau', hint='', effects=dict(review=[2, 'Mở màn hát chay, lệch tông cả bài.']), good=False,
                       outcome='Nhạc vào trễ nửa bài, ca sĩ đứng hình.'),
                  dict(id='refuse', label='Bắt giữ bài cũ, không hỏi chủ tiệc', hint='', effects=dict(patience=-1), good=None,
                       outcome='Ca sĩ hát bài cũ, hơi miễn cưỡng.')],
         default='refuse'),
    dict(id='taste', title='Chú rể xin vào bếp nếm thử', emoji='🥄', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Chú rể ló đầu vào bếp: “Cho anh nếm thử món lẩu trước, nhà gái khó tính lắm.”',
         options=[dict(id='cup', label='Múc một chén nhỏ bằng muỗng sạch ra cửa ra món cho chú rể nếm', hint='',
                       effects=dict(xp=4, review=[5, 'Được nếm trước một chén, yên tâm hẳn.']), good=True,
                       outcome='Chú rể gật gù, chỉ xin thêm chút sả cho bàn nhà gái.'),
                  dict(id='pot', label='Đưa luôn vá cho chú rể nếm từ nồi', hint='', effects=dict(review=[2, 'Bếp cho khách nếm thẳng từ nồi, mất vệ sinh.']), good=False,
                       outcome='Cả nồi lẩu phải đổ bỏ vì vá đã qua miệng khách.'),
                  dict(id='no', label='Nói bếp không cho khách nếm', hint='', effects=dict(patience=-2), good=None,
                       outcome='Chú rể lo lắng tới tận lúc món ra.')],
         default='no'),
]

MILESTONES = [
    dict(id='helper', label='Phụ bếp vững tay', jobs=15, days=5, roles=1),
    dict(id='both', label='Đứng bếp lẫn đứng sảnh', jobs=60, days=20, roles=3),
    dict(id='soul', label='Linh hồn Hồng Mây', jobs=160, days=40, roles=3),
]
NOTEBOOK = [
    'Mọi quy định, giá và thực đơn ở đây là quy tắc hư cấu dùng cho nhà hàng tiệc Hồng Mây.',
    'Đầu ca bếp: rửa tay xà phòng 20 giây → sát khuẩn tay → đội mũ, mặc tạp dề → đeo bao tay → kiểm bếp gas, máy hút mùi, nhiệt độ tủ mát. Đoàn kiểm tra vệ sinh an toàn thực phẩm có thể ghé bất chợt và xem đúng những việc này.',
    'Cuối ca bếp: gom rác → rửa, sát khuẩn dụng cụ → lau mặt bếp, bàn sơ chế → lau sàn; rồi tắt mọi thiết bị đang bật (bếp gas, hút mùi, nồi cơm, lò, ấm, bếp chiên). Tủ mát và tủ đông luôn để chạy.',
    f'Quên kiểm tra thiết bị điện cuối ca: đêm đó có thể chập cháy (khoảng {round(FIRE_CHANCE * 100)}% số lần). Tiền đền bù trừ vào ví của bạn: {FIRE_PCT}% lương ca, ít nhất {FIRE_MIN} xu, nhiều nhất {FIRE_CAP} xu, không bao giờ quá số tiền đang có.',
    'Thớt màu: xanh lá cho rau củ quả, đỏ cho thịt sống, xanh dương cho hải sản sống, vàng cho đồ đã nấu chín.',
    'Sơ chế: rau ngâm nước muối loãng rồi xả ba lần; thịt, hải sản đông lạnh rã đông trong ngăn mát; thịt tươi lọc trên thớt riêng; hải sản tươi giữ trên đá, bồn riêng. Số gam = số suất × gam mỗi suất.',
    'Bảo quản: hộp có nắp, dán nhãn tên và giờ sơ chế. Rau ở ngăn trên tủ mát; thịt, hải sản sống ở ngăn dưới cùng.',
    'Salad: nhặt lá dập → ngâm muối → xả ba lần → quay ráo → cắt, xé. Theo công thức, bỏ món trái lưu ý của khách; khách xin đổi sốt thì đổi. Số gam rau = số đĩa × gam mỗi đĩa.',
    'Dụng cụ: lấy đủ dụng cụ cho từng món trên bảng ca. Tô, chén, đĩa: đúng số suất cộng 10% dự phòng, làm tròn lên. Dao mẻ hoặc lỏng cán thì đổi và ghi sổ; dao cùn thì mài trước ca.',
    'Kiểm nguyên liệu: hàng mát nhận khi từ 5°C trở xuống, hàng đông khi từ −18°C trở xuống và không có dấu rã đông; rau không dập úng; hàng khô bao nguyên, còn hạn. Hàng không đạt thì lập biên bản trả, cân thực nhận chỉ tính hàng nhận. Cất hàng lạnh trước, hàng mới xếp sau hàng cũ.',
    'Chế biến: làm đúng thứ tự công thức, kiểm độ chín bằng dấu hiệu chắc chắn (thịt gà, chả từ 75°C). Nếm bằng muỗng nếm riêng. Số phần = số bàn × phần mỗi bàn + phần lẻ.',
    'Ra món: đúng dụng cụ của món, đủ món trang trí của món trừ món trái lưu ý; lau mép đĩa bằng khăn giấy sạch. Món nóng từ 60°C thì ra ngay; dưới 60°C mà chưa quá 2 giờ thì hâm lại tới từ 75°C; để quá 2 giờ thì bỏ, nấu mẻ mới.',
    f'Sảnh: {SEATS} khách một bàn, làm tròn lên; tiệc cưới thêm 2 bàn dự phòng. Chọn phòng nhỏ nhất đủ số bàn (phòng càng lớn càng đắt). Thực đơn: hợp lưu ý của khách, giá cao nhất không vượt ngân sách mỗi bàn.',
    'Trang trí: đủ đồ hợp dịp và hợp chủ đề; khách dị ứng phấn hoa thì dùng hoa lụa thay hoa tươi (không thì dùng hoa tươi); không bóng bay khi khách dặn; sảnh kín không dùng nến lửa thật.',
    'Trước giờ đón khách: thử âm thanh, ánh sáng; đi một vòng kiểm điện: ổ cắm nối chồng, dây tróc vỏ, máy tạo khói sát rèm, ổ cắm gần nước không nắp, bình chữa cháy bị che đều phải xử lý.',
    'Sự cố trong tiệc: an toàn của khách trước, giữ bình tĩnh, báo người phụ trách, không tự làm việc của bảo vệ hay y tế.',
    'Ngày lễ đông khách (giờ Việt Nam): Tết, 14/2, 8/3, 30/4–1/5, 1/6, 2/9, 20/10, 20/11, Giáng sinh, Tết Dương lịch. Thêm phiếu việc, thưởng ×1.5, nhưng sai một bước trừ chất lượng nhiều hơn.',
    f'Phụ bếp thử việc {PROBATION} ca bếp đạt (sát khuẩn đầu ca, ít nhất một việc đạt từ 90%, dọn và tắt điện cuối ca, không bị đoàn kiểm tra nhắc) thì lên Đầu bếp. Lên rồi, mỗi ca chọn làm Phụ bếp, Đầu bếp hay Sảnh đều được.',
    'Lương ca trả theo hợp đồng khi khép ca; thưởng chất lượng nhỏ theo từng việc, sai bước thì sửa tại chỗ và thưởng giảm.',
]
