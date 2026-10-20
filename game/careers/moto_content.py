"""🏍️ Tiệm sửa xe Út Lanh: the words and tables of the motorbike repair shop (game/careers/moto.py).

Every table is static: a ticket is a pure function of (day, slot), so validate_state can rebuild it. The owner's rule
("nghề nào cũng phải có nhiều yêu cầu oái oăm"): each ticket carries one or two awkward customer demands (DEMANDS) and
the counter has its own surprises between tickets (DESK, kit.desk), some of which leave a mark that brings a later
event (a cheap box of "parts" bought off the street brings the ward police round two days later).
All numbers (pressures, oil volumes, wear limits) follow the shop's own notebook below; they are the game's rules.
"""
from __future__ import annotations

PLACE = 'Tiệm sửa xe Út Lanh'
OWNER = 'Út Lanh'

PEOPLE = [
    ('Út Lanh', 'Chủ tiệm sửa xe', 'Ba mươi năm cầm cờ lê, nghe tiếng máy là biết bệnh. Dặn hoài: an toàn trước, tiền sau.', 'warm'),
    ('Tèo', 'Thợ phụ, mười bảy tuổi', 'Rửa xe, bơm bánh, hay làm rơi ốc. Mê xem clip độ xe.', 'genz'),
    ('Bà Chín', 'Bán vé số đầu hẻm', 'Đẩy chiếc xe số cũ đi bán từ sáng tới tối, ít khi đủ tiền sửa.', 'warm'),
    ('Anh Khang', 'Shipper', 'Một ngày chạy trăm cây số, cần xe chạy lại ngay.', 'quiet'),
    ('Chị Mai', 'Nhân viên văn phòng', 'Chạy tay ga, nghe kêu “cạch” một cái là ghé tiệm.', 'picky'),
    ('Chú Hai Lúa', 'Người chơi xe cub cũ', 'Mê đồ zin, nghi tiệm nào cũng tráo đồ.', 'picky'),
    ('Bé Tí', 'Học sinh lớp 8', 'Ghé bơm xe đạp, đứng coi thợ làm cả buổi.', 'genz'),
    ('Anh Tài', 'Thanh niên mê độ xe', 'Muốn pô kêu to, đèn chớp bảy màu.', 'genz'),
]
MENTOR = 0
HELPER = 1
CUSTOMERS = (2, 3, 4, 5, 6, 7)

WRONG_COST = 8          # quality lost per redone step
QUALITY_FLOOR = 40
MILESTONES = (4, 10, 20, 40)   # days: a third step kind, a second demand, the harder faults
MASTER = (100, 30)      # Thợ vững tay: good tickets, active days
EXPERT = (180, 45)      # Thợ cả Út Lanh

BIKES = [
    ('Xe số 110 phân khối', 'so'), ('Xe cub 50 đời cũ', 'so'), ('Xe tay ga 125 phân khối', 'ga'),
    ('Xe tay ga 150 phân khối', 'ga'), ('Xe côn tay 150 phân khối', 'con'), ('Xe số 125 phân khối', 'so'),
]
COLORS = ('đỏ đô', 'xanh dương', 'đen nhám', 'trắng ngà', 'xám bạc', 'vàng chanh')
PROVINCES = ('59', '51', '61', '72', '43', '29')

