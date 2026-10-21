"""💍 Tiệm vàng Ngọc Mây: the words and tables of the gold and jewellery shop (game/careers/jewelry.py).

Every table is static: a job is a pure function of (day, slot), so validate_state can rebuild it. Player #472 asked for
"làm chủ bán vàng, bán kim cương"; the owner: "nghề mới thì làm đi". The shop's notebook below is the game's rule book
(weights, purities, the board's spread, the buy-back deduction, the 4C of a diamond); every number is fiction kept close
to how a Vietnamese tiệm vàng works. Each customer brings one or two awkward demands (DEMANDS), and the counter has its
own surprises between customers (DESK), some of which leave a mark that brings a later event.
"""
from __future__ import annotations

PLACE = 'Tiệm vàng Ngọc Mây'
OWNER = 'Cô Ba Ngọc'

PEOPLE = [
    ('Cô Ba Ngọc', 'Chủ tiệm vàng', 'Ba mươi năm đứng quầy, nhìn màu vàng là đoán được tuổi. Dặn hoài: cân trước mặt khách, giấy tờ rõ ràng.', 'warm'),
    ('Chú Tư Bạc', 'Thợ kim hoàn', 'Ngồi bàn chế tác sau quầy: đánh bóng, hàn khoen, khắc chữ. Ít nói, tay rất vững.', 'quiet'),
    ('Chị Hằng', 'Cô dâu sắp cưới', 'Đi chọn nhẫn cưới với mẹ chồng tương lai, hai người ý kiến trái ngược.', 'picky'),
    ('Bà Năm Chợ', 'Bán cá ngoài chợ', 'Để dành tiền mua vàng ta từng chỉ, tin vàng hơn tin ai.', 'warm'),
    ('Anh Phát', 'Thanh niên mê đầu tư', 'Ngày nào cũng hỏi giá, đọc tin trên mạng, rất hay mặc cả.', 'genz'),
    ('Ông Sáu Râu', 'Ông cụ về hưu', 'Mang đồ gia bảo đi xem, kể chuyện xưa không dứt.', 'sour'),
    ('Chị Thu', 'Mẹ bỉm sữa', 'Mua nhẫn đầy tháng, lắc bạc cho con, hỏi kỹ từng đồng.', 'picky'),
    ('Người đội nón kín', 'Khách vãng lai', 'Đi vội, nói ít, muốn bán gấp.', 'quiet'),
]
MENTOR = 0
SMITH = 1
CUSTOMERS = (2, 3, 4, 5, 6)
STRANGER = 7

WRONG_COST = 8          # quality lost per redone step
QUALITY_FLOOR = 40
MILESTONES = (3, 6, 12, 25)   # days: diamonds, fakes and doubtful sellers, two demands, the hardest stones
MASTER = (100, 30)      # Thợ vàng vững tay: good jobs, active days
EXPERT = (180, 45)      # Chủ tiệm vàng có tiếng

# ---------------------------------------------------------------- the board (jewelry.board builds it)
REF = 520               # xu a chỉ of 9999 gold in the middle of the band (the shop's own market, not Kim Phát's)
SPREAD_BP = 120         # the shop sells 1,2 % above the company's middle price and buys 1,2 % below
REFINE_BP = 0           # the company takes old gold back at its middle price (the shop's margin is the spread)
SILVER = (6, 8, 10)     # bạc 925 a chỉ: mua vào, giá giữa, bán ra (silver hardly moves)
TUOI = {                # purity: (per 10 000, the label, the tuổi the street says)
    '9999': (9999, '9999', 'vàng ta 24K'),
    '18k': (7500, '18K', 'vàng tây 7 tuổi rưỡi'),
    '14k': (5850, '14K', 'vàng tây 5 tuổi 85'),
    '10k': (4160, '10K', 'vàng tây 4 tuổi'),
    'bac': (0, 'Bạc 925', 'bạc'),
}
GOLD = ('9999', '18k', '14k')   # on the board
DEDUCT_OTHER = 3        # % off old gold from another shop or without the shop's invoice
GRAM_PER_PHAN = 0.375   # 1 chỉ = 3,75 g = 10 phân

