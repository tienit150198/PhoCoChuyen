"""⚔️ Bang (player guilds): every number, name and table of game/bang.py (owner design 19/10).

Ids here are stored in the database (bangs, bang_members, bang_facilities, bang_items): never rename or remove one;
add new ones at the end. Money is xu; points are điểm cống hiến (per member per bang, never xu).
"""
from __future__ import annotations

# ---------------------------------------------------------------- founding (Lập bang)
FOUND_FEE = 5_000_000          # a pure sink: wallet then bank, never a loan, never into the fund
FOUND_ACCOUNT_DAYS = 14        # the leader's account is at least this many real days old
NAME_MIN, NAME_MAX = 2, 20
MOTTO_MAX = 60
EMOJIS = ('⚔️', '🐉', '🦁', '🐯', '🦅', '🐺', '🦊', '🐼', '🦄', '🔥', '🌊', '⭐', '🌙', '🌸', '🍀', '🏮')
# id: (name, hex, ink: readable text on a light tag, wardrobe colour id (look.tint), garage paint id)
COLORS = {
    'do': ('Đỏ son', '#d2453d', '#a3271f', 'do', 'do'),
    'vang': ('Vàng kim', '#e0b43f', '#8a6410', 'vang', 'vang'),
    'mint': ('Xanh bạc hà', '#5cbf9a', '#23795a', 'mint', 'xanh_la'),
    'navy': ('Xanh navy', '#3a4e7c', '#2a3a63', 'navy', 'navy'),
    'lavender': ('Tím lavender', '#9d86c9', '#6a4fa3', 'lavender', 'tim'),
    'hong': ('Hồng phấn', '#ef9bb8', '#b0456d', 'hong', 'hong'),
    'dao': ('Cam đào', '#f0955a', '#a8541c', 'dao', 'cam'),
    'den': ('Đen tuyền', '#3a3436', '#2a2527', 'den', 'den'),
    'trang': ('Trắng ngọc', '#f3f0e8', '#6d665a', 'trang', 'trang'),
    'bac': ('Bạc ánh kim', '#b8bec6', '#5e6670', 'bac', 'bac'),
}

# ---------------------------------------------------------------- members and roles (Danh hiệu bang)
# id: (name, short, seats (None: no limit), rank: higher commands lower)
ROLES = {
    'chu': ('Bang chủ', 'Chủ', 1, 5),
    'pho': ('Phó bang', 'Phó', 2, 4),
    'lao': ('Trưởng lão', 'Lão', 3, 3),
    'tinh': ('Tinh anh', 'Tinh', 5, 2),
    'tv': ('Thành viên', 'TV', None, 1),
}
ROLE_ORDER = ('chu', 'pho', 'lao', 'tinh', 'tv')
APPOINT = ('pho', 'lao', 'tinh', 'tv')         # what Bang chủ may set (Bang chủ itself: the handover)
APPROVE_FROM = 3                                # Trưởng lão and up: accept asks, invite, decline
KICK_FROM = 4                                   # Phó bang and up (never someone of the same or a higher rank)
BUILD_FROM = 4                                  # Phó bang and up start a facility upgrade and set the Giờ vàng
SETTINGS_FROM = 5                               # Bang chủ: open / by approval, motto, emoji, colour, disband

# ---------------------------------------------------------------- the fund (Quỹ bang): deposits only
GIVE_MIN = 1_000
GIVE_MAX = 10_000_000          # one deposit = one wallet history row at most (every build validates ±10 M)
GIVE_PRESETS = (100_000, 500_000, 1_000_000, 5_000_000)
FUND_BASE_CAP = 20_000_000     # without a Kho bang

# ---------------------------------------------------------------- điểm cống hiến
XU_PER_POINT = 1_000           # 1 point per 1.000 xu given (plus the Kho bang's bonus)
CHECKIN_POINTS = 20            # 📅 Điểm danh, once a Vietnam day
WORK_POINTS = 10               # a work day closed (end_day) ...
WORK_DAYS = 3                  # ... at most this many a Vietnam day
ACTIVITY_DAY_MAX = CHECKIN_POINTS + WORK_POINTS * WORK_DAYS   # activity points a member earns a day at most

