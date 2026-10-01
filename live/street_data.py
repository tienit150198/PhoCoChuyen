"""🚶 Đi dạo: the places, the topic cards of the tám chuyện tables, the street vendors' calls, and the ids a
stroller's look and title may use (copies of game/wardrobe.py and game/journey.py TITLES, checked by
tests/test_live_street.py: the live service never imports the game).

Geometry is in world units: every place is 600 × 900 (portrait, phone first; wider screens letterbox it).
`walk` is a list of axis-aligned rectangles (x0, y0, x1, y1) whose union is where people may stand and walk;
nothing outside it is ever a position. Tables: (x, y, seats). Spots: named points other features attach to
(`bench`: phase 3's "Góc hẹn hò", see public/js/v4/walk.js addSpot).
"""
from __future__ import annotations

W, H = 600, 900

PLACES = {
    'boho': dict(
        name='Bờ hồ', icon='🌊',
        walk=[(20, 30, 580, 85), (20, 30, 75, 560), (525, 30, 580, 560), (20, 515, 580, 880)],
        tables=[(130, 720, 4), (470, 720, 3)],
        spots=dict(bench=(300, 565), spawn=(300, 820)),
    ),
    'chodem': dict(
        name='Chợ đêm', icon='🏮',
        walk=[(160, 30, 440, 880), (20, 650, 580, 880)],
        tables=[(115, 765, 4), (485, 765, 3)],
        spots=dict(bench=(300, 700), spawn=(300, 560)),
    ),
    'congvien': dict(
        name='Công viên', icon='🌳',
        walk=[(20, 30, 300, 880), (20, 400, 580, 880)],
        tables=[(150, 290, 4), (450, 760, 3)],
        spots=dict(bench=(455, 470), spawn=(250, 650)),
    ),
    'phodibo': dict(
        name='Phố đi bộ', icon='⛲',
        walk=[(20, 165, 580, 340), (20, 520, 580, 880), (20, 165, 210, 880), (390, 165, 580, 880)],
        tables=[(115, 250, 3), (480, 765, 4)],
        spots=dict(bench=(300, 565), spawn=(300, 720)),
    ),
    # "Rủ đi cà phê": a private room for two, opened from a player's card (never listed, never joined by walk_in)
    'cafe': dict(
        name='Quán cà phê', icon='☕', private=True,
        walk=[(60, 300, 540, 860)],
        tables=[(300, 560, 2)],
        spots=dict(spawn=(300, 770)),
    ),
}
PUBLIC = tuple(k for k, v in PLACES.items() if not v.get('private'))

