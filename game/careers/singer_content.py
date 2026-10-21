"""🎤 Phòng trà Mây Chiều: the words and tables of the singer's evenings (game/careers/singer.py).

Every table is static: a set is a pure function of (day, slot), so validate_state can rebuild it. The owner's rule
("nghề nào cũng phải có nhiều yêu cầu oái oăm"): each set carries one or two awkward demands from the room (DEMANDS) and
the tea room has its own surprises between sets (DESK, kit.desk), some of which leave a mark that brings a later event
(a guest singer who mimed to a recording is caught by a regular who knows voices). Every song title is invented, the
songbook is the tea room's own (bài đã xin phép biểu diễn); no real artist or song is named.
"""
from __future__ import annotations

PLACE = 'Phòng trà Mây Chiều'
MENTOR_NAME = 'Cô Diệu Hiền'

PEOPLE = [
    ('Cô Diệu Hiền', 'Chủ phòng trà, ca sĩ một thời', 'Hát ba mươi năm. Dặn ai cũng một câu: “Hát cho người ngồi trước mặt mình, không hát cho cái micro.”', 'warm'),
    ('Anh Tâm', 'Kỹ thuật âm thanh', 'Ít nói, tai thính, ghét nhất tiếng micro hú.', 'quiet'),
    ('Chú Bảy', 'Trưởng ban nhạc, đàn piano', 'Thuộc cả ngàn bài, chỉ cần một cái gật đầu là đổi tông.', 'warm'),
    ('Ông bà Tư', 'Khách quen, cưới nhau bốn mươi năm', 'Tối thứ bảy nào cũng ngồi bàn số 3, gọi một bình trà.', 'warm'),
    ('Anh Khoa', 'Doanh nhân, khách sộp', 'Hay mời rượu, hay đòi “hát cho bàn anh thôi”.', 'entitled'),
    ('Chị Ngọc', 'Khách sành nhạc', 'Nghe là biết ai hát thật, ai hát nhép.', 'picky'),
    ('Bé Linh', 'Sinh viên năm nhất trường nhạc', 'Ngồi góc cuối ghi chép cách ca sĩ lấy hơi.', 'genz'),
    ('Chú Năm', 'Khách vui tính', 'Uống hai ly là đòi lên hát chung.', 'bossy'),
    ('Cô Mỹ', 'Người hâm mộ', 'Tối nào cũng mang một bó hồng, ngồi bàn đầu.', 'warm'),
]
MENTOR = 0
SOUND = 1
BAND = 2
GUESTS = (3, 4, 5, 6, 7, 8)

WRONG_COST = 8
QUALITY_FLOOR = 40
MILESTONES = (4, 10, 20, 40)   # days: a request from the floor, a second demand, an incident on stage, the harder sets
MASTER = (90, 30)       # Giọng hát vững vàng: good sets, active days
EXPERT = (170, 45)      # Giọng ca của Mây Chiều

