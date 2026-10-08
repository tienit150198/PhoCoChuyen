"""🛍️ Mua sắm hạng sang: the catalogue of game/lux.py (pure data, no imports).

Owner 07/10: "đưa ra nhiều cái mà mọi người sẽ mua để kích thích khả năng tiêu tiền vì hiện tại mọi người nhiều tiền quá
rồi". DESIGN_0610 §0.1: the median player earns ≈ 262 xu a life day and spends ≈ 12; wallets p90 ≈ 3,300, p99 ≈ 26,400;
the top 1 % hold half of all wealth (3.4 M, 1.9 M, 1.6 M at the top) and nothing cost more than the 150,000 xu yacht.
So this catalogue sits where the money is: 5,000 → 3,000,000 xu (T3 ước mơ and T4 đẳng cấp of §3.2), with a few
cheaper doors (a photo, a souvenir, a home party) so a p75 player can join in.

Never pay-to-win: nothing here pays xu, speeds up work, helps an exam or a review. Effects are status (titles worn in
chat through game/spend.py, the profile card), the album, tinh thần within the existing caps, and public plaques.
Prices are plain constants (no shared PRICE_INDEX existed when this was written, 07/10).

Ids are stored in saves and in the `lux_gifts` table: never rename or remove one (retire it with `gone: True`).
"""

