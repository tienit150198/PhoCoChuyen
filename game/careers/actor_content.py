"""🎬 Hãng phim Bến Mây: the words and tables of an actor's shooting days (game/careers/actor.py).

Every table is static: a scene is a pure function of (day, slot), so validate_state can rebuild it. The owner's rule
("nghề nào cũng phải có nhiều yêu cầu oái oăm"): each scene carries one or two awkward demands from the set (DEMANDS)
and the studio has its own surprises between scenes (DESK, kit.desk), some of which leave a mark that brings a later
event (a script page photographed and posted turns up online a few days later). The series, the roles and every line
of dialogue are invented for the game.
"""
from __future__ import annotations

PLACE = 'Hãng phim Bến Mây'
MENTOR_NAME = 'Đạo diễn Minh Triết'
SERIES = 'Ngõ Nhỏ Có Nắng'

PEOPLE = [
    ('Đạo diễn Minh Triết', 'Đạo diễn phim truyền hình', 'Nói nhỏ mà ai cũng nghe. Câu quen miệng: “Diễn ít thôi, sống nhiều vào.”', 'warm'),
    ('Chị Kiều', 'Thư ký trường quay', 'Chụp ảnh từng cảnh, nhớ ai cầm ly tay nào, áo cài mấy nút.', 'picky'),
    ('Anh Lực', 'Điều phối hành động', 'Hai mươi năm đóng thế. Chưa tập đủ thì chưa ai được quay.', 'quiet'),
    ('Tuấn Kiệt', 'Bạn diễn, đang nổi', 'Hay sửa thoại, hay tới trễ, nghĩ mình là ngôi sao.', 'entitled'),
    ('Bé Bắp', 'Diễn viên nhí, tám tuổi', 'Thuộc thoại nhanh hơn người lớn, mệt là ngủ gục.', 'genz'),
    ('Chị Sa', 'Phục trang', 'Mỗi bộ đồ một móc, một thẻ tên. Trả nhầm móc là chị biết liền.', 'warm'),
    ('Anh Tùng', 'Truyền thông của hãng', 'Muốn phim “nổ” trên mạng bằng mọi giá.', 'bossy'),
    ('Bà Năm', 'Chủ căn nhà làm bối cảnh', 'Cho đoàn mượn nhà, chỉ xin đừng làm hư bộ ghế gỗ của ông nhà.', 'warm'),
]
MENTOR = 0
SCRIPT = 1
STUNT = 2
COSTAR = 3
KID = 4
COSTUME = 5
PR = 6
HOUSE = 7

WRONG_COST = 8
QUALITY_FLOOR = 40
MILESTONES = (4, 10, 20, 40)   # days: continuity and retakes, a second demand, a harder scene list, the hardest days
MASTER = (90, 30)       # Diễn viên vững nghề: good scenes, active days
EXPERT = (170, 45)      # Gương mặt của Bến Mây

