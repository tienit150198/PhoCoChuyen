"""🏝️ Thiết kế đảo (owner 24/10: "đảo cũng chán quá, nâng cấp đảo xịn xò hơn đi, đảo to và xây được hồ bơi, nhà,... cây
này kia đặt cho đẹp hơn"): the free grid of every private island, its size tiers (🌊 lấn biển) and the decorations that
go anywhere on it (data only; the rules: game/island_design.py).

* GRID: one square grid over each island's map, G × G cells of CELL map units from X0 (the map's x east, y south: the
  units of public/js/island-layout.js and game/island_build_content.py PLOTS). The old map was the square 0..1; the grid
  reaches X0 .. X0 + G·CELL = −0.22 .. 1.22 so an island can grow past it. A building of game/island_build_content.py
  stands on BUILD_FOOT × BUILD_FOOT cells (an old plot is .072 = 3 cells: the drawings are the same).
* SHAPES: each look's coast, the same numbers public/js/island-layout.js gives blob() (tests/test_island_design.py
  checks both lists match): centre, radii, the bumps around it, how wide the beach is.
* TIERS: the coast's scale over the old one by size tier. Tier 0 is the new base every island has (owner: "đảo to"),
  free, at once: the old coast grown 15 %. Tiers 1… are bought (EXPAND_PCT of the island's list price each, in order)
  and add EXPAND_PTS to the 🏝️ Đảo đẹp board. Nothing on land moves when the coast grows; what lies on the water
  (the pier, a dive spot, the stilt huts, a marina plot of the old map: FIXED `sea`) moves out with the coast.
* FIXED: what the island already has (the villa, the pier, the helipad or the runway, the mountain, the spots, the
  palms…): rectangles (x, y, w, h, sea) no decoration may cover, the same features public/js/island-layout.js draws.
* DECOR: the decorations (ids are stored in saves and island_layout rows: never rename one). w × h cells (turned a
  quarter: h × w), price in xu, `pts` on the 🏝️ Đảo đẹp board (pts_for(price): the buildings' 7·M^0.6, never above
  2.5 a million, 0 under 200 000), `max` on one island, `where`: land | coast (on land, touching the beach) | pier
  (some on land, some on the sea) | sea | any, `solid`: in the way of walking, `pose`: a spot to sit, lie, swim or
  stand at (no xu, no tinh thần: a place), `cat`: the 🏗️ sheet's group. A decoration is paid once, placed at once,
  moved, turned and put back into the kho (inventory) for free; it never pays anything (owner 19/10: a place, a sink).
"""

G = 60
X0 = -0.22
CELL = 0.024
BUILD_FOOT = 3
SEA_SPOTS = ('lan', 'san_ho', 'nha_san')   # the spots on the water: they move out with the coast

# look -> (cx, cy, rx, ry, bumps, sand width): public/js/island-layout.js LOOKS[look].shape
SHAPES = {
    'dua': (.5, .5, .38, .36, (1, .96, 1.04, .98, 1.02, .93, 1, 1.05), .07),
    'san_ho': (.48, .55, .4, .27, (1, 1.05, .92, 1, 1.06, .95, 1.02, .97), .085),
    'may_da': (.5, .5, .39, .37, (1, .9, 1.06, .96, 1.04, .9, 1.02, 1.08, .94), .05),
    'hoang_hon': (.5, .52, .43, .4, (1, 1.03, .97, 1.05, 1, .95, 1.04, .98), .06),
}
TIERS = (1.15, 1.25, 1.35, 1.45, 1.55)
EXPAND_PCT = (20, 30, 40, 50)          # tier 1, 2, 3, 4: this % of the island's list price
EXPAND_PTS = (20, 25, 30, 40)
EXPAND_NAMES = ('Lấn biển lần 1', 'Lấn biển lần 2', 'Lấn biển lần 3', 'Lấn biển lần 4')

# look -> ((x, y, w, h, sea), …): public/js/island-layout.js fixedRects(LOOKS[look]) (the villa, the dock, the pad, the
# spots, the deco, the blocks, the palms), checked by tests/test_island_design.py.
_PALM = .02
_SPOT = .03


