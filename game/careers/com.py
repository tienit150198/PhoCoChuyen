"""Cơm tấm Dì Bảy: a rice stall at the mouth of the market (plugin career).

Dì Bảy has sold rice on the same corner for twenty years: cơm tấm sườn nướng off the charcoal
grill, and at noon cơm phần from the glass case (cá kho, thịt kho trứng, rau muống, tàu hũ sốt cà).
The player works the stall. What the job is:

* the morning (``setup`` task): cook the two pots (broken rice takes less water than white rice:
  half a knuckle against one knuckle; the wrong line gives mushy or hard rice for the whole pot),
  taste the bowl of nước mắm Dì Bảy mixed last night and fix it (too salty → water, bland → fish
  sauce, too sweet → lime, too sour → sugar; one wrong fix spoils a good bowl), light the charcoal,
  lay the trays in the glass case from the stock room, then open;
* the grill: sườn go on in batches of up to four, are turned once and lifted; each side wants
  8–16 real seconds. A pink side is raw pork (a safety mistake if it reaches a plate), a long side
  chars, then burns. Grilled pieces wait on the rack; the player picks which piece goes on a plate;
* every plate: a dish for here or a box to take away, rice from the right pot by the ladle
  (ít cơm one, a normal plate two, thêm cơm three), the dishes the customer names from the case or
  the rack, a fried egg (runny or well done) from the pan, then mỡ hành (never for a vegetarian:
  it is made with lard), nước mắm poured over, on the side (always on the side for a box) or soy
  sauce for a vegetarian, and a bowl of soup if wanted;
* cash with the shared till (game/careers/till.py);
* the evening: cooked food does not keep. What is left in the case, on the rack and in the pots
  is thrown out and booked as waste: cook to the day.

Mistakes go through consequences (cq.slip / cq.react); money only through the engine's money().
Everything random is rolled from the day, slot or task id.
"""
from __future__ import annotations

import copy

from ..jsoncopy import tree_copy
from . import kit
from . import till
from .. import consequences as cq

ID = 'com'
GEN = 1

# ---------------------------------------------------------------- the two pots
POT_VA = 14               # ladles of rice in one pot
COOK_S = 20               # real seconds before a pot is cooked
VA_MAX = 4                # ladles on one plate
WATER = {'lung': 'Lưng đốt ngón tay', 'mot': 'Một đốt ngón tay', 'ruoi': 'Một đốt rưỡi'}
RICE = {
    'tam': dict(name='Cơm tấm', short='tấm', emoji='🍚', item='gao_tam', water='lung', wrong={'mot': 'nhao', 'ruoi': 'nhao'}),
    'trang': dict(name='Cơm trắng', short='trắng', emoji='🍙', item='gao', water='mot', wrong={'lung': 'suong', 'ruoi': 'nhao'}),
}
RICE_Q = ('ok', 'nhao', 'suong')
RICE_NOTE = {'nhao': 'nhão, dính bết', 'suong': 'sượng, còn hột'}
VA_WORD = {1: 'ít cơm', 2: 'cơm vừa', 3: 'thêm cơm', 4: 'thêm cơm'}

# ---------------------------------------------------------------- the charcoal grill
BATCH_MAX = 4
RACK_MAX = 8
SIDE_OK = (8, 16)         # seconds a side: shorter is still pink, longer chars
SIDE_BURN = 24            # past this the side is burnt
GRILL_Q = ('ok', 'song', 'xem', 'khet')
GRILL_RANK = {'ok': 0, 'xem': 1, 'khet': 2, 'song': 3}
GRILL_NOTE = {'ok': 'vàng đều, thơm', 'song': 'còn hồng, chưa chín', 'xem': 'hơi xém cạnh', 'khet': 'cháy khét'}

# ---------------------------------------------------------------- dishes
DISHES = {
    'suon': dict(name='Sườn nướng', short='sườn', emoji='🍖', src='grill', chay=False, price='suon'),
    'bi': dict(name='Bì', short='bì', emoji='🥢', src='tray', chay=False, price='bi'),
    'cha': dict(name='Chả trứng', short='chả', emoji='🍮', src='tray', chay=False, price='cha'),
    'trung_dao': dict(name='Ốp la lòng đào', short='ốp la lòng đào', emoji='🍳', src='pan', chay=False, price='trung'),
    'trung_chin': dict(name='Ốp la chín kỹ', short='ốp la chín', emoji='🍳', src='pan', chay=False, price='trung'),
    'ca_kho': dict(name='Cá kho tộ', short='cá kho', emoji='🐟', src='tray', chay=False, price='ca_kho'),
    'thit_kho': dict(name='Thịt kho trứng', short='thịt kho', emoji='🍲', src='tray', chay=False, price='thit_kho'),
    'rau': dict(name='Rau muống xào tỏi', short='rau muống', emoji='🥬', src='tray', chay=True, price='rau'),
    'dau_hu': dict(name='Tàu hũ sốt cà', short='tàu hũ', emoji='🍅', src='tray', chay=True, price='dau_hu'),
}
TRAYS = ('bi', 'cha', 'ca_kho', 'thit_kho', 'rau', 'dau_hu')
TRAY_N = dict(bi=8, cha=8, ca_kho=6, thit_kho=6, rau=8, dau_hu=8)    # portions from one unit of stock
TRAY_MAX = 16
ITEMS_MAX = 6             # dishes on one plate
PLATES_MAX = 6
VESSELS = {'dia': dict(name='Dĩa ăn tại chỗ', emoji='🍽️'), 'hop': dict(name='Hộp mang về', emoji='🥡')}
MAM = {'ruoi': 'Rưới nước mắm', 'rieng': 'Nước mắm để riêng', 'tuong': 'Nước tương'}

# ---------------------------------------------------------------- the bowl of nước mắm
MAM_Q = ('ok', 'man', 'lat', 'ngot', 'chua')
FIX = {'nuoc': 'man', 'mam': 'lat', 'chanh': 'ngot', 'duong': 'chua'}          # what each spoonful fixes
SPOIL = {'nuoc': 'lat', 'mam': 'man', 'chanh': 'chua', 'duong': 'ngot'}        # …and what it does to a good bowl
ADD_LABEL = {'nuoc': 'Thêm nước sôi để nguội', 'mam': 'Thêm nước mắm nhĩ', 'chanh': 'Vắt thêm chanh', 'duong': 'Thêm đường'}
TASTE = {'ok': 'vừa miệng: mằn mặn, ngọt dịu, chua nhẹ, thơm tỏi ớt.', 'man': 'mặn gắt, chát cả lưỡi.',
         'lat': 'lạt nhách, như nước đường.', 'ngot': 'ngọt lợ, ăn ngán.', 'chua': 'chua gắt, xé lưỡi.'}

ITEMS = [
    dict(id='gao_tam', name='Gạo tấm (một nồi)', emoji='🌾', group='gao', unit='nồi', cost=4, life=30, start=4),
    dict(id='gao', name='Gạo trắng (một nồi)', emoji='🌾', group='gao', unit='nồi', cost=3, life=30, start=4),
    dict(id='suon', name='Sườn cốt lết ướp sẵn', emoji='🍖', group='tuoi', unit='miếng', cost=2, life=2, start=12),
    dict(id='trung', name='Trứng gà', emoji='🥚', group='tuoi', unit='quả', cost=1, life=10, start=10),
    dict(id='bi', name='Bì trộn thính', emoji='🥢', group='khay', unit='hộp', cost=3, life=2, start=2),
    dict(id='cha', name='Chả trứng hấp', emoji='🍮', group='khay', unit='khuôn', cost=4, life=2, start=2),
    dict(id='ca_kho', name='Cá basa kho tộ', emoji='🐟', group='khay', unit='nồi', cost=6, life=2, start=2),
    dict(id='thit_kho', name='Thịt ba rọi kho trứng', emoji='🍲', group='khay', unit='nồi', cost=7, life=2, start=2),
    dict(id='rau', name='Rau muống xào tỏi', emoji='🥬', group='khay', unit='bó', cost=2, life=1, start=2),
    dict(id='dau_hu', name='Tàu hũ sốt cà', emoji='🍅', group='khay', unit='chảo', cost=3, life=2, start=2),
    dict(id='hop', name='Hộp giấy mang về', emoji='🥡', group='bao_bi', unit='hộp', cost=1, life=90, start=20),
]
# xu: a plate of broken rice / white rice (two ladles), a third ladle, each dish, the box.
PRICES = dict(com_tam=4, com_trang=3, them=1, suon=6, bi=2, cha=3, trung=2, ca_kho=5, thit_kho=6, rau=2, dau_hu=3, hop=1)

PEOPLE = [
    ('Dì Bảy', 'Chủ quán cơm', 'Bán cơm đầu chợ hai mươi năm, bốn giờ sáng đã nhóm bếp than.', 'warm'),
    ('Chú Bình', 'Xe ôm đầu hẻm', 'Sáng nào cũng một dĩa cơm tấm sườn, ăn xong mới chạy cuốc đầu.', 'quiet'),
    ('Chị Ngân', 'Kế toán công ty gần chợ', 'Hay đặt cơm hộp cho cả phòng, dặn từng hộp một.', 'bossy'),
    ('Anh Mạnh', 'Thợ hồ công trình đầu hẻm', 'Ăn khỏe, dĩa nào cũng thêm cơm, liếc dĩa là biết đủ hay thiếu.', 'sour'),
    ('Nhi', 'Sinh viên ở trọ', 'Tính từng đồng, cuối tháng chỉ dám ăn cơm bì chả.', 'genz'),
    ('Bà Sương', 'Hưu trí, ăn chay ngày rằm', 'Mùng một, ngày rằm ăn chay, dặn kỹ từng món.', 'picky'),
    ('Chị Lụa', 'Bán rau ngoài chợ', 'Ăn vội giữa buổi chợ, để quang gánh ngoài lề.', 'warm'),
]

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Sáng dân lao động ghé ăn cơm tấm, trưa dân văn phòng ghé cơm phần.', weight=3),
    dict(id='rain', emoji='🌧️', label='Mưa dầm', hint='Ít người ngồi lại, nhiều người mua hộp mang về: nước mắm để riêng.', min_day=2, weight=2),
    dict(id='market', emoji='🛒', label='Chợ phiên', hint='Chợ đông từ sớm, khách cơm tấm nối đuôi: nướng sườn sẵn trên vỉ.', min_day=2, weight=2),
    dict(id='ram', emoji='🌕', label='Ngày rằm', hint='Nhiều cô bác ăn chay: tàu hũ, rau, nước tương, không mỡ hành.', min_day=3, weight=1),
]
MOD = {m['id']: m for m in MODS}


def _l(r, va, items, mo=True, mam='ruoi', canh=True, chay=False):
    return dict(r=r, va=va, it=list(items), mo=mo, mam=mam, canh=canh, chay=chay)


def _h(r, va, items, mo=True, mam='rieng', canh=False, chay=False):
    """A take-away box: the sauce always on the side, no soup unless asked."""
    return _l(r, va, items, mo, mam, canh, chay)


