"""🔧 Xưởng độ xe Tư Pít-tông: the words and tables of the tuning shop (game/careers/tuning.py).

Every table is static: a ticket is a pure function of (day, slot), so validate_state can rebuild it. A customer brings a
car or a motorbike with a goal (đi phố êm, đua drag ở trường đua, đua đường đèo trong ngày đóng đường, triển lãm) and a
budget; the build sheet follows the shop's priority list for that goal within the budget, legal parts only. The owner's
rule ("nghề nào cũng phải có nhiều yêu cầu oái oăm"): each ticket carries one or two awkward demands (DEMANDS: a straight
pipe, a catalytic converter "for later", a folding plate, flashing lights, a fake spec card…) and the shop has its own
surprises between tickets (DESK, kit.desk), some of which leave a mark that brings a later event.
All numbers (priorities, prices, pressures, limits) are the shop's own notebook below; they are the game's rules.
"""
from __future__ import annotations

PLACE = 'Xưởng độ xe Tư Pít-tông'
OWNER = 'Anh Tư Pít-tông'

PEOPLE = [
    ('Anh Tư Pít-tông', 'Chủ xưởng độ', 'Hai mươi năm độ xe, mê tốc độ mà ghét nhất pô thẳng chạy trong phố. Câu cửa miệng: “Nhanh mà phải dừng được.”', 'warm'),
    ('Mi Lốp', 'Thợ phụ, mười chín tuổi', 'Thuộc lòng thông số lốp, ghi sổ dyno kỹ từng dòng, mơ một lần chạy trường đua.', 'genz'),
    ('Chị Kiều', 'Kỹ sư dyno', 'Đọc biểu đồ dyno như đọc báo, nói ít mà trúng.', 'quiet'),
    ('Anh Bảo', 'Dân chạy đèo cuối tuần', 'Câu lạc bộ thuê đèo Mây Bay đóng đường chạy mỗi tháng, cần xe ôm cua chắc, phanh bền.', 'picky'),
    ('Chị Linh', 'Nhân viên văn phòng', 'Đi làm mỗi ngày, muốn xe êm, bốc vừa đủ, đỡ tốn xăng.', 'warm'),
    ('Cậu Khoa', 'Sinh viên mê đua drag', 'Gom tiền nửa năm để chạy giải drag ở trường đua Bến Mây.', 'genz'),
    ('Ông Hoàng', 'Người chơi xe sưu tầm', 'Mang xe đi triển lãm, quý từng con ốc, ghét ai “phá zin”.', 'picky'),
    ('Anh Sang', 'Thanh niên mê đèn mê pô', 'Muốn đèn chớp xanh đỏ, pô nổ lụp bụp cho “ngầu”.', 'sour'),
]
MENTOR = 0
HELPER = 1
DYNO = 2
CUSTOMERS = (3, 4, 5, 6, 7)

WRONG_COST = 7          # quality lost per redone step (a ticket is longer than a repair slip)
QUALITY_FLOOR = 40
MILESTONES = (4, 10, 20, 40)   # days: the papers check and a second work step, AFR reading, a second demand, the harder builds
MASTER = (90, 30)       # Thợ độ vững tay: good tickets, active days
EXPERT = (160, 45)      # Thợ cả Tư Pít-tông
LEGAL_FINE = 5          # xu: the ward's warning to the shop when an illegal fit or a failed reading is passed
WARN_EVERY = 3          # every third warning brings the inspection team (desk mark 'warned')

# The vehicles brought in: (name, kind, peak power in mã lực, weight kg, top rpm). kind: 'bike' | 'car'.
VEHICLES = [
    ('Xe côn tay 150 phân khối', 'bike', 16, 125, 10000),
    ('Xe tay ga 155 phân khối', 'bike', 15, 128, 9000),
    ('Mô tô 300 phân khối', 'bike', 38, 165, 11000),
    ('Ô tô hatchback 1.4', 'car', 98, 1080, 6500),
    ('Ô tô sedan 1.5 tăng áp', 'car', 150, 1300, 6000),
    ('Ô tô thể thao 2.0', 'car', 200, 1350, 7000),
]
COLORS = ('đỏ đô', 'trắng ngọc', 'xanh dương', 'đen nhám', 'xám xi măng', 'vàng chanh')
PROVINCES = ('59', '51', '61', '72', '43', '29')
KIND_NAME = dict(bike='xe máy', car='ô tô')

# The customer's goal: name, emoji, min day, labour (xu, before quality), the shop's priority list (the build sheet
# takes them in this order while the budget lasts; one that does not fit is skipped), what the customer says.
GOALS = {
    'pho': dict(name='Đi phố êm', emoji='🏙️', day=1, net=18, prio=('giam_xoc', 'lop', 'ecu', 'den'),
                say=('Em đi làm mỗi ngày, muốn xe êm, vào ga mượt, đỡ tốn xăng.', 'Chở con đi học thôi, chỉ mong xe êm với bốc vừa đủ.')),
    'show': dict(name='Triển lãm xe', emoji='✨', day=1, net=20, prio=('son', 'den', 'lop', 'giam_xoc'),
                 say=('Tháng sau có triển lãm xe ở nhà văn hóa, tôi muốn xe đẹp mà máy vẫn zin.', 'Mang xe đi trưng bày, cần bóng bẩy, đèn đẹp, đừng đụng vô máy.')),
    'drag': dict(name='Đua drag', emoji='🏁', day=2, net=24, prio=('lop', 'phanh', 'ecu', 'hut_xa', 'giam_can', 'turbo'),
                 say=('Tháng sau em chạy giải drag 400 mét ở trường đua Bến Mây.', 'Em cần xe đề-pa thật bốc, chạy thẳng bốn trăm mét trong trường đua.')),
    'deo': dict(name='Đua đường đèo', emoji='⛰️', day=3, net=24, prio=('phanh', 'lop', 'giam_xoc', 'ecu', 'giam_can', 'khi_dong'),
                say=('Câu lạc bộ thuê đèo Mây Bay đóng đường chạy cuối tháng, tôi cần ôm cua chắc.', 'Vào cua là xe chòng chành, đổ dốc thì phanh nóng hết.')),
}
GOAL_ORDER = tuple(GOALS)

