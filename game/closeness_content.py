"""Điểm thân quen: authored content (tiers, gifts, likes, lines). Rules live in game/closeness.py.

Vietnamese strings are whole literals. Lines may be a dict(male=, female=, none=) when the
speaker addresses the player as anh/chị; `{anh}` / `{Anh}` tokens follow life_content.TOKENS.
"""
from __future__ import annotations

# (lowest score, name, emoji). tier(score) = 1 + the index of the last row whose low <= score.
TIERS = (
    (0, 'Người lạ', '🙂'),
    (20, 'Quen mặt', '👋'),
    (40, 'Người quen', '🤝'),
    (60, 'Thân thiết', '💛'),
    (80, 'Như người nhà', '🏡'),
)

# What people like or dislike. A person's likes are revealed as you get closer (or when a gift lands).
TAGS = {
    'sweet': ('🍧', 'Đồ ngọt, chè'),
    'betel': ('🌿', 'Trầu cau'),
    'fruit': ('🍊', 'Trái cây'),
    'cake': ('🍰', 'Bánh ngọt'),
    'snack': ('🍿', 'Bánh snack, kẹo'),
    'tea': ('🍵', 'Trà'),
    'coffee': ('☕', 'Cà phê'),
    'beer': ('🍺', 'Bia'),
    'flower': ('🌼', 'Hoa'),
    'comic': ('📚', 'Truyện, sách'),
    'toy': ('🪀', 'Đồ chơi'),
    'food': ('🍜', 'Món ăn nóng'),
    'cash': ('🧧', 'Phong bì'),
}

# Gifts you can buy on the street (paid from the workplace fund you are in, category 'gift_out').
GIFTS = {
    'che': dict(name='Ly chè đậu', emoji='🍧', price=4, tags=('sweet',)),
    'trau': dict(name='Khay trầu cau', emoji='🌿', price=5, tags=('betel',)),
    'snack': dict(name='Bịch bánh snack', emoji='🍿', price=3, tags=('snack',)),
    'keo_dua': dict(name='Hũ kẹo dừa', emoji='🍬', price=4, tags=('sweet', 'snack')),
    'trai_cay': dict(name='Túi trái cây', emoji='🍊', price=8, tags=('fruit',)),
    'banh_bong_lan': dict(name='Hộp bánh bông lan', emoji='🍰', price=9, tags=('cake', 'sweet')),
    'hoa_cuc': dict(name='Bó hoa cúc', emoji='🌼', price=7, tags=('flower',)),
    'tra': dict(name='Gói trà Thái Nguyên', emoji='🍵', price=10, tags=('tea',)),
    'ca_phe': dict(name='Túi cà phê rang', emoji='☕', price=10, tags=('coffee',)),
    'bia': dict(name='Lốc bia lon', emoji='🍺', price=12, tags=('beer',)),
    'truyen': dict(name='Cuốn truyện tranh', emoji='📚', price=6, tags=('comic',)),
    'do_choi': dict(name='Con quay đồ chơi', emoji='🪀', price=5, tags=('toy',)),
    'phong_bi': dict(name='Phong bì nhỏ', emoji='🧧', price=10, tags=('cash',)),
}

# Something from the place you work, at cost price (category 'gift_out'). One per workplace, where it fits.
STALL = {
    'milk_tea': dict(name='Ly trà sữa của tiệm', emoji='🧋', price=3, tags=('sweet',)),
    'cafe_bakery': dict(name='Hộp bánh su kem của tiệm', emoji='🧁', price=4, tags=('cake', 'sweet')),
    'restaurant': dict(name='Hộp mì xào của quán', emoji='🍜', price=4, tags=('food',)),
    'grocery': dict(name='Túi trái cây của tạp hóa', emoji='🍎', price=5, tags=('fruit',)),
    'florist': dict(name='Bó hoa nhỏ của tiệm', emoji='💐', price=4, tags=('flower',)),
    'farm': dict(name='Rổ trứng gà của trại', emoji='🥚', price=4, tags=('food',)),
    'homestay': dict(name='Hũ mứt dâu của homestay', emoji='🍓', price=4, tags=('sweet', 'fruit')),
    'boba': dict(name='Ly trà sữa của tiệm', emoji='🧋', price=3, tags=('sweet',)),
    'ice_cream': dict(name='Hộp kem dừa của tiệm', emoji='🍨', price=4, tags=('sweet',)),
    'pho': dict(name='Túi phở mang về của quán', emoji='🍜', price=4, tags=('food',)),
    'com': dict(name='Hộp cơm tấm sườn của quán', emoji='🍚', price=4, tags=('food',)),
    'photobooth': dict(name='Dải ảnh bốn ô khung dễ thương', emoji='🎞️', price=4, tags=('gift',)),
    'nail': dict(name='Chậu sen đá nhỏ trên bàn nail', emoji='🪴', price=4, tags=('flower',)),
}