# (npc, kind, title, opening, lines, note, min_day, mod, flags)
ORDERS = [
    (1, 'serve', 'Chú Bình ăn sáng', 'Cho chú dĩa cơm tấm sườn nghen con, như mọi bữa.', [_l('tam', 2, ['suon'])],
     'Chú Bình dựng xe ôm bên lề, kéo ghế nhựa ngồi đầu bàn.', 1, None, {}),
    (4, 'serve', 'Nhi ăn cơm phần', 'Chị ơi, cho em dĩa cơm phần: thịt kho hột vịt với rau muống, thêm cơm nha.', [_l('trang', 3, ['thit_kho', 'rau'])],
     'Nhi đếm mấy tờ tiền lẻ trong ví.', 1, None, {}),
    (2, 'serve', 'Chị Ngân mua hai hộp', 'Hai hộp mang về nha em: một hộp cơm tấm sườn bì chả, một hộp cá kho với rau. Nước mắm để riêng giùm chị.',
     [_h('tam', 2, ['suon', 'bi', 'cha']), _h('trang', 2, ['ca_kho', 'rau'])],
     'Chị Ngân tranh thủ giờ nghỉ trưa, tay còn cầm điện thoại.', 1, None, dict(togo=True)),
    (3, 'serve', 'Anh Mạnh ăn khỏe', 'Dĩa cơm tấm sườn ốp la, thêm cơm! Trứng chiên chín kỹ giùm anh.', [_l('tam', 3, ['suon', 'trung_chin'])],
     'Anh Mạnh vừa xong ca đổ bê tông, áo còn dính xi măng.', 2, None, dict(check=True)),
    (1, 'serve', 'Chú Bình bớt cơm', 'Bữa nay chú ăn sườn với ốp la lòng đào. Ít cơm thôi con, bác sĩ dặn bớt tinh bột.',
     [_l('tam', 1, ['suon', 'trung_dao'])], 'Chú Bình vỗ vỗ cái bụng, cười hiền.', 2, None, {}),
    (4, 'serve', 'Nhi cuối tháng', 'Cuối tháng rồi chị ơi… dĩa cơm tấm bì chả thôi, ít cơm, khỏi canh.', [_l('tam', 1, ['bi', 'cha'], canh=False)],
     'Nhi cười trừ, tiền trong ví còn đúng mấy đồng.', 2, None, {}),
    (6, 'serve', 'Chị Lụa ăn vội', 'Cho chị dĩa cá kho với tàu hũ, không hành nha em, chị ăn lẹ rồi ra sạp.', [_l('trang', 2, ['ca_kho', 'dau_hu'], mo=False)],
     'Chị Lụa để quang gánh rau ngoài lề.', 2, None, {}),
    (3, 'serve', 'Anh Mạnh mua cho tổ thợ', 'Ba hộp mang về cho tổ thợ: hai hộp cơm tấm sườn, một hộp thịt kho rau. Hộp nào cũng thêm cơm nha!',
     [_h('tam', 3, ['suon']), _h('tam', 3, ['suon']), _h('trang', 3, ['thit_kho', 'rau'])],
     'Mấy anh thợ ngồi chờ trên giàn giáo đầu hẻm.', 3, None, dict(togo=True, check=True)),
    (5, 'serve', 'Bà Sương ghé quán', 'Cho bà dĩa cơm trắng với cá kho, ít cơm, thêm chén canh nghe con.', [_l('trang', 1, ['ca_kho'])],
     'Bà Sương chọn bàn gần cây quạt máy.', 3, None, {}),
    (4, 'serve', 'Nhi rủ bạn cùng phòng', 'Hai dĩa nha chị: một dĩa sườn ốp la lòng đào, một dĩa cá kho rau muống, cơm vừa.',
     [_l('tam', 2, ['suon', 'trung_dao']), _l('trang', 2, ['ca_kho', 'rau'])], 'Nhi với bạn chia nhau cái ghế đẩu.', 3, None, {}),
    (5, 'serve', 'Bà Sương ăn chay', 'Bữa nay rằm, bà ăn chay. Cho bà dĩa tàu hũ với rau muống, nước tương, đừng cho mỡ hành nghe con.',
     [_l('trang', 2, ['dau_hu', 'rau'], mo=False, mam='tuong', canh=False, chay=True)],
     'Bà Sương lần tràng hạt. Canh của quán nấu tôm khô nên bà khỏi.', 2, 'ram', dict(chay=True)),
    (6, 'serve', 'Chị Lụa mua hộp chay', 'Rằm rồi, gói chị hộp chay mang lên chùa: tàu hũ với rau, nước tương để riêng, đừng cho hành mỡ.',
     [_h('trang', 2, ['dau_hu', 'rau'], mo=False, mam='tuong', chay=True)], 'Chị Lụa cầm sẵn bó nhang.', 3, 'ram', dict(togo=True, chay=True)),
    (6, 'serve', 'Chị Lụa trú mưa', 'Mưa quá, cho chị hộp cơm tấm sườn bì mang về, thêm bịch canh nóng nha.', [_h('tam', 2, ['suon', 'bi'], canh=True)],
     'Chị Lụa trùm áo mưa, rau ngoài sạp đã che bạt.', 2, 'rain', dict(togo=True)),
    (2, 'serve', 'Chị Ngân ngại mưa', 'Em ơi mưa quá, cho chị hộp cơm phần: thịt kho với rau, ít cơm, nước mắm để riêng nha.',
     [_h('trang', 1, ['thit_kho', 'rau'])], 'Chị Ngân đứng dưới mái hiên, giũ dù.', 2, 'rain', dict(togo=True)),
    (1, 'serve', 'Chú Bình ngày chợ phiên', 'Chợ đông quá con ơi! Dĩa sườn bì chả, chú ăn lẹ còn chạy cuốc.', [_l('tam', 2, ['suon', 'bi', 'cha'])],
     'Khách đi chợ đứng chờ xe ôm sau lưng chú.', 2, 'market', {}),
    (3, 'serve', 'Anh Mạnh với thằng em', 'Hai dĩa sườn ốp la chín, dĩa nào cũng thêm cơm, anh với thằng em.',
     [_l('tam', 3, ['suon', 'trung_chin']), _l('tam', 3, ['suon', 'trung_chin'])], 'Thằng em anh Mạnh mới lên thành phố làm phụ hồ.', 2, 'market',
     dict(check=True)),
]
OFFICE = (2, 'office', 'Đơn cơm văn phòng của chị Ngân',
          'Em ơi, phòng chị đặt bốn hộp: hai hộp sườn bì chả, một hộp thịt kho rau, một hộp chay tàu hũ rau. '
          'Hộp nào nước mắm cũng để riêng, hộp chay thì nước tương, không hành mỡ.',
          [_h('tam', 2, ['suon', 'bi', 'cha']), _h('tam', 2, ['suon', 'bi', 'cha']), _h('trang', 2, ['thit_kho', 'rau']),
           _h('trang', 2, ['dau_hu', 'rau'], mo=False, mam='tuong', chay=True)],
          'Chị Ngân nhắn kèm danh sách: mười hai giờ đúng anh bảo vệ ra lấy.', 3, None, dict(togo=True))
KINDS = ('setup', 'serve', 'office')
STAGES = ('prep', 'pay', 'done')

# Regulars' small stories: one line per finished visit, on and on across days.
REG_STORY = {
    1: ('Chú Bình: “Cơm tấm phải có miếng sườn cháy cạnh mới ngon con ạ.”', 'Chú Bình kể hồi xưa chú chở dì Bảy đi chợ đầu mối mỗi sáng.',
        'Chú Bình để dành cho quán mấy trái chanh nhà trồng.', 'Chú Bình giới thiệu cả nhóm xe ôm đầu hẻm ra quán ăn sáng.'),
    2: ('Chị Ngân: “Cả phòng chị khen nước mắm quán em ngon nhất chợ.”', 'Chị Ngân được lên kế toán trưởng, khao cả phòng một bữa cơm tấm.',
        'Chị Ngân bảo giờ phòng chị chỉ đặt cơm ở quán mình.'),
    3: ('Anh Mạnh: “Làm hồ mà ăn ít cơm là chiều xỉu đó em.”', 'Anh Mạnh khoe công trình đầu hẻm sắp cất nóc.',
        'Anh Mạnh sửa giùm quán cái chân bàn bị khập khiễng.'),
    4: ('Nhi: “Ăn cơm dì Bảy như ăn cơm nhà.”', 'Nhi thi xong học kỳ, được học bổng, ghé quán khoe.',
        'Nhi rủ cả phòng trọ ra quán ăn mừng sinh nhật.'),
    5: ('Bà Sương: “Quán nhớ bà ăn chay, bà mừng lắm.”', 'Bà Sương dặn dì Bảy giữ sức, đừng thức khuya quá.',
        'Bà Sương mang tặng quán chậu húng quế bà trồng.'),
    6: ('Chị Lụa: “Rau muống quán xào giòn ghê, rau của chị đó!”', 'Chị Lụa để dành cho quán bó rau muống non nhất sạp.',
        'Chị Lụa rủ mấy bà bạn hàng ra quán ăn trưa.'),
}