# The sets: the kind of song the room wants (name, emoji, min day, bonus in xu before quality), who asks and what they
# say, what you see from the stage, and two songs of that kind in the tea room's songbook (invented titles).
SETS = {
    'bolero': dict(name='Bolero sâu lắng', emoji='🌙', day=1, bonus=5, guest=3,
                   say=('Con hát giùm bài gì buồn buồn mà thấm, như hồi tụi ông mới quen.', 'Tối nay kỷ niệm ngày cưới, con hát một bài chậm thôi nghe.'),
                   see=('Khán phòng toàn khách lớn tuổi, đèn vàng, ai cũng gọi trà.', 'Bàn số 3 hai ông bà nắm tay, chờ một bài chậm rãi.'),
                   songs=('Chiều Quê Mưa Bay', 'Thư Gửi Người Xa')),
    'nhac_xua': dict(name='Nhạc xưa hoài niệm', emoji='📻', day=1, bonus=5, guest=5,
                     say=('Hát bài gì của mấy năm xưa, nghe là nhớ phố cũ ấy.', 'Tôi muốn nghe lại thứ nhạc mẹ tôi hay mở radio.'),
                     see=('Khách trung niên ngồi kín, nhiều người mang theo máy ảnh phim.', 'Chị Ngọc ngồi một mình, gọi ly cà phê đen, mắt nhìn ra cửa sổ.'),
                     songs=('Phố Cũ Lá Vàng', 'Hàng Me Năm Ấy')),
    'tinh_ca': dict(name='Tình ca ngọt ngào', emoji='💞', day=2, bonus=6, guest=4,
                    say=('Tối nay anh cầu hôn, em hát bài nào ngọt ngọt để anh quỳ xuống nha.', 'Hát một bài tình ca, bạn gái anh thích nhẹ nhàng.'),
                    see=('Bàn số 5 có hộp nhẫn giấu dưới khăn, cô gái chưa biết gì.', 'Một cặp đôi trẻ ngồi sát nhau, ánh nến lung linh.'),
                    songs=('Ngày Mình Chung Đôi', 'Gọi Tên Em Dịu Dàng')),
    'acoustic': dict(name='Acoustic trẻ trung', emoji='🎸', day=2, bonus=5, guest=6,
                     say=('Chị ơi tụi em là sinh viên, chị hát bài gì trẻ trẻ với guitar thôi.', 'Hát gì nhẹ nhàng mà vui vui, tụi em mới thi xong.'),
                     see=('Một nhóm sinh viên chiếm hai bàn, gọi trà đào, ai cũng cầm điện thoại.', 'Khán phòng trẻ, có người gõ nhịp lên bàn.'),
                     songs=('Cà Phê Mưa Tháng Sáu', 'Đạp Xe Qua Cầu Gió')),
    'que_huong': dict(name='Dân ca quê hương', emoji='🌾', day=3, bonus=6, guest=5,
                      say=('Bà con xa xứ mới về, hát giùm một bài quê nhà nghe.', 'Đoàn khách về thăm quê, ai cũng muốn nghe điệu dân ca.'),
                      see=('Một đoàn khách đi xa nhiều năm mới về, có cụ ông rưng rưng.', 'Khách đặt cả dãy bàn, trên bàn có gói bánh tráng quê.'),
                      songs=('Dòng Sông Quê Ngoại', 'Lúa Thơm Đầu Đình')),
    'sinh_nhat': dict(name='Bài mừng sinh nhật', emoji='🎂', day=4, bonus=6, guest=8,
                      say=('Hôm nay sinh nhật con gái cô, con hát mừng giùm cô nha.', 'Bàn đầu có người sinh nhật, hát gì cho cả phòng vỗ tay.'),
                      see=('Bàn đầu có bánh kem cắm nến số 20.', 'Một cô gái đội vương miện giấy, cả bàn cầm bóng bay.'),
                      songs=('Tuổi Mới Bình Yên', 'Nến Hồng Thắp Sáng')),
    'cha_cha': dict(name='Cha-cha-cha vui tươi', emoji='💃', day=5, bonus=6, guest=7,
                    say=('Tất niên công ty, hát gì cho anh em ra nhảy với!', 'Cuối năm rồi, hát bài vui cho mọi người đứng dậy.'),
                    see=('Hai dãy bàn tiệc tất niên, có người đã kéo ghế ra giữa sàn.', 'Khách mặc đồ đẹp, nhạc mở đầu là ai cũng nhún nhảy.'),
                    songs=('Xuân Về Trên Phố', 'Bước Chân Vui Tết')),
    'jazz': dict(name='Jazz đêm khuya', emoji='🎷', day=6, bonus=7, guest=4,
                 say=('Khuya rồi, hát gì chậm, sang một chút cho khách nước ngoài của anh.', 'Bàn anh tiếp đối tác, hát gì êm êm, có kèn.'),
                 see=('Gần nửa đêm, khách thưa, có hai vị khách nước ngoài ngồi quầy bar.', 'Đèn tối dần, chú Bảy chuyển sang hợp âm jazz.'),
                 songs=('Đêm Mây Không Ngủ', 'Ly Cà Phê Muộn')),
}
SET_ORDER = tuple(SETS)
# who a song slip is for: the dedication must go to the right table and name
DEDICATEES = ('chị Lan', 'anh Hùng', 'cô Thu', 'bác Tám', 'em Vy', 'anh Minh', 'chị Hạnh', 'chú Lộc')
SONG_TRAP = 'Bản hit đang hot của một ca sĩ nổi tiếng (phòng trà chưa xin phép biểu diễn)'

