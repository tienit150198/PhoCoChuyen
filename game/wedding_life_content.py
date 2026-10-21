"""💍 Đời sống vợ chồng: the catalogue of game/wedding_life.py (pure data; docs/WEDDING_LIFE_PLAN.md).

Player feedback #442 (lễ rước dâu, lễ gia tiên before the town party) and #444 (life after the wedding: chores, trips,
the child, together); owner 21/10 "có đi thật luôn nhé, có chụp ảnh này kia luôn, thuê máy bay du thuyền gì đó".
Light flavour only, warm and short. Prices are the base (pre-07/10) ones; game/wedding_life.py indexes them
(game/price_index.py). Ids are stored in the wl_* tables: never rename or remove one.

Photo choices (bd, light, pose, face, prop) are game/photo_studio.py ids (public/js/v4/portrait-art.js draws them);
tests/test_wedding_life.py checks every one.
"""


def _o(oid, text, pts, reply):
    return dict(id=oid, text=text, pts=pts, reply=reply)


# ---------------------------------------------------------------- 🧺 lễ rước dâu + lễ gia tiên
# Six steps, alternating: 'lead' is the side that starts (họ đi rước), 'host' the other (họ đón). {a}: the lead's name,
# {b}: the host's. Every option is fine (no losing): 2 points for the most fitting one, 1 for the others.
RITE_STEPS = (
    dict(id='le_vat', side='lead', emoji='🧺', title='Sửa soạn mâm quả', who='Bà nội họ nhà {a}',
         line='Mâm quả phải có trầu cau đi đầu đó con. Con xếp thêm món gì?', options=(
        _o('trau_cau', 'Trầu cau, rượu, chè, bánh phu thê', 2, 'Đủ lễ, đẹp lắm. Trầu cau là đầu câu chuyện.'),
        _o('xoi_gac', 'Trầu cau, xôi gấc, lợn quay, hoa quả', 2, 'Xôi gấc đỏ au, lợn quay vàng ruộm, sang ghê!'),
        _o('banh_keo', 'Bánh kẹo, nước ngọt cho tiện', 1, 'Thôi được, nhưng bà thêm buồng cau vào cho đủ lễ nha.'),
    )),
    dict(id='xin_dau', side='lead', emoji='🚪', title='Tới nhà xin phép rước dâu', who='Ông chủ hôn họ nhà {a}',
         line='Tới cổng nhà {b} rồi. Con thưa chuyện với hai họ thế nào?', options=(
        _o('thua', '“Thưa hai bác, nhà con xin phép được đón {b} về làm dâu, làm rể.”', 2, 'Lời lẽ đâu ra đó, hai họ gật gù.'),
        _o('cuoi', '“Con tới đón người thương, cả nhà cho con xin nhé!”', 1, 'Cả họ cười rộ, không khí vui hẳn lên.'),
        _o('hat', 'Hát một câu quan họ thay lời chào', 1, 'Giọng hơi run mà đáng yêu, bà ngoại vỗ tay.'),
    )),
    dict(id='nhan_le', side='host', emoji='🍵', title='Nhà đón nhận lễ', who='Mẹ của {b}',
         line='Họ nhà {a} sang rồi kìa con. Mình đón khách thế nào?', options=(
        _o('moi_tra', 'Mời trà, mời trầu, mở mâm quả ra trình lễ', 2, 'Hai họ ngồi lại, chén trà nóng, câu chuyện ấm.'),
        _o('thach', 'Đùa “thách cưới” một trăm thúng xôi cho vui', 1, 'Ai cũng bật cười, họ nhà {a} xin khất xôi tới Tết.'),
        _o('om', 'Chạy ra ôm người thương trước cả nhà', 1, 'Cô dì xúm lại trêu, mặt hai đứa đỏ như gấc.'),
    )),
    dict(id='gia_tien', side='host', emoji='🕯️', title='Thắp hương bàn thờ gia tiên', who='Ông của {b}',
         line='Hai con đứng trước bàn thờ, thưa với ông bà tổ tiên đi.', options=(
        _o('khan', 'Thắp ba nén hương, cùng vái và khấn xin phép', 2, 'Khói hương thơm, ông bà như mỉm cười.'),
        _o('lang', 'Đứng lặng một lúc, cúi đầu cảm ơn ông bà', 2, 'Không cần nhiều lời, ai cũng thấy hai đứa thật lòng.'),
        _o('quen', 'Lỡ quên mang bật lửa, phải mượn ông', 1, 'Ông cười hiền: “Lần sau nhớ nha con.”'),
    )),
    dict(id='trao', side='lead', emoji='💍', title='Trao quà, cha mẹ dặn dò', who='Bố mẹ hai bên',
         line='Cha mẹ trao quà cưới và dặn đôi lời. Con đáp lại thế nào?', options=(
        _o('cam_on', 'Cúi đầu cảm ơn, hứa thương nhau tới già', 2, 'Mẹ rơm rớm nước mắt, bố vỗ vai thật chặt.'),
        _o('hua', '“Con hứa nấu cơm tối, rửa bát trưa!”', 1, 'Cả nhà cười, ghi sổ lời hứa luôn.'),
        _o('nhan', 'Trao nhẫn cho nhau trước mặt hai họ', 2, 'Tiếng vỗ tay vang khắp sân.'),
    )),
    dict(id='ruoc', side='host', emoji='🚗', title='Đón dâu về nhà', who='Bà mối',
         line='Giờ đẹp tới rồi! Mình lên đường về nhà mới thế nào đây?', options=(
        _o('o_do', 'Che ô đỏ, bước qua chậu than đỏ lửa', 2, 'Đúng lệ xưa, may mắn theo về.'),
        _o('xe_hoa', 'Lên xe hoa, vẫy tay chào cả xóm', 1, 'Trẻ con chạy theo xin kẹo cả con đường.'),
        _o('di_bo', 'Nắm tay đi bộ về, vừa đi vừa trò chuyện', 2, 'Con đường ngắn mà vui như cả đời.'),
    )),
)
RITE_GRADES = ((11, '🌟 Lễ trọn vẹn, hai họ hài lòng'), (9, '💛 Lễ ấm cúng, ai cũng vui'), (0, '😄 Lễ vui nhộn, nhớ mãi'))
RITE_TRAYS = (5, 7, 9)            # lễ vật: mâm quả (the an_hoi options of game/wedding_content.py)
# live/wedding.py (the MC tells the guests at the party): a couple's latest finished ceremony, and its short form.
RITE_SQL = "SELECT lead, trays, score FROM wl_rites WHERE couple=? AND status='done' ORDER BY id DESC LIMIT 1"