INTRO = dict(
    title='Giới thiệu nghề: bán cơm',
    lead='Một xe cơm có tủ kính, cái bếp than nướng sườn, hai nồi cơm điện và mấy cái bàn nhựa đỏ ở đầu chợ. '
         'Dì Bảy nấu từ bốn giờ sáng, bạn đứng quầy bán giúp dì.',
    work=[('🍚', 'Nấu hai nồi: cơm tấm lưng đốt nước, cơm trắng một đốt'), ('🫙', 'Nếm chén nước mắm, mặn thì thêm nước, lạt thì thêm mắm'),
          ('🔥', 'Nhóm bếp than, nướng sườn: mỗi mặt 8–16 giây, trở một lần'), ('🍱', 'Bày khay lên tủ kính: đủ bán, đừng dư'),
          ('🍽️', 'Mỗi dĩa: xới đúng nồi, đúng số vá, gắp đúng món khách gọi'), ('🌿', 'Mỡ hành, nước mắm, chén canh theo lời khách dặn'),
          ('🥡', 'Hộp mang về: nước mắm luôn để riêng'), ('💵', 'Thu tiền, thối đúng')],
    meet=[('🛵', 'Chú Bình: cơm tấm sườn mỗi sáng'), ('🧾', 'Chị Ngân: đơn cơm hộp cho cả phòng'),
          ('👷', 'Anh Mạnh: dĩa nào cũng thêm cơm'), ('🎒', 'Nhi: sinh viên, tính từng đồng'),
          ('📿', 'Bà Sương: ăn chay ngày rằm'), ('🌧️', 'Mưa dầm, chợ phiên, ngày rằm')],
    stars=[('🍚', 'Cơm dẻo, đủ vá'), ('🍖', 'Sườn vàng đều, chín tới'), ('🍱', 'Đúng món, đúng lời dặn'),
           ('🫙', 'Nước mắm vừa miệng'), ('📿', 'Nhớ người ăn chay'), ('💵', 'Thối đúng tiền')],
)

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='flies', title='Ruồi bu quanh tủ kính', emoji='🪰', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Trưa nắng, mấy con ruồi bay vo ve quanh khay thịt kho. Cửa tủ kính để mở từ sáng.',
         options=[dict(id='close', label='Kéo cửa kính lại, giăng vợt ruồi, lau mặt tủ', hint='', effects=dict(xp=3), good=True,
                       outcome='Tủ kính đóng kín, ruồi bay đi. Khách đứng chọn món thấy sạch sẽ.'),
                  dict(id='fan', label='Bật quạt thổi ruồi', hint='', effects=dict(patience=-2), good=None,
                       outcome='Ruồi bay đi một lúc rồi quay lại, quạt thổi bay cả khăn giấy.'),
                  dict(id='ignore', label='Kệ, chợ nào chả có ruồi', hint='',
                       effects=dict(review=[2, 'Ruồi bu đầy tủ kính đồ ăn mà quán cũng kệ.', 2]), good=False,
                       outcome='Chị Ngân đứng chọn món, nhăn mặt rồi đi quán khác.')],
         default='fan'),
    dict(id='smoke', title='Khói bếp than bay vào nhà bên', emoji='💨', npc=0, min_day=2, tone='tense', at='open', weight=2, mods=None,
         text='Gió đổi chiều, khói bếp than bay thẳng vào tiệm may bên cạnh. Cô chủ tiệm may ra đứng chống nạnh.',
         options=[dict(id='move', label='Xin lỗi, dời bếp ra mép đường, quạt khói về phía chợ', hint='Khách chờ chút', effects=dict(patience=-3, xp=4), good=True,
                       outcome='Khói bay ra phía chợ. Cô chủ tiệm may gật đầu, trưa còn ra mua hộp cơm.'),
                  dict(id='later', label='Dạ, nướng xong mẻ này con dời', hint='', effects=dict(patience=-1), good=None,
                       outcome='Cô chủ tiệm may đóng cửa cái rầm.'),
                  dict(id='argue', label='“Quán bán ở đây hai chục năm rồi”', hint='',
                       effects=dict(review=[2, 'Quán cơm hun khói cả dãy phố, nói còn cãi.']), good=False,
                       outcome='Cô chủ tiệm may gọi tổ dân phố ra nhắc.')],
         default='later'),
    dict(id='ticket_seller', title='Cô bán vé số xin chén cơm', emoji='🎫', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một cô bán vé số tóc bạc, xấp vé còn dày, đứng nép bên tủ kính: “Con ơi, cô xin chén cơm với chút nước mắm thôi…”',
         options=[dict(id='plate', label='Mời cô ngồi, xới dĩa cơm có miếng thịt kho', hint='Mất một phần cơm', effects=dict(money=-3, xp=5), good=True,
                       outcome='Cô ăn chậm rãi, cảm ơn mãi. Dì Bảy nghe kể: “Làm vậy là phải đó con.”'),
                  dict(id='rice', label='Gói cho cô hộp cơm trắng với chén nước mắm', hint='', effects=dict(money=-1, xp=2), good=None,
                       outcome='Cô cầm hộp cơm, cúi đầu cảm ơn rồi đi tiếp.'),
                  dict(id='shoo', label='“Quán đang đông, cô đi chỗ khác giùm”', hint='',
                       effects=dict(review=[3, 'Bà cụ bán vé số xin chén cơm mà quán đuổi đi. Buồn.']), good=False,
                       outcome='Cô lặng lẽ đi. Mấy người khách nhìn nhau.')],
         default='rice'),
    dict(id='inspect', title='Phường kiểm tra an toàn thực phẩm', emoji='📋', npc=0, min_day=3, tone='tense', at='open', weight=2, mods=None,
         text='Hai anh cán bộ phường ghé: “Quán cho xem giấy nguồn gốc thịt, cá; tủ kính, thớt dao để sống chín riêng chưa?”',
         options=[dict(id='show', label='Đưa sổ nhập hàng, chỉ thớt sống chín riêng, đeo găng khi gắp', hint='', effects=dict(xp=5), good=True,
                       outcome='Hai anh ghi biên bản: quán sạch sẽ, có nguồn gốc rõ ràng. Còn dặn giữ vậy nha.'),
                  dict(id='later', label='Hẹn chiều dì Bảy về rồi đưa giấy', hint='', effects=dict(patience=-3), good=None,
                       outcome='Hai anh hẹn chiều quay lại, khách đứng chờ một lúc.'),
                  dict(id='envelope', label='Dúi phong bì cho “xong việc”', hint='10 xu',
                       effects=dict(money=-10, review=[1, 'Quán cơm đầu chợ dúi tiền đoàn kiểm tra, có gì khuất tất mới vậy.']), good=False,
                       outcome='Hai anh từ chối thẳng, ghi thêm một dòng vào biên bản.')],
         default='later'),
    dict(id='leftover_ask', title='Người xin mua đồ ăn hôm qua giá rẻ', emoji='🥡', npc=0, min_day=3, tone='gentle', at='open', weight=2, mods=None,
         text='Một anh bán xôi đầu hẻm hỏi: “Đồ ăn dư hôm qua quán còn không, bán rẻ anh hâm lại bán sáng.”',
         options=[dict(id='no', label='Đồ ăn qua đêm quán bỏ hết, không bán cho ai', hint='', effects=dict(xp=3), good=True,
                       outcome='Anh ấy gật gù: “Vậy mới giữ được khách hai chục năm.”'),
                  dict(id='buy', label='Rủ anh ấy mua nồi canh mới nấu sáng nay', hint='', effects=dict(money=4), good=None,
                       outcome='Anh ấy mua nửa nồi canh chua, trả tiền đàng hoàng.')],
         default='no'),
    dict(id='rain_tarp', title='Mưa tạt vào bàn ăn', emoji='🌧️', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=('rain',),
         text='Mưa xéo tạt ướt hai bàn ngoài, nước nhỏ giọt xuống chén nước mắm.',
         options=[dict(id='tarp', label='Kéo bạt, dời bàn vào mái hiên, thay chén nước mắm mới', hint='Mất chút thời gian', effects=dict(patience=-3, xp=3), good=True,
                       outcome='Khách ngồi khô ráo, ăn xong còn ngồi lại uống trà đá chờ tạnh.'),
                  dict(id='later', label='Để tạnh rồi lau', hint='', effects=dict(money=-2), good=None,
                       outcome='Hai khách ngồi ngoài bỏ dở dĩa cơm vì ướt.')],
         default='later'),
    dict(id='market_rush', title='Chợ phiên: hàng chờ dài', emoji='🛒', npc=0, min_day=2, tone='tense', at='between', weight=3, mods=('market',),
         text='Chợ phiên đông nghẹt, hàng chờ cơm tấm kéo ra tới sạp rau của chị Lụa. Vỉ sườn chỉ còn hai miếng.',
         options=[dict(id='batch', label='Nướng mẻ sườn mới, nhờ chị Lụa kêu khách xếp hàng', hint='', effects=dict(patience=4, xp=3), good=True,
                       outcome='Khói sườn thơm lừng, khách xếp hàng trật tự, không ai bỏ đi.'),
                  dict(id='rush', label='Bày ghế thêm cho khách ngồi chờ', hint='', effects=dict(patience=2), good=None,
                       outcome='Khách ngồi chờ, có người sốt ruột nhìn đồng hồ.')],
         default='rush'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='CT-S01', title='Miếng sườn còn hồng', npc=3, tone='tense', min_day=1,
         opening='Anh Mạnh cắt miếng sườn, chìa cái đĩa ra: “Em coi nè, giữa miếng thịt còn hồng hồng, ăn vô đau bụng ai chịu?”',
         swap='Bạn là anh Mạnh, làm hồ cả ngày, chỉ mong một dĩa cơm tấm tử tế.',
         facts=[dict(id='grill', title='Vỉ nướng', source='Bếp than', text='Mẻ sườn vừa rồi lật sớm, mặt dưới chỉ nướng được năm giây.'),
                dict(id='pork', title='Thịt heo', source='Dì Bảy', text='Thịt heo phải chín hẳn, không còn hồng ở giữa mới ăn được.'),
                dict(id='rack', title='Trên vỉ', source='Bếp than', text='Trên vỉ còn hai miếng sườn mới nướng vàng đều.')],
         options=[dict(id='swap', label='Xin lỗi, đổi ngay miếng sườn chín, nướng lại mẻ kia cho kỹ', requires=['grill', 'pork'], quality='good', stars=5,
                       review='Miếng sườn chưa chín nhưng quán đổi liền, xin lỗi đàng hoàng. Lần sau ăn tiếp.',
                       outcome='Anh Mạnh ăn hết dĩa, còn dặn: “Nướng kỹ nghen em.”',
                       perspectives=[dict(who='Anh Mạnh', emoji='👷', text='Sai mà sửa liền thì được.'),
                                     dict(who='Dì Bảy', emoji='👩‍🍳', text='Thịt heo thì chín mới bán, chậm chút cũng được.')]),
                  dict(id='discount', label='Bớt cho anh ít tiền', requires=['grill'], quality='ok', stars=3,
                       review='Bớt tiền thì bớt, nhưng miếng sườn sống vẫn nằm đó.',
                       outcome='Anh Mạnh lắc đầu, gạt miếng sườn ra mép dĩa.',
                       perspectives=[dict(who='Anh Mạnh', emoji='😒', text='Anh cần miếng sườn chín, đâu cần bớt tiền.'),
                                     dict(who='Dì Bảy', emoji='👩‍🍳', text='Thiếu chín là đổi, không phải bớt.')]),
                  dict(id='deny', label='“Sườn nướng than là vậy đó anh”', quality='bad', stars=1,
                       review='Sườn còn sống mà nói là vậy đó. Tối về đau bụng.',
                       outcome='Anh Mạnh đứng dậy bỏ đi, dĩa cơm còn nguyên.',
                       perspectives=[dict(who='Anh Mạnh', emoji='😠', text='Coi thường người ăn quá.'),
                                     dict(who='Chú Bình', emoji='🛵', text='Sườn hồng thì phải nướng lại chớ.')])],
         lesson='Sườn nướng mỗi mặt đủ lửa, cắt ra không còn hồng mới bán. Khách phát hiện thì đổi ngay, nướng lại.'),
    dict(id='CT-S02', title='Hộp cơm chay có mỡ hành', npc=5, tone='tense', min_day=2,
         opening='Bà Sương quay lại quầy, giọng run run: “Con ơi, hộp chay của bà có mấy cọng hành mỡ… mỡ này mỡ heo phải không con?”',
         facts=[dict(id='lard', title='Mỡ hành', source='Bếp', text='Mỡ hành của quán phi bằng mỡ heo.'),
                dict(id='said', title='Lời dặn', source='Bà Sương', text='Lúc mua bà đã dặn ăn chay, không mỡ hành.'),
                dict(id='box', title='Hộp mới', source='Tủ kính', text='Khay tàu hũ và rau muống còn đủ làm hộp khác.')],
         options=[dict(id='redo', label='Xin lỗi bà, làm hộp chay mới, không hành mỡ, nước tương riêng', requires=['lard', 'said'], quality='good', stars=5,
                       review='Quán nhận lỗi, làm hộp mới đàng hoàng. Người ăn chay yên tâm.',
                       outcome='Bà Sương nhận hộp mới, dặn: “Lần sau nhớ giùm bà nghe con.”',
                       perspectives=[dict(who='Bà Sương', emoji='📿', text='Biết lỗi là được rồi con.'),
                                     dict(who='Dì Bảy', emoji='👩‍🍳', text='Khách ăn chay thì muỗng, chén riêng, không mỡ hành.')]),
                  dict(id='scrape', label='Gạt hành mỡ ra rồi đưa lại', requires=['lard'], quality='bad', stars=2,
                       review='Gạt hành ra thì mỡ vẫn thấm vô cơm. Không được.',
                       outcome='Bà Sương cầm hộp cơm, đứng lặng một lúc rồi về.',
                       perspectives=[dict(who='Bà Sương', emoji='😔', text='Mỡ thấm rồi đâu gạt ra được.'),
                                     dict(who='Chị Lụa', emoji='🥬', text='Ăn chay là kiêng cả mỡ chứ.')]),
                  dict(id='deny', label='“Mỡ hành có chút xíu, không sao đâu bà”', quality='bad', stars=1,
                       review='Đã dặn ăn chay mà còn bảo không sao. Không ghé nữa.',
                       outcome='Bà Sương trả lại hộp cơm, không nói thêm câu nào.',
                       perspectives=[dict(who='Bà Sương', emoji='😞', text='Ăn chay là lòng thành, đâu phải chuyện chút xíu.'),
                                     dict(who='Dì Bảy', emoji='👩‍🍳', text='Mất một người khách ruột vì một muỗng mỡ.')])],
         lesson='Khách ăn chay: không mỡ hành (phi bằng mỡ heo), nước tương thay nước mắm, không canh tôm. Sai thì làm lại hộp mới.'),
    dict(id='CT-S03', title='Dĩa cơm ít quá', npc=3, tone='tense', min_day=2,
         opening='Anh Mạnh gõ muỗng vào dĩa: “Anh kêu thêm cơm mà dĩa này có hai vá. Quán bớt cơm hả em?”',
         facts=[dict(id='ladle', title='Cái vá', source='Nồi cơm', text='Dĩa thêm cơm là ba vá; dĩa này mới xới hai vá.'),
                dict(id='price', title='Giá', source='Bảng giá', text='Thêm cơm cộng một xu, anh Mạnh đã trả đủ.'),
                dict(id='pot', title='Nồi cơm', source='Bếp', text='Nồi cơm tấm còn đầy, cơm mới chín, dẻo thơm.')],
         options=[dict(id='add', label='Xin lỗi, xới thêm vá cơm, không tính tiền', requires=['ladle', 'price'], quality='good', stars=5,
                       review='Thiếu cơm mà quán xới bù liền, cười tươi. Ăn no về làm tiếp.',
                       outcome='Anh Mạnh cười khà khà: “Vậy mới được chớ!”',
                       perspectives=[dict(who='Anh Mạnh', emoji='👷', text='Làm hồ mà thiếu cơm là chiều xỉu.'),
                                     dict(who='Dì Bảy', emoji='👩‍🍳', text='Khách kêu thêm cơm là ba vá, nhớ nghe con.')]),
                  dict(id='refund', label='Trả lại một xu tiền thêm cơm', requires=['ladle'], quality='ok', stars=3,
                       review='Trả lại tiền thì được, nhưng bụng vẫn đói.',
                       outcome='Anh Mạnh cầm đồng xu, nhìn dĩa cơm vơi.',
                       perspectives=[dict(who='Anh Mạnh', emoji='🤨', text='Anh cần cơm chứ đâu cần một xu.'),
                                     dict(who='Nhi', emoji='🎒', text='Dĩa của em cũng hơi ít á.')]),
                  dict(id='deny', label='“Vá nhà em to, hai vá là nhiều rồi”', quality='bad', stars=1,
                       review='Kêu thêm cơm mà xới hai vá còn cãi. Quán kỳ.',
                       outcome='Anh Mạnh ăn hết, trả tiền, không nói gì. Mấy hôm sau không thấy anh ra quán.',
                       perspectives=[dict(who='Anh Mạnh', emoji='😠', text='Ăn ở đây cả năm mà giờ bị cãi.'),
                                     dict(who='Chú Bình', emoji='🛵', text='Có vá cơm mà mất khách ruột.')])],
         lesson='Ít cơm một vá, dĩa thường hai vá, thêm cơm ba vá. Thiếu thì xới bù, đừng để khách phải nói.'),
]