# The scenes: (name, emoji, min day, bonus in xu before quality, who hands you the page, how it reads, what you see
# on set, the plan ('set' or 'press'), and the lines in the order they are said; the order can be read from the lines).
SCENES = {
    'cai_nhau': dict(name='Cảnh cãi nhau', emoji='😠', day=1, bonus=6, npc=1, plan='set',
                     say=('Trang 12: hai vợ chồng to tiếng trong bếp, chồng về muộn.', 'Trang 30: chị em ruột cãi nhau vì căn nhà của mẹ.'),
                     see=('Bối cảnh là gian bếp, nồi cơm đã nguội trên bàn.', 'Đèn hắt vàng, bạn diễn đứng cạnh chiếc tủ lạnh cũ.'),
                     lines=[('a', '“Anh lại về muộn, cơm nguội hết rồi.”'), ('b', '“Công ty có việc gấp, em đừng làm lớn chuyện.”'),
                            ('c', '“Việc gấp mà một tin nhắn cũng không có?”'), ('d', '“Anh xin lỗi. Mai anh về sớm nấu cho em.”')]),
    'chia_tay': dict(name='Cảnh chia tay', emoji='😢', day=1, bonus=6, npc=0, plan='set',
                     say=('Trang 45: hai người chia tay ở bến xe, không ai khóc thành tiếng.', 'Trang 46: tiễn bạn thân đi làm xa.'),
                     see=('Bến xe buổi sáng, chiếc vali đặt dưới chân.', 'Trời âm u, tiếng loa gọi xe vang lên.'),
                     lines=[('a', '“Xe sắp chạy rồi.”'), ('b', '“Tới nơi nhớ gọi cho mình.”'),
                            ('c', '“Ừ. Bạn ở lại giữ sức khỏe.”'), ('d', '“Đi đi, kẻo lỡ chuyến.”')]),
    'doan_tu': dict(name='Cảnh đoàn tụ', emoji='🤗', day=2, bonus=6, npc=1, plan='set',
                    say=('Trang 60: con đi xa mười năm về, mẹ đứng ở cổng.', 'Trang 61: hai anh em gặp lại sau trận lũ.'),
                    see=('Cổng nhà có giàn bông giấy, bà Năm đứng xem từ xa.', 'Một chiếc xe ôm dừng trước ngõ.'),
                    lines=[('a', '“Mẹ ơi, con về rồi.”'), ('b', '“Trời ơi… con đó hả?”'),
                           ('c', '“Con xin lỗi, đi lâu quá.”'), ('d', '“Về là được rồi. Vô nhà ăn cơm con.”')]),
    'hoi_hop': dict(name='Cảnh hồi hộp', emoji='😨', day=3, bonus=7, npc=0, plan='set',
                    say=('Trang 72: nghe tiếng động lạ trong nhà lúc nửa đêm.', 'Trang 73: tìm chìa khóa khi có người gõ cửa.'),
                    see=('Phòng khách tối, chỉ có ánh đèn pin.', 'Tiếng mưa rơi trên mái, cửa sổ hé mở.'),
                    lines=[('a', '“Ai đó?”'), ('b', '(Im lặng, tiếng bước chân lại gần.)'),
                           ('c', '“Tôi gọi công an đó nghe!”'), ('d', '“Thì ra là con mèo…”')]),
    'hanh_dong': dict(name='Cảnh hành động', emoji='🥊', day=4, bonus=8, npc=2, plan='set',
                      say=('Trang 80: giằng co với tên cướp giật túi ở đầu hẻm.', 'Trang 81: chạy đuổi theo kẻ trộm qua dãy sạp chợ.'),
                      see=('Đầu hẻm trải đệm, anh Lực đang dựng mốc.', 'Dãy sạp chợ dựng giả, nền đất còn ướt.'),
                      lines=[('a', '“Đứng lại!”'), ('b', '“Trả túi cho cô ấy!”'),
                             ('c', '(Giằng co, kẻ cướp bỏ chạy.)'), ('d', '“Chị có sao không?”')]),
    'tre_em': dict(name='Cảnh với diễn viên nhí', emoji='🧒', day=5, bonus=7, npc=4, plan='set',
                   say=('Trang 90: dạy bé Bắp đạp xe trong sân.', 'Trang 91: dỗ bé Bắp khóc vì mất con mèo.'),
                   see=('Sân nhà bà Năm, chiếc xe đạp nhỏ dựng sẵn.', 'Bé Bắp ôm gối, mắt còn ngái ngủ.'),
                   lines=[('a', '“Bắp ơi, lại đây chú chỉ.”'), ('b', '“Con sợ té lắm.”'),
                          ('c', '“Có chú giữ phía sau rồi.”'), ('d', '“Con đạp được rồi nè!”')]),
    'mua': dict(name='Cảnh dưới mưa', emoji='🌧️', day=6, bonus=8, npc=0, plan='set',
                say=('Trang 100: đứng dưới mưa chờ người không tới.', 'Trang 101: chạy dưới mưa đuổi theo chiếc xe.'),
                see=('Xe bồn phun mưa đã sẵn, dây điện đèn được bọc kín.', 'Nước mưa giả lạnh, chị Sa ôm sẵn khăn và áo khô.'),
                lines=[('a', '(Nhìn đồng hồ, nhìn ra đầu ngõ.)'), ('b', '“Chắc anh ấy không tới đâu.”'),
                       ('c', '(Một chiếc ô che lên đầu.)'), ('d', '“Em xin lỗi, anh tới muộn.”')]),
    'ra_mat': dict(name='Buổi ra mắt phim', emoji='🎬', day=8, bonus=7, npc=6, plan='press',
                   say=('Tối nay ra mắt phim, em lên phát biểu rồi trả lời báo chí nha.', 'Họp báo trước giờ chiếu tập một, em nói ngắn thôi.'),
                   see=('Thảm đỏ trước rạp, phóng viên cầm máy ảnh đứng kín.', 'Sân khấu nhỏ, micro, phông có tên phim.'),
                   lines=[('a', '“Xin chào quý vị khán giả và báo chí.”'), ('b', '“Cảm ơn đạo diễn và cả đoàn phim đã làm việc cực khổ.”'),
                          ('c', '“Vai diễn này dạy tôi biết kiên nhẫn.”'), ('d', '“Mời mọi người đón xem phim tối thứ bảy.”')]),
}
SCENE_ORDER = tuple(SCENES)
ROLES = ('vai Hạnh', 'vai Tú', 'vai cô giáo Mai', 'vai anh Ba', 'vai bà chủ quán', 'vai Dũng', 'vai Thảo', 'vai Lâm')