# The faults a ticket can carry: name, emoji, min day, parts (xu, advanced against the ticket), labour (xu),
# the customer's complaint and what you see or hear.
FAULTS = {
    'thung_sam': dict(name='Thủng săm', emoji='🛞', day=1, cost=2, net=11,
                      say=('Bánh sau xẹp lép, em dắt bộ từ đầu hẻm vô.', 'Sáng bơm rồi, trưa lại xẹp.'),
                      see=('Lăn bánh từ từ thấy một cây đinh cắm ở lòng lốp.', 'Bóp thử, lốp mềm nhũn, nghe xì xì nhỏ.')),
    'thay_nhot': dict(name='Quá hạn thay nhớt', emoji='🛢️', day=1, cost=6, net=9,
                      say=('Dạo này máy nóng, chạy ì ì.', 'Lâu rồi chưa thay nhớt, em quên mất.'),
                      see=('Que thăm nhớt đen kịt, sát vạch dưới.', 'Tiếng máy lạch xạch, sờ lốc máy nóng ran.')),
    'bugi': dict(name='Bugi tới hạn', emoji='⚡', day=2, cost=4, net=10,
                 say=('Sáng đề hoài không nổ, nổ rồi chạy giật giật.', 'Lên dốc là hụt hơi.'),
                 see=('Rút chụp bugi đánh thử, tia lửa đỏ yếu.', 'Đề máy nổ không đều, pô phụt khói.')),
    'xich': dict(name='Sên chùng', emoji='⛓️', day=2, cost=1, net=10,
                 say=('Chạy nghe lạch cạch dưới chân.', 'Sang số nghe giật cục.'),
                 see=('Lắc sên ở giữa, sên đánh võng xuống.', 'Sên khô rang, có chỗ gỉ.')),
    'phanh': dict(name='Má phanh mòn', emoji='🛑', day=3, cost=5, net=12,
                  say=('Bóp thắng kêu ken két, phải bóp sát tay mới ăn.', 'Đổ dốc cầu mà thắng không ăn, sợ lắm.'),
                  see=('Soi má phanh qua khe, lớp bố mỏng dính.', 'Tay thắng bóp chạm sát tay lái.')),
    'den': dict(name='Đèn pha tắt', emoji='💡', day=4, cost=1, net=9,
                say=('Tối qua đang chạy, đèn pha tắt ngúm.', 'Bật pha không sáng, cos cũng không.'),
                see=('Bật công tắc, đèn trước không lên, đèn hậu vẫn sáng.', 'Mở hộp cầu chì thấy một cái đứt dây.')),
    'acquy': dict(name='Ắc quy yếu', emoji='🔋', day=5, cost=18, net=12,
                  say=('Bấm đề nghe tạch tạch rồi im.', 'Còi kêu yếu xìu, đèn xi-nhan chớp chậm.'),
                  see=('Bấm đề, đèn báo trên đồng hồ mờ hẳn.', 'Cọc bình lên một lớp phấn trắng.')),
    'ngap': dict(name='Xe lội nước chết máy', emoji='🌊', day=6, cost=7, net=16,
                 say=('Mưa ngập tới yên, em lội qua thì xe tắt máy.', 'Em đề mãi mà không nổ.'),
                 see=('Mở ốc xả, nhớt chảy ra trắng đục như sữa.', 'Ống pô nhỏ nước tong tong.')),
}
FAULT_ORDER = tuple(FAULTS)

# ---------------------------------------------------------------- the fault's own steps (moto.py builds them)
PLUG_LOOK = {   # what the old spark plug looks like → the honest reading (the soi step)
    'den_kho': ('đầu sứ đen muội khô như bồ hóng', 'Xăng giàu gió thiếu: kiểm lọc gió bẩn, chỉnh lại xăng gió'),
    'uot': ('ướt sũng, nồng mùi xăng', 'Máy ngộp xăng: lau khô bugi, kiểm bộ chế hòa khí hoặc kim phun'),
    'nau': ('màu nâu nhạt, đều', 'Máy đốt tốt: bugi chỉ là tới hạn thay'),
    'trang': ('trắng bệch, điện cực mòn cháy', 'Xăng nghèo, máy quá nóng: kiểm chỗ hở gió và loại bugi'),
}
SPROCKET = {    # the chain and sprockets: what you see → the honest answer
    'mon': ('Răng dĩa nhọn hoắt như lưỡi cưa, ốc tăng sên đã hết nấc', 'Báo khách thay cả bộ nhông, sên, dĩa'),
    'tot': ('Răng dĩa còn đều, ốc tăng sên còn nhiều nấc', 'Chỉ cần chỉnh độ chùng và tra nhớt sên'),
}
SPROCKET_WRONG = ('Thay riêng sợi sên, giữ dĩa mòn', 'Tháo bớt một mắt sên cho căng')
BATTERY = {     # the voltmeter reading → the conclusion
    'day': ('12,7', 'Bình đầy: tìm lỗi chỗ khác (củ đề, rơ-le đề)'),
    'yeu': ('12,3', 'Bình yếu: sạc chậm rồi đo lại'),
    'hong': ('11,4', 'Bình hỏng (sạc qua đêm vẫn tụt): thay bình mới'),
}
BATTERY_WRONG = 'Câu tạm bình của xe khác cho khách chạy về'
OIL_KIND = {
    'so': 'Nhớt xe số (JASO MA)',
    'con': 'Nhớt xe số (JASO MA)',
    'ga': 'Nhớt xe tay ga (JASO MB), thay luôn nhớt hộp số',
}
OIL_WRONG = ('Nhớt ô tô loại rẻ nhất', 'Nửa can nhớt cũ của khách trước')