# ================================================================ small helpers
def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _who(t: dict) -> str:
    i = _npc_index(t)
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Khách'


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _p(c: dict, key: str) -> int:
    return max(1, int(kit.price(c, key, PRICES[key])))


def line_text(ln: dict) -> str:
    dishes = ', '.join(DISHES[x]['short'] for x in ln['it'])
    bits = [RICE[ln['r']]['name'] + ('' if ln['va'] == 2 else f', {VA_WORD[ln["va"]]}'), dishes]
    if not ln['mo']:
        bits.append('không hành mỡ')
    bits.append({'ruoi': 'rưới nước mắm', 'rieng': 'nước mắm để riêng', 'tuong': 'nước tương'}.get(ln['mam'], 'không nước mắm'))
    if ln['canh']:
        bits.append('có canh')
    return ' · '.join(bits)


# ================================================================ tasks
def _kind(day: int, slot: int) -> str:
    if slot == 0:
        return 'setup'
    if day >= 3 and day % 3 == 0 and slot == 2:
        return 'office'
    return 'serve'


def _pick(day: int, slot: int, mod: str) -> tuple:
    if day == 1:
        return ORDERS[min(2, slot - 1)] if slot <= 3 else ORDERS[(slot - 1) % 3]
    pool = [o for o in ORDERS if o[6] <= day and o[7] in (None, mod)]
    weighted = [o for o in pool for _ in range(3 if o[7] else 1)]
    return weighted[kit.rng(ID, day, slot).randrange(len(weighted))]


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    kind = _kind(day, slot)
    common = dict(gen=GEN, stage='prep', plates=[], price=None, cash=None, cost=0, choice=None, story=None)
    if kind == 'setup':
        note = {'rain': 'Mưa dầm: khách mua mang về nhiều, nhớ đủ hộp.', 'market': 'Chợ phiên: nướng sẵn vài miếng sườn trên vỉ.',
                'ram': 'Ngày rằm: bày thêm khay tàu hũ, rau muống cho khách ăn chay.'}.get(
            mod, 'Nấu hai nồi cơm, nếm nước mắm, nhóm bếp than, bày khay lên tủ kính rồi mở quán.')
        return kit.base_task(ID, day, slot, serial, 0, 'Dọn quán cơm đầu ngày',
                             'Dì Bảy dặn: “Dì ra chợ mua thêm rau. Con nấu hai nồi cơm, nếm lại chén nước mắm dì pha tối qua, '
                             'nhóm bếp than, bày khay lên tủ kính rồi mở quán nghe.”',
                             kind='setup', needs=dict(setup=True, note=note), **common)
    npc, k, title, opening, lines, note, _, _, flags = OFFICE if kind == 'office' else _pick(day, slot, mod)
    needs = dict(lines=copy.deepcopy(lines), note=note, togo=bool(flags.get('togo')), check=bool(flags.get('check')),
                 chay=bool(flags.get('chay')))
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind=k, needs=needs, **common)


FIXED = ('needs',)


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the stall's data
def _fresh_pot() -> dict:
    return dict(va=0, q='ok', at=0.0, c=0)


def _fresh_shop(day: int) -> dict:
    return dict(day=day, open=False)


def _fresh_today(day: int) -> dict:
    return dict(day=day, plates=0, customers=0, va=0, over_va=0, grilled=0, raw=0, burnt=0, waste=0)


def initial() -> dict:
    return dict(v=1, intro=False, shop=_fresh_shop(0), pots={k: _fresh_pot() for k in RICE}, mam=dict(q='ok', tasted=False),
                grill=dict(lit=False, b=None), rack=[], trays={k: dict(n=0, c=0) for k in TRAYS}, regulars={},
                today=_fresh_today(0), stats=dict(plates=0, customers=0, va=0, over_va=0, grilled=0, raw=0, burnt=0, waste=0, fair=0),
                desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'shop', 'mam', 'grill'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k in RICE:
        d['pots'].setdefault(k, _fresh_pot())
    for k in TRAYS:
        d['trays'].setdefault(k, dict(n=0, c=0))
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    return d


def mam_of(day: int) -> str:
    """How last night's bowl of nước mắm tastes this morning."""
    if day == 1:
        return 'man'      # the first morning teaches the taste
    r = kit.rng(ID, 'mam', day).randrange(100)
    return 'ok' if r < 45 else ('man', 'lat', 'ngot', 'chua')[r % 4]


def grill_q(side1: float, side2: float) -> str:
    def one(x):
        return 'song' if x < SIDE_OK[0] else 'ok' if x <= SIDE_OK[1] else 'xem' if x <= SIDE_BURN else 'khet'
    return max(one(side1), one(side2), key=lambda q: GRILL_RANK[q])


def pot_ready(pot: dict) -> bool:
    return pot['va'] > 0 and kit.now() >= pot['at']


# ================================================================ the actions
FREE = ('com_intro',)
TICKING = ('com_cook', 'com_tray', 'com_open', 'com_grill', 'com_serve', 'com_decline')
PHYSICAL = ('com_cook', 'com_tray', 'com_fire', 'com_grill', 'com_lift', 'com_rice', 'com_pick', 'com_egg')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'com_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Bếp than đang chờ ở đầu chợ.')
    desk = d['desk']
    if name == 'com_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở quán, quyết xong rồi bán tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở quán cơm.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc quán cơm.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    return t


def _need_open(d: dict) -> None:
    kit.need(d['shop']['open'], 'Chưa mở quán: nấu cơm, nếm nước mắm, nhóm bếp, bày khay rồi bấm “Mở quán” nhé.')


# ---------------------------------------------------------------- the morning (and refills during the day)
def _cook(s, c, d, p):
    r = kit.one_of(p.get('r'), RICE, 'Nồi cơm tấm hay nồi cơm trắng?')
    water = kit.one_of(p.get('water'), WATER, 'Đổ nước tới đâu?')
    pot = d['pots'][r]
    x = RICE[r]
    kit.need(pot['va'] <= 0, f'Nồi {_lower(x["name"])} còn cơm, bán hết rồi hẵng nấu nồi mới.')
    kit.need(kit.stock(c, x['item']) > 0, f'Hết {_lower(kit.item(ID, x["item"])["name"])} rồi. Nhập thêm ở kho nhé.')
    cost = kit.take(c, x['item'], 1)
    q = 'ok' if water == x['water'] else x['wrong'][water]
    d['pots'][r] = dict(va=POT_VA, q=q, at=round(kit.now() + COOK_S, 3), c=cost)
    return dict(message=f'🍚 Vo gạo hai nước, đổ nước {_lower(WATER[water])}, bấm nút nồi {_lower(x["name"])}. Chừng {COOK_S} giây nữa cơm chín.')