# Bàn tám chuyện: a card is dealt when someone sits, then every 2 minutes or when everyone taps "đổi chủ đề".
TOPICS = (
    'Hôm nay khách khó nhất là ai? Kể nghe coi 👀',
    'Món ăn vặt đầu hẻm nhà bạn ngon nhất là món gì?',
    'Trà sữa full topping hay trà đá vỉa hè? Chọn một thôi!',
    'Bài hát đang "ám" bạn tuần này là bài gì?',
    'Kể một lần quê xệ nhất mà giờ nghĩ lại vẫn cười.',
    'Nếu được nghỉ phép 1 tuần, bạn xách balo đi đâu liền?',
    'Red flag lớn nhất ở một người đồng nghiệp là gì?',
    'Green flag nào làm bạn quý ai đó ngay lập tức?',
    'Lý do đi trễ "kinh điển" nhất bạn từng dùng?',
    'Crush hồi cấp 3 giờ ra sao rồi? Có ai còn theo dõi không 🙈',
    'Một kỹ năng vô dụng nhưng bạn cực kỳ tự hào?',
    'Nghề mơ ước hồi nhỏ của bạn là gì?',
    'Đi biển hay lên núi? Vì sao?',
    'Món nào bạn nấu ngon nhất (hoặc đỡ dở nhất)?',
    'Tin nhắn "seen không rep" làm bạn đau nhất là của ai?',
    'Nếu trúng số 1 tỷ, việc đầu tiên bạn làm là gì?',
    'Bạn là team ngủ sớm hay team cú đêm?',
    'App nào bạn mở nhiều nhất mỗi ngày? Thú thật đi.',
    'Câu nói của bố mẹ mà giờ bạn thấy... đúng thiệt?',
    'Deadline dí thì bạn xử lý kiểu gì?',
    'Kể một lần bạn "flex" xong bị quê.',
    'Món quà nhỏ nhất mà làm bạn vui nhất?',
    'Nếu khu phố mở thêm một quán, bạn muốn quán gì?',
    'Đồ ăn "bị đánh giá thấp" nhất theo bạn là gì?',
    'Bạn hay sống ảo ở góc nào nhất khu phố?',
    'Một thói quen nhỏ giúp bạn chill mỗi ngày?',
    'Lần gần nhất bạn cười tới đau bụng là vì gì?',
    'Chuyện drama nhất bạn từng chứng kiến ở chỗ làm?',
    'Nếu được đổi nghề 1 ngày, bạn thử nghề gì?',
    'Phim hay series nào bạn cày xuyên đêm gần đây?',
    'Bạn đã từng đu idol nào chưa? Giờ còn đu không?',
    'Cà phê đen đá, bạc xỉu hay muối? Team nào đây?',
    'Một câu cửa miệng của bạn mà bạn bè hay nhại lại?',
    'Bạn sẽ đặt tên quán của mình là gì?',
    'Kỷ niệm Tết đáng nhớ nhất của bạn?',
    'Thứ gì bạn mua xong hối hận liền?',
    'Bạn hay mua đồ online lúc mấy giờ? Đêm khuya đúng không 😏',
    'Nếu có siêu năng lực trong 1 ngày, bạn chọn gì?',
    'Một người lạ từng làm ngày của bạn tốt hơn?',
    'Bạn thuộc team nhắn tin dài hay gửi voice?',
    'Món bánh tráng trộn hay bánh tráng nướng?',
    'Chỗ nào ở phố này bạn thấy "chữa lành" nhất?',
    'Sếp lý tưởng trong mơ của bạn trông như thế nào?',
    'Bạn đã từng bị khách "bom hàng" chưa? Kể nghe với.',
    'Nếu được nuôi một con vật bất kỳ, bạn chọn con gì?',
    'Bạn giữ bình tĩnh thế nào khi gặp người "ô dề"?',
    'Đi ăn chung thì bạn là người chọn quán hay người "gì cũng được"?',
    'Một trend trên mạng bạn thấy hơi bị... cạn lời?',
    'Ngày hoàn hảo của bạn bắt đầu thế nào?',
    'Bạn hay hát karaoke bài gì "trấn phòng"?',
    'Cái tên biệt danh hồi nhỏ của bạn là gì? 😆',
    'Thứ bạn luôn mang theo khi ra đường?',
    'Bạn có tin vào "duyên" gặp người lạ ngoài phố không?',
    'Món ăn nào bạn ăn cả tuần không ngán?',
    'Nếu khu phố có lễ hội riêng, bạn muốn có hoạt động gì?',
    'Lần "toang" nhất trong ngày làm việc của bạn?',
    'Một lời khen bạn nhớ mãi?',
    'Bạn là người hay quên đồ ở đâu nhất?',
    'Bạn từng nhận một yêu cầu "khó đỡ" nào từ khách chưa?',
    'Mùa nào trong năm bạn thích nhất ở phố này?',
    'Bạn hay nghe nhạc gì khi làm việc?',
    'Hàng xóm "lầy" nhất bạn từng gặp?',
    'Nếu viết một quyển sách về đời mình, tựa đề là gì?',
    'Bạn từng đi lạc ở đâu chưa? Kết cục ra sao?',
    'Đồ uống "chân ái" của bạn vào ngày mưa?',
    'Một điều nhỏ làm bạn thấy mình đã "lớn" rồi?',
    'Bạn thường tự thưởng cho mình bằng gì sau ngày dài?',
    'Nếu được mời một người nổi tiếng đi trà đá, bạn mời ai?',
    'Thói quen "báo thủ" nhất của bạn là gì? 😅',
    'Chuyện tình cảm hài hước nhất bạn từng nghe kể?',
    'Một món đồ cũ bạn không nỡ vứt đi?',
    'Bạn nghĩ mình hợp làm nghề gì nhất ở khu phố?',
)

# The little happenings: a street vendor crosses and calls out (one line, the place's own).
VENDORS = {
    'boho': (('🍦', 'Kem Tràng Tiền đâyyy, mát lạnh luôn!'), ('🎈', 'Bóng bay đây, bóng bay đủ màu!'), ('🌽', 'Ngô nướng thơm phức đây!')),
    'chodem': (('🍢', 'Xiên que nướng đây, ba xiên mười nghìn!'), ('👕', 'Áo thun đồng giá, xả hàng cuối ngày!'), ('🧃', 'Nước mía mát lạnh đâyyy!')),
    'congvien': (('🍿', 'Bắp rang bơ nóng hổi đây!'), ('🍭', 'Kẹo bông gòn đây, ngọt như người yêu cũ!'), ('🪁', 'Diều đây, thả là bay liền!')),
    'phodibo': (('🍋', 'Trà chanh giã tay đâyyy!'), ('📸', 'Chụp ảnh lấy liền đây, đẹp như idol!'), ('🥗', 'Bánh tráng trộn đây, cay xé lưỡi!')),
}

