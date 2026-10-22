"""🚗 Đại lý xe Phố Mây: the words and tables of the motorbike and car showroom (game/careers/car_dealer.py).

Every table is static: a job is a pure function of (day, slot), so validate_state can rebuild it. Player #472 asked for
"làm chủ bán xe hơi, xe máy"; the owner: "nghề mới thì làm đi". The models are the same ones the players buy for
themselves in 🚗 Xe & phương tiện (game/garage.py), at the showroom's own list price; the showroom never sells to a
player and never lends: a customer's trả góp is the NPC bank's, under the game's bank rules (game/bank.py).
"""
from __future__ import annotations

PLACE = 'Đại lý xe Phố Mây'
OWNER = 'Anh Quân'

PEOPLE = [
    ('Anh Quân', 'Chủ đại lý', 'Mười lăm năm bán xe, nhớ thông số từng đời xe. Câu cửa miệng: “Bán chiếc xe, giữ người khách.”', 'warm'),
    ('Chị Mai', 'Kế toán, lo giấy tờ', 'Giữ sổ sách và hồ sơ đăng ký xe, không để sót một tờ.', 'picky'),
    ('Tú', 'Kỹ thuật viên', 'Kiểm xe mới, bảo dưỡng lần đầu, lau xe bóng loáng trước khi giao.', 'genz'),
    ('Cô Hạnh', 'Giáo viên tiểu học', 'Cần chiếc xe nhẹ, cốp rộng để chở tập vở, ngại xe nặng.', 'picky'),
    ('Anh Dũng', 'Shipper', 'Chạy cả ngày, cần xe bền, ít hao xăng, dễ sửa.', 'warm'),
    ('Bé Na', 'Sinh viên năm nhất', 'Chưa có bằng lái xe máy, cần xe đi học gần.', 'genz'),
    ('Chú Bảy', 'Về hưu', 'Muốn chiếc ô tô nhỏ chở vợ đi chợ, đi chùa, rất kỹ tính.', 'sour'),
    ('Chị Vy', 'Chủ chuỗi tiệm bánh', 'Cần xe rộng chở cả nhà và hàng, hay đi tỉnh.', 'picky'),
    ('Người mặc áo khoác dày', 'Khách vãng lai', 'Muốn bán gấp chiếc xe, nói chuyện lảng tránh.', 'quiet'),
]
MENTOR = 0
CLERK = 1
TECH = 2
CUSTOMERS = (3, 4, 5, 6, 7)
STRANGER = 8

WRONG_COST = 8
QUALITY_FLOOR = 40
MILESTONES = (3, 6, 12, 25)   # days: cars and after-sales, trả góp and doubtful sellers, two demands, the dearest cars
MASTER = (100, 30)
EXPERT = (180, 45)

