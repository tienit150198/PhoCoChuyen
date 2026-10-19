"""🏗️ Xây trên đảo: the plots of every private island and the buildings that go on them (data only).

Owner 19/10: "công trình trên đảo k kiếm tiền, xây dựng nơi riêng, nhà này kia thôi", "thời gian lên đảo thoải mái".
A pure money sink and a place of one's own: no building ever pays xu, takes guests' money, shortens a job or changes an
income. What a building gives: it stands on the island for everyone who comes (2.5D and the old 2D map), its leisure
spots (swim, picnic, putt, camp, moor) and a small daily tinh thần for using them, the homes' "inside" view, and the
weekly 🏝️ Đảo đẹp board's points (a title only, game/island_lb.py).

* PLOTS: island id (game/island_content.py) → its plots, in order: (x, y, coast) as fractions of the island's square map
  (x east, y south), the same numbers public/js/island-layout.js draws (tests/test_island_build.py checks both lists
  match). The plot index is what saves and the island_builds table store: never reorder or remove a plot, only append.
  `coast` plots touch the beach: a ⚓ bến du thuyền needs one.
* BUILDINGS: id, emoji, name, cat ('home': tap it to go inside; 'fun': a leisure spot), `pts` (the board's points per
  level), `levels` ((price in xu, real hours to build), …) for level 1, 2, 3: each level is paid in full when it starts
  and stands after its hours (scaffolding meanwhile). `max`: at most this many on one island; `coast`: coast plots
  only; `big`: only on an island of at least BIG_FROM xu (a castle needs room). `spot`: the pose a player takes there.
  Prices sit beside the islands' (30M → 200M) and the richest wallets (13–48M): a first nhà sàn is 2M, a finished
  castle 125M. Ids are stored in saves and in island_builds: never rename one.
* SALVAGE_PCT: phá dỡ (or selling the island) gives back this share of everything paid into the plot, construction in
  progress included: "thu hồi vật liệu". The 💰 board and the phí giữ tài sản lớn count a building at that value.
"""

PLOTS = {
    'dao_dua': ((.37, .52, 0), (.46, .52, 0), (.55, .52, 0), (.37, .61, 0), (.46, .61, 0), (.7, .72, 1)),
    'dao_san_ho': ((.41, .38, 0), (.5, .38, 0), (.59, .38, 0), (.68, .38, 0), (.41, .47, 0), (.5, .47, 0), (.37, .7, 0),
                   (.46, .7, 0), (.55, .7, 0), (.13, .54, 1)),
    'dao_may_da': ((.26, .5, 0), (.35, .5, 0), (.44, .5, 0), (.53, .5, 0), (.62, .5, 0), (.35, .59, 0), (.44, .59, 0),
                   (.53, .59, 0), (.62, .59, 0), (.71, .59, 0), (.35, .68, 0), (.44, .68, 0), (.53, .68, 0),
                   (.62, .68, 0), (.26, .68, 0), (.71, .68, 1)),
    'dao_hoang_hon': ((.56, .3, 0), (.65, .3, 0), (.74, .3, 0), (.215, .43, 0), (.305, .43, 0), (.215, .52, 0),
                      (.305, .52, 0), (.305, .61, 0), (.4, .42, 0), (.49, .42, 0), (.58, .42, 0), (.4, .51, 0),
                      (.49, .51, 0), (.58, .51, 0), (.68, .43, 0), (.77, .43, 0), (.68, .52, 0), (.77, .52, 0),
                      (.68, .61, 0), (.4, .72, 0), (.49, .72, 0), (.58, .72, 0), (.12, .52, 1), (.88, .5, 1)),
}

