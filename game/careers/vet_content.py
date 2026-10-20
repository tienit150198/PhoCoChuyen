"""🩺 Phòng khám Thú y Cỏ May: the words and tables of the vet clinic (game/careers/vet.py).

Every table is static: a case is a pure function of (day, slot), so validate_state can rebuild it. The owner's rule
("nghề nào cũng phải có nhiều yêu cầu oái oăm"): each case carries one or two awkward owner demands (DEMANDS) and the
clinic has its own surprises between cases (DESK, kit.desk), some of which leave a mark that brings a later event (a
fake vaccination book signed for a neighbour brings the ward's animal-health officer round days later).
All numbers (temperatures, doses, fasting hours, fluid rates) follow the clinic's own notebook below; they are the
game's rules, simplified for play, never medical advice for a real animal.
"""
from __future__ import annotations

PLACE = 'Phòng khám Thú y Cỏ May'
MENTOR_NAME = 'Bác sĩ Thảo'

PEOPLE = [
    ('Bác sĩ Thảo', 'Trưởng phòng khám', 'Mười lăm năm khám chó mèo trong hẻm. Nhỏ nhẹ, nhưng sai quy trình là nhắc ngay.', 'warm'),
    ('Chị Duyên', 'Trợ lý, lễ tân', 'Giữ sổ tiêm, cân bé, ôm bé giỏi nhất phòng khám.', 'quiet'),
    ('Cô Ba Mập', 'Chủ bé Lu (chó ta)', 'Thương chó như con, hay nghe mẹo trên mạng.', 'warm'),
    ('Anh Hùng', 'Chủ bé Mướp (mèo)', 'Nhân viên ngân hàng, lúc nào cũng vội.', 'picky'),
    ('Bé Na', 'Học sinh lớp 6', 'Nuôi hamster, mang cả lồng tới khám.', 'genz'),
    ('Chú Tư', 'Chủ quán nhậu đầu hẻm', 'Nuôi chó giữ nhà, tiếc tiền thuốc.', 'quiet'),
    ('Chị Vy', 'Chủ bé Bông (chó Poodle)', 'Mê làm đẹp cho chó, đòi gì cũng phải liền.', 'picky'),
    ('Ông Sáu', 'Chủ bé Mun (mèo già)', 'Ở một mình với con mèo mười bốn tuổi.', 'warm'),
]
MENTOR = 0
HELPER = 1
OWNERS = (2, 3, 4, 5, 6, 7)

WRONG_COST = 8
QUALITY_FLOOR = 40
MILESTONES = (4, 10, 20, 40)
MASTER = (90, 30)       # Bác sĩ vững tay: good cases, active days
EXPERT = (170, 45)      # Bác sĩ chính của Cỏ May

# The pets that come in: (name, kind dog/cat, what it is)
PETS = [
    ('Lu', 'dog', 'chó ta vàng'), ('Bông', 'dog', 'chó Poodle trắng'), ('Ki', 'dog', 'chó Phốc sóc'), ('Mực', 'dog', 'chó ta đen'),
    ('Mướp', 'cat', 'mèo mướp'), ('Mun', 'cat', 'mèo đen'), ('Miu', 'cat', 'mèo Anh lông ngắn'), ('Bơ', 'cat', 'mèo vàng'),
]
COLLARS = ('vòng cổ đỏ', 'vòng cổ xanh', 'vòng cổ vàng', 'không vòng cổ')