# ---------------------------------------------------------------- the showroom (inventory items; car_dealer.ITEMS)
# vid: the garage model (game/garage.py VEHICLES) this is; price: the list price (xu, VAT in); cost_pct: what the
# maker charges the dealer (% of the list price); kind: xm (motorbike, trước bạ 2 %, biển 5 xu) or ot (car, 10 %, 20 xu).
MODELS = {
    'dx_xe_dien': dict(vid='xe_dap_dien', name='Xe đạp điện', emoji='🚲', kind='xm', price=330, cost_pct=95, start=1, day=1,
                       spec=('Sạc đầy chạy được bao xa?', 'Hãng công bố 60 km mỗi lần sạc, chở nặng hoặc lên dốc thì ít hơn',
                             ('Chạy cả tuần không cần sạc', '200 km, cứ yên tâm'))),
    'dx_xe_so': dict(vid='xe_so', name='Xe số Cub', emoji='🏍️', kind='xm', price=660, cost_pct=95, start=1, day=1,
                     spec=('Xe này hao xăng cỡ nào?', 'Hãng công bố 1,6 lít mỗi 100 km; chạy phố đông, chở nặng thì hao hơn',
                           ('Nửa lít chạy cả tuần', 'Xe số không hao xăng đâu'))),
    'dx_xe_ga': dict(vid='xe_ga', name='Xe tay ga cổ điển', emoji='🛵', kind='xm', price=1100, cost_pct=95, start=1, day=1,
                     spec=('Cốp xe để vừa mũ bảo hiểm không?', 'Cốp 15 lít: vừa một mũ nửa đầu và áo mưa, mũ cả đầu thì không vừa',
                           ('Vừa hai mũ cả đầu', 'Cốp để gì cũng vừa'))),
    'dx_oto_mini': dict(vid='o_to_mini', name='Ô tô mini 4 chỗ', emoji='🚗', kind='ot', price=3300, cost_pct=97, start=0, day=3, unlock=2,
                        spec=('Xe có túi khí không?', 'Có hai túi khí phía trước; hàng ghế sau không có túi khí',
                              ('Có túi khí khắp xe', 'Túi khí làm gì, xe nhỏ chạy chậm mà'))),
    'dx_oto_suv': dict(vid='o_to_suv', name='SUV 7 chỗ', emoji='🚙', kind='ot', price=7250, cost_pct=97, start=0, day=6, unlock=3,
                       spec=('Hàng ghế thứ ba ngồi người lớn được không?', 'Hàng ba hợp cho trẻ em hoặc người lớn đi gần; đi xa người lớn sẽ chật',
                             ('Rộng như hàng hai', 'Ngồi năm người lớn hàng ba vẫn được'))),
    'dx_mui_tran': dict(vid='mui_tran', name='Xe mui trần cổ', emoji='🏎️', kind='ot', price=13200, cost_pct=98, start=0, day=10, unlock=4,
                        spec=('Mui xe có chống mưa tốt không?', 'Mui vải đóng kín chống mưa thường; mưa to lâu nên đỗ trong nhà, mui cần bảo dưỡng',
                              ('Mui vải mà kín hơn mui thép', 'Để ngoài mưa cả tháng cũng không sao'))),
}
# Accessories (inventory items): price key in SPEC prices (tunable 75–125 %), cost to the dealer.
ACCESSORIES = {
    'dx_mu': dict(name='Mũ bảo hiểm nửa đầu', emoji='⛑️', cost=6, base=10, start=6, unit='chiếc'),
    'dx_khoa': dict(name='Khóa đĩa chống trộm', emoji='🔒', cost=5, base=9, start=4, unit='chiếc'),
    'dx_tham': dict(name='Bộ thảm lót sàn ô tô', emoji='🧽', cost=12, base=20, start=2, unit='bộ'),
    'dx_camera': dict(name='Camera hành trình', emoji='📹', cost=30, base=45, start=1, unit='chiếc'),
}
FEES = {   # the dealer's service fees (SPEC prices): what the price board names them
    'dv_dang_ky_xm': dict(name='Phí dịch vụ đăng ký xe máy', emoji='🧾', base=15),
    'dv_dang_ky_ot': dict(name='Phí dịch vụ đăng ký ô tô', emoji='🧾', base=40),
    'bao_duong': dict(name='Phí bảo dưỡng lần đầu', emoji='🔧', base=20),
}
TAX = {'xm': (2, 5), 'ot': (10, 20)}   # lệ phí trước bạ (% of the list price, rounded down) and the plate fee (xu)

# What a customer needs, by model: (customer index, what they say). The right model is the one that fits.
NEEDS = {
    'dx_xe_dien': ((5, 'Em chưa có bằng lái xe máy, nhà cách trường 3 km. Ngân sách tầm 350 xu.'),
                   (3, 'Cô cần xe thật nhẹ, không cần bằng, chỉ đi chợ gần nhà. Dưới 400 xu thôi.')),
    'dx_xe_so': ((4, 'Anh chạy giao hàng cả ngày, cần xe bền, ít hao xăng, sửa ở đâu cũng được. Tầm 700 xu.'),
                 (6, 'Chú cần chiếc xe máy bền, rẻ, để thằng cháu chạy đi làm. Tầm 700 xu.')),
    'dx_xe_ga': ((3, 'Cô có bằng A1, muốn xe tay ga cốp rộng chở tập vở, không phải sang số. Tầm 1.100 xu.'),
                 (7, 'Chị cần xe tay ga đi phố cho gọn, có cốp để áo mưa. Dưới 1.200 xu.')),
    'dx_oto_mini': ((6, 'Chú có bằng B, cần ô tô nhỏ chở bà nhà đi chợ, hẻm nhà hẹp. Tầm 3.500 xu.'),
                    (3, 'Cô muốn chiếc ô tô nhỏ dễ đỗ, đi trong phố là chính. Dưới 3.500 xu.')),
    'dx_oto_suv': ((7, 'Nhà chị bảy người, hay về quê và chở hàng, cần gầm cao. Tầm 7.500 xu.'),),
    'dx_mui_tran': ((7, 'Chị muốn một chiếc xe thật nổi để chụp ảnh cưới và quảng cáo tiệm bánh. Tầm 13.500 xu.'),),
}

