"""🔬 Viện nghiên cứu Sông Mây: a fictional applied-research institute (seeds, recipes, small inventions).

Every rule, number, person and result here is game content only: no real agronomy, food safety or engineering advice.
"""

PEOPLE = [
    ('Cô Diệu Linh', 'Viện trưởng', 'Đọc báo cáo bằng bút đỏ, hỏi “số liệu gốc đâu?” trước khi chào.', 'picky'),
    ('Anh Quý', 'Nghiên cứu viên cùng phòng', 'Hay đứng cạnh lúc chụp ảnh kết quả, ít khi đứng cạnh lúc rửa ống nghiệm.', 'quiet'),
    ('Chị Nhàn', 'Kỹ thuật viên phòng thí nghiệm', 'Thuộc vị trí từng lọ hóa chất, ghét nhất ai để găng tay trên bàn cân.', 'warm'),
    ('Ông Hưng', 'Nhà tài trợ đề tài', 'Công ty giống cây Hưng Phát, muốn có kết quả “trước Tết cho đẹp”.', 'picky'),
    ('GS. Bảo', 'Chủ tịch hội đồng khoa học', 'Ba mươi năm duyệt đề tài, chưa từng cho qua một biểu đồ không có sai số.', 'picky'),
    ('Bé Su', 'Thực tập sinh', 'Năm cuối đại học, nhanh tay, hay dán nhãn bằng bút dạ sắp hết mực.', 'genz'),
    ('Bác Tư', 'Nông dân nhận khảo nghiệm', 'Cho viện mượn ba sào ruộng, nuôi một con trâu rất tò mò.', 'warm'),
]
DIRECTOR = 0      # Cô Diệu Linh hands out the job slips and checks lab safety
COLLEAGUE = 1     # Anh Quý, who takes the credit
SPONSOR = 3       # Ông Hưng
COUNCIL = 4       # GS. Bảo
INTERN = 5

# 🔬 three tracks, chosen at the start of a shift (any of them, any day)
TRACKS = {
    'seed': ('Giống cây', '🌱', 'Lai tạo, khảo nghiệm, ngân hàng hạt giống'),
    'recipe': ('Công thức món', '🍳', 'Chuẩn hóa công thức, hội đồng nếm, giá vốn và nhãn'),
    'invent': ('Sáng chế', '🛠️', 'Làm mẫu thử, thử độ bền, hồ sơ sáng chế'),
}
JOBS = {
    'cross': ('Lai tạo giống mới', '🧬', 'seed'),
    'field': ('Khảo nghiệm ngoài đồng', '🌾', 'seed'),
    'bank': ('Cất vào ngân hàng hạt giống', '🫙', 'seed'),
    'scale': ('Chuẩn hóa công thức', '⚖️', 'recipe'),
    'taste': ('Hội đồng nếm thử', '🥄', 'recipe'),
    'cost': ('Giá vốn và nhãn món', '🏷️', 'recipe'),
    'proto': ('Làm mẫu thử', '🔧', 'invent'),
    'drop': ('Thử độ bền', '📦', 'invent'),
    'patent': ('Hồ sơ sáng chế', '📜', 'invent'),
}
TRACK_JOBS = {'seed': ('cross', 'field', 'bank'), 'recipe': ('scale', 'taste', 'cost'), 'invent': ('proto', 'drop', 'patent')}
BONUS = dict(cross=6, field=7, bank=6, scale=6, taste=7, cost=7, proto=7, drop=6, patent=8)
WRONG_COST = 6          # quality lost per redone step
QUALITY_FLOOR = 60
COUNCIL_DAY = 4         # from this career day every job ends in front of the council
RATS_DAY = 3            # from this day the field trial may find samples the rats got to

# 🔥 Leaving the lab without the closing check: some nights a heater left on spoils the samples.
NIGHT_CHANCE = 0.15
NIGHT_PCT = 8           # the compensation: 8% of the day's contract salary…
NIGHT_MIN, NIGHT_CAP = 2, 6   # …at least 2 and at most 6 xu, and never more than the wallet holds
SAFETY_CHANCE = 0.3     # the director's surprise safety walk, on about one lab day in three (from day 2)

# ---------------------------------------------------------------- shift checklists
OPEN_STEPS = [('coat', 'Mặc áo blouse, cài kín cúc'), ('goggles', 'Đeo kính bảo hộ'), ('gloves', 'Đeo găng tay nitrile'),
              ('hood', 'Bật tủ hút, kiểm tra quạt hút chạy'), ('book', 'Ghi giờ vào sổ nhật ký phòng thí nghiệm')]
CLOSE_ORDER = [('samples', 'Cất mẫu vào tủ lạnh mẫu, đúng ngăn, đúng nhãn'), ('chem', 'Khóa tủ hóa chất, trả chìa cho chị Nhàn'),
               ('wash', 'Rửa dụng cụ, úp lên giá ráo'), ('log', 'Ghi sổ: việc đã làm, mẫu còn lại, sự cố trong ngày')]
# Equipment at closing: id, label, (state words, must be switched off tonight?) when on / off
EQUIPMENT = [
    ('hotplate', 'Bếp từ thí nghiệm', ('mặt bếp còn đỏ đèn', True), ('đã tắt, nguội', False)),
    ('stirrer', 'Máy khuấy từ', ('cá từ vẫn quay', True), ('đã tắt', False)),
    ('uv', 'Đèn UV tủ cấy', ('đèn tím còn sáng', True), ('đã tắt', False)),
    ('iron', 'Mỏ hàn bàn sáng chế', ('đèn báo nóng còn sáng', True), ('đã rút phích', False)),
    ('dryer', 'Máy sấy hạt', ('quạt còn chạy, 45°C', True), ('đã tắt', False)),
    ('oven', 'Lò nướng bếp thử', ('quạt lò còn quay', True), ('đã tắt, nguội', False)),
    ('incubator', 'Tủ ấm ươm mầm', ('đang chạy 28°C', False), ('đang chạy 27°C', False)),
    ('fridge', 'Tủ lạnh mẫu', ('đang chạy 4°C', False), ('đang chạy 5°C', False)),
]