# The cases: name, emoji, min day, bonus (xu, before quality), which pets (dog / cat / both), the owner's words, what
# you see on the table.
CASES = {
    'tiem': dict(name='Tiêm phòng định kỳ', emoji='💉', day=1, bonus=6, kinds=('dog', 'cat'),
                 say=('Tới hẹn tiêm nhắc rồi bác sĩ ơi.', 'Mới nhận nuôi, chưa tiêm mũi nào.'),
                 see=('Bé lanh lợi, mũi ướt, ăn uống bình thường.', 'Bé lông mượt, chạy nhảy quanh bàn khám.')),
    'cat_mong': dict(name='Cắt móng', emoji='✂️', day=1, bonus=5, kinds=('dog', 'cat'),
                     say=('Móng dài cào rách hết ghế sô-pha.', 'Bé đi trên gạch nghe lạch cạch.'),
                     see=('Móng cong dài, có móng sắp đâm vào đệm thịt.', 'Móng trắng thấy rõ phần hồng bên trong.')),
    've': dict(name='Ve chó, bọ chét', emoji='🪲', day=2, bonus=6, kinds=('dog',),
               say=('Bé gãi suốt đêm, sờ thấy cục cục sau tai.', 'Dắt đi dạo bãi cỏ về là gãi.'),
               see=('Vạch lông sau tai thấy mấy con ve căng tròn bám chặt.', 'Kẽ chân có ve nhỏ, da đỏ vì gãi.')),
    'socola': dict(name='Ăn nhầm sô-cô-la', emoji='🍫', day=3, bonus=8, kinds=('dog',),
                   say=('Nó ăn sạch hộp sô-cô-la đen trên bàn!', 'Thằng nhỏ cho nó ăn nửa thanh sô-cô-la.'),
                   see=('Giấy bọc sô-cô-la rách tả tơi trong túi chủ mang theo.', 'Bé thở nhanh, đi tới đi lui không yên.')),
    'parvo': dict(name='Nôn, tiêu chảy ra máu', emoji='🦠', day=4, bonus=9, kinds=('dog',),
                  say=('Cún mới mua tuần trước, nôn từ hôm qua, đi ngoài có máu.', 'Bé bỏ ăn hai ngày, nằm lì.'),
                  see=('Cún hai tháng tuổi, chưa tiêm phòng, mắt trũng, phân lẫn máu mùi tanh.', 'Cún lả, sờ da kéo lên chậm xẹp: mất nước.')),
    'tac_tieu': dict(name='Mèo đực rặn tiểu không ra', emoji='🚽', day=5, bonus=9, kinds=('cat',),
                     say=('Nó ngồi khay cát hoài mà không ra giọt nào.', 'Nó kêu rên mỗi lần đi vệ sinh.'),
                     see=('Mèo đực, sờ bụng dưới thấy bàng quang căng cứng như trái chanh.', 'Khay cát khô ran cả ngày.')),
    'di_vat': dict(name='Nuốt dị vật', emoji='🧦', day=6, bonus=9, kinds=('dog', 'cat'),
                   say=('Nó nuốt mất chiếc vớ, giờ nôn ọe hoài.', 'Sợi chỉ thòng ra miệng, kéo không ra.'),
                   see=('Phim X-quang thấy một khối tròn trong dạ dày.', 'Bé nôn sau mỗi lần uống nước.')),
    'triet_san': dict(name='Triệt sản theo hẹn', emoji='🩹', day=8, bonus=8, kinds=('dog', 'cat'),
                      say=('Hẹn mổ triệt sản hôm nay đó bác sĩ.', 'Nhà đông mèo quá, triệt sản cho bé luôn.'),
                      see=('Bé khỏe, đã khám tiền mê hôm trước.', 'Phiếu hẹn mổ ghi giờ mổ chiều nay.')),
}
CASE_ORDER = tuple(CASES)

# ---------------------------------------------------------------- the case's own steps (vet.py builds them)
NORMAL_TEMP = dict(dog=(38, 39), cat=(38, 39))      # °C, whole-degree band of the notebook (simplified)
TEMP_READ = {   # the reading → the honest decision (the vaccination's nhiet step)
    'ok': 'Thân nhiệt bình thường: tiêm được',
    'sot': 'Đang sốt: hoãn tiêm, khám tìm nguyên nhân, hẹn lại',
}
TEMP_WRONG = ('Tiêm luôn, tiêm xong là hết sốt', 'Tiêm nửa liều cho nhẹ')
STEPS = {
    'tiem': [('so', 'Xem sổ tiêm, hỏi bé có ốm gần đây không'), ('lay', 'Lấy vắc xin trong tủ mát, kiểm hạn dùng'),
             ('lac', 'Pha, lắc đều lọ vắc xin'), ('sat', 'Sát trùng chỗ tiêm'), ('tiem', 'Tiêm dưới da vùng gáy'),
             ('ghi', 'Dán tem lọ vào sổ, ghi ngày hẹn mũi nhắc'), ('doi', 'Dặn chủ ngồi chờ theo dõi 30 phút')],
    'mong': [('om', 'Chị Duyên ôm giữ bé nhẹ nhàng'), ('an', 'Ấn đệm thịt cho móng lộ ra'),
             ('soi', 'Soi tìm phần hồng (tủy móng)'), ('cat', 'Cắt cách tủy 2 mm, từng móng một'),
             ('dua', 'Dũa mép móng cho khỏi sắc'), ('thuong', 'Khen, thưởng bé một miếng bánh')],
    've': [('gang', 'Đeo găng tay'), ('nhip', 'Kẹp nhíp sát da, ngay đầu con ve'), ('keo', 'Kéo thẳng ra từ từ, không xoắn, không bóp thân ve'),
           ('sat', 'Sát trùng chỗ ve cắn'), ('con', 'Bỏ ve vào lọ cồn, đậy kín')],
    'parvo': [('ao', 'Mặc áo choàng, đeo găng trước khi vào phòng cách ly'), ('kham', 'Khám, đặt kim truyền dịch cho bé'),
              ('rac', 'Gom chất thải vào túi riêng, cột kín'), ('lau', 'Lau sàn, chuồng bằng dung dịch sát trùng'),
              ('thay', 'Cởi áo choàng, găng, rửa tay ngay ở cửa phòng cách ly')],
    'mo': [('kham', 'Khám tiền mê, nghe tim phổi'), ('nhin', 'Hỏi chắc bé đã nhịn ăn đúng giờ'), ('cao', 'Cạo lông, sát trùng vùng mổ'),
           ('me', 'Gây mê, theo dõi nhịp thở'), ('mo', 'Mổ, khâu vết mổ'), ('tinh', 'Giữ ấm, theo dõi tới khi bé tỉnh hẳn')],
    'kham': [('nhin', 'Nhìn tổng thể: dáng đi, lông, mắt, mũi'), ('tai', 'Soi tai, xem răng lợi'), ('tim', 'Nghe tim phổi'),
             ('bung', 'Sờ nắn bụng nhẹ nhàng'), ('nhiet', 'Đo thân nhiệt'), ('ghi', 'Ghi sổ khám, dặn chủ')],
}
PIPETTE = ((4, 'Ống cho chó dưới 4 kg'), (10, 'Ống cho chó 4–10 kg'), (25, 'Ống cho chó 10–25 kg'), (40, 'Ống cho chó 25–40 kg'))
TICK_GOOD = ('Nhỏ thuốc lại sau một tháng', 'Giặt, phơi nắng ổ nằm của bé', 'Kiểm kẽ chân, sau tai mỗi lần dắt về')
TICK_BAD = ('Bôi dầu hỏa cho ve tự rụng', 'Nhỏ chung ống thuốc chó cho con mèo trong nhà')
QUICK_BLEED = ('Lỡ cắt trúng tủy móng, rỉ máu.',
               'Ấn bột cầm máu vào đầu móng, giữ một phút, nói thật với chủ',
               ('Giấu đi, lau máu rồi trả bé', 'Băng kín cả bàn chân thật chặt', 'Cắt sâu thêm cho bằng'))