# ---------------------------------------------------------------- the sale (ban)
DRIVE_GOOD = ('Xem bằng lái đúng hạng của khách', 'Nhân viên ngồi cùng xe hoặc chạy kèm', 'Chạy cung đường cố định quanh phố')
DRIVE_BAD = ('Đưa chìa cho khách chạy một mình về nhà thử', 'Chưa có bằng cũng cho chạy thử một vòng')
PAPERS_GOOD = ('Hóa đơn bán xe', 'Phiếu xuất xưởng của hãng', 'Tờ khai đăng ký xe', 'CCCD của người đứng tên')
PAPERS_BAD = ('Giấy tờ photo của người khác', 'Biển số làm sẵn mua ngoài chợ', 'Hóa đơn ghi giá thấp cho bớt trước bạ')
PLATE = ('Khách muốn biển đẹp toàn số 9: “Lo giùm anh, tốn bao nhiêu cũng được.”',
         'Nói thật: biển bấm ngẫu nhiên ở công an; biển đẹp chỉ có qua 🔨 đấu giá biển số',
         ('Hứa lo được biển đẹp, thu thêm 50 xu', 'Mua biển số đẹp làm sẵn gắn tạm'))
HANDOVER_GOOD = ('Kiểm lại xe trước mặt khách', 'Hướng dẫn sử dụng, hẹn lịch bảo dưỡng lần đầu', 'Giao đủ chìa, sổ bảo hành, hóa đơn')
HANDOVER_BAD = ('Giao xe chưa lau, bình xăng cạn', 'Hứa bảo hành trọn đời cho khách vui')
LOAN_OK = 'Duyệt: khoản góp mỗi tuần không quá 40% thu nhập'
LOAN_NO = 'Chưa duyệt: khoản góp vượt 40% thu nhập; mời trả trước nhiều hơn hoặc chọn xe rẻ hơn'
LOAN_WRONG = ('Duyệt luôn, khách quen mà', 'Khuyên khách khai thu nhập cao lên cho lọt')

# ---------------------------------------------------------------- the morning (nhận lô xe, PDI)
PDI = [('ngoai', 'Đi một vòng kiểm sơn, trầy xước, gương, đèn'), ('dau', 'Kiểm nhớt, nước làm mát, áp suất lốp'),
       ('dien', 'Bật thử đèn, còi, xi-nhan, đồng hồ'), ('chay', 'Chạy thử một vòng bãi, thử phanh'), ('ky', 'Ký phiếu kiểm xe, dán tem đã kiểm')]
LISTING_GOOD = ('Giá niêm yết đã gồm thuế VAT', 'Ghi rõ lệ phí trước bạ và biển số tính riêng', 'Mức hao xăng ghi theo công bố của hãng')
LISTING_BAD = ('Ghi “rẻ nhất phố” không có căn cứ', 'Giấu phí trước bạ cho giá trông thấp')

# ---------------------------------------------------------------- trade-ins (thu cũ)
USED = {   # (the model's new price, years used range, possible repairs (what, xu))
    'xe_so': ('Xe số Cub', 660, (1, 6)),
    'xe_ga': ('Xe tay ga cổ điển', 1100, (1, 5)),
    'xe_dien': ('Xe đạp điện', 330, (1, 4)),
    'oto_mini': ('Ô tô mini 4 chỗ', 3300, (2, 6)),
}
REPAIRS = (('Lốp sau mòn hết gai', 12), ('Ắc quy yếu', 8), ('Vỏ nhựa trầy, nứt một mảnh', 15), ('Phanh trước mòn tới giới hạn', 6),
           ('Đèn pha mờ, chóa đèn ố', 5), ('Sên chùng, nhông mòn', 10))
DEPRECIATE = (10, 30)   # % a year off the new price, down to at least this % of it
YARD_PCT = 106          # the used-vehicle yard pays the dealer this % of the trade-in price, the same day
TRADE_OK = ('Khách đưa giấy đăng ký xe đúng tên, CCCD khớp; số khung, số máy trên xe khớp giấy.',
            'Khớp: chụp số khung, số máy, làm giấy mua bán có chữ ký rồi định giá',
            ('Khỏi xem giấy, xe đẹp là được', 'Định giá trước, giấy tờ tính sau'))
