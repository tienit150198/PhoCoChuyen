"""📻 Đài phát thanh Sóng Mây: a fictional ward radio station (FM 99,9). Rules, sponsors, songs and callers are game content only.

Owner's standing rule for every career: many "oái oăm" demands. Here: callers who want songs nobody has heard of, a sponsor who
changes the script a minute before air, the power going out in the middle of a show, listeners who call in to swear, names read
wrong on air, a guest who turns up late or drunk.
"""

PEOPLE = [
    ('Chị Hoa', 'Trưởng đài, biên tập viên', 'Duyệt từng chữ trước khi lên sóng, bút đỏ lúc nào cũng gài sau tai.', 'picky'),
    ('Anh Tuấn', 'Kỹ thuật viên phòng máy', 'Thuộc từng sợi dây sau bàn trộn âm, chìa khóa máy phát đeo ở cổ.', 'quiet'),
    ('Ông Lực', 'Chủ Điện máy Lực Phát, nhà tài trợ', 'Gửi kịch bản quảng cáo lúc chín giờ năm mươi chín cho bản tin mười giờ.', 'picky'),
    ('Cô Ba Gánh', 'Thính giả gọi vào mỗi sáng', 'Gánh xôi đầu hẻm, vừa bán vừa nghe đài, xin bài cho cả xóm.', 'warm'),
    ('Bé Su', 'Học sinh lớp 9', 'Gọi xin những bài mà cả đài chưa ai nghe tên.', 'genz'),
    ('Chú Hùng', 'Thính giả nóng tính', 'Gọi vào để chê, chê xong lại gọi xin bài.', 'picky'),
    ('Bà Tư', 'Tổ trưởng tổ dân phố', 'Mang tin phường tới đài, chữ viết tay nghiêng như lá lúa.', 'warm'),
]
MANAGER = 0        # Chị Hoa hands out every work slip
TECH = 1           # Anh Tuấn, the power and the transmitter
SPONSOR = 2        # Ông Lực, the sponsor

# 🎙️ two roles. 'news' (Phát thanh viên) is where everyone starts; 'dj' (DJ ca nhạc, the evening show) opens after probation.
ROLES = {
    'news': ('Phát thanh viên', '🎙️', 'Bản tin phường, quảng cáo, lời chúc thính giả'),
    'dj': ('DJ ca nhạc', '🎧', 'Nhạc theo yêu cầu, thính giả gọi vào, xếp chương trình'),
}
JOBS = {
    'bulletin': ('Bản tin phường', '📰', 'news'),
    'spot': ('Đọc quảng cáo nhà tài trợ', '📢', 'news'),
    'wishes': ('Đọc lời chúc thính giả', '💌', 'news'),
    'request': ('Khách gọi xin bài', '🎵', 'dj'),
    'callin': ('Thính giả gọi vào sóng', '☎️', 'dj'),
    'playlist': ('Xếp chương trình ca nhạc', '🎚️', 'dj'),
}
ROLE_JOBS = {'news': ('bulletin', 'spot', 'wishes'), 'dj': ('request', 'callin', 'playlist')}
BONUS = dict(bulletin=6, spot=6, wishes=6, request=8, callin=8, playlist=8)
PROBATION = 3      # good shifts as Phát thanh viên (studio check + a good job + the outage handled) before DJ
WRONG_COST = 6     # quality lost per redone step
QUALITY_FLOOR = 60
OUTAGE_CHANCE = 0.35   # a power cut in the middle of the show, from day 2, after the first finished job
OUTAGE_SLIPS = 3       # this many wrong steps while the air is dead: "sóng câm" too long, a 2★ review

# ---------------------------------------------------------------- shift checklists
OPEN_STEPS = [('mixer', 'Bật bàn trộn âm, kéo hết cần gạt về 0'), ('mic', 'Nói thử mic: “Một, hai, ba, Sóng Mây xin chào”'),
              ('phones', 'Đeo tai nghe, nghe tiếng vọng và tiếng rè'), ('line', 'Kiểm đường truyền tới cột phát: đèn xanh'),
              ('onair', 'Bật đèn ĐANG PHÁT SÓNG rồi mới mở mic')]
OUTAGE_STEPS = [('ups', 'Chuyển máy phát sang bộ lưu điện (UPS)'), ('tape', 'Bật băng dự phòng “Sóng Mây xin lỗi, chờ chút nhé”'),
                ('gen', 'Gọi anh Tuấn khởi động máy phát điện'), ('check', 'Kiểm lại bàn trộn và mic trước khi quay lại sóng'),
                ('say', 'Lên sóng xin lỗi thính giả, nói rõ vì sao gián đoạn'), ('log', 'Ghi sổ sự cố: giờ mất điện, giờ có lại')]
OUTAGE_CAUSES = [
    'Đang đọc dở thì cả phòng thu tối om: cột điện đầu hẻm vừa bị xe tải quẹt.',
    'Sét đánh gần cột phát, cầu dao tổng nhảy, tai nghe im bặt.',
    'Điện lực cắt điện đột xuất để sửa đường dây, không báo trước.',
    'Con chuột cắn đứt dây nguồn sau tủ máy, đèn ĐANG PHÁT SÓNG tắt phụt.',
    'Ông hàng xóm cắm máy hàn chung đường điện, cả dãy nhà sập cầu dao.',
]

