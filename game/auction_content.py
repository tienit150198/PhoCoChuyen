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
* vehicle 🏎️ Xe bản giới hạn (owner 16/10): a numbered car, motorbike, yacht or private plane in a special paint, one of a
         kind. Won, it joins the garage like a bought vehicle (game/garage.py: the base model's ride, fuel, trip and
         upkeep), never sold in the shop and never sold back (the xu were burned at the auction: nothing to refund).
* reg    ✈️ Số đăng ký tàu bay ("VN-A888"): the plate of a private plane.
* hull   ⚓ Biển tên du thuyền: the name painted on a yacht's hull.
  The three plate kinds (plate, reg, hull) are attached to one of the owner's vehicles of the right group (PLATE_FIT,
  jr_garage_plate in game/garage.py) and moved between them at will; one plate a vehicle.
Since 20/10 (owner: "thêm nhiều đồ mới cho đấu giá nhé, thêm nhiều vào và ứng dụng được"), three kinds more, each with
a use inside the game's existing caps (kept in journey.uniq_y, game/auction.py Y_KEY):
* decor   🪑 Đồ trang trí độc bản: a one-of-a-kind piece of furniture (`uq_<id>` in game/deco_content.py, never sold
          by the shop, never sold back) shaped like its `base` piece: placed at home from the bag, it counts its Ấm cúng
          (the base's + DECO_COZY[tier]) and stands in for its base (and `alt`) in the theme sets. The morning bonus
          stays the home's steps (reno.COZY_STEPS / deco.RENT_STEPS): one piece never lifts it past them.
* petgear 🐾 Đồ thú cưng độc bản: an existing wardrobe piece (`piece`, game/pet_wardrobe_content.py) at a rank the shop
          never sells (`rank`, A…SS; owner 21/10: auction pet gear stops at SS, SSS only by fusing), straight into Tủ đồ thú cưng. Worn, it adds to the pet's work bonus like any
          piece of that rank (pet_wardrobe.BONUS_BP, LUX_BONUS, the outfit's BONUS_MAX and the pet's own day cap).
* tool    🧰 Đồ nghề độc bản: a signature tool of one workplace (`career`): each shift closed there adds TOOL_PCT[tier]
          percent of the shift's base net (the same base as 🔥 x3 and Biển đẹp). With the Biển đẹp of the same shift
          it never goes past PCT_CAP percent nor BONUS_CAP xu a shift (game/journey.py _end_of_day).
An item may carry its own `start` / `step` (a premium starting price), else its tier's.

💰 Biển đẹp +x % (owner 16/10, "gắn biển số vào và tăng % lợi nhuận (3-10% tùy mỗi cái)"): this OVERRIDES the earlier
"cosmetic and status only" rule for plates. The vehicle the player rides (garage `ride`) and that carries an auction
plate adds PLATE_PCT[its group][the plate's tier] percent (+LIMITED_PCT for a limited edition, never above PCT_CAP) to
the career income of each shift closed (game/journey.py _end_of_day: the day's base net, the same base as the 🔥 x3
bonus, at most BONUS_CAP xu a shift). One vehicle only, never stacked; locked at the shift's start (the smaller of the
start and the close counts), so switching vehicles mid-shift gains nothing. Nothing else: not the fair, the black
market, interest, investments, transfers, gifts, lì xì, the auction or selling anything.
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
# 🐾 Đồ thú cưng have a slot of their own every evening (owner 21/10 "sao lâu thế"): one piece a day at 22:00, the
# cheapest rank first (A, then S, then SS); an unsold piece comes back the next evening. The other slots never pick one.
PET_HOUR, PET_MIN = 22, 0
PET_SLOT = 9
SNIPE_SECS = 300               # a bid in the last 5 minutes adds 5 minutes
SNIPE_CAP_SECS = 6 * 3600      # never more than 6 hours past the planned end
ACCOUNT_DAYS = 3               # an account at least this many days old may bid (real days)

KINDS = (
    ('plate', '🚗', 'Biển số đẹp'),
    ('phone', '📱', 'Số điện thoại đẹp'),
    ('art', '🖼️', 'Tranh độc bản'),
    ('land', '🏞️', 'Đặt tên danh thắng'),
    ('title', '👑', 'Danh hiệu độc bản'),
    ('vehicle', '🏎️', 'Xe bản giới hạn'),
    ('reg', '✈️', 'Số đăng ký tàu bay'),
    ('hull', '⚓', 'Biển tên du thuyền'),
    ('decor', '🪑', 'Đồ trang trí độc bản'),
    ('petgear', '🐾', 'Đồ thú cưng độc bản'),
    ('tool', '🧰', 'Đồ nghề độc bản'),
)
# The kinds journey.uniq.own holds: every build since it opened validates that block strictly (game/auction.py), so
# the newer kinds live in journey.uniq_x (game/auction.py X_KEY), which an older build keeps without reading.
OLD_KINDS = ('plate', 'phone', 'art', 'land', 'title')
NEW_KINDS = ('vehicle', 'reg', 'hull')
# 20/10: every build since 16/10 validates journey.uniq_x.own strictly too (NEW_KINDS), so these live in journey.uniq_y.
Y_KINDS = ('decor', 'petgear', 'tool')
DECO_COZY = {1: 1, 2: 2, 3: 3}   # 🪑 Ấm cúng a one-of-a-kind piece adds over its base piece's
TOOL_PCT = {1: 2, 2: 3, 3: 4}    # 🧰 percent of a shift's base net, by tier (with Biển đẹp: never above PCT_CAP)

# ---------------------------------------------------------------- 💰 Biển đẹp +x % (see the module's docstring)
PLATE_KINDS = ('plate', 'reg', 'hull')
PLATE_FIT = {'plate': ('bike', 'car'), 'reg': ('plane',), 'hull': ('boat',)}   # the garage groups a plate goes on
NO_PLATE = ('xe_dap', 'xe_dap_dien')   # pedal bikes carry no plate (game/garage.py ids)
PLATE_PCT = {                  # percent by the vehicle's group and the plate's tier (1, 2, 3)
    'bike': (3, 4, 5),
    'car': (4, 5, 7),
    'boat': (5, 6, 8),
    'plane': (5, 7, 9),
}
LIMITED_PCT = 1                # a limited edition (kind vehicle) carrying the plate: one point more
PCT_CAP = 10                   # never more, whatever the table says
BONUS_CAP = 2000               # xu one shift's bonus pays at most
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


def _veh(iid, tier, emoji, name, base, paint, serial, desc):
    """A limited edition: `iid` is also its garage id (≤ 24 characters, game/garage.py ID_RE); `base` the shop model
    whose ride, fuel, trip and upkeep it keeps; `paint` one of game/garage.py SPECIAL_PAINTS; `serial` its number."""
    return dict(id=iid, kind='vehicle', tier=tier, name=name, emoji=emoji, base=base, paint=paint, serial=serial, desc=desc)


def _reg(iid, tier, text):
    return dict(id=iid, kind='reg', tier=tier, name=text, emoji='✈️')


def _hull(iid, tier, text):
    return dict(id=iid, kind='hull', tier=tier, name=text, emoji='⚓')


def _deco(iid, tier, emoji, name, base, glow, desc, alt=()):
    """🪑 `iid` ≤ 21 characters (the bag's piece is `uq_<iid>`, game/reno.py _ID); `base` the deco piece whose size, spot,
    rooms and tags it takes; `alt` other pieces it stands in for in a theme set; `glow` the sparkle's colour."""
    return dict(id=iid, kind='decor', tier=tier, name=name, emoji=emoji, base=base, alt=tuple(alt), glow=glow, desc=desc)


PET_RANK_MAX = 5   # 🐾 SS: SSS pet gear is never sold at auction (owner 21/10 "đồ thú cưng 3S sao đấu giá được, 2S thôi")


# 🐾 the pet pieces' own starting price and step by rank (owner 21/10 "giá mở thấp quá": SS 1tr, S 100k, A 20k)
PET_START = {5: (1_000_000, 50_000), 4: (100_000, 5_000), 3: (20_000, 1_000)}


def _pet(iid, tier, emoji, name, piece, rank, desc):
    """🐾 `piece` a game/pet_wardrobe_content.py id every build since 2.4.56 knows; `rank` 3 A … 5 SS (RANK_MAX: never SSS at auction, owner 21/10)."""
    start, step = PET_START[rank]
    return dict(id=iid, kind='petgear', tier=tier, name=name, emoji=emoji, piece=piece, rank=rank, desc=desc, start=start, step=step)


def _tool(iid, tier, emoji, name, career, desc, **price):
    """🧰 the workplace `career` it works for (a game/content.py career id)."""
    return dict(id=iid, kind='tool', tier=tier, name=name, emoji=emoji, career=career, desc=desc, **price)


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
    # 🏎️ limited editions (16/10): the id is the garage id too (never renamed)
    _veh('lx_xe_so_81', 1, '🏍️', 'Cub Kỷ Niệm số 81', 'xe_so', 'kem_co', '81/81',
         'Chiếc Cub cuối của lô kỷ niệm: yên da nâu, tem số 81 trên ốp sườn.'),
    _veh('lx_xe_ga_01', 2, '🛵', 'Tay ga Ngọc Bích số 01', 'xe_ga', 'ngoc_bich', '01/01',
         'Sơn ngọc bích pha nhũ, mạ crôm từng con ốc. Chạy ngang chợ là ai cũng hỏi.'),
    _veh('lx_mui_tran_07', 2, '🏎️', 'Mui trần Rượu Vang số 07', 'mui_tran', 'do_ruou', '07/07',
         'Đỏ rượu vang, vô lăng gỗ, ghế da khâu tay. Chiếc thứ bảy và cũng là chiếc cuối.'),
    _veh('lx_sieu_xe_01', 3, '🚘', 'Tia Chớp Vàng Kim số 01', 'sieu_xe', 'vang_kim', '01/01',
         'Siêu xe phủ vàng kim, cửa cánh chim. Cả phố chỉ có một chiếc.'),
    _veh('lx_du_thuyen_01', 3, '🛳️', 'Ngọc Trai Đêm số 01', 'sieu_du_thuyen', 'xanh_dem', '01/01',
         'Siêu du thuyền sơn xanh đêm, boong gỗ, đèn sao trên mũi. Neo ở bến là cả vịnh ngoái nhìn.'),
    _veh('lx_phan_luc_01', 3, '✈️', 'Phản lực Cánh Mây số 01', 'phan_luc', 'bach_kim', '01/01',
         'Phản lực tám ghế phủ bạch kim, cánh vẽ mây bạc. Đậu ở sân bay tư nhân.'),
    # ✈️ plane registrations, ⚓ yacht names (as painted)
    _reg('rg_vna888', 3, 'VN-A888'), _reg('rg_vna168', 2, 'VN-A168'), _reg('rg_vna686', 2, 'VN-A686'),
    _reg('rg_vna123', 1, 'VN-A123'),
    _hull('hn_hoang_hon', 3, 'HOÀNG HÔN VÀNG'), _hull('hn_ngoc_may', 2, 'NGỌC MÂY'), _hull('hn_sao_bien', 1, 'SAO BIỂN 01'),
    # ---------------------------------------------------------------- 20/10: "thêm nhiều đồ mới … và ứng dụng được"
    # 🏎️ limited editions: the garage's ride, trips and upkeep of their base model; a plate on one pays +LIMITED_PCT more
    _veh('lx_cub_50', 1, '🏍️', 'Cub Đồng Cổ số 50', 'xe_so', 'dong_co', '50/50',
         'Cub đời đầu phủ màu đồng cổ, yên da bò khâu tay. Chiếc thứ 50, chiếc cuối của lô.'),
    _veh('lx_xe_ga_88', 1, '🛵', 'Tay ga Hồng Ngọc số 88', 'xe_ga', 'hong_ngoc', '88/88',
         'Sơn hồng ngọc ánh kim, gương tròn mạ crôm. Đỗ trước tiệm là có người xin chụp ảnh.'),
    _veh('lx_mini_02', 1, '🚗', 'Mini Ngọc Trai số 02', 'o_to_mini', 'ngoc_trai', '02/02',
         'Ô tô mini sơn trắng ngọc trai, mui kẻ sọc vàng. Len hẻm nhỏ mà vẫn sang.'),
    _veh('lx_suv_09', 2, '🚙', 'SUV Đêm Nhung số 09', 'o_to_suv', 'den_nhung', '09/09',
         'SUV bảy chỗ sơn đen nhung, ghế da bò, đèn viền xanh. Chở cả nhà về quê ai cũng ngoái nhìn.'),
    _veh('lx_buom_03', 2, '⛵', 'Buồm Hoàng Hôn số 03', 'thuyen_buom', 'cam_hoang_hon', '03/03',
         'Thuyền buồm thân gỗ, cánh buồm nhuộm màu hoàng hôn. Giương buồm lúc chiều là đẹp nhất sông.'),
    _veh('lx_canh_quat_01', 2, '🛩️', 'Cánh quạt Ngọc Trai số 01', 'may_bay_nho', 'ngoc_trai', '01/01',
         'Máy bay hai chỗ sơn ngọc trai, cánh quạt gỗ đánh vecni. Cất cánh từ đường băng cỏ.'),
    _veh('lx_truc_thang_01', 3, '🚁', 'Trực thăng Đồng Cổ số 01', 'truc_thang', 'dong_co', '01/01',
         'Trực thăng bốn ghế phủ đồng cổ, ghế da nâu. Đáp xuống sân thượng là cả phố nhìn lên.'),
    dict(_veh('lx_sieu_xe_02', 3, '🚘', 'Tia Chớp Hồng Ngọc số 02', 'sieu_xe', 'hong_ngoc', '02/02',
              'Song sinh với Tia Chớp Vàng Kim: sơn hồng ngọc, cửa cánh chim, mâm vàng. Chỉ hai chiếc trong phố.'),
         start=1_000_000, step=50_000),
    # 🚗 ✈️ ⚓ plates: Biển đẹp +x % on the vehicle they are attached to
    _p('pl_30l99999', 3, '30L-999.99'), _p('pl_51k88888', 3, '51K-888.88'), _p('pl_29k68686', 2, '29K-686.86'),
    _p('pl_79a56789', 2, '79A-567.89'), _p('pl_may1975', 1, 'Mây-1975'), _p('pl_65a12345', 1, '65A-123.45'),
    _p('pl_may2468', 1, 'Mây-2468'),
    _reg('rg_vna999', 3, 'VN-A999'), _reg('rg_vna386', 2, 'VN-A386'), _reg('rg_vna520', 1, 'VN-A520'),
    _hull('hn_rong_bien', 3, 'RỒNG BIỂN'), _hull('hn_trang_ram', 2, 'TRĂNG RẰM'), _hull('hn_bien_ngoc', 1, 'BIỂN NGỌC 07'),
    # 👑 titles: worn from Phong cách, beside the name in chat with the one-of-a-kind frame
    _title('dh_phuong_hoang', 3, '🔥', 'Phượng Hoàng Phố Mây', 'Phượng Hoàng'),
    _title('dh_ngan_ha', 3, '🌌', 'Chủ Nhân Dải Ngân Hà', 'Ngân Hà'),
    _title('dh_hoang_hon', 2, '🌇', 'Người Giữ Hoàng Hôn', 'Giữ Hoàng Hôn'),
    _title('dh_hai_dang', 2, '🗼', 'Ngọn Hải Đăng Của Phố', 'Hải Đăng'),
    _title('dh_ca_phe', 1, '☕', 'Tri Kỷ Quán Cà Phê', 'Tri Kỷ Cà Phê'),
    _title('dh_mua_sao', 1, '🌠', 'Người Nhặt Sao Rơi', 'Nhặt Sao Rơi'),
    # 🪑 one-of-a-kind furniture (bag → home): Ấm cúng and the theme sets of their base piece
    _deco('dc_sap_kham', 3, '🪵', 'Sập gụ khảm xà cừ', 'sap_go', '#f3e3c0',
          'Sập gỗ gụ trăm năm, mặt khảm xà cừ hình tứ linh. Trải chiếu ngồi pha trà là cả nhà quây quần.'),
    _deco('dc_bonsai_sanh', 3, '🌳', 'Bonsai sanh trăm tuổi', 'bonsai', '#b8e39a',
          'Cây sanh dáng trực, rễ ôm đá, ba đời nghệ nhân uốn tỉa. Đặt ở hiên là khách nào cũng dừng chân.'),
    _deco('dc_piano_go', 3, '🎹', 'Piano gỗ hồng đời 1930', 'piano', '#f6cfa8',
          'Đàn piano đứng gỗ hồng, phím ngà đã ngả màu, chân nến đồng hai bên. Tiếng đàn ấm cả căn phòng.', alt=('dan',)),
    _deco('dc_dong_ho_phap', 2, '🕰️', 'Đồng hồ quả lắc Pháp 1920', 'dong_ho_qua_lac', '#e9c46a',
          'Vỏ gỗ sồi chạm lá nho, quả lắc đồng vàng. Mỗi giờ điểm chuông vang khắp nhà.'),
    _deco('dc_den_chum', 2, '💎', 'Đèn chùm pha lê cung điện', 'den_chum', '#d6f1ff',
          'Ba tầng pha lê, trăm hạt chuông nhỏ bắt ánh đèn. Bật lên là trần nhà như có sao.'),
    _deco('dc_binh_chu_dau', 2, '🏺', 'Bình gốm Chu Đậu cổ', 'binh_gom', '#9cc6e8',
          'Men lam vẽ chim công giữa hoa sen, đáy còn dấu lò cũ. Trưng ở góc phòng khách là đủ chuyện kể.'),
    _deco('dc_am_tu_sa', 1, '🍵', 'Bộ ấm tử sa ngàn năm', 'am_chen', '#d9895f',
          'Ấm đất tím mỏng như giấy, nắp khít không lọt hơi, bốn chén quân. Trà pha ra thơm lâu.'),
    _deco('dc_mai_co_thu', 1, '🌼', 'Mai vàng cổ thụ', 'cay_mai', '#ffe07a',
          'Gốc mai già xù xì, nở năm cánh vàng rực cả năm trong chậu men rạn. Nhà có mai là Tết quanh năm.'),
    _deco('dc_den_keo_quan', 1, '🏮', 'Đèn kéo quân phố Hội', 'den_keo_quan', '#ffb547',
          'Đèn lụa đỏ, bóng ngựa và người kéo quân xoay đều quanh ngọn nến. Đêm nào cũng như Trung thu.'),
    # 🐾 wardrobe pieces at a rank the shop never sells: straight into Tủ đồ thú cưng
    _pet('pw_vong_kc_ss', 3, '💎', 'Vòng kim cương hạng SS', 'vong_kim_cuong', 5,
         'Vòng kim cương dòng sang, hạng SS. Muốn lên SSS thì phải tự ghép.'),
    _pet('pw_vm_kc_ss', 3, '👑', 'Vương miện kim cương hạng SS', 'vuong_mien_kim_cuong', 5,
         'Bảy viên kim cương xếp hình ngôi sao, hạng SS. Bé đội vào là cả xóm cúi chào.'),
    _pet('pw_canh_phuong_ss', 3, '🔥', 'Cánh phượng hoàng hạng SS', 'canh_phuong_hoang', 5,
         'Đôi cánh lửa dòng sang, hạng SS. Bé đi đâu là ánh vàng theo đó.'),
    _pet('pw_kinh_kc_s', 2, '💠', 'Kính kim cương hạng S', 'kinh_kim_cuong', 4,
         'Gọng bạch kim viền kim cương, hạng S. Nắng chiếu vào là lóa cả góc phố.'),
    _pet('pw_ao_hoang_gia_s', 2, '🦸', 'Áo choàng hoàng gia hạng S', 'ao_choang_hoang_gia', 4,
         'Áo choàng nhung đỏ viền lông trắng, hạng S. Mặc vào là thành vua của khu phố.'),
    _pet('pw_canh_rong_a', 1, '🐉', 'Cánh rồng vàng hạng A', 'canh_rong_vang', 3,
         'Đôi cánh rồng vảy vàng, hạng A, mạnh hơn hẳn đồ ở tiệm.'),
    # 🧰 a workplace's signature tool: +TOOL_PCT[tier] % of each shift there (with Biển đẹp never above PCT_CAP)
    _tool('tl_espresso', 3, '☕', 'Máy espresso Ý đời 1961', 'cafe_bakery',
          'Cỗ máy đòn bẩy mạ crôm, ba vòi, đồng hồ áp suất kim vàng. Tách nào cũng lớp crema dày như kem.',
          start=800_000, step=40_000),
    _tool('tl_may_anh', 3, '📷', 'Máy ảnh phim ống kính vàng', 'photobooth',
          'Thân đồng đen, ống kính viền vàng, màn trập kêu tách giòn tan. Ảnh chụp ra khách nào cũng đòi in thêm.'),
    _tool('tl_quay_go', 2, '🧮', 'Quầy gỗ lim và bàn tính cổ', 'grocery',
          'Quầy gỗ lim lên nước bóng, bàn tính hạt ngà của bà chủ đời đầu. Khách đứng trước quầy là muốn mua thêm.'),
    _tool('tl_noi_pho', 2, '🍲', 'Nồi nước dùng đồng trăm lít', 'pho',
          'Nồi đồng gò tay, ninh xương suốt đêm không cạn. Nước phở trong mà ngọt sâu.'),
    _tool('tl_may_may', 2, '🧵', 'Máy may đạp chân đời 1930', 'clothing',
          'Thân gang sơn đen chữ vàng, bàn đạp hoa văn, chạy êm không một tiếng kẹt. Đường may thẳng tắp.'),
    _tool('tl_keo_hoa', 1, '✂️', 'Kéo cắt hoa thép rèn tay', 'florist',
          'Thép rèn trăm lớp, cán gỗ mun, cắt cành một nhát là ngọt. Hoa cắm lâu tàn hơn.'),
    _tool('tl_do_nghe', 1, '🔧', 'Hộp đồ nghề mạ vàng chú Tư', 'repair',
          'Hộp gỗ ba tầng, cờ lê mỏ lết mạ vàng, tua vít đủ cỡ. Món gì hỏng cũng có đồ vừa tay.'),
    _tool('tl_binh_lac', 1, '🧋', 'Bình lắc trà sữa bạc chạm hoa', 'milk_tea',
          'Bình bạc chạm hoa sen, nắp khít, lắc ra lớp bọt mịn như mây. Ly nào cũng đều tay.'),
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
    'plate': 'Biển độc bản gắn lên xe máy hoặc ô tô, hiện cả khi dạo phố. Đi xe có biển đẹp: lợi nhuận mỗi ca tăng thêm.',
    'phone': 'Số độc bản hiện trên điện thoại và hồ sơ của chủ nhân.',
    'land': 'Tên chủ nhân gắn với danh thắng của phố sau khi thắng phiên.',
    'title': 'Danh hiệu độc bản để đeo cạnh tên, chỉ một người trong phố sở hữu.',
    'reg': 'Số đăng ký độc bản gắn lên máy bay riêng. Đi máy bay có biển đẹp: lợi nhuận mỗi ca tăng thêm.',
    'hull': 'Tên độc bản sơn trên mạn du thuyền. Đi du thuyền có biển đẹp: lợi nhuận mỗi ca tăng thêm.',
}
for _it in ITEMS:
    _it['collector_points'] = COLLECTOR_POINTS[_it['tier']]
    if _it['kind'] == 'art':
        _it['medium'], _it['story'] = ART_NOTES[_it['motif']]
    elif _it['kind'] in ('vehicle',) + Y_KINDS:
        _it['story'] = _it['desc']
    else:
        _it['story'] = KIND_STORY[_it['kind']]