# Legal mods the shop fits: name, emoji, parts (xu) for (bike, car) (None: not for that kind), power gain in %.
MODS = {
    'ecu': dict(name='Nạp lại bản đồ ECU', emoji='💻', cost=(8, 14), hp=8),
    'hut_xa': dict(name='Lọc gió và pô có tiêu âm đạt chuẩn', emoji='🔊', cost=(6, 11), hp=4),
    'turbo': dict(name='Bộ tăng áp turbo', emoji='🌀', cost=(None, 34), hp=30),
    'lop': dict(name='Lốp bám đường', emoji='🛞', cost=(6, 12), hp=0),
    'phanh': dict(name='Phanh đĩa lớn, má phanh hiệu năng', emoji='🛑', cost=(7, 14), hp=0),
    'giam_xoc': dict(name='Phuộc chỉnh được độ cứng', emoji='🔩', cost=(9, 16), hp=0),
    'giam_can': dict(name='Giảm cân: ghế nhẹ, bỏ đồ thừa', emoji='🪶', cost=(4, 9), hp=0),
    'khi_dong': dict(name='Cánh gió, cản trước khí động học', emoji='🪽', cost=(None, 12), hp=0),
    'son': dict(name='Dán decal, đánh bóng sơn', emoji='🎨', cost=(5, 10), hp=0),
    'den': dict(name='Đèn LED đúng chuẩn, chỉnh góc chiếu', emoji='💡', cost=(4, 7), hp=0),
}
SHORT = dict(ecu='map ECU', hut_xa='pô và lọc gió', turbo='turbo', lop='lốp', phanh='phanh', giam_xoc='phuộc', giam_can='giảm cân',
             khi_dong='cánh gió', son='decal', den='đèn')
# Illegal fits a customer asks for (the trap on every build sheet): name, emoji, parts (bike, car), the rule it breaks.
ILLEGAL = {
    'po_thang': dict(name='Pô thẳng không tiêu âm, nổ lụp bụp', emoji='📢', cost=(5, 9), rule='tiếng ồn'),
    'xuc_tac': dict(name='Tháo bộ xúc tác khí thải cho “thoáng”', emoji='💨', cost=(3, 6), rule='khí thải'),
    'den_chop': dict(name='Đèn chớp xanh đỏ như xe ưu tiên', emoji='🚨', cost=(3, 5), rule='đèn'),
    'bien_gap': dict(name='Khung biển số gập, qua camera thì giấu', emoji='🙈', cost=(2, 3), rule='biển số'),
}

