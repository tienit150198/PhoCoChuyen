"""🏰 Dinh thự: the villas above game/housing.py's homes, and the rooms only a villa has (data only).

Owner 07/10: "tăng thêm biệt thự khác giá cao hơn, rồi bên trong mỗi phòng khác nhau, biệt thự bên trong lớn hơn… cho
đa dạng". Players (F#226, F#228): Biệt thự Sông Hồng looked like a normal house inside. So:

* ESTATES: six villas, 150,000 → 2,500,000 xu, each with its own theme (garden, Indochine, glass, beach, penthouse,
  island) and more, BIGGER rooms on two or three floors (`fl`, the interior's floor switcher), with the villa-only room
  types of ROOM_TYPES (thư phòng, phòng khách quý, phòng chiếu phim, hầm rượu, gym, phòng thay đồ, gara trưng bày,
  sân thượng, hồ bơi vô cực, chòi vườn). Bought, sold back and billed by game/lux.py (they live in journey.lux, never
  in journey.home: an older build's housing.validate only knows its own homes), lived in through game/estates.py.
* SONG_HONG_V2: the bigger three-floor inside of Biệt thự Sông Hồng (game/housing.py), free for every owner.
* Each room type has its look (WALL / FLOOR colours in public/js/v4/deco-art.js, its theme's skins SKIN0), its built-in
  signature fixture (FIXTURES, drawn by deco-art.js and kept clear by game/deco.py) and its own furniture (ITEMS), and
  the old furniture fits it by BASE (a study takes what a living room or a bedroom takes).
`register()` adds all this to game/deco_content.py's tables (one call at its end). Ids are stored in saves: never rename.
"""

# ---------------------------------------------------------------- room types only a villa has
# type: (emoji, name, BASE: the older room types whose furniture fits it too)
ROOM_TYPES = {
    'study': ('📚', 'Thư phòng', ('living', 'bed')),
    'suite': ('🛎️', 'Phòng khách quý', ('bed', 'living')),
    'cinema': ('🎬', 'Phòng chiếu phim', ('living',)),
    'cellar': ('🍷', 'Hầm rượu', ('living', 'kitchen')),
    'gym': ('🏋️', 'Phòng gym', ('living',)),
    'closet': ('👗', 'Phòng thay đồ', ('bed',)),
    'showroom': ('🚘', 'Gara trưng bày', ('living',)),
    'terrace': ('🌇', 'Sân thượng', ('balcony',)),
    'infinity': ('🌊', 'Hồ bơi vô cực', ('pool',)),
    'pavilion': ('🏯', 'Chòi vườn', ('yard',)),
}
TYPES = tuple(ROOM_TYPES)
OUTDOOR = ('terrace', 'infinity', 'pavilion')
NO_SKIN = ('infinity', 'pavilion')

# Built-in fixtures (deco_content.FIX_FREE rules; names for the "vướng …" line).
FIX_FREE = {'bookwall': dict(block=True), 'screen': dict(block=True), 'racks': dict(block=True), 'mirror': dict(block=True),
            'rails': dict(block=True), 'gate': dict(block=True, rug=True), 'car': dict(block=True), 'gazebo': dict(block=True)}
FIX_NAMES = {'bookwall': 'kệ sách âm tường', 'screen': 'màn chiếu', 'racks': 'giá rượu', 'mirror': 'gương tập',
             'rails': 'giá treo đồ', 'gate': 'cửa cuốn', 'car': 'chiếc xe trưng bày', 'gazebo': 'mái chòi'}

# ---------------------------------------------------------------- the themes: default wallpaper and floor
# (deco_content.SKINS ids; a room's own choice wins). Signature rooms keep their look whatever the theme.
THEMES = {
    'vuon': dict(w='go_thong', f='go_sang'),
    'dong_duong': dict(w='dong_duong', f='gach_bong'),
    'kinh': dict(w='kinh', f='da_cam_thach'),
    'bien': dict(w='trang_bien', f='go_tau'),
    'sky': dict(w='kinh', f='go_oc_cho'),
    'dao': dict(w='trang_bien', f='da_cam_thach'),
}
TYPE_SKIN = {'cinema': dict(w='nhung', f='tham_do'), 'cellar': dict(w='da_hoc', f='gach_nung'), 'gym': dict(f='cao_su'),
             'closet': dict(w='hong_dao', f='tham_len'), 'study': dict(w='op_go', f='xuong_ca'), 'showroom': dict(f='da_cam_thach')}