# ---------------------------------------------------------------- on set
BLOCKING = [
    ('Chị Kiều dán dấu chữ X bằng băng keo trên sàn, máy quay đặt bên trái.',
     'Đứng lên dấu X, nghiêng nửa người về phía máy', ('Đứng giữa phòng cho nổi', 'Quay lưng về máy cho tự nhiên')),
    ('Cảnh hai người, máy quay qua vai bạn diễn để thấy mặt bạn.',
     'Đứng đúng dấu, nhìn vào mắt bạn diễn, không nhìn máy', ('Nhìn thẳng ống kính cho rõ mặt', 'Bước lên che bạn diễn')),
    ('Bạn phải đi từ cửa tới bàn rồi dừng đúng dấu thứ hai.',
     'Đếm bước lúc tập, dừng đúng dấu thứ hai trong ánh đèn', ('Đi tự do, máy sẽ theo', 'Dừng chỗ nào thấy hợp')),
    ('Đèn chính rọi từ bên phải; bước lệch nửa bước là mặt bị tối.',
     'Giữ đúng dấu, nghiêng mặt về phía đèn', ('Bước ra khỏi dấu cho thoải mái', 'Cúi mặt xuống cho buồn')),
    ('Cận cảnh: khung hình chỉ thấy từ vai trở lên.',
     'Giữ người yên, diễn bằng mắt và giọng', ('Vung tay cho có cảm xúc', 'Lắc đầu nhiều cho sinh động')),
]
CONTINUITY = [
    ('Ảnh chị Kiều chụp cảnh trước: bạn cầm ly trà tay phải, trà còn nửa ly.',
     'Cầm ly tay phải, rót trà còn nửa ly như ảnh', ('Cầm tay nào cũng được', 'Rót đầy ly cho đẹp')),
    ('Cảnh trước bạn cài áo hai nút, tóc vén sau tai trái.',
     'Cài đúng hai nút, vén tóc tai trái như ảnh chị Kiều chụp', ('Cài hết nút cho gọn', 'Xõa tóc cho tự nhiên')),
    ('Cảnh trước trời mưa, áo bạn ướt vai. Hôm nay quay cảnh tiếp theo ngay sau đó.',
     'Nhờ chị Sa xịt nước cho áo ướt đúng chỗ như ảnh', ('Mặc áo khô cho thoải mái', 'Kệ, khán giả không để ý')),
    ('Hôm qua bạn đeo đồng hồ tay trái trong cảnh này, quay tiếp đoạn sau.',
     'Đeo lại đồng hồ tay trái như hôm qua', ('Bỏ đồng hồ cho gọn', 'Đeo tay phải cho tiện')),
]
DIRECTIONS = [
    ('Đạo diễn: “Nhỏ lại, đây là cận cảnh.”',
     'Giảm biểu cảm, nói nhỏ, để mắt kể chuyện', ('Diễn to hơn cho rõ', 'Cãi là mình đang diễn đúng')),
    ('Đạo diễn: “Chậm lại một nhịp trước câu cuối.”',
     'Dừng một nhịp thở rồi mới nói câu cuối', ('Nói nhanh cho kịp giờ', 'Bỏ luôn câu cuối')),
    ('Đạo diễn: “Lần này giận mà không được hét.”',
     'Nói chậm, giọng thấp, nắm chặt tay', ('Hét to hơn lần trước', 'Cười cho đỡ căng')),
    ('Đạo diễn: “Khóc mà đừng cố khóc.”',
     'Nhớ lại chuyện buồn có thật, để nước mắt tự đến, không ép', ('Nhỏ thuốc nhỏ mắt cho nhanh', 'Che mặt, giả tiếng khóc')),
    ('Đạo diễn: “Diễn lại, nhưng lần này nhân vật đang giấu chuyện.”',
     'Nói đúng thoại, ánh mắt né đi một nhịp', ('Kể luôn bí mật cho rõ', 'Đổi thoại cho hợp ý mình')),
]
RETAKE = (2, 3, 4)       # camera angles of a scene; each needs a number of good takes
STEPS = {
    'an_toan': [('dem', 'Kiểm tra đệm và mặt sàn'), ('cham', 'Tập chậm từng động tác với anh Lực'), ('bao_ho', 'Mặc bảo hộ dưới trang phục'),
                ('ra_hieu', 'Thống nhất tín hiệu dừng'), ('tap', 'Tập đủ tốc độ, chưa quay'), ('quay', 'Quay khi anh Lực hô sẵn sàng')],
}
PRESS = [
    ('Phóng viên: “Nghe nói bạn và bạn diễn đang hẹn hò, đúng không?”',
     'Cười, nói thật là đồng nghiệp, mời mọi người quan tâm tới phim', ('Úp mở cho tin lan', 'Nói “đúng rồi” cho phim nổi')),
    ('Phóng viên: “Tập cuối ai chết vậy?”',
     'Giữ bí mật, mời khán giả xem tới tập cuối', ('Kể hết cái kết', 'Gợi ý vài chi tiết cho vui')),
    ('Phóng viên: “Bạn có cảnh nào phải đóng thế không?”',
     'Nói thật cảnh nguy hiểm có anh Lực và người đóng thế, cảm ơn họ', ('Nói mình tự đóng hết cho oai', 'Lảng sang chuyện khác')),
    ('Phóng viên: “Cát-xê của bạn bao nhiêu?”',
     'Cảm ơn, xin giữ chuyện hợp đồng riêng, nói về vai diễn', ('Nói một con số thật to', 'Nói xấu cát-xê của bạn diễn')),
]
PROMO_GOOD = ('Ảnh hậu trường đã được hãng duyệt', 'Lịch chiếu đúng ngày, đúng kênh', 'Lời cảm ơn đoàn phim')
PROMO_BAD = ('Ảnh trang kịch bản tập cuối', 'Tin đồn hẹn hò bạn diễn cho phim nổi', 'Số lượt xem tự bịa thêm')
COSTUME_HOOKS = (3, 4, 5, 6, 7, 8, 9, 10, 11, 12)

