"""✈️ Du lịch trải nghiệm: the catalogue of game/travel.py (pure data; prices are indexed at import by game/travel.py).

Feedback #464 (owner OK 23/10, "du lịch trải nghiệm thật"): "bấm đi du lịch chọn nước và mua vé đi máy bay, bay liền thì
giá vé mắc, mua trước 4-5 ngày thì giá ổn, xong lên máy bay rồi tiếp viên phục vụ và xuống máy bay rồi mình tham quan
vùng đất mới". Each place has its own look (sky, ground, accent, a skyline of emoji), a greeting on landing, five spots
(a photo, a dish, a light game or a rest, each a small scene) and three souvenirs.

Money (DESIGN_0610 §0.1 and docs/CAREER_SCALE_VALIDATION_2026-10-14.md): a median player earns ≈ 262 xu a life day and
holds ≈ 600 xu; Xả stress's "Cuối tuần lên Đà Lạt" costs 120 (base). So a domestic return ticket booked early costs
about one good day's pay (240–340 base), flying today twice that; abroad 1,100 (Thái Lan, no visa) to 5,500 (Mỹ, the
consulate's visa of game/lux.py first). Spots cost 0–150, souvenirs 45–1,500. Nothing here earns xu.

Ids are stored in saves (book.to, trip.seen, cards, souv, stamps): never rename or remove one.
"""

# ---------------------------------------------------------------- tickets
# Days booked ahead (index) -> percent of the best fare. Booking 4+ life days ahead is the good price.
AHEAD_PCT = (200, 160, 135, 115, 100, 100, 100, 100)
MAX_AHEAD = len(AHEAD_PCT) - 1
GOOD_AHEAD = 4
CLASSES = (
    dict(id='eco', emoji='💺', name='Phổ thông', mult=1, lux='pho_thong'),
    dict(id='biz', emoji='🥂', name='Thương gia', mult=3, lux='thuong_gia'),
)
REFUND_EARLY = 90      # % back when cancelled before the flight's life day
REFUND_LATE = 50       # % back when cancelled on the day, or when the flight was missed (automatic)
STAY_DAYS = 2          # a trip still open this many life days after departure flies home by itself
HOME_AIRPORT = 'Sân bay Thành phố'
AIRLINE = 'Mây Air'
FLIGHT_PREFIX = 'MA'

# Tinh thần and the needs bars (game/needs.py), all inside their 0–100 caps.
LAND_SPIRIT = dict(eco=5, biz=8)
HOME_SPIRIT = 2
MEAL_SPIRIT = dict(eco=1, biz=2)
MEAL_FULL = 25          # bụng after a meal on board
FOOD_FULL = 15          # bụng after a dish at a spot
REST_WAKE = 15          # tỉnh táo after a rest spot
BIZ_WAKE = 10           # tỉnh táo after a lie-flat seat
SOUV_MAX = 99
LOG_MAX = 12

# ---------------------------------------------------------------- on board (included in the ticket)
MEALS = dict(
    food=(
        dict(id='com_ga', emoji='🍗', name='Cơm gà xối mỡ', cls='eco'),
        dict(id='mi_bo', emoji='🍝', name='Mì xào bò', cls='eco'),
        dict(id='banh_mi', emoji='🥖', name='Bánh mì pa tê', cls='eco'),
        dict(id='bo_bit_tet', emoji='🥩', name='Bò bít tết sốt tiêu', cls='biz'),
        dict(id='pho_bo', emoji='🍜', name='Phở bò Hà Nội', cls='biz'),
        dict(id='ca_hoi', emoji='🐟', name='Cá hồi áp chảo', cls='biz'),
    ),
    drink=(
        dict(id='nuoc_suoi', emoji='💧', name='Nước suối', cls='eco'),
        dict(id='nuoc_cam', emoji='🍊', name='Nước cam', cls='eco'),
        dict(id='tra_nong', emoji='🍵', name='Trà nóng', cls='eco'),
        dict(id='ca_phe', emoji='☕', name='Cà phê sữa', cls='eco'),
        dict(id='tra_sen', emoji='🪷', name='Trà sen', cls='biz'),
        dict(id='sinh_to', emoji='🥭', name='Sinh tố xoài', cls='biz'),
        dict(id='vang_do', emoji='🍷', name='Vang đỏ', cls='biz'),
    ),
)
SERVE_LINES = ('Dạ của mình đây ạ. Chúc mình ngon miệng!',
               'Món nóng nên mình ăn từ từ nha. Cần gì cứ bấm chuông ạ.',
               'Dạ đây ạ. Hôm nay bếp làm món này ngon lắm đó!')