# ---------------------------------------------------------------- the stock (inventory items; jewelry.ITEMS)
# phan: weight in phân (1/10 chỉ); tuoi: purity; cong: the price key of its tiền công (SPEC prices, tunable 75–125 %);
# stone: xu of the stone set in it (the diamond ring); start: pieces on the opening shelf (free, like every shop's).
PIECES = {
    'vg_nhan_be': dict(name='Nhẫn trơn 9999 cho bé', emoji='👶', tuoi='9999', phan=5, cong='cong_vang', start=3, unit='chiếc'),
    'vg_nhan_tron': dict(name='Nhẫn tròn trơn 9999 một chỉ', emoji='💍', tuoi='9999', phan=10, cong='cong_vang', start=2, unit='chiếc'),
    'vg_bong_tai': dict(name='Bông tai 18K', emoji='✨', tuoi='18k', phan=3, cong='cong_tay', start=3, unit='đôi'),
    'vg_day_chuyen': dict(name='Dây chuyền 18K', emoji='📿', tuoi='18k', phan=15, cong='cong_tay', start=1, unit='sợi'),
    'vg_lac_14k': dict(name='Lắc tay 14K', emoji='⛓️', tuoi='14k', phan=10, cong='cong_tay', start=1, unit='chiếc'),
    'vg_lac_bac': dict(name='Lắc tay bạc 925', emoji='🪙', tuoi='bac', phan=20, cong='cong_bac', start=4, unit='chiếc'),
    'vg_kieng_bac': dict(name='Vòng kiềng bạc cho bé', emoji='🧿', tuoi='bac', phan=15, cong='cong_bac', start=1, unit='chiếc'),
    'vg_nhan_cuoi': dict(name='Cặp nhẫn cưới 18K', emoji='💞', tuoi='18k', phan=20, cong='cong_cuoi', start=0, unit='cặp', unlock=2),
    'vg_nhan_kc': dict(name='Nhẫn kim cương 18K', emoji='💎', tuoi='18k', phan=12, cong='cong_kc', start=0, unit='chiếc', unlock=3, stone=300),
}
# The shop's tiền công (SPEC prices): what the price board names them (extra_content.price_board reads `name`).
CONG = {
    'cong_vang': dict(name='Tiền công nhẫn vàng ta', emoji='💍', base=12),
    'cong_tay': dict(name='Tiền công vàng tây', emoji='✨', base=25),
    'cong_cuoi': dict(name='Tiền công cặp nhẫn cưới', emoji='💞', base=60),
    'cong_bac': dict(name='Tiền công đồ bạc', emoji='🪙', base=22),
    'cong_kc': dict(name='Tiền công nhẫn kim cương', emoji='💎', base=80),
    'kiem_dinh': dict(name='Phí kiểm định kim cương', emoji='🔍', base=30),
}
# What a customer asks for, by piece: (customer index, words).
WANT = {
    'vg_nhan_be': ((6, 'Mua cho bé nhà em chiếc nhẫn vàng ta đầy tháng, nhỏ nhỏ thôi.'),
                   (3, 'Cháu nội tui đầy tháng, lấy chiếc nhẫn vàng ta nhỏ cho nó.')),
    'vg_nhan_tron': ((3, 'Lấy cho tui một chỉ vàng ta để dành, loại nhẫn tròn trơn đó.'),
                     (4, 'Em gom nhẫn tròn 9999, lấy một chiếc một chỉ.')),
    'vg_bong_tai': ((2, 'Em muốn đôi bông tai vàng tây nhỏ nhỏ đeo đi làm.'),
                    (6, 'Chị lấy đôi bông tai vàng, đeo hằng ngày không đen.')),
    'vg_day_chuyen': ((2, 'Mẹ chồng em muốn tặng sợi dây chuyền vàng tây.'),
                      (5, 'Tặng con gái sợi dây chuyền 18K nhân sinh nhật.')),
    'vg_lac_14k': ((4, 'Mua cái lắc tay vàng tây cho bạn gái, đừng mắc quá.'),),
    'vg_lac_bac': ((6, 'Lắc bạc cho con em đeo, bạc thật nha chị.'),
                   (2, 'Em lấy cái lắc tay bạc làm quà cho đứa bạn.')),
    'vg_kieng_bac': ((3, 'Mua vòng kiềng bạc cho cháu, người ta nói đeo bạc giải cảm.'),
                     (6, 'Lấy cái vòng kiềng bạc cho bé hai tuổi.')),
    'vg_nhan_cuoi': ((2, 'Tụi em chọn cặp nhẫn cưới vàng tây, cưới tháng sau.'),),
    'vg_nhan_kc': ((4, 'Em sắp cầu hôn, muốn chiếc nhẫn có hột kim cương thiệt.'),),
}

