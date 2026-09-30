"""Trà đá gốc bàng: a sidewalk iced-tea stall (plugin career).

Bà Lựu has sold tea under the bàng tree at the mouth of the lane for thirty
years. Her back hurts, so the player minds the stall for her. What the job is:

* set up in the morning (``setup`` task): pick a spot on the pavement (the
  tree shade, the awning of the closed tailor's when it rains, never out on
  the road), put the stools out, open the umbrella, place the ice box, brew
  the thermos and crush the first block of ice;
* brew the thermos (1–3 handfuls of leaves: weak, right, strong). Topping it
  up with hot water saves leaves but thins the tea, and brewed tea goes sour
  after a few hours (sooner in the heat). Regulars taste it;
* crush the ice blocks into the ice box. Crushed ice melts every turn: slower
  in the shade, twice as fast on a heat-wave day. A morning ice man drops the
  blocks you asked for;
* pour glasses (trà đá, trà nóng, trà chanh, sấu dầm in season), hand out
  snacks, refuse cigarettes to children, wash glasses in the basin and change
  the water when it turns murky;
* take the cash and give change with the shared till kit (game/careers/till.py):
  short change, extra change and "khỏi thối" tips follow the till rules;
* keep the tab (``tab`` tasks): chú Tường the xe ôm driver drinks on credit and
  settles every few days (``settle`` task). The player writes each amount in the
  book; a wrong line comes back at settlement as a dispute, and bà Lựu checks
  the book every evening;
* the timed "trật tự đô thị" sweep: pack the stools and the umbrella before
  the ward's truck reaches the stall (real seconds) or pay a fine and lose stools;
* surprises (rain, the ice cart, a runaway table, a drunk, minding a bike or a
  child, the street's gossip that links to the other careers), a football
  night rush (``match``), regulars whose small stories go on across days and a
  stall that grows (stools, a big umbrella, a banner).

Mistakes go through consequences (cq.slip / cq.react); money only through the
engine's money(). Everything random is rolled from the day, slot or task id.
"""
from __future__ import annotations

import copy
from ..jsoncopy import tree_copy
import hashlib

from . import kit
from . import till
from .. import consequences as cq
from .. import archive as ar

ID = 'tra_da'
GEN = 1

# ---------------------------------------------------------------- the stall's numbers
THERMOS_MAX = 12            # glasses in a full thermos
TOPUP = 6                   # glasses added by topping up with hot water
TOPUP_DROP = 20             # strength lost per top-up
BREW = {1: 50, 2: 75, 3: 90}   # handfuls of leaves -> strength
WEAK = 60                   # below: regulars say the tea is weak
WATERY = 40                 # below: "nước lã"
STALE_TURNS = 15            # brewed tea turns sour after this many turns (≈5 hours)
STALE_HEAT = 10
ICE_MAX = 24                # crushed portions the ice box holds
BLOCK = 8                   # portions from one block of ice
GLASSES_START = 8
GLASSES_MAX = 24
BASIN_MAX = 12              # glasses washed before the basin water turns murky
WASH_BATCH = 8
STOOLS_START = 4
STOOLS_MAX = 12
STOOLS_MIN = 2
TAB_LINES = 30
MATCH_TURNS = 8             # a football table wants its tea before half-time
SWEEP_FIRST, SWEEP_LATER = 30, 20   # seconds before the ward's truck reaches the stall
FINE_BASE, FINE_STOOL, FINE_UMBRELLA, FINE_ROAD = 10, 3, 5, 15
ICE_PLAN_MAX = 6
SAU_BATCH = 6               # portions the sấu seller leaves on a sấu-season morning

DRINKS = [
    dict(id='tra_da', name='Trà đá', emoji='🧊', cold=True, uses=()),
    dict(id='tra_nong', name='Trà nóng', emoji='🍵', cold=False, uses=()),
    dict(id='tra_chanh', name='Trà chanh', emoji='🍋', cold=True, uses=('chanh',)),
    dict(id='sau_da', name='Sấu dầm đá', emoji='🟢', cold=True, uses=('sau',)),
]
DRINK = {x['id']: x for x in DRINKS}
SNACKS = ('huong_duong', 'lac', 'keo_lac', 'banh_quy', 'thuoc_la')

ITEMS = [
    dict(id='che', name='Chè Thái khô', emoji='🍃', group='tea', unit='nắm', cost=2, life=30, start=10),
    dict(id='da', name='Đá cây', emoji='🧊', group='ice', unit='cây', cost=4, life=1, start=2),
    dict(id='chanh', name='Chanh', emoji='🍋', group='fruit', unit='quả', cost=1, life=5, start=8),
    dict(id='sau', name='Sấu dầm', emoji='🟢', group='fruit', unit='phần', cost=2, life=3, start=0),
    dict(id='huong_duong', name='Hướng dương', emoji='🌻', group='snack', unit='gói', cost=2, price=5, life=60, start=6),
    dict(id='lac', name='Lạc rang', emoji='🥜', group='snack', unit='gói', cost=2, price=5, life=20, start=6),
    dict(id='keo_lac', name='Kẹo lạc', emoji='🍬', group='snack', unit='thanh', cost=1, price=2, life=60, start=10),
    dict(id='banh_quy', name='Bánh quy', emoji='🍪', group='snack', unit='gói', cost=2, price=4, life=30, start=4),
    dict(id='thuoc_la', name='Thuốc lá lẻ', emoji='🚬', group='smoke', unit='điếu', cost=1, price=2, life=90, start=20),
]
ITEM = {x['id']: x for x in ITEMS}
PRICES = {'tra_da': 3, 'tra_nong': 3, 'tra_chanh': 6, 'sau_da': 7,
          'huong_duong': 5, 'lac': 5, 'keo_lac': 2, 'banh_quy': 4, 'thuoc_la': 2}

SPOTS = {
    'goc_bang': dict(name='Gốc bàng đầu ngõ', emoji='🌳', cap=8, shade=True, legal=True, dry=False,
                     note='Bóng mát, sát tường, không lấn lối đi.'),
    'hien': dict(name='Mái hiên tiệm may', emoji='🏚️', cap=5, shade=True, legal=True, dry=True,
                 note='Tiệm may đóng cửa cả tuần. Có mái che mưa, hơi chật.'),
    'le_duong': dict(name='Sát mép lòng đường', emoji='🛣️', cap=10, shade=False, legal=False, dry=False,
                     note='Rộng, đông người qua… nhưng là lấn ra đường.'),
}

PEOPLE = [
    ('Bà Lựu', 'Chủ quán trà đá', 'Bán trà gốc bàng ba mươi năm, nhớ mặt cả phố.', 'warm'),
    ('Chú Tường', 'Xe ôm đầu ngõ', 'Mê bóng đá, uống ghi sổ, hẹn ngày trả.', 'bossy'),
    ('Ông Khang', 'Hưu trí, cao thủ cờ tướng', 'Ngồi cả chiều với một cốc trà, chê chè nhạt.', 'sour'),
    ('Anh Đạt', 'Nhân viên văn phòng', 'Ra hút điếu thuốc giữa giờ, đếm tiền thối kỹ.', 'picky'),
    ('Linh', 'Học sinh lớp 11', 'Tan học rủ bạn uống trà chanh, hay xin thêm đá.', 'genz'),
    ('Cô Hoa', 'Bán xôi đầu ngõ', 'Biết hết chuyện cả phố, kể không ngừng.', 'warm'),
    ('Anh Hùng', 'Shipper', 'Chạy đơn liên tục, uống vội một cốc rồi đi.', 'quiet'),
    ('Cu Tủn', 'Cậu bé nhà bên', 'Học lớp 5, hay bị người lớn sai đi mua hộ.', 'genz'),
]
TAB_NPC = 1
KID_NPC = 7

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Nắng nhẹ, khách đều tay. Hợp để làm quen.', weight=3),
    dict(id='heat', emoji='🥵', label='Nắng nóng gay gắt', hint='Đá tan nhanh gấp đôi, ai cũng gọi trà đá. Canh thùng đá!', min_day=2, weight=2),
    dict(id='rain', emoji='🌧️', label='Mưa rào', hint='Mưa bất chợt: dọn quán vào mái hiên. Khách hay gọi trà nóng.', min_day=2, weight=2),
    dict(id='cool', emoji='🍃', label='Gió mát', hint='Trời dịu, đá tan chậm. Các ông ngồi đánh cờ lâu hơn.', min_day=2, weight=2),
    dict(id='football', emoji='⚽', label='Tối nay có trận', hint='Cả phố ra xem bóng: một bàn đông gọi dồn dập.', min_day=3, weight=1),
    dict(id='sau', emoji='🟢', label='Mùa sấu', hint='Sấu non về chợ: sáng nay có sấu dầm, khách hỏi luôn.', min_day=4, weight=1),
]
MOD = {m['id']: m for m in MODS}

# (npc, kind, title, opening, drinks, snacks, seats, note, min_day, mod)
ORDERS = [
    (6, 'glass', 'Anh Hùng uống vội', 'Một cốc trà đá, nhanh giúp anh nhé, đơn đang chờ!', {'tra_da': 1}, {}, 1,
     'Anh Hùng đứng cạnh xe, mũ bảo hiểm còn chưa kịp cởi.', 1, None),
    (2, 'glass', 'Ông Khang gọi trà nóng', 'Cho ông cốc trà nóng. Pha đặc vào, nhạt là ông trả lại đấy!', {'tra_nong': 1}, {}, 1,
     'Ông Khang bày bàn cờ, chắc ngồi đến chiều.', 1, None),
    (4, 'glass', 'Linh tan học', 'Chị ơi, cho em hai cốc trà chanh nhiều đá ạ!', {'tra_chanh': 2}, {}, 2,
     'Linh đi cùng bạn thân, cặp sách còn đeo trên vai.', 1, None),
    (3, 'glass', 'Anh Đạt giờ giải lao', 'Cho anh cốc trà đá với hai điếu thuốc. Mười phút nữa anh phải lên họp.', {'tra_da': 1},
     {'thuoc_la': 2}, 1, 'Anh Đạt hay đếm lại tiền thối ngay tại chỗ.', 1, None),
    (5, 'glass', 'Cô Hoa ngồi buôn chuyện', 'Cho cô cốc trà đá với cái kẹo lạc. Ngồi đây cô kể cho nghe chuyện này hay lắm…',
     {'tra_da': 1}, {'keo_lac': 1}, 1, 'Cô Hoa vừa bán hết gánh xôi sáng.', 1, None),
    (2, 'glass', 'Hai ông bạn cờ', 'Hai trà đá, một gói lạc cho hai ông già nào!', {'tra_da': 2}, {'lac': 1}, 2,
     'Ván cờ đang đến đoạn gay cấn.', 2, None),
    (4, 'glass', 'Nhóm bạn của Linh', 'Ba cốc trà chanh, thêm một gói hướng dương chị nhé!', {'tra_chanh': 3}, {'huong_duong': 1}, 3,
     'Cả nhóm vừa thi xong, ồn như chợ vỡ.', 2, None),
    (6, 'glass', 'Anh Hùng uống một, mang một', 'Hai cốc trà đá với gói bánh quy, anh uống một cốc, cốc kia mang lên cho khách.',
     {'tra_da': 2}, {'banh_quy': 1}, 1, 'Khách quen trên tầng năm hay nhờ anh Hùng mua trà.', 2, None),
    (3, 'glass', 'Anh Đạt dẫn đồng nghiệp', 'Ba trà đá, một trà nóng cho sếp anh, thêm một điếu nữa nhé.', {'tra_da': 3, 'tra_nong': 1},
     {'thuoc_la': 1}, 4, 'Cả phòng xuống giải lao cùng lúc.', 3, None),
    (5, 'glass', 'Cô Hoa đãi bạn hàng', 'Hai trà chanh cho cô với bà bán rau, thêm gói hướng dương.', {'tra_chanh': 2},
     {'huong_duong': 1}, 2, 'Bà bán rau vừa kể xong chuyện con dâu.', 3, None),
    (2, 'glass', 'Ông Khang gọi thêm bánh', 'Cốc trà nóng nữa, với gói bánh quy. Thằng Tường nó lại thua ông rồi!', {'tra_nong': 1},
     {'banh_quy': 1}, 1, 'Ông Khang cười khà khà, vuốt râu.', 3, None),
    (5, 'glass', 'Cô Hoa trốn nắng', 'Nóng chảy mỡ! Cho cô cốc trà đá nhiều đá vào!', {'tra_da': 1}, {}, 1,
     'Mồ hôi ướt đẫm lưng áo cô Hoa.', 2, 'heat'),
    (6, 'glass', 'Anh Hùng giữa trưa nắng', 'Hai trà đá liền một lúc, khát khô cả cổ!', {'tra_da': 2}, {}, 1,
     'Nắng hắt từ mặt đường lên như rang.', 2, 'heat'),
    (6, 'glass', 'Anh Hùng trú mưa', 'Mưa to quá! Cho anh cốc trà nóng ngồi chờ tạnh.', {'tra_nong': 1}, {'banh_quy': 1}, 1,
     'Áo mưa của anh Hùng nhỏ nước tong tong.', 2, 'rain'),
    (3, 'glass', 'Anh Đạt trú mưa', 'Mưa thế này chưa về được. Trà nóng và một điếu cho ấm người.', {'tra_nong': 1}, {'thuoc_la': 1}, 1,
     'Đôi giày da của anh Đạt ướt sũng.', 2, 'rain'),
    (2, 'glass', 'Ông Khang hóng gió', 'Trời mát thế này đánh cờ đến tối. Hai trà nóng, gói lạc!', {'tra_nong': 2}, {'lac': 1}, 2,
     'Gió thổi lá bàng rơi lả tả xuống bàn cờ.', 2, 'cool'),
    (4, 'glass', 'Linh hỏi sấu dầm', 'Chị ơi, sấu dầm có chưa ạ? Cho em hai cốc!', {'sau_da': 2}, {}, 2,
     'Mùa sấu, cả lớp Linh mê sấu dầm.', 4, 'sau'),
    (2, 'glass', 'Ông Khang nhớ mùa sấu', 'Sấu về rồi à? Cho ông một cốc sấu đá, gói lạc nữa.', {'sau_da': 1}, {'lac': 1}, 1,
     'Ông bảo sấu làm ông nhớ phố cũ ngày xưa.', 4, 'sau'),
    (5, 'glass', 'Cô Hoa mời sấu', 'Hai sấu dầm, một trà đá! Cô đãi mấy đứa bán hàng.', {'sau_da': 2, 'tra_da': 1}, {}, 3,
     'Cô Hoa hôm nay bán hết sớm.', 4, 'sau'),
    (7, 'kid', 'Cu Tủn đi mua hộ bố', 'Cô ơi, bố cháu bảo mua ba điếu thuốc với một cái kẹo lạc ạ!', {}, {'thuoc_la': 3, 'keo_lac': 1}, 0,
     'Cu Tủn mới học lớp 5, tay nắm tờ tiền nhàu.', 2, None),
    (7, 'kid', 'Cu Tủn khát nước', 'Cô ơi cho cháu cốc trà chanh… với hai điếu thuốc, chú xe ôm nhờ cháu mua ạ!', {'tra_chanh': 1},
     {'thuoc_la': 2}, 1, 'Cu Tủn mồ hôi nhễ nhại sau giờ đá bóng.', 3, None),
    (1, 'tab', 'Chú Tường ghi sổ', 'Cốc trà đá với điếu thuốc, ghi sổ cho chú! Tối qua đội nhà đá hay chưa…', {'tra_da': 1},
     {'thuoc_la': 1}, 1, 'Chú Tường mở miệng là nói chuyện bóng đá.', 1, None),
    (1, 'tab', 'Chú Tường với bạn xe ôm', 'Hai trà đá, một gói lạc, ghi sổ cả nhé cháu!', {'tra_da': 2}, {'lac': 1}, 2,
     'Bạn xe ôm của chú vừa chạy cuốc về.', 2, None),
    (1, 'tab', 'Chú Tường thua cờ', 'Trà nóng cho chú, gói hướng dương, ghi sổ! Ông Khang lại chấp chú con xe rồi.', {'tra_nong': 1},
     {'huong_duong': 1}, 1, 'Chú Tường vừa thua ông Khang một ván cờ.', 3, None),
    (1, 'match', 'Bàn xem bóng của chú Tường', 'Cả hội ra xem bóng! Năm trà đá, một trà chanh, hai gói hướng dương, một gói lạc. Hôm nay chú khao, trả tiền mặt!',
     {'tra_da': 5, 'tra_chanh': 1}, {'huong_duong': 2, 'lac': 1}, 6, 'Phải ra đủ trước khi hết hiệp một.', 3, 'football'),
]
KINDS = ('setup', 'glass', 'kid', 'tab', 'settle', 'match')
STAGES = ('prep', 'pay', 'book', 'read', 'dispute', 'done')

