"""Giúp việc theo giờ: content (people, homes, surfaces, tools, surprises, situations).

Rules live in game/careers/giupviec.py. Everything here is fixed content; the jobs are rolled from it
by day and slot. Words are what the player reads: no developer words, one short line per thing.
"""
from __future__ import annotations

# ---------------------------------------------------------------- the people
# (name, role, note, persona). Index 0 is cô Mai, who runs the team and gives the morning.
PEOPLE = [
    ('Cô Mai', 'Tổ trưởng tổ giúp việc Nhà Thơm', 'Hai mươi năm dọn nhà theo giờ, vuốt ngón tay lên nóc tủ là biết người dọn có kỹ không.', 'warm'),
    ('Anh Tùng', 'Lập trình viên làm việc ở nhà', 'Căn studio tầng mười hai, bàn làm việc ba màn hình, ghét nhất ai đụng vào giấy tờ.', 'quiet'),
    ('Chị Hà', 'Chủ của mèo Mướp', 'Căn hộ hai phòng ngủ, mèo Mướp rụng lông khắp sofa và sợ tiếng máy hút bụi.', 'genz'),
    ('Bà Xuân', 'Hưu trí, sống một mình', 'Nhà ống trong ngõ, có gian thờ, tủ kính bình gốm của ông, hay để quên nhẫn trên lavabo.', 'warm'),
    ('Chị Quyên', 'Mẹ của bé Bin hai tuổi', 'Bé Bin bò khắp nhà, mút tay: sàn chỉ lau nước sạch, hóa chất phải cất cao.', 'bossy'),
    ('Anh Khải', 'Chủ căn hộ cho thuê theo ngày', 'Khách trả phòng mười hai giờ, khách mới tới hai giờ: dọn nhanh mà phải sạch bong.', 'sour'),
    ('Cô Diệu', 'Cô giáo về hưu', 'Đeo găng tay trắng vuốt nóc tủ để kiểm, ít khen, mà khen là khen thật.', 'picky'),
]

# ---------------------------------------------------------------- the cleaning cart
TOOLS = {
    'phat_tran': dict(name='Chổi phất trần', short='Phất trần', emoji='🪶', verb='Phủi'),
    'hut_bui': dict(name='Máy hút bụi', short='Hút bụi', emoji='🌀', verb='Hút'),
    'choi': dict(name='Chổi quét nhà', short='Chổi', emoji='🧹', verb='Quét'),
    'khan_xanh': dict(name='Khăn xanh', short='Khăn xanh', emoji='🟦', note='kính, gương', verb='Lau'),
    'khan_vang': dict(name='Khăn vàng', short='Khăn vàng', emoji='🟨', note='bàn, kệ, bếp', verb='Lau'),
    'khan_do': dict(name='Khăn đỏ', short='Khăn đỏ', emoji='🟥', note='chỉ bồn cầu', verb='Lau'),
    'ban_chai': dict(name='Bàn chải cọ', short='Bàn chải', emoji='🪥', verb='Cọ'),
    'cay_lau': dict(name='Cây lau nhà', short='Cây lau', emoji='🪣', verb='Lau'),
}
# item: the bottle in the cart (None: nothing to use up)
PRODUCTS = {
    'kho': dict(name='Lau khô', short='Khô', emoji='💨', item=None),
    'nuoc': dict(name='Nước sạch', short='Nước sạch', emoji='💧', item=None),
    'kinh': dict(name='Nước lau kính', short='Lau kính', emoji='🫧', item='chai_kinh'),
    'da_nang': dict(name='Nước tẩy rửa dịu', short='Tẩy dịu', emoji='🧴', item='chai_da_nang'),
    'dau_mo': dict(name='Tẩy dầu mỡ', short='Tẩy dầu', emoji='🍋', item='chai_dau_mo'),
    'toilet': dict(name='Tẩy bồn cầu', short='Tẩy bồn cầu', emoji='🧪', item='chai_toilet'),
    'lau_san': dict(name='Nước lau sàn', short='Lau sàn', emoji='🌸', item='chai_lau_san'),
}
BOTTLES = tuple(k for k, v in PRODUCTS.items() if v['item'])
WET = ('nuoc', 'kinh', 'da_nang', 'dau_mo', 'toilet', 'lau_san')
HARSH = ('dau_mo', 'toilet')
LEVELS = {0: 'Trên cao', 1: 'Bàn, kệ, đồ đạc', 2: 'Sàn: quét, hút', 3: 'Sàn: lau ướt'}


def _harm(*pairs):
    """{tool or product: (sev, what the client says, short note)}."""
    return {k: v for k, v in pairs}


WOOD = _harm(('dau_mo', (2, 'Tẩy dầu mỡ lên mặt gỗ: bạc trắng một mảng.', 'mặt gỗ bạc màu')),
             ('toilet', (2, 'Đổ tẩy bồn cầu lên đồ gỗ, gỗ loang lổ hết rồi.', 'mặt gỗ loang lổ')))