def rite_brief(row, a_sid: str) -> dict:
    """{lead: 'a' | 'b' (the side that went to fetch), trays, full: the most fitting choice at every step}."""
    return dict(lead='a' if row['lead'] == a_sid else 'b', trays=int(row['trays']), full=int(row['score']) >= RITE_GRADES[0][0])

# ---------------------------------------------------------------- ✈️ đi chơi cùng nhau
# base: two tickets and the stay (pre-07/10 xu). sea: a yacht can go. abroad: a plane (not a helicopter) for a private
# ride. bd: game/photo_studio.py backdrops used by the day photos.
DESTS = (
    dict(id='da_lat', emoji='🌲', name='Đà Lạt', kind='vn', sea=False, days=3, base=300),
    dict(id='hoi_an', emoji='🏮', name='Hội An', kind='vn', sea=False, days=3, base=300),
    dict(id='sa_pa', emoji='⛰️', name='Sa Pa', kind='vn', sea=False, days=3, base=350),
    dict(id='ha_long', emoji='⛵', name='Vịnh Hạ Long', kind='vn', sea=True, days=3, base=350),
    dict(id='nha_trang', emoji='🏖️', name='Nha Trang', kind='vn', sea=True, days=3, base=400),
    dict(id='phu_quoc', emoji='🌴', name='Phú Quốc', kind='vn', sea=True, days=3, base=450),
    dict(id='han_quoc', emoji='🇰🇷', name='Seoul, Hàn Quốc', kind='abroad', sea=False, days=4, base=1200),
    dict(id='nhat_ban', emoji='🇯🇵', name='Osaka, Nhật Bản', kind='abroad', sea=False, days=4, base=1400),
    dict(id='phap', emoji='🇫🇷', name='Lyon, Pháp', kind='abroad', sea=False, days=4, base=2000),
    dict(id='uc', emoji='🇦🇺', name='Melbourne, Úc', kind='abroad', sea=False, days=4, base=2000),
    dict(id='dao_rieng', emoji='🏝️', name='Đảo riêng nhà mình', kind='island', sea=True, days=3, base=50),
)
# (id, emoji, name): how the couple goes. 've' is the ticket (the island's own boat on a private island).
RIDES = (
    ('ve', '🎫', 'Vé thường'),
    ('thue_bay', '🛩️', 'Thuê máy bay riêng'),
    ('thue_thuyen', '🛥️', 'Thuê du thuyền'),
    ('nha', '🔑', 'Phương tiện nhà mình'),
)
RENT = {'thue_bay': dict(vn=6000, abroad=15000, island=6000), 'thue_thuyen': dict(vn=4000, island=4000)}
FUEL_DIV = 10                     # 🔑 a plane / yacht the couple owns: fuel = the rent ÷ 10

