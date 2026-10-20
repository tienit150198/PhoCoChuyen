"""🏦 Ngân hàng — giao dịch viên: Quầy số 3 of the Bến Chợ transaction office of Ngân hàng Phố. Everything here is
fictional game content: rules, fees, rates and people. Money at the counter is the bank's cash, counted in nghìn đồng
(k), never the player's xu, wallet or bank account.
"""
from __future__ import annotations

PEOPLE = [
    ('Chị Hạnh', 'Trưởng quầy, người kèm bạn', 'Mười hai năm đứng quầy, đếm tiền nhanh như máy mà vẫn đếm lại lần hai.', 'picky'),
    ('Anh Quân', 'Giao dịch viên ca sáng, phụ trách ATM', 'Hay nhờ vả, nhanh tay báo cáo việc của người khác.', 'bossy'),
    ('Bà Lựu', 'Chủ quán trà đá gốc bàng', 'Bán trà ba mươi năm, đang dành tiền mua chiếc xe trà mới.', 'warm'),
    ('Dì Bảy', 'Chủ quán cơm tấm đầu chợ', 'Sáng nào cũng ghé đổi tiền lẻ, nói nhanh hơn máy đếm.', 'bossy'),
    ('Bác Lâm', 'Chủ quán phở gốc đa', 'Không tin máy đếm, chỉ tin mười đầu ngón tay mình.', 'sour'),
    ('Ông Khang', 'Hưu trí, cao thủ cờ tướng', 'Mã PIN đổi ba lần một năm, lần nào cũng quên.', 'sour'),
    ('Chị Thơ', 'Chủ tiệm album Mây Pop', 'Chuyển tiền nhập album cho nhà phân phối, lúc nào cũng vội.', 'genz'),
    ('Anh Hùng', 'Shipper', 'Nộp tiền thu hộ giữa hai cuốc xe, mũ bảo hiểm không kịp tháo.', 'quiet'),
    ('Ông Tài', 'Khách tự nhận quen giám đốc', 'Áo vest, kính râm, câu cửa miệng “tôi quen sếp các cô”.', 'bossy'),
    ('Chị Vy', 'Giám đốc phòng giao dịch', 'Chỉ tiêu treo đầy bảng trắng, tin nhắn tới lúc 22 giờ.', 'bossy'),
    ('Cụ Mến', 'Bà cụ bán vé số', 'Gom tiền lẻ cả năm trong hộp bánh quy thiếc.', 'warm'),
]
MENTOR, OPS, LUU, BAY, LAM, KHANG, THO, HUNG, TAI, VY, MEN = range(11)

# 💵 The counter's notes, in nghìn đồng. A bundle (cọc) is 10 notes of one value.
DENOMS = (500, 200, 100, 50, 20, 10)
DENOM_KEYS = tuple(str(d) for d in DENOMS)
BUNDLE = 10
TRAY_MAX = 300           # notes of one value on the tray at most

JOBS = {
    'withdraw': ('Rút tiền', '💵', 'giao_dich'),
    'change': ('Đổi tiền lẻ', '🪙', 'giao_dich'),
    'transfer': ('Chuyển tiền', '🔁', 'giao_dich'),
    'savings': ('Gửi tiết kiệm theo mục tiêu', '🐷', 'tu_van'),
    'atm': ('Tiếp quỹ ATM', '🏧', 'van_hanh'),
}
JOB_IDS = tuple(JOBS)
# The day's queue, slot by slot (pure: the same day and slot always bring the same kind of customer).
ROTA = ('withdraw', 'transfer', 'change', 'savings', 'withdraw', 'atm', 'transfer', 'change', 'withdraw', 'savings')
BONUS = dict(withdraw=6, change=6, transfer=7, savings=8, atm=7)
HANDOVER_BONUS = 3       # a clean handover at the end of the shift (xu, into the career fund)
WRONG_COST = 8           # quality lost per redone step
QUALITY_FLOOR = 60
GOOD = 90                # a job counts as good from this quality

# 🎓 Hiring inside the branch: học việc ngắn → thi thực hành → bảng tên → ca kèm cặp → giao dịch viên.
STAGES = ('learn', 'exam', 'training', 'teller')
STAGE_LABEL = dict(learn='Học việc', exam='Chờ thi thực hành', training='Tập sự (có người kèm)', teller='Giao dịch viên')
STAGE_PCT = dict(learn=50, exam=50, training=75, teller=100)   # the job bonus while learning
TRAINING = 2             # good shifts with chị Hạnh beside you before standing alone
TRAINING_GOOD = 2        # good jobs that make a training shift count
EXAM_FAST = 150          # seconds: ⚡ Thi nhanh
LESSONS = [
    dict(id='notes', emoji='💵', title='Đếm tiền theo cọc',
         text='Một cọc là 10 tờ cùng mệnh giá. Đếm hai lần: một lần bằng máy, một lần bằng tay, trước mặt khách.',
         ask='Dì Bảy cần 3 cọc tờ 20 nghìn. Đó là bao nhiêu tiền?',
         options=[('600', '600.000đ'), ('60', '60.000đ'), ('300', '300.000đ')], answer='600'),
    dict(id='check', emoji='🪪', title='Đối chiếu trước khi chi',
         text='Tên trên phiếu, ảnh và số trên CCCD phải khớp người đứng trước quầy. Số và chữ trên phiếu phải bằng nhau.',
         ask='Phiếu ghi số 2.350.000đ nhưng chữ ghi “hai triệu năm trăm ba mươi nghìn”. Làm gì?',
         options=[('ask', 'Dừng lại, hỏi khách, cho khách ký xác nhận số đúng'), ('digits', 'Làm theo số, số mới đúng'),
                  ('words', 'Làm theo chữ, chữ mới đúng')], answer='ask'),
    dict(id='flow', emoji='🧾', title='Năm bước một khách',
         text='Nhận yêu cầu → kiểm tra thông tin → xử lý tiền → xác nhận với khách → giao biên nhận. Không nhảy bước.',
         ask='Bước nào ngay trước khi giao biên nhận?',
         options=[('confirm', 'Xác nhận lại với khách'), ('money', 'Đếm tiền'), ('slip', 'Nhận phiếu yêu cầu')], answer='confirm'),
]

# 🏅 Promotion branches (inside the bank; the town's 🎖️ Thăng tiến ladder runs alongside).
BRANCHES = {
    'giao_dich': dict(label='Giao dịch', emoji='💵', jobs=('withdraw', 'change', 'transfer'),
                      ladder=('Giao dịch viên', 'Giao dịch viên cao cấp', 'Trưởng quầy')),
    'tu_van': dict(label='Tư vấn', emoji='🐷', jobs=('savings',),
                   ladder=('Giao dịch viên', 'Phụ trách khách quen', 'Chuyên viên mục tiêu tài chính')),
    'van_hanh': dict(label='Vận hành', emoji='🏧', jobs=('atm',),
                     ladder=('Giao dịch viên', 'Vận hành ATM', 'Kiểm soát giao dịch', 'Vận hành chi nhánh')),
    'quan_ly': dict(label='Quản lý', emoji='🗂️', jobs=('handover',), needs=('giao_dich', 2),
                    ladder=('Trưởng quầy', 'Quản lý chi nhánh')),
}
BRANCH_IDS = tuple(BRANCHES)
# Good jobs of the branch (for quan_ly: clean handovers) since its last step, to reach a rank; True = a review exam too.
RANK_NEEDS = {('giao_dich', 1): (8, False), ('giao_dich', 2): (16, True),
              ('tu_van', 1): (4, False), ('tu_van', 2): (10, True),
              ('van_hanh', 1): (3, False), ('van_hanh', 2): (6, False), ('van_hanh', 3): (10, True),
              ('quan_ly', 1): (6, True)}