# New wallpapers and floors (deco_content.SKINS: part, name, price, types). Drawn in deco-art.js.
SKINS = {
    'go_thong': ('wall', 'Ốp gỗ thông', 150), 'dong_duong': ('wall', 'Vàng Đông Dương', 150), 'kinh': ('wall', 'Vách kính', 200),
    'trang_bien': ('wall', 'Trắng xanh biển', 150), 'nhung': ('wall', 'Nhung đỏ rạp', 200), 'da_hoc': ('wall', 'Đá hộc', 150),
    'da_cam_thach': ('floor', 'Đá cẩm thạch', 200), 'go_oc_cho': ('floor', 'Gỗ óc chó', 200), 'go_tau': ('floor', 'Sàn gỗ boong tàu', 150),
    'tham_do': ('floor', 'Thảm đỏ', 150), 'cao_su': ('floor', 'Sàn cao su', 100), 'gach_nung': ('floor', 'Gạch nung', 120),
}

# ---------------------------------------------------------------- signature furniture (deco_content.ITEMS, appended)
# id: (cat, spot, w, h, price, cozy, rooms, name, emoji, tags, surface)
ITEMS = {
    'giuong_king': ('bed', 'floor', 3, 2, 2000, 3, ('bed', 'suite'), 'Giường king trải lụa', '👑', ('bed',), 18),
    'ban_go_lim': ('table', 'floor', 3, 1, 900, 3, ('study', 'living'), 'Bàn gỗ lim', '🪵', ('desk', 'table'), 26),
    'ghe_da_bo': ('table', 'floor', 1, 1, 600, 3, ('study', 'living', 'suite', 'cinema'), 'Ghế bành da bò', '💺', ('seat', 'soft'), 0),
    'qua_dia_cau': ('fun', 'top', 1, 1, 250, 2, ('study', 'living'), 'Quả địa cầu cổ', '🌍', ('books',), 0),
    'ghe_rap_doi': ('table', 'floor', 2, 1, 800, 3, ('cinema', 'living'), 'Ghế rạp đôi', '🛋️', ('seat', 'soft'), 0),
    'may_bong_ngo': ('fun', 'floor', 1, 1, 350, 2, ('cinema', 'living', 'kitchen'), 'Máy bỏng ngô', '🍿', (), 0),
    'loa_cot': ('fun', 'floor', 1, 1, 700, 2, ('cinema', 'living'), 'Loa cột', '🔊', ('music',), 0),
    'thung_ruou': ('bep', 'floor', 1, 1, 400, 2, ('cellar', 'kitchen'), 'Thùng rượu sồi', '🛢️', (), 22),
    'ban_nem_ruou': ('bep', 'floor', 2, 1, 900, 3, ('cellar',), 'Bàn nếm rượu', '🍷', ('table',), 24),
    'may_chay_bo': ('fun', 'floor', 2, 1, 1200, 2, ('gym',), 'Máy chạy bộ', '🏃', (), 0),
    'gia_ta': ('fun', 'floor', 2, 1, 700, 2, ('gym',), 'Giá tạ', '🏋️', (), 0),
    'tu_giay': ('bed', 'wall', 2, 2, 600, 2, ('closet',), 'Tủ kính giày', '👠', (), 0),
    'dao_trang_suc': ('bed', 'floor', 2, 1, 1500, 3, ('closet',), 'Đảo trang sức', '💎', ('table',), 22),
    'xe_may_co': ('fun', 'floor', 2, 1, 3000, 3, ('showroom',), 'Xe máy cổ trưng bày', '🏍️', (), 0),
    'bien_neon': ('light', 'wall', 2, 1, 300, 2, ('showroom', 'cinema', 'gym'), 'Biển neon', '🌈', ('lamp',), 0),
    'lo_suoi_ngoai': ('pool', 'floor', 1, 1, 800, 3, ('terrace', 'pavilion', 'yard'), 'Lò sưởi ngoài trời', '🔥', ('lamp',), 0),
    'quay_bar_ho': ('pool', 'floor', 2, 1, 1500, 3, ('infinity', 'terrace', 'pool'), 'Quầy bar hồ bơi', '🍹', ('table',), 26),
    'kinh_thien_van': ('fun', 'floor', 1, 1, 1000, 2, ('terrace', 'pavilion'), 'Kính thiên văn', '🔭', (), 0),
}
# Theme sets (deco_content.SETS shape).
SETS = {
    'rap_nha': dict(emoji='🎬', name='Rạp tại gia', bonus=3, need=(('ghe_rap_doi',), ('may_bong_ngo',), ('loa_cot',))),
    'ham_vang': dict(emoji='🍷', name='Hầm rượu vang', bonus=3, need=(('thung_ruou',), ('ban_nem_ruou',), ('tag', 'lamp'))),
    'thu_phong': dict(emoji='📚', name='Thư phòng cổ', bonus=3, need=(('ban_go_lim',), ('ghe_da_bo',), ('qua_dia_cau',))),
    'phong_tap': dict(emoji='🏋️', name='Phòng tập', bonus=2, need=(('may_chay_bo',), ('gia_ta',))),
    'hien_sao': dict(emoji='🌅', name='Hiên ngắm sao', bonus=3, need=(('lo_suoi_ngoai',), ('kinh_thien_van', 'quay_bar_ho'), ('tag', 'seat'))),
    'tu_do': dict(emoji='👗', name='Phòng thay đồ', bonus=2, need=(('tu_giay',), ('dao_trang_suc',))),
    'gara_dep': dict(emoji='🚘', name='Gara trưng bày', bonus=2, need=(('xe_may_co',), ('bien_neon',))),
}