# ---------------------------------------------------------------- buying old gold back (mua lại)
# (what the customer brings, purity, weight range in phân, a stone's weight in phân (0: none), the shop's own with its invoice)
OLD = [
    ('Chiếc nhẫn tròn 9999 mua ở tiệm mình, còn hóa đơn', '9999', (5, 20), 0, True),
    ('Sợi dây chuyền 18K mua ở tiệm khác', '18k', (8, 25), 0, False),
    ('Đôi bông tai 14K đứt khoen, không còn hóa đơn', '14k', (3, 8), 0, False),
    ('Chiếc lắc 18K có mặt đá, mua ở tiệm mình, còn hóa đơn', '18k', (10, 20), 1, True),
    ('Cặp nhẫn cưới cũ 18K của tiệm khác', '18k', (12, 24), 0, False),
    ('Mấy chiếc nhẫn 9999 của mẹ để lại, không hóa đơn', '9999', (10, 30), 0, False),
]
XRF = {   # what the gun-shaped XRF scanner prints for each purity
    '9999': 'Au 99,99%',
    '18k': 'Au 75,0% · Ag 12,5% · Cu 12,5%',
    '14k': 'Au 58,5% · Ag 9,5% · Cu 32,0%',
    '10k': 'Au 41,6% · Ag 11,0% · Cu 47,4%',
    'fake': 'Au 1,8% (lớp mạ ngoài) · Cu 66,2% · Zn 32,0%',
}
TUOI_OPTS = {   # the choice rows of the purity step
    '9999': '9999: vàng ta 24K',
    '18k': '18K: vàng tây 7 tuổi rưỡi',
    '14k': '14K: vàng tây 5 tuổi 85',
    '10k': '10K: vàng tây 4 tuổi',
    'fake': 'Đồ mạ, không phải vàng',
}
FAKE = ('Sợi dây chuyền “18K” sáng bóng, khoen có khắc chữ 18K, khách nói mua ở chợ đêm', 'Chiếc nhẫn “vàng ta” nặng tay, khách nói bạn trả nợ bằng nhẫn này')
FAKE_THEN = ('Máy báo đồ mạ. Khách nài: “Khắc 18K rõ ràng mà, mua đỡ giá nào cũng được.”',
             'Trả lại món cho khách, nói thật kết quả máy quét, tiệm không mua',
             ('Mua theo giá 18K vì có khắc chữ', 'Mua giá rẻ rồi bán lại cho người khác', 'Giữ món lại để “kiểm thêm”'))
DOUBT = (
    ('Ba chiếc nhẫn cưới khắc ba cặp tên khác nhau, đựng trong túi ni lông. Khách không mang CCCD, muốn bán gấp lấy tiền mặt.',
     'Không mua: xin CCCD, không có thì từ chối; nghi đồ gian thì ghi lại đặc điểm, báo công an khu vực',
     ('Mua nhanh giá rẻ, khỏi hỏi nhiều', 'Mua rồi đợi vài hôm mới nấu', 'Giữ đồ lại, đuổi khách đi')),
    ('Sợi dây chuyền đứt ngang như bị giật, khách đội nón kín mặt, đưa CCCD của người khác.',
     'Không mua: CCCD không phải của người bán; ghi lại đặc điểm, báo công an khu vực',
     ('Mua vì có CCCD là được', 'Mua giá nửa để “phòng hờ”', 'Bảo khách về lấy CCCD rồi mua liền khỏi ghi sổ')),
)
ID_OK = ('Khách đưa CCCD còn hạn, đúng mặt người bán.',
         'Đối chiếu CCCD, chụp món, ghi sổ mua hàng rồi mới cân',
         ('Khỏi giấy tờ, khách quen mà', 'Giữ luôn CCCD của khách làm tin', 'Ghi sổ sau, cân trước cho nhanh'))
LEDGER_GOOD = ('Số CCCD và tên người bán', 'Ảnh chụp món hàng', 'Tuổi vàng và số phân', 'Số tiền đã trả, chữ ký người bán')
LEDGER_BAD = ('Ghi tuổi thấp hơn kết quả máy để trả ít', 'Bỏ trống dòng tên cho khách khỏi ngại')

# ---------------------------------------------------------------- selling (bán)
INVOICE_GOOD = ('Tên món và tuổi vàng', 'Trọng lượng (phân)', 'Giá vàng bán ra hôm nay', 'Tiền công')
INVOICE_BAD = ('Ghi tuổi cao hơn cho khách vui', 'Bỏ trống trọng lượng cho gọn', 'Ghi giá thấp hơn cho khách đỡ thuế')
HAND_GOOD = ('Cân lại trước mặt khách', 'Bỏ hộp nhung, đưa hóa đơn', 'Ghi phiếu bảo hành đánh bóng miễn phí một năm')
HAND_BAD = ('Đưa món trong túi ni lông khỏi hộp', 'Hứa “bán lại lúc nào cũng nguyên giá”')
SCALE_FIX = ('Đặt quả cân chuẩn 10 g lên cân: màn hình hiện 10,04 g.',
             'Ngưng cân hàng: chỉnh chuẩn cân, đặt lại quả cân chuẩn cho đúng 10,00 g',
             ('Cân hàng luôn, lệch chút xíu không sao', 'Trừ 0,04 g cho mỗi món trong đầu', 'Tắt cân, đoán bằng tay'))
SCALE_OK = ('Đặt quả cân chuẩn 10 g lên cân: màn hình hiện 10,00 g.',
            'Cân đúng: ghi sổ kiểm cân đầu ngày rồi bán',
            ('Chỉnh lại cho chắc, lệch thêm chút cũng được', 'Bỏ quả cân chuẩn, khỏi kiểm mỗi ngày'))