SCREEN = _harm(*[(p, (2, 'Xịt nước lên máy tính, bàn phím chập chờn cả buổi.', 'xịt nước lên máy tính')) for p in WET])
ALTAR = _harm(*[(p, (2, 'Lau bàn thờ bằng nước tẩy, mùi hóa chất bay khắp gian thờ.', 'lau bàn thờ bằng hóa chất')) for p in WET if p != 'nuoc'])
FABRIC = _harm(*[(p, (1, 'Sofa vải ướt loang một vệt, mấy hôm mới khô.', 'đồ vải bị ướt')) for p in WET])
GLASSTOP = _harm(('toilet', (2, 'Tẩy bồn cầu làm mờ mặt kính, nhìn như có sương.', 'mặt kính bị mờ')))
INDUCTION = _harm(('ban_chai', (1, 'Cọ bàn chải lên mặt bếp kính, xước mấy đường.', 'mặt bếp bị xước')))


def S(name, emoji, lvl, mat, tools, products, harm=None):
    return dict(name=name, emoji=emoji, lvl=lvl, mat=mat, tools=tuple(tools), products=tuple(products), harm=dict(harm or {}))


# Every surface of every home: what it is, how high, what it is made of, the right tool(s) and product(s).
SPOTS = {
    # trên cao
    'quat_tran': S('Quạt trần', '🪭', 0, 'bụi bám cánh', ['phat_tran'], ['kho']),
    'noc_tu': S('Nóc tủ', '🗄️', 0, 'bụi dày', ['phat_tran'], ['kho']),
    'hut_mui': S('Máy hút mùi', '♨️', 0, 'dầu mỡ', ['khan_vang'], ['dau_mo']),
    'den_tran': S('Đèn trần', '💡', 0, 'bụi, xác muỗi', ['phat_tran'], ['kho']),
    # bàn, kệ, đồ đạc
    'ban_tra': S('Bàn trà kính', '🫖', 1, 'kính, vết tay', ['khan_xanh'], ['kinh'], GLASSTOP),
    'ke_tivi': S('Kệ ti vi gỗ', '📺', 1, 'gỗ, bụi', ['khan_vang'], ['da_nang', 'kho'], WOOD),
    'ban_an': S('Bàn ăn gỗ', '🍽️', 1, 'gỗ, vụn cơm', ['khan_vang'], ['da_nang'], WOOD),
    'ban_lam_viec': S('Bàn làm việc', '💻', 1, 'máy tính, giấy tờ', ['khan_vang'], ['kho'], SCREEN),
    'ban_tho': S('Bàn thờ', '🪔', 1, 'gỗ, tàn nhang', ['khan_vang'], ['kho'], dict(WOOD, **ALTAR)),
    'tu_kinh': S('Tủ kính', '🏺', 1, 'kính, bụi', ['khan_xanh'], ['kinh'], GLASSTOP),
    'guong': S('Gương', '🪞', 1, 'kính, vệt nước', ['khan_xanh'], ['kinh'], GLASSTOP),
    'cua_kinh': S('Cửa kính ban công', '🪟', 1, 'kính, vết tay', ['khan_xanh'], ['kinh'], GLASSTOP),
    'mat_bep': S('Mặt bếp', '🍳', 1, 'dầu mỡ', ['khan_vang'], ['dau_mo'], INDUCTION),
    'bon_rua': S('Bồn rửa chén', '🚰', 1, 'inox, cặn', ['khan_vang'], ['da_nang']),
    'tu_lanh': S('Cửa tủ lạnh', '🧊', 1, 'vết tay', ['khan_vang'], ['da_nang']),
    'lavabo': S('Lavabo', '🫧', 1, 'sứ, cặn xà phòng', ['ban_chai'], ['da_nang']),
    'bon_cau': S('Bồn cầu', '🚽', 1, 'sứ, ố vàng', ['khan_do', 'ban_chai'], ['toilet']),
    'sofa': S('Sofa vải', '🛋️', 1, 'vải, lông, bụi', ['hut_bui'], ['kho'], FABRIC),
    'nem': S('Nệm giường', '🛏️', 1, 'vải, bụi', ['hut_bui'], ['kho'], FABRIC),
    # sàn
    'san_quet': S('Bụi tóc trên sàn', '🧹', 2, 'bụi, tóc', ['choi', 'hut_bui'], ['kho']),
    'tham': S('Thảm', '🟫', 2, 'bụi, lông', ['hut_bui'], ['kho'], FABRIC),
    'san_lau': S('Sàn gạch', '✨', 3, 'gạch men', ['cay_lau'], ['lau_san', 'nuoc']),
    'san_go': S('Sàn gỗ', '🪵', 3, 'gỗ, vắt kiệt', ['cay_lau'], ['nuoc', 'lau_san'], WOOD),
    'san_tam': S('Sàn nhà tắm', '🚿', 3, 'gạch, cặn', ['ban_chai', 'cay_lau'], ['da_nang']),
}
FLOOR_WET = ('san_lau', 'san_go')     # a 'gentle' home (cat, toddler): these take clean water only

ROOMS = {
    'khach': dict(name='Phòng khách', emoji='🛋️'),
    'ngu': dict(name='Phòng ngủ', emoji='🛏️'),
    'bep': dict(name='Bếp', emoji='🍳'),
    'tam': dict(name='Nhà tắm', emoji='🛁'),
    'bancong': dict(name='Ban công', emoji='🪴'),
    'tho': dict(name='Gian thờ', emoji='🪔'),
}