# ---------------------------------------------------------------- the villas
# rooms: (room id, type, cols, floor rows, floor, own name or ''); kits: deco_content.KITS added (bathroom, pool) and
# their floor. bp: phí hạng sang (quản gia, bảo vệ, làm vườn, hồ bơi) in basis points of the price paid a tháng (5 life
# days, game/lux.py bills it). power: điện nước a life day while you live there (the living cost's rent part).
ESTATES = (
    dict(id='bt_vuon_da_lat', theme='vuon', emoji='🌲', name='Biệt thự vườn Đà Lạt', where='Đồi thông, cuối dốc sương',
         price=150000, bp=40, power=20, staff='Quản gia, người làm vườn',
         rooms=(('living', 'living', 10, 4, 1, ''), ('kitchen', 'kitchen', 8, 3, 1, ''), ('study', 'study', 8, 3, 1, ''),
                ('pavilion', 'pavilion', 10, 4, 1, 'Chòi vườn thông'), ('bed', 'bed', 9, 4, 2, ''), ('bed2', 'bed2', 8, 3, 2, ''),
                ('closet', 'closet', 7, 3, 2, '')),
         kits=(('bath_l', 2),)),
    dict(id='bt_dong_duong', theme='dong_duong', emoji='🏛️', name='Biệt thự Đông Dương', where='Phố Pháp, hàng me tây',
         price=300000, bp=45, power=30, staff='Quản gia, bảo vệ, làm vườn',
         rooms=(('living', 'living', 11, 4, 1, 'Sảnh khách'), ('kitchen', 'kitchen', 9, 3, 1, ''), ('study', 'study', 9, 4, 1, ''),
                ('yard', 'yard', 11, 4, 1, 'Vườn hoa sứ'), ('bed', 'bed', 10, 4, 2, ''), ('suite', 'suite', 9, 4, 2, ''),
                ('closet', 'closet', 8, 3, 2, ''), ('terrace', 'terrace', 10, 3, 2, 'Hiên lầu')),
         kits=(('bath_xl', 2), ('pool_m', 1))),
    dict(id='bt_kinh', theme='kinh', emoji='🏙️', name='Biệt thự kính Mây', where='Khu đô thị ven hồ',
         price=500000, bp=50, power=40, staff='Quản gia, bảo vệ, kỹ thuật',
         rooms=(('living', 'living', 12, 5, 1, ''), ('kitchen', 'kitchen', 10, 3, 1, ''), ('showroom', 'showroom', 10, 4, 1, ''),
                ('gym', 'gym', 9, 4, 1, ''), ('bed', 'bed', 10, 4, 2, ''), ('suite', 'suite', 9, 4, 2, ''),
                ('cinema', 'cinema', 10, 4, 2, ''), ('closet', 'closet', 8, 3, 2, ''), ('terrace', 'terrace', 12, 4, 3, ''),
                ('infinity', 'infinity', 12, 4, 3, '')),
         kits=(('bath_xl', 2),)),
    dict(id='bt_bien', theme='bien', emoji='🏖️', name='Biệt thự biển Mũi Né', where='Mũi Né, sát bãi cát',
         price=800000, bp=55, power=50, staff='Quản gia, đầu bếp, cứu hộ hồ bơi',
         rooms=(('living', 'living', 12, 5, 1, ''), ('kitchen', 'kitchen', 10, 4, 1, ''), ('cellar', 'cellar', 9, 4, 1, ''),
                ('gym', 'gym', 9, 4, 1, ''), ('infinity', 'infinity', 12, 5, 1, 'Hồ bơi nhìn biển'),
                ('pavilion', 'pavilion', 10, 4, 1, 'Chòi biển'), ('bed', 'bed', 11, 4, 2, ''), ('suite', 'suite', 10, 4, 2, ''),
                ('bed2', 'bed2', 9, 3, 2, ''), ('closet', 'closet', 9, 3, 2, ''), ('terrace', 'terrace', 12, 4, 2, 'Hiên ngắm biển')),
         kits=(('bath_xl', 2),)),
    dict(id='penthouse_sky', theme='sky', emoji='🌆', name='Penthouse Sky Mây', where='Tầng 52–53, tháp Sky Mây',
         price=1200000, bp=55, power=60, staff='Quản gia, lễ tân tòa, đầu bếp',
         rooms=(('living', 'living', 12, 5, 1, ''), ('kitchen', 'kitchen', 10, 4, 1, ''), ('study', 'study', 9, 4, 1, ''),
                ('cinema', 'cinema', 11, 4, 1, ''), ('cellar', 'cellar', 9, 3, 1, ''), ('bed', 'bed', 11, 5, 2, ''),
                ('suite', 'suite', 10, 4, 2, ''), ('closet', 'closet', 10, 3, 2, ''), ('gym', 'gym', 10, 4, 2, ''),
                ('terrace', 'terrace', 12, 5, 3, 'Sân thượng 53'), ('infinity', 'infinity', 12, 4, 3, '')),
         kits=(('bath_xl', 2),)),
    dict(id='dinh_thu_dao', theme='dao', emoji='🏝️', name='Dinh thự đảo Hòn Mây', where='Đảo riêng, 40 phút ca nô',
         price=2500000, bp=60, power=80, staff='Quản gia, đầu bếp, thủy thủ, bảo vệ đảo',
         rooms=(('living', 'living', 12, 5, 1, 'Đại sảnh'), ('kitchen', 'kitchen', 12, 4, 1, ''), ('cellar', 'cellar', 10, 4, 1, ''),
                ('cinema', 'cinema', 12, 4, 1, ''), ('showroom', 'showroom', 12, 4, 1, 'Gara & bến ca nô'), ('gym', 'gym', 10, 4, 1, ''),
                ('bed', 'bed', 12, 5, 2, ''), ('suite', 'suite', 11, 4, 2, ''), ('bed2', 'bed2', 10, 4, 2, ''),
                ('closet', 'closet', 10, 4, 2, ''), ('study', 'study', 10, 4, 2, 'Thư viện'),
                ('terrace', 'terrace', 12, 5, 3, 'Sân thượng ngắm đảo'), ('infinity', 'infinity', 12, 5, 3, ''),
                ('pavilion', 'pavilion', 12, 4, 3, 'Chòi bãi biển')),
         kits=(('bath_xl', 2),)),
)