# The activities of a destination: (id, emoji, text, bd, light, pose, face, prop). Each trip day offers three of them.
_SIGHT = {
    'da_lat': (
        ('cho_dem', '🌙', 'Dạo chợ đêm, ăn bánh tráng nướng', 'pho_den', 'vang', 'khoac_vai', 'cuoi_tit', 'none'),
        ('vuon_hoa', '💐', 'Lạc trong vườn hoa cẩm tú cầu', 'cho_hoa', 'tu_nhien', 'tim_to', 'cuoi_hip', 'hoa'),
        ('ho', '🛶', 'Đạp vịt trên hồ, gió se lạnh', 'ho_sen', 'tu_nhien', 'tua_vai', 'lap_lanh', 'none'),
        ('doi_thong', '🌲', 'Đi bộ qua đồi thông lúc sương sớm', 'cau', 'vang', 'nam_tay', 'auto', 'none'),
        ('ca_phe', '☕', 'Ngồi quán cà phê nhìn thung lũng', 'kem', 'mem', 'chum_dau', 'mat_tim', 'none'),
        ('dau', '🍓', 'Hái dâu tây ở vườn nhà dân', 'cho_hoa', 'tu_nhien', 'cung_nhay', 'cuoi_tit', 'none'),
    ),
    'hoi_an': (
        ('den_long', '🏮', 'Thả đèn hoa đăng trên sông Hoài', 'pho_den', 'vang', 'om_nhau', 'mat_tim', 'long_den'),
        ('ao_dai', '👘', 'Mặc áo dài dạo phố cổ', 'pho_den', 'tu_nhien', 'nam_tay', 'cuoi_hip', 'non_la'),
        ('cao_lau', '🍜', 'Ăn cao lầu, uống nước mót', 'kem', 'mem', 'chum_dau', 'cuoi_tit', 'none'),
        ('xe_dap', '🚲', 'Đạp xe ra làng rau Trà Quế', 'ho_sen', 'tu_nhien', 'cung_nhay', 'lap_lanh', 'non_la'),
        ('may_do', '🧵', 'May đo đôi áo giống nhau', 'hong', 'mem', 'tua_vai', 'cuoi_hip', 'none'),
        ('cau', '🌉', 'Ngắm hoàng hôn ở Chùa Cầu', 'cau', 'vang', 'khoac_vai', 'do_mat', 'none'),
    ),
    'sa_pa': (
        ('ruong', '🌾', 'Ngắm ruộng bậc thang mùa lúa chín', 'cau', 'vang', 'nam_tay', 'lap_lanh', 'none'),
        ('may', '☁️', 'Săn mây trên đỉnh núi', 'xanh', 'tu_nhien', 'tim_to', 'cuoi_hip', 'none'),
        ('cho_phien', '🧣', 'Đi chợ phiên, mua khăn thổ cẩm', 'pho_den', 'tu_nhien', 'khoac_vai', 'cuoi_tit', 'none'),
        ('lau', '🍲', 'Ăn lẩu cá hồi bên bếp lửa', 'kem', 'mem', 'chum_dau', 'mat_tim', 'none'),
        ('ban', '🏡', 'Ngủ homestay bản làng', 'giay', 'mem', 'tua_vai', 'auto', 'none'),
        ('thac', '💦', 'Leo tới thác Bạc', 'ho_sen', 'tu_nhien', 'cung_nhay', 'cuoi_hip', 'none'),
    ),
    'ha_long': (
        ('kayak', '🛶', 'Chèo kayak qua hang đá', 'dao', 'tu_nhien', 'cung_nhay', 'cuoi_tit', 'kinh_ram'),
        ('hoang_hon', '🌅', 'Ngắm hoàng hôn trên boong', 'cau', 'vang', 'om_nhau', 'mat_tim', 'none'),
        ('hang', '🪨', 'Thăm hang Sửng Sốt', 'den', 'ven', 'nam_tay', 'lap_lanh', 'none'),
        ('hai_san', '🦐', 'Ăn hải sản ở làng chài', 'kem', 'mem', 'chum_dau', 'cuoi_tit', 'none'),
        ('tam', '🏊', 'Tắm biển ở bãi Ti Tốp', 'dao', 'tu_nhien', 'tim_to', 'cuoi_hip', 'kinh_ram'),
        ('dem', '🌌', 'Câu mực đêm trên vịnh', 'den', 'kich', 'tua_vai', 'auto', 'none'),
    ),
    'nha_trang': (
        ('bien', '🏖️', 'Nằm dài trên bãi biển', 'dao', 'tu_nhien', 'tua_vai', 'cuoi_hip', 'kinh_ram'),
        ('lan', '🐠', 'Lặn ngắm san hô', 'xanh', 'tu_nhien', 'cung_nhay', 'lap_lanh', 'none'),
        ('bun', '♨️', 'Tắm bùn khoáng nóng', 'kem', 'mem', 'chum_dau', 'cuoi_tit', 'none'),
        ('thap', '🛕', 'Thăm tháp Bà Ponagar', 'chua', 'vang', 'nam_tay', 'auto', 'non_la'),
        ('dao_khi', '🐒', 'Ra đảo Khỉ chơi', 'dao', 'tu_nhien', 'khoac_vai', 'le_luoi', 'none'),
        ('cho_dem', '🌙', 'Dạo chợ đêm ven biển', 'pho_den', 'vang', 'om_nhau', 'mat_tim', 'long_den'),
    ),
    'phu_quoc': (
        ('hoang_hon', '🌅', 'Ngắm hoàng hôn Sunset Town', 'cau', 'vang', 'om_nhau', 'mat_tim', 'none'),
        ('cap_treo', '🚡', 'Đi cáp treo vượt biển', 'xanh', 'tu_nhien', 'tim_to', 'lap_lanh', 'none'),
        ('bai_sao', '🏝️', 'Tắm biển Bãi Sao cát trắng', 'dao', 'tu_nhien', 'cung_nhay', 'cuoi_hip', 'kinh_ram'),
        ('nuoc_mam', '🐟', 'Tham quan nhà thùng nước mắm', 'giay', 'mem', 'nam_tay', 'cuoi_tit', 'none'),
        ('cau_ca', '🎣', 'Câu cá, lặn ngắm san hô', 'dao', 'tu_nhien', 'tua_vai', 'auto', 'non_la'),
        ('cho_dem', '🍢', 'Ăn hải sản chợ đêm', 'pho_den', 'vang', 'chum_dau', 'cuoi_tit', 'none'),
    ),
    'han_quoc': (
        ('hanbok', '👘', 'Mặc hanbok dạo cung điện', 'chua', 'tu_nhien', 'nam_tay', 'cuoi_hip', 'none'),
        ('thap', '🗼', 'Treo khóa tình yêu trên tháp Namsan', 'pho_den', 'vang', 'tim_to', 'mat_tim', 'none'),
        ('ga_ran', '🍗', 'Ăn gà rán uống nước ngọt bên sông Hàn', 'cau', 'vang', 'chum_dau', 'cuoi_tit', 'none'),
        ('cho', '🛍️', 'Mua sắm ở phố Myeongdong', 'pho_den', 'mem', 'khoac_vai', 'lap_lanh', 'kinh_ram'),
        ('busan', '🌊', 'Đi tàu xuống biển Busan', 'dao', 'tu_nhien', 'cung_nhay', 'cuoi_hip', 'none'),
        ('kara', '🎤', 'Hát karaoke đôi tới khuya', 'den', 'kich', 'om_nhau', 'le_luoi', 'none'),
    ),
    'nhat_ban': (
        ('den', '⛩️', 'Đi qua ngàn cổng đỏ', 'chua', 'vang', 'nam_tay', 'auto', 'none'),
        ('takoyaki', '🐙', 'Ăn takoyaki ở phố Dotonbori', 'pho_den', 'vang', 'chum_dau', 'cuoi_tit', 'none'),
        ('kimono', '🎎', 'Mặc kimono đi dạo phố cổ', 'chua', 'tu_nhien', 'tua_vai', 'cuoi_hip', 'none'),
        ('onsen', '♨️', 'Tắm suối nước nóng onsen', 'kem', 'mem', 'chum_dau', 'mat_tim', 'none'),
        ('nai', '🦌', 'Cho nai ăn bánh ở Nara', 'ho_sen', 'tu_nhien', 'cung_nhay', 'le_luoi', 'none'),
        ('anh_dao', '🌸', 'Ngồi dưới hàng cây hoa anh đào', 'hong', 'tu_nhien', 'om_nhau', 'mat_tim', 'hoa'),
    ),
    'phap': (
        ('banh_mi', '🥐', 'Ăn bánh sừng bò ở tiệm sáng sớm', 'kem', 'mem', 'chum_dau', 'cuoi_tit', 'none'),
        ('song', '🌉', 'Dạo bờ sông lúc lên đèn', 'cau', 'vang', 'om_nhau', 'mat_tim', 'none'),
        ('cho', '🧀', 'Đi chợ phiên mua phô mai', 'cho_hoa', 'tu_nhien', 'khoac_vai', 'cuoi_hip', 'none'),
        ('nha_tho', '⛪', 'Leo đồi ngắm toàn thành phố', 'chua', 'vang', 'nam_tay', 'lap_lanh', 'none'),
        ('picnic', '🧺', 'Picnic trong công viên', 'ho_sen', 'tu_nhien', 'tua_vai', 'cuoi_hip', 'hoa'),
        ('le_hoi', '🕯️', 'Xem lễ hội ánh sáng', 'den', 'ven', 'tim_to', 'mat_tim', 'none'),
    ),
    'uc': (
        ('bien', '🏄', 'Học lướt sóng ở bãi biển', 'dao', 'tu_nhien', 'cung_nhay', 'cuoi_tit', 'kinh_ram'),
        ('chim', '🐧', 'Ngắm chim cánh cụt về tổ', 'dao', 'vang', 'om_nhau', 'mat_tim', 'none'),
        ('ca_phe', '☕', 'Uống cà phê trong hẻm tranh tường', 'giay', 'mem', 'chum_dau', 'cuoi_hip', 'none'),
        ('kangaroo', '🦘', 'Gặp kangaroo ở công viên', 'ho_sen', 'tu_nhien', 'khoac_vai', 'le_luoi', 'none'),
        ('duong', '🚗', 'Chạy xe dọc đường ven biển', 'cau', 'vang', 'tua_vai', 'lap_lanh', 'kinh_ram'),
        ('cho', '🍓', 'Đi chợ trời mua trái cây', 'cho_hoa', 'tu_nhien', 'nam_tay', 'cuoi_tit', 'none'),
    ),
    'dao_rieng': (
        ('bbq', '🍖', 'Nướng BBQ trên bãi cát nhà mình', 'dao', 'vang', 'chum_dau', 'cuoi_tit', 'none'),
        ('vong', '🌴', 'Nằm võng dưới hàng dừa', 'dao', 'tu_nhien', 'tua_vai', 'cuoi_hip', 'kinh_ram'),
        ('lan', '🐠', 'Lặn ngắm cá quanh đảo', 'xanh', 'tu_nhien', 'cung_nhay', 'lap_lanh', 'none'),
        ('sao', '✨', 'Đếm sao trên cầu tàu', 'den', 'ven', 'om_nhau', 'mat_tim', 'none'),
        ('cau', '🎣', 'Câu cá ở mũi đảo', 'cau', 'vang', 'khoac_vai', 'auto', 'non_la'),
        ('dao', '🐚', 'Nhặt vỏ sò lúc thủy triều xuống', 'dao', 'tu_nhien', 'tim_to', 'cuoi_tit', 'none'),
    ),
}
ACTIVITIES = {k: tuple(dict(id=a[0], emoji=a[1], text=a[2], bd=a[3], light=a[4], pose=a[5], face=a[6], prop=a[7]) for a in v)
              for k, v in _SIGHT.items()}