# ---------------------------------------------------------------- ✈️ Du lịch nước ngoài (Đại lý vé Cánh Cò)
# docs: what the consulate wants (DOCS). bank: the bank account must show bank × the economy trip price. days: how many
# life days a visa lasts. The trip price is the economy one; a class multiplies it (CLASSES).
COUNTRIES = (
    dict(id='trung_quoc', flag='🇨🇳', name='Trung Quốc', cities='Thượng Hải · Lệ Giang', trip=4500, visa=300, days=30, bank=1,
         docs=('anh', 'sao_ke'), lang='tieng_trung'),
    dict(id='han_quoc', flag='🇰🇷', name='Hàn Quốc', cities='Seoul · Jeju', trip=6500, visa=500, days=30, bank=2,
         docs=('anh', 'sao_ke', 'cong_viec'), lang='tieng_han'),
    dict(id='nhat_ban', flag='🇯🇵', name='Nhật Bản', cities='Tokyo · Kyoto', trip=9000, visa=600, days=60, bank=2,
         docs=('anh', 'sao_ke', 'cong_viec', 'lich_trinh'), lang='tieng_nhat'),
    dict(id='my', flag='🇺🇸', name='Mỹ', cities='California · New York', trip=18000, visa=4000, days=200, bank=3,
         docs=('anh', 'sao_ke', 'cong_viec', 'lich_trinh'), lang='tieng_anh', interview=3),
    dict(id='chau_au', flag='🇪🇺', name='Châu Âu', cities='Paris · Rome · Praha', trip=24000, visa=2500, days=100, bank=3,
         docs=('anh', 'sao_ke', 'cong_viec', 'lich_trinh', 'bao_hiem'), lang='tieng_phap'),
)
CLASSES = (
    dict(id='pho_thong', emoji='💺', name='Phổ thông', mult=1),
    dict(id='thuong_gia', emoji='🥂', name='Thương gia', mult=3),
    dict(id='hoang_gia', emoji='👑', name='Hoàng gia', mult=10),
)
DOCS = (
    dict(id='anh', emoji='📷', name='Ảnh 3.5×4.5'),
    dict(id='sao_ke', emoji='🏦', name='Sao kê'),
    dict(id='cong_viec', emoji='💼', name='Xác nhận việc'),
    dict(id='lich_trinh', emoji='🗓️', name='Lịch trình'),
    dict(id='bao_hiem', emoji='🛡️', name='Bảo hiểm'),
)
PHOTO_PRICE = 20            # 📷 ảnh thẻ nền trắng at the photo shop: valid PHOTO_DAYS life days
PHOTO_DAYS = 30
WORK_DAYS = 3               # 💼 the employer letter needs this many life days worked (journey.days)
INSURE_PCT = 1              # 🛡️ travel insurance: 1 % of the economy trip, for one application
TRIP_SPIRIT = 3
# 🇺🇸 the consulate interview: three questions drawn per attempt (one with the English course done). ok: the index of
# the honest answer (the other two are why visas get refused in real life).
INTERVIEW = (
    dict(q='Sang Mỹ làm gì?', a=('Sang rồi tính', 'Du lịch, có vé khứ hồi', 'Kiếm việc làm thêm'), ok=1),
    dict(q='Ai trả tiền chuyến đi?', a=('Tôi tự trả, có sao kê', 'Bạn bên đó lo', 'Chưa biết nữa'), ok=0),
    dict(q='Khi nào về nước?', a=('Hết tiền thì về', 'Chưa định về', 'Sau 10 ngày, đúng vé'), ok=2),
    dict(q='Ở nhà bạn làm gì?', a=('Đang đi làm, có giấy', 'Đang rảnh', 'Không muốn nói'), ok=0),
    dict(q='Bên đó ở đâu?', a=('Ngủ sân bay', 'Khách sạn đã đặt', 'Nhà người quen, chưa hỏi'), ok=1),
)
# Two scenes of each trip (one line each, picked by the save's seed): the awkward bits are flavour, never a charge.
TRIP_LINES = {
    'trung_quoc': ('Hướng dẫn viên dẫn cả đoàn vào ba tiệm ngọc liền, ai cũng bị mời “xem thôi không mua”.',
                   'Lệ Giang mưa phùn, phố cổ đèn lồng đỏ, bạn ăn bát mì bò cay xé lưỡi.',
                   'Ở Thượng Hải ngắm Bến Thượng Hải về đêm, chen chân chụp một tấm cho bằng được.'),
    'han_quoc': ('Thuê hanbok chụp ở cung Gyeongbok, cô bán vé khen “đẹp như diễn viên”.',
                 'Jeju gió to bay cả mũ, bạn đuổi theo nửa bãi biển.',
                 'Đêm Seoul ăn gà rán uống soda, quán đông tới mức đứng ăn.'),
    'nhat_ban': ('Tàu Shinkansen đúng giờ tới từng giây, bạn chạy hụt hơi mới kịp.',
                 'Kyoto mùa lá đỏ, đền Fushimi cổng đỏ nối nhau không thấy điểm cuối.',
                 'Khách sạn phòng bé xíu, mở vali là hết chỗ đứng.'),
    'my': ('Hải quan hỏi thêm ba câu, may mà giấy tờ đủ cả.',
           'Cầu Cổng Vàng chìm trong sương, bạn chờ một tiếng mới thấy đỉnh cầu.',
           'Quảng trường Thời Đại sáng như ban ngày lúc nửa đêm.'),
    'chau_au': ('Tàu đêm Paris – Rome trễ hai tiếng, cả toa ngồi ăn bánh mì kể chuyện.',
                'Đứng dưới tháp Eiffel lúc đèn nhấp nháy, cả nhóm hò reo.',
                'Phố cổ Praha lát đá, kéo vali kêu lộc cộc suốt buổi sáng.'),
}
# Bought in the country, the life day of the trip only. Not resold: a pure sink (a keepsake, not an asset).
SOUVENIRS = {
    'trung_quoc': (dict(id='am_tu_sa', emoji='🫖', name='Ấm trà Tử Sa', price=800),
                   dict(id='tranh_to_chau', emoji='🧧', name='Tranh lụa Tô Châu', price=3000),
                   dict(id='ngoc_bich', emoji='🐉', name='Ngọc bích chạm rồng', price=15000)),
    'han_quoc': (dict(id='mat_na_hahoe', emoji='🎭', name='Mặt nạ Hahoe', price=400),
                 dict(id='my_pham_seoul', emoji='💄', name='Bộ mỹ phẩm Seoul', price=1500),
                 dict(id='hong_sam', emoji='🌱', name='Hồng sâm 6 năm', price=8000)),
    'nhat_ban': (dict(id='meo_vay_tay', emoji='🐱', name='Mèo vẫy tay', price=300),
                 dict(id='dao_seki', emoji='🔪', name='Dao rèn Seki', price=2500),
                 dict(id='su_arita', emoji='🍶', name='Bộ chén sứ Arita', price=12000)),
    'my': (dict(id='mu_new_york', emoji='🧢', name='Mũ New York', price=300),
           dict(id='ao_da_my', emoji='🧥', name='Áo khoác da', price=3500),
           dict(id='guitar_ky_ten', emoji='🎸', name='Guitar có chữ ký', price=20000)),
    'chau_au': (dict(id='nuoc_hoa_paris', emoji='🌸', name='Nước hoa Paris', price=2000),
                dict(id='pha_le_bohemia', emoji='🔮', name='Pha lê Bohemia', price=6000),
                dict(id='tui_florence', emoji='👜', name='Túi da Florence', price=18000)),
}
SOUV_MAX = 99               # copies of one souvenir kept