# Regulars' small stories: one line per finished visit, on and on across days.
REG_STORY = {
    1: ('Chú Tường: “Cháu mới à? Chú chạy xe ôm đầu ngõ này hai mươi năm rồi. Có gì cứ gọi chú!”',
        'Chú Tường cá với ông Khang đội nhà thắng hai bàn. Thua thì khao cả quán trà.',
        'Chú Tường khoe con gái đỗ đại học, móc ví ra xem ảnh mãi.',
        'Chú Tường bảo giờ nhiều người đặt xe qua app, chú đang tập dùng điện thoại.',
        'Chú Tường nhận cuốc xe qua app đầu tiên, về kể cả buổi: “Nó chỉ đường tận nơi, hay phết!”'),
    2: ('Ông Khang: “Chè phải đậm thì mới tỉnh mà đánh cờ.”',
        'Ông Khang dạy Linh thế cờ “pháo đầu”, con bé học nhanh ra phết.',
        'Ông Khang kể hồi trẻ ông làm thợ in, tay lúc nào cũng đen mực.',
        'Ông Khang mang cho quán cái điếu cày cũ: “Để dành cho khách quen.”',
        'Ông Khang nhấp ngụm trà: “Chè cháu pha giờ ngon gần bằng bà Lựu rồi.”'),
    3: ('Anh Đạt thở dài: “Sếp lại bắt làm báo cáo cuối tháng.”',
        'Anh Đạt bảo đang định bỏ thuốc, hôm nay chỉ mua đúng một điếu.',
        'Anh Đạt được lên trưởng nhóm, khao cả phòng trà đá.',
        'Anh Đạt chuyển sang uống trà nóng, bảo đang cai thuốc tuần thứ hai.',
        'Anh Đạt khoe đã bỏ hẳn thuốc lá, giờ ra đây chỉ để ngồi cho vui.'),
    4: ('Linh hỏi bà Lựu hè này quán có cần người phụ không.',
        'Linh đang ôn thi chuyên Văn, mang cả tập đề ra quán đọc.',
        'Linh thi xong môn Văn, bảo đề hỏi đúng bài em thích.',
        'Linh đỗ trường chuyên, dẫn cả nhóm ra quán ăn mừng.',
        'Linh viết bài văn về “quán trà đá gốc bàng”, được cô giáo đọc trước lớp.'),
    5: ('Cô Hoa: “Cháu bà Lựu đấy à? Trông sáng sủa đấy!”',
        'Cô Hoa kể nhà số 9 sắp cưới con gái, cỗ những ba mươi mâm.',
        'Cô Hoa than giá gạo nếp tăng, nồi xôi phải bớt đỗ.',
        'Cô Hoa mang sang cho quán nắm xôi xéo còn nóng hổi.',
        'Cô Hoa bảo cả phố khen quán trà giờ sạch sẽ hơn hẳn.'),
    6: ('Anh Hùng: “Uống vội cốc trà thôi em, app nó đếm từng phút.”',
        'Anh Hùng bị khách bom hai đơn liền, ngồi thừ ra cả buổi.',
        'Anh Hùng được thưởng tài xế chăm chỉ, mua cho quán một gói chè ngon.',
        'Anh Hùng kể vợ sắp sinh, đang chạy thêm ca tối.',
        'Anh Hùng khoe ảnh con gái mới sinh: “Đặt tên là Trà My, nghe mát không?”'),
    7: ('Cu Tủn khoe được điểm mười môn Toán.',
        'Cu Tủn học được cách đếm tiền thối, đòi đứng quầy phụ.',
        'Cu Tủn bảo bố nó hứa bỏ thuốc lá rồi.'),
}

# The stall's own story: bà Lựu hands it over, the regulars take to the new helper, it grows.
ARC = [
    dict(id='keys', emoji='🔑', title='Bà Lựu giao quán', glasses=0, day=1, gift=None,
         text=('Bà Lựu đưa chùm chìa khóa tủ chè: “Bà đau lưng, cháu trông quán hộ bà mấy hôm nhé.”',
               'Bà dặn: “Chè phải đậm, cốc phải sạch, tiền phải đếm. Khách quen thì nhớ mặt.”')),
    dict(id='taste', emoji='🍵', title='Bà Lựu nếm chè', glasses=8, day=1, gift=('stools', 2),
         text=('Bà Lựu chống gậy ra, rót một cốc, nhấp một ngụm: “Được. Có tay rồi đấy.”',
               'Bà sai cháu nội mang sang hai cái ghế nhựa đỏ: “Thêm chỗ cho khách.”')),
    dict(id='chess', emoji='♟️', title='Bàn cờ của ông Khang', glasses=18, day=3, gift=('chess', 1),
         text=('Ông Khang đặt bàn cờ tướng cũ lên bàn: “Để lại quán, ai rảnh thì đánh.”',
               'Từ hôm đó chiều nào gốc bàng cũng có người đứng xem cờ.')),
    dict(id='umbrella', emoji='⛱️', title='Chiếc ô mới', glasses=32, day=5, gift=('umbrella', 2),
         text=('Chiếc ô cũ rách một mảng. Bà Lựu dúi tiền: “Mua cái ô to vào, nắng thế này đá tan hết.”',
               'Ô mới màu xanh lá, che kín cả bàn. Thùng đá tan chậm hẳn.')),
    dict(id='banner', emoji='🪧', title='Tấm biển “Trà đá bà Lựu”', glasses=50, day=8, gift=('banner', 1),
         text=('Linh vẽ tặng tấm biển: “Trà đá bà Lựu · Chè đậm, đá mát, có sổ ghi.”',
               'Bà Lựu đứng ngắm mãi: “Giờ là quán của hai bà cháu rồi.”')),
]
ARC_INDEX = {x['id']: x for x in ARC}

GROWTH = [
    dict(id='stools', emoji='🪑', name='Thêm 2 ghế nhựa', cost=8, note='Thêm chỗ ngồi cho nhóm đông.'),
    dict(id='glasses', emoji='🥛', name='Thêm 4 cốc thủy tinh', cost=6, note='Đỡ phải rửa cốc liên tục.'),
    dict(id='umbrella', emoji='⛱️', name='Ô to che nắng', cost=30, note='Che kín bàn: đá tan chậm, mưa nhỏ không ướt ghế.'),
    dict(id='banner', emoji='🪧', name='Biển hiệu của quán', cost=20, note='Người qua đường nhận ra quán từ xa.'),
]
GROWTH_INDEX = {x['id']: x for x in GROWTH}

