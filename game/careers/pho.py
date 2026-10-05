"""Quán phở Cây Si: bác Lâm's phở shop under the old banyan at the ward corner (plugin career).

Bác Lâm came up from Nam Định thirty years ago and still sets the bones on the fire at three in the
morning; the player works the stove beside him. What the job is:

* the big pot (``setup`` task, then all day): the broth simmered overnight on a low fire. Turn the
  fire to "lăn tăn" (a gentle simmer, 97 °C), skim the scum off the top, taste and season (a spoon of
  fish sauce, a dash of boiling water), then open. The pot is a live thing: every bowl takes broth and
  a little heat, a hard boil (lửa lớn) heats fast but throws up scum and turns the broth cloudy, and a
  pot run low is topped up with water and a batch of bones (cold, scummy and under-seasoned again);
* yesterday's bánh phở: fresh rice noodles keep a day; some mornings yesterday's lot has gone sour
  and must be thrown out (never served);
* each bowl, by hand: a bowl (thường / lớn) or a take-away box; blanch a fistful of bánh in the
  trụng basket by dipping it (three or four dips: fewer and it is stiff and stuck together, more and
  it goes mushy); lay the cuts on top (tái sliced raw, chín, nạm, gầu, gân, bò viên; tái on the side
  when asked, and always on the side for take-away); hành (none, a pinch, a lot); a raw egg yolk goes
  in BEFORE the broth (trứng trần) or it stays raw; then the ladle;
* the ladle (``pho_pour`` → ``pho_stop``, a tap-to-stop on kit.tap_now): the broth rises in the bowl
  in real seconds and the player stops it at the line the customer asked for (ít / vừa / nhiều; a
  take-away bag "vừa buộc được"). Where it comes from matters: clear broth from deep under the fat,
  "nước béo" skimmed from the top with the marrow fat, or the small pot bác Lâm keeps without MSG for
  the regulars who say "không mì chính". Broth under 95 °C leaves the tái red;
* the hot clock: from the first ladle a bowl cools in real seconds (faster on a cold-wind day);
* sides: quẩy, the herb plate with bean sprouts for southern customers;
* cash with the shared till (game/careers/till.py);
* the apprenticeship: for the first three customers bác Lâm stands at the stove and catches each
  mistake once before the bowl leaves the counter (nothing recorded, no desk surprises).

The noodle shop (restaurant.py) times a boil in a basket and pumps chili; here the timed step is the
ladle level, the dip is counted, and the pot itself (heat, scum, clarity, salt, level) is the craft.

Mistakes go through consequences (cq.slip / cq.react); money only through the engine's money().
Everything random is rolled from the day, slot or task id.
"""
from __future__ import annotations

import copy
import hashlib

from ..jsoncopy import tree_copy
from . import kit
from . import till
from .. import consequences as cq

ID = 'pho'
GEN = 1

# ---------------------------------------------------------------- the pot
FIRE_T = {'nho': 92, 'vua': 97, 'lon': 100}        # where each fire setting takes the broth
FIRE_LABEL = {'nho': 'Lửa ủ', 'vua': 'Lửa lăn tăn', 'lon': 'Lửa lớn'}
FIRE_OK = 'vua'
TAI_COOK = 95             # broth this hot cooks the tái pink in the bowl
CLOUD_AT = 3              # a hard boil this long and the broth is cloudy for the day
FOAM_AT = 2               # this much scum on top and it lands in the bowl
LEVEL_LOW = 30            # "nồi sắp cạn"
TOPUP = 45                # water + bones added by one top-up
TOPUP_AT = 60             # above this the pot does not need one yet
SMALL_MAX = 100           # the small pot without MSG (bác Lâm makes it every morning)
SALT_WORD = {-2: 'nhạt thếch', -1: 'hơi nhạt', 0: 'vừa miệng, ngọt xương', 1: 'hơi mặn', 2: 'mặn chát'}
SOURCES = {'trong': 'Nước trong', 'beo': 'Nước béo', 'nho': 'Nồi nhỏ không mì chính'}
SOURCE_NOTE = {'trong': 'muôi sâu, dưới lớp mỡ', 'beo': 'hớt lớp mỡ tủy trên mặt', 'nho': 'nồi riêng cho khách dặn không mì chính'}

# ---------------------------------------------------------------- bowls
VESSELS = {
    'to': dict(name='Tô thường', emoji='🍜', banh=1, vol=9, rate=14, price='to'),
    'to_lon': dict(name='Tô lớn', emoji='🥣', banh=2, vol=12, rate=11, price='to_lon'),
    'hop': dict(name='Hộp mang về', emoji='🥡', banh=1, vol=10, rate=12, price='hop', item='hop'),
}
# Where the broth should reach (0 = empty, 100 = the brim), by vessel and by what the customer said.
BANDS = {
    'bowl': {'it': (52, 68), 'vua': (70, 88), 'nhieu': (88, 97)},
    'bag': {'it': (40, 57), 'vua': (58, 80), 'nhieu': (80, 90)},
}
SPILL = {'bowl': 98, 'bag': 92}
NUOC_LABEL = {'it': 'ít nước', 'vua': 'nước vừa', 'nhieu': 'nhiều nước'}
DIP_OK = (3, 4)           # dips in the trụng basket
DIP_MAX = 9
CUT_MAX = 5
MEATS = {
    'tai': dict(name='Tái', emoji='🥩', note='thăn bò thái mỏng'),
    'chin': dict(name='Chín', emoji='🍖', note='bắp bò luộc thái'),
    'nam': dict(name='Nạm', emoji='🥓', note='nạm bò'),
    'gau': dict(name='Gầu', emoji='🍗', note='gầu giòn béo'),
    'gan': dict(name='Gân', emoji='🦴', note='gân bò hầm'),
    'vien': dict(name='Bò viên', emoji='🧆', note='bò viên dai'),
}
HANH = {'khong': 'không hành', 'vua': 'hành vừa', 'nhieu': 'nhiều hành'}
HOT_BASE = 35             # seconds before a bowl starts to cool, from the first ladle
HOT_UNIT = 10             # more per bowl
HOT_MOD = {'cold': 80}
SIDES = ('quay', 'rau')
BOWL_MAX = 6

ITEMS = [
    dict(id='banh', name='Bánh phở tươi', emoji='🍜', group='banh', unit='nắm', cost=2, life=2, start=16),
    dict(id='tai', name='Thăn bò (tái)', emoji='🥩', group='thit', unit='phần', cost=6, life=2, start=8),
    dict(id='chin', name='Bắp bò chín', emoji='🍖', group='thit', unit='phần', cost=4, life=3, start=8),
    dict(id='nam', name='Nạm bò', emoji='🥓', group='thit', unit='phần', cost=4, life=3, start=6),
    dict(id='gau', name='Gầu bò', emoji='🍗', group='thit', unit='phần', cost=5, life=3, start=4),
    dict(id='gan', name='Gân bò', emoji='🦴', group='thit', unit='phần', cost=4, life=3, start=4),
    dict(id='vien', name='Bò viên', emoji='🧆', group='thit', unit='phần', cost=3, life=6, start=6),
    dict(id='trung', name='Trứng gà', emoji='🥚', group='them', unit='quả', cost=2, life=7, start=6),
    dict(id='quay', name='Quẩy', emoji='🥖', group='them', unit='cái', cost=1, life=2, start=12),
    dict(id='rau', name='Đĩa rau thơm, giá', emoji='🌿', group='them', unit='đĩa', cost=1, life=2, start=6),
    dict(id='xuong', name='Xương ống bò', emoji='🦴', group='noi', unit='mẻ', cost=8, life=4, start=1),
    dict(id='hop', name='Hộp + túi mang về', emoji='🥡', group='noi', unit='bộ', cost=2, start=8),
]
PRICES = dict(to=30, to_lon=38, hop=32, them=3, trung=5, quay=3)   # them: each cut over two

# ---------------------------------------------------------------- học nghề: the first customers with bác Lâm
APPRENTICE = 3
LESSONS = [
    ('Bài 1 · Trụng bánh, xếp thịt', 'Bác Lâm đứng cạnh: “Nhúng rổ bánh ba bốn lượt là bánh tơi, mềm. Xếp thịt lên trên rồi mới chan.”'),
    ('Bài 2 · Muôi nước dùng', 'Bác Lâm dặn: “Chan tới đâu là do tay con. Khách dặn ít hay nhiều nước thì dừng muôi đúng vạch đó.”'),
    ('Bài 3 · Nồi nước và lời dặn', 'Bác Lâm nhắc: “Nồi phải lăn tăn mới chín tái. Khách dặn không mì chính thì múc nồi nhỏ.”'),
]
CATCH = {
    'stiff': 'Khoan con, bánh mới nhúng một hai lượt, còn dính chùm. Đổ tô, trụng lại ba bốn lượt.',
    'soggy': 'Bánh nhúng lâu quá, nát rồi. Đổ tô làm lại, ba bốn lượt là vừa.',
    'missing': 'Khoan, chưa đúng món khách gọi. Coi lại phiếu, tô nào sai thì đổ làm lại.',
    'extra': 'Có tô khách đâu có gọi. Bỏ tô dư ra đã con.',
    'tai_raw': 'Tái còn đỏ au kìa, nồi chưa đủ sôi. Đổ tô, chờ nồi lăn tăn lại rồi chan.',
    'msg': 'Khách dặn không mì chính! Đổ tô, múc nước ở nồi nhỏ cho khách.',
    'not_fatty': 'Khách dặn nước béo, con múc nước trong rồi. Chan lại bằng muôi hớt mặt.',
    'little': 'Nước chưa tới vạch khách dặn. Bấm chan thêm cho đủ.',
    'much': 'Nước nhiều hơn khách dặn rồi. Lần sau dừng muôi sớm hơn chút.',
    'spill': 'Tràn ra mép tô, nóng bỏng tay khách đó. Đổ tô làm lại.',
    'no_onion': 'Tô này quên rắc hành rồi con.',
    'onion': 'Hành chưa đúng lời khách dặn. Coi lại phiếu.',
    'egg_raw': 'Trứng phải đập vào trước rồi mới chan nước sôi cho chín tới. Đổ tô làm lại.',
    'egg': 'Trứng chưa đúng lời khách dặn kìa.',
    'tai_mixed': 'Khách dặn tái để riêng. Đổ hộp làm lại, tái để túi riêng.',
    'untied': 'Túi nước chưa buộc kìa, khách cầm là đổ hết.',
    'sour': 'Dừng! Bánh hôm qua chua rồi, không được bán. Đổ tô, bỏ lô bánh cũ.',
    'quay': 'Khách gọi quẩy, con chưa lấy đủ.',
    'rau': 'Khách xin đĩa rau với giá kìa.',
}

PEOPLE = [
    ('Bác Lâm', 'Chủ quán phở', 'Người Nam Định, ba giờ sáng đã bắc nồi xương, nếm nước bằng cái muôi đồng.', 'warm'),
    ('Ông giáo Thụ', 'Thầy giáo về hưu', 'Sáng nào cũng đọc báo bên tô phở, nước trong, không mì chính.', 'picky'),
    ('Chị Nguyệt', 'Bán xôi đầu ngõ', 'Ăn vội trước giờ đông khách, mê nước béo với quẩy.', 'bossy'),
    ('Anh Tuấn', 'Thợ hồ công trình', 'Ăn tô lớn cho chắc bụng, hay mua mang về cho cả tổ.', 'quiet'),
    ('Chị Hạnh', 'Mẹ bé Bống', 'Đưa bé đi học rồi ghé ăn, tô của bé không hành, ít nước.', 'warm'),
    ('Cô Linh', 'Nhân viên ngân hàng', 'Mua mang về, lúc nào cũng vội, dặn tái để riêng.', 'genz'),
    ('Anh Sáu', 'Tài xế xe tải Sài Gòn', 'Ăn phở kiểu miền Nam: trứng trần, đĩa rau, giá.', 'sour'),
]

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Người đi làm ghé ăn sáng, khách đều tay.', weight=3),
    dict(id='cold', emoji='🌬️', label='Gió mùa về', hint='Trời lạnh: phở nguội nhanh, nồi mất nhiệt nhanh hơn. Giữ lửa lăn tăn.', min_day=2, weight=2),
    dict(id='rain', emoji='🌧️', label='Mưa sáng', hint='Khách trú mưa ăn bát phở nóng, ngồi lâu hơn.', min_day=2, weight=2),
    dict(id='weekend', emoji='🛍️', label='Cuối tuần', hint='Cả nhà đi ăn phở, tô lớn, trứng, quẩy gọi nhiều.', min_day=2, weight=2),
    dict(id='early', emoji='🌅', label='Chợ sớm', hint='Năm giờ rưỡi đã có khách: nước béo đầu nồi ngon nhất.', min_day=3, weight=1),
]
MOD = {m['id']: m for m in MODS}