# A small surprise each day (seeded by the trip and the day). {a}, {b}: the two names.
EVENTS = (
    '🌧️ Mưa bất chợt, hai bạn chung một chiếc áo mưa, cười suốt đường về.',
    '🗺️ Lạc đường một chút, rồi tình cờ tìm ra quán ăn ngon nhất chuyến.',
    '👵 Một cô bán hàng khen hai bạn đẹp đôi, tặng thêm phần ăn.',
    '📷 Một du khách xin chụp giùm, tấm ảnh đẹp không ngờ.',
    '🌈 Cầu vồng hiện ra đúng lúc hai bạn nắm tay.',
    '🧳 {a} quên kem chống nắng, {b} đã lén mang theo sẵn.',
    '🎶 Nhạc đường phố vang lên, hai bạn nhảy một điệu giữa phố.',
    '🍦 Ăn chung một cây kem, tranh nhau miếng cuối.',
    '😴 Ngủ quên một chút, dậy muộn mà vẫn kịp ngắm bình minh.',
    '💌 {b} viết một tấm bưu thiếp gửi về phố cho {a}.',
)
RIDE_LINES = {
    've': '🎫 Hai bạn xách vali ra bến, ngồi cạnh nhau suốt chặng đường.',
    'island': '🚤 Xuồng của đảo đón hai bạn ở bến, sóng êm, nắng đẹp.',
    'thue_bay': '🛩️ Máy bay riêng chờ sẵn ở đường băng, phi công mời hai bạn ngắm mây từ buồng lái.',
    'thue_thuyen': '🛥️ Du thuyền rời bến, thủy thủ đoàn mở nhạc, gió biển mát rượi.',
    'nha_plane': '🔑 Lên máy bay nhà mình, cất cánh khi nào mình muốn.',
    'nha_boat': '🔑 Du thuyền nhà mình nhổ neo, hai bạn tự cầm lái một đoạn.',
}