M = 1_000_000
BUILDINGS = (
    # 🏠 homes: tap to go inside
    dict(id='nha_san', emoji='🛖', name='Nhà sàn', cat='home', pts=10, spot='sit',
         levels=((2 * M, 6), (4 * M, 12), (7 * M, 24)),
         lv=('Nhà sàn gỗ một gian', 'Hai gian, hiên rộng', 'Mái lá cọ, võng trên hiên'),
         desc='Nhà gỗ trên cột, gió biển lùa qua sàn.'),
    dict(id='biet_thu', emoji='🏡', name='Biệt thự biển', cat='home', pts=24, spot='sit',
         levels=((8 * M, 18), (14 * M, 30), (22 * M, 48)),
         lv=('Biệt thự một tầng', 'Thêm tầng, ban công nhìn biển', 'Sân thượng, đèn vàng buổi tối'),
         desc='Tường trắng, mái xanh, cửa kính mở ra biển.'),
    dict(id='lau_dai', emoji='🏰', name='Lâu đài', cat='home', pts=50, spot='stand', max=1, big=True,
         levels=((25 * M, 36), (40 * M, 48), (60 * M, 48)),
         lv=('Tháp đá và cổng vòm', 'Hai tháp, cờ bay', 'Ba tháp, tường thành sáng đèn'),
         desc='Tháp đá, cờ trên nóc. Chỉ đảo lớn mới đủ chỗ.'),
    # 🎡 leisure: walk up and use it
    dict(id='cong_vien', emoji='🌳', name='Công viên', cat='fun', pts=8, spot='sit',
         levels=((1_500_000, 6), (3 * M, 12), (5 * M, 18)),
         lv=('Bãi cỏ, ghế đá', 'Thêm hoa, lối đi', 'Đài phun nước'),
         desc='Ghế đá dưới bóng cây, ngồi ngắm biển.',
         lines=('Ngồi ghế đá, gió biển mát rượi.', 'Đi dạo quanh vườn hoa, nghe chim hót.')),
    dict(id='ho_boi', emoji='🏊', name='Hồ bơi', cat='fun', pts=14, spot='swim',
         levels=((3 * M, 8), (6 * M, 16), (10 * M, 24)),
         lv=('Hồ bơi nhỏ', 'Ghế tắm nắng, dù che', 'Cầu trượt nước'),
         desc='Nước xanh trong, ghế tắm nắng quanh hồ.',
         lines=('Bơi vài vòng, nước mát lạnh.', 'Nằm phao giữa hồ, nắng chiều vàng óng.')),
    dict(id='golf', emoji='⛳', name='Sân golf mini', cat='fun', pts=20, spot='stand', max=1,
         levels=((6 * M, 12), (10 * M, 24), (16 * M, 36)),
         lv=('Ba lỗ golf', 'Hố cát, cờ mới', 'Chín lỗ, xe điện'),
         desc='Vài lỗ golf trên cỏ, gậy để sẵn.',
         lines=('Vụt một gậy, bóng lăn sát lỗ!', 'Bóng rơi vào hố cát, cười một trận.')),
    dict(id='cam_trai', emoji='🏕️', name='Khu cắm trại', cat='fun', pts=6, spot='sit',
         levels=((1 * M, 6), (2 * M, 10), (4 * M, 16)),
         lv=('Hai cái lều', 'Lửa trại, ghế gỗ', 'Lều lớn, dây đèn'),
         desc='Lều vải, lửa trại, nướng bắp ngô.',
         lines=('Ngồi quanh lửa, nướng bắp thơm phức.', 'Nằm trong lều nghe sóng vỗ.')),
    dict(id='ben_thuyen', emoji='⚓', name='Bến du thuyền', cat='fun', pts=18, spot='stand', max=1, coast=True,
         levels=((5 * M, 12), (9 * M, 24), (15 * M, 36)),
         lv=('Cầu gỗ ra biển', 'Thêm thuyền buồm', 'Du thuyền neo bến'),
         desc='Cầu gỗ ra biển, thuyền đậu sát bến. Cần ô đất sát bờ.',
         lines=('Ngồi mép cầu, thả chân xuống nước.', 'Ngắm thuyền buồm lắc lư bên bến.')),
)
LEVELS = 3
CREWS = 2                     # constructions at once on one island (two crews of builders)
SALVAGE_PCT = 20              # phá dỡ / selling the island: 20 % of what the plot cost back ("thu hồi vật liệu")
BIG_FROM = 120_000_000        # 🏰 only on Mây Đá and Hoàng Hôn
VARIETY = 10                  # board points for each different kind standing on the island
USE_SPIRIT = 1                # tinh thần for using a leisure building
USE_MAX = 3                   # … at most this many times a Vietnam day (whatever the island)