def _b(v, *meat, nuoc='vua', src='trong', hanh='vua', egg=False, rieng=False):
    """One bowl of an order."""
    return dict(v=v, meat=list(meat), nuoc=nuoc, src=src, hanh=hanh, egg=egg, rieng=rieng)


# (npc, kind, title, opening, bowls, note, min_day, mod, flags)
ORDERS = [
    (2, 'serve', 'Chị Nguyệt ăn sáng', 'Cho chị tô tái nạm, nước béo, hai cái quẩy. Nhanh giùm chị, mẹt xôi ngoài kia không ai trông!',
     [_b('to', 'tai', 'nam', src='beo')], 'Chị Nguyệt bán xôi đầu ngõ, tranh thủ ăn trước giờ đông.', 1, None, dict(quay=2)),
    (3, 'serve', 'Anh Tuấn trước giờ vào ca', 'Tô lớn tái chín. Hôm nay đổ bê tông, phải ăn cho chắc bụng.',
     [_b('to_lon', 'tai', 'chin')], 'Anh Tuấn đội mũ bảo hộ, quần còn dính vữa.', 1, None, {}),
    (4, 'serve', 'Chị Hạnh cho bé Bống', 'Một tô chín cho bé, không hành, ít nước thôi em, bé ăn chậm lắm.',
     [_b('to', 'chin', nuoc='it', hanh='khong')], 'Bé Bống ngồi ghế nhựa, chân đung đưa.', 1, None, {}),
    (1, 'serve', 'Ông giáo Thụ đọc báo', 'Cho ông tô tái chín, nước trong, nhiều hành. Nhớ là ông không ăn mì chính đâu nhé.',
     [_b('to', 'tai', 'chin', src='nho', hanh='nhieu')], 'Ông giáo trải tờ báo sáng lên bàn, đeo kính lão.', 2, None, dict(check=True)),
    (5, 'take', 'Cô Linh mua mang về', 'Em lấy một suất mang về, tái nạm, tái để riêng, ít nước thôi anh.',
     [_b('hop', 'tai', 'nam', nuoc='it', rieng=True)], 'Cô Linh vừa nghe điện thoại vừa nhìn đồng hồ.', 2, None, {}),
    (6, 'serve', 'Anh Sáu ăn kiểu Sài Gòn', 'Cho anh tô tái gầu, đập cái hột gà vô, thêm dĩa rau với giá nghen!',
     [_b('to', 'tai', 'gau', egg=True)], 'Anh Sáu đậu xe tải đầu ngõ, giọng Sài Gòn sang sảng.', 2, None, dict(rau=True)),
    (2, 'serve', 'Chị Nguyệt bán hết xôi', 'Tô bò viên, nước béo, nhiều hành. Hôm nay hết xôi sớm!',
     [_b('to', 'vien', src='beo', hanh='nhieu')], 'Chị Nguyệt khoe mẹt xôi bán hết veo.', 2, None, {}),
    (3, 'serve', 'Anh Tuấn ăn tô đặc biệt', 'Tô lớn đặc biệt, đủ tái nạm gầu gân. Hai cái quẩy nữa.',
     [_b('to_lon', 'tai', 'nam', 'gau', 'gan')], 'Anh Tuấn vừa lĩnh lương tuần.', 3, None, dict(quay=2)),
    (1, 'serve', 'Ông giáo Thụ ăn tô chín', 'Hôm nay ông ăn chín nạm, nước trong, đừng cho mì chính nhé.',
     [_b('to', 'chin', 'nam', src='nho')], 'Ông giáo khen bác Lâm vẫn giữ được vị phở Nam Định.', 3, None, dict(check=True)),
    (4, 'serve', 'Chị Hạnh với bé Bống', 'Một tô tái nạm cho chị, một tô chín cho bé, không hành, ít nước.',
     [_b('to', 'tai', 'nam'), _b('to', 'chin', nuoc='it', hanh='khong')], 'Bé Bống đòi ăn quẩy, chị Hạnh lắc đầu.', 3, None, {}),
    (5, 'take', 'Cô Linh mua cho sếp', 'Hai suất mang về: một tái để riêng, một chín. Nước vừa thôi anh nhé.',
     [_b('hop', 'tai', rieng=True), _b('hop', 'chin')], 'Cô Linh dặn: “Sếp em khó tính lắm.”', 3, None, {}),
    (6, 'serve', 'Anh Sáu ngày gió mùa', 'Trời lạnh quá, cho anh tô lớn tái nạm, nhiều nước, nóng hổi nghen!',
     [_b('to_lon', 'tai', 'nam', nuoc='nhieu')], 'Anh Sáu xoa hai bàn tay, hơi thở phả khói.', 2, 'cold', {}),
    (1, 'serve', 'Ông giáo trú mưa', 'Mưa thế này phải bát phở nóng. Tái chín, nhiều hành, không mì chính.',
     [_b('to', 'tai', 'chin', src='nho', hanh='nhieu')], 'Ông giáo gấp ô, lau cặp kính mờ hơi nước.', 2, 'rain', dict(check=True)),
    (3, 'serve', 'Anh Tuấn chủ nhật', 'Chủ nhật nghỉ, anh ăn tô lớn tái gầu, trứng trần, ba cái quẩy.',
     [_b('to_lon', 'tai', 'gau', egg=True)], 'Anh Tuấn dẫn theo thằng con trai.', 2, 'weekend', dict(quay=3)),
    (2, 'serve', 'Chị Nguyệt sáng sớm', 'Sớm thế này mới có nước béo ngon. Tái nạm, nước béo, nhiều nước nhé em.',
     [_b('to', 'tai', 'nam', src='beo', nuoc='nhieu')], 'Mới năm giờ rưỡi, ngoài ngõ còn tối.', 2, 'early', {}),
]
CREW = (3, 'crew', 'Đơn mang về cho tổ thợ',
        'Bốn suất mang về cho anh em công trình: hai tái nạm, tái để riêng, hai chín. Bốn cái quẩy nữa.',
        [_b('hop', 'tai', 'nam', rieng=True), _b('hop', 'tai', 'nam', rieng=True), _b('hop', 'chin'), _b('hop', 'chin')],
        'Anh Tuấn chạy xe máy ra, sau xe buộc sẵn thùng xốp.', 3, None, dict(quay=4))
KINDS = ('setup', 'serve', 'take', 'crew')
STAGES = ('prep', 'pay', 'done')

# Regulars' small stories: one line per finished visit, on and on across days.
REG_STORY = {
    1: ('Ông giáo Thụ: “Phở ngon là ở nước trong, nhìn thấy đáy tô.”', 'Ông giáo kể hồi xưa đi dạy, sáng nào cũng một tô phở gánh.',
        'Ông giáo cắt bài báo viết về phở Nam Định, dán lên tường quán.', 'Ông giáo gật gù: “Nước hôm nay ngọt xương. Được.”'),
    2: ('Chị Nguyệt: “Nước béo mới đậm, ăn xong bán xôi tới trưa.”', 'Chị Nguyệt để phần quán một gói xôi xéo.',
        'Chị Nguyệt dắt mối mấy bà bán rau sang ăn phở.'),
    3: ('Anh Tuấn: “Tô lớn mới đủ sức vác xi măng.”', 'Anh Tuấn khoe công trình sắp cất nóc.',
        'Anh Tuấn bảo cả tổ thợ giờ chỉ ăn phở ở đây.'),
    4: ('Chị Hạnh: “Bé Bống chịu ăn hết tô rồi đó em.”', 'Bé Bống vẽ tặng quán cái nồi phở bốc khói.',
        'Chị Hạnh kể bé Bống được cô giáo khen ăn giỏi.'),
    5: ('Cô Linh: “Tái để riêng về văn phòng chần lại là ngon.”', 'Cô Linh được sếp khen mua phở khéo.',
        'Cô Linh đặt phở cho cả phòng họp sáng thứ hai.'),
    6: ('Anh Sáu: “Ngoài này phở nước trong, ăn riết cũng ghiền.”', 'Anh Sáu mang biếu bác Lâm chai tương đen Sài Gòn.',
        'Anh Sáu kể chuyến hàng ra Bắc lần này chở toàn quất Tết.'),
}