INTRO = dict(
    title='Giới thiệu nghề: bán trà đá vỉa hè',
    lead='Một chiếc bàn gỗ, bình chè, thùng đá và dăm cái ghế nhựa dưới gốc bàng. Bà Lựu bán ở đây ba mươi năm; mấy hôm nay bà đau lưng, nhờ bạn trông quán.',
    work=[('🪑', 'Dọn hàng: chọn chỗ, bày ghế, dựng ô, đặt thùng đá'),
          ('🍵', 'Pha bình chè: đủ chè thì đậm, châm nước nhiều là nhạt'),
          ('🧊', 'Đập đá, canh thùng đá: trời nóng đá tan rất nhanh'),
          ('🥤', 'Rót trà đá, trà nóng, trà chanh, sấu dầm'),
          ('🌻', 'Bán hướng dương, lạc, kẹo lạc, bánh quy, thuốc lẻ'),
          ('🧽', 'Rửa cốc trong chậu, nước đục thì thay'),
          ('📒', 'Ghi sổ cho chú xe ôm, đến hẹn thì thu'),
          ('💵', 'Thu tiền lẻ, thối đúng từng xu')],
    meet=[('🛵', 'Chú Tường xe ôm: bàn chuyện bóng đá, uống ghi sổ'),
          ('♟️', 'Ông Khang: ngồi cả chiều một cốc, chê chè nhạt'),
          ('🚬', 'Anh Đạt: ra hút thuốc giữa giờ, đếm tiền kỹ'),
          ('🎒', 'Linh và lũ bạn: trà chanh nhiều đá'),
          ('🗣️', 'Cô Hoa: tin gì trong phố cô cũng biết'),
          ('📦', 'Anh Hùng shipper: uống vội rồi chạy'),
          ('🚨', 'Trật tự đô thị: dẹp nhanh kẻo bị phạt, mất ghế'),
          ('🌧️', 'Mưa rào, nắng gắt, đêm bóng đá, khách quỵt, người say')],
    stars=[('✅', 'Rót đúng món, đủ số cốc'),
           ('🍵', 'Chè đậm vừa, không để ôi'),
           ('🧊', 'Trà đá có đá, cốc sạch'),
           ('💵', 'Thối đúng tiền, ghi sổ đúng số'),
           ('🙅', 'Không bán thuốc lá cho trẻ con'),
           ('🌳', 'Bày quán gọn, không lấn lòng đường')],
)

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='rain_shower', title='Mưa rào ập tới', emoji='🌧️', npc=5, min_day=2, tone='tense', at='between', weight=4, mods=('rain',),
         text='Mây đen kéo sập xuống, mưa rào quất ngang vỉa hè. Khách ôm cốc chạy toán loạn, ghế nhựa ướt nhẹp.',
         options=[dict(id='awning', label='Bê bàn, ghế, thùng đá vào mái hiên tiệm may', hint='Mất chút thời gian, quán vẫn bán tiếp',
                       effects=dict(patience=-5, move='hien'), good=True,
                       outcome='Cả quán dời vào mái hiên. Chật một chút nhưng khô ráo, khách ngồi lại uống trà nóng chờ tạnh.'),
                  dict(id='tarp', label='Căng tấm bạt che tạm', hint='Tốn 4 xu mua bạt', effects=dict(money=-4), good=None,
                       outcome='Tấm bạt xanh căng vội qua cành bàng. Dột một góc, nhưng tạm ổn.'),
                  dict(id='stay', label='Mưa bóng mây thôi, cứ ngồi nguyên', hint='Không tốn gì… nếu mưa tạnh nhanh',
                       effects=dict(wet=4, review=[2, 'Mưa hắt ướt hết ghế mà quán cứ để nguyên. Cốc nào cũng lẫn nước mưa.']), good=False,
                       outcome='Mưa không tạnh. Mấy cái cốc úp trên bàn lẫn nước mưa, phải rửa lại hết.')],
         default='stay'),
    dict(id='ice_cart', title='Xe đá đi ngang', emoji='🧊', npc=6, min_day=2, tone='gentle', at='between', weight=2,
         mods=('heat', 'normal', 'football'),
         text='Anh Tuấn xe đá bấm còi tin tin: “Nắng thế này đá tan nhanh lắm, lấy thêm cây không em?”',
         options=[dict(id='two', label='Lấy thêm 2 cây đá (10 xu)', hint='Đắt hơn giao buổi sáng, nhưng có ngay',
                       effects=dict(money=-10, stock={'da': 2}), good=True, outcome='Hai cây đá lạnh buốt được thả vào bao tải cạnh thùng.'),
                  dict(id='one', label='Lấy 1 cây thôi (5 xu)', hint='Dự phòng một ít', effects=dict(money=-5, stock={'da': 1}), good=None,
                       outcome='Thêm một cây đá dự phòng.'),
                  dict(id='no', label='Thôi, còn đủ', hint='Nhớ canh thùng đá', effects={}, good=None, outcome='Xe đá đi mất hút cuối phố.')],
         default='no'),
    dict(id='dash', title='Khách uống xong chuồn thẳng', emoji='🏃', npc=1, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Hai thanh niên lạ mặt uống bốn cốc trà đá, cắn hết gói hướng dương rồi đứng dậy nổ máy phóng đi, không trả một đồng.',
         options=[dict(id='shout', label='Gọi với theo', hint='Hên xui', effects=dict(stock={'huong_duong': -1}, dirty=4),
                       luck=dict(p=0.4, win=dict(effects=dict(money=17), good=True,
                                                 outcome='Một cậu quay xe lại, gãi đầu: “Em tưởng bạn em trả rồi.” Trả đủ 17 xu.'),
                                 lose=dict(effects={}, good=False, outcome='Tiếng gọi chìm trong tiếng còi xe. Mất trắng 17 xu tiền trà và hướng dương.'))),
                  dict(id='xeom', label='Nhờ chú Tường xe ôm đuổi theo', hint='Chú thuộc từng ngõ ngách', effects=dict(stock={'huong_duong': -1}, dirty=4),
                       luck=dict(p=0.7, win=dict(effects=dict(money=17, xp=4), good=True,
                                                 outcome='Chú Tường đuổi kịp ở ngã tư, hai cậu kia xin lỗi rối rít, gửi đủ 17 xu. Chú còn dặn: “Khách lạ thì thu tiền trước nhé.”'),
                                 lose=dict(effects={}, good=None, outcome='Hai cậu kia vượt đèn đỏ, chú Tường đành quay về: “Thôi, của đi thay người.”'))),
                  dict(id='let', label='Thôi, coi như làm phúc', hint='Mất 17 xu tiền hàng', effects=dict(stock={'huong_duong': -1}, dirty=4), good=None,
                       outcome='Bạn thở dài dọn bốn cái cốc. Cô Hoa lắc đầu: “Khách lạ thì thu tiền luôn cháu ạ.”')],
         default='let'),
    dict(id='drunk', title='Ông khách say lè nhè', emoji='🍺', npc=5, min_day=4, tone='tense', at='between', weight=2,
         mods=('football', 'normal', 'cool'),
         text='Một ông mặt đỏ gay từ quán nhậu bên kia đường sang, đập bàn đòi “trà pha rượu”, lè nhè trêu cô Hoa.',
         options=[dict(id='calm', label='Mời cốc trà nóng đặc, gọi người nhà ra đón', hint='Mềm mỏng, mất chút thời gian',
                       effects=dict(patience=-4, xp=4), good=True,
                       outcome='Uống cốc trà nóng, ông ấy dịu hẳn. Vợ ông ra đón, cúi đầu xin lỗi cả quán.'),
                  dict(id='shoo', label='Nói thẳng mời ông đi chỗ khác', hint='Nhanh gọn, nhưng dễ to chuyện', effects={},
                       luck=dict(p=0.5, win=dict(effects={}, good=None, outcome='Ông ấy lầm bầm rồi loạng choạng đi về.'),
                                 lose=dict(effects=dict(broke_stool=1), good=False,
                                           outcome='Ông ấy nổi khùng đá văng một cái ghế nhựa, gãy cả chân ghế rồi mới chịu đi.'))),
                  dict(id='serve', label='Chiều khách, rót thêm cho ông ấy ngồi', hint='Yên chuyện trước mắt',
                       effects=dict(review=[2, 'Quán để người say ngồi trêu phụ nữ cả buổi. Khó chịu!']), good=False,
                       outcome='Ông ấy ngồi lì cả tiếng, trêu hết người này đến người khác. Cô Hoa bỏ về giữa chừng.')],
         default='serve'),
    dict(id='watch_bike', title='Trông hộ xe', emoji='🛵', npc=6, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Anh Hùng dựng xe sát bàn: “Trông hộ anh cái xe với thùng hàng nhé, anh chạy lên tầng năm giao đơn, năm phút thôi!”',
         options=[dict(id='move', label='Dắt xe vào sát gốc bàng rồi trông', hint='Không vướng lối đi, dễ để mắt', effects=dict(xp=4, money=2), good=True,
                       outcome='Anh Hùng xuống, thấy xe gọn gàng dưới gốc cây: “Chu đáo quá!” Dúi cho 2 xu mua kẹo.'),
                  dict(id='yes', label='Ừ, anh cứ đi', hint='Xe đứng giữa lối đi', effects={},
                       luck=dict(p=0.7, win=dict(effects=dict(money=2), good=True, outcome='Năm phút sau anh Hùng xuống, cảm ơn rối rít, dúi 2 xu.'),
                                 lose=dict(effects=dict(patience=-5), good=None,
                                           outcome='Một bà cụ đi qua vướng xe suýt ngã. Bạn vội chạy ra đỡ, xin lỗi mãi.'))),
                  dict(id='no', label='Em đang đông khách, anh thông cảm', hint='', effects={}, good=None,
                       outcome='Anh Hùng gật đầu, dắt xe đi gửi chỗ khác.')],
         default='no'),
    dict(id='watch_kid', title='Trông hộ đứa bé', emoji='👶', npc=5, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Cô Hoa dắt thằng cháu năm tuổi sang: “Trông hộ cô nửa tiếng, cô chạy ra chợ lấy gạo nếp. Nó ngoan lắm!”',
         options=[dict(id='seat', label='Cho bé ngồi ghế trong cùng, bóc cho gói bánh quy', hint='Mất một gói bánh',
                       effects=dict(stock={'banh_quy': -1}, xp=4), good=True,
                       outcome='Bé ngồi ngoan ăn bánh, xem ông Khang đánh cờ. Cô Hoa về cảm ơn mãi.'),
                  dict(id='yes', label='Vâng, cô cứ để đấy', hint='Vừa bán vừa trông', effects={},
                       luck=dict(p=0.5, win=dict(effects={}, good=True, outcome='Bé chơi với con mèo nhà bên, không sao cả.'),
                                 lose=dict(effects=dict(patience=-8), good=False,
                                           outcome='Đang rót trà thì bé chạy ra mép đường nhặt bóng. Bạn lao theo bế vào, tim đập thình thịch, khách chờ cả lượt.'))),
                  dict(id='no', label='Khéo từ chối vì đang đông khách', hint='', effects={}, good=None,
                       outcome='Cô Hoa hơi phụng phịu nhưng hiểu, bế cháu đi chợ cùng.')],
         default='yes'),
    dict(id='gossip_mart', title='Cô Hoa có tin nóng', emoji='🗣️', npc=5, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='Cô Hoa ghé sớm, hạ giọng: “Biết gì chưa? Siêu thị mini Mây Mart sắp mở ngay cạnh tạp hoá cô Ba. Khổ thân cô Ba…”',
         options=[dict(id='listen', label='Rót cốc trà, nghe cô kể', hint='', effects=dict(xp=3), good=True,
                       outcome='Cô Hoa kể một mạch. Bạn nghe, gật gù, không thêm bớt gì.'),
                  dict(id='cheer', label='Rủ cả phố mua ủng hộ cô Ba', hint='', effects=dict(xp=4), good=True,
                       outcome='Cô Hoa gật gù: “Ừ, mớ rau bó hành cũng nên mua chỗ quen.” Chiều ấy cô rủ cả hội chợ sang tạp hoá cô Ba.'),
                  dict(id='spread', label='Kể lại cho từng khách nghe cho vui', hint='Chuyện càng kể càng to',
                       effects=dict(review=[3, 'Ngồi uống trà mà toàn nghe chuyện nhà người khác, mệt.']), good=False,
                       outcome='Đến chiều, tin đồn đã thành “cô Ba sắp dẹp tiệm”. Cô Ba nghe được, buồn lắm.')],
         default='listen'),
    dict(id='gossip_noodle', title='Chuyện quán mì đầu phố', emoji='🍜', npc=5, min_day=3, tone='gentle', at='any', weight=1, mods=None,
         text='Cô Hoa: “Quán mì cay Mây đầu phố vừa bị đoàn kiểm tra vệ sinh ghé. Sổ sách đủ cả nên người ta chỉ nhắc nhở thôi.”',
         options=[dict(id='check', label='Tự thay chậu nước rửa cốc của quán mình', hint='Mất một lượt', effects=dict(clean=1), good=True,
                       outcome='Bạn thay chậu nước mới, tráng lại mấy cái cốc. Bà Lựu gật gù: “Phải thế.”'),
                  dict(id='listen', label='Nghe cho biết', hint='', effects={}, good=None, outcome='Cô Hoa kể xong lại sang chuyện nhà số 9.')],
         default='listen'),
    dict(id='gossip_delivery', title='Anh Hùng bị bom hàng', emoji='📦', npc=6, min_day=3, tone='gentle', at='between', weight=1, mods=None,
         text='Anh Hùng ngồi thừ: “Hôm nay bên Giao nhanh Mây Chiều anh bị bom ba đơn thu hộ. Tiền ứng ra chưa biết đòi ai.”',
         options=[dict(id='treat', label='Mời anh cốc trà, không lấy tiền', hint='Mất 3 xu tiền trà', effects=dict(money=-3, xp=3), good=True,
                       outcome='Anh Hùng uống một hơi cạn cốc: “Có cốc trà mát là thấy đời dễ thở hơn.”'),
                  dict(id='advice', label='Nhắc anh gọi xác nhận khách trước khi chạy', hint='', effects=dict(xp=3), good=True,
                       outcome='Anh Hùng gật gù: “Ừ, gọi trước mất một phút mà đỡ mất cả buổi.”'),
                  dict(id='shrug', label='Ừ, nghề nào chẳng có lúc xui', hint='', effects={}, good=None,
                       outcome='Anh Hùng cười méo xệch rồi lại lên xe.')],
         default='shrug'),
    dict(id='bet', title='Rủ cá độ trận tối nay', emoji='⚽', npc=1, min_day=3, tone='tense', at='between', weight=3, mods=('football',),
         text='Bàn bên rủ rê: “Đặt cửa đội nhà thắng đi, 20 ăn 40!” Chú Tường cũng đang hăng máu.',
         options=[dict(id='no', label='Cười trừ, không chơi', hint='', effects={}, good=True, outcome='Bạn chỉ rót trà. Xem bóng cho vui là đủ.'),
                  dict(id='stop', label='Khuyên chú Tường đừng chơi', hint='', effects=dict(xp=4), good=True,
                       outcome='Chú Tường gãi đầu: “Ừ, tiền đấy để đóng học cho con.” Chú cất ví vào túi.'),
                  dict(id='yes', label='Đặt 20 xu cho vui', hint='Cờ bạc là bác thằng bần', effects={},
                       luck=dict(p=0.4, win=dict(effects=dict(money=20), good=False,
                                                 outcome='Đội nhà thắng. Bạn được 20 xu, nhưng bà Lựu nghe chuyện thì lắc đầu mãi.'),
                                 lose=dict(effects=dict(money=-20), good=False,
                                           outcome='Đội nhà thua. Mất 20 xu, bằng tiền bán gần bảy cốc trà.')))],
         default='no'),
    dict(id='ward_notice', title='Tổ trưởng dân phố nhắc', emoji='📢', npc=0, min_day=3, tone='gentle', at='open', weight=2, mods=None,
         text='Bác tổ trưởng dân phố ghé: “Mấy hôm này phường ra quân dẹp vỉa hè đấy. Cháu kê ghế gọn vào, đừng lấn ra lòng đường nhé.”',
         options=[dict(id='thank', label='Cảm ơn bác, kê ghế gọn sát gốc cây', hint='', effects=dict(xp=3, mark='warned'), good=True,
                       outcome='Bác tổ trưởng gật đầu, xin cốc trà đá rồi đi báo tiếp các nhà.'),
                  dict(id='shrug', label='“Ai chẳng bày ra thế hả bác”', hint='', effects={}, good=False,
                       outcome='Bác tổ trưởng lắc đầu: “Tùy cháu, bị phạt thì đừng kêu.”')],
         default='thank'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='TD-S01', title='Cu Tủn mua thuốc lá cho bố', npc=7, tone='tense', min_day=1,
         opening='Cu Tủn chìa tờ tiền: “Cô ơi, bố cháu bảo mua ba điếu thuốc.” Ông bố đứng tít đầu ngõ, vẫy vẫy.',
         swap='Bạn là Cu Tủn, học lớp 5, bị bố sai ra quán mua thuốc lá.',
         facts=[dict(id='age', title='Tuổi của khách', source='Cu Tủn', text='Cu Tủn mới mười tuổi. Luật không cho bán thuốc lá cho người dưới 18 tuổi.'),
                dict(id='dad', title='Ông bố ở đầu ngõ', source='Nhìn ra đầu ngõ', text='Bố Cu Tủn đứng cách quán chừng hai chục bước chân, đang nói điện thoại.'),
                dict(id='habit', title='Chuyện hằng ngày', source='Cô Hoa', text='Cô Hoa bảo: “Ông ấy sai thằng bé mua suốt, quán nào cũng bán cho.”')],
         options=[dict(id='refuse_kind', label='Từ chối nhẹ nhàng, mời bố cháu ra tự mua', requires=['age', 'dad'], quality='good', stars=5,
                       review='Quán không bán thuốc cho con tôi, còn nói khéo. Tôi thấy ngượng, mà phục.',
                       outcome='Bố Cu Tủn đi ra, gãi đầu: “Ừ, chú sai rồi.” Ông tự mua, còn hứa sẽ bớt hút.',
                       perspectives=[dict(who='Cu Tủn', emoji='🧒', text='Cháu cứ tưởng mua hộ thì không sao.'),
                                     dict(who='Bố Cu Tủn', emoji='👨', text='Người ta từ chối con mình, mình mới giật mình nghĩ lại.'),
                                     dict(who='Bà Lựu', emoji='👵', text='Bán cho trẻ con một điếu là mất cả cái tiếng ba mươi năm.')]),
                  dict(id='refuse', label='“Không bán cho trẻ con!” rồi quay đi', requires=['age'], quality='ok', stars=4,
                       review='Đúng là không nên bán, nhưng quát thằng bé làm gì.',
                       outcome='Cu Tủn mếu máo chạy về. Bố cháu phải tự ra mua, mặt hơi khó chịu.',
                       perspectives=[dict(who='Cu Tủn', emoji='😢', text='Cháu có làm gì sai đâu…'),
                                     dict(who='Cô Hoa', emoji='🗣️', text='Đúng luật, nhưng nói với trẻ con thì nhẹ nhàng thôi.')]),
                  dict(id='sell', label='Bán luôn, bố nó sai mà', quality='bad', stars=1,
                       review='Quán bán thuốc lá cho trẻ con. Không chấp nhận được!',
                       outcome='Mẹ Cu Tủn biết chuyện, sang tận quán nói to cả phố nghe.',
                       perspectives=[dict(who='Mẹ Cu Tủn', emoji='😠', text='Hôm nay mua hộ, mai nó hút thử thì sao?'),
                                     dict(who='Bà Lựu', emoji='👵', text='Vài xu mà mang tiếng cả đời.')])],
         lesson='Người mua là trẻ con thì không bán thuốc lá, dù ai sai đi mua; từ chối cho khéo để người lớn tự nghĩ lại.'),
    dict(id='TD-S02', title='Chú Tường cãi sổ', npc=1, tone='tense', min_day=2,
         opening='Đến hẹn trả sổ, chú Tường lật trang: “Hôm ấy chú uống có một cốc, sao ghi những ba cốc?”',
         facts=[dict(id='book', title='Dòng trong sổ', source='Sổ ghi nợ', text='Dòng ghi: “2 trà đá, 1 gói lạc — 11 xu”, kèm ngày.'),
                dict(id='friend', title='Hôm đó ngồi cùng ai', source='Ông Khang', text='Ông Khang nhớ hôm đó chú Tường khao bạn xe ôm một cốc.'),
                dict(id='habit', title='Thói quen ghi sổ', source='Bà Lựu', text='Bà Lựu dặn: ghi từng món, có ngày, có tên người ngồi cùng.')],
         options=[dict(id='show', label='Cho chú xem dòng sổ, nhắc hôm ấy chú khao bạn', requires=['book', 'friend'], quality='good', stars=5,
                       review='Sổ sách rõ ràng từng món, tôi nhớ nhầm thật. Quán làm ăn tử tế.',
                       outcome='Chú Tường vỗ trán: “À đúng rồi, khao thằng Bảy!” Chú trả đủ, còn cười xòa.',
                       perspectives=[dict(who='Chú Tường', emoji='🛵', text='Có sổ có ngày, chú cãi làm gì nữa.'),
                                     dict(who='Ông Khang', emoji='♟️', text='Ghi sổ kỹ thì không ai mất lòng ai.')]),
                  dict(id='drop', label='Thôi bỏ dòng đó cho chú', quality='ok', stars=4,
                       review='Quán dễ tính, nhưng cứ thế thì lỗ mất.',
                       outcome='Chú Tường vui, quán mất 11 xu. Bà Lựu nghe chuyện chỉ thở dài.',
                       perspectives=[dict(who='Chú Tường', emoji='🛵', text='Được cái dễ tính!'),
                                     dict(who='Bà Lựu', emoji='👵', text='Dễ tính một lần thì lần sau ai cũng cãi sổ.')]),
                  dict(id='argue', label='Cãi to: “Sổ ghi thế thì trả thế!”', quality='bad', stars=2,
                       review='Có mấy xu mà quát khách quen giữa phố.',
                       outcome='Chú Tường trả tiền, mặt nặng như chì. Mấy hôm sau chú ngồi quán khác.',
                       perspectives=[dict(who='Chú Tường', emoji='😤', text='Hai mươi năm uống trà ở đây mà bị quát.'),
                                     dict(who='Cô Hoa', emoji='🗣️', text='Đúng mà nói to thì cũng thành sai.')])],
         lesson='Sổ ghi nợ phải có ngày, có món, có số; khi khách thắc mắc thì cùng xem sổ, nói nhỏ nhẹ.'),
    dict(id='TD-S03', title='Trật tự đô thị ghé phố', npc=0, tone='tense', min_day=2,
         opening='Xe trật tự đô thị dừng ở đầu phố, loa phát: “Đề nghị các hộ kinh doanh không lấn chiếm vỉa hè, lòng đường!”',
         facts=[dict(id='line', title='Vạch sơn vỉa hè', source='Nhìn xuống chân', text='Phường kẻ vạch: được bày trong 1,5 mét sát tường, chừa lối cho người đi bộ.'),
                dict(id='stools', title='Ghế đang bày', source='Quán', text='Hai cái ghế đang thò ra mép lòng đường.'),
                dict(id='rule', title='Mức phạt', source='Bác tổ trưởng', text='Lấn chiếm lòng đường bị lập biên bản, ghế bàn có thể bị thu.')],
         options=[dict(id='tidy', label='Dẹp gọn vào trong vạch, chừa lối đi', requires=['line', 'stools'], quality='good', stars=5,
                       review='Quán gọn gàng, đi bộ qua không phải lách.',
                       outcome='Tổ công tác đi qua, gật đầu. Quán bán tiếp như thường.',
                       perspectives=[dict(who='Cán bộ phường', emoji='👮', text='Hộ nào cũng thế này thì phố đẹp.'),
                                     dict(who='Người đi bộ', emoji='🚶', text='Không phải đi xuống lòng đường nữa.')]),
                  dict(id='hide', label='Ôm hết ghế chạy vào ngõ, lát họ đi lại bày ra', quality='ok',
                       outcome='Thoát được lần này, nhưng chiều lại bày ra như cũ.',
                       perspectives=[dict(who='Bà Lựu', emoji='👵', text='Chạy mãi thì mệt lắm cháu ạ.'),
                                     dict(who='Cán bộ phường', emoji='👮', text='Lần sau chúng tôi đi lại đúng giờ ấy.')]),
                  dict(id='argue', label='Cãi: “Cả phố bày, sao bắt mỗi tôi?”', quality='bad', cost=20, stars=2,
                       review='Chủ quán cãi nhau với phường ngay trước mặt khách.',
                       outcome='Bị lập biên bản, phạt 20 xu và thu hai cái ghế.',
                       perspectives=[dict(who='Cán bộ phường', emoji='👮', text='Làm đúng thì không phải cãi.'),
                                     dict(who='Khách', emoji='😬', text='Đang uống dở phải đứng dậy nhường ghế.')])],
         lesson='Bày quán trong phần vỉa hè được phép, chừa lối cho người đi bộ; gọn gàng thì chẳng sợ ai.'),
    dict(id='TD-S04', title='Ông Khang ngồi cả chiều một cốc', npc=2, tone='gentle', min_day=2,
         opening='Giờ tan tầm, khách đứng chờ ghế. Ông Khang vẫn ngồi với cốc trà nóng từ trưa, bàn cờ bày kín ghế bên cạnh.',
         facts=[dict(id='regular', title='Khách quen', source='Bà Lựu', text='Ông Khang uống ở quán mười mấy năm, tết nào cũng mừng tuổi bà Lựu.'),
                dict(id='crowd', title='Khách đang chờ', source='Quầy', text='Ba anh văn phòng đứng chờ, chỉ thiếu đúng hai cái ghế.'),
                dict(id='stool', title='Ghế dự phòng', source='Góc tường', text='Sau gốc cây còn hai cái ghế gấp chưa bày.')],
         options=[dict(id='extra', label='Bày thêm ghế dự phòng, để ông ngồi yên', requires=['crowd', 'stool'], quality='good', stars=5,
                       review='Đông mà quán vẫn xoay xở được chỗ cho mọi người.',
                       outcome='Ba anh văn phòng có ghế ngồi. Ông Khang không hề biết mình suýt bị mời đứng dậy.',
                       perspectives=[dict(who='Ông Khang', emoji='♟️', text='Quán này ngồi yên tâm như ở nhà.'),
                                     dict(who='Anh Đạt', emoji='💼', text='Chờ có một phút là có ghế.')]),
                  dict(id='ask_move', label='Nhờ ông dẹp bàn cờ gọn sang một ghế', requires=['regular'], quality='ok', stars=4,
                       review='Hơi phiền, nhưng hiểu cho quán lúc đông.',
                       outcome='Ông Khang lẩm bẩm nhưng dẹp gọn. Khách mới có chỗ ngồi.',
                       perspectives=[dict(who='Ông Khang', emoji='😑', text='Thì dẹp, đang thế cờ hay…'),
                                     dict(who='Khách mới', emoji='🙂', text='Cảm ơn ông cụ.')]),
                  dict(id='kick', label='Nói thẳng: “Ông uống xong rồi thì nhường ghế”', quality='bad', stars=2,
                       review='Khách quen mười mấy năm mà bị đuổi khéo như thế.',
                       outcome='Ông Khang đứng dậy về luôn. Mấy hôm sau không thấy ông ra quán.',
                       perspectives=[dict(who='Ông Khang', emoji='😠', text='Một cốc hay mười cốc thì cũng là khách.'),
                                     dict(who='Bà Lựu', emoji='👵', text='Quán vỉa hè sống nhờ khách quen, cháu ạ.')])],
         lesson='Quán vỉa hè sống nhờ khách quen: tìm cách xoay chỗ trước khi mời ai đứng dậy.'),
    dict(id='TD-S05', title='Người say gây gổ', npc=5, tone='tense', min_day=3,
         opening='Một ông say từ quán nhậu sang, đập bàn đòi uống chịu, nói to với cô Hoa.',
         facts=[dict(id='drunk', title='Tình trạng', source='Nhìn qua', text='Ông ấy đi không vững, nói lè nhè, mùi rượu nồng.'),
                dict(id='home', title='Nhà ông ấy', source='Chú Tường', text='Chú Tường biết nhà, vợ ông ấy bán tạp hoá cuối ngõ.'),
                dict(id='people', title='Xung quanh', source='Quán', text='Có mấy học sinh đang ngồi uống trà chanh.')],
         options=[dict(id='calm', label='Mời cốc trà nóng, nhờ chú Tường gọi người nhà', requires=['drunk', 'home'], quality='good', stars=5,
                       review='Quán xử lý người say rất khéo, không ai bị làm sao.',
                       outcome='Vợ ông ấy ra đón. Hôm sau ông sang xin lỗi, trả tiền cốc trà.',
                       perspectives=[dict(who='Cô Hoa', emoji='🗣️', text='Không cãi nhau câu nào mà êm chuyện.'),
                                     dict(who='Linh', emoji='🎒', text='Tụi em sợ lắm, may quán bình tĩnh.')]),
                  dict(id='shout', label='Quát cho ông ấy đi', quality='ok', stars=3,
                       review='Đuổi người say là đúng, nhưng to tiếng quá làm cả quán sợ.',
                       outcome='Ông ấy chửi đổng một hồi rồi mới đi.',
                       perspectives=[dict(who='Linh', emoji='😨', text='Hai người quát nhau, tụi em chạy về luôn.'),
                                     dict(who='Chú Tường', emoji='🛵', text='Với người say, to tiếng chỉ thêm to chuyện.')]),
                  dict(id='ignore', label='Kệ ông ấy, lo bán hàng', quality='bad', stars=2,
                       review='Để người say trêu phụ nữ, học sinh mà quán không nói gì.',
                       outcome='Ông ấy ngồi lì cả tiếng, khách lần lượt bỏ về.',
                       perspectives=[dict(who='Cô Hoa', emoji='😣', text='Cháu phải lên tiếng chứ.'),
                                     dict(who='Linh', emoji='🎒', text='Chắc lâu lâu tụi em mới dám ra.')])],
         lesson='Với người say: giữ bình tĩnh, giữ an toàn cho khách, tìm người nhà thay vì to tiếng.'),
    dict(id='TD-S06', title='Anh Hùng gửi tiền thu hộ', npc=6, tone='gentle', min_day=3,
         opening='Anh Hùng dúi cái túi: “Em giữ hộ anh tiền thu hộ, anh chạy đơn gần đây. Đừng mở ra nhé!”',
         facts=[dict(id='amount', title='Trong túi', source='Anh Hùng', text='Anh Hùng bảo trong túi có 180 xu tiền thu hộ của khách.'),
                dict(id='busy', title='Quán đang đông', source='Quầy', text='Quán đang đông, bàn nào cũng có người.'),
                dict(id='rule', title='Lời bà Lựu', source='Bà Lựu', text='Bà Lựu dặn: tiền của người khác thì đếm trước mặt họ rồi mới giữ.')],
         options=[dict(id='count', label='Đếm trước mặt anh, ghi giấy, cất vào ngăn tủ khóa', requires=['amount', 'rule'], quality='good', stars=5,
                       review='Gửi tiền ở quán mà được đếm, ghi giấy đàng hoàng. Yên tâm tuyệt đối.',
                       outcome='Anh Hùng quay lại lấy đủ 180 xu, cảm ơn rối rít.',
                       perspectives=[dict(who='Anh Hùng', emoji='📦', text='Có tờ giấy ghi số, anh yên tâm chạy.'),
                                     dict(who='Bà Lựu', emoji='👵', text='Giữ tiền cho người là giữ chữ tín.')]),
                  dict(id='keep', label='Ừ, để đấy em trông', quality='ok', stars=3,
                       review='Quán tốt bụng nhưng giữ tiền hơi tùy tiện.',
                       outcome='Không mất gì, nhưng anh Hùng về đếm lại mãi vẫn thấy lo.',
                       perspectives=[dict(who='Anh Hùng', emoji='😬', text='Không ai đếm, lỡ thiếu thì biết nói sao.'),
                                     dict(who='Bà Lựu', emoji='👵', text='Nhận giữ tiền thì phải đếm, không thì đừng nhận.')]),
                  dict(id='no', label='Từ chối: quán không giữ tiền hộ', requires=['busy'], quality='ok',
                       outcome='Anh Hùng hiểu, mang túi tiền theo người.',
                       perspectives=[dict(who='Anh Hùng', emoji='🙂', text='Đúng thôi, đông thế này ai trông cho xuể.'),
                                     dict(who='Cô Hoa', emoji='🗣️', text='Thà từ chối còn hơn nhận rồi để mất.')])],
         lesson='Giữ tiền hộ người khác thì đếm trước mặt, ghi rõ số; không kham nổi thì từ chối.'),
]