# Things people give YOU. `bag`: kept in your gift bag (you can pass it on or enjoy it yourself).
RECEIVED = {
    'xoai': dict(name='Mấy trái xoài chín', emoji='🥭', tags=('fruit',), tier=3),
    'banh_it': dict(name='Chục bánh ít lá gai', emoji='🍙', tags=('cake',), tier=3),
    'che_nha': dict(name='Nồi chè nhà nấu', emoji='🍧', tags=('sweet',), tier=3),
    'rau_vuon': dict(name='Bó rau vườn nhà', emoji='🥬', tags=('food',), tier=3),
    'banh_bo': dict(name='Hộp bánh bò nướng', emoji='🍰', tags=('cake', 'sweet'), tier=4),
    'tra_ngon': dict(name='Gói trà ngon', emoji='🍵', tags=('tea',), tier=4),
    'chao': dict(name='Cà mên cháo gà', emoji='🍲', tags=('food',), tier=4),
    'mut': dict(name='Hũ mứt gừng', emoji='🫙', tags=('sweet',), tier=4),
}
ENVELOPE = dict(name='Phong bì mừng', emoji='🧧')

# Who you know from the journey: seeded likes (two) and one dislike each.
CAST_TASTE = {
    'ba_tam': dict(likes=('betel', 'sweet'), dislikes=('beer',)),
    'co_ba': dict(likes=('tea', 'fruit'), dislikes=('snack',)),
    'co_lua': dict(likes=('flower', 'cake'), dislikes=('beer',)),
    'anh_khoa': dict(likes=('coffee', 'beer'), dislikes=('flower',)),
    'chu_tu': dict(likes=('beer', 'tea'), dislikes=('sweet',)),
    'be_ti': dict(likes=('snack', 'comic'), dislikes=('betel',)),
    'ba_sau': dict(likes=('fruit', 'betel'), dislikes=('coffee',)),
}
# Career NPCs get likes rolled once from their id (children from KID_POOL).
ADULT_POOL = ('sweet', 'fruit', 'cake', 'tea', 'coffee', 'flower', 'food', 'beer', 'snack', 'comic')
KID_POOL = ('snack', 'toy', 'comic', 'sweet', 'cake', 'fruit')
KID_NOT = ('beer', 'coffee', 'betel', 'cash')