INTRO = dict(
    title='Giới thiệu nghề: bán phở',
    lead='Một nồi nước dùng to đùng bốc khói dưới gốc cây si, rổ trụng bánh, cái thớt gỗ và mấy bộ bàn ghế nhựa. '
         'Bác Lâm ninh xương từ ba giờ sáng, bạn đứng bếp cùng bác.',
    work=[('🔥', 'Giữ nồi lăn tăn: lửa lớn nhanh sôi nhưng nước đục, nhiều bọt'), ('🥄', 'Hớt bọt, nếm nước, nêm cho vừa'),
          ('🍜', 'Nhúng rổ bánh ba bốn lượt cho tơi'), ('🥩', 'Xếp tái, chín, nạm, gầu theo lời khách'),
          ('🫗', 'Chan nước dùng, dừng muôi đúng vạch khách dặn'), ('🧅', 'Nhớ lời dặn: không hành, nhiều hành, không mì chính, nước béo'),
          ('🥡', 'Mang về: tái để riêng, túi nước buộc chặt'), ('💵', 'Thu tiền, thối đúng')],
    meet=[('📰', 'Ông giáo Thụ: nước trong, không mì chính'), ('🍙', 'Chị Nguyệt: nước béo, thêm quẩy'),
          ('👷', 'Anh Tuấn: tô lớn, mua cho cả tổ'), ('👧', 'Chị Hạnh và bé Bống: không hành, ít nước'),
          ('💼', 'Cô Linh: mang về, tái để riêng'), ('🚚', 'Anh Sáu: trứng trần, đĩa rau giá')],
    stars=[('🍲', 'Nước trong, nóng, vừa miệng'), ('🍜', 'Bánh tơi mềm, tái chín hồng'), ('🫗', 'Nước đúng mức khách dặn'),
           ('🧅', 'Nhớ đúng lời dặn'), ('⏱️', 'Bưng ra còn nóng hổi'), ('💵', 'Thối đúng tiền')],
)

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='gas_out', title='Bình gas hết giữa ca', emoji='🔥', npc=0, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Ngọn lửa dưới nồi phụt tắt, bình gas nhẹ tênh. Khách vẫn ngồi chờ, nồi nước nguội dần.',
         options=[dict(id='swap', label='Thay bình gas dự phòng, kiểm van rồi mới bật lửa', hint='Khách chờ thêm chút', effects=dict(patience=-3, xp=3), good=True,
                       outcome='Bình mới lắp xong, ngửi van không thấy mùi gas, lửa xanh đều. Nồi lăn tăn trở lại.'),
                  dict(id='coal', label='Nhóm bếp than tổ ong kê tạm', hint='Nồi nóng chậm', effects=dict(heat=-6, patience=-5), good=None,
                       outcome='Bếp than đỏ lửa, nồi nóng lên từ từ. Khói than bay cả ra ngõ.'),
                  dict(id='keep', label='Cứ chan nước đang còn ấm', hint='', effects=dict(heat=-12), good=False,
                       outcome='Nước dùng ấm ấm, tái thả vào vẫn còn đỏ. Mấy khách nhìn nhau.')],
         default='keep'),
    dict(id='spill_kid', title='Bé làm đổ bát nước dùng', emoji='😭', npc=4, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Một bé ngồi bàn ngoài với tay lấy đũa, bát nước dùng nóng đổ trúng mu bàn tay. Bé khóc thét.',
         options=[dict(id='cool', label='Xả nước mát lên chỗ bỏng mười lăm phút, không bôi gì lạ', hint='', effects=dict(xp=5), good=True,
                       outcome='Bàn tay bé đỡ đỏ dần. Mẹ bé cảm ơn, hẹn đưa bé đi trạm y tế xem lại cho chắc.'),
                  dict(id='toothpaste', label='Lấy kem đánh răng bôi lên cho mát', hint='', effects=dict(review=[2, 'Con tôi bị bỏng mà quán bôi kem đánh răng, bác sĩ phải rửa sạch lại.']),
                       good=False, outcome='Bé vẫn rát. Ra trạm y tế, bác sĩ phải rửa sạch lớp kem đi.'),
                  dict(id='wipe', label='Lau khô rồi để bé ngồi yên', hint='', effects=dict(patience=-2), good=None,
                       outcome='Bé nín dần nhưng mu bàn tay vẫn đỏ ửng.')],
         default='wipe'),
    dict(id='cat', title='Mèo hoang rình bàn thịt', emoji='🐈', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Con mèo mướp nhảy lên ghế, vươn cổ ngửi rổ thịt bò bày trên thớt.',
         options=[dict(id='cover', label='Đậy lồng bàn lên rổ thịt, bế mèo ra ngoài', hint='', effects=dict(xp=3), good=True,
                       outcome='Thịt đậy kín. Con mèo ra nằm dưới gốc si chờ xương.'),
                  dict(id='shoo', label='Xua mèo đi rồi làm tiếp', hint='', effects={}, good=None,
                       outcome='Mèo chạy đi, lát sau lại lảng vảng quanh thớt.'),
                  dict(id='ignore', label='Kệ, mèo chưa ăn đâu', hint='', effects=dict(review=[2, 'Mèo nhảy lên bàn thịt mà quán cứ để vậy, nhìn mất vệ sinh.']),
                       good=False, outcome='Một khách chụp được cảnh con mèo đứng cạnh rổ thịt.')],
         default='shoo'),
    dict(id='cheap_meat', title='Người mời mua thịt bò rẻ', emoji='🥩', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Một người chở thùng xốp ghé: “Thịt bò rẻ bằng nửa chợ, khỏi giấy tờ gì cho mệt. Lấy chục ký không?”',
         options=[dict(id='no', label='Không lấy: thịt phải có giấy kiểm dịch, mua mối quen', hint='', effects=dict(xp=4), good=True,
                       outcome='Người đó đi tiếp. Bác Lâm gật đầu: “Thịt không rõ nguồn là không bao giờ vào nồi nhà mình.”'),
                  dict(id='look', label='Xem thử rồi tính', hint='', effects=dict(patience=-3), good=None,
                       outcome='Thịt sẫm màu, ấn vào không đàn hồi. Bạn trả lại, mất chút thời gian.'),
                  dict(id='buy', label='Lấy năm ký cho rẻ', hint='Rẻ…', effects=dict(money=-10, review=[1, 'Ăn phở xong đau bụng cả buổi, nghe nói quán mua thịt trôi nổi.']),
                       good=False, outcome='Chiều đó có khách gọi điện, kêu ăn xong đau bụng.')],
         default='no'),
    dict(id='refill', title='Khách xin thêm nước dùng', emoji='🫗', npc=6, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Anh Sáu húp hết nước, chìa tô ra: “Cho anh xin thêm chút nước nghen, ngon quá!”',
         options=[dict(id='give', label='Chan thêm một muôi nóng, không lấy tiền', hint='', effects=dict(xp=3, pot=-2), good=True,
                       outcome='Anh Sáu cười khà khà: “Ngoài này chơi đẹp ghê!”'),
                  dict(id='charge', label='Thêm nước thì tính thêm hai xu', hint='', effects=dict(money=2), good=None,
                       outcome='Anh Sáu trả tiền, hơi chưng hửng.'),
                  dict(id='no', label='“Hết nước rồi anh”', hint='', effects=dict(review=[2, 'Xin thêm muôi nước dùng mà quán nói hết, nồi to đùng kia.']),
                       good=False, outcome='Anh Sáu nhìn cái nồi đầy ắp, lắc đầu.')],
         default='charge'),
    dict(id='inspect', title='Đoàn kiểm tra vệ sinh phường', emoji='📋', npc=0, min_day=3, tone='tense', at='open', weight=2, mods=None,
         text='Hai cán bộ phường ghé: “Quán cho xem giấy nguồn gốc thịt, chỗ rửa bát với thùng rác nhé.”',
         options=[dict(id='show', label='Đưa sổ nhập thịt có giấy kiểm dịch, dẫn xem chỗ rửa bát', hint='', effects=dict(xp=4), good=True,
                       outcome='Cán bộ ghi “đạt”, còn dặn đậy nắp thùng rác cho kín.'),
                  dict(id='later', label='Xin hẹn hôm khác, đang đông khách', hint='', effects=dict(patience=-2), good=None,
                       outcome='Đoàn hẹn tuần sau quay lại, ghi tên quán vào sổ.'),
                  dict(id='tip', label='Mời hai anh tô phở cho qua', hint='', effects=dict(money=-6, review=[2, 'Thấy quán mời cán bộ ăn phở cho qua kiểm tra, nghĩ sao đây?']),
                       good=False, outcome='Hai cán bộ từ chối, ghi biên bản kỹ hơn.')],
         default='later'),
    dict(id='forgot_phone', title='Khách bỏ quên điện thoại', emoji='📱', npc=5, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Dọn bàn thì thấy chiếc điện thoại nằm dưới tờ khăn giấy. Hình như của cô Linh vừa mua mang về.',
         options=[dict(id='keep', label='Cất vào ngăn kéo, chờ chủ quay lại hoặc gọi số người thân', hint='', effects=dict(xp=4), good=True,
                       outcome='Mười phút sau cô Linh hớt hải quay lại, mừng rơi nước mắt.'),
                  dict(id='leave', label='Để nguyên trên bàn', hint='', effects={}, good=None,
                       outcome='Lát sau chiếc điện thoại vẫn nằm đó, may chưa ai lấy.'),
                  dict(id='post', label='Đăng lên nhóm phố tìm chủ, chụp cả màn hình khóa', hint='', effects=dict(review=[3, 'Quán tốt bụng nhưng đăng cả ảnh màn hình khóa có tin nhắn của tôi lên mạng.']),
                       good=None, outcome='Cô Linh tìm lại được máy, nhưng hơi ngại vì ảnh tin nhắn lộ ra.')],
         default='keep'),
    dict(id='rain_awning', title='Mưa hắt vào bàn ngoài', emoji='🌧️', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=('rain', 'cold'),
         text='Mưa xiên hắt vào mấy bàn ngoài, ống đũa với rổ quẩy ướt nhẹp.',
         options=[dict(id='move', label='Kéo bạt, dời bàn vào trong, thay ống đũa khô', hint='Mất chút thời gian', effects=dict(patience=-3, xp=3), good=True,
                       outcome='Khách ngồi khô ráo, quẩy vẫn giòn.'),
                  dict(id='later', label='Để tạnh mưa rồi dọn', hint='', effects=dict(stock={'quay': -3}), good=None,
                       outcome='Rổ quẩy ướt mềm phải bỏ.')],
         default='later'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='PH-S01', title='Tô phở nhiều mì chính', npc=1, tone='tense', min_day=2,
         opening='Ông giáo Thụ đặt đũa xuống: “Ông dặn không mì chính, mà sao húp vào cứ khô cổ thế này hả cháu?”',
         swap='Bạn là ông giáo Thụ, ăn phở ở đây mười năm, uống mì chính vào là khô cổ, nhức đầu.',
         facts=[dict(id='pot', title='Muôi nước', source='Bếp', text='Muôi vừa chan là muôi múc ở nồi lớn, nồi đã nêm mì chính từ sáng.'),
                dict(id='small', title='Nồi nhỏ', source='Bác Lâm', text='Bác Lâm nấu riêng một nồi nhỏ không mì chính cho khách quen dặn.'),
                dict(id='habit', title='Lời dặn', source='Phiếu', text='Lúc gọi món ông đã dặn rõ: không mì chính.')],
         options=[dict(id='remake', label='Xin lỗi ông, làm tô khác bằng nước nồi nhỏ, không lấy tiền tô lỗi', requires=['pot', 'small'], quality='good', stars=5,
                       review='Quán lỡ tay nhưng nhận ngay, làm lại tô khác bằng nồi riêng. Đáng mặt quán quen.',
                       outcome='Ông giáo húp thìa nước mới, gật gù: “Thế mới là phở.”',
                       perspectives=[dict(who='Ông giáo Thụ', emoji='📰', text='Lỡ thì sửa, ông không trách.'),
                                     dict(who='Bác Lâm', emoji='🧑‍🍳', text='Khách dặn gì phải nhớ cái muôi múc ở nồi nào.')]),
                  dict(id='water', label='Rót cho ông cốc trà đá cho đỡ khô cổ', requires=['habit'], quality='ok', stars=3,
                       review='Quán có hỏi han, nhưng tô phở vẫn là tô có mì chính.',
                       outcome='Ông giáo uống trà, ăn nốt nửa tô rồi về sớm.',
                       perspectives=[dict(who='Ông giáo Thụ', emoji='🤨', text='Trà đá không làm tô phở hết mì chính được.'),
                                     dict(who='Chị Nguyệt', emoji='🍙', text='Ông dặn mấy năm nay rồi mà.')]),
                  dict(id='deny', label='“Quán có cho mì chính đâu ông”', quality='bad', stars=1,
                       review='Dặn rõ ràng mà còn chối. Mười năm ăn ở đây, buồn.',
                       outcome='Ông giáo gấp tờ báo, đứng dậy về, sáng hôm sau không thấy ông ra.',
                       perspectives=[dict(who='Ông giáo Thụ', emoji='😞', text='Ông nếm là biết, cháu ạ.'),
                                     dict(who='Bác Lâm', emoji='🧑‍🍳', text='Mất khách quen vì một muôi nước.')])],
         lesson='Khách dặn không mì chính thì múc nồi nhỏ. Lỡ tay thì nhận, làm lại tô khác.'),
    dict(id='PH-S02', title='Thịt bò rẻ bất thường', npc=0, tone='tense', min_day=3,
         opening='Mối thịt quen báo tăng giá. Một người khác nhắn tin chào thịt bò rẻ hơn ba mươi phần trăm, “khỏi giấy tờ, giao tận nơi”.',
         facts=[dict(id='color', title='Miếng thịt mẫu', source='Thớt', text='Thịt mẫu màu đỏ sẫm, ấn tay vào lõm mãi không lên, mặt nhớt.'),
                dict(id='paper', title='Giấy tờ', source='Tin nhắn', text='Người bán không có giấy kiểm dịch, không cho biết lò mổ nào.'),
                dict(id='old', title='Mối quen', source='Sổ nhập', text='Mối quen có tem kiểm dịch từng lô, tăng giá vì bò hơi lên giá.')],
         options=[dict(id='keep', label='Giữ mối quen, xin bớt chút, tăng giá tô phở một xu và nói rõ với khách', requires=['color', 'paper'], quality='good', stars=5,
                       review='Quán tăng một xu nhưng nói rõ lý do, thịt vẫn tươi ngon. Ủng hộ.',
                       outcome='Khách quen gật gù, thịt vẫn đỏ tươi, ăn yên tâm.',
                       perspectives=[dict(who='Ông giáo Thụ', emoji='📰', text='Một xu mà ăn yên tâm thì ông trả.'),
                                     dict(who='Bác Lâm', emoji='🧑‍🍳', text='Ba mươi năm bán phở chưa lần nào mua thịt trôi nổi.')]),
                  dict(id='half', label='Mua một nửa thịt rẻ để bù lỗ', requires=['old'], quality='bad', stars=2,
                       review='Tô hôm nay thịt dai, mùi lạ. Quán đổi mối thịt hả?',
                       outcome='Khách để thừa thịt, có người hỏi thẳng.',
                       perspectives=[dict(who='Chị Nguyệt', emoji='🍙', text='Thịt này không phải thịt mọi hôm.'),
                                     dict(who='Bác Lâm', emoji='🧑‍🍳', text='Tiết kiệm kiểu đó là mất khách.')]),
                  dict(id='all', label='Đổi hẳn sang mối rẻ', quality='bad', stars=1,
                       review='Ăn xong cả nhà đau bụng. Không dám quay lại.',
                       outcome='Tối đó có ba khách gọi điện kêu đau bụng.',
                       perspectives=[dict(who='Chị Hạnh', emoji='👧', text='Bé nhà chị nôn cả đêm.'),
                                     dict(who='Cán bộ phường', emoji='📋', text='Thịt không nguồn gốc là vi phạm an toàn thực phẩm.')])],
         lesson='Thịt phải có nguồn gốc, giấy kiểm dịch. Giá lên thì nói thật với khách, đừng đổi sang thịt trôi nổi.'),
    dict(id='PH-S03', title='Tô phở nguội ngắt', npc=6, tone='tense', min_day=2,
         opening='Anh Sáu bưng tô phở trở lại quầy: “Phở gì nguội ngắt, tái còn đỏ lòm nè em!”',
         facts=[dict(id='fire', title='Ngọn lửa', source='Bếp', text='Lúc nãy châm nước với xương mới, nồi tụt xuống còn tám mươi mấy độ, chưa kịp sôi lại.'),
                dict(id='tai', title='Miếng tái', source='Tô phở', text='Miếng tái còn đỏ, nước không đủ nóng để chín tới.'),
                dict(id='rule', title='Lời bác Lâm', source='Bác Lâm', text='Nồi chưa lăn tăn thì chưa chan, khách chờ thêm một phút còn hơn ăn tô nguội.')],
         options=[dict(id='remake', label='Xin lỗi, chờ nồi sôi lại rồi làm tô mới nóng hổi', requires=['fire', 'tai'], quality='good', stars=5,
                       review='Tô đầu nguội thật nhưng quán đổi tô mới nóng hổi, tái chín hồng. Được.',
                       outcome='Anh Sáu húp xì xụp tô mới, giơ ngón cái.',
                       perspectives=[dict(who='Anh Sáu', emoji='🚚', text='Đổi liền là được rồi em.'),
                                     dict(who='Bác Lâm', emoji='🧑‍🍳', text='Châm nồi xong phải chờ sôi lại.')]),
                  dict(id='hot', label='Chan thêm muôi nước nóng vào tô cũ', requires=['tai'], quality='ok', stars=3,
                       review='Có chan thêm nước nóng, nhưng tái vẫn tái tái, bánh trương.',
                       outcome='Anh Sáu ăn tạm, bánh đã trương phình.',
                       perspectives=[dict(who='Anh Sáu', emoji='🤨', text='Ăn được, nhưng hông ngon.'),
                                     dict(who='Ông giáo Thụ', emoji='📰', text='Tô phở phải nóng từ đầu.')]),
                  dict(id='deny', label='“Phở mùa này nguội nhanh lắm anh”', quality='bad', stars=1,
                       review='Bưng ra tô nguội tái sống, còn nói trời lạnh. Thôi khỏi.',
                       outcome='Anh Sáu đặt tiền lên bàn rồi đi, tô còn nguyên.',
                       perspectives=[dict(who='Anh Sáu', emoji='😠', text='Lần sau ghé quán khác.'),
                                     dict(who='Chị Nguyệt', emoji='🍙', text='Nồi chưa sôi mà đã chan rồi.')])],
         lesson='Châm nước, thêm xương xong phải chờ nồi lăn tăn lại mới chan. Tô nguội thì làm tô mới.'),
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
    i = _npc_index(t)
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Khách'


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _p(c: dict, key: str) -> int:
    return max(1, int(kit.price(c, key, PRICES[key])))


