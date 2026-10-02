"""🪴 Bày trí phòng (game/deco.py): the furniture catalogue, the rooms of every place you can live in drawn as a
grid, the theme sets and the neighbours who drop by. Data only (no state).

Grid: a room is `cols` columns wide; its back wall has `wrows` rows of hanging spots (0 outdoors), its floor `frows`
rows from the back (row 0, against the wall) to the front. public/js/v4/deco-art.js draws one floor cell 40 × 30
and one wall cell 40 × 34 (a cosy 3/4 front view).

An item (ITEMS) has a spot: 'wall' (hangs on the back wall), 'floor' (stands on the floor), 'rug' (lies under the
furniture: only rugs block rugs) or 'top' (a small thing set on a table, a shelf, a bed, a kitchen counter, or on
a free floor cell). `w` × `h` cells (floor/rug: columns × rows of depth; wall: columns × rows). `surface` > 0: the
height of its top in the drawing, and small things can sit on it. `rooms`: the room types it suits. `tags`: what
the theme sets look for. Ids are stored in saves: never rename or remove one (the first 27 came with 1.2.0).

Fixtures (FIX in a room): the window, the door, the kitchen counter, the attic's sloping roof, the dorm's pillow…
drawn by the room and blocking their cells; a counter is a surface too. `fix` stays exactly as 1.3.2 had it (the grid
mirror an older build reads, game/deco.py); built-ins added since then (the dorm's shelf) are in `more`.

Since 1.4 pieces stand anywhere (game/deco.py, free placement): positions are units, U to a cell (x across, y from the
back of the floor or the top of the wall). FIX_FREE says what each fixture does there: which ones keep pieces off
(`block`; a doormat by the door and curtains over a window are fine), which ones small things stand on (`top`: the
height of a floor surface; `ledge`: where a wall shelf's plank is, from the top of its wall cells) and how many
(`hold` a cell of width). An item's `ledge` (a wall shelf) works the same way. SKINS: wallpapers, floors, the bunk's sheets.
"""
from __future__ import annotations

# Room types (a room's `type`; an item lists the types it suits).
LIVE = ('living', 'bed', 'bed2', 'studio')
SLEEP = ('bed', 'bed2', 'studio')
IN = ('living', 'bed', 'bed2', 'kitchen', 'studio')
OUT = ('balcony', 'yard')
BATH = ('bath',)                   # 1.4.11: a home's own bathroom
WALLS = IN + ('loft', 'bunk') + BATH
SMALL = IN + ('loft', 'bunk')
# 1.4.11: 'bathc' is the shared bathroom of the dorm and Bà Tám's house (only your own small things), 'pool' a villa's
# pool deck (outdoors: no wall).
TYPES = IN + OUT + ('loft', 'bunk') + BATH + ('bathc', 'pool')
POOLSIDE = ('pool', 'yard')

CATS = (('bed', '🛏️', 'Giường, tủ & thảm'), ('table', '🪑', 'Bàn ghế'), ('light', '💡', 'Đèn'), ('plant', '🪴', 'Cây & hoa'),
        ('wall', '🖼️', 'Trang trí tường'), ('fun', '🧸', 'Đồ chơi & tiện ích'), ('bath', '🛁', 'Nhà tắm'),
        ('pool', '🏖️', 'Hồ bơi & sân vườn'), ('le', '🏮', 'Trung thu & Tết'))
SPOTS = ('wall', 'floor', 'rug', 'top')


def _i(cat, spot, w, h, price, cozy, rooms, name, emoji, tags=(), surface=0, ledge=0):
    return dict(cat=cat, spot=spot, w=w, h=h, price=price, cozy=cozy, rooms=tuple(rooms), name=name, emoji=emoji,
                tags=tuple(tags), surface=surface, ledge=ledge)