TRADE_BAD = (
    ('Số khung trên xe bị đục sửa, không khớp giấy đăng ký. Khách nói “xe mua lại của người quen”.',
     'Không mua: số khung không khớp giấy; ghi lại đặc điểm xe, báo công an khu vực',
     ('Mua giá rẻ vì có rủi ro', 'Mua rồi làm lại giấy sau', 'Đục lại số khung cho khớp')),
    ('Giấy đăng ký đứng tên người khác, khách không có giấy ủy quyền, muốn bán gấp lấy tiền mặt.',
     'Không mua: không có giấy ủy quyền của chủ xe; mời chủ xe ra cùng',
     ('Mua vì có giấy đăng ký là được', 'Mua giá nửa cho chắc ăn')),
)
TRADE_LEDGER_GOOD = ('Giấy mua bán có chữ ký hai bên', 'Bản sao CCCD người bán', 'Ảnh số khung, số máy', 'Giấy đăng ký gốc')
TRADE_LEDGER_BAD = ('Ghi giá thu thấp hơn số tiền đã trả', 'Bỏ trống tên người bán')

# ---------------------------------------------------------------- after-sales (hậu mãi)
WARRANTY = (
    ('Xe mua 5 tháng, chạy 4.000 km, đèn pha chập chờn. Tem bảo hành còn nguyên, không độ chế gì.',
     'Bảo hành miễn phí: lỗi linh kiện trong hạn 3 năm hoặc 30.000 km',
     ('Thu tiền sửa vì đèn là đồ hao mòn', 'Bảo khách ra tiệm ngoài cho nhanh')),
    ('Xe mua 8 tháng, bị ngã gãy càng, khách nói “còn bảo hành mà”.',
     'Không bảo hành phần gãy do va chạm; báo giá sửa rõ ràng, khách đồng ý mới làm',
     ('Bảo hành luôn cho khách vui', 'Sửa luôn rồi tính tiền gấp đôi')),
    ('Xe mua 2 năm, máy kêu to. Khách đã độ pô và chế lại bộ chế hòa khí ở tiệm ngoài.',
     'Phần máy đã độ chế không còn bảo hành; nói rõ lý do, báo giá trả về như zin',
     ('Bảo hành hết, khách đâu biết', 'Từ chối nói chuyện, mời khách về')),
)
SERVICE = [('xa', 'Xả nhớt cũ, thay long đen ốc xả'), ('loc', 'Vệ sinh lọc gió'), ('do', 'Đổ nhớt mới đúng lượng'),
           ('siet', 'Kiểm và siết lại ốc, nan hoa, tay lái'), ('so', 'Ghi sổ bảo hành, đóng dấu mốc km')]
SERVICE_FIRST = 1000   # km of the first service
SERVICE_EVERY = 4000   # km between the next ones

# ---------------------------------------------------------------- accessories (phụ kiện)
HELMET = ((54, 55, 'M'), (56, 57, 'L'), (58, 59, 'XL'))
ACC_WANT = {
    'dx_mu': ((3, 'Cô mua thêm cái mũ bảo hiểm nhẹ nhẹ, đội đi chợ.'), (5, 'Em cần mũ bảo hiểm có tem hợp chuẩn, đừng mũ thời trang nha.')),
    'dx_khoa': ((4, 'Anh hay đậu xe ngoài đường, mua thêm cái khóa chống trộm.'),),
    'dx_tham': ((6, 'Chú mua bộ thảm lót sàn, xe mới sợ dơ.'),),
    'dx_camera': ((7, 'Chị cần camera hành trình, có chuyện gì còn có cái làm bằng.'),),
}
ACC_HAND_GOOD = ('Mở hộp kiểm hàng trước mặt khách', 'Đưa hóa đơn và phiếu bảo hành')
ACC_HAND_BAD = ('Bán mũ không tem hợp chuẩn cho rẻ', 'Không cho khách đổi nếu chưa dùng')

