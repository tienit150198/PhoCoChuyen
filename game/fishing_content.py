"""🎣 Câu cá: every number of the fishing system in one place (owner 24/10: "phát triển thành bộ sưu tập cá, mua cần
câu, quăng xa ra cá lớn, gần ra cá nhỏ … cá chia phổ thông, quý, hiếm … tới huyền thoại, cổ đại … cần có giá để người
ta câu cá kiếm tiền"; then "cần tăng giá … mỗi loại nhiều cá … quăng cùng loại cần thì lượng xa cũng hên xui").

Tune here, never in game/fishing.py. The model functions below are pure: the server rolls with them (game/fishing.py)
and tests/test_fishing_ev.py integrates them to the expected xu per cast and per hour of each rod (`expected`).

Ids are stored in saves (journey.fish): never rename a species, rod, bait, basket or spot id.
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------- rarities
RARITIES = (   # index = rarity; price band per fish (xu, the owner's ranges), weight band (kg) is per species
    dict(id='pho_thong', name='Phổ thông', emoji='⚪', color='#b8c0c8', price=(10, 150)),
    dict(id='kha', name='Khá', emoji='🟢', color='#43b05c', price=(150, 600)),
    dict(id='quy', name='Quý', emoji='🔵', color='#3d7bff', price=(800, 3_000)),
    dict(id='hiem', name='Hiếm', emoji='🟣', color='#a855f7', price=(5_000, 20_000)),
    dict(id='su_thi', name='Sử thi', emoji='🟠', color='#ff8a1c', price=(40_000, 150_000)),
    dict(id='huyen_thoai', name='Huyền thoại', emoji='🟡', color='#ffcf26', price=(400_000, 1_500_000)),
    dict(id='co_dai', name='Cổ đại', emoji='🔴', color='#ff3b3b', price=(3_000_000, 10_000_000)),
)
NR = len(RARITIES)
CARRY_MIN = 3          # 🟣 Hiếm and up can be carried on the shoulder / in the hand (mang trên người)
AUCTION_MIN = 5        # 🟡 Huyền thoại and up would be the auction's (not supported: game/auction.py sells no player items)
NEWS_MIN = 6           # 🔴 Cổ đại: a line on the town ticker

# ---------------------------------------------------------------- spots
SPOTS = {
    'ho': dict(name='Hồ phố', emoji='🏞️', max=100, luck=1.0, water='#4aa3c7', deep='#1f5f86', shore='#7bbf6a',
               hint='Hồ lớn giữa phố, nước ngọt, nhiều cá đồng.'),
    'song': dict(name='Sông', emoji='🌊', max=110, luck=1.05, water='#5f9eb0', deep='#2f5f6e', shore='#b9a37a',
                 hint='Sông rộng nước chảy, cá da trơn và cá lớn.'),
    'bien': dict(name='Bến cảng', emoji='⚓', max=120, luck=1.1, water='#2f86c7', deep='#123f75', shore='#d8c79a',
                 hint='Cầu cảng ra biển, cá biển và quái vật dưới sâu.'),
    'dao': dict(name='Đảo riêng', emoji='🏝️', max=120, luck=1.15, water='#22b7c9', deep='#0d5e8a', shore='#f1dfa6',
                hint='Biển quanh đảo: rạn san hô, cá màu và cá khổng lồ.', island=True),
}
SPOT_IDS = tuple(SPOTS)
PUBLIC_SPOTS = ('ho', 'song', 'bien')

# Distance zones (metres from the shore): far = bigger and rarer fish. The weights per rarity (before luck / bait).
ZONES = (
    dict(id='gan', name='Gần', to=20, junk=0.15, rar=(100, 4, 0.35, 0.025, 0.0015, 0.0001, 0.00001), skew=1.8),
    dict(id='vua', name='Vừa', to=40, junk=0.10, rar=(100, 5, 0.45, 0.035, 0.0025, 0.0002, 0.00002), skew=1.4),
    dict(id='xa', name='Xa', to=65, junk=0.06, rar=(100, 12, 1.8, 0.25, 0.03, 0.003, 0.0003), skew=1.1),
    dict(id='sau', name='Sâu', to=10**9, junk=0.04, rar=(100, 28, 6.5, 1.2, 0.15, 0.016, 0.0018), skew=0.85),
)


def zone_of(dist: float) -> int:
    return next(i for i, z in enumerate(ZONES) if dist < z['to'])


# ---------------------------------------------------------------- rods, baits, baskets
# range: metres at full power; line: the heaviest fish (kg) it holds safely; luck: rare weights × luck^rarity;
# reel: reel speed (a shorter fight); bite: the share of casts a fish really bites (else it only nibbles: rỉa mồi). Cổ đại from Cần bạch kim (`ancient`), else × ANCIENT_GATE.
RODS = (
    dict(id='tre', name='Cần tre', emoji='🎋', price=0, range=20, line=6, luck=1.0, reel=1.0, bite=0.78, ancient=False, color='#c9a96b'),
    dict(id='truc', name='Cần trúc', emoji='🎍', price=30_000, range=24, line=15, luck=1.0, reel=1.05, bite=0.8, ancient=False, color='#9bbf5a'),
    dict(id='carbon', name='Cần carbon', emoji='🎣', price=200_000, range=40, line=45, luck=1.31, reel=1.1, bite=0.89, ancient=False, color='#3b3f4a'),
    dict(id='bien', name='Cần câu biển', emoji='🌊', price=1_500_000, range=60, line=180, luck=1.69, reel=1.15, bite=0.93, ancient=False, color='#2a6fb8'),
    dict(id='vang', name='Cần vàng', emoji='🥇', price=8_000_000, range=75, line=800, luck=2.07, reel=1.2, bite=0.95, ancient=False, color='#e6b422'),
    dict(id='bach_kim', name='Cần bạch kim', emoji='💠', price=20_000_000, range=90, line=3_500, luck=2.1, reel=1.25, bite=0.97, ancient=True, color='#cfd8e3'),
    dict(id='long_vuong', name='Cần Long Vương', emoji='🐉', price=50_000_000, range=110, line=25_000, luck=2.18, reel=1.3, bite=0.98, ancient=True, color='#d62f2f'),
)
ROD = {r['id']: r for r in RODS}
ROD_IDS = tuple(ROD)
ANCIENT_GATE = 0.05

# Baits: bought by the box (`n` uses), one used per cast while chosen. `rar`: × weight per rarity; `wait`: × bite wait.
# Priced so the bait meant for a rod (giun: tre, tôm: carbon, mồi giả: biển, phát sáng: vàng, huyền thoại: Long Vương) costs
# about 85 % of what it adds there (tests/test_fishing_ev.py): a small edge and the rarer species, never a money sink.
BAITS = (
    dict(id='giun', name='Giun đất', emoji='🪱', price=60, n=30, rar=(1.25, 1.2, 1, 1, 1, 1, 1), wait=0.85,
         hint='Cá nhỏ cắn nhanh hơn.'),
    dict(id='tom', name='Tôm tươi', emoji='🦐', price=100, n=20, rar=(1, 1.3, 1.3, 1.2, 1, 1, 1), wait=0.95,
         hint='Cá Khá, Quý ưa mồi tôm.'),
    dict(id='moi_gia', name='Mồi giả', emoji='🪝', price=600, n=10, rar=(0.9, 1, 1.4, 1.45, 1.3, 1, 1), wait=1.0,
         hint='Cá săn mồi (Quý, Hiếm) mê mồi giả.'),
    dict(id='phat_sang', name='Mồi phát sáng', emoji='✨', price=5_000, n=10, rar=(0.85, 0.9, 1, 1.5, 1.6, 1.5, 1.2), wait=1.0,
         night=1.25, hint='Sáng lấp lánh, ban đêm càng hiệu nghiệm.'),
    dict(id='huyen_thoai', name='Mồi huyền thoại', emoji='🔱', price=50_000, n=5, rar=(0.8, 0.8, 0.9, 1, 1.2, 2.2, 2.2), wait=1.05,
         hint='Gọi cá Huyền thoại, Cổ đại.'),
)
BAIT = {b['id']: b for b in BAITS}
BAIT_IDS = tuple(BAIT)
BAIT_MAX = 999          # uses of one bait a save holds

BASKETS = (   # 🧺 giỏ cá: how many fish the bag holds
    dict(id='gio_tre', name='Giỏ tre', emoji='🧺', price=0, cap=20),
    dict(id='gio_may', name='Giỏ mây', emoji='🧺', price=50_000, cap=40),
    dict(id='thung_da', name='Thùng đá', emoji='🧊', price=500_000, cap=80),
    dict(id='khoang_lanh', name='Khoang lạnh', emoji='❄️', price=5_000_000, cap=150),
)
AQUARIUM_MAX = 8        # 🐠 fish kept swimming in the home aquarium (deco 'be_ca')

# ---------------------------------------------------------------- casting, bite, reel
POWER_SWEET = 0.95      # above: overpower, the line may tangle (rối dây)
TANGLE_CHANCE = 0.4
SPREAD = (0.8, 1.2)     # distance = power × rod range × uniform(SPREAD): the same rod and power land differently
CAST_SECONDS = 1.6      # the cast's flight: the wait counts from the splash
WAIT = ((5, 15), (6, 17), (9, 20), (14, 28), (16, 30), (18, 34), (24, 45))   # bite wait (s) per rarity: longer → heavier
JUNK_WAIT = (5, 12)
NOBITE_WAIT = (10, 18)  # rỉa mồi: nibbles only, then the bait is gone
HOOK_WINDOW = 1.4       # seconds after the bite to tap Giật
HOOK_EARLY = 0.25       # a tap this long before the bite still counts (network), earlier scares the fish off
HOOK_LATE = 0.8         # and this long after the window (network)
REEL = (3.0, 4.0, 5.0, 6.5, 8.0, 10.0, 12.0)   # fight seconds per rarity (+ up to 3 s for a heavy one), ÷ rod reel
REEL_MIN_SHARE = 0.6    # the server refuses a landing sooner than this share of the fight
ROUND_TTL = 180         # seconds a round stays open
NIBBLES = (0, 3)        # fake twitches before the bite (scare the fish if tapped)
SNAP_BASE, SNAP_SLOPE = 0.4, 1.0   # a fish heavier than the line: P(snap) = base + slope × (kg/line − 1), at most 1

# ---------------------------------------------------------------- the market (🐟 Quầy thu mua)
HAGGLE_CHANCE = 0.22    # a sale the trader haggles ("bị trả giá")
HAGGLE_OFFER = (70, 95)  # % of the price he offers
BARGAIN = ((0.45, 100), (0.10, 108), (0.45, 0))   # trả giá lại: full price / a small bonus / he refuses (0)
DEAL_TTL = 300          # seconds an offer stands
RELEASE_SPIRIT = 3      # 🐟 thả cá: +1 tinh thần, at most this many a day

# ---------------------------------------------------------------- the sim's "decent play" (tests/test_fishing_ev.py)
SIM_POWER = (0.70, 0.95)
SIM_HOOK = 0.9                                    # taps Giật in time
SIM_REEL = (0.95, 0.93, 0.9, 0.85, 0.8, 0.75, 0.7)   # keeps the tension green to the end
SIM_UI = (3.0, 1.5)     # seconds on the catch card (landed) / after a miss
HAGGLE_EV = 1 - HAGGLE_CHANCE * (1 - sum(HAGGLE_OFFER) / 200)   # accepting every offer
# xu per hour of active fishing (the best public spot, day, no rain, no bait). The free bamboo rod sets the floor; each
# rod bought pays itself back in ≈50 h (20–60 h) of fishing on the income it adds over the rod before it.
EV_TARGET_HOUR = dict(tre=4_900, truc=5_600, carbon=9_500, bien=40_000, vang=200_000, bach_kim=600_000, long_vuong=1_600_000)

# ---------------------------------------------------------------- junk
JUNK = (('dep', '🩴', 'chiếc dép tổ ong'), ('lon', '🥫', 'vỏ lon nước ngọt'), ('tui', '🛍️', 'túi ni lông'),
        ('go', '🪵', 'khúc gỗ mục'), ('tat', '🧦', 'chiếc tất lạc'), ('cua', '🦀', 'chú cua nhỏ (thả lại)'),
        ('rong', '🌿', 'mớ rong rêu'), ('chai', '🍾', 'chai thủy tinh'))

# ---------------------------------------------------------------- species
# (id, name, rarity, family, spots, kg min, kg max, body, belly/accent, fin, pattern, condition, hint)
# family: the silhouette (public/js/v4/fish-art.js). condition: '' always | 'dem' night (18:00–05:59 VN) | 'ngay' day |
# 'mua' while it rains | 'm:1,2' those months only. Rarer = heavier on the whole (tests check the means).
_S = (
    # ⚪ Phổ thông (28)
    ('ca_ro', 'Cá rô', 0, 'perch', 'ho song', 0.05, 0.4, '#91ad73', '#e5e0a8', '#5d7a48', 'bands', '', 'Ao hồ nước lặng, gần bờ.'),
    ('ca_chep', 'Cá chép', 0, 'carp', 'ho song', 0.3, 3, '#d89d5f', '#f3d9a6', '#b56a2e', 'scales', '', 'Hồ phố, sông chậm.'),
    ('ca_tram', 'Cá trắm', 0, 'carp', 'ho song', 0.5, 3, '#758d96', '#d6dfe0', '#4b5f68', 'scales', '', 'Hồ rộng, ăn cỏ ven bờ.'),
    ('ca_ro_phi', 'Cá rô phi', 0, 'disc', 'ho', 0.2, 1.5, '#7f9286', '#d9e1d6', '#566a5d', 'bands', '', 'Hồ phố, đâu cũng có.'),
    ('ca_me', 'Cá mè', 0, 'carp', 'ho', 0.3, 3, '#b9c4c9', '#eef2f3', '#8a979d', 'none', '', 'Hồ phố, bơi thành đàn.'),
    ('ca_diec', 'Cá diếc', 0, 'carp', 'ho', 0.05, 0.5, '#c9b37a', '#efe6c4', '#9c8650', 'scales', '', 'Hồ cạn nhiều rong.'),
    ('ca_tre', 'Cá trê', 0, 'cat', 'ho', 0.2, 1.5, '#4e4a3f', '#a9a28c', '#35322a', 'spots', 'dem', 'Hồ phố, kiếm ăn ban đêm.'),
    ('ca_sac', 'Cá sặc', 0, 'disc', 'ho', 0.05, 0.3, '#9aa874', '#e3e2b4', '#6c7a4c', 'bands', '', 'Ruộng, ao hồ nhiều cỏ.'),
    ('luon', 'Lươn đồng', 0, 'eel', 'ho', 0.1, 0.6, '#8a6a32', '#d7b46a', '#634a20', 'none', 'mua', 'Bờ hồ lầy, trời mưa mới bò ra.'),
    ('ca_bong', 'Cá bống', 0, 'perch', 'song', 0.05, 0.3, '#a58e6a', '#e2d3b4', '#7a6545', 'spots', '', 'Đáy sông cát.'),
    ('ca_long_tong', 'Cá lòng tong', 0, 'perch', 'song', 0.01, 0.05, '#c7cfd3', '#f2f5f6', '#8d989e', 'stripe', '', 'Mặt sông, bơi nhanh.'),
    ('ca_chach', 'Cá chạch', 0, 'eel', 'song', 0.05, 0.3, '#9b8457', '#dccb9f', '#6f5d3a', 'spots', '', 'Bùn đáy sông.'),
    ('ca_linh', 'Cá linh', 0, 'carp', 'song', 0.01, 0.08, '#d5d9cf', '#f6f6ee', '#a3a99a', 'none', 'm:8,9,10,11', 'Về theo mùa nước nổi (tháng 8–11).'),
    ('ca_muong', 'Cá mương', 0, 'perch', 'song', 0.05, 0.3, '#bfc8c2', '#eef1ee', '#8c9890', 'stripe', '', 'Sông, gần mặt nước.'),
    ('ca_chot', 'Cá chốt', 0, 'cat', 'song', 0.05, 0.3, '#c4a24f', '#ecdca8', '#8f7430', 'bands', '', 'Sông, nhiều nhất mùa nước lên.'),
    ('ca_nganh', 'Cá ngạnh', 0, 'cat', 'song', 0.1, 0.8, '#a39f8f', '#e0ddd0', '#77736a', 'none', '', 'Sông nước chảy, đáy đá.'),
    ('ca_com', 'Cá cơm', 0, 'perch', 'bien', 0.01, 0.04, '#c9d6dc', '#f4f8fa', '#8fa2ab', 'stripe', '', 'Biển gần bờ, đàn lớn.'),
    ('ca_nuc', 'Cá nục', 0, 'tuna', 'bien', 0.1, 0.5, '#6f8fa8', '#dfe8ee', '#4a6a82', 'none', '', 'Cầu cảng, bơi đàn.'),
    ('ca_trich', 'Cá trích', 0, 'perch', 'bien', 0.05, 0.3, '#8fa7b5', '#eaf0f3', '#647f8f', 'none', '', 'Biển nông.'),
    ('ca_doi', 'Cá đối', 0, 'perch', 'bien song', 0.2, 1.5, '#8d9aa0', '#e3e8ea', '#64737a', 'stripe', '', 'Cửa sông, nước lợ.'),
    ('ca_bac_ma', 'Cá bạc má', 0, 'tuna', 'bien', 0.1, 0.5, '#7a95a6', '#e6edf1', '#556f80', 'spots', '', 'Biển gần bờ.'),
    ('ca_liet', 'Cá liệt', 0, 'disc', 'bien', 0.03, 0.2, '#c3c9c4', '#f2f4f2', '#949b95', 'none', '', 'Đáy cát gần cảng.'),
    ('ca_thoi_loi', 'Cá thòi lòi', 0, 'perch', 'bien dao', 0.02, 0.1, '#8c7f62', '#d8cfb6', '#5f5440', 'spots', '', 'Bãi bùn, rừng ngập mặn.'),
    ('ca_song', 'Cá sòng', 0, 'tuna', 'bien', 0.1, 0.6, '#5f8299', '#dce6ec', '#3f5f74', 'stripe', '', 'Biển gần cảng.'),
    ('ca_thia', 'Cá thia biển', 0, 'disc', 'dao', 0.02, 0.1, '#3d8fd6', '#a9d6ff', '#2a62a0', 'none', '', 'Rạn san hô quanh đảo.'),
    ('ca_son', 'Cá sơn', 0, 'perch', 'dao', 0.03, 0.2, '#e0714f', '#f6c3a8', '#b04a2e', 'none', '', 'Hốc đá quanh đảo.'),
    ('ca_bang_chai', 'Cá bàng chài', 0, 'perch', 'dao', 0.1, 1, '#4fae8f', '#c6ecd8', '#2f7f63', 'stripe', '', 'Rạn san hô.'),
    ('ca_kinh', 'Cá kình', 0, 'disc', 'dao', 0.2, 1, '#9e9f6a', '#e6e5bf', '#72734a', 'spots', '', 'Bãi rong biển quanh đảo.'),
    # 🟢 Khá (24)
    ('ca_loc', 'Cá lóc', 1, 'snake', 'ho song', 0.5, 6, '#5d6650', '#c9c7a6', '#3d4433', 'spots', '', 'Bờ hồ nhiều cỏ, rình mồi.'),
    ('ca_chep_do', 'Cá chép đỏ', 1, 'carp', 'ho', 0.3, 4, '#e2483a', '#ffc2a3', '#b52a1f', 'scales', 'm:1,2', 'Hồ phố dịp Tết ông Công ông Táo (tháng 1–2).'),
    ('ca_tai_tuong', 'Cá tai tượng', 1, 'disc', 'ho', 0.5, 5, '#a28f6b', '#ead9b6', '#7a6a4b', 'bands', '', 'Hồ sâu, nước tĩnh.'),
    ('ca_dieu_hong', 'Cá điêu hồng', 1, 'disc', 'ho', 0.3, 2, '#f08a6c', '#ffd1bd', '#c45e44', 'none', '', 'Hồ phố, màu hồng cam.'),
    ('ca_chim_trang', 'Cá chim trắng', 1, 'disc', 'ho', 0.5, 5, '#b7c0c4', '#f0f2f3', '#d16b5b', 'none', '', 'Hồ phố, răng như người.'),
    ('ca_bong_tuong', 'Cá bống tượng', 1, 'perch', 'song', 0.3, 2.5, '#7f6d4f', '#d4c39d', '#5a4c35', 'marble', '', 'Đáy sông, nằm im rình mồi.'),
    ('ca_basa', 'Cá basa', 1, 'cat', 'song', 1, 8, '#8e9aa3', '#eef1f2', '#66737c', 'none', '', 'Sông lớn miền Tây.'),
    ('ca_tra', 'Cá tra', 1, 'cat', 'song', 1, 10, '#6e7e8a', '#dfe5e8', '#4b5a65', 'none', '', 'Sông lớn, nước đục.'),
    ('ca_lang', 'Cá lăng', 1, 'cat', 'song', 1, 10, '#9a7b5a', '#e5d4bc', '#6f5538', 'spots', '', 'Sông sâu nước chảy.'),
    ('ca_he', 'Cá he', 1, 'carp', 'song', 0.3, 2, '#c9b25a', '#f1e7b3', '#e05a3a', 'scales', '', 'Sông Mekong, vây đỏ.'),
    ('ca_chinh', 'Cá chình', 1, 'eel', 'song', 0.5, 5, '#5c5a3f', '#c9c49a', '#3d3c28', 'none', 'dem', 'Hang đá ven sông, ra đêm.'),
    ('ca_kim', 'Cá kìm', 1, 'needle', 'song bien', 0.2, 1.5, '#9fc0b5', '#eef7f3', '#6f9488', 'stripe', '', 'Mặt nước cửa sông.'),
    ('ca_chuon', 'Cá chuồn', 1, 'flyer', 'bien', 0.2, 1, '#4c7fb3', '#dbe9f6', '#87b9e8', 'none', 'ngay', 'Biển khơi, bay trên sóng ban ngày.'),
    ('ca_thu', 'Cá thu', 1, 'tuna', 'bien', 1, 10, '#5a7f9e', '#e3ecf2', '#3b5d7a', 'spots', '', 'Biển xa bờ một chút.'),
    ('ca_hong', 'Cá hồng', 1, 'perch', 'bien', 0.5, 5, '#e05d5d', '#ffd0c4', '#b33a3a', 'none', '', 'Rạn đá ngoài cảng.'),
    ('ca_mu', 'Cá mú', 1, 'perch', 'bien dao', 0.5, 6, '#8a7a5c', '#d9ccb0', '#5f533c', 'spots', '', 'Hang đá, rạn san hô.'),
    ('ca_chim_bien', 'Cá chim biển', 1, 'disc', 'bien', 0.3, 3, '#a9b4bc', '#eef2f5', '#7a8790', 'none', '', 'Biển gần bờ.'),
    ('ca_bon', 'Cá bơn', 1, 'flat', 'bien', 0.3, 3, '#a08a68', '#e7dcc6', '#75644a', 'spots', '', 'Nằm dẹt dưới đáy cát.'),
    ('ca_cang', 'Cá căng', 1, 'perch', 'bien', 0.2, 1.5, '#b5b08a', '#efedd8', '#7f7b5c', 'stripe', '', 'Cửa sông, đáy cát.'),
    ('ca_noc', 'Cá nóc', 1, 'puffer', 'bien dao', 0.2, 2, '#c7b46b', '#f3ecc8', '#8f7f45', 'spots', '', 'Phồng tròn khi sợ. Đừng ăn nhé!'),
    ('ca_he_hoa', 'Cá hề', 1, 'perch', 'dao', 0.05, 0.3, '#ff8a2a', '#ffffff', '#1f1f1f', 'clown', '', 'Trốn trong hải quỳ quanh đảo.'),
    ('ca_bo_hom', 'Cá bò hòm', 1, 'box', 'dao', 0.1, 0.6, '#f2cf3a', '#fff3b8', '#c9a21c', 'spots', '', 'Rạn san hô, thân vuông vức.'),
    ('ca_mo', 'Cá mó', 1, 'perch', 'dao', 0.5, 5, '#3fb7a3', '#c3efe6', '#e97aa0', 'scales', '', 'Rạn san hô, mỏ như vẹt.'),
    ('ca_buom', 'Cá bướm', 1, 'disc', 'dao', 0.1, 0.5, '#ffd84a', '#ffffff', '#1f1f1f', 'bands', '', 'Rạn san hô, bơi từng cặp.'),
    # 🔵 Quý (20)
    ('ca_loc_bong', 'Cá lóc bông', 2, 'snake', 'ho song', 2, 10, '#4f5e4a', '#d7d3b0', '#2f3a2c', 'marble', '', 'Hồ sâu, bờ nhiều bèo.'),
    ('ca_koi', 'Cá koi', 2, 'carp', 'ho', 1, 10, '#ffffff', '#ffffff', '#e8452c', 'koi', '', 'Hồ phố, ai thả từ lâu.'),
    ('ca_dia', 'Cá đĩa', 2, 'disc', 'ho', 0.2, 1, '#e8743b', '#ffd1a6', '#3c8fd0', 'stripe', '', 'Góc hồ nước ấm.'),
    ('ca_rong_bac', 'Cá rồng bạc', 2, 'arowana', 'ho', 1, 5, '#c9d3d9', '#f5f8fa', '#8796a0', 'scales', '', 'Hồ sâu, nhảy đớp mồi trên mặt.'),
    ('ca_tram_den', 'Cá trắm đen', 2, 'carp', 'ho song', 3, 40, '#3d4447', '#9aa3a6', '#262b2d', 'scales', '', 'Đáy hồ sâu, ăn ốc.'),
    ('ca_chien', 'Cá chiên', 2, 'cat', 'song', 2, 30, '#6f6a4a', '#d2cca4', '#4a4630', 'marble', '', 'Thác ghềnh sông lớn.'),
    ('ca_anh_vu', 'Cá anh vũ', 2, 'carp', 'song', 1, 6, '#8f9a7a', '#e5e8d6', '#c9606a', 'scales', '', 'Ngã ba sông, cá tiến vua.'),
    ('ca_leo', 'Cá leo', 2, 'cat', 'song', 3, 25, '#7d8a96', '#e5eaee', '#58636d', 'none', 'dem', 'Sông sâu, săn mồi ban đêm.'),
    ('ca_dua', 'Cá dứa', 2, 'cat', 'song bien', 2, 12, '#9a9f8c', '#ecede5', '#6f7363', 'none', '', 'Cửa sông nước lợ.'),
    ('ca_huong_ven', 'Cá hường vện', 2, 'disc', 'song', 0.5, 4, '#e2c060', '#fff1c4', '#2b2b2b', 'bands', '', 'Sông Mekong, vằn như hổ.'),
    ('ca_chem', 'Cá chẽm', 2, 'perch', 'song bien', 2, 30, '#8a9aa3', '#e8eef1', '#5f6f78', 'none', '', 'Cửa sông, săn cá con.'),
    ('ca_ngu_van', 'Cá ngừ vằn', 2, 'tuna', 'bien', 2, 15, '#2f5679', '#dce8f2', '#1d3a55', 'stripe', '', 'Biển khơi, bơi rất nhanh.'),
    ('ca_bop', 'Cá bớp', 2, 'tuna', 'bien', 5, 40, '#5a5146', '#cfc5b6', '#3b352d', 'stripe', '', 'Phao, cọc ngoài cảng.'),
    ('ca_cam', 'Cá cam', 2, 'tuna', 'bien', 3, 40, '#8aa1a8', '#eef3f4', '#e0b94a', 'stripe', '', 'Biển sâu ngoài cảng.'),
    ('ca_duoi', 'Cá đuối', 2, 'ray', 'bien', 5, 60, '#7d7262', '#e8e0d0', '#594f42', 'spots', '', 'Nằm dưới cát đáy biển.'),
    ('ca_nhong', 'Cá nhồng', 2, 'snake', 'bien dao', 2, 20, '#9bb0bb', '#eef3f5', '#5e7480', 'bars', '', 'Rạn ngoài khơi, răng sắc.'),
    ('ca_mu_do', 'Cá mú đỏ', 2, 'perch', 'dao', 1, 8, '#d64a3a', '#ffc4b5', '#a12d22', 'spots', '', 'Hang san hô sâu.'),
    ('ca_than_tien', 'Cá thần tiên', 2, 'angel', 'dao', 0.2, 1.5, '#ffd34d', '#fff4c2', '#3a7bd5', 'stripe', '', 'Rạn san hô, vây dài.'),
    ('ca_mo_xanh', 'Cá mó xanh', 2, 'perch', 'dao', 5, 40, '#2f8f7f', '#bfe8de', '#1f6a5d', 'scales', '', 'Rạn san hô ngoài xa.'),
    ('ca_bo_gai', 'Cá bò gai', 2, 'disc', 'dao', 0.5, 4, '#3b3b52', '#f2d34a', '#f2d34a', 'trigger', '', 'Rạn san hô, gai trên lưng.'),
    # 🟣 Hiếm (18)
    ('ca_rong_do', 'Cá rồng huyết long', 3, 'arowana', 'ho', 2, 8, '#d63a2a', '#ffb39f', '#a3241a', 'scales', '', 'Hồ sâu, vảy đỏ như máu.'),
    ('ca_chep_vang', 'Cá chép vàng', 3, 'carp', 'ho', 3, 15, '#ffc934', '#fff0a8', '#e09a12', 'scales', 'm:1,2,3', 'Hồ phố đầu năm (tháng 1–3).'),
    ('ca_loc_hoang_de', 'Cá lóc hoàng đế', 3, 'snake', 'song', 5, 20, '#3f4f5a', '#c9d4d9', '#e2a23a', 'spots', '', 'Sông sâu, đầu to dữ tợn.'),
    ('ca_tam', 'Cá tầm', 3, 'sturgeon', 'song', 10, 60, '#6b7680', '#d7dde1', '#48525a', 'plates', '', 'Sông lạnh nước sâu.'),
    ('ca_chinh_hoa', 'Cá chình hoa', 3, 'eel', 'song', 5, 25, '#9a8a3e', '#e8dc9a', '#4a3f18', 'marble', 'dem', 'Hang đá sông sâu, ra đêm.'),
    ('ca_sau_hoa_tien', 'Cá sấu hỏa tiễn', 3, 'gar', 'song', 20, 120, '#6f6a45', '#d5d0a6', '#4b4729', 'spots', '', 'Sông lớn, mõm dài như cá sấu.'),
    ('ca_ngu_dai_duong', 'Cá ngừ đại dương', 3, 'tuna', 'bien', 20, 150, '#253f63', '#e5eef5', '#f2c230', 'none', '', 'Biển khơi sâu.'),
    ('ca_kiem', 'Cá kiếm', 3, 'bill', 'bien', 50, 400, '#3b4a63', '#d9e2ec', '#26324a', 'none', '', 'Biển sâu, mỏ như kiếm.'),
    ('ca_co', 'Cá cờ', 3, 'sail', 'bien dao', 20, 90, '#2b4f8a', '#dde8f5', '#3f86d9', 'bars', '', 'Biển khơi, vây lưng như cánh buồm.'),
    ('ca_duoi_dien', 'Cá đuối điện', 3, 'ray', 'bien', 5, 40, '#6a5a8a', '#e3dcef', '#4a3d66', 'spots', 'dem', 'Đáy biển ban đêm, coi chừng giật!'),
    ('ca_mat_trang', 'Cá mặt trăng', 3, 'mola', 'bien', 200, 1000, '#9ea8b0', '#eef1f3', '#737d86', 'none', '', 'Biển khơi, nằm phơi nắng trên mặt.'),
    ('ca_bon_lon', 'Cá bơn khổng lồ', 3, 'flat', 'bien', 20, 150, '#8a7454', '#e5d8c2', '#5f4f38', 'spots', '', 'Đáy biển sâu.'),
    ('ca_mu_nghe', 'Cá mú nghệ', 3, 'perch', 'bien dao', 30, 200, '#6f6a3a', '#e3df9c', '#f2c52e', 'spots', '', 'Hang đá lớn ngoài khơi.'),
    ('ca_map_vay_den', 'Cá mập vây đen', 3, 'shark', 'dao', 10, 50, '#8a9aa6', '#eef2f5', '#1f1f1f', 'tips', '', 'Rạn san hô quanh đảo.'),
    ('ca_lich_bien', 'Cá lịch biển', 3, 'eel', 'dao', 3, 25, '#5f8a3a', '#d5e8b8', '#3f5f22', 'spots', 'dem', 'Hốc đá san hô, ra đêm.'),
    ('ca_noc_nhim', 'Cá nóc nhím', 3, 'puffer', 'dao', 1, 6, '#c9b07a', '#f5ecd2', '#8a7346', 'spikes', '', 'Rạn san hô, đầy gai.'),
    ('ca_hoang_de', 'Cá hoàng đế', 3, 'angel', 'dao', 0.5, 3, '#2d4fb3', '#ffd34d', '#ffd34d', 'stripe', '', 'Rạn san hô sâu.'),
    ('ca_napoleon', 'Cá Napoleon', 3, 'perch', 'dao', 20, 150, '#3f9f8f', '#bfe8de', '#2a6f63', 'marble', '', 'Rạn san hô ngoài khơi, trán gù.'),
    # 🟠 Sử thi (14)
    ('ca_rong_kim_long', 'Cá rồng kim long', 4, 'arowana', 'ho', 5, 20, '#f2c230', '#fff2b0', '#c9971a', 'scales', '', 'Hồ sâu, vảy vàng óng.'),
    ('ca_hai_tuong', 'Cá hải tượng', 4, 'arowana', 'ho song', 50, 200, '#4f5f4a', '#d9a26a', '#c4442f', 'scales', '', 'Hồ, sông lớn, ngoi lên thở.'),
    ('ca_tra_dau', 'Cá tra dầu', 4, 'cat', 'song', 80, 300, '#6a7378', '#e1e5e7', '#4a5257', 'none', '', 'Sông Mekong, cá da trơn khổng lồ.'),
    ('ca_duoi_nuoc_ngot', 'Cá đuối nước ngọt', 4, 'ray', 'song', 100, 500, '#7a6b52', '#ece2cf', '#54493a', 'spots', '', 'Đáy sông Mekong.'),
    ('ca_chinh_khong_lo', 'Cá chình khổng lồ', 4, 'eel', 'song', 20, 80, '#4a4a2f', '#c9c48f', '#2f2f1d', 'marble', 'dem', 'Vực sông sâu, ra đêm.'),
    ('ca_tam_nga', 'Cá tầm Nga', 4, 'sturgeon', 'song', 30, 120, '#5a646c', '#d2d8dc', '#3c444a', 'plates', '', 'Sông lạnh, vực sâu.'),
    ('ca_ngu_vay_xanh', 'Cá ngừ vây xanh', 4, 'tuna', 'bien', 100, 600, '#1d3557', '#e6eef5', '#3a7bd5', 'none', '', 'Biển khơi, bơi xuyên đại dương.'),
    ('ca_marlin', 'Cá marlin xanh', 4, 'bill', 'bien dao', 100, 700, '#1f4f8f', '#dde9f6', '#2f7fd0', 'bars', '', 'Biển khơi, nhảy vọt khỏi sóng.'),
    ('ca_map_bua', 'Cá mập búa', 4, 'hammer', 'bien dao', 100, 450, '#7d8c98', '#eef2f5', '#56636d', 'none', '', 'Biển sâu, đầu như búa.'),
    ('ca_map_ho', 'Cá mập hổ', 4, 'shark', 'bien', 200, 800, '#7a8070', '#ecece4', '#4d5246', 'bars', '', 'Biển xa, vằn như hổ.'),
    ('ca_map_dua', 'Cá mập đuôi dài', 4, 'thresher', 'bien', 100, 350, '#6a7f9a', '#e9eef4', '#465a73', 'none', '', 'Biển khơi, đuôi dài như roi.'),
    ('ca_mai_cheo', 'Cá mái chèo', 4, 'oar', 'bien dao', 50, 270, '#c9d1d6', '#f5f7f8', '#e0443a', 'none', 'dem', 'Biển sâu, chỉ ngoi lên ban đêm.'),
    ('ca_duoi_manta', 'Cá đuối manta', 4, 'ray', 'dao', 300, 1500, '#2a2f3a', '#f2f4f6', '#1a1d24', 'manta', '', 'Biển quanh đảo, lướt như chim.'),
    ('ca_co_den', 'Cá cờ đen', 4, 'bill', 'dao', 150, 700, '#20262f', '#d9dee5', '#3a4250', 'none', '', 'Biển sâu quanh đảo.'),
    # 🟡 Huyền thoại (10)
    ('koi_rong', 'Koi rồng', 5, 'carp', 'ho', 15, 60, '#ffffff', '#ffe08a', '#e8452c', 'koi', 'mua', 'Hồ phố, chỉ hiện khi trời mưa.'),
    ('ca_vang_hoang_kim', 'Cá vàng hoàng kim', 5, 'fancy', 'ho', 5, 25, '#ffb21f', '#fff0a8', '#ff7a1a', 'none', 'dem', 'Hồ phố, ánh vàng giữa đêm.'),
    ('ca_ho', 'Cá hô khổng lồ', 5, 'carp', 'song', 100, 300, '#9aa3a0', '#eef1ef', '#6f7875', 'scales', 'm:11,12,1,2', 'Sông Mekong mùa khô (tháng 11–2).'),
    ('ca_tam_trang', 'Cá tầm trắng', 5, 'sturgeon', 'song', 300, 1500, '#c9d1d6', '#f5f7f8', '#8e989f', 'plates', '', 'Vực sông lạnh, sống cả trăm năm.'),
    ('ca_chep_hoa_rong', 'Cá chép hóa rồng', 5, 'carp', 'song', 20, 80, '#ff5a2a', '#ffe08a', '#ffcf26', 'scales', 'mua', 'Vượt vũ môn khi trời mưa.'),
    ('long_vuong', 'Cá rồng Long Vương', 5, 'arowana', 'bien dao', 40, 200, '#d62f2f', '#ffd34d', '#ffcf26', 'scales', 'mua', 'Biển động mưa giông, Long Vương ngoi lên.'),
    ('ca_map_trang', 'Cá mập trắng', 5, 'shark', 'bien', 500, 2000, '#7f8c96', '#f3f5f7', '#56636d', 'none', '', 'Biển khơi lạnh.'),
    ('hai_xa', 'Hải xà', 5, 'oar', 'bien', 300, 1200, '#2f6f5f', '#bfe8c8', '#e0443a', 'scales', 'dem', 'Truyền thuyết biển đêm.'),
    ('ca_nham_voi', 'Cá nhám voi', 5, 'whale', 'dao bien', 2000, 12000, '#3f5a73', '#f2f4f6', '#2a3f52', 'dots', '', 'Biển quanh đảo, hiền như voi.'),
    ('ca_than_mat_troi', 'Cá thần mặt trời', 5, 'mola', 'dao', 40, 270, '#d9473a', '#ffd0c4', '#ffcf26', 'dots', '', 'Biển sâu quanh đảo.'),
    # 🔴 Cổ đại (8)
    ('bothriolepis', 'Bothriolepis', 6, 'armor', 'ho', 80, 300, '#7a6a4a', '#d8c9a2', '#4f4430', 'plates', '', 'Đáy hồ cổ, áo giáp từ 380 triệu năm.'),
    ('mawsonia', 'Mawsonia', 6, 'lobe', 'song', 150, 600, '#4f6a7f', '#c9d8e2', '#2f4a5f', 'dots', 'mua', 'Vực sông khi mưa lớn.'),
    ('vay_tay', 'Cá vây tay', 6, 'lobe', 'bien dao', 60, 110, '#2f4f7a', '#c9d8ea', '#1d3355', 'dots', 'dem', 'Hang sâu dưới biển, ra đêm.'),
    ('xiphactinus', 'Xiphactinus', 6, 'xipha', 'dao', 300, 900, '#5f7f9a', '#e2ebf2', '#3b5a73', 'none', '', 'Biển sâu kỷ Phấn trắng.'),
    ('helicoprion', 'Helicoprion', 6, 'shark', 'bien', 400, 1500, '#5a5f73', '#d9dce5', '#3a3e4f', 'saw', 'dem', 'Răng cưa xoắn, biển đêm.'),
    ('dunkleosteus', 'Dunkleosteus', 6, 'armor', 'bien', 1000, 4000, '#5f5a52', '#d2cbbf', '#3a3631', 'plates', '', 'Quái vật bọc giáp biển sâu.'),
    ('leedsichthys', 'Leedsichthys', 6, 'whale', 'bien', 5000, 20000, '#4f6f8a', '#e2ebf2', '#2f4a5f', 'none', '', 'Cá khổng lồ kỷ Jura, biển khơi.'),
    ('megalodon', 'Megalodon', 6, 'shark', 'bien dao', 8000, 25000, '#4a5560', '#e5e9ed', '#2c343b', 'none', '', 'Vua đại dương cổ đại.'),
)
FAMILIES = ('perch', 'carp', 'cat', 'snake', 'eel', 'disc', 'angel', 'flat', 'ray', 'manta', 'shark', 'hammer', 'thresher',
            'whale', 'bill', 'sail', 'needle', 'flyer', 'tuna', 'puffer', 'box', 'arowana', 'gar', 'sturgeon', 'mola',
            'oar', 'fancy', 'armor', 'lobe', 'xipha')
PATTERNS = ('none', 'bands', 'bars', 'stripe', 'spots', 'dots', 'scales', 'marble', 'koi', 'clown', 'plates', 'tips',
            'spikes', 'trigger', 'manta', 'saw')


def _value_of(rows: list) -> dict:
    """v (0..1) per species: the heavier of its rarity, the dearer (price = band ^ (0.2 v + 0.8 f²))."""
    out = {}
    for r in range(NR):
        mine = sorted((x for x in rows if x[2] == r), key=lambda x: (x[6], x[0]))
        for i, x in enumerate(mine):
            out[x[0]] = round(i / max(1, len(mine) - 1), 3)
    return out


_V = _value_of(list(_S))
SPECIES = {x[0]: dict(id=x[0], name=x[1], r=x[2], fam=x[3], spots=tuple(x[4].split()), w=(float(x[5]), float(x[6])),
                      body=x[7], belly=x[8], fin=x[9], pat=x[10], cond=x[11], hint=x[12], v=_V[x[0]])
           for x in _S}
SPECIES_IDS = tuple(SPECIES)
SP_INDEX = {k: i for i, k in enumerate(SPECIES_IDS)}
LEGACY = ('ca_ro', 'ca_chep', 'ca_tram')   # game/leisure.py's three keepsakes: their counts move into Sổ cá


def by_rarity(r: int) -> list:
    return [s for s in SPECIES.values() if s['r'] == r]


def at_spot(spot: str) -> list:
    return [s for s in SPECIES.values() if spot in s['spots']]


# ---------------------------------------------------------------- conditions (Vietnam time)
VN_OFFSET = 7 * 3600
RAIN_SHARE = (0.18, 0.35)   # share of 3-hour blocks with rain: dry season / rainy season (months 5–10)


def vn_parts(t: float) -> tuple:
    """(day ordinal, hour, month) in Vietnam."""
    import datetime
    d = datetime.datetime.fromtimestamp(t + VN_OFFSET, datetime.timezone.utc)
    return d.toordinal(), d.hour, d.month


def is_night(t: float) -> bool:
    return not 6 <= vn_parts(t)[1] < 18


def is_rain(t: float) -> bool:
    """The town's weather: the same for everyone, a 3-hour block at a time (seeded, nothing stored)."""
    import hashlib
    day, hour, month = vn_parts(t)
    h = hashlib.sha256(f'mua|{day}|{hour // 3}'.encode()).digest()
    return int.from_bytes(h[:4], 'big') / 2**32 < RAIN_SHARE[1 if 5 <= month <= 10 else 0]