def kind_of(v: str) -> str:
    return 'bag' if v == 'hop' else 'bowl'


def band(ln: dict) -> tuple:
    return BANDS[kind_of(ln['v'])][ln['nuoc']]


def meats_text(meat: list) -> str:
    return ' '.join(_lower(MEATS[m]['name']) for m in meat)


def line_text(ln: dict) -> str:
    v = VESSELS[ln['v']]
    bits = [f'{_lower(v["name"])} {meats_text(ln["meat"])}']
    if ln['rieng']:
        bits.append('tái để riêng')
    if ln['nuoc'] != 'vua':
        bits.append(NUOC_LABEL[ln['nuoc']])
    if ln['src'] == 'beo':
        bits.append('nước béo')
    elif ln['src'] == 'nho':
        bits.append('không mì chính')
    if ln['hanh'] != 'vua':
        bits.append(HANH[ln['hanh']])
    if ln['egg']:
        bits.append('trứng trần')
    return ', '.join(bits)


# ================================================================ tasks
def _kind(day: int, slot: int) -> str:
    if slot == 0:
        return 'setup'
    if day >= 3 and day % 3 == 0 and slot == 2:
        return 'crew'
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
    common = dict(gen=GEN, stage='prep', bowls=[], side=dict(quay=0, rau=False), pour=None, hot=None, price=None, cash=None,
                  cost=0, choice=None, story=None)
    if kind == 'setup':
        needs = dict(setup=True, note={'cold': 'Gió mùa: nồi mất nhiệt nhanh, giữ lửa cho đều.', 'early': 'Chợ sớm: khách tới từ năm giờ rưỡi.',
                                       'rain': 'Mưa sáng: kéo bạt che mấy bàn ngoài.'}.get(mod, 'Vặn lửa, hớt bọt, nếm nước, ngửi bánh rồi mở quán.'))
        return kit.base_task(ID, day, slot, serial, 0, 'Mở quán phở đầu ngày',
                             'Bác Lâm dặn: “Nồi xương bác ủ lửa từ đêm. Con vặn lửa lăn tăn, hớt bọt, nếm nước, ngửi lại bánh hôm qua rồi hẵng bán.”',
                             kind='setup', needs=needs, **common)
    npc, k, title, opening, lines, note, _, _, flags = CREW if kind == 'crew' else _pick(day, slot, mod)
    needs = dict(lines=copy.deepcopy(lines), note=note, check=bool(flags.get('check')), quay=int(flags.get('quay', 0)),
                 rau=bool(flags.get('rau')))
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind=k, needs=needs, **common)


FIXED = ('needs',)


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the shop's data
def _fresh_shop(day: int) -> dict:
    return dict(day=day, open=False, tasted=False, sniffed=False)


def _fresh_today(day: int) -> dict:
    return dict(day=day, bowls=0, customers=0, topups=0, cloudy=0, raw=0, cold=0, spills=0)


def initial() -> dict:
    return dict(v=1, intro=False, shop=_fresh_shop(0), pot=dict(level=100, heat=97, fire=FIRE_OK, foam=0, cloud=0, salt=0, tasted=False),
                small=SMALL_MAX, sour=False, regulars={}, today=_fresh_today(0),
                stats=dict(bowls=0, customers=0, topups=0, cloudy=0, raw=0, cold=0, spills=0, fair=0), desk=kit.desk_initial(),
                learn=dict(task=None, codes=[], done=False))


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'shop', 'pot', 'learn'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    return d


def salt_of(day: int) -> int:
    """How the overnight broth tastes in the morning (−2 bland … +2 salty)."""
    if day == 1:
        return -1         # the first morning teaches the tasting spoon
    return (-1, 0, 1, 0, -1, 1, -2)[kit.rng(ID, 'salt', day).randrange(7)]


def foam_of(day: int) -> int:
    return 3 if day == 1 else 2 + kit.rng(ID, 'foam', day).randrange(3)


def heat_word(heat: int) -> str:
    return 'sôi sùng sục' if heat >= 99 else 'lăn tăn' if heat >= TAI_COOK else 'âm ấm, chưa sôi' if heat < 88 else 'gần sôi'


# ================================================================ the pot
def _pot_tick(d: dict, c: dict) -> None:
    """One move at the stove: the fire takes the broth towards its heat; a hard boil throws up scum and clouds it."""
    pot = d['pot']
    goal = FIRE_T[pot['fire']]
    if pot['heat'] < goal:
        pot['heat'] = min(goal, pot['heat'] + (3 if pot['fire'] == 'lon' else 2))
    elif pot['heat'] > goal:
        pot['heat'] = max(goal, pot['heat'] - 1)
    if pot['fire'] == 'lon' and pot['heat'] >= 100:
        pot['cloud'] = min(9, pot['cloud'] + 1)
        pot['foam'] = min(9, pot['foam'] + 1)


# Moves that take no time at the stove.
POT_STILL = ('pho_intro', 'pho_desk', 'pho_taste', 'pho_stop', 'pho_pay', 'pho_short', 'pho_sniff', 'pho_decline')


def _old_banh(c: dict) -> int:
    """Bánh phở received before today (still in date by the stock's rules): yesterday's lot."""
    inv = c['ext'].get('inv') or {}
    return sum(l['qty'] for l in inv.get('lots', []) if l['item'] == 'banh' and l['received'] < c['day'] and l['expires'] >= c['day'])


# ================================================================ the actions
FREE = ('pho_intro',)
NO_TICK = ('pho_intro', 'pho_fire', 'pho_skim', 'pho_taste', 'pho_season', 'pho_sniff', 'pho_toss', 'pho_topup', 'pho_bowl', 'pho_dip',
           'pho_meat', 'pho_onion', 'pho_egg', 'pho_pour', 'pho_stop', 'pho_tie', 'pho_side', 'pho_drop', 'pho_pay', 'pho_short', 'pho_desk')
PHYSICAL = ('pho_dip', 'pho_meat', 'pho_pour', 'pho_topup', 'pho_skim')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'pho_intro':
        d['intro'] = True
        return dict(message='Vào bếp thôi! Nồi nước dùng đang bốc khói dưới gốc si.')
    desk = d['desk']
    if name == 'pho_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'), hook=_desk_hook)
    if name not in ('pho_stop', 'pho_fire'):
        kit.desk_block(desk, 'Có chuyện ở quán, quyết xong rồi bán tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở quán phở.')
    result = fn(s, c, d, p)
    if name not in POT_STILL:
        _pot_tick(d, c)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    if learning(d) or _pouring(c):
        return             # no surprises while bác Lâm is still teaching, nor with the ladle in the air
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc quán phở.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    return t


def _need_open(d: dict) -> None:
    kit.need(d['shop']['open'], 'Chưa mở quán: vặn lửa, hớt bọt, nếm nước, ngửi bánh rồi bấm “Mở quán” nhé.')


def _pouring(c: dict) -> dict | None:
    return next((t for t in c['tasks'] if t.get('career') == ID and t.get('pour') and t['status'] not in ('completed', 'referred', 'cancelled')), None)


# ---------------------------------------------------------------- the pot and the morning
def _fire(s, c, d, p):
    fire = kit.one_of(p.get('fire'), FIRE_T, 'Lửa ủ, lăn tăn hay lửa lớn?')
    d['pot']['fire'] = fire
    line = {'nho': 'lửa ủ liu riu, nồi giữ ấm nhưng không đủ sôi để chín tái.',
            'vua': 'lửa lăn tăn, mặt nồi sủi tăm nhỏ: nước trong, đủ nóng.',
            'lon': 'lửa lớn, nồi sôi sùng sục: nóng nhanh nhưng bọt nổi, nước dễ đục.'}[fire]
    return dict(message=f'🔥 Vặn {_lower(FIRE_LABEL[fire])}: {line}')


def _skim(s, c, d, p):
    pot = d['pot']
    kit.need(pot['foam'] > 0, 'Mặt nồi sạch bọt rồi.')
    pot['foam'] -= 1
    return dict(message='🥄 Hớt một muôi bọt xám trên mặt nồi.' + (' Mặt nồi trong veo rồi.' if not pot['foam'] else f' Còn bọt, hớt tiếp.'))


def _taste(s, c, d, p):
    pot = d['pot']
    pot['tasted'] = True
    d['shop']['tasted'] = True
    word = SALT_WORD[pot['salt']]
    fix = ' Thêm chút nước mắm.' if pot['salt'] < 0 else ' Châm chút nước sôi cho dịu.' if pot['salt'] > 0 else ''
    return dict(message=f'👅 Nếm một thìa nước dùng: {word}.{fix}')


