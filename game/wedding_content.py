"""Hôn nhân: the price lists and the words of a Vietnamese wedding (game/marriage.py).

Scale: 1 xu is about 100.000 đồng. A shop day earns ~40–120 xu, office pay is
16–55 xu a day and rent + meals cost 10–20 xu, so a modest home wedding (~500
xu for the couple) is a few weeks of saving and a restaurant wedding of 20
tables (~1.600 xu) a real goal. Tiền mừng usually covers the tables, rarely the
venue, the ceremonies and the extras: a sensible wedding ends near break-even or
a little in the red, a lavish one with few acquaintances costs a lot.

Every price here is authoritative: the client only shows these numbers and the
server recomputes every total (marriage.quote).
"""
from __future__ import annotations

DEPOSIT_PCT = 30            # đặt cọc when both spouses confirm; the rest is paid on the day
TABLE_SEATS = 10
TABLES_MIN, TABLES_MAX = 5, 60
DAYS_MIN, DAYS_MAX, DAYS_DEFAULT = 2, 10, 3   # the wedding is N life days after both confirm
PROPOSALS_PER_DAY = 3
DECLINE_HOURS = 3           # a declined proposer waits this long (real hours) before asking the same person (owner 02/10: 3 tiếng)
REMARRY_DAYS = 3            # after a divorce, both wait this long before a new proposal
PROPOSAL_DAYS = 7           # an unanswered proposal expires (the ring comes back)

# ---------------------------------------------------------------- rings
RINGS = [
    dict(id='bac', emoji='💍', tone='silver', name='Nhẫn bạc khắc tên', price=50,
         desc='Bạc 925, khắc tên hai đứa ở mặt trong.'),
    dict(id='vang_tay', emoji='💍', tone='gold', name='Nhẫn vàng tây 18K', price=150,
         desc='Vàng 18K trơn, đeo hằng ngày không lo trầy.'),
    dict(id='vang_ta', emoji='💍', tone='gold', name='Nhẫn vàng ta 24K (1 chỉ)', price=280,
         desc='Một chỉ vàng 9999, sau này để dành cũng được.'),
    dict(id='ruby', emoji='💍', tone='ruby', name='Nhẫn vàng đính ruby', price=480,
         desc='Viên ruby đỏ như pháo cưới, ổ vàng 18K.'),
    dict(id='kim_cuong', emoji='💎', tone='diamond', name='Nhẫn kim cương 5 ly', price=900,
         desc='Kim cương 5 ly có giấy kiểm định, lấp lánh dưới đèn.'),
]
RING_INDEX = {r['id']: r for r in RINGS}

# Nhẫn đổi màu: the metal (every ring) and the stone (rings with one). A colour costs
# max(0, its extra - the extra of the tier's own colour): choosing never makes a ring cheaper.
METALS = [
    dict(id='bac', name='Bạc', hex='#c9ced6', dark='#7f8893', extra=0),
    dict(id='vang', name='Vàng', hex='#e6b843', dark='#a4761a', extra=20),
    dict(id='vang_hong', name='Vàng hồng', hex='#eaa98f', dark='#ad6049', extra=25),
    dict(id='bach_kim', name='Bạch kim', hex='#eef0f3', dark='#9aa3ad', extra=60),
]
METAL_INDEX = {m['id']: m for m in METALS}
STONES = [
    dict(id='trang', name='Kim cương trắng', hex='#f4fbff', dark='#9fc3dd', extra=30),
    dict(id='ruby', name='Ruby đỏ', hex='#e0334f', dark='#8e1027', extra=0),
    dict(id='sapphire', name='Sapphire xanh', hex='#3564dc', dark='#152f86', extra=20),
    dict(id='luc_bao', name='Ngọc lục bảo', hex='#23a574', dark='#0c5c3d', extra=25),
    dict(id='tim', name='Thạch anh tím', hex='#9563dc', dark='#4f2a8c', extra=0),
    dict(id='hong', name='Đá hồng', hex='#f387b0', dark='#b0406c', extra=10),
]
STONE_INDEX = {x['id']: x for x in STONES}
RING_COLORS = {'bac': ('bac', None), 'vang_tay': ('vang', None), 'vang_ta': ('vang', None), 'ruby': ('vang', 'ruby'), 'kim_cuong': ('bach_kim', 'trang')}
RECOLOR_FEE = 20        # "tiệm kim hoàn": re-plating / re-setting a ring you hold, plus any colour difference