# ---------------------------------------------------------------- 🌀 oái oăm on set (one or two a scene)
# (min day, what someone says, the right answer, the wrong ones, only for these scenes or None)
DEMANDS = [
    (1, 'Tuấn Kiệt: “Tát thật đi cho cảm xúc, anh chịu được.”',
     'Từ chối tát thật; nhờ anh Lực dựng góc máy che, tập động tác giả', ('Tát thật cho chân thật', 'Tát nhẹ thôi'), ('cai_nhau',)),
    (1, 'Anh Tùng: “Chụp trang kịch bản tập cuối đăng lên cho khán giả tò mò.”',
     'Không đăng; kịch bản là bí mật của hãng', ('Đăng một góc thôi', 'Đăng rồi xóa sau một tiếng'), None),
    (1, 'Tuấn Kiệt: “Bỏ câu thoại này đi, anh nghĩ câu khác hay hơn.”',
     'Hỏi đạo diễn trước; đạo diễn duyệt thì mới đổi', ('Đổi luôn theo ý anh Kiệt', 'Cãi nhau với anh Kiệt'), None),
    (1, 'Phụ trách đoàn: “Quay thêm tới hai giờ sáng nha, tiền ngoài giờ tính sau.”',
     'Hỏi rõ giờ và tiền ngoài giờ theo hợp đồng trước khi đồng ý', ('Quay luôn, tính sau', 'Bỏ về không nói gì'), None),
    (2, 'Anh Tùng: “Tung tin em với Kiệt hẹn hò cho phim nổi.”',
     'Từ chối tung tin giả; mời truyền thông bằng hậu trường thật', ('Đồng ý cho phim nổi', 'Tự đăng úp mở'), None),
    (2, 'Một người lạ: “Đóng tiền chị đưa em vào vai chính phim khác.”',
     'Từ chối; vai diễn thì qua thử vai của hãng, không đóng tiền', ('Đóng thử một ít', 'Hỏi giá rẻ hơn'), None),
    (3, 'Tuấn Kiệt: “Tự nhảy qua sạp luôn, chờ đệm lâu quá.”',
     'Chờ anh Lực kiểm tra đệm, tập chậm rồi mới quay', ('Nhảy luôn cho nhanh', 'Nhảy mà không cần đệm'), ('hanh_dong',)),
    (3, 'Phụ trách đoàn: “Quay cảnh chạy xe máy không cần mũ cho đẹp.”',
     'Đội mũ; xe đứng yên hoặc có xe kéo, đường đã chặn', ('Bỏ mũ cho đẹp hình', 'Chạy nhanh rồi tính'), None),
    (4, 'Phụ trách đoàn: “Cho bé Bắp quay thêm tới mười giờ đêm, bé còn tỉnh mà.”',
     'Cho bé nghỉ đúng giờ; cảnh còn lại quay ngày mai có mẹ bé đi cùng', ('Quay thêm, bé còn tỉnh', 'Hỏi bé có muốn quay không'), ('tre_em',)),
    (4, 'Một người trong đoàn hút thuốc ngay cạnh bé Bắp.',
     'Nhờ anh ấy ra ngoài khu hút thuốc, cách xa bé', ('Kệ, chỗ nào chẳng có khói', 'Cho bé ra ngoài thay'), ('tre_em',)),
    (5, 'Phụ trách đoàn: “Xe phun mưa chập điện, cứ quay đi, dây đèn ướt chút không sao.”',
     'Dừng lại, báo tắt điện, chờ thợ bọc dây xong mới quay', ('Quay nhanh cho xong', 'Né dây ra rồi quay tiếp'), ('mua',)),
    (6, 'Anh Tùng: “Nói với báo là em tự đóng hết cảnh nguy hiểm.”',
     'Nói thật có người đóng thế và anh Lực, cảm ơn họ', ('Nhận hết cho oai', 'Nói úp mở'), ('ra_mat', 'hanh_dong')),
]