def _taste(s, c, d, p):
    m = d['mam']
    m['tasted'] = True
    return dict(message=f'🥄 Chấm đầu đũa nếm thử: nước mắm {TASTE[m["q"]]}')


def _fix(s, c, d, p):
    add = kit.one_of(p.get('add'), FIX, 'Thêm gì vào chén nước mắm?')
    m = d['mam']
    kit.need(m['tasted'], 'Nếm thử trước đã rồi hẵng pha thêm.')
    before = m['q']
    if before == 'ok':
        m['q'] = SPOIL[add]
        tail = f'Nếm lại: {TASTE[m["q"]]} Lỡ tay rồi, chỉnh lại cho vừa.'
    elif FIX[add] == before:
        m['q'] = 'ok'
        tail = f'Nếm lại: {TASTE["ok"]}'
    else:
        tail = f'Nếm lại: vẫn {TASTE[before]}'
    return dict(message=f'🫙 {ADD_LABEL[add]}, khuấy đều. {tail}')


def _fire(s, c, d, p):
    g = d['grill']
    kit.need(not g['lit'], 'Bếp than đang cháy đỏ rồi.')
    g['lit'] = True
    return dict(message='🔥 Xếp than, mồi giấy, quạt nan phành phạch: than hồng đều, vỉ nướng nóng rồi.')


def _tray(s, c, d, p):
    k = kit.one_of(p.get('item'), TRAYS, 'Khay món này không có.')
    tray = d['trays'][k]
    kit.need(tray['n'] + TRAY_N[k] <= TRAY_MAX, f'Khay {_lower(DISHES[k]["name"])} còn đầy, bán bớt rồi bày thêm.')
    kit.need(kit.stock(c, k) > 0, f'Kho hết {_lower(kit.item(ID, k)["name"])}. Nhập thêm ở kho nhé.')
    cost = kit.take(c, k, 1)
    tray['n'] += TRAY_N[k]
    tray['c'] += cost
    return dict(message=f'{DISHES[k]["emoji"]} Bày khay {_lower(DISHES[k]["name"])} lên tủ kính: {tray["n"]} phần.')


def _open(s, c, d, p):
    t = _task(c, p, ('setup',))
    sh = d['shop']
    kit.need(not sh['open'], 'Quán mở rồi.')
    m, pots = d['mam'], d['pots']
    if not any(pot['va'] > 0 for pot in pots.values()):
        t['mistakes'] += 1
        cq.slip(t, 'no_rice', 2, 'Quán mở mà chưa có nồi cơm nào, khách ngồi chờ dài cổ.', 'chưa nấu cơm')
    elif any(pot['va'] > 0 and pot['q'] != 'ok' for pot in pots.values()):
        t['mistakes'] += 1
        cq.slip(t, 'rice_water', 1, 'Nồi cơm đong nước chưa đúng, cơm nhão hoặc sượng cả nồi.', 'đong nước nồi cơm chưa đúng')
    if not m['tasted']:
        t['mistakes'] += 1
        cq.slip(t, 'no_taste', 1, 'Chưa nếm chén nước mắm đã bán, mặn lạt thế nào cũng không biết.', 'chưa nếm nước mắm')
    elif m['q'] != 'ok':
        t['mistakes'] += 1
        cq.slip(t, 'mam_off', 1, f'Nước mắm còn {TASTE[m["q"]].rstrip(".")}', 'nước mắm chưa vừa')
    if not d['grill']['lit']:
        t['mistakes'] += 1
        cq.slip(t, 'no_fire', 1, 'Chưa nhóm bếp than, khách cơm tấm phải chờ nướng sườn.', 'chưa nhóm bếp')
    if not any(tr['n'] > 0 for tr in d['trays'].values()):
        t['mistakes'] += 1
        cq.slip(t, 'no_tray', 1, 'Tủ kính trống trơn, khách cơm phần không có gì để chọn.', 'chưa bày khay')
    sh['open'] = True
    kit.start_work(t)
    ok = not cq.slips(t)
    kit.complete(s, c, t, 0, 'Nấu cơm, nếm nước mắm, nhóm bếp, bày tủ kính.')
    return dict(message='🍚 Mở quán! ' + ('Dì Bảy nhắn: “Giỏi lắm con, bán đắt nghe!”' if ok else 'Dì Bảy nhắn: “Mở đi con, mai nhớ kỹ hơn nghe.”'),
                celebrate=ok)


# ---------------------------------------------------------------- the grill
def _grill(s, c, d, p):
    g = d['grill']
    kit.need(g['lit'], 'Chưa nhóm bếp than.')
    kit.need(g['b'] is None, 'Vỉ đang có mẻ sườn, gắp ra rồi hẵng nướng mẻ mới.')
    n = kit.integer(p.get('n', 1), 1, BATCH_MAX)
    kit.need(len(d['rack']) + n <= RACK_MAX, f'Khay giữ ấm chỉ để được {RACK_MAX} miếng, bán bớt đã.')
    kit.need(kit.stock(c, 'suon') >= n, f'Kho còn {kit.stock(c, "suon")} miếng sườn ướp. Nhập thêm ở kho nhé.')
    cost = kit.take(c, 'suon', n)
    g['b'] = dict(n=n, start=round(kit.now(), 3), flip=None, c=cost)
    return dict(message=f'🍖 Đặt {n} miếng sườn lên vỉ, mỡ chảy xèo xèo. Canh lửa rồi trở mặt nhé.')


def _flip(s, c, d, p):
    b = d['grill']['b']
    kit.need(b, 'Trên vỉ chưa có sườn.')
    kit.need(b['flip'] is None, 'Đã trở mặt rồi, giờ canh mặt kia.')
    b['flip'] = round(max(b['start'], kit.tap_now(p)), 3)
    side = b['flip'] - b['start']
    look = 'mặt dưới còn hồng' if side < SIDE_OK[0] else 'mặt dưới vàng cánh gián' if side <= SIDE_OK[1] else 'mặt dưới xém cạnh' if side <= SIDE_BURN else 'mặt dưới cháy đen'
    return dict(message=f'🔄 Trở mặt sườn sau {side:.0f} giây: {look}.')


def _lift(s, c, d, p):
    g = d['grill']
    b = g['b']
    kit.need(b, 'Trên vỉ chưa có sườn.')
    at = max(b['start'], kit.tap_now(p))
    if b['flip'] is None:
        q = 'song'
        side = at - b['start']
        how = f'Chưa trở mặt: một mặt nướng {side:.0f} giây, mặt kia còn sống.'
    else:
        q = grill_q(b['flip'] - b['start'], at - b['flip'])
        how = f'Hai mặt {b["flip"] - b["start"]:.0f} và {at - b["flip"]:.0f} giây.'
    per, extra = divmod(b['c'], b['n'])
    for i in range(b['n']):
        d['rack'].append(dict(q=q, c=per + (1 if i < extra else 0)))
    g['b'] = None
    d['today']['grilled'] += b['n']
    d['stats']['grilled'] += b['n']
    return dict(message=f'🍖 Gắp {b["n"]} miếng sườn ra khay giữ ấm: {GRILL_NOTE[q]}. {how}',
                celebrate=q == 'ok')


def _toss(s, c, d, p):
    kit.need(d['rack'], 'Khay giữ ấm trống.')
    i = kit.integer(p.get('i'), 0, len(d['rack']) - 1)
    pc = d['rack'].pop(i)
    kit.waste(c, 'suon', 1, pc['c'], f'Miếng sườn {GRILL_NOTE[pc["q"]]}')
    d['today']['waste'] += pc['c']
    d['stats']['waste'] += pc['c']
    return dict(message=f'🗑️ Bỏ miếng sườn {GRILL_NOTE[pc["q"]]}.')


# ---------------------------------------------------------------- building a plate
def _need_prep(t: dict) -> None:
    kit.need(t['known'], 'Hỏi khách gọi gì đã nhé.')
    kit.need(t['stage'] == 'prep', 'Đơn này đã tính tiền rồi.')


def _plate_of(t: dict, p: dict) -> dict:
    kit.need(t['plates'], 'Lấy dĩa hoặc hộp trước đã.')
    if p.get('plate') is not None:
        return t['plates'][kit.integer(p.get('plate'), 0, len(t['plates']) - 1)]
    return t['plates'][-1]


def _plate(s, c, d, p):
    t = _task(c, p, ('serve', 'office'))
    _need_open(d)
    _need_prep(t)
    v = kit.one_of(p.get('v'), VESSELS, 'Dĩa hay hộp?')
    kit.need(len(t['plates']) < PLATES_MAX, 'Quầy hết chỗ đặt dĩa rồi.')
    cost = 0
    if v == 'hop':
        kit.need(kit.stock(c, 'hop') > 0, 'Hết hộp giấy rồi. Nhập thêm ở kho nhé.')
        cost = kit.take(c, 'hop', 1)
    t['plates'].append(dict(v=v, r=None, va=0, it=[], x=[], mo=False, mam=None, canh=False, c=cost))
    t['cost'] += cost
    kit.start_work(t)
    return dict(message=f'{VESSELS[v]["emoji"]} Lấy {_lower(VESSELS[v]["name"])}.')


def _rice(s, c, d, p):
    t = _task(c, p, ('serve', 'office'))
    _need_open(d)
    _need_prep(t)
    pl = _plate_of(t, p)
    r = kit.one_of(p.get('r'), RICE, 'Xới nồi nào?')
    pot = d['pots'][r]
    x = RICE[r]
    kit.need(pot['va'] > 0, f'Nồi {_lower(x["name"])} hết cơm. Nấu nồi mới nhé.')
    left = pot['at'] - kit.now()
    kit.need(left <= 0, f'Nồi {_lower(x["name"])} chưa chín, chờ chừng {max(1, round(left))} giây nữa.')
    kit.need(pl['va'] < VA_MAX, 'Dĩa đầy cơm rồi.')
    per = pot['c'] // POT_VA
    pot['va'] -= 1
    pl['va'] += 1
    pl['r'] = r if pl['r'] in (None, r) else 'mix'
    if pot['q'] != 'ok' and pot['q'] not in pl['x']:
        pl['x'].append(pot['q'])
    pl['c'] += per
    t['cost'] += per
    d['today']['va'] += 1
    d['stats']['va'] += 1
    kit.start_work(t)
    warn = f' ⚠️ Cơm {RICE_NOTE[pot["q"]]}.' if pot['q'] != 'ok' else ''
    return dict(message=f'{x["emoji"]} Xới một vá {_lower(x["name"])}: dĩa có {pl["va"]} vá ({VA_WORD[min(pl["va"], 4)]}).{warn}')