CHOC_EARLY = ('Bé ăn sô-cô-la cách đây 30 phút, chưa có dấu hiệu gì.',
              'Cho thuốc gây nôn tại phòng khám, theo dõi tiếp',
              ('Về nhà cho uống sữa giải độc', 'Đợi xem có sao không rồi tính'))
CHOC_LATE = ('Bé ăn sô-cô-la cách đây 5 tiếng, giờ run rẩy, tim đập nhanh.',
             'Không gây nôn nữa: truyền dịch, theo dõi tim, nằm lại phòng khám',
             ('Cho thuốc gây nôn liền', 'Về nhà cho uống nhiều nước là được'))
CHOC_HOME_GOOD = ('Cất sô-cô-la, kẹo lên cao, đóng tủ', 'Không cho ăn nho, hành, tỏi', 'Kẹo cao su có xylitol cũng độc với chó')
CHOC_HOME_BAD = ('Cho ăn ít sô-cô-la sữa thì không sao', 'Cho uống nước muối để nôn ở nhà')
PARVO_FIRST = ('Cún nôn, đi ngoài ra máu, chưa tiêm phòng, đang nằm ở phòng chờ đông người.',
               'Bế ngay vào phòng cách ly, sát trùng ghế phòng chờ',
               ('Khám tại chỗ ở phòng chờ cho nhanh', 'Cho uống thuốc cầm tiêu chảy rồi về'))
URINE_FIRST = ('Chủ: “Để mai coi sao, chắc nó táo bón thôi.”',
               'Nói rõ mèo đực tắc tiểu là cấp cứu, để quá một ngày có thể chết: xử lý ngay',
               ('Cho về, mai quay lại', 'Bán thuốc nhuận tràng'))
URINE_GOOD = ('Cho ăn hạt tiết niệu theo đơn', 'Thêm pate, nước để bé uống nhiều', 'Khay cát sạch, đặt chỗ yên tĩnh')
URINE_BAD = ('Cho ăn cá khô mặn cho bé thèm', 'Cho nhịn uống để đỡ phải tiểu')
FOREIGN_FIRST = ('Sợi chỉ thòng ra miệng mèo, chủ định kéo ra.',
                 'Không kéo: sợi chỉ có thể cứa ruột. Chụp phim, tính mổ hoặc nội soi',
                 ('Kéo mạnh một phát cho ra', 'Cho uống dầu ăn cho trôi'))