# Preset proposal messages: no free text (no harassment, nothing to moderate).
MESSAGES = [
    dict(id='hem', text='Mình đi qua bao nhiêu con hẻm, chỉ muốn về chung một nhà với bạn. Bạn đồng ý nhé?'),
    dict(id='tra', text='Từ ly trà đầu tiên ở phố, mình đã biết là bạn rồi. Mình cưới nhau nha?'),
    dict(id='tiem', text='Mai mốt mình cùng mở một tiệm nhỏ, tối nào cũng cùng nhau khép ca. Bạn chịu không?'),
    dict(id='nhan', text='Không cần pháo hoa, chỉ cần mỗi ngày sống ở phố đều có bạn. Bạn nhận chiếc nhẫn này nhé?'),
    dict(id='ba_tam', text='Bà Tám bảo cưới sớm cho bà có dịp nấu nồi canh chua thật to. Mình cũng nghĩ vậy. Còn bạn?'),
    dict(id='ca_pho', text='Cả phố biết mình thương bạn rồi, giờ chỉ còn chờ bạn gật đầu thôi.'),
]
MESSAGE_INDEX = {m['id']: m for m in MESSAGES}

# ---------------------------------------------------------------- the reception
# menu_pct: the same menu costs less when the neighbourhood cooks at home and more in a big hall.
# gifts: tiền mừng of an ordinary guest (xu, weight): people give by the venue they are invited to.
VENUES = [
    dict(id='home', emoji='🏠', name='Rạp cưới tại nhà', fee=120, max_tables=30, menu_pct=85, mood=1, near=5,
         desc='Dựng rạp trước ngõ, thuê bàn ghế, bát đĩa; đội nấu cỗ lo cơm nước. Hàng xóm đến đông.',
         gifts=((2, 15), (3, 30), (5, 45), (10, 10))),
    dict(id='restaurant', emoji='🍽️', name='Nhà hàng Hoa Sen', fee=200, max_tables=40, menu_pct=100, mood=1, near=0,
         desc='Phí sảnh đã gồm âm thanh, ánh sáng cơ bản và phục vụ bàn.',
         gifts=((3, 10), (5, 50), (10, 32), (20, 8))),
    dict(id='center', emoji='🏛️', name='Trung tâm tiệc cưới Sen Vàng', fee=450, max_tables=60, menu_pct=140, mood=2, near=0,
         desc='Sảnh lớn, đèn chùm, màn LED và lối đi hoa. Khách thường mừng nhiều hơn.',
         gifts=((5, 55), (10, 35), (20, 8), (50, 2))),
]
VENUE_INDEX = {v['id']: v for v in VENUES}

# Price of one table of 10 at a restaurant (menu_pct 100); gift_pct: guests who eat well give a little more.
MENUS = [
    dict(id='binh_dan', name='Bình dân', price=25, gift_pct=95,
         dishes=['Gỏi ngó sen tôm thịt', 'Gà luộc lá chanh', 'Nem rán', 'Xôi gấc', 'Canh măng móng giò',
                 'Rau cải xào tỏi', 'Bia và nước ngọt']),
    dict(id='tieu_chuan', name='Tiêu chuẩn', price=40, gift_pct=100,
         dishes=['Súp cua gà xé', 'Gỏi ngó sen tôm thịt', 'Gà hấp lá chanh', 'Tôm hấp nước dừa', 'Bò lúc lắc',
                 'Lẩu Thái hải sản', 'Chè hạt sen long nhãn', 'Bia và nước ngọt']),
    dict(id='sang_trong', name='Sang trọng', price=65, gift_pct=110,
         dishes=['Súp bào ngư hải sâm', 'Salad cá hồi', 'Tôm hùm nướng bơ tỏi', 'Bò Úc sốt tiêu đen',
                 'Cá tầm hấp xì dầu', 'Lẩu cua biển', 'Bánh kem và trái cây', 'Rượu vang và bia']),
]
MENU_INDEX = {m['id']: m for m in MENUS}

# ---------------------------------------------------------------- ceremonies (all optional)
CEREMONIES = [
    dict(id='dam_ngo', name='Lễ dạm ngõ', price=20, mood=1,
         desc='Nhà trai sang thưa chuyện: trầu cau, ấm chè, bánh kẹo.'),
    dict(id='an_hoi', name='Lễ ăn hỏi', options=((5, 60, 1), (7, 85, 2), (9, 120, 3)),
         desc='Tráp trầu cau, bánh cốm, chè sen, mứt, rượu, lợn quay; đội bê tráp mặc áo dài.'),
    dict(id='gia_tien', name='Lễ gia tiên', price=30, mood=2,
         desc='Thắp hương trước bàn thờ hai họ, trao nhẫn, rước dâu.'),
    dict(id='le_duong', name='Lễ thành hôn (lễ đường)', price=50, mood=1,
         desc='Cổng hoa, sân khấu, rót rượu, cắt bánh trước quan khách.'),
]
CEREMONY_INDEX = {c['id']: c for c in CEREMONIES}
AN_HOI_TRAYS = tuple(n for n, _, _ in CEREMONY_INDEX['an_hoi']['options'])

