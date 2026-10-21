"""🚶 Đi dạo: the places, the topic cards of the tám chuyện tables, the street vendors' calls, and the ids a
stroller's look and titles may use (copies of game/wardrobe.py, game/journey.py TITLES and the certificates, checked by
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
    # 💍 A wedding party (live/wedding.py): the tent and its stage at the top, the red carpet from the flower gate,
    # four round tables. Never listed, never joined by walk_in.
    'wedding': dict(
        name='Đám cưới', icon='💍', private=True,
        walk=[(30, 300, 570, 870), (170, 205, 430, 310)],
        tables=[(125, 470, 4), (475, 470, 4), (125, 680, 4), (475, 680, 4)],
        spots=dict(stage=(300, 250), spawn=(300, 800), gate=(300, 845)),
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

# What a look may contain (game/wardrobe.py ITEMS and DEFAULTS; public/js/v4/look.js draws them). The 1.9.2 pieces
# are here too: a 1.9.1 live service (or an old client) does not know them and shows the slot's default.
LOOK_SLOTS = ('hair', 'shade', 'skin', 'top', 'bottom', 'shoes', 'acc')
LOOK_IDS = {
    'hair': ('toc_ngan', 'toc_bui', 'toc_dai', 'toc_bob', 'toc_duoi_ngua', 'toc_xoan', 'toc_bui_cao', 'toc_bui_doi',
            'toc_bui_thap', 'toc_song_dai', 'toc_bob_mai', 'toc_duoi_cao', 'toc_bui_tron', 'toc_wolf',
            'toc_undercut', 'toc_mai_bay', 'toc_tet'),
    'shade': ('mau_nau', 'mau_den', 'mau_mat_ong', 'mau_hong', 'mau_xanh_khoi', 'mau_bach_kim'),
    'skin': ('da_sang', 'da_hong', 'da_trung', 'da_ngam'),
    'top': ('ao_quen', 'ao_thun_kem', 'ao_thun_xanh', 'ao_so_mi', 'ao_len', 'ao_hoodie', 'ao_dai', 'ao_chi_may',
            'ao_hoa', 'ao_vest', 'ao_cuoi', 'vest_cuoi', 'dam_cong_chua', 'dam_du_tiec', 'dam_yem', 'dam_maxi',
            'vay_babydoll', 'ao_blazer', 'ao_cardigan', 'ao_polo', 'ao_croptop', 'ao_baby_tee', 'ao_bomber',
            'ao_hoodie_os', 'ao_so_mi_os', 'ao_khoac_jean', 'vay_hai_day', 'ao_dai_cach_tan', 'ao_ba_lo',
            'dam_suong', 'vay_maxi_hoa', 'dam_so_mi', 'vay_yem_jean', 'dam_hoa_nhi', 'dam_kim_sa'),
    'bottom': ('quan_kem', 'quan_xam', 'quan_jean', 'quan_short', 'vay_xoe', 'vay_dai', 'vay_chu_a', 'quan_ong_rong',
            'quan_cargo', 'vay_tennis', 'quan_jogger', 'quan_short_jean', 'chan_vay_jean', 'vay_xep_ly_dai'),
    'shoes': ('giay_nau', 'dep_lao', 'giay_trang', 'giay_do', 'bot_den', 'sandal_nau', 'sneaker_chunky',
            'giay_mary_jane', 'boot_co_ngan', 'dep_quai_ngang'),
    'acc': ('pk_khong', 'kinh_tron', 'kinh_ram', 'non_la', 'mu_len', 'no_toc', 'tui_cheo', 'tui_xach', 'bong_tai',
            'khan_lua', 'kinh_mat_meo', 'mu_bucket', 'mu_luoi_trai', 'vong_co', 'dong_ho', 'kep_toc', 'kinh_can',
            'no_lua', 'khuyen_tron', 'khan_bandana', 'balo_mini', 'mu_beret', 'mu_cao_boi', 'tai_nghe',
            'vuong_mien', 'bang_do_tai_meo', 'vong_hoa', 'khau_trang', 'khan_choang'),
}
# Bảng màu (1.3.1 accessories, then clothes and shoes): look['tint'] = {worn item id: colour id}
# (game/wardrobe.py TINTABLE, CLOTHES, TINT_SLOTS and COLORS). Hair keeps its own shades.
TINTABLE = ('kinh_tron', 'kinh_ram', 'non_la', 'mu_len', 'no_toc', 'tui_cheo', 'tui_xach', 'bong_tai', 'khan_lua',
            'kinh_mat_meo', 'mu_bucket', 'mu_luoi_trai', 'vong_co', 'dong_ho', 'kep_toc', 'kinh_can', 'no_lua',
            'khuyen_tron', 'khan_bandana', 'balo_mini', 'mu_beret', 'mu_cao_boi', 'tai_nghe', 'vuong_mien',
            'bang_do_tai_meo', 'vong_hoa', 'khau_trang', 'khan_choang')
TINT_SLOTS = ('top', 'bottom', 'shoes', 'acc')
PAINTABLE = frozenset(TINTABLE + LOOK_IDS['top'] + LOOK_IDS['bottom'] + LOOK_IDS['shoes'])
TINT_MAX = 8      # entries a client may send (it sends at most one per slot in TINT_SLOTS)
COLOR_IDS = ('den', 'nau', 'vang', 'bac', 'hong', 'do', 'dao', 'mint', 'navy', 'lavender', 'trang')
LOOK_DEFAULTS = {
    'male': dict(hair='toc_ngan', shade='mau_nau', skin='da_sang', top='ao_quen', bottom='quan_xam', shoes='giay_nau', acc='pk_khong'),
    'female': dict(hair='toc_bui', shade='mau_nau', skin='da_sang', top='ao_quen', bottom='quan_kem', shoes='giay_nau', acc='pk_khong'),
    None: dict(hair='toc_ngan', shade='mau_nau', skin='da_sang', top='ao_quen', bottom='quan_kem', shoes='giay_nau', acc='pk_khong'),
}

# 🎖️ The rank a stroller wears (game/org_content.py grade ids, public/js/v4/insignia.js draws them): `rk` = {o, g} in
# walk_in / wed_in, apart from the look (older services ignore it, an id this list lacks shows nothing).
ORG_GRADES = {'cand': ('binh_nhi', 'binh_nhat', 'ha_si', 'trung_si', 'thuong_si', 'thieu_uy', 'trung_uy', 'thuong_uy', 'dai_uy',
                       'thieu_ta', 'trung_ta', 'thuong_ta', 'dai_ta', 'thieu_tuong', 'hoc_vien')}   # 11/10: GĐ's general, Học viên
ORG_GRADES['hq'] = ('tap_su', 'ktv_1', 'ktv_2', 'ktv_3', 'ktvc_1', 'ktvc_2', 'ktvc_3', 'ktvcc_1', 'ktvcc_2', 'ktvcc_3')   # 🛃 Hải quan (16/10)

# 🐾 The pet walking beside a stroller (game/pets_content.py breed ids -> number of coats; public/js/v4/pet-art.js draws
# them): `pt` = {b, c, n, a} in walk_in / wed_in, apart from the look (older services ignore it; a breed this list lacks,
# or an accessory id PET_ACCS lacks, simply is not shown).
PET_BREEDS = {'cho_ta': 4, 'poodle': 4, 'corgi': 2, 'shiba': 3, 'pom': 3, 'chihuahua': 3, 'husky': 3, 'golden': 2, 'alaska': 2, 'phu_quoc': 3, 'bac_ha': 3, 'pug': 2, 'samoyed': 2, 'lap_xuong': 3, 'meo_muop': 2, 'tam_the': 2, 'meo_mun': 2, 'aln': 3, 'ald': 3, 'ba_tu': 3, 'scottish': 3, 'munchkin': 3, 'ragdoll': 2, 'bengal': 2, 'sphynx': 2, 'maine_coon': 3, 'xiem': 2, 'becgie': 2, 'dalmatian': 2, 'shihtzu': 2, 'beagle': 2, 'border': 2, 'bulldog': 2, 'chowchow': 2, 'akita': 2, 'cho_lai': 2, 'nga_xanh': 1, 'abyssinian': 2, 'exotic': 2, 'mau': 2, 'bombay': 1, 'maltese': 2, 'spitz': 2, 'doberman': 2, 'cavalier': 2, 'chinchilla': 2, 'angora': 2, 'savannah': 2, 'korat': 1, 'hmong': 3, 'lai_van_ho': 1, 'goldendoodle': 2, 'pomsky': 2, 'corgi_inu': 2, 'soi_tuyet': 1, 'soi_xam': 1, 'dom_mat_xe': 1, 'himalaya': 2, 'ragamuffin': 2, 'toyger': 1, 'scottish_kilt': 2, 'ngoc_bich': 1, 'tam_the_duc': 1, 'linh_khuyen': 1, 'than_tai': 1, 'ky_lan': 2, 'ky_lan_sung': 2, 'khung_long': 2, 'khung_long_co': 2, 'khung_long_ba_sung': 2, 'rong_con': 2}
PET_FX = frozenset(['bang_tinh', 'cau_vong', 'dot_bien', 'hong_ngoc', 'ngan_ha'])   # 🏅 the coat effects an SSS (or a mutant pup) shows: game/pet_tiers.py FX_IDS
PET_ACCS = frozenset(['ao_bi_ngo', 'ao_choang_hoang_gia', 'ao_choang_sieu_nhan', 'ao_dai', 'ao_dai_hoa', 'ao_hanbok', 'ao_hawaii', 'ao_khung_long', 'ao_kimono', 'ao_len', 'ao_long_cuu', 'ao_mua', 'ao_ngu_sac', 'ao_ong', 'ao_phao', 'ao_phi_hanh_gia', 'ao_tac_nam', 'ao_thuy_thu', 'ao_vn', 'balo_ca', 'bang_do_tai_tho', 'bo_hoa_lung', 'cai_toc_hoa', 'canh_ac_quy', 'canh_bang_tuyet', 'canh_buom', 'canh_buom_dem', 'canh_cau_vong', 'canh_chuon_chuon', 'canh_cong', 'canh_doi', 'canh_hac', 'canh_hoa_cuoi', 'canh_hoa_sen', 'canh_keo_bong', 'canh_lua', 'canh_ngan_ha', 'canh_ong_nho', 'canh_pha_le', 'canh_phuong_hoang', 'canh_qua_den', 'canh_rong', 'canh_rong_vang', 'canh_thien_nga', 'canh_thien_than', 'canh_thien_than_den', 'canh_thien_than_vang', 'canh_tien', 'day_chuyen_tim', 'hoodie_tho', 'khan_dong', 'khan_len_soc', 'khan_quang_do', 'khan_thuy_thu', 'khan_voan_cuoi', 'kinh_boi', 'kinh_kim_cuong', 'kinh_mot_trong', 'kinh_ram', 'kinh_sao', 'kinh_tim', 'kinh_tron', 'kinh_vang', 'mat_na_ma', 'mu_bao_hiem', 'mu_cao_boi', 'mu_ech', 'mu_len_tai_meo', 'mu_noi', 'mu_phu_thuy', 'mu_sinh_nhat', 'mu_thuy_thu', 'no_buom_co', 'no_cham', 'no_co_cuoi', 'no_hong', 'non_la', 'phao_boi', 'pijama_sao', 'vay_cong_chua', 'vay_cuoi', 'vay_hoa_nhi', 'vay_tutu', 'vest_chu_re', 'vong_chuong', 'vong_da', 'vong_hao_quang', 'vong_hoa_dai', 'vong_hoa_hong', 'vong_keo', 'vong_kim_cuong', 'vong_ngoc', 'vong_ngoc_bich', 'vong_trang_khuyet', 'vong_vang', 'vuong_mien', 'vuong_mien_kim_cuong', 'yem_dau'])   # 👗 the wardrobe's pieces but beds (game/pet_wardrobe_content.py)
PET_LUX = frozenset(['ao_choang_hoang_gia', 'canh_phuong_hoang', 'kinh_kim_cuong', 'lau_dai_pha_le', 'vong_kim_cuong', 'vuong_mien_kim_cuong'])   # 💎 its luxury pieces (only with one owned: live/pet_rank.py)
PET_SETS = frozenset(['cuoi', 'halloween', 'hoang_gia', 'oct20', 'thuy_thu'])   # ✨ the sets whose effect a whole outfit shows

# Danh hiệu shown under the name tag (game/journey.py TITLES: id -> emoji + name). A title the game adds later
# and this list does not have yet simply shows no title.
TITLES = {
    'st_newcomer': '🏠 Hàng xóm mới', 'st_familiar': '👋 Người quen mặt', 'st_skilled': '🛠️ Có nghề trong tay',
    'st_trusted': '🤝 Người được tin cậy', 'st_office': '💼 Dân văn phòng', 'st_local': '🏮 Người của khu phố',
    'g_first': '🌱 Việc đầu tiên', 'g_tasks50': '💪 Chăm chỉ', 'g_tasks200': '🙌 Đôi tay không nghỉ', 'g_places3': '🧭 Thử nhiều nghề',
    'g_places8': '🌈 Đa năng', 'g_places_all': '🗺️ Thuộc từng ngõ nghề', 'g_mature5': '🌿 Vững vàng', 'g_mature10': '🌳 Trưởng thành',
    'g_days30': '📅 Một tháng ở phố', 'g_days100': '🗓️ Trăm ngày thương',
    'c_milk_tea': '🧋 Thợ pha trà sữa', 'c_grocery': '🛒 Chủ quầy tạp hóa', 'c_delivery': '🛵 Shipper thuộc đường',
    'c_customs': '🛃 Người gác cửa khẩu', 'c_hotel': '🛎️ Người giữ chìa khóa Sông Mây', 'c_banquet': '👨‍🍳 Chiếc mũ trắng Hồng Mây', 'c_reception': '🔑 Người giữ bảng móc chìa', 'c_teller': '🏦 Người đếm tiền hai lần', 'c_restore': '🧰 Người giữ hồn đồ xưa', 'c_research': '🔬 Cuốn sổ thí nghiệm bìa xanh', 'c_radio': '📻 Giọng nói của Sóng Mây', 'c_moto': '🏍️ Tay cờ lê đầu hẻm', 'c_vet': '🩺 Bác sĩ của các bé', 'c_tuning': '🔧 Bàn tay chỉnh dyno', 'c_cafe_bakery': '☕ Barista buổi sớm', 'c_florist': '💐 Người cắm hoa', 'c_mother_baby': '🎁 Người gói quà khéo',
    'c_restaurant': '🍜 Đầu bếp mì cay', 'c_pet_care': '🐾 Bạn của chó mèo', 'c_salon': '💇 Thợ tóc có nghề',
    'c_repair': '🔧 Thợ sửa đồ tin cậy', 'c_farm': '🌾 Nông dân đồi gió', 'c_homestay': '🏡 Chủ nhà hiếu khách',
    'c_customer_care': '🎧 Người lắng nghe', 'c_pharmacy': '💊 Người đọc nhãn kỹ', 'c_tour_guide': '🧭 Người kể chuyện đường xa',
    'c_teacher': '🍎 Người dạy tận tâm', 'c_accounting': '📒 Người giữ sổ gọn', 'c_corp_accounting': '🧮 Kế toán vững tay',
    'c_tax_payroll': '🧾 Người tính lương chuẩn', 'c_group_accounting': '🏢 Kế toán hợp nhất',
    'c_hr_admin': '🗂️ Người giữ hồ sơ nhân sự', 'c_secretary': '📅 Thư ký chu đáo', 'c_it_helpdesk': '🖥️ Cứu tinh máy tính', 'c_oil': '🛢️ Người giữ ổ khóa đỏ', 'c_police': '👮 Người giữ bình yên hẻm', 'c_zpop': '💿 Người giữ seal nguyên vẹn',
    'c_lighthouse': '🗼 Người giữ lửa Hòn Gió',
    'k_careful': '🔍 Mắt tinh', 'k_communication': '💬 Nói dễ hiểu', 'k_patience': '🌱 Kiên nhẫn như đất', 'k_numbers': '🔢 Đầu óc con số',
    'k_teamwork': '🫶 Đồng đội tốt', 'k_creative': '🎨 Bàn tay khéo', 'k_tech': '💻 Rành máy móc', 'k_calm': '🧘 Bình tĩnh giờ cao điểm',
    'k_learning': '📚 Ham học hỏi',
    'm_first_draw': '👛 Tự lo cơm áo', 'm_save200': '🐷 Có của để dành', 'm_save1000': '💰 Ví dày', 'm_investor': '📈 Nhà đầu tư nhỏ',
    'm_salary': '💵 Đồng lương đầu tiên', 'm_debt_free': '🕊️ Trả hết nợ', 'm_home': '🏠 An cư', 'm_home_free': '🔑 Nhà hết nợ',
    'x_streak10': '✨ Mười việc liền mạch', 'x_festival3': '🎏 Mê ngày hội', 'x_calm5': '🍵 Người của ngày thư thả',
    'x_reopen': '🔑 Nghỉ để đi xa hơn', 'x_boss': '🍀 Người gặp may', 'x_loyal': '🏡 Chung thủy một quán', 'x_hopper': '🦘 Chân sáo',
    'x_comeback': '🌅 Từ tay trắng',
    'w_crowd': '🎉 Đám cưới đông vui', 'w_100': '💞 Trăm ngày bên nhau', 'w_1y': '🎂 Tròn một năm', 'w_500': '💍 Năm trăm ngày thương',
    'w_1000': '👑 Nghìn ngày son sắt', 'w_vip': '🥇 Khách quý của phố', 'w_pro': '🎊 Ăn cưới chuyên nghiệp',
}

# Certificates worn like titles (game/journey.py CERT_WEAR + game/certificates.py GROUPS: 'cert:<id>' -> emoji + name).
CERTS = {
    'cert:work_safety': '🦺 Chứng chỉ An toàn lao động', 'cert:grooming': '✂️ Chứng chỉ Chăm sóc tóc & thú cưng',
    'cert:customer_service': '🎧 Chứng chỉ Chăm sóc khách hàng', 'cert:teaching': '🍎 Chứng chỉ Nghiệp vụ sư phạm',
    'cert:accounting': '🧮 Chứng chỉ Kế toán cơ bản', 'cert:air_safety': '✈️ Chứng chỉ An toàn bay cơ bản',
    'cert:office_admin': '🗂️ Chứng chỉ Hành chính văn phòng', 'cert:offshore_safety': '🛢️ Chứng chỉ An toàn cơ bản ngoài khơi', 'cert:ice_cream_craft': '🍨 Chứng chỉ làm kem',
    'cert:archive_craft': '🗂️ Chứng chỉ nghiệp vụ lưu trữ',
    'cert:rail_safety': '🚦 Chứng chỉ An toàn đường ngang',
    'cert:patient_safety': '🏥 Chứng chỉ An toàn người bệnh',
    'cert:light_keeping': '🗼 Chứng chỉ Gác đèn biển',
    'cert:emergency_call': '📞 Chứng chỉ Tiếp nhận cuộc gọi khẩn cấp',
    'cert:pool_rescue': '🛟 Chứng chỉ Cứu hộ hồ bơi',
    'cert:ward_service': '👮 Chứng chỉ Tiếp dân & hòa giải',
    'cert:customs_basics': '🛃 Chứng chỉ Nghiệp vụ hải quan cơ bản',
    'cert:hotel_service': '🛎️ Chứng chỉ Nghiệp vụ khách sạn cơ bản',
    'cert:banquet_service': '👨‍🍳 Chứng chỉ Bếp tiệc và sảnh sự kiện cơ bản',
    'cert:reception_service': '🛎️ Chứng chỉ Nghiệp vụ lễ tân cơ bản',
    'cert:teller_service': '🏦 Chứng chỉ Nghiệp vụ giao dịch viên cơ bản',
    'cert:research_basics': '🔬 Chứng chỉ Phương pháp nghiên cứu cơ bản',
    'cert:radio_basics': '📻 Chứng chỉ Phát thanh viên cơ bản',
    'cert:moto_basics': '🏍️ Chứng chỉ Kỹ thuật sửa xe máy cơ bản',
    'cert:vet_basics': '🩺 Chứng chỉ Chăm sóc thú y cơ bản',
    'cert:tuning_basics': '🔧 Chứng chỉ Độ xe đúng luật cơ bản',
}

EMOTES = {'wave': '👋', 'heart': '❤️', 'laugh': '😂', 'wow': '😮', 'pray': '🙏', 'dance': '💃'}   # 💃: a wedding's stage (live/wedding.py)