# Things that need care before the surface under them is cleaned.
# kind: fragile (lift it off, put it back after), valuable (put it in the little tray, tell the client),
# pet (carry it to another room, close the door).
ITEMS_CARE = {
    'binh_gom': dict(name='Bình gốm của ông', emoji='🏺', kind='fragile', move='Nhấc bình gốm ra', back='Đặt bình gốm lại',
                     comp=18, broke='Bình gốm của ông rơi xuống, vỡ một miếng ở miệng bình.'),
    'lo_hoa': dict(name='Lọ hoa thủy tinh', emoji='💐', kind='fragile', move='Nhấc lọ hoa ra', back='Đặt lọ hoa lại',
                   comp=8, broke='Lọ hoa thủy tinh đổ, nước lênh láng, vỡ tan dưới sàn.'),
    'khung_anh': dict(name='Khung ảnh cưới', emoji='🖼️', kind='fragile', move='Nhấc khung ảnh ra', back='Đặt khung ảnh lại',
                      comp=10, broke='Khung ảnh cưới rơi úp mặt, nứt một đường trên mặt kính.'),
    'nhan': dict(name='Chiếc nhẫn vàng', emoji='💍', kind='valuable', move='Cất nhẫn vào khay',
                 lost='Chiếc nhẫn lăn xuống lỗ thoát nước, phải tháo ống mới lấy ra được.'),
    'dong_ho': dict(name='Đồng hồ đeo tay', emoji='⌚', kind='valuable', move='Cất đồng hồ vào khay',
                    lost='Đồng hồ trượt khỏi mép bàn, rơi xuống gạch, xước mặt kính.'),
    'tai_nghe': dict(name='Tai nghe khách trước để quên', emoji='🎧', kind='valuable', move='Cất tai nghe vào khay',
                     lost='Tai nghe kẹt vào máy hút bụi, đứt một bên dây.'),
    'meo': dict(name='Mèo Mướp đang ngủ', emoji='🐈', kind='pet', move='Bế Mướp sang phòng khác',
                lost='Máy hút bụi rú lên sát tai, Mướp hoảng, cào một đường lên tay rồi chui gầm giường cả buổi.'),
}

# ---------------------------------------------------------------- the homes (one per client)
# rooms: room id -> (spots that are always there, spots that may be dirty today);
# items: (item id, room, spot); notes: what the client always says.
HOMES = {
    1: dict(place='Căn studio 12A, chung cư Mây', rooms={
            'khach': (('ban_lam_viec', 'san_quet', 'san_go'), ('quat_tran', 'ke_tivi', 'sofa')),
            'bep': (('mat_bep', 'san_quet', 'san_lau'), ('hut_mui', 'bon_rua', 'tu_lanh')),
            'tam': (('bon_cau', 'san_tam'), ('guong', 'lavabo'))},
            items=(('dong_ho', 'bep', 'tu_lanh'),), notes=('desk',)),
    2: dict(place='Căn 7B, chung cư Mây', rooms={
            'khach': (('sofa', 'san_quet', 'san_lau'), ('quat_tran', 'ban_tra', 'tham')),
            'ngu': (('nem', 'san_quet', 'san_lau'), ('noc_tu', 'guong')),
            'bep': (('mat_bep', 'san_quet', 'san_lau'), ('bon_rua', 'tu_lanh')),
            'bancong': (('cua_kinh', 'san_quet', 'san_lau'), ())},
            items=(('meo', 'khach', 'sofa'),), notes=('cat',)),
    3: dict(place='Nhà ống ngõ Hoa Sữa', rooms={
            'tho': (('ban_tho', 'tu_kinh', 'san_quet', 'san_lau'), ('den_tran',)),
            'khach': (('ke_tivi', 'san_quet', 'san_lau'), ('quat_tran', 'ban_tra')),
            'bep': (('mat_bep', 'san_quet', 'san_lau'), ('hut_mui', 'ban_an')),
            'tam': (('lavabo', 'bon_cau', 'san_tam'), ('guong',))},
            items=(('binh_gom', 'tho', 'tu_kinh'), ('nhan', 'tam', 'lavabo')), notes=('altar',)),
    4: dict(place='Căn 3C, khu tập thể Hoa Ban', rooms={
            'khach': (('tham', 'san_quet', 'san_lau'), ('quat_tran', 'ke_tivi')),
            'ngu': (('nem', 'san_quet', 'san_lau'), ('noc_tu', 'guong')),
            'bep': (('ban_an', 'san_quet', 'san_lau'), ('mat_bep', 'tu_lanh')),
            'tam': (('bon_cau', 'san_tam'), ('lavabo', 'guong'))},
            items=(('lo_hoa', 'khach', 'ke_tivi'),), notes=('baby',)),
    5: dict(place='Căn hộ cho thuê 9D, phố Gạo', rooms={
            'ngu': (('nem', 'san_quet', 'san_go'), ('noc_tu', 'guong', 'den_tran')),
            'tam': (('guong', 'bon_cau', 'san_tam'), ('lavabo',)),
            'bep': (('bon_rua', 'san_quet', 'san_lau'), ('mat_bep', 'tu_lanh'))},
            items=(('tai_nghe', 'ngu', 'nem'),), notes=('turnover',)),
    6: dict(place='Nhà phố số 18, đường Lá Me', rooms={
            'khach': (('noc_tu', 'ban_tra', 'san_quet', 'san_lau'), ('quat_tran', 'sofa')),
            'ngu': (('noc_tu', 'nem', 'san_quet', 'san_go'), ('guong', 'den_tran')),
            'bep': (('hut_mui', 'mat_bep', 'san_quet', 'san_lau'), ('bon_rua', 'ban_an')),
            'tam': (('guong', 'lavabo', 'bon_cau', 'san_tam'), ())},
            items=(('khung_anh', 'ngu', 'noc_tu'),), notes=('glove',)),
}
NOTES = {
    'desk': ('🚫', 'Đừng động vào bàn làm việc', 'Anh Tùng: “Bàn làm việc để nguyên giúp anh, giấy tờ anh xếp theo ý anh.”'),
    'cat': ('🐈', 'Nhà có mèo', 'Chị Hà: “Mướp hay liếm chân, sàn lau nước sạch thôi nha. Hút bụi thì bế Mướp ra chỗ khác.”'),
    'altar': ('🪔', 'Gian thờ lau khăn khô', 'Bà Xuân: “Bàn thờ ông bà con lau khăn khô thôi, đừng xịt gì lên.”'),
    'baby': ('👶', 'Nhà có bé nhỏ', 'Chị Quyên: “Bé Bin bò khắp nhà, sàn chỉ lau nước sạch. Đồ dễ vỡ để chỗ cao giúp chị.”'),
    'turnover': ('⏱️', 'Khách mới tới lúc hai giờ', 'Anh Khải: “Hai giờ khách vào. Nhanh mà sạch, đồ khách cũ để quên thì cất giùm.”'),
    'glove': ('🧤', 'Kiểm bằng găng trắng', 'Cô Diệu: “Cô vuốt găng trắng lên nóc tủ. Trên cao sạch thì cô mới tin chỗ dưới sạch.”'),
}
GENTLE = ('cat', 'baby')          # floors with clean water only
SKIP = {'desk': ('khach', 'ban_lam_viec')}   # a surface the client said to leave alone