# ---------------------------------------------------------------- 🌱 Giống cây
CROPS = [('lua', 'lúa', 'hạt'), ('ot', 'ớt', 'trái'), ('dua', 'dưa hấu', 'trái'), ('cachua', 'cà chua', 'trái'),
         ('bap', 'bắp', 'trái'), ('dau', 'đậu xanh', 'hạt')]
TRAITS = [('han', 'chịu hạn'), ('man', 'chịu mặn'), ('sau', 'kháng sâu'), ('to', 'to và chắc'), ('som', 'chín sớm'),
          ('ngot', 'ngọt hơn')]
TARGET_WHY = {
    'han': 'ruộng bác Tư mùa khô hay thiếu nước',
    'man': 'nước sông Mây mùa khô bị nhiễm mặn',
    'sau': 'năm nay sâu cuốn lá về sớm',
    'to': 'thương lái chê hàng nhỏ',
    'som': 'muốn kịp bán trước mưa bão',
    'ngot': 'chợ đầu mối trả giá cao hàng ngọt',
}
GERM = (80, 50, 40, 25, 20)            # germination % of a cross (an exact 100/p keeps the sum whole)
TAGS = [('full', 'Mã tổ hợp lai, ngày gieo, tên hai dòng bố mẹ, người làm'), ('pencil', 'Ghi “giống mới” bằng bút chì cho nhanh'),
        ('memory', 'Nhớ trong đầu, khay nào cũng giống nhau'), ('sponsor', 'Ghi tên nhà tài trợ thật to cho đẹp ảnh')]
CONTROL = [('control', 'Gieo kèm một khay giống cũ làm đối chứng: cùng đất, cùng nước, cùng chỗ'),
           ('none', 'Chỉ gieo giống mới cho đỡ tốn khay'),
           ('shade', 'Để khay giống cũ chỗ râm cho giống mới trông tốt hơn'),
           ('water', 'Tưới giống mới nhiều hơn một chút cho chắc ăn')]
PLOT_SPOIL = [('flood', 'vỡ bờ, ngập nước hai ngày'), ('buffalo', 'trâu nhà bác Tư vào giẫm nát một góc'),
              ('spray', 'ruộng bên cạnh phun thuốc bay sang'), ('duck', 'đàn vịt chạy đồng ăn mất nửa ô')]
VERDICT = [('pass', 'Đạt: vượt đối chứng từ 10% trở lên, đề nghị khảo nghiệm vụ sau'),
           ('fail', 'Chưa đạt: ghi đúng kết quả, lai lại vụ sau'),
           ('pretty', 'Bỏ thêm ô thấp nhất cho số đẹp rồi báo đạt'),
           ('rush', 'Báo đạt luôn cho nhà tài trợ vui')]
RATS = [('log', 'Ghi sổ mẫu hỏng, không tính vào kết quả, lấy túi dự phòng cùng lô, xin hộp kín và đặt bẫy'),
        ('refill', 'Lấy hạt túi khác đổ vào cho đủ cân'), ('weigh', 'Cân luôn phần còn lại, coi như đủ'),
        ('hide', 'Giấu túi gặm đi để khỏi bị viện trưởng la')]
BANK_STEPS = [('clean', 'Làm sạch, loại hạt lép'), ('dry', 'Sấy nhẹ tới độ ẩm chuẩn'), ('measure', 'Đo lại độ ẩm'),
              ('pack', 'Đóng túi kín, hút chân không'), ('label', 'Dán nhãn mã giống, ngày, độ ẩm'), ('cold', 'Cất kho lạnh')]
STORE = [('cold', 'Kho lạnh 5°C, khô ráo, kệ có mã'), ('room', 'Để ở góc phòng cho tiện lấy'),
         ('fridge', 'Chung tủ lạnh với hộp cơm của phòng'), ('sun', 'Phơi ngoài nắng cho hạt khỏe')]