STEPS = {
    'va': [('thao', 'Tháo bánh hoặc nạy lốp, rút săm ra'), ('tim', 'Bơm căng săm, nhúng chậu nước tìm chỗ sủi bọt'),
           ('cha', 'Đánh dấu lỗ, chà nhám quanh lỗ cho ráp'), ('keo', 'Quét keo, đợi keo se mặt'),
           ('dan', 'Dán miếng vá, miết chặt từ giữa ra mép'), ('dinh', 'Sờ lòng lốp, gỡ cây đinh còn cắm'),
           ('lap', 'Lắp săm, lốp và bánh lại')],
    'nhot': [('no', 'Nổ máy 2–3 phút cho nhớt ấm, loãng'), ('tat', 'Tắt máy, dựng chân chống giữa trên nền phẳng'),
             ('xa', 'Tháo ốc xả, hứng nhớt cũ vào khay'), ('long_den', 'Thay long đen mới, siết ốc xả vừa tay'),
             ('do', 'Đổ nhớt mới đúng lượng'), ('que', 'Nổ máy một phút, tắt, đợi rồi xem que thăm trong vạch')],
    'bugi': [('nguoi', 'Đợi máy nguội hẳn'), ('chup', 'Rút chụp bugi, thổi sạch bụi quanh chân bugi'),
             ('thao', 'Tháo bugi cũ bằng tuýp bugi'), ('khe', 'Kiểm khe hở bugi mới bằng thước lá'),
             ('van', 'Vặn bugi mới bằng tay cho ăn ren rồi mới siết'), ('chup2', 'Siết vừa lực, cắm lại chụp bugi')],
    'phanh': [('dung', 'Dựng chân chống giữa, chèn bánh'), ('thao', 'Tháo bánh (thắng đùm) hoặc heo dầu (thắng đĩa)'),
              ('bui', 'Chải bụi má phanh bằng cọ, không thổi bụi vào mặt'), ('lap', 'Lắp cặp má mới đúng chiều'),
              ('chinh', 'Chỉnh ốc tăng hoặc bóp vài lần cho má ăn'), ('thu', 'Thử thắng tại chỗ rồi mới chạy thử')],
    'sen': [('no_truc', 'Nới ốc trục bánh sau'), ('tang', 'Vặn hai ốc tăng sên đều nhau, cùng số vạch hai bên'),
            ('do', 'Đo lại độ chùng sên ở giữa'), ('siet', 'Siết chặt ốc trục bánh sau'), ('tra', 'Lau sên, tra nhớt sên')],
    'binh': [('tat', 'Tắt máy, rút chìa khóa'), ('am', 'Tháo cực âm (−) trước'), ('duong', 'Tháo cực dương (+) sau'),
             ('dat', 'Đặt bình mới đúng chiều, chèn chặt'), ('duong2', 'Lắp cực dương (+) trước'),
             ('am2', 'Lắp cực âm (−) sau, bôi mỡ chống gỉ cọc bình')],
    'ngap': [('bugi', 'Tháo bugi'), ('doc', 'Dốc đầu xe, đạp cần khởi động đẩy nước khỏi buồng đốt'),
             ('xa', 'Xả hết nhớt lẫn nước'), ('loc', 'Tháo, lau khô lọc gió và ống pô'), ('nhot', 'Đổ nhớt mới'),
             ('lap', 'Lau khô bugi, lắp lại rồi mới đề thử')],
}
LIGHT_GOOD = ('Cầu chì trong hộp', 'Bóng đèn (dây tóc có đứt không)', 'Giắc cắm sau chóa đèn', 'Công tắc pha cốt')
LIGHT_BAD = ('Thay luôn cả cụm đèn mới cho nhanh', 'Đấu thẳng dây từ bình vào bóng')
FUSE_BLOWS = ('Cầu chì mới vừa lắp, bật đèn là đứt liền.',
              'Dừng lại, dò chỗ dây điện chạm mát (chập) rồi mới thay cầu chì',
              ('Lắp cầu chì to gấp đôi cho khỏi đứt', 'Quấn giấy bạc thay cầu chì', 'Thay cầu chì liên tục tới khi chịu'))
FLOOD_FIRST = ('Xe lội nước tắt máy, khách đứng chờ. Việc đầu tiên?',
               'Không đề, không đạp nổ: dắt vào, tháo bugi trước',
               ('Đề liên tục cho tới khi máy nổ', 'Đạp nổ thật mạnh vài cái', 'Phơi nắng nửa tiếng rồi đề'))
BRAKE_OK = 'Chưa tới giới hạn: vệ sinh, chỉnh lại, hẹn kiểm lần sau'
BRAKE_NEW = 'Đã tới giới hạn: thay cặp má phanh mới'
BRAKE_WRONG = ('Xịt dầu bôi trơn vào má phanh cho hết kêu', 'Thay cả bộ đĩa và heo dầu cho chắc ăn')