# ================================================================ small helpers
def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _who(t: dict) -> str:
    return PEOPLE[_npc_index(t)][0] if 0 <= _npc_index(t) < len(PEOPLE) else 'Khách'


def _price(c: dict, key: str) -> int:
    return max(1, int(kit.price(c, key, PRICES[key])))


def _label(key: str) -> str:
    if key in DRINK:
        return DRINK[key]['name']
    return ITEM[key]['name'] if key in ITEM else key


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _list_text(counts: dict) -> str:
    parts = []
    for k, q in counts.items():
        if q <= 0:
            continue
        unit = 'cốc' if k in DRINK else ITEM[k]['unit']
        parts.append(f'{q} {unit} {_lower(_label(k))}' if unit != 'cốc' else f'{q} {_lower(_label(k))}')
    return ', '.join(parts)


# ================================================================ tasks
def _kind(day: int, slot: int, mod: str) -> str:
    if slot == 0:
        return 'setup'
    if day == 1:
        return {1: 'glass', 2: 'tab'}.get(slot, 'glass')
    if slot == 1 and day % 3 == 0:
        return 'settle'
    if mod == 'football' and slot == 2:
        return 'match'
    deck = ['glass', 'glass', 'tab', 'glass', 'kid', 'glass']
    kit.rng(ID, 'deck', day).shuffle(deck)
    return deck[(slot - 1) % len(deck)]


def _pick(day: int, slot: int, kind: str, mod: str) -> tuple:
    if day == 1 and slot == 1:
        return ORDERS[0]
    if day == 1 and slot == 2:
        return next(o for o in ORDERS if o[1] == 'tab')
    pool = [o for o in ORDERS if o[1] == kind and o[8] <= day and o[9] in (None, mod)]
    if kind == 'match' and not pool:
        pool = [o for o in ORDERS if o[1] == 'match']
    if not pool:
        pool = [o for o in ORDERS if o[1] == 'glass' and o[9] is None and o[8] <= day]
    weighted = [o for o in pool for _ in range(3 if o[9] else 1)]
    return weighted[kit.rng(ID, day, slot).randrange(len(weighted))]


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    kind = _kind(day, slot, mod)
    common = dict(gen=GEN, stage='prep', tray=[], snacks={}, refused=False, price=None, owe=None, cost=0, cash=None,
                  start_turn=None, story=None, bill=None, dispute=None, written=None)
    if kind == 'setup':
        rain = mod == 'rain'
        spot = 'hien' if rain else 'goc_bang'
        needs = dict(setup=True, spot=spot, umbrella=spot != 'hien', stools=[STOOLS_MIN, SPOTS[spot]['cap']], heat=mod == 'heat',
                     note='Trời mưa: dọn vào mái hiên tiệm may cho khô.' if rain else
                     'Nắng to: nhớ dựng ô che thùng đá.' if mod == 'heat' else 'Bày dưới gốc bàng cho mát, gọn sát tường.')
        title = 'Dọn hàng ngày mưa' if rain else 'Dọn hàng đầu ngày'
        opening = ('Bà Lựu: “Mưa thế này thì dọn vào mái hiên, cháu nhé. Pha ấm chè, đập đá rồi hãy mở hàng.”' if rain else
                   'Bà Lựu: “Dọn hàng thôi cháu! Bày ghế, dựng ô, đặt thùng đá, pha ấm chè, đập đá.”')
        return kit.base_task(ID, day, slot, serial, 0, title, opening, kind='setup', needs=needs, **common)
    if kind == 'settle':
        needs = dict(settle=True, note='Chú Tường ghé trả sổ theo hẹn. Đọc sổ cho chú, đúng dòng nào thu dòng đó.')
        return kit.base_task(ID, day, slot, serial, TAB_NPC, 'Chú Tường trả sổ',
                             'Chú Tường rút ví: “Đến hẹn rồi, sổ chú hết bao nhiêu cháu?”', kind='settle', needs=needs, **common)
    npc, k, title, opening, drinks, snacks, seats, note, _, _ = _pick(day, slot, kind, mod)
    needs = dict(drinks=dict(drinks), snacks=dict(snacks), seats=seats, pay='tab' if k == 'tab' else 'cash', kid=k == 'kid', note=note)
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind=k, needs=needs, **common)


FIXED = ('needs',)


def on_task(s: dict, c: dict, t: dict) -> None:
    d = _data(c)
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'
    elif t['kind'] == 'settle':
        _open_bill(d, t)


def _open_bill(d: dict, t: dict) -> None:
    lines = [dict(x) for x in d['tab'] if x['npc'] == TAB_NPC]
    t['bill'] = dict(lines=lines, total=sum(x['amount'] for x in lines))
    t['dispute'] = None
    if not lines:
        return
    wrong = next((i for i, x in enumerate(lines) if x['amount'] > x['due']), None)
    if wrong is not None:
        t['dispute'] = dict(line=lines[wrong]['id'], wrong=True, state='open')
    elif _hash('td-dispute', t['id']) % 100 < 40:
        i = _hash('td-dispute-line', t['id']) % len(lines)
        t['dispute'] = dict(line=lines[i]['id'], wrong=False, state='open')


# ================================================================ the stall's data
def _fresh_stall(day: int) -> dict:
    return dict(day=day, spot=None, stools=0, umbrella=False, box=False, open=False, packed=False)


def _fresh_today(day: int) -> dict:
    return dict(day=day, glasses=0, snacks=0, melted=0, weak=0, refused=0, fine=0, lost_stools=0)


