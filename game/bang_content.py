"""⚔️ Bang (player guilds): every number, name and table of game/bang.py (owner design 19/10).

Ids here are stored in the database (bangs, bang_members, bang_facilities, bang_items): never rename or remove one;
add new ones at the end. Money is xu; points are điểm cống hiến (per member per bang, never xu).
"""
from __future__ import annotations

# ---------------------------------------------------------------- founding (Lập bang)
FOUND_FEE = 5_000_000          # a pure sink: wallet then bank, never a loan, never into the fund
FOUND_ACCOUNT_DAYS = 7         # the leader's account is at least this many real days old (owner 20/10 evening: "7 ngày là tạo được bang, k phải 14 ngày")
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
RENAME_MAX = 2                 # owner 20/10 "tên bang và huy hiệu cho phép đổi", "giới hạn 1 bang được đổi 2 lần": a bang's name
BADGE_MAX = 2                  # and its badge (emoji) change at most this many times each, ever (bang_log 'rename' / 'badge' rows)
SETTINGS_FROM = 5                               # Bang chủ: open / by approval, motto, emoji, colour, disband
RULES_FROM = 4                                  # Phó bang and up: the join mode and the requirements (owner 20/10)
# 🚪 How a bang takes new members (owner 20/10 "tắt, mở hoặc tự động duyệt member vào bang tùy chọn"): id -> label.
# closed: nobody joins or asks (an officer's invitation still lets a player in, and asks already open may still be
# approved); ask: a request waits for a Trưởng lão or higher; auto: whoever meets the requirements is in at once
# (someone who does not is refused with the reason).
JOIN_MODES = {'closed': '🚫 Đóng', 'ask': '🔒 Cần duyệt', 'auto': '🚪 Tự động duyệt'}
REQ_DAYS_MAX = 365             # a requirement on the account's age, in days, at most
REQ_RANK_MAX = 7               # the longest promotion ladder (game/promotion.py top)

# ---------------------------------------------------------------- the fund (Quỹ bang): deposits only
# Owner 21/10: "quỹ bang cho k giới hạn", "góp 1 lần không giới hạn tiền": no fund cap, no per-gift cap but what the
# player has (wallet then bank; the wallet's part in Sổ ví rows of at most 10 M, game/bang.py _take). GIVE_MAX and
# FUND_MAX are only technical ceilings far above anything reachable (a wallet and a bank account hold 1 tỷ each at most):
# GIVE_MAX = game/bang.py BIG, the bound every build since 2.4.63 validates journey.bang.last.a with.
GIVE_MIN = 1_000               # whole thousands
GIVE_MAX = 10**12
GIVE_PRESETS = (1_000_000, 10_000_000, 100_000_000)   # the client adds "Tất cả" (everything the player has)
FUND_MAX = 10**15              # bangs.fund is a bigint: never near it
FUND_BASE_CAP = 20_000_000     # before 21/10: the fund's cap without a Kho bang (KHO_CAP below), no longer applied

