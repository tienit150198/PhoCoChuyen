"""🔨 Nhà đấu giá đồ độc bản (game/auction.py): the catalogue of one-of-a-kind lots, the price tiers and the schedule.
Data only (no state, no imports from the game), so game/spend_content.py and game/deco_content.py can register the
titles and the paintings.

Every item exists once: exactly one player will ever own it (the `auction_lots` unique index on `item` among open and
sold lots). An item a lot did not sell goes back to the pool. Ids are stored in saves and in the database: never
rename or remove one. Prices are written as they are (never through game/price_index.py): a starting price is a floor,
the players set the rest.

Kinds:
* plate  🚗 Biển số đẹp: shown in gold on the vehicle the owner rides (garage, street, profile). A free "biển tên"
         (game/garage.py) may not copy one (garage refuses the text).
* phone  📱 Số điện thoại đẹp: on the profile and on the phone (Điện thoại & đồ công nghệ).
* art    🖼️ Tranh độc bản: a painting by a fictional artist, hung at home like any wall piece (game/deco_content.py
         registers `uq_<id>` pieces that the shop never sells), with its plaque.
* land   🏞️ Quyền đặt tên danh thắng: a lake, a hill, a pier named after the winner for good ("Hồ Lan Mây"), on the
         town map's 🏞️ Danh thắng board.
* title  👑 Danh hiệu độc bản: beside the name in chat (`tt`, live/honours.py) and worn from Phong cách (spend.py).
"""
from __future__ import annotations

# ---------------------------------------------------------------- tiers: the starting price and the fixed step
# The next bid is at least max(high + PCT %, high + step); the first bid at least the starting price.
TIERS = {
    1: dict(start=5_000, step=500, name='Phổ thông'),
    2: dict(start=50_000, step=2_500, name='Quý hiếm'),
    3: dict(start=500_000, step=25_000, name='Huyền thoại'),
}
PCT = 5
QUICK = (1, 2, 5)              # the lot card's quick raises: the minimum step × 1, × 2, × 5

# ---------------------------------------------------------------- the schedule (Vietnam time)
# Each Vietnam day has 1–3 lots, deterministic from the date (game/auction.py plan()): slot 1 is a tier-1 lot, slot 2
# a tier-2 one, slot 3 a tier-3 one. They open after the evening peak (17:30–20:00) and run 24 hours, so they also end
# after it; the slots are 30 minutes apart so their last minutes do not overlap.
OPEN_HOUR, OPEN_MIN = 20, 30
SLOT_GAP_MIN = 30
HOURS = 24
COUNTS = (1, 2, 2, 3)          # the day's lot count: COUNTS[hash(date) % 4]
SNIPE_SECS = 300               # a bid in the last 5 minutes adds 5 minutes
SNIPE_CAP_SECS = 6 * 3600      # never more than 6 hours past the planned end
ACCOUNT_DAYS = 3               # an account at least this many days old may bid (real days)

KINDS = (
    ('plate', '🚗', 'Biển số đẹp'),
    ('phone', '📱', 'Số điện thoại đẹp'),
    ('art', '🖼️', 'Tranh độc bản'),
    ('land', '🏞️', 'Đặt tên danh thắng'),
    ('title', '👑', 'Danh hiệu độc bản'),
)
KIND_EMOJI = {k: e for k, e, _ in KINDS}
KIND_NAME = {k: n for k, _, n in KINDS}


def _p(iid, tier, text):
    return dict(id=iid, kind='plate', tier=tier, name=text, emoji='🚗')


def _ph(iid, tier, text):
    return dict(id=iid, kind='phone', tier=tier, name=text, emoji='📱')


def _art(iid, tier, name, artist, year, colors, motif):
    return dict(id=iid, kind='art', tier=tier, name=name, emoji='🖼️', artist=artist, year=year, colors=colors, motif=motif)


def _land(iid, tier, base, emoji, where):
    return dict(id=iid, kind='land', tier=tier, name=f'{base} ···', emoji=emoji, base=base, where=where)