RULES = [
    'Mọi con số, quy định và thoại dưới đây là sổ tay của Hãng phim Bến Mây trong trò chơi; phim “Ngõ Nhỏ Có Nắng” là phim của hãng.',
    'Đọc trang kịch bản trước: cảnh gì, ai nói trước, cảm xúc gì.',
    'Thoại nói đúng thứ tự trong kịch bản. Muốn đổi thoại phải hỏi đạo diễn.',
    'Đứng đúng dấu băng keo trên sàn; nhìn bạn diễn, không nhìn máy quay; cận cảnh thì diễn bằng mắt.',
    'Nối cảnh: làm y như ảnh chị Kiều chụp cảnh trước (tay cầm, nút áo, tóc, đồ đeo, áo ướt).',
    'Số lượt còn phải quay = số góc máy × số lượt đạt mỗi góc − số lượt đã đạt.',
    'Cảnh hành động: đệm → tập chậm với anh Lực → bảo hộ → tín hiệu dừng → tập đủ tốc độ → quay khi anh Lực hô.',
    'Không tát thật, không đóng cảnh nguy hiểm khi chưa có anh Lực; chạy xe phải đội mũ.',
    'Diễn viên nhí nghỉ đúng giờ, có người nhà đi cùng; không hút thuốc gần bé.',
    'Cảnh mưa: dây điện phải bọc kín; chập điện là dừng ngay.',
    'Kịch bản là bí mật của hãng; không tung tin đồn, không nói dối báo chí.',
    'Quay xong, trả trang phục đúng móc, đúng thẻ tên vai cho chị Sa.',
]