# Small talk with the journey cast: low tiers (1–3) and close tiers (4–5).
CHAT = {
    'ba_tam': (
        ('Ăn cơm chưa cháu? Nồi canh chua bà còn trên bếp đó.', 'Tiền phòng cứ từ từ, lo làm cho đàng hoàng là bà vui.',
         'Trời nay oi quá, đi làm nhớ mang chai nước theo nghe.'),
        ('Cháu về rồi hả? Bà để phần cháu chén chè đậu đỏ trong tủ.', 'Nhìn cháu đi làm về là bà yên bụng rồi.',
         'Có chuyện gì buồn thì lên đây kể bà nghe, đừng ôm một mình.'),
    ),
    'co_ba': (
        ('Tạp hóa hôm nay đông, cô tay chân không kịp luôn đó con.', 'Con mới đi làm về hả? Uống miếng nước rồi đi.',
         'Giá trứng lại lên rồi con ơi, chợ dạo này khó ghê.'),
        ('Con ghé đúng lúc, cô mới pha ấm trà, ngồi uống với cô chút.', 'Có gì cần cứ qua cô, đừng ngại nghe con.',
         'Hồi con mới tới cô lo lắm, giờ thấy con vững vàng cô mừng.'),
    ),
    'co_lua': (
        ('Tuần sau tổ dân phố họp, cháu rảnh thì ghé cho biết mặt mọi người.', 'Nhớ khai tạm trú đầy đủ nghe cháu.',
         'Hẻm mình sắp làm lại đèn đường, cô đang đi xin ý kiến.'),
        ('Cả tổ ai cũng khen cháu siêng. Cô nghe mà vui lây.', 'Cuối tháng phố làm tiệc, cô để phần cháu một chỗ ngồi.',
         'Có gì khó ở chỗ làm cứ nói cô, cô quen nhiều người lắm.'),
    ),
    'anh_khoa': (
        ('Hôm nay deadline dí quá, anh mới ngóc đầu lên được.', 'Em làm ở đâu dạo này? Nghe nói siêng lắm.',
         'Tối nay có trận bóng, rảnh qua coi chung không?'),
        ('Ê, cuối tuần đi ăn ốc không? Anh bao.', 'Có gì cần sửa CV hay viết thư ứng tuyển cứ quăng anh xem.',
         'Làm hàng xóm với em vui ghê, hẻm mình có thêm người để tám.'),
    ),
    'chu_tu': (
        ('Cái quạt nhà con kêu thì mang qua chú coi cho.', 'Nghề nào cũng vậy, tay quen rồi thì mắt tinh.',
         'Chú đang sửa cái radio cũ, nghe lại mấy bài xưa hay lắm.'),
        ('Rảnh ghé chú làm ly trà, chú kể chuyện hồi chú mới vô nghề.', 'Con làm ăn đàng hoàng, chú nhìn là biết.',
         'Xe cộ có gì trục trặc cứ dắt qua, chú sửa khỏi lấy tiền.'),
    ),
    'be_ti': (
        (dict(male='Anh ơi, bài toán này khó quá à!', female='Chị ơi, bài toán này khó quá à!', none='Ơi, bài toán này khó quá à!'),
         'Mẹ em nói phải học xong mới được chơi. Chán ghê!',
         dict(male='Anh có biết chơi quay không? Em mới tập nè.', female='Chị có biết chơi quay không? Em mới tập nè.',
              none='Có biết chơi quay không? Em mới tập nè.')),
        (dict(male='Anh ơi! Em được điểm 9 môn toán nè, khoe anh trước tiên luôn!',
              female='Chị ơi! Em được điểm 9 môn toán nè, khoe chị trước tiên luôn!', none='Em được điểm 9 môn toán nè, khoe đầu tiên luôn!'),
         dict(male='Mai anh dắt em đi ăn kem nha, em để dành tiền rồi nè.', female='Mai chị dắt em đi ăn kem nha, em để dành tiền rồi nè.',
              none='Mai dắt em đi ăn kem nha, em để dành tiền rồi nè.'),
         dict(male='Lớn lên em muốn giỏi nhiều nghề như anh.', female='Lớn lên em muốn giỏi nhiều nghề như chị.',
              none='Lớn lên em muốn giỏi nhiều nghề vậy luôn.')),
    ),
    'ba_sau': (
        ('Con mèo nhà bà lại trốn lên mái rồi, con có thấy nó không?', 'Hồi xưa hẻm này toàn nhà lá, giờ khác quá.',
         'Đi làm về trễ vậy con? Nhớ ăn uống cho đủ.'),
        ('Bà có hũ dưa cải muối, lát bà xới cho con một ít.', 'Con giống thằng cháu nội bà hồi trẻ, siêng mà hiền.',
         'Ngồi đây với bà chút, bà kể chuyện hẻm mình hồi xưa cho nghe.'),
    ),
}
# Small talk with customers you know (by message, from anywhere). {name} = their name.
CHAT_NPC = (
    ('Chào {anh}! Hôm nay tiệm có đông khách không?', 'Hôm trước {anh} làm cho mình ưng lắm đó.',
     'Mấy bữa nay bận quá, chưa ghé được. Tuần sau mình ghé nha!'),
    ('{Anh} ơi, mình mới đi chơi về, có mua chút quà, bữa nào ghé lấy nha!', 'Mình giới thiệu thêm mấy người bạn tới chỗ {anh} rồi đó.',
     'Nhắn hỏi thăm {anh} chút thôi. Làm việc nhớ giữ sức nha!'),
)