def _palms(*pts):
    return tuple((x, y, _PALM, _PALM, 0) for x, y in pts)


FIXED = {
    'dua': ((.5, .36, .17, .11, 0), (.47, .82, .06, .16, 1), (.76, .58, .09, .09, 0),
            (.25, .47, _SPOT, _SPOT, 0), (.42, .7, _SPOT, _SPOT, 0), (.62, .68, _SPOT, _SPOT, 0), (.15, .42, _SPOT, _SPOT, 1))
           + _palms((.24, .38), (.3, .3), (.2, .55), (.31, .64), (.72, .3), (.78, .42), (.62, .24), (.4, .78), (.66, .8)),
    'san_ho': ((.27, .47, .14, .09, 0), (.24, .21, .05, .28, 1), (.72, .62, .09, .09, 0),
               (.3, .12, _SPOT, _SPOT, 1), (.86, .32, _SPOT, _SPOT, 1), (.6, .55, _SPOT, _SPOT, 0), (.38, .62, _SPOT, _SPOT, 0),
               (.2, .62, _SPOT, _SPOT, 0),
               (.86, .28, .098, .056, 1), (.12, .84, .07, .04, 1), (.7, .9, .056, .032, 1), (.33, .09, .05, .04, 1), (.4, .13, .05, .04, 1),
               (.33, .12, .14, .04, 1))
              + _palms((.17, .45), (.3, .6), (.82, .5), (.8, .42), (.16, .6), (.62, .79), (.8, .62)),
    'may_da': ((.33, .38, .13, .09, 0), (.6, .84, .05, .14, 1), (.72, .42, .09, .09, 0),
               (.56, .24, _SPOT, _SPOT, 0), (.2, .62, _SPOT, _SPOT, 0), (.45, .78, _SPOT, _SPOT, 0), (.87, .62, _SPOT, _SPOT, 1),
               (.56, .3, .182, .104, 0), (.2, .59, .05, .05, 0), (.6, .18, .05, .05, 0), (.18, .3, .08, .04, 0), (.82, .8, .08, .04, 0),
               (.5, .3, .14, .08, 0))
              + _palms((.14, .52), (.3, .76), (.67, .77), (.8, .58), (.2, .43)),
    'hoang_hon': ((.4, .31, .2, .11, 0), (.6, .88, .06, .11, 1),
                  (.86, .36, _SPOT, _SPOT, 0), (.5, .6, _SPOT, _SPOT, 0), (.3, .7, _SPOT, _SPOT, 0), (.72, .74, _SPOT, _SPOT, 0),
                  (.42, .82, _SPOT, _SPOT, 0),
                  (.5, .2, .56, .06, 0), (.86, .32, .05, .05, 0), (.5, .6, .175, .075, 0))
                 + _palms((.11, .62), (.24, .68), (.88, .62), (.76, .68), (.35, .87), (.66, .86), (.14, .36)),
}


def pts_for(price: int) -> int:
    """The 🏝️ Đảo đẹp points of a decoration of this price: the buildings' 7·M^0.6 (game/island_build_content.py),
    never more than 2.5 a million (so many small things are no cheaper a point than a castle), 0 under 200 000 xu."""
    if price < 200_000:
        return 0
    m = price / 1_000_000
    return max(1, round(min(7 * m ** 0.6, 2.5 * m)))


CATS = (('cay', '🌴 Cây'), ('ho', '🏊 Hồ bơi'), ('ct', '🏛️ Công trình'), ('do', '🪑 Ngoài trời'), ('loi', '🛤️ Lối đi'),
        ('bien', '🌊 Bờ biển'))
M = 1_000_000


def _d(id, emoji, name, cat, w, h, price, mx, where='land', solid=True, pose='', rot=True, desc=''):
    return dict(id=id, emoji=emoji, name=name, cat=cat, w=w, h=h, price=price, pts=pts_for(price), max=mx, where=where,
                solid=solid, pose=pose, rot=rot, desc=desc)