ITEMS = {
    # 1.2.0 (names, prices and Ấm cúng unchanged)
    'sofa': _i('table', 'floor', 3, 1, 180, 3, ('living', 'studio'), 'Sofa vải', '🛋️', ('seat', 'soft')),
    'ban_tra': _i('table', 'floor', 2, 1, 70, 1, ('living', 'studio', 'loft') + OUT + ('pool',), 'Bàn trà', '🫖', ('table',), surface=14),
    'giuong': _i('bed', 'floor', 3, 2, 220, 3, SLEEP, 'Giường gỗ', '🛏️', ('bed',), surface=16),
    'tv': _i('fun', 'floor', 2, 1, 240, 2, LIVE, 'Ti vi', '📺', ('screen',)),
    'be_ca': _i('fun', 'floor', 2, 1, 150, 3, ('living', 'studio'), 'Bể cá', '🐠', ('water',)),
    'ke_sach': _i('bed', 'floor', 2, 1, 90, 2, LIVE, 'Kệ sách', '📚', ('books',)),
    'ban_lam_viec': _i('table', 'floor', 2, 1, 120, 1, LIVE, 'Bàn làm việc', '💻', ('desk',), surface=24),
    'dan': _i('fun', 'floor', 1, 1, 110, 2, LIVE + ('loft',), 'Đàn ghi-ta', '🎸', ('music',)),
    'gau_bong': _i('fun', 'top', 1, 1, 35, 1, LIVE + ('loft', 'bunk'), 'Gấu bông', '🧸', ('soft',)),
    'cay_canh': _i('plant', 'floor', 1, 1, 40, 2, IN + OUT + ('loft',) + BATH + ('pool',), 'Chậu cây cảnh', '🪴', ('plant',)),
    'ghe_may': _i('table', 'floor', 1, 1, 70, 1, IN + OUT + ('pool',), 'Ghế mây', '🪑', ('seat',)),
    'tu_lanh': _i('fun', 'floor', 1, 1, 260, 2, ('kitchen', 'studio'), 'Tủ lạnh', '🧊', ('kitchen',)),
    'ban_an': _i('table', 'floor', 2, 1, 160, 2, ('kitchen', 'living', 'studio'), 'Bàn ăn', '🍽️', ('table',), surface=24),
    'noi_com': _i('fun', 'top', 1, 1, 45, 1, ('kitchen', 'studio'), 'Nồi cơm điện', '🍚', ('kitchen',)),
    'may_giat': _i('fun', 'floor', 1, 1, 200, 1, ('kitchen',) + OUT + BATH, 'Máy giặt', '🫧'),
    'hoa_giay': _i('plant', 'floor', 1, 1, 50, 2, OUT + ('pool',), 'Chậu hoa giấy', '🌺', ('plant', 'flower')),
    'ban_ngoai': _i('table', 'floor', 2, 1, 160, 2, OUT + ('pool',), 'Bàn ô ngoài trời', '⛱️', ('table',), surface=22),
    'tranh': _i('wall', 'wall', 2, 1, 70, 2, WALLS, 'Tranh phong cảnh', '🖼️', ('art',)),
    'den_long': _i('light', 'wall', 1, 1, 35, 1, WALLS, 'Đèn lồng', '🏮', ('lamp',)),
    'den_nhay': _i('light', 'wall', 2, 1, 30, 2, WALLS, 'Dây đèn nháy', '✨', ('lamp',)),
    'dong_ho': _i('wall', 'wall', 1, 1, 50, 1, WALLS, 'Đồng hồ treo tường', '🕰️'),
    'guong': _i('wall', 'wall', 1, 1, 45, 1, WALLS, 'Gương tròn', '🪞'),
    'ke_cay': _i('plant', 'wall', 1, 1, 55, 2, WALLS, 'Kệ treo cây', '🌿', ('plant',)),
    'anh': _i('wall', 'wall', 1, 1, 25, 1, WALLS, 'Khung ảnh kỷ niệm', '📸', ('art',)),
    'lich': _i('wall', 'wall', 1, 1, 15, 1, WALLS, 'Lịch treo tường', '📅'),
    'may_lanh': _i('fun', 'wall', 2, 1, 320, 2, LIVE + ('loft',), 'Máy lạnh', '❄️'),
    'ke_bep': _i('wall', 'wall', 2, 1, 30, 1, ('kitchen', 'studio'), 'Kệ gia vị', '🧂', ('kitchen',)),
    # 1.3: Giường, tủ & thảm
    'tu_quan_ao': _i('bed', 'floor', 2, 1, 200, 2, SLEEP, 'Tủ quần áo', '🗄️'),
    'nem': _i('bed', 'floor', 2, 2, 90, 2, SLEEP + ('loft',), 'Nệm trải sàn', '🛌', ('bed', 'soft'), surface=6),
    'tu_dau_giuong': _i('bed', 'floor', 1, 1, 45, 1, SLEEP + ('loft',), 'Tủ đầu giường', '🗃️', (), surface=20),
    'ke_go': _i('bed', 'floor', 1, 1, 40, 1, IN + ('loft',), 'Kệ gỗ nhỏ', '📦', (), surface=22),
    'goi_om': _i('bed', 'top', 1, 1, 25, 1, SLEEP + ('living', 'loft', 'bunk'), 'Gối ôm hình mèo', '🐱', ('soft',)),
    'rem_giuong': _i('bed', 'wall', 1, 2, 40, 2, ('bunk',), 'Rèm giường riêng', '🎀', ('fabric',)),
    'tham': _i('bed', 'rug', 3, 2, 90, 2, LIVE + ('loft',), 'Thảm lông xù', '🟣', ('rug', 'soft')),
    'tham_hoa': _i('bed', 'rug', 2, 1, 20, 1, IN + ('loft',) + BATH, 'Thảm chùi chân hoa', '🌸', ('rug',)),
    # Bàn ghế
    'ban_hoc': _i('table', 'floor', 2, 1, 110, 2, LIVE, 'Bàn học', '✏️', ('desk',), surface=24),
    'ghe_hoc': _i('table', 'floor', 1, 1, 50, 1, IN, 'Ghế học xoay', '💺', ('seat',)),
    'ghe_luoi': _i('table', 'floor', 1, 1, 60, 2, LIVE + ('loft',), 'Ghế lười', '🫘', ('seat', 'soft')),
    'ban_xep': _i('table', 'floor', 1, 1, 35, 1, SLEEP + ('loft', 'bunk'), 'Bàn xếp mini', '📐', ('desk',), surface=12),
    'ghe_dau': _i('table', 'floor', 1, 1, 15, 1, IN + OUT + BATH + ('pool',), 'Ghế đẩu nhựa', '🔴', ('seat',), surface=16),
    'ban_gaming': _i('table', 'floor', 2, 1, 260, 2, LIVE, 'Bàn gaming', '🕹️', ('desk', 'gaming'), surface=24),
    'ghe_gaming': _i('table', 'floor', 1, 1, 180, 2, LIVE, 'Ghế gaming', '🎮', ('seat', 'gaming')),
    'xich_du': _i('table', 'floor', 2, 1, 260, 3, ('yard',), 'Xích đu gỗ', '🌳', ('seat',)),
    'vong': _i('table', 'floor', 2, 1, 70, 2, OUT + ('pool',), 'Võng dù', '🏝️', ('soft',)),
    # Đèn
    'den_ban': _i('light', 'top', 1, 1, 35, 1, SMALL, 'Đèn bàn', '💡', ('lamp',)),
    'den_cay': _i('light', 'floor', 1, 1, 80, 2, LIVE + ('kitchen',), 'Đèn cây chân gỗ', '🔦', ('lamp',)),
    'den_ngu': _i('light', 'top', 1, 1, 30, 1, SLEEP + ('living', 'loft', 'bunk'), 'Đèn ngủ cây nấm', '🍄', ('lamp',)),
    'den_tha': _i('light', 'wall', 1, 1, 65, 1, IN, 'Đèn thả giỏ mây', '🧺', ('lamp',)),
    'den_led': _i('light', 'wall', 2, 1, 45, 1, LIVE + ('loft', 'bunk'), 'Dây LED đổi màu', '🌈', ('lamp', 'gaming')),
    # Cây & hoa
    'cay_monstera': _i('plant', 'floor', 1, 1, 90, 2, IN + OUT + BATH + ('pool',), 'Cây trầu bà lá xẻ', '🌱', ('plant',)),
    'cay_luoi_ho': _i('plant', 'floor', 1, 1, 50, 1, IN + OUT + ('loft',) + BATH + ('pool',), 'Cây lưỡi hổ', '🌾', ('plant',)),
    'xuong_rong': _i('plant', 'top', 1, 1, 15, 1, SMALL + OUT + BATH + ('pool',), 'Chậu xương rồng mini', '🌵', ('plant',)),
    'binh_hoa': _i('plant', 'top', 1, 1, 30, 1, SMALL + BATH, 'Bình hoa cúc họa mi', '🌼', ('plant', 'flower')),
    'gian_rau': _i('plant', 'floor', 2, 1, 80, 2, OUT, 'Giàn rau thơm', '🥬', ('plant',)),
    # Trang trí tường
    'rem': _i('wall', 'wall', 1, 2, 60, 2, IN, 'Rèm cửa hoa nhí', '🪟', ('fabric',)),
    'poster': _i('wall', 'wall', 1, 2, 25, 1, IN + ('bunk',), 'Poster hoạt hình', '🎞️', ('art',)),
    'ke_treo': _i('wall', 'wall', 2, 1, 40, 1, WALLS, 'Kệ treo tường', '📗', ('books',)),
    'bang_ghim': _i('wall', 'wall', 2, 1, 35, 1, WALLS, 'Bảng ghim ảnh', '📌', ('art',)),
    'dong_ho_cuc_cu': _i('wall', 'wall', 1, 1, 120, 2, IN + ('loft',), 'Đồng hồ cúc cu', '🐦'),
    # Đồ chơi & tiện ích
    'quat': _i('fun', 'floor', 1, 1, 60, 1, IN, 'Quạt cây', '🌀'),
    'quat_mini': _i('fun', 'top', 1, 1, 25, 1, SMALL, 'Quạt mini để bàn', '🍃'),
    'loa': _i('fun', 'top', 1, 1, 70, 1, SMALL + BATH + ('pool',), 'Loa bluetooth', '🔊', ('music',)),
    'may_choi_game': _i('fun', 'top', 1, 1, 220, 2, LIVE + ('loft', 'bunk'), 'Máy chơi game', '👾', ('gaming', 'screen')),
    'hop_nhac': _i('fun', 'top', 1, 1, 55, 1, SMALL, 'Hộp nhạc', '🎶', ('music',)),
    'o_meo': _i('fun', 'floor', 1, 1, 45, 2, LIVE + ('loft',), 'Ổ mèo bông', '🐈', ('soft',)),
    # 1.4: a plain wall shelf, small things stand on it
    'ke_go_treo': _i('wall', 'wall', 2, 1, 30, 1, WALLS, 'Kệ gỗ treo trơn', '🪵', (), ledge=24),
    # 1.4.11: Nhà tắm (a home's bathroom; the shared one takes only your own small things)
    'bon_tam': _i('bath', 'floor', 3, 2, 300, 3, BATH, 'Bồn tắm nằm', '🛁', ('soak',), surface=14),
    'buong_tam': _i('bath', 'floor', 1, 1, 220, 2, BATH, 'Buồng tắm kính', '🚿', ('soak',)),
    'bon_rua': _i('bath', 'floor', 2, 1, 140, 2, BATH, 'Bồn rửa mặt tủ gỗ', '🚰', (), surface=26),
    'guong_tam': _i('bath', 'wall', 2, 1, 80, 1, BATH, 'Gương đèn nhà tắm', '🪞', ('lamp',)),
    'ke_khan': _i('bath', 'wall', 2, 1, 40, 1, BATH, 'Thanh treo khăn bông', '🧖', ('towel',)),
    'ke_tam': _i('bath', 'floor', 1, 1, 45, 1, BATH, 'Kệ đứng nhà tắm', '🧺', (), surface=30),
    'gio_do_tam': _i('bath', 'top', 1, 1, 20, 1, BATH + ('bathc',), 'Giỏ đồ tắm', '🧴', ('towel',)),
    'tham_tam': _i('bath', 'rug', 2, 1, 25, 1, BATH + ('bathc',), 'Thảm chân nhà tắm', '🟦', ('rug', 'soft')),
    'vit_cao_su': _i('bath', 'top', 1, 1, 10, 1, BATH + ('bathc', 'pool'), 'Vịt cao su', '🦆', ('toy', 'float')),
    # Hồ bơi & sân vườn
    'ghe_tam_nang': _i('pool', 'floor', 2, 1, 140, 2, POOLSIDE + ('balcony',), 'Ghế tắm nắng', '🌞', ('seat', 'lounge')),
    'du_che': _i('pool', 'floor', 1, 1, 90, 1, POOLSIDE + ('balcony',), 'Dù che nắng', '🌂', ('shade',)),
    'phao': _i('pool', 'floor', 1, 1, 50, 1, ('pool',), 'Phao bơi', '🛟', ('toy', 'float')),
    'lo_nuong': _i('pool', 'floor', 1, 1, 160, 2, POOLSIDE + ('balcony',), 'Lò nướng BBQ', '🍢', ('grill',)),
    'cay_dua': _i('pool', 'floor', 1, 1, 110, 2, POOLSIDE, 'Cây dừa cảnh', '🌴', ('plant',)),
    'den_vuon': _i('pool', 'floor', 1, 1, 60, 1, POOLSIDE + ('balcony',), 'Đèn sân vườn', '🕯️', ('lamp',)),
    # After 1.4.19 (KNOWN_1419): đồ nhà kiểu Việt. Phòng khách
    'sap_go': _i('table', 'floor', 3, 1, 280, 3, ('living',), 'Sập gỗ', '🪵', ('seat',), surface=16),
    'am_chen': _i('fun', 'top', 1, 1, 30, 1, SMALL + OUT + ('pool',), 'Bộ ấm chén', '🍵', ('tea',)),
    'tranh_dong_ho': _i('wall', 'wall', 2, 1, 65, 2, IN + ('loft',), 'Tranh Đông Hồ', '🐖', ('art',)),
    'dong_ho_qua_lac': _i('wall', 'wall', 1, 2, 95, 2, IN, 'Đồng hồ quả lắc', '🕰️'),
    'cay_kim_tien': _i('plant', 'floor', 1, 1, 70, 2, IN + OUT + ('loft',) + BATH + ('pool',), 'Chậu kim tiền', '🪴', ('plant',)),
    'quat_tran': _i('fun', 'wall', 2, 1, 140, 1, IN + ('loft',), 'Quạt trần', '🌀'),
    'dan_bau': _i('fun', 'floor', 2, 1, 150, 2, LIVE + ('loft',), 'Đàn bầu', '🎼', ('music',)),
    'binh_sen': _i('plant', 'top', 1, 1, 35, 1, SMALL + BATH, 'Bình gốm cắm sen', '🪷', ('plant', 'flower')),
    'radio': _i('fun', 'top', 1, 1, 60, 1, SMALL, 'Radio cát-xét', '📻', ('music',)),
    'may_may': _i('table', 'floor', 2, 1, 130, 2, LIVE + ('loft',), 'Máy may đạp chân', '🧵', (), surface=22),
    # Phòng ngủ
    'man_tuyn': _i('bed', 'wall', 3, 2, 55, 2, SLEEP + ('bunk',), 'Màn tuyn', '🛏️', ('fabric', 'soft')),
    'ban_trang_diem': _i('bed', 'floor', 2, 1, 170, 2, ('bed', 'bed2'), 'Bàn trang điểm', '💄', (), surface=24),
    'gau_bong_lon': _i('fun', 'floor', 1, 1, 95, 2, SLEEP + ('living', 'loft'), 'Gấu bông khổng lồ', '🐻', ('soft',)),
    'den_sao': _i('light', 'top', 1, 1, 45, 1, SMALL, 'Đèn chiếu sao', '🌟', ('lamp',)),
    'moc_ao': _i('bed', 'floor', 1, 1, 45, 1, LIVE + ('loft',), 'Cây treo quần áo', '🧥'),
    # Bếp
    'am_sieu_toc': _i('fun', 'top', 1, 1, 30, 1, ('kitchen', 'studio', 'living'), 'Ấm siêu tốc', '♨️', ('kitchen',)),
    'lo_vi_song': _i('fun', 'top', 1, 1, 130, 1, ('kitchen', 'studio'), 'Lò vi sóng', '⏲️', ('kitchen',)),
    'chan_bat': _i('bed', 'floor', 1, 1, 120, 2, ('kitchen',), 'Chạn bát gỗ', '🥣', ('kitchen',)),
    'tu_lanh_magnet': _i('fun', 'floor', 2, 1, 300, 3, ('kitchen',), 'Tủ lạnh dán magnet', '🧲', ('kitchen',)),
    'gio_trai_cay': _i('fun', 'top', 1, 1, 20, 1, SMALL + OUT + ('pool',), 'Giỏ trái cây', '🍊', ('fruit',)),
    # Nhà tắm, hồ bơi
    'duong_xi': _i('plant', 'wall', 1, 1, 45, 2, WALLS, 'Giỏ dương xỉ treo', '🌿', ('plant',)),
    'nen_thom': _i('light', 'top', 1, 1, 25, 1, SMALL + BATH + ('bathc',), 'Nến thơm', '🕯️', ('lamp',)),
    'ao_choang': _i('bath', 'wall', 1, 1, 35, 1, BATH, 'Áo choàng tắm', '👘', ('towel', 'soft')),
    'phao_hong_hac': _i('pool', 'floor', 2, 1, 90, 2, ('pool',), 'Phao hồng hạc', '🦩', ('toy', 'float')),
    # Ban công, sân vườn
    'bonsai': _i('plant', 'floor', 1, 1, 160, 3, OUT + ('living', 'pool'), 'Chậu bonsai', '🌳', ('plant',)),
    'long_chim': _i('pool', 'floor', 1, 1, 110, 2, OUT + ('living',), 'Lồng chim chào mào', '🐦', ('bird',)),
    'xe_dap': _i('pool', 'floor', 2, 1, 140, 1, OUT + ('living',), 'Xe đạp mini', '🚲', ('ride',)),
    'ban_co_tuong': _i('table', 'floor', 2, 1, 85, 2, OUT + ('living', 'pool'), 'Bàn cờ tướng', '♟️', ()),
    'chum_nuoc': _i('pool', 'floor', 1, 1, 55, 1, OUT + ('pool',), 'Chum sành', '🏺', ('water',)),
    # Trung thu & Tết
    'long_den_sao': _i('le', 'wall', 1, 1, 30, 1, WALLS, 'Lồng đèn ông sao', '⭐', ('lamp',)),
    'den_keo_quan': _i('le', 'top', 1, 1, 55, 2, SMALL + OUT, 'Đèn kéo quân', '🏮', ('lamp',)),
    'cay_mai': _i('le', 'floor', 1, 1, 150, 3, IN + OUT + ('loft', 'pool'), 'Chậu mai vàng', '🌼', ('plant', 'flower')),
    'canh_dao': _i('le', 'floor', 1, 1, 130, 3, IN + OUT + ('loft',), 'Bình đào Tết', '🌸', ('plant', 'flower')),
    'cau_doi': _i('le', 'wall', 2, 2, 40, 1, IN, 'Câu đối đỏ', '🧧', ('art',)),
    'mam_ngu_qua': _i('le', 'top', 1, 1, 45, 1, SMALL + OUT, 'Mâm ngũ quả', '🍍'),
}
LEGACY = tuple(ITEMS)[:27]          # the 1.2.0 catalogue (reno.py slots)
KNOWN_132 = tuple(ITEMS)[:65]       # what a 1.3.2 build knows (the grid mirror only holds these)
KNOWN_1419 = tuple(ITEMS)[:81]      # what 1.4.11–1.4.19 know (an older build keeps the others in reno.items, unshown)