# (client index, job title, opening, the rooms of the home this job covers (None: rolled), min_day, mod)
JOBS = [
    (1, 'Dọn căn studio của anh Tùng', 'Anh Tùng mở cửa, tai vẫn đeo tai nghe: “Em dọn giúp anh phòng khách với nhà tắm nhé, anh họp trong phòng.”',
     ('khach', 'tam'), 1, None),
    (2, 'Dọn nhà có mèo Mướp', 'Chị Hà ôm laptop ra quán cà phê: “Chìa khóa đây, Mướp đang ngủ trên sofa. Em dọn phòng khách với bếp giúp chị nha.”',
     ('khach', 'bep'), 1, None),
    (3, 'Dọn nhà bà Xuân', 'Bà Xuân chống gậy ra mở cổng: “Con vào đi. Gian thờ với nhà tắm hôm nay giúp bà nhé, tay bà run không lau được.”',
     ('tho', 'tam'), 1, None),
    (4, 'Dọn nhà chị Quyên', 'Chị Quyên bế bé Bin ra cửa: “Chị đưa bé đi tiêm, hai tiếng nữa về. Em dọn giúp chị nhé.”', None, 2, None),
    (5, 'Dọn căn hộ trả phòng', 'Anh Khải nhắn: “Khách vừa trả phòng 9D. Hai giờ khách mới vào, em dọn giúp anh.”', None, 2, None),
    (6, 'Dọn nhà cô Diệu', 'Cô Diệu đứng chờ ở cửa, tay cầm đôi găng trắng: “Cô dọn cả đời rồi, con làm thử cô xem.”', None, 3, None),
    (1, 'Dọn studio sau buổi tụ tập', 'Anh Tùng ngáp dài: “Tối qua mấy đứa bạn sang ăn lẩu… Bếp với phòng khách nhờ em nhé.”', ('khach', 'bep'), 2, None),
    (2, 'Dọn nhà trước khi mẹ chị Hà lên', 'Chị Hà nhắn: “Mai mẹ chị từ quê lên, em dọn kỹ giúp chị phòng ngủ với ban công nha.”', ('ngu', 'bancong'), 2, None),
    (3, 'Dọn nhà bà Xuân đón cháu', 'Bà Xuân cười móm mém: “Cuối tuần thằng cháu đích tôn về. Con dọn cho bà phòng khách với bếp nhé.”', ('khach', 'bep'), 2, 'weekend'),
    (6, 'Tổng vệ sinh nhà cô Diệu', 'Cô Diệu: “Sắp giỗ ông nhà cô, họ hàng về đông. Con dọn kỹ giúp cô.”', None, 3, 'tet'),
    (4, 'Dọn nhà chị Quyên sau mưa', 'Chị Quyên: “Mưa mấy hôm, bé đi chơi về chân lấm lem khắp nhà. Em lau giúp chị nhé.”', None, 2, 'mua'),
    (5, 'Dọn căn hộ sau mùa nồm', 'Anh Khải nhắn: “Nồm quá, gương với sàn đọng nước hết. Dọn kỹ giúp anh trước khi khách tới.”', None, 3, 'nom'),
]
KINDS = ('setup', 'job')
STAGES = ('work', 'done')

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Lịch hẹn đều đều, khách đi làm để chìa khóa lại.', weight=3),
    dict(id='weekend', emoji='🏡', label='Cuối tuần', hint='Khách ở nhà, nhìn bạn làm. Khách quen hay hẹn thêm.', min_day=2, weight=2),
    dict(id='mua', emoji='🌧️', label='Mưa dầm', hint='Sàn lấm bùn dép: quét, lau mấy lượt mới sạch.', min_day=2, weight=2),
    dict(id='nom', emoji='💦', label='Trời nồm', hint='Gương, kính đọng hơi nước, sàn trơn: lau kỹ hơn.', min_day=2, weight=2),
    dict(id='bui', emoji='🍂', label='Hanh khô, nhiều bụi', hint='Bụi bám dày trên cao: phủi kỹ trước khi lau.', min_day=2, weight=2),
    dict(id='tet', emoji='🧧', label='Mùa tổng vệ sinh', hint='Nhà nào cũng dọn kỹ, chỗ nào cũng bẩn hơn mọi khi. Tiền công thêm chút.', min_day=3, weight=1),
]