FOREIGN_XRAY = {   # what the film shows → the decision
    'nho': ('Một khối nhỏ, tròn trơn, đã xuống tới ruột già', 'Theo dõi, cho ăn mềm, chụp lại sau 12 giờ'),
    'to': ('Một khối to nằm chắn ở dạ dày, bé nôn liên tục', 'Mổ lấy dị vật hôm nay'),
}
FOREIGN_WRONG = 'Cho uống thuốc xổ thật mạnh'
AFTER_OP_GOOD = ('Đeo loa chống liếm vết mổ', 'Giữ vết mổ khô, không tắm 10 ngày', 'Hẹn tái khám, cắt chỉ')
AFTER_OP_BAD = ('Tắm ngay hôm sau cho sạch', 'Cho chạy nhảy thoải mái ngay tối đó')
FED_ALREADY = ('Chủ: “Sáng nay thấy tội, cho nó ăn một chén cơm rồi.” Giờ mổ còn hai tiếng.',
               'Hoãn mổ sang hôm khác, giải thích nguy cơ sặc khi gây mê',
               ('Mổ luôn, chắc không sao', 'Cho uống thuốc nôn rồi mổ liền'))

# ---------------------------------------------------------------- 🌀 oái oăm at the table (one or two a case)
# (min day, what the owner says, the right answer, the wrong ones, only for these cases / kinds ('dog', 'cat') or None)
DEMANDS = [
    (1, 'Chủ: “Chích thêm kháng sinh cho chắc, bệnh gì cũng phòng luôn.”',
     'Không dùng kháng sinh khi không có chỉ định, giải thích vì sao', ('Chích luôn cho chủ yên tâm', 'Bán thêm vỉ kháng sinh mang về'), None),
    (1, 'Chủ: “Ở nhà có paracetamol, cho mèo uống nửa viên hạ sốt được không?”',
     'Không: paracetamol rất độc với mèo. Chỉ dùng thuốc bác sĩ kê', ('Nửa viên thì được', 'Bẻ một phần tư viên thôi'), ('cat',)),
    (1, 'Chủ: “Ở nhà có thuốc giảm đau của người, cho chó uống một viên được không?”',
     'Không: thuốc của người có thể làm chó ngộ độc. Chỉ dùng thuốc bác sĩ kê', ('Một viên thì được', 'Nửa viên thôi'), ('dog',)),
    (1, 'Chủ: “Bán lọ vắc xin cho tôi về tự tiêm, khỏi tốn công.”',
     'Không bán vắc xin cho chủ tự tiêm: tiêm tại phòng khám, có sổ, có theo dõi', ('Bán, dặn cách tiêm', 'Bán, khỏi dặn'), ('tiem',)),
    (1, 'Chủ: “Khỏi cân, cứ ước chừng mà cho thuốc.”',
     'Vẫn cân bé: liều thuốc tính theo cân nặng', ('Ước chừng bằng mắt', 'Cho liều chó to cho chắc'), None),
    (2, 'Chủ: “Bôi nước tỏi giã lên da trị ve, trên mạng nói vậy.”',
     'Không bôi tỏi: tỏi độc với chó. Dùng thuốc trị ve đúng cân nặng', ('Bôi thử cũng được', 'Cho ăn tỏi luôn cho ve sợ'), ('ve',)),
    (2, 'Chủ: “Cho tôi ôm bé vào phòng chụp X-quang cho nó đỡ sợ.”',
     'Không cho chủ vào phòng chụp; trợ lý mặc áo chì giữ bé', ('Cho vào, đứng sát bé', 'Chụp luôn khi chủ đang ôm'), None),
    (2, 'Chủ: “Tiêm xong về liền, khỏi chờ 30 phút.”',
     'Mời chủ chờ 30 phút để theo dõi phản ứng sau tiêm', ('Cho về ngay', 'Dặn có gì thì quay lại'), ('tiem',)),
    (3, 'Chủ: “Tiêm xong đem đi tắm spa liền nhé.”',
     'Dặn kiêng tắm vài ngày sau tiêm', ('Tắm liền cũng được', 'Tắm nước lạnh cho hạ sốt'), ('tiem',)),
    (3, 'Chủ: “Viết giùm giấy tiêm phòng, bé chưa tiêm nhưng cần giấy gửi khách sạn chó.”',
     'Từ chối: chỉ ghi sổ khi đã thật sự tiêm. Mời tiêm hôm nay', ('Viết giấy cho xong', 'Viết giấy, ghi lùi ngày'), None),
    (4, 'Chủ: “Bớt nửa tiền đi, tháng sau trả.”',
     'Báo giá rõ từng hạng mục; làm phần cấp cứu trước, bàn cách trả', ('Từ chối khám luôn', 'Cắt bớt thuốc cho vừa tiền'), None),
    (5, 'Chủ: “Cắt tai, cắt đuôi cho nó đẹp như chó trên mạng.”',
     'Từ chối cắt tai, cắt đuôi thẩm mỹ', ('Cắt, thêm tiền là được', 'Cắt tai thôi, giữ đuôi'), ('dog',)),
    (6, 'Chủ: “Cho nó ăn sáng no rồi, mổ được mà ha?”',
     'Hỏi kỹ giờ ăn; ăn chưa đủ giờ nhịn thì hoãn mổ', ('Mổ luôn', 'Cho nôn rồi mổ'), ('triet_san', 'di_vat')),
    (6, 'Chủ: “Mèo nhà tôi khỏi đeo loa, nó ghét lắm.”',
     'Giải thích vì sao phải đeo loa, chọn loa mềm cho bé', ('Khỏi đeo, chủ muốn vậy', 'Băng kín vết mổ thay loa'), ('triet_san', 'di_vat')),
]