# ---------------------------------------------------------------- the set's own steps (singer.py builds them)
STEPS = {
    'khoi_dong': [('nuoc', 'Uống ngụm nước ấm'), ('vai', 'Khởi động cổ, vai cho mềm'), ('tho', 'Thở bụng chậm bốn nhịp'),
                  ('ngan', 'Ngân khẽ “ư” cho ấm giọng'), ('luyen', 'Luyến lên xuống theo thang âm'), ('thu', 'Hát thử câu cao nhất của bài')],
}
# Sound check with anh Tâm: (what happens, the right fix, the wrong ones)
SOUND_CHECK = [
    ('Bước tới mép sân khấu, micro hú rít một tiếng chói tai.',
     'Lùi ra sau loa kiểm âm, ra hiệu anh Tâm giảm độ lớn micro', ('Đưa micro sát loa cho hết hú', 'Hét to lấn tiếng hú')),
    ('Tiếng đàn to át cả giọng, bạn không nghe mình hát.',
     'Nhờ anh Tâm tăng giọng trong loa kiểm âm, ra hiệu chú Bảy đàn nhỏ lại', ('Gào to hơn tiếng đàn', 'Bịt một tai mà hát')),
    ('Hát thử câu cao, micro rè rè như vỡ tiếng.',
     'Đưa micro ra xa miệng hơn ở câu cao, nhờ anh Tâm giảm độ nhạy', ('Áp sát micro vào môi', 'Bỏ luôn câu cao')),
    ('Pin micro không dây báo còn một vạch.',
     'Nhờ anh Tâm thay pin trước khi lên, để sẵn micro dây dự phòng', ('Kệ, chắc đủ một bài', 'Hát không micro cho chắc')),
    ('Tiếng giày dép, ly tách vang vào micro mỗi khi bạn quay đi.',
     'Giữ micro hướng về miệng, cầm vững, quay người cả micro theo', ('Để micro trên giá, đi lại tự do', 'Xin khách đừng uống trà nữa')),
]
SET_MINUTES = (20, 25, 30)      # a singer's turn on stage
# A request from the floor: (what comes, the right answer, the wrong ones)
REQUESTS = [
    ('Bàn 6 gửi giấy xin một bài band chưa có hợp âm, đòi hát ngay.',
     'Hỏi chú Bảy; band không thuộc thì mời khách một bài khác cùng không khí, hẹn lần sau', ('Hát đại theo trí nhớ, sai lời cũng kệ', 'Lờ tờ giấy đi')),
    ('Một tờ giấy xin bài tặng “người yêu cũ đang ngồi bàn bên, cho nó biết mặt”.',
     'Từ chối khéo: không hát để làm khó khách khác, mời bài tặng chính người xin', ('Hát rồi đọc to lời nhắn', 'Chỉ tay về bàn bên cho vui')),
    ('Cô Mỹ xin bài tặng mẹ đang nằm viện, nhờ đọc lời chúc.',
     'Đọc lời chúc đúng tên, nói ngắn, hát trọn bài', ('Đọc lời chúc thật dài cho cảm động', 'Hát luôn, khỏi đọc')),
    ('Hai bàn cùng xin hai bài khác nhau cho bài kế tiếp.',
     'Hát theo thứ tự tờ giấy tới trước, báo bàn kia bài sau', ('Hát bài của bàn boa nhiều hơn', 'Bỏ cả hai cho công bằng')),
    ('Một khách xin hát bằng tiếng Anh bài bạn chưa thuộc lời.',
     'Nói thật chưa thuộc, mời một bài tiếng Anh bạn hát chắc', ('Hát ậm ừ cho có', 'Đọc lời trên điện thoại giữa sân khấu')),
]
# On stage something goes wrong: (what happens, the right move, the wrong ones)
INCIDENTS = [
    ('Micro tắt ngúm giữa điệp khúc.',
     'Ra hiệu anh Tâm đưa micro dự phòng; trong lúc chờ hát mộc với chú Bảy đàn nhỏ lại', ('Dừng hát, đứng chờ', 'Lắc micro, gõ vào tay')),
    ('Bạn quên lời câu đầu đoạn hai.',
     'Ngân giai điệu một câu, nhìn chú Bảy, vào lại lời ở câu sau', ('Dừng hẳn, xin hát lại từ đầu', 'Bịa đại lời khác')),
    ('Đang hát thì cúp điện, cả phòng tối om.',
     'Bình tĩnh hát mộc, nhờ phục vụ thắp nến, chú Bảy chuyển sang guitar', ('Bỏ xuống sân khấu chờ có điện', 'Bảo khách bật đèn điện thoại chiếu lên mình')),
    ('Dây đàn guitar của chú Bảy đứt giữa bài.',
     'Hát chậm lại theo piano, đợi chú Bảy đổi đàn', ('Hát nhanh cho xong bài', 'Quay sang trách ban nhạc')),
    ('Một vị khách say bước lên sân khấu giành micro.',
     'Mỉm cười mời khách hát theo điệp khúc từ bàn, ra hiệu bảo vệ đỡ khách xuống', ('Giằng co micro với khách', 'Bỏ đi vào hậu trường')),
]
# The end of the turn: (what happens, the right answer, the wrong ones)
ENCORE = [
    ('Khán giả hô “Thêm một bài!”, lượt của bạn còn ba phút, ca sĩ sau đã đứng chờ.',
     'Cảm ơn, hát lại một đoạn điệp khúc ngắn rồi mời ca sĩ sau', ('Hát nguyên bài sáu phút', 'Đi thẳng vào trong, không chào')),
    ('Khán giả hô “Thêm một bài!”, lượt của bạn còn tám phút.',
     'Hát thêm một bài ngắn năm phút, cảm ơn rồi chào', ('Hát liền hai bài dài', 'Từ chối vì mệt')),
    ('Anh Khoa đứng dậy: “Hát thêm ba bài cho bàn anh, anh trả gấp đôi!” Ca sĩ sau đang chờ.',
     'Cảm ơn anh, hẹn lượt sau; hỏi cô Diệu Hiền nếu muốn thêm giờ', ('Hát thêm ba bài, kệ ca sĩ sau', 'Nhận tiền rồi hát một bài cho xong')),
    ('Hết lượt, cô Mỹ lên tặng hoa, cả phòng vỗ tay.',
     'Nhận hoa, cảm ơn cô và khán giả, cúi chào rồi xuống', ('Đứng lại kể chuyện mười phút', 'Đưa hoa cho phục vụ rồi đi luôn')),
]