# ---------------------------------------------------------------- the work: procedures (ordered) per mod
STEPS = {
    'ecu': [('luu', 'Đọc và lưu bản map gốc của xe'), ('sac', 'Gắn sạc giữ điện cho ắc quy'), ('nap', 'Nạp bản map mới'),
            ('loi', 'Xóa lỗi, đọc lại bảng lỗi'), ('nong', 'Nổ máy tới nhiệt độ làm việc'), ('dyno', 'Chạy dyno, ghi đường AFR')],
    'hut_xa': [('nguoi', 'Đợi pô nguội hẳn'), ('thao', 'Tháo pô cũ, giữ lại các ốc'), ('gioang', 'Lắp gioăng mới ở cổ pô'),
               ('lap', 'Lắp pô có tiêu âm, siết đều các ốc'), ('loc', 'Thay lọc gió, kẹp chặt cổ hút'), ('do', 'Nổ máy, đo tiếng ồn bằng máy đo dB')],
    'turbo': [('nhot', 'Chạy đường nhớt và nước làm mát cho turbo'), ('lap', 'Lắp turbo và cổ xả'), ('ket', 'Lắp két làm mát khí nạp, kẹp đường ống'),
              ('moi', 'Mồi nhớt cho turbo trước khi nổ máy'), ('ro', 'Nổ máy không tải, kiểm rò khí, rò nhớt'), ('map', 'Nạp map turbo, chạy dyno tải nhẹ trước')],
    'lop': [('kich', 'Kích xe, chèn bánh'), ('thao', 'Tháo bánh, tháo lốp cũ'), ('lap', 'Lắp lốp mới đúng chiều quay'),
            ('can', 'Cân bằng động bánh xe'), ('luc', 'Siết ốc bánh chéo góc, đúng lực'), ('bom', 'Bơm đúng áp suất theo sổ')],
    'phanh': [('chen', 'Chèn bánh, kích xe'), ('thao', 'Tháo heo và má phanh cũ'), ('dia', 'Lắp đĩa lớn và heo mới'),
              ('ma', 'Lắp má phanh hiệu năng'), ('xa', 'Thay dầu phanh, xả gió từng bánh'), ('ra', 'Rà má: phanh nhẹ nhiều lần ở đường thử')],
    'giam_xoc': [('kich', 'Kích xe, tháo bánh'), ('thao', 'Tháo phuộc cũ'), ('lap', 'Lắp phuộc mới, siết đúng lực'),
                 ('sag', 'Đo độ lún tĩnh, chỉnh tăng chỉnh'), ('goc', 'Cân chỉnh góc đặt bánh'), ('thu', 'Chạy thử qua gờ giảm tốc')],
    'giam_can': [('can', 'Cân xe trước khi tháo'), ('liet', 'Ghi danh sách đồ được tháo'), ('thao', 'Tháo ghế sau và đồ thừa'),
                 ('giu', 'Kiểm lại dây an toàn, gương, bình cứu hỏa vẫn đủ'), ('can2', 'Cân lại, ghi số ký bớt được')],
    'khi_dong': [('do', 'Đo chiều rộng thân xe và khoảng sáng gầm'), ('gia', 'Bắt giá cánh gió vào điểm có sẵn, không khoan cốp'),
                 ('lap', 'Lắp cánh gió và cản trước'), ('che', 'Kiểm không che đèn, không che biển số'), ('siet', 'Siết lại sau khi chạy thử')],
    'son': [('rua', 'Rửa xe, tẩy dầu mỡ'), ('che', 'Che đèn, kính và biển số'), ('dan', 'Dán decal từ giữa ra mép'),
            ('ho', 'Hơ nóng mép decal cho bám'), ('bong', 'Đánh bóng phần sơn còn lại'), ('go', 'Gỡ giấy che, kiểm đèn và biển số')],
    'den': [('tat', 'Tắt máy, rút cầu chì đèn'), ('thao', 'Tháo bóng cũ'), ('lap', 'Lắp bóng LED có chứng nhận, đúng chân'),
            ('giac', 'Cắm giắc, lắp lại cầu chì'), ('chinh', 'Chỉnh góc chiếu trên tường cách 10 m')],
}
WORK_TITLE = {
    'ecu': 'Nạp map ECU đúng thứ tự', 'hut_xa': 'Thay pô và lọc gió đúng thứ tự', 'turbo': 'Lắp turbo đúng thứ tự',
    'lop': 'Thay lốp đúng thứ tự', 'phanh': 'Thay phanh đúng thứ tự', 'giam_xoc': 'Thay phuộc đúng thứ tự',
    'giam_can': 'Giảm cân đúng thứ tự', 'khi_dong': 'Lắp cánh gió đúng thứ tự', 'son': 'Dán decal đúng thứ tự', 'den': 'Thay đèn đúng thứ tự',
}

# The ECU map's air–fuel ratio at full load (the notebook): city 13,2; a race build 12,8; with a turbo 11,8.
AFR_OPTIONS = (('pho', '13,2: êm, đỡ hao xăng'), ('nat', '12,8: hút khí tự nhiên chạy đua'), ('turbo', '11,8: có turbo, giàu xăng cho mát máy'),
               ('ngheo', '14,7: như lúc chạy không tải'))
AFR_LIMIT = 135         # tenths: leaner than 13,5 at full load is a fault
BRAKE_DISC = ('Vành xe hiện tại 16 inch; đĩa 320 mm chỉ lọt vành từ 17 inch trở lên.',
              'Chọn bộ đĩa 300 mm vừa vành 16 inch',
              ('Lắp đĩa 320 mm, mài bớt heo cho lọt', 'Bỏ phanh lớn, giữ phanh zin cho đỡ tốn', 'Đổi sang vành 15 inch cho nhẹ'))
WING = ('Khách muốn cánh gió dài hơn thân xe mỗi bên 15 cm “cho ngầu”.',
        'Chọn cánh gió nằm gọn trong chiều rộng thân xe, mép bo tròn',
        ('Lắp cánh dài như khách muốn', 'Lắp cánh bằng thép tấm cắt sắc cho nhẹ', 'Khoan cốp bắt cánh cho chắc'))
REPAINT = ('Khách đổi màu xe từ trắng sang đỏ toàn thân bằng decal.',
           'Dán xong thì hướng dẫn khách khai báo đổi màu với cơ quan đăng ký xe trước khi chạy',
           ('Khỏi khai báo, decal bóc được mà', 'Chỉ dán nửa xe để khỏi khai', 'Ghi phiếu là xe vẫn màu trắng'))
DROP_GOOD = ('Ghế sau', 'Thảm cách âm trong cốp', 'Loa siêu trầm', 'Giá nóc chở đồ')
DROP_BAD = ('Dây an toàn', 'Gương chiếu hậu', 'Bình cứu hỏa', 'Tấm chắn nhiệt pô')

INSPECT_GOOD = ('Đối chiếu số khung, số máy với giấy đăng ký', 'Đo nén máy, nghe tiếng máy', 'Soi gầm, khung sườn có nứt hay gỉ',
                'Kiểm rò rỉ nhớt và nước làm mát', 'Đo độ mòn phanh, lốp hiện tại')
INSPECT_BAD = ('Rửa xe bằng dầu cho bóng trước đã', 'Nạp map ECU luôn rồi kiểm sau', 'Tháo bộ xúc tác ra để kiểm cho dễ', 'Bỏ qua, khách nói xe còn mới')