def _season(s, c, d, p):
    what = kit.one_of(p.get('what'), ('mam', 'nuoc'), 'Nêm nước mắm hay châm nước sôi?')
    pot = d['pot']
    if what == 'mam':
        kit.need(pot['salt'] < 2, 'Nồi đã mặn chát rồi, nêm nữa là hỏng.')
        pot['salt'] += 1
        msg = '🫙 Nêm một muôi nước mắm, khuấy đều.'
    else:
        kit.need(pot['salt'] > -2, 'Nồi đã nhạt thếch rồi, châm nữa là nhạt như nước lã.')
        pot['salt'] -= 1
        pot['level'] = min(100, pot['level'] + 3)
        pot['heat'] = max(70, pot['heat'] - 2)
        msg = '💧 Châm một gáo nước sôi, khuấy đều.'
    pot['tasted'] = False
    return dict(message=msg + ' Nếm lại cho chắc.')


def _sniff(s, c, d, p):
    d['shop']['sniffed'] = True
    old = _old_banh(c)
    if not old:
        return dict(message='👃 Bánh phở toàn mẻ mới giao, trắng mềm, thơm mùi gạo.')
    if d['sour']:
        return dict(message=f'👃 {old} nắm bánh hôm qua có mùi chua, sờ vào nhớt tay: bánh đã hỏng. Bỏ, không bán.')
    return dict(message=f'👃 {old} nắm bánh hôm qua vẫn thơm, sợi còn dẻo. Bán trước bánh mới.')


def _toss(s, c, d, p):
    kit.need(d['sour'] and _old_banh(c), 'Không có bánh hỏng.')
    inv = c['ext']['inv']
    keep = []
    n = 0
    for lot in inv['lots']:
        if lot['item'] == 'banh' and lot['received'] < c['day']:
            n += lot['qty']
            if lot['qty']:
                kit.waste(c, 'banh', lot['qty'], lot['qty'] * lot['unit_cost'], 'Bánh phở chua')
        else:
            keep.append(lot)
    inv['lots'] = keep
    d['sour'] = False
    d['shop']['sniffed'] = True
    return dict(message=f'🗑️ Bỏ {n} nắm bánh chua, ghi sổ hao hụt.' + ('' if kit.stock(c, 'banh') else ' Hết bánh rồi: đặt mối bánh giao gấp ở kho.'))


def _open(s, c, d, p):
    t = _task(c, p, ('setup',))
    pot, sh = d['pot'], d['shop']
    kit.need(not sh['open'], 'Quán mở rồi.')
    if pot['fire'] != FIRE_OK:
        t['mistakes'] += 1
        cq.slip(t, 'fire', 1, 'Lửa còn ủ, nồi chưa đủ sôi để chín tái.' if pot['fire'] == 'nho' else 'Để lửa lớn sùng sục, nước sẽ đục ngầu.',
                'lửa chưa lăn tăn')
    if not sh['tasted']:
        t['mistakes'] += 1
        cq.slip(t, 'no_taste', 1, 'Chưa nếm nước đã bán, mặn nhạt thế nào cũng không biết.', 'chưa nếm nước dùng')
    if pot['salt']:
        t['mistakes'] += 1
        cq.slip(t, 'salt', 1, f'Nồi nước còn {SALT_WORD[pot["salt"]]}.', 'nước dùng chưa vừa')
    if pot['foam'] >= FOAM_AT:
        t['mistakes'] += 1
        cq.slip(t, 'foam', 1, 'Mặt nồi còn váng bọt xám.', 'chưa hớt bọt')
    if d['sour'] and _old_banh(c):
        t['mistakes'] += 1
        cq.slip(t, 'sour_left', 2, 'Còn bánh hôm qua chua nằm trong rổ, lỡ trụng bán cho khách.', 'chưa bỏ bánh chua')
    sh['open'] = True
    kit.start_work(t)
    ok = not cq.slips(t)
    kit.complete(s, c, t, 0, 'Vặn lửa, hớt bọt, nếm nước, ngửi bánh.')
    return dict(message='🍜 Mở quán! ' + ('Bác Lâm cười: “Nồi này bán tới trưa vẫn ngọt.”' if ok else 'Bác Lâm dặn: “Mở thì mở, mai nhớ kỹ hơn con nhé.”'),
                celebrate=ok)


def _topup(s, c, d, p):
    pot = d['pot']
    kit.need(not _pouring(c), 'Đang chan dở, dừng muôi đã.')
    kit.need(pot['level'] <= TOPUP_AT, f'Nồi còn {pot["level"]} phần, chưa cần châm.')
    kit.need(kit.stock(c, 'xuong') > 0, 'Hết xương ống. Nhập thêm ở kho nhé.')
    kit.take(c, 'xuong', 1)
    pot['level'] = min(100, pot['level'] + TOPUP)
    pot['heat'] = max(70, pot['heat'] - 10)
    pot['foam'] = min(9, pot['foam'] + 3)
    pot['salt'] = max(-2, pot['salt'] - 1)
    pot['tasted'] = False
    d['today']['topups'] += 1
    d['stats']['topups'] += 1
    return dict(message=f'🦴 Châm nước, thả mẻ xương mới: nồi lên {pot["level"]} phần, tụt còn {pot["heat"]} °C, bọt nổi lên. '
                        'Chờ sôi lại, hớt bọt, nếm lại rồi hẵng chan.')


# ---------------------------------------------------------------- building a bowl
def _need_prep(t: dict) -> None:
    kit.need(t['known'], 'Hỏi khách gọi gì đã nhé.')
    kit.need(t['stage'] == 'prep', 'Đơn này đã tính tiền rồi.')


def _bowl_now(t: dict) -> dict:
    kit.need(t['bowls'], 'Lấy tô hoặc hộp trước đã.')
    return t['bowls'][-1]


def _need_still(t: dict) -> None:
    kit.need(not t['pour'], 'Đang chan nước: bấm “Dừng muôi” đã.')


def _bowl(s, c, d, p):
    t = _task(c, p, ('serve', 'take', 'crew'))
    _need_open(d)
    _need_prep(t)
    _need_still(t)
    v = kit.one_of(p.get('v'), VESSELS, 'Tô thường, tô lớn hay hộp mang về?')
    kit.need(len(t['bowls']) < BOWL_MAX, 'Quầy hết chỗ đặt tô rồi.')
    cost = 0
    if VESSELS[v].get('item'):
        kit.need(kit.stock(c, 'hop') > 0, 'Hết hộp mang về rồi. Nhập thêm ở kho nhé.')
        cost = kit.take(c, 'hop', 1)
    t['bowls'].append(dict(v=v, dip=0, meat=[], side=[], hanh=0, egg=None, lvl=0, src=[], x=[], tied=False, c=cost))
    t['cost'] += cost
    kit.start_work(t)
    x = VESSELS[v]
    return dict(message=f'{x["emoji"]} Lấy {_lower(x["name"])}.' + (' Nước dùng sẽ chan vào túi riêng.' if v == 'hop' else ''))


def _dip(s, c, d, p):
    t = _task(c, p, ('serve', 'take', 'crew'))
    _need_open(d)
    _need_prep(t)
    _need_still(t)
    b = _bowl_now(t)
    kit.need(not b['meat'] and not b['side'] and not b['lvl'], 'Bánh đã vào tô rồi. Muốn trụng lại thì đổ tô làm lại.')
    kit.need(b['dip'] < DIP_MAX, 'Nhúng nữa là bánh nát bấy.')
    if not b['dip']:
        n = VESSELS[b['v']]['banh']
        kit.need(kit.stock(c, 'banh') >= n, 'Hết bánh phở rồi. Nhập thêm ở kho, hoặc nói thật với khách.')
        old = _old_banh(c)
        cost = kit.take(c, 'banh', n)
        b['c'] += cost
        t['cost'] += cost
        if d['sour'] and old:
            b['x'].append('sour')
    b['dip'] += 1
    kit.start_work(t)
    n = b['dip']
    look = ('sợi bánh còn dính chùm, cứng' if n < DIP_OK[0] else 'sợi bánh tơi, mềm, trong' if n <= DIP_OK[1] else 'sợi bánh bắt đầu nát, bở')
    warn = ' ⚠️ Bánh có mùi chua!' if 'sour' in b['x'] and n == 1 else ''
    return dict(message=f'🍜 Nhúng rổ bánh lần {n}: {look}.{warn}')


def _meat(s, c, d, p):
    t = _task(c, p, ('serve', 'take', 'crew'))
    _need_prep(t)
    _need_still(t)
    b = _bowl_now(t)
    kit.need(b['dip'], 'Trụng bánh trước rồi mới xếp thịt lên.')
    kit.need(not b['lvl'], 'Thịt xếp trước rồi mới chan nước. Muốn thêm thì đổ tô làm lại.')
    m = kit.one_of(p.get('m'), MEATS, 'Quán không có phần thịt này.')
    side = bool(p.get('side'))
    kit.need(not side or m == 'tai', 'Chỉ tái mới để riêng.')
    kit.need(m not in b['meat'] and m not in b['side'], f'Tô đã có {_lower(MEATS[m]["name"])} rồi.')
    kit.need(len(b['meat']) + len(b['side']) < CUT_MAX, 'Tô đầy thịt rồi.')
    kit.need(kit.stock(c, m) > 0, f'Hết {_lower(MEATS[m]["name"])} rồi. Nhập thêm ở kho, hoặc nói thật với khách.')
    cost = kit.take(c, m, 1)
    b['c'] += cost
    t['cost'] += cost
    (b['side'] if side else b['meat']).append(m)
    kit.start_work(t)
    x = MEATS[m]
    if side:
        return dict(message=f'{x["emoji"]} Thái tái để riêng ra {"túi nhỏ" if b["v"] == "hop" else "đĩa nhỏ"}.')
    return dict(message=f'{x["emoji"]} ' + ('Thái mỏng thăn bò, xếp tái lên mặt bánh.' if m == 'tai' else f'Xếp {_lower(x["name"])} lên mặt bánh.'))


def _onion(s, c, d, p):
    t = _task(c, p, ('serve', 'take', 'crew'))
    _need_prep(t)
    _need_still(t)
    b = _bowl_now(t)
    kit.need(b['dip'], 'Trụng bánh trước đã.')
    kit.need(b['hanh'] < 3, 'Hành ngập tô rồi.')
    b['hanh'] += 1
    return dict(message='🧅 Rắc một nhúm hành lá, hành tây.' if b['hanh'] == 1 else f'🧅 Rắc thêm hành ({b["hanh"]} nhúm).')


def _egg(s, c, d, p):
    t = _task(c, p, ('serve', 'take', 'crew'))
    _need_prep(t)
    _need_still(t)
    b = _bowl_now(t)
    kit.need(b['dip'], 'Trụng bánh trước đã.')
    kit.need(b['egg'] is None, 'Tô đã có trứng rồi.')
    kit.need(kit.stock(c, 'trung') > 0, 'Hết trứng rồi. Nhập thêm ở kho nhé.')
    cost = kit.take(c, 'trung', 1)
    b['c'] += cost
    t['cost'] += cost
    if b['lvl']:
        b['egg'] = 'raw'
        return dict(message='🥚 Đập quả trứng lên mặt nước: lòng đỏ nằm trơ, nước không còn đủ nóng để chín.')
    b['egg'] = 'ok'
    return dict(message='🥚 Đập quả trứng vào tô, lòng đỏ nằm giữa: chan nước sôi lên là chín tới.')


def _start_hot(d: dict, t: dict) -> None:
    if t['hot']:
        return
    n = sum(1 for b in t['needs']['lines'] if b['v'] != 'hop')
    limit = (HOT_BASE + HOT_UNIT * n) * HOT_MOD.get(mod_of(t['day'])['id'], 100) // 100
    t['hot'] = dict(start=round(kit.now(), 3), limit=int(limit), end=None)