# ---------------------------------------------------------------- diamonds (kiểm định 4C)
COLOR_GRADES = ('D', 'E', 'F', 'G', 'H', 'I', 'J', 'K')
CLARITY = {   # what the 10x loupe shows → the grade
    'IF': 'Soi kính lúp 10x khắp mặt bàn và đáy: không thấy một vết nào bên trong',
    'VVS': 'Soi 10x rất lâu mới thấy một chấm li ti như hạt bụi, phải nghiêng đá mới thấy',
    'VS': 'Soi 10x thấy vài chấm nhỏ, phải tìm mới thấy; mắt thường không thấy',
    'SI': 'Soi 10x thấy ngay một vết như lông vũ; nhìn kỹ bằng mắt thường thấy mờ mờ',
    'I': 'Mắt thường đã thấy rõ một vết nứt và đốm đen',
}
CLARITY_NAMES = {'IF': 'IF: sạch bên trong', 'VVS': 'VVS: rất rất ít tạp', 'VS': 'VS: rất ít tạp',
                 'SI': 'SI: ít tạp, soi thấy ngay', 'I': 'I: tạp thấy bằng mắt thường'}
CUTS = {   # (table %, depth %, what the light does) → the cut grade
    'ex': ((56, 61, 'ánh lửa đều khắp mặt đá'), 'Excellent: giác cắt chuẩn'),
    'good': ((61, 64, 'giữa mặt đá hơi tối khi nghiêng'), 'Good: giác cắt khá'),
    'poor': ((66, 71, 'giữa mặt đá tối như cửa sổ đen'), 'Poor: cắt quá sâu, tối đá'),
}
CUT_WRONG = 'Very Good: chỉ cần đá sáng là được'
STONE_KIND = ('Thử bằng bút thử nhiệt rồi máy thử điện dẫn: bút báo “kim cương”, máy điện dẫn báo “moissanite”.',
              'Đá moissanite, không phải kim cương: ghi rõ vào phiếu, báo khách',
              ('Kim cương: bút thử báo kim cương là đủ', 'Ghi “kim cương nhân tạo” cho khách đỡ buồn'))

# ---------------------------------------------------------------- the morning (mở két, niêm yết bảng giá)
BILLS = ((100, 'xấp tờ 100 xu (mỗi xấp 10 tờ)', 1000), (50, 'tờ 50 xu', 50), (20, 'tờ 20 xu', 20), (10, 'tờ 10 xu', 10))
SAFE_OK = ('Khớp sổ: ký sổ giao ca, mở két làm việc', 'Lệch: báo cô Ba, lập biên bản, không tự bù')
SAFE_WRONG = ('Lấy tiền túi bù cho khớp, khỏi báo', 'Sửa số trong sổ cho khớp két')