RANK_PCT = 15            # +15% job bonus per rank of the job's branch
RECORD_KEYS = ('honest', 'by_book', 'shortcuts', 'covered')
RECORD_LABEL = dict(honest='Tư vấn đúng nhu cầu', by_book='Làm đúng quy trình', shortcuts='Đi tắt', covered='Bị nhận vơ công')

# ---------------------------------------------------------------- 💵 Rút tiền
WITHDRAW_NPC = (BAY, LAM, KHANG, THO, HUNG, LUU, MEN)
WISHES = [
    ('none', 'Khách không dặn gì thêm.', {}),
    ('no500', '“Đừng đưa tờ năm trăm nhé, ra chợ không ai thối.”', {'max': {'500': 0}}),
    ('lixi', '“Cho xin năm tờ năm chục để lì xì cho mấy đứa nhỏ.”', {'min': {'50': 5}}),
    ('small', '“Lấy toàn tờ một trăm trở xuống, đi chợ cho dễ.”', {'allowed': ['100', '50', '20', '10']}),
    ('few', '“Ít tờ nhất có thể, ví chật lắm rồi.”', {'fewest': True}),
]
OUT_LINES = {'200': 'Ngăn tờ 200 nghìn trong két vừa hết, không chi được tờ này.',
             '50': 'Ngăn tờ 50 nghìn hết sạch từ sáng, chưa kịp tiếp.'}
CHECK_OPTS = [('ok', 'Thông tin khớp, làm tiếp'), ('clarify', 'Số và chữ lệch nhau: dừng lại hỏi khách, khách ký xác nhận số đúng'),
              ('sign', 'Phiếu thiếu chữ ký: mời khách ký trước mặt mình'), ('refuse', 'Người đứng quầy không phải chủ tài khoản: chưa chi, hướng dẫn giấy ủy quyền')]
WD_VARIANTS = ('ok', 'ok', 'clarify', 'sign', 'refuse', 'ok')
RELATIVES = ['con trai', 'cháu nội', 'em vợ', 'hàng xóm']
CONFIRM_OPTS = [('count', 'Đếm lại từng tờ trước mặt khách, đọc to tổng số rồi mới đưa'),
                ('fast', 'Đưa luôn cả xấp cho nhanh, máy đếm rồi'),
                ('seal', 'Bỏ vào phong bì dán lại, khách về nhà tự đếm')]
RECEIPT_OPTS = [('own', 'Đưa liên khách cho chính khách, liên ngân hàng cất vào khay chứng từ'),
                ('both', 'Đưa cả hai liên cho khách giữ hộ'),
                ('none', 'Không cần biên nhận, khách quen mà')]
REFUSE_NEXT = [('poa', 'Giải thích cần chính chủ hoặc giấy ủy quyền có công chứng; đưa mẫu giấy ủy quyền'),
               ('call', 'Gọi điện cho chủ tài khoản, nghe đồng ý qua điện thoại là chi'),
               ('half', 'Chi trước một nửa cho đỡ mất lòng')]

# ---------------------------------------------------------------- 🪙 Đổi tiền lẻ
CHANGE_NPC = (BAY, LAM, LUU, THO)
CHANGE_SHOP = {BAY: 'quán cơm tấm', LAM: 'quán phở', LUU: 'quán trà đá', THO: 'tiệm album'}
BUNDLE_OPTS = [('band', 'Buộc từng cọc 10 tờ bằng dây thun, kẹp giấy ghi mệnh giá, đếm lại trước mặt khách'),
               ('loose', 'Để rời trong túi cho khách tự chia'),
               ('mix', 'Gom chung một xấp to cho gọn')]
LIST_OPTS = [('list', 'Ghi bảng kê đổi tiền: tiền nhận, từng cọc đã đưa, hai bên ký'),
             ('oral', 'Nói miệng là đủ, khách quen'),
             ('later', 'Để cuối ngày ghi bù')]

# ---------------------------------------------------------------- 🔁 Chuyển tiền
TRANSFER_NPC = (THO, HUNG, BAY, KHANG, LAM)
FACES_M = ('👨🏻‍🦱', '👴🏻', '🧔🏻', '👨🏻‍🦲')       # grown-ups only: every account holder and payee is an adult
FACES_F = ('👩🏻', '👱🏻‍♀️', '👩🏻‍🦳', '👵🏻')
FACES = FACES_M + FACES_F
# The face on a person's own slip and ID card (PEOPLE order): a woman's face for a woman, an old face for the old.
NPC_FACE = ('👩🏻', '👨🏻‍🦱', '👵🏻', '👩🏻', '👴🏻', '👴🏻', '👱🏻‍♀️', '🧔🏻', '👨🏻‍🦲', '👩🏻', '👵🏻')
NAMES = ('Nguyễn Văn An', 'Trần Thị Hoa', 'Lê Minh Tuấn', 'Phạm Thu Hà', 'Đỗ Văn Nam', 'Vũ Thị Lan')
NEAR = {'Nguyễn Văn An': 'Nguyễn Văn Ân', 'Trần Thị Hoa': 'Trần Thị Hòa', 'Lê Minh Tuấn': 'Lê Minh Tú',
        'Phạm Thu Hà': 'Phạm Thu Hằng', 'Đỗ Văn Nam': 'Đỗ Văn Năm', 'Vũ Thị Lan': 'Vũ Thị Lam'}
DETAILS = ('bán bánh mì đầu chợ', 'thợ sửa xe đạp', 'giáo viên trường tiểu học', 'chủ tiệm may', 'tài xế xe tải',
           'bán rau ở chợ Bến', 'thợ điện', 'y tá trạm xá')
PURPOSES = ('gửi tiền hàng', 'gửi tiền học cho con', 'trả tiền công', 'gửi tiền về quê', 'trả tiền mua xe cũ')
FEE_OTHER = 11           # nghìn đồng, to another bank (fictional)
READBACK_OPTS = [('read', 'Đọc lại tên, nghề và đuôi tài khoản người nhận cùng số tiền; khách gật đầu mới bấm chuyển'),
                 ('trust', 'Khách nói đúng rồi thì chuyển luôn'),
                 ('later', 'Chuyển trước, đọc lại sau')]
TRANSFER_RECEIPT = [('own', 'In ủy nhiệm chi, đưa liên khách cho chính người chuyển'),
                    ('photo', 'Chụp màn hình gửi Zalo cho khách là được'),
                    ('none', 'Không cần chứng từ')]

# ---------------------------------------------------------------- 🐷 Gửi tiết kiệm theo mục tiêu
GOALS = [
    # (npc, goal, emoji, goal amount, saved, months, flexible: may need part of it before the goal)
    (BAY, 'sửa lại mái quán cơm trước mùa mưa', '🏠', 24000, 6000, 12, True),
    (HUNG, 'mua chiếc xe máy mới chạy đơn', '🛵', 18000, 4800, 11, False),
    (THO, 'mở thêm một quầy album ở chợ đêm', '🏪', 30000, 9000, 14, False),
    (LAM, 'thay nồi nước dùng và tủ đông cho quán phở', '🍲', 15000, 3000, 10, True),
    (KHANG, 'đưa bà nhà đi du lịch dịp kỷ niệm 40 năm cưới', '🧳', 12000, 4200, 6, False),
]
ASK_OPTS = [('goal', 'Hỏi cần bao nhiêu, đã có bao nhiêu, bao lâu nữa cần và có lúc nào phải rút ra không'),
            ('salary', 'Hỏi lương tháng bao nhiêu để mời gói cao nhất'),
            ('insure', 'Mời mua bảo hiểm liên kết trước cho đủ chỉ tiêu')]
