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
# 🏡 Kiểu nhà (owner 20/10 "coi hướng đảo có thể xây nhà các kiểu đẹp và nhiều hơn"): fifteen more homes, in four tiers
# (TIERS), each in three colours (`looks`: the palettes of public/js/house-art.js HOUSES, same order). A colour is stored
# in the kind itself, '<id>__<n>' (n = 1…2; 0 is the plain id): an older build keeps such a kind by shape (never shown or
# counted, like any kind it does not know) and the island_builds table needs no new column. Same rules as the first
# three: a pure money sink, prices beside the islands' (30M → 200M), `pts` ≈ 7 × (level-1 price in millions)^0.6 like
# the first three (2M → 10, 8M → 24, 25M → 50), at most 48 hours a level; the two 👑 palaces only on a big island, one each.
def _home(id, emoji, name, tier, pts, levels, lv, desc, looks, spot='sit', **more):
    return dict(id=id, emoji=emoji, name=name, cat='home', pts=pts, spot=spot, levels=levels, lv=lv, desc=desc, tier=tier,
                looks=looks, **more)


HOUSES = (
    _home('nha_tranh', '🏚️', 'Nhà tranh vách đất', 1, 9, ((1_500_000, 6), (3 * M, 10), (5 * M, 16)),
          ('Mái tranh, vách đất, sân đất nện', 'Hàng rào tre, gian bếp bên hông', 'Đụn rơm, giếng nước, gà vườn'),
          'Mái tranh vàng, vách đất, chái bếp khói lam chiều.', ('Rơm vàng', 'Rạ nâu', 'Cỏ tranh')),
    _home('nha_tre', '🎋', 'Nhà tre sinh thái', 1, 12, ((2_500_000, 6), (4_500_000, 12), (8 * M, 20)),
          ('Nhà tre trên cột thấp, mái lá', 'Hiên tre, bồn rau trước nhà', 'Pin mặt trời, bồn nước mưa, dây đèn'),
          'Tre ghép, mái lá, gió lùa mát rượi. Sống xanh giữa đảo.', ('Lá xanh', 'Rơm', 'Lá cọ sẫm')),
    _home('nha_cay', '🌳', 'Nhà trên cây', 1, 14, ((3 * M, 8), (6 * M, 14), (10 * M, 24)),
          ('Căn chòi gỗ trên cây cổ thụ', 'Lan can quanh sàn, xích đu thả xuống', 'Cầu trượt, dây đèn lấp lánh'),
          'Leo thang gỗ lên căn chòi giữa tán lá.', ('Gỗ mộc', 'Xanh trời', 'Đỏ gạch'), spot='stand'),
    _home('cabin_go', '🛖', 'Cabin gỗ chữ A', 1, 16, ((4 * M, 8), (7 * M, 16), (12 * M, 24)),
          ('Mái chữ A, cửa kính tam giác', 'Hiên gỗ bên hông, củi xếp gọn', 'Bồn tắm nóng, dây đèn vàng'),
          'Mái dốc chữ A, ống khói và khung kính nhìn ra biển.', ('Gỗ sẫm', 'Đỏ kho thóc', 'Bạch dương')),
    _home('bungalow', '🏝️', 'Bungalow mái lá', 2, 18, ((5 * M, 10), (9 * M, 18), (15 * M, 30)),
          ('Nhà gỗ trên nền đá, mái lá cao', 'Hồ ngâm nhỏ bên hiên', 'Ghế tắm nắng, đuốc tre, cây sứ trắng'),
          'Mái lá dựng cao kiểu nhiệt đới, hiên mở bốn phía.', ('Gỗ tếch', 'Vôi trắng', 'Gỗ sẫm')),
    _home('pho_hoi_an', '🏮', 'Nhà phố Hội An', 2, 20, ((6 * M, 12), (10 * M, 20), (16 * M, 30)),
          ('Tường vàng, cửa gỗ, đèn lồng', 'Lên lầu, ban công gỗ', 'Giàn hoa giấy, đèn lồng sáng cả đêm'),
          'Tường vàng, mái ngói âm dương, đèn lồng trước hiên.', ('Vàng nghệ', 'Xanh ngọc', 'Hồng đào')),
    _home('nha_ruong', '🏯', 'Nhà rường Huế', 2, 22, ((7 * M, 12), (12 * M, 24), (18 * M, 36)),
          ('Nhà gỗ ba gian, hiên cột', 'Thêm nhà ngang phía sau', 'Bình phong, ao sen, chậu kiểng'),
          'Gỗ lim ba gian, mái ngói cong đầu đao kiểu cố đô.', ('Ngói đỏ', 'Ngói rêu', 'Ngói vàng')),
    _home('hai_dang', '🗼', 'Nhà hải đăng', 2, 22, ((7 * M, 12), (12 * M, 24), (20 * M, 36)),
          ('Ngọn tháp và căn nhà người gác', 'Tháp cao hơn, đèn quét ra biển', 'Đèn sáng rực, cờ hiệu bên nhà'),
          'Tháp sọc đỏ trắng, đèn quét qua mặt biển mỗi tối.', ('Đỏ trắng', 'Xanh trắng', 'Đen trắng'), spot='stand', max=1),
    _home('nha_nhat', '🎎', 'Nhà kiểu Nhật', 2, 24, ((8 * M, 16), (14 * M, 24), (22 * M, 36)),
          ('Cửa giấy shoji, hiên gỗ', 'Thêm tầng, mái hai lớp', 'Đèn đá, hồ cá koi, cây phong đỏ'),
          'Cửa giấy, sàn chiếu, mái ngói xám vươn rộng.', ('Ngói xám', 'Mái đồng xanh', 'Ngói đen')),
    _home('hanok', '🏘️', 'Nhà kiểu Hàn (Hanok)', 2, 24, ((8 * M, 16), (14 * M, 24), (22 * M, 36)),
          ('Nền đá, khung gỗ, mái ngói cong', 'Thêm chái nhà hình chữ L', 'Hũ tương, cây hồng, tường đá thấp'),
          'Khung gỗ, giấy dán cửa, mái ngói cong mềm như cánh chim.', ('Ngói than', 'Ngói ngọc', 'Ngói nâu đất')),
    _home('villa_phap', '🏛️', 'Biệt thự Pháp', 3, 31, ((12 * M, 24), (20 * M, 36), (32 * M, 48)),
          ('Tường vàng kem, cửa chớp xanh', 'Lên lầu, ban công sắt', 'Vườn xén, đài phun nước'),
          'Kiểu Đà Lạt xưa: mái ngói dốc, cửa chớp, ống khói.', ('Vàng kem', 'Trắng mái xám', 'Hồng phấn')),
    _home('dia_trung_hai', '🏖️', 'Biệt thự Địa Trung Hải', 3, 34, ((14 * M, 24), (22 * M, 36), (35 * M, 48)),
          ('Khối trắng, mái vòm xanh', 'Thêm phòng bên, sân thượng', 'Hồ bơi, tháp chuông, dù che nắng'),
          'Tường trắng, mái vòm xanh, hoa giấy hồng trên vách.', ('Mái vòm xanh', 'Mái vòm ngọc', 'Mái vòm đất nung')),
    _home('villa_kinh', '🪟', 'Biệt thự kính hiện đại', 3, 39, ((18 * M, 24), (28 * M, 36), (45 * M, 48)),
          ('Một tầng vách kính, mái phẳng', 'Tầng hai đua ra, vườn trên mái', 'Hồ bơi tràn bờ, đèn sáng cả nhà'),
          'Vách kính từ sàn tới trần, mái phẳng, nhìn thẳng ra biển.', ('Kính xanh', 'Kính khói', 'Gỗ ấm')),
    _home('dinh_thu', '🏰', 'Dinh thự châu Âu', 4, 54, ((30 * M, 36), (48 * M, 48), (70 * M, 48)),
          ('Nhà đá hai tháp tròn', 'Thêm hai tháp sau, cờ bay', 'Vườn xén, đài phun nước, đèn sáng'),
          'Tường đá, tháp nhọn mái lam. Chỉ đảo lớn mới đủ chỗ.', ('Đá kem mái lam', 'Đá trắng mái đồng', 'Đá hồng mái than'),
          spot='stand', max=1, big=True),
    _home('hoang_cung', '👑', 'Hoàng cung Á Đông', 4, 59, ((35 * M, 36), (55 * M, 48), (80 * M, 48)),
          ('Điện son hai tầng mái', 'Thêm hai điện phụ phía sau', 'Đèn lồng, cờ phướn, bảo châu trên nóc'),
          'Cột son thếp vàng, mái ngói hoàng gia. Chỉ đảo lớn mới đủ chỗ.', ('Ngói hoàng gia', 'Ngói lưu ly xanh', 'Ngói đỏ son'),
          spot='stand', max=1, big=True),
)
BUILDINGS = BUILDINGS + HOUSES
# The tiers the 🏗️ Xây sheet groups the homes by (the first three homes: nhà sàn 1, biệt thự 3, lâu đài 4).
TIERS = ((1, '🌾 Mộc mạc'), (2, '🏮 Phong vị'), (3, '💎 Sang trọng'), (4, '👑 Đỉnh cao'))
TIER_OF = dict(nha_san=1, biet_thu=3, lau_dai=4)
LOOKS = 3                     # colours a style comes in (house-art.js VARIANTS): '<id>' and '<id>__1', '<id>__2'
PAINT_PCT = 10                # 🎨 sơn lại (another colour of the same style): 10 % of its level-1 price, at once
PAINT_MIN = 200_000

LEVELS = 3
CREWS = 2                     # constructions at once on one island (two crews of builders)
SALVAGE_PCT = 20              # phá dỡ / selling the island: 20 % of what the plot cost back ("thu hồi vật liệu")
BIG_FROM = 120_000_000        # 🏰 only on Mây Đá and Hoàng Hôn
VARIETY = 10                  # board points for each different kind standing on the island
USE_SPIRIT = 1                # tinh thần for using a leisure building
USE_MAX = 3                   # … at most this many times a Vietnam day (whatever the island)