ADVICE_GOOD = ('Hẹn ngày tái khám, ghi vào sổ', 'Dặn dấu hiệu phải quay lại ngay', 'Đưa đơn thuốc ghi rõ liều')
ADVICE_BAD = ('Dặn chủ lên mạng tìm thêm thuốc', 'Hứa chắc chắn khỏi 100%')

RULES = [
    'Mọi con số dưới đây là sổ tay của phòng khám Cỏ May, luật của trò chơi, không phải lời khuyên chữa bệnh thật.',
    'Nghe chủ kể, khám rồi mới chốt bệnh. Chưa chốt bệnh thì chưa cho thuốc.',
    'Cân bé: người ôm bé đứng lên cân, trừ cân người đứng một mình (hoặc cân cả lồng trừ lồng rỗng). Liều thuốc tính theo cân nặng.',
    'Thân nhiệt chó mèo bình thường 38–39 °C. Cao hơn 39 °C là sốt: hoãn tiêm, khám tìm nguyên nhân.',
    'Tiêm phòng: xem sổ → lấy vắc xin tủ mát, kiểm hạn → lắc đều → sát trùng → tiêm dưới da gáy → dán tem, hẹn mũi nhắc → theo dõi 30 phút. Kiêng tắm vài ngày.',
    'Cắt móng: ôm giữ nhẹ → ấn đệm thịt → soi tủy hồng → cắt cách tủy 2 mm → dũa. Lỡ trúng tủy: bột cầm máu, nói thật.',
    'Gỡ ve: găng tay → nhíp sát da → kéo thẳng từ từ, không xoắn → sát trùng → bỏ ve vào cồn. Thuốc nhỏ gáy chọn theo cân nặng; thuốc của chó không dùng cho mèo.',
    'Sô-cô-la độc với chó. Ăn chưa tới 2 tiếng, chưa có dấu hiệu: gây nôn tại phòng khám, liều 1 ml cho mỗi 5 kg. Quá 2 tiếng hoặc đã run: không gây nôn, truyền dịch, theo dõi.',
    'Cún nôn, đi ngoài ra máu, chưa tiêm phòng: cách ly ngay. Truyền dịch theo sổ: ml mỗi kg mỗi giờ × cân nặng × số giờ.',
    'Mèo đực rặn tiểu không ra là cấp cứu. Nước uống cần mỗi ngày khoảng 50 ml cho mỗi kg.',
    'Nuốt dị vật: không kéo sợi chỉ thòng ra miệng, không cho uống dầu. Chụp phim: khối nhỏ đã xuống ruột thì theo dõi; khối to chắn dạ dày thì mổ.',
    'Trước mổ nhịn ăn 8 tiếng. Sau mổ: đeo loa, giữ vết mổ khô 10 ngày, hẹn cắt chỉ.',
    'Không dùng kháng sinh khi không có chỉ định, không bán vắc xin cho chủ tự tiêm, không viết giấy tiêm khống, không cắt tai, đuôi thẩm mỹ.',
    'Trả bé: so phiếu số chuồng, tên bé và vòng cổ với phiếu chủ cầm.',
]