REG_STORY = {
    1: ('Anh Tùng giơ ngón cái qua màn hình: “Giấy tờ y chỗ cũ, tuyệt.”', 'Anh Tùng để lại hộp bánh trên bàn với tờ giấy: “Cho em.”',
        'Anh Tùng hẹn lịch cố định sáng thứ bảy.', 'Anh Tùng giới thiệu thêm hai bạn cùng chung cư.'),
    2: ('Chị Hà gửi ảnh Mướp nằm phơi bụng trên sofa sạch: “Nó thích lắm!”', 'Chị Hà khen: “Không còn sợi lông nào, đỉnh!”',
        'Mướp ra cửa đón bạn, cọ cọ vào chân.', 'Chị Hà đặt lịch hai tuần một lần.'),
    3: ('Bà Xuân rót chén trà mời bạn ngồi nghỉ.', 'Bà Xuân kể chuyện ông mua cái bình gốm ở chợ Đồng Xuân năm bảy mươi.',
        'Bà Xuân dúi vào tay túi ổi nhà trồng.', 'Bà Xuân dặn: “Tuần sau con lại đến nhé, bà chờ.”'),
    4: ('Bé Bin bò trên sàn thơm tho, cười khanh khách.', 'Chị Quyên nhắn: “Sàn sạch mà không mùi hóa chất, chị yên tâm.”',
        'Chị Quyên gửi bạn hộp sữa chua nhà làm.'),
    5: ('Anh Khải chụp ảnh căn phòng đăng lên trang: “Sạch như khách sạn.”', 'Khách mới của anh Khải chấm năm sao, khen phòng sạch.',
        'Anh Khải nhờ bạn dọn thêm căn thứ hai.'),
    6: ('Cô Diệu vuốt găng trắng lên nóc tủ, nhìn ngón tay, gật đầu.', 'Cô Diệu khen: “Con làm có thứ tự, cô ưng.”',
        'Cô Diệu gọi điện cho cô Mai: “Cứ cho đứa này sang nhà tôi.”'),
}

INTRO = dict(
    title='Giới thiệu nghề: giúp việc theo giờ',
    lead='Một xe đẩy đồ nghề, mấy cái khăn ba màu, xô, cây lau và một cuốn lịch hẹn. '
         'Cô Mai dọn nhà theo giờ hai mươi năm, giờ cô xếp lịch, bạn tới từng nhà khách.',
    work=[('🧺', 'Sáng: giặt khăn, châm đầy các chai trên xe đẩy'), ('🔔', 'Tới nhà khách, nghe lời dặn'),
          ('🧽', 'Chọn đúng dụng cụ, đúng chai cho từng chỗ'), ('⬇️', 'Trên cao trước, dưới thấp sau; khô trước, ướt sau'),
          ('🏺', 'Nhấc đồ dễ vỡ ra rồi đặt lại, cất đồ quý vào khay'), ('🚪', 'Mời khách đi một vòng kiểm nhà, nhận tiền công')],
    meet=[('💻', 'Anh Tùng: đừng động vào bàn làm việc'), ('🐈', 'Chị Hà và mèo Mướp sợ máy hút bụi'),
          ('🪔', 'Bà Xuân: gian thờ, bình gốm của ông'), ('👶', 'Chị Quyên: bé Bin bò khắp nhà'),
          ('⏱️', 'Anh Khải: dọn căn hộ trước giờ khách tới'), ('🧤', 'Cô Diệu: kiểm bằng găng trắng')],
    stars=[('✨', 'Chỗ nào cũng sạch'), ('🧽', 'Đúng khăn, đúng chai, không làm hỏng đồ'), ('🏺', 'Đồ dễ vỡ nguyên vẹn, đúng chỗ'),
           ('💍', 'Đồ quý cất vào khay, báo khách'), ('📝', 'Nhớ lời dặn'), ('⏱️', 'Gọn gàng, không làm đi làm lại')],
)