# ---------------------------------------------------------------- 📰 Bản tin phường
# id, text, kind: urgent (an alert) > service (a public service) > event; rumor and ad never go into a bulletin.
NEWS = {
    'urgent': [('bao', 'Cảnh báo áp thấp nhiệt đới: chiều nay mưa to, gió giật cấp 7, bà con chằng chống nhà cửa'),
               ('dien', 'Điện lực báo cúp điện khu chợ từ 13 giờ đến 16 giờ để thay trạm biến áp'),
               ('ngap', 'Đường Bến Mây ngập nửa bánh xe, tổ dân phố đề nghị đi đường vòng qua cầu gỗ'),
               ('nuoc', 'Nhà máy nước báo nước yếu cả phường từ 22 giờ đêm nay đến 5 giờ sáng'),
               ('lua', 'Phòng cháy chữa cháy nhắc: tuyệt đối không đốt vàng mã dưới đường dây điện')],
    'service': [('tiem', 'Trạm y tế phường tiêm chủng cho trẻ dưới 5 tuổi sáng thứ bảy, nhớ mang sổ tiêm'),
                ('rac', 'Lịch thu gom rác cồng kềnh đổi sang tối thứ tư hằng tuần'),
                ('giay', 'Bộ phận một cửa phường nhận hồ sơ cả sáng thứ bảy trong tháng này'),
                ('hoc', 'Thư viện phường mở lớp đọc sách miễn phí cho thiếu nhi chiều chủ nhật')],
    'event': [('vannghe', 'Đêm văn nghệ tổ dân phố số 3 diễn ra tối chủ nhật ở sân nhà văn hóa'),
              ('cho', 'Phiên chợ quê cuối tháng có thêm gian hàng nông sản sạch'),
              ('bong', 'Giải bóng đá thiếu nhi phường khai mạc sáng chủ nhật ở sân trường'),
              ('trang', 'Tổ phụ nữ phường hướng dẫn làm lồng đèn cho các cháu tối thứ sáu')],
    'rumor': [('don1', 'Nghe nói tuần sau phường giải tỏa cả dãy nhà mặt tiền (chưa ai xác nhận)'),
              ('don2', 'Có người kể uống nước lá ổi khỏi hẳn tiểu đường, bà con nên thử'),
              ('don3', 'Tin nhắn lan truyền: ngân hàng phát tiền cho ai bấm vào đường dẫn')],
    'ad': [('qc1', 'Tiệm vàng Kim Hạnh giảm giá công chế tác, mời bà con ghé ngay'),
           ('qc2', 'Quán nhậu Ba Khía khai trương, bia mua một tặng một suốt tuần'),
           ('qc3', 'Nhận làm đẹp tại nhà, gọi ngay để được giá tốt')],
}
READ_ORDER = ('urgent', 'service', 'event')
JINGLE = (8, 10, 12)       # seconds of the bulletin's jingle
PER_ITEM = (20, 25, 30)    # seconds a news item takes to read
SIGN_OFF = (5, 10, 15)     # seconds of the closing line
# (the news item tonight's bulletin must carry for this to happen, or None; situation, right, wrongs)
BULLETIN_FIX = [
    ('dien', 'Bà Tư chạy vào giơ tờ giấy: giờ cúp điện khu chợ đổi từ 13 giờ sang 14 giờ, mà bạn vừa đọc xong tin đó.',
     'Cuối bản tin đọc đính chính: “Xin đính chính, khu chợ cúp điện từ 14 giờ”, rồi ghi vào sổ',
     ('Thôi kệ, ai nghe nhầm thì chịu', 'Đọc lại cả bản tin từ đầu, bỏ khung quảng cáo', 'Sửa trong sổ, không nói lên sóng')),
    ('ngap', 'Bạn vừa đọc nhầm “đường Bến Mây” thành “đường Bến Mới” trong tin ngập nước.',
     'Nói ngay: “Xin lỗi, xin đọc lại cho đúng: đường Bến Mây”, rồi đọc tiếp',
     ('Đọc tiếp như không có gì', 'Tắt mic, mở một bài hát cho qua', 'Cười trừ trên sóng rồi đọc tiếp')),
    ('tiem', 'Chị Hoa giơ bảng qua lớp kính: tin tiêm chủng mới đổi sang chiều thứ bảy.',
     'Đọc tin theo giờ mới chị Hoa ghi, nói rõ “lịch mới cập nhật”',
     ('Đọc theo giờ cũ đã in sẵn cho đúng kịch bản', 'Đọc cả hai giờ để bà con tự chọn', 'Bỏ hẳn tin đó cho chắc')),
    ('ngap', 'Một thính giả nhắn vào đài: “Đọc tin ngập nhanh lên, đang kẹt xe ngoài đó!”',
     'Giữ đúng thứ tự bản tin, đọc tin ngập nước rõ ràng, nhắc lại đường vòng ở cuối bản tin',
     ('Bỏ hết tin khác, chỉ đọc tin ngập', 'Đọc nhanh gấp đôi cho xong', 'Đọc tên người nhắn lên sóng để cảm ơn')),
    (None, 'Đang bản tin thì ông Lực gõ cửa kính, đòi chen quảng cáo tủ lạnh vào giữa tin cảnh báo.',
     'Ra hiệu chờ, đọc hết bản tin; quảng cáo vào đúng khung quảng cáo sau bản tin',
     ('Ngắt tin cảnh báo, đọc quảng cáo trước', 'Đọc quảng cáo xen giữa hai tin cho ông vui', 'Bỏ khung quảng cáo của ông hôm nay')),
]

# ---------------------------------------------------------------- 📢 Quảng cáo nhà tài trợ
SPONSORS = [('lucphat', 'Điện máy Lực Phát', 'tủ lạnh'), ('banam', 'Sữa đậu nành Bà Năm', 'sữa đậu'),
            ('kimhanh', 'Tiệm vàng Kim Hạnh', 'nhẫn cưới'), ('canhdieu', 'Nhà sách Cánh Diều', 'sách giáo khoa'),
            ('gaomay', 'Gạo Mây Trắng', 'gạo mới'), ('xedap', 'Xe đạp Gió Lành', 'xe đạp trẻ em')]
# The slip's speaker: Ông Lực for his own shop; any other sponsor's slip is handed over by Chị Hoa (the sponsor is not a
# person of the station, and the spot never calls them "ông": bà Năm is a woman). The spot's words say "nhà tài trợ".
SPONSOR_NPC = dict(lucphat=2, banam=0, kimhanh=0, canhdieu=0, gaomay=0, xedap=0)
# A script's lines: ok ones a spot may say, and claims the station never reads (misleading, unprovable, frightening).
SPOT_OK = ['Giảm 10% cho khách mua trong tuần này', 'Giao hàng tận nhà trong phường', 'Mở cửa từ 7 giờ sáng đến 9 giờ tối',
           'Có chỗ để xe trước cửa', 'Đổi trả trong 7 ngày nếu còn hóa đơn', 'Ghé xem hàng không mua cũng được']