# ---------------------------------------------------------------- 🌀 oái oăm at the counter (one or two a customer)
# (min day, what the customer says, the right answer, the wrong ones, only for these kinds or None)
DEMANDS = [
    (1, 'Khách: “Khỏi xuất hóa đơn đi, bớt cho chị chút tiền công.”',
     'Vẫn xuất hóa đơn đủ dòng; tiền công theo bảng giá tiệm', ('Không xuất hóa đơn, bớt 5 xu', 'Ghi hóa đơn giá thấp hơn giá thật'), ('ban',)),
    (1, 'Khách: “Cân sau quầy rồi đưa luôn, khỏi cân trước mặt.”',
     'Cân trước mặt khách, quay màn hình cân cho khách xem', ('Cân sau quầy cho nhanh', 'Đọc số theo tem, khỏi cân'), ('ban', 'mua')),
    (1, 'Khách: “Mua lẹ giùm, khỏi ghi sổ, khỏi CCCD, tui đang gấp.”',
     'Nói rõ đây là quy định: xem CCCD, ghi sổ mua hàng rồi mới mua', ('Mua nhanh, bỏ qua sổ', 'Ghi đại tên khác vào sổ'), ('mua',)),
    (2, 'Khách hỏi: “Vàng 18K là vàng gì? Có phải vàng ta không?”',
     'Nói thật: 18K là vàng tây, 75% vàng; vàng ta là 9999', ('Nói 18K cũng như vàng ta cho dễ bán', 'Nói 18K còn quý hơn 9999'), ('ban',)),
    (2, 'Khách: “Hôm qua giá rẻ hơn mà, bán giá hôm qua đi.”',
     'Giải thích giá theo bảng niêm yết hôm nay, ai mua cũng một giá', ('Bán giá hôm qua cho vui lòng', 'Nâng giá vì khách hỏi khó'), ('ban',)),
    (2, 'Khách bán vàng mà đòi tính theo giá bán ra trên bảng.',
     'Chỉ khách cột mua vào: tiệm mua theo giá mua vào, có niêm yết rõ', ('Tính giá bán ra cho khách vui', 'Tính giá giữa cho đỡ cãi'), ('mua',)),
    (3, 'Khách: “Khắc tên tụi em vô nhẫn liền đi, đợi không được.”',
     'Ghi phiếu khắc chữ, hẹn giờ lấy theo lịch chú Tư', ('Khắc vội bằng tay cho kịp', 'Hứa khắc liền rồi để khách đợi cả buổi'), ('ban',)),
    (3, 'Khách: “Ghi giấy kiểm định cao lên giùm, em cầm ngân hàng cho được nhiều.”',
     'Ghi đúng kết quả kiểm định, không nâng giá trị', ('Nâng nhẹ một bậc màu', 'Ghi thêm “giá tham khảo” cao gấp đôi'), ('kc',)),
    (3, 'Khách: “Soi lẹ giùm, khỏi soi kỹ, đá mua hãng mà.”',
     'Vẫn soi đủ bốn bước rồi mới ghi phiếu', ('Ghi theo giấy của khách, khỏi soi', 'Soi qua loa một mặt'), ('kc',)),
    (4, 'Khách: “Đồ của mẹ chồng để lại, không có hóa đơn, nhưng có CCCD của tui.”',
     'Mua được: xem CCCD, ghi sổ, trừ hao theo hàng không hóa đơn', ('Từ chối vì không có hóa đơn', 'Mua giá nửa vì không hóa đơn'), ('mua',)),
    (4, 'Khách trả 2.000 xu tiền mặt, không muốn ghi tên người mua.',
     'Giao dịch lớn: ghi tên người mua theo quy định, mời chuyển khoản', ('Bán luôn khỏi ghi tên', 'Chia làm hai hóa đơn cho dưới mức ghi tên'), ('ban',)),
    (5, 'Khách: “Bán cho anh năm lượng vàng miếng, khỏi giấy tờ.”',
     'Nói thật: tiệm chỉ bán trang sức; vàng miếng mua ở nơi có giấy phép', ('Gom nhẫn tròn bán thay vàng miếng', 'Hứa mua giùm ngoài chợ'), ('ban',)),
    (5, 'Khách: “Cho em cầm tạm chiếc nhẫn này lấy chút tiền, mai chuộc.”',
     'Tiệm không làm cầm đồ: chỉ mua hẳn theo giá mua vào, có ghi sổ', ('Nhận cầm, tính lãi theo ngày', 'Giữ nhẫn, đưa tiền khỏi ghi giấy'), ('mua',)),
    (6, 'Khách: “Đánh bóng lại chiếc nhẫn cũ cho như mới rồi bán cho em giá mới.”',
     'Nói rõ món đánh bóng vẫn là hàng cũ, tính theo tuổi và trọng lượng thật', ('Bán như hàng mới', 'Thay tem mới cho đẹp'), ('ban',)),
    (8, 'Khách hỏi: “Kim cương này mai bán lại được nguyên giá không?”',
     'Nói thật: bán lại thường thấp hơn giá mua, tùy giấy và tình trạng đá', ('Hứa bán lại nguyên giá', 'Hứa bán lại còn lời'), ('kc', 'ban')),
]

RULES = [
    'Mọi con số dưới đây là sổ tay của tiệm Ngọc Mây, luật của trò chơi.',
    '1 lượng (cây) = 10 chỉ; 1 chỉ = 10 phân = 3,75 g; 1 phân = 0,375 g.',
    'Tuổi vàng: 9999 (vàng ta, 24K) 99,99%; 18K (7 tuổi rưỡi) 75%; 14K (5 tuổi 85) 58,5%; 10K (4 tuổi) 41,6%. Máy quét chỉ thấy lớp mỏng vài phần trăm vàng là đồ mạ.',
    'Bảng giá: mỗi sáng công ty vàng báo giá giữa của vàng 9999. Tiệm mua vào thấp hơn 1,2%, bán ra cao hơn 1,2% (làm tròn tới xu). Vàng tây tính theo tuổi, đã ghi sẵn trên bảng.',
    'Bán: tiền vàng = số phân × giá bán ra một chỉ ÷ 10 (bỏ phần lẻ), cộng tiền công theo bảng giá tiệm. Cân trước mặt khách.',
    'Mua lại: tiền trả = số phân × giá mua vào một chỉ ÷ 10, trừ hao hụt rồi bỏ phần lẻ. Hàng tiệm mình còn hóa đơn: không trừ. Hàng tiệm khác hoặc không hóa đơn: trừ 3%. Món có gắn đá: trừ trọng lượng đá trước.',
    'Mua lại phải xem CCCD đúng người bán, chụp món, ghi sổ mua hàng. Không mua đồ không rõ nguồn gốc; nghi đồ gian thì từ chối, ghi đặc điểm, báo công an khu vực.',
    'Hóa đơn ghi đủ: tên món, tuổi vàng, trọng lượng, giá vàng hôm nay, tiền công. Không ghi khống, không bỏ dòng. Giao dịch lớn ghi tên người mua.',
    'Kim cương 4C: carat (1 ct = 0,2 g = 100 điểm), màu (D trắng nhất tới K ngả vàng; đặt cạnh bộ đá mẫu, đá nằm giữa hai mẫu thì lấy màu của mẫu ngả vàng hơn), độ sạch (soi kính lúp 10x: IF, VVS, VS, SI, I), giác cắt (mặt bàn 53–58%, độ sâu 59–63% là Excellent).',
    'Giấy kiểm định: số trên giấy phải khớp số khắc laser trên mép đá. Không khớp thì ghi rõ, không định giá theo giấy. Bút thử nhiệt không phân biệt được moissanite: thử thêm máy điện dẫn.',
    'Két: đầu ngày đếm két so với sổ giao ca. Lệch thì báo chủ tiệm, lập biên bản; không tự bù, không sửa sổ. Cân kiểm bằng quả cân chuẩn trước khi bán.',
    'Tiệm chỉ bán trang sức và kiểm định đá. Vàng miếng và cầm đồ là nghề khác, cần giấy phép riêng.',
]