# Biệt thự Sông Hồng (game/housing.py 'biet_thu_song'), three floors: every room it had (same ids, bigger) and more.
# Its own rooms keep the look of its repairs (game/reno.py); the new ones get their room type's look.
SONG_HONG = 'biet_thu_song'
SONG_HONG_V2 = dict(rooms=(('living', 'living', 11, 4, 1, ''), ('kitchen', 'kitchen', 9, 3, 1, ''), ('study', 'study', 8, 3, 1, ''),
                           ('yard', 'yard', 11, 4, 1, 'Sân ven sông'), ('bed', 'bed', 10, 4, 2, ''), ('bed2', 'bed2', 9, 3, 2, ''),
                           ('suite', 'suite', 8, 3, 2, ''), ('terrace', 'terrace', 10, 3, 3, 'Sân thượng ngắm sông')),
                    kits=(('bath_xl', 2), ('pool_l', 1)))


def register(DC: dict) -> None:
    """Add the villa rooms, skins, fixtures, furniture and sets to game/deco_content.py's tables (its globals)."""
    ITEMS_ = DC['ITEMS']
    for k, it in ITEMS_.items():   # the older furniture fits the villa rooms by BASE
        extra = tuple(t for t, (_, _, base) in ROOM_TYPES.items() if set(base) & set(it['rooms']) and t not in it['rooms'])
        if extra:
            it['rooms'] = tuple(it['rooms']) + extra
    for k, (cat, spot, w, h, price, cozy, rooms, name, emoji, tags, surface) in ITEMS.items():
        ITEMS_[k] = DC['_i'](cat, spot, w, h, price, cozy, rooms, name, emoji, tags, surface=surface)
    for k, (part, name, price) in SKINS.items():
        DC['SKINS'][k] = DC['_sk'](part, name, price)
    DC['FIX_FREE'].update(FIX_FREE)
    DC['SETS'].update(SETS)
    DC['TYPES'] = tuple(DC['TYPES']) + TYPES
    DC['NO_SKIN'] = tuple(DC['NO_SKIN']) + NO_SKIN
    DC['TAG_WORDS'].setdefault('seat', 'một chỗ ngồi')