PRODUCTS = [('flex', 'Tích lũy linh hoạt: góp hằng tháng, rút một phần được, lãi thấp hơn'),
            ('goal', 'Tích lũy mục tiêu: góp hằng tháng tới đúng ngày mục tiêu, lãi cao hơn, rút trước hạn mất lãi'),
            ('lock', 'Kỳ hạn 36 tháng gửi một lần, khóa chặt'),
            ('coin', 'Quỹ Mây Coin lời nhanh, rủi ro cao')]
BOOK_OPTS = [('book', 'Đưa sổ tích lũy, hẹn ngày góp đầu mỗi tháng, dặn mang CCCD khi rút'),
             ('keep', 'Giữ sổ hộ khách cho khỏi mất'),
             ('none', 'Không cần đưa sổ, có tin nhắn là được')]
REMIND_OPTS = [('payday', 'Hẹn nhắc góp đúng ngày khách hay có tiền (cuối tuần chợ đông), ghi vào sổ khách quen'),
               ('daily', 'Nhắn tin nhắc mỗi ngày cho khỏi quên'),
               ('none', 'Thôi, khách tự nhớ')]

# 🍵 Bà Lựu's arc: saving for a new tea cart (stages 0..4; ARC_N = done: the cart is in the street).
ARC_N = 5
ARC_GOAL = 12000
ARC_SAVED = 2400
ARC_MONTHS = 8
ARC_MONTHLY = 1200
ARC_SHORT = 30           # her first bag is 30k short of what she says
ARC_STAGES = [
    dict(title='Bà Lựu muốn mua xe trà mới', emoji='🍵'),
    dict(title='Bà Lựu góp tháng đầu', emoji='👜'),
    dict(title='Cháu trai xin bà rút tiền', emoji='🛵'),
    dict(title='Đợt góp cuối cho chiếc xe', emoji='🧮'),
    dict(title='Trả tiền xe trà cho xưởng inox', emoji='💸'),
    dict(title='Bà Lựu gửi tiền bán trà', emoji='🍵'),
]
# Her deposits after the first month, before the last one (nghìn đồng); the last fills the goal.
ARC_DEPOSITS = (1200, 1200, 1200, 1200, 1200)
ARC_INTEREST = 84
CART_SHOPS = ('Xưởng inox Phát Đạt', 'Xưởng inox Phát Đạt', 'Xưởng inox Phát Lộc')
NEPHEW_OPTS = [('advise', 'Nói thật: rút bây giờ thì mất lãi và chậm mua xe; quyết định là của bà, cần thì rút một phần'),
               ('push', 'Khuyên rút hết cho cháu, người nhà cả mà'),
               ('lock', 'Nói dối là tiền đã khóa, không rút được')]
SHORT_OPTS = [('tell', 'Báo bà túi thiếu 30 nghìn, hỏi bà muốn gửi 1.170.000đ hay bù thêm'),
              ('fill', 'Tự bỏ 30 nghìn của mình bù cho đủ'),
              ('round', 'Ghi đủ 1.200.000đ, chắc bà đếm đúng')]

# ---------------------------------------------------------------- 🏧 Tiếp quỹ ATM
ATM_CAP = 400            # notes per cassette when full
ATM_LOW = 100            # below this, the cassette must be refilled
ATM_SLOTS = ('1', '2', '3', '4')
ATM_DENOMS = ('500', '200', '100', '50')
SEAL_OPTS = [('two', 'Hai người cùng mở máy, cùng đếm, cùng ký sổ, niêm phong rồi chạy thử một giao dịch'),
             ('alone', 'Một mình làm cho nhanh, anh Quân bận'),
             ('skip', 'Lắp xong là được, khỏi ghi sổ')]
ATM_LOG = [('jam', 'Kẹt tiền khe 2 lúc 02:14, máy tự trả lại', True),
           ('eat', 'Nuốt thẻ của khách lúc 06:40', True),
           ('short', 'Một lần chi thiếu 1 tờ, khách đã gọi tổng đài', True),
           ('ok1', 'Rút 2.000.000đ thành công lúc 07:05', False),
           ('ok2', 'Tra số dư lúc 07:20', False),
           ('ok3', 'Đổi PIN thành công lúc 08:02', False)]

# ---------------------------------------------------------------- 🧾 Đầu ca, cuối ca
FLOAT = 50000            # the drawer's float at opening (nghìn đồng)
ENVELOPES = [('500', 40), ('200', 50), ('100', 80), ('50', 120), ('20', 150), ('10', 200)]
OPEN_SIGN = [('sign', 'Đếm đủ, khớp sổ bàn giao: ký nhận quỹ'), ('report', 'Lệch sổ: chưa ký, lập biên bản với trưởng quầy')]
SHORT_DAY_EVERY = 5      # on day n with n % SHORT_DAY_EVERY == 3 the handed-over float is 200k short
PENDING_OPTS = [('log', 'Ghi sổ giao dịch treo, báo trưởng quầy, để biên bản cho ca sau'),
                ('cancel', 'Tự hủy giao dịch cho sổ đẹp'),
                ('ignore', 'Để đó, mai tính')]
TX_KINDS = [('dep', 'Gửi vào'), ('wd', 'Rút ra')]
ROSTERS = [  # tomorrow's roster for the manager: (option text, fits every constraint)
    ('Sáng: bạn quầy 3, chị Hạnh quầy 2, anh Quân ATM cùng chị Hạnh lúc 10:00; chiều: anh Quân quầy 3', True),
    ('Sáng: anh Quân quầy 3 và ATM một mình; chiều: bạn và chị Hạnh', False),
    ('Sáng: chỉ mở quầy 3; anh Quân nghỉ cả ngày; ATM để chiều tính', False),
]
ROSTER_RULES = 'Ngày mai là ngày nhận lương hưu: sáng cần hai quầy. Anh Quân xin nghỉ buổi sáng (đi khám), nhưng ATM sáng phải có hai người cùng ký.'
ROSTER_FIX = ('Anh Quân xin nghỉ sáng nhưng chưa ai thay; chị Hạnh đề nghị anh đổi giờ khám sang chiều.',)

# ---------------------------------------------------------------- 🗓️ The day's mood (kit.daily)
MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Khách đều, máy gọi số chạy ngon. Hợp để làm quen.', weight=3),
    dict(id='pension', emoji='👵', label='Ngày nhận lương hưu', hint='Các cụ xếp hàng từ 6 giờ sáng: nói chậm, đọc to, đếm tiền trước mặt các cụ.', min_day=2, weight=2),
    dict(id='month_end', emoji='📆', label='Cuối tháng', hint='Ai cũng chuyển tiền hàng, tiền nhà. Đọc lại tên người nhận thật kỹ.', min_day=2, weight=2),
    dict(id='slow', emoji='🐢', label='Hệ thống chậm', hint='Màn hình quay vòng lâu. Chưa thấy “thành công” thì chưa chi tiền.', min_day=3, weight=1),
    dict(id='rain', emoji='🌧️', label='Mưa to', hint='Ít khách nhưng tiền ướt: đếm chậm, tờ dính nhau.', min_day=2, weight=2),
]