def conditions(t: float) -> dict:
    day, hour, month = vn_parts(t)
    return dict(night=is_night(t), rain=is_rain(t), month=month)


def available(sp: dict, cond: dict) -> bool:
    c = sp['cond']
    if not c:
        return True
    if c == 'dem':
        return bool(cond.get('night'))
    if c == 'ngay':
        return not cond.get('night')
    if c == 'mua':
        return bool(cond.get('rain'))
    if c.startswith('m:'):
        return int(cond.get('month') or 0) in {int(m) for m in c[2:].split(',')}
    return False


def cond_text(sp: dict) -> str:
    c = sp['cond']
    if c == 'dem':
        return '🌙 Chỉ ban đêm'
    if c == 'ngay':
        return '☀️ Chỉ ban ngày'
    if c == 'mua':
        return '🌧️ Khi trời mưa'
    if c.startswith('m:'):
        return '📅 Tháng ' + ', '.join(c[2:].split(','))
    return ''


# ---------------------------------------------------------------- the model (server rolls, sim integrates)
def rarity_weights(spot: str, zone: int, rod: str, bait: str | None, cond: dict) -> list:
    """Weight per rarity (0 where the spot has no species available now)."""
    z, rd, sp = ZONES[zone], ROD[rod], SPOTS[spot]
    luck = rd['luck'] * sp['luck']
    b = BAIT.get(bait) if bait else None
    out = []
    for r in range(NR):
        if not any(available(s, cond) for s in by_rarity(r) if spot in s['spots']):
            out.append(0.0)
            continue
        w = z['rar'][r] * luck ** r
        if r == NR - 1 and not rd['ancient']:
            w *= ANCIENT_GATE
        if b:
            w *= b['rar'][r] * (b.get('night', 1.0) if cond.get('night') and r >= 3 else 1.0)
        out.append(w)
    return out