ITEM = {it['id']: it for it in ITEMS}
LIMITED = tuple(it for it in ITEMS if it['kind'] == 'vehicle')   # game/garage.py adds them to its catalogue

# 👑 the titles, as game/spend_content.py style items (worn from Phong cách for good, never sold)
EARN = 'Thắng đấu giá'
STYLE_TITLES = tuple(dict(id=it['id'], emoji=it['emoji'], name=it['name'], price=0, need={}, earn=EARN, uq=True)
                     for it in ITEMS if it['kind'] == 'title')

# 🖼️ the paintings, as game/deco_content.py wall pieces: (cat, spot, w, h, price, cozy, rooms, name, emoji)
ART_PIECE = {f'uq_{it["id"]}': it for it in ITEMS if it['kind'] == 'art'}
ART_COZY = 3
# 🪑 the one-of-a-kind furniture, as game/deco_content.py pieces (registered there from their base piece)
DECO_PIECE = {f'uq_{it["id"]}': it for it in ITEMS if it['kind'] == 'decor'}
# 🧰 the signature tools by workplace (one each)
TOOLS = {it['career']: it for it in ITEMS if it['kind'] == 'tool'}

# Words on the lot card (≤ 30 words a screen, docs/UI_KIT.md)
ANON = 'Ẩn danh'
GONE = 'Một người chơi'