# ---------------------------------------------------------------- 🌀 oái oăm at the counter (one or two a ticket)
# (min day, what the customer says, the right answer, the wrong ones, only for these faults or None)
DEMANDS = [
    (1, 'Khách: “Lấy nhớt rẻ nhất cho em, nhớt xe số đổ xe tay ga cũng được mà.”',
     'Nói rõ xe tay ga cần đúng nhớt tay ga, báo giá chênh lệch để khách chọn', ('Đổ nhớt xe số cho rẻ, khách muốn vậy', 'Đổ nửa nhớt số nửa nhớt ga'), ('thay_nhot',)),
    (1, 'Khách: “Đừng thay gì hết, làm sao cho hết kêu là được.”',
     'Nói thật chỗ hư và mức nguy hiểm; khách không thay thì ghi phiếu khách từ chối', ('Xịt dầu cho hết kêu rồi trả xe', 'Lặng lẽ thay luôn rồi tính tiền'), None),
    (1, 'Khách: “Năm phút nữa em phải đón con, làm lẹ giùm!”',
     'Báo thật thời gian cần làm, làm đủ bước; gấp thì gọi xe ôm giúp khách', ('Bỏ bớt bước siết ốc cho kịp', 'Hứa năm phút rồi làm nửa tiếng'), None),
    (1, 'Khách: “Món thay ra đưa lại tôi coi, tiệm hay tráo đồ lắm.”',
     'Bỏ đồ cũ vào túi, đưa khách xem và giữ lại', ('Vứt đồ cũ, nói “đồ hư giữ làm gì”', 'Cãi lại: “Tiệm tôi không tráo!”'), None),
    (2, 'Khách: “Bớt nửa giá đi, tiệm đầu hẻm làm có một nửa.”',
     'Giữ giá công, chỉ ra hạng mục cần làm trước nếu khách muốn bớt', ('Bớt nửa giá rồi dùng đồ dỏm bù', 'Đuổi khách đi'), None),
    (2, 'Khách: “Tháo luôn hai cái gương giùm, để vậy mới đẹp.”',
     'Không tháo gương: xe chạy đường phải có gương chiếu hậu', ('Tháo gương, khách muốn mà', 'Tháo một cái thôi'), None),
    (2, 'Khách: “Thay nhớt tuần trước rồi mà!” nhưng tem dán ghi thay từ ba tháng trước.',
     'Chỉ tem và số km cho khách xem, để khách quyết thay hay không', ('Gật đầu cho qua, không thay', 'Thay luôn khỏi hỏi'), ('thay_nhot',)),
    (3, 'Khách: “Gửi xe qua đêm, khỏi phiếu khỏi ghi, quen mà.”',
     'Vẫn ghi phiếu gửi xe, chụp số km và đồ để trong cốp', ('Dắt vào, khỏi ghi gì', 'Không nhận gửi'), None),
    (3, 'Khách: “Lắp cầu chì to hơn cho khỏi đứt nữa.”',
     'Lắp đúng số ampe ghi trên nắp hộp, dò chỗ chập', ('Lắp cầu chì to gấp đôi', 'Nối tắt luôn khỏi cầu chì'), ('den',)),
    (4, 'Khách: “Đề thử cái coi nổ chưa, đề liền đi!” khi xe vừa lội nước.',
     'Không đề khi chưa xả nước buồng đốt và nhớt', ('Đề thử một cái cho khách yên tâm', 'Đạp nổ thay vì đề'), ('ngap',)),
    (4, 'Phụ huynh: “Tháo bộ hạn chế cho xe 50 phân khối của thằng nhỏ chạy nhanh hơn.”',
     'Từ chối: xe học sinh giữ nguyên như thiết kế', ('Tháo lén, lấy thêm tiền', 'Chỉnh vừa vừa thôi'), None),
    (5, 'Khách tự mua bugi trên mạng, không rõ hàng, đòi lắp.',
     'Kiểm mã bugi đúng loại xe rồi mới lắp, ghi phiếu đồ khách mang tới', ('Lắp liền khỏi coi', 'Từ chối, bắt mua bugi của tiệm'), ('bugi',)),
    (5, 'Khách: “Chạy thử xong chở luôn em ra chợ, tiện đường.”',
     'Chạy thử một vòng quanh tiệm, không dùng xe khách việc riêng', ('Chở khách đi chợ luôn', 'Chạy thử lên tận cầu cho chắc'), None),
    (6, 'Khách: “Chỉnh đồng hồ km lùi xuống giùm, tuần sau em bán xe.”',
     'Từ chối: không chỉnh số km để bán xe', ('Lùi bớt chút thôi', 'Lùi được, tính giá gấp đôi'), None),
    (8, 'Khách: “Ắc quy còn bảo hành, đổi bình mới mà ghi phiếu là hỏng do tiệm.”',
     'Ghi đúng tình trạng bình, hướng dẫn khách mang phiếu mua tới đại lý bảo hành', ('Ghi phiếu theo ý khách', 'Đổi bình rồi khỏi ghi'), ('acquy',)),
]

CHECKS_GOOD = ('Chạy thử một vòng quanh tiệm', 'Trả túi đồ cũ đã thay cho khách xem',
               'Ghi phiếu bảo hành và số km lần bảo dưỡng tới', 'Siết lại mọi con ốc vừa tháo')
