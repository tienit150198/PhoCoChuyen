"""💛 Thân thiết với NPC: authored content of the goodwill perks (rules in game/goodwill.py).

Vietnamese strings are whole literals (the English pack translates each whole). {who} is a person's name; {anh} / {Anh}
follow life_content.TOKENS like the closeness lines.

A perk row: (tier, id, emoji, name, words, hidden). A hidden row reads "🔒 ???" in the panel until it is reached; its
name and words are never sent before that (game/goodwill.py ladder()).
"""
from __future__ import annotations

# ---------------------------------------------------------------- everyone you serve (customers, cast aliases included)
# The pay a regular adds when you finish their job, by tier (percent of the job's pay), and the "giữ liên lạc" extra.
PAY_PCT = {1: 0, 2: 0, 3: 2, 4: 4, 5: 6}
KEEP_PCT = 2

COMMON = (
    (2, 'likes', '💡', 'Biết dần sở thích', 'Thân hơn là biết họ thích món gì, ghét món gì.', False),
    (2, 'tip', '🪙', 'Hay bo hơn', 'Khách quen bo thường hơn: tới gấp 1,6 lần khi như người nhà.', False),
    (3, 'pay', '💼', 'Khách ruột trả thêm', 'Phục vụ xong, họ trả thêm 2% (Thân thiết 4%, Như người nhà 6%).', False),
    (3, 'keep', '💬', 'Giữ liên lạc', 'Hỏi thăm hoặc tặng quà trong 7 ngày gần đây: trả thêm 2% nữa.', False),
    (4, 'forgive', '🤝', 'Bỏ qua lỗi nhỏ', 'Lỡ sai một chút, họ vẫn vui vẻ, ít phàn nàn.', False),
    (4, 'warn', '⚠️', 'Báo tin trước', 'Có đoàn kiểm tra là họ nhắn trước cho bạn.', False),
    (5, 'refer', '🤝', 'Giới thiệu khách sộp', 'Mỗi tuần, hỏi thăm là họ giới thiệu bạn bè tới: 3 khách sộp trả thêm 10%.', True),
)