APPRENTICE = 2
LESSONS = [
    ('Bài 1 · Trên cao trước', 'Cô Mai đi cùng: “Trên cao xuống thấp, khô trước ướt sau. Lau sàn trước rồi phủi quạt là bụi rơi xuống sàn vừa lau.”'),
    ('Bài 2 · Khăn ba màu', 'Cô Mai dặn: “Khăn xanh cho kính, khăn vàng cho bàn bếp, khăn đỏ chỉ cho bồn cầu. Không bao giờ lẫn.”'),
]
CATCH = {
    'skip': 'Khoan, khách dặn để nguyên chỗ này mà con. Đọc lại lời dặn đi.',
    'fragile': 'Dừng tay! Nhấc đồ dễ vỡ ra trước rồi hẵng lau.',
    'valuable': 'Khoan, cất món đồ quý vào khay trước đã, kẻo rơi mất.',
    'pet': 'Bế con mèo ra chỗ khác trước, máy hút bụi ồn nó hoảng đấy.',
    'red_cloth': 'Khăn đỏ là khăn bồn cầu, không lau chỗ khác bao giờ con nhé.',
    'harm': 'Khoan, chai này mạnh quá, làm hỏng mặt đồ đấy. Đổi chai khác.',
    'gentle': 'Nhà này dặn sàn lau nước sạch thôi con.',
    'wet_first': 'Sàn còn bụi tóc kìa. Quét trước, lau sau con ạ.',
    'not_back': 'Đặt đồ dễ vỡ lại chỗ cũ rồi hẵng mời khách kiểm.',
    'dirty': 'Còn chỗ chưa sạch đấy. Xem lại từng phòng rồi hẵng mời khách.',
}

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='money_sofa', title='Tờ tiền dưới gầm sofa', emoji='💵', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Hút bụi gầm sofa, máy kêu “rột” một tiếng. Bạn cúi xuống: một tờ tiền gấp tư kẹt ở chân ghế.',
         options=[dict(id='tell', label='Để lên bàn, nhắn khách đã tìm thấy', hint='', effects=dict(xp=5), good=True,
                       outcome='Khách nhắn lại: “Trời, tìm cả tuần nay! Cảm ơn em nhiều.”'),
                  dict(id='leave', label='Đặt lại chỗ cũ, không nói gì', hint='', effects=dict(xp=1), good=None,
                       outcome='Tờ tiền vẫn nằm đó. Không ai biết bạn đã thấy.'),
                  dict(id='pocket', label='Bỏ túi, chắc khách cũng quên rồi', hint='+5 xu',
                       effects=dict(money=5, review=[1, 'Camera phòng khách quay cảnh người dọn nhặt tiền bỏ túi. Thất vọng.', 0]), good=False,
                       outcome='Tối đó cô Mai gọi điện, giọng buồn: khách xem lại camera rồi.')],
         default='leave'),
    dict(id='neighbour', title='Hàng xóm nhờ dọn riêng', emoji='🚪', npc=0, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Bà hàng xóm cùng tầng gõ cửa: “Cháu dọn nhà bà luôn nhé, bà trả tiền mặt, khỏi qua cô Mai cho rẻ.”',
         options=[dict(id='book', label='Xin số bà, nhờ cô Mai xếp lịch đàng hoàng', hint='', effects=dict(xp=5), good=True,
                       outcome='Cô Mai xếp lịch cho bà sáng thứ ba. Tổ có thêm một khách mới.'),
                  dict(id='decline', label='Từ chối khéo, hôm nay kín lịch', hint='', effects=dict(xp=1), good=None,
                       outcome='Bà gật gù rồi đóng cửa.'),
                  dict(id='cash', label='Nhận luôn, làm thêm giờ lấy tiền mặt', hint='+8 xu',
                       effects=dict(money=8, patience=-10, review=[2, 'Làm dở việc nhà tôi để chạy sang nhà bên kiếm thêm.', 0]), good=False,
                       outcome='Bạn chạy qua chạy lại, việc nhà khách chính bị chậm, cô Mai biết chuyện.')],
         default='decline'),
    dict(id='lift_broken', title='Thang máy hỏng', emoji='🛗', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Thang máy dán tờ giấy “Đang bảo trì”. Nhà khách ở tầng bảy, xe đẩy thì nặng.',
         options=[dict(id='split', label='Chia đồ làm hai chuyến, xách thang bộ', hint='Mất thêm chút thời gian', effects=dict(patience=-4, xp=3), good=True,
                       outcome='Mỏi chân nhưng đủ đồ. Khách thấy mồ hôi bạn, mời cốc nước mát.'),
                  dict(id='light', label='Chỉ mang khăn với một chai, còn lại để dưới sảnh', hint='',
                       effects=dict(xp=1), good=None, outcome='Lên tới nơi mới thấy thiếu cây lau, phải chạy xuống lấy.'),
                  dict(id='wait', label='Ngồi chờ thang sửa xong', hint='Khách chờ lâu', effects=dict(patience=-12), good=False,
                       outcome='Bốn mươi phút sau thang mới chạy. Khách gọi hỏi mãi.')],
         default='wait'),
    dict(id='camera_call', title='Khách gọi video kiểm tra', emoji='📱', npc=0, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Khách gọi video giữa chừng: “Em quay một vòng cho chị xem với.”',
         options=[dict(id='show', label='Vui vẻ quay một vòng, chỉ chỗ đã xong, chỗ đang làm', hint='', effects=dict(xp=4), good=True,
                       outcome='Khách cười: “Ok em, cứ làm đi.” Rồi tắt máy.'),
                  dict(id='later', label='Nhắn “em đang dở tay, lát gửi ảnh”', hint='', effects=dict(xp=1), good=None,
                       outcome='Lát sau bạn gửi ba tấm ảnh, khách thả tim.'),
                  dict(id='grumble', label='Càu nhàu: “Không tin thì đừng thuê”', hint='',
                       effects=dict(review=[2, 'Gọi hỏi một câu mà người dọn gắt gỏng.', 0]), good=False,
                       outcome='Khách im lặng tắt máy. Cô Mai nhắc bạn chuyện này buổi tối.')],
         default='later'),
    dict(id='spill_bucket', title='Đổ xô nước', emoji='🪣', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Quay người hơi nhanh, chân vướng quai xô. Nước lau nhà loang ra tận chân tủ gỗ.',
         options=[dict(id='dry', label='Lấy khăn khô thấm ngay, lau khô chân tủ', hint='', effects=dict(patience=-3, xp=3), good=True,
                       outcome='Chân tủ khô ráo, không phồng. Bạn kê xô vào góc cho chắc.'),
                  dict(id='mop', label='Cứ để đó, lát lau sàn luôn thể', hint='',
                       luck=dict(p=0.5, win=dict(effects={}, good=None, outcome='May mà nước chưa ngấm vào gỗ.'),
                                 lose=dict(effects=dict(money=-6), good=False, outcome='Chân tủ gỗ phồng lên một mảng, bạn đền tiền sửa.')), effects={})],
         default='mop'),
    dict(id='cleaner_smell', title='Mùi tẩy nồng quá', emoji='🌬️', npc=0, min_day=3, tone='gentle', at='between', weight=2, mods=('nom', 'mua'),
         text='Trời nồm, cửa đóng kín. Mùi tẩy bồn cầu đọng lại, cay cay sống mũi.',
         options=[dict(id='air', label='Mở cửa sổ, bật quạt thông gió, đeo khẩu trang', hint='', effects=dict(xp=3), good=True,
                       outcome='Gió lùa qua, mùi tan dần. Đầu óc tỉnh hẳn.'),
                  dict(id='more', label='Xịt thêm nước thơm cho át mùi', hint='', effects=dict(patience=-3), good=False,
                       outcome='Mùi thơm trộn mùi tẩy, càng nồng. Khách về nhăn mũi.')],
         default='more'),
    dict(id='lonely', title='Bà cụ muốn có người trò chuyện', emoji='🍵', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Bà Xuân rót trà, kéo ghế: “Con ngồi nghỉ tí, nghe bà kể chuyện ông ngày xưa.”',
         options=[dict(id='sit', label='Ngồi uống chén trà, nghe bà kể một lúc', hint='Chậm việc chút', effects=dict(patience=-3, xp=5), good=True,
                       outcome='Bà kể chuyện ông cưới bà bằng một xe đạp hoa. Bà cười suốt.'),
                  dict(id='later', label='Hẹn bà lúc dọn xong sẽ ngồi', hint='', effects=dict(xp=2), good=None,
                       outcome='Dọn xong bạn ngồi với bà mười phút. Bà vui.')],
         default='later'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='GV-S01', title='Khách tìm không thấy đôi bông tai', npc=3, tone='tense', min_day=2,
         opening='Bà Xuân gọi điện, giọng lo: “Con ơi, đôi bông tai vàng bà để trên lavabo đâu mất rồi. Hôm qua chỉ có con vào nhà.”',
         swap='Bạn là bà Xuân: mắt kém, hay cất đồ rồi quên, và đôi bông tai là của mẹ bà để lại.',
         facts=[dict(id='tray', title='Khay đồ quý', source='Thói quen', text='Hôm qua bạn cất mọi thứ trên lavabo vào cái khay sứ nhỏ trên kệ gương, có báo bà.'),
                dict(id='note', title='Tin nhắn hôm qua', source='Điện thoại', text='Tin nhắn gửi bà lúc chiều: “Bà ơi, con cất nhẫn với bông tai vào khay sứ trên kệ gương nhé.”'),
                dict(id='mood', title='Bà Xuân', source='Giọng bà', text='Bà không trách, bà sợ mất kỷ vật của mẹ.')],
         options=[dict(id='guide', label='Nhẹ nhàng nhắc bà xem khay sứ trên kệ gương, đọc lại tin nhắn hôm qua', requires=['tray', 'note'],
                       quality='good', stars=5, review='Con bé cất đồ cẩn thận, nhắn tin rõ ràng. Bà tìm thấy ngay.',
                       outcome='Bà tìm thấy đôi bông tai trong khay, cười run run: “Bà già lẩm cẩm quá.”',
                       perspectives=[dict(who='Bà Xuân', emoji='👵', text='Có người cẩn thận vậy bà yên tâm.'),
                                     dict(who='Cô Mai', emoji='🧺', text='Cất đồ quý rồi báo khách: tránh được bao nhiêu chuyện.')]),
                  dict(id='come', label='Hứa chiều ghé qua tìm giúp bà', requires=['mood'], quality='ok', stars=3,
                       review='Bà lo cả buổi sáng mới được con bé sang tìm giúp.',
                       outcome='Chiều bạn ghé, mở khay sứ ra là thấy. Bà đã lo suốt mấy tiếng.',
                       perspectives=[dict(who='Bà Xuân', emoji='😟', text='Giá mà biết sớm hơn.'),
                                     dict(who='Bạn', emoji='🙂', text='Lẽ ra nói luôn chỗ cất là xong.')]),
                  dict(id='deny', label='“Con không biết, con không đụng vào đồ của bà”', quality='bad', stars=1,
                       review='Hỏi một câu mà nó gắt lên, bà sợ quá.',
                       outcome='Bà buồn, gọi cho cô Mai. Mãi tối mới tìm thấy trong khay.',
                       perspectives=[dict(who='Bà Xuân', emoji='😢', text='Bà có trách con đâu…'),
                                     dict(who='Cô Mai', emoji='🧺', text='Khách lo thì mình bình tĩnh chỉ chỗ, đừng tự ái.')])],
         lesson='Đồ quý thì cất vào một chỗ cố định và báo khách ngay. Khách hỏi lại thì bình tĩnh chỉ chỗ.'),
    dict(id='GV-S02', title='Chủ nhà nhờ xem đồ của người thuê', npc=5, tone='tense', min_day=2,
         opening='Anh Khải nhắn: “Phòng 9D người thuê dài hạn đi vắng. Em dọn tiện mở tủ chụp giùm anh xem họ để gì trong đó.”',
         facts=[dict(id='lease', title='Phòng đang cho thuê', source='Lịch dọn', text='Phòng 9D đang có người thuê theo tháng, họ chỉ nhờ dọn sàn và nhà tắm.'),
                dict(id='rule', title='Lời cô Mai', source='Cô Mai', text='Dọn nhà ai là được tin vào nhà người đó. Không mở tủ, không chụp đồ riêng.'),
                dict(id='why', title='Lý do', source='Anh Khải', text='Anh Khải nghi người thuê nấu ăn trong phòng, nhưng chưa hỏi họ.')],
         options=[dict(id='refuse', label='Từ chối mở tủ, chỉ dọn đúng phần được nhờ; gợi ý anh hỏi thẳng người thuê', requires=['lease', 'rule'],
                       quality='good', stars=5, review='Người dọn biết giữ chừng mực. Người thuê tin, chủ nhà cũng tin.',
                       outcome='Anh Khải im một lúc rồi nhắn: “Ừ, để anh hỏi họ.”',
                       perspectives=[dict(who='Người thuê', emoji='🙂', text='Đồ của mình nguyên chỗ, yên tâm.'),
                                     dict(who='Cô Mai', emoji='🧺', text='Tổ mình sống bằng chữ tín.')]),
                  dict(id='look', label='Chỉ hé mắt nhìn, không chụp', requires=['why'], quality='ok', stars=2,
                       review='Không chụp nhưng vẫn mở tủ người ta.',
                       outcome='Người thuê về thấy cửa tủ không đóng khít, hỏi chủ nhà.',
                       perspectives=[dict(who='Người thuê', emoji='😕', text='Ai đã mở tủ của mình?'),
                                     dict(who='Anh Khải', emoji='😐', text='Rắc rối hơn anh nghĩ.')]),
                  dict(id='photo', label='Mở tủ chụp gửi anh Khải', quality='bad', stars=1,
                       review='Người dọn mở tủ chụp đồ riêng của người thuê. Không thể chấp nhận được.',
                       outcome='Người thuê biết chuyện, báo công an phường. Cô Mai phải xin lỗi.',
                       perspectives=[dict(who='Người thuê', emoji='😠', text='Riêng tư của tôi đâu?'),
                                     dict(who='Cô Mai', emoji='🧺', text='Một tấm ảnh mất cả tổ.')])],
         lesson='Vào nhà người ta là được tin. Chỉ dọn phần được nhờ, không mở tủ, không chụp đồ riêng của ai.'),
    dict(id='GV-S03', title='Khách đòi bớt tiền vì “dọn nhanh quá”', npc=6, tone='gentle', min_day=3,
         opening='Cô Diệu nhìn đồng hồ: “Hẹn hai tiếng mà con xong sớm hai mươi phút. Cô trả bớt nhé?”',
         facts=[dict(id='done', title='Việc đã xong', source='Lịch hẹn', text='Mọi phòng trong lịch đã sạch, cô Diệu vừa vuốt găng kiểm xong.'),
                dict(id='price', title='Giá của tổ', source='Cô Mai', text='Tổ tính theo việc trong lịch hẹn, xong sớm thì tiền công vẫn vậy.'),
                dict(id='extra', title='Còn thời gian', source='Đồng hồ', text='Còn hai mươi phút trước lịch nhà sau.')],
         options=[dict(id='offer', label='Lễ phép nói giá theo việc; xin làm thêm một việc nhỏ trong hai mươi phút', requires=['done', 'price', 'extra'],
                       quality='good', stars=5, review='Con bé nói chuyện lễ phép, còn lau giúp cô cái cửa sổ. Cô trả đủ, vui vẻ.',
                       outcome='Bạn lau thêm hai ô cửa sổ. Cô Diệu gật gù trả đủ tiền.',
                       perspectives=[dict(who='Cô Diệu', emoji='🧤', text='Nhanh mà kỹ thì cô chịu.'),
                                     dict(who='Cô Mai', emoji='🧺', text='Giữ giá, giữ cả lòng khách.')]),
                  dict(id='accept', label='Thôi cô bớt bao nhiêu cũng được', requires=['done'], quality='ok', stars=3,
                       review='Dọn sạch, nhưng hình như cô làm khó con bé.',
                       outcome='Cô Diệu bớt một ít. Tối cô Mai bảo lần sau cứ nói giá của tổ.',
                       perspectives=[dict(who='Cô Diệu', emoji='🧤', text='Cũng được.'),
                                     dict(who='Bạn', emoji='😔', text='Làm nhanh mà lại thiệt.')]),
                  dict(id='argue', label='“Cô không trả đủ thì lần sau đừng gọi tổ”', quality='bad', stars=1,
                       review='Hỏi một câu mà nói năng xấc xược.',
                       outcome='Cô Diệu gọi cho cô Mai đổi người.',
                       perspectives=[dict(who='Cô Diệu', emoji='😤', text='Thời nay ăn nói thế à.'),
                                     dict(who='Cô Mai', emoji='🧺', text='Nói giá cho rõ, đừng nói nặng.')])],
         lesson='Tiền công tính theo việc. Xong sớm thì lễ phép nói rõ, có thể xin làm thêm một việc nhỏ.'),
]