CHECKS_BAD = ('Đổ thêm xăng rồi tính tiền khách', 'Lau xe bằng xăng cho bóng', 'Chở bạn đi ăn sáng thay cho chạy thử')

RULES = [
    'Mọi con số dưới đây là sổ tay của tiệm Út Lanh, luật của trò chơi.',
    'Nghe khách tả bệnh, nhìn và nghe xe rồi mới chốt lỗi. Chưa chốt lỗi thì chưa đụng cờ lê.',
    'Áp suất lốp theo tem dán trên càng xe; chở thêm người hoặc hàng thì cộng 3 psi bánh sau.',
    'Thay nhớt: nổ máy cho nhớt ấm → tắt máy, chân chống giữa → xả nhớt cũ → long đen mới, siết ốc xả → đổ đúng lượng → xem que thăm. Xe tay ga dùng nhớt tay ga (JASO MB) và thay nhớt hộp số; xe số, xe côn tay dùng nhớt xe số (JASO MA).',
    'Lượng nhớt: thay nhớt theo dòng “thay nhớt” trong sổ xe, không theo dòng “rã máy”.',
    'Vá săm: tháo săm → bơm căng, nhúng nước tìm lỗ → chà nhám → quét keo đợi se → dán, miết từ giữa ra → gỡ đinh trong lốp → lắp lại.',
    'Bugi: đợi máy nguội → thổi bụi quanh chân → tháo → kiểm khe hở bugi mới → vặn tay cho ăn ren → siết vừa lực. Soi đầu bugi cũ để biết máy đốt ra sao.',
    'Sên: độ chùng chỉnh về giữa khoảng trong sổ; hai ốc tăng vặn đều, cùng số vạch. Dĩa nhọn như lưỡi cưa thì thay cả bộ nhông sên dĩa.',
    'Má phanh: mỏng tới giới hạn thì thay; chưa tới thì vệ sinh, chỉnh. Không bao giờ xịt dầu vào má phanh. Hành trình tự do tay thắng chỉnh về giữa khoảng.',
    'Ắc quy: ≥ 12,6 V là đầy, 12,2–12,5 V là yếu (sạc chậm), dưới 12 V mà sạc vẫn tụt là hỏng. Tháo cực âm trước, lắp cực âm sau. Giờ sạc ≈ dung lượng (Ah) chia dòng sạc (A), làm tròn lên.',
    'Đèn tắt: kiểm cầu chì, bóng, giắc, công tắc. Cầu chì đúng số ampe trên nắp hộp; mới thay lại đứt là có chỗ chập.',
    'Xe lội nước: không đề, không đạp. Tháo bugi → đẩy nước khỏi buồng đốt → xả nhớt lẫn nước (súc hai lần) → lau lọc gió, pô → đổ nhớt mới → lắp bugi rồi mới đề.',
    'Trước khi giao: chạy thử quanh tiệm, trả túi đồ cũ, ghi phiếu bảo hành, siết lại ốc. Giao đúng xe theo phiếu: so biển số.',
    'Không chỉnh lùi số km, không tháo gương, không độ pô, không tháo hạn chế xe học sinh, không mua phụ tùng không rõ nguồn.',
]