SAFETY_GOOD = ('Siết ốc bánh đúng lực bằng cần lực', 'Xả gió dầu phanh, kiểm phanh ăn chắc', 'Kiểm rò rỉ xăng, nhớt, nước làm mát',
               'Kiểm đèn, xi-nhan, còi', 'Kiểm biển số gắn cố định, đọc rõ')
SAFETY_BAD = ('Bỏ chạy thử vì khách đang gấp', 'Tháo cầu chì ABS cho xe nhẹ', 'Dán giấy che biển số lúc chạy thử', 'Tắt đèn báo lỗi trên đồng hồ cho gọn')
NOISE_LIMIT = dict(bike=95, car=96)     # dB at half the top rpm (the notebook)
CO_LIMIT = 45                           # tenths of a % CO at idle (the notebook): 4,5 %

TEST_DRIVE = [
    ('Chạy thử ở đường thử sau xưởng: xe kéo lệch trái khi phanh gấp.',
     'Quay về xưởng, kiểm má phanh và xả gió bên trái trước khi giao',
     ('Giao luôn, khách tự quen dần', 'Chạy thêm vài vòng cho má phanh “ăn”')),
    ('Sau hai vòng chạy thử, kim nhiệt độ máy nhích sát vạch đỏ.',
     'Dừng xe, kiểm két nước và quạt, chạy dyno tải nhẹ lại',
     ('Giao xe, dặn khách chạy chậm thôi', 'Đổ thêm nước lạnh vào két khi máy đang nóng')),
    ('Xe êm, phanh chắc, không có tiếng lạ.',
     'Ghi phiếu chạy thử: quãng đường, tốc độ trong giới hạn, không lỗi',
     ('Chạy thêm một vòng ngoài phố cho “đã”', 'Khỏi ghi phiếu, xe ngon rồi')),
    ('Tay lái rung ở 80 km/h sau khi thay lốp.',
     'Cân bằng động lại bánh xe rồi chạy thử lại',
     ('Bơm căng lốp cho hết rung', 'Giao xe, nói lốp mới phải chạy rô-đa')),
    ('Khách đòi tự cầm lái chạy thử, phóng nhanh ra đường phố.',
     'Chỉ chạy thử ở đường thử của xưởng, thợ ngồi bên, đúng tốc độ',
     ('Đưa chìa khóa cho khách chạy ra phố', 'Cho chạy nhưng dặn đừng quá 120 km/h')),
    ('Có tiếng rít ở cổ xả khi tăng ga mạnh.',
     'Kiểm gioăng cổ xả và kẹp ống, siết lại rồi đo tiếng ồn lại',
     ('Tăng âm lượng loa cho át tiếng rít', 'Giao xe, tiếng rít là “chất” xe độ')),
]