# ---------------------------------------------------------------- extras
# per10: price per 10 seats (thiệp and quà cảm ơn are counted per guest).
# attend: extra share of invited guests who come (thiệp mời đàng hoàng).
EXTRAS = [
    dict(id='album', emoji='📸', name='Ảnh cưới & album', price=120, mood=0, desc='Chụp ngoại cảnh một ngày, album 30 trang.'),
    dict(id='dress', emoji='👗', name='Váy cưới & vest (thuê)', price=60, mood=1, desc='Hai bộ váy, một bộ vest, đổi size miễn phí.'),
    dict(id='makeup', emoji='💄', name='Trang điểm', price=25, mood=1, desc='Trang điểm và làm tóc cho cô dâu, chú rể.'),
    dict(id='mc', emoji='🎤', name='MC dẫn chương trình', price=30, mood=1, desc='Dẫn lễ, mời phát biểu, giữ nhịp tiệc.'),
    dict(id='band', emoji='🎸', name='Ban nhạc & ca sĩ', price=70, mood=2, desc='Ba nhạc công và một ca sĩ hát suốt tiệc.'),
    dict(id='car', emoji='🚗', name='Xe hoa', price=45, mood=1, desc='Xe kết hoa tươi rước dâu, có tài xế.'),
    dict(id='flowers', emoji='💐', name='Trang trí hoa', price=60, mood=1, desc='Cổng hoa, bàn gallery, hoa bàn tiệc.'),
    dict(id='cards', emoji='💌', name='Thiệp cưới', price=0, mood=1, attend=6,   # mời khách không mất tiền (owner, 01/10)
         desc='Miễn phí. Mời bằng thiệp thì khách đến đông hơn.'),
    dict(id='confetti', emoji='🎉', name='Pháo giấy', price=15, mood=1, desc='Pháo kim tuyến lúc cô dâu chú rể bước vào.'),
    dict(id='favors', emoji='🎁', name='Quà cảm ơn khách', per10=8, mood=2,
         desc='0,8 xu mỗi khách: hộp kẹo và túi trà nhỏ in tên hai bạn.'),
]
EXTRA_INDEX = {x['id']: x for x in EXTRAS}

MOODS = ((12, '🎊', 'Linh đình, cả phố còn nhắc mãi'), (8, '🥳', 'Rộn ràng, khách nán lại chụp ảnh'),
         (4, '😊', 'Vui vẻ, ấm cúng'), (0, '🙂', 'Tiệc gọn, khách ăn xong về sớm'))

# ---------------------------------------------------------------- guests and tiền mừng
# Closeness 0–100 (game/closeness.py when present, else bonds/relationships); tier 1–5.
TIER_NAMES = {1: 'Người lạ', 2: 'Quen mặt', 3: 'Người quen', 4: 'Thân thiết', 5: 'Như người nhà'}   # = closeness_content.TIERS
# Tiền mừng of a named guest by tier (xu, weight).
TIER_GIFTS = {
    5: ((20, 40), (30, 30), (50, 25), (100, 5)),
    4: ((10, 45), (20, 40), (30, 15)),
    3: ((5, 40), (10, 50), (20, 10)),
    2: ((3, 20), (5, 60), (10, 20)),
    1: ((2, 20), (3, 30), (5, 50)),
}
FAR_ATTEND = 35             # % of seats beyond the couple's circle that still fill (người quen sơ)
NEAR_ATTEND = 78            # % of seats within the circle that fill, before warmth, mood and thiệp

# Groups of ordinary guests (no names), in the order seats are given out.
GROUPS = [
    dict(id='ho_hang', emoji='👨‍👩‍👧', name='Họ hàng hai bên'),
    dict(id='ban_be', emoji='🧑‍🤝‍🧑', name='Bạn bè'),
    dict(id='dong_nghiep', emoji='💼', name='Đồng nghiệp'),
    dict(id='hang_xom', emoji='🏘️', name='Hàng xóm khu phố'),
    dict(id='khach_quen', emoji='🛍️', name='Khách quen của tiệm'),
]