# ---------------------------------------------------------------- 🔔 clinic surprises (kit.desk)
DESK = [
    dict(id='snake', title='Khách ôm con rắn cảnh tới khám', emoji='🐍', npc=1, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Một thanh niên mở hộp: con trăn cảnh nằm lờ đờ, đòi khám liền. Phòng khám chỉ có thuốc, đồ nghề cho chó mèo.',
         options=[dict(id='refer', label='Nói thật phòng khám không chuyên bò sát, gọi giới thiệu bác sĩ thú y bò sát', hint='', effects=dict(xp=5), good=True,
                       outcome='Thanh niên cảm ơn, chạy qua phòng khám bò sát bên quận kia.'),
                  dict(id='guess', label='Khám đại, kê thuốc như cho mèo', hint='', effects=dict(review=[1, 'Phòng khám không biết mà vẫn kê thuốc bừa.', 0]), good=False,
                       outcome='Con trăn yếu thêm. Chủ của nó quay lại làm ầm.')],
         default='refer'),
    dict(id='dog_fight', title='Hai con chó cắn nhau ở phòng chờ', emoji='🐕', npc=5, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Chó của chú Tư không rọ mõm, xông vào con Phốc sóc đang ngồi trong lòng chủ. Cả phòng chờ hét lên.',
         options=[dict(id='split', label='Không thò tay can giữa hai mõm: chị Duyên chèn tấm ván, kéo dây xích tách ra, rồi khám vết cắn', hint='',
                       effects=dict(xp=6, review=[4, 'Phòng khám xử lý nhanh, bình tĩnh.', 5]), good=True,
                       outcome='Hai con tách ra. Con Phốc sóc chỉ trầy nhẹ ở tai.'),
                  dict(id='hands', label='Thò tay vào kéo hai con ra', hint='', effects=dict(patience=-3, money=-5, money_loss='normal'), good=False,
                       outcome='Bạn bị cắn trúng tay, phải đi tiêm phòng dại.'),
                  dict(id='rule', label='Từ giờ dán bảng: chó phải đeo rọ mõm, xích ngắn ở phòng chờ', hint='', effects=dict(xp=4), good=True,
                       outcome='Chú Tư càu nhàu nhưng lần sau mang rọ mõm theo.')],
         default='split'),
    dict(id='stray_hit', title='Mèo hoang bị xe tông, không ai là chủ', emoji='🚑', npc=6, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Bé Na và mấy đứa bạn ôm vào một con mèo hoang bị xe tông, chân sau lủng lẳng. Không ai trả tiền.',
         options=[dict(id='treat', label='Sơ cứu, giảm đau, nẹp chân; ghi sổ ca từ thiện của phòng khám', hint='', effects=dict(xp=7, money=-6, mark='stray_saved'), good=True,
                       outcome='Con mèo nằm nghỉ trong chuồng. Lũ nhỏ góp tiền mua hộp pate.'),
                  dict(id='refuse', label='Không có chủ thì không nhận', hint='', effects=dict(review=[1, 'Con mèo bị tông mà phòng khám đuổi lũ nhỏ về.', 6]), good=False,
                       outcome='Lũ nhỏ ôm con mèo khóc ngoài cửa.')],
         default='treat'),
    dict(id='stray_home', title='Con mèo hoang được nhận nuôi', emoji='🏡', npc=7, min_day=4, tone='gentle', at='between', weight=5, mods=None,
         need_mark='stray_saved',
         text='Ông Sáu ghé hỏi con mèo hoang hôm trước: “Nó lành chân chưa? Cho tôi đem về nuôi với con Mun.”',
         options=[dict(id='adopt', label='Khám lại, tiêm phòng, dặn ông cách cho ăn rồi giao bé', hint='',
                       effects=dict(xp=5, unmark='stray_saved', review=[5, 'Phòng khám cứu con mèo hoang, giờ nó có nhà.', 7]), good=True,
                       outcome='Ông Sáu ôm con mèo về, đặt tên là Tông.'),
                  dict(id='later', label='Bận quá, hẹn ông tuần sau', hint='', effects=dict(unmark='stray_saved'), good=None,
                       outcome='Ông Sáu về một mình, tuần sau quay lại.')],
         default='adopt'),
    dict(id='neighbour_drug', title='Nhờ chích thuốc chó hàng xóm cho “im”', emoji='🤫', npc=5, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Chú Tư thì thầm: “Chó nhà bên sủa cả đêm. Bán tôi ít thuốc ngủ, tối tôi ném qua cho nó im.”',
         options=[dict(id='refuse', label='Từ chối thẳng, gợi ý nói chuyện với hàng xóm, nhờ tổ dân phố hòa giải', hint='', effects=dict(xp=6), good=True,
                       outcome='Chú Tư lầm bầm. Tuần sau hai nhà ngồi uống trà với tổ trưởng.'),
                  dict(id='sell', label='Bán, tiền nào của nấy', hint='', effects=dict(money=8, review=[1, 'Phòng khám bán thuốc cho người đầu độc chó nhà tôi.', 5]), good=False,
                       outcome='Con chó nhà bên phải cấp cứu. Cả hẻm biết thuốc từ đâu.')],
         default='refuse'),
    dict(id='rooster', title='Gà đá bị thương, chủ đòi chích “thuốc tăng lực”', emoji='🐓', npc=5, min_day=4, tone='tense', at='between', weight=2, mods=None,
         text='Một người ôm con gà đá rách mồng: “Chích gì cho nó hăng, chiều nay đá tiếp.”',
         options=[dict(id='wound', label='Rửa, khâu vết thương, nói rõ không chích thuốc kích thích cho gà đá', hint='', effects=dict(xp=5), good=True,
                       outcome='Người đó trả tiền khâu, bỏ đi không vui.'),
                  dict(id='dope', label='Chích thuốc kích thích, lấy tiền gấp đôi', hint='', effects=dict(money=8, review=[1, 'Phòng khám chích thuốc cho gà đá độ.', 0]), good=False,
                       outcome='Con gà gục ngay trận chiều. Chủ quay lại đòi tiền.')],
         default='wound'),
    dict(id='euthanasia', title='Ông Sáu hỏi chuyện cho bé Mun đi', emoji='🕯️', npc=7, min_day=6, tone='gentle', at='between', weight=2, mods=None,
         text='Bé Mun mười bốn tuổi, suy thận nặng, bỏ ăn một tuần. Ông Sáu ngồi lặng: “Bác sĩ nói thật đi, nó còn đau nhiều không?”',
         options=[dict(id='honest', label='Ngồi xuống nói thật bệnh tình, các lựa chọn, để ông quyết, không giục', hint='',
                       effects=dict(xp=7, review=[5, 'Bác sĩ ngồi với tôi cả tiếng, nói thật mà nhẹ nhàng.', 7]), good=True,
                       outcome='Ông Sáu ôm bé Mun thêm một buổi chiều ở phòng khám rồi mới quyết.'),
                  dict(id='rush', label='Nói nhanh cho xong, phòng chờ đông', hint='', effects=dict(review=[2, 'Bác sĩ vội quá, tôi chưa kịp hỏi gì.', 7]), good=False,
                       outcome='Ông Sáu ôm bé về, không nói lời nào.')],
         default='honest'),
    dict(id='under_cabinet', title='Mèo trốn dưới gầm tủ', emoji='🙀', npc=3, min_day=1, tone='gentle', at='open', weight=3, mods=None,
         text='Anh Hùng mở lồng, bé Mướp phóng vọt xuống chui tít dưới gầm tủ thuốc, gầm gừ.',
         options=[dict(id='calm', label='Tắt bớt đèn, để khăn có mùi bé, ngồi đợi; chị Duyên dùng khăn trùm bé nhẹ nhàng', hint='',
                       effects=dict(xp=4, review=[5, 'Mèo nhà tôi dữ vậy mà phòng khám dỗ được.', 3]), good=True,
                       outcome='Mười phút sau Mướp tự ló đầu ra, bị trùm khăn gọn gàng.'),
                  dict(id='broom', label='Lấy cây chổi chọc cho nó ra', hint='', effects=dict(patience=-2, review=[2, 'Lấy chổi chọc mèo của tôi.', 3]), good=False,
                       outcome='Mướp hoảng, cào rách tay chị Duyên.')],
         default='calm'),
    dict(id='long_wait', title='Chủ chê chờ lâu, dọa đánh giá 1 sao', emoji='⏳', npc=6, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Chị Vy giơ điện thoại: “Chờ bốn mươi phút rồi! Không làm liền tôi đánh giá một sao.” Bên trong đang cấp cứu ca tắc tiểu.',
         options=[dict(id='explain', label='Xin lỗi, nói thật đang có ca cấp cứu, báo giờ chờ, mời nước', hint='',
                       effects=dict(xp=4, review=[4, 'Chờ hơi lâu nhưng được nói rõ là có ca cấp cứu.', 6]), good=True,
                       outcome='Chị Vy ngồi xuống, lướt điện thoại, không đánh giá gì.'),
                  dict(id='skip', label='Cho chị Vy chen lên trước ca cấp cứu', hint='', effects=dict(review=[1, 'Mèo tôi đang cấp cứu mà phòng khám cho người khác chen ngang.', 3]), good=False,
                       outcome='Ca cấp cứu bị dừng giữa chừng.')],
         default='explain'),
    dict(id='fake_book', title='Nhờ ký sổ tiêm khống cho chó hàng xóm', emoji='📒', npc=6, min_day=3, tone='tense', at='between', weight=2, mods=None,
         no_mark='book_faked',
         text='Chị Vy: “Ký giùm cuốn sổ tiêm phòng dại cho chó nhà bạn em, nó đi du lịch mang chó theo, cần gấp.”',
         options=[dict(id='refuse', label='Từ chối: chỉ ký khi chính tay tiêm', hint='', effects=dict(xp=6), good=True,
                       outcome='Chị Vy hẹn bạn mang chó tới tiêm chiều nay.'),
                  dict(id='sign', label='Ký luôn, có gì đâu', hint='', effects=dict(money=5, mark='book_faked'), good=False,
                       outcome='Cuốn sổ mang chữ ký của phòng khám đi theo con chó chưa tiêm.')],
         default='refuse'),
    dict(id='fake_book_check', title='Cán bộ thú y phường kiểm sổ tiêm', emoji='🧾', npc=0, min_day=5, tone='tense', at='between', weight=5, mods=None,
         need_mark='book_faked',
         text='Con chó mang sổ tiêm phòng khám ký cắn người ở khu du lịch. Cán bộ thú y phường tới đối chiếu sổ lô vắc xin.',
         options=[dict(id='admit', label='Nhận đã ký khống, nộp phạt, hợp tác truy con chó', hint='',
                       effects=dict(unmark='book_faked', money=-25, money_loss='fine', review=[2, 'Phòng khám từng ký sổ tiêm khống, có nhận lỗi.', 0]), good=None,
                       outcome='Biên bản lập, tiền phạt nộp. Bác sĩ Thảo im lặng cả buổi.'),
                  dict(id='deny', label='Chối, nói sổ giả mạo chữ ký', hint='',
                       effects=dict(unmark='book_faked', money=-40, money_loss='fine', review=[1, 'Phòng khám ký sổ tiêm khống còn chối.', 0]), good=False,
                       outcome='Sổ lô vắc xin không khớp. Phạt nặng hơn.')],
         default='admit'),
    dict(id='hamster', title='Bé Na khóc vì hamster', emoji='🐹', npc=4, min_day=1, tone='gentle', at='between', weight=3, mods=None,
         text='Bé Na mang lồng hamster tới, mắt đỏ hoe: “Nó không chạy bánh xe nữa, con chỉ có hai chục nghìn.”',
         options=[dict(id='look', label='Khám nhẹ nhàng, chỉ cách lót chuồng, cho ăn; lấy tiền tượng trưng', hint='', effects=dict(xp=5, review=[5, 'Bác sĩ khám hamster cho con tôi, còn dạy nó cách nuôi.', 4]), good=True,
                       outcome='Hamster chỉ bị lạnh. Bé Na về lót thêm giấy, hôm sau nó chạy bánh xe lại.'),
                  dict(id='no', label='Phòng khám không khám chuột', hint='', effects=dict(review=[2, 'Con tôi khóc về vì bị từ chối.', 4]), good=None,
                       outcome='Bé Na ôm lồng về.')],
         default='look'),
    dict(id='online_vaccine', title='Chủ mang lọ vắc xin mua online tới nhờ tiêm', emoji='📦', npc=2, min_day=4, tone='tense', at='between', weight=2, mods=None,
         text='Cô Ba Mập đặt lên bàn lọ vắc xin mua online, giao bằng túi nilon, đá đã tan hết: “Tiêm giùm, cô trả tiền công.”',
         options=[dict(id='refuse', label='Không tiêm lọ không rõ bảo quản; giải thích vắc xin mất lạnh là hỏng, tiêm lọ của phòng khám', hint='',
                       effects=dict(xp=6, review=[4, 'Bác sĩ giải thích kỹ vụ vắc xin, cô hiểu rồi.', 2]), good=True,
                       outcome='Cô Ba tiếc tiền nhưng gật đầu tiêm lọ của phòng khám.'),
                  dict(id='inject', label='Tiêm luôn cho cô vui', hint='', effects=dict(money=2, review=[2, 'Tiêm xong chó vẫn bệnh, hóa ra lọ thuốc hỏng.', 2]), good=False,
                       outcome='Hai tháng sau bé Lu vẫn bệnh như chưa tiêm.')],
         default='refuse'),
    dict(id='fridge_out', title='Cúp điện, tủ vắc xin mất lạnh', emoji='🔌', npc=1, min_day=5, tone='tense', at='open', weight=2, mods=None,
         text='Sáng mở cửa, đêm qua cúp điện bốn tiếng. Nhiệt kế tủ vắc xin chỉ 14 °C, còn nguyên một khay vắc xin.',
         options=[dict(id='discard', label='Ghi sổ sự cố, loại bỏ khay vắc xin mất lạnh, gọi nhà cung cấp; gắn ổ điện có lưu điện', hint='',
                       effects=dict(xp=7, money=-10, money_loss='normal'), good=True,
                       outcome='Mất tiền một khay, nhưng không ai bị tiêm vắc xin hỏng.'),
                  dict(id='use', label='Vẫn dùng, chắc không sao', hint='', effects=dict(review=[1, 'Tiêm ở Cỏ May mà chó vẫn mắc bệnh.', 2]), good=False,
                       outcome='Một tháng sau mấy bé tiêm hôm đó lần lượt quay lại vì bệnh.')],
         default='discard'),
]