# ---------------------------------------------------------------- 🌀 oái oăm at the counter (one or two a ticket)
# (min day, what the customer says, the right answer, the wrong ones, only for these goals or None, the rule it is about)
# Rules: 'khi_thai', 'tieng_on', 'den', 'bien_so', 'giay_to', 'an_toan' are legal ones (a wrong answer warns the shop);
# 'trung_thuc' is honesty with the customer.
LEGAL_RULES = ('khi_thai', 'tieng_on', 'den', 'bien_so', 'giay_to', 'an_toan')
DEMANDS = [
    (1, 'Khách: “Làm cái pô thẳng nổ lụp bụp cho ngầu, ai cấm.”',
     'Từ chối pô thẳng; giới thiệu pô có tiêu âm đạt chuẩn, đo tiếng ồn trước khi giao', ('Lắp pô thẳng, khách chịu', 'Lắp pô thẳng, dặn chạy đêm thôi'), None, 'tieng_on'),
    (1, 'Khách: “Gắn đèn chớp xanh đỏ như xe cứu thương cho dễ qua đường.”',
     'Từ chối: đèn ưu tiên chỉ xe ưu tiên được gắn', ('Gắn nhỏ nhỏ thôi', 'Gắn rồi chỉ khách cách tắt khi gặp công an'), None, 'den'),
    (1, 'Khách: “Độ xong ghi phiếu là xe còn zin nha, để còn bảo hành hãng.”',
     'Ghi đúng các hạng mục đã độ, báo khách độ có thể mất bảo hành hãng', ('Ghi phiếu xe zin cho khách vui', 'Không ghi phiếu gì hết'), None, 'trung_thuc'),
    (2, 'Khách: “Tháo luôn bộ xúc tác cho máy thở, bữa đăng kiểm lắp lại.”',
     'Từ chối: xe phải đạt khí thải mọi lúc, không chỉ ngày kiểm định', ('Tháo, cất bộ xúc tác vào cốp', 'Khoan thủng ruột bộ xúc tác cho thoáng'), None, 'khi_thai'),
    (2, 'Khách: “Làm khung biển số gập, qua camera thì gập lại.”',
     'Từ chối: biển số phải gắn cố định, đọc rõ', ('Làm khung gập loại xịn', 'Dán phim mờ lên biển số thôi'), None, 'bien_so'),
    (2, 'Khách: “Tối nay em đua với tụi bạn trên cầu, chỉnh cho xe chạy nhanh nhất.”',
     'Từ chối hỗ trợ đua trên đường phố; chỉ chỗ đua hợp pháp ở trường đua Bến Mây', ('Độ cho thật nhanh, khách tự chịu', 'Độ nhưng dặn đua lúc vắng xe'), None, 'an_toan'),
    (2, 'Khách: “Ghi thẻ thông số 200 mã lực cho em bán được giá.”',
     'Ghi đúng số đo dyno trên thẻ thông số', ('Ghi tròn lên cho đẹp', 'Ghi hai thẻ: một thật, một để bán'), None, 'trung_thuc'),
    (3, 'Khách: “Thiếu tiền rồi, bỏ khoản phanh đi, dồn tiền lên turbo.”',
     'Không: tăng công suất phải đi cùng phanh; thiếu tiền thì bỏ turbo trước', ('Bỏ phanh, lắp turbo như khách muốn', 'Lắp turbo, hẹn tháng sau thay phanh'), ('drag', 'deo'), 'an_toan'),
    (3, 'Khách: “Đèn pha xenon trắng xanh thật chói cho dễ thấy đường.”',
     'Lắp đèn đúng chuẩn, chỉnh góc chiếu không làm chói xe ngược chiều', ('Lắp bóng chói nhất, chỉnh hắt lên cao', 'Lắp đèn trợ sáng chiếu thẳng vào mắt xe trước'), None, 'den'),
    (3, 'Khách: “Xe của bạn em, giấy tờ để bên nó, cứ độ đi anh.”',
     'Chỉ nhận độ khi có giấy đăng ký hoặc giấy ủy quyền của chủ xe', ('Độ luôn, quen biết mà', 'Độ trước, giấy tờ mang sau'), None, 'giay_to'),
    (4, 'Khách: “Gắn còi hơi tàu hỏa kêu thật to cho ai cũng né.”',
     'Không gắn còi hơi quá to; dùng còi đúng chuẩn', ('Gắn còi hơi, dặn bấm nhẹ thôi', 'Gắn hai cái còi cho chắc'), None, 'tieng_on'),
    (4, 'Khách: “Tắt đèn báo lỗi với túi khí cho bảng đồng hồ gọn.”',
     'Không tắt đèn báo lỗi, không tháo thiết bị an toàn; tìm và sửa lỗi', ('Tắt cho gọn', 'Dán băng keo đen che đèn báo'), None, 'an_toan'),
    (5, 'Khách: “Hạ gầm sát đất, khoảng sáng gầm còn năm phân thôi.”',
     'Giữ khoảng sáng gầm trong giới hạn sổ tay, chỉ cho khách thấy ổ gà, gờ giảm tốc', ('Hạ sát theo ý khách', 'Cắt lò xo cho thấp nhanh'), ('pho', 'show', 'deo'), 'an_toan'),
    (5, 'Ông chủ xe triển lãm: “Đừng đụng một con ốc nào của máy, kể cả khi thấy rò nhớt.”',
     'Báo thật chỗ rò nhớt và mức nguy hiểm; ông không cho sửa thì ghi phiếu khách từ chối', ('Lặng lẽ sửa luôn, khỏi nói', 'Xịt bóng che vết nhớt cho đẹp'), ('show',), 'trung_thuc'),
    (6, 'Khách: “Dán phim đen kịt kính lái cho kín, khỏi ai nhìn vô.”',
     'Kính lái giữ đủ độ trong để nhìn đường; chỉ dán phim nhạt đạt chuẩn', ('Dán đen kín theo ý khách', 'Dán đen, dặn khách mở cửa sổ khi trời tối'), None, 'an_toan'),
    (8, 'Khách: “Chỉnh đồng hồ tốc độ chạy chậm lại cho khỏi bị bắn tốc độ.”',
     'Từ chối: đồng hồ tốc độ phải chỉ đúng', ('Chỉnh chậm lại 10 km/h', 'Rút dây đồng hồ cho khỏi chạy'), None, 'an_toan'),
]

CARD_WRONG = ('ghi tròn lên cho đẹp', 'không ghi các hạng mục đã độ')

RULES = [
    'Mọi con số dưới đây là sổ tay của xưởng Tư Pít-tông, luật của trò chơi.',
    'Nghe khách nói chạy ở đâu, chạy làm gì rồi mới chốt mục tiêu: đi phố êm, triển lãm, đua drag ở trường đua, đua đèo trong ngày đóng đường.',
    'Trước khi độ: đối chiếu số khung, số máy với giấy đăng ký; đo nén máy; soi gầm; kiểm rò rỉ; đo mòn phanh, lốp.',
    'Bảng độ theo thứ tự ưu tiên của mục tiêu, trong ngân sách: món nào còn vừa tiền thì lấy, không vừa thì bỏ qua, xét tiếp món sau.',
    'Ưu tiên: đi phố êm: phuộc → lốp → ECU → đèn. Triển lãm: decal → đèn → lốp → phuộc. Đua drag: lốp → phanh → ECU → pô và lọc gió → giảm cân → turbo. Đua đèo: phanh → lốp → phuộc → ECU → giảm cân → cánh gió.',
    'Xe máy không lắp turbo, không lắp cánh gió.',
    'Xưởng không lắp: pô thẳng không tiêu âm, tháo bộ xúc tác, đèn chớp xanh đỏ, khung biển số gập. Lắp đồ trái luật là khách bị phạt, xưởng bị nhắc nhở.',
    'Map xăng ECU ở tải lớn: đi phố 13,2; đua không turbo 12,8; có turbo 11,8. Nghèo hơn 13,5 khi tải lớn là phải nạp lại map.',
    'Turbo: mỗi 1 psi tăng áp lùi lửa 1 độ so với góc lửa gốc.',
    'Lốp: áp lạnh theo tem xe; đua đèo cộng 2 psi; đua drag bánh dẫn động bớt 4 psi (chỉ trong trường đua); đi phố, triển lãm theo đúng tem.',
    'Phuộc: độ lún tĩnh bằng 30% hành trình (xe máy), 25% hành trình (ô tô).',
    'Đèn: cách tường 10 m, vệt sáng đèn cốt phải thấp hơn tâm đèn 10 cm.',
    'Pô mới đo tiếng ồn ở nửa vòng tua tối đa: xe máy tối đa 95 dB, ô tô tối đa 96 dB. Khí thải CO ở không tải tối đa 4,5%.',
    'Đổi màu xe phải khai báo với cơ quan đăng ký. Cánh gió nằm trong chiều rộng thân xe, mép bo tròn.',
    'Trước khi giao: siết ốc bánh đúng lực, xả gió phanh, kiểm rò rỉ, kiểm đèn còi, biển số cố định; chạy thử ở đường thử của xưởng.',
    'Thẻ thông số ghi đúng số đo dyno và đủ các hạng mục đã độ.',
]