# ---------------------------------------------------------------- rooms
def _fx(t, layer, x, y, w=1, h=1, surface=0):
    return dict(t=t, layer=layer, x=x, y=y, w=w, h=h, surface=surface)


def _door(x):
    """A door on the back wall: two wall rows, and the floor cell in front of it stays clear."""
    return [_fx('door', 'wall', x, 0, 1, 2), _fx('door', 'floor', x, 0)]


ROOM_NAMES = {'living': ('🛋️', 'Phòng khách'), 'bed': ('🛏️', 'Phòng ngủ'), 'bed2': ('🧸', 'Phòng ngủ nhỏ'),
              'kitchen': ('🍲', 'Bếp'), 'balcony': ('🌤️', 'Ban công'), 'yard': ('🌳', 'Sân vườn')}
_COLS = {0: 6, 1: 6, 2: 6, 3: 7, 4: 8, 5: 9}


def own_room(rid: str, wall: int, floor: int, name: str | None = None) -> dict:
    """A room of a home you own (reno.HOUSES rows: room, 1.2.0 wall slots, floor slots[, its own name])."""
    emoji, base = ROOM_NAMES[rid]
    cols = _COLS[max(0, min(5, floor))]
    out = rid in OUT
    frows = (2 if floor <= 2 else 3) if out else (3 if floor <= 3 else 4)
    wrows = 0 if out else 2
    fix: list = []
    if rid == 'living':
        fix = [_fx('window', 'wall', 1, 0, 2, 2)] + _door(cols - 1)
    elif rid in ('bed', 'bed2'):
        fix = _door(0) + [_fx('window', 'wall', cols - 3, 0, 2, 2)]
    elif rid == 'kitchen':
        fix = [_fx('counter', 'floor', 0, 0, cols - 2, 1, surface=30), _fx('splash', 'wall', 0, 1, cols - 2, 1),
               _fx('window', 'wall', 1, 0, 2, 1)] + _door(cols - 1)
    return dict(id=rid, type=rid, emoji=emoji, name=name or base, cols=cols, wrows=wrows, frows=frows, out=out, fix=fix, tags=())


