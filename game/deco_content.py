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
drawn by the room and blocking their cells; a counter is a surface too.
"""
from __future__ import annotations

# Room types (a room's `type`; an item lists the types it suits).
LIVE = ('living', 'bed', 'bed2', 'studio')
SLEEP = ('bed', 'bed2', 'studio')
IN = ('living', 'bed', 'bed2', 'kitchen', 'studio')
OUT = ('balcony', 'yard')
WALLS = IN + ('loft', 'bunk')
SMALL = IN + ('loft', 'bunk')
TYPES = IN + OUT + ('loft', 'bunk')

CATS = (('bed', '🛏️', 'Giường, tủ & thảm'), ('table', '🪑', 'Bàn ghế'), ('light', '💡', 'Đèn'), ('plant', '🪴', 'Cây & hoa'),
        ('wall', '🖼️', 'Trang trí tường'), ('fun', '🧸', 'Đồ chơi & tiện ích'))
SPOTS = ('wall', 'floor', 'rug', 'top')


def _i(cat, spot, w, h, price, cozy, rooms, name, emoji, tags=(), surface=0):
    return dict(cat=cat, spot=spot, w=w, h=h, price=price, cozy=cozy, rooms=tuple(rooms), name=name, emoji=emoji,
                tags=tuple(tags), surface=surface)


ITEMS = {
    # 1.2.0 (names, prices and Ấm cúng unchanged)
    'sofa': _i('table', 'floor', 3, 1, 180, 3, ('living', 'studio'), 'Sofa vải', '🛋️', ('seat', 'soft')),
    'ban_tra': _i('table', 'floor', 2, 1, 70, 1, ('living', 'studio', 'loft') + OUT, 'Bàn trà', '🫖', ('table',), surface=14),
    'giuong': _i('bed', 'floor', 3, 2, 220, 3, SLEEP, 'Giường gỗ', '🛏️', ('bed',), surface=16),
    'tv': _i('fun', 'floor', 2, 1, 240, 2, LIVE, 'Ti vi', '📺', ('screen',)),
    'be_ca': _i('fun', 'floor', 2, 1, 150, 3, ('living', 'studio'), 'Bể cá', '🐠', ('water',)),
    'ke_sach': _i('bed', 'floor', 2, 1, 90, 2, LIVE, 'Kệ sách', '📚', ('books',)),
    'ban_lam_viec': _i('table', 'floor', 2, 1, 120, 1, LIVE, 'Bàn làm việc', '💻', ('desk',), surface=24),
    'dan': _i('fun', 'floor', 1, 1, 110, 2, LIVE + ('loft',), 'Đàn ghi-ta', '🎸', ('music',)),
    'gau_bong': _i('fun', 'top', 1, 1, 35, 1, LIVE + ('loft', 'bunk'), 'Gấu bông', '🧸', ('soft',)),
    'cay_canh': _i('plant', 'floor', 1, 1, 40, 2, IN + OUT + ('loft',), 'Chậu cây cảnh', '🪴', ('plant',)),
    'ghe_may': _i('table', 'floor', 1, 1, 70, 1, IN + OUT, 'Ghế mây', '🪑', ('seat',)),
    'tu_lanh': _i('fun', 'floor', 1, 1, 260, 2, ('kitchen', 'studio'), 'Tủ lạnh', '🧊', ('kitchen',)),
    'ban_an': _i('table', 'floor', 2, 1, 160, 2, ('kitchen', 'living', 'studio'), 'Bàn ăn', '🍽️', ('table',), surface=24),
    'noi_com': _i('fun', 'top', 1, 1, 45, 1, ('kitchen', 'studio'), 'Nồi cơm điện', '🍚', ('kitchen',)),
    'may_giat': _i('fun', 'floor', 1, 1, 200, 1, ('kitchen',) + OUT, 'Máy giặt', '🫧'),
    'hoa_giay': _i('plant', 'floor', 1, 1, 50, 2, OUT, 'Chậu hoa giấy', '🌺', ('plant', 'flower')),
    'ban_ngoai': _i('table', 'floor', 2, 1, 160, 2, OUT, 'Bàn ô ngoài trời', '⛱️', ('table',), surface=22),
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
    'tham_hoa': _i('bed', 'rug', 2, 1, 20, 1, IN + ('loft',), 'Thảm chùi chân hoa', '🌸', ('rug',)),
    # Bàn ghế
    'ban_hoc': _i('table', 'floor', 2, 1, 110, 2, LIVE, 'Bàn học', '✏️', ('desk',), surface=24),
    'ghe_hoc': _i('table', 'floor', 1, 1, 50, 1, IN, 'Ghế học xoay', '💺', ('seat',)),
    'ghe_luoi': _i('table', 'floor', 1, 1, 60, 2, LIVE + ('loft',), 'Ghế lười', '🫘', ('seat', 'soft')),
    'ban_xep': _i('table', 'floor', 1, 1, 35, 1, SLEEP + ('loft', 'bunk'), 'Bàn xếp mini', '📐', ('desk',), surface=12),
    'ghe_dau': _i('table', 'floor', 1, 1, 15, 1, IN + OUT, 'Ghế đẩu nhựa', '🔴', ('seat',), surface=16),
    'ban_gaming': _i('table', 'floor', 2, 1, 260, 2, LIVE, 'Bàn gaming', '🕹️', ('desk', 'gaming'), surface=24),
    'ghe_gaming': _i('table', 'floor', 1, 1, 180, 2, LIVE, 'Ghế gaming', '🎮', ('seat', 'gaming')),
    'xich_du': _i('table', 'floor', 2, 1, 260, 3, ('yard',), 'Xích đu gỗ', '🌳', ('seat',)),
    'vong': _i('table', 'floor', 2, 1, 70, 2, OUT, 'Võng dù', '🏝️', ('soft',)),
    # Đèn
    'den_ban': _i('light', 'top', 1, 1, 35, 1, SMALL, 'Đèn bàn', '💡', ('lamp',)),
    'den_cay': _i('light', 'floor', 1, 1, 80, 2, LIVE + ('kitchen',), 'Đèn cây chân gỗ', '🔦', ('lamp',)),
    'den_ngu': _i('light', 'top', 1, 1, 30, 1, SLEEP + ('living', 'loft', 'bunk'), 'Đèn ngủ cây nấm', '🍄', ('lamp',)),
    'den_tha': _i('light', 'wall', 1, 1, 65, 1, IN, 'Đèn thả giỏ mây', '🧺', ('lamp',)),
    'den_led': _i('light', 'wall', 2, 1, 45, 1, LIVE + ('loft', 'bunk'), 'Dây LED đổi màu', '🌈', ('lamp', 'gaming')),
    # Cây & hoa
    'cay_monstera': _i('plant', 'floor', 1, 1, 90, 2, IN + OUT, 'Cây trầu bà lá xẻ', '🌱', ('plant',)),
    'cay_luoi_ho': _i('plant', 'floor', 1, 1, 50, 1, IN + OUT + ('loft',), 'Cây lưỡi hổ', '🌾', ('plant',)),
    'xuong_rong': _i('plant', 'top', 1, 1, 15, 1, SMALL + OUT, 'Chậu xương rồng mini', '🌵', ('plant',)),
    'binh_hoa': _i('plant', 'top', 1, 1, 30, 1, SMALL, 'Bình hoa cúc họa mi', '🌼', ('plant', 'flower')),
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
    'loa': _i('fun', 'top', 1, 1, 70, 1, SMALL, 'Loa bluetooth', '🔊', ('music',)),
    'may_choi_game': _i('fun', 'top', 1, 1, 220, 2, LIVE + ('loft', 'bunk'), 'Máy chơi game', '👾', ('gaming', 'screen')),
    'hop_nhac': _i('fun', 'top', 1, 1, 55, 1, SMALL, 'Hộp nhạc', '🎶', ('music',)),
    'o_meo': _i('fun', 'floor', 1, 1, 45, 2, LIVE + ('loft',), 'Ổ mèo bông', '🐈', ('soft',)),
}
LEGACY = tuple(ITEMS)[:27]          # the 1.2.0 catalogue (reno.py slots)


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


# Rented rooms and Bà Tám's attic (no structure to repair: the landlord's).
RENT_ROOMS = {
    'attic': (dict(id='attic', type='studio', emoji='🏚️', name='Căn gác', cols=6, wrows=2, frows=3, out=False, tags=(),
                   fix=[_fx('slope', 'wall', 0, 0, 2, 1), _fx('window', 'wall', 3, 0, 1, 1)] + _door(5)),),
    'tro_moi': (dict(id='tro', type='studio', emoji='🛏️', name='Phòng trọ', cols=7, wrows=2, frows=3, out=False, tags=(),
                     fix=[_fx('window', 'wall', 2, 0, 2, 2)] + _door(6)),
                dict(id='loft', type='loft', emoji='🪜', name='Gác lửng', cols=6, wrows=1, frows=2, out=False, tags=(),
                     fix=[_fx('ladder', 'floor', 5, 1)])),
    'ky_tuc_xa': (dict(id='bunk', type='bunk', emoji='🛏️', name='Góc giường của bạn', cols=5, wrows=2, frows=2, out=False,
                       tags=('bed',), fix=[_fx('pillow', 'floor', 0, 0)]),),
}


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