def _pour(s, c, d, p):
    t = _task(c, p, ('serve', 'take', 'crew'))
    _need_open(d)
    _need_prep(t)
    b = _bowl_now(t)
    kit.need(not _pouring(c), 'Đang chan một tô khác: dừng muôi đã.')
    kit.need(b['dip'], 'Trụng bánh vào tô trước rồi mới chan.')
    src = kit.one_of(p.get('src', 'trong'), SOURCES, 'Múc nồi nào?')
    x = VESSELS[b['v']]
    kit.need(b['lvl'] < SPILL[kind_of(b['v'])], 'Đầy tới miệng rồi.')
    if b['v'] == 'hop':
        kit.need(not b['tied'], 'Túi nước buộc rồi.')
    if src == 'nho':
        kit.need(d['small'] >= x['vol'] * 2, 'Nồi nhỏ không mì chính hết rồi. Nói thật với khách nhé.')
    else:
        kit.need(d['pot']['level'] >= x['vol'], 'Nồi lớn cạn rồi: châm nước, thả xương rồi chờ sôi lại.')
    t['pour'] = dict(start=round(kit.now(), 3), base=int(b['lvl']), src=src, rate=x['rate'])
    kit.start_work(t)
    where = 'túi nước' if b['v'] == 'hop' else _lower(x['name'])
    return dict(message=f'🫗 {SOURCES[src]}: muôi nước dùng nghiêng vào {where}… Bấm “Dừng muôi” đúng vạch.')


def level_at(pour: dict, at: float) -> int:
    return int(pour['base'] + max(0.0, at - pour['start']) * pour['rate'])


def _stop(s, c, d, p):
    t = _task(c, p, ('serve', 'take', 'crew'))
    pr = t['pour']
    kit.need(pr, 'Đang không chan nước.')
    b = _bowl_now(t)
    lvl = min(110, level_at(pr, kit.tap_now(p)))
    added = max(0, lvl - pr['base'])
    t['pour'] = None
    k = kind_of(b['v'])
    spill = lvl >= SPILL[k]
    b['lvl'] = min(100, lvl)
    x = VESSELS[b['v']]
    used = (added * x['vol'] + 99) // 100
    pot = d['pot']
    first = not b['src']
    if pr['src'] not in b['src']:
        b['src'] = sorted(b['src'] + [pr['src']])
    flags = b['x']
    if pr['src'] == 'nho':
        d['small'] = max(0, d['small'] - used * 2)
        heat = 97
    else:
        pot['level'] = max(0, pot['level'] - used)
        heat = pot['heat']
        pot['heat'] = max(70, pot['heat'] - (2 if mod_of(c['day'])['id'] == 'cold' else 1))
        if pot['cloud'] >= CLOUD_AT and 'cloudy' not in flags:
            flags.append('cloudy')
        if pot['foam'] >= FOAM_AT and 'foam' not in flags:
            flags.append('foam')
        if pot['salt'] < 0 and 'bland' not in flags:
            flags.append('bland')
        elif pot['salt'] > 0 and 'salty' not in flags:
            flags.append('salty')
    if first and added:
        if 'tai' in b['meat'] and heat < TAI_COOK:
            flags.append('tai_raw')
        if b['v'] != 'hop':
            _start_hot(d, t)
    if spill and 'spill' not in flags:
        flags.append('spill')
        d['today']['spills'] += 1
        d['stats']['spills'] += 1
    del flags[8:]
    if b['v'] == 'hop':
        word = 'tràn miệng túi, không buộc được!' if spill else 'túi căng tròn' if lvl >= 80 else 'túi vừa buộc' if lvl >= 58 else 'túi còn lưng lửng'
    else:
        word = ('tràn ra mép tô!' if spill else 'gần miệng tô' if lvl >= 88 else 'ngập mặt bánh, cách miệng tô một đốt ngón tay' if lvl >= 70
                else 'xâm xấp mặt bánh' if lvl >= 52 else 'chưa ngập bánh')
    tail = ' ⚠️ Tái còn đỏ, nước chưa đủ sôi!' if 'tai_raw' in flags and first and added else ''
    return dict(message=f'🫗 Dừng muôi: nước tới {b["lvl"]}%, {word}.{tail}')


def _tie(s, c, d, p):
    t = _task(c, p, ('take', 'crew'))
    _need_prep(t)
    _need_still(t)
    b = _bowl_now(t)
    kit.need(b['v'] == 'hop', 'Chỉ túi nước mang về mới buộc.')
    kit.need(b['lvl'] > 0, 'Túi chưa có nước.')
    kit.need(not b['tied'], 'Túi buộc rồi.')
    b['tied'] = True
    return dict(message='🎀 Xoắn miệng túi, buộc hai vòng thun, xếp vào hộp cạnh bánh.')


def _side(s, c, d, p):
    t = _task(c, p, ('serve', 'take', 'crew'))
    _need_prep(t)
    item = kit.one_of(p.get('item'), SIDES, 'Quẩy hay đĩa rau?')
    sd = t['side']
    if item == 'rau':
        kit.need(not sd['rau'], 'Đã có đĩa rau rồi.')
    else:
        kit.need(sd['quay'] < 8, 'Đủ quẩy rồi.')
    kit.need(kit.stock(c, item) > 0, 'Hết quẩy rồi.' if item == 'quay' else 'Hết rau thơm rồi.')
    cost = kit.take(c, item, 1)
    t['cost'] += cost
    if item == 'rau':
        sd['rau'] = True
        return dict(message='🌿 Bưng đĩa rau húng, ngò gai, giá chần, chanh ớt.')
    sd['quay'] += 1
    return dict(message=f'🥖 Gắp quẩy ra đĩa ({sd["quay"]} cái).')


def _drop(s, c, d, p):
    """Pour away the bowl being made (a wrong cut, cold broth, stiff noodles)."""
    t = _task(c, p, ('serve', 'take', 'crew'))
    _need_prep(t)
    _need_still(t)
    b = _bowl_now(t)
    t['bowls'].pop()
    t['cost'] = max(0, t['cost'] - b['c'])
    if b['c']:
        kit.waste(c, 'banh', 1, b['c'], 'Tô phở làm lại')
    return dict(message=f'🗑️ Đổ {_lower(VESSELS[b["v"]]["name"])} vừa làm, làm lại.')


# ---------------------------------------------------------------- handing it over
def bowl_price(c: dict, b: dict) -> int:
    v = _p(c, VESSELS[b['v']]['price']) + _p(c, 'them') * max(0, len(b['meat']) + len(b['side']) - 2)
    if b['egg']:
        v += _p(c, 'trung')
    return v


def _match(t: dict) -> tuple[list, list, list]:
    """Pair the bowls on the counter with the bowls of the order: (pairs, lines left, bowls left)."""
    bowls = list(range(len(t['bowls'])))
    pairs, left = [], []
    for li, ln in enumerate(t['needs']['lines']):
        want = sorted(ln['meat'])
        hit = next((bi for bi in bowls if t['bowls'][bi]['v'] == ln['v']
                    and sorted(t['bowls'][bi]['meat'] + t['bowls'][bi]['side']) == want), None)
        if hit is None:
            left.append(li)
        else:
            bowls.remove(hit)
            pairs.append((li, hit))
    return pairs, left, bowls


def _checks(c: dict, d: dict, t: dict, pairs: list, left: list, extra: list) -> None:
    """Record what the customer will notice at the hand-over."""
    n = t['needs']
    check = bool(n.get('check'))
    if left:
        t['mistakes'] += 1
        cq.slip(t, 'missing', 2, f'Tôi gọi {line_text(n["lines"][left[0]])} mà không phải tô này.', 'sai món, thiếu tô')
    if extra:
        t['mistakes'] += 1
        cq.slip(t, 'extra', 1, 'Có tô tôi đâu có gọi.', 'đưa thừa tô')
    flags = {f for b in t['bowls'] for f in b['x']}
    if 'sour' in flags:
        t['mistakes'] += 1
        cq.slip(t, 'sour', 3, 'Bánh phở chua lè, nhớt nhớt. Bánh hôm qua phải không?', 'bán bánh phở chua', safety=True)
    dips = [b['dip'] for b in t['bowls']]
    if any(x < DIP_OK[0] for x in dips):
        t['mistakes'] += 1
        cq.slip(t, 'stiff', 1, 'Bánh dính chùm, cứng như chưa trụng.', 'bánh trụng chưa tới')
    elif any(x > DIP_OK[1] for x in dips):
        t['mistakes'] += 1
        cq.slip(t, 'soggy', 1, 'Bánh nát bấy, gắp lên đứt từng khúc.', 'bánh trụng quá lâu')
    if 'tai_raw' in flags:
        t['mistakes'] += 1
        d['today']['raw'] += 1
        d['stats']['raw'] += 1
        cq.slip(t, 'tai_raw', 2, 'Tái còn đỏ au, nước chan vào chẳng nóng gì cả.', 'nước chưa sôi, tái sống')
    if 'cloudy' in flags:
        t['mistakes'] += 1
        d['today']['cloudy'] += 1
        d['stats']['cloudy'] += 1
        cq.slip(t, 'cloudy', 2 if check else 1, 'Nước dùng đục ngầu, không thấy đáy tô.', 'sôi to lửa, nước đục')
    elif 'foam' in flags:
        t['mistakes'] += 1
        cq.slip(t, 'foam', 1, 'Mặt tô lổn nhổn váng bọt xám.', 'chưa hớt bọt')
    if 'bland' in flags or 'salty' in flags:
        t['mistakes'] += 1
        cq.slip(t, 'salt', 2 if check else 1, 'Nước dùng nhạt quá.' if 'bland' in flags else 'Nước dùng mặn chát.', 'nước dùng chưa nêm vừa')
    if 'spill' in flags:
        t['mistakes'] += 1
        cq.slip(t, 'spill', 2, 'Nước tràn cả ra mép, bưng vào nóng bỏng tay.' if any(b['v'] != 'hop' for b in t['bowls'])
                else 'Túi nước căng quá, buộc không được, rỉ ra cả hộp.', 'chan tràn')
    for li, bi in pairs:
        ln, b = n['lines'][li], t['bowls'][bi]
        lo, hi = band(ln)
        if b['lvl'] < lo and 'spill' not in b['x']:
            t['mistakes'] += 1
            cq.slip(t, f'little_{li}', 1, 'Nước xâm xấp, bánh khô cong.' if ln['nuoc'] != 'it' else 'Ít nước thì ít, chứ khô thế này sao ăn.',
                    'chan thiếu nước')
        elif b['lvl'] > hi and 'spill' not in b['x']:
            t['mistakes'] += 1
            cq.slip(t, f'much_{li}', 1, 'Tôi dặn ít nước mà.' if ln['nuoc'] == 'it' else 'Nước đầy quá, bưng sóng sánh.', 'chan nhiều nước quá')
        if ln['src'] == 'nho' and b['src'] != ['nho']:
            t['mistakes'] += 1
            cq.slip(t, 'msg', 2, f'{_who(t)} húp một thìa, cau mày: “Dặn không mì chính rồi mà.”', 'khách dặn không mì chính')
        elif ln['src'] == 'beo' and 'beo' not in b['src']:
            t['mistakes'] += 1
            cq.slip(t, f'not_fatty_{li}', 1, 'Tôi dặn nước béo mà sao nhạt mỡ thế này.', 'quên nước béo')
        h = b['hanh']
        if ln['hanh'] == 'khong' and h:
            t['mistakes'] += 1
            cq.slip(t, f'onion_{li}', 1, 'Đã dặn không hành rồi mà.', 'khách dặn không hành')
        elif ln['hanh'] == 'nhieu' and h < 2:
            t['mistakes'] += 1
            cq.slip(t, f'onion_{li}', 1, 'Tôi dặn nhiều hành mà, có mấy cọng.', 'quên nhiều hành')
        elif ln['hanh'] == 'vua' and not h:
            t['mistakes'] += 1
            cq.slip(t, f'no_onion_{li}', 1, 'Phở gì mà không có cọng hành nào.', 'quên rắc hành')
        elif ln['hanh'] == 'vua' and h > 2:
            t['mistakes'] += 1
            cq.slip(t, f'onion_{li}', 1, 'Hành ngập tô, hăng quá.', 'rắc nhiều hành quá')
        if ln['egg'] and not b['egg']:
            t['mistakes'] += 1
            cq.slip(t, f'egg_{li}', 1, 'Tôi gọi trứng trần mà không thấy trứng.', 'quên trứng')
        elif ln['egg'] and b['egg'] == 'raw':
            t['mistakes'] += 1
            cq.slip(t, f'egg_raw_{li}', 1, 'Lòng đỏ sống nhớt nằm trên mặt tô.', 'đập trứng sau khi chan')
        elif not ln['egg'] and b['egg']:
            t['mistakes'] += 1
            cq.slip(t, f'egg_{li}', 1, 'Có trứng đâu tôi gọi.', 'thêm trứng khách không gọi')
        if ln['rieng'] and 'tai' in b['meat']:
            t['mistakes'] += 1
            cq.slip(t, f'tai_mixed_{li}', 1, 'Dặn tái để riêng mà, về tới nơi tái chín nhừ rồi.', 'quên để riêng tái')
        if b['v'] == 'hop' and not b['tied']:
            t['mistakes'] += 1
            cq.slip(t, f'untied_{li}', 2, 'Túi nước không buộc, đổ lênh láng cả túi xách.', 'quên buộc túi nước')
    sd = t['side']
    if n.get('quay') and sd['quay'] < n['quay']:
        t['mistakes'] += 1
        cq.slip(t, 'quay', 1, f'Tôi gọi {n["quay"]} cái quẩy mà.', 'thiếu quẩy')
    if n.get('rau') and not sd['rau']:
        t['mistakes'] += 1
        cq.slip(t, 'rau', 1, 'Cho anh xin dĩa rau với giá chứ em.', 'quên đĩa rau')
    hot = t['hot']
    if hot:
        el = (hot['end'] if hot['end'] is not None else kit.now()) - hot['start']
        if el > hot['limit'] * 8 / 5:
            t['mistakes'] += 1
            d['today']['cold'] += 1
            d['stats']['cold'] += 1
            cq.slip(t, 'cold', 2, 'Phở bưng ra nguội ngắt, bánh trương phình.', 'bưng ra quá chậm, phở nguội')
        elif el > hot['limit']:
            t['mistakes'] += 1
            cq.slip(t, 'cooling', 1, 'Phở hơi nguội rồi.', 'bưng ra hơi chậm')