RICH = [  # one in five weddings (more in a big hall): a big envelope
    dict(name='Chú Sáu Việt kiều', emoji='🧳', amount=120, what='một chỉ vàng',
         line='Chú về ăn cưới tụi con nè! Mừng một chỉ vàng làm vốn, mai mốt mở tiệm nhớ mời chú ghé.'),
    dict(name='Bác Hai chủ vựa trái cây', emoji='🍍', amount=100, what='mười triệu',
         line='Bác không giỏi nói, bác gửi phong bì dày dày chút cho hai đứa.'),
    dict(name='Dì Út trúng số năm ngoái', emoji='🎫', amount=80, what='tám triệu',
         line='Dì hên được một lần, giờ chia hên cho tụi con!'),
]
JOKES = [  # a funny envelope
    dict(name='Tèo bạn nối khố', emoji='🤪', amount=1,
         line='Phong bì có đúng một tờ vé số và dòng chữ “trúng thì chia đôi nghe”.'),
    dict(name='Anh Bảy xe ôm đầu hẻm', emoji='🛵', amount=2,
         line='Mừng 2 xu kèm lời hứa chở cô dâu chú rể miễn phí trọn một năm.'),
    dict(name='Nhóm bạn đại học', emoji='🎓', amount=10,
         line='Mười hai đứa góp chung một phong bì, bên trong 10 xu và mười hai chữ ký.'),
]
FORGOT = [  # forgets the envelope, sends it later (about half a day after the party); never someone listed as a named guest
    dict(who='chu_tu', name='Chú Tư tiệm sửa đồ', emoji='👨‍🔧', later=10,
         line='Chú quên phong bì trên xe rồi! Mai chú gửi qua nghe, đừng giận chú.'),
    dict(who='co_hai_loa', name='Cô Hai Loa', emoji='🗣️', later=5,
         line='Cô để quên cái ví ở nhà, mà chuyện đám cưới này cô kể khắp hẻm giùm rồi nha!'),
    dict(who='anh_khoa', name='Anh Khoa hàng xóm', emoji='🧑‍💻', later=15,
         line='Anh chuyển khoản mà app ngân hàng bảo trì. Tối anh chuyển lại liền!'),
]
GOSSIP = [
    'Cô Hai Loa: “Cỗ ngon mà chè hơi ngọt. Nói vậy thôi chứ cô ăn hai chén.”',
    'Thím Bảy: “Cô dâu chú rể hôm nay đẹp hơn bữa đi chợ nhiều!”',
    'Chị Tư Zalo đã đăng 37 tấm ảnh lên nhóm khu phố trước khi tiệc tàn.',
]
SPEECHES = {
    'mc': 'MC: “Xin mời hai họ nâng ly chúc mừng {a} và {b} trăm năm hạnh phúc!”',
    'ba_tam': 'Bà Tám: “Bà nhìn hai đứa từ hồi còn ở gác trọ. Giờ thì về chung một nhà rồi, nhớ thương nhau nghe.”',
    'co_lua': 'Cô Lụa (tổ trưởng): “Thay mặt tổ dân phố, chúc hai cháu thuận vợ thuận chồng, tát biển Đông cũng cạn.”',
    'co_ba': 'Cô Ba tạp hóa: “Ly trà đầu tiên ở phố cô còn nhớ, giờ tới ly rượu mừng. Chúc hai đứa hạnh phúc!”',
    'chu_tu': 'Chú Tư: “Nhà cửa có gì hư cứ gọi chú. Còn tình cảm thì hai đứa tự giữ nghe!”',
    'ba_sau': 'Bà Sáu: “Sống với nhau là nhường nhau một chút. Bà chúc hai đứa sớm có tin vui.”',
    'anh_khoa': 'Anh Khoa: “Chúc mừng đồng nghiệp! Từ nay có người nhắc giờ khép ca rồi nha.”',
    'be_ti': 'Bé Tí: “Chúc anh chị hạnh phúc! Có bánh kem thì cho em một miếng nha.”',
    'friend': '{g}: “Tụi mình quen nhau ở phố này, giờ đi ăn cưới nhau luôn. Chúc hai bạn hạnh phúc!”',
    'plain': 'Một vị khách lớn tuổi: “Chúc hai cháu trăm năm đầu bạc răng long.”',
}
NEWS_TEXT = '💍 {a} & {b} vừa tổ chức đám cưới {tables} bàn tại {venue}!'
NEWS_ENGAGED = '💞 {a} & {b} vừa đính hôn. Cả phố chờ ăn cưới!'
NEWS_BOOKED = '💌 {a} & {b} sẽ cưới lúc {at} tại {venue}! Cả phố vào Khu phố › Lịch cưới để dự nha.'
STICKER = dict(emoji='🏡', name='Đã về chung một nhà')