# ---------------------------------------------------------------- 🌀 oái oăm at the showroom
DEMANDS = [
    (1, 'Khách: “Ghi hóa đơn thấp xuống giùm cho bớt tiền trước bạ.”',
     'Ghi đúng giá bán; trước bạ tính theo giá thật', ('Ghi thấp một nửa', 'Ghi hai hóa đơn, một cái giá thấp'), ('ban',)),
    (1, 'Khách: “Xe này có phải xe mới nguyên không, hay xe trưng bày?”',
     'Nói thật: xe trưng bày đã chạy thử trong bãi, số km ghi trên đồng hồ', ('Nói xe mới nguyên đai', 'Lùi đồng hồ km cho đẹp'), ('ban',)),
    (1, 'Khách: “Bớt cho anh 10% đi, không thì anh qua đại lý khác.”',
     'Giữ giá niêm yết, tặng kèm phụ kiện theo chương trình nếu có', ('Bớt 10% cho kịp chốt', 'Hứa bớt rồi tăng phí giấy tờ bù lại'), ('ban',)),
    (2, 'Khách: “Giao xe liền đi, giấy tờ tính sau.”',
     'Làm hồ sơ đăng ký trước, giao xe khi có biển hoặc giấy hẹn hợp lệ', ('Giao luôn, khách tự lo giấy', 'Gắn tạm biển xe khác'), ('ban',)),
    (2, 'Khách chưa có bằng lái ô tô, muốn lái thử “một vòng thôi”.',
     'Mời người có bằng lái thử, khách ngồi cạnh trải nghiệm', ('Cho lái một vòng trong bãi đông người', 'Cho lái nếu khách hứa chạy chậm'), ('ban',)),
    (2, 'Khách: “Xe đạp điện có cần đội mũ bảo hiểm không em?”',
     'Có: đi xe đạp điện vẫn phải đội mũ bảo hiểm', ('Không cần, xe đạp mà', 'Chỉ cần khi đi đường lớn'), ('ban', 'pk')),
    (3, 'Khách: “Bảo hành trọn đời không em? Hứa đi rồi anh mua.”',
     'Nói đúng chính sách: 3 năm hoặc 30.000 km, tùy điều kiện nào tới trước', ('Hứa trọn đời cho khách vui', 'Hứa bảo hành cả khi xe ngã'), ('ban', 'hau_mai')),
    (3, 'Khách: “Định giá xe cũ của anh cao lên, rồi bù vào giá xe mới.”',
     'Định giá theo sổ tay, ghi riêng từng khoản cho khách xem', ('Nâng giá xe cũ, tăng giá xe mới', 'Định giá cao, hứa bù bằng phụ kiện'), ('thu_cu',)),
    (3, 'Khách: “Xe tôi có độ pô, độ đèn, tính thêm tiền đồ chơi nha.”',
     'Nói thật: đồ độ không làm tăng giá thu, xe phải trả về như zin mới bán lại được', ('Cộng thêm tiền đồ chơi', 'Mua giá cao vì xe độ đẹp'), ('thu_cu',)),
    (4, 'Khách: “Thay nhớt loại rẻ nhất cũng được, miễn rẻ.”',
     'Dùng đúng loại nhớt hãng khuyên, báo giá rõ', ('Đổ nhớt rẻ không đúng loại', 'Đổ nhớt cũ còn dư trong kho'), ('hau_mai',)),
    (4, 'Khách: “Ghi sổ bảo dưỡng giùm, khỏi làm, anh bận.”',
     'Chỉ ghi sổ khi đã bảo dưỡng thật, hẹn lịch khác cho khách', ('Ghi sổ cho xong', 'Ghi sổ, thu nửa tiền'), ('hau_mai',)),
    (5, 'Khách: “Trả góp mà khỏi chứng minh thu nhập được không?”',
     'Ngân hàng cần giấy tờ thu nhập; đại lý không tự cho vay', ('Đại lý cho nợ, trả dần', 'Làm giấy xác nhận thu nhập giùm'), ('ban',)),
    (5, 'Khách: “Mũ này không có tem, nhưng đẹp, bán rẻ cho em.”',
     'Chỉ bán mũ có tem hợp chuẩn; mời khách chọn mẫu có tem', ('Bán mũ không tem cho rẻ', 'Dán tem giả lên mũ'), ('pk',)),
    (6, 'Khách: “Camera hành trình quay luôn trong nhà người ta được không?”',
     'Nói rõ: camera để ghi đường đi; không quay lén nhà người khác', ('Được, quay gì cũng được', 'Chỉ cách tắt đèn camera để quay lén'), ('pk',)),
    (8, 'Khách hỏi: “Mua xe này bán lại có lời không?”',
     'Nói thật: xe mất giá theo năm, bán lại thường thấp hơn giá mua', ('Hứa bán lại còn lời', 'Hứa đại lý mua lại nguyên giá'), ('ban', 'thu_cu')),
]