def _serve(s, c, d, p):
    t = _task(c, p, ('serve', 'take', 'crew'))
    _need_open(d)
    _need_prep(t)
    _need_still(t)
    kit.need(t['bowls'], 'Chưa có tô nào trên quầy.')
    kit.need(all(b['dip'] for b in t['bowls']), 'Còn tô chưa có bánh: trụng bánh hoặc bỏ tô đó ra.')
    kit.need(all(b['lvl'] for b in t['bowls']), 'Còn tô chưa chan nước dùng.')
    caught = _catch(c, d, t)
    if caught:
        return caught
    pairs, left, extra = _match(t)
    _checks(c, d, t, pairs, left, extra)
    sd = t['side']
    price = sum(bowl_price(c, t['bowls'][bi]) for _, bi in pairs) + _p(c, 'quay') * min(sd['quay'], max(t['needs'].get('quay', 0), 0))
    t['price'] = max(1, price) if pairs else 1
    if t['hot'] and t['hot']['end'] is None:
        t['hot']['end'] = round(kit.now(), 3)
    n = len(t['bowls'])
    d['today']['bowls'] += n
    d['stats']['bowls'] += n
    t['stage'] = 'pay'
    t['cash'] = till.new(t['price'], t['id'], c=c, t=t)
    rec = t['cash']
    head = (f'🥡 Đưa {n} suất mang về cho {_who(t)}' if all(b['v'] == 'hop' for b in t['bowls']) else
            f'🍜 Bưng phở ra cho {_who(t)}, khách ăn xong ra quầy') + f' · {t["price"]} xu.'
    if 'sp' in rec:
        return dict(message=head)
    return dict(message=f'{head} Khách đưa {sum(rec["tender"])} xu: thối lại cho đúng.')


def learning(d: dict) -> bool:
    """Học nghề: the first APPRENTICE customers, bác Lâm at your side."""
    return not d['learn']['done'] and d['stats']['customers'] < APPRENTICE


def _catch(c: dict, d: dict, t: dict) -> dict | None:
    """While learning, bác Lâm looks at the bowls before they go out: the first time a mistake shows he stops you
    and says how to fix it (nothing is recorded). The same mistake again goes through, and a cooling bowl is
    never held back (time cannot be undone)."""
    if not learning(d):
        return None
    lr = d['learn']
    if lr['task'] != t['id']:
        lr['task'], lr['codes'] = t['id'], []
    tt, dd = copy.deepcopy(t), copy.deepcopy(d)
    pairs, left, extra = _match(tt)
    _checks(c, dd, tt, pairs, left, extra)
    for x in cq.slips(tt):
        code = x['code'].rsplit('_', 1)[0] if x['code'][-1:].isdigit() else x['code']
        if code in CATCH and code not in lr['codes']:
            lr['codes'].append(code)
            return dict(message=f'🧑‍🍳 Bác Lâm: “{CATCH[code]}”', correct=False, lesson=code)
    return None


def _graduate(d: dict) -> str:
    if d['learn']['done'] or d['stats']['customers'] < APPRENTICE:
        return ''
    d['learn'].update(done=True, task=None, codes=[])
    return ' 🎓 Học nghề xong! Bác Lâm: “Giờ con đứng bếp một mình được rồi. Bác ra chợ mua xương đây.”'


def _decline(s, c, d, p):
    """Out of what the customer wants: say so honestly."""
    t = _task(c, p, ('serve', 'take', 'crew'))
    kit.need(t['known'] and t['stage'] == 'prep', 'Không phải lúc này.')
    _need_still(t)
    for b in t['bowls']:
        if b['c']:
            kit.waste(c, 'banh', 1, b['c'], 'Đơn không bán được')
    t['bowls'], t['cost'], t['choice'] = [], 0, 'decline'
    kit.start_work(t)
    msg = _finish(s, c, d, t, 0, f'Nói thật với {_who(t)}: quán hết món khách gọi, hẹn hôm sau.')
    return dict(message='🙏 ' + msg)


def _pay(s, c, d, p):
    t = _task(c, p, ('serve', 'take', 'crew'))
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
    grad = _graduate(d)
    return dict(message=f'{head} {msg}{grad}'.strip(), celebrate=not cq.slips(t) or bool(grad))


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
    t['pour'] = None
    kit.complete(s, c, t, max(0, int(reward)), (narrative or t['title'])[:300])
    return f'{narrative} 💬 {story}'.strip() if story else narrative


def _desk_hook(s: dict, c: dict, key: str, v) -> str | None:
    d = _data(c)
    pot = d['pot']
    if key == 'heat':
        pot['heat'] = max(70, min(100, pot['heat'] + int(v)))
        return f'Nồi nước còn {pot["heat"]} °C.'
    if key == 'pot':
        pot['level'] = max(0, min(100, pot['level'] + int(v)))
        return None
    return None