# ---------------------------------------------------------------- Công trình bang (facilities)
# Each: name, emoji, levels [(cost xu, build hours)], perk text per level. Level n of any facility but the hall needs the
# hall at ceil(n / 2). Paid from the fund only, by Phó bang and up; the level rises after the real-time build.
HALL = 'dai_sanh'
FACILITIES = {
    'dai_sanh': dict(name='Đại sảnh', emoji='🏯', blurb='Nhà chính của bang: thêm chỗ cho thành viên.',
                     levels=[(0, 0), (20_000_000, 6), (50_000_000, 12), (100_000_000, 24), (200_000_000, 48)],
                     start=1),
    'kho': dict(name='Kho bang', emoji='🏦', blurb='Quỹ chứa được nhiều hơn, góp xu được thêm điểm cống hiến.',
                levels=[(2_000_000, 1), (4_000_000, 2), (7_000_000, 3), (12_000_000, 5), (20_000_000, 8), (32_000_000, 12),
                        (50_000_000, 16), (75_000_000, 24), (110_000_000, 36), (160_000_000, 48)]),
    'xuong_may': dict(name='Xưởng may', emoji='🧵', blurb='May đồng phục màu bang, giảm giá đồ may ở cửa hàng.',
                      levels=[(3_000_000, 2), (8_000_000, 4), (18_000_000, 8), (35_000_000, 16), (60_000_000, 24)]),
    'san_pet': dict(name='Sân luyện pet', emoji='🐾', blurb='Sân tập cho thú cưng: bé ra trận Bang chiến pet khỏe hơn.',
                    levels=[(2_000_000, 1), (4_000_000, 2), (7_000_000, 3), (12_000_000, 5), (20_000_000, 8), (32_000_000, 12),
                            (50_000_000, 16), (75_000_000, 24), (110_000_000, 36), (160_000_000, 48)]),
    'den_vang': dict(name='Đền vàng', emoji='⏰', blurb='Giờ vàng riêng của bang: bang chủ chọn giờ, lãi tiệm và quầy ×2.',
                     levels=[(10_000_000, 4), (25_000_000, 8), (50_000_000, 16), (90_000_000, 24), (150_000_000, 48)]),
    'tuong': dict(name='Tượng bang', emoji='🗿', blurb='Bảng vinh danh: thêm điểm xếp hạng Bang mạnh nhất tuần.',
                  levels=[(3_000_000, 2), (6_000_000, 3), (10_000_000, 4), (16_000_000, 6), (25_000_000, 8), (40_000_000, 12),
                          (60_000_000, 16), (90_000_000, 24), (130_000_000, 36), (180_000_000, 48)]),
    'cong': dict(name='Cổng bang', emoji='⛩️', blurb='Cổng và cờ lớn: mở Cờ bang, Pháo hoa bang ở cửa hàng.',
                 levels=[(1_000_000, 1), (5_000_000, 3), (15_000_000, 6), (40_000_000, 12), (80_000_000, 24)]),
}
FAC_ORDER = ('dai_sanh', 'kho', 'xuong_may', 'den_vang', 'cong', 'tuong', 'san_pet')
HALL_CAP = (0, 10, 15, 20, 25, 30)      # members by hall level (start 10, up to 30)
KHO_CAP = (FUND_BASE_CAP, 30_000_000, 50_000_000, 80_000_000, 120_000_000, 180_000_000, 260_000_000, 360_000_000,
           500_000_000, 700_000_000, 1_000_000_000)
KHO_BONUS = 2                  # +2 % points on deposits per Kho bang level
XUONG_OFF = 5                  # −5 % on the uniform, the badge and the boat paint per Xưởng may level
TUONG_BONUS = 2                # +2 % weekly score per Tượng bang level
FAC_SCORE = 100                # weekly score per facility level the bang holds
PET_WAR_SCORE = 100            # weekly score per point of the week's 🛡️ Bang chiến pet ladder (a win 3, the title 5 more)
PET_WAR_MAX = 5                # % the Sân luyện pet adds in the war at most (game/pet_war.py TRAINING_MAX, 1 %/level)
SLOTS = ((1, 1), (3, 2))       # builds at once: 1, 2 from hall level 3


def max_level(fac: str) -> int:
    return len(FACILITIES[fac]['levels'])


def build_slots(hall: int) -> int:
    return max(n for need, n in SLOTS if hall >= need)


def hall_needed(fac: str, level: int) -> int:
    """The hall level a facility's level `level` needs (the hall itself: none)."""
    return 0 if fac == HALL else (level + 1) // 2