# ---------------------------------------------------------------- 💎 Bộ sưu tập (Phố hàng hiệu)
# rare: 1 ★ thường, 2 ★★ hiếm, 3 ★★★ quý, 4 ★★★★ huyền thoại. Fictional makers only. Resold at SELL_PCT. Wine can be
# opened instead (game/lux.py jr_lux_open): gone, no money back, a line in the album.
SETS = (
    dict(id='dong_ho', emoji='⌚', name='Đồng hồ', items=(
        dict(id='dh_co_sg', name='Đồng hồ cơ Sài Gòn', price=5000, rare=1),
        dict(id='dh_lan_bien', name='Đồng hồ lặn Thủy Thủ', price=18000, rare=2),
        dict(id='dh_van_nien', name='Lịch vạn niên Trăng Rằm', price=60000, rare=3),
        dict(id='dh_tourbillon', name='Tourbillon Kim Cương', price=250000, rare=4),
        dict(id='dh_doc_ban', name='Độc bản Hoàng Đế', price=1000000, rare=4))),
    dict(id='tui', emoji='👜', name='Túi hiệu', items=(
        dict(id='tui_da_may', name='Túi da Mây', price=4000, rare=1),
        dict(id='tui_sen_trang', name='Túi Sen Trắng', price=15000, rare=2),
        dict(id='tui_ca_sau', name='Túi cá sấu Kim Ngân', price=80000, rare=3),
        dict(id='tui_bach_kim', name='Túi bạch kim đính đá', price=400000, rare=4),
        dict(id='tui_hoang_hau', name='Túi Hoàng Hậu độc bản', price=1200000, rare=4))),
    dict(id='trang_suc', emoji='💍', name='Trang sức', items=(
        dict(id='ts_nhan_bac', name='Nhẫn bạc chạm hoa', price=3000, rare=1),
        dict(id='ts_ngoc_trai', name='Chuỗi ngọc trai biển', price=12000, rare=2),
        dict(id='ts_hong_ngoc', name='Bông tai hồng ngọc', price=45000, rare=3),
        dict(id='ts_luc_bao', name='Vòng cổ lục bảo', price=180000, rare=4),
        dict(id='ts_vuong_mien', name='Vương miện sapphire', price=900000, rare=4))),
    dict(id='tranh', emoji='🖼️', name='Tranh', items=(
        dict(id='tr_dong_ho', name='Tranh Đông Hồ', price=2500, rare=1),
        dict(id='tr_son_mai', name='Tranh sơn mài', price=20000, rare=2),
        dict(id='tr_lua_co', name='Tranh lụa cổ', price=75000, rare=3),
        dict(id='tr_son_dau', name='Sơn dầu danh họa', price=350000, rare=4),
        dict(id='tr_kiet_tac', name='Kiệt tác thế kỷ', price=2000000, rare=4))),
    dict(id='tuong', emoji='🗿', name='Tượng hiếm', items=(
        dict(id='tg_to_he', name='Tò he men lam', price=2000, rare=1),
        dict(id='tg_ngua_tram', name='Ngựa gỗ trầm hương', price=9000, rare=2),
        dict(id='tg_rong_ngoc', name='Rồng ngọc phỉ thúy', price=40000, rare=3),
        dict(id='tg_ky_lan', name='Kỳ lân vàng ròng', price=150000, rare=4),
        dict(id='tg_phuong', name='Phượng hoàng pha lê', price=700000, rare=4))),
    dict(id='ruou', emoji='🍷', name='Rượu vang', items=(
        dict(id='rv_da_lat', name='Vang Đà Lạt', price=1000, rare=1),
        dict(id='rv_phap_20', name='Vang Pháp 20 năm', price=8000, rare=2),
        dict(id='rv_y_co', name='Vang Ý cổ', price=30000, rare=3),
        dict(id='rv_1945', name='Bordeaux 1945', price=120000, rare=4),
        dict(id='rv_hoang_gia', name='Champagne hoàng gia', price=500000, rare=4))),
)
WINE_SET = 'ruou'
OPEN_SPIRIT = 3
INSURE_FROM = 50000         # 🧾 a piece from this price pays bảo hiểm & két sắt every tháng (ASSET upkeep below)
INSURE_BP = 20              # 0,2 % of the price paid, a tháng (5 life days)