def _dish(s, c, d, p):
    t = _task(c, p, ('serve', 'office'))
    _need_open(d)
    _need_prep(t)
    pl = _plate_of(t, p)
    k = kit.one_of(p.get('item'), [x for x in DISHES if DISHES[x]['src'] != 'pan'], 'Món này không có.')
    kit.need(len(pl['it']) < ITEMS_MAX, 'Dĩa đầy món rồi.')
    if k == 'suon':
        kit.need(d['rack'], 'Khay giữ ấm hết sườn. Nướng mẻ mới nhé.')
        i = kit.integer(p.get('i', 0), 0, len(d['rack']) - 1)
        pc = d['rack'].pop(i)
        cost = pc['c']
        if pc['q'] != 'ok' and pc['q'] not in pl['x']:
            pl['x'].append(pc['q'])
        tail = f' ⚠️ Miếng này {GRILL_NOTE[pc["q"]]}.' if pc['q'] != 'ok' else ''
    else:
        tray = d['trays'][k]
        kit.need(tray['n'] > 0, f'Khay {_lower(DISHES[k]["name"])} hết rồi. Bày thêm khay từ kho nhé.')
        cost = tray['c'] // tray['n']
        tray['n'] -= 1
        tray['c'] -= cost
        tail = ''
    pl['it'].append(k)
    pl['c'] += cost
    t['cost'] += cost
    kit.start_work(t)
    return dict(message=f'{DISHES[k]["emoji"]} Gắp {_lower(DISHES[k]["name"])} lên {"hộp" if pl["v"] == "hop" else "dĩa"}.{tail}')


def _egg(s, c, d, p):
    t = _task(c, p, ('serve', 'office'))
    _need_open(d)
    _need_prep(t)
    pl = _plate_of(t, p)
    how = kit.one_of(p.get('how'), ('dao', 'chin'), 'Lòng đào hay chín kỹ?')
    kit.need(len(pl['it']) < ITEMS_MAX, 'Dĩa đầy món rồi.')
    kit.need(kit.stock(c, 'trung') > 0, 'Hết trứng rồi. Nhập thêm ở kho nhé.')
    cost = kit.take(c, 'trung', 1)
    k = 'trung_' + how
    pl['it'].append(k)
    pl['c'] += cost
    t['cost'] += cost
    kit.start_work(t)
    return dict(message='🍳 Đập trứng vào chảo mỡ nóng, ' + ('lòng đỏ còn sóng sánh: ốp la lòng đào.' if how == 'dao' else 'lật hai mặt: ốp la chín kỹ.'))


def _mo(s, c, d, p):
    t = _task(c, p, ('serve', 'office'))
    _need_prep(t)
    pl = _plate_of(t, p)
    want = p.get('on')
    pl['mo'] = (not pl['mo']) if want is None else bool(want)
    return dict(message='🌿 Chan một muỗng mỡ hành lên cơm.' if pl['mo'] else 'Bỏ mỡ hành ra.')


def _mam(s, c, d, p):
    t = _task(c, p, ('serve', 'office'))
    _need_prep(t)
    pl = _plate_of(t, p)
    m = p.get('m')
    if m in (None, '', 'none'):
        pl['mam'] = None
        return dict(message='Không lấy nước mắm.')
    m = kit.one_of(m, MAM, 'Nước mắm thế nào?')
    pl['mam'] = m
    box = pl['v'] == 'hop'
    return dict(message={'ruoi': '🫙 Rưới một vá nước mắm lên cơm.' if not box else '🫙 Rưới nước mắm vào hộp.',
                         'rieng': '🫙 Múc nước mắm ra ' + ('bịch nhỏ, cột thun bỏ kèm hộp.' if box else 'chén nhỏ đặt cạnh dĩa.'),
                         'tuong': '🫘 Lấy nước tương ' + ('bịch riêng.' if box else 'chén riêng.')}[m])


def _canh(s, c, d, p):
    t = _task(c, p, ('serve', 'office'))
    _need_prep(t)
    pl = _plate_of(t, p)
    want = p.get('on')
    pl['canh'] = (not pl['canh']) if want is None else bool(want)
    box = pl['v'] == 'hop'
    return dict(message=('🥣 Múc ' + ('bịch canh nóng, cột chặt.' if box else 'chén canh chua nóng.')) if pl['canh'] else 'Bỏ canh ra.')


def _drop(s, c, d, p):
    """Throw away the plate being made (a wrong pot, a wrong dish)."""
    t = _task(c, p, ('serve', 'office'))
    _need_prep(t)
    kit.need(t['plates'], 'Chưa có dĩa nào.')
    pl = t['plates'].pop()
    t['cost'] = max(0, t['cost'] - pl['c'])
    if pl['c']:
        kit.waste(c, pl['it'][0] if pl['it'] else ('hop' if pl['v'] == 'hop' else 'gao'), 1, pl['c'], 'Dĩa cơm làm lại')
        d['today']['waste'] += pl['c']
        d['stats']['waste'] += pl['c']
    return dict(message=f'🗑️ Bỏ {"hộp" if pl["v"] == "hop" else "dĩa"} vừa làm, làm lại cái khác.')


# ---------------------------------------------------------------- handing it over
def plate_price(c: dict, pl: dict) -> int:
    v = _p(c, 'com_tam' if pl['r'] == 'tam' else 'com_trang') + (_p(c, 'them') if pl['va'] >= 3 else 0)
    v += sum(_p(c, DISHES[k]['price']) for k in pl['it'])
    if pl['v'] == 'hop':
        v += _p(c, 'hop')
    return v


def _match(t: dict) -> tuple[list, list, list]:
    """Pair the plates on the counter with the lines of the order by their dishes: (pairs, lines left, plates left)."""
    plates = list(range(len(t['plates'])))
    pairs, left = [], []
    for li, ln in enumerate(t['needs']['lines']):
        want = sorted(ln['it'])
        hit = next((pi for pi in plates if sorted(t['plates'][pi]['it']) == want), None)
        if hit is None:
            left.append(li)
        else:
            plates.remove(hit)
            pairs.append((li, hit))
    return pairs, left, plates


def _checks(c: dict, d: dict, t: dict, pairs: list, left: list, extra: list) -> None:
    """Record what the customer will notice at the hand-over."""
    n = t['needs']
    if left:
        t['mistakes'] += 1
        ln = n['lines'][left[0]]
        cq.slip(t, 'missing', 2, f'Tôi gọi {", ".join(DISHES[k]["short"] for k in ln["it"])} mà dĩa không đúng món.', 'sai món, thiếu món')
    if extra:
        t['mistakes'] += 1
        cq.slip(t, 'extra', 1, 'Có dĩa tôi đâu có gọi.', 'đưa thừa món')
    flags = {f for pl in t['plates'] for f in pl['x']}
    if 'song' in flags:
        t['mistakes'] += 1
        d['today']['raw'] += 1
        d['stats']['raw'] += 1
        cq.slip(t, 'raw', 3, 'Miếng sườn cắt ra còn hồng ở giữa, thịt heo chưa chín!', 'bán sườn chưa chín', safety=True)
    if 'khet' in flags:
        t['mistakes'] += 1
        d['today']['burnt'] += 1
        d['stats']['burnt'] += 1
        cq.slip(t, 'burnt', 1, 'Miếng sườn cháy khét, đắng nghét.', 'sườn cháy khét')
    if flags & {'nhao', 'suong'}:
        t['mistakes'] += 1
        cq.slip(t, 'rice_bad', 1, 'Cơm nhão nhoẹt, dính bết.' if 'nhao' in flags else 'Cơm sượng, nhai còn hột.', 'cơm nấu chưa đúng nước')
    if d['mam']['q'] != 'ok' and any(pl['mam'] in ('ruoi', 'rieng') for pl in t['plates']):
        t['mistakes'] += 1
        cq.slip(t, 'mam_taste', 1, f'Nước mắm {TASTE[d["mam"]["q"]].rstrip(".")}', 'nước mắm pha chưa vừa')
    for li, pi in pairs:
        ln, pl = n['lines'][li], t['plates'][pi]
        tag = str(li)
        if pl['r'] != ln['r']:
            t['mistakes'] += 1
            cq.slip(t, 'pot_' + tag, 1, 'Tôi kêu cơm tấm mà xới cơm trắng.' if ln['r'] == 'tam' else 'Tôi ăn cơm trắng mà xới cơm tấm.', 'xới nhầm nồi')
        if pl['va'] < ln['va']:
            t['mistakes'] += 1
            cq.slip(t, 'less_' + tag, 2 if n.get('check') else 1, 'Kêu thêm cơm mà dĩa có chút xíu.' if ln['va'] >= 3 else 'Dĩa cơm ít quá.', 'xới thiếu cơm')
        elif ln['va'] == 1 and pl['va'] >= 3:
            t['mistakes'] += 1
            cq.slip(t, 'more_' + tag, 1, 'Đã dặn ít cơm mà xới cả núi.', 'dặn ít cơm mà xới nhiều')
        elif pl['va'] > ln['va']:
            d['today']['over_va'] += pl['va'] - ln['va']
            d['stats']['over_va'] += pl['va'] - ln['va']
        if ln['chay'] and (pl['mo'] or pl['mam'] in ('ruoi', 'rieng') or pl['canh']):
            t['mistakes'] += 1
            cq.slip(t, 'chay', 3, 'Đã dặn ăn chay mà còn mỡ hành, nước mắm, canh tôm!', 'đồ mặn cho người ăn chay')
        else:
            if ln['mo'] and not pl['mo']:
                t['mistakes'] += 1
                cq.slip(t, 'mo_' + tag, 1, 'Cơm tấm mà không có mỡ hành, khô khốc.', 'quên mỡ hành')
            elif not ln['mo'] and pl['mo']:
                t['mistakes'] += 1
                cq.slip(t, 'nomo_' + tag, 1, 'Đã dặn không hành mà vẫn chan mỡ hành.', 'chan mỡ hành khách không ăn')
            if ln['canh'] and not pl['canh']:
                t['mistakes'] += 1
                cq.slip(t, 'canh_' + tag, 1, 'Quên chén canh của tôi rồi.', 'quên canh')
        if pl['mam'] is None:
            t['mistakes'] += 1
            cq.slip(t, 'nomam_' + tag, 1, 'Cơm tấm mà không có nước mắm sao ăn.' if not ln['chay'] else 'Không có chén nước tương nào.', 'quên nước mắm')
        elif ln['mam'] == 'tuong' and pl['mam'] != 'tuong' and not ln['chay']:
            t['mistakes'] += 1
            cq.slip(t, 'tuong_' + tag, 1, 'Tôi xin nước tương mà.', 'nhầm nước tương')
        elif ln['mam'] == 'tuong' and pl['mam'] != 'tuong':
            pass                                   # named above (chay)
        elif pl['v'] == 'hop' and pl['mam'] == 'ruoi':
            t['mistakes'] += 1
            cq.slip(t, 'soggy_' + tag, 1, 'Nước mắm rưới thẳng vô hộp, về tới nơi cơm nhão nhoẹt.', 'rưới nước mắm vào hộp mang về')
        elif ln['mam'] == 'ruoi' and pl['mam'] == 'tuong':
            t['mistakes'] += 1
            cq.slip(t, 'tuong_' + tag, 1, 'Cơm tấm mà chan nước tương?', 'nhầm nước tương')
        togo = n.get('togo')
        if (pl['v'] == 'hop') != bool(togo):
            t['mistakes'] += 1
            cq.slip(t, 'vessel', 1, 'Tôi mua mang về mà đưa dĩa.' if togo else 'Tôi ngồi ăn đây mà đưa hộp.', 'nhầm dĩa với hộp')