# Free placement (1.4): units to a grid cell, and what each fixture does there.
U = 20
FIX_FREE = {
    'window': dict(block=True, allow=('fabric',)),   # curtains may hang over it
    'door': dict(block=True, rug=True),              # a doormat may lie in front of it
    'slope': dict(block=True),
    'splash': dict(),                                # the kitchen tiles: a spice rack hangs there
    'counter': dict(block=True, top=30, hold=2),
    'ladder': dict(block=True),
    'pillow': dict(block=True, top=9, hold=2),       # a teddy on the dorm pillow
    'shelf': dict(ledge=24, hold=2),                 # the dorm's shelf over the bunk (and the shared bathroom's)
    'shower': dict(block=True),                      # 1.4.11: the bathroom's shower on the wall
    'toilet': dict(block=True, top=40, hold=1),      # a little cactus on the cistern
    'pool': dict(block=True, allow=('float',)),      # a float or a rubber duck may go on the water
}

# Rented rooms and Bà Tám's attic (no structure to repair: the landlord's).
RENT_ROOMS = {
    'attic': (dict(id='attic', type='studio', emoji='🏚️', name='Căn gác', cols=6, wrows=2, frows=3, out=False, tags=(),
                   fix=[_fx('slope', 'wall', 0, 0, 2, 1), _fx('window', 'wall', 3, 0, 1, 1)] + _door(5)),),
    'tro_moi': (dict(id='tro', type='studio', emoji='🛏️', name='Phòng trọ', cols=7, wrows=2, frows=3, out=False, tags=(),
                     fix=[_fx('window', 'wall', 2, 0, 2, 2)] + _door(6)),
                dict(id='loft', type='loft', emoji='🪜', name='Gác lửng', cols=6, wrows=1, frows=2, out=False, tags=(),
                     fix=[_fx('ladder', 'floor', 5, 1)])),
    'ky_tuc_xa': (dict(id='bunk', type='bunk', emoji='🛏️', name='Góc giường của bạn', cols=5, wrows=2, frows=2, out=False,
                       tags=('bed',), fix=[_fx('pillow', 'floor', 0, 0)], more=[_fx('shelf', 'wall', 0, 0, 2, 1)]),),
}