SPOT_BAD = ['Tốt nhất thế giới, không đâu sánh bằng', 'Dùng là khỏi bệnh, không cần đi bác sĩ', 'Rẻ nhất Việt Nam, ai rẻ hơn đền gấp mười',
            'Ai không mua sẽ hối hận cả đời', 'Bác sĩ khuyên dùng hằng ngày (chưa có giấy tờ)', 'Chỉ còn 5 cái cuối cùng (tuần nào cũng nói vậy)']
WORDS_PER_S = (2, 3)       # reading speed the station uses, words a second
SPONSOR_JINGLE = (3, 4, 5)
SPOT_DEMANDS = [
    ('Nhà tài trợ gọi điện: “Đọc tên cửa hàng năm lần liên tục cho người ta nhớ!”',
     'Giữ đúng hợp đồng (tên đọc hai lần), mời nhà tài trợ báo chị Hoa nếu muốn đổi hợp đồng',
     ('Đọc năm lần cho nhà tài trợ vui', 'Đọc mười lần, tặng thêm', 'Cúp máy, không đọc nữa')),
    ('Nhà tài trợ đòi đọc nhanh gấp đôi để nhét thêm ba câu vào spot 30 giây.',
     'Đọc đúng tốc độ của đài; bớt câu hoặc mua thêm thời lượng, báo chị Hoa',
     ('Đọc như súng liên thanh cho đủ chữ', 'Tự kéo spot dài ra, lấn sang bản tin', 'Bỏ nhạc hiệu nhà tài trợ cho đủ giờ')),
    ('Nhà tài trợ muốn bạn đọc bằng giọng hét thật to “như ngoài chợ”.',
     'Đọc rõ, vui, đúng âm lượng chuẩn của đài; không hét vào mic',
     ('Hét sát mic cho đúng ý khách', 'Vặn hết cỡ cần gạt âm lượng', 'Nhờ anh Tuấn mở còi xe trước khi đọc')),
    ('Phút chót, nhà tài trợ đòi đọc thêm câu chê cửa hàng đối thủ bên kia đường.',
     'Không đọc câu chê đối thủ; chỉ đọc nội dung đã duyệt',
     ('Đọc nhỏ giọng cho đỡ lộ', 'Đọc nhưng không nói tên đối thủ, chỉ tả nhà', 'Đọc, rồi xin lỗi đối thủ sau')),
    ('Nhà tài trợ đòi phát quảng cáo trong lúc đọc tin cảnh báo bão “vì lúc đó đông người nghe”.',
     'Từ chối chen vào tin khẩn; đặt spot ở khung quảng cáo kế tiếp',
     ('Chen vào giữa tin bão một lần thôi', 'Bỏ tin bão, phát quảng cáo trước', 'Đọc tin bão nhanh để kịp quảng cáo')),
]

# ---------------------------------------------------------------- 💌 Lời chúc thính giả
WISH_OK = [('sn', 'Chúc mừng sinh nhật ông Tám 80 tuổi, con cháu chúc ông mạnh khỏe'),
           ('cuoi', 'Chúc anh Duy và chị Thảo trăm năm hạnh phúc'),
           ('thi', 'Chúc cả lớp 9A thi vào lớp 10 thật tốt'),
           ('me', 'Con chúc mẹ ở quê luôn vui, Tết này con về'),
           ('co', 'Cả xóm cảm ơn cô Ba gánh xôi đã nấu cơm cho đội cứu hộ hôm ngập'),
           ('ban', 'Chúc bạn Na đi du học bình an, nhớ gọi về')]
WISH_BAD = [('sdt', 'Ai cần mua đất liên hệ 0903 xxx xxx, giá tốt bất ngờ', 'Có số điện thoại, quảng cáo bán đất'),
            ('che', 'Gửi thằng Tí lớp 8B: mày học dốt nhất lớp, cả trường biết', 'Bêu riếu, xúc phạm một em học sinh'),
            ('dc', 'Gửi người yêu cũ ở số 12 hẻm 7, tên thật là Nguyễn Văn K., tôi chưa quên đâu', 'Lộ địa chỉ, tên thật của người khác'),
            ('link', 'Vào trang muabanmay.vn nhận quà miễn phí, nhanh tay nhé', 'Có đường link lạ')]
WISH_TIMES = ('18:52', '19:03', '19:10', '19:18', '19:26', '19:34', '19:41')
NAME_ASK = [
    ('Nguyen Thi Hue', ('Huế', 'Huệ', 'Hụê')), ('Tran Van Tung', ('Tùng', 'Tụng', 'Tửng')),
    ('Le Thi Nga', ('Nga', 'Ngà', 'Ngã')), ('Pham Duc Hai', ('Hải', 'Hai', 'Hài')),
    ('Vo Thanh Tam', ('Tâm', 'Tám', 'Tấm')), ('Do Minh Tri', ('Trí', 'Trị', 'Trì')),
]
# (the wish it slips on, which tonight's box must carry; situation, right, wrongs)
WISH_SLIPS = [
    ('sn', 'Bạn lỡ đọc “chúc ông Tám 80 tuổi” thành “chúc ông Tám 18 tuổi”, cả phòng máy bật cười.',
     'Xin lỗi ngay trên sóng, đọc lại cho đúng: “ông Tám 80 tuổi”',
     ('Cười theo rồi đọc tiếp', 'Tắt mic, mở bài hát cho qua', 'Nói người gửi viết sai')),
    ('cuoi', 'Bạn đọc nhầm tên “chị Thảo” thành “chị Thủy” trong lời chúc đám cưới.',
     'Xin lỗi cô dâu chú rể, đọc lại lời chúc với đúng tên “chị Thảo”',
     ('Thôi, ai cũng hiểu mà', 'Đọc lại cả chương trình từ đầu', 'Đổi sang lời chúc khác cho khỏi ngại')),
    ('thi', 'Bạn đọc “lớp 9A” thành “lớp 9B”, mấy phút sau cả lớp 9A gọi điện vào đài.',
     'Cảm ơn các em đã gọi, xin lỗi và đọc lại lời chúc gửi đúng lớp 9A',
     ('Bảo các em đừng gọi nữa, đang bận', 'Đọc lời chúc cho cả 9A lẫn 9B cho công bằng', 'Bỏ qua, chương trình đã sang mục khác')),
    ('me', 'Bạn đọc “Tết này con về” thành “Tết này con không về”, mấy phút sau mẹ ở quê gọi lên đài hỏi.',
     'Xin lỗi ngay trên sóng, đọc lại cho đúng: “Tết này con về”',
     ('Bảo bà cụ nghe nhầm', 'Đọc tiếp lời chúc khác cho qua', 'Tắt mic, mở một bài hát')),
    ('co', 'Bạn đọc “cô Ba gánh xôi” thành “cô Bảy gánh xôi”, cả xóm nhắn vào đài.',
     'Xin lỗi cô Ba và cả xóm, đọc lại lời cảm ơn với đúng tên “cô Ba”',
     ('Cô Ba hay cô Bảy cũng vậy thôi', 'Nói người gửi viết khó đọc', 'Bỏ qua, chương trình đã sang mục khác')),
    ('ban', 'Bạn đọc “chúc bạn Na” thành “chúc bạn Nga” trong lời chúc đi du học.',
     'Xin lỗi, đọc lại lời chúc với đúng tên “bạn Na”',
     ('Thôi, Na hay Nga ai cũng hiểu', 'Đọc lời chúc cho cả Na lẫn Nga', 'Cười trừ trên sóng rồi đọc tiếp')),
]