# ---------------------------------------------------------------- 🌀 oái oăm from the room (one or two a set)
# (min day, what someone says, the right answer, the wrong ones, only for these sets or None)
DEMANDS = [
    (1, 'Cô Diệu Hiền: “Hôm nay em khàn thì hát nhép theo bản thu cho khỏe.”',
     'Hát thật; khàn thì nhờ chú Bảy hạ tông, chọn bài vừa giọng', ('Hát nhép cho đỡ mệt', 'Hát nhép đoạn cao thôi'), None),
    (1, 'Chú Năm: “Đưa micro đây, anh lên hát chung một bài!”',
     'Mời chú hát theo điệp khúc từ bàn, micro vẫn ở sân khấu', ('Đưa micro cho chú hát cả bài', 'Giả vờ không nghe'), None),
    (1, 'Anh Khoa: “Uống với anh ly rượu rồi hát tiếp.”',
     'Cảm ơn anh, xin uống nước ấm để giữ giọng', ('Uống cạn cho khách vui', 'Uống nửa ly thôi'), None),
    (1, 'Một khách giơ điện thoại: “Quay nguyên bài đăng kênh của anh, có tiền quảng cáo đó.”',
     'Mời khách quay đoạn ngắn làm kỷ niệm; đăng kiếm tiền thì phải xin phép phòng trà', ('Cứ quay, càng nổi càng tốt', 'Giật điện thoại của khách'), None),
    (2, 'Anh Khoa nhét tờ tiền: “Hát năm bài liền cho bàn anh, kệ mấy bàn kia.”',
     'Cảm ơn, nhận một bài theo yêu cầu, giữ thứ tự cho cả phòng', ('Hát năm bài cho bàn anh', 'Nhận tiền mà không hát'), None),
    (2, 'Một khách: “Hát giọng y chang ca sĩ nổi tiếng, rồi xưng là cô ấy luôn cho vui.”',
     'Hát bằng giọng của mình, không mạo danh ca sĩ khác', ('Nhại giọng, xưng tên ca sĩ', 'Nhại giọng mà không xưng tên'), None),
    (2, 'Ca sĩ khác: “Đổi lượt cho chị lên trước nha, chị có hẹn.”',
     'Hỏi cô Diệu Hiền; cô đồng ý thì đổi, báo ban nhạc', ('Tự đổi, khỏi hỏi ai', 'Từ chối thẳng, không nói lý do'), None),
    (3, 'Cô Mỹ: “Cho cô ôm chụp hình ngay trên sân khấu giữa bài nha.”',
     'Hẹn cô chụp hình sau lượt hát', ('Dừng bài cho cô chụp', 'Kéo cô lên sân khấu hát chung'), None),
    (3, 'Một khách: “Đổi lời bài hát thành chửi người yêu cũ của tôi đi.”',
     'Từ chối khéo, hát đúng lời gốc', ('Đổi lời cho khách vui', 'Đổi lời nhẹ nhẹ thôi'), None),
    (4, 'Cô Diệu Hiền: “Phòng đông, em hát thêm ba bài, tối nay chưa tính tiền nha.”',
     'Nói rõ giờ hát trong hợp đồng; hát thêm thì thỏa thuận thêm', ('Hát thêm, tính sau', 'Bỏ về giữa chừng'), None),
    (4, 'Anh chàng cầu hôn: “Khi anh quỳ, em hô to tên cô ấy cho cả phòng biết nha.” Anh chưa hỏi cô gái có muốn công khai không.',
     'Hỏi lại anh, gợi ý để cô gái tự quyết; hát nhẹ, không làm cô bị ép giữa đông người', ('Hô thật to tên cô gái', 'Mời cả phòng hô “đồng ý đi”'), ('tinh_ca',)),
    (5, 'Trưởng đoàn tất niên: “Hát bài này nhưng đổi lời quảng cáo công ty anh vào.”',
     'Hát lời gốc; lời chúc của công ty thì đọc riêng trước bài', ('Đổi lời theo ý anh', 'Đổi lời mà không hỏi phòng trà'), ('cha_cha',)),
]