def pool(spot: str, r: int, cond: dict) -> list:
    return [s for s in SPECIES.values() if s['r'] == r and spot in s['spots'] and available(s, cond)]


def weight_of(sp: dict, f: float) -> float:
    lo, hi = sp['w']
    return lo + (hi - lo) * max(0.0, min(1.0, f))


def grams(kg: float) -> int:
    return max(1, int(round(kg * 1000)))


def frac_of(sp: dict, g: int) -> float:
    lo, hi = sp['w']
    return max(0.0, min(1.0, (g / 1000 - lo) / (hi - lo))) if hi > lo else 0.0


def price(sp_id: str, g: int) -> int:
    """Xu the 🐟 Quầy thu mua pays for one fish (before haggling): inside its rarity's band, dearer for a heavier
    species and a heavier fish."""
    sp = SPECIES[sp_id]
    lo, hi = RARITIES[sp['r']]['price']
    e = 0.2 * sp['v'] + 0.8 * frac_of(sp, g) ** 2
    return int(round(lo * (hi / lo) ** e))


def wait_of(r: int, f: float, noise: float, bait: str | None = None) -> float:
    """Seconds from the splash to the bite: longer for rarer fish, and a longer wait leans to a heavier one."""
    lo, hi = WAIT[r]
    m = BAIT[bait]['wait'] if bait in BAIT else 1.0
    return (lo + (hi - lo) * max(0.0, min(1.0, 0.65 * f + 0.35 * noise))) * m