# ---------------------------------------------------------------- 🎵 Khách gọi xin bài
# Songs of the station's library (all fictional): id, title, artist, genre, length in seconds, a line of the lyrics, may air?
SONGS = [
    ('mua_ton', 'Mưa trên mái tôn', 'Thu Hà', 'bolero', 245, 'mưa rơi trên mái tôn, nhớ người xa', True),
    ('pho_den', 'Phố lên đèn', 'Nhóm Gió Nam', 'pop', 212, 'phố lên đèn, mình chung lối về', True),
    ('mua_xuan', 'Mùa xuân trên bến', 'Minh Khang', 'trữ tình', 268, 'xuân về bên bến sông Mây', True),
    ('ca_dao', 'Ca dao mẹ hát', 'Bé Ngọc', 'thiếu nhi', 154, 'ầu ơ ví dầu, mẹ ru con ngủ', True),
    ('dem_sao', 'Đêm đầy sao', 'Lam Phương Vy', 'ballad', 236, 'đêm đầy sao, anh đợi em', True),
    ('xe_dap', 'Chiếc xe đạp cũ', 'Ba Duy', 'pop', 198, 'xe đạp cũ chở em qua cầu', True),
    ('song_que', 'Sông quê', 'Thu Hà', 'trữ tình', 284, 'sông quê chảy mãi về xuôi', True),
    ('nhay_di', 'Nhảy đi nào', 'KIWIZ', 'k-pop', 187, 'nhảy đi nào, đừng ngại ngần', True),
    ('tinh_lo', 'Tình lỡ (bản thu lậu)', 'Không rõ', 'ballad', 241, 'bản thu từ điện thoại, rè cả bài', False),
    ('remix_x', 'Remix nhà bên', 'DJ Vô Danh', 'remix', 230, 'lời có chữ chửi thề ở điệp khúc', False),
]
SONG_ASKS = {
    'mua_ton': 'Bài gì mà có câu “mưa rơi trên mái tôn” ấy, giọng nữ, nhạc buồn buồn',
    'pho_den': 'Bài của một nhóm nhạc nam, có câu “phố lên đèn”, nghe vui vui',
    'mua_xuan': 'Bài trữ tình về mùa xuân, có nhắc bến sông Mây',
    'ca_dao': 'Bài thiếu nhi có tiếng “ầu ơ ví dầu” cho cháu tôi ngủ',
    'dem_sao': 'Bài ballad có câu “anh đợi em” dưới trời sao',
    'xe_dap': 'Bài pop có câu chở em qua cầu bằng xe đạp',
    'song_que': 'Bài của ca sĩ Thu Hà mà về sông quê, không phải bài mưa',
    'nhay_di': 'Bài nhảy của nhóm KIWIZ, điệp khúc “nhảy đi nào”',
}
NO_AIR = [
    ('Bé Su đòi bài “Tình lỡ” bản thu lậu trên mạng, nghe rè cả bài.',
     'Xin lỗi em, bài đó chưa có bản quyền phát sóng; gợi ý một bài ballad cùng kiểu có trong kho',
     ('Mở luôn từ điện thoại của em qua mic', 'Tìm bản lậu trên mạng phát cho nhanh', 'Cúp máy không giải thích')),
    ('Một khách đòi mở “Remix nhà bên”, điệp khúc có chữ chửi thề.',
     'Từ chối nhẹ nhàng vì lời không phù hợp phát sóng; mời chọn bài remix khác trong kho',
     ('Mở nhưng vặn nhỏ đoạn điệp khúc', 'Mở cho vui, khuya rồi ít người nghe', 'Tự hát thay đoạn có chữ chửi')),
    ('Cô Ba đòi bài “mà con gái tôi hát trong đám cưới hôm trước”, đài chưa có bản thu nào.',
     'Nói thật là đài chưa có bản thu; xin tên bài để tìm bản chính thức, hôm nay mời nghe một bài khác',
     ('Mở đại một bài nào đó, nói là bài đó', 'Bảo cô hát qua điện thoại rồi phát luôn', 'Hứa mai có rồi quên luôn')),
]
SHOW_LEFT = (300, 330, 360, 390, 420)   # seconds until the news at the top of the hour
REQUEST_ODD = [
    ('Cô Ba đòi mở bài “Ca dao mẹ hát” ba lần liên tục cho cháu ngủ.',
     'Mở một lần, cảm ơn cô; hẹn mở lại cuối chương trình nếu còn giờ',
     ('Mở ba lần liên tục, các thính giả khác chịu khó', 'Từ chối luôn, không mở bài nào', 'Mở bản tua nhanh cho đủ ba lần')),
    ('Bé Su xin DJ tự hát bài đó trên sóng vì “anh hát hay hơn ca sĩ”.',
     'Cảm ơn em, DJ không hát thay ca sĩ; mở bản thu chính thức của bài',
     ('Hát luôn cho em vui', 'Hát với giọng chọc ghẹo', 'Bảo em tự hát qua điện thoại')),
    ('Một khách xin bài kèm lời nhắn có tên đầy đủ và địa chỉ nhà người yêu cũ.',
     'Mở bài nhưng chỉ đọc lời nhắn chung chung, không đọc tên đầy đủ hay địa chỉ của ai',
     ('Đọc nguyên văn cho đúng ý khách', 'Đọc tên nhưng bỏ số nhà', 'Không mở bài, cúp máy')),
    ('Chú Hùng xin bài rồi dặn: “Tua qua đoạn dạo nhạc, tôi chỉ nghe điệp khúc thôi!”',
     'Mở trọn bài như mọi thính giả; mời chú nghe phần điệp khúc ở phút thứ nhất',
     ('Tua thẳng tới điệp khúc', 'Chỉ phát điệp khúc rồi tắt', 'Phát hai lần điệp khúc cho chú')),
]