DECOR = (
    # 🌴 trees and flowers
    _d('cay_dua', '🌴', 'Cây dừa', 'cay', 1, 1, 300_000, 60, desc='Thân nghiêng, tàu lá đung đưa trong gió.'),
    _d('cay_co', '🌿', 'Cọ quạt', 'cay', 1, 1, 250_000, 60, desc='Lá xòe như cái quạt.'),
    _d('khom_tre', '🎋', 'Khóm tre', 'cay', 1, 1, 220_000, 60, desc='Tre xanh rì rào.'),
    _d('thong_bien', '🌲', 'Thông biển', 'cay', 1, 1, 400_000, 40, desc='Dáng thẳng, lá kim xanh đậm.'),
    _d('hoa_giay', '🌺', 'Hoa giấy', 'cay', 1, 1, 350_000, 40, desc='Chùm hoa hồng rực trên vách.'),
    _d('cay_chuoi', '🍌', 'Bụi chuối', 'cay', 1, 1, 180_000, 40, desc='Tàu chuối to bản, mát cả góc vườn.'),
    _d('xuong_rong', '🌵', 'Xương rồng', 'cay', 1, 1, 150_000, 30, desc='Chịu nắng, chịu gió biển.'),
    _d('bui_hoa', '🌼', 'Bụi hoa', 'cay', 1, 1, 120_000, 80, desc='Bụi hoa nhỏ nhiều màu.'),
    _d('luong_hoa', '🌷', 'Luống hoa', 'cay', 2, 1, 450_000, 40, desc='Một luống tulip đủ màu.'),
    _d('huong_duong', '🌻', 'Hàng hướng dương', 'cay', 2, 1, 500_000, 30, desc='Hoa vàng hướng về mặt trời.'),
    _d('cay_bang', '🌳', 'Bàng biển', 'cay', 2, 2, 700_000, 20, desc='Tán rộng che cả một khoảng sân.'),
    _d('cay_phuong', '🌳', 'Phượng vĩ', 'cay', 2, 2, 900_000, 20, desc='Mùa hè đỏ rực một góc trời.'),
    _d('tung_canh', '🌲', 'Tùng bonsai', 'cay', 1, 1, 1_200_000, 12, desc='Cây cảnh dáng thế, chậu men xanh.'),
    _d('hoa_dao', '🌸', 'Anh đào', 'cay', 2, 2, 1_500_000, 12, desc='Tán hoa hồng phấn, cánh rơi lả tả.'),
    _d('vuon_hoa', '🌷', 'Vườn hoa', 'cay', 3, 2, 1_600_000, 10, desc='Luống hoa nhiều màu, viền đá trắng.'),
    # 🏊 pools (walk in: a swim)
    _d('ho_ca', '🐟', 'Hồ cá koi', 'ho', 2, 2, 1_800_000, 6, solid=False, pose='stand', desc='Cá koi đỏ trắng lượn dưới lá sen.'),
    _d('ho_nho', '🏊', 'Hồ bơi nhỏ', 'ho', 2, 2, 2_500_000, 6, solid=False, pose='swim', desc='Vừa đủ ngâm mình ngắm trời.'),
    _d('be_suc', '♨️', 'Bể sục', 'ho', 2, 2, 3_000_000, 4, solid=False, pose='swim', desc='Bể tròn sủi bọt ấm.'),
    _d('ho_dai', '🏊', 'Hồ bơi chữ nhật', 'ho', 3, 2, 5_000_000, 6, solid=False, pose='swim', desc='Làn nước xanh, bậc thang inox.'),
    _d('ho_tron', '🫧', 'Hồ bơi bo tròn', 'ho', 3, 3, 7_000_000, 4, solid=False, pose='swim', desc='Bờ cong mềm như hạt đậu.'),
    _d('ho_lon', '🏖️', 'Hồ bơi lớn có bậc', 'ho', 4, 3, 11_000_000, 3, solid=False, pose='swim', desc='Bậc lội, đảo nhỏ giữa hồ.'),
    _d('ho_tran', '🌅', 'Hồ tràn bờ', 'ho', 5, 3, 20_000_000, 2, where='coast', solid=False, pose='swim',
       desc='Mép hồ liền mặt biển. Đặt sát bờ.'),
    # 🏛️ structures
    _d('lua_trai', '🔥', 'Đống lửa trại', 'ct', 1, 1, 300_000, 6, solid=False, pose='sit', desc='Củi xếp, lửa tí tách.'),
    _d('cong_hoa', '💐', 'Cổng hoa', 'ct', 2, 1, 900_000, 8, solid=False, desc='Vòm hoa hồng trên lối đi.'),
    _d('khu_bbq', '🍖', 'Khu BBQ', 'ct', 2, 2, 1_200_000, 4, pose='stand', desc='Lò nướng, bàn gỗ, dây đèn.'),
    _d('choi_la', '🛖', 'Chòi lá', 'ct', 2, 2, 1_500_000, 8, pose='sit', desc='Mái lá cọ, ngồi hóng gió.'),
    _d('cau_vom', '🌉', 'Cầu vòm gỗ', 'ct', 1, 3, 2_000_000, 6, where='any', solid=False, desc='Cầu gỗ cong qua suối hay mép nước.'),
    _d('suoi_da', '💧', 'Suối đá', 'ct', 1, 3, 2_500_000, 6, desc='Dòng nước nhỏ róc rách qua sỏi.'),
    _d('san_choi', '🛝', 'Sân chơi', 'ct', 3, 3, 2_800_000, 3, pose='stand', desc='Cầu trượt, xích đu, bập bênh.'),
    _d('dai_phun', '⛲', 'Đài phun nước', 'ct', 2, 2, 4_000_000, 4, desc='Tia nước lấp lánh giữa sân.'),
    _d('nha_kinh', '🪴', 'Nhà kính', 'ct', 3, 2, 5_000_000, 3, desc='Vườn lan trong khung kính.'),
    _d('nha_thuyen', '🛥️', 'Nhà thuyền', 'ct', 3, 3, 5_000_000, 2, where='coast', desc='Mái gỗ che du thuyền. Đặt sát bờ.'),
    _d('nha_go', '🏠', 'Nhà gỗ', 'ct', 3, 3, 6_000_000, 4, pose='sit', desc='Nhà gỗ thông, hiên rộng nhìn ra biển.'),
    _d('san_tennis', '🎾', 'Sân tennis', 'ct', 5, 4, 8_000_000, 1, solid=False, pose='stand', desc='Mặt sân xanh, lưới trắng.'),
    _d('bungalow_nuoc', '🏝️', 'Bungalow trên nước', 'ct', 3, 3, 12_000_000, 6, where='pier',
       desc='Nhà sàn mái lá giữa làn nước. Đặt một phần trên bờ.'),
    _d('thac_nuoc', '🏞️', 'Thác nước', 'ct', 4, 3, 16_000_000, 2, desc='Vách đá, thác trắng đổ xuống hồ xanh.'),
    _d('resort', '🏨', 'Khu resort', 'ct', 6, 5, 45_000_000, 1, desc='Sảnh mái cong, hai dãy phòng, hồ bơi giữa.'),
    # 🪑 outdoors
    _d('den_vuon', '💡', 'Đèn vườn', 'do', 1, 1, 180_000, 40, desc='Sáng ấm khi trời tối.'),
    _d('chau_hoa', '🪴', 'Chậu hoa', 'do', 1, 1, 100_000, 60, desc='Chậu gốm, hoa dại.'),
    _d('o_du', '⛱️', 'Ô dù bãi biển', 'do', 1, 1, 300_000, 20, desc='Dù sọc che nắng.'),
    _d('ghe_go', '🪑', 'Ghế gỗ', 'do', 2, 1, 300_000, 20, pose='sit', desc='Băng ghế gỗ nhìn ra biển.'),
    _d('cot_den', '🏮', 'Cột đèn', 'do', 1, 1, 350_000, 30, desc='Cột đèn sắt kiểu cũ.'),
    _d('vong', '🛏️', 'Võng', 'do', 2, 1, 350_000, 10, pose='lie', desc='Võng dù mắc giữa hai cột.'),
    _d('ghe_dai', '🏖️', 'Ghế tắm nắng', 'do', 1, 2, 400_000, 20, solid=False, pose='lie', desc='Nằm dài nghe sóng.'),
    _d('xich_du', '🪢', 'Xích đu', 'do', 2, 1, 600_000, 8, pose='sit', desc='Xích đu gỗ đôi.'),
    _d('bo_ban_ghe', '☕', 'Bàn ghế ngoài trời', 'do', 2, 2, 700_000, 12, pose='sit', desc='Bàn tròn, bốn ghế, dù che.'),
    _d('kinh_thien_van', '🔭', 'Kính thiên văn', 'do', 1, 1, 800_000, 3, pose='stand', desc='Ngắm sao, ngắm tàu xa.'),
    _d('tuong_da', '🗿', 'Tượng đá', 'do', 1, 1, 1_000_000, 6, desc='Tượng đá rêu phong.'),
    # 🛤️ paths and fences (paths are walked on)
    _d('loi_soi', '⚪', 'Lối sỏi', 'loi', 1, 1, 30_000, 200, solid=False, desc='Sỏi trắng lạo xạo.'),
    _d('loi_da', '🪨', 'Đường lát đá', 'loi', 1, 1, 40_000, 200, solid=False, desc='Đá phiến xám ghép.'),
    _d('loi_gach', '🧱', 'Gạch đỏ', 'loi', 1, 1, 45_000, 200, solid=False, desc='Gạch nung xếp xương cá.'),
    _d('loi_go', '🟫', 'Sàn gỗ', 'loi', 1, 1, 50_000, 200, solid=False, desc='Ván gỗ lót đường.'),
    _d('rao_go', '🪵', 'Rào gỗ', 'loi', 1, 1, 60_000, 150, desc='Rào gỗ mộc.'),
    _d('rao_tre', '🎋', 'Rào tre', 'loi', 1, 1, 70_000, 150, desc='Rào tre đan.'),
    _d('rao_trang', '🤍', 'Rào trắng', 'loi', 1, 1, 80_000, 150, desc='Rào sơn trắng.'),
    _d('rao_cay', '🌳', 'Hàng rào cây', 'loi', 1, 1, 90_000, 150, desc='Bụi cây xén vuông.'),
    # 🌊 the shore
    _d('da_bien', '🪨', 'Đá bờ biển', 'bien', 1, 1, 100_000, 40, where='any', desc='Đá tròn nhẵn sóng.'),
    _d('phao_boi', '🛟', 'Phao bơi', 'bien', 1, 1, 150_000, 20, where='sea', solid=False, desc='Phao đỏ trắng nổi dập dềnh.'),
    _d('lau_dai_cat', '🏰', 'Lâu đài cát', 'bien', 1, 1, 150_000, 10, desc='Ai đắp mà khéo thế.'),
    _d('da_lon', '⛰️', 'Cụm đá lớn', 'bien', 2, 2, 400_000, 12, where='any', desc='Mấy tảng đá xếp chồng.'),
    _d('kayak', '🛶', 'Thuyền kayak', 'bien', 1, 2, 500_000, 6, where='coast', desc='Kayak đỏ kéo lên bãi.'),
    _d('cau_tau', '⚓', 'Cầu tàu gỗ', 'bien', 1, 4, 1_800_000, 4, where='pier', solid=False, pose='stand',
       desc='Cầu gỗ ra biển, đi được. Đặt một đầu trên bờ.'),
    _d('du_thuyen', '🛳️', 'Du thuyền neo', 'bien', 2, 5, 25_000_000, 2, where='sea', desc='Du thuyền trắng neo ngoài khơi.'),
    _d('bong_chuyen', '🏐', 'Sân bóng chuyền bãi biển', 'bien', 4, 3, 3_000_000, 1, solid=False, pose='stand',
       desc='Lưới căng giữa bãi cát.'),
)
ITEMS_MAX = 300          # decorations on one island
INV_MAX = 999            # of one kind in the kho
PTS_COPIES = 12          # the board counts at most this many of one decoration on an island
VARIETY = 3              # board points for each different decoration placed
