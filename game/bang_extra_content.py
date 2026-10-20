"""⚔️ Bang "nhiều hơn" (owner 20/10 "bang hội nữa nhiều hơn"): the numbers and names of game/bang_extra.py.

Ids here are stored in the database (bang_facilities.place, bang_facilities.fac 'd_<id>', bang_fund ids, bang_points
ids): never rename or remove one; add new ones at the end. Money is xu from the bang fund (a pure sink: nothing pays
out); points are điểm cống hiến (the bang shop only, never xu, never the weekly ranking).
"""
from __future__ import annotations

M = 1_000_000

# ---------------------------------------------------------------- 🏯 Kiểu đại sảnh (hall styles)
# id: (name, emoji, the Đại sảnh level it needs, price from the fund, paid once per bang). The art is the house style of
# the same id in public/js/house-art.js (drawn big on the Đảo bang); 'dinh' is the bang's own hall (the art by level
# band, client/isometric/bang-island.ts hall()), free, and every bang has it. A style bought once is kept: switching
# back and forth costs nothing more (only the cooldown), and each comes in the house style's three colours (free).
HALL_DEFAULT = 'dinh'
HALL_STYLES = {
    'dinh': ('Đình bang', '🏯', 1, 0),
    'nha_ruong': ('Phủ rường cố đô', '🏯', 2, 10 * M),
    'hanok': ('Sảnh Hanok', '🏘️', 2, 10 * M),
    'nha_nhat': ('Sảnh Phù Tang', '🎎', 2, 10 * M),
    'villa_phap': ('Dinh thự Pháp', '🏛️', 3, 25 * M),
    'dia_trung_hai': ('Sảnh Địa Trung Hải', '🏖️', 3, 25 * M),
    'villa_kinh': ('Sảnh kính hiện đại', '🪟', 4, 50 * M),
    'dinh_thu': ('Lâu đài châu Âu', '🏰', 4, 60 * M),
    'hoang_cung': ('Hoàng cung Á Đông', '👑', 5, 100 * M),
}
HALL_ORDER = tuple(HALL_STYLES)
HALL_LOOKS = 3                 # colours of a style (house-art.js VARIANTS)
HALL_GAP = 3600                # seconds between two changes of style or colour (the island is repainted for everyone)

# ---------------------------------------------------------------- 🎏 Trang trí đảo bang (decorations)
# id: (name, emoji, price from the fund, the Đại sảnh level it needs, blurb). Bought once each, at once (no build),
# a pure sink. Each one standing adds DECOR_BONUS % to the weekly quests' points, DECOR_BONUS_MAX % at most.
DECOR = {
    'den_long': ('Dãy đèn lồng', '🏮', 3 * M, 1, 'Đèn lồng đỏ dọc đường từ bến lên quảng trường.'),
    'hoa_dao': ('Vườn đào', '🌸', 5 * M, 1, 'Hai cây đào nở hồng hai bên đại sảnh.'),
    'co_hoi': ('Cờ hội', '🎏', 6 * M, 2, 'Cờ màu bang phấp phới bên cổng.'),
    'rong_da': ('Tượng rồng đá', '🐉', 12 * M, 2, 'Hai rồng ngọc canh cửa đại sảnh.'),
    'lau_chuong': ('Lầu chuông', '🔔', 15 * M, 3, 'Lầu chuông mái đỏ, chuông đồng gọi cả bang.'),
    'thuyen_rong': ('Thuyền rồng', '🐲', 20 * M, 3, 'Thuyền rồng của bang neo cạnh bến.'),
}
DECOR_ORDER = tuple(DECOR)
DECOR_FAC = 'd_'               # bang_facilities.fac = 'd_<id>', level 1 (game/bang.py levels and the ranking skip them)
DECOR_BONUS = 5
DECOR_BONUS_MAX = 30

# ---------------------------------------------------------------- 📋 Nhiệm vụ tuần (weekly bang quests)
# Three a week for each bang (picked from QUESTS by the week and the bang id), done together: the members' check-ins,
# work days, gifts. A member who did something for the bang that week (a check-in, a work day or a gift in this bang)
# claims each quest done once: its points (+ the decorations' bonus) as điểm cống hiến. At most QUEST_WEEK_MAX claims
# a player a week, every bang together (hopping between bangs earns nothing more). Never xu, never the ranking.
# id: (emoji, text with {n}, measure, per member, at least, at most, points)
#   measure: checkin (check-ins this week), work (work days closed), active (members with a check-in or a work day),
#   give (xu given to the fund), build (fund spent on buildings, styles, decorations, the island: at least one).
QUESTS = {
    'diem_danh': ('📅', 'Cả bang điểm danh {n} lượt', 'checkin', 3, 5, 60, 40),
    'lam_viec': ('💼', 'Cả bang chốt {n} ngày làm việc', 'work', 4, 6, 90, 50),
    'dong_long': ('👥', '{n} thành viên cùng hoạt động', 'active', 0.6, 3, 25, 60),
    'gop_quy': ('💰', 'Góp quỹ {n} xu trong tuần', 'give', 1 * M, 3 * M, 50 * M, 60),
    'xay_dung': ('🏗️', 'Dùng quỹ xây một công trình hay trang trí', 'build', 0, 1, 1, 40),
    'chuyen_can': ('🔥', 'Chuyên cần: cả bang điểm danh {n} lượt', 'checkin', 5, 10, 120, 80),
}
QUEST_ORDER = tuple(QUESTS)
QUESTS_A_WEEK = 3
QUEST_WEEK_MAX = 3