def cost(fac: str, level: int) -> tuple[int, int]:
    """(xu, build seconds) to reach `level` (1-based) of `fac`."""
    xu, hours = FACILITIES[fac]['levels'][level - 1]
    return xu, hours * 3600


def perk(fac: str, level: int) -> str:
    """What a level gives, in a few words (0: nothing yet)."""
    if level <= 0:
        return 'Chưa xây'
    if fac == 'dai_sanh':
        return f'{HALL_CAP[level]} thành viên' + (', 2 công trình xây cùng lúc' if build_slots(level) > 1 else '')
    if fac == 'kho':
        return f'Quỹ chứa {KHO_CAP[level] // 1_000_000} triệu xu, +{KHO_BONUS * level}% điểm khi góp'
    if fac == 'xuong_may':
        styles = [UNIFORMS[k][0] for k in UNIFORM_ORDER if UNIFORMS[k][2] <= level]
        out = f'Đồng phục: {", ".join(styles)}; đồ may −{XUONG_OFF * level}%'
        return out + ('; sơn thuyền màu bang' if level >= 2 else '')
    if fac == 'san_pet':
        return f'Bé ra trận Bang chiến pet +{min(level, PET_WAR_MAX)}% chỉ số' + (' (tối đa)' if level >= PET_WAR_MAX else '')
    if fac == 'den_vang':
        g = GOLDEN[level]
        return f'Giờ vàng {g[1]} phút, {g[0]} lần/tuần' + (' (mỗi ngày 1 lần)' if g[0] >= 7 else '')
    if fac == 'tuong':
        return f'+{TUONG_BONUS * level}% điểm xếp hạng tuần'
    if fac == 'cong':
        out = ['Cờ bang'] + (['Pháo hoa bang'] if level >= 3 else []) + (['Cổng vàng'] if level >= 5 else [])
        return 'Mở: ' + ', '.join(out)
    return ''


# ---------------------------------------------------------------- ⏰ Giờ vàng của bang (Đền vàng)
GOLDEN = ((0, 0), (1, 30), (2, 30), (3, 45), (7, 45), (7, 60))   # by Đền vàng level: (windows a VN ISO week, minutes)
GOLDEN_MULT = 200              # hundredths: ×2 on shop and counter profit, like the town's Giờ vàng
GOLDEN_AHEAD_MIN = 3600        # set at least 1 hour ahead
GOLDEN_AHEAD_MAX = 7 * 86400   # at most 7 days ahead
GOLDEN_STEP = 300              # on 5-minute marks
GOLDEN_LOOKBACK = 14 * 86400   # windows a settlement still books (offline catch-up within two weeks)

# ---------------------------------------------------------------- 🛍️ Cửa hàng bang (points only)
# id: (name, emoji, price in points, needs (facility, level) or None, kind)
ITEMS = {
    'ao': ('Áo đồng phục bang', '👕', 300, ('xuong_may', 1), 'wear'),
    'huy': ('Huy hiệu bang', '🎖️', 150, None, 'wear'),
    'co': ('Cờ bang', '🚩', 200, ('cong', 1), 'wear'),
    'thuyen': ('Sơn thuyền màu bang', '⛵', 400, ('xuong_may', 2), 'wear'),
    'phao': ('Pháo hoa bang', '🎆', 100, ('cong', 3), 'use'),
}
ITEM_ORDER = ('huy', 'ao', 'co', 'thuyen', 'phao')
SEWN = ('ao', 'huy', 'thuyen')          # Xưởng may discounts these
PHAO_MAX = 20                           # fireworks held at once
PHAO_GAP = 600                          # one bang show every 10 minutes at most
WEAR_BITS = {'ao': 1, 'huy': 2, 'co': 4, 'thuyen': 8}
# Uniform styles: (name, wardrobe top id, Xưởng may level)
UNIFORMS = {'polo': ('Áo polo', 'ao_polo', 1), 'hoodie': ('Áo hoodie', 'ao_hoodie', 3), 'aodai': ('Áo dài', 'ao_dai', 5)}
UNIFORM_ORDER = ('polo', 'hoodie', 'aodai')

# ---------------------------------------------------------------- 👑 Bang mạnh nhất tuần
WEEK_TITLE = '👑 Bang mạnh nhất tuần'
BOARD_TOP = 10