# ---------------------------------------------------------------- 🔔 studio surprises (kit.desk)
DESK = [
    dict(id='script_photo', title='Bạn diễn chụp kịch bản tập cuối', emoji='📸', npc=3, min_day=3, tone='tense', at='between', weight=2, mods=None,
         no_mark='leaked',
         text='Tuấn Kiệt chụp trang kịch bản tập cuối, nói để “khoe nhẹ” với người hâm mộ. Anh rủ bạn chụp chung.',
         options=[dict(id='stop', label='Nhắc anh xóa ảnh, báo chị Kiều cất kịch bản', hint='', effects=dict(xp=6), good=True,
                       outcome='Tuấn Kiệt lầm bầm nhưng xóa ảnh. Chị Kiều khóa tủ kịch bản.'),
                  dict(id='join', label='Chụp chung cho vui, chắc không ai biết', hint='', effects=dict(mark='leaked'), good=False,
                       outcome='Tấm ảnh nằm trong điện thoại của hai người.')],
         default='stop'),
    dict(id='leak_found', title='Kịch bản tập cuối lộ trên mạng', emoji='🔥', npc=6, min_day=4, tone='tense', at='between', weight=5, mods=None,
         need_mark='leaked',
         text='Ảnh trang kịch bản tập cuối lan khắp mạng. Anh Tùng hỏi cả đoàn: ai chụp?',
         options=[dict(id='admit', label='Nhận thật, xin lỗi đạo diễn, cùng hãng gỡ ảnh', hint='',
                       effects=dict(unmark='leaked', review=[3, 'Lỡ sai nhưng nhận lỗi đàng hoàng.', 0]), good=None,
                       outcome='Đạo diễn thở dài: “Lần sau giữ kịch bản như giữ ví nghe.”'),
                  dict(id='deny', label='Im lặng, để Tuấn Kiệt chịu', hint='',
                       effects=dict(unmark='leaked', money=-10, money_loss='normal', review=[1, 'Lộ kịch bản mà chối.', 0]), good=False,
                       outcome='Ảnh có cả tay bạn trong khung. Hãng trừ tiền cả hai.')],
         default='admit'),
    dict(id='stunt_skip', title='Bạn diễn đòi bỏ buổi tập võ', emoji='🥋', npc=3, min_day=4, tone='tense', at='between', weight=2, mods=None,
         text='Tuấn Kiệt bảo: “Bỏ buổi tập với anh Lực đi, mai quay luôn, anh từng học võ.”',
         options=[dict(id='train', label='Vẫn tập đủ với anh Lực, rủ Kiệt cùng tập', hint='', effects=dict(xp=6), good=True,
                       outcome='Hôm sau cảnh giằng co xong trong hai lượt, không ai trầy xước.'),
                  dict(id='skip', label='Bỏ tập cho khỏe', hint='', effects=dict(patience=-3, review=[2, 'Diễn viên tập không kỹ, quay mãi không xong.', 2]), good=False,
                       outcome='Kiệt trật cổ tay ngay lượt đầu. Đoàn nghỉ nửa ngày.')],
         default='train'),
    dict(id='late_costar', title='Bạn diễn tới trễ hai tiếng', emoji='⏰', npc=3, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Tuấn Kiệt tới trễ hai tiếng, cả đoàn ngồi chờ. Đạo diễn hỏi bạn có muốn quay trước các cảnh riêng không.',
         options=[dict(id='solo', label='Đồng ý quay trước các cảnh riêng, giữ năng lượng cho cảnh chung', hint='', effects=dict(xp=5), good=True,
                       outcome='Đoàn không mất buổi. Kiệt tới, thấy mọi người đã quay xong ba cảnh.'),
                  dict(id='complain', label='Lên mạng than bạn diễn đi trễ', hint='', effects=dict(review=[2, 'Chuyện nội bộ mang lên mạng.', 6]), good=False,
                       outcome='Bài than lan nhanh. Anh Tùng gọi điện, giọng không vui.')],
         default='solo'),
    dict(id='kid_tired', title='Bé Bắp ngủ gục giữa cảnh', emoji='😴', npc=4, min_day=5, tone='gentle', at='between', weight=2, mods=None,
         text='Bé Bắp ngủ gục trên ghế, cảnh còn hai lượt. Mẹ bé đang đi mua nước.',
         options=[dict(id='rest', label='Xin đạo diễn cho bé nghỉ, quay cảnh của mình trước', hint='', effects=dict(xp=5, review=[5, 'Đoàn thương bé Bắp lắm.', 4]), good=True,
                       outcome='Bé ngủ ba mươi phút, dậy diễn một lượt là đạt.'),
                  dict(id='wake', label='Đánh thức bé dậy quay cho xong', hint='', effects=dict(review=[2, 'Bé quay mệt quá, khóc ngay trên trường quay.', 4]), good=False,
                       outcome='Bé khóc òa, phải dỗ mất cả tiếng.')],
         default='rest'),
    dict(id='broken_chair', title='Lỡ làm gãy chân ghế của bà Năm', emoji='🪑', npc=7, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Lúc tập cảnh cãi nhau, bạn đẩy mạnh làm gãy chân bộ ghế gỗ của ông nhà bà Năm.',
         options=[dict(id='own', label='Xin lỗi bà Năm, báo đoàn, nhờ thợ sửa bằng tiền của mình', hint='', effects=dict(money=-4, money_loss='normal', xp=5, review=[5, 'Đoàn làm hư đồ nhưng sửa đàng hoàng.', 7]), good=True,
                       outcome='Thợ mộc ráp lại chân ghế. Bà Năm còn nấu chè mời đoàn.'),
                  dict(id='hide', label='Kê lại cho đứng, coi như không có gì', hint='', effects=dict(review=[1, 'Đoàn phim làm gãy ghế rồi giấu.', 7]), good=False,
                       outcome='Bà Năm ngồi xuống, ghế sụp. Đoàn mất chỗ quay.')],
         default='own'),
    dict(id='fans_on_set', title='Người hâm mộ tràn vào trường quay', emoji='📱', npc=6, min_day=4, tone='gentle', at='between', weight=2, mods=None,
         text='Một nhóm người hâm mộ đứng sát máy quay xin chụp hình, cảnh đang quay dở.',
         options=[dict(id='later', label='Cười chào, hẹn chụp hình giờ nghỉ, nhờ đoàn giữ khoảng cách', hint='', effects=dict(xp=4), good=True,
                       outcome='Giờ nghỉ bạn chụp với cả nhóm. Ai cũng vui.'),
                  dict(id='now', label='Dừng quay, chụp hình luôn', hint='', effects=dict(patience=-2, review=[3, 'Diễn viên dễ thương mà đoàn trễ giờ.', 0]), good=None,
                       outcome='Đoàn trễ bốn mươi phút, đạo diễn lắc đầu.')],
         default='later'),
    dict(id='heatwave', title='Nắng gắt giữa trưa', emoji='☀️', npc=5, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='Trưa nay nắng gắt, bạn mặc áo khoác dày của vai diễn ngoài trời.',
         options=[dict(id='water', label='Uống nước đủ, cởi áo khoác giữa các lượt, nghỉ trong bóng râm', hint='', effects=dict(xp=4), good=True,
                       outcome='Cả buổi bạn vẫn tươi tỉnh, không ai bị say nắng.'),
                  dict(id='push', label='Mặc nguyên áo cả ngày cho nhập vai', hint='', effects=dict(patience=-3), good=False,
                       outcome='Bạn choáng váng, phải nằm nghỉ một tiếng.')],
         default='water'),
    dict(id='casting_fee', title='Tin nhắn mời thử vai có phí', emoji='💸', npc=6, min_day=4, tone='tense', at='between', weight=2, mods=None,
         text='Một trang mạng nhắn: “Chuyển một triệu phí hồ sơ để thử vai chính phim điện ảnh.”',
         options=[dict(id='refuse', label='Không chuyển; thử vai thật không thu phí, hỏi anh Tùng', hint='', effects=dict(xp=5), good=True,
                       outcome='Anh Tùng cười: trang đó lừa cả chục bạn trẻ rồi.'),
                  dict(id='pay', label='Chuyển thử cho chắc suất', hint='', effects=dict(money=-10, money_loss='normal'), good=False,
                       outcome='Trang mạng đó biến mất sau một đêm.')],
         default='refuse'),
    dict(id='ad_lib', title='Lỡ nói thoại ngoài kịch bản', emoji='💬', npc=0, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Lượt vừa rồi bạn buột miệng một câu ngoài kịch bản. Cả đoàn bật cười, chị Kiều nhìn đạo diễn.',
         options=[dict(id='ask', label='Hỏi đạo diễn giữ hay bỏ, ghi lại cho chị Kiều', hint='', effects=dict(xp=5), good=True,
                       outcome='Đạo diễn giữ câu đó. Chị Kiều ghi vào sổ cho cảnh sau khớp.'),
                  dict(id='keep', label='Lượt sau cứ nói thêm cho vui', hint='', effects=dict(review=[3, 'Thoại mỗi lượt một kiểu, khó dựng.', 1]), good=None,
                       outcome='Bên dựng phim than không ghép được hai lượt.')],
         default='ask'),
    dict(id='review_bomb', title='Bị chê tơi tả trên mạng', emoji='💢', npc=6, min_day=6, tone='tense', at='between', weight=2, mods=None,
         text='Tập một lên sóng, có người chê bạn diễn đơ, bình luận nặng lời.',
         options=[dict(id='learn', label='Đọc góp ý có lý, hỏi đạo diễn cách sửa, không cãi nhau', hint='', effects=dict(xp=6), good=True,
                       outcome='Tập sau nhiều người khen bạn tiến bộ.'),
                  dict(id='fight', label='Trả lời từng bình luận cho ra lẽ', hint='', effects=dict(review=[2, 'Diễn viên cãi nhau với khán giả.', 6]), good=False,
                       outcome='Cuộc cãi nhau nổi hơn cả phim.')],
         default='learn'),
    dict(id='lost_voice', title='Sáng dậy khàn giọng', emoji='🤒', npc=0, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='Sáng nay bạn khàn giọng, hôm nay có hai cảnh thoại dài.',
         options=[dict(id='tell', label='Báo đạo diễn, xin quay cảnh không thoại trước, uống nước ấm', hint='', effects=dict(xp=4), good=True,
                       outcome='Đạo diễn đổi lịch, chiều giọng bạn đã ổn.'),
                  dict(id='hide', label='Giấu, gắng nói cho xong', hint='', effects=dict(patience=-2, review=[3, 'Giọng diễn viên khàn đặc, phải lồng tiếng lại.', 1]), good=None,
                       outcome='Phòng thu phải lồng tiếng lại cả hai cảnh.')],
         default='tell'),
]