# ---------------------------------------------------------------- 🛫 Phương tiện có phi hành đoàn (above the garage's)
# 1.9.11: the names say "có tổ bay" / "có thủy thủ đoàn" so they never read like the garage's own Trực thăng riêng,
# Phản lực riêng and Siêu du thuyền Ngọc Trai (game/garage.py: self-owned, indexed prices). Ids differ from the garage's
# and live in journey.lux, not journey.garage.
# The villas are game/estates_content.py (lived in, with their own rooms). These are the vehicles above the garage's
# yacht. bp: upkeep (bảo hiểm, bến bãi, phi công / thủy thủ đoàn) in basis points of the price paid, a tháng (5 life
# days). use: the fee of one trip out, once a life day across every vehicle, TRIP_SPIRIT tinh thần.
ASSETS = (
    dict(id='truc_thang_vip', group='fly', emoji='🚁', name='Trực thăng VIP có tổ bay', price=200000, bp=60, use=200, verb='Bay ngắm phố'),
    dict(id='du_thuyen_hg', group='fly', emoji='🛳️', name='Siêu du thuyền Hoàng Gia có thủy thủ đoàn', price=1000000, bp=70, use=1000, verb='Ra khơi'),
    dict(id='chuyen_co', group='fly', emoji='🛫', name='Chuyên cơ thân rộng có tổ bay', price=2000000, bp=80, use=2000, verb='Bay ra biển'),
)
USE_LINES = {
    'fly': ('Phi công chào “chúc anh chị một chuyến bay êm”, mây trắng ngay dưới chân.',
            'Từ trên cao, phố Mây bé xíu như mô hình.',
            'Hạ cánh kịp ăn bữa tối hải sản rồi về.'),
}
SELL_PCT = 60               # an asset or a collection piece bought back at 60 % of the price paid

# ---------------------------------------------------------------- 🎉 Tiệc ở nhà
PARTY_KINDS = (
    dict(id='sinh_nhat', emoji='🎂', name='Sinh nhật'),
    dict(id='tan_gia', emoji='🏠', name='Tân gia', home=True),     # needs a home you own (or an estate)
)
PARTY_TIERS = (
    dict(id='binh_dan', emoji='🍢', name='Tiệc nhà', base=1500, guest=30),
    dict(id='nha_hang', emoji='🍽️', name='Nhà hàng', base=8000, guest=150),
    dict(id='sang', emoji='🥂', name='Sang trọng', base=40000, guest=800, news=True),
    dict(id='hoang_gia', emoji='👑', name='Hoàng gia', base=200000, guest=4000, news=True),
)
GUESTS_MIN, GUESTS_MAX, GUESTS_STEP = 5, 100, 5
PARTY_SPIRIT = 4

# ---------------------------------------------------------------- 🎓 Khóa học (paid up front, one lesson a life day)
COURSES = (
    dict(id='tieng_anh', emoji='🇬🇧', name='Tiếng Anh', price=6000, lessons=5, lang=True),
    dict(id='tieng_han', emoji='🇰🇷', name='Tiếng Hàn', price=5000, lessons=5, lang=True),
    dict(id='tieng_nhat', emoji='🇯🇵', name='Tiếng Nhật', price=5500, lessons=5, lang=True),
    dict(id='tieng_trung', emoji='🇨🇳', name='Tiếng Trung', price=4500, lessons=5, lang=True),
    dict(id='tieng_phap', emoji='🇫🇷', name='Tiếng Pháp', price=7000, lessons=5, lang=True),
    dict(id='ruou_vang', emoji='🍷', name='Nếm rượu vang', price=30000, lessons=6),
    dict(id='golf', emoji='⛳', name='Học golf', price=60000, lessons=8),
    dict(id='mba', emoji='🎓', name='MBA Phố Mây', price=250000, lessons=10),
    dict(id='phi_cong', emoji='🛩️', name='Bằng lái máy bay riêng', price=400000, lessons=10),
)