def _serve(s, c, d, p):
    t = _task(c, p, ('serve', 'office'))
    _need_open(d)
    _need_prep(t)
    kit.need(t['plates'], 'Chưa có dĩa nào trên quầy.')
    kit.need(all(pl['va'] > 0 for pl in t['plates']), 'Còn dĩa chưa xới cơm.')
    pairs, left, extra = _match(t)
    _checks(c, d, t, pairs, left, extra)
    t['price'] = max(1, sum(plate_price(c, t['plates'][pi]) for _, pi in pairs)) if pairs else 1
    t['stage'] = 'pay'
    n = len(t['plates'])
    d['today']['plates'] += n
    d['stats']['plates'] += n
    t['cash'] = till.new(t['price'], t['id'], c=c, t=t)
    what = 'hộp cơm' if t['needs'].get('togo') else 'dĩa cơm'
    return dict(message=f'🍚 Đưa {n} {what} cho {_who(t)} · {t["price"]} xu. Khách đưa {sum(t["cash"]["tender"])} xu: thối lại cho đúng.')


def _decline(s, c, d, p):
    """Out of what the customer wants: say so honestly."""
    t = _task(c, p, ('serve', 'office'))
    kit.need(t['known'] and t['stage'] == 'prep', 'Không phải lúc này.')
    for pl in t['plates']:
        if pl['c']:
            kit.waste(c, pl['it'][0] if pl['it'] else 'gao', 1, pl['c'], 'Đơn không bán được')
    t['plates'], t['cost'], t['choice'] = [], 0, 'decline'
    kit.start_work(t)
    msg = _finish(s, c, d, t, 0, f'Nói thật với {_who(t)}: quán hết món khách gọi, hẹn bữa sau.')
    return dict(message='🙏 ' + msg)


def _pay(s, c, d, p):
    t = _task(c, p, ('serve', 'office'))
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    who = _who(t)
    rec = t['cash']
    chk = till.check(s, c, t, rec, p.get('change'), who)
    if chk['stop']:
        return dict(message='💵 ' + chk['message'], correct=False)
    react = cq.react(s, c, t, t['price'], who=who)
    st = till.settle(s, c, t, rec, react, who)
    net = react['pay'] - st['loss']
    d['today']['customers'] += 1
    d['stats']['customers'] += 1
    if not cq.slips(t):
        d['stats']['fair'] += 1
    parts = [x for x in (react['message'], st['message']) if x]
    msg = _finish(s, c, d, t, max(0, net), ' '.join(parts))
    if net < 0:
        lost = min(-net, c['money'])
        if lost:
            kit.money(s, c, -lost, f'Thối dư cho khách: {t["title"]}'[:120], t['id'], 'change_loss')
    given = sum(rec['change'])
    head = f'💵 Thu {t["price"]} xu' + (f', thối {given} xu.' if given else '.')
    return dict(message=f'{head} {msg}'.strip(), celebrate=not cq.slips(t))


def _short(s, c, p):
    t = _task(c, p)
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    return till.short_action(s, c, t, t['cash'], p, _who(t))


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
    t['stage'] = 'done'
    kit.complete(s, c, t, max(0, int(reward)), (narrative or t['title'])[:300])
    return f'{narrative} 💬 {story}'.strip() if story else narrative


