"""🎪 Hội chợ việc làm (game/town_fair.py): the words of the fair. Groups of careers, the booths' "trình diễn" (show-off)
acts, the "oái oăm" moments a booth owner answers, the 🎟️ stamp rewards and the booth titles. Nothing here moves money:
a moment's choice only moves the booth's mood (điểm gian hàng, 0–100), a show adds a little, and every reward is a
cosmetic of 🎨 Phong cách (game/spend_content.py FAIR_TITLES / FAIR_FRAMES, granted for good through a live_effects row).
"""
from __future__ import annotations

# ---------------------------------------------------------------- careers into groups (the sheet's filter chips)
GROUPS = (
    ('food', '🍜', 'Ẩm thực'),
    ('shop', '🛍️', 'Cửa hàng'),
    ('service', '💇', 'Dịch vụ'),
    ('office', '💼', 'Văn phòng'),
    ('outdoor', '🌾', 'Ngoài trời'),
)
GROUP_IDS = tuple(g[0] for g in GROUPS)
# the careers the catalogue leaves without a category (game/content.py CATALOG `category`)
GROUP_OF = dict(mother_baby='shop', pharmacy='shop', accounting='office', customer_care='office', teacher='service',
                tour_guide='outdoor', milk_tea='food')

# ---------------------------------------------------------------- 🎭 trình diễn: (id, icon, name, line)
# The booth owner picks one; visitors who watch it while it runs get that career's 🎟️ stamp. One signature act for
# some careers, then three acts of the career's group.
SHOWS = {
    'food': (
        ('tung_chao', '🍳', 'Tung chảo biểu diễn', 'Lửa bùng lên một cái, cả dãy hàng xóm vỗ tay rần rần.'),
        ('moi_nem', '🥢', 'Mời nếm thử', 'Từng miếng nhỏ xíu được chuyền tay nhau, ai cũng gật gù.'),
        ('rao_hang', '📣', 'Rao hàng như chợ quê', 'Giọng rao ngân nga khiến mấy bác lớn tuổi đứng lại nghe.'),
    ),
    'shop': (
        ('xep_hang', '🧺', 'Xếp hàng nghệ thuật', 'Kệ hàng thành một tháp nhỏ, khách đứng chụp ảnh liên tục.'),
        ('goi_qua', '🎁', 'Gói quà siêu tốc', 'Ba mươi giây một hộp quà thắt nơ, đồng hồ bấm giờ hẳn hoi.'),
        ('boc_tham', '🎟️', 'Bốc thăm vui', 'Ai bốc trúng ô hình ngôi sao được một lời chúc may mắn.'),
    ),
    'service': (
        ('lam_mau', '✨', 'Làm mẫu tại chỗ', 'Bạn làm thử một lượt cho người xem, từng bước rõ ràng.'),
        ('mach_nho', '💡', 'Mách mẹo nghề', 'Ba mẹo nhỏ ai cũng dùng được, người xem ghi vội vào điện thoại.'),
        ('hoi_dap', '🙋', 'Hỏi gì đáp nấy', 'Năm câu hỏi khó của khách, bạn trả lời gọn từng câu.'),
    ),
    'office': (
        ('go_phim', '⌨️', 'Gõ phím thần tốc', 'Một trang giấy gõ xong trong một phút, không sai dấu nào.'),
        ('xep_ho_so', '🗂️', 'Xếp hồ sơ thần sầu', 'Một chồng giấy lộn xộn thành ba tập gọn gàng, có nhãn hẳn hoi.'),
        ('tinh_nham', '🧮', 'Tính nhẩm đố vui', 'Khách đọc số, bạn nhẩm ra tổng trước cả máy tính.'),
    ),
    'outdoor': (
        ('do_nghe', '🧰', 'Khoe đồ nghề', 'Từng món đồ nghề được giới thiệu như báu vật, có cả chuyện kể.'),
        ('thu_suc', '💪', 'Thử sức cùng khách', 'Ai bê nổi thùng hàng mẫu được vỗ tay một tràng.'),
        ('ke_chuyen', '🗺️', 'Kể chuyện đi đường', 'Chuyện những ngày mưa gió ngoài đường làm cả nhóm nghe say.'),
    ),
}
CAREER_SHOWS = {
    'pho': ('chan_pho', '🍜', 'Chần phở một tay', 'Bánh phở trụng, nước dùng chan, hành lá rắc đều trong mười giây.'),
    'milk_tea': ('lac_tra', '🧋', 'Lắc trà như bartender', 'Bình lắc bay qua vai rồi rót đúng vạch, trân châu không rơi hạt nào.'),
    'tra_da': ('ke_ghe', '🪑', 'Kê ghế nhựa thần tốc', 'Mười cái ghế nhựa xòe ra một hàng thẳng tắp trong chớp mắt.'),
    'ice_cream': ('nan_kem', '🍦', 'Nặn kem ba tầng', 'Ba viên kem chồng lên nhau, nghiêng mà không đổ.'),
    'cafe_bakery': ('nan_banh', '🥐', 'Nặn bánh hình thú', 'Cục bột thành chú mèo, chú thỏ, trẻ con xếp hàng xin.'),
    'florist': ('bo_hoa', '💐', 'Bó hoa một phút', 'Một bó hoa tròn trịa thành hình ngay trước mặt khách.'),
    'salon': ('tet_toc', '💇', 'Tết tóc xương cá', 'Một kiểu tóc tết xong trong hai phút, người mẫu xoay một vòng.'),
    'nail': ('ve_mong', '💅', 'Vẽ móng tí hon', 'Một bông hoa đào bé xíu nở trên đầu móng tay.'),
    'photobooth': ('chup_nhanh', '📸', 'Chụp ảnh lấy liền', 'Bốn kiểu tạo dáng, một dải ảnh in ra còn ấm.'),
    'pet_care': ('tia_long', '🐩', 'Tỉa lông cún mẫu', 'Chú cún bông thành hình đám mây, chủ nhà cười tít mắt.'),
    'pet_shop': ('cho_an', '🐹', 'Giờ ăn của bé cưng', 'Bé hamster nhai hạt hướng dương, ai cũng cúi xuống nhìn.'),
    'repair': ('sua_dai', '🔧', 'Sửa đài trong năm phút', 'Cái đài cũ rè rè bỗng hát lại một bài nhạc vàng.'),
    'teacher': ('lop_mini', '📚', 'Lớp học năm phút', 'Mấy bé ngồi xếp bằng, học thuộc một bài thơ ngắn.'),
    'pilot': ('bao_cao', '✈️', 'Đọc bản tin cơ trưởng', '“Kính thưa quý khách, chúng ta sắp hạ cánh xuống hội chợ…”'),
    'flight_attendant': ('huong_dan', '🦺', 'Hướng dẫn an toàn', 'Thắt dây, đeo mặt nạ, chỉ lối thoát hiểm, đều tay như thật.'),
    'police': ('chi_duong', '👮', 'Điều khiển giao thông', 'Tiếng còi và cánh tay dứt khoát, dòng khách đi vào nề nếp.'),
    'lifeguard': ('so_cuu', '🛟', 'Sơ cứu đuối nước', 'Thổi còi, kéo phao, ép tim trên hình nộm, ai cũng nín thở.'),
    'nurse': ('do_huyet_ap', '🩺', 'Đo huyết áp miễn phí', 'Từng bác ngồi xuống, nghe dặn dò ăn nhạt, ngủ sớm.'),
    'rescue': ('nghe_may', '📞', 'Nghe máy cấp cứu', 'Một cuộc gọi giả, bạn hỏi đúng bốn câu và điều xe trong ba mươi giây.'),
    'railway': ('ha_chan', '🚦', 'Hạ chắn đúng giờ', 'Còi tàu (thu âm) vang lên, thanh chắn hạ xuống đúng nhịp.'),
    'lighthouse': ('den_bien', '🔦', 'Nháy đèn tín hiệu', 'Ba ngắn, ba dài, ba ngắn: mấy bạn nhỏ thi nhau đoán chữ.'),
    'library': ('tim_sach', '📖', 'Tìm sách trong mười giây', 'Khách đọc tên sách, bạn chỉ đúng kệ, đúng ngăn.'),
    'it_helpdesk': ('cuu_may', '💻', 'Cứu máy treo', 'Một cái laptop treo cứng, ba phím tắt, nó sống lại.'),
    'lawyer': ('tu_van', '⚖️', 'Tư vấn một phút', 'Một câu hỏi về hợp đồng thuê nhà, bạn trả lời gọn, dễ hiểu.'),
    'farm': ('nho_rau', '🥬', 'Nhổ rau cùng bé', 'Mấy bé được cầm cây rau thật, tay lấm đất mà cười tươi.'),
    'delivery': ('xep_hang_xe', '🛵', 'Xếp hàng lên xe', 'Mười gói hàng chồng gọn trên yên xe, buộc dây một vòng là xong.'),
    'pagoda': ('go_mo', '🪷', 'Gõ mõ tụng kinh', 'Tiếng mõ đều đều, cả góc hội chợ bỗng yên ả lạ thường.'),
    'banquet': ('xep_khan', '🍽️', 'Gấp khăn hình thiên nga', 'Chiếc khăn ăn thành con thiên nga, đặt lên đĩa sứ.'),
    'hotel': ('don_phong', '🛏️', 'Dọn giường ba phút', 'Ga trải phẳng phiu, gối xếp thẳng hàng, khăn gấp hình con voi.'),
    'reception': ('check_in', '🛎️', 'Check-in siêu tốc', 'Khách đưa giấy tờ, bạn trao chìa khóa kèm nụ cười trong hai phút.'),
    'zpop': ('nhay_cover', '💿', 'Nhảy cover một đoạn', 'Một đoạn vũ đạo quen thuộc, fan đứng quanh hát theo.'),
    'art_studio': ('ve_chan_dung', '🎨', 'Ký họa chân dung', 'Ba phút một bức ký họa, khách được cầm về làm kỷ niệm.'),
    'post_office': ('dong_dau', '📮', 'Đóng dấu bưu thiếp', 'Tem dán thẳng, dấu đóng rõ, bưu thiếp sẵn sàng gửi đi.'),
}