RULES = [
    'Mọi con số dưới đây là sổ tay của Đại lý xe Phố Mây, luật của trò chơi.',
    'Giá niêm yết đã gồm thuế VAT. Lệ phí trước bạ: xe máy 2%, ô tô 10% giá xe (bỏ phần lẻ). Phí biển số: xe máy 5 xu, ô tô 20 xu. Khách trả giá xe + trước bạ + biển số; trước bạ và biển số đại lý nộp hộ, không phải tiền lời.',
    'Chọn xe theo nhu cầu, bằng lái và ngân sách của khách. Xe đạp điện không cần bằng; xe máy cần bằng A1; ô tô cần bằng B.',
    'Thông số nói theo công bố của hãng. Không hứa quá sự thật, không chê xe khác để bán xe mình.',
    'Lái thử: xem bằng lái đúng hạng, nhân viên đi cùng, chạy cung đường cố định.',
    'Trả góp qua Ngân hàng Phố: trả trước ít nhất 30% giá xe (làm tròn lên), khoản vay tối đa 5.000 xu, lãi 4% mỗi tuần, kỳ hạn 14–28 ngày. Khoản góp mỗi tuần không quá 40% thu nhập. Ngân hàng trả đủ tiền cho đại lý; đại lý không tự cho nợ.',
    'Biển số bấm ngẫu nhiên ở công an. Biển đẹp chỉ có qua 🔨 đấu giá biển số.',
    'Thu xe cũ: giá theo tuổi = giá xe mới trừ 10% mỗi năm đã dùng (bỏ phần lẻ), thấp nhất còn 30% giá mới. Trừ tiếp tiền sửa những chỗ hư. Bãi xe cũ mua lại của đại lý 106% giá thu trong ngày.',
    'Thu xe cũ phải có giấy đăng ký đúng tên hoặc giấy ủy quyền, số khung số máy khớp giấy. Không khớp thì không mua, báo công an khu vực.',
    'Bảo hành 3 năm hoặc 30.000 km. Không bảo hành phần hư do va chạm hoặc đã độ chế. Bảo dưỡng lần đầu ở 1.000 km, sau đó mỗi 4.000 km.',
    'Kiểm xe mới (PDI) đủ năm bước trước khi trưng bày. Số khung trên xe phải khớp phiếu xuất xưởng.',
    'Mũ bảo hiểm phải có tem hợp chuẩn. Cỡ mũ theo vòng đầu: 54–55 cm cỡ M, 56–57 cm cỡ L, 58–59 cm cỡ XL.',
]