# ---------------------------------------------------------------- ☎️ Thính giả gọi vào sóng
CALL_FIRST = [
    ('Chú Hùng vừa được nối máy, câu đầu tiên đã chửi thề. Đài có độ trễ phát sóng 7 giây.',
     'Bấm nút XÓA TRỄ trong 7 giây để câu đó không lên sóng, rồi chuyển máy về hàng chờ',
     ('Để nguyên, cho thính giả nghe cho biết', 'Chửi lại cho chú biết điều', 'Tắt cả đài 5 phút')),
    ('Một người gọi vào, giọng lè nhè, bắt đầu hát karaoke vào điện thoại.',
     'Cảm ơn nhẹ nhàng, giữ máy ở hàng chờ, mời người gọi kế tiếp lên sóng',
     ('Để người đó hát hết bài', 'Chê giọng hát trên sóng', 'Cúp máy giữa câu hát rồi cười')),
    ('Một em bé gọi nhầm, khóc: “Con muốn gặp mẹ.” Mẹ em là người bán hàng gần đài.',
     'Tắt đường gọi khỏi sóng, hỏi tên mẹ và chỗ bán, nhờ anh Tuấn chạy ra báo',
     ('Để em nói trên sóng cho cả phố giúp', 'Cúp máy vì gọi nhầm', 'Hỏi địa chỉ nhà em đọc lên sóng')),
    ('Một người gọi vào chỉ “alo alo” rồi cười khúc khích, lần thứ ba trong buổi.',
     'Không đưa lên sóng nữa, ghi số máy vào sổ gọi phá, nối máy người tiếp theo',
     ('Đọc số điện thoại người đó lên sóng', 'Mắng người đó trên sóng', 'Cho lên sóng thêm lần nữa xem sao')),
]
CALL_GRIPES = [
    ('Thính giả chê: “Nhạc đài dạo này dở ẹc, toàn bài cũ!”',
     'Cảm ơn góp ý, hỏi bác thích bài gì, hứa ghi vào sổ chọn nhạc tuần sau',
     ('Nói nhạc cũ mới hay, ai chê là không biết nghe', 'Im lặng cho qua', 'Đổi ngay sang nhạc remix cho vui')),
    ('Thính giả chê giọng đọc của bạn “ngủ gật”.',
     'Cảm ơn, nhận góp ý, đọc phần tiếp theo tươi tỉnh hơn',
     ('Cãi lại là giọng mình chuẩn rồi', 'Đọc giọng hét để chứng minh', 'Nhờ người khác đọc thay luôn')),
    ('Thính giả trách: “Hôm qua gọi xin bài mà không mở!”',
     'Xin lỗi, hỏi lại tên bài; có trong kho thì xếp mở trong chương trình hôm nay',
     ('Nói hôm qua không phải ca của mình', 'Hứa mở rồi không ghi lại', 'Mở ngay, chen ngang bài đang phát')),
]
CALL_OFFTOPIC = [
    ('Người gọi tiếp theo giới thiệu “cơ hội làm giàu”, mời cả phố tham gia đóng tiền.',
     'Cảm ơn, đài không nhận quảng cáo qua cuộc gọi; cắt khỏi sóng, mời người kế tiếp',
     ('Để họ nói hết cho công bằng', 'Hỏi thêm cách đóng tiền trên sóng', 'Hứa đọc lại số tài khoản của họ cuối chương trình')),
    ('Người gọi xin đài kêu gọi cả phố chuyển tiền giúp mình, không có giấy tờ gì.',
     'Không kêu gọi chuyển tiền trên sóng; hướng dẫn họ liên hệ hội chữ thập đỏ phường',
     ('Đọc số tài khoản của họ lên sóng', 'Kêu gọi giúp, giấy tờ tính sau', 'Mắng họ lừa đảo trên sóng')),
    ('Người gọi đòi đài nói xấu nhà hàng xóm “vì họ đỗ xe trước cửa nhà tôi”.',
     'Không nói chuyện riêng của ai trên sóng; gợi ý báo tổ dân phố hòa giải',
     ('Cho người đó kể hết trên sóng', 'Đọc tên nhà hàng xóm để họ biết', 'Hứa mai đài sẽ lên tiếng giúp')),
]
CALL_LOG = [('time', 'Giờ gọi vào', True), ('topic', 'Nội dung tóm tắt', True), ('dump', 'Đã bấm xóa trễ hay chưa', True),
            ('name', 'Tên người gọi tự xưng', True), ('phone_air', 'Đọc số điện thoại người gọi lên sóng', False),
            ('quote', 'Chép nguyên văn câu chửi lên bảng tin của đài', False), ('ignore', 'Không ghi gì, cho nhanh', False)]