# ---------------------------------------------------------------- 🍳 Công thức món
# id, name, the main ingredient, grams for 4 servings, ordered steps (one sensible order: DISH_AFTER says which others pass)
DISHES = [
    ('comga', 'Cơm gà xé phay', 'thịt gà', 300, [('wash', 'Làm sạch gà, chần sơ'), ('boil', 'Luộc gà lửa vừa'), ('rice', 'Nấu cơm bằng nước luộc gà'),
                                                  ('shred', 'Xé gà, trộn rau răm hành tây'), ('plate', 'Bày cơm, gà, chén nước mắm gừng')]),
    ('flan', 'Bánh flan sữa dừa', 'sữa dừa', 240, [('caramel', 'Thắng đường làm caramel'), ('mix', 'Đánh trứng với sữa dừa'), ('strain', 'Lọc hỗn hợp qua rây'),
                                                   ('steam', 'Hấp lửa nhỏ 25 phút'), ('chill', 'Để nguội, cho vào tủ mát')]),
    ('che', 'Chè đậu xanh nước cốt dừa', 'đậu xanh', 200, [('soak', 'Ngâm đậu ba tiếng'), ('cook', 'Nấu đậu tới mềm'), ('sugar', 'Thêm đường, khuấy tan'),
                                                          ('coco', 'Nấu nước cốt dừa riêng'), ('serve', 'Múc chè, chan nước cốt')]),
    ('nuocmam', 'Nước chấm chua ngọt', 'nước mắm', 120, [('sugar', 'Hòa tan đường với nước ấm'), ('lime', 'Vắt chanh'), ('fish', 'Thêm nước mắm từ từ'),
                                                         ('taste', 'Nếm, chỉnh lại'), ('garlic', 'Thả tỏi ớt băm sau cùng')]),
    ('banhmi', 'Bánh mì nướng mỡ hành', 'bột mì', 400, [('dough', 'Nhào bột'), ('rest', 'Ủ bột 45 phút'), ('shape', 'Chia, tạo hình'),
                                                         ('bake', 'Nướng 180°C'), ('top', 'Phết mỡ hành khi bánh còn nóng')]),
    ('canh', 'Canh bí đỏ tôm khô', 'bí đỏ', 500, [('prep', 'Gọt bí, cắt miếng'), ('shrimp', 'Ngâm tôm khô'), ('broth', 'Phi hành, xào tôm, đổ nước'),
                                                  ('pumpkin', 'Cho bí vào nấu mềm'), ('season', 'Nêm, rắc ngò')]),
]
# The recipe card of each dish (shown on the order step), and what must come before each step: every order that keeps
# these passes (cơm and xé gà both wait for the boiled chicken but not for each other, nước cốt dừa is cooked apart…).
DISH_CARD = {
    'comga': 'Thẻ công thức: gà làm sạch, chần sơ rồi mới luộc; cơm nấu bằng nước luộc gà; gà luộc xong mới xé; bày đĩa sau cùng.',
    'flan': 'Thẻ công thức: thắng caramel đổ đáy khuôn; trứng đánh với sữa dừa rồi lọc qua rây, đổ lên caramel rồi mới hấp; hấp xong để nguội, cho vào tủ mát.',
    'che': 'Thẻ công thức: đậu ngâm rồi mới nấu, đậu mềm mới thêm đường; nước cốt dừa nấu riêng, lúc nào cũng được; múc chè sau cùng.',
    'nuocmam': 'Thẻ công thức: hòa tan đường trước; rồi vắt chanh và thêm nước mắm; nếm, chỉnh lại; tỏi ớt thả sau cùng cho nổi.',
    'banhmi': 'Thẻ công thức: nhào bột, ủ 45 phút, chia và tạo hình, nướng 180°C; bánh vừa ra lò mới phết mỡ hành.',
    'canh': 'Thẻ công thức: tôm khô ngâm trước khi xào; phi hành, xào tôm, đổ nước làm nước dùng; bí gọt sẵn, nước dùng có rồi mới cho bí; nêm, rắc ngò sau cùng.',
}
DISH_AFTER = {
    'comga': dict(boil=('wash',), rice=('boil',), shred=('boil',), plate=('rice', 'shred')),
    'flan': dict(strain=('mix',), steam=('strain', 'caramel'), chill=('steam',)),
    'che': dict(cook=('soak',), sugar=('cook',), serve=('sugar', 'coco')),
    'nuocmam': dict(lime=('sugar',), fish=('sugar',), taste=('lime', 'fish'), garlic=('taste',)),
    'banhmi': dict(rest=('dough',), shape=('rest',), bake=('shape',), top=('bake',)),
    'canh': dict(broth=('shrimp',), pumpkin=('broth', 'prep'), season=('pumpkin',)),
}
# What goes into each dish (name, allergen tag): the first three always, two of the rest on a given day.
DISH_INGREDIENTS = {
    'comga': [('Thịt gà', ''), ('Gạo', ''), ('Rau răm', ''), ('Hành tây', ''), ('Gừng', ''), ('Nước mắm', ''), ('Đậu phộng rang', 'peanut'), ('Mè rang', 'sesame')],
    'flan': [('Trứng gà', 'egg'), ('Sữa dừa', ''), ('Đường', ''), ('Sữa tươi', 'milk'), ('Vani', ''), ('Cà phê', '')],
    'che': [('Đậu xanh', ''), ('Nước cốt dừa', ''), ('Đường', ''), ('Mè rang', 'sesame'), ('Đậu phộng rang', 'peanut'), ('Bột năng', ''), ('Muối', '')],
    'nuocmam': [('Nước mắm', ''), ('Đường', ''), ('Chanh', ''), ('Tỏi', ''), ('Ớt', ''), ('Đậu phộng rang', 'peanut'), ('Tôm khô giã', 'shrimp')],
    'banhmi': [('Bột mì', 'gluten'), ('Men nở', ''), ('Hành lá', ''), ('Dầu ăn', ''), ('Muối', ''), ('Trứng gà', 'egg'), ('Sữa tươi', 'milk')],
    'canh': [('Bí đỏ', ''), ('Tôm khô', 'shrimp'), ('Hành tím', ''), ('Ngò', ''), ('Muối', ''), ('Dầu ăn', '')],
}
DISH_CORE = 3
SERVINGS = (12, 20, 28, 32, 40, 60)
VARIABLE = [('one', 'Chỉ đổi một yếu tố (lượng đường), giữ nguyên mọi thứ khác'),
            ('all', 'Đổi cả đường, lửa và thời gian cho mau ra món ngon'),
            ('mood', 'Đổi tùy cảm hứng hôm đó'), ('boss', 'Nấu theo khẩu vị riêng của viện trưởng')]
LABBOOK = [('all', 'Ghi lượng, nhiệt độ, thời gian của từng lần thử, kể cả lần hỏng'), ('best', 'Chỉ ghi lần ngon nhất'),
           ('later', 'Để cuối tuần ghi một thể'), ('photo', 'Chụp ảnh món là đủ')]
CODING = [('blind', 'Mã ngẫu nhiên ba chữ số, không ghi tên công thức, xáo thứ tự đưa mẫu'),
          ('names', 'Ghi tên công thức lên chén cho người nếm dễ nhớ'),
          ('favourite', 'Đưa mẫu viện trưởng thích ra trước'), ('cook', 'Mời người nấu mẫu ngồi nếm cùng')]
# A taster whose scores do not count, and why
BIASED = [('Vừa ăn xong một tô mì cay cấp 7', 'chili'), ('Là người nấu ba mẫu này', 'cook'),
          ('Đang cảm cúm, nghẹt mũi', 'cold'), ('Ngó trộm được tên công thức trên khay', 'peek')]
TASTERS = ['Chị Nhàn', 'Anh Quý', 'Bé Su', 'Chú bảo vệ Toàn', 'Cô kế toán Hương', 'Bác Tư']
ALLERGENS = dict(peanut='Đậu phộng', milk='Sữa', egg='Trứng', shrimp='Tôm, cua (giáp xác)', sesame='Mè', gluten='Gluten (lúa mì)')
CLAIMS = [('true', 'Ghi đúng thành phần và chất gây dị ứng, không ghi công dụng chữa bệnh'),
          ('miracle', 'Ghi “thần dược giảm cân” cho bán chạy'), ('short', 'Bỏ dòng dị ứng cho nhãn gọn'),
          ('natural', 'Ghi “100% tự nhiên” dù có phẩm màu')]