# ---------------------------------------------------------------- 1.4.11: nhà tắm, hồ bơi
# Rooms every home gets with no payment: a bathroom (a home of its own: `bath`; the dorm and Bà Tám's house: the shared
# one, `bathc`, where only your own small things go) and, for the villas, the pool deck. Built from the kind of the home
# (never stored). KITS are the room templates, also sent once in the catalogue: the room you live in names them
# (deco.public `more`), so the per-save state stays small and a page loaded before 1.4.11 never sees them (it draws
# `rooms` only). NEW_ROOMS: the ids an older build does not know (deco.py keeps them out of the 1.3.2 grid mirror and
# marks the free layout's place, so an older build never refuses a save with a piece in one of them).
def _bath(cols: int, frows: int, name: str, win: int = 1) -> dict:
    """A bathroom: the shower on the left wall, a small window, the toilet by the door on the right."""
    wx = 1 if cols <= 4 else 2
    fix = [_fx('shower', 'wall', 0, 0, 1, 2), _fx('window', 'wall', wx, 0, win, 1), _fx('toilet', 'floor', cols - 2, 0)] + _door(cols - 1)
    return dict(id='bath', type='bath', emoji='🛁', name=name, cols=cols, wrows=2, frows=frows, out=False, tags=(), fix=fix)