# ---------------------------------------------------------------- 🏠 sống chung mỗi ngày
# kind: (emoji, name, the starter's line, roles {id: (text, the line in the diary)}). 'cham_con' needs a shared child.
CHORES = {
    'viec_nha': dict(emoji='🧹', name='Việc nhà cùng nhau', ask='Mình dọn nhà cùng nhau nha?', roles=(
        ('rua_bat', 'Rửa bát'), ('lau_nha', 'Lau nhà'), ('giat_do', 'Giặt phơi đồ'), ('tuoi_cay', 'Tưới cây'))),
    'di_cho': dict(emoji='🧺', name='Đi chợ', ask='Đi chợ với mình không?', roles=(
        ('xach', 'Xách giỏ'), ('mac_ca', 'Mặc cả'), ('chon_rau', 'Chọn rau'), ('chon_ca', 'Chọn cá thịt'))),
    'nau_an': dict(emoji='🍳', name='Nấu cơm chung', ask='Tối nay mình nấu cơm chung nha?', roles=(
        ('nau', 'Đứng bếp'), ('so_che', 'Sơ chế'), ('don_mam', 'Dọn mâm'), ('nem', 'Nếm thử'))),
    'cham_con': dict(emoji='👶', name='Chăm con', ask='Mình cùng chăm bé nha?', roles=(
        ('tam', 'Tắm cho bé'), ('ru', 'Ru bé ngủ'), ('cho_an', 'Cho bé ăn'), ('choi', 'Chơi với bé'))),
}
CHORE_DONE = ('{a} {ra}, {b} {rb}. Nhà mình vui hẳn! 🏡', '{a} {ra}, {b} {rb}. Xong việc còn kịp ôm nhau một cái 🤗',
              '{a} {ra}, {b} {rb}. Phối hợp ăn ý ghê 💞')