# ---------------------------------------------------------------- điểm cống hiến
XU_PER_POINT = 1_000           # 1 point per 1.000 xu given (plus the Kho bang's bonus)
GIVE_PTS_DAY = 50_000          # points from gifts a player earns a Vietnam day at most, every bang together (21/10: with no
                               # fund cap a huge gift still gives its xu, but its points stop here: the shop and the
                               # contribution ranking stay a matter of days, not of one deposit)
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
    'kho': dict(name='Kho bang', emoji='🏦', blurb='Góp quỹ được thêm điểm cống hiến.',
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
# KHO_CAP: the fund's cap per Kho bang level before 21/10 (kept for the record; the fund has no cap now).
KHO_BONUS = 5                  # +5 % points on deposits per Kho bang level (21/10: was +2 %, the Kho no longer raises a cap)
XUONG_OFF = 5                  # −5 % on the uniform, the badge and the boat paint per Xưởng may level
# 👑 Bang mạnh nhất tuần (owner 21/10, final: "đừng để cống hiến bang tính điểm nhé, hãy tính điểm của pets, công trình và
# cấp bang làm điểm nhé"): three parts, heaviest first (game/bang.py standings), the sum × the Tượng bang's bonus. Điểm cống
# hiến never counts (it buys from the bang shop only).
#   🐾 Pets = the week's Bang chiến pet ladder points × PET_WAR_SCORE (a win 3 → 1.500, the champion of 3 rounds
#      3 × 3 + 5 = 14 → 7.000; counted once the war's matches have been shown) + the week's ⚔️ Thách đấu bang (CHAL_WIN a
#      win, CHAL_DRAW a draw, at most CHAL_WEEK_MAX) + 💪 Chiến lực ÷ POWER_DIV (each current member's strongest pet power,
#      the top POWER_TOP: 20 members with A-rank pets ≈ 6.000 → 3.000);
#   🏗️ Công trình = Σ levels of the facilities but the Đại sảnh × FAC_SCORE (all 45 levels 6.750, a usual bang 10–20 levels
#      1.500–3.000);
#   ⭐ Cấp bang = (the Đại sảnh's level (the bang's level: its member cap) + its 🏝️ Đảo bang's level, bangs.isle 0–5:
#      game/bang.py _isle_level) × LEVEL_SCORE (hall 1 with no island → 500, hall 5 + island 5 → 5.000).
# So pets weigh most (the champion, 7.500 with its level 1, beats a level-5 bang of 25 facility levels, 6.250); a bang
# that only gave xu (no pets, no buildings) ranks low.
PET_WAR_SCORE = 500
CHAL_WIN, CHAL_DRAW = 200, 70
CHAL_WEEK_MAX = 2_000
POWER_DIV = 2
POWER_TOP = 30
FAC_SCORE = 150
LEVEL_SCORE = 500
TUONG_BONUS = 2                # +2 % of the whole score per Tượng bang level
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
        return f'+{KHO_BONUS * level}% điểm cống hiến khi góp quỹ'
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
GOLDEN_SENIORITY = 86400       # a window counts for members who joined the bang at least 24 h before it starts (review 19/10:
                               # no hopping into another bang's window), and only while they are still in (until they leave)
GOLDEN_CANCEL_FREEZE = 300     # a window can no longer be cancelled in its last 5 minutes before the start (every process's
                               # snapshot of the windows is at most a minute old: none books a cancelled one)

# ---------------------------------------------------------------- anti-churn (joining stays free, owner 19/10)
REJOIN_HOURS = 24             # owner 20/10 evening "chỉnh lại rời bang chờ 24h nhé" (was 48); owner 21/10: "thoát bang thì cần 48h sau mới vào được bang khác": after leaving a bang (Rời bang),
                               # another bang (join, ask, invite, approval, founding) waits this long; the same bang takes you back at
                               # once; a kick or a disband never makes anyone wait. MNL_BANG_REJOIN_HOURS overrides (0: off)
SWITCH_DAY_MAX = 10            # bangs joined (or founded) a Vietnam day at most per player: a soft cap against hopping

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


# ---------------------------------------------------------------- 🏝️ Đảo bang: bought and upgraded from the fund (owner 21/10)
# "đảo bang bắt phải mua nhé … sau mở rộng lên được", "mua giá như giá đảo", "có mức rẻ hơn cho đảo bang là 1m",
# "muốn lên thì nâng cấp tiếp, 30m thì được cấp 2". One ladder: cấp 1 is bought for ISLE_BUY (at once); cấp 2…5 cost the
# private islands' prices (game/island_content.py ISLANDS, in their order: Đảo Dừa, San Hô, Mây Đá, Hoàng Hôn; those are
# written as paid, never through game/price_index.py, so no multiplier here either) and take a real-time build. Paid
# from the fund only (a pure sink, ledger kind 'build', id 'i:<bang>:<level>'), by Phó bang and up, under the bang row's
# lock. Each level enlarges the island's map (public/js/bang-island-layout.js: a new zone), raises the live room's cap
# and lets the facilities climb further (isle_needed). A bang that has not bought it plays nothing on the island (no
# visit, no pet arena, no Bang chiến): game/bang.py has_island. Bangs from before this release hold cấp 1 for free.
from . import island_content as _IC

ISLE_BUY = 1_000_000
ISLE_PRICES = (ISLE_BUY,) + tuple(int(i['price']) for i in _IC.ISLANDS)   # cấp 1…5
ISLE_HOURS = (0, 6, 12, 24, 48)                 # build hours to reach cấp 1…5 (cấp 1: at once)
ISLE_CAP = (0, 30, 40, 50, 60, 80)              # people on the island at once by level (the live room's cap)
ISLE_MAX = len(ISLE_PRICES)
# What each level adds to the map (the zone of public/js/bang-island-layout.js ZONES, same order).
ISLE_ZONES = ('🏯 Đảo nhỏ: đại sảnh, quảng trường, bến tàu', '🥋 Võ đường bên bờ đông', '🍵 Trà đình bên hồ cá bờ tây',
              '🛕 Bảo tháp trên đồi thông', '🗼 Hải đăng và đèn lồng vàng khắp đảo')
# A facility's level n needs the island at isle_needed(fac, n): on the ten-level scale (a 5-level facility counts double)
# levels 1–4 need nothing (they work without the island, as before 21/10), 5–6 cấp 2, 7–8 cấp 3, 9 cấp 4, 10 cấp 5.
# Levels already built stay (only further upgrades wait).
ISLE_GATE = (0, 0, 0, 0, 0, 2, 2, 3, 3, 4, 5)


def isle_cost(level: int) -> tuple[int, int]:
    """(xu, build seconds) to reach island level `level` (1-based)."""
    return ISLE_PRICES[level - 1], ISLE_HOURS[level - 1] * 3600


def isle_cap(level: int) -> int:
    return ISLE_CAP[max(0, min(ISLE_MAX, level))]


def isle_needed(fac: str, level: int) -> int:
    """The island level a facility's level `level` needs (0: none)."""
    top = max_level(fac)
    scaled = -(-level * 10 // top) if top != 10 else level
    return ISLE_GATE[max(0, min(10, scaled))]