# ---------------------------------------------------------------- 🔔 desk surprises (kit.desk): chuyện ở xưởng
DESK = [
    dict(id='street_race', title='Đám thanh niên rủ đua đêm', emoji='🌃', npc=7, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Anh Sang dẫn ba người bạn ghé xưởng: “Tối nay đua trên đường ven sông, anh độ giùm tụi em, tiền gấp đôi.”',
         options=[dict(id='track', label='Từ chối, đưa tờ lịch ngày chạy thử mở cửa của trường đua Bến Mây', hint='',
                       effects=dict(xp=6, review=[4, 'Xưởng không độ cho đua đường phố mà chỉ chỗ đua đàng hoàng, phục.', 7]), good=True,
                       outcome='Anh Sang lầm bầm, nhưng cuối tuần dắt cả nhóm ra trường đua.'),
                  dict(id='do', label='Nhận độ, tiền là tiền', hint='', effects=dict(money=12, mark='street_build'), good=False,
                       outcome='Tiền vào túi. Đêm đó cả bờ sông nghe tiếng máy gầm.'),
                  dict(id='ignore', label='Lắc đầu cho qua, không nói gì', hint='', effects=dict(patience=-2), good=None,
                       outcome='Nhóm thanh niên đi sang tiệm khác.')],
         default='ignore'),
    dict(id='street_crash', title='Chiếc xe độ đêm qua bị giữ', emoji='🚓', npc=0, min_day=4, tone='tense', at='between', weight=5, mods=None,
         need_mark='street_build',
         text='Sáng ra, cảnh sát giao thông gọi tới xưởng: chiếc xe độ hôm trước bị giữ sau vụ đua trái phép, trên xe còn dán tem xưởng.',
         options=[dict(id='cooperate', label='Mang phiếu độ ra làm việc, khai đúng những gì đã lắp', hint='',
                       effects=dict(unmark='street_build', money=-15, money_loss='fine', review=[2, 'Xưởng từng độ cho đua đường phố, có chịu làm việc.', 0]), good=None,
                       outcome='Xưởng bị phạt 15 xu và nhắc nhở. Anh Tư gỡ hết tem xưởng khỏi xe ngoài kia.'),
                  dict(id='deny', label='Nói không biết chiếc xe đó', hint='',
                       effects=dict(unmark='street_build', money=-30, money_loss='fine', review=[1, 'Xưởng độ xe cho đua đường phố còn chối.', 0]), good=False,
                       outcome='Phiếu nhận xe nằm ngay trên bàn. Xưởng bị phạt nặng hơn, cả phố bàn tán.')],
         default='cooperate'),
    dict(id='inspection', title='Đoàn kiểm tra ghé xưởng', emoji='📋', npc=0, min_day=3, tone='tense', at='between', weight=6, mods=None,
         need_mark='warned',
         text='Phường đã nhắc nhở xưởng mấy lần về đồ lắp trái luật. Hôm nay đoàn kiểm tra ghé, xin xem sổ phiếu độ và kho phụ tùng.',
         options=[dict(id='open', label='Mở sổ phiếu, kho phụ tùng; trình bày cách xưởng đã sửa', hint='',
                       effects=dict(xp=6, unmark='warned', review=[4, 'Xưởng minh bạch sổ sách, biết sửa sai.', 0]), good=True,
                       outcome='Đoàn ghi biên bản: xưởng đã chấn chỉnh. Anh Tư dán bảng “Không lắp đồ trái luật” trước cửa.'),
                  dict(id='hide', label='Giấu mấy cái pô thẳng ra sau, nói xưởng không làm', hint='',
                       effects=dict(unmark='warned', money=-25, money_loss='fine'), good=False,
                       outcome='Mi Lốp vô tình kéo tấm bạt ra. Xưởng bị phạt 25 xu.')],
         default='open'),
    dict(id='fake_turbo', title='Turbo “hàng xịn” giá rẻ', emoji='📦', npc=7, min_day=3, tone='tense', at='between', weight=2, mods=None,
         no_mark='fake_bought',
         text='Một người lạ chào bán năm bộ turbo “hàng hãng” giá bằng một phần tư, không hóa đơn, tem nhãn in mờ.',
         options=[dict(id='refuse', label='Từ chối: đồ không rõ nguồn thì xưởng không lắp cho khách', hint='', effects=dict(xp=6), good=True,
                       outcome='Người lạ bỏ đi. Anh Tư: “Turbo nổ ở 180 km/h là chuyện mạng người.”'),
                  dict(id='buy', label='Mua hết, lời to', hint='', effects=dict(money=-14, mark='fake_bought'), good=False,
                       outcome='Năm cái hộp chất trong kho. Mấy ngày sau mới biết chuyện.')],
         default='refuse'),
    dict(id='turbo_blow', title='Turbo hàng nhái nổ trên băng thử', emoji='💥', npc=2, min_day=5, tone='tense', at='between', weight=5, mods=None,
         need_mark='fake_bought',
         text='Chị Kiều đang chạy dyno thì cái turbo mua rẻ hôm trước gãy cánh, khói trắng mù xưởng. May chưa giao cho khách.',
         options=[dict(id='scrap', label='Bỏ hết lô turbo đó, báo nơi bán cho công an phường, lắp lại hàng có hóa đơn', hint='',
                       effects=dict(xp=5, unmark='fake_bought', money=-10, money_loss='normal'), good=True,
                       outcome='Mất tiền lô hàng, nhưng không chiếc xe khách nào mang cái turbo đó ra đường.'),
                  dict(id='keep', label='Lắp tiếp mấy cái còn lại, chắc tại cái này xui', hint='',
                       effects=dict(unmark='fake_bought', money=-20, money_loss='normal', review=[1, 'Xe độ ở xưởng này nổ turbo giữa đường.', 5]), good=False,
                       outcome='Một tuần sau, xe của khách nổ turbo trên đường. Xưởng phải đền.')],
         default='scrap'),
    dict(id='dyno_noise', title='Hàng xóm phàn nàn tiếng dyno', emoji='🏘️', npc=4, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Chị Linh ở dãy nhà bên cạnh ghé: “Tối qua chín giờ xưởng còn chạy dyno, con chị không ngủ được.”',
         options=[dict(id='hours', label='Xin lỗi, dán giờ chạy dyno 8–18 giờ, đóng cửa cách âm khi chạy', hint='', effects=dict(xp=5, review=[5, 'Xưởng nghe hàng xóm góp ý, sửa liền.', 4]), good=True,
                       outcome='Tối đó cả dãy nhà yên tĩnh. Chị Linh gửi cho Mi Lốp bịch xôi.'),
                  dict(id='argue', label='Xưởng làm ăn mà, ồn chút chịu khó', hint='', effects=dict(review=[2, 'Xưởng độ xe ồn tới khuya, nói còn cãi.', 4]), good=False,
                       outcome='Tổ dân phố ghé nhắc nhở.')],
         default='hours'),
    dict(id='fuel_leak', title='Rò xăng trên băng thử', emoji='🧯', npc=2, min_day=3, tone='tense', at='any', weight=2, mods=None,
         text='Đang chạy dyno, chị Kiều ngửi thấy mùi xăng: một khớp nối ống xăng rỉ từng giọt xuống cổ xả nóng.',
         options=[dict(id='stop', label='Tắt máy ngay, mở cửa thông gió, để bình chữa cháy sẵn, thay khớp rồi mới chạy lại', hint='', effects=dict(xp=7), good=True,
                       outcome='Thay khớp nối mất mười phút. Chị Kiều gật đầu: “Đúng bài.”'),
                  dict(id='finish', label='Chạy nốt lần đo cho xong rồi tính', hint='', effects=dict(money=-12, money_loss='normal', review=[1, 'Xưởng để rò xăng mà vẫn chạy máy, hú hồn.', 2]), good=False,
                       outcome='Một tia lửa nhỏ bén lên. May bình chữa cháy ở gần, nhưng hỏng bộ dây đo.')],
         default='stop'),
    dict(id='mi_dream', title='Mi Lốp xin chạy giải drag', emoji='🏁', npc=1, min_day=4, tone='gentle', at='between', weight=2, mods=None,
         text='Mi Lốp lí nhí: “Anh ơi, cuối tháng trường đua có giải cho người mới, em xin nghỉ một buổi chạy thử được không?”',
         options=[dict(id='support', label='Cho nghỉ, còn cho mượn mũ bảo hiểm và dặn đọc kỹ luật trường đua', hint='', effects=dict(xp=4, mark='mi_raced'), good=True,
                       outcome='Mi Lốp cười tít mắt, tối đó ngồi chép luật trường đua vào sổ.'),
                  dict(id='no', label='Không, xưởng đông việc', hint='', effects=dict(patience=-1), good=None,
                       outcome='Mi Lốp gật đầu, làm việc mà mắt cứ nhìn ra cửa.')],
         default='no'),
    dict(id='mi_trophy', title='Mi Lốp mang cúp về xưởng', emoji='🏆', npc=1, min_day=6, tone='gentle', at='open', weight=5, mods=None,
         need_mark='mi_raced',
         text='Mi Lốp mang về chiếc cúp hạng ba giải người mới: “Nhờ anh dặn em đọc luật, em không bị loại vì xuất phát sớm.”',
         options=[dict(id='shelf', label='Đặt cúp lên kệ xưởng, chụp hình chung cả xưởng', hint='', effects=dict(xp=4, unmark='mi_raced', review=[5, 'Xưởng có thợ trẻ chạy giải đàng hoàng, dễ thương ghê.', 3]), good=True,
                       outcome='Tấm hình treo cạnh bảng giá. Khách nào vào cũng hỏi.')],
         default='shelf'),
    dict(id='scratch', title='Ông Hoàng thấy vết xước', emoji='🔍', npc=6, min_day=3, tone='tense', at='between', weight=3, mods=None,
         text='Ông Hoàng soi đèn pin quanh chiếc xe triển lãm: “Vết xước ở cản sau này đâu ra? Hôm đưa tới không có.”',
         options=[dict(id='photos', label='Mở ảnh chụp lúc nhận xe, chỉ vết xước đã có từ trước, ghi chú trên phiếu', hint='', effects=dict(xp=6, review=[5, 'Xưởng chụp ảnh nhận xe kỹ, nói có sách mách có chứng.', 6]), good=True,
                       outcome='Ông Hoàng xem ảnh, gật gù, rồi nhờ đánh bóng luôn vết xước đó.'),
                  dict(id='free', label='Đánh bóng miễn phí cho xong chuyện', hint='', effects=dict(money=-4), good=None,
                       outcome='Vết xước mờ đi. Ông Hoàng vẫn nghĩ xưởng làm xước.'),
                  dict(id='argue', label='Cãi: “Xưởng tôi không làm xước!”', hint='', effects=dict(review=[2, 'Hỏi có câu mà xưởng to tiếng.', 6]), good=False,
                       outcome='Hai bên lời qua tiếng lại, khách khác đứng xem.')],
         default='free'),
    dict(id='rain_test', title='Mưa to, đường thử trơn', emoji='🌧️', npc=5, min_day=2, tone='gentle', at='any', weight=2, mods=None,
         text='Mưa như trút, đường thử sau xưởng đọng nước. Cậu Khoa đòi chạy thử ngay để kịp khoe với bạn.',
         options=[dict(id='wait', label='Hoãn chạy thử tới khi đường khô, hẹn giờ cụ thể', hint='', effects=dict(xp=4), good=True,
                       outcome='Cậu Khoa phụng phịu, nhưng chiều tạnh mưa chạy thử thấy xe ngon lành.'),
                  dict(id='go', label='Chạy luôn cho khách vui', hint='', effects=dict(money=-8, money_loss='normal', review=[2, 'Chạy thử dưới mưa trượt bánh, xước cả cản.', 5]), good=False,
                       outcome='Xe trượt vào bờ cỏ, xước cản trước. Xưởng chịu tiền sơn.')],
         default='wait'),
    dict(id='installment', title='Cậu Khoa thiếu tiền', emoji='💸', npc=5, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Cậu Khoa móc túi đếm đi đếm lại: “Em thiếu chút xíu, anh lắp luôn turbo rồi em trả góp nha.”',
         options=[dict(id='plan', label='Làm phần trong ngân sách trước (lốp, phanh), hẹn đợt sau khi đủ tiền', hint='', effects=dict(xp=5, review=[5, 'Xưởng tư vấn làm từng phần, không ép mình vay.', 5]), good=True,
                       outcome='Cậu Khoa đồng ý, tháng sau quay lại với đủ tiền.'),
                  dict(id='credit', label='Lắp hết, ghi nợ', hint='', effects=dict(money=-6), good=None,
                       outcome='Cậu Khoa vui, còn xưởng thì thêm một dòng nợ trong sổ.')],
         default='plan'),
    dict(id='tiktok', title='Clip “xe độ 300 mã lực”', emoji='📱', npc=7, min_day=4, tone='tense', at='between', weight=2, mods=None,
         text='Anh Sang đăng clip chiếc xe độ ở xưởng, chú thích “300 mã lực, chạy 250 km/h trên phố”. Thực ra dyno chỉ đo được 180.',
         options=[dict(id='correct', label='Nhắn anh Sang sửa chú thích đúng số dyno, nhắc không quay clip chạy nhanh trên phố', hint='', effects=dict(xp=5), good=True,
                       outcome='Anh Sang sửa lại chú thích. Bình luận khen xưởng nói thật.'),
                  dict(id='share', label='Chia sẻ clip về trang xưởng, có tiếng là được', hint='', effects=dict(review=[2, 'Xưởng quảng cáo số liệu láo, còn cổ vũ chạy nhanh trên phố.', 7]), good=False,
                       outcome='Vài người vào chê số liệu láo. Phường hỏi thăm xưởng.')],
         default='correct'),
    dict(id='kid_visit', title='Bé nhà bên xin coi xe đua', emoji='🧒', npc=1, min_day=1, tone='gentle', at='open', weight=3, mods=None,
         text='Bé trai nhà bên đứng bám cửa xưởng, mắt tròn xoe nhìn chiếc xe đang lên băng thử.',
         options=[dict(id='show', label='Cho đứng sau vạch vàng, đưa nút bịt tai, chỉ cho bé đâu là phanh', hint='', effects=dict(xp=3, review=[5, 'Con tôi về kể xưởng chỉ cho cách phanh, an toàn ghê.', 4]), good=True,
                       outcome='Bé về kể cả buổi chiều về chiếc phanh “to như cái mâm”.'),
                  dict(id='shoo', label='Đuổi về cho an toàn', hint='', effects=dict(), good=None,
                       outcome='Bé lủi thủi về, chiều lại lấp ló ngoài cửa.')],
         default='shoo'),
]
