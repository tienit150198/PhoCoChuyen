"""☕ Chỗ tiêu xu: the catalogue of game/spend.py (pure data, one import: game/price_index.py; live/styles.py reads it too).

Prices are keyed to the income percentiles of DESIGN_0610 §0.1 (xu per life day: p50 ≈ 260, p75 ≈ 400, p90 ≈ 690):
* T0 thói quen, 8–40 xu (3–15 % of a median day): a drink or a bowl at the street's own shops, a spa, a film;
* T1 hằng tuần, 60–400 xu (0.2–1.5 median days): a name colour, a profile frame or a title for 7 days;
* 🙏 công đức: from 5 xu, open-ended, a pure sink with a public weekly board.
Nothing here pays xu, speeds up work or helps an exam: needs bars (game/needs.py), tinh thần and showing off only.

Ids are stored in saves and in the `chat_style` table: never rename or remove one (retire it with `gone: True`).

💹 07/10: every price below is written as the base and indexed once at the end of this file (game/price_index.py):
the shops, the spa, the film, the week's styles and the công đức presets (GIVE_MIN stays: spend.validate pins it).
"""
from . import price_index as pi

# ---------------------------------------------------------------- T0: đi quán làm khách
# shop id → (emoji, name, items). Item: id, emoji, name, price, full (no bụng +), wake (tỉnh táo +).
SHOPS = {
    'co_lan': dict(emoji='☕', name='Cà phê Cô Lan', items=(
        dict(id='ca_phe_muoi', emoji='🧂', name='Cà phê muối', price=9, full=0, wake=20),
        dict(id='bac_xiu', emoji='🥛', name='Bạc xỉu', price=8, full=5, wake=12),
    )),
    'tra_sua_may': dict(emoji='🧋', name='Trà sữa Mây', items=(
        dict(id='tra_sua_tc', emoji='🧋', name='Trà sữa trân châu', price=12, full=10, wake=8),
        dict(id='tra_dao', emoji='🍑', name='Trà đào cam sả', price=14, full=5, wake=10),
    )),
    'pho_hang_may': dict(emoji='🍜', name='Phở Hàng Mây', items=(
        dict(id='pho_tai_lan', emoji='🍜', name='Phở tái lăn', price=15, full=45, wake=0),
        dict(id='banh_mi_chao', emoji='🍳', name='Bánh mì chảo', price=18, full=45, wake=5),
    )),
    'lau_ba_sau': dict(emoji='🍲', name='Lẩu Bà Sáu', items=(
        dict(id='oc_xao_dua', emoji='🐚', name='Ốc len xào dừa', price=28, full=30, wake=0),
        dict(id='lau_mot_nguoi', emoji='🍲', name='Lẩu một người', price=35, full=65, wake=0),
    )),
}
STAMP_CARD = 10           # the 10th stamp at one shop earns its sticker (the card starts again)

# The other side of "khách khó tính": now the player is the customer and the shop is the awkward one (flavour only).
QUAN_LINES = (
    'Quán hết đá, chủ quán bảo đợi đá về 20 phút.',
    'Bàn bên cạnh mở loa TikTok to hết cỡ.',
    'Nhân viên ghi tên bạn thành “Bé Na”.',
    'Wifi quán đổi mật khẩu, hỏi ba lần mới nói.',
    'Chủ quán hỏi “ăn ở đây hay mang đi” lần thứ tư.',
    'Ông chú bàn bên xin ké sạc điện thoại.',
    'Mèo của quán nhảy lên ghế bạn ngồi, không chịu xuống.',
    'Quán bật nhạc remix lúc 7 giờ sáng.',
)

# ---------------------------------------------------------------- T0: spa (Tiệm Thư Giãn Sen)
SPA_NAME = 'Tiệm Thư Giãn Sen'
SPA = (
    dict(id='goi_dau', emoji='💆', name='Gội đầu dưỡng sinh', price=25, wake=10),
    dict(id='lam_mong', emoji='💅', name='Làm móng', price=30, wake=0),
    dict(id='massage_chan', emoji='🦶', name='Massage chân', price=40, wake=15),
)
SPA_SPIRIT = 2            # tinh thần, the first spa of a life day only

# ---------------------------------------------------------------- T0: 🎬 Rạp Mây (one film a week)
FILM_PRICE = 20
FILM_SPIRIT = 2
FILMS = (       # the film of a week: FILMS[ISO week number % len]
    dict(id='ong_trum_pho_may', emoji='🎬', name='Ông trùm phố Mây'),
    dict(id='ma_da_song_hong', emoji='👻', name='Ma da sông Hồng'),
    dict(id='hen_em_ngo_nho', emoji='💙', name='Hẹn em ngõ nhỏ'),
    dict(id='tet_o_lang_may', emoji='🧧', name='Tết ở làng Mây'),
    dict(id='cuoc_dua_xe_om', emoji='🛵', name='Cuộc đua xe ôm'),
    dict(id='co_ba_ban_xoi', emoji='🍙', name='Cô Ba bán xôi'),
)