def _pool(cols: int) -> dict:
    """The pool deck: the water in the middle, room around it for loungers, an umbrella, a grill."""
    return dict(id='pool', type='pool', emoji='🏊', name='Hồ bơi', cols=cols, wrows=0, frows=4, out=True, tags=(),
                fix=[_fx('pool', 'floor', 2, 1, cols - 4, 2)])


KITS = {
    'bath_s': _bath(4, 3, 'Nhà tắm'),
    'bath_m': _bath(5, 3, 'Nhà tắm'),
    'bath_l': _bath(7, 3, 'Phòng tắm lớn', 2),
    'bath_xl': _bath(8, 4, 'Phòng tắm lớn', 2),
    'bathc': dict(id='bath', type='bathc', emoji='🚿', name='Nhà tắm chung', cols=4, wrows=2, frows=2, out=False, tags=(),
                  fix=[_fx('shower', 'wall', 0, 0, 1, 2), _fx('shelf', 'wall', 1, 0, 2, 1), _fx('toilet', 'floor', 2, 0)] + _door(3)),
    'pool_m': _pool(8),
    'pool_l': _pool(9),
}
# The place (deco.place: 'attic', a rented room's kind, a home's kind) -> its new rooms, after the ones it had.
EXTRA_ROOMS = {
    'attic': ('bathc',), 'ky_tuc_xa': ('bathc',), 'tro_moi': ('bath_s',),
    'tap_the': ('bath_s',), 'can_ho_studio': ('bath_s',), 'can_ho_mini': ('bath_s',), 'can_ho_1pn': ('bath_m',),
    'can_ho_2pn': ('bath_m',), 'penthouse': ('bath_l',), 'nha_pho': ('bath_m',), 'nha_san': ('bath_m',),
    'biet_thu_vuon': ('bath_l', 'pool_m'), 'biet_thu_song': ('bath_xl', 'pool_l'),
}
NEW_ROOMS = ('bath', 'pool')