# ---------------------------------------------------------------- 🔔 desk surprises (kit.desk): chuyện ở tiệm
DESK = [
    dict(id='power_cut', title='Cúp điện, cân điện tử tắt ngúm', emoji='🔌', npc=0, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Đang đông khách thì cúp điện. Cân điện tử tắt, máy quét tuổi vàng cũng tắt. Hai khách đang chờ cân.',
         options=[dict(id='battery', label='Lấy cân dự phòng chạy pin đã kiểm chuẩn, mời khách đợi máy quét có điện lại', hint='',
                       effects=dict(xp=5, review=[5, 'Cúp điện mà tiệm vẫn cân bằng cân chuẩn, đàng hoàng.', 3]), good=True,
                       outcome='Cân dự phòng hiện đúng 10,00 g với quả cân chuẩn. Khách gật gù đợi.'),
                  dict(id='guess', label='Đoán trọng lượng bằng tay cho nhanh', hint='',
                       effects=dict(review=[1, 'Tiệm vàng mà cân bằng tay, ai dám tin.', 3]), good=False,
                       outcome='Khách nghi ngờ, bỏ về tiệm khác.'),
                  dict(id='wait', label='Đóng khay, mời khách quay lại sau', hint='', effects=dict(patience=-3), good=None,
                       outcome='Khách lầm bầm ra về, hẹn chiều quay lại.')],
         default='wait'),
    dict(id='crowd_tray', title='Một nhóm khách đông vây quầy', emoji='👥', npc=7, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Bốn người vào cùng lúc, hai người hỏi giá liên tục, một người đứng sát khay nhẫn đang mở.',
         options=[dict(id='one', label='Đóng khay lại, mỗi lần chỉ đưa ra một món, đếm lại trước khi lấy món khác', hint='',
                       effects=dict(xp=6), good=True, outcome='Nhóm khách đứng một lúc rồi đi. Đếm khay: đủ món.'),
                  dict(id='open', label='Bày hết khay ra cho khách chọn thoải mái', hint='',
                       effects=dict(stock={'vg_nhan_be': -1}), good=False,
                       outcome='Nhóm khách đi rồi, đếm khay thiếu một chiếc nhẫn bé.'),
                  dict(id='shout', label='Lớn tiếng đuổi cả nhóm ra', hint='', effects=dict(review=[2, 'Bước vào hỏi giá mà bị đuổi như kẻ trộm.', 4]), good=None,
                       outcome='Có một người là khách thật, bỏ đi luôn.')],
         default='one'),
    dict(id='police_list', title='Công an phường gửi danh sách đồ bị mất', emoji='👮', npc=0, min_day=3, tone='gentle', at='open', weight=2, mods=None,
         text='Anh công an khu vực gửi tờ danh sách trang sức bị mất trộm ở phường bên, nhờ các tiệm vàng để ý.',
         options=[dict(id='post', label='Dán danh sách ở quầy, dò lại sổ mua hàng mấy hôm nay', hint='', effects=dict(xp=6, mark='list_checked'), good=True,
                       outcome='Sổ mua hàng không có món nào khớp. Cô Ba gật đầu: “Sổ ghi kỹ là để lúc này.”'),
                  dict(id='drawer', label='Bỏ vào ngăn kéo, rảnh coi sau', hint='', effects=dict(), good=None,
                       outcome='Tờ danh sách nằm dưới xấp hóa đơn cả tuần.')],
         default='drawer'),
    dict(id='rush_news', title='Tin giá vàng tăng, khách xếp hàng mua', emoji='📈', npc=4, min_day=3, tone='tense', at='open', weight=2, mods=None,
         text='Mạng đồn giá vàng sắp tăng mạnh. Sáng mở cửa đã có hàng dài chờ mua nhẫn tròn. Anh Phát đề nghị: “Nâng giá lên đi, đông vậy mà.”',
         options=[dict(id='board', label='Phát số thứ tự, bán đúng bảng niêm yết, mỗi người tối đa hai chỉ', hint='',
                       effects=dict(xp=7, review=[5, 'Đông nghẹt mà tiệm bán đúng giá niêm yết, phát số đàng hoàng.', 3]), good=True,
                       outcome='Hàng chờ trật tự. Ai cũng mua được, không ai cãi nhau.'),
                  dict(id='raise', label='Nâng giá bán thêm vài xu mỗi chỉ', hint='', effects=dict(money=8, review=[1, 'Thấy đông là tăng giá, tiệm chặt chém.', 3]), good=False,
                       outcome='Có người chụp bảng giá đăng lên nhóm phường.')],
         default='board'),
    dict(id='fake_bill', title='Một tờ 500 xu nghi giả', emoji='💵', npc=7, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Khách trả tiền, Chú Tư rờ tờ 500 xu thấy trơn tuột, soi đèn không thấy hình chìm.',
         options=[dict(id='lamp', label='Soi đèn trước mặt khách, lịch sự nhờ khách đổi tờ khác', hint='', effects=dict(xp=5), good=True,
                       outcome='Khách đỏ mặt, đưa tờ khác: “Chắc người ta thối nhầm cho tui.”'),
                  dict(id='take', label='Nhận luôn cho khỏi mất lòng', hint='', effects=dict(money=-20, money_loss='normal'), good=False,
                       outcome='Cuối ngày ngân hàng không nhận tờ tiền đó. Tiệm mất 20 xu.')],
         default='take'),
    dict(id='safe_note', title='Mã két dán dưới quầy', emoji='🔐', npc=1, min_day=3, tone='gentle', at='open', weight=2, mods=None,
         text='Lau quầy buổi sáng, bạn thấy mảnh giấy dán dưới mặt quầy ghi sẵn mã mở két, chữ của ai đó trong tiệm.',
         options=[dict(id='change', label='Gỡ giấy, báo cô Ba đổi mã, mỗi người tự nhớ mã của mình', hint='', effects=dict(xp=6), good=True,
                       outcome='Cô Ba đổi mã ngay, dặn cả tiệm không ghi mã ra giấy.'),
                  dict(id='leave', label='Kệ, để đó lỡ quên còn có mà coi', hint='', effects=dict(mark='code_left'), good=False,
                       outcome='Mảnh giấy vẫn dán dưới quầy.')],
         default='leave'),
    dict(id='code_found', title='Người sửa máy lạnh nhìn dưới quầy', emoji='🛠️', npc=7, min_day=5, tone='tense', at='between', weight=5, mods=None,
         need_mark='code_left',
         text='Thợ sửa máy lạnh vào làm, chui xuống gầm quầy kéo dây, ở dưới đó khá lâu.',
         options=[dict(id='change', label='Đợi thợ về, đổi mã két ngay, gỡ mảnh giấy', hint='', effects=dict(xp=4, unmark='code_left'), good=True,
                       outcome='Mã mới chỉ cô Ba và bạn biết. Tối đó ngủ ngon.'),
                  dict(id='ignore', label='Thôi, chắc không ai để ý', hint='', effects=dict(unmark='code_left', money=-25, money_loss='normal'), good=False,
                       outcome='Vài hôm sau két hụt 25 xu, không ai giải thích được.')],
         default='change'),
    dict(id='acid', title='Chú Tư muốn dùng nước tẩy mạnh', emoji='🧪', npc=1, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Chú Tư đánh bóng một lố nhẫn cũ, hỏi có nên ngâm nước tẩy mạnh cho nhanh, dù chai ghi “làm mòn kim loại”.',
         options=[dict(id='slow', label='Đánh bóng bằng bột và vải như sổ tay, chậm mà không hao vàng', hint='', effects=dict(xp=5), good=True,
                       outcome='Lố nhẫn sáng lên, cân lại không hụt một ly.'),
                  dict(id='acid', label='Ngâm cho nhanh, khách đâu có biết', hint='', effects=dict(money=-10, money_loss='normal', review=[2, 'Nhẫn đánh bóng xong nhẹ hẳn, tiệm làm hao vàng của khách.', 3]), good=False,
                       outcome='Khách cân lại ở nhà, thấy hụt, quay lại hỏi. Tiệm phải bù.')],
         default='slow'),
    dict(id='old_watch', title='Ông Sáu nhờ định giá đồng hồ vàng', emoji='⌚', npc=5, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Ông Sáu mang chiếc đồng hồ vỏ vàng của ông nội: “Coi giùm cái này đáng bao nhiêu, tui tính bán.”',
         options=[dict(id='honest', label='Nói thật: tiệm chỉ mua theo vàng; đồng hồ cổ nên hỏi thợ đồng hồ trước khi bán vàng', hint='',
                       effects=dict(xp=5, review=[5, 'Tiệm nói thật, không ép bán theo giá vàng vụn.', 5]), good=True,
                       outcome='Ông Sáu mang đi hỏi thợ đồng hồ. Tuần sau ông quay lại, kể đồng hồ quý hơn vàng.'),
                  dict(id='scrap', label='Mua theo giá vàng vụn cho nhanh', hint='', effects=dict(money=6, review=[2, 'Đồ gia bảo mà tiệm mua như vàng vụn.', 5]), good=False,
                       outcome='Ông Sáu bán rồi, về nhà lại tiếc.')],
         default='honest'),
    dict(id='scale_check', title='Đoàn kiểm tra đo lường ghé tiệm', emoji='⚖️', npc=0, min_day=4, tone='gentle', at='open', weight=2, mods=None,
         text='Đoàn kiểm tra đo lường của phường ghé, hỏi tem kiểm định cân và sổ kiểm cân đầu ngày.',
         options=[dict(id='show', label='Đưa tem kiểm định và sổ kiểm cân mỗi sáng', hint='', effects=dict(xp=6), good=True,
                       outcome='Đoàn ghi biên bản đạt, khen tiệm ghi sổ kỹ.'),
                  dict(id='hide', label='Nói cân mới mua, chưa kịp kiểm', hint='', effects=dict(money=-15, money_loss='fine'), good=False,
                       outcome='Đoàn lập biên bản nhắc nhở và phạt 15 xu.')],
         default='show'),
    dict(id='pawn_ask', title='Hàng xóm xin “cầm” chiếc nhẫn', emoji='🏚️', npc=3, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Bà Năm Chợ thì thầm: “Cho tui cầm chiếc nhẫn này lấy ít tiền đóng học cho thằng nhỏ, cuối tuần tui chuộc.”',
         options=[dict(id='explain', label='Nói tiệm không làm cầm đồ; nếu bà muốn bán thì mua theo giá mua vào, ghi sổ đàng hoàng', hint='',
                       effects=dict(xp=5, review=[4, 'Tiệm nói rõ ràng, không lợi dụng lúc người ta kẹt.', 3]), good=True,
                       outcome='Bà Năm nghĩ một lúc, quyết giữ nhẫn, đi hỏi vay họ hàng.'),
                  dict(id='pawn', label='Nhận cầm, lấy lãi theo ngày', hint='', effects=dict(money=5, mark='pawned'), good=False,
                       outcome='Bà Năm cầm tiền đi. Tiệm giữ một chiếc nhẫn không có trong sổ nào.')],
         default='explain'),
    dict(id='pawn_check', title='Cán bộ phường hỏi chuyện cầm đồ', emoji='📋', npc=0, min_day=5, tone='tense', at='between', weight=5, mods=None,
         need_mark='pawned',
         text='Cán bộ phường ghé: có người phản ánh tiệm nhận cầm đồ không giấy phép, lấy lãi theo ngày.',
         options=[dict(id='own', label='Nhận lỗi, trả nhẫn cho bà Năm, không lấy lãi', hint='',
                       effects=dict(unmark='pawned', money=-10, money_loss='fine', review=[3, 'Tiệm có làm sai nhưng chịu sửa.', 0]), good=True,
                       outcome='Biên bản nhắc nhở. Bà Năm nhận lại nhẫn, cảm ơn vì tiệm không giữ lãi.'),
                  dict(id='deny', label='Chối, nói chỉ giữ giùm', hint='',
                       effects=dict(unmark='pawned', money=-30, money_loss='fine', review=[1, 'Tiệm vàng cầm đồ chui còn chối.', 0]), good=False,
                       outcome='Bà Năm kể lại hết. Tiệm bị phạt 30 xu.')],
         default='own'),
    dict(id='rain_window', title='Mưa tạt vào tủ kính', emoji='🌧️', npc=1, min_day=1, tone='gentle', at='any', weight=2, mods=None,
         text='Mưa to tạt nước vào mép tủ kính bày dây chuyền, sàn trơn trượt.',
         options=[dict(id='tidy', label='Kéo rèm, lau khô tủ, đặt biển “sàn trơn” trước cửa', hint='', effects=dict(xp=3), good=True,
                       outcome='Không ai trượt chân, dây chuyền vẫn khô ráo.'),
                  dict(id='later', label='Mưa tạnh rồi lau', hint='', effects=dict(patience=-2), good=None,
                       outcome='Một khách trượt chân suýt ngã ở cửa.')],
         default='tidy'),
    dict(id='gift_box', title='Bé Bông xin hộp nhung không', emoji='🎁', npc=6, min_day=1, tone='gentle', at='open', weight=2, mods=None,
         text='Con chị Thu theo mẹ ghé tiệm, nhìn chồng hộp nhung đỏ: “Cô cho con xin một cái để đựng kẹp tóc.”',
         options=[dict(id='give', label='Cho bé một hộp nhung cũ còn đẹp', hint='', effects=dict(xp=3, review=[5, 'Bé nhà tôi khoe hộp nhung cả tuần, cảm ơn tiệm.', 6]), good=True,
                       outcome='Bé ôm hộp nhung cười tít mắt.'),
                  dict(id='sell', label='Hộp nhung là tiền, muốn thì mua', hint='', effects=dict(money=1), good=None,
                       outcome='Chị Thu móc ra một xu, bé buồn thiu.')],
         default='give'),
]