# ---------------------------------------------------------------- 🙏 công đức Chùa Gió Lành
GIVE_MIN, GIVE_MAX = 5, 1_000_000
GIVE_PRESETS = (5, 20, 50, 200, 1000)
ANON_UNDER = 50           # the client ticks "Ẩn danh" by default below this amount
WISHES = (                # a donation carries one of these (no free text: nothing to moderate on a public board)
    ('', ''),
    ('binh_an', 'Cầu bình an'),
    ('me_khoe', 'Cầu cho mẹ khỏe'),
    ('buon_may', 'Buôn may bán đắt'),
    ('thi_do', 'Cầu thi đỗ'),
    ('gia_dao', 'Gia đạo an khang'),
    ('tinh_duyen', 'Cầu tình duyên'),
)
WISH_IDS = tuple(w[0] for w in WISHES)
THANKS = 'Sư thầy chắp tay: “A Di Đà Phật. Tấm lòng nào cũng quý như nhau.”'   # the same for every amount

# ---------------------------------------------------------------- T1: 🎨 status for a week (never pay-to-win)
WEEK_SECS = 7 * 86400
AHEAD_MAX = 4 * WEEK_SECS  # renewals stack up to 4 weeks ahead
KINDS = ('color', 'frame', 'title')
# Name colours: [light theme, dark theme] (WCAG ≥ 4.5 on both, tests/test_spend.py); grad: two stops.
COLORS = (
    dict(id='c_cam', emoji='🧡', name='Cam đất', price=120, light='#c2410c', dark='#fdba74'),
    dict(id='c_ngoc', emoji='💚', name='Xanh ngọc', price=150, light='#0f766e', dark='#5eead4'),
    dict(id='c_dao', emoji='🩷', name='Hồng đào', price=150, light='#be185d', dark='#f9a8d4'),
    dict(id='c_tim', emoji='💜', name='Tím mộng', price=200, light='#7e22ce', dark='#d8b4fe'),
    dict(id='c_vang', emoji='💛', name='Vàng kim', price=300, light='#a16207', dark='#fde047'),
    dict(id='c_hoang_hon', emoji='🌇', name='Hoàng hôn', price=400, light='#c2410c', dark='#fdba74',
         grad=('#c2410c', '#be185d'), grad_dark=('#fdba74', '#f9a8d4')),
)
FRAMES = (
    dict(id='f_tre', emoji='🎋', name='Khung tre', price=100, ring='#4d7c0f'),
    dict(id='f_may', emoji='☁️', name='Khung mây', price=150, ring='#64748b'),
    dict(id='f_hoa_dao', emoji='🌸', name='Khung hoa đào', price=200, ring='#db2777'),
    dict(id='f_sen_vang', emoji='🪷', name='Khung sen vàng', price=300, ring='#ca8a04'),
    dict(id='f_rong_may', emoji='🐉', name='Khung rồng mây', price=400, ring='#b91c1c'),
)
# need: {stat of journey.spend.stats: at least}. Shown on the name tag in place of a worn title, with honours first.
TITLES = (
    dict(id='t_hang_xom', emoji='🌸', name='Hàng xóm dễ thương', price=60, need={}),
    dict(id='t_tin_do_cafe', emoji='☕', name='Tín đồ cà phê', price=80, need={'eat': 10}),
    dict(id='t_mot_phim', emoji='🎬', name='Mọt phim', price=80, need={'film': 3}),
    dict(id='t_dan_choi', emoji='🛵', name='Dân chơi phố Mây', price=150, need={}),
    dict(id='t_tam_long_vang', emoji='🙏', name='Tấm lòng vàng', price=200, need={'give': 5}),
    dict(id='t_dai_gia', emoji='💎', name='Đại gia phố Mây', price=400, need={}),
)
# 💹 07/10: index the base prices above once (the dicts are this module's own).
for _row in [it for sh in SHOPS.values() for it in sh['items']] + list(SPA) + list(COLORS) + list(FRAMES) + list(TITLES):
    _row['price'] = pi.price(_row['price'])
FILM_PRICE = pi.price(FILM_PRICE)
GIVE_PRESETS = tuple(pi.price(x) for x in GIVE_PRESETS)   # the Chùa's suggested amounts (GIVE_MIN stays)
BIG_MEAL = pi.price(28)   # game/spend.py: the first quán of a day from this price gives +2 tinh thần (base 28)
STYLE_ITEMS = {x['id']: dict(x, kind=k) for k, rows in (('color', COLORS), ('frame', FRAMES), ('title', TITLES)) for x in rows}
TITLE_TEXT = {x['id']: f"{x['emoji']} {x['name']}" for x in TITLES}