# ---------------------------------------------------------------- 🛠️ Sáng chế
PARTS = dict(motor='Mô-tơ mini', fan='Cánh quạt nhựa', battery='Hộp pin', switch='Công tắc', led='Bóng LED', resistor='Điện trở',
             sensor='Cảm biến độ ẩm', pump='Bơm nước mini', pipe='Ống dẫn nước', buzzer='Còi chíp', button='Nút bấm',
             foam='Xốp cách nhiệt', lid='Nắp kín', thermo='Cảm biến nhiệt', clip='Kẹp gấp', solar='Tấm pin mặt trời mini',
             light='Cảm biến ánh sáng')
# id, name, required parts, what it does
GADGETS = [
    ('fan', 'Quạt cầm tay gấp gọn', ('motor', 'fan', 'battery', 'switch', 'clip'), 'thổi mát lúc chờ xe buýt'),
    ('lamp', 'Đèn học chống chói', ('led', 'resistor', 'battery', 'switch'), 'đọc sách không mỏi mắt'),
    ('water', 'Máy tưới cây tự động', ('sensor', 'pump', 'pipe', 'battery'), 'tưới chậu cây khi đất khô'),
    ('bell', 'Chuông cửa bấm vui', ('buzzer', 'button', 'battery'), 'kêu “ting tong” vui tai'),
    ('box', 'Hộp cơm giữ ấm', ('foam', 'lid', 'thermo', 'battery'), 'giữ cơm ấm tới giờ trưa'),
    ('solar', 'Đèn sân vườn năng lượng mặt trời', ('solar', 'led', 'battery', 'light'), 'tự sáng khi trời tối'),
]
BATTERY = [('safe', 'Pin sạc có mạch bảo vệ, đúng điện áp ghi trên mạch'), ('toy', 'Pin cũ tháo từ xe đồ chơi'),
           ('swollen', 'Pin hơi phồng nhưng còn sạc được'), ('double', 'Nối hai pin cho mạnh gấp đôi')]
TEST_ORDER = [('cold', 'Kiểm mạch khi chưa cấp điện'), ('low', 'Cấp điện thấp, đo dòng điện'), ('heat', 'Chạy 10 phút, đo nhiệt vỏ'),
              ('full', 'Chạy thử đầy tải, có người canh')]
# (supply volts, LED drop volts, current mA): the resistor (V − drop) / I is a whole number of ohms
OHM = [(5, 3, 20), (5, 2, 30), (9, 3, 20), (9, 3, 30), (12, 2, 20), (12, 3, 30), (5, 3, 10), (9, 2, 35)]
DROP_VERDICT = [('fix', 'Ghi đúng tỷ lệ hỏng, gia cố chỗ nứt, làm lô mới thử lại'),
                ('drop', 'Bỏ mẫu hỏng khỏi báo cáo cho gọn'), ('again', 'Thả lại mẫu hỏng tới khi nó chịu được'),
                ('floor', 'Ghi do sàn quá cứng, không phải lỗi thiết kế')]
FEATURES = [('fold', 'gập được làm ba'), ('magnet', 'đế nam châm hít vào cửa tủ'), ('timer', 'tự tắt sau 30 phút'),
            ('solar', 'sạc bằng nắng'), ('quiet', 'chạy êm dưới 30 dB'), ('water', 'chống nước khi mưa nhỏ'),
            ('voice', 'bật tắt bằng tiếng vỗ tay'), ('light', 'phát sáng trong bóng tối')]
NOTEBOOK_OPT = [('signed', 'Sổ thí nghiệm đánh số trang, ghi ngày, ký tên, có người chứng kiến ký'),
                ('loose', 'Ghi vào giấy nháp rời, nộp kèm sau'), ('chat', 'Chụp màn hình tin nhắn nhóm làm bằng chứng'),
                ('none', 'Không cần sổ, đã có mẫu thật')]
CREDIT = [('true', 'Ghi tác giả theo đóng góp thật trong sổ thí nghiệm; ghi anh Quý vào phần cảm ơn vì đã góp ý'),
          ('give', 'Để anh Quý đứng tên tác giả chính cho êm chuyện'),
          ('tear', 'Xé trang sổ có tên anh Quý đi'), ('fight', 'Cãi nhau tay đôi với anh Quý giữa phòng họp')]
FEE_BASE, FEE_PER, FEE_FREE = 30, 4, 10   # the filing fee: base, per claim past FEE_FREE

# ---------------------------------------------------------------- the council (day ≥ COUNCIL_DAY)
COUNCIL_ASKS = [
    ('GS. Bảo đòi bỏ hai số liệu thấp cho biểu đồ “đẹp hơn”.', 'Giữ nguyên số liệu, ghi rõ vì sao số thấp, đề xuất làm thêm lần lặp'),
    ('Hội đồng chê phông chữ, đòi in lại cả báo cáo trước 8 giờ sáng mai.', 'Sửa định dạng theo mẫu của viện, nội dung giữ nguyên, hẹn giờ nộp rõ ràng'),
    ('Một thành viên đòi trích dẫn thêm năm bài báo của chính ông ấy.', 'Chỉ trích dẫn bài liên quan thật, cảm ơn góp ý và giải thích lịch sự'),
    ('Hội đồng hỏi vặn vì sao chỉ làm ba lần lặp.', 'Trình bày đúng số lần đã làm và giới hạn của thí nghiệm, đề xuất làm thêm'),
    ('Ông Hưng ngồi dự, đòi ghi “đột phá thế giới” vào kết luận.', 'Kết luận đúng mức dữ liệu cho phép, không phóng đại'),
    ('Hội đồng không chịu xem bản đánh máy, đòi sổ thí nghiệm gốc.', 'Mang sổ gốc có ngày và chữ ký; bản đánh máy để kèm'),
    ('Anh Quý xin trình bày thay vì “nói hay hơn”, rồi nhận luôn là ý tưởng của mình.', 'Tự trình bày phần mình làm, ghi rõ ai góp phần nào'),
    ('Hội đồng đòi kết quả “như năm ngoái” dù năm nay thời tiết khác hẳn.', 'Báo cáo kết quả thật của năm nay, nêu rõ điều kiện khác năm ngoái'),
]
COUNCIL_WRONG = ['Sửa số cho vừa ý hội đồng', 'Cãi tay đôi với hội đồng', 'Ôm báo cáo bỏ về, mai tính', 'Đồng ý hết cho mau xong']