RULES = [
    'Mọi bài hát, con số và quy định dưới đây là sổ tay của Phòng trà Mây Chiều trong trò chơi; tên bài đều là bài trong sổ hợp âm của phòng trà.',
    'Nhìn khán phòng trước khi chọn bài: ai ngồi, dịp gì, không khí ra sao.',
    'Khởi động: nước ấm → cổ, vai → thở bụng → ngân khẽ → luyến theo thang âm → hát thử câu cao nhất.',
    'Chỉ hát bài trong sổ hợp âm của phòng trà (đã xin phép biểu diễn). Bài hit chưa xin phép thì không hát.',
    'Hát thật, không hát nhép, không nhại giọng xưng tên ca sĩ khác. Khàn thì nhờ ban nhạc hạ tông, chọn bài vừa giọng.',
    'Thử âm với anh Tâm: micro hú thì lùi ra sau loa kiểm âm; đàn át giọng thì nhờ tăng loa kiểm âm, ban nhạc đàn nhỏ lại; câu cao thì đưa micro xa hơn.',
    'Mỗi lượt có số phút cố định: thời gian còn lại = lượt − các bài đã hát − thời gian chào, giới thiệu.',
    'Giấy xin bài: hát theo thứ tự tới trước, đọc lời chúc đúng tên, không hát để làm khó khách khác.',
    'Sự cố trên sân khấu: micro tắt thì xin micro dự phòng và hát mộc; quên lời thì ngân giai điệu, vào lại câu sau; cúp điện thì bình tĩnh hát mộc.',
    'Hết lượt: còn ít phút thì chỉ hát lại điệp khúc rồi mời ca sĩ sau; khách đòi thêm giờ thì hỏi chủ phòng trà.',
    'Khách mời rượu thì xin nước ấm; khách giành micro thì mời hát theo từ bàn; quay phim đăng kiếm tiền phải xin phép.',
    'Đọc lời chúc đúng bàn, đúng tên trên giấy xin bài.',
]