# Small talk with the crew (the client's, no command): ask -> answer.
CREW = (
    dict(id='chan', ask='🧣 Xin thêm chăn', say='Dạ chăn với gối của mình đây ạ. Lạnh quá cứ gọi em nha.'),
    dict(id='gio', ask='⏰ Bao lâu nữa tới?', say='Mình còn khoảng {m} phút nữa là hạ cánh ạ.'),
    dict(id='rem', ask='🪟 Mở rèm ngắm mây', say='Mây hôm nay đẹp lắm ạ! Lát nữa nghiêng cánh là thấy cả bờ biển.'),
    dict(id='anh', ask='📸 Nhờ chụp một tấm', say='Cười lên nào… một, hai, ba! Xinh lắm ạ.'),
    dict(id='keo', ask='🍬 Xin kẹo ngậm', say='Kẹo gừng của mình đây ạ, ngậm cho đỡ ù tai lúc hạ cánh nha.'),
)
CAPTAIN = dict(up='Cơ trưởng xin chào! Chúng ta đang bay ở độ cao 10.000 mét, trời quang, chúc quý khách chuyến bay vui vẻ.',
               down='Máy bay chuẩn bị hạ cánh. Quý khách vui lòng thắt dây an toàn và dựng thẳng lưng ghế.')

# ---------------------------------------------------------------- places
# kind: vn | intl. base: the best economy return fare (booked GOOD_AHEAD+ days ahead), before game/price_index.py.
# fly: minutes in the air. visa: the game/lux.py country whose visa this place needs ('' none).
# sky/land/accent: the scene's colours. skyline: the emoji drawn along the ground.
# Spots: kind photo (a postcard shot) | food (a dish: bụng) | play (a light game) | rest (tỉnh táo); fee in xu (base).


def _s(id, emoji, name, kind, fee, sp, line):
    return dict(id=id, emoji=emoji, name=name, kind=kind, fee=fee, sp=sp, line=line)


def _g(id, emoji, name, price):
    return dict(id=id, emoji=emoji, name=name, price=price)