# ---------------------------------------------------------------- the neighbours (journey cast)
CAST = {
    'ba_tam': (
        (4, 'meal', '🍲', 'Bữa cơm nhà bà', 'Mỗi tuần bà gọi xuống ăn cơm một bữa: tinh thần +5.', False),
        (4, 'rent', '🏠', 'Bớt tiền phòng', 'Còn ở gác nhà bà: tiền phòng bớt 10%, như người nhà bớt 20%.', False),
        (5, 'story', '📖', 'Chuyện riêng của bà', 'Bà kể chuyện ông nhà và căn gác năm xưa.', True),
    ),
    'co_ba': (
        (4, 'shop', '🛒', 'Mua quà giá quen', 'Quà mua ngoài phố rẻ hơn 10% (như người nhà 20%).', False),
        (4, 'parcel', '🎁', 'Gói quà quê', 'Mỗi tuần cô gói cho một món quê vào túi quà.', False),
        (5, 'item', '🫙', 'Món giấu dưới quầy', 'Hũ me ngào đường cô Ba tự làm, chỉ bán cho người thân. Ai nhận cũng mê.', True),
        (5, 'story', '📖', 'Chuyện riêng của cô Ba', 'Vì sao tạp hóa đầu hẻm không bao giờ đóng cửa sớm.', True),
    ),
    'co_lua': (
        (4, 'party', '🎉', 'Tiệc tổ dân phố', 'Mỗi tuần cô kéo bạn đi tiệc tổ: cả hẻm thân thêm 1, tinh thần +3.', False),
        (5, 'title', '🎖️', 'Người tốt của tổ', 'Cô Lụa ghi tên bạn vào sổ “Người tốt việc tốt” của tổ.', True),
        (5, 'story', '📖', 'Chuyện riêng của cô Lụa', 'Cái sổ tay cũ cô giữ từ hồi mới làm tổ trưởng.', True),
    ),
    'anh_khoa': (
        (4, 'post', '📣', 'Đăng bài giới thiệu', 'Mỗi tuần anh đăng bài khen chỗ bạn làm lên nhóm cư dân: 3 khách sộp trả thêm 10%.', True),
        (5, 'story', '📖', 'Chuyện riêng của anh Khoa', 'Dự án anh làm đêm mà chưa kể với ai.', True),
    ),
    'chu_tu': (
        (4, 'tea', '☕', 'Ấm trà đậm của chú', 'Mỗi tuần chú pha một ấm trà đậm: tỉnh táo +20.', False),
        (5, 'story', '📖', 'Chuyện riêng của chú Tư', 'Cái radio cũ chú sửa hoài không bán.', True),
    ),
    'be_ti': (
        (4, 'roof', '🌇', 'Sân thượng bí mật', 'Bé Tí dẫn lên góc sân thượng ngắm hoàng hôn, mỗi tuần một lần: tinh thần +6.', True),
        (5, 'story', '📖', 'Chuyện riêng của Bé Tí', 'Ước mơ Bé Tí chưa dám kể với mẹ.', True),
    ),
    'ba_sau': (
        (4, 'veg', '🥬', 'Rổ rau vườn', 'Mỗi tuần bà hái cho một món vườn nhà vào túi quà.', False),
        (5, 'recipe', '📜', 'Bí kíp gia truyền', 'Bà chỉ cách nêm nếm: quán ăn, quán nước của bạn được khách trả thêm 2%.', True),
        (5, 'story', '📖', 'Chuyện riêng của bà Sáu', 'Con hẻm này hồi còn là xóm lá.', True),
    ),
}
# The one weekly favour of each neighbour: the perk id that is the favour, the button words.
FAVOURS = {
    'ba_tam': ('meal', '🍲 Xuống ăn cơm với bà'),
    'co_ba': ('parcel', '🎁 Nhận gói quà quê'),
    'co_lua': ('party', '🎉 Đi tiệc tổ dân phố'),
    'anh_khoa': ('post', '📣 Nhờ anh đăng bài'),
    'chu_tu': ('tea', '☕ Ghé uống trà với chú'),
    'be_ti': ('roof', '🌇 Lên sân thượng với Bé Tí'),
    'ba_sau': ('veg', '🥬 Nhận rổ rau vườn'),
}
FAVOUR_LINES = {
    'ba_tam': 'Bà Tám dọn mâm cơm canh chua cá lóc: “Ăn đi cháu, nhà có hai bà cháu mình thôi mà.”',
    'co_ba': 'Cô Ba dúi vào tay gói quà: “Quê cô mới gửi lên, cầm về ăn lấy thảo.”',
    'co_lua': 'Tiệc tổ đông vui, cô Lụa giới thiệu bạn với từng nhà: “Đây là người mới siêng nhất hẻm mình đó.”',
    'anh_khoa': 'Anh Khoa gõ lạch cạch: “Xong! Bài khen chỗ em làm lên nhóm cư dân rồi, chờ khách tới nha.”',
    'chu_tu': 'Chú Tư rót trà: “Uống đi, trà này tỉnh cả buổi. Hồi chú mới vô nghề cũng nhờ nó.”',
    'be_ti': 'Bé Tí kéo tay bạn leo lên sân thượng: “Chỗ này bí mật đó, em chỉ dẫn người thân thôi!” Trời chiều tím ngắt.',
    'ba_sau': 'Bà Sáu đưa rổ đồ vườn: “Bà trồng không phân thuốc, ăn cho khỏe.”',
}
FAVOUR_ITEMS = {'co_ba': ('tra_ngon', 'mut', 'banh_bo'), 'ba_sau': ('rau_vuon', 'xoai', 'che_nha')}

# Customers at Như người nhà introduce a friend (the hidden 'refer' row of COMMON): their words.
REFER_LINE = '{who} nhắn: “Mình giới thiệu mấy người bạn tới {place} rồi đó, họ hào phóng lắm, phục vụ tốt nha!”'

# Chuyện riêng: told at Như người nhà after a few small favours done for them (ERRANDS_FOR_STORY).
STORIES = {
    'ba_tam': 'Căn gác bạn ở là phòng ông nhà bà ngồi viết thư hồi trẻ. Từ ngày ông mất, bà chỉ cho người bà tin ở. '
              '“Bà thấy cháu giống ổng: ít nói mà thương người.”',
    'co_ba': 'Hồi mới mở tạp hóa, một đêm mưa có đứa nhỏ chạy tới mua thuốc cho mẹ mà tiệm nào cũng đóng. Từ đó cô Ba '
             'luôn mở tới khuya: “Lỡ ai cần thì sao con.”',
    'co_lua': 'Trong sổ tay cũ của cô Lụa là tên từng nhà từng giúp nhau qua mùa lũ năm nào. Cô vừa thêm một dòng mới: '
              'tên của bạn.',
    'anh_khoa': 'Anh Khoa đang viết một ứng dụng để cả hẻm đặt hàng của nhau, không qua sàn nào. “Xong anh cho tiệm em '
                'lên đầu tiên, nhớ giữ bí mật nha!”',
    'chu_tu': 'Cái radio cũ là của người thầy dạy chú nghề sửa đồ. Chú sửa hoài để nó còn hát: “Còn tiếng là còn nhớ.”',
    'be_ti': 'Bé Tí muốn làm kiến trúc sư, xây lại hẻm mình có cây xanh và sân chơi. “Đừng nói mẹ nha, mẹ muốn em làm '
             'bác sĩ.”',
    'ba_sau': 'Hồi hẻm còn là xóm lá, bà Sáu nấu nồi cháo chung cho cả xóm mỗi lần mưa bão. “Nồi cháo đó nấu bằng tình '
              'người, con nhớ vậy.”',
}
ERRANDS_FOR_STORY = 3