def _title(iid, tier, emoji, name, short):
    return dict(id=iid, kind='title', tier=tier, name=name, emoji=emoji, short=short)


ITEMS = (
    # 🚗 plates (≤ 12 characters, upper case, as printed)
    _p('pl_29a88888', 3, '29A-888.88'), _p('pl_51g99999', 3, '51G-999.99'), _p('pl_30k66666', 2, '30K-666.66'),
    _p('pl_may6666', 2, 'Mây-6666'), _p('pl_68loc68', 2, '68-LỘC-68'), _p('pl_88phat88', 2, '88-PHÁT-88'),
    _p('pl_may0001', 1, 'Mây-0001'), _p('pl_43a77777', 1, '43A-777.77'), _p('pl_may2026', 1, 'Mây-2026'),
    _p('pl_39tai39', 1, '39-TÀI-39'), _p('pl_may8888', 3, 'Mây-8888'), _p('pl_15a11111', 1, '15A-111.11'),
    # 📱 phone numbers (tứ quý, ngũ quý, sảnh)
    _ph('ph_0999999999', 3, '0999.999.999'), _ph('ph_0888888888', 3, '0888.888.888'), _ph('ph_0909090909', 2, '0909.090.909'),
    _ph('ph_0868686868', 2, '0868.686.868'), _ph('ph_0912345678', 2, '0912.345.678'), _ph('ph_0966666666', 2, '0966.666.666'),
    _ph('ph_0901111111', 1, '0901.11.11.11'), _ph('ph_0779797979', 1, '0779.79.79.79'), _ph('ph_0833338888', 1, '0833.33.8888'),
    _ph('ph_0356785678', 1, '0356.78.5678'),
    # 🖼️ paintings by fictional artists of the town (colors: sky, land, accent for the drawn canvas)
    _art('tr_nuoc_noi', 3, 'Mùa nước nổi', 'Lê Mây', 1998, ('#7fb3d5', '#c8a96a', '#e85d3a'), 'water'),
    _art('tr_pho_5h', 2, 'Phố Mây lúc năm giờ chiều', 'Trần Nắng', 2004, ('#f6b26b', '#8e7cc3', '#ffd966'), 'street'),
    _art('tr_ganh_hang', 2, 'Gánh hàng rong', 'Bà Tư Sơn Mài', 1987, ('#d9c27e', '#6b4f2a', '#c0392b'), 'figure'),
    _art('tr_meo_mai_ton', 1, 'Con mèo trên mái tôn', 'Út Mực Tàu', 2019, ('#a9c4eb', '#8a8a8a', '#f1c232'), 'cat'),
    _art('tr_sen_ho', 1, 'Sen hồ Mây', 'Cô Ba Lụa', 2011, ('#cfe2f3', '#6aa84f', '#e06666'), 'lotus'),
    _art('tr_den_long', 1, 'Đêm đèn lồng', 'Hai Giấy Dó', 2015, ('#1c2541', '#3a506b', '#ff9f1c'), 'lantern'),
    _art('tr_tau_cuoi', 2, 'Chuyến tàu cuối', 'Ông Sáu Than', 1979, ('#5b6c8f', '#3d3d3d', '#ffe599'), 'train'),
    _art('tr_hai_dang', 1, 'Hải đăng gió', 'Năm Muối', 2021, ('#9fc5e8', '#0b5394', '#ffffff'), 'light'),
    _art('tr_cho_tet', 2, 'Chợ Tết phố Mây', 'Tư Lụa Hồng', 1993, ('#f4cccc', '#990000', '#ffd966'), 'market'),
    _art('tr_trang_rang', 3, 'Trăng rằm trên đồi', 'Lê Mây', 2001, ('#20124d', '#38761d', '#fff2cc'), 'moon'),
    _art('tr_long_van', 3, 'Long vân sơn mài', 'Bà Tư Sơn Mài', 1982, ('#241b22', '#82342f', '#e9bf68'), 'dragon'),
    _art('tr_hac_ngoc', 2, 'Hạc trên nền ngọc', 'Cô Ba Lụa', 2007, ('#b8d6c6', '#245951', '#fff1ce'), 'cranes'),
    _art('tr_vinh_ngoc', 2, 'Vịnh ngọc ban mai', 'Năm Muối', 2018, ('#f5d6a1', '#236b70', '#df8154'), 'bay'),
    _art('tr_ngan_ha', 3, 'Ngân hà khảm trai', 'Út Mực Tàu', 2023, ('#171d3b', '#616295', '#b4e6d5'), 'galaxy'),
    _art('tr_bac_thang', 2, 'Nấc vàng trên mây', 'Lê Mây', 2009, ('#c9d9d3', '#547469', '#e5bd61'), 'terraces'),
    _art('tr_mua_pho', 1, 'Chiếc ô qua phố mưa', 'Trần Nắng', 2020, ('#66778d', '#374861', '#e7a35b'), 'rain'),
    _art('tr_cho_noi', 2, 'Chợ nổi bình minh', 'Năm Muối', 2005, ('#f5ceb1', '#4b8585', '#bc614b'), 'floating'),
    _art('tr_gom_lam', 1, 'Men lam bên cửa sổ', 'Cô Ba Lụa', 2017, ('#eadcc3', '#325e86', '#e9aa70'), 'ceramic'),
    _art('tr_ca_chep', 3, 'Cửu ngư hội thủy', 'Bà Tư Sơn Mài', 1991, ('#193c40', '#306365', '#e7ac59'), 'koi'),
    _art('tr_phuong', 3, 'Phượng hoàng ban mai', 'Tư Lụa Hồng', 1996, ('#51273f', '#9b4358', '#f0c677'), 'phoenix'),
    _art('tr_trong_dong', 3, 'Tiếng đồng ngàn năm', 'Ông Sáu Than', 1984, ('#293936', '#776047', '#d8b46c'), 'bronze'),
    _art('tr_cong_que', 2, 'Qua cổng làng xưa', 'Hai Giấy Dó', 2002, ('#e4d7b2', '#74644c', '#9caf79'), 'gate'),
    _art('tr_vuon_cuc', 1, 'Cúc trắng đầu hiên', 'Cô Ba Lụa', 2022, ('#d0ddd0', '#587a63', '#edd495'), 'daisies'),
    _art('tr_doi_che', 1, 'Đồi chè sương sớm', 'Lê Mây', 2016, ('#d7dfd0', '#3e7460', '#a8bf74'), 'tea'),
    _art('tr_mua_roi', 2, 'Sân khấu trên mặt nước', 'Hai Giấy Dó', 1999, ('#333f52', '#4e8581', '#d65d47'), 'puppet'),
    _art('tr_vuon_buom', 1, 'Cánh bướm mùa hạ', 'Út Mực Tàu', 2024, ('#ece2c5', '#537c67', '#be708f'), 'butterflies'),
    _art('tr_ngua_gio', 3, 'Ngựa gió qua đồi son', 'Bà Tư Sơn Mài', 1989, ('#d8bd8e', '#ad523f', '#f1dfaa'), 'horse'),
    _art('tr_ban_cong', 2, 'Ban công hoa giấy', 'Trần Nắng', 2013, ('#e9c591', '#6f827c', '#c3537b'), 'balcony'),
    _art('tr_thuyen_thung', 1, 'Thuyền thúng mùa gió', 'Năm Muối', 2022, ('#bcd9da', '#4f9297', '#d6ab69'), 'basket'),
    _art('tr_bon_mua', 2, 'Tứ mùa trong một khung', 'Tư Lụa Hồng', 2008, ('#f3dfc0', '#485e55', '#c57258'), 'seasons'),
    # 🏞️ landmarks named after the winner, for good
    _land('dt_ho', 3, 'Hồ', '🏞️', 'hồ lớn sau Ngoại ô'), _land('dt_doi', 2, 'Đồi', '⛰️', 'ngọn đồi thông cạnh hải đăng'),
    _land('dt_ben', 2, 'Bến', '⛵', 'bến sông chiều'), _land('dt_vuon', 1, 'Vườn', '🌳', 'vườn hoa ven hồ'),
    _land('dt_cau', 1, 'Cầu', '🌉', 'cây cầu đá cũ'), _land('dt_thac', 2, 'Thác', '💦', 'thác nhỏ trên núi'),
    # 👑 one-of-a-kind titles
    _title('dh_mat_trang', 3, '🌕', 'Người đầu tiên lên Mặt Trăng Phố Mây', 'Lên Mặt Trăng'), _title('dh_rong_vang', 3, '🐉', 'Rồng Vàng Phố Mây', 'Rồng Vàng'),
    _title('dh_ky_lan', 2, '🦄', 'Kỳ Lân Phố Mây', 'Kỳ Lân'), _title('dh_chia_khoa', 2, '🗝️', 'Người Giữ Chìa Khóa Phố', 'Giữ Chìa Khóa'),
    _title('dh_thuyen_truong', 2, '⛵', 'Thuyền Trưởng Sông Mây', 'Thuyền Trưởng'), _title('dh_cong_tuoc', 2, '🦚', 'Công Tước Phố Mây', 'Công Tước'),
    _title('dh_bac_dau', 1, '🌟', 'Ngôi Sao Bắc Đẩu', 'Sao Bắc Đẩu'), _title('dh_den_long', 1, '🏮', 'Chủ Nhân Đèn Lồng Vàng', 'Đèn Lồng Vàng'),
    _title('dh_nghe_si', 1, '🎻', 'Nghệ Sĩ Không Tên', 'Nghệ Sĩ'), _title('dh_gio_mua', 1, '🍃', 'Người Gọi Gió Mùa', 'Gọi Gió Mùa'),
)
# Fixed collection points, never a resale quote or a multiplier for money earned.
COLLECTOR_POINTS = {1: 10, 2: 40, 3: 120}
ART_NOTES = {
    'water': ('Sơn dầu', 'Ghe nhỏ lướt qua đồng ngập, giữ lại một mùa nước nổi của phố.'),
    'street': ('Sơn dầu', 'Mái nhà tím trong nắng cuối ngày, ô cửa vàng vừa lên đèn.'),
    'figure': ('Sơn mài', 'Đôi quang gánh cong trên nền son, một đời buôn bán của bà Tư.'),
    'cat': ('Mực màu', 'Chú mèo vàng canh mái tôn, chiếc đuôi vắt qua vệt trăng.'),
    'lotus': ('Lụa', 'Cánh sen hồng trên mặt hồ xanh, nét lụa mỏng như sương.'),
    'lantern': ('Giấy dó', 'Đèn lồng treo qua bờ sông, ánh đỏ rung theo sóng nước.'),
    'train': ('Than & màu', 'Đầu tàu xuyên sương, ngọn đèn cuối cùng đưa người về phố.'),
    'light': ('Màu nước', 'Hải đăng trắng trên mỏm đá, cánh buồm nhỏ đón ngọn gió.'),
    'market': ('Lụa', 'Sạp hoa, mái bạt đỏ và cành đào chen nhau buổi chợ Tết.'),
    'moon': ('Sơn dầu', 'Trăng tròn ôm sườn đồi thông, lối mòn sáng giữa trời đêm.'),
    'dragon': ('Sơn mài dát vàng', 'Rồng cuộn giữa mây son; vảy vàng được chấm từng nét trên nền sơn đen.'),
    'cranes': ('Lụa thêu', 'Đôi hạc sải cánh trên nền ngọc, viền lông thêu bằng chỉ ánh ngà.'),
    'bay': ('Lụa vẽ tay', 'Núi đá chồng lớp bên cánh buồm nâu, sương mai tan trên vịnh ngọc.'),
    'galaxy': ('Khảm trai', 'Vụn vỏ trai ghép thành dải ngân hà, sao xanh tím nổi trên nền đêm.'),
    'terraces': ('Màu nước trên lụa', 'Từng bậc lúa vàng uốn theo sườn núi, lối nhỏ đưa người lên tận mây.'),
    'rain': ('Mực & màu nước', 'Chiếc ô cam ngang con phố tím, bóng đèn vỡ thành những vệt dài trong mưa.'),
    'floating': ('Sơn dầu', 'Ba chiếc ghe chở sắc chợ sớm, cây bẹo nhô lên giữa hơi nước hồng.'),
    'ceramic': ('Màu khoáng', 'Bình men lam và nhành quả chín bên cửa sổ, hoa văn xanh giữ nét bàn tay.'),
    'koi': ('Sơn mài dát vàng', 'Chín con cá quấn thành vòng nước, vảy son và vàng nổi trên nền ngọc sẫm.'),
    'phoenix': ('Lụa thêu chỉ vàng', 'Cánh phượng mở giữa vầng sáng, đuôi dài xòe thành những dải lửa nhiều tầng.'),
    'bronze': ('Chạm đồng trên gỗ', 'Mặt trời ở tâm trống, chim lạc nối vòng bay quanh những vành đồng cổ.'),
    'gate': ('Giấy dó', 'Cổng làng soi bóng cây đa, bậc đá dẫn vào một khoảng sân vắng nắng trưa.'),
    'daisies': ('Lụa', 'Một bình cúc trắng nghiêng đầu hiên, cánh hoa nhỏ đón từng vệt nắng.'),
    'tea': ('Màu nước', 'Luống chè xanh cuộn quanh ngọn đồi, người hái chè bé xíu giữa sương mai.'),
    'puppet': ('Sơn mài', 'Chú Tễu cùng đôi cá gỗ múa trước mái thủy đình, mặt nước mang màu đèn hội.'),
    'butterflies': ('Giấy dó ép hoa', 'Ba cánh bướm khác sắc đậu giữa cành lá, những hạt phấn còn vương trên giấy.'),
    'horse': ('Sơn mài dát bạc', 'Bạch mã tung vó khỏi đồi son, bờm và đuôi kéo gió thành những dải bạc.'),
    'balcony': ('Sơn dầu', 'Hoa giấy đổ qua ban công xanh, chiếc ghế trống đợi một buổi chiều dịu nắng.'),
    'basket': ('Màu nước', 'Thúng tre nằm trên bờ cát, lưới phơi cong trước những lớp sóng xanh.'),
    'seasons': ('Bộ tứ bình trên lụa', 'Mai, sen, cúc, trúc chia bốn ô trong cùng một khung, kể hết một vòng mùa.'),
}
KIND_STORY = {
    'plate': 'Biển độc bản gắn trên chiếc xe bạn đang đi, hiện cả khi dạo phố.',
    'phone': 'Số độc bản hiện trên điện thoại và hồ sơ của chủ nhân.',
    'land': 'Tên chủ nhân gắn với danh thắng của phố sau khi thắng phiên.',
    'title': 'Danh hiệu độc bản để đeo cạnh tên, chỉ một người trong phố sở hữu.',
}
for _it in ITEMS:
    _it['collector_points'] = COLLECTOR_POINTS[_it['tier']]
    if _it['kind'] == 'art':
        _it['medium'], _it['story'] = ART_NOTES[_it['motif']]
    else:
        _it['story'] = KIND_STORY[_it['kind']]
ITEM = {it['id']: it for it in ITEMS}

# 👑 the titles, as game/spend_content.py style items (worn from Phong cách for good, never sold)
EARN = 'Thắng đấu giá'
STYLE_TITLES = tuple(dict(id=it['id'], emoji=it['emoji'], name=it['name'], price=0, need={}, earn=EARN, uq=True)
                     for it in ITEMS if it['kind'] == 'title')

# 🖼️ the paintings, as game/deco_content.py wall pieces: (cat, spot, w, h, price, cozy, rooms, name, emoji)
ART_PIECE = {f'uq_{it["id"]}': it for it in ITEMS if it['kind'] == 'art'}
ART_COZY = 3

# Words on the lot card (≤ 30 words a screen, docs/UI_KIT.md)
ANON = 'Ẩn danh'
GONE = 'Một người chơi'