# The reply after a gift. {who} = their name, {gift} = the gift name.
GIFT_LINES = dict(
    liked=('{who} cười tít mắt: “Trời, đúng món ưng nhất luôn. Cảm ơn nhiều nghe!”',
           '{who} cầm {gift} mà vui ra mặt: “Sao biết hay vậy? Thích lắm luôn!”'),
    neutral=('{who} nhận {gift}: “Cảm ơn nha, bày vẽ chi cho tốn kém.”',
             '{who} gật gù: “Quý hóa quá, cảm ơn nghe.”'),
    disliked=('{who} cười gượng: “Cảm ơn nha… mà món này dạo này kiêng rồi.”',
              '{who} nhận {gift}, hơi lúng túng: “Ờ… cảm ơn. Chắc để dành cho người khác.”'),
    cash=('{who} đẩy phong bì lại: “Có gì đâu mà đưa tiền, kỳ lắm. Thôi lần này nhận cho vui thôi nghe.”',),
)

# Neighbour events you are invited to (journey cast only).
INVITES = {
    'ba_tam': ('🕯️', 'Đám giỗ ông nhà', 'Mai nhà bà làm đám giỗ ông nhà. Cháu ghé thắp nén nhang, ăn bữa cơm với cả nhà nghe.'),
    'co_ba': ('👶', 'Đầy tháng cháu nội', 'Cháu nội cô đầy tháng rồi! Tối mai con qua ăn mừng với cô nha.'),
    'co_lua': ('🏮', 'Tiệc tổ dân phố', 'Tổ mình làm tiệc cuối tuần ở đầu hẻm. Cháu tới góp vui với cả tổ nghe.'),
    'anh_khoa': ('🏠', 'Tân gia', 'Anh mới dọn chỗ làm việc tại gia, tối mai làm vài món tân gia. Qua chơi nha em!'),
    'chu_tu': ('🎂', 'Sinh nhật chú Tư', 'Chú sáu mươi tuổi rồi, bà xã chú làm mâm cơm. Con qua ăn với chú nghe.'),
    'be_ti': ('🎈', 'Sinh nhật Bé Tí', dict(male='Mai sinh nhật em! Anh qua ăn bánh kem với em nha, em mời cả lớp luôn.',
                                           female='Mai sinh nhật em! Chị qua ăn bánh kem với em nha, em mời cả lớp luôn.',
                                           none='Mai sinh nhật em! Qua ăn bánh kem với em nha, em mời cả lớp luôn.')),
    'ba_sau': ('🍑', 'Mừng thọ Bà Sáu', 'Con cháu làm lễ mừng thọ bà tám mươi. Con ghé chung vui với bà nghe.'),
}
INVITE_COST = 10   # the envelope you bring when you go

# Close people check on you. {anh} tokens allowed.
CARE = (
    'Hôm nay con mệt không? Đi làm về nhớ ăn cơm nghe.',
    'Thấy {anh} dạo này về trễ, giữ sức khỏe nha.',
    'Có gì buồn thì nói ra, cả hẻm ở đây mà.',
    'Nghe nói chỗ làm dạo này đông khách, cố lên nha!',
)
TIRED = (
    'Thấy con mệt quá, {who} mang qua {gift}. Ăn cho lại sức nghe.',
    '{who} gõ cửa, đưa {gift}: “Nghe nói dạo này mệt, ăn đi cho khỏe.”',
)
GIFT_ARRIVE = (
    '{who} ghé cho {gift}: “Nhà có nhiều, chia cho ăn lấy thảo.”',
    '{who} gửi {gift}: “Thấy ngon nên để phần một ít.”',
    '{who} dúi vào tay {gift}: “Cầm lấy, khách sáo gì.”',
)
ENVELOPE_ARRIVE = (
    '{who} dúi vào tay phong bì {amount} xu: “Lấy hên nghe, làm ăn phát đạt!”',
    '{who} lì xì phong bì {amount} xu: “Chúc năm nay mọi sự như ý nghe con.”',
)
WARN_INSPECT = '{who} nhắn: “Nghe nói mai có đoàn kiểm tra ghé {place} đó. Dọn dẹp gọn gàng, giấy tờ để sẵn nha.”'
THANK = '{who} cười: “Có gì đâu mà cảm ơn, quen biết mà.”'
UNTHANKED = '{who} hơi buồn vì chưa nghe một lời cảm ơn.'