# ---------------------------------------------------------------- 😵 oái oăm moments: (key, icon, text, choices)
# choice: (id, label, mood delta, what happens). Delta only moves the booth's mood (0–100): no xu, no item.
MOMENTS = (
    ('thu_khong_mua', '🫤', 'Một khách thử hết mấy món mẫu, khen nức nở rồi… đi thẳng sang gian bên cạnh.', (
        ('cuoi', 'Cười, mời lần sau ghé', 4, 'Khách quay lại vẫy tay: “Lần sau ghé thật nha!” Người xem thấy bạn dễ mến.'),
        ('to_roi', 'Đưa tờ rơi, dặn tìm bạn ở Phố dịch vụ', 2, 'Khách nhét tờ rơi vào túi. Biết đâu đấy.'),
        ('cang', 'Nói to “thử thì phải mua chứ!”', -6, 'Cả dãy quay lại nhìn. Gian của bạn mất điểm hẳn.'),
    )),
    ('tre_con_do', '🧒', 'Một bé chạy qua, vướng chân làm đổ cả khay đồ trưng bày.', (
        ('do_be', 'Đỡ bé dậy trước, dọn đồ sau', 6, 'Bé nín khóc, bố mẹ bé cảm ơn rối rít và đứng lại xem gian.'),
        ('goi_bo_me', 'Gọi bố mẹ bé ra nói chuyện', 0, 'Bố mẹ bé xin lỗi, phụ bạn nhặt đồ. Hòa cả làng.'),
        ('quat', 'Quát cho bé sợ', -8, 'Bé khóc ré lên, người đi qua lắc đầu.'),
    )),
    ('mua_bat_chot', '🌧️', 'Mưa bất chợt! Bạt gian hàng bắt đầu dột lách tách.', (
        ('moi_tru', 'Kéo bạt, mời khách trú mưa trong gian', 6, 'Gian chật mà vui, ai cũng ở lại nghe bạn giới thiệu.'),
        ('dong_tam', 'Đóng tạm gian, chờ tạnh', -2, 'Mười phút vắng tanh. Tạnh mưa thì khách đã sang gian khác.'),
        ('ke', 'Kệ, khách ướt thì thôi', -6, 'Mấy khách ướt sũng bỏ đi, còn kịp ngoái lại nhìn bạn.'),
    )),
    ('nhac_to', '🔊', 'Gian bên cạnh mở loa kẹo kéo hết cỡ, khách không nghe được bạn nói gì.', (
        ('sang_noi', 'Sang nói nhẹ nhàng xin vặn nhỏ', 4, 'Hàng xóm gật đầu, còn mời bạn một ly nước.'),
        ('viet_bang', 'Viết bảng to thay lời rao', 3, 'Tấm bảng chữ to đùng lại hút khách bất ngờ.'),
        ('mo_to_hon', 'Mở loa nhà mình to hơn nữa', -7, 'Hai cái loa đấu nhau, cả dãy bịt tai bỏ đi.'),
    )),
    ('so_gia', '🧾', 'Khách giơ điện thoại so giá: “Gian kia rẻ hơn chút xíu đó nha.”', (
        ('giai_thich', 'Giải thích chỗ khác biệt, không chê ai', 4, 'Khách gật gù: “Nghe hợp lý ghê.”'),
        ('chuc', 'Cười, chúc khách chọn được chỗ ưng', 2, 'Khách thấy thoải mái, hứa sẽ quay lại xem.'),
        ('che', 'Chê gian kia làm ẩu', -6, 'Chủ gian kia nghe thấy. Không khí cả dãy chùng xuống.'),
    )),
    ('cup_dien', '💡', 'Cúp điện cả dãy hội chợ, đèn và quạt tắt phụt.', (
        ('den_pin', 'Bật đèn pin điện thoại, làm tiếp', 5, 'Gian bạn là chỗ sáng nhất dãy, khách kéo tới xem.'),
        ('ke_chuyen', 'Mời khách ngồi nghỉ, kể chuyện nghề', 3, 'Mấy câu chuyện nghề làm ai cũng quên trời nóng.'),
        ('than', 'Than thở với khách suốt', -4, 'Khách nghe một lúc rồi lặng lẽ đi.'),
    )),
    ('gio_bay_bien', '🌬️', 'Gió thổi bay tấm bảng hiệu, nó lăn tới tận cổng hội chợ.', (
        ('chay_nhat', 'Chạy đi nhặt, cảm ơn người giữ hộ', 3, 'Người giữ bảng hóa ra là khách, đi theo bạn về gian.'),
        ('bang_tay', 'Viết bảng tạm bằng bìa các-tông', 2, 'Bảng tay xiêu vẹo mà dễ thương, có người chụp đăng mạng.'),
        ('bo', 'Thôi, không cần bảng', -4, 'Khách đi qua không biết gian bạn làm nghề gì.'),
    )),
    ('livestream', '📱', 'Một bạn đứng ngay trước gian livestream, chắn hết lối khách vào.', (
        ('moi_quay', 'Mời bạn ấy quay luôn gian mình', 5, 'Buổi live có thêm gian của bạn, vài người xem tìm tới.'),
        ('nho_dich', 'Nhờ dịch sang một chút', 2, 'Bạn ấy xin lỗi, dịch sang. Lối vào thông thoáng.'),
        ('giat', 'Đứng chen vào chắn lại', -7, 'Hai người lời qua tiếng lại, cả hội chợ được dịp hóng.'),
    )),
    ('bao_ve', '👮', 'Bác bảo vệ nhắc: kệ hàng của bạn lấn ra lối đi hai gang tay.', (
        ('lui', 'Lùi vào ngay, cảm ơn bác', 3, 'Bác bảo vệ cười, dặn ai hỏi đường thì chỉ sang gian bạn.'),
        ('xin', 'Xin thêm năm phút', -1, 'Bác đứng chờ năm phút, mặt hơi nặng.'),
        ('cai', 'Cãi “gian bên kia còn lấn hơn”', -6, 'Bác ghi tên gian của bạn vào sổ. Ngại ghê.'),
    )),
    ('vi_roi', '👛', 'Khách để quên ví trên bàn gian của bạn rồi đi mất.', (
        ('loa', 'Nhờ ban tổ chức đọc loa tìm chủ', 7, 'Chủ ví chạy lại cảm ơn rối rít, kể với cả nhóm bạn.'),
        ('cat', 'Cất kỹ, chờ khách quay lại', 4, 'Nửa tiếng sau khách quay lại, mừng rỡ.'),
        ('mac', 'Để nguyên trên bàn', -5, 'Cái ví nằm chơ vơ cả buổi, ai đi qua cũng nhìn bạn ái ngại.'),
    )),
    ('cho_chay', '🐕', 'Một chú chó lạc chạy vào gian, đánh hơi khắp nơi.', (
        ('giu_cho', 'Cho uống nước, nhờ loa tìm chủ', 5, 'Chủ chú chó tìm tới, ôm cún, ở lại mua ủng hộ.'),
        ('duoi_nhe', 'Dẫn ra ngoài nhẹ nhàng', 1, 'Chú chó ngoan ngoãn đi theo. Gian sạch sẽ trở lại.'),
        ('hoang', 'Hét toáng lên', -5, 'Chú chó sợ quá chạy vòng vòng, đổ thêm hai món.'),
    )),
    ('chen_ep', '🙋', 'Ba khách cùng hỏi một lúc, ai cũng muốn được trả lời trước.', (
        ('so_thu_tu', 'Phát số thứ tự', 4, 'Ai cũng thấy công bằng, còn khen gian bạn chuyên nghiệp.'),
        ('nhanh', 'Trả lời từng người thật nhanh', 2, 'Hơi cuống nhưng không ai phải chờ lâu.'),
        ('khach_quen', 'Ưu tiên khách quen trước', -4, 'Hai khách lạ bĩu môi bỏ đi.'),
    )),
    ('xin_giam_them', '🤏', 'Khách xin giảm thêm nữa, ngoài giá hội chợ.', (
        ('giu_gia', 'Giữ giá, tặng một lời chúc may mắn', 3, 'Khách bật cười: “Thôi được, chúc lại bạn đông khách!”'),
        ('giai_thich', 'Giải thích giá hội chợ đã giảm rồi', 1, 'Khách gật đầu, hơi tiếc nhưng hiểu.'),
        ('duoi', 'Bảo khách sang chỗ khác', -6, 'Khách kể với cả hội bạn là gian bạn khó tính.'),
    )),
    ('het_to_roi', '🗒️', 'Hết sạch tờ rơi giới thiệu dịch vụ mà khách vẫn còn đông.', (
        ('qr', 'Viết tên mình lên bảng, dặn tìm ở Phố dịch vụ', 4, 'Mấy khách chụp lại tấm bảng. Tiện hơn tờ rơi.'),
        ('mieng', 'Giới thiệu bằng miệng từng người', 2, 'Hơi khàn giọng nhưng ai cũng nhớ tên bạn.'),
        ('thoi', 'Thôi, hết thì nghỉ', -3, 'Khách hỏi mà không có gì cầm về.'),
    )),
    ('chup_anh', '🤳', 'Một nhóm bạn trẻ xin chụp ảnh check-in ở gian mà không mua gì.', (
        ('tao_dang', 'Chỉ chỗ đẹp, tạo dáng cùng', 5, 'Ảnh đăng lên mạng gắn tên gian của bạn, lượt ghé tăng vèo.'),
        ('cho_chup', 'Cho chụp, nhắc đừng làm đổ đồ', 2, 'Nhóm bạn chụp xong cảm ơn, gian vẫn gọn gàng.'),
        ('cam', 'Không cho chụp', -4, 'Nhóm bạn tiu nghỉu, đứng chụp gian bên cạnh.'),
    )),
    ('mc_micro', '🎤', 'MC hội chợ bất ngờ chìa micro: “Gian này có gì đặc biệt?”', (
        ('ngan_gon', 'Giới thiệu ngắn gọn, vui vẻ', 6, 'Cả khu nghe rõ tên gian bạn, vài người đi tới ngay.'),
        ('run', 'Run quá, cười trừ', 0, 'MC đỡ lời giúp bạn. Không sao cả.'),
        ('noi_dai', 'Nói một mạch mười phút', -3, 'MC phải khéo léo lấy lại micro. Khán giả ngáp.'),
    )),
)
MOMENT_INDEX = {m[0]: m for m in MOMENTS}

# ---------------------------------------------------------------- rewards (cosmetics of 🎨 Phong cách, granted for good)
# 🎟️ stamps of different careers in one fair: (stamps needed, style item id)
STAMP_TIERS = ((3, 't_hc_khach'), (6, 'f_hc_den_long'), (10, 't_hc_tho_dia'))
HOST_ITEM = 't_hc_chu_gian'        # a booth that served HOST_SERVED customers in one fair
SERVED_ITEM = 't_hc_dat_khach'     # top TOP of the 🛎️ served board of a fair
RATED_ITEM = 't_hc_duoc_yeu'       # top TOP of the ⭐ booth-score board of a fair
ITEM_IDS = frozenset([x for _, x in STAMP_TIERS] + [HOST_ITEM, SERVED_ITEM, RATED_ITEM])