# ---------------------------------------------------------------- 🔔 desk surprises
DESK = [
    dict(id='rain_lot', title='Mưa lớn, nước tràn vào bãi xe', emoji='🌧️', npc=2, min_day=1, tone='tense', at='between', weight=2, mods=None,
         text='Mưa như trút, nước bắt đầu tràn vào góc bãi đang đậu ba chiếc xe máy mới.',
         options=[dict(id='move', label='Dắt xe lên bục cao, kê ván, che bạt', hint='', effects=dict(xp=5), good=True,
                       outcome='Xe khô ráo. Tú lau lại từng chiếc, không trầy chỗ nào.'),
                  dict(id='later', label='Mưa tạnh rồi tính', hint='', effects=dict(money=-15, money_loss='normal'), good=False,
                       outcome='Một chiếc bị nước ngập bánh, phải vệ sinh lại phanh. Tốn 15 xu.')],
         default='later'),
    dict(id='scratch', title='Khách lỡ tay làm trầy xe trưng bày', emoji='🪛', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một khách đeo túi xách có khóa kim loại, quẹt một đường trên yếm xe trưng bày. Khách luống cuống xin lỗi.',
         options=[dict(id='calm', label='Trấn an khách, ghi biên bản xe trưng bày, đánh bóng lại', hint='', effects=dict(xp=5, review=[5, 'Mình lỡ tay mà đại lý không làm khó, lại còn mời nước.', 3]), good=True,
                       outcome='Tú đánh bóng xong, vết trầy mờ hẳn. Khách hẹn tuần sau quay lại mua.'),
                  dict(id='charge', label='Bắt khách đền 30 xu', hint='', effects=dict(money=10, review=[1, 'Lỡ quẹt một đường mà bị bắt đền như ăn cướp.', 3]), good=False,
                       outcome='Khách trả 10 xu rồi bỏ đi, không quay lại.')],
         default='calm'),
    dict(id='keys_left', title='Chìa khóa cắm trên xe trưng bày', emoji='🔑', npc=2, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='Sáng mở cửa, bạn thấy chìa khóa ô tô trưng bày vẫn cắm trong ổ từ hôm qua.',
         options=[dict(id='box', label='Rút chìa, cất vào tủ chìa có sổ ký mượn', hint='', effects=dict(xp=5), good=True,
                       outcome='Từ hôm đó tủ chìa có sổ, ai mượn chìa cũng ký.'),
                  dict(id='leave', label='Để đó cho khách xem tiện', hint='', effects=dict(mark='keys_left'), good=False,
                       outcome='Chìa khóa vẫn cắm trên xe.')],
         default='leave'),
    dict(id='joyride', title='Một thanh niên ngồi lên xe nổ máy', emoji='🚨', npc=8, min_day=4, tone='tense', at='between', weight=5, mods=None,
         need_mark='keys_left',
         text='Một thanh niên vào xem xe, ngồi tọt lên ô tô trưng bày còn cắm chìa và vặn nổ máy.',
         options=[dict(id='stop', label='Bình tĩnh mời khách xuống, rút chìa, nói rõ quy định lái thử', hint='', effects=dict(unmark='keys_left', xp=4), good=True,
                       outcome='Thanh niên xuống xe, gãi đầu xin lỗi. Chìa khóa vào tủ từ đó.'),
                  dict(id='laugh', label='Cười xòa cho qua', hint='', effects=dict(unmark='keys_left', money=-40, money_loss='normal'), good=False,
                       outcome='Xe nhích lên, quẹt vào cột. Sửa mất 40 xu.')],
         default='stop'),
    dict(id='rival_flyer', title='Tờ rơi chê xe của đại lý', emoji='📰', npc=0, min_day=3, tone='gentle', at='open', weight=2, mods=None,
         text='Ai đó phát tờ rơi trước cửa, ghi xe tay ga bên mình “hao xăng gấp đôi”, không có số liệu.',
         options=[dict(id='facts', label='Dán bảng thông số công bố của hãng ở cửa, không nói xấu ai', hint='', effects=dict(xp=6), good=True,
                       outcome='Khách đọc bảng thông số, gật gù. Tờ rơi nằm trong thùng rác.'),
                  dict(id='attack', label='In tờ rơi chê lại đại lý kia', hint='', effects=dict(money=-10, money_loss='fine', review=[2, 'Hai đại lý chê qua chê lại, khách nhìn mà ngán.', 0]), good=False,
                       outcome='Phường nhắc nhở cả hai bên phát tờ rơi sai, phạt 10 xu.')],
         default='facts'),
    dict(id='odometer', title='Người lạ nhờ lùi đồng hồ km', emoji='🔢', npc=8, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Một người dắt xe cũ vào: “Lùi giùm đồng hồ xuống 5.000 km, anh trả 30 xu, mai anh bán xe.”',
         options=[dict(id='no', label='Từ chối, nói rõ lùi km là lừa người mua', hint='', effects=dict(xp=6), good=True,
                       outcome='Người lạ lầm bầm bỏ đi. Anh Quân gật đầu.'),
                  dict(id='yes', label='Nhận 30 xu, lùi cho nhanh', hint='', effects=dict(money=30, mark='odo_done'), good=False,
                       outcome='Bạn bỏ túi 30 xu. Chiếc xe ra khỏi đại lý với con số không thật.')],
         default='no'),
    dict(id='odo_back', title='Người mua xe cũ quay lại khiếu nại', emoji='📢', npc=3, min_day=5, tone='tense', at='between', weight=5, mods=None,
         need_mark='odo_done',
         text='Một người mua lại chiếc xe hôm trước, phát hiện đồng hồ bị lùi, quay lại đại lý làm lớn chuyện.',
         options=[dict(id='own', label='Nhận lỗi, trả lại 30 xu, xin lỗi công khai', hint='', effects=dict(unmark='odo_done', money=-30, money_loss='fine', review=[3, 'Đại lý có làm sai nhưng chịu nhận.', 3]), good=True,
                       outcome='Người mua nguôi giận. Anh Quân dặn không bao giờ đụng vào đồng hồ km nữa.'),
                  dict(id='deny', label='Chối, nói không biết', hint='', effects=dict(unmark='odo_done', money=-60, money_loss='fine', review=[1, 'Đại lý lùi đồng hồ km mà còn chối.', 3]), good=False,
                       outcome='Camera ghi lại cảnh lùi km. Phường phạt 60 xu.')],
         default='own'),
    dict(id='test_rider', title='Khách lái thử xin chạy về nhà', emoji='🛵', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Anh Dũng chạy thử ưng quá: “Cho anh chạy về nhà khoe vợ, nửa tiếng quay lại liền.”',
         options=[dict(id='route', label='Mời chạy thêm một vòng cung đường cố định, hẹn chở vợ tới xem', hint='', effects=dict(xp=4), good=True,
                       outcome='Chiều đó anh Dũng chở vợ tới, hai vợ chồng chốt luôn.'),
                  dict(id='go', label='Cho chạy về nhà, tin người', hint='', luck=dict(p=0.6, win=dict(outcome='Anh Dũng quay lại đúng hẹn, cười tươi.', good=None),
                                                                                       lose=dict(outcome='Anh Dũng quẹt xe vào cột điện, đại lý mất 25 xu sửa.', effects=dict(money=-25), good=False)),
                       effects=dict(), good=None, outcome='')],
         default='route'),
    dict(id='battery_dead', title='Xe trưng bày không nổ máy', emoji='🔋', npc=2, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='Khách tới xem, chiếc tay ga trưng bày đề không nổ: ắc quy cạn vì đứng lâu.',
         options=[dict(id='charge', label='Câu bình, sạc lại, ghi lịch nổ máy xe trưng bày mỗi tuần', hint='', effects=dict(xp=5), good=True,
                       outcome='Xe nổ giòn. Từ đó Tú có lịch nổ máy xe trưng bày.'),
                  dict(id='swap', label='Tháo bình xe khác lắp tạm', hint='', effects=dict(patience=-2), good=None,
                       outcome='Khách đứng chờ khá lâu, xe kia giờ lại hết bình.')],
         default='charge'),
    dict(id='kid_seat', title='Khách hỏi ghế trẻ em', emoji='👶', npc=7, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Chị Vy hỏi: “Bé nhà chị 2 tuổi, ngồi ghế trước cho tiện trông được không em?”',
         options=[dict(id='back', label='Khuyên ngồi ghế trẻ em ở hàng sau, chỉ cách lắp móc ghế', hint='', effects=dict(xp=5, review=[5, 'Đại lý dặn kỹ chuyện ghế cho bé, thấy yên tâm.', 7]), good=True,
                       outcome='Chị Vy cảm ơn, mua thêm ghế trẻ em ở tiệm đồ em bé.'),
                  dict(id='front', label='Ngồi trước cũng được, có túi khí mà', hint='', effects=dict(review=[2, 'Đại lý khuyên cho bé ngồi trước, nghe mà sợ.', 7]), good=False,
                       outcome='Chị Vy đọc lại sách hướng dẫn, thấy ghi ngược hẳn.')],
         default='back'),
    dict(id='papers_late', title='Hồ sơ đăng ký trễ hẹn', emoji='📂', npc=1, min_day=4, tone='gentle', at='open', weight=2, mods=None,
         text='Chị Mai báo: một bộ hồ sơ đăng ký xe bị thiếu chữ ký, biển số trễ hẹn hai ngày.',
         options=[dict(id='call', label='Gọi báo khách thật, xin lỗi, hẹn ngày mới, ký bổ sung ngay', hint='', effects=dict(xp=5), good=True,
                       outcome='Khách thông cảm, ghé ký bổ sung. Hai hôm sau có biển.'),
                  dict(id='silent', label='Im lặng, đợi khách hỏi', hint='', effects=dict(review=[2, 'Hẹn biển số rồi im luôn, gọi mãi mới nói.', 6]), good=False,
                       outcome='Khách gọi tới hỏi, bực mình vì không ai báo.')],
         default='call'),
    dict(id='coffee_spill', title='Ly cà phê đổ lên ghế da', emoji='☕', npc=6, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Chú Bảy ngồi thử ghế lái ô tô, ly cà phê sữa đổ nguyên lên ghế da sáng màu.',
         options=[dict(id='clean', label='Lau ngay bằng khăn ẩm và dung dịch vệ sinh da', hint='', effects=dict(xp=3), good=True,
                       outcome='Ghế sạch như cũ. Chú Bảy cười ngượng.'),
                  dict(id='later', label='Đợi khách về rồi lau', hint='', effects=dict(money=-8, money_loss='normal'), good=False,
                       outcome='Vết cà phê thấm vào da, phải thuê tiệm vệ sinh nội thất 8 xu.')],
         default='clean'),
]