DESTS = (
    dict(id='da_lat', kind='vn', flag='🌲', name='Đà Lạt', area='Lâm Đồng', airport='Liên Khương', base=240, fly=55, visa='',
         sky='#bfe3f2', land='#6d9f6a', accent='#8e5bb5', skyline='🌲⛪🌸🏡🌲',
         tag='Thành phố sương mù, đồi thông và dâu tây.',
         greet='Gió lạnh ùa vào cửa máy bay. Đà Lạt 16°C, ai cũng kéo khóa áo khoác.',
         spots=(_s('dl_ho', '🦢', 'Hồ Xuân Hương', 'photo', 0, 3, 'Sương còn lãng đãng trên mặt hồ, đàn vịt thiên nga chở khách chầm chậm.'),
                _s('dl_cho', '🫓', 'Chợ đêm Đà Lạt', 'food', 25, 4, 'Bánh tráng nướng giòn rụm, ly sữa đậu nóng hổi giữa trời lạnh. Đã!'),
                _s('dl_dau', '🍓', 'Vườn dâu tây', 'play', 30, 4, 'Bạn hái đầy một rổ dâu đỏ mọng, hái trái nào ăn luôn trái đó.'),
                _s('dl_ga', '🚂', 'Ga Đà Lạt', 'photo', 10, 3, 'Nhà ga ba mái nhọn, đầu tàu hơi nước đỏ thắm. Một tấm ảnh “rất Đà Lạt”.'),
                _s('dl_doi', '☁️', 'Đồi thông săn mây', 'rest', 0, 4, 'Bạn nằm dài trên cỏ dưới tán thông, nghe gió hát vi vu.')),
         souv=(_g('dl_mut', '🍓', 'Mứt dâu tây', 45), _g('dl_atiso', '🍵', 'Trà atiso', 70), _g('dl_khan', '🧣', 'Khăn len đan tay', 160))),
    dict(id='hoi_an', kind='vn', flag='🏮', name='Hội An', area='Quảng Nam', airport='Đà Nẵng', base=280, fly=80, visa='',
         sky='#ffe2b0', land='#c99a4b', accent='#d9822b', skyline='🏮🏯🛶🏮🌳',
         tag='Phố cổ tường vàng, đèn lồng và sông Hoài.',
         greet='Xe đưa bạn từ Đà Nẵng vào phố cổ. Tường vàng, đèn lồng đung đưa trong gió.',
         spots=(_s('ha_cau', '🌉', 'Chùa Cầu', 'photo', 0, 3, 'Cây cầu gỗ mái ngói bốn trăm năm tuổi. Bạn đứng bên kia sông chụp cho đủ cả mái.'),
                _s('ha_cao', '🍜', 'Quán cao lầu', 'food', 30, 4, 'Cao lầu sợi dai, thịt xíu, rau Trà Quế thơm lừng.'),
                _s('ha_den', '🪷', 'Thả đèn hoa đăng', 'play', 20, 5, 'Bạn thả chiếc đèn giấy xuống sông Hoài, ước một điều thật nhỏ.'),
                _s('ha_may', '👗', 'Tiệm may áo dài', 'photo', 40, 3, 'Cô thợ đo mười phút là xong. Mặc thử một bộ, chụp liền một tấm.'),
                _s('ha_thung', '🛶', 'Thuyền thúng Rừng Dừa', 'play', 40, 5, 'Chú lái xoay thúng tít mù, cả thuyền cười nghiêng ngả.')),
         souv=(_g('ha_den_lua', '🏮', 'Đèn lồng lụa', 60), _g('ha_gom', '🏺', 'Tượng gốm Thanh Hà', 120), _g('ha_ao_dai', '👘', 'Áo dài may đo', 320))),
    dict(id='phu_quoc', kind='vn', flag='🏝️', name='Phú Quốc', area='Kiên Giang', airport='Phú Quốc', base=300, fly=60, visa='',
         sky='#bfeefa', land='#f2dfa7', accent='#1aa3a3', skyline='🌴🏝️☀️🌊🌴',
         tag='Đảo ngọc: biển xanh, cát trắng, hoàng hôn đỏ.',
         greet='Nắng chói chang, nước biển trong veo. Phú Quốc đón bạn bằng gió nồm mằn mặn.',
         spots=(_s('pq_sao', '🏖️', 'Bãi Sao', 'rest', 0, 4, 'Cát trắng mịn như bột. Bạn nằm võng đọc sách tới lúc ngủ quên.'),
                _s('pq_lan', '🐠', 'Lặn ngắm san hô', 'play', 70, 5, 'Đàn cá vàng sọc đen bơi quanh tay bạn, san hô đỏ rực dưới chân.'),
                _s('pq_cap', '🚠', 'Cáp treo Hòn Thơm', 'photo', 90, 4, 'Cáp treo vượt biển, dưới chân là những chiếc thuyền chài xanh đỏ.'),
                _s('pq_goi', '🐟', 'Gỏi cá trích', 'food', 35, 4, 'Gỏi cá trích cuốn bánh tráng, rau rừng, chấm nước mắm Phú Quốc.'),
                _s('pq_dinh', '🌅', 'Hoàng hôn Dinh Cậu', 'photo', 0, 3, 'Mặt trời lặn đỏ ối sau ngôi miếu nhỏ trên ghềnh đá.')),
         souv=(_g('pq_tieu', '🌶️', 'Tiêu Phú Quốc', 45), _g('pq_mam', '🫙', 'Nước mắm nhĩ', 70), _g('pq_ngoc', '🦪', 'Ngọc trai Phú Quốc', 420))),
    dict(id='ha_long', kind='vn', flag='⛰️', name='Hạ Long', area='Quảng Ninh', airport='Vân Đồn', base=320, fly=120, visa='',
         sky='#cfe9f5', land='#3f8f8a', accent='#2c7a9e', skyline='⛰️⛵⛰️🌊⛰️',
         tag='Nghìn đảo đá giữa vịnh xanh như tranh.',
         greet='Ngoài vịnh, hàng nghìn đảo đá nhô lên như một bức tranh thủy mặc.',
         spots=(_s('hl_tau', '🛳️', 'Du thuyền ra vịnh', 'photo', 50, 4, 'Tàu len giữa hòn Gà Chọi và hòn Đỉnh Hương, ai cũng giơ máy lên chụp.'),
                _s('hl_kayak', '🛶', 'Chèo kayak hang Luồn', 'play', 40, 5, 'Bạn chèo qua vòm đá thấp, mấy chú khỉ con ngó xuống tò mò.'),
                _s('hl_hang', '🪨', 'Hang Sửng Sốt', 'photo', 30, 3, 'Thạch nhũ lấp lánh dưới ánh đèn. Đúng là sửng sốt thật!'),
                _s('hl_muc', '🦑', 'Chả mực Hạ Long', 'food', 60, 4, 'Chả mực giã tay giòn sần sật, chấm tương ớt cay xè.'),
                _s('hl_titop', '🏖️', 'Đảo Ti Tốp', 'rest', 0, 4, 'Leo lên đỉnh ngắm toàn vịnh rồi xuống tắm biển cho mát.')),
         souv=(_g('hl_cha', '🦑', 'Chả mực hút chân không', 90), _g('hl_tranh', '🖼️', 'Tranh than đá', 180), _g('hl_ngoc', '📿', 'Vòng ngọc trai', 350))),
    dict(id='sa_pa', kind='vn', flag='🏔️', name='Sa Pa', area='Lào Cai', airport='Nội Bài', base=340, fly=130, visa='',
         sky='#dfe9f3', land='#7aa35b', accent='#b5463c', skyline='🏔️🌾🏔️🏡☁️',
         tag='Ruộng bậc thang, biển mây và nóc nhà Đông Dương.',
         greet='Từ Nội Bài, xe khách vượt đèo lên Sa Pa. Mây bay ngang qua cửa sổ.',
         spots=(_s('sp_fansi', '🚡', 'Đỉnh Fansipan', 'photo', 80, 5, 'Cáp treo vượt biển mây, bạn đứng trên “nóc nhà Đông Dương”.'),
                _s('sp_ruong', '🌾', 'Ruộng bậc thang Mường Hoa', 'photo', 0, 3, 'Từng tầng ruộng uốn lượn như bậc thang lên trời.'),
                _s('sp_nuong', '🍢', 'Chợ đồ nướng', 'food', 35, 4, 'Xiên nướng, trứng nướng, ly trà gừng ấm bụng giữa trời sương.'),
                _s('sp_ban', '🧵', 'Bản Cát Cát', 'play', 20, 4, 'Bà cụ người H’Mông dạy bạn dệt thổ cẩm. Đường chỉ hơi méo mà vui.'),
                _s('sp_tam', '🌿', 'Tắm lá thuốc người Dao', 'rest', 50, 5, 'Ngâm bồn gỗ lá thuốc thơm lừng, mỏi chân leo núi tan biến.')),
         souv=(_g('sp_tao', '🍎', 'Táo mèo sấy', 50), _g('sp_tui', '👜', 'Túi thổ cẩm', 120), _g('sp_bac', '💍', 'Vòng bạc H’Mông', 300))),
    dict(id='thai_lan', kind='intl', flag='🇹🇭', name='Thái Lan', area='Bangkok', airport='Suvarnabhumi', base=1100, fly=95, visa='',
         sky='#ffd9b3', land='#e0a33a', accent='#d4492a', skyline='🛕🐘🛺🛕🌴',
         tag='Chùa vàng, chợ nổi, tuk-tuk. Không cần visa.',
         greet='“Sawasdee kha!” Bangkok nóng hầm hập, tuk-tuk bóp còi inh ỏi.',
         spots=(_s('th_wat', '🛕', 'Chùa Phật Nằm Wat Pho', 'photo', 40, 4, 'Tượng Phật nằm dát vàng dài 46 mét, phải lùi tận cuối điện mới chụp đủ.'),
                _s('th_cho', '🥭', 'Chợ nổi Damnoen', 'food', 50, 4, 'Bà bán hàng chèo thuyền tới, xúc cho bạn đĩa xôi xoài ngọt lịm.'),
                _s('th_tuk', '🛺', 'Dạo phố bằng tuk-tuk', 'play', 40, 4, 'Chú tài xế lạng lách giữa phố đông, vừa chạy vừa mở nhạc ầm ầm.'),
                _s('th_massage', '💆', 'Massage Thái', 'rest', 80, 5, 'Bà kỹ thuật viên bẻ khớp kêu răng rắc. Đứng dậy nhẹ như bông.'),
                _s('th_dem', '🎡', 'Chợ đêm Asiatique', 'photo', 0, 3, 'Vòng quay khổng lồ bên sông Chao Phraya sáng rực về đêm.')),
         souv=(_g('th_dau', '🌿', 'Dầu gió thảo mộc', 80), _g('th_quan', '🐘', 'Quần voi sặc sỡ', 150), _g('th_lua', '🧣', 'Khăn lụa Thái', 700))),
    dict(id='trung_quoc', kind='intl', flag='🇨🇳', name='Trung Quốc', area='Bắc Kinh', airport='Thủ Đô Bắc Kinh', base=1500, fly=210,
         visa='trung_quoc', sky='#f5d7c6', land='#b8432f', accent='#c8102e', skyline='🏯🧱🏮🐼🏯',
         tag='Trường Thành, Tử Cấm Thành và gấu trúc.',
         greet='“Nǐ hǎo!” Bắc Kinh đón bạn bằng gió heo may và những dãy đèn lồng đỏ.',
         spots=(_s('cn_thanh', '🧱', 'Vạn Lý Trường Thành', 'play', 80, 5, 'Bạn leo tới tháp canh thứ sáu, thở hồng hộc mà cười toe.'),
                _s('cn_cung', '🏯', 'Tử Cấm Thành', 'photo', 60, 4, 'Mái ngói vàng nối nhau tít tắp, chín nghìn gian phòng đi không hết.'),
                _s('cn_vit', '🦆', 'Vịt quay Bắc Kinh', 'food', 90, 4, 'Đầu bếp lạng vịt ngay tại bàn, da giòn tan cuốn bánh mỏng.'),
                _s('cn_panda', '🐼', 'Thăm gấu trúc', 'photo', 50, 5, 'Bé gấu trúc lăn tròn rồi nằm ngửa gặm măng. Cả đoàn reo ầm.'),
                _s('cn_ho', '🏮', 'Hồ Hậu Hải về đêm', 'rest', 0, 3, 'Đèn lồng soi bóng xuống hồ, bạn dạo bộ nghe đàn nhị réo rắt.')),
         souv=(_g('cn_quat', '🪭', 'Quạt giấy vẽ tay', 90), _g('cn_gau', '🐼', 'Gấu trúc bông', 180), _g('cn_tra', '🍵', 'Trà Long Tỉnh', 380))),
    dict(id='han_quoc', kind='intl', flag='🇰🇷', name='Hàn Quốc', area='Seoul', airport='Incheon', base=2200, fly=270, visa='han_quoc',
         sky='#dbe7ff', land='#8aa6c9', accent='#d6336c', skyline='🏯🗼🍁🏙️🏯',
         tag='Hanbok, gà rán, K-pop và lá vàng.',
         greet='“Annyeonghaseyo!” Seoul se lạnh, hàng cây lá vàng rực hai bên đường.',
         spots=(_s('kr_hanbok', '👘', 'Mặc hanbok ở Gyeongbokgung', 'photo', 60, 5, 'Bạn thuê hanbok hồng phấn, vào cung được miễn vé, chụp cả buổi không chán.'),
                _s('kr_ga', '🍗', 'Gà rán & tteokbokki', 'food', 70, 4, 'Gà rán giòn rụm, bánh gạo cay xè, cả bàn hít hà.'),
                _s('kr_namsan', '🗼', 'Tháp Namsan', 'photo', 50, 4, 'Bạn treo một ổ khóa lên lan can, cả Seoul trải dưới chân.'),
                _s('kr_kpop', '💃', 'Học nhảy K-pop', 'play', 60, 5, 'Thầy hô “hana, dul, set!”, bạn nhảy lệch nhịp mà vẫn vui.'),
                _s('kr_jjim', '♨️', 'Xông hơi jjimjilbang', 'rest', 50, 5, 'Quấn khăn tai cừu, ăn trứng nướng, nằm phòng đá muối ấm áp.')),
         souv=(_g('kr_mat_na', '🧴', 'Hộp mặt nạ dưỡng da', 120), _g('kr_lightstick', '🔦', 'Lightstick K-pop', 350), _g('kr_sam', '🌱', 'Hồng sâm Hàn', 800))),
    dict(id='nhat_ban', kind='intl', flag='🇯🇵', name='Nhật Bản', area='Tokyo · Kyoto', airport='Narita', base=3000, fly=330, visa='nhat_ban',
         sky='#ffe4ec', land='#9fb88f', accent='#c0392b', skyline='🗻⛩️🌸🏯🗼',
         tag='Cổng torii, sushi, onsen và núi Phú Sĩ.',
         greet='“Konnichiwa!” Mọi thứ sạch bong, đúng giờ tới từng giây. Núi Phú Sĩ thấp thoáng sau mây.',
         spots=(_s('jp_torii', '⛩️', 'Cổng đỏ Fushimi Inari', 'photo', 0, 4, 'Hàng nghìn cổng torii đỏ nối nhau lên núi, đi mãi không thấy cuối.'),
                _s('jp_sushi', '🍣', 'Sushi băng chuyền', 'food', 90, 4, 'Đĩa sushi chạy vòng vòng, bạn chồng được mười hai đĩa.'),
                _s('jp_tau', '🚄', 'Tàu Shinkansen', 'play', 100, 4, 'Tàu lướt 300 km/h mà ly nước không gợn. Núi Phú Sĩ vụt qua cửa sổ.'),
                _s('jp_onsen', '♨️', 'Tắm onsen', 'rest', 80, 5, 'Ngâm suối khoáng nóng ngoài trời, tuyết rơi lất phất trên đầu.'),
                _s('jp_shibuya', '🚦', 'Ngã tư Shibuya', 'photo', 0, 3, 'Đèn xanh bật, cả nghìn người cùng băng qua mà không ai va ai.')),
         souv=(_g('jp_kitkat', '🍫', 'KitKat trà xanh', 90), _g('jp_meo', '🐱', 'Mèo thần tài', 150), _g('jp_yukata', '👘', 'Yukata', 900))),
    dict(id='uc', kind='intl', flag='🇦🇺', name='Úc', area='Sydney', airport='Kingsford Smith', base=4200, fly=540, visa='uc',
         sky='#bfe6ff', land='#d9a066', accent='#e67e22', skyline='🦘🏙️⛵🌉🏖️',
         tag='Nhà hát Con Sò, kangaroo và biển Bondi.',
         greet='“G’day mate!” Sydney nắng vàng, gió biển lồng lộng, mòng biển đậu đầy bến cảng.',
         spots=(_s('au_opera', '🎶', 'Nhà hát Con Sò', 'photo', 0, 4, 'Mái trắng như những cánh buồm bên cảng. Bạn chụp từ phía cầu Harbour.'),
                _s('au_kangaroo', '🦘', 'Vườn koala & kangaroo', 'play', 90, 5, 'Bạn cho kangaroo ăn, bé koala ôm cây ngủ gật trước ống kính.'),
                _s('au_bondi', '🏄', 'Biển Bondi', 'rest', 0, 4, 'Sóng đẹp, dân lướt sóng đông nghịt. Bạn đứng trên ván được ba giây!'),
                _s('au_pie', '🥧', 'Bánh pie & fish and chips', 'food', 80, 4, 'Bánh pie nóng hổi, cá chiên giòn ăn ngay bên bến cảng.'),
                _s('au_cau', '🌉', 'Cầu cảng Harbour', 'photo', 0, 3, 'Hoàng hôn nhuộm cam cả cây cầu thép khổng lồ.')),
         souv=(_g('au_bum', '🪃', 'Boomerang', 150), _g('au_koala', '🐨', 'Koala bông', 220), _g('au_opal', '💎', 'Đá opal', 1500))),
    dict(id='phap', kind='intl', flag='🇫🇷', name='Pháp', area='Paris', airport='Charles de Gaulle', base=5000, fly=780, visa='chau_au',
         sky='#dfe6f7', land='#b9a37e', accent='#2b4c9b', skyline='🗼🥐🎨🏰🍂',
         tag='Tháp Eiffel, bánh sừng bò và sông Seine.',
         greet='“Bonjour!” Paris mùa thu, lá vàng rụng đầy đại lộ, tiếng accordion văng vẳng.',
         spots=(_s('fr_eiffel', '🗼', 'Tháp Eiffel', 'photo', 80, 5, 'Đúng giờ chẵn, tháp nhấp nháy ánh đèn. Cả quảng trường ồ lên.'),
                _s('fr_banh', '🥐', 'Tiệm bánh sừng bò', 'food', 50, 4, 'Bánh sừng bò vừa ra lò, bơ thơm lừng, ăn kèm ly cà phê sữa.'),
                _s('fr_louvre', '🖼️', 'Bảo tàng Louvre', 'photo', 90, 4, 'Nàng Mona Lisa nhỏ hơn bạn tưởng, nhưng nụ cười thì đúng là bí ẩn.'),
                _s('fr_seine', '🛥️', 'Du thuyền sông Seine', 'rest', 70, 4, 'Thuyền trôi chầm chậm dưới những cây cầu đá cổ, gió thu mát rượi.'),
                _s('fr_ve', '🎨', 'Vẽ chân dung ở Montmartre', 'play', 60, 5, 'Ông họa sĩ râu bạc vẽ bạn trong mười phút, giống tới bảy phần.')),
         souv=(_g('fr_thap', '🗼', 'Mô hình tháp Eiffel', 120), _g('fr_macaron', '🍬', 'Hộp macaron', 200), _g('fr_nuoc_hoa', '🌸', 'Nước hoa Paris', 1200))),
    dict(id='my', kind='intl', flag='🇺🇸', name='Mỹ', area='New York', airport='JFK', base=5500, fly=1020, visa='my',
         sky='#cfe3ff', land='#8d99ae', accent='#1d4ed8', skyline='🗽🏙️🚕🌉🏙️',
         tag='Tượng Nữ thần, Times Square và Central Park.',
         greet='“Welcome to New York!” Taxi vàng nối đuôi nhau, nhà chọc trời cao ngất ngưởng.',
         spots=(_s('us_tuong', '🗽', 'Tượng Nữ thần Tự do', 'photo', 70, 5, 'Phà chạy vòng quanh đảo, bức tượng xanh đồng hiện ra sừng sững.'),
                _s('us_times', '🌃', 'Quảng trường Thời Đại', 'photo', 0, 4, 'Nửa đêm mà màn hình quảng cáo sáng như ban ngày.'),
                _s('us_pizza', '🍕', 'Pizza New York', 'food', 50, 4, 'Miếng pizza to bằng mặt, gập đôi lại ăn kiểu dân New York.'),
                _s('us_park', '🚲', 'Đạp xe Central Park', 'play', 60, 4, 'Bạn đạp xe giữa rừng lá đỏ, sóc nhỏ chạy ngang đường.'),
                _s('us_broadway', '🎭', 'Nhạc kịch Broadway', 'rest', 150, 5, 'Nốt cao cuối cùng vang lên, cả nhà hát đứng dậy vỗ tay.')),
         souv=(_g('us_mu', '🧢', 'Mũ I ♥ NY', 120), _g('us_taxi', '🚕', 'Mô hình taxi vàng', 180), _g('us_ao', '🧥', 'Áo khoác bóng chày', 900))),
)

# What each spot kind looks like on the itinerary (the client's mini scene is picked by kind).
KINDS = dict(photo=dict(emoji='📸', verb='Chụp ảnh'), food=dict(emoji='🍽️', verb='Ăn thử'),
             play=dict(emoji='🎯', verb='Chơi'), rest=dict(emoji='🌿', verb='Thư giãn'))