# ---------------------------------------------------------------- 🎚️ Xếp chương trình ca nhạc
SEGMENTS = [('jingle_in', 'Nhạc hiệu mở chương trình'), ('open_song', 'Một bài vui mở màn'), ('ads', 'Khung quảng cáo'),
            ('requests', 'Bài theo yêu cầu thính giả'), ('wishes', 'Đọc lời chúc'), ('jingle_out', 'Nhạc hiệu kết chương trình')]
SHOW_MIN = (20, 25, 30)    # minutes of the show
ADS_S = 60                 # two ad breaks of 30 seconds each
GUEST_ODD = [
    ('Ca sĩ khách mời báo tới trễ 10 phút, chương trình đã bắt đầu.',
     'Phát thêm bài dự phòng, báo thính giả “khách mời đang trên đường”, dời phần phỏng vấn xuống sau',
     ('Để sóng im chờ ca sĩ', 'Nói ca sĩ không tới, hủy phần phỏng vấn', 'Tự phỏng vấn mình cho đủ giờ')),
    ('Khách mời đòi đọc quảng cáo quán nhậu của mình ngay trong phần phỏng vấn.',
     'Nhắc khéo phần phỏng vấn không quảng cáo; quảng cáo phải mua khung và qua chị Hoa duyệt',
     ('Cho đọc một lần thôi', 'Tự đọc giúp quảng cáo cho thân', 'Cắt luôn phần phỏng vấn')),
    ('Khách mời tới nơi, người nồng mùi rượu, nói to và lè nhè.',
     'Mời khách ngồi phòng chờ uống trà, báo chị Hoa, hôm nay phát bài thu sẵn thay phần phỏng vấn',
     ('Cứ cho lên sóng, khuya rồi', 'Cãi nhau với khách ở cửa phòng thu', 'Cho khách lên rồi vặn nhỏ mic')),
    ('Khách mời đòi tăng tiền thù lao ngay trên sóng trước cả phố.',
     'Cảm ơn, hẹn bàn chuyện thù lao với chị Hoa sau chương trình; chuyển sang bài hát',
     ('Hứa trên sóng sẽ trả gấp đôi', 'Cãi lại trên sóng', 'Đưa luôn tiền túi cho khách')),
]