ACTIONS = {
    'pho_fire': _fire, 'pho_skim': _skim, 'pho_taste': _taste, 'pho_season': _season, 'pho_sniff': _sniff, 'pho_toss': _toss,
    'pho_open': _open, 'pho_topup': _topup,
    'pho_bowl': _bowl, 'pho_dip': _dip, 'pho_meat': _meat, 'pho_onion': _onion, 'pho_egg': _egg, 'pho_pour': _pour, 'pho_stop': _stop,
    'pho_tie': _tie, 'pho_side': _side, 'pho_drop': _drop, 'pho_serve': _serve, 'pho_decline': _decline, 'pho_pay': _pay,
    'pho_short': lambda s, c, d, p: _short(s, c, p),
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['pot'] = dict(level=100, heat=88, fire='nho', foam=foam_of(day), cloud=0, salt=salt_of(day), tasted=False)
    d['small'] = SMALL_MAX
    d['shop'] = _fresh_shop(day)
    d['today'] = _fresh_today(day)
    # Yesterday's bánh phở: some mornings it has gone sour overnight.
    d['sour'] = bool(day >= 2 and _old_banh(c) and kit.rng(ID, 'sour', day).randrange(100) < 45)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
        if t.get('career') == ID and t.get('pour'):
            t['pour'] = None     # a ladle left in the air overnight
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


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK, hook=_desk_hook)
    today = d['today']
    for t in c['tasks']:
        if t.get('career') == ID and t.get('pour'):
            t['pour'] = None
    lines = [f'🍜 Bưng {today["bowls"]} tô phở cho {today["customers"]} khách.']
    if today['cloudy']:
        lines.append(f'🍲 Bác Lâm nhìn nồi: “Lửa lớn lâu quá, nước đục rồi con. Có {today["cloudy"]} khách chê. Lăn tăn thôi là trong.”')
    elif today['raw']:
        lines.append(f'🥩 Có {today["raw"]} tô tái còn đỏ: nồi chưa sôi đã chan. Châm nồi xong nhớ chờ lăn tăn lại.')
    elif today['bowls']:
        lines.append('🍲 Bác Lâm múc thìa nước cuối nồi: “Nước vẫn trong, ngọt. Được.”')
    if today['cold']:
        lines.append(f'⏱️ Có {today["cold"]} lần phở bưng ra đã nguội.')
    if today['topups']:
        lines.append(f'🦴 Châm nồi {today["topups"]} lần.')
    if desk_note:
        lines.append(desk_note)
    left = kit.stock(c, 'banh')
    old = left   # tonight's bánh is tomorrow's "bánh hôm qua"
    if old:
        lines.append(f'🌅 Ngày mai: còn {old} nắm bánh để qua đêm. Sáng mai nhớ ngửi bánh trước khi trụng.')
    d['shop'].update(open=False)
    pot = d['pot']
    pot['fire'] = 'nho'
    return dict(lines=lines, note=f'Kho còn {left} nắm bánh, {kit.stock(c, "xuong")} mẻ xương, {kit.stock(c, "tai")} phần tái.',
                bowls=today['bowls'], customers=today['customers'], topups=today['topups'])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 85 else 4 if p >= 65 else 3 if p >= 45 else 2
    codes = {x['code'] for x in cq.slips(t)}
    base = {k.rsplit('_', 1)[0] if k[-1:].isdigit() else k for k in codes}
    if t['kind'] == 'setup':
        pot = 5 - len(base & {'fire', 'foam', 'salt', 'no_taste'})
        clean = 5 - len(base & {'sour_left'}) * 3
        return dict(criteria=[dict(key='broth', label='Nồi nước dùng', score=max(1, pot), note='lăn tăn, sạch bọt, vừa miệng' if pot == 5 else 'nồi chưa sẵn sàng'),
                              dict(key='clean', label='Bánh tươi, sạch', score=max(1, clean), note='ngửi bánh, bỏ bánh cũ' if clean == 5 else 'còn bánh chua')])
    if t.get('choice') == 'decline':
        return dict(criteria=[dict(key='honest', label='Nói thật', score=5, note='hết món thì nói thật'),
                              dict(key='order', label='Có món đúng ý', score=3, note='lần này chưa có')])
    order = 2 if 'missing' in base else 4 if base & {'extra', 'onion', 'no_onion', 'egg', 'egg_raw', 'quay', 'rau', 'tai_mixed', 'not_fatty'} else 5
    broth = 2 if base & {'tai_raw', 'cold', 'msg'} else 3 if base & {'cloudy', 'salt', 'little', 'much', 'cooling'} else 4 if 'foam' in base else 5
    banh = 3 if base & {'stiff', 'soggy'} else 5
    clean = 1 if 'sour' in base else 3 if base & {'spill', 'untied'} else 5
    return dict(criteria=[dict(key='order', label='Đúng món, đúng lời dặn', score=order, note='đúng thịt, nhớ lời dặn' if order == 5 else 'chưa đúng lời dặn'),
                          dict(key='broth', label='Nước dùng trong, nóng', score=broth, note='trong, ngọt, nóng hổi' if broth == 5 else 'nước dùng chưa ngon'),
                          dict(key='banh', label='Bánh tơi mềm', score=banh, note='bánh tơi, mềm' if banh == 5 else 'bánh cứng hoặc nát'),
                          dict(key='clean', label='Sạch sẽ, an toàn', score=clean, note='bánh tươi, gọn gàng' if clean == 5 else 'chưa sạch, chưa an toàn'),
                          dict(key='speed', label='Nhanh gọn', score=speed, note=f'chờ còn {p}% kiên nhẫn')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return 'Bác Lâm dặn: vặn lửa lăn tăn, hớt bọt, nếm và nêm nước dùng, ngửi bánh hôm qua (chua thì bỏ) rồi mở quán. ' + n['note']
    lines = '; '.join(line_text(x) for x in n['lines'])
    tail = ''
    if n.get('quay'):
        tail += f' Thêm {n["quay"]} cái quẩy.'
    if n.get('rau'):
        tail += ' Xin đĩa rau, giá.'
    if n.get('check'):
        tail += ' Khách sành ăn, nếm nước rất kỹ.'
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
    for k in ('pot', 'shop'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    mod = mod_of(c['day'])
    pot = d['pot']
    stock = {x['id']: kit.stock(c, x['id']) for x in ITEMS} if c['ext'].get('inv') else {}
    return dict(intro=d['intro'], shop=d['shop'],
                pot=dict(level=pot['level'], heat=pot['heat'], fire=pot['fire'], foam=pot['foam'], cloudy=pot['cloud'] >= CLOUD_AT,
                         word=heat_word(pot['heat']), taste=SALT_WORD[pot['salt']] if pot['tasted'] else None, salt=pot['salt'] if pot['tasted'] else None),
                small=d['small'], sour=bool(d['sour']) if d['shop'].get('sniffed') else None, old_banh=_old_banh(c) if c['ext'].get('inv') else 0,
                stock=stock, mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                today=d['today'], stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                desk=kit.desk_public(d['desk'], DESK, ID), learn=_learn_public(d))


def _learn_public(d: dict) -> dict:
    on = not d['learn']['done'] and d['stats']['customers'] < APPRENTICE
    n = min(d['stats']['customers'], APPRENTICE - 1)
    return dict(on=on, n=d['stats']['customers'], of=APPRENTICE, title=LESSONS[n][0] if on else None, text=LESSONS[n][1] if on else None)


def content() -> dict:
    return dict(vessels={k: dict(name=v['name'], emoji=v['emoji'], banh=v['banh'], rate=v['rate'], bag=k == 'hop') for k, v in VESSELS.items()},
                meats=MEATS, sources=SOURCES, source_note=SOURCE_NOTE, bands={k: {kk: list(vv) for kk, vv in v.items()} for k, v in BANDS.items()},
                spill=SPILL, nuoc=NUOC_LABEL, hanh=HANH, dip_ok=list(DIP_OK), fire=FIRE_T, fire_label=FIRE_LABEL, fire_ok=FIRE_OK,
                tai_cook=TAI_COOK, foam_at=FOAM_AT, level_low=LEVEL_LOW, topup_at=TOPUP_AT, small_max=SMALL_MAX, prices=PRICES,
                denoms=list(till.DENOMS), intro=INTRO, people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE], apprentice=APPRENTICE)


def hint(c: dict, t: dict) -> str:
    if t.get('kind') == 'setup':
        return 'Vặn lửa lăn tăn → hớt bọt → nếm, nêm cho vừa → ngửi bánh hôm qua (chua thì bỏ) → Mở quán.'
    if t.get('kind') in ('take', 'crew'):
        return 'Hỏi khách → lấy hộp → nhúng bánh 3–4 lượt → xếp thịt (tái để riêng) → chan túi nước, dừng đúng vạch → buộc túi → thu tiền.'
    return 'Hỏi khách → lấy tô → nhúng bánh 3–4 lượt → xếp thịt → hành, trứng → chan nước, dừng muôi đúng vạch → bưng ra khi còn nóng → thu tiền.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = _data(c)
    if e.get('role') == 'skim':
        d['pot']['foam'] = 0
        return 'Đã hớt sạch bọt trên mặt nồi.'
    if e.get('role') == 'table':
        return 'Đã lau bàn, thay ống đũa, rót sẵn trà đá.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu quán phở sai.')


def _vnum(x, lo, hi) -> None:
    kit.need(type(x) in (int, float) and lo <= x <= hi, 'Dữ liệu quán phở sai.')


BOWL_KEYS = {'v', 'dip', 'meat', 'side', 'hanh', 'egg', 'lvl', 'src', 'x', 'tied', 'c'}
FLAGS = {'sour', 'tai_raw', 'cloudy', 'foam', 'bland', 'salty', 'spill'}


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc quán phở không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc quán phở sai.')
    bowls = t.get('bowls')
    kit.need(isinstance(bowls, list) and len(bowls) <= BOWL_MAX, 'Tô trên quầy sai.')
    for b in bowls:
        kit.need(isinstance(b, dict) and set(b) == BOWL_KEYS and b['v'] in VESSELS, 'Tô trên quầy sai.')
        kit.integer(b['dip'], 0, DIP_MAX)
        kit.need(isinstance(b['meat'], list) and isinstance(b['side'], list) and len(b['meat']) + len(b['side']) <= CUT_MAX
                 and all(m in MEATS for m in b['meat'] + b['side']) and len(set(b['meat'] + b['side'])) == len(b['meat']) + len(b['side'])
                 and set(b['side']) <= {'tai'}, 'Thịt trong tô sai.')
        kit.integer(b['hanh'], 0, 3)
        kit.need(b['egg'] in (None, 'ok', 'raw'), 'Trứng trong tô sai.')
        kit.integer(b['lvl'], 0, 100)
        kit.need(isinstance(b['src'], list) and len(b['src']) <= 3 and all(x in SOURCES for x in b['src']) and b['src'] == sorted(set(b['src'])),
                 'Nước dùng trong tô sai.')
        kit.need(isinstance(b['x'], list) and len(b['x']) <= 8 and all(x in FLAGS for x in b['x']) and len(set(b['x'])) == len(b['x']), 'Tô trên quầy sai.')
        _vbool(b['tied'])
        kit.integer(b['c'], 0, 10000)
    sd = t.get('side')
    kit.need(isinstance(sd, dict) and set(sd) == {'quay', 'rau'}, 'Đồ ăn kèm sai.')
    kit.integer(sd['quay'], 0, 8)
    _vbool(sd['rau'])
    pr = t.get('pour')
    if pr is not None:
        kit.need(isinstance(pr, dict) and set(pr) == {'start', 'base', 'src', 'rate'} and pr['src'] in SOURCES and bowls, 'Muôi nước dùng sai.')
        _vnum(pr['start'], 0, 10 ** 11)
        kit.integer(pr['base'], 0, 100)
        kit.need(pr['rate'] in {x['rate'] for x in VESSELS.values()}, 'Muôi nước dùng sai.')
    h = t.get('hot')
    if h is not None:
        kit.need(isinstance(h, dict) and set(h) == {'start', 'limit', 'end'}, 'Đồng hồ phở nguội sai.')
        _vnum(h['start'], 0, 10 ** 11)
        kit.integer(h['limit'], 1, 1000)
        if h['end'] is not None:
            _vnum(h['end'], 0, 10 ** 11)
    if t.get('price') is not None:
        kit.integer(t['price'], 0, 10 ** 6)
    kit.integer(t.get('cost'), 0, 10 ** 6)
    kit.need(t.get('choice') in (None, 'decline'), 'Cách giải quyết sai.')
    till.validate(t.get('cash'), t)
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách quen sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    _vbool(d['sour'])
    till.validate_book(c)
    sh = d['shop']
    kit.need(isinstance(sh, dict) and set(sh) == {'day', 'open', 'tasted', 'sniffed'}, 'Quán phở sai.')
    kit.integer(sh['day'], 0, 10 ** 7)
    for k in ('open', 'tasted', 'sniffed'):
        _vbool(sh[k])
    pot = d['pot']
    kit.need(isinstance(pot, dict) and set(pot) == {'level', 'heat', 'fire', 'foam', 'cloud', 'salt', 'tasted'}, 'Nồi nước dùng sai.')
    kit.integer(pot['level'], 0, 100)
    kit.integer(pot['heat'], 70, 100)
    kit.need(pot['fire'] in FIRE_T, 'Nồi nước dùng sai.')
    kit.integer(pot['foam'], 0, 9)
    kit.integer(pot['cloud'], 0, 9)
    kit.need(type(pot['salt']) is int and -2 <= pot['salt'] <= 2, 'Nồi nước dùng sai.')
    _vbool(pot['tasted'])
    kit.integer(d['small'], 0, SMALL_MAX)
    lr = d['learn']
    kit.need(isinstance(lr, dict) and set(lr) == {'task', 'codes', 'done'}, 'Học nghề sai.')
    kit.need(lr['task'] is None or (isinstance(lr['task'], str) and len(lr['task']) <= 80), 'Học nghề sai.')
    kit.need(isinstance(lr['codes'], list) and len(lr['codes']) <= len(CATCH) and set(lr['codes']) <= set(CATCH), 'Học nghề sai.')
    _vbool(lr['done'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu quán phở sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='pho_', category='food',
    meta=dict(short='Bán phở', place='Quán phở Cây Si', tagline='Nước trong, tái hồng, bánh tơi.', icon='pho',
              color='#c8642a', light='#fff0e3', weather='Sáng sớm đầu ngõ', work='Khách gọi phở', station='Nồi nước dùng & rổ trụng',
              greeting='Vặn lửa lăn tăn, hớt bọt, nếm nước rồi mở quán. Mỗi tô: nhúng bánh ba bốn lượt, xếp thịt, chan nước dừng muôi đúng vạch khách dặn nhé.',
              caption='Nồi nước lăn tăn từ ba giờ sáng', map_label='26 · QUÁN PHỞ CÂY SI'),
    people=PEOPLE,
    staff=[('Tí', 'skim', 'Cháu bác Lâm, hớt bọt, canh nồi chăm chỉ.', 76, 90),
           ('Mai', 'table', 'Sinh viên làm thêm ca sáng, bưng bê nhanh nhẹn.', 84, 76),
           ('Hưng', 'skim', 'Thợ phụ bếp cũ, nhìn mặt nồi là biết sôi già hay non.', 72, 94),
           ('Thảo', 'table', 'Nhớ mặt khách quen, rót trà đá không ai phải gọi.', 80, 82)],
    roles={'skim': 'Canh nồi, hớt bọt', 'table': 'Dọn bàn, rót trà'},
    inventory=dict(items=ITEMS, capacity=80),
    prices=PRICES,
    tip=1,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('🍜', 'Bếp phở gọn gàng', [('Nồi nước dùng', 'Ninh từ ba giờ sáng'), ('Rổ trụng', 'Nồi nước sôi riêng'),
                                        ('Thớt thịt', 'Tái, chín, nạm, gầu'), ('Rổ quẩy', 'Quẩy giòn mới chiên')],
              ['Vặn lửa lăn tăn, hớt bọt', 'Nếm nước, nêm cho vừa', 'Nhúng bánh, xếp thịt', 'Chan nước, bưng ra, thu tiền']),
    stories=[('Nồi xương ba giờ sáng', ('Ba giờ sáng bác Lâm đã chần xương, rửa sạch, thả vào nồi nước lạnh.',
                                       'Gừng, hành nướng thơm lừng, quế hồi thảo quả rang vừa dậy mùi.',
                                       'Lửa lăn tăn suốt đêm, nước trong như hổ phách.')),
             ('Muôi đồng của bác Lâm', ('Cái muôi đồng sáng bóng treo cạnh nồi, cán quấn vải.',
                                       'Bác bảo muôi nào cũng được, quan trọng là dừng tay đúng lúc.',
                                       'Từ đó bạn nhìn vạch nước trong tô trước khi bưng ra.')),
             ('Ông giáo và tờ báo', ('Sáng nào ông giáo Thụ cũng ngồi bàn trong cùng, trải tờ báo.',
                                    'Ông chỉ cần nếm một thìa là biết nồi hôm nay sôi to hay nhỏ.',
                                    'Bác Lâm bảo: “Khách như ông giáo là thầy dạy nấu phở.”'))],
    review_asides=['Nước dùng trong veo, ngọt xương.', 'Tái chín hồng, bánh tơi mềm.', 'Nhớ cả lời dặn không mì chính của tôi.',
                   'Bưng ra còn nóng hổi, khói nghi ngút.'],
    situations=SITUATIONS,
    guide='Vặn lửa lăn tăn → hớt bọt → nếm, nêm → ngửi bánh → mở quán. Mỗi khách: hỏi gọi gì → lấy tô → nhúng bánh 3–4 lượt → xếp thịt → '
          'hành, trứng → chan nước, dừng muôi đúng vạch → bưng ra → thu tiền.',
)