def reel_of(r: int, f: float, rod: str) -> float:
    return (REEL[r] + 3.0 * f) / ROD[rod]['reel']


def snap_chance(kg: float, rod: str) -> float:
    line = ROD[rod]['line']
    return 0.0 if kg <= line else min(1.0, SNAP_BASE + SNAP_SLOPE * (kg / line - 1))


def fight_of(r: int, kg: float, rod: str) -> dict:
    """What the client's reel mini-game uses: pull 0..1 (how hard the fish fights), dart 0..1 (how often it darts),
    green 0..1 (the green zone's width)."""
    load = min(1.5, kg / ROD[rod]['line'])
    pull = min(1.0, 0.18 + 0.1 * r + 0.35 * load)
    return dict(pull=round(pull, 3), dart=round(min(0.95, 0.12 + 0.12 * r), 3), green=round(max(0.18, 0.46 - 0.04 * r - 0.08 * min(1, load)), 3))


# ---------------------------------------------------------------- expected value (tests/test_fishing_ev.py)
def expected(rod: str, spot: str, bait: str | None = None, cond: dict | None = None, steps: int = 24) -> dict:
    """{cast: xu per cast, hour: xu per hour, casts: casts per hour, bait: bait xu per hour} of decent play (SIM_*),
    by integrating the model above over power, spread, zone, rarity, species and weight."""
    cond = cond or dict(night=False, rain=False, month=6)
    rd, sp = ROD[rod], SPOTS[spot]
    zp = [0.0] * len(ZONES)
    n = steps
    for i in range(n):
        p = SIM_POWER[0] + (SIM_POWER[1] - SIM_POWER[0]) * (i + .5) / n
        for k in range(n):
            s = SPREAD[0] + (SPREAD[1] - SPREAD[0]) * (k + .5) / n
            zp[zone_of(min(sp['max'], p * rd['range'] * s))] += 1 / (n * n)
    value = time_ = 0.0
    for zi, pz in enumerate(zp):
        if pz <= 0:
            continue
        z = ZONES[zi]
        time_ += pz * (1 - rd['bite']) * (CAST_SECONDS + sum(NOBITE_WAIT) / 2 + SIM_UI[1])
        time_ += pz * rd['bite'] * z['junk'] * (CAST_SECONDS + sum(JUNK_WAIT) / 2 + 2.0 + SIM_UI[1])
        ws = rarity_weights(spot, zi, rod, bait, cond)
        tot = sum(ws)
        for r, w in enumerate(ws):
            if w <= 0:
                continue
            pr = pz * rd['bite'] * (1 - z['junk']) * w / tot
            sps = pool(spot, r, cond)
            for spc in sps:
                ps = pr / len(sps)
                for u in range(n):
                    f = ((u + .5) / n) ** z['skew']
                    kg = weight_of(spc, f)
                    wait = wait_of(r, f, 0.5, bait)
                    reel = reel_of(r, f, rod)
                    snap = snap_chance(kg, rod)
                    land = SIM_HOOK * SIM_REEL[r] * (1 - snap)
                    v = land * price(spc['id'], grams(kg)) * HAGGLE_EV
                    t = (CAST_SECONDS + wait + SIM_HOOK * reel * (1 - 0.5 * snap)
                         + land * SIM_UI[0] + (1 - land) * SIM_UI[1])
                    value += ps / n * v
                    time_ += ps / n * t
    casts = 3600 / time_ if time_ else 0.0
    b = BAIT.get(bait) if bait else None
    bait_hour = casts * b['price'] / b['n'] if b else 0.0
    return dict(cast=value, hour=value * casts, casts=casts, bait=bait_hour, zones=zp)