# ---------------------------------------------------------------- 🎆 Mạnh Thường Quân (public, a weekly board)
# size: fixed choices (fireworks); slots: limited numbered plaques (permanent); week: one week's banner (the top
# sponsor of the week shows); min/max: an amount the player picks (the library fund).
GIVES = (
    dict(id='phao_hoa', emoji='🎆', name='Pháo hoa cả phố', sizes=(
        dict(id='nho', name='Pháo hoa nhỏ', price=20000),
        dict(id='lon', name='Pháo hoa lớn', price=80000),
        dict(id='dai_tiec', name='Đại tiệc pháo hoa', price=300000)), gap=600),
    dict(id='ghe_da', emoji='🪑', name='Ghế đá khắc tên', price=30000, slots=24, where='Công viên bờ hồ'),
    dict(id='cot_den', emoji='💡', name='Cột đèn khắc tên', price=60000, slots=12, where='Đường ven sông'),
    dict(id='hoi_cho', emoji='🏮', name='Tài trợ hội chợ', price=150000, week=True),
    dict(id='zpop', emoji='🎤', name='Tài trợ đêm nhạc ZPOP', price=250000, week=True),
    dict(id='thu_vien', emoji='📚', name='Quỹ thư viện trường', min=10000, max=5000000, presets=(10000, 50000, 200000, 1000000)),
)
# A plaque's line (no free text: nothing to moderate on a public sign).
DEDICATIONS = (
    ('me', 'Tặng mẹ'), ('bo', 'Tặng bố'), ('nguoi_thuong', 'Tặng người thương'), ('ca_xom', 'Cho cả xóm'),
    ('ong_ba', 'Nhớ ông bà'), ('ngay_cuoi', 'Kỷ niệm ngày cưới'), ('pho_may', 'Cảm ơn phố Mây'),
)
# 🎆 A wish shown with the fireworks on every open screen (optional; a fixed list, nothing to moderate). Ids are stored
# in the give's `m` (an id, like a plaque's dedication), so an older build keeps a save that has one.
FW_WISHES = (
    ('ca_pho', 'Chúc cả phố vui vẻ'), ('sinh_nhat', 'Mừng sinh nhật'), ('cuoi', 'Mừng đám cưới'),
    ('nha_moi', 'Mừng nhà mới'), ('tot_nghiep', 'Mừng tốt nghiệp'), ('viec_moi', 'Mừng việc mới'),
    ('nguoi_thuong', 'Tặng người thương'), ('me', 'Tặng mẹ'), ('bo', 'Tặng bố'), ('cam_on', 'Cảm ơn phố Mây'),
)
NEWS_GAP = 120              # seconds between two lines a sponsorship puts on the ticker (fireworks keep their own gap)

# ---------------------------------------------------------------- 🏷️ titles earned here (worn through game/spend.py)
# The ids are game/spend_content.py LUX_TITLES (a title worn in chat must be in its STYLE_ITEMS). rule: what earns it.
EARN = (
    ('t_xe_dich', 'countries', 3), ('t_toan_cau', 'countries', 5),
    ('t_suu_tam', 'pieces', 5), ('t_bau_vat', 'legend', 1),
    ('t_dinh_thu', 'home', 1), ('t_chu_dao', 'island', 1), ('t_bau_troi', 'fly', 1),
    ('t_trum_tiec', 'parties', 5),
    ('t_da_ngon_ngu', 'langs', 3), ('t_mba', 'course:mba', 1), ('t_sommelier', 'course:ruou_vang', 1),
    ('t_golf', 'course:golf', 1), ('t_phi_cong', 'course:phi_cong', 1),
    ('t_mtq', 'gave', 100000), ('t_thap_sang', 'fireworks', 1), ('t_an_nhan', 'library', 50000),
)