# ---------------------------------------------------------------- 🔔 Oái oăm ở quầy (kit.desk scripts)
# Effects: generic kit keys plus 'record' {key: +n} (the career's own service record, shown in its profile and read by
# the promotion reviews). Marks make lasting consequences: a later script needs them.
DESK = [
    dict(id='short_float', title='Ca trước bàn giao quỹ thiếu', emoji='💼', npc=OPS, min_day=2, tone='tense', at='open', weight=3, mods=None,
         text='Mở két nhận quỹ, bạn đếm hụt 200 nghìn so với sổ bàn giao. Anh Quân ca trước đã về, nhắn: “Chắc em đếm nhầm, ký đại đi, chiều anh tính.”',
         options=[dict(id='audit', label='Tự kiểm lại từng phong bì và biên nhận của ca trước rồi mới ký', hint='Hàng chờ đợi thêm một lúc',
                       effects=dict(xp=6, patience=-6, record={'by_book': 1}, mark='audited'), good=True,
                       outcome='Tờ 200 nghìn kẹt trong phong bì biên nhận của khách rút lúc 16:58. Quỹ đủ, bạn ghi chú vào sổ.'),
                  dict(id='lead', label='Báo chị Hạnh lập biên bản, chưa ký nhận đủ', hint='',
                       effects=dict(xp=5, record={'by_book': 1}, mark='reported_gap'), good=True,
                       outcome='Chị Hạnh lập biên bản, hai bên ký. Chiều anh Quân quay lại tìm ra tờ tiền trong ngăn kéo phụ.'),
                  dict(id='sign', label='Ký đại cho kịp mở quầy', hint='Nhanh nhất',
                       effects=dict(record={'shortcuts': 1}, mark='signed_short'), good=False,
                       outcome='Quầy mở đúng giờ. Nhưng từ giờ, 200 nghìn thiếu là của ca bạn.')],
         default='sign'),
    dict(id='short_blame', title='Kiểm quỹ đột xuất: quỹ ca bạn thiếu', emoji='🔍', npc=MENTOR, min_day=3, tone='tense', at='between', weight=5,
         mods=None, need_mark='signed_short',
         text='Kiểm soát viên kiểm quỹ đột xuất: thiếu 200 nghìn. Chữ ký nhận đủ hôm trước là của bạn.',
         options=[dict(id='own', label='Nhận đã ký vội, xin xem lại camera giờ bàn giao', hint='',
                       effects=dict(xp=4, record={'by_book': 1}, unmark='signed_short'), good=True,
                       outcome='Camera cho thấy tờ tiền nằm lại trong ngăn kéo anh Quân. Chị Hạnh dặn: “Lệch là không ký, lần sau nhé.”'),
                  dict(id='blame', label='Đổ hết cho anh Quân', hint='',
                       effects=dict(review=[2, 'Ký nhận đủ rồi lại đổ cho đồng nghiệp, phòng giao dịch mất đoàn kết.', MENTOR], unmark='signed_short'), good=False,
                       outcome='Anh Quân giận, cả quầy nói chuyện nhỏ nhẹ với nhau suốt một tuần.'),
                  dict(id='pay', label='Ký biên bản thiếu, đền 6 xu', hint='',
                       effects=dict(money=-6, money_loss='fine', unmark='signed_short'), good=None,
                       outcome='Bạn đền 6 xu. Chuyện khép lại, bài học thì còn.')],
         default='pay'),
    dict(id='cake_box', title='Hộp bánh đầy tiền lẻ', emoji='🍪', npc=MEN, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Cụ Mến đặt lên quầy một hộp bánh quy thiếc: “Tiền lẻ bà gom cả năm, gửi hết giúp bà.” Trong hộp còn cúc áo, tem thư và một chiếc nhẫn bạc cũ. Hàng chờ dài dần.',
         options=[dict(id='sort', label='Đếm từng tờ trước mặt cụ, nhặt đồ lạ ra trả cụ, xin lỗi hàng chờ', hint='Hàng chờ mất kiên nhẫn',
                       effects=dict(xp=6, patience=-12, mark='keepsake', review=[5, 'Cô cậu ở quầy 3 đếm từng tờ cho bà, còn tìm lại được chiếc nhẫn của ông nhà.']), good=True,
                       outcome='Đếm xong 1.236.000đ. Chiếc nhẫn bạc là nhẫn cưới của ông nhà, cụ tưởng mất từ năm ngoái.'),
                  dict(id='machine', label='Đổ cả hộp vào máy đếm cho nhanh', hint='',
                       effects=dict(patience=-6, mark='lost_ring', review=[2, 'Đổ cả hộp của bà vào máy, cái nhẫn rơi đâu mất.']), good=False,
                       outcome='Cúc áo kẹt máy, máy đếm nghỉ nửa tiếng. Chiếc nhẫn rơi đâu không rõ.'),
                  dict(id='later', label='Hẹn cụ chiều quay lại, giờ đông quá', hint='', effects=dict(patience=-2), good=None,
                       outcome='Cụ ngồi ghế đá chờ suốt buổi trưa, ôm khư khư hộp bánh.')],
         default='later'),
    dict(id='keepsake_story', title='Cháu nội cụ Mến quay lại', emoji='💍', npc=MEN, min_day=3, tone='gentle', at='between', weight=5, mods=None,
         need_mark='keepsake',
         text='Cháu nội cụ Mến mang tới gói xôi: “Nhờ quầy giữ lại chiếc nhẫn, bà cháu kể chuyện ông bà quen nhau ở bến đò cả tối.” Cậu muốn mở cho bà một sổ nhỏ để dành tiền thuốc.',
         options=[dict(id='own', label='Hướng dẫn mở sổ đứng tên chính cụ, cụ tự ký, cháu đi cùng', hint='',
                       effects=dict(xp=8, record={'honest': 1}, unmark='keepsake', review=[5, 'Sổ đứng tên bà, bà tự ký, cháu đứng cạnh. Tử tế ghê.']), good=True,
                       outcome='Cụ Mến ký nắn nót tên mình, rồi kể nốt chuyện bến đò cho cả quầy nghe.'),
                  dict(id='grand', label='Mở sổ đứng tên cháu cho tiện', hint='',
                       effects=dict(unmark='keepsake', record={'shortcuts': 1}, review=[2, 'Tiền của bà mà sổ lại đứng tên cháu.']), good=False,
                       outcome='Hai tháng sau sổ bị rút sạch. Cụ không biết, cháu không nói.'),
                  dict(id='later', label='Nhận gói xôi, hẹn hôm khác', hint='', effects=dict(unmark='keepsake'), good=None,
                       outcome='Gói xôi còn ấm, chuyện mở sổ để hôm khác.')],
         default='later'),
    dict(id='vip', title='Khách tự nhận quen giám đốc', emoji='🕶️', npc=TAI, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Ông Tài gõ kính râm lên quầy: “Tôi chỗ quen với giám đốc Vy. Rút cho tôi năm mươi triệu ngay, khỏi bốc số, khỏi giấy tờ.”',
         options=[dict(id='queue', label='Mời ông bốc số như mọi người; tới lượt thì kiểm CCCD như thường lệ', hint='',
                       effects=dict(record={'by_book': 1}, mark='by_the_book'),
                       luck=dict(p=0.6, win=dict(effects=dict(xp=6), good=True, outcome='Giám đốc Vy đi ngang, cười: “Đúng quy trình là đúng.” Ông Tài lẩm bẩm rồi cũng bốc số.'),
                                 lose=dict(effects=dict(xp=4, review=[2, 'Quầy số 3 làm khó khách quen của giám đốc.', TAI]), good=True,
                                           outcome='Ông Tài chê ầm lên mạng. Giám đốc Vy đọc xong vẫn ghi nhận bạn làm đúng.')),
                       good=True),
                  dict(id='skip', label='Cho ông lên trước, bỏ qua kiểm giấy tờ', hint='Nhanh nhất',
                       effects=dict(patience=-10, mark='skipped_check', record={'shortcuts': 1},
                                    review=[1, 'Đứng chờ bốn mươi phút mà có người chen ngang vì quen sếp.', HUNG]), good=False,
                       outcome='Ông Tài cầm tiền đi thẳng. Hàng chờ nhìn bạn không chớp mắt.'),
                  dict(id='call', label='Gọi điện hỏi giám đốc Vy ngay trước mặt ông', hint='', effects=dict(patience=-3), good=None,
                       outcome='Giám đốc Vy: “Ông nào cơ? Chị không quen.” Ông Tài bỏ về, hàng chờ cười ồ.')],
         default='call'),
    dict(id='fraud_call', title='Chủ tài khoản thật gọi tới', emoji='📞', npc=MENTOR, min_day=3, tone='tense', at='between', weight=5, mods=None,
         need_mark='skipped_check',
         text='Một bà cụ gọi lên chi nhánh: hôm qua có người rút năm mươi triệu từ tài khoản của bà, mà bà không hề ra ngân hàng.',
         options=[dict(id='tell', label='Thành thật báo chị Hạnh mình đã bỏ qua kiểm CCCD, cùng làm hồ sơ tra soát', hint='',
                       effects=dict(xp=4, record={'by_book': 1}, unmark='skipped_check'), good=True,
                       outcome='Camera cho thấy người rút là cháu bà. Bà tự giải quyết trong nhà; chi nhánh siết lại quy trình.'),
                  dict(id='hide', label='Im lặng, đổ cho lỗi hệ thống', hint='',
                       effects=dict(record={'shortcuts': 1}, unmark='skipped_check',
                                    review=[1, 'Bỏ qua kiểm giấy tờ rồi im lặng khi có chuyện. Không chấp nhận được.', MENTOR]), good=False,
                       outcome='Camera vẫn ra. Bạn bị ghi một lỗi vào hồ sơ thi đua.')],
         default='hide'),
    dict(id='came_back', title='Khách quay lại bảo đưa thiếu tiền', emoji='😤', npc=LAM, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Bác Lâm vừa rút 3 triệu, mười phút sau quay lại đập quầy: “Thiếu một tờ năm trăm! Đếm lại cho tôi!”',
         options=[dict(id='check', label='Mời bác ngồi; đếm lại quỹ quầy, xem biên nhận, camera và cả túi của bác', hint='',
                       effects={}, good=True,
                       luck=dict(p=0.75, win=dict(effects=dict(xp=6), good=True, outcome='Tờ năm trăm kẹp trong cuốn sổ nợ của bác. Bác đỏ mặt, mua tặng cả quầy chè đậu.'),
                                 lose=dict(effects=dict(xp=4, review=[3, 'Quầy kiểm kỹ, camera rõ ràng. Thôi tôi về tìm lại.']), good=True,
                                           outcome='Quỹ quầy khớp, camera rõ bạn đếm đủ sáu tờ. Bác vẫn càu nhàu nhưng chịu về tìm lại.'))),
                  dict(id='pay', label='Lấy tiền quỹ bù luôn cho êm', hint='',
                       effects=dict(mark='drawer_short', record={'shortcuts': 1}), good=False,
                       outcome='Bác về. Tối kiểm quỹ thiếu đúng 500 nghìn; tờ tiền nằm trong túi áo bác.'),
                  dict(id='argue', label='Khẳng định mình đếm đủ, mời bác về', hint='',
                       effects=dict(review=[2, 'Giao dịch viên cãi tay đôi với khách lớn tuổi.']), good=None,
                       outcome='Bác về, vừa đi vừa nói to cho cả chợ nghe.')],
         default='argue'),
    dict(id='drawer_hole', title='Quỹ quầy hụt 500 nghìn', emoji='🕳️', npc=MENTOR, min_day=3, tone='tense', at='open', weight=5, mods=None,
         need_mark='drawer_short',
         text='Chị Hạnh cầm sổ quỹ: “Hôm trước em lấy quỹ bù cho khách mà không lập biên bản. Giờ quỹ hụt 500 nghìn, tính sao?”',
         options=[dict(id='report', label='Viết tường trình, nhận đã làm sai quy trình, xin đối chiếu với khách', hint='',
                       effects=dict(xp=3, record={'by_book': 1}, unmark='drawer_short'), good=True,
                       outcome='Bác Lâm nghe chuyện, lục túi áo, đem trả tờ năm trăm kèm một tô phở.'),
                  dict(id='pay', label='Đền 8 xu cho xong', hint='', effects=dict(money=-8, money_loss='fine', unmark='drawer_short'), good=None,
                       outcome='Quỹ đủ lại. Chị Hạnh ghi chú: “Bù quỹ phải có biên bản.”')],
         default='pay'),
    dict(id='ticket', title='Máy gọi số in ba vé cùng số 027', emoji='🎫', npc=HUNG, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Máy lấy số trục trặc: ba người cùng cầm vé 027 đứng trước quầy, ai cũng bảo mình tới trước.',
         options=[dict(id='time', label='Xem giờ in trên từng vé, phục vụ theo giờ; báo anh Quân khởi động lại máy, ghi sổ sự cố', hint='',
                       effects=dict(xp=5, record={'by_book': 1}), good=True,
                       outcome='Vé in sớm nhất là của anh Hùng, 07:58. Hai người còn lại gật gù, máy chạy lại từ số 028.'),
                  dict(id='loud', label='Phục vụ người nói to nhất cho nhanh', hint='',
                       effects=dict(review=[2, 'Cùng số mà ai to mồm hơn được làm trước.']), good=False,
                       outcome='Hai người còn lại cãi nhau ngay giữa sảnh.'),
                  dict(id='rps', label='Cho ba người oẳn tù tì', hint='', effects=dict(patience=-2), good=None,
                       outcome='Anh Hùng ra búa, thắng. Cả sảnh vỗ tay, nhưng chị Hạnh lắc đầu.')],
         default='rps'),
    dict(id='upsell', title='Sếp ép bán gói không hợp với khách', emoji='📈', npc=VY, min_day=3, tone='tense', at='between', weight=3, mods=None,
         text='Giám đốc Vy nhắn: “Quầy 3 còn thiếu 4 hợp đồng bảo hiểm liên kết. Cụ vừa gửi tiết kiệm kia, mời luôn gói 15 năm.” Cụ chỉ cần chỗ cất tiền thuốc.',
         options=[dict(id='honest', label='Tư vấn đúng nhu cầu của cụ: tích lũy linh hoạt; ghi lý do vào sổ tư vấn', hint='Không đủ chỉ tiêu tháng này',
                       effects=dict(xp=6, record={'honest': 1}, mark='honest_advice', review=[5, 'Giao dịch viên nói thật, không ép mua gì.', MEN]), good=True,
                       outcome='Cụ cầm sổ ra về yên tâm. Sổ tư vấn ghi rõ lý do; buổi xét lên chức, người ta sẽ lật đúng trang này.'),
                  dict(id='sell', label='Mời gói 15 năm cho đủ chỉ tiêu', hint='Sếp vui',
                       effects=dict(xp=2, mark='missold', record={'shortcuts': 1}), good=False,
                       outcome='Đủ chỉ tiêu, giám đốc thả tim. Cụ ký mà không đọc hết.'),
                  dict(id='talk', label='Nhắn lại sếp: gói này không hợp cụ, xin tìm khách khác có nhu cầu', hint='',
                       effects=dict(xp=4, record={'honest': 1}), good=True,
                       outcome='Giám đốc Vy im một lúc rồi trả lời: “Ừ. Tìm khách khác.”')],
         default='sell'),
    dict(id='missold_back', title='Cụ quay lại đòi hủy hợp đồng', emoji='📄', npc=MEN, min_day=4, tone='tense', at='between', weight=5, mods=None,
         need_mark='missold',
         text='Cụ cầm hợp đồng 15 năm quay lại, mắt đỏ hoe: tháng này cụ không đủ tiền đóng phí, lại cần tiền thuốc.',
         options=[dict(id='cancel', label='Xin lỗi cụ, hướng dẫn hủy trong thời gian cân nhắc, nhận lại phí theo hợp đồng', hint='',
                       effects=dict(xp=4, record={'honest': 1}, unmark='missold', review=[4, 'Cô cậu nhận sai, giúp bà hủy kịp hạn.']), good=True,
                       outcome='Cụ nhận lại tiền phí, gửi vào sổ linh hoạt. Bạn tự hứa không bán kiểu đó nữa.'),
                  dict(id='keep', label='Bảo cụ cố đóng cho đủ năm', hint='',
                       effects=dict(unmark='missold', review=[1, 'Bán cho bà gói không hợp rồi bảo bà cố đóng.']), good=False,
                       outcome='Cụ về, bỏ bớt một đợt thuốc.'),
                  dict(id='pass', label='Chỉ sang quầy bảo hiểm', hint='', effects=dict(unmark='missold', review=[2, 'Bán thì nhiệt tình, hủy thì đẩy đi.']), good=None,
                       outcome='Cụ đi vòng hai quầy rồi mới hủy được.')],
         default='pass'),
    dict(id='credit', title='Đồng nghiệp nhờ làm hộ rồi nhận công', emoji='🙃', npc=OPS, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Anh Quân dúi tập hồ sơ mở thẻ: “Làm hộ anh mấy bộ này, anh ra ATM chút.” Tuần trước anh mang đúng tập bạn làm đi báo cáo là của anh.',
         options=[dict(id='log', label='Làm hộ nhưng ghi tên người thực hiện trên nhật ký hệ thống như quy định', hint='',
                       effects=dict(xp=5, record={'by_book': 1}), good=True,
                       outcome='Cuối tháng, bảng thi đua ghi đúng tên bạn. Anh Quân cười trừ.'),
                  dict(id='quiet', label='Làm hộ, không nói gì', hint='',
                       effects=dict(mark='used_by_quan', record={'covered': 1}), good=None,
                       outcome='Anh Quân lại báo cáo là của anh. Chị Hạnh khen anh trước cả phòng.'),
                  dict(id='no', label='Từ chối: quầy em đang đông', hint='', effects=dict(patience=-1), good=None,
                       outcome='Anh Quân lầm bầm tự làm. Hồ sơ trễ một ngày.')],
         default='quiet'),
    dict(id='quan_sign', title='Anh Quân nhờ ký thay ô kiểm soát', emoji='✍️', npc=OPS, min_day=3, tone='tense', at='between', weight=5, mods=None,
         need_mark='used_by_quan',
         text='Anh Quân đưa tờ phiếu chi: “Ký giùm anh ô kiểm soát, anh ký ô lập rồi. Chỗ anh em mà.”',
         options=[dict(id='refuse', label='Không ký: ô kiểm soát phải do người thật sự kiểm', hint='',
                       effects=dict(xp=5, record={'by_book': 1}, unmark='used_by_quan'), good=True,
                       outcome='Anh Quân đỏ mặt, mang phiếu sang chị Hạnh. Từ đó anh thôi nhờ vả kiểu cũ.'),
                  dict(id='sign', label='Ký cho xong', hint='',
                       effects=dict(record={'shortcuts': 1}, unmark='used_by_quan', review=[2, 'Ký kiểm soát mà không kiểm gì cả.', MENTOR]), good=False,
                       outcome='Phiếu chi đó sai số. Chữ ký kiểm soát là của bạn.'),
                  dict(id='report', label='Báo chị Hạnh chuyện anh nhờ ký thay', hint='',
                       effects=dict(xp=3, record={'by_book': 1}, unmark='used_by_quan'), good=True,
                       outcome='Chị Hạnh nhắc cả phòng: không ai ký thay ai.')],
         default='sign'),
    dict(id='fake', title='Tờ tiền nghi giả', emoji='🔦', npc=THO, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Trong xấp tiền gửi của chị Thơ có một tờ 500 nghìn mờ hình chìm, sờ không thấy nổi.',
         options=[dict(id='proc', label='Soi đèn, kiểm máy, mời chị chứng kiến, lập biên bản tạm giữ theo quy định', hint='',
                       effects=dict(xp=6, record={'by_book': 1}), good=True,
                       outcome='Đúng là tiền giả. Chị Thơ nhớ ra của một khách mua album sáng nay; biên bản giúp chị báo công an phường.'),
                  dict(id='back', label='Trả lại, bảo chị tiêu chỗ khác', hint='',
                       effects=dict(record={'shortcuts': 1}), good=False,
                       outcome='Tờ giả đi tiếp ra chợ. Chiều, bác Lâm phở cầm phải.'),
                  dict(id='take', label='Nhận luôn cho êm', hint='',
                       effects=dict(mark='drawer_short', review=[2, 'Quầy nhận cả tiền giả rồi cuối ngày tìm người chịu.', MENTOR]), good=False,
                       outcome='Cuối ngày máy đếm loại ra một tờ giả trong quỹ của bạn.')],
         default='take'),
    dict(id='pin', title='Ông Khang quên mã PIN lần thứ ba', emoji='🔢', npc=KHANG, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Ông Khang đập thẻ xuống quầy: “Máy nó khóa thẻ rồi! Mã là ngày sinh con gái hay ngày cưới bà ấy, cô xem trong máy giúp tôi.”',
         options=[dict(id='reset', label='Giải thích ngân hàng không xem được PIN; làm thủ tục cấp lại với CCCD chính chủ, ông tự đặt số mới', hint='',
                       effects=dict(xp=5, review=[5, 'Cô giải thích dễ hiểu, tôi tự đặt mã mới, nhớ được luôn.']), good=True,
                       outcome='Ông Khang đặt mã mới là nước đi cờ ông thích nhất. Ông bảo lần này không quên.'),
                  dict(id='daughter', label='Gọi con gái ông hỏi giúp ngày sinh', hint='',
                       effects=dict(review=[2, 'Gọi cho con tôi hỏi mã thẻ của tôi, ra cái thể thống gì.']), good=False,
                       outcome='Con gái ông hốt hoảng tưởng bố bị lừa, gọi lại tới năm cuộc.'),
                  dict(id='write', label='Đặt PIN mới rồi viết lên mặt sau thẻ cho dễ nhớ', hint='', effects=dict(mark='pin_on_card'), good=False,
                       outcome='Ông Khang cảm ơn rối rít, nhét thẻ vào ví.')],
         default='daughter'),
    dict(id='pin_stolen', title='Thẻ có PIN viết sau lưng bị nhặt mất', emoji='🃏', npc=KHANG, min_day=3, tone='tense', at='between', weight=5, mods=None,
         need_mark='pin_on_card',
         text='Ông Khang đánh rơi ví ở quán trà đá. Ai đó nhặt được thẻ có mã PIN viết sau lưng và rút mất 2 triệu.',
         options=[dict(id='lock', label='Khóa thẻ ngay, làm đơn tra soát, nhận lỗi đã viết PIN lên thẻ', hint='',
                       effects=dict(xp=3, record={'by_book': 1}, unmark='pin_on_card', review=[3, 'Mất tiền thì bực, nhưng cô nhận lỗi và lo giấy tờ ngay.']), good=True,
                       outcome='Camera ATM ghi được người rút. Công an phường đang làm việc.'),
                  dict(id='blame', label='Bảo ông tự bất cẩn', hint='',
                       effects=dict(unmark='pin_on_card', review=[1, 'Chính cô viết mã lên thẻ tôi mà giờ đổ cho tôi.']), good=False,
                       outcome='Ông Khang đứng giữa sảnh kể cho mọi người nghe ai đã viết mã lên thẻ ông.')],
         default='blame'),
    dict(id='net_down', title='Mất mạng giữa giao dịch', emoji='📡', npc=HUNG, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Đang nộp 4 triệu tiền thu hộ cho anh Hùng thì màn hình quay vòng rồi báo mất kết nối. Chưa rõ đã ghi nhận chưa; anh Hùng còn ba đơn chờ giao.',
         options=[dict(id='hold', label='Dừng lại, ghi phiếu tạm hai chữ ký, cất riêng số tiền, chờ tra cứu rồi mới xác nhận', hint='Anh Hùng phải chờ',
                       effects=dict(xp=6, patience=-5, record={'by_book': 1}), good=True,
                       outcome='Mười phút sau mạng có lại: giao dịch chưa ghi. Làm lại một lần, sổ khớp từng đồng.'),
                  dict(id='redo', label='Làm lại giao dịch lần nữa cho chắc', hint='',
                       effects=dict(mark='double_post', record={'shortcuts': 1}), good=False,
                       outcome='Mạng có lại: tài khoản anh Hùng được ghi hai lần 4 triệu.'),
                  dict(id='send', label='Bảo anh Hùng mai quay lại', hint='', effects=dict(review=[2, 'Mất mạng là đuổi khách về, tiền thu hộ của người ta biết để đâu.']), good=None,
                       outcome='Anh Hùng ôm 4 triệu đi giao ba đơn, lo nơm nớp cả buổi.')],
         default='send'),
    dict(id='double_fix', title='Một khoản bị ghi hai lần', emoji='🧮', npc=HUNG, min_day=3, tone='tense', at='open', weight=5, mods=None,
         need_mark='double_post',
         text='Đối soát đầu ngày: tài khoản anh Hùng dư 4 triệu do ghi hai lần. Anh Hùng đã tiêu mất một nửa.',
         options=[dict(id='fix', label='Báo kiểm soát, gọi anh Hùng giải thích, lập thỏa thuận hoàn trả', hint='',
                       effects=dict(xp=3, record={'by_book': 1}, unmark='double_post'), good=True,
                       outcome='Anh Hùng gãi đầu, hẹn trả dần trong tuần. Sổ đã khớp lại.'),
                  dict(id='hide', label='Tự trừ tài khoản anh Hùng không báo ai', hint='',
                       effects=dict(record={'shortcuts': 1}, unmark='double_post', review=[1, 'Tự dưng tài khoản bị trừ không ai nói một câu.']), good=False,
                       outcome='Anh Hùng phát hiện, khiếu nại lên giám đốc.')],
         default='hide'),
    dict(id='digits', title='Khách đọc sai số tài khoản', emoji='🔢', npc=THO, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Chị Thơ đọc số tài khoản nhà phân phối: “…0 4 7 1 9 9 3”. Màn hình hiện người nhận NGUYEN THI HOA, mà nhà phân phối là Công ty Mây Pop.',
         options=[dict(id='verify', label='Dừng lại; đọc lại từng số, nhờ chị xem lại giấy báo; tên phải khớp mới chuyển', hint='',
                       effects=dict(xp=6, record={'by_book': 1}), good=True,
                       outcome='Chị Thơ đọc nhầm số 1 thành 7. Số đúng hiện CONG TY MAY POP. Chị thở phào.'),
                  dict(id='send', label='Chuyển theo số chị đọc, chị bảo đúng rồi', hint='', effects=dict(mark='misdirected'), good=False,
                       outcome='Tiền đi. Chị Thơ vui vẻ về tiệm.'),
                  dict(id='ask', label='Hỏi chị có chắc không rồi chuyển', hint='',
                       effects={}, good=None,
                       luck=dict(p=0.3, win=dict(effects=dict(xp=2), good=None, outcome='Chị Thơ ngập ngừng, mở lại giấy báo, thấy mình đọc nhầm.'),
                                 lose=dict(effects=dict(mark='misdirected'), good=False, outcome='“Chắc mà!” Tiền đi vào tài khoản Nguyễn Thị Hoa.')))],
         default='ask'),
    dict(id='recall', title='Khoản chuyển nhầm cần gọi lại', emoji='↩️', npc=THO, min_day=3, tone='tense', at='between', weight=5, mods=None,
         need_mark='misdirected',
         text='Hôm trước 8 triệu của chị Thơ đã vào tài khoản Nguyễn Thị Hoa. Nhà phân phối đòi tiền hàng, chị Thơ khóc ở quầy.',
         options=[dict(id='recall', label='Lập đề nghị tra soát, hoàn trả gửi ngân hàng nhận; nói rõ quy trình và thời gian cho chị', hint='',
                       effects=dict(xp=5, record={'by_book': 1}, unmark='misdirected', review=[4, 'Quầy nhận phần mình, làm giấy đòi lại tiền ngay. Ba hôm sau tiền về.']), good=True,
                       outcome='Bà Hoa ở tỉnh khác đồng ý hoàn trả. Ba hôm sau 8 triệu về lại tài khoản chị Thơ.'),
                  dict(id='threat', label='Tự tra số điện thoại người nhận rồi gọi đòi', hint='',
                       effects=dict(unmark='misdirected', record={'shortcuts': 1}, review=[1, 'Nhân viên tự lấy thông tin khách đi gọi đòi tiền.', VY]), good=False,
                       outcome='Bà Hoa khiếu nại ngân hàng làm lộ thông tin. Giám đốc Vy gọi bạn lên phòng.'),
                  dict(id='shrug', label='Bảo chị tự lo, chị đọc số mà', hint='',
                       effects=dict(unmark='misdirected', review=[1, 'Mình đọc nhầm thật, nhưng quầy cũng đâu đọc lại cho mình.']), good=False,
                       outcome='Chị Thơ phải tự đi ba chi nhánh mới làm được giấy tra soát.')],
         default='shrug'),
    dict(id='recall_other', title='Có người chuyển nhầm vào tài khoản bác Lâm', emoji='📨', npc=LAM, min_day=5, tone='gentle', at='between', weight=2, mods=None,
         text='Ngân hàng bên kia gửi đề nghị hoàn trả: một khách ở tỉnh xa chuyển nhầm 3 triệu vào tài khoản bác Lâm. Bác bảo: “Tiền vào túi tôi là của tôi!”',
         options=[dict(id='explain', label='Giải thích tiền chuyển nhầm phải trả lại; mời bác ký đồng ý hoàn trả, giữ thông tin người chuyển kín', hint='',
                       effects=dict(xp=5, record={'by_book': 1}, review=[4, 'Cô cậu nói phải trái rõ ràng, tôi ký trả. Tiền không phải của mình thì thôi.']), good=True,
                       outcome='Bác Lâm ký, rồi kể cả buổi về lần bác đánh rơi ví ở bến xe.'),
                  dict(id='freeze', label='Tự ý trừ tiền tài khoản bác không hỏi', hint='',
                       effects=dict(record={'shortcuts': 1}, review=[1, 'Tự dưng trừ tiền của tôi, ngân hàng gì kỳ vậy!']), good=False,
                       outcome='Bác Lâm mang cả xoong nước dùng ra đứng trước cửa phòng giao dịch.'),
                  dict(id='leave', label='Kệ, để bác quyết', hint='', effects=dict(patience=-2), good=None,
                       outcome='Hồ sơ treo một tuần, hai bên gọi qua gọi lại.')],
         default='leave'),
    dict(id='livestream', title='Khách livestream ngay tại quầy', emoji='📱', npc=THO, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một bạn trẻ dựng điện thoại livestream “một ngày đi rút tiền”, quay rõ màn hình và CCCD của khách quầy bên.',
         options=[dict(id='ask', label='Lịch sự nhờ bạn quay về phía mình, không quay giấy tờ và màn hình người khác', hint='',
                       effects=dict(xp=4, record={'by_book': 1}), good=True,
                       outcome='Bạn trẻ xoay máy, còn khen “ngân hàng xịn ghê” trên sóng.'),
                  dict(id='let', label='Kệ, người ta có quyền quay', hint='',
                       effects=dict(review=[2, 'Ra ngân hàng mà CCCD của mình lên livestream.', KHANG]), good=False,
                       outcome='Ông Khang thấy CCCD của mình trên mạng, gọi lên chi nhánh.'),
                  dict(id='yell', label='Quát tắt máy ngay', hint='', effects=dict(review=[3, 'Nhắc thì đúng, mà quát to quá.']), good=None,
                       outcome='Buổi live đổi tiêu đề thành “bị giao dịch viên quát”.')],
         default='let'),
    dict(id='rain_notes', title='Xấp tiền ướt dính chặt', emoji='💧', npc=BAY, min_day=2, tone='gentle', at='between', weight=2, mods=('rain',),
         text='Dì Bảy chạy mưa vào, đặt lên quầy một xấp tiền ướt sũng dính vào nhau: “Đổi lẹ cho dì, dì về dọn hàng!”',
         options=[dict(id='dry', label='Tách từng tờ bằng tay, kẹp giấy thấm, đếm chậm hai lần', hint='Mất thêm thời gian',
                       effects=dict(xp=4, patience=-4), good=True, outcome='Đủ 1.850.000đ, không rách tờ nào. Dì Bảy dúi cho bạn hộp cơm sườn.'),
                  dict(id='machine', label='Cho cả xấp vào máy đếm', hint='', effects=dict(review=[2, 'Máy kẹt, rách mất hai tờ của dì.']), good=False,
                       outcome='Máy kẹt, hai tờ rách đôi phải làm thủ tục đổi tiền rách.'),
                  dict(id='later', label='Bảo dì về phơi khô rồi quay lại', hint='', effects=dict(patience=-1), good=None,
                       outcome='Dì Bảy đội mưa về, càu nhàu suốt dọc đường.')],
         default='later'),
    dict(id='pension_queue', title='Các cụ xếp hàng từ sáu giờ sáng', emoji='👵', npc=KHANG, min_day=2, tone='gentle', at='open', weight=3, mods=('pension',),
         text='Ngày nhận lương hưu: chưa mở cửa đã hai mươi cụ đứng chờ ngoài nắng, ông Khang dẫn đầu, tay cầm sẵn quạt nan.',
         options=[dict(id='early', label='Mở sảnh sớm 15 phút cho các cụ ngồi ghế chờ, phát số trước, rót nước', hint='',
                       effects=dict(xp=5, review=[5, 'Sáng nay quầy mở sớm cho các cụ ngồi, có cả nước chè.']), good=True,
                       outcome='Các cụ ngồi quạt, kể chuyện cờ tướng tới lượt mình.'),
                  dict(id='rule', label='Đúng giờ mới mở cửa, quy định là quy định', hint='', effects=dict(review=[2, 'Bắt người già đứng nắng chờ đúng từng phút.']), good=None,
                       outcome='Đúng 7 giờ cửa mở. Hai cụ chóng mặt phải ngồi bệt xuống bậc thềm.')],
         default='rule'),
]