DESK = [
    dict(id='boom', title='Bình phản ứng phụt nắp', emoji='💥', npc=2, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='“Bụp!” Nắp bình đang đun ở bàn bên bật tung, bọt trào ra mặt bàn, mùi khét lan khắp phòng.',
         options=[dict(id='safe', label='Tắt nguồn nhiệt, mở tủ hút, mời mọi người ra ngoài, báo chị Nhàn, ghi sổ sự cố', hint='',
                       effects=dict(xp=6), good=True,
                       outcome='Không ai bị thương. Chị Nhàn tìm ra van xả bị tắc, dán biển “kiểm van trước khi đun”.'),
                  dict(id='wipe', label='Lấy giấy lau tay lau vội rồi đun tiếp cho kịp', hint='', effects=dict(review=[2, 'Bọt hóa chất dính vào găng, suýt bỏng tay.', 2]), good=False,
                       outcome='Giấy lau bén nhiệt bốc khói, cả phòng phải sơ tán thật.'),
                  dict(id='leave', label='Đóng cửa phòng, về sớm', hint='', effects=dict(patience=-2), good=None,
                       outcome='Sáng mai mặt bàn còn vệt cháy, chẳng ai biết chuyện gì đã xảy ra.')],
         default='leave'),
    dict(id='rats', title='Mẫu hạt bị chuột ăn', emoji='🐀', npc=2, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Ba túi mẫu hạt khảo nghiệm trong kho bị gặm thủng, hạt vương vãi khắp kệ. Chiều nay phải gửi mẫu cho hội đồng.',
         options=[dict(id='report', label='Ghi sổ mẫu hỏng, lấy túi dự phòng cùng lô, chuyển mẫu sang hộp kín, báo đặt bẫy', hint='',
                       effects=dict(xp=6), good=True,
                       outcome='May còn túi dự phòng cùng lô. Hội đồng khen kho mẫu có dự phòng và sổ ghi rõ ràng.'),
                  dict(id='mix', label='Hốt hạt dưới kệ bỏ lại vào túi cho đủ cân', hint='',
                       effects=dict(review=[2, 'Mẫu gửi hội đồng lẫn hạt lạ, phải làm lại cả đợt.', 4]), good=False,
                       outcome='Hội đồng phát hiện hạt lẫn giống khác, cả đợt khảo nghiệm phải làm lại.'),
                  dict(id='later', label='Để mai tính, giờ đang bận', hint='', effects=dict(patience=-2), good=None,
                       outcome='Đêm đó chuột gặm thêm hai túi nữa.')],
         default='later'),
    dict(id='council', title='Hội đồng duyệt khó tính', emoji='🧐', npc=4, min_day=3, tone='tense', at='between', weight=3, mods=None,
         text='GS. Bảo gửi lại đề cương với 47 ghi chú bút đỏ, trong đó có “vì sao lề trái 2 cm mà không phải 2,5 cm?”.',
         options=[dict(id='table', label='Lập bảng trả lời từng ghi chú, sửa cái hợp lý, giải thích lịch sự cái chưa hợp lý', hint='',
                       effects=dict(xp=7, review=[5, 'Bảng trả lời ghi chú rõ ràng, có lý có tình.', 4]), good=True,
                       outcome='GS. Bảo gạch 45 ghi chú, giữ lại 2 cái về lề giấy. Đề cương được thông qua.'),
                  dict(id='all', label='Sửa theo hết, kể cả chỗ làm sai thí nghiệm', hint='', effects=dict(review=[3, 'Sửa theo hết mà không hỏi lại, thí nghiệm lệch mục tiêu.', 0]), good=False,
                       outcome='Đề cương thông qua nhưng thí nghiệm không còn trả lời được câu hỏi ban đầu.'),
                  dict(id='ignore', label='Nộp lại y nguyên, coi như chưa đọc', hint='', effects=dict(patience=-2), good=None,
                       outcome='Hội đồng hẹn họp lại tháng sau.')],
         default='ignore'),
    dict(id='sponsor', title='Nhà tài trợ đòi kết quả sớm', emoji='💼', npc=3, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Ông Hưng gọi: “Tuần sau công ty ra mắt sản phẩm, viện gửi trước kết quả ‘đạt’ cho tôi in tờ rơi. Số liệu đủ sau cũng được.”',
         options=[dict(id='honest', label='Gửi kết quả tạm có ghi rõ “chưa đủ lần lặp”, hẹn ngày có kết luận chính thức', hint='',
                       effects=dict(xp=7), good=True,
                       outcome='Ông Hưng lầm bầm nhưng in tờ rơi ghi “đang khảo nghiệm”. Hai tuần sau kết quả thật vẫn đạt, ông còn mừng hơn.'),
                  dict(id='fake', label='Gửi luôn chữ “đạt” cho ông vui', hint='',
                       luck=dict(p=0.3, win=dict(effects=dict(xp=1), outcome='May mà kết quả thật cũng đạt, nhưng viện trưởng biết chuyện và nhắc nhở.', good=False),
                                 lose=dict(effects=dict(review=[1, 'Tờ rơi ghi “đạt” trong khi khảo nghiệm thất bại. Viện mất uy tín.', 0]),
                                           outcome='Kết quả thật không đạt. Tờ rơi phải thu hồi, viện phải đính chính.', good=False)),
                       effects={}),
                  dict(id='silent', label='Không nghe máy nữa', hint='', effects=dict(patience=-2), good=None,
                       outcome='Ông Hưng gọi thẳng cho viện trưởng.')],
         default='silent'),
    dict(id='credit', title='Đồng nghiệp nhận vơ công', emoji='🦹', npc=1, min_day=3, tone='tense', at='between', weight=3, mods=None,
         text='Bản tin của viện đăng ảnh anh Quý cầm khay mạ của bạn, chú thích: “Anh Quý và giống lúa mới do anh lai tạo”.',
         options=[dict(id='book', label='Mang sổ thí nghiệm có ngày, chữ ký gặp viện trưởng, xin đính chính lịch sự', hint='',
                       effects=dict(xp=7, review=[5, 'Sổ thí nghiệm rõ ràng từng ngày, đính chính đúng người đúng việc.', 0]), good=True,
                       outcome='Bản tin đính chính. Anh Quý ngượng, hứa từ nay chỉ đứng cạnh khay mạ của mình.'),
                  dict(id='post', label='Lên nhóm chat của viện chửi thẳng mặt', hint='', effects=dict(review=[2, 'Cãi nhau trên nhóm chung, cả viện ngại.', 0]), good=False,
                       outcome='Nhóm chat ồn ào ba ngày, chẳng ai nhớ ai lai giống lúa.'),
                  dict(id='swallow', label='Thôi kệ, cho êm chuyện', hint='', effects=dict(patience=-2), good=None,
                       outcome='Lần sau anh Quý lại đứng cạnh khay của bạn khi có người chụp ảnh.')],
         default='swallow'),
    dict(id='blackout', title='Cúp điện, tủ ấm tắt', emoji='🔌', npc=2, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Cả dãy nhà cúp điện. Tủ ấm ươm mầm đang ở 28°C, nhiệt độ bắt đầu tụt.',
         options=[dict(id='ups', label='Chuyển tủ ấm sang ổ lưu điện, ghi giờ cúp và nhiệt độ mỗi 15 phút vào sổ', hint='',
                       effects=dict(xp=6), good=True,
                       outcome='Bộ lưu điện giữ được hai tiếng, đủ tới lúc có điện lại. Sổ ghi đủ để hội đồng tin số liệu.'),
                  dict(id='gas', label='Mượn bếp ga mini đặt cạnh tủ cho ấm', hint='', effects=dict(review=[1, 'Đặt bếp ga cạnh tủ ươm, suýt cháy phòng.', 2]), good=False,
                       outcome='Khói đen bám đầy cửa kính tủ, khay mạ héo một góc.'),
                  dict(id='wait', label='Ngồi chờ có điện', hint='', effects=dict(patience=-2), good=None,
                       outcome='Có điện lại sau ba tiếng, một nửa số khay chậm nảy mầm.')],
         default='wait'),
    dict(id='pretty', title='Sếp gợi ý “làm đẹp” số liệu', emoji='📈', npc=1, min_day=4, tone='tense', at='between', weight=2, mods=None,
         text='Anh Quý thì thầm: “Lệch có 3% thôi mà, sửa nhẹ cột đó thành 10% là qua hội đồng ngay. Ai biết đâu?”',
         options=[dict(id='no', label='Giữ số thật, viết rõ giới hạn, đề nghị thêm một lần lặp', hint='',
                       effects=dict(xp=7), good=True,
                       outcome='Lần lặp thêm cho kết quả 11%. Số thật mà vẫn qua, không ai phải lo.'),
                  dict(id='yes', label='Sửa cho qua', hint='', effects=dict(review=[1, 'Số liệu bị sửa, hội đồng phát hiện khi đối chiếu sổ gốc.', 4]), good=False,
                       outcome='Hội đồng đối chiếu sổ gốc, đề tài bị đình chỉ một tháng.'),
                  dict(id='shrug', label='Không trả lời, làm tiếp', hint='', effects=dict(patience=-1), good=None,
                       outcome='Anh Quý tự sửa trong file chung. Bạn phải mất buổi chiều khôi phục bản gốc.')],
         default='shrug'),
    dict(id='reviewer', title='Phản biện đòi trích dẫn bài của mình', emoji='📝', npc=4, min_day=4, tone='gentle', at='between', weight=2, mods=None,
         text='Thư phản biện: “Đề nghị tác giả trích dẫn thêm sáu bài báo” — cả sáu bài đều của người phản biện, có bài về nuôi cá.',
         options=[dict(id='relevant', label='Trích một bài thật sự liên quan, giải thích lịch sự vì sao năm bài kia không hợp', hint='',
                       effects=dict(xp=5), good=True,
                       outcome='Ban biên tập đồng ý với bạn. Bài được nhận đăng.'),
                  dict(id='all', label='Trích hết sáu bài cho êm', hint='', effects=dict(review=[3, 'Bài về giống lúa mà trích dẫn nuôi cá.', 4]), good=False,
                       outcome='Người đọc thắc mắc vì sao bài về giống lúa lại trích dẫn sáu bài nuôi cá.'),
                  dict(id='angry', label='Viết thư mắng phản biện', hint='', effects=dict(patience=-2), good=None,
                       outcome='Bài bị treo thêm hai tháng.')],
         default='angry'),
    dict(id='label', title='Thực tập sinh dán nhầm nhãn', emoji='🏷️', npc=5, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Bé Su hớn hở: “Em dán nhãn xong cả 40 ống rồi!” — nhãn ống 12 tới 20 trùng mã với ống 1 tới 9.',
         options=[dict(id='check', label='Cùng bé Su đối chiếu sổ, dán lại nhãn mới, ghi chú việc sửa nhãn', hint='',
                       effects=dict(xp=6), good=True,
                       outcome='Đối chiếu xong trong nửa tiếng. Bé Su học được cách đánh mã không trùng.'),
                  dict(id='guess', label='Đoán đại theo màu nước trong ống', hint='', effects=dict(review=[2, 'Mẫu bị nhầm nhãn, kết quả lộn xộn.', 0]), good=False,
                       outcome='Ống số 13 hóa ra là nước rửa tay. Kết quả cả đợt vô nghĩa.'),
                  dict(id='scold', label='La bé Su một trận rồi để đó', hint='', effects=dict(patience=-2), good=None,
                       outcome='Bé Su khóc, nhãn vẫn sai.')],
         default='scold'),
    dict(id='cat', title='Mèo của viện ngủ trên khay mẫu', emoji='🐈', npc=2, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Con mèo Mướp chui qua cửa sổ, nằm ngủ ngon lành trên khay mạ thí nghiệm số 3.',
         options=[dict(id='move', label='Bế Mướp ra, ghi khay 3 bị ảnh hưởng, đóng cửa lưới cho phòng mẫu', hint='',
                       effects=dict(xp=4), good=True,
                       outcome='Khay 3 được ghi chú riêng, không tính vào kết quả. Mướp được cho một chỗ nằm ở phòng bảo vệ.'),
                  dict(id='count', label='Kệ, cứ tính khay 3 như thường', hint='', effects=dict(review=[3, 'Khay mạ bị đè nát mà vẫn tính vào kết quả.', 4]), good=False,
                       outcome='Khay 3 kéo số trung bình xuống, kết luận sai cả đợt.'),
                  dict(id='photo', label='Chụp ảnh đăng mạng trước đã', hint='', effects=dict(patience=-1), good=None,
                       outcome='Ảnh được nghìn lượt thích, khay mạ thì bẹp.')],
         default='photo'),
    dict(id='receipts', title='Quỹ đòi báo cáo chi tiêu gấp', emoji='🧾', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Phòng kế toán cần báo cáo chi tiêu đề tài trước 5 giờ chiều. Thiếu hai hóa đơn mua phân bón.',
         options=[dict(id='ask', label='Liên hệ cửa hàng xin hóa đơn bản sao, ghi rõ khoản còn thiếu, không tự “bù” khoản khác', hint='',
                       effects=dict(xp=6), good=True,
                       outcome='Cửa hàng gửi bản sao kịp 4 giờ rưỡi. Báo cáo khớp từng đồng.'),
                  dict(id='make', label='Tự viết một tờ hóa đơn cho đủ', hint='', effects=dict(review=[1, 'Hóa đơn tự viết, kiểm toán phát hiện ngay.', 0]), good=False,
                       outcome='Kiểm toán gọi lên làm việc ba buổi.'),
                  dict(id='late', label='Nộp trễ, mai bổ sung', hint='', effects=dict(patience=-2), good=None,
                       outcome='Đề tài bị nhắc tên trong cuộc họp giao ban.')],
         default='late'),
    dict(id='press', title='Phóng viên muốn giật tít “thần dược”', emoji='📰', npc=3, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Một phóng viên xin phỏng vấn, đã đặt sẵn tít: “Viện Sông Mây tìm ra giống ớt chữa bách bệnh”.',
         options=[dict(id='facts', label='Nhận phỏng vấn, nói đúng kết quả đã có, đề nghị sửa tít', hint='',
                       effects=dict(xp=6, review=[5, 'Bài báo viết đúng, dễ hiểu, không phóng đại.', 3]), good=True,
                       outcome='Tít mới: “Giống ớt chịu hạn đang được khảo nghiệm ở Sông Mây”. Ít giật gân hơn mà ai cũng tin.'),
                  dict(id='hype', label='Hùa theo cho viện nổi tiếng', hint='', effects=dict(review=[1, 'Báo đăng “chữa bách bệnh”, viện phải đính chính.', 0]), good=False,
                       outcome='Người dân kéo tới xin ớt chữa đau lưng. Viện trưởng phải lên tiếng đính chính.'),
                  dict(id='hide', label='Trốn trong kho mẫu', hint='', effects=dict(patience=-1), good=None,
                       outcome='Bài báo vẫn đăng, dựa theo lời kể của anh Quý.')],
         default='hide'),
    dict(id='taste_boss', title='Viện trưởng đòi món phải cay hơn', emoji='🌶️', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Cô Diệu Linh nếm mẫu nước chấm: “Nhạt! Thêm ớt gấp ba.” Khách hàng đặt công thức là trường mầm non.',
         options=[dict(id='client', label='Giữ độ cay theo yêu cầu của khách, làm riêng một chén cay cho cô viện trưởng', hint='',
                       effects=dict(xp=5), good=True,
                       outcome='Trường mầm non nhận đúng công thức không cay. Cô viện trưởng ăn chén riêng, gật gù.'),
                  dict(id='triple', label='Thêm ớt gấp ba cho cả mẻ', hint='', effects=dict(review=[2, 'Nước chấm cho trường mầm non mà cay xé lưỡi.', 0]), good=False,
                       outcome='Các bé khóc ré, trường trả lại cả mẻ.'),
                  dict(id='nod', label='Gật đầu cho qua, không làm gì', hint='', effects=dict(patience=-1), good=None,
                       outcome='Cô viện trưởng hỏi lại vào chiều hôm sau.')],
         default='nod'),
    dict(id='deadline', title='Hạn nộp đề tài dời lên sớm', emoji='⏰', npc=0, min_day=4, tone='tense', at='between', weight=2, mods=None,
         text='Thông báo mới: hạn nộp hồ sơ đề tài dời lên sớm hai ngày, “vì sở muốn họp trước kỳ nghỉ”.',
         options=[dict(id='plan', label='Chia việc theo ngày, nộp phần đã xong, ghi rõ phần đang làm và ngày bổ sung', hint='',
                       effects=dict(xp=6), good=True,
                       outcome='Hồ sơ nộp đúng hạn mới, phần bổ sung được chấp nhận ghi kèm.'),
                  dict(id='copy', label='Chép phần kết quả của đề tài năm ngoái vào cho đủ', hint='', effects=dict(review=[1, 'Hồ sơ chép kết quả năm ngoái, bị trả về.', 0]), good=False,
                       outcome='Hồ sơ bị trả về với dòng chữ đỏ “kết quả trùng đề tài năm 2025”.'),
                  dict(id='panic', label='Thức trắng làm lại từ đầu', hint='', effects=dict(patience=-2), good=None,
                       outcome='Hồ sơ nộp kịp nhưng sai ba chỗ vì buồn ngủ.')],
         default='panic'),
]