# Hidden gift item under Cô Ba's counter (bought like the street gifts; never kept in a bag).
HIDDEN_GIFT = dict(id='me_co_ba', name='Hũ me ngào cô Ba làm', emoji='🫙', price=6, tags=('sweet', 'fruit'), extra=2)

# The street titles you can earn (shown in 👥 Người quen; nothing in journey.titles).
TITLES = {
    'co_lua': ('🎖️', 'Người tốt của tổ'),
    'all': ('💛', 'Cả hẻm thương'),
}

# ---------------------------------------------------------------- việc nhờ (one small request a day)
# tag -> (what to bring, why). The request is done by giving them any gift with that tag.
ERRANDS = {
    'sweet': ('một món ngọt', 'Tối nay nhà có khách, thiếu món tráng miệng.'),
    'fruit': ('ít trái cây', 'Mai nhà cúng rằm, cần ít trái cây bày mâm.'),
    'cake': ('hộp bánh ngọt', 'Mai sinh nhật đứa cháu, chưa kịp mua bánh.'),
    'snack': ('bịch bánh snack', 'Lũ nhỏ trong nhà đòi quà vặt quá trời.'),
    'tea': ('gói trà', 'Hết trà tiếp khách rồi mà chưa kịp ra chợ.'),
    'coffee': ('túi cà phê', 'Sáng nay quên mua cà phê, cả ngày lừ đừ.'),
    'beer': ('lốc bia', 'Cuối tuần có trận bóng, rủ mấy người ngồi coi.'),
    'flower': ('bó hoa', 'Mai có người quen khai trương, muốn tặng bó hoa.'),
    'comic': ('cuốn truyện', 'Mấy bữa nay buồn, muốn có gì đọc cho vui.'),
    'toy': ('món đồ chơi nhỏ', 'Đứa nhỏ nhà bên ốm, muốn có quà an ủi.'),
}
ERRAND_ASK = '{who} nhờ: “Ghé chợ thì mua giúp {what} nha. {why}”'
ERRAND_DONE = '{who} mừng rỡ: “Đúng lúc quá, cảm ơn nhiều nha! Có gì cần cứ nói lại nghe.”'

# ---------------------------------------------------------------- sinh nhật
BIRTHDAYS = {   # the neighbours' (dd, mm); everyone else's is drawn from their id
    'ba_tam': (12, 3), 'co_ba': (5, 8), 'co_lua': (20, 10), 'anh_khoa': (14, 2), 'chu_tu': (2, 9), 'be_ti': (1, 6),
    'ba_sau': (27, 1),
}
BIRTHDAY_LINE = '🎂 {who} xúc động: “Trời, nhớ cả sinh nhật luôn hả? Quý quá đi!”'

# ---------------------------------------------------------------- reveals (a word from them when a hidden row opens)
REVEAL = {
    'co_ba:item': 'Cô Ba nháy mắt: “Thân rồi cô mới nói nha, dưới quầy cô có hũ me ngào tự làm. Muốn tặng ai cứ lấy.”',
    'be_ti:roof': 'Bé Tí thì thầm: “Em biết một chỗ bí mật trên sân thượng, ngắm hoàng hôn đẹp lắm. Rảnh em dẫn lên!”',
    'ba_sau:recipe': 'Bà Sáu kéo bạn vô bếp: “Bà chỉ cho cách nêm của bà, nấu quán nào khách cũng khen.”',
    'anh_khoa:post': 'Anh Khoa: “Nhóm cư dân hẻm mình mấy ngàn người đó. Cần thì anh đăng bài giới thiệu chỗ em làm cho.”',
    'co_lua:title': 'Cô Lụa: “Tổ họp rồi, cả tổ thống nhất ghi tên cháu vào sổ Người tốt việc tốt!”',
    'refer': '{who}: “Thân vầy rồi, để mình giới thiệu bạn bè tới chỗ làm nha. Hỏi thăm mình là mình nhớ liền.”',
    'all': 'Cả hẻm ai cũng nhắc tên bạn. Đi tới đâu cũng có người chào, có người mời ly trà.',
    'story': '{who} hẹn: “Bữa nào rảnh ngồi đây, có chuyện này chưa kể ai nghe.”',
}