MILESTONES = [
    dict(id='steady', label='Quầy số 3 vững tay', jobs=15, days=5, kinds=2),
    dict(id='trusted', label='Người cả chợ tin', jobs=60, days=20, kinds=4),
    dict(id='pillar', label='Trụ cột phòng giao dịch Bến Chợ', jobs=160, days=40, kinds=5),
]

NOTEBOOK = [
    'Mọi quy định, phí và lãi ở đây là quy tắc hư cấu của phòng giao dịch Bến Chợ, Ngân hàng Phố. Tiền ở quầy là tiền của ngân hàng (tính bằng nghìn đồng), không phải xu trong ví hay tài khoản của bạn.',
    'Năm bước một khách: nhận yêu cầu → kiểm tra thông tin → xử lý tiền → xác nhận với khách → giao biên nhận.',
    'Đầu ca: đếm từng phong bì quỹ, cộng tổng rồi so với sổ bàn giao. Khớp mới ký nhận; lệch thì chưa ký, lập biên bản với trưởng quầy.',
    'Kiểm tra thông tin: tên trên phiếu, ảnh và số CCCD phải khớp người đứng quầy. Số và chữ trên phiếu phải bằng nhau; lệch thì hỏi khách và cho khách ký xác nhận số đúng. Phiếu thiếu chữ ký thì mời ký. Không phải chủ tài khoản thì chưa chi, cần giấy ủy quyền có công chứng.',
    'Khay tiền tự cộng: kéo hoặc chạm tờ tiền vào khay, khay hiện tổng. Sai thì bỏ bớt, sửa xong mới bấm xác nhận. Làm theo lời dặn của khách (không tờ 500, ít tờ nhất, có tờ 50…) và ngăn két đang hết.',
    'Đổi tiền lẻ: một cọc là 10 tờ cùng mệnh giá. Đếm tiền khách đưa trước; đưa đúng số cọc khách cần, phần còn lại theo mệnh giá khách chọn. Buộc từng cọc, ghi bảng kê hai bên ký.',
    f'Chuyển tiền: người nhận phải khớp cả tên, ảnh và một chi tiết khác (nghề, nơi làm). Hai người trùng tên là chuyện thường. Cùng Ngân hàng Phố miễn phí; khác ngân hàng phí {FEE_OTHER} nghìn, thu thêm của khách. Đọc lại cho khách gật đầu rồi mới bấm chuyển.',
    'Gửi tiết kiệm theo mục tiêu: hỏi cần bao nhiêu, đã có bao nhiêu, bao lâu, có phải rút giữa chừng không. Mỗi tháng góp = (cần − đã có) ÷ số tháng, làm tròn lên tới 10 nghìn. Có thể phải rút giữa chừng thì tích lũy linh hoạt; không thì tích lũy mục tiêu. Không bán thứ khách không cần.',
    f'Tiếp quỹ ATM: hộp tiền dưới {ATM_LOW} tờ thì phải tiếp, nạp đầy lại tới {ATM_CAP} tờ. Lắp đúng khe đúng mệnh giá. Luôn hai người cùng mở máy, cùng ký sổ, niêm phong, chạy thử.',
    'Cuối ca bàn giao: khớp từng biên nhận với giao dịch; giao dịch chưa có biên nhận là giao dịch treo, ghi sổ và báo trưởng quầy. Tiền quầy = quỹ đầu ca + tiền gửi vào − tiền đã chi; khoản treo chưa chi thì không trừ.',
    f'Học việc: ba bài ngắn → thi thực hành ba phần (đếm và đổi tiền; xác nhận người nhận khi có hai người trùng tên; xử lý bất thường) → bảng tên → {TRAINING} ca có chị Hạnh kèm → đứng quầy một mình. Thi trong {EXAM_FAST} giây là ⚡, không xin gợi ý là 🎯.',
    'Nhánh nghề: Giao dịch (cao cấp → trưởng quầy), Tư vấn (khách quen → mục tiêu tài chính), Vận hành (ATM → kiểm soát → vận hành chi nhánh), Quản lý (trưởng quầy → quản lý chi nhánh). Mỗi bậc thưởng việc của nhánh +15%. Sổ tư vấn trung thực được đọc khi xét lên chức.',
    'Lương ca trả theo hợp đồng khi khép ca; mỗi khách xong có thưởng nhỏ theo chất lượng. Sai bước thì sửa ngay tại bước đó, thưởng giảm.',
]