def initial() -> dict:
    return dict(v=1, intro=False, stall=_fresh_stall(0), thermos=dict(tea=0, strength=0, turn=0),
                ice=dict(portions=0, turn=0, acc=0), glasses=dict(clean=GLASSES_START, dirty=0, grimy=0), basin=0,
                tab=[], tab_seq=0, owned=dict(stools=STOOLS_START, glasses=GLASSES_START, umbrella=1, banner=False, chess=False),
                regulars={}, arc=dict(seen=[], due=None), sweep=None, sweeps=[], ice_plan=3, today=_fresh_today(0),
                stats=dict(glasses=0, snacks=0, fines=0, sweeps_ok=0, refused_kid=0, underbooked=0, overbooked=0, weak=0),
                desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k, v in base['stats'].items():
        d['stats'].setdefault(k, v)
    for k, v in base['owned'].items():
        d['owned'].setdefault(k, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    return d


# ---------------------------------------------------------------- ice and tea over time
def _shaded(d: dict) -> bool:
    st = d['stall']
    spot = SPOTS.get(st['spot'] or 'goc_bang')
    return spot['shade'] or (st['umbrella'] and d['owned']['umbrella'] >= 2)


def melt_rate(c: dict, d: dict) -> int:
    """Crushed ice lost per turn, in twelfths of a portion."""
    st = d['stall']
    base = 3 if _shaded(d) else 5
    if st['umbrella'] and SPOTS.get(st['spot'] or 'goc_bang')['shade']:
        base = 2 if d['owned']['umbrella'] >= 2 else 3
    mod = mod_of(c['day'])['id']
    if mod == 'heat':
        base *= 2
    elif mod in ('cool', 'rain'):
        base = max(1, base * 2 // 3)
    return base


def _melt_view(c: dict, d: dict) -> tuple[int, int, int]:
    """(portions left, acc, lost) at the current turn, without changing anything."""
    ice = d['ice']
    turns = max(0, c['turn'] - ice['turn'])
    if not turns or not ice['portions']:
        return ice['portions'], (ice['acc'] if ice['portions'] else 0), 0
    acc = ice['acc'] + melt_rate(c, d) * turns
    lost = min(ice['portions'], acc // 12)
    left = ice['portions'] - lost
    return left, (acc % 12 if left else 0), lost


def _melt(c: dict, d: dict) -> int:
    left, acc, lost = _melt_view(c, d)
    d['ice'].update(portions=left, acc=acc, turn=c['turn'])
    if lost:
        d['today']['melted'] += lost
    return lost


def _stale_after(c: dict) -> int:
    return STALE_HEAT if mod_of(c['day'])['id'] == 'heat' else STALE_TURNS


def _stale(c: dict, d: dict) -> bool:
    th = d['thermos']
    return th['tea'] > 0 and c['turn'] - th['turn'] > _stale_after(c)


# ================================================================ the actions
FREE = ('td_intro', 'td_arc', 'td_ice_plan', 'td_buy')
NO_TICK = ('td_intro', 'td_short', 'td_arc', 'td_ice_plan', 'td_buy', 'td_pack', 'td_sweep_end', 'td_snack', 'td_takeback', 'td_refuse',
           'td_pay', 'td_book', 'td_bill', 'td_dispute', 'td_spot', 'td_stools', 'td_umbrella', 'td_box', 'td_desk')
PHYSICAL = ('td_pour', 'td_wash', 'td_crush', 'td_brew', 'td_basin', 'td_unpack')
SWEEP_OK = ('td_pack', 'td_sweep_end', 'td_intro', 'td_arc', 'td_ice_plan')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    _melt(c, d)
    if name == 'td_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Bà Lựu đang chờ ở gốc bàng.')
    if name == 'td_arc':
        return _arc_seen(d)
    if name == 'td_ice_plan':
        d['ice_plan'] = kit.integer(p.get('n'), 0, ICE_PLAN_MAX)
        return dict(message=f'Đã dặn anh Tuấn xe đá: mỗi sáng thả {d["ice_plan"]} cây đá.' if d['ice_plan'] else
                    'Đã dặn anh Tuấn xe đá: sáng mai khỏi thả đá.')
    if name == 'td_buy':
        return _buy(s, c, d, p)
    sw = d['sweep']
    if sw and sw['stage'] == 'coming' and name not in SWEEP_OK:
        if kit.now() > sw['start'] + sw['limit']:
            _sweep_resolve(s, c, d)
        else:
            kit.need(False, 'Trật tự đô thị đang tới! Dẹp ghế, gấp ô trước đã.', 'sweep')
    desk = d['desk']
    if name == 'td_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'), hook=_desk_hook)
    if name not in ('td_pack', 'td_sweep_end'):
        kit.desk_block(desk, 'Có chuyện ở quán, quyết xong rồi làm tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở quán trà.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    _arc_tick(c, d)
    if _sweep_tick(s, c, d):
        result['message'] = (result.get('message', '') + ' 🚨 Xe trật tự đô thị đang tới đầu phố! Dẹp ghế, gấp ô ngay!').strip()
        result['surprise'] = True
        return
    if d['sweep'] and d['sweep']['stage'] == 'coming':
        return
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc quán trà.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    return t


# ---------------------------------------------------------------- setting up
def _spot(s, c, d, p):
    spot = kit.one_of(p.get('spot'), SPOTS, 'Chỗ bày quán không hợp lệ.')
    st = d['stall']
    st['spot'] = spot
    st['stools'] = min(st['stools'], d['owned']['stools'])
    x = SPOTS[spot]
    warn = ' ⚠️ Chỗ này lấn ra lòng đường, phường mà đi qua là bị phạt.' if not x['legal'] else ''
    return dict(message=f'{x["emoji"]} Bày quán ở {_lower(x["name"])}. {x["note"]}{warn}')


def _stools(s, c, d, p):
    n = kit.integer(p.get('n'), 0, STOOLS_MAX)
    st = d['stall']
    kit.need(st['spot'], 'Chọn chỗ bày quán trước đã.')
    kit.need(n <= d['owned']['stools'], f'Quán chỉ có {d["owned"]["stools"]} cái ghế.')
    st['stools'] = n
    cap = SPOTS[st['spot']]['cap']
    warn = f' ⚠️ Chỗ này chỉ vừa {cap} ghế, ghế thừa sẽ tràn ra lối đi.' if n > cap else ''
    return dict(message=f'🪑 Đã bày {n} ghế nhựa.{warn}')


def _umbrella(s, c, d, p):
    up = p.get('up')
    kit.need(type(up) is bool, 'Dựng hay gấp ô?')
    d['stall']['umbrella'] = up
    return dict(message='⛱️ Đã dựng ô.' if up else '⛱️ Đã gấp ô lại.')


def _box(s, c, d, p):
    kit.need(d['stall']['spot'], 'Chọn chỗ bày quán trước đã.')
    d['stall']['box'] = True
    return dict(message='🧊 Thùng đá đã đặt chỗ râm, nắp đậy kín.')


def _open(s, c, d, p):
    t = _task(c, p, ('setup',))
    st, n = d['stall'], t['needs']
    kit.need(st['spot'], 'Chọn chỗ bày quán trước đã.')
    kit.need(st['stools'] >= STOOLS_MIN, f'Bày ít nhất {STOOLS_MIN} ghế rồi mới mở hàng.')
    kit.need(st['box'], 'Đặt thùng đá vào chỗ râm trước đã.')
    spot = SPOTS[st['spot']]
    if not spot['legal']:
        t['mistakes'] += 1
        cq.slip(t, 'road', 2, 'Bày quán tràn ra tận lòng đường, xe máy phải lách. Phường đi qua là phạt đấy cháu.', 'bày lấn lòng đường')
    elif st['spot'] != n['spot']:
        t['mistakes'] += 1
        cq.slip(t, 'rain_spot' if n['spot'] == 'hien' else 'spot', 1,
                'Mưa thế này mà không dọn vào mái hiên, ghế ướt hết.' if n['spot'] == 'hien' else 'Chỗ này nắng quá, gốc bàng mát hơn nhiều.',
                'chọn chỗ chưa hợp')
    if n['umbrella'] and not st['umbrella'] and st['spot'] != 'hien':
        t['mistakes'] += 1
        cq.slip(t, 'no_umbrella', 2 if n['heat'] else 1, 'Nắng thế mà không dựng ô, đá tan hết, khách ngồi chói mắt.', 'quên dựng ô')
    if st['stools'] > spot['cap']:
        t['mistakes'] += 1
        cq.slip(t, 'crowd', 1, 'Ghế bày tràn ra lối đi, người đi bộ phải lách.', 'bày quá nhiều ghế')
    th = d['thermos']
    if not th['tea']:
        t['mistakes'] += 1
        cq.slip(t, 'no_tea', 1, 'Chưa pha chè đã mở hàng, khách đến lại phải chờ.', 'chưa pha chè')
    elif th['strength'] < WEAK:
        t['mistakes'] += 1
        cq.slip(t, 'weak_brew', 1, 'Ấm chè đầu ngày mà nhạt thế này thì các ông chê chết.', 'pha chè nhạt')
    if not d['ice']['portions']:
        t['mistakes'] += 1
        cq.slip(t, 'no_ice', 1, 'Thùng đá còn trống trơn, trà đá lấy gì mà mát?', 'chưa đập đá')
    st['open'] = True
    st['packed'] = False
    kit.start_work(t)
    ok = not cq.slips(t)
    line = 'Bà Lựu gật gù: “Gọn gàng, đâu ra đấy. Mở hàng thôi!”' if ok else 'Bà Lựu chép miệng: “Thôi, mở hàng đã, lần sau nhớ nhé.”'
    kit.complete(s, c, t, 0, f'Dọn hàng ở {_lower(spot["name"])}, {st["stools"]} ghế.')
    return dict(message=f'☀️ Mở hàng! {line}', celebrate=ok)


def _unpack(s, c, d, p):
    st = d['stall']
    kit.need(st['packed'], 'Quán đang bày rồi.')
    st['packed'] = False
    st['stools'] = min(d['owned']['stools'], max(STOOLS_MIN, st['stools'] or STOOLS_MIN))
    st['umbrella'] = True
    return dict(message=f'🪑 Bày lại quán: {st["stools"]} ghế, dựng ô. Khách lục tục ngồi lại.')


# ---------------------------------------------------------------- the thermos and the ice
def _brew(s, c, d, p):
    leaves = kit.integer(p.get('leaves'), 1, 3)
    kit.need(kit.stock(c, 'che') >= leaves, f'Chỉ còn {kit.stock(c, "che")} nắm chè. Mở kho nhập thêm nhé.')
    kit.take(c, 'che', leaves)
    th = d['thermos']
    old = th['tea']
    th.update(tea=THERMOS_MAX, strength=BREW[leaves], turn=c['turn'])
    taste = {1: 'nước chè vàng nhạt', 2: 'nước chè xanh vàng, thơm đúng vị', 3: 'nước chè đậm, chát nhẹ'}[leaves]
    return dict(message=f'🍵 Tráng ấm, bỏ {leaves} nắm chè, chế nước sôi: {taste}.' + (f' (Đổ bỏ {old} cốc chè cũ.)' if old else ''))


def _topup(s, c, d, p):
    th = d['thermos']
    kit.need(th['tea'] > 0, 'Bình hết sạch chè rồi, châm nước chỉ ra nước lã. Pha ấm mới nhé.')
    kit.need(th['tea'] < THERMOS_MAX, 'Bình còn đầy.')
    th['tea'] = min(THERMOS_MAX, th['tea'] + TOPUP)
    th['strength'] = max(10, th['strength'] - TOPUP_DROP)
    warn = ' ⚠️ Chè nhạt rồi đấy, khách quen sẽ chê.' if th['strength'] < WEAK else ''
    return dict(message=f'🫖 Châm thêm nước sôi: bình đầy hơn, chè nhạt đi.{warn}')


def _dump_tea(s, c, d, p):
    th = d['thermos']
    kit.need(th['tea'] > 0, 'Bình đang trống.')
    th.update(tea=0, strength=0)
    return dict(message='🚰 Đổ bỏ chè cũ, tráng bình sạch.')


def _crush(s, c, d, p):
    kit.need(d['stall']['box'], 'Đặt thùng đá ra trước đã.')
    ice = d['ice']
    kit.need(ice['portions'] <= ICE_MAX - BLOCK, 'Thùng đá còn đầy, đập thêm là tràn ra ngoài.')
    kit.need(kit.stock(c, 'da') > 0, 'Hết đá cây rồi! Chờ xe đá, hoặc mở kho gọi đá gấp.')
    kit.take(c, 'da', 1)
    ice['portions'] += BLOCK
    ice['turn'] = c['turn']
    return dict(message=f'🔨 Cốc cốc cốc! Đập xong một cây đá: thùng có {ice["portions"]} phần đá.')


# ---------------------------------------------------------------- glasses
def _wash(s, c, d, p):
    g = d['glasses']
    kit.need(g['dirty'] or g['grimy'], 'Không còn cốc bẩn nào.')
    n = min(WASH_BATCH, g['dirty'] + g['grimy'])
    if d['basin'] >= BASIN_MAX:
        from_dirty = min(g['dirty'], n)
        g['dirty'] -= from_dirty
        g['grimy'] += from_dirty
        return dict(message=f'🧽 Rửa {from_dirty} cốc… nhưng nước trong chậu đục ngầu rồi, cốc vẫn nhờn. Thay nước đã!', correct=False)
    take_grimy = min(g['grimy'], n)
    take_dirty = n - take_grimy
    g['grimy'] -= take_grimy
    g['dirty'] -= take_dirty
    g['clean'] += n
    d['basin'] = min(BASIN_MAX, d['basin'] + n)
    warn = ' Nước chậu bắt đầu đục, lần sau thay nước nhé.' if d['basin'] >= BASIN_MAX else ''
    return dict(message=f'🧽 Rửa sạch {n} cốc, úp lên khay cho ráo.{warn}')


def _basin(s, c, d, p):
    kit.need(d['basin'] > 0, 'Nước chậu vẫn còn trong.')
    d['basin'] = 0
    return dict(message='🪣 Hắt chậu nước đục vào rãnh, xách chậu nước sạch mới.')


# ---------------------------------------------------------------- pouring and serving
def _need_open(d: dict) -> None:
    st = d['stall']
    kit.need(st['open'], 'Chưa dọn hàng: bày ghế, dựng ô, đặt thùng đá rồi bấm “Mở hàng” nhé.')
    kit.need(not st['packed'], 'Quán đang dẹp. Bày lại ghế đã rồi bán tiếp.')


def _need_prep(t: dict) -> None:
    kit.need(t['known'], 'Hỏi khách gọi gì đã nhé.')
    kit.need(t['stage'] == 'prep', 'Đã đưa trà cho khách rồi.')


def _pour(s, c, d, p):
    t = _task(c, p, ('glass', 'kid', 'tab', 'match'))
    _need_open(d)
    _need_prep(t)
    drink = kit.one_of(p.get('drink'), DRINK, 'Món này quán không có.')
    kit.need(len(t['tray']) < 10, 'Khay đầy rồi.')
    th, g = d['thermos'], d['glasses']
    kit.need(th['tea'] > 0, 'Bình chè hết rồi. Pha ấm mới đã nhé.')
    kit.need(g['clean'] or g['grimy'], 'Hết cốc sạch! Rửa cốc trong chậu đã.')
    for item in DRINK[drink]['uses']:
        kit.need(kit.stock(c, item) > 0, f'Hết {_lower(ITEM[item]["name"])} rồi.')
    for item in DRINK[drink]['uses']:
        t['cost'] += kit.take(c, item, 1)
    grimy = not g['clean']
    if grimy:
        g['grimy'] -= 1
    else:
        g['clean'] -= 1
    th['tea'] -= 1
    ice = False
    if DRINK[drink]['cold'] and d['ice']['portions'] > 0:
        d['ice']['portions'] -= 1
        ice = True
    stale = c['turn'] - th['turn'] > _stale_after(c)
    t['tray'].append(dict(d=drink, s=th['strength'], stale=stale, ice=ice, grimy=grimy))
    if t['start_turn'] is None:
        t['start_turn'] = c['turn']
    kit.start_work(t)
    notes = []
    if DRINK[drink]['cold'] and not ice:
        notes.append('Hết đá, cốc này không có đá!')
    if grimy:
        notes.append('Cốc còn nhờn vì rửa nước đục.')
    if stale:
        notes.append('Chè để lâu đã hơi ôi.')
    if th['strength'] < WEAK:
        notes.append('Chè nhạt.')
    return dict(message=f'{DRINK[drink]["emoji"]} Rót một cốc {_lower(DRINK[drink]["name"])}.' + (' ⚠️ ' + ' '.join(notes) if notes else ''))


def _snack(s, c, d, p):
    t = _task(c, p, ('glass', 'kid', 'tab', 'match'))
    _need_open(d)
    _need_prep(t)
    item = kit.one_of(p.get('item'), SNACKS, 'Món này quán không bán.')
    kit.need(t['snacks'].get(item, 0) < 6, 'Lấy thế đủ rồi.')
    kit.need(kit.stock(c, item) > 0, f'Hết {_lower(ITEM[item]["name"])} rồi. Mở kho nhập thêm nhé.')
    t['cost'] += kit.take(c, item, 1)
    t['snacks'][item] = t['snacks'].get(item, 0) + 1
    kit.start_work(t)
    return dict(message=f'{ITEM[item]["emoji"]} Lấy 1 {ITEM[item]["unit"]} {_lower(ITEM[item]["name"])}.')


def _takeback(s, c, d, p):
    t = _task(c, p, ('glass', 'kid', 'tab', 'match'))
    _need_prep(t)
    if p.get('item') is not None:
        item = kit.one_of(p.get('item'), SNACKS, 'Món này quán không bán.')
        kit.need(t['snacks'].get(item, 0) > 0, 'Món này chưa lấy ra.')
        t['snacks'][item] -= 1
        if not t['snacks'][item]:
            del t['snacks'][item]
        it = ITEM[item]
        kit.add_lot(c, item, 1, it['cost'], it['life'], 'return')
        t['cost'] = max(0, t['cost'] - it['cost'])
        return dict(message=f'↩️ Cất lại 1 {it["unit"]} {_lower(it["name"])}.')
    i = kit.integer(p.get('index'), 0, max(0, len(t['tray']) - 1))
    kit.need(t['tray'], 'Khay còn trống.')
    glass = t['tray'].pop(i)
    d['glasses']['dirty'] += 1
    return dict(message=f'🚰 Đổ bỏ cốc {_lower(DRINK[glass["d"]]["name"])}, cốc cho vào chậu rửa.')


def _refuse(s, c, d, p):
    t = _task(c, p, ('kid',))
    _need_prep(t)
    kit.need(not t['refused'], 'Đã nói với cháu rồi.')
    t['refused'] = True
    d['today']['refused'] += 1
    d['stats']['refused_kid'] += 1
    back = t['snacks'].pop('thuoc_la', 0)
    if back:
        kit.add_lot(c, 'thuoc_la', back, ITEM['thuoc_la']['cost'], ITEM['thuoc_la']['life'], 'return')
    return dict(message='🙅 “Thuốc lá cô không bán cho trẻ con đâu. Cháu về bảo bố ra tự mua nhé!” Cu Tủn gãi đầu: “Dạ…”')


def _served(t: dict) -> dict:
    out = {}
    for g in t['tray']:
        out[g['d']] = out.get(g['d'], 0) + 1
    return out


def _order_price(c: dict, t: dict) -> int:
    """What the customer pays: what they ordered and actually got, at today's prices."""
    n, got = t['needs'], _served(t)
    total = sum(min(q, got.get(k, 0)) * _price(c, k) for k, q in n['drinks'].items())
    for k, q in n['snacks'].items():
        if n['kid'] and k == 'thuoc_la':
            continue
        total += min(q, t['snacks'].get(k, 0)) * _price(c, k)
    return total


def _hand_slips(c: dict, d: dict, t: dict) -> None:
    n, got = t['needs'], _served(t)
    who = _who(t)
    missing = {k: q - got.get(k, 0) for k, q in n['drinks'].items() if got.get(k, 0) < q}
    extra = {k: q - n['drinks'].get(k, 0) for k, q in got.items() if q > n['drinks'].get(k, 0)}
    if extra and missing:
        t['mistakes'] += 1
        a, b = next(iter(missing)), next(iter(extra))
        cq.slip(t, 'wrong_drink', 2, f'Tôi gọi {_lower(DRINK[a]["name"])} mà lại mang {_lower(DRINK[b]["name"])} ra.', 'rót nhầm món')
    elif missing:
        t['mistakes'] += 1
        cq.slip(t, 'missing', 2, f'Gọi {_list_text(n["drinks"])} mà thiếu mất {_list_text(missing)}.', 'thiếu cốc')
    elif extra:
        t['mistakes'] += 1
        cq.slip(t, 'extra', 1, f'Rót thừa {_list_text(extra)}, tôi có gọi đâu.', 'rót thừa')
    if t['tray']:
        low = min(g['s'] for g in t['tray'])
        if low < WATERY:
            t['mistakes'] += 1
            d['today']['weak'] += 1
            d['stats']['weak'] += 1
            cq.slip(t, 'watery', 2, 'Trà gì mà nhạt như nước lã, uống chẳng ra vị chè.', 'chè nhạt như nước lã')
        elif low < WEAK:
            t['mistakes'] += 1
            d['today']['weak'] += 1
            d['stats']['weak'] += 1
            cq.slip(t, 'weak', 1, 'Chè hôm nay nhạt quá, châm nước nhiều rồi phải không?', 'chè nhạt')
        if any(g['stale'] for g in t['tray']):
            t['mistakes'] += 1
            cq.slip(t, 'stale', 1, 'Chè để từ sáng, uống có vị ôi ôi.', 'chè để lâu bị ôi')
        if any(DRINK[g['d']]['cold'] and not g['ice'] for g in t['tray']):
            t['mistakes'] += 1
            cq.slip(t, 'no_ice', 1, 'Trà đá mà chẳng có viên đá nào, uống ấm ấm.', 'trà đá không có đá')
        if any(g['grimy'] for g in t['tray']):
            t['mistakes'] += 1
            cq.slip(t, 'grimy', 1, 'Cốc còn nhờn nhờn, rửa bằng nước đục phải không?', 'cốc chưa sạch')
    for k, q in n['snacks'].items():
        if n['kid'] and k == 'thuoc_la':
            continue
        if t['snacks'].get(k, 0) < q:
            t['mistakes'] += 1
            cq.slip(t, 'snack_' + k, 1, f'Tôi có gọi {_lower(ITEM[k]["name"])} mà quên mất rồi.', 'quên món ăn vặt')
            break
    if n['kid'] and t['snacks'].get('thuoc_la'):
        t['mistakes'] += 1
        cq.slip(t, 'minor_smoke', 3, 'Quán bán thuốc lá cho trẻ con! Con tôi mới mười tuổi.', 'bán thuốc lá cho trẻ em', safety=True)
    if n['seats'] > d['stall']['stools']:
        t['mistakes'] += 1
        cq.slip(t, 'no_seat', 1, f'Đi {n["seats"]} người mà quán chỉ bày {d["stall"]["stools"]} ghế, phải đứng uống.', 'thiếu ghế')
    if t['kind'] == 'match' and t['start_turn'] is not None and c['turn'] - t['start_turn'] > MATCH_TURNS:
        t['mistakes'] += 1
        cq.slip(t, 'slow', 1, 'Hết cả hiệp một mới đủ trà. Cả bàn khát khô cổ.', 'ra trà chậm')
    del who


def _serve(s, c, d, p):
    t = _task(c, p, ('glass', 'kid', 'tab', 'match'))
    _need_open(d)
    _need_prep(t)
    kit.need(t['tray'] or t['snacks'] or t['refused'], 'Khay còn trống. Rót trà hoặc lấy đồ cho khách đã.')
    _hand_slips(c, d, t)
    price = _order_price(c, t)
    t['price'] = price
    d['glasses']['dirty'] += len(t['tray'])
    d['today']['glasses'] += len(t['tray'])
    d['stats']['glasses'] += len(t['tray'])
    sold = sum(q for k, q in t['snacks'].items())
    d['today']['snacks'] += sold
    d['stats']['snacks'] += sold
    who = _who(t)
    if cq.safety(t):
        react = cq.react(s, c, t, price, who=who)
        msg = _finish(s, c, d, t, react['pay'], f'Cô Hoa trông thấy, chạy sang: “Bán thuốc cho trẻ con à?” {react["message"]}')
        return dict(message='🚨 ' + msg, correct=False)
    if t['needs']['pay'] == 'tab':
        react = cq.react(s, c, t, price, who=who)
        t['owe'] = react['pay']
        if react['kind'] in ('refuse', 'walkout') or not t['owe']:
            msg = _finish(s, c, d, t, 0, react['message'] or f'{who} uống xong, không ghi gì.')
            return dict(message=msg)
        t['stage'] = 'book'
        head = f'{who}: “Ghi sổ cho chú nhé!”'
        return dict(message=(head + (' ' + react['message'] if react['message'] else '')).strip())
    if not price:
        react = cq.react(s, c, t, 0, who=who)
        msg = _finish(s, c, d, t, 0, react['message'] or f'{who} lắc đầu bỏ đi, không trả đồng nào.')
        return dict(message=msg, correct=False)
    t['cash'] = till.new(price, t['id'], c=c, t=t)
    t['stage'] = 'pay'
    tender = sum(t['cash']['tender'])
    return dict(message=f'🥤 Đưa trà cho {who}. Khách đưa {tender} xu: tính tiền, thối lại cho đúng.')


def _pay(s, c, d, p):
    t = _task(c, p, ('glass', 'kid', 'match', 'settle'))
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    who = _who(t)
    rec = t['cash']
    chk = till.check(s, c, t, rec, p.get('change'), who)
    if chk['stop']:
        return dict(message='💵 ' + chk['message'], correct=False)
    price = t['price'] if t['kind'] != 'settle' else t['bill']['total']
    react = cq.react(s, c, t, price, who=who)
    st = till.settle(s, c, t, rec, react, who)
    net = react['pay'] - st['loss']
    parts = [x for x in (react['message'], st['message']) if x]
    if t['kind'] == 'settle':
        _close_bill(d, t)
    msg = _finish(s, c, d, t, max(0, net), ' '.join(parts))
    if net < 0:
        lost = min(-net, c['money'])
        if lost:
            kit.money(s, c, -lost, f'Thối dư cho khách: {t["title"]}'[:120], t['id'], 'change_loss')
    given = sum(rec['change'])
    head = f'💵 Thu {price} xu' + (f', thối {given} xu.' if given else '.')
    return dict(message=f'{head} {msg}'.strip(), celebrate=not cq.slips(t))


def _short(s, c, p):
    """Khách đưa thiếu tiền (game/short_pay.py via the till): count again, remind, call the police…"""
    t = _task(c, p)
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    return till.short_action(s, c, t, t['cash'], p, _who(t))


def _book(s, c, d, p):
    t = _task(c, p, ('tab',))
    kit.need(t['stage'] == 'book', 'Chưa đến lúc ghi sổ.')
    amount = kit.integer(p.get('amount'), 0, 500)
    kit.need(amount > 0, 'Ghi số tiền vào sổ đã nhé.')
    d['tab_seq'] += 1
    what = _list_text({**_served(t), **t['snacks']}) or 'trà'
    line = dict(id=f'tab-{d["tab_seq"]}', npc=_npc_index(t), task=t['id'], day=c['day'], amount=amount, due=t['owe'], what=what[:120])
    d['tab'] = ar.last(d['tab'] + [line], TAB_LINES, 'tra_da.tab', c)
    t['written'] = amount
    if amount < t['owe']:
        d['stats']['underbooked'] += t['owe'] - amount
    elif amount > t['owe']:
        d['stats']['overbooked'] += amount - t['owe']
    msg = _finish(s, c, d, t, 0, f'📒 Ghi sổ: ngày {c["day"]} · {what} · {amount} xu.')
    return dict(message=msg)


# ---------------------------------------------------------------- the tab settlement
def _bill_line(t: dict, lid: str) -> dict | None:
    return next((x for x in t['bill']['lines'] if x['id'] == lid), None)


def _bill(s, c, d, p):
    t = _task(c, p, ('settle',))
    kit.need(t['known'], 'Chào chú Tường đã nhé.')
    kit.need(t['stage'] == 'prep', 'Đã đọc sổ cho chú rồi.')
    if t['bill'] is None:
        _open_bill(d, t)
    kit.start_work(t)
    b = t['bill']
    if not b['lines']:
        msg = _finish(s, c, d, t, 0, 'Sổ của chú trắng trơn. Chú cười: “Thế thì làm cốc trà đá, trả tiền ngay!”')
        return dict(message='📒 ' + msg)
    dp = t['dispute']
    if dp and dp['state'] == 'open':
        t['stage'] = 'dispute'
        x = _bill_line(t, dp['line'])
        return dict(message=f'📒 Đọc sổ: {len(b["lines"])} dòng, {b["total"]} xu. Chú Tường nhíu mày: “Ơ, ngày {x["day"]} chú uống gì mà những {x["amount"]} xu?”')
    return _to_pay(d, t, f'📒 Đọc sổ: {len(b["lines"])} dòng, cộng {b["total"]} xu. Chú Tường gật gù móc ví.')


def _to_pay(d: dict, t: dict, head: str) -> dict:
    total = t['bill']['total']
    if total <= 0:
        t['stage'] = 'pay'
        return dict(message=head)
    t['stage'] = 'pay'
    t['cash'] = till.new(total, t['id'])
    return dict(message=f'{head} Chú đưa {sum(t["cash"]["tender"])} xu, thối lại cho đúng.')


def _dispute(s, c, d, p):
    t = _task(c, p, ('settle',))
    kit.need(t['stage'] == 'dispute' and t['dispute'], 'Không có dòng nào đang thắc mắc.')
    choice = kit.one_of(p.get('choice'), ('show', 'fix', 'drop', 'argue'), 'Chọn cách xử lý dòng sổ.')
    dp = t['dispute']
    x = _bill_line(t, dp['line'])
    book = next((r for r in d['tab'] if r['id'] == dp['line']), None)
    if choice == 'fix':
        kit.need(dp['wrong'], f'Dòng ngày {x["day"]} ghi đúng rồi ({x["what"]}): cho chú xem sổ là được.')
        x['amount'] = x['due']
        if book:
            book['amount'] = book['due']
        dp['state'] = 'fixed'
        head = f'✏️ Sửa dòng ngày {x["day"]} thành {x["due"]} xu. Chú Tường cười: “Thấy chưa, chú nhớ mà!”'
    elif choice == 'show':
        if dp['wrong'] and dp['state'] == 'open':
            t['mistakes'] += 1
            cq.slip(t, 'overbook', 2, f'Sổ ghi lố tiền của tôi: hôm đó {x["what"]} mà ghi {x["amount"]} xu.', 'ghi sổ lố tiền')
            dp['state'] = 'shown'
            return dict(message=f'📒 Chú Tường dí ngón tay vào dòng: “{x["what"]}, {x["due"]} xu thôi chứ, sao ghi {x["amount"]}?” Sửa lại hoặc bỏ dòng đó.', correct=False)
        kit.need(not dp['wrong'], 'Chú đã xem sổ rồi, dòng này ghi lố thật. Sửa lại hoặc bỏ dòng đó.')
        dp['state'] = 'ok'
        head = f'📒 Chỉ dòng ngày {x["day"]}: {x["what"]}. Chú Tường vỗ trán: “À, hôm ấy chú khao thằng Bảy!”'
    elif choice == 'drop':
        t['bill']['lines'] = [r for r in t['bill']['lines'] if r['id'] != x['id']]
        dp['state'] = 'dropped'
        if book:
            d['tab'] = [r for r in d['tab'] if r['id'] != x['id']]
        head = f'🤝 Bỏ dòng ngày {x["day"]} ({x["amount"]} xu) cho chú. Chú Tường vui ra mặt.'
    else:
        t['mistakes'] += 1
        cq.slip(t, 'argue', 2 if dp['wrong'] else 1, 'Có mấy xu mà quát khách quen giữa phố.', 'to tiếng với khách quen')
        dp['state'] = 'argued'
        if dp['wrong']:
            t['bill']['lines'] = [r for r in t['bill']['lines'] if r['id'] != x['id']]
            if book:
                d['tab'] = [r for r in d['tab'] if r['id'] != x['id']]
            head = f'😤 Hai bên to tiếng. Chú Tường gạch luôn dòng ngày {x["day"]}: “Dòng này chú không trả!”'
        else:
            head = '😤 Hai bên to tiếng. Chú Tường lầm bầm trả đủ, mặt nặng như chì.'
    t['bill']['total'] = sum(r['amount'] for r in t['bill']['lines'])
    return _to_pay(d, t, head)


def _settle_free(s, c, d, p):
    """A settlement whose book ends at 0 xu (every line dropped)."""
    t = _task(c, p, ('settle',))
    kit.need(t['stage'] == 'pay' and t['bill'] and t['bill']['total'] == 0, 'Còn tiền trong sổ, thu tiền nhé.')
    react = cq.react(s, c, t, 0, who=_who(t))
    _close_bill(d, t)
    return dict(message=_finish(s, c, d, t, 0, react['message'] or 'Sổ của chú Tường đã sạch.'))


def _close_bill(d: dict, t: dict) -> None:
    ids = {x['id'] for x in (t.get('bill') or {}).get('lines', [])}
    if t.get('dispute') and t['dispute']['state'] in ('dropped', 'argued') and t['dispute']['wrong']:
        ids.add(t['dispute']['line'])
    d['tab'] = [x for x in d['tab'] if x['id'] not in ids]


# ---------------------------------------------------------------- finishing a customer
def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str) -> str:
    i = _npc_index(t)
    story = ''
    if i in REG_STORY and t['kind'] != 'setup':
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        lines = REG_STORY[i]
        story = lines[min(r['visits'], len(lines)) - 1]
        t['story'] = story
    kit.complete(s, c, t, max(0, int(reward)), (narrative or t['title'])[:300])
    if story:
        return f'{narrative} 💬 {story}'.strip()
    return narrative


# ================================================================ the ward's sweep (timed)
def sweep_plan(day: int) -> tuple[int, int] | None:
    """(after how many finished jobs today, seconds to pack) or None: no sweep today."""
    if day < 3:
        return None
    if day == 3:
        return 2, SWEEP_FIRST
    r = kit.rng(ID, 'sweep', day)
    if r.random() >= 0.35:
        return None
    return 1 + r.randrange(3), SWEEP_LATER


def _sweep_tick(s: dict, c: dict, d: dict) -> bool:
    plan = sweep_plan(c['day'])
    st = d['stall']
    if not plan or not c.get('open') or not st['open'] or st['packed'] or d['desk']['ev'] is not None:
        return False
    if d['sweep'] and d['sweep']['day'] == c['day']:
        return False
    if any(x['day'] == c['day'] for x in d['sweeps']):
        return False
    if c['day_completed'] < plan[0]:
        return False
    d['sweep'] = dict(day=c['day'], stage='coming', start=kit.now(), limit=plan[1],
                      stools=st['stools'], umbrella=st['umbrella'], packed_stools=0, folded=False, result=None)
    kit.log(s, c, 'surprise', '🚨 Xe trật tự đô thị dừng đầu phố, loa phát: “Đề nghị các hộ không lấn chiếm vỉa hè!”', kit.npc_id(ID, 0), f'sweep-{c["day"]}')
    return True


def _pack(s, c, d, p):
    sw = d['sweep']
    kit.need(sw and sw['stage'] == 'coming', 'Không có đoàn kiểm tra nào đang tới.')
    what = kit.one_of(p.get('what'), ('stools', 'umbrella'), 'Dẹp gì trước?')
    if kit.now() > sw['start'] + sw['limit']:
        return _sweep_resolve(s, c, d)
    if what == 'stools':
        left = sw['stools'] - sw['packed_stools']
        kit.need(left > 0, 'Ghế đã xếp chồng gọn hết rồi.')
        sw['packed_stools'] += min(2, left)
    else:
        kit.need(sw['umbrella'] and not sw['folded'], 'Ô đã gấp rồi.')
        sw['folded'] = True
    if sw['packed_stools'] >= sw['stools'] and (sw['folded'] or not sw['umbrella']):
        return _sweep_resolve(s, c, d)
    left = sw['stools'] - sw['packed_stools']
    return dict(message=f'📦 Xếp chồng ghế… còn {left} ghế' + (' và cái ô' if sw['umbrella'] and not sw['folded'] else '') + '!')


def _sweep_end(s, c, d, p):
    sw = d['sweep']
    kit.need(sw and sw['stage'] == 'coming', 'Không có đoàn kiểm tra nào đang tới.')
    kit.need(kit.now() >= sw['start'] + sw['limit'] - 1, 'Xe còn ở đầu phố, tranh thủ dẹp tiếp!')
    return _sweep_resolve(s, c, d)


def _sweep_resolve(s: dict, c: dict, d: dict) -> dict:
    sw = d['sweep']
    st = d['stall']
    left = max(0, sw['stools'] - sw['packed_stools'])
    umbrella_out = sw['umbrella'] and not sw['folded']
    road = st['spot'] == 'le_duong'
    fine, lost = 0, 0
    if left or umbrella_out or road:
        fine = FINE_BASE + FINE_STOOL * left + (FINE_UMBRELLA if umbrella_out else 0) + (FINE_ROAD if road else 0)
        lost = min(left, 3)
    if lost:
        d['owned']['stools'] = max(STOOLS_MIN, d['owned']['stools'] - lost)
    paid = min(fine, c['money'])
    if paid:
        kit.money(s, c, -paid, 'Phạt lấn chiếm vỉa hè', f'sweep-{c["day"]}', 'fine')
    d['today']['fine'] += paid
    d['today']['lost_stools'] += lost
    d['stats']['fines'] += paid
    if not fine:
        d['stats']['sweeps_ok'] += 1
        c['xp'] += 8
    sw.update(stage='done', result=dict(fine=paid, lost=lost, left=left, umbrella=umbrella_out, road=road))
    d['sweeps'] = ar.last(d['sweeps'] + [dict(day=c['day'], fine=paid, lost=lost)], 20, 'tra_da.sweeps', c)
    st['packed'] = True
    st['stools'] = 0
    st['umbrella'] = False
    if not fine:
        msg = '✅ Xe trật tự đi qua. Quán đã dẹp gọn sát gốc cây, các anh chỉ gật đầu. Bày lại quán rồi bán tiếp!'
        kit.log(s, c, 'surprise', 'Dẹp gọn kịp lúc, trật tự đô thị đi qua không nhắc nhở gì.', kit.npc_id(ID, 0), f'sweep-{c["day"]}')
        return dict(message=msg, celebrate=True)
    bits = []
    if left:
        bits.append(f'{left} ghế còn trên vỉa hè')
    if umbrella_out:
        bits.append('ô chưa gấp')
    if road:
        bits.append('quán bày lấn lòng đường')
    msg = f'🚨 Không kịp rồi: {", ".join(bits)}. Lập biên bản, phạt {paid} xu' + (f', thu {lost} ghế' if lost else '') + '. Bày lại quán rồi bán tiếp.'
    kit.log(s, c, 'surprise', msg, kit.npc_id(ID, 0), f'sweep-{c["day"]}')
    return dict(message=msg, correct=False)


# ================================================================ story, growth and surprises
def _arc_tick(c: dict, d: dict) -> None:
    a = d['arc']
    if a['due']:
        return
    nxt = next((x for x in ARC if x['id'] not in a['seen']), None)
    if not nxt or c['day'] < nxt['day'] or d['stats']['glasses'] < nxt['glasses']:
        return
    a['due'] = nxt['id']
    gift = nxt['gift']
    if gift:
        k, v = gift
        o = d['owned']
        if k == 'stools':
            o['stools'] = min(STOOLS_MAX, o['stools'] + v)
        elif k == 'umbrella':
            o['umbrella'] = max(o['umbrella'], v)
        elif k in ('banner', 'chess'):
            o[k] = True


def _arc_seen(d: dict) -> dict:
    a = d['arc']
    kit.need(a['due'], 'Không có chuyện mới của quán.')
    x = ARC_INDEX[a['due']]
    a['seen'].append(a['due'])
    a['due'] = None
    return dict(message=f'{x["emoji"]} {x["title"]}')


def _buy(s, c, d, p):
    item = kit.one_of(p.get('item'), GROWTH_INDEX, 'Món này không có.')
    g, o = GROWTH_INDEX[item], d['owned']
    if item == 'stools':
        kit.need(o['stools'] + 2 <= STOOLS_MAX, 'Vỉa hè không kê thêm ghế được nữa.')
    elif item == 'glasses':
        kit.need(o['glasses'] + 4 <= GLASSES_MAX, 'Khay cốc đã đủ nhiều rồi.')
    elif item == 'umbrella':
        kit.need(o['umbrella'] < 2, 'Quán đã có ô to rồi.')
    else:
        kit.need(not o['banner'], 'Quán đã có biển rồi.')
    kit.confirm(p, f'Mua {_lower(g["name"])} hết {g["cost"]} xu nhé?')
    kit.need(c['money'] >= g['cost'], f'Chưa đủ {g["cost"]} xu.')
    kit.money(s, c, -g['cost'], g['name'], f'td-buy-{item}', 'equipment')
    if item == 'stools':
        o['stools'] += 2
    elif item == 'glasses':
        o['glasses'] += 4
        d['glasses']['clean'] += 4
    elif item == 'umbrella':
        o['umbrella'] = 2
    else:
        o['banner'] = True
    return dict(message=f'{g["emoji"]} Đã mua {_lower(g["name"])}. {g["note"]}', celebrate=True)


def _desk_hook(s: dict, c: dict, key: str, v) -> str | None:
    d = _data(c)
    g = d['glasses']
    if key == 'move':
        d['stall']['spot'] = v
        d['stall']['stools'] = min(d['stall']['stools'], SPOTS[v]['cap'])
        return None
    if key == 'wet':
        n = min(int(v), g['clean'])
        g['clean'] -= n
        g['grimy'] += n
        return f'{n} cốc phải rửa lại.' if n else None
    if key == 'dirty':
        n = min(int(v), g['clean'])
        g['clean'] -= n
        g['dirty'] += n
        return None
    if key == 'broke_stool':
        d['owned']['stools'] = max(STOOLS_MIN, d['owned']['stools'] - int(v))
        d['stall']['stools'] = min(d['stall']['stools'], d['owned']['stools'])
        return 'Quán mất một cái ghế.'
    if key == 'clean':
        d['basin'] = 0
        g['clean'] += g['grimy']
        g['grimy'] = 0
        return None
    return None


# ---------------------------------------------------------------- dispatch
ACTIONS = {
    'td_spot': _spot, 'td_stools': _stools, 'td_umbrella': _umbrella, 'td_box': _box, 'td_open': _open, 'td_unpack': _unpack,
    'td_brew': _brew, 'td_topup': _topup, 'td_dump_tea': _dump_tea, 'td_crush': _crush,
    'td_wash': _wash, 'td_basin': _basin,
    'td_pour': _pour, 'td_snack': _snack, 'td_takeback': _takeback, 'td_refuse': _refuse, 'td_serve': _serve,
    'td_pay': _pay, 'td_book': _book, 'td_bill': _bill, 'td_dispute': _dispute, 'td_settle_free': _settle_free,
    'td_pack': _pack, 'td_sweep_end': _sweep_end,
    'td_short': lambda s, c, d, p: _short(s, c, p),
}


# ================================================================ day start and close
def _ice_man(s: dict, c: dict, d: dict) -> str | None:
    n = d['ice_plan']
    if not n:
        return None
    cost = ITEM['da']['cost']
    n = min(n, c['money'] // cost)
    if not n:
        return 'Anh Tuấn xe đá ghé, nhưng quỹ quán không đủ tiền lấy đá.'
    kit.money(s, c, -n * cost, f'Anh Tuấn xe đá giao {n} cây đá', f'td-ice-{c["day"]}', 'stock')
    kit.add_lot(c, 'da', n, cost, 1, 'ice_man')
    return f'Anh Tuấn xe đá thả {n} cây đá trước cửa ({n * cost} xu).'


def _sau_seller(s: dict, c: dict, d: dict) -> str | None:
    cost = SAU_BATCH * ITEM['sau']['cost']
    if c['money'] < cost:
        return None
    kit.money(s, c, -cost, f'Bà bán sấu để lại {SAU_BATCH} phần sấu dầm', f'td-sau-{c["day"]}', 'stock')
    kit.add_lot(c, 'sau', SAU_BATCH, ITEM['sau']['cost'], ITEM['sau']['life'], 'sau_seller')
    return f'Bà bán sấu ghé để lại {SAU_BATCH} phần sấu dầm ({cost} xu).'


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['stall'] = _fresh_stall(day)
    d['thermos'] = dict(tea=0, strength=0, turn=c['turn'])
    d['ice'] = dict(portions=0, turn=c['turn'], acc=0)
    d['today'] = _fresh_today(day)
    d['sweep'] = None
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    notes = []
    if day > 1:
        notes.append(_ice_man(s, c, d))
    if mod_of(day)['id'] == 'sau':
        notes.append(_sau_seller(s, c, d))
    for n in notes:
        if n:
            kit.log(s, c, 'stock', n, kit.npc_id(ID, 0), f'td-morning-{day}')
    setup = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] == day
                  and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if setup is None and not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        # Yesterday's customers are still waiting (no new jobs were drawn): the stall still has to be set up.
        setup = make_task(day, 0, c['turn'])
        c['tasks'].append(setup)
        on_task(s, c, setup)
    if setup:
        c['active_task'] = setup['id']
        setup['deferred'] = False
    elif c['active_task'] and not any(t['id'] == c['active_task'] and t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks']):
        kit.eng().next_active(c)
    _arc_tick(c, d)
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    _melt(c, d)
    sweep_note = None
    sw = d['sweep']
    if sw and sw['stage'] == 'coming':
        # Closing time: the stall is packed up for the night before the truck gets here.
        sw.update(packed_stools=sw['stools'], folded=True)
        sweep_note = '🚨 Xe trật tự tới đúng lúc quán đang dọn về: không bị nhắc nhở.'
        if d['stall']['spot'] == 'le_duong':
            d['stall']['spot'] = 'goc_bang'
        _sweep_resolve(s, c, d)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK, hook=_desk_hook)
    today = d['today']
    lines = [f'🥤 Rót {today["glasses"]} cốc, bán {today["snacks"]} món ăn vặt.']
    if today['melted']:
        lines.append(f'🧊 Đá tan mất {today["melted"]} phần trong thùng.')
    if today['weak']:
        lines.append(f'🍵 {today["weak"]} lượt khách chê chè nhạt.')
    if today['refused']:
        lines.append('🙅 Không bán thuốc lá cho trẻ con. Bà Lựu khen phải.')
    written = [x for x in d['tab'] if x['day'] == c['day']]
    under = sum(x['due'] - x['amount'] for x in written if x['amount'] < x['due'])
    over = sum(x['amount'] - x['due'] for x in written if x['amount'] > x['due'])
    owed = sum(x['amount'] for x in d['tab'])
    if written:
        check = 'khớp từng dòng' if not under and not over else (f'ghi thiếu {under} xu' if under else '') + \
            (' và ' if under and over else '') + (f'ghi lố {over} xu' if over else '')
        lines.append(f'📒 Bà Lựu dò sổ tối nay: {len(written)} dòng mới, {check}.')
    if owed:
        lines.append(f'📒 Sổ chú Tường đang nợ {owed} xu.')
    if today['fine']:
        lines.append(f'🚨 Bị phạt {today["fine"]} xu' + (f', mất {today["lost_stools"]} ghế.' if today['lost_stools'] else '.'))
    elif d['sweep'] and d['sweep']['day'] == c['day'] and d['sweep']['result'] and not d['sweep']['result']['fine']:
        lines.append('✅ Dẹp gọn kịp lúc khi trật tự đô thị đi qua.')
    if sweep_note:
        lines.append(sweep_note)
    if desk_note:
        lines.append(desk_note)
    left = d['thermos']['tea']
    if left:
        lines.append(f'🚰 Đổ bỏ {left} cốc chè thừa, úp bình.')
    g = d['glasses']
    washed = g['dirty'] + g['grimy']
    if washed:
        lines.append(f'🧽 Rửa nốt {washed} cốc, úp gọn vào khay.')
    g['clean'] += washed
    g['dirty'] = g['grimy'] = 0
    d['basin'] = 0
    d['thermos'] = dict(tea=0, strength=0, turn=c['turn'])
    d['ice'] = dict(portions=0, turn=c['turn'], acc=0)
    d['stall'].update(open=False, packed=False, stools=0, umbrella=False, box=False)
    plan = d['ice_plan']
    return dict(lines=lines, note=f'Sáng mai anh Tuấn xe đá thả {plan} cây đá.' if plan else 'Sáng mai không đặt đá.',
                glasses=today['glasses'], snacks=today['snacks'], melted=today['melted'], owed=owed, fine=today['fine'])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 85 else 4 if p >= 65 else 3 if p >= 45 else 2
    codes = {x['code'] for x in cq.slips(t)}
    if t['kind'] == 'setup':
        spot = 3 if codes & {'road', 'spot', 'rain_spot', 'crowd'} else 5
        ready = 5 - len(codes & {'no_tea', 'weak_brew', 'no_ice', 'no_umbrella'})
        return dict(criteria=[dict(key='spot', label='Chỗ bày quán', score=spot, note='gọn, đúng chỗ' if spot == 5 else 'chỗ bày chưa hợp'),
                              dict(key='ready', label='Chuẩn bị đủ', score=max(2, ready), note='chè, đá, ô đủ cả' if ready == 5 else 'còn thiếu khâu chuẩn bị')])
    if t['kind'] == 'settle':
        book = 3 if codes & {'overbook'} else 5
        manner = 2 if 'argue' in codes else 5
        return dict(criteria=[dict(key='book', label='Sổ sách rõ ràng', score=book, note='từng dòng có ngày, có món' if book == 5 else 'có dòng ghi lố'),
                              dict(key='manner', label='Cách nói chuyện', score=manner, note='nhẹ nhàng' if manner == 5 else 'to tiếng với khách quen')])
    tray = t.get('tray') or []
    low = min((g['s'] for g in tray), default=75)
    tea = 5 if low >= WEAK and not any(g['stale'] for g in tray) else 3 if low >= WATERY else 2
    clean = 3 if any(g['grimy'] for g in tray) else 5
    rows = [dict(key='order', label='Đúng món', score=5, note='đủ cốc, đúng món'),
            dict(key='tea', label='Chè ngon', score=tea, note='chè đậm vừa' if tea == 5 else 'chè nhạt hoặc để lâu'),
            dict(key='clean', label='Cốc sạch, đá mát', score=3 if 'no_ice' in codes else clean,
                 note='cốc sạch, đá mát' if clean == 5 and 'no_ice' not in codes else 'cốc chưa sạch hoặc thiếu đá'),
            dict(key='speed', label='Nhanh gọn', score=speed, note=f'chờ còn {p}% kiên nhẫn')]
    if t['kind'] == 'kid':
        rows.append(dict(key='care', label='Có trách nhiệm', score=5 if t.get('refused') else 1 if 'minor_smoke' in codes else 4,
                         note='không bán thuốc cho trẻ em' if t.get('refused') else 'chưa nói rõ với cháu'))
    return dict(criteria=rows)


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        spot = SPOTS[n['spot']]
        return (f'Bà Lựu dặn: bày ở {_lower(spot["name"])}, {n["stools"][0]}–{n["stools"][1]} ghế'
                + (', dựng ô' if n['umbrella'] else '') + ', đặt thùng đá chỗ râm, pha ấm chè, đập một cây đá rồi mở hàng. ' + n['note'])
    if t['kind'] == 'settle':
        return n['note']
    parts = [x for x in (_list_text(n['drinks']), _list_text({k: v for k, v in n['snacks'].items()})) if x]
    pay = 'ghi sổ' if n['pay'] == 'tab' else 'trả tiền mặt'
    seats = f' · {n["seats"]} người ngồi' if n['seats'] > 1 else ''
    kid = ' · Khách là trẻ con.' if n['kid'] else ''
    return f'{_who(t)} gọi: {", ".join(parts)}{seats} · {pay}.{kid} {n["note"]}'


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
    v['cash'] = till.public(t.get('cash'))
    if isinstance(v.get('bill'), dict):
        # The book shows what was written, never what it should have said.
        v['bill']['lines'] = [{k: x[k] for k in x if k != 'due'} for x in v['bill']['lines']]
    if v['kind'] == 'settle' and isinstance(t.get('dispute'), dict):
        dp = t['dispute']
        v['dispute'] = dict(line=dp['line'], state=dp['state']) if t['stage'] in ('dispute', 'pay', 'done') or dp['state'] != 'open' else None
    return v


def _sweep_public(d: dict) -> dict | None:
    sw = d.get('sweep')
    if not sw:
        return None
    v = dict(sw)
    v['left'] = max(0, sw['stools'] - sw['packed_stools'])
    v['remain'] = max(0.0, round(sw['start'] + sw['limit'] - kit.now(), 1)) if sw['stage'] == 'coming' else 0
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    left, _, lost = _melt_view(c, d)
    mod = mod_of(c['day'])
    th = d['thermos']
    arc = d['arc']
    due = ARC_INDEX.get(arc['due']) if arc.get('due') else None
    return dict(
        intro=d['intro'], stall=d['stall'], owned=d['owned'], basin=d['basin'], basin_max=BASIN_MAX, glasses=d['glasses'],
        thermos=dict(tea=th['tea'], strength=th['strength'], max=THERMOS_MAX, stale=_stale(c, d),
                     age=max(0, c['turn'] - th['turn']) if th['tea'] else 0, stale_after=_stale_after(c)),
        ice=dict(portions=left, max=ICE_MAX, rate=melt_rate(c, d), blocks=kit.stock(c, 'da'), block=BLOCK),
        tab=dict(lines=[{k: x[k] for k in x if k != 'due'} for x in d['tab']], owed=sum(x['amount'] for x in d['tab'])),
        mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
        sweep=_sweep_public(d), sweeps=d['sweeps'][-5:], ice_plan=d['ice_plan'], stats=d['stats'], today=d['today'],
        regulars={k: dict(v) for k, v in d['regulars'].items()},
        arc=dict(seen=list(arc['seen']), total=len(ARC),
                 due=dict(id=due['id'], emoji=due['emoji'], title=due['title'], text=list(due['text'])) if due else None),
        desk=kit.desk_public(d['desk'], DESK, ID))


def content() -> dict:
    return dict(drinks=DRINKS, snacks=[dict(id=k, name=ITEM[k]['name'], emoji=ITEM[k]['emoji'], unit=ITEM[k]['unit']) for k in SNACKS],
                prices=PRICES, spots=SPOTS, brew=BREW, weak=WEAK, watery=WATERY, thermos_max=THERMOS_MAX, topup=TOPUP,
                topup_drop=TOPUP_DROP, ice_max=ICE_MAX, block=BLOCK, basin_max=BASIN_MAX, stools_min=STOOLS_MIN,
                stools_max=STOOLS_MAX, match_turns=MATCH_TURNS, denoms=list(till.DENOMS), ice_plan_max=ICE_PLAN_MAX,
                growth=GROWTH, intro=INTRO, arc=[dict(id=x['id'], emoji=x['emoji'], title=x['title']) for x in ARC],
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    k = t.get('kind')
    if k == 'setup':
        return 'Chọn chỗ → bày ghế → dựng ô → đặt thùng đá → pha ấm chè → đập đá → Mở hàng.'
    if k == 'settle':
        return 'Đọc sổ cho chú → có dòng thắc mắc thì cùng xem sổ (ghi lố thì sửa) → thu tiền, thối đúng.'
    if k == 'tab':
        return 'Hỏi món → rót đủ cốc, lấy đồ ăn vặt → đưa trà → ghi đúng số tiền vào sổ.'
    if k == 'kid':
        return 'Trẻ con mua thuốc lá: từ chối khéo, bán phần còn lại, thối tiền đúng.'
    return 'Hỏi món → rót đúng cốc (trà đá cần đá) → lấy đồ ăn vặt → đưa trà → thu tiền, thối đúng.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = _data(c)
    if e.get('role') == 'wash':
        g = d['glasses']
        if d['basin'] >= BASIN_MAX:
            d['basin'] = 0
            return 'Đã thay chậu nước rửa cốc.'
        if g['dirty'] or g['grimy']:
            n = min(WASH_BATCH, g['dirty'] + g['grimy'], BASIN_MAX - d['basin'])
            if n:
                a = min(g['grimy'], n)
                g['grimy'] -= a
                g['dirty'] -= n - a
                g['clean'] += n
                d['basin'] += n
                return f'Đã rửa {n} cốc.'
        return 'Đã lau bàn, quét lá bàng quanh quán.'
    if e.get('role') == 'ice':
        _melt(c, d)
        if d['stall']['box'] and d['ice']['portions'] <= ICE_MAX - BLOCK and d['ice']['portions'] < 6 and kit.stock(c, 'da'):
            kit.take(c, 'da', 1)
            d['ice']['portions'] += BLOCK
            d['ice']['turn'] = c['turn']
            return 'Đã đập thêm một cây đá vào thùng.'
        return 'Đã đậy kín thùng đá, kê lại chỗ râm.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu quán trà sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc quán trà không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc quán trà sai.')
    tray = t.get('tray')
    kit.need(isinstance(tray, list) and len(tray) <= 10, 'Khay trà sai.')
    for g in tray:
        kit.need(isinstance(g, dict) and set(g) == {'d', 's', 'stale', 'ice', 'grimy'} and g['d'] in DRINK, 'Cốc trà sai.')
        kit.integer(g['s'], 0, 100)
        for k in ('stale', 'ice', 'grimy'):
            _vbool(g[k])
    sn = t.get('snacks')
    kit.need(isinstance(sn, dict) and all(k in SNACKS for k in sn), 'Đồ ăn vặt sai.')
    for q in sn.values():
        kit.integer(q, 1, 6)
    _vbool(t.get('refused'))
    for k in ('price', 'owe', 'written', 'start_turn'):
        if t.get(k) is not None:
            kit.integer(t[k], 0, 10 ** 9)
    kit.integer(t.get('cost'), 0, 10 ** 6)
    till.validate(t.get('cash'), t)
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách quen sai.')
    b = t.get('bill')
    if b is not None:
        kit.need(isinstance(b, dict) and isinstance(b.get('lines'), list) and len(b['lines']) <= TAB_LINES, 'Hóa đơn sổ sai.')
        for x in b['lines']:
            _valid_line(x)
        kit.need(b.get('total') == sum(x['amount'] for x in b['lines']), 'Tổng sổ sai.')
    dp = t.get('dispute')
    if dp is not None:
        kit.need(isinstance(dp, dict) and dp.get('state') in ('open', 'shown', 'fixed', 'ok', 'dropped', 'argued'), 'Dòng thắc mắc sai.')
        _vbool(dp.get('wrong'))
        kit.text(dp.get('line'), 40)


def _valid_line(x) -> None:
    kit.need(isinstance(x, dict) and set(x) == {'id', 'npc', 'task', 'day', 'amount', 'due', 'what'}, 'Dòng sổ sai.')
    kit.text(x['id'], 40)
    kit.text(x['task'], 60)
    kit.text(x['what'], 120)
    kit.integer(x['npc'], 0, len(PEOPLE) - 1)
    kit.integer(x['day'], 1, 10 ** 7)
    kit.integer(x['amount'], 0, 500)
    kit.integer(x['due'], 0, 500)


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    till.validate_book(c)
    st = d['stall']
    kit.need(isinstance(st, dict) and set(_fresh_stall(0)) <= set(st) and st['spot'] in (None, *SPOTS), 'Quán trà sai.')
    kit.integer(st['day'], 0, 10 ** 7)
    kit.integer(st['stools'], 0, STOOLS_MAX)
    for k in ('umbrella', 'box', 'open', 'packed'):
        _vbool(st[k])
    th = d['thermos']
    kit.integer(th.get('tea'), 0, THERMOS_MAX)
    kit.integer(th.get('strength'), 0, 100)
    kit.integer(th.get('turn'), 0, 10 ** 9)
    ice = d['ice']
    kit.integer(ice.get('portions'), 0, ICE_MAX)
    kit.integer(ice.get('turn'), 0, 10 ** 9)
    kit.integer(ice.get('acc'), 0, 11)
    g = d['glasses']
    kit.need(isinstance(g, dict) and set(g) == {'clean', 'dirty', 'grimy'}, 'Cốc sai.')
    for v in g.values():
        kit.integer(v, 0, GLASSES_MAX * 2)
    kit.integer(d['basin'], 0, BASIN_MAX)
    kit.need(isinstance(d['tab'], list) and len(d['tab']) <= TAB_LINES, 'Sổ ghi nợ sai.')
    for x in d['tab']:
        _valid_line(x)
    kit.integer(d['tab_seq'], 0, 10 ** 9)
    o = d['owned']
    kit.integer(o['stools'], STOOLS_MIN, STOOLS_MAX)
    kit.integer(o['glasses'], 1, GLASSES_MAX)
    kit.integer(o['umbrella'], 1, 2)
    _vbool(o['banner'])
    _vbool(o['chess'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
    a = d['arc']
    kit.need(isinstance(a, dict) and isinstance(a.get('seen'), list) and all(x in ARC_INDEX for x in a['seen'])
             and len(set(a['seen'])) == len(a['seen']) and a.get('due') in (None, *ARC_INDEX), 'Chuyện quán sai.')
    sw = d['sweep']
    if sw is not None:
        kit.need(isinstance(sw, dict) and sw.get('stage') in ('coming', 'done'), 'Đợt dẹp vỉa hè sai.')
        kit.integer(sw.get('day'), 1, 10 ** 7)
        kit.need(isinstance(sw.get('start'), (int, float)) and not isinstance(sw.get('start'), bool) and 0 <= sw['start'] < 10 ** 11, 'Giờ dẹp vỉa hè sai.')
        kit.integer(sw.get('limit'), 1, 120)
        kit.integer(sw.get('stools'), 0, STOOLS_MAX)
        kit.integer(sw.get('packed_stools'), 0, STOOLS_MAX)
        _vbool(sw.get('umbrella'))
        _vbool(sw.get('folded'))
        r = sw.get('result')
        kit.need(r is None or (isinstance(r, dict) and all(type(r.get(k)) is int for k in ('fine', 'lost', 'left'))), 'Kết quả dẹp vỉa hè sai.')
    kit.need(isinstance(d['sweeps'], list) and len(d['sweeps']) <= 20, 'Lịch sử dẹp vỉa hè sai.')
    for x in d['sweeps']:
        kit.need(isinstance(x, dict), 'Lịch sử dẹp vỉa hè sai.')
        for k in ('day', 'fine', 'lost'):
            kit.integer(x.get(k), 0, 10 ** 7)
    kit.integer(d['ice_plan'], 0, ICE_PLAN_MAX)
    kit.need(isinstance(d['today'], dict) and set(_fresh_today(0)) <= set(d['today']), 'Số liệu trong ngày sai.')
    for v in d['today'].values():
        kit.integer(v, 0, 10 ** 9)
    kit.need(isinstance(d['stats'], dict), 'Số liệu quán sai.')
    for v in d['stats'].values():
        kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='td_', category='food',
    meta=dict(short='Trà đá vỉa hè', place='Trà đá gốc bàng', tagline='Cốc trà đá, cái ghế nhựa, chuyện cả phố.', icon='coffee',
              color='#4f8a5b', light='#eef6e4', weather='Nắng nhẹ dưới tán bàng', work='Khách ngồi', station='Quán trà',
              greeting='Dọn hàng, pha bình chè, đập đá, rót trà, thu tiền lẻ. Nhớ ghi sổ cho chú xe ôm và canh xe trật tự đô thị nhé.',
              caption='Một cốc trà đá, trăm câu chuyện phố', map_label='18 · TRÀ ĐÁ GỐC BÀNG'),
    people=PEOPLE,
    staff=[('Tí', 'wash', 'Cháu nội bà Lựu, rửa cốc nhanh thoăn thoắt.', 82, 80),
           ('Bảy', 'ice', 'Bạn xe ôm của chú Tường, đập đá khỏe.', 78, 84),
           ('Mơ', 'wash', 'Sinh viên làm thêm, cốc nào cũng tráng hai lần.', 70, 93),
           ('Toàn', 'ice', 'Nhớ giờ xe đá, thùng đá lúc nào cũng đầy.', 85, 78)],
    roles={'wash': 'Rửa cốc', 'ice': 'Đập đá'},
    inventory=dict(items=ITEMS, capacity=40),
    prices=PRICES,
    tip=2,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('🧊', 'Quán trà gọn gàng', [('Chè Thái khô', 'Hộp thiếc'), ('Đá cây', 'Thùng đá'), ('Kẹo lạc', 'Lọ thủy tinh'), ('Cốc bẩn', 'Chậu rửa')],
              ['Bày ghế, dựng ô', 'Pha bình chè', 'Đập đá, rót trà', 'Thu tiền, thối đúng']),
    stories=[('Chè của bà Lựu', ('Bà Lựu bảo chè ngon phải là chè Thái, sao kỹ, tráng ấm bằng nước sôi.',
                                 'Bạn pha thử ba ấm: ít chè, vừa chè, nhiều chè. Ông Khang nếm từng cốc.',
                                 'Ông Khang chọn ấm vừa chè: “Thế này mới là trà đá gốc bàng.”')),
             ('Cuốn sổ của chú Tường', ('Chú Tường uống ghi sổ đã hai mươi năm, sổ cũ nát cả gáy.',
                                        'Bạn chép sang cuốn sổ mới, ghi rõ từng ngày, từng món.',
                                        'Đến hẹn chú trả đủ, còn khen: “Sổ này đọc sướng mắt!”')),
             ('Mùa sấu', ('Sấu non về chợ, Linh hỏi quán có sấu dầm không.',
                          'Bà Lựu dạy bạn dầm sấu với đường, gừng, ớt.',
                          'Cốc sấu đá đầu mùa, cả nhóm của Linh xuýt xoa.'))],
    review_asides=['Chè đậm, đá mát, ngồi gốc bàng gió thổi mát rượi.', 'Tiền lẻ thối đúng từng xu, nhanh gọn.',
                   'Cốc sạch bong, uống yên tâm.', 'Ngồi một cốc mà nghe được cả chuyện phố, vui!'],
    situations=SITUATIONS,
    guide='Dọn hàng → pha chè → đập đá → rót trà → đưa trà → thu tiền, thối đúng. Chú xe ôm: ghi đúng số vào sổ, đến hẹn thu. Xe trật tự tới: dẹp ghế, gấp ô thật nhanh.',
)