# ---------------------------------------------------------------- theme sets
# need: one distinct placed item per entry, all in the same room; an entry is ('tag', t) or a tuple of kinds.
# A room's own tags (the dorm bunk is a bed) fill a ('tag', …) entry too. Each set counts once per home.
SETS = {
    'hoc': dict(emoji='📚', name='Góc học tập', bonus=3, need=(('tag', 'desk'), ('tag', 'lamp'), ('tag', 'books'))),
    'xanh': dict(emoji='🌿', name='Góc xanh', bonus=3, need=(('tag', 'plant'), ('tag', 'plant'), ('tag', 'plant'))),
    'chill': dict(emoji='☁️', name='Góc chill', bonus=3, need=(('tag', 'rug'), ('tag', 'lamp'), ('tag', 'soft'))),
    'ngu': dict(emoji='😴', name='Giấc ngủ êm', bonus=3, need=(('tag', 'bed'), ('den_ngu',), ('tag', 'fabric'))),
    'game': dict(emoji='🎮', name='Góc gaming', bonus=3, need=(('ban_gaming',), ('ghe_gaming',), ('den_led', 'may_choi_game'))),
    'bep': dict(emoji='🍚', name='Bếp ấm', bonus=2, need=(('noi_com',), ('ban_an',), ('ke_bep', 'tu_lanh'))),
    'nhac': dict(emoji='🎸', name='Góc âm nhạc', bonus=2, need=(('dan',), ('loa', 'hop_nhac'))),
    'tuong': dict(emoji='🖼️', name='Bức tường kỷ niệm', bonus=2, need=(('tag', 'art'), ('tag', 'art'), ('tag', 'art'))),
    'vuon': dict(emoji='🌺', name='Vườn nhỏ', bonus=3, need=(('hoa_giay',), ('gian_rau',), ('vong', 'xich_du', 'ghe_may', 'ban_ngoai'))),
    # 1.4.11
    'spa': dict(emoji='🛁', name='Phòng tắm thư giãn', bonus=3, need=(('bon_tam', 'buong_tam'), ('ke_khan', 'gio_do_tam'), ('tag', 'plant'))),
    'resort': dict(emoji='🏖️', name='Hồ bơi nghỉ dưỡng', bonus=3, need=(('ghe_tam_nang',), ('du_che',), ('phao', 'vit_cao_su', 'phao_hong_hac'))),
    'bbq': dict(emoji='🍢', name='Tiệc nướng ngoài trời', bonus=2, need=(('lo_nuong',), ('ban_ngoai', 'ban_tra'), ('ghe_may', 'ghe_dau', 'ghe_tam_nang'))),
    # After 1.4.19. Only 'tet' can be done in a rented room or the attic (the others want a living room, a kitchen, a bedroom
    # or a yard): every set possible where you live rides in deco.public, and the attic's state stays small.
    'tet': dict(emoji='🧧', name='Góc Tết sum vầy', bonus=3, need=(('cay_mai', 'canh_dao'), ('cau_doi',), ('mam_ngu_qua',))),
    'xua': dict(emoji='🫖', name='Phòng khách xưa', bonus=3, need=(('sap_go',), ('tranh_dong_ho',), ('dong_ho_qua_lac', 'am_chen', 'radio'))),
    'hien': dict(emoji='🐦', name='Hiên nhà thong thả', bonus=2, need=(('bonsai',), ('long_chim',), ('ban_co_tuong', 'am_chen'))),
    'bep_moi': dict(emoji='🍱', name='Bếp tiện nghi', bonus=2, need=(('lo_vi_song',), ('am_sieu_toc',), ('chan_bat', 'tu_lanh_magnet'))),
    'mo': dict(emoji='🌙', name='Phòng ngủ mộng mơ', bonus=2, need=(('ban_trang_diem',), ('gau_bong_lon',), ('den_sao', 'man_tuyn'))),
}
# What a missing ('tag', t) entry is called in a hint ("Thiếu: một cây đèn").
TAG_WORDS = {'desk': 'một cái bàn', 'lamp': 'một cây đèn', 'books': 'kệ sách', 'plant': 'một chậu cây', 'rug': 'một tấm thảm',
             'soft': 'đồ bông mềm', 'bed': 'giường hoặc nệm', 'fabric': 'rèm', 'art': 'tranh, ảnh'}