def best_hour(rod: str, bait: str | None = None, cond: dict | None = None) -> tuple:
    """(xu per hour, spot) at the best public spot."""
    return max((expected(rod, s, bait, cond)['hour'], s) for s in PUBLIC_SPOTS)


# ---------------------------------------------------------------- 📖 Sổ cá milestones and titles
# Completing a rarity tier (every species of it caught once): xu (modest) and, from 🟣 Hiếm, a 🎨 Phong cách title.
TIER_REWARD = (10_000, 30_000, 100_000, 300_000, 1_000_000, 2_000_000, 5_000_000)
TIER_TITLE = (None, None, None, 't_ca_hiem', 't_ca_su_thi', 't_ca_huyen', 't_ca_co_dai')
SPOT_TITLE = dict(ho='t_ca_ho', song='t_ca_song', bien='t_ca_bien', dao='t_ca_dao')
ALL_TITLE, ALL_FRAME = 't_ca_than_cau', 'f_ca_than_cau'
SPOT_REWARD = 200_000
STYLE_TITLES = tuple(dict(x, price=0, need={}) for x in (   # 🎨 spend_content TITLES rows: earned only, never sold
    dict(id='t_ca_hiem', emoji='🟣', name='Thợ câu cá hiếm', earn='Câu đủ mọi loài 🟣 Hiếm trong 📖 Sổ cá.'),
    dict(id='t_ca_su_thi', emoji='🟠', name='Cần thủ sử thi', earn='Câu đủ mọi loài 🟠 Sử thi trong 📖 Sổ cá.'),
    dict(id='t_ca_huyen', emoji='🟡', name='Huyền thoại sông hồ', earn='Câu đủ mọi loài 🟡 Huyền thoại trong 📖 Sổ cá.'),
    dict(id='t_ca_co_dai', emoji='🔴', name='Người câu cổ đại', earn='Câu đủ mọi loài 🔴 Cổ đại trong 📖 Sổ cá.'),
    dict(id='t_ca_ho', emoji='🏞️', name='Chúa tể Hồ phố', earn='Câu đủ mọi loài ở 🏞️ Hồ phố.'),
    dict(id='t_ca_song', emoji='🌊', name='Hà Bá của Sông', earn='Câu đủ mọi loài ở 🌊 Sông.'),
    dict(id='t_ca_bien', emoji='⚓', name='Long Vương Bến cảng', earn='Câu đủ mọi loài ở ⚓ Bến cảng.'),
    dict(id='t_ca_dao', emoji='🏝️', name='Chúa đảo câu cá', earn='Câu đủ mọi loài ở 🏝️ Đảo riêng.'),
    dict(id='t_ca_than_cau', emoji='🎣', name='Thần câu của phố', earn='Câu đủ toàn bộ 📖 Sổ cá.'),
))
STYLE_FRAMES = (
    dict(id='f_ca_than_cau', emoji='🎣', name='Khung Thần câu', price=0, ring='#2f9fd6', earn='Câu đủ toàn bộ 📖 Sổ cá.'),
)