ACTIONS = {
    'com_cook': _cook, 'com_taste': _taste, 'com_fix': _fix, 'com_fire': _fire, 'com_tray': _tray, 'com_open': _open,
    'com_grill': _grill, 'com_flip': _flip, 'com_lift': _lift, 'com_toss': _toss,
    'com_plate': _plate, 'com_rice': _rice, 'com_pick': _dish, 'com_egg': _egg, 'com_mo': _mo, 'com_mam': _mam, 'com_canh': _canh,
    'com_drop': _drop, 'com_serve': _serve, 'com_decline': _decline, 'com_pay': _pay,
    'com_short': lambda s, c, d, p: _short(s, c, p),
}
NO_TICK = tuple(sorted({'com_intro', 'com_desk', *ACTIONS} - set(TICKING)))


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['shop'] = _fresh_shop(day)
    d['today'] = _fresh_today(day)
    d['mam'] = dict(q=mam_of(day), tasted=False)
    d['grill'] = dict(lit=False, b=None)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    setup = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] == day
                  and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if setup is None and not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        setup = make_task(day, 0, c['turn'])
        c['tasks'].append(setup)
        on_task(s, c, setup)
    if setup:
        c['active_task'] = setup['id']
        setup['deferred'] = False
    elif c['active_task'] and not any(t['id'] == c['active_task'] and t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks']):
        kit.eng().next_active(c)
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')


def _throw(c: dict, d: dict, item: str, qty: int, value: int, reason: str) -> int:
    if qty <= 0:
        return 0
    kit.waste(c, item, qty, value, reason)
    d['today']['waste'] += value
    d['stats']['waste'] += value
    return value


LOW = dict(gao_tam=1, gao=1, suon=4, trung=3, bi=1, cha=1, ca_kho=1, thit_kho=1, rau=1, dau_hu=1, hop=6)


def on_close(s: dict, c: dict) -> dict:
    """Cooked food does not keep: what is left in the case, on the rack and in the pots goes out tonight."""
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    today = d['today']
    lines = [f'🍚 Bán {today["plates"]} dĩa, hộp cho {today["customers"]} khách, xới {today["va"]} vá cơm.']
    dumped = []
    for k in TRAYS:
        tr = d['trays'][k]
        if tr['n'] > 0:
            _throw(c, d, k, 1, tr['c'], 'Đồ ăn còn dư cuối ngày')
            dumped.append(dict(id=k, n=tr['n']))
        d['trays'][k] = dict(n=0, c=0)
    rack = d['rack']
    if rack:
        _throw(c, d, 'suon', len(rack), sum(pc['c'] for pc in rack), 'Sườn nướng còn dư cuối ngày')
        dumped.append(dict(id='suon', n=len(rack)))
    b = d['grill']['b']
    if b:
        _throw(c, d, 'suon', b['n'], b['c'], 'Mẻ sườn bỏ quên trên vỉ')
    d['rack'] = []
    d['grill'] = dict(lit=False, b=None)
    rice_left = 0
    for r, pot in d['pots'].items():
        if pot['va'] > 0:
            _throw(c, d, RICE[r]['item'], 1, pot['c'] * pot['va'] // POT_VA, 'Cơm nguội cuối ngày')
            rice_left += pot['va']
        d['pots'][r] = _fresh_pot()
    if dumped or rice_left:
        what = [f'{x["n"]} phần {DISHES[x["id"]]["short"]}' for x in dumped] + ([f'{rice_left} vá cơm'] if rice_left else [])
        worth = f' ({today["waste"]} xu)' if today['waste'] else ''
        lines.append(f'🗑️ Đồ nấu không để qua đêm: bỏ {", ".join(what)}{worth}. Mai bày khay vừa đủ bán nghe con.')
    if today['raw']:
        lines.append(f'🍖 Có {today["raw"]} lần sườn chưa chín tới tay khách. Dì Bảy dặn: mỗi mặt đủ tám giây trở lên mới trở.')
    if today['over_va']:
        lines.append(f'🍚 Xới dư {today["over_va"]} vá so với lời khách gọi.')
    if desk_note:
        lines.append(desk_note)
    d['shop'].update(open=False)
    low = [dict(id=x['id'], name=x['name'], n=kit.stock(c, x['id'])) for x in ITEMS if kit.stock(c, x['id']) <= LOW[x['id']]]
    tm = mod_of(c['day'] + 1)
    return dict(lines=lines, dumped=dumped, rice_left=rice_left, waste=today['waste'], low=low,
                tomorrow=dict(emoji=tm['emoji'], label=tm['label'], hint=tm['hint']),
                plates=today['plates'], customers=today['customers'], raw=today['raw'], over=today['over_va'])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 85 else 4 if p >= 65 else 3 if p >= 45 else 2
    codes = {x['code'] for x in cq.slips(t)}
    if t['kind'] == 'setup':
        kitchen = 5 - len(codes & {'no_rice', 'rice_water', 'no_fire'})
        taste = 5 - len(codes & {'no_taste', 'mam_off', 'no_tray'}) * 2
        return dict(criteria=[dict(key='kitchen', label='Cơm chín, bếp đỏ', score=max(2, kitchen), note='hai nồi cơm đúng nước' if kitchen == 5 else 'bếp chưa sẵn'),
                              dict(key='taste', label='Nước mắm vừa, tủ kính đầy', score=max(1, taste), note='nếm kỹ, bày đủ' if taste == 5 else 'còn sót khâu chuẩn bị')])
    if t.get('choice') == 'decline':
        return dict(criteria=[dict(key='honest', label='Nói thật', score=5, note='hết món thì nói thật'),
                              dict(key='order', label='Có món đúng ý', score=3, note='lần này chưa có')])
    pre = lambda *xs: any(k.startswith(xs) for k in codes)
    order = 2 if 'missing' in codes else 4 if codes & {'extra', 'vessel'} or pre('pot_') else 5
    rice = 2 if pre('less_') and t['needs'].get('check') else 3 if pre('less_', 'more_') or 'rice_bad' in codes else 5
    taste = 1 if 'raw' in codes else 3 if codes & {'burnt', 'mam_taste'} or pre('mo_', 'nomo_', 'nomam_', 'tuong_', 'soggy_', 'canh_') else 5
    care = 1 if codes & {'raw', 'chay'} else 5
    return dict(criteria=[dict(key='order', label='Đúng món', score=order, note='đúng món, đúng dĩa' if order == 5 else 'món chưa đúng ý'),
                          dict(key='rice', label='Cơm đủ vá, dẻo', score=rice, note='đủ cơm, dẻo thơm' if rice == 5 else 'cơm chưa đúng ý'),
                          dict(key='taste', label='Sườn, nước mắm vừa miệng', score=taste, note='sườn vàng, mắm vừa' if taste == 5 else 'chưa vừa miệng'),
                          dict(key='care', label='An toàn, nhớ lời dặn', score=care, note='chín kỹ, nhớ ăn chay' if care == 5 else 'chưa an toàn'),
                          dict(key='speed', label='Nhanh gọn', score=speed, note=f'chờ còn {p}% kiên nhẫn')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return ('Dì Bảy dặn: nồi cơm tấm đổ nước lưng đốt ngón tay, nồi cơm trắng một đốt; nếm chén nước mắm, mặn thì thêm nước, '
                'lạt thì thêm mắm; nhóm bếp than; bày khay lên tủ kính rồi mở quán. ' + n['note'])
    lines = '; '.join(line_text(x) for x in n['lines'])
    tail = ' Mang về.' if n.get('togo') else ''
    if n.get('chay'):
        tail += ' ⚠️ Ăn chay.'
    return f'{_who(t)} gọi: {lines}.{tail} {n["note"]}'


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
    v['cash'] = till.public(t.get('cash'))
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    stock = {x['id']: kit.stock(c, x['id']) for x in ITEMS} if c['ext'].get('inv') else {}
    mam = d['mam']
    return dict(intro=d['intro'], shop=d['shop'], pots=d['pots'], mam=dict(tasted=mam.get('tasted'), q=mam.get('q') if mam.get('tasted') else None),
                grill=d['grill'], rack=d['rack'], trays=d['trays'], stock=stock,
                mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                today=d['today'], stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                desk=kit.desk_public(d['desk'], DESK, ID))


def content() -> dict:
    return dict(rice=RICE, water=WATER, pot_va=POT_VA, cook_s=COOK_S, va_max=VA_MAX, va_word={str(k): v for k, v in VA_WORD.items()},
                rice_note=RICE_NOTE, dishes=DISHES, trays=list(TRAYS), tray_n=TRAY_N, tray_max=TRAY_MAX, vessels=VESSELS, mam=MAM,
                fix=ADD_LABEL, fix_for=FIX, taste=TASTE, batch_max=BATCH_MAX, rack_max=RACK_MAX, side_ok=list(SIDE_OK), side_burn=SIDE_BURN,
                grill_note=GRILL_NOTE, prices=PRICES, denoms=list(till.DENOMS), intro=INTRO,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE], items_max=ITEMS_MAX, plates_max=PLATES_MAX)


def hint(c: dict, t: dict) -> str:
    if t.get('kind') == 'setup':
        return 'Nấu nồi tấm (lưng đốt) và nồi trắng (một đốt) → nếm nước mắm, chỉnh cho vừa → nhóm bếp than → bày khay → Mở quán.'
    return 'Hỏi khách → lấy dĩa / hộp → xới đúng nồi, đủ vá → gắp món → mỡ hành, nước mắm, canh theo lời dặn → đưa cơm → thu tiền.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'grill':
        d = _data(c)
        if not d['grill']['lit']:
            d['grill']['lit'] = True
            return 'Đã nhóm bếp than, quạt cho than hồng đều.'
        return 'Đã quạt than, cời tro cho bếp cháy đều.'
    if e.get('role') == 'wash':
        return 'Đã rửa chén dĩa, lau bàn ghế sạch sẽ.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu quán cơm sai.')


def _vnum(x, lo, hi) -> None:
    kit.need(type(x) in (int, float) and lo <= x <= hi, 'Dữ liệu quán cơm sai.')


def _vline(ln) -> None:
    kit.need(isinstance(ln, dict) and set(ln) == {'r', 'va', 'it', 'mo', 'mam', 'canh', 'chay'} and ln['r'] in RICE
             and ln['mam'] in MAM and isinstance(ln['it'], list) and 1 <= len(ln['it']) <= ITEMS_MAX
             and all(k in DISHES for k in ln['it']), 'Món khách gọi sai.')
    kit.integer(ln['va'], 1, VA_MAX)
    for k in ('mo', 'canh', 'chay'):
        _vbool(ln[k])


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc quán cơm không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc quán cơm sai.')
    n = t.get('needs')
    if t['kind'] != 'setup':
        kit.need(isinstance(n, dict) and isinstance(n.get('lines'), list) and 1 <= len(n['lines']) <= PLATES_MAX, 'Món khách gọi sai.')
        for ln in n['lines']:
            _vline(ln)
    plates = t.get('plates')
    kit.need(isinstance(plates, list) and len(plates) <= PLATES_MAX, 'Dĩa trên quầy sai.')
    for pl in plates:
        kit.need(isinstance(pl, dict) and set(pl) == {'v', 'r', 'va', 'it', 'x', 'mo', 'mam', 'canh', 'c'} and pl['v'] in VESSELS
                 and pl['r'] in (None, 'mix', *RICE) and (pl['mam'] is None or pl['mam'] in MAM), 'Dĩa trên quầy sai.')
        kit.integer(pl['va'], 0, VA_MAX)
        kit.integer(pl['c'], 0, 10000)
        kit.need(isinstance(pl['it'], list) and len(pl['it']) <= ITEMS_MAX and all(k in DISHES for k in pl['it']), 'Dĩa trên quầy sai.')
        kit.need(isinstance(pl['x'], list) and len(pl['x']) <= 4 and set(pl['x']) <= {'nhao', 'suong', 'song', 'xem', 'khet'}, 'Dĩa trên quầy sai.')
        _vbool(pl['mo'])
        _vbool(pl['canh'])
    if t.get('price') is not None:
        kit.integer(t['price'], 0, 10 ** 6)
    kit.integer(t.get('cost'), 0, 10 ** 6)
    kit.need(t.get('choice') in (None, 'decline'), 'Cách giải quyết sai.')
    till.validate(t.get('cash'), t)
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách quen sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    till.validate_book(c)
    sh = d['shop']
    kit.need(isinstance(sh, dict) and set(sh) == {'day', 'open'}, 'Quán cơm sai.')
    kit.integer(sh['day'], 0, 10 ** 7)
    _vbool(sh['open'])
    kit.need(isinstance(d['pots'], dict) and set(d['pots']) == set(RICE), 'Nồi cơm sai.')
    for pot in d['pots'].values():
        kit.need(isinstance(pot, dict) and set(pot) == {'va', 'q', 'at', 'c'} and pot['q'] in RICE_Q, 'Nồi cơm sai.')
        kit.integer(pot['va'], 0, POT_VA)
        _vnum(pot['at'], 0, 10 ** 11)
        kit.integer(pot['c'], 0, 10000)
    m = d['mam']
    kit.need(isinstance(m, dict) and set(m) == {'q', 'tasted'} and m['q'] in MAM_Q, 'Chén nước mắm sai.')
    _vbool(m['tasted'])
    g = d['grill']
    kit.need(isinstance(g, dict) and set(g) == {'lit', 'b'}, 'Bếp than sai.')
    _vbool(g['lit'])
    b = g['b']
    if b is not None:
        kit.need(isinstance(b, dict) and set(b) == {'n', 'start', 'flip', 'c'}, 'Mẻ sườn trên vỉ sai.')
        kit.integer(b['n'], 1, BATCH_MAX)
        _vnum(b['start'], 0, 10 ** 11)
        if b['flip'] is not None:
            _vnum(b['flip'], 0, 10 ** 11)
        kit.integer(b['c'], 0, 10000)
    kit.need(isinstance(d['rack'], list) and len(d['rack']) <= RACK_MAX, 'Khay giữ ấm sai.')
    for pc in d['rack']:
        kit.need(isinstance(pc, dict) and set(pc) == {'q', 'c'} and pc['q'] in GRILL_Q, 'Khay giữ ấm sai.')
        kit.integer(pc['c'], 0, 10000)
    kit.need(isinstance(d['trays'], dict) and set(d['trays']) == set(TRAYS), 'Tủ kính sai.')
    for tr in d['trays'].values():
        kit.need(isinstance(tr, dict) and set(tr) == {'n', 'c'}, 'Tủ kính sai.')
        kit.integer(tr['n'], 0, TRAY_MAX)
        kit.integer(tr['c'], 0, 10000)
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu quán cơm sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='com_', category='food',
    meta=dict(short='Bán cơm', place='Cơm tấm Dì Bảy', tagline='Cơm dẻo, sườn thơm, nước mắm vừa miệng.', icon='com',
              color='#c8742c', light='#fff1e0', weather='Nắng sớm đầu chợ', work='Khách gọi cơm', station='Xe cơm & bếp than',
              greeting='Nấu hai nồi cơm, nếm chén nước mắm, nhóm bếp than, bày khay lên tủ kính rồi mở quán. Khách gọi gì, dặn gì thì làm đúng vậy nhé.',
              caption='Dĩa cơm nào cũng đủ vá, đúng món', map_label='25 · CƠM TẤM DÌ BẢY'),
    people=PEOPLE,
    staff=[('Tí', 'grill', 'Cháu dì Bảy, quạt than đều tay, mắt không rời vỉ sườn.', 76, 88),
           ('Hồng', 'wash', 'Rửa chén dĩa nhanh thoăn thoắt, bàn nào cũng lau sạch bong.', 80, 84),
           ('Tâm', 'grill', 'Sinh viên làm thêm buổi sáng, kỹ tính từng miếng sườn.', 70, 92),
           ('Lan', 'wash', 'Quen mặt cả chợ, vừa dọn bàn vừa chào khách.', 82, 78)],
    roles={'grill': 'Quạt than, canh bếp', 'wash': 'Rửa chén, dọn bàn'},
    inventory=dict(items=ITEMS, capacity=120),
    prices=PRICES,
    tip=1,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('🍚', 'Xe cơm gọn gàng', [('Cơm tấm', 'Nồi bên trái'), ('Sườn nướng', 'Bếp than'), ('Tủ kính', 'Sáu khay món'), ('Nước mắm', 'Chén pha sẵn')],
              ['Nấu cơm đúng nước', 'Nếm nước mắm', 'Nướng sườn, trở một lần', 'Xới cơm, gắp món, thu tiền']),
    stories=[('Nước mắm dì Bảy', ('Tối nào dì Bảy cũng pha một thau nước mắm: mắm nhĩ, đường, chanh, nước sôi để nguội.',
                                  'Dì giã tỏi ớt bằng cái cối đá của bà ngoại, không cho vào máy xay.',
                                  'Sáng ra dì nếm đầu đũa, thiếu gì thêm nấy, không bao giờ để khách ăn chén mặn chát.')),
             ('Miếng sườn cháy cạnh', ('Chú Bình kể: cơm tấm ngon là miếng sườn hơi cháy cạnh, thơm mùi than.',
                                       'Nhưng cháy cạnh khác cháy khét, dì Bảy nói, và giữa miếng thịt không được hồng.',
                                       'Từ đó mẻ sườn nào bạn cũng đếm giây, trở đúng một lần.')),
             ('Bữa cơm ngày rằm', ('Ngày rằm, bà Sương ghé quán ăn chay.',
                                   'Dì Bảy lấy chén, muỗng riêng, múc nước tương, không chan mỡ hành.',
                                   'Bà Sương nói: “Quán nhớ bà ăn chay, bà mừng lắm.”'))],
    review_asides=['Cơm dẻo, sườn thơm mùi than.', 'Nước mắm vừa miệng, chan là mê.', 'Nhớ cả lời dặn ăn chay của mẹ tôi.',
                   'Dĩa cơm đầy đặn, giá mềm.'],
    situations=SITUATIONS,
    guide='Nấu nồi tấm (lưng đốt), nồi trắng (một đốt) → nếm nước mắm → nhóm bếp → bày khay → mở quán. Mỗi khách: hỏi → dĩa / hộp → '
          'xới cơm → gắp món → mỡ hành, nước mắm, canh → đưa cơm → thu tiền.',
)