# ---------------------------------------------------------------- the neighbours who drop by
# Per place: (emoji, name, lines). {item}: a placed item's name inside a sentence.
GUESTS = {
    'attic': (('👵', 'Bà Tám', ('“Gác này hồi đó trống trơn, giờ con bày {item} vô nhìn ấm hẳn.”',
                                 '“Bà mang chè lên nè. Ủa, {item} xinh quá ta!”',
                                 '“Ở gác mà gọn gàng dễ thương vầy, bà khoe cả xóm luôn.”')),),
    'tro_moi': (('👩', 'Cô Hạnh', ('“Phòng trọ cô cho thuê bao năm, chưa ai bày {item} khéo như con.”',
                                    '“Con mèo nhà cô cứ đòi chui vô phòng con, chắc tại {item} đó.”',
                                    '“Nhìn phòng này là biết người ở chăm chút lắm.”')),),
    'ky_tuc_xa': (('🎓', 'Quân', ('“Góc của bạn chill ghê, cho mình ngồi làm đồ án ké chút nha.”',
                                   '“Ủa {item} mua ở đâu vậy, chỉ mình với!”')),
                  ('🛵', 'Anh Tuấn', ('“Đi ca đêm về thấy {item} của bạn, tự nhiên thấy ấm lòng.”',
                                       '“Góc giường gì mà như homestay vậy trời.”')),
                  ('📦', 'My', ('“Cho My mượn góc giường livestream một bữa nha, {item} lên hình đẹp lắm!”',
                                 '“Bạn khéo tay ghê, My chụp hình đăng story nha.”'))),
    'home': (('👵', 'Bà Tám', ('“Nhà cửa đẹp quá con ơi, nhìn {item} là bà thích liền.”',
                                '“Bà ghé chơi chút thôi mà muốn ở lại ăn cơm luôn á.”')),
             ('🛒', 'Cô Ba', ('“Ui, {item} xinh quá! Mua ở đâu chỉ cô với.”',
                               '“Nhà con ấm cúng thiệt, bữa nào cô dẫn mấy đứa nhỏ qua chơi.”')),
             ('🧔', 'Chú Tư', ('“Chú đi ngang thấy đèn sáng nên ghé coi. Cái {item} này được đó nha!”',
                                '“Nhà gọn gàng sạch sẽ, nhìn là biết chủ nhà siêng.”'))),
}


# ---------------------------------------------------------------- wallpapers and floors (1.4)
# part 'wall' | 'floor' ('auto': either, the room as it came). price 0: free; a priced one is bought once and then
# used in any room. types: the room types it suits (None: any room with that part, but not the bunk's mattress and
# not a garden lawn; the bunk has its own sheets). Ids are stored in saves.
def _sk(part, name, price, types=None):
    return dict(part=part, name=name, price=price, types=types)


SKINS = {
    'auto': _sk('both', 'Như ban đầu', 0),
    'kem': _sk('wall', 'Sơn kem sữa', 0),
    'bac_ha': _sk('wall', 'Sơn xanh bạc hà', 0),
    'hong_dao': _sk('wall', 'Sơn hồng đào', 0),
    'soc': _sk('wall', 'Giấy kẻ sọc pastel', 25),
    'cham_bi': _sk('wall', 'Giấy chấm bi', 25),
    'hoa_nhi': _sk('wall', 'Giấy hoa nhí', 35),
    'may_sao': _sk('wall', 'Giấy mây và sao', 40),
    'gach_the': _sk('wall', 'Ốp gạch thẻ', 45),
    'op_go': _sk('wall', 'Ốp gỗ nửa tường', 60),
    'go_sang': _sk('floor', 'Sàn gỗ sáng', 0),
    'gach_trang': _sk('floor', 'Gạch men trắng', 0),
    'chieu': _sk('floor', 'Chiếu cói', 20),
    'caro': _sk('floor', 'Gạch caro', 30),
    'tham_len': _sk('floor', 'Thảm len hồng', 40),
    'gach_bong': _sk('floor', 'Gạch bông', 45),
    'xuong_ca': _sk('floor', 'Sàn gỗ xương cá', 50),
    'ga_ke': _sk('floor', 'Ga kẻ hồng', 0, ('bunk',)),
    'ga_may': _sk('floor', 'Ga mây xanh', 20, ('bunk',)),
    'ga_dau': _sk('floor', 'Ga dâu tây', 25, ('bunk',)),
    'ga_meo': _sk('floor', 'Ga mèo con', 30, ('bunk',)),
}


NO_SKIN = ('bathc', 'pool')         # the shared bathroom is not yours to repaint; the pool deck stays as built


def skin_fits(room: dict, skin: str, part: str) -> bool:
    """May `skin` cover the `part` ('wall' | 'floor') of `room`?"""
    S = SKINS.get(skin)
    if not S or S['part'] not in (part, 'both'):
        return False
    if part == 'wall' and (room['out'] or not room['wrows']):
        return False
    if skin == 'auto':
        return True
    if room['type'] in NO_SKIN:
        return False
    if S['types'] is not None:
        return room['type'] in S['types']
    return room['type'] not in ('bunk', 'yard')