# ---------------------------------------------------------------- desk surprises (kit.desk): chuyện ở đài
DESK = [
    dict(id='cat', title='Con mèo nhảy lên bàn trộn âm', emoji='🐈', npc=1, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Con mèo mướp của anh Tuấn nhảy phóc lên bàn trộn âm, đuôi quét qua dãy cần gạt đang mở.',
         options=[dict(id='bed', label='Bật băng nhạc chờ, bế mèo ra khỏi phòng thu, kéo các cần gạt về đúng mức rồi quay lại sóng', hint='',
                       effects=dict(xp=5, review=[5, 'Nghe đài thấy có tiếng mèo kêu một cái rồi nhạc vang lên ngay, dễ thương ghê.']), good=True,
                       outcome='Thính giả gọi vào hỏi tên con mèo. Từ hôm đó nó thành “mèo trực đài”.'),
                  dict(id='shout', label='Hét đuổi mèo ngay trên sóng', hint='', effects=dict(review=[2, 'Đang nghe nhạc thì nghe đài hét toáng lên, giật cả mình.']), good=False,
                       outcome='Mèo hoảng, gạt tung cần âm lượng, cả phố nghe một tiếng rít chói tai.'),
                  dict(id='leave', label='Kệ nó, nó nằm im mà', hint='', effects=dict(patience=-2), good=None,
                       outcome='Mèo nằm đè lên nút micro khách, tiếng gừ gừ lên sóng suốt hai phút.')],
         default='leave'),
    dict(id='cake', title='Thính giả mang bánh tới tận đài', emoji='🎂', npc=3, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Cô Ba gõ cửa phòng thu, cầm hộp bánh: “Đài mở bài cho cháu cô thi đậu, cô cảm ơn cả đài!”',
         options=[dict(id='thanks', label='Bật nhạc chờ, ra cửa nhận bánh, cảm ơn cô trên sóng và chia cả đài', hint='',
                       effects=dict(xp=5, review=[5, 'Đài nhắc tên cháu tôi trên sóng, cả nhà vui lắm.']), good=True,
                       outcome='Cả phòng máy ăn bánh, cô Ba hứa mai lại gọi xin bài.'),
                  dict(id='in', label='Mời cô vào hẳn phòng thu nói chuyện khi mic đang mở', hint='', effects=dict(review=[3, 'Nghe đài thấy tiếng sột soạt, tiếng cười nói lung tung.']), good=False,
                       outcome='Tiếng hộp bánh sột soạt và tiếng cô cười át cả bài hát.'),
                  dict(id='no', label='Không nhận, đang trong giờ phát', hint='', effects=dict(patience=-1), good=None,
                       outcome='Cô Ba để hộp bánh ở phòng bảo vệ, hơi tủi thân.')],
         default='no'),
    dict(id='leak', title='Mưa dột ngay trên tủ máy', emoji='🌧️', npc=1, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Trời mưa to, nước nhỏ từng giọt xuống nóc tủ máy phát, ngay cạnh ổ cắm điện.',
         options=[dict(id='safe', label='Báo anh Tuấn ngắt điện tủ phụ, che bạt, chuyển sang máy dự phòng rồi mới phát tiếp', hint='',
                       effects=dict(xp=6), good=True,
                       outcome='Tủ máy khô ráo, sóng chỉ ngắt mười giây. Mai thợ lên lợp lại mái.'),
                  dict(id='bucket', label='Đặt cái xô lên nóc tủ hứng nước, phát tiếp', hint='', effects=dict(review=[2, 'Đài rè rè, tiếng lụp bụp như nước nhỏ.', 3]), good=False,
                       outcome='Xô tràn, nước chảy vào ổ cắm, cầu dao nhảy, sóng tắt nửa tiếng.'),
                  dict(id='ignore', label='Mưa chút rồi tạnh, kệ', hint='', effects=dict(patience=-2), good=None,
                       outcome='Tủ máy kêu tách tách cả buổi, anh Tuấn mặt tái xanh.')],
         default='ignore'),
    dict(id='star', title='Người xưng là ca sĩ nổi tiếng gọi vào', emoji='🌟', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một người gọi tới, nói mình là ca sĩ Lam Phương Vy, muốn lên sóng chào khán giả ngay bây giờ.',
         options=[dict(id='verify', label='Cảm ơn, xin số quản lý của ca sĩ để chị Hoa gọi lại xác nhận trước khi lên sóng', hint='',
                       effects=dict(xp=5), good=True,
                       outcome='Hóa ra là Bé Su giả giọng. Lần sau em xin bài đàng hoàng.'),
                  dict(id='air', label='Cho lên sóng luôn, tin người ta', hint='', effects=dict(review=[2, 'Đài để người giả danh ca sĩ lên sóng, kỳ ghê.']), good=False,
                       outcome='Giọng “ca sĩ” vỡ tiếng giữa chừng, cả phố biết là giả.'),
                  dict(id='hang', label='Cúp máy, chắc là trò đùa', hint='', effects=dict(patience=-1), good=None,
                       outcome='Không ai biết có thật hay không, Bé Su cười khúc khích bên kia.')],
         default='hang'),
    dict(id='lostdog', title='Thính giả nhờ đọc tin tìm chó lạc', emoji='🐕', npc=6, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Bà Tư gọi: chú chó Vàng nhà bà đi lạc từ sáng, nhờ đài đọc giúp tin tìm chó.',
         options=[dict(id='read', label='Đọc tin ngắn ở khung tin cộng đồng: màu lông, nơi lạc, nhờ báo về tổ dân phố (không đọc số nhà)', hint='',
                       effects=dict(xp=5, review=[5, 'Đài đọc tin giúp, chiều nay hàng xóm dắt Vàng về rồi!']), good=True,
                       outcome='Một bác xe ôm nghe đài, thấy Vàng ở chợ, dắt về tận nhà.'),
                  dict(id='now', label='Ngắt bài đang phát để đọc ngay', hint='', effects=dict(review=[3, 'Đang nghe bài hay thì đài ngắt ngang đọc tin chó lạc.']), good=False,
                       outcome='Tin đọc vội, quên cả màu lông. Thính giả gọi vào hỏi lại cả buổi.'),
                  dict(id='no', label='Đài không đọc tin riêng', hint='', effects=dict(patience=-2), good=None,
                       outcome='Bà Tư tự đi dán giấy khắp hẻm.')],
         default='no'),
    dict(id='mic', title='Mic khách rè rè giữa phỏng vấn', emoji='🎤', npc=1, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Đang phỏng vấn khách mời, mic khách rè rè rồi hú lên một tiếng dài.',
         options=[dict(id='swap', label='Hạ cần mic khách, đưa mic dự phòng, xin lỗi thính giả rồi hỏi tiếp', hint='',
                       effects=dict(xp=5), good=True,
                       outcome='Tiếng hú tắt ngay, khách mời đùa “mic cũng muốn hát”.'),
                  dict(id='tap', label='Gõ gõ vào mic xem còn chạy không', hint='', effects=dict(review=[2, 'Đài cứ bụp bụp vào tai, đau cả đầu.']), good=False,
                       outcome='Tiếng gõ dội vào loa cả phố, anh Tuấn ôm đầu.'),
                  dict(id='go', label='Kệ, nói to lên là được', hint='', effects=dict(patience=-2), good=None,
                       outcome='Khách mời gân cổ nói, tiếng hú vẫn kéo dài.')],
         default='go'),
    dict(id='quiz', title='Trò chơi có thưởng, hai người cùng đúng', emoji='🎁', npc=0, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Câu đố có thưởng chỉ có một phần quà, mà hai thính giả trả lời đúng cùng một lúc.',
         options=[dict(id='rule', label='Theo thể lệ đã đọc: người gọi vào trước (theo giờ ghi trong sổ) nhận quà, người kia nhận quà khuyến khích', hint='',
                       effects=dict(xp=5, review=[5, 'Đài làm đúng thể lệ, ai cũng phục.']), good=True,
                       outcome='Hai người cười xòa, hẹn tuần sau chơi tiếp.'),
                  dict(id='pick', label='Chọn người quen của đài', hint='', effects=dict(review=[1, 'Đài thiên vị người quen!']), good=False,
                       outcome='Người kia gọi vào phàn nàn cả buổi chiều.'),
                  dict(id='none', label='Không ai nhận cho công bằng', hint='', effects=dict(patience=-2), good=None,
                       outcome='Phần quà nằm trong tủ đài thêm một tuần.')],
         default='none'),
    dict(id='fan', title='Fan đứng chờ ngoài cửa kính', emoji='📸', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Mấy em học sinh dí điện thoại vào cửa kính phòng thu, đòi chụp ảnh với DJ ngay lúc đang đọc.',
         options=[dict(id='later', label='Ra hiệu chờ, đọc xong mục này rồi ra chụp ảnh ở hành lang', hint='',
                       effects=dict(xp=4, review=[5, 'DJ dễ thương, đọc xong ra chụp ảnh với tụi em liền.']), good=True,
                       outcome='Ảnh chụp chung lên mạng, chương trình có thêm cả lớp nghe.'),
                  dict(id='now', label='Mở cửa cho vào phòng thu chụp luôn', hint='', effects=dict(review=[2, 'Đài lẫn tiếng cười đùa, chẳng nghe được gì.']), good=False,
                       outcome='Tiếng cười nói lọt vào mic, bản tin bị cắt ngang.'),
                  dict(id='curtain', label='Kéo rèm che cửa kính', hint='', effects=dict(patience=-1), good=None,
                       outcome='Các em buồn bã ra về.')],
         default='curtain'),
    dict(id='wrongday', title='Kịch bản ghi nhầm ngày lễ', emoji='📅', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Bạn sắp đọc lời chào “mừng Quốc khánh 2/9” thì nhận ra hôm nay không phải ngày đó: kịch bản là bản cũ năm ngoái.',
         options=[dict(id='swap', label='Bỏ đoạn chào cũ, đọc lời chào chung, báo chị Hoa sửa kịch bản', hint='',
                       effects=dict(xp=5), good=True,
                       outcome='Không ai nhận ra, chị Hoa gạch bút đỏ bản cũ và cảm ơn bạn.'),
                  dict(id='read', label='Cứ đọc theo kịch bản, đã duyệt rồi mà', hint='', effects=dict(review=[2, 'Đài chúc mừng nhầm ngày lễ, buồn cười ghê.']), good=False,
                       outcome='Cả phố gọi vào hỏi “hôm nay lễ gì vậy đài?”.'),
                  dict(id='skip', label='Tắt mic, mở nhạc thay lời chào', hint='', effects=dict(patience=-1), good=None,
                       outcome='Chương trình mở đầu hơi cụt.')],
         default='skip'),
    dict(id='neighbor', title='Hàng xóm sang phàn nàn loa đài to', emoji='🔊', npc=5, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Chú Hùng sang tận đài: “Loa phường ngay cửa sổ nhà tôi, sáng nào cũng như sấm!”',
         options=[dict(id='check', label='Cảm ơn chú, nhờ anh Tuấn đo âm lượng loa ở cột đó, chỉnh hướng loa và ghi sổ', hint='',
                       effects=dict(xp=5, review=[5, 'Đài chỉnh loa liền, sáng nay nghe vừa tai.']), good=True,
                       outcome='Loa được xoay về phía đường, chú Hùng hôm sau gọi xin bài.'),
                  dict(id='argue', label='Nói loa phường thì phải to', hint='', effects=dict(review=[2, 'Đài trả lời cộc lốc.']), good=False,
                       outcome='Chú Hùng gọi vào chê đài suốt một tuần.'),
                  dict(id='off', label='Tắt luôn cái loa đó', hint='', effects=dict(patience=-1), good=None,
                       outcome='Cả xóm bên kia không nghe được tin cảnh báo mưa.')],
         default='off'),
]