MILESTONES = [
    dict(id='junior', label='Nghiên cứu viên tập sự', jobs=15, days=5, tracks=1),
    dict(id='three', label='Thạo cả ba hướng', jobs=60, days=20, tracks=3),
    dict(id='lead', label='Chủ nhiệm đề tài Sông Mây', jobs=160, days=40, tracks=3),
]
NOTEBOOK = [
    'Mọi quy định, số liệu và kết quả ở Viện nghiên cứu Sông Mây là quy tắc hư cấu của trò chơi.',
    'Đầu ca: mặc áo blouse → đeo kính bảo hộ → đeo găng → bật tủ hút, kiểm quạt → ghi giờ vào sổ nhật ký. Cô Diệu Linh có thể đi kiểm tra an toàn bất chợt.',
    'Cuối ca: cất mẫu đúng ngăn đúng nhãn → khóa tủ hóa chất → rửa dụng cụ → ghi sổ; rồi tắt mọi thiết bị đang bật (bếp từ, máy khuấy, đèn UV, mỏ hàn, máy sấy hạt, lò nướng). Tủ ấm ươm mầm và tủ lạnh mẫu luôn để chạy.',
    f'Quên kiểm tra thiết bị cuối ca: đêm đó có thể hỏng mẫu (khoảng {round(NIGHT_CHANCE * 100)}% số lần). Tiền đền bù trừ vào ví: {NIGHT_PCT}% lương ca, ít nhất {NIGHT_MIN} xu, nhiều nhất {NIGHT_CAP} xu, không bao giờ quá số tiền đang có.',
    '🌱 Lai tạo: chọn đúng hai dòng bố mẹ mang hai đặc tính cần lai. Số hạt gieo = số cây con cần × 100 ÷ tỷ lệ nảy mầm, làm tròn lên. Khay nào cũng ghi mã tổ hợp, ngày gieo, bố mẹ, người làm; luôn có khay đối chứng giống cũ cùng điều kiện.',
    '🌾 Khảo nghiệm: ô bị hỏng vì lý do ngoài thí nghiệm (ngập, trâu giẫm, thuốc bay sang, vịt ăn) thì bỏ ra, ghi rõ lý do; năng suất trung bình = tổng các ô còn lại ÷ số ô. Đạt khi trung bình từ 110% năng suất đối chứng trở lên.',
    '🐀 Mẫu bị chuột gặm: ghi sổ mẫu hỏng, không tính, lấy túi dự phòng cùng lô; không bao giờ đổ hạt túi khác vào cho đủ cân.',
    '🫙 Ngân hàng hạt giống: làm sạch → sấy → đo lại độ ẩm → đóng túi kín → dán nhãn → cất kho lạnh 5°C. Giờ sấy = (độ ẩm hiện tại − độ ẩm chuẩn) ÷ số phần trăm máy rút được mỗi giờ. Tỷ lệ nảy mầm = số cây mọc × 100 ÷ số hạt ươm thử.',
    '⚖️ Chuẩn hóa công thức: lượng nguyên liệu = lượng cho 4 suất × số suất ÷ 4. Mỗi lần thử chỉ đổi một yếu tố; ghi đủ lượng, nhiệt độ, thời gian của mọi lần, kể cả lần hỏng.',
    '🥄 Hội đồng nếm: mẫu mã hóa ba chữ số, không ghi tên, xáo thứ tự. Bỏ điểm của người nếm không khách quan (vừa ăn cay, người nấu, đang cảm, đã thấy tên). Mẫu thắng là mẫu có tổng điểm cao nhất của những người còn lại.',
    '🏷️ Giá vốn mỗi suất = tổng tiền nguyên liệu ÷ số suất. Giá bán: mức thấp nhất trong bảng mà vẫn lời ít nhất bằng tỷ lệ yêu cầu. Nhãn ghi đủ mọi chất gây dị ứng có trong món, không ghi công dụng chữa bệnh.',
    '🔧 Mẫu thử: lấy đủ linh kiện của thiết kế, không lấy thừa; chỉ dùng pin có mạch bảo vệ, đúng điện áp. Thử theo thứ tự: kiểm mạch nguội → cấp điện thấp đo dòng → chạy 10 phút đo nhiệt → chạy đầy tải có người canh. Điện trở cho đèn LED = (điện áp nguồn − điện áp đèn) ÷ dòng điện (A).',
    '📦 Thử độ bền: mẫu nào chịu được thấp hơn độ cao yêu cầu là hỏng. Tỷ lệ hỏng = số mẫu hỏng × 100 ÷ số mẫu. Ghi đúng, gia cố rồi thử lô mới; không bỏ mẫu hỏng khỏi báo cáo.',
    f'📜 Hồ sơ sáng chế: điểm mới là đặc điểm chưa có ở thiết bị nào đã biết. Phí nộp = {FEE_BASE} xu + {FEE_PER} xu cho mỗi điểm yêu cầu bảo hộ vượt quá {FEE_FREE}. Sổ thí nghiệm đánh số trang, có ngày, chữ ký và người chứng kiến. Tác giả ghi theo đóng góp thật.',
    f'🧐 Từ ngày nghề {COUNCIL_DAY}, việc nào cũng kết thúc trước hội đồng: giữ số liệu thật, sửa hình thức khi hợp lý, giải thích lịch sự, không phóng đại.',
    '📬 Đơn của người chơi khác (Phố dịch vụ): nhận đơn, làm ba bước nghiên cứu theo yêu cầu, giao kết quả. Hiệu ứng có giới hạn rõ ràng, ghi ngay trên đơn.',
    'Lương ca trả theo hợp đồng khi khép ca; thưởng chất lượng nhỏ theo từng việc, sai bước thì sửa tại chỗ và thưởng giảm.',
]
