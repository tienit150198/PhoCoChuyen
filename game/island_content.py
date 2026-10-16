"""🏝️ Đảo riêng: the private islands and the seats of every yacht and plane that can take friends there (data only).

Owner 16/10: "cho phép mua đảo riêng giá cao, mời bạn ra chơi bằng du thuyền hoặc phi cơ, có dung lượng người dùng vào
được với mỗi loại, bên trong có map riêng". The richest hold 13–48 million xu (top 1 ≈ 48M, top 10 ≥ 13M), so the
cheapest island sits around the top-10 wallets and the dearest is a long goal even for the top 1.

* ISLANDS: four islands, 15M → 100M xu, each its own map (`look`: public/js/island-layout.js draws it on both
  interfaces) with its own spots to sit at, swim, dive. Bought, sold back at SELL_PCT % and billed every tháng
  (basis points `bp` of the price paid, like the villas: game/island.py). A player may own several (each pays its own
  bill). No island earns anything: no rent, no tourists, no xu from a visit.
* SEATS: how many people one trip takes, the owner included, keyed by the vehicle id of game/garage.py VEHICLES or
  game/lux_content.py ASSETS (those ids are stored in saves and never renamed; this table never renames them either).
  ARRIVE: where it lands (boat: the pier, heli: the helipad, plane: the island's strip). A boat or plane id this table
  does not know yet (a newer garage model) takes GROUP_SEATS of its garage group; anything else cannot carry guests.
* A trip (game/island_trips.py) lasts SESSION_MIN minutes, the owner can end it sooner; going alone needs no vehicle.
Ids are stored in saves and in the island_trips table: never rename or remove one (retire it with `gone: True`).
"""

ISLANDS = (
    dict(id='dao_dua', emoji='🏝️', name='Đảo Dừa', price=15_000_000, bp=30, look='dua',
         where='Ngoài vịnh Phố Mây, 40 phút du thuyền',
         desc='Bãi cát trắng, rặng dừa nghiêng, một biệt thự gỗ và cầu tàu ra làn nước xanh.'),
    dict(id='dao_san_ho', emoji='🌺', name='Đảo San Hô', price=30_000_000, bp=30, look='san_ho',
         where='Giữa rạn san hô phía nam',
         desc='Nước trong thấy đáy, nhà sàn trên mặt biển, rạn san hô ngay sát bờ để lặn.'),
    dict(id='dao_may_da', emoji='🌋', name='Đảo Mây Đá', price=60_000_000, bp=25, look='may_da',
         where='Hòn núi lửa đã ngủ, mây phủ quanh năm',
         desc='Vách đá đen, suối nước nóng giữa rừng, đài ngắm sao trên đỉnh đồi.'),
    dict(id='dao_hoang_hon', emoji='👑', name='Đảo Hoàng Hôn', price=100_000_000, bp=25, look='hoang_hon',
         where='Xa nhất vịnh, nhìn thẳng ra hoàng hôn',
         desc='Đường băng riêng, ngọn hải đăng, dinh thự ba tầng và hồ bơi tràn bờ.'),
)
SELL_PCT = 60                 # bought back at 60 % of the price paid (like the villas)
SESSION_MIN = 60              # one trip on the island: 60 minutes, the owner may end it sooner
INVITE_MAX = 30               # invitations (pending or aboard) on one trip at most

# vehicle id -> (seats, the owner included; where it arrives). Never rename a key: they are game/garage.py and
# game/lux_content.py ids.
SEATS = {
    'thuyen_buom': (4, 'boat'),          # ⛵ Thuyền buồm nhỏ
    'du_thuyen': (8, 'boat'),            # 🛥️ Du thuyền Hoàng Hôn
    'sieu_du_thuyen': (12, 'boat'),      # 🛳️ Siêu du thuyền Ngọc Trai
    'du_thuyen_hg': (20, 'boat'),        # 🛳️ Siêu du thuyền Hoàng Gia (Mua sắm)
    'may_bay_nho': (2, 'plane'),         # 🛩️ Máy bay cánh quạt: hai chỗ ngồi
    'truc_thang': (4, 'heli'),           # 🚁 Trực thăng riêng: bốn ghế
    'phan_luc': (8, 'plane'),            # ✈️ Phản lực riêng: tám ghế da
    'truc_thang_vip': (6, 'heli'),       # 🚁 Trực thăng VIP (Mua sắm)
    'chuyen_co': (16, 'plane'),          # 🛫 Chuyên cơ thân rộng (Mua sắm)
    'lx_du_thuyen_01': (12, 'boat'),     # 🏎️ Ngọc Trai Đêm số 01 (Nhà đấu giá, bản giới hạn: a superyacht)
    'lx_phan_luc_01': (8, 'plane'),      # 🏎️ Phản lực Cánh Mây số 01 (Nhà đấu giá, bản giới hạn: a jet)
}
GROUP_SEATS = {'boat': (4, 'boat'), 'plane': (4, 'plane')}   # a garage boat / plane this table does not list yet
SEATS_MAX = 40
ARRIVE = {'solo': '🚤 Xuồng của đảo', 'boat': 'Cầu tàu', 'heli': 'Bãi đáp trực thăng', 'plane': 'Đường băng'}