MILESTONES = [
    dict(id='voice', label='Giọng đọc vững vàng', jobs=15, days=5, roles=1),
    dict(id='both', label='Đọc tin lẫn làm DJ', jobs=60, days=20, roles=2),
    dict(id='soul', label='Giọng nói của Sóng Mây', jobs=160, days=40, roles=2),
]

NOTEBOOK = [
    'Mọi quy định, nhà tài trợ, bài hát và người gọi ở đây là nội dung hư cấu của đài Sóng Mây.',
    'Đầu ca: bật bàn trộn âm, kéo cần về 0 → nói thử mic → đeo tai nghe kiểm tiếng → kiểm đường truyền tới cột phát → bật đèn ĐANG PHÁT SÓNG rồi mới mở mic.',
    'Mất điện giữa sóng: chuyển sang bộ lưu điện → bật băng dự phòng → gọi anh Tuấn khởi động máy phát → kiểm lại bàn trộn, mic → xin lỗi thính giả, nói rõ lý do → ghi sổ sự cố. Sai nhiều bước thì sóng câm lâu, thính giả chê.',
    'Bản tin phường: đọc tin khẩn trước (cảnh báo, cúp điện, ngập), rồi tin dịch vụ công, rồi tin sự kiện. Không đọc tin đồn chưa kiểm chứng, không đọc quảng cáo trong bản tin.',
    'Thời lượng bản tin = nhạc hiệu + số tin × giây mỗi tin + lời chào cuối.',
    'Đọc sai trên sóng: xin lỗi ngay, đọc lại cho đúng. Có đính chính phút chót thì đọc đính chính rõ ràng, rồi ghi sổ.',
    'Quảng cáo: chỉ đọc bản MỚI NHẤT ĐÃ ĐƯỢC CHỊ HOA DUYỆT. Bản gửi qua tin nhắn, đọc qua điện thoại mà chưa duyệt thì chưa đọc.',
    'Không đọc câu quảng cáo phóng đại, không kiểm chứng được hay dọa người nghe (tốt nhất thế giới, khỏi bệnh, rẻ nhất, ai không mua sẽ hối hận…).',
    'Thời lượng spot = số chữ chia tốc độ đọc (làm tròn lên) + nhạc hiệu nhà tài trợ. Giữ đúng hợp đồng: không đọc thêm, không chen vào tin khẩn.',
    'Lời chúc: đọc theo giờ gửi tới, sớm trước muộn sau. Không đọc lời có số điện thoại, đường link, địa chỉ hay tên thật của người khác, lời bêu riếu.',
    'Tên viết không dấu thì gọi lại hỏi đúng dấu, không đọc đại.',
    'Xin bài: tìm theo lời bài, ca sĩ, thể loại khách tả. Bài chưa có bản quyền phát sóng hoặc lời không phù hợp thì xin lỗi và gợi ý bài khác trong kho.',
    'Lời dẫn tối đa = thời gian còn lại tới bản tin − độ dài bài hát (tính bằng giây).',
    'Thính giả gọi vào: đài trễ 7 giây. Câu chửi thề thì bấm XÓA TRỄ ngay. Góp ý thì cảm ơn, bình tĩnh. Không nhận quảng cáo, kêu gọi chuyển tiền, chuyện riêng của ai qua cuộc gọi.',
    'Sổ cuộc gọi: giờ gọi, nội dung tóm tắt, đã xóa trễ hay chưa, tên người gọi tự xưng. Không đọc số điện thoại của ai lên sóng.',
    'Chương trình ca nhạc: nhạc hiệu mở → bài vui mở màn → quảng cáo → bài theo yêu cầu → lời chúc → nhạc hiệu kết. Lời dẫn = tổng thời lượng − các bài − 60 giây quảng cáo.',
    f'Phát thanh viên thử việc {PROBATION} ca đạt (kiểm phòng thu đầu ca, ít nhất một việc đạt từ 90%, mất điện thì xử lý xong) thì làm được DJ ca nhạc buổi tối.',
    '📻 Hàng xóm trong phố đặt quảng cáo tiệm hoặc gửi bài hát tặng người thương ở 🛎️ Phố dịch vụ. Bạn duyệt lời, chọn nhạc rồi bấm Lên sóng: dòng chữ chạy trên bảng tin cả phố trong một khung giờ. Lương ca trả theo hợp đồng khi khép ca.',
]