# ---------------------------------------------------------------- 🔔 tea-room surprises (kit.desk)
DESK = [
    dict(id='guest_mime', title='Ca sĩ khách mời xin hát nhép', emoji='🎧', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=None,
         no_mark='mimed',
         text='Ca sĩ khách mời đêm nay bị khàn, xin anh Tâm chạy bản thu để hát nhép. Cô Diệu Hiền đi vắng, nhờ bạn quyết.',
         options=[dict(id='honest', label='Gợi ý đổi sang bài nhẹ, hát mộc với piano, báo khán giả ca sĩ hơi mệt', hint='', effects=dict(xp=6), good=True,
                       outcome='Khán giả vỗ tay rất lâu cho bài hát mộc khàn khàn.'),
                  dict(id='mime', label='Cho chạy bản thu, chắc không ai biết', hint='', effects=dict(mark='mimed'), good=False,
                       outcome='Bài hát trơn tru như đĩa. Chị Ngọc nhíu mày ở bàn cuối.')],
         default='honest'),
    dict(id='mime_caught', title='Chuyện hát nhép bị phát hiện', emoji='📣', npc=5, min_day=4, tone='tense', at='between', weight=5, mods=None,
         need_mark='mimed',
         text='Chị Ngọc đăng bài: “Phòng trà Mây Chiều cho ca sĩ hát nhép, khách trả tiền nghe đĩa.” Bài viết đang lan khắp phố.',
         options=[dict(id='apologize', label='Nhận thật, xin lỗi khán giả, mời chị Ngọc đêm sau nghe hát mộc', hint='',
                       effects=dict(unmark='mimed', review=[3, 'Phòng trà có sai nhưng đã xin lỗi đàng hoàng.', 5]), good=None,
                       outcome='Chị Ngọc tới, nghe hết lượt của bạn, gật đầu một cái.'),
                  dict(id='deny', label='Chối, nói chị Ngọc nghe nhầm', hint='',
                       effects=dict(unmark='mimed', money=-8, money_loss='normal', review=[1, 'Hát nhép còn chối.', 5]), good=False,
                       outcome='Có người tung đoạn ghi âm. Mấy bàn quen hủy đặt chỗ.')],
         default='apologize'),
    dict(id='table_fight', title='Hai bàn cãi nhau giữa bài', emoji='😤', npc=4, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Bàn anh Khoa và bàn bên cạnh cãi nhau vì giành bài, có người đứng bật dậy.',
         options=[dict(id='calm', label='Hát chậm lại, ra hiệu bảo vệ, mời cô Diệu Hiền ra nói chuyện', hint='', effects=dict(xp=5, review=[4, 'Ca sĩ giữ được không khí, không ai to tiếng nữa.', 5]), good=True,
                       outcome='Hai bàn ngồi xuống. Bài sau anh Khoa còn mời bàn bên một bình trà.'),
                  dict(id='stop', label='Dừng nhạc, la lên bảo hai bàn im', hint='', effects=dict(review=[2, 'Ca sĩ la khách giữa phòng.', 5]), good=False,
                       outcome='Cả phòng im phăng phắc, không khí mất sạch.')],
         default='calm'),
    dict(id='livestream_night', title='Khách livestream cả đêm thu tiền', emoji='📹', npc=4, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Một khách dựng điện thoại trên chân máy, phát trực tiếp cả đêm hát lên kênh có bật nhận quà tặng.',
         options=[dict(id='ask', label='Nhờ cô Diệu Hiền nhắc nhẹ: chỉ quay đoạn ngắn, không phát trực tiếp kiếm tiền', hint='', effects=dict(xp=4), good=True,
                       outcome='Khách tắt máy, xin lỗi, gọi thêm bình trà.'),
                  dict(id='ignore', label='Kệ, thêm người biết phòng trà', hint='', effects=dict(review=[2, 'Phòng trà để người ta phát cả đêm thu tiền.', 0]), good=False,
                       outcome='Kênh đó cắt ghép giọng bạn bán khóa học thanh nhạc.')],
         default='ask'),
    dict(id='cover_post', title='Muốn đăng bản cover bài của nhạc sĩ khác', emoji='🎼', npc=6, min_day=4, tone='gentle', at='between', weight=2, mods=None,
         text='Bé Linh quay giúp bạn một bản cover rất hay bài của một nhạc sĩ còn giữ bản quyền, rủ đăng lên kênh có bật kiếm tiền.',
         options=[dict(id='license', label='Xin phép tác giả hoặc đơn vị giữ quyền trước; chưa có thì chỉ đăng bài phòng trà được phép', hint='', effects=dict(xp=5), good=True,
                       outcome='Tác giả trả lời: đồng ý, chỉ cần ghi tên ông. Video lên kênh đàng hoàng.'),
                  dict(id='post', label='Đăng luôn, ghi tên tác giả là đủ', hint='', effects=dict(review=[2, 'Ca sĩ đăng bài người khác lấy tiền.', 6]), good=False,
                       outcome='Video bị gỡ vì vi phạm bản quyền sau hai ngày.')],
         default='license'),
    dict(id='blackout', title='Cúp điện đầu tối', emoji='🕯️', npc=1, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='Bảy giờ tối, khách đã ngồi kín thì cả dãy phố cúp điện. Loa, đèn sân khấu tắt hết.',
         options=[dict(id='acoustic', label='Thắp nến, chú Bảy ôm guitar, bạn hát mộc giữa phòng', hint='', effects=dict(xp=6, review=[5, 'Cúp điện mà đêm nhạc mộc hay nhất từ trước tới giờ.', 3]), good=True,
                       outcome='Không ai về. Có người nói đêm nay hay hơn mọi đêm.'),
                  dict(id='cancel', label='Xin lỗi, hủy đêm nhạc', hint='', effects=dict(review=[3, 'Cúp điện thì nghỉ, hơi tiếc.', 3]), good=None,
                       outcome='Khách lục tục ra về.')],
         default='acoustic'),
    dict(id='stage_fright', title='Bé Linh run khi lên hát thử', emoji='😰', npc=6, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Cô Diệu Hiền cho bé Linh hát thử một bài. Bé đứng run, micro rung theo tay.',
         options=[dict(id='support', label='Đứng cạnh hát bè, nhắc bé thở bụng, nhìn một khán giả quen', hint='', effects=dict(xp=5), good=True,
                       outcome='Tới điệp khúc thứ hai, bé Linh hát vững hẳn.'),
                  dict(id='leave', label='Để bé tự lo, ai cũng phải qua lần đầu', hint='', effects=dict(review=[3, 'Bé hát run quá, tội nghiệp.', 6]), good=None,
                       outcome='Bé hát xong, chạy vào hậu trường khóc.')],
         default='support'),
    dict(id='fan_messages', title='Người hâm mộ nhắn tin mỗi đêm', emoji='💌', npc=8, min_day=4, tone='gentle', at='between', weight=2, mods=None,
         text='Cô Mỹ xin số điện thoại riêng của bạn, nói muốn nhắn tin chúc ngủ ngon mỗi đêm.',
         options=[dict(id='polite', label='Cảm ơn cô, mời cô nhắn qua trang của phòng trà; giữ số riêng', hint='', effects=dict(xp=4), good=True,
                       outcome='Cô Mỹ vẫn mang hoa tới mỗi tối thứ bảy.'),
                  dict(id='give', label='Cho số cho vui', hint='', effects=dict(patience=-2), good=False,
                       outcome='Điện thoại của bạn reo tới hai giờ sáng.')],
         default='polite'),
    dict(id='slot_war', title='Ca sĩ khác giành lượt giờ vàng', emoji='⏱️', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Một ca sĩ mới tự ý dời tên mình lên lượt chín giờ, lượt của bạn bị đẩy xuống cuối.',
         options=[dict(id='ask', label='Nhờ cô Diệu Hiền xem lại lịch, theo lịch đã ký', hint='', effects=dict(xp=4), good=True,
                       outcome='Cô Diệu Hiền xếp lại lịch, dặn từ giờ đổi lượt phải hỏi cô.'),
                  dict(id='fight', label='Cãi nhau ngay trong hậu trường', hint='', effects=dict(patience=-3, review=[2, 'Hậu trường ồn ào nghe tới ngoài.', 0]), good=False,
                       outcome='Khán giả nghe tiếng cãi vọng ra từ cánh gà.')],
         default='ask'),
    dict(id='sore_throat', title='Sáng dậy khàn tiếng', emoji='🤒', npc=0, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='Sáng nay bạn thức dậy, nói không ra hơi. Tối nay vẫn có lượt hát.',
         options=[dict(id='rest', label='Uống nước ấm, nói ít, báo cô Diệu Hiền đổi sang bài nhẹ', hint='', effects=dict(xp=4), good=True,
                       outcome='Tối đó bạn hát hai bài nhẹ, giọng vẫn ấm.'),
                  dict(id='pills', label='Uống thuốc giảm đau, gào cho xong', hint='', effects=dict(patience=-3, review=[2, 'Ca sĩ hát hụt hơi, nghe tội.', 5]), good=False,
                       outcome='Bạn mất giọng thêm ba ngày.')],
         default='rest'),
    dict(id='hospital_song', title='Ông Tư nhờ hát qua điện thoại', emoji='📞', npc=3, min_day=5, tone='gentle', at='between', weight=2, mods=None,
         text='Bà Tư nằm viện. Ông Tư ngồi một mình bàn số 3, nhờ bạn gọi video hát tặng bà bài hai ông bà hay nghe.',
         options=[dict(id='sing', label='Xin cô Diệu Hiền năm phút, gọi video hát tặng bà', hint='', effects=dict(xp=7, review=[5, 'Ca sĩ hát qua điện thoại cho vợ tôi nằm viện.', 3]), good=True,
                       outcome='Bà Tư khóc trong điện thoại. Cả phòng lặng đi rồi vỗ tay.'),
                  dict(id='later', label='Hẹn ông khi khác, giờ đang đông khách', hint='', effects=dict(review=[3, 'Ca sĩ bận quá.', 3]), good=None,
                       outcome='Ông Tư gật đầu, uống hết bình trà rồi về.')],
         default='sing'),
    dict(id='star_fee', title='Người lạ hứa “đẩy” bạn thành ngôi sao', emoji='⭐', npc=4, min_day=4, tone='tense', at='between', weight=2, mods=None,
         text='Một người tự xưng giám đốc công ty giải trí đưa danh thiếp: “Đóng năm triệu phí đào tạo, tháng sau lên truyền hình.”',
         options=[dict(id='refuse', label='Từ chối; tra công ty, hỏi cô Diệu Hiền, không đóng tiền trước', hint='', effects=dict(xp=5), good=True,
                       outcome='Cô Diệu Hiền cười: công ty đó đổi tên ba lần trong năm.'),
                  dict(id='pay', label='Đóng thử một phần cho chắc suất', hint='', effects=dict(money=-10, money_loss='normal'), good=False,
                       outcome='Số điện thoại kia không bao giờ nghe máy nữa.')],
         default='refuse'),
]