# What a look may contain (game/wardrobe.py ITEMS and DEFAULTS; public/js/v4/look.js draws them).
LOOK_SLOTS = ('hair', 'shade', 'skin', 'top', 'bottom', 'shoes', 'acc')
LOOK_IDS = {
    'hair': ('toc_ngan', 'toc_bui', 'toc_dai', 'toc_bob', 'toc_duoi_ngua', 'toc_xoan'),
    'shade': ('mau_nau', 'mau_den', 'mau_mat_ong', 'mau_hong', 'mau_xanh_khoi', 'mau_bach_kim'),
    'skin': ('da_sang', 'da_hong', 'da_trung', 'da_ngam'),
    'top': ('ao_quen', 'ao_thun_kem', 'ao_thun_xanh', 'ao_so_mi', 'ao_len', 'ao_hoodie', 'ao_dai', 'ao_chi_may', 'ao_hoa', 'ao_vest',
            'ao_cuoi', 'vest_cuoi'),
    'bottom': ('quan_kem', 'quan_xam', 'quan_jean', 'quan_short', 'vay_xoe', 'vay_dai'),
    'shoes': ('giay_nau', 'dep_lao', 'giay_trang', 'giay_do', 'bot_den'),
    'acc': ('pk_khong', 'kinh_tron', 'kinh_ram', 'non_la', 'mu_len', 'no_toc', 'tui_cheo'),
}
LOOK_DEFAULTS = {
    'male': dict(hair='toc_ngan', shade='mau_nau', skin='da_sang', top='ao_quen', bottom='quan_xam', shoes='giay_nau', acc='pk_khong'),
    'female': dict(hair='toc_bui', shade='mau_nau', skin='da_sang', top='ao_quen', bottom='quan_kem', shoes='giay_nau', acc='pk_khong'),
    None: dict(hair='toc_ngan', shade='mau_nau', skin='da_sang', top='ao_quen', bottom='quan_kem', shoes='giay_nau', acc='pk_khong'),
}

# Danh hiệu shown under the name tag (game/journey.py TITLES: id -> emoji + name). A title the game adds later
# and this list does not have yet simply shows no title.
TITLES = {
    'st_newcomer': '🏠 Hàng xóm mới', 'st_familiar': '👋 Người quen mặt', 'st_skilled': '🛠️ Có nghề trong tay',
    'st_trusted': '🤝 Người được tin cậy', 'st_office': '💼 Dân văn phòng', 'st_local': '🏮 Người của khu phố',
    'g_first': '🌱 Việc đầu tiên', 'g_tasks50': '💪 Chăm chỉ', 'g_tasks200': '🙌 Đôi tay không nghỉ', 'g_places3': '🧭 Thử nhiều nghề',
    'g_places8': '🌈 Đa năng', 'g_places_all': '🗺️ Thuộc từng ngõ nghề', 'g_mature5': '🌿 Vững vàng', 'g_mature10': '🌳 Trưởng thành',
    'g_days30': '📅 Một tháng ở phố', 'g_days100': '🗓️ Trăm ngày thương',
    'c_milk_tea': '🧋 Thợ pha trà sữa', 'c_grocery': '🛒 Chủ quầy tạp hóa', 'c_delivery': '🛵 Shipper thuộc đường',
    'c_cafe_bakery': '☕ Barista buổi sớm', 'c_florist': '💐 Người cắm hoa', 'c_mother_baby': '🎁 Người gói quà khéo',
    'c_restaurant': '🍜 Đầu bếp mì cay', 'c_pet_care': '🐾 Bạn của chó mèo', 'c_salon': '💇 Thợ tóc có nghề',
    'c_repair': '🔧 Thợ sửa đồ tin cậy', 'c_farm': '🌾 Nông dân đồi gió', 'c_homestay': '🏡 Chủ nhà hiếu khách',
    'c_customer_care': '🎧 Người lắng nghe', 'c_pharmacy': '💊 Người đọc nhãn kỹ', 'c_tour_guide': '🧭 Người kể chuyện đường xa',
    'c_teacher': '🍎 Người dạy tận tâm', 'c_accounting': '📒 Người giữ sổ gọn', 'c_corp_accounting': '🧮 Kế toán vững tay',
    'c_tax_payroll': '🧾 Người tính lương chuẩn', 'c_group_accounting': '🏢 Kế toán hợp nhất',
    'k_careful': '🔍 Mắt tinh', 'k_communication': '💬 Nói dễ hiểu', 'k_patience': '🌱 Kiên nhẫn như đất', 'k_numbers': '🔢 Đầu óc con số',
    'k_teamwork': '🫶 Đồng đội tốt', 'k_creative': '🎨 Bàn tay khéo', 'k_tech': '💻 Rành máy móc', 'k_calm': '🧘 Bình tĩnh giờ cao điểm',
    'k_learning': '📚 Ham học hỏi',
    'm_first_draw': '👛 Tự lo cơm áo', 'm_save200': '🐷 Có của để dành', 'm_save1000': '💰 Ví dày', 'm_investor': '📈 Nhà đầu tư nhỏ',
    'm_salary': '💵 Đồng lương đầu tiên', 'm_debt_free': '🕊️ Trả hết nợ', 'm_home': '🏠 An cư', 'm_home_free': '🔑 Nhà hết nợ',
    'x_streak10': '✨ Mười việc liền mạch', 'x_festival3': '🎏 Mê ngày hội', 'x_calm5': '🍵 Người của ngày thư thả',
    'x_reopen': '🔑 Nghỉ để đi xa hơn', 'x_boss': '🍀 Người gặp may', 'x_loyal': '🏡 Chung thủy một quán', 'x_hopper': '🦘 Chân sáo',
    'x_comeback': '🌅 Từ tay trắng',
}

EMOTES = {'wave': '👋', 'heart': '❤️', 'laugh': '😂', 'wow': '😮', 'pray': '🙏'}