# ---------------------------------------------------------------- 🔔 desk surprises (kit.desk): chuyện ở tiệm
DESK = [
    dict(id='key_left', title='Chìa khóa cắm quên trong ổ', emoji='🔑', npc=3, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Anh Khang gửi xe chờ thay nhớt rồi chạy đi giao hàng bộ, chìa khóa còn cắm trong ổ, xe đậu sát lề.',
         options=[dict(id='keep', label='Rút chìa cất vào hộc tủ, dắt xe vào trong, nhắn anh Khang', hint='',
                       effects=dict(xp=5, review=[5, 'Tiệm giữ chìa giùm, còn nhắn tin báo, yên tâm ghê.', 3]), good=True,
                       outcome='Anh Khang về, thấy tin nhắn, cảm ơn rối rít.'),
                  dict(id='leave', label='Kệ, xe ngay trước tiệm mà', hint='', effects=dict(patience=-2), good=None,
                       outcome='Một thằng nhỏ lạ ngồi lên xe vặn ga thử, Tèo phải chạy ra đuổi.'),
                  dict(id='ride', label='Chạy xe anh ấy đi mua cà phê luôn cho tiện', hint='',
                       effects=dict(review=[1, 'Tiệm lấy xe khách đi việc riêng, hết tin.', 3]), good=False,
                       outcome='Anh Khang về sớm, thấy xe mất, hốt hoảng gọi điện.')],
         default='leave'),
    dict(id='cheap_parts', title='Thùng phụ tùng giá rẻ bất ngờ', emoji='📦', npc=7, min_day=3, tone='tense', at='between', weight=2, mods=None,
         no_mark='parts_bought',
         text='Một người lạ chở tới thùng bố thắng, bugi, sên còn mới, bán bằng một phần ba giá chợ, không hóa đơn, không nói lấy ở đâu.',
         options=[dict(id='refuse', label='Từ chối: phụ tùng không rõ nguồn thì tiệm không mua', hint='',
                       effects=dict(xp=6, mark='parts_refused'), good=True,
                       outcome='Người lạ lầm bầm bỏ đi. Út Lanh gật đầu: “Rẻ quá là có chuyện.”'),
                  dict(id='buy', label='Mua hết, lời to', hint='', effects=dict(money=-12, mark='parts_bought'), good=False,
                       outcome='Thùng phụ tùng chất trong kho. Mấy ngày sau mới biết chuyện.'),
                  dict(id='ask', label='Hỏi giấy tờ, không có thì thôi', hint='', effects=dict(xp=4, mark='parts_refused'), good=True,
                       outcome='Người lạ nói “để mai mang giấy”, rồi không bao giờ quay lại.')],
         default='refuse'),
    dict(id='police_parts', title='Công an phường ghé hỏi lô phụ tùng', emoji='👮', npc=0, min_day=5, tone='tense', at='between', weight=5, mods=None,
         need_mark='parts_bought',
         text='Anh công an khu vực ghé: có một vụ trộm kho phụ tùng ở phường bên. Thùng hàng mua hôm trước khớp mô tả.',
         options=[dict(id='hand', label='Giao nộp thùng phụ tùng, kể rõ người bán và ngày mua', hint='',
                       effects=dict(xp=4, unmark='parts_bought', review=[3, 'Tiệm có mua nhầm đồ gian nhưng chịu khai báo đàng hoàng.', 0]), good=True,
                       outcome='Anh công an ghi biên bản, cảm ơn vì đã hợp tác. Tiền mua coi như mất.'),
                  dict(id='hide', label='Nói không biết gì, giấu thùng ra sau', hint='',
                       effects=dict(unmark='parts_bought', money=-30, money_loss='fine', review=[1, 'Tiệm chứa đồ gian còn chối.', 0]), good=False,
                       outcome='Thùng hàng bị tìm thấy. Tiệm bị phạt 30 xu và cả hẻm bàn tán.')],
         default='hand'),
    dict(id='grandma', title='Bà Chín đẩy xe xẹp bánh, không đủ tiền', emoji='👵', npc=2, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Bà Chín đẩy chiếc xe số cũ tới, bánh sau xẹp lép, móc túi chỉ còn mấy tờ vé số chưa bán.',
         options=[dict(id='free', label='Vá miễn phí, mời bà ly nước, khỏi trả', hint='', effects=dict(xp=6, mark='grandma_helped', money=-2), good=True,
                       outcome='Bà Chín cười móm mém: “Trúng số bà mua bánh cho con.”'),
                  dict(id='later', label='Vá rồi ghi sổ, bà rảnh thì trả', hint='', effects=dict(xp=3, mark='grandma_helped'), good=True,
                       outcome='Bà gật đầu, hứa cuối tuần ghé trả.'),
                  dict(id='no', label='Không có tiền thì tiệm chịu', hint='', effects=dict(review=[2, 'Bà già đẩy xe mà tiệm làm lơ.', 2]), good=False,
                       outcome='Bà Chín đẩy xe đi tiếp dưới nắng, Tèo nhìn theo.')],
         default='later'),
    dict(id='grandma_thanks', title='Bà Chín mang chè tới cảm ơn', emoji='🍮', npc=2, min_day=4, tone='gentle', at='between', weight=5, mods=None,
         need_mark='grandma_helped',
         text='Bà Chín xách bịch chè đậu trắng tới: “Hôm bữa con vá xe cho bà, bà bán được hết xấp vé.”',
         options=[dict(id='thanks', label='Nhận chè, mời bà ngồi nghỉ, kiểm luôn hơi bánh xe cho bà', hint='',
                       effects=dict(xp=4, unmark='grandma_helped', review=[5, 'Tiệm Út Lanh tốt bụng, ai trong hẻm cũng biết.', 2]), good=True,
                       outcome='Cả tiệm ăn chè. Bà Chín kể khắp hẻm, chiều có thêm ba khách mới.'),
                  dict(id='busy', label='Bận quá, cảm ơn bà rồi làm tiếp', hint='', effects=dict(unmark='grandma_helped'), good=None,
                       outcome='Bà Chín để bịch chè trên ghế rồi đi.')],
         default='busy'),
    dict(id='loud_pipe', title='Anh Tài đòi độ pô kêu to', emoji='🔊', npc=7, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Anh Tài dựng xe giữa tiệm: “Khoét pô cho kêu to như xe đua, tháo luôn đèn hậu cho gọn, tiền không thành vấn đề.”',
         options=[dict(id='refuse', label='Từ chối độ pô và tháo đèn, giới thiệu dọn pô cho êm, sáng đèn đúng chuẩn', hint='',
                       effects=dict(xp=5), good=True, outcome='Anh Tài bĩu môi bỏ đi, chiều lại quay lại thay bóng đèn hậu.'),
                  dict(id='do', label='Làm luôn, có tiền thì làm', hint='', effects=dict(money=10, review=[1, 'Tiệm độ pô ồn cả hẻm, đêm ngủ không yên.', 2]), good=False,
                       outcome='Tối đó cả hẻm bị đánh thức. Tổ trưởng ghé hỏi tiệm nào độ pô.')],
         default='refuse'),
    dict(id='zin', title='Chú Hai Lúa nghi tráo đồ zin', emoji='🧐', npc=5, min_day=3, tone='tense', at='between', weight=3, mods=None,
         text='Chú Hai Lúa quay lại, mặt hầm hầm: “Cái bộ chế hòa khí zin của tôi tiệm tráo đồ lô rồi phải không?”',
         options=[dict(id='show', label='Mở sổ phiếu, chỉ ảnh chụp lúc nhận xe và dấu sơn đánh trên đồ zin', hint='',
                       effects=dict(xp=6, review=[5, 'Tiệm chụp ảnh, đánh dấu đồ đàng hoàng. Phục.', 5]), good=True,
                       outcome='Chú Hai soi dấu sơn, gãi đầu: “Ờ… đúng của tôi.” Rồi gửi luôn chiếc cub thứ hai.'),
                  dict(id='argue', label='Cãi tay đôi: “Tiệm tôi làm ăn đàng hoàng!”', hint='', effects=dict(review=[2, 'Hỏi có một câu mà tiệm to tiếng.', 5]), good=False,
                       outcome='Hai bên lớn tiếng, khách khác đứng xem.'),
                  dict(id='refund', label='Trả lại tiền cho xong chuyện', hint='', effects=dict(money=-8), good=None,
                       outcome='Chú Hai cầm tiền đi, vẫn nói tiệm có tật giật mình.')],
         default='refund'),
    dict(id='flood_line', title='Mưa ngập, năm chiếc xe chết máy xếp hàng', emoji='🌧️', npc=0, min_day=4, tone='tense', at='any', weight=2, mods=None,
         text='Mưa to nửa tiếng, nước ngập tới gối. Năm người dắt xe chết máy tới cùng lúc, ai cũng đòi làm trước.',
         options=[dict(id='queue', label='Phát số thứ tự, ưu tiên người chở người già và trẻ nhỏ, dặn ai cũng đừng đề xe', hint='',
                       effects=dict(xp=7, review=[5, 'Mưa ngập mà tiệm xếp số đàng hoàng, dặn kỹ.', 3]), good=True,
                       outcome='Út Lanh và Tèo làm tới tối, không xe nào bị đề thủy kích.'),
                  dict(id='loud', label='Ai trả nhiều hơn làm trước', hint='', effects=dict(money=6, review=[1, 'Tiệm thấy ngập là chặt chém.', 3]), good=False,
                       outcome='Mấy người bỏ đi tiệm khác, vừa đi vừa chửi.'),
                  dict(id='close', label='Đóng cửa, ngập quá thì nghỉ', hint='', effects=dict(patience=-3), good=None,
                       outcome='Người dắt xe đứng dưới mưa gõ cửa.')],
         default='close'),
    dict(id='bad_fuel', title='Xăng pha nước từ cây xăng lạ', emoji='⛽', npc=4, min_day=5, tone='tense', at='between', weight=2, mods=None,
         text='Chị Mai đổ xăng ở cây xăng lạ, chạy được một đoạn thì giật cục rồi tắt. Chị đòi tiệm “làm sao cho hết”.',
         options=[dict(id='drain', label='Xả bình xăng, giữ lại một chai mẫu, ghi phiếu để chị khiếu nại cây xăng', hint='',
                       effects=dict(xp=6, review=[5, 'Tiệm còn giữ mẫu xăng cho mình đi khiếu nại.', 4]), good=True,
                       outcome='Chị Mai mang chai mẫu đi, tuần sau được cây xăng đền.'),
                  dict(id='additive', label='Bán chai phụ gia “khử nước” giá cao', hint='', effects=dict(money=4, review=[2, 'Bán chai nước gì đâu mà xe vẫn giật.', 4]), good=False,
                       outcome='Xe chạy thêm hai cây số rồi tắt tiếp.')],
         default='drain'),
    dict(id='cat_engine', title='Con mèo ngủ trên lốc máy', emoji='🐈', npc=1, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='Sáng mở cửa, con mèo hoang cuộn tròn ngủ ngay trên lốc máy chiếc xe gửi qua đêm, còn ấm.',
         options=[dict(id='gentle', label='Gõ yên xe, đợi mèo tự chui ra rồi mới nổ máy', hint='', effects=dict(xp=4), good=True,
                       outcome='Mèo vươn vai bỏ đi. Tèo đặt ở góc tiệm cái thùng giấy lót áo cũ.'),
                  dict(id='start', label='Nổ máy luôn, nó tự chạy', hint='', effects=dict(review=[2, 'Sáng sớm nghe mèo kêu thét trong tiệm, sợ quá.', 4]), good=False,
                       outcome='Mèo hoảng nhảy tung, cào xước yên xe của khách.')],
         default='gentle'),
    dict(id='odometer', title='Người lạ nhờ lùi đồng hồ km', emoji='🕵️', npc=7, min_day=4, tone='tense', at='between', weight=2, mods=None,
         text='Một người dắt chiếc tay ga đời mới: “Lùi giùm đồng hồ còn một vạn cây, mai bán được giá, chia em phân nửa.”',
         options=[dict(id='refuse', label='Từ chối thẳng, không lùi số km', hint='', effects=dict(xp=6), good=True,
                       outcome='Người đó dắt xe đi. Út Lanh: “Mình sửa xe, không sửa sự thật.”'),
                  dict(id='do', label='Lùi đồng hồ, lấy tiền công gấp ba', hint='', effects=dict(money=15, mark='odo_faked'), good=False,
                       outcome='Tiền vào túi, nhưng biển tiệm nằm trong ảnh người mua chụp lại.')],
         default='refuse'),
    dict(id='odo_buyer', title='Người mua xe quay lại tố tiệm', emoji='📸', npc=4, min_day=6, tone='tense', at='between', weight=5, mods=None,
         need_mark='odo_faked',
         text='Người mua chiếc tay ga hôm trước dắt xe tới, cầm ảnh đồng hồ: “Hãng nói xe chạy bốn vạn rồi. Ai lùi số?”',
         options=[dict(id='own', label='Nhận lỗi, trả lại tiền công đã lấy, chỉ người bán cho khách', hint='',
                       effects=dict(unmark='odo_faked', money=-15, money_loss='fine', review=[2, 'Tiệm từng lùi đồng hồ km, có nhận lỗi.', 4]), good=None,
                       outcome='Mất tiền, mất tiếng, nhưng ít ra đã nói thật.'),
                  dict(id='deny', label='Chối, nói tiệm không biết', hint='',
                       effects=dict(unmark='odo_faked', review=[1, 'Tiệm lùi đồng hồ km lừa người mua, còn chối.', 4]), good=False,
                       outcome='Khách đăng ảnh lên nhóm của phường. Cả tuần vắng khách.')],
         default='own'),
    dict(id='teo_bolt', title='Tèo làm rơi con ốc vào lốc máy', emoji='🔩', npc=1, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Tèo lí nhí: “Em… em làm rớt con ốc nhỏ vô lỗ bugi xe chị Mai rồi.”',
         options=[dict(id='fish', label='Không nổ máy, dùng nam châm que gắp ốc ra, kiểm lại buồng đốt', hint='', effects=dict(xp=6), good=True,
                       outcome='Gắp được ốc ra sau mười phút. Tèo thở phào, từ đó đặt ốc vào khay.'),
                  dict(id='start', label='Nổ máy thử, chắc nó văng ra', hint='', effects=dict(money=-20, money_loss='normal', review=[1, 'Gửi xe thay bugi mà máy bị xước xi-lanh.', 4]), good=False,
                       outcome='Máy kêu rắc một tiếng. Tiệm phải bù tiền làm lại máy.'),
                  dict(id='scold', label='La Tèo một trận trước khách', hint='', effects=dict(patience=-2), good=None,
                       outcome='Tèo đỏ mặt. Ốc vẫn nằm trong máy, Út Lanh phải tự gắp.')],
         default='scold'),
    dict(id='free_pump', title='Bé Tí xin bơm bánh xe đạp', emoji='🚲', npc=6, min_day=1, tone='gentle', at='open', weight=3, mods=None,
         text='Bé Tí đeo cặp, dắt xe đạp: “Cô ơi bơm giùm con, con trễ học rồi.”',
         options=[dict(id='pump', label='Bơm liền, miễn phí, dặn bánh trước bánh sau', hint='', effects=dict(xp=3, review=[5, 'Con tôi nói tiệm bơm xe miễn phí, cảm ơn nhiều.', 6]), good=True,
                       outcome='Bé Tí đạp đi, ngoái lại vẫy tay.'),
                  dict(id='charge', label='Bơm, lấy tiền như khách thường', hint='', effects=dict(money=1), good=None,
                       outcome='Bé Tí móc đồng xu cuối cùng trong túi.')],
         default='pump'),
]
