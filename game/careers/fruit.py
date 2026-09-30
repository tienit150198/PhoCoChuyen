"""Sạp trái cây Dì Tư: a fruit stall at the mouth of the Mây market (plugin career).

Dì Tư goes to the wholesale market before dawn; the player minds the stall. What the job is:

* set up in the morning (``setup`` task): put the umbrella up (the tarp on a rainy day), test
  the spring scale with the 1 kg weight and set the needle right when it drifted, and pick the
  bruised fruit out of each basket before it spoils the rest;
* ripeness by the day: every lot of fruit has an age. Mango, banana and avocado ripen (còn xanh
  → vừa chín → chín kỹ); orange, dragon fruit, grapes and pomelo stay fresh, then wilt. Stock that
  comes in today is green; tomorrow's customer wants it ripe. The last day of a lot is its last:
  it is thrown away at closing, unless it was sold off cheap (``tc_xa``, "rao xả hàng");
* choosing fruit: the customer says what for (eat tonight, keep for three days, blend a smoothie,
  the altar tray) and the player picks from the right ripeness basket;
* weighing: the fruit goes in a plastic basket on the scale. Zero the basket first ("trừ bì"),
  weigh to what was asked (a kilo, half a kilo, three fruits) and read the price off the scale;
* bargaining: some customers haggle. Hold the price, meet halfway, throw in a small orange, or
  give in; each customer takes one of these best (what they say hints which);
* cash with the shared till (game/careers/till.py), a customer who comes back with yesterday's
  fruit (``return``), the smoothie man who buys the over-ripe fruit (``bulk``), the altar tray on
  the 1st and 15th of the lunar month (``altar``), and small surprises at the market;
* the awkward people (0.9.16): customers who call your prices a rip-off and bargain (the player names
  a price and the customer decides), want it on credit, or walk off "to fetch the wallet"; a debt book
  to chase or write off; shoplifters and people filming the stall "bán đắt"; many more surprises.

Honesty is the heart of it: an unzeroed basket or a drifted scale charges the customer for fruit
they never got. Careful customers weigh again at the market's check scale; everyone else never
knows, and Dì Tư's evening note says what it cost them.
Mistakes go through consequences (cq.slip / cq.react); money only through the engine's money().
Everything random is rolled from the day, slot or task id.
"""
from __future__ import annotations

import copy
import hashlib

from ..jsoncopy import tree_copy
from . import kit
from . import till
from . import street_folk as folk
from .. import consequences as cq

ID = 'fruit'
GEN = 1

BASKET = 150              # grams of the plastic basket on the scale ("bì")
DRIFTS = (0, 0, 0, 40, -40, 60, 0, 30)   # how far the spring drifted overnight (grams); day 1 is fixed below
XA_OFF = 40               # over-ripe / wilting fruit sells at 40% off
SHORT = 90                # % of the asked weight: under this the customer says it is short
BAG_MAX = 16
STAGE_LABEL = {'xanh': 'Còn xanh', 'chin': 'Vừa chín', 'ky': 'Chín kỹ', 'tuoi': 'Tươi', 'heo': 'Hơi héo'}
CHEAP = ('ky', 'heo')

# id, name, emoji, unit, cost per unit, grams per unit, price per kg, stages by age (the last is the last day)
FRUITS = [
    dict(id='xoai', name='Xoài cát', emoji='🥭', unit='trái', cost=3, g=380, kg=14, stages=('xanh', 'xanh', 'chin', 'chin', 'ky'), start=10),
    dict(id='chuoi', name='Chuối già', emoji='🍌', unit='nải', cost=6, g=1300, kg=8, stages=('xanh', 'chin', 'chin', 'ky'), start=4),
    dict(id='bo', name='Bơ sáp', emoji='🥑', unit='trái', cost=3, g=320, kg=18, stages=('xanh', 'xanh', 'chin', 'chin', 'ky'), start=8),
    dict(id='cam', name='Cam sành', emoji='🍊', unit='trái', cost=2, g=260, kg=12, stages=('tuoi',) * 6 + ('heo', 'heo'), start=16),
    dict(id='thanh_long', name='Thanh long', emoji='🐉', unit='trái', cost=3, g=450, kg=10, stages=('tuoi',) * 5 + ('heo',), start=8),
    dict(id='nho', name='Nho xanh', emoji='🍇', unit='chùm', cost=10, g=500, kg=32, stages=('tuoi', 'tuoi', 'heo'), start=4),
    dict(id='buoi', name='Bưởi da xanh', emoji='🍈', unit='trái', cost=10, g=1300, kg=12, stages=('tuoi',) * 10 + ('heo', 'heo'), start=4),
]
FRUIT = {x['id']: x for x in FRUITS}
ITEMS = [dict(id=x['id'], name=x['name'], emoji=x['emoji'], group='fruit', unit=x['unit'], cost=x['cost'], life=len(x['stages']),
              start=x['start']) for x in FRUITS]
PRICES = {x['id']: x['kg'] for x in FRUITS}
# Dì Tư leaves yesterday's ripe fruit on the stall for the first morning: (item, qty, days left).
FIRST_MORNING = (('xoai', 5, 3), ('chuoi', 2, 2), ('bo', 4, 3), ('xoai', 2, 1))

PEOPLE = [
    ('Dì Tư', 'Chủ sạp trái cây', 'Bán trái cây đầu chợ hai mươi năm, sáng nào cũng đi chợ đầu mối từ bốn giờ.', 'warm'),
    ('Cô Năm', 'Nội trợ đi chợ sớm', 'Lựa từng trái, trả giá từng xu, nhưng mua đều như cơm bữa.', 'picky'),
    ('Chú Bảy', 'Hưu trí, lo việc cúng kiếng', 'Rằm, mùng một nào cũng tự tay chọn mâm ngũ quả.', 'bossy'),
    ('Chị Thảo', 'Nhân viên văn phòng', 'Ghé mua vội giờ nghỉ trưa, ít nói, ghét chờ lâu.', 'quiet'),
    ('Bà Hai', 'Cụ bà xóm chợ', 'Đi đâu cũng mang theo cái cân đồng hồ nhỏ, mua gì cũng cân lại.', 'sour'),
    ('Tuấn', 'Sinh viên mê tập gym', 'Mua chuối với bơ làm sinh tố, hay hỏi có gì rẻ.', 'genz'),
    ('Anh Lâm', 'Chủ quán sinh tố đầu hẻm', 'Chuyên mua trái chín kỹ giá rẻ về xay, mặc cả rất gắt.', 'bossy'),
    ('Bé Mơ', 'Học sinh lớp 6', 'Hay được mẹ sai đi mua trái cây, cầm tờ giấy ghi sẵn.', 'genz'),
]
KID_NPC = 7

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Chợ đông vừa phải, khách mua đều tay.', weight=3),
    dict(id='heat', emoji='🥵', label='Nắng gắt', hint='Trái mau dập, mau héo: lựa hàng kỹ, bán xả sớm.', min_day=2, weight=2),
    dict(id='rain', emoji='🌧️', label='Mưa dầm', hint='Căng bạt che trái, kẻo ướt dập cả rổ.', min_day=2, weight=2),
    dict(id='ram', emoji='🌕', label='Rằm, mùng một', hint='Người ta mua mâm ngũ quả cúng: trái phải chắc, đẹp, để được lâu.', min_day=3, weight=2),
    dict(id='weekend', emoji='🛍️', label='Cuối tuần', hint='Khách đông, hay mua nhiều và trả giá.', min_day=2, weight=2),
]
MOD = {m['id']: m for m in MODS}

# One line of an order: (item, 'kg' grams | 'n' count, amount, wanted stages)
def _line(i, how, amount, want):
    return dict(i=i, kg=amount if how == 'kg' else None, n=amount if how == 'n' else None, want=list(want))


# (npc, kind, title, opening, lines, haggle (offer %, the way that pleases) or None, check scale, note, min_day, mod)
ORDERS = [
    (3, 'buy', 'Chị Thảo mua cam', 'Cho chị một ký cam sành, lựa trái tươi giúp chị nha.', [_line('cam', 'kg', 1000, ('tuoi',))], None, False,
     'Chị Thảo cầm điện thoại, sắp tới giờ họp.', 1, None),
    (1, 'buy', 'Cô Năm mua xoài', 'Nửa ký xoài cát, chín ăn liền tối nay. Bớt cho cô chút nghe con!', [_line('xoai', 'kg', 500, ('chin',))],
     (80, 'meet'), False, 'Cô Năm bóp nhẹ từng trái, lắc đầu với trái còn cứng.', 1, None),
    (5, 'buy', 'Tuấn mua chuối', 'Cho em hai nải chuối chín, em ăn trước giờ tập.', [_line('chuoi', 'n', 2, ('chin',))], None, False,
     'Tuấn mặc áo ba lỗ, đeo tai nghe.', 1, None),
    (5, 'buy', 'Tuấn xay sinh tố', 'Ba trái bơ, chín kỹ cũng được, em về xay liền. Có rẻ hơn không?', [_line('bo', 'n', 3, ('chin', 'ky'))],
     (85, 'extra'), False, 'Tuấn đếm tiền lẻ trong ví.', 2, None),
    (4, 'buy', 'Bà Hai mua thanh long', 'Một ký thanh long. Bà có mang cân theo đấy nhé.', [_line('thanh_long', 'kg', 1000, ('tuoi',))], None, True,
     'Bà Hai đặt cái cân đồng hồ nhỏ lên sạp.', 1, None),
    (4, 'buy', 'Bà Hai mua nho', 'Nửa ký nho xanh, lựa chùm tươi. Bà cân lại đấy!', [_line('nho', 'kg', 500, ('tuoi',))], (90, 'hold'), True,
     'Bà Hai soi từng chùm, nhặt ra một quả dập.', 2, None),
    (3, 'buy', 'Chị Thảo mua cho cả phòng', 'Hai ký cam mang lên công ty, lựa trái tươi nha.', [_line('cam', 'kg', 2000, ('tuoi',))], None, False,
     'Cả phòng góp tiền mua trái cây ăn chiều.', 2, None),
    (3, 'buy', 'Chị Thảo mua xoài để dành', 'Một ký xoài còn xanh, ba hôm nữa chị mới ăn.', [_line('xoai', 'kg', 1000, ('xanh',))], None, False,
     'Chị Thảo sắp đi công tác ba ngày.', 2, None),
    (1, 'buy', 'Cô Năm mua bơ', 'Một ký bơ sáp, chín vừa ăn tối nay. Bán cô rẻ rẻ thôi!', [_line('bo', 'kg', 1000, ('chin',))], (80, 'extra'),
     False, 'Cô Năm vừa kể nhà có khách từ quê lên.', 2, None),
    (1, 'buy', 'Cô Năm mua nho', 'Nửa ký nho xanh, con bớt đi chứ đắt quá!', [_line('nho', 'kg', 500, ('tuoi',))], (85, 'meet'), False,
     'Cô Năm so giá với sạp bên kia đường.', 3, None),
    (2, 'buy', 'Chú Bảy chọn bưởi', 'Chú lấy một trái bưởi to, chắc tay, để thờ.', [_line('buoi', 'n', 1, ('tuoi',))], None, False,
     'Chú Bảy nâng từng trái lên ước lượng.', 2, None),
    (7, 'buy', 'Bé Mơ mua cho mẹ', 'Cô ơi, mẹ con bệnh, con mua ba trái cam với một nải chuối chín ạ.', [_line('cam', 'n', 3, ('tuoi',)),
     _line('chuoi', 'n', 1, ('chin',))], None, False, 'Bé Mơ cầm tờ giấy mẹ ghi, tay nắm chặt tiền.', 2, None),
    (4, 'buy', 'Bà Hai mua cam vắt', 'Một ký cam vắt nước. Cân cho đủ, bà cân lại đấy.', [_line('cam', 'kg', 1000, ('tuoi', 'heo'))], None, True,
     'Bà Hai bảo cam hơi héo vắt vẫn ngọt.', 3, None),
    (5, 'buy', 'Tuấn mua xoài', 'Nửa ký xoài chín, bớt em chút đỉnh nha!', [_line('xoai', 'kg', 500, ('chin', 'ky'))], (85, 'meet'), False,
     'Tuấn vừa tập xong, mồ hôi nhễ nhại.', 3, 'weekend'),
    (3, 'buy', 'Chị Thảo trú mưa', 'Mưa quá, chị mua đại một chùm nho rồi về.', [_line('nho', 'n', 1, ('tuoi',))], None, False,
     'Chị Thảo đứng nép dưới tấm bạt, tóc ướt lấm tấm.', 2, 'rain'),
    (1, 'buy', 'Cô Năm mua cuối tuần', 'Cuối tuần nhà đông, cô lấy một ký xoài chín với một ký cam. Tính rẻ nghe!',
     [_line('xoai', 'kg', 1000, ('chin',)), _line('cam', 'kg', 1000, ('tuoi',))], (85, 'extra'), False, 'Con cháu cô Năm về chơi cuối tuần.', 3, 'weekend'),
    (2, 'altar', 'Mâm ngũ quả của chú Bảy', 'Mai rằm, chú lấy mâm ngũ quả: một bưởi, một nải chuối xanh, ba cam, hai xoài xanh, một thanh long. '
     'Trái phải chắc, bày được mấy hôm.', [_line('buoi', 'n', 1, ('tuoi',)), _line('chuoi', 'n', 1, ('xanh',)), _line('cam', 'n', 3, ('tuoi',)),
     _line('xoai', 'n', 2, ('xanh',)), _line('thanh_long', 'n', 1, ('tuoi',))], None, False, 'Chú Bảy cúng rất kỹ, trái dập là chú trả lại.', 3, 'ram'),
    (1, 'altar', 'Cô Năm sắm mâm cúng', 'Cô lấy mâm cúng rằm: một bưởi, ba cam, hai xoài xanh, một nải chuối xanh. Tính cô giá mềm nha.',
     [_line('buoi', 'n', 1, ('tuoi',)), _line('cam', 'n', 3, ('tuoi',)), _line('xoai', 'n', 2, ('xanh',)), _line('chuoi', 'n', 1, ('xanh',))],
     (90, 'meet'), False, 'Cô Năm cúng xong còn mang trái biếu hàng xóm.', 3, 'ram'),
    (6, 'bulk', 'Anh Lâm gom trái chín', 'Có xoài, chuối hay bơ chín kỹ không? Anh gom hết về xay sinh tố, bán rẻ cho anh.', [], (75, 'meet'), False,
     'Anh Lâm chở cái sọt nhựa to sau xe.', 2, None),
]
KINDS = ('setup', 'buy', 'altar', 'bulk', 'return')
STAGES = ('prep', 'haggle', 'credit', 'pay', 'done')   # credit: a customer wants it on tab / walks off (0.9.16)
RETURNS = [
    dict(npc=1, item='xoai', fault='buyer', title='Cô Năm trả xoài', opening='Hôm qua con bán xoài gì mà bổ ra sượng ngắt, chua lè!',
         look='Trái còn cứng, vỏ xanh, cuống tươi: xoài còn xanh, để thêm hai hôm là chín ngọt.',
         note='Hôm qua cô mua xoài xanh để dành, nhưng nhà có khách nên bổ ăn luôn.'),
    dict(npc=4, item='cam', fault='shop', title='Bà Hai mang cam lại', opening='Cam hôm qua cháu bán, bóc ra hai trái thâm một góc. Cháu xem đi!',
         look='Hai trái mềm nhũn một bên, vỏ có vết dập: trái dập từ rổ hàng, không phải lỗi người mua.',
         note='Bà Hai mang theo cả túi cam, chỉ vào vết thâm.'),
    dict(npc=3, item='bo', fault='shop', title='Chị Thảo đổi bơ', opening='Em ơi, trái bơ chị mua hôm qua bổ ra đen xì bên trong.',
         look='Ruột bơ thâm đen, có mùi hắc: bơ chín quá lẽ ra phải bán xả, không bán như bơ vừa chín.',
         note='Chị Thảo giữ nguyên hóa đơn viết tay.'),
    dict(npc=5, item='chuoi', fault='buyer', title='Tuấn chê chuối', opening='Chuối anh bán hôm kia đen hết vỏ rồi, sao nhanh vậy?',
         look='Vỏ lốm đốm đen nhưng ruột còn chắc, thơm: chuối chín kỹ vì để nắng trong phòng, vẫn ăn tốt.',
         note='Tuấn để nải chuối ngay cửa sổ phòng trọ hướng tây.'),
]
DEALS = ('hold', 'meet', 'extra', 'give')

# Regulars' small stories: one line per finished visit, on and on across days.
REG_STORY = {
    1: ('Cô Năm: “Mua ở đây hai chục năm rồi, dì Tư chưa cân thiếu cô lạng nào.”',
        'Cô Năm dạy cách chọn xoài: “Cuống thơm, bóp nhẹ thấy mềm đều là ăn được.”',
        'Cô Năm khoe đứa cháu đầu lòng mới đầy tháng, dúi cho sạp gói xôi.',
        'Cô Năm bảo sạp giờ cân nhanh, tính gọn, không phải đứng chờ.'),
    2: ('Chú Bảy: “Mâm ngũ quả là tấm lòng, trái phải chắc, phải tươi.”',
        'Chú Bảy kể ngày xưa ông bà chú bày mâm “cầu, dừa, đủ, xoài, sung”.',
        'Chú Bảy mang cho sạp chậu vạn thọ nhỏ: “Để góc sạp cho có sắc.”'),
    3: ('Chị Thảo: “Mua nhanh giúp chị, sếp đang gọi.”', 'Chị Thảo được lên trưởng nhóm, mua trái cây đãi cả phòng.',
        'Chị Thảo bảo trái cây sạp mình ăn chiều cả phòng khen.'),
    4: ('Bà Hai đặt cân lên sạp: “Cân lại cho chắc, đừng giận bà.”', 'Bà Hai cân lại, gật gù: “Đủ. Cháu này thật thà.”',
        'Bà Hai bảo từ nay khỏi mang cân, tin sạp này rồi.'),
    5: ('Tuấn: “Chuối là chân ái của dân tập gym đó.”', 'Tuấn tăng được hai ký cơ, khoe ảnh chụp trước gương.',
        'Tuấn dẫn cả đội gym tới mua bơ.'),
    6: ('Anh Lâm: “Trái chín kỹ mà ngọt là anh lấy hết.”', 'Anh Lâm kể quán sinh tố mới có thêm bàn ngoài vỉa hè.',
        'Anh Lâm bảo nhờ sạp mà ly sinh tố bơ của anh đắt hàng hẳn.'),
    7: ('Bé Mơ: “Mẹ con dặn lựa trái tươi, không lấy trái dập ạ.”', 'Bé Mơ khoe mẹ đã khỏe, cảm ơn cô bán cam ngọt.',
        'Bé Mơ được học sinh giỏi, ghé khoe giấy khen.'),
}

INTRO = dict(
    title='Giới thiệu nghề: bán trái cây ở chợ',
    lead='Một sạp gỗ đầu chợ, mấy rổ tre, cây dù và cái cân đồng hồ. Sáng nào dì Tư cũng đi chợ đầu mối từ bốn giờ; bạn trông sạp giúp dì.',
    work=[('⛱️', 'Dọn sạp: dựng dù, trời mưa thì căng bạt'), ('⚖️', 'Thử cân với quả cân 1 ký, lệch thì chỉnh kim'),
          ('🧺', 'Lựa trái dập ra khỏi rổ trước khi mở hàng'), ('🥭', 'Chọn trái đúng độ chín: ăn liền, để dành hay xay sinh tố'),
          ('🧮', 'Trừ bì rổ, cân đúng, đọc giá theo ký'), ('🤝', 'Trả giá: giữ giá, bớt chút hay tặng thêm trái'),
          ('📣', 'Chiều tối rao xả trái chín kỹ, héo'), ('💵', 'Thu tiền, thối đúng từng xu')],
    meet=[('🧺', 'Cô Năm: lựa kỹ, trả giá từng xu'), ('🌕', 'Chú Bảy: mâm ngũ quả ngày rằm'), ('💼', 'Chị Thảo: mua vội giờ trưa'),
          ('⚖️', 'Bà Hai: mang cân riêng, cân lại'), ('🏋️', 'Tuấn: chuối, bơ làm sinh tố'), ('🥤', 'Anh Lâm: gom trái chín kỹ giá rẻ'),
          ('🌧️', 'Mưa dầm, nắng gắt, thu phí chợ, xe hàng dán nhãn giả')],
    stars=[('🥭', 'Trái đúng độ chín khách cần'), ('⚖️', 'Trừ bì, cân đúng, không cân lệch'), ('🧺', 'Không bán trái dập'),
           ('🤝', 'Trả giá vui vẻ, không cãi'), ('💵', 'Thối đúng tiền'), ('🙏', 'Hết hàng đúng ý thì nói thật')],
)

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='rain_gust', title='Mưa ập xuống', emoji='🌧️', npc=0, min_day=2, tone='tense', at='between', weight=3, mods=('rain', 'normal', 'heat'),
         text='Gió lật cả mép dù, mưa hắt thẳng vào mấy rổ trái. Nước đọng lại dưới đáy rổ cam.',
         options=[dict(id='tarp', label='Căng bạt, kê rổ lên cao', hint='Mất chút thời gian', effects=dict(patience=-4), good=True,
                       outcome='Tấm bạt xanh căng kín sạp. Rổ trái khô ráo, khách đứng nép dưới bạt chọn tiếp.'),
                  dict(id='cover', label='Lấy bao tải trùm tạm', hint='Nhanh, nhưng dễ ủ hơi', effects=dict(bruise=1), good=None,
                       outcome='Trùm được mấy rổ, nhưng rổ cam ủ hơi nóng, vài trái bắt đầu mềm.'),
                  dict(id='wait', label='Mưa bóng mây, chắc tạnh liền', hint='Không tốn gì… nếu tạnh', effects=dict(bruise=2),
                       good=False, outcome='Mưa không tạnh. Nước ngấm vào đáy rổ, mấy trái bị úng.')],
         default='wait'),
    dict(id='fee', title='Ban quản lý chợ thu phí', emoji='🧾', npc=0, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='Anh thu phí của ban quản lý chợ ghé: “Phí vệ sinh với chỗ ngồi hôm nay 4 xu nha. Có biên lai đàng hoàng.”',
         options=[dict(id='pay', label='Đóng 4 xu, lấy biên lai', hint='Đúng quy định', effects=dict(money=-4, xp=3), good=True,
                       outcome='Anh thu phí xé biên lai, còn dặn sáng mai có xe xịt rửa đường chợ.'),
                  dict(id='bribe', label='Dúi 8 xu “cho chỗ đẹp hơn”, khỏi biên lai', hint='Nghe cũng tiện…', effects=dict(money=-8),
                       good=False, outcome='Anh ta cầm tiền rồi đi. Chỗ ngồi chẳng đổi gì, lại mất thêm tiền không biên lai.'),
                  dict(id='argue', label='Cãi: “Sạp nhỏ xíu mà thu gì!”', hint='', effects=dict(money=-4, review=[3, 'Sạp cãi nhau với ban quản lý ngay đầu chợ, ồn ào.']),
                       good=False, outcome='Cãi một hồi vẫn phải đóng, khách đứng chờ mặt ngán ngẩm.')],
         default='pay'),
    dict(id='taster', title='Khách nếm cả chùm nho', emoji='🍇', npc=1, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một bà khách lạ bứt nho nếm hết quả này tới quả khác, ăn gần nửa chùm rồi bảo: “Chua, không mua.”',
         options=[dict(id='kind', label='Mời nếm một quả, nói khéo là trái bán theo ký', hint='', effects=dict(xp=3), good=True,
                       outcome='Bà khách ngượng, mua luôn nửa ký cam. Cô Năm đứng bên gật gù.'),
                  dict(id='shrug', label='Kệ, cho qua', hint='Mất nửa chùm nho', effects=dict(stock={'nho': -1}), good=None,
                       outcome='Bà khách đi mất. Chùm nho vặt trụi phải bỏ riêng.'),
                  dict(id='shout', label='Quát: “Ăn thì phải mua chứ!”', hint='', effects=dict(stock={'nho': -1}, review=[2, 'Sạp quát khách giữa chợ, sợ luôn.']),
                       good=False, outcome='Cả dãy chợ ngoái lại nhìn. Bà khách bỏ đi, còn nói to cho người khác nghe.')],
         default='shrug'),
    dict(id='fake_label', title='Xe hàng dán nhãn', emoji='🏷️', npc=6, min_day=3, tone='tense', at='open', weight=2, mods=None,
         text='Một xe tải nhỏ ghé: “Xoài nhập giá rẻ, có sẵn tem “xoài cát Hòa Lộc” dán vào là bán gấp đôi. Lấy không em?”',
         options=[dict(id='refuse', label='Không lấy: bán trái gì nói trái đó', hint='', effects=dict(xp=4), good=True,
                       outcome='Xe đi sang sạp khác. Dì Tư về nghe chuyện, gật đầu: “Giữ cái tiếng là giữ khách.”'),
                  dict(id='plain', label='Mua vài ký nhưng bán đúng tên, đúng giá', hint='Tốn 10 xu, được 3 trái xoài',
                       effects=dict(money=-10, stock={'xoai': 3}), good=None, outcome='Bán đúng tên, giá thấp. Không lời mấy nhưng yên tâm.'),
                  dict(id='relabel', label='Lấy tem dán, bán giá hàng xịn', hint='Lời to… nếu không ai biết',
                       effects=dict(money=-10, stock={'xoai': 3}, review=[1, 'Mua “xoài cát Hòa Lộc” mà bổ ra xơ, nhạt. Dán nhãn giả!']),
                       good=False, outcome='Chiều đó có khách quay lại, cầm trái xoài chỉ vào con tem bong ra.')],
         default='refuse'),
    dict(id='kid_spill', title='Rổ cam lăn ra đường', emoji='🍊', npc=7, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một cậu nhóc chạy vấp chân sạp, rổ cam đổ ào, mấy trái lăn ra giữa lối xe máy.',
         options=[dict(id='safe', label='Kéo bé vào trong trước, rồi mới nhặt cam', hint='', effects=dict(stock={'cam': -2}, xp=4), good=True,
                       outcome='Bé không sao. Hai trái cam bị xe cán bẹp, còn lại nhặt vào rổ. Mẹ bé cảm ơn rối rít.'),
                  dict(id='fine', label='Bắt mẹ bé đền tiền cam', hint='', effects=dict(money=4, review=[3, 'Trẻ con lỡ tay mà sạp bắt đền, kỳ ghê.']),
                       good=False, outcome='Mẹ bé đưa 4 xu, mặt hằm hằm. Người đứng xem xì xào.'),
                  dict(id='grab', label='Lao ra nhặt cam ngay', hint='', effects=dict(stock={'cam': -1}, patience=-5), good=None,
                       outcome='Suýt bị xe máy quẹt. Nhặt được gần hết, tim đập thình thịch.')],
         default='safe'),
    dict(id='neighbour', title='Bà bán rau nhờ trông hàng', emoji='🥬', npc=0, min_day=3, tone='gentle', at='between', weight=1, mods=None,
         text='Bà bán rau sạp bên: “Trông giùm bà mấy mớ rau nha, bà chạy về nấu cơm cho ông, nửa tiếng thôi.”',
         options=[dict(id='yes', label='Nhận trông, ghi giá rau ra giấy', hint='', effects=dict(xp=3, money=2), good=True,
                       outcome='Bán giùm được ba mớ rau. Bà về dúi cho 2 xu với bó hành.'),
                  dict(id='no', label='Khéo từ chối vì đang đông khách', hint='', effects={}, good=None,
                       outcome='Bà gật đầu, nhờ sạp khác.')],
         default='no'),
]

# The awkward people at the stall (0.9.16): more surprises, each with its own way out.
DESK += [
    dict(id='squeeze', title='Khách bóp nát cả rổ', emoji='🥭', npc=1, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Một bà khách bóp từng trái xoài chín, trái nào cũng lõm một vết ngón tay, rồi phán: “Mềm hết rồi, không mua.”',
         options=[dict(id='ask', label='Nhờ khéo: “Cô chọn bằng mắt giúp con, bóp là dập đó”', hint='', effects=dict(xp=3), good=True,
                       outcome='Bà khách khựng lại, mua hai trái cho đỡ ngại.'),
                  dict(id='bear', label='Kệ, lựa trái dập ra sau', hint='Mất vài trái', effects=dict(stock={'xoai': -2}), good=None,
                       outcome='Hai trái xoài thâm vết tay, chỉ còn bán xả.'),
                  dict(id='snap', label='“Bóp nát rồi thì mua đi chứ!”', hint='', effects=dict(review=[2, 'Chưa mua đã bị quát, sạp gì mà dữ.']), good=False,
                       outcome='Bà khách bỏ đi, vừa đi vừa chửi đổng cả dãy chợ nghe.')],
         default='bear'),
    dict(id='bite_swap', title='Cắn dở rồi đòi đổi', emoji='😬', npc=5, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Tuấn cầm trái xoài đã cắn một miếng quay lại: “Chua lè, đổi trái khác đi, không thì trả tiền.”',
         options=[dict(id='taste', label='Nếm thử miếng khác trong rổ cùng lô, nói rõ lô này ngọt', hint='', effects=dict(xp=3), good=True,
                       outcome='Tuấn nếm miếng bạn cắt: “Ờ ngọt thật, chắc tại em cắn chỗ gần vỏ.” Không đòi đổi nữa.'),
                  dict(id='swap', label='Đổi cho xong chuyện', hint='Mất một trái', effects=dict(stock={'xoai': -1}), good=None,
                       outcome='Tuấn cầm trái mới đi, còn nháy mắt: “Uy tín!”'),
                  dict(id='no', label='“Cắn rồi ai đổi, trò gì vậy?”', hint='', effects=dict(review=[2, 'Mua trái chua mà không cho đổi, bán hàng kiểu gì vậy trời.']), good=False,
                       outcome='Tuấn đăng story “né sạp này ra nha anh em”.')],
         default='swap'),
    dict(id='deliver', title='Đòi giao tận nhà miễn phí', emoji='🏢', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Chị Thảo gọi: “Giao giùm chị 2 ký cam lên tầng 7 chung cư, thang máy hỏng, free ship nha, khách quen mà.”',
         options=[dict(id='fee', label='Nhận giao, xin 3 xu tiền công leo lầu', hint='', effects=dict(money=3, patience=-3), good=True,
                       outcome='Chị Thảo chuyển 3 xu, còn khen “sòng phẳng, chị thích”.'),
                  dict(id='free', label='Giao free cho vui lòng', hint='Leo 7 tầng', effects=dict(patience=-6, xp=2), good=None,
                       outcome='Leo bảy tầng thở không ra hơi. Khách ở sạp chờ dài cổ.'),
                  dict(id='no', label='Từ chối vì đang trông sạp', hint='', effects={}, good=None, outcome='Chị Thảo “ừ thôi” rồi đặt app.')],
         default='no'),
    dict(id='reweigh', title='Đòi cân lại ba lần', emoji='⚖️', npc=4, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Bà Hai đặt túi lên cân sạp, lên cân mình, rồi lên cân sạp bên cạnh: “Sao ba cái cân ra ba số? Cân nhà cháu có vấn đề!”',
         options=[dict(id='weight', label='Đặt quả cân 1 ký lên cân của sạp cho bà xem', hint='', effects=dict(xp=4), good=True,
                       outcome='Kim chỉ đúng một ký. Bà Hai gật gù: “Ừ, cân bà lệch rồi.”'),
                  dict(id='extra', label='Bù thêm trái cho bà khỏi thắc mắc', hint='Mất một trái cam', effects=dict(stock={'cam': -1}), good=None,
                       outcome='Bà Hai cầm thêm trái cam, vẫn lẩm bẩm “cân gì mà lạ”.'),
                  dict(id='snap', label='“Bà muốn cân mấy lần nữa?”', hint='', effects=dict(review=[2, 'Hỏi cân lại mà bị gắt, chắc là cân điêu thật.']), good=False,
                       outcome='Bà Hai kể khắp xóm là sạp “có tật giật mình”.')],
         default='extra'),
    dict(id='online_price', title='Khách giơ giá trên mạng', emoji='📲', npc=5, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Tuấn giơ điện thoại: “Trên sàn có 8 xu/ký, free ship. Sạp bán 14 là chặt chém vl. Bán 8 đi em lấy 3 ký.”',
         options=[dict(id='explain', label='Cho nếm, chỉ trái tươi, nói rõ giá chợ', hint='', effects=dict(xp=3), good=True,
                       outcome='Tuấn nếm xong: “Ờ, hàng mạng toàn trái xanh ủ.” Mua một ký giá chợ.'),
                  dict(id='cut', label='Bán 10 xu/ký cho được mối', hint='Lời mỏng', effects=dict(money=4), good=None,
                       outcome='Bán được ba ký, gần như hòa vốn. Tuấn khoe cả phòng gym “deal xịn”.'),
                  dict(id='mock', label='“Thế lên mạng mà mua”', hint='', effects=dict(review=[2, 'Hỏi giá tí mà chủ sạp cà khịa, bye.']), good=False,
                       outcome='Tuấn đi thẳng, còn quay clip “review sạp thái độ”.')],
         default='explain'),
    dict(id='fish_spot', title='Hàng cá chiếm chỗ bày sạp', emoji='🐟', npc=0, min_day=2, tone='tense', at='open', weight=2, mods=None,
         text='Sáng ra thấy bà bán cá kê thau cá lấn nửa chỗ sạp, nước tanh chảy tràn qua rổ cam: “Chỗ chung mà, ai tới trước thì bày.”',
         options=[dict(id='board', label='Mời ban quản lý chợ xem sơ đồ chỗ ngồi', hint='', effects=dict(xp=4, patience=-2), good=True,
                       outcome='Ban quản lý chỉ vạch sơn. Bà bán cá lầm bầm dời thau đi.'),
                  dict(id='move', label='Kê rổ lên cao, nhường cho yên', hint='Chật chội cả buổi', effects=dict(patience=-4), good=None,
                       outcome='Sạp chật như nêm, khách phải đứng nghiêng người lựa trái.'),
                  dict(id='fight', label='Hất thau cá ra', hint='', effects=dict(money=-6, review=[1, 'Hai sạp đánh nhau vì chỗ ngồi, xấu hổ cả chợ.']), good=False,
                       outcome='Cá nhảy tung tóe, hai bên cãi nhau ầm ĩ, bạn phải đền 6 xu con cá dập.')],
         default='move'),
    dict(id='beggar_kid', title='Em bé xin trái', emoji='🧒', npc=7, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một em bé lem luốc đứng nhìn rổ chuối mãi, rồi lí nhí: “Cô cho con xin một trái, con đói…”',
         options=[dict(id='give', label='Cho em nải chuối chín kỹ, dặn đi học', hint='', effects=dict(stock={'chuoi': -1}, xp=4), good=True,
                       outcome='Em bé ôm nải chuối chạy đi. Dì Tư nghe kể, gật đầu: “Làm vậy là đúng.”'),
                  dict(id='one', label='Cho một trái cam', hint='', effects=dict(stock={'cam': -1}, xp=2), good=True,
                       outcome='Em bé cảm ơn rối rít rồi chạy ra đầu chợ.'),
                  dict(id='shoo', label='Xua đi cho khỏi phiền khách', hint='', effects={}, good=False,
                       outcome='Em bé cúi đầu đi. Cô Năm đứng bên thở dài.')],
         default='one'),
    dict(id='drunk_credit', title='Ông say đòi mua chịu', emoji='🍺', npc=2, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Một ông say khướt bốc nguyên nải chuối: “Ghi nợ, mai trả! Không tin tao à? Tao ở đầu ngõ, ai chả biết!”',
         options=[dict(id='calm', label='Mềm mỏng lấy lại nải chuối, nhờ bảo vệ đưa ông về', hint='', effects=dict(xp=4, patience=-3), good=True,
                       outcome='Bảo vệ dìu ông đi. Nải chuối nguyên vẹn về rổ.'),
                  dict(id='give', label='Cho ông cầm đi cho yên', hint='Mất nải chuối', effects=dict(stock={'chuoi': -1}), good=None,
                       outcome='Ông đi lảo đảo, được hai bước đánh rơi nải chuối xuống cống.'),
                  dict(id='shout', label='Quát đuổi', hint='', effects={}, luck=dict(p=0.5,
                       win=dict(effects={}, good=None, outcome='Ông chửi đổng rồi bỏ đi.'),
                       lose=dict(effects=dict(stock={'cam': -3}), good=False, outcome='Ông nổi điên đạp đổ rổ cam, lăn khắp lối.')))],
         default='give'),
    dict(id='pick30', title='Lựa nửa tiếng mua một trái', emoji='⏳', npc=1, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Cô Năm lựa từng trái thanh long, lật lên lật xuống nửa tiếng, khách sau xếp hàng dài: “Từ từ, lựa cho kỹ chứ!”',
         options=[dict(id='help', label='Lựa giúp cô trái đẹp nhất, mời khách sau vào', hint='', effects=dict(xp=3), good=True,
                       outcome='Cô Năm ưng trái bạn chọn. Hàng khách chạy lại bình thường.'),
                  dict(id='wait', label='Đứng đợi', hint='Khách sau sốt ruột', effects=dict(patience=-6), good=None,
                       outcome='Cô Năm mua đúng một trái. Hai khách sau bỏ đi.'),
                  dict(id='hurry', label='“Cô ơi, nhanh giùm, người ta chờ!”', hint='', effects=dict(review=[3, 'Mua có trái thanh long mà bị hối như chạy giặc.']), good=False,
                       outcome='Cô Năm phật ý, lần sau sang sạp khác.')],
         default='wait'),
    dict(id='bags', title='Đòi thêm năm cái túi', emoji='🛍️', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Chị Thảo mua đúng một ký cam: “Cho chị thêm năm cái túi ni-lông, túi to nha, để đựng đồ ở văn phòng.”',
         options=[dict(id='one', label='Đưa một túi, mời chị dùng túi vải lần sau', hint='', effects=dict(xp=2), good=True,
                       outcome='Chị Thảo cười: “Ờ, túi vải cũng xinh.”'),
                  dict(id='five', label='Đưa luôn năm cái', hint='Tốn túi', effects=dict(money=-1), good=None, outcome='Chị Thảo ôm xấp túi đi, không mua thêm gì.'),
                  dict(id='no', label='“Túi cũng tiền đó chị”', hint='', effects=dict(review=[3, 'Xin cái túi mà cũng kể lể, keo ghê.']), good=False,
                       outcome='Chị Thảo bĩu môi.')],
         default='one'),
    dict(id='change_big', title='Tờ 500 mua một trái cam', emoji='💴', npc=5, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Tuấn đưa tờ 500 xu mua đúng một trái cam 3 xu: “Thối đi, em không có tiền lẻ.” Túi tiền lẻ gần cạn.',
         options=[dict(id='change', label='Chạy đổi tiền ở sạp bên, thối đủ', hint='Mất thời gian', effects=dict(patience=-4, xp=2), good=True,
                       outcome='Đổi được tiền lẻ, thối đủ 497 xu. Tuấn gật gù.'),
                  dict(id='later', label='Cho cầm trái cam, mai trả 3 xu', hint='', effects={}, luck=dict(p=0.6,
                       win=dict(effects=dict(money=3), good=True, outcome='Hôm sau Tuấn ghé trả 3 xu, còn mua thêm nải chuối.'),
                       lose=dict(effects=dict(stock={'cam': -1}), good=None, outcome='Tuấn quên mất tiêu. Coi như cho trái cam.'))),
                  dict(id='no', label='“Không có lẻ thì thôi”', hint='', effects={}, good=None, outcome='Tuấn nhún vai đi mất.')],
         default='later'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='TC-S01', title='Cân lệch mấy lạng', npc=4, tone='tense', min_day=1,
         opening='Bà Hai đặt túi thanh long lên cân riêng: “Cháu bảo một ký, cân bà chỉ có chín lạng. Cân cháu làm sao thế?”',
         swap='Bạn là bà Hai, mua gì cũng cân lại vì từng bị cân thiếu nhiều lần.',
         facts=[dict(id='weight', title='Quả cân 1 ký', source='Sạp', text='Đặt quả cân 1 ký lên, kim cân của sạp chỉ 1,1 ký: lò xo lệch 100 gam.'),
                dict(id='basket', title='Cái rổ trên cân', source='Nhìn lại', text='Lúc cân, rổ nhựa vẫn nằm trên cân mà chưa trừ bì.'),
                dict(id='habit', title='Lời dì Tư', source='Dì Tư', text='Dì Tư dặn: sáng nào cũng thử cân, khách thiệt một lạng là mất khách cả đời.')],
         options=[dict(id='fix', label='Xin lỗi, bù đủ cân, chỉnh lại kim ngay trước mặt bà', requires=['weight', 'basket'], quality='good', stars=5,
                       review='Cân lệch thật, nhưng sạp nhận lỗi, bù đủ và chỉnh cân ngay. Thật thà.',
                       outcome='Bà Hai gật gù, còn mua thêm nửa ký cam.',
                       perspectives=[dict(who='Bà Hai', emoji='⚖️', text='Sai mà nhận thì còn quay lại được.'),
                                     dict(who='Dì Tư', emoji='👩‍🌾', text='Chỉnh cân mất một phút, giữ khách cả đời.')]),
                  dict(id='bonus', label='Tặng thêm một trái cho bà vui', requires=['weight'], quality='ok', stars=4,
                       review='Có bù, nhưng cân vẫn để lệch thế thì khách khác thiệt.',
                       outcome='Bà Hai nhận trái thanh long, nhưng lúc đi vẫn dặn: “Chỉnh cái cân đi.”',
                       perspectives=[dict(who='Bà Hai', emoji='🤨', text='Bù cho tôi, còn người sau thì sao?'),
                                     dict(who='Cô Năm', emoji='🧺', text='Cân lệch thì cả chợ thiệt, không riêng bà Hai.')]),
                  dict(id='deny', label='Cãi: “Cân bà sai chứ cân cháu chuẩn!”', quality='bad', stars=1,
                       review='Cân thiếu còn cãi. Cả xóm chợ biết rồi đấy.',
                       outcome='Bà Hai mang cân ra ban quản lý chợ. Cân đối chứng chỉ ra sạp cân thiếu.',
                       perspectives=[dict(who='Ban quản lý chợ', emoji='🧾', text='Cân đối chứng không nói dối.'),
                                     dict(who='Cô Năm', emoji='🧺', text='Từ nay tôi cũng mang cân theo.')])],
         lesson='Sáng nào cũng thử cân, cân trong rổ thì trừ bì; khách phát hiện thiếu thì nhận lỗi và bù đủ.'),
    dict(id='TC-S02', title='Thuốc ủ chín cấp tốc', npc=6, tone='tense', min_day=2,
         opening='Một người chào bán gói bột: “Rắc vào rổ xoài xanh, ủ một đêm là vàng ươm, bán giá xoài chín. Ai cũng xài.”',
         facts=[dict(id='label', title='Gói bột', source='Nhìn kỹ', text='Gói bột không nhãn mác, không ghi thành phần, mùi hắc như khí đá.'),
                dict(id='kids', title='Người mua', source='Sạp', text='Khách quen có Bé Mơ mua cho mẹ đang ốm, có Tuấn xay sinh tố ăn liền.'),
                dict(id='time', title='Chín tự nhiên', source='Dì Tư', text='Xoài để hai, ba hôm trong rổ thoáng là chín, thơm tự nhiên.')],
         options=[dict(id='refuse', label='Từ chối, để trái chín tự nhiên', requires=['label'], quality='good', stars=5,
                       review='Sạp nói thẳng xoài nào chín tự nhiên, xoài nào còn xanh. Mua yên tâm.',
                       outcome='Bán chậm hơn một hôm, nhưng khách quen hỏi là nói thật được.',
                       perspectives=[dict(who='Bé Mơ', emoji='🎒', text='Mẹ con ăn trái cây ở đây thấy yên tâm.'),
                                     dict(who='Dì Tư', emoji='👩‍🌾', text='Trái chín ép thì vỏ vàng mà ruột sượng.')]),
                  dict(id='ask', label='Hỏi giấy tờ, nguồn gốc rồi mới tính', requires=['label', 'time'], quality='ok', stars=4,
                       outcome='Người bán lảng đi, không có giấy tờ gì. Bạn không mua.',
                       review='Sạp cẩn thận, hỏi nguồn gốc rõ ràng.',
                       perspectives=[dict(who='Người chào hàng', emoji='🕶️', text='Hỏi nhiều quá, đi sạp khác.'),
                                     dict(who='Cô Năm', emoji='🧺', text='Không rõ nguồn gốc thì đừng đụng tới.')]),
                  dict(id='use', label='Mua thử một gói cho kịp hàng chín', quality='bad', cost=6, stars=1,
                       review='Xoài vàng ươm mà ăn sượng, hăng mùi lạ. Không dám mua nữa.',
                       outcome='Chiều hôm sau có khách đau bụng quay lại hỏi.',
                       perspectives=[dict(who='Tuấn', emoji='🏋️', text='Ăn xong thấy cồn cào, sợ luôn.'),
                                     dict(who='Dì Tư', emoji='👩‍🌾', text='Hai mươi năm bán hàng, dì chưa từng dùng thứ đó.')])],
         lesson='Trái cây để chín tự nhiên; thứ bột không nhãn mác, không nguồn gốc thì không dùng cho đồ ăn.'),
    dict(id='TC-S03', title='Bán trái dập cho quán sinh tố', npc=6, tone='gentle', min_day=2,
         opening='Anh Lâm lục rổ trái dập: “Mấy trái này bán anh rẻ đi, anh xay liền.” Có vài trái đã chớm hư.',
         facts=[dict(id='bruise', title='Trái dập', source='Rổ riêng', text='Năm trái dập còn tốt, ba trái đã có đốm mốc trắng.'),
                dict(id='use', title='Anh Lâm dùng làm gì', source='Anh Lâm', text='Anh xay sinh tố bán cho học sinh tan trường.'),
                dict(id='rule', title='Lời dì Tư', source='Dì Tư', text='Trái dập bán rẻ được, trái mốc thì bỏ, không bán cho ai.')],
         options=[dict(id='honest', label='Bán rẻ trái dập còn tốt, bỏ riêng trái mốc', requires=['bruise', 'rule'], quality='good', stars=5, reward=6,
                       review='Sạp bán trái chín kỹ rẻ mà nói rõ trái nào dùng được. Làm ăn đàng hoàng.',
                       outcome='Anh Lâm lấy năm trái, trả 6 xu. Ba trái mốc bạn bỏ vào thùng rác hữu cơ.',
                       perspectives=[dict(who='Anh Lâm', emoji='🥤', text='Nói thật vậy anh mới dám mua dài dài.'),
                                     dict(who='Học sinh', emoji='🎒', text='Sinh tố ngon, không có mùi lạ.')]),
                  dict(id='all', label='Bán luôn cả rổ cho nhanh', quality='bad', reward=9, stars=2,
                       review='Trong rổ trái rẻ có trái mốc, xay ra có mùi. Mất khách!',
                       outcome='Tối đó anh Lâm gọi điện trách, đổ bỏ cả mẻ sinh tố.',
                       perspectives=[dict(who='Anh Lâm', emoji='😠', text='Trái mốc thì nói anh một tiếng chứ.'),
                                     dict(who='Dì Tư', emoji='👩‍🌾', text='Được mấy xu mà mất mối quen.')]),
                  dict(id='none', label='Không bán gì, bỏ hết cho chắc', requires=['bruise'], quality='ok',
                       outcome='Bỏ cả trái còn dùng được. Anh Lâm tiếc, mua chỗ khác.',
                       perspectives=[dict(who='Anh Lâm', emoji='🤷', text='Trái chín kỹ còn ngon mà bỏ uổng.'),
                                     dict(who='Cô Năm', emoji='🧺', text='Cẩn thận quá hóa phí.')])],
         lesson='Trái chín kỹ, dập nhẹ bán rẻ và nói rõ; trái mốc thì bỏ, không bán cho ai.'),
    dict(id='TC-S04', title='Khách nếm rồi không mua', npc=1, tone='gentle', min_day=2,
         opening='Buổi sáng đông khách, ba người liền xin nếm nho, nếm xoài rồi đi, không mua gì.',
         facts=[dict(id='loss', title='Hao hụt', source='Rổ nho', text='Sáng nay mất gần một chùm nho chỉ vì nếm thử.'),
                dict(id='plate', title='Đĩa nếm', source='Dì Tư', text='Dì Tư hay cắt sẵn vài miếng vào đĩa nhỏ, ai muốn nếm thì lấy ở đó.'),
                dict(id='regular', title='Khách quen', source='Cô Năm', text='Cô Năm bảo: “Cho nếm một miếng mới biết ngọt mà mua.”')],
         options=[dict(id='plate', label='Cắt sẵn đĩa nếm nhỏ, mời khách lấy', requires=['plate', 'loss'], quality='good', stars=5,
                       review='Có đĩa nếm sẵn, thử rồi mua, không ngại.', outcome='Hao hụt ít hẳn, khách nếm xong mua nhiều hơn.',
                       perspectives=[dict(who='Cô Năm', emoji='🧺', text='Nếm một miếng biết ngọt là mua liền.'),
                                     dict(who='Dì Tư', emoji='👩‍🌾', text='Mất một trái mà được mười khách.')]),
                  dict(id='sign', label='Treo biển “Không nếm thử”', quality='ok', stars=3, review='Không cho nếm thì sao biết ngọt hay chua.',
                       outcome='Đỡ hao, nhưng vài khách bỏ sang sạp bên.',
                       perspectives=[dict(who='Khách lạ', emoji='🤨', text='Sạp này khó tính quá.'),
                                     dict(who='Dì Tư', emoji='👩‍🌾', text='Cũng được, nhưng cứng quá thì mất khách.')]),
                  dict(id='glare', label='Lườm khách nào đụng vào trái', quality='bad', stars=2,
                       review='Chưa mua mà bị lườm, thôi đi chỗ khác.', outcome='Sáng đó sạp vắng hẳn.',
                       perspectives=[dict(who='Khách', emoji='😒', text='Mua bán mà mặt nặng mày nhẹ.'),
                                     dict(who='Cô Năm', emoji='🧺', text='Buôn bán phải vui vẻ chứ con.')])],
         lesson='Cho nếm có chừng mực: một đĩa nếm nhỏ giữ được khách mà không hao hàng.'),
    dict(id='TC-S05', title='Mâm ngũ quả hết trái đẹp', npc=2, tone='gentle', min_day=3,
         opening='Chú Bảy muốn bày mâm ngũ quả nhưng sạp chỉ còn xoài chín kỹ và thanh long hơi héo.',
         facts=[dict(id='stock', title='Hàng còn lại', source='Rổ', text='Xoài chín kỹ để mai là nhũn; thanh long cuống đã héo.'),
                dict(id='days', title='Mâm bày mấy ngày', source='Chú Bảy', text='Chú bày từ chiều nay tới hết ngày rằm, gần ba ngày.'),
                dict(id='order', title='Hàng về', source='Dì Tư', text='Sáng mai dì Tư lấy hàng mới ở chợ đầu mối.')],
         options=[dict(id='truth', label='Nói thật, hẹn chú sáng mai lấy trái mới', requires=['stock', 'order'], quality='good', stars=5,
                       review='Hết trái đẹp thì nói thật, hẹn sáng mai có hàng mới. Tin được.',
                       outcome='Sáng hôm sau chú Bảy ghé sớm, chọn được mâm trái thật đẹp.',
                       perspectives=[dict(who='Chú Bảy', emoji='🌕', text='Cúng là tấm lòng, trái héo thì ngại lắm.'),
                                     dict(who='Dì Tư', emoji='👩‍🌾', text='Mất một mối hôm nay còn hơn mất khách mãi.')]),
                  dict(id='mix', label='Gợi ý đổi loại trái khác còn tươi', requires=['days'], quality='ok', stars=4,
                       review='Không đủ loại mình muốn, nhưng được tư vấn trái khác bày lâu được.',
                       outcome='Chú Bảy lấy bưởi, cam thay cho xoài.',
                       perspectives=[dict(who='Chú Bảy', emoji='🙂', text='Cũng được, miễn tươi.'),
                                     dict(who='Cô Năm', emoji='🧺', text='Bưởi, cam bày cả tuần vẫn đẹp.')]),
                  dict(id='sell', label='Bán luôn, bảo “trái còn tốt mà chú”', quality='bad', stars=1,
                       review='Mâm ngũ quả mới bày một hôm đã nhũn, ruồi bu. Buồn lắm.',
                       outcome='Hôm sau chú Bảy mang mâm trái nhũn trả lại.',
                       perspectives=[dict(who='Chú Bảy', emoji='😞', text='Đồ cúng mà bán vậy thì hết tin.'),
                                     dict(who='Dì Tư', emoji='👩‍🌾', text='Nói thật thì khách còn quay lại.')])],
         lesson='Trái để bày lâu phải chắc và tươi; không có thì nói thật và hẹn hàng mới.'),
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


def _price_kg(c: dict, item: str) -> int:
    return max(1, int(kit.price(c, item, PRICES[item])))


def kg_text(g: int) -> str:
    """1000 → '1 ký', 500 → '5 lạng', 1250 → '1,25 ký'."""
    g = int(g)
    if g < 1000 and g % 100 == 0:
        return f'{g // 100} lạng'
    s = f'{g / 1000:.2f}'.rstrip('0').rstrip('.').replace('.', ',')
    return f'{s} ký'


def _line_text(x: dict) -> str:
    f = FRUIT[x['i']]
    want = ' hoặc '.join(_lower(STAGE_LABEL[s]) for s in x['want'])
    amount = kg_text(x['kg']) if x['kg'] else f'{x["n"]} {f["unit"]}'
    return f'{amount} {_lower(f["name"])} ({want})'


# ---------------------------------------------------------------- ripeness of the stock
def stage_of(item: str, lot: dict, day: int) -> str:
    stages = FRUIT[item]['stages']
    left = lot['expires'] - day + 1
    return stages[max(0, min(len(stages) - 1, len(stages) - left))]


def baskets(c: dict) -> dict:
    """{item: {stage: qty}} of what is on the stall today."""
    out = {x['id']: {} for x in FRUITS}
    for lot in c['ext']['inv']['lots']:
        if lot['item'] in FRUIT and lot['qty'] > 0 and lot['expires'] >= c['day']:
            st = stage_of(lot['item'], lot, c['day'])
            out[lot['item']][st] = out[lot['item']].get(st, 0) + lot['qty']
    return out


def _take_stage(c: dict, item: str, stage: str) -> dict | None:
    """One fruit of that ripeness, from the lot that goes off first. Returns (expires, unit cost) or None."""
    x = c['ext']['inv']
    lots = sorted((l for l in x['lots'] if l['item'] == item and l['qty'] > 0 and l['expires'] >= c['day']
                   and stage_of(item, l, c['day']) == stage), key=lambda l: (l['expires'], l['received']))
    if not lots:
        return None
    lot = lots[0]
    lot['qty'] -= 1
    x['lots'] = [l for l in x['lots'] if l['qty'] > 0]
    return dict(e=lot['expires'], c=lot['unit_cost'])


def _put_back(c: dict, item: str, expires: int, cost: int) -> None:
    lot = next((l for l in c['ext']['inv']['lots'] if l['item'] == item and l['expires'] == expires and l['unit_cost'] == cost), None)
    if lot:
        lot['qty'] += 1
    elif expires >= c['day']:
        kit.add_lot(c, item, 1, cost, expires - c['day'] + 1, 'return')


# ================================================================ tasks
def _kind(day: int, slot: int, mod: str) -> str:
    if slot == 0:
        return 'setup'
    if day == 1:
        return 'buy'
    if mod == 'ram' and slot == 1:
        return 'altar'
    if slot == 2 and day % 3 == 0:
        return 'return'
    deck = ['buy', 'buy', 'buy', 'bulk', 'buy', 'buy'] if day >= 2 else ['buy']
    kit.rng(ID, 'deck', day).shuffle(deck)
    return deck[(slot - 1) % len(deck)]


def _pick(day: int, slot: int, kind: str, mod: str) -> tuple:
    if day == 1:
        return ORDERS[0] if slot == 1 else ORDERS[1] if slot == 2 else ORDERS[2]
    pool = [o for o in ORDERS if o[1] == kind and o[8] <= day and o[9] in (None, mod)]
    if not pool:
        pool = [o for o in ORDERS if o[1] == 'buy' and o[9] is None and o[8] <= day]
    weighted = [o for o in pool for _ in range(3 if o[9] else 1)]
    return weighted[kit.rng(ID, day, slot).randrange(len(weighted))]


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    kind = _kind(day, slot, mod)
    common = dict(gen=GEN, stage='prep', bag=[], seq=0, tare=False, weighed=None, price=None, offer=None, deal=None,
                  cash=None, cost=0, look=False, choice=None, story=None, extra=None)
    if kind == 'setup':
        rain = mod == 'rain'
        needs = dict(setup=True, cover='bat' if rain else 'du', note='Trời mưa: căng bạt che kín các rổ.' if rain else
                     'Nắng gắt: dựng dù, để rổ trong bóng râm.' if mod == 'heat' else 'Dựng dù, thử cân, lựa trái dập rồi mở hàng.')
        return kit.base_task(ID, day, slot, serial, 0, 'Dọn sạp ngày mưa' if rain else 'Dọn sạp đầu ngày',
                             'Dì Tư nhắn: “Dì đi lấy hàng rồi. Con dựng dù, thử cân, lựa trái dập ra rồi hẵng bán nghe.”',
                             kind='setup', needs=needs, **common)
    if kind == 'return':
        r = RETURNS[kit.rng(ID, 'ret', day, slot).randrange(len(RETURNS))]
        needs = dict(ret=r['item'], note=r['note'])
        return kit.base_task(ID, day, slot, serial, r['npc'], r['title'], r['opening'], kind='return', needs=needs,
                             _fault=r['fault'], _look=r['look'], **common)
    npc, k, title, opening, lines, haggle, check, note, _, _ = _pick(day, slot, kind, mod)
    needs = dict(lines=copy.deepcopy(lines), check=check, note=note)
    if k == 'bulk':
        needs.update(bulk=['xoai', 'chuoi', 'bo'], min=2, max=8)
    extra = {}
    if haggle:
        extra['_haggle'] = dict(pct=haggle[0], wants=haggle[1])
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind=k, needs=needs, **extra, **common)


FIXED = ('needs', '_haggle', '_fault', '_look')


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'
    tw = twist_of(t)
    if tw:
        # Customers made before 0.9.16 have no twist; a new one carries it from the start (and it must match twist_of).
        t['twist'], t['tw'] = tw, dict(state='wait', choice=None)


# ================================================================ the stall's data
def _fresh_stall(day: int) -> dict:
    return dict(day=day, cover=None, open=False, tested=False, xa=False)


def _fresh_today(day: int) -> dict:
    return dict(day=day, sold_g=0, customers=0, xa_sold=0, xa_money=0, over_g=0, over_xu=0, sorted=0, rotted=0, bargains=0)


def initial() -> dict:
    return dict(v=1, intro=False, seeded=False, stall=_fresh_stall(0), scale=dict(off=0, day=0), bruise={}, regulars={},
                today=_fresh_today(0), stats=dict(sold_g=0, customers=0, over_xu=0, xa_sold=0, rotted=0, returns=0, fair=0,
                                                  stolen=0, dashed=0, caught=0), desk=kit.desk_initial(), debts=[], trouble=folk.trouble_initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'stall'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    for k, v in folk.trouble_initial().items():
        d['trouble'].setdefault(k, copy.deepcopy(v))
    return d


def drift_of(day: int) -> int:
    if day == 1:
        return 40          # the first morning teaches the scale test
    return DRIFTS[kit.rng(ID, 'drift', day).randrange(len(DRIFTS))]


# ================================================================ the actions
FREE = ('tc_intro', 'tc_chase')
# Picking a fruit is a moment; the weighing is the customer's turn at the stall.
NO_TICK = ('tc_intro', 'tc_short', 'tc_cover', 'tc_scale_test', 'tc_pick', 'tc_tare', 'tc_unpick', 'tc_deal', 'tc_pay', 'tc_look', 'tc_desk',
           'tc_decline', 'tc_offer', 'tc_credit', 'tc_chase', 'tc_trouble')
PHYSICAL = ('tc_pick', 'tc_sort', 'tc_weigh', 'tc_xa', 'tc_scale_fix')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'tc_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Mấy rổ trái đang chờ ở sạp.')
    desk = d['desk']
    if name == 'tc_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'), hook=_desk_hook)
    if name in ('tc_chase', 'tc_trouble'):
        return ACTIONS[name](s, c, d, p)
    kit.desk_block(desk, 'Có chuyện ở sạp, quyết xong rồi bán tiếp nhé.')
    kit.need(d['trouble']['ev'] is None, 'Có chuyện ở sạp: xử lý trước đã.', 'surprise_open')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở sạp trái cây.')
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
    elif _trouble_tick(s, c, d):
        result['message'] = f'{result.get("message", "")} 🔔 Có chuyện ở sạp!'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc sạp trái cây.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    return t


def _need_open(d: dict) -> None:
    kit.need(d['stall']['open'], 'Chưa mở hàng: dựng dù, thử cân, lựa trái dập rồi bấm “Mở hàng” nhé.')


# ---------------------------------------------------------------- setting up
def _cover(s, c, d, p):
    cover = kit.one_of(p.get('cover'), ('du', 'bat'), 'Dựng dù hay căng bạt?')
    d['stall']['cover'] = cover
    return dict(message='⛱️ Đã dựng dù che nắng.' if cover == 'du' else '🟦 Đã căng bạt kín, kê rổ lên cao cho khỏi ướt.')


def _scale_test(s, c, d, p):
    sc = d['scale']
    d['stall']['tested'] = True
    shown = 1000 + sc['off']
    if not sc['off']:
        return dict(message='⚖️ Đặt quả cân 1 ký: kim chỉ đúng 1 ký. Cân chuẩn.')
    return dict(message=f'⚖️ Đặt quả cân 1 ký: kim chỉ {kg_text(shown)}. Cân lệch {abs(sc["off"])} gam, chỉnh kim lại đã.')


def _scale_fix(s, c, d, p):
    sc = d['scale']
    kit.need(d['stall']['tested'], 'Thử cân với quả cân 1 ký trước đã.')
    kit.need(sc['off'], 'Cân đang chuẩn rồi.')
    sc['off'] = 0
    return dict(message='🔧 Vặn con ốc dưới mặt cân, kim về đúng 1 ký. Cân chuẩn rồi.')


def _sort(s, c, d, p):
    item = kit.one_of(p.get('item'), FRUIT, 'Rổ trái này không có.')
    n = d['bruise'].get(item, 0)
    kit.need(n > 0, f'Rổ {_lower(FRUIT[item]["name"])} không có trái dập.')
    got = min(n, kit.stock(c, item))
    if got:
        lost = kit.take(c, item, got)
        kit.waste(c, item, got, lost, 'Trái dập lựa ra')
    d['bruise'].pop(item, None)
    d['today']['sorted'] += got
    return dict(message=f'🧺 Lựa ra {got} {FRUIT[item]["unit"]} {_lower(FRUIT[item]["name"])} dập, để riêng. Rổ sạch rồi.')


def _open(s, c, d, p):
    t = _task(c, p, ('setup',))
    st, n = d['stall'], t['needs']
    kit.need(st['cover'], 'Dựng dù hoặc căng bạt trước đã.')
    if st['cover'] != n['cover']:
        t['mistakes'] += 1
        cq.slip(t, 'cover', 2 if n['cover'] == 'bat' else 1, 'Mưa thế này mà chỉ dựng dù, nước hắt ướt hết rổ.' if n['cover'] == 'bat'
                else 'Căng bạt kín mít giữa nắng, trái hầm hơi mau nhũn.', 'che sạp chưa hợp trời')
        if n['cover'] == 'bat':
            _wet(c, d, 1)
    if not st['tested']:
        t['mistakes'] += 1
        cq.slip(t, 'untested', 1, 'Chưa thử cân đã bán, lỡ cân lệch thì khách thiệt.', 'chưa thử cân')
    elif d['scale']['off']:
        t['mistakes'] += 1
        cq.slip(t, 'drift', 2, 'Thử cân thấy lệch mà không chỉnh, bán vậy là cân sai cho khách.', 'cân lệch chưa chỉnh')
    left = {k: v for k, v in d['bruise'].items() if v}
    if left:
        t['mistakes'] += 1
        cq.slip(t, 'bruised_left', 1, 'Còn trái dập lẫn trong rổ, để lâu lây sang trái lành.', 'chưa lựa trái dập')
    st['open'] = True
    kit.start_work(t)
    ok = not cq.slips(t)
    kit.complete(s, c, t, 0, 'Dọn sạp, thử cân, lựa trái dập.')
    return dict(message='☀️ Mở hàng! ' + ('Dì Tư nhắn: “Giỏi lắm con, bán đắt nghe!”' if ok else 'Dì Tư nhắn: “Mở hàng đi, mai nhớ kỹ hơn nghe con.”'),
                celebrate=ok)


# ---------------------------------------------------------------- choosing and weighing
def _need_prep(t: dict) -> None:
    kit.need(t['known'], 'Hỏi khách mua gì đã nhé.')
    kit.need(t['stage'] == 'prep', 'Đã cân xong rồi.')


def _pick_fruit(s, c, d, p):
    t = _task(c, p, ('buy', 'altar', 'bulk'))
    _need_open(d)
    _need_prep(t)
    item = kit.one_of(p.get('item'), FRUIT, 'Sạp không có trái này.')
    stage = kit.one_of(p.get('stage'), STAGE_LABEL, 'Độ chín không hợp lệ.')
    kit.need(len(t['bag']) < BAG_MAX, 'Rổ đầy rồi.')
    got = _take_stage(c, item, stage)
    kit.need(got, f'Hết {_lower(FRUIT[item]["name"])} {_lower(STAGE_LABEL[stage])}. Chọn rổ khác hoặc nói thật với khách.')
    t['seq'] += 1
    f = FRUIT[item]
    g = int(round(f['g'] * (85 + _hash('tc-g', t['id'], t['seq']) % 31) / 100 / 10.0)) * 10
    bruised = d['bruise'].get(item, 0) > 0
    if bruised:
        d['bruise'][item] -= 1
        if not d['bruise'][item]:
            d['bruise'].pop(item)
    t['bag'].append(dict(i=item, s=stage, g=g, e=got['e'], c=got['c'], b=bruised))
    t['cost'] += got['c']
    kit.start_work(t)
    warn = ' ⚠️ Trái này bị dập (rổ chưa lựa)!' if bruised else ''
    return dict(message=f'{f["emoji"]} Bỏ một {f["unit"]} {_lower(f["name"])} ({_lower(STAGE_LABEL[stage])}, ~{g} gam) vào rổ.{warn}')


def _unpick(s, c, d, p):
    t = _task(c, p, ('buy', 'altar', 'bulk'))
    _need_prep(t)
    kit.need(t['bag'], 'Rổ còn trống.')
    i = kit.integer(p.get('index'), 0, len(t['bag']) - 1)
    x = t['bag'].pop(i)
    if x['b']:
        kit.waste(c, x['i'], 1, x['c'], 'Trái dập lựa ra')
        msg = f'🧺 Lấy trái {_lower(FRUIT[x["i"]]["name"])} dập ra, bỏ riêng.'
    else:
        _put_back(c, x['i'], x['e'], x['c'])
        msg = f'↩️ Để lại một {FRUIT[x["i"]]["unit"]} {_lower(FRUIT[x["i"]]["name"])} vào rổ.'
    t['cost'] = max(0, t['cost'] - x['c'])
    return dict(message=msg)


def _tare(s, c, d, p):
    t = _task(c, p, ('buy', 'altar', 'bulk'))
    _need_prep(t)
    kit.need(not t['tare'], 'Đã trừ bì rồi.')
    t['tare'] = True
    return dict(message='⚖️ Nhấc rổ không lên cân, vặn kim về 0: đã trừ bì rổ.')


def shown_grams(d: dict, t: dict) -> int:
    """What the scale needle shows for this basket right now."""
    real = sum(x['g'] for x in t['bag'])
    return real + (0 if t['tare'] else BASKET) + d['scale']['off']


def _value(c: dict, bag: list) -> float:
    return sum(x['g'] * _price_kg(c, x['i']) * ((100 - XA_OFF) if x['s'] in CHEAP else 100) / 100 / 1000 for x in bag)


def bill(c: dict, d: dict, t: dict) -> int:
    real = sum(x['g'] for x in t['bag'])
    if not real:
        return 0
    return max(1, int(round(_value(c, t['bag']) * shown_grams(d, t) / real)))


def _lines_check(t: dict, d: dict) -> None:
    """Record what the customer will notice at the hand-over."""
    n, bag = t['needs'], t['bag']
    who = _who(t)
    if t['kind'] == 'bulk':
        wrong = [x for x in bag if x['i'] not in n['bulk'] or x['s'] != 'ky']
        if wrong:
            t['mistakes'] += 1
            cq.slip(t, 'bulk_wrong', 1, 'Anh gom trái chín kỹ giá rẻ, sao bỏ lẫn trái khác vào?', 'lẫn trái không phải chín kỹ')
    else:
        for ln in n['lines']:
            mine = [x for x in bag if x['i'] == ln['i']]
            f = FRUIT[ln['i']]
            if not mine:
                t['mistakes'] += 1
                cq.slip(t, 'missing_' + ln['i'], 2, f'Tôi mua {_lower(f["name"])} mà không thấy trong túi.', 'thiếu loại trái')
                continue
            if ln['n'] and len(mine) != ln['n']:
                t['mistakes'] += 1
                cq.slip(t, 'count_' + ln['i'], 1, f'Tôi lấy {ln["n"]} {f["unit"]} {_lower(f["name"])}, sao ra {len(mine)}?', 'sai số trái')
            off = [x for x in mine if x['s'] not in ln['want']]
            if off:
                st = off[0]['s']
                line = {'xanh': 'Mua về ăn liền mà trái còn xanh, cứng ngắc.', 'ky': 'Trái chín nhũn cả rồi, không bày được lâu.',
                        'heo': 'Trái héo cuống, không tươi như lời hứa.', 'chin': 'Tôi dặn trái xanh để dành, chín thế này mai là nhũn.',
                        'tuoi': 'Tôi lấy loại khác cơ.'}[st]
                t['mistakes'] += 1
                cq.slip(t, 'ripe_' + ln['i'], 2 if t['kind'] == 'altar' else 1, line, 'chọn sai độ chín')
        extra = {x['i'] for x in bag} - {ln['i'] for ln in n['lines']}
        if extra:
            t['mistakes'] += 1
            cq.slip(t, 'extra', 1, 'Túi có trái tôi đâu có mua.', 'bỏ nhầm trái')
    if any(x['b'] for x in bag):
        t['mistakes'] += 1
        cq.slip(t, 'bruised', 2, f'{who} bóc ra thấy trái dập, thâm một góc.', 'bán trái dập')
    shown, real = shown_grams(d, t), sum(x['g'] for x in bag)
    over = shown - real
    if over > 0:
        d['today']['over_g'] += over
        if n.get('check'):
            t['mistakes'] += 1
            cq.slip(t, 'cheat_scale', 2, f'Cân lại ở cân đối chứng thiếu {over} gam. Cân rổ không trừ bì, hay cân lệch?', 'cân thiếu cho khách')


def _weigh(s, c, d, p):
    t = _task(c, p, ('buy', 'altar', 'bulk'))
    _need_open(d)
    _need_prep(t)
    kit.need(t['bag'], 'Rổ còn trống. Chọn trái cho khách đã.')
    n = t['needs']
    shown = shown_grams(d, t)
    who = _who(t)
    if t['kind'] == 'bulk':
        kit.need(n['min'] <= len(t['bag']) <= n['max'], f'Anh Lâm gom từ {n["min"]} tới {n["max"]} trái chín kỹ.')
    real = sum(x['g'] for x in t['bag'])
    for ln in n['lines']:
        # The customer reads the needle: one fruit fewer that still makes the weight is one too many.
        mine = sorted(x['g'] for x in t['bag'] if x['i'] == ln['i'])
        if ln['kg'] and len(mine) > 1 and _share(shown, real, sum(mine) - mine[0]) >= ln['kg']:
            return dict(message=f'{who}: “Nhiều quá, tôi lấy {kg_text(ln["kg"])} thôi. Bớt ra một trái đi.”', correct=False)
    _lines_check(t, d)
    for ln in n['lines']:
        mine = sum(x['g'] for x in t['bag'] if x['i'] == ln['i'])
        share = _share(shown, real, mine)
        if ln['kg'] and mine and share * 100 < ln['kg'] * SHORT:
            t['mistakes'] += 1
            cq.slip(t, 'short_' + ln['i'], 1, f'Tôi mua {kg_text(ln["kg"])} mà cân có {kg_text(share)}.', 'cân chưa đủ')
    t['weighed'] = shown
    t['price'] = bill(c, d, t)
    h = _haggle_of(t)
    if h:
        t['offer'] = max(1, t['price'] * h['pct'] // 100)
        t['stage'] = 'haggle'
        if _tw(t, 'dear'):
            t['tw']['state'] = 'done'
            ask = _dear_line(c, t)
            return dict(message=f'⚖️ Cân: {kg_text(shown)} · {t["price"]} xu. {who}: {ask} “{t["offer"]} xu thôi!”', surprise=True)
        ask = {'meet': 'Bớt chút đi, tính cho tròn!', 'extra': 'Mua nhiều vậy mà không cho thêm gì à?',
               'hold': 'Đắt thế, bớt đi chứ?'}[h['wants']]
        return dict(message=f'⚖️ Cân: {kg_text(shown)} · {t["price"]} xu. {who}: “{t["offer"]} xu thôi! {ask}”')
    return _to_pay(c, t, f'⚖️ Cân: {kg_text(shown)} · {t["price"]} xu.')


def _share(shown: int, real: int, grams: int) -> int:
    """What the needle says for `grams` of the fruit in the basket (the basket and a drift spread over it)."""
    return grams + (shown - real) * grams // max(1, real)


def _to_pay(c: dict, t: dict, head: str) -> dict:
    st = _tw(t, 'tab', 'dash')
    if st and st['state'] == 'wait':
        # Before the money: this customer wants it on credit / walks off with the bag.
        st['state'] = 'on'
        t['stage'] = 'credit'
        line = (TAB_LINES if t['twist']['kind'] == 'tab' else DASH_LINES)[t['twist']['n']]
        return dict(message=f'{head} {_who(t)}: {line}', surprise=True)
    t['stage'] = 'pay'
    t['cash'] = till.new(t['price'], t['id'], c=c, t=t)
    return dict(message=f'{head} Khách đưa {sum(t["cash"]["tender"])} xu: thối lại cho đúng.')


def _deal(s, c, d, p):
    t = _task(c, p, ('buy', 'altar', 'bulk'))
    h = _haggle_of(t)
    kit.need(t['stage'] == 'haggle' and h, 'Khách không trả giá.')
    deal = kit.one_of(p.get('deal'), DEALS, 'Chọn cách trả giá.')
    who, full = _who(t), t['price']
    t['deal'] = deal
    d['today']['bargains'] += 1
    if deal == 'hold':
        line = 'Trái tươi, cân đủ, giá này là đúng giá rồi ạ.'
        if h['wants'] != 'hold':
            t['mistakes'] += 1
            cq.slip(t, 'stiff', 1, 'Trả giá có một chút mà không bớt đồng nào.', 'không chịu bớt giá')
    elif deal == 'meet':
        t['price'] = (full + t['offer'] + 1) // 2
        line = f'Thôi con bớt, lấy {t["price"]} xu cho tròn nha.'
    elif deal == 'extra':
        kit.need(kit.stock(c, 'cam') > 0, 'Hết cam để tặng thêm rồi. Chọn cách khác nhé.')
        cost = kit.take(c, 'cam', 1)
        t['cost'] += cost
        t['extra'] = 'cam'
        line = 'Giá này nha, con tặng thêm trái cam ăn lấy thảo.'
    else:
        t['price'] = t['offer']
        line = f'Dạ, {t["offer"]} xu cũng được.'
        if t['price'] < t['cost']:
            line += ' (bán dưới giá vốn)'
    good = deal == h['wants'] or (deal == 'give')
    tail = {True: 'Khách cười tươi, móc tiền ra.', False: 'Khách gật, nhưng hơi lưỡng lự.'}[good]
    return _to_pay(c, t, f'🤝 “{line}” {tail}')


def _decline(s, c, d, p):
    """Nothing on the stall fits what the customer asked for: say so honestly."""
    t = _task(c, p, ('buy', 'altar', 'bulk'))
    kit.need(t['known'] and t['stage'] == 'prep', 'Không phải lúc này.')
    for x in list(t['bag']):
        if x['b']:
            kit.waste(c, x['i'], 1, x['c'], 'Trái dập lựa ra')
        else:
            _put_back(c, x['i'], x['e'], x['c'])
    t['bag'], t['cost'], t['choice'] = [], 0, 'decline'
    kit.start_work(t)
    msg = _finish(s, c, d, t, 0, f'Nói thật với {_who(t)}: sạp chưa có trái đúng ý, hẹn hôm sau.')
    return dict(message='🙏 ' + msg)


def _pay(s, c, d, p):
    t = _task(c, p, ('buy', 'altar', 'bulk'))
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    who = _who(t)
    rec = t['cash']
    chk = till.check(s, c, t, rec, p.get('change'), who)
    if chk['stop']:
        return dict(message='💵 ' + chk['message'], correct=False)
    react = cq.react(s, c, t, t['price'], who=who)
    st = till.settle(s, c, t, rec, react, who)
    net = react['pay'] - st['loss']
    grams = sum(x['g'] for x in t['bag'])
    _sold(d, t)
    over = shown_grams(d, t) - grams
    if over > 0:
        cut = t['price'] - int(round(_value(c, t['bag'])))
        d['today']['over_xu'] += max(0, cut)
        d['stats']['over_xu'] += max(0, cut)
    elif not cq.slips(t):
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


# ---------------------------------------------------------------- a customer brings fruit back
def _look(s, c, d, p):
    t = _task(c, p, ('return',))
    kit.need(t['known'], 'Nghe khách nói đã nhé.')
    t['look'] = True
    kit.start_work(t)
    return dict(message='🔍 ' + t['_look'])


def _settle_return(s, c, d, p):
    t = _task(c, p, ('return',))
    kit.need(t['known'], 'Nghe khách nói đã nhé.')
    choice = kit.one_of(p.get('choice'), ('swap', 'refund', 'explain', 'argue'), 'Chọn cách giải quyết.')
    item, fault, who = t['needs']['ret'], t['_fault'], _who(t)
    f = FRUIT[item]
    kit.start_work(t)
    t['choice'] = choice
    d['stats']['returns'] += 1
    if not t['look']:
        t['mistakes'] += 1
        cq.slip(t, 'no_look', 1, 'Chưa xem trái đã phán, chẳng hỏi han gì.', 'chưa xem trái')
    if choice == 'swap':
        good = next((st for st in f['stages'] if st not in CHEAP and baskets(c)[item].get(st)), None)
        kit.need(good, f'Hết {_lower(f["name"])} tốt để đổi. Hoàn tiền cho khách nhé.')
        got = _take_stage(c, item, good)
        kit.waste(c, item, 1, got['c'], 'Đổi trái cho khách')
        line = f'Đổi cho {who} trái {_lower(f["name"])} khác.'
    elif choice == 'refund':
        back = min(max(2, f['kg'] * f['g'] // 1000), c['money'])
        if back:
            kit.money(s, c, -back, f'Hoàn tiền trái hư: {t["title"]}'[:120], t['id'], 'refund')
        line = f'Hoàn {back} xu cho {who}.'
    elif choice == 'explain':
        line = 'Giải thích cho khách vì sao trái như vậy.'
        if fault == 'shop':
            t['mistakes'] += 1
            cq.slip(t, 'excuse', 2, 'Trái dập từ sạp mà còn giải thích vòng vo.', 'đổ lỗi cho khách')
    else:
        line = 'Cãi với khách giữa chợ.'
        t['mistakes'] += 1
        cq.slip(t, 'argue', 2, 'Mang trái lại mà bị cãi như mình đi ăn vạ.', 'cãi khách')
    if fault == 'buyer' and choice == 'explain':
        line = {'xoai': 'Xoài còn xanh, cô để thêm hai hôm là chín ngọt.', 'chuoi': 'Chuối chín kỹ vì để nắng, ruột vẫn ngon anh ạ.'}.get(item, line)
    react = cq.react(s, c, t, 0, who=who)
    msg = _finish(s, c, d, t, 0, (line + (' ' + react['message'] if react['message'] else '')).strip())
    return dict(message='🧺 ' + msg, celebrate=not cq.slips(t))


# ---------------------------------------------------------------- selling off the ripe fruit
def _xa(s, c, d, p):
    _need_open(d)
    kit.need(not d['stall']['xa'], 'Hôm nay đã rao xả rồi.')
    b = baskets(c)
    cheap = {k: sum(q for st, q in v.items() if st in CHEAP) for k, v in b.items()}
    kit.need(any(cheap.values()), 'Không có trái chín kỹ hay héo nào để xả.')
    sold, money = 0, 0
    for item, q in cheap.items():
        if not q:
            continue
        n = max(1, q * (55 + _hash('tc-xa', c['day'], item) % 30) // 100)
        f = FRUIT[item]
        for _ in range(n):
            st = 'ky' if b[item].get('ky') else 'heo'
            got = _take_stage(c, item, st)
            if not got:
                break
            b[item][st] -= 1
            sold += 1
            money += f['g'] * _price_kg(c, item) * (100 - XA_OFF) / 100 / 1000
    money = int(round(money))
    d['stall']['xa'] = True
    d['today']['xa_sold'] += sold
    d['today']['xa_money'] += money
    d['stats']['xa_sold'] += sold
    if money:
        kit.money(s, c, money, f'Rao xả {sold} trái chín kỹ, héo', f'tc-xa-{c["day"]}', 'sales')
    return dict(message=f'📣 “Xả hàng đây, trái chín ngọt bán rẻ!” Bán được {sold} trái, thu {money} xu.', celebrate=bool(sold))


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


def _wet(c: dict, d: dict, n: int) -> str | None:
    """Rain soaked the baskets: n more bruised fruit in the orange and grape baskets."""
    hit = []
    for item in ('cam', 'nho', 'xoai'):
        if kit.stock(c, item) > d['bruise'].get(item, 0):
            d['bruise'][item] = d['bruise'].get(item, 0) + n
            hit.append(_lower(FRUIT[item]['name']))
    return f'Có trái bị úng trong rổ {", ".join(hit)}: lựa ra kẻo lây.' if hit else None


def _desk_hook(s: dict, c: dict, key: str, v) -> str | None:
    d = _data(c)
    if key == 'bruise':
        return _wet(c, d, int(v))
    return None


# ================================================================ the awkward people at the stall (0.9.16)
# A customer made from 0.9.16 on may carry a twist (twist_of, from the task id: never regenerated, only checked):
# 'dear' calls the price a rip-off and bargains; 'tab' wants it on credit; 'dash' walks off with the bag
# "to fetch the wallet". The player answers in their own way (a price they name, a deposit they ask
# for, holding the bag, calling the market guard); each person decides from hidden traits (street_folk).
TWISTS = ('dear', 'tab', 'dash')
TW_STATES = ('wait', 'on', 'done')
CREDIT = {'tab': ('tab', 'part', 'refuse'), 'dash': ('hold', 'trust', 'call')}
DEAR_LINES = (
    '“Sạp đầu chợ bán {kg} xu/ký thôi, ở đây cắt cổ vậy?”',
    '“Trên mạng có {kg} xu/ký, giao tận nhà. Bán đắt vl.”',
    '“Hôm qua mua có {kg} xu/ký, nay lên giá hả? Ăn cướp à?”',
    '“Siêu thị còn rẻ hơn, {kg} xu/ký. Bớt đi không tôi đi chỗ khác.”',
)
TAB_LINES = (
    '“Quên ví ở nhà rồi, ghi nợ đi, mai trả.”',
    '“Mua ở đây bao năm rồi, ghi sổ tí có sao đâu.”',
    '“Cuối tháng lương về trả một thể, ok không?”',
    '“Ghi nợ đi em, chị quỵt đâu mà lo, hihi.”',
)
DASH_LINES = (
    '“Để chị chạy ra xe lấy ví nha…” rồi xách túi đi thẳng.',
    '“Ơ quên ví, để anh ra cây ATM…” vừa nói vừa bước nhanh.',
    '“Tí quay lại trả nha!” Túi trái đã trên tay.',
    'Khách vừa nghe điện thoại vừa lùi dần ra đường, túi trái vẫn cầm chặt.',
)


def twist_of(t: dict) -> dict | None:
    """The twist a customer carries (a pure function of the job: the validator checks a stored twist against it)."""
    if t.get('day', 1) < 2 or t.get('kind') not in ('buy', 'altar'):
        return None
    r, n = folk.roll('tc-twist', t['id']), folk.roll('tc-twist-n', t['id'])
    if t['kind'] == 'altar':
        kind = 'tab' if r < 25 else None
    elif t.get('_haggle'):
        kind = 'tab' if r < 20 else 'dash' if r < 32 else None
    else:
        kind = 'dear' if r < 30 else 'tab' if r < 45 else 'dash' if r < 55 else None
    if not kind:
        return None
    tw = dict(kind=kind, n=n % 4)
    if kind == 'dear':
        tw.update(pct=75 + n % 14, wants=('meet', 'extra', 'hold')[n % 3])
    return tw


def _tr(t: dict) -> dict:
    i = _npc_index(t)
    return folk.traits(t['id'], PEOPLE[i][3] if 0 <= i < len(PEOPLE) else None)


def _tw(t: dict, *kinds) -> dict | None:
    tw = t.get('twist')
    return t.get('tw') if isinstance(tw, dict) and tw.get('kind') in kinds else None


def _haggle_of(t: dict) -> dict | None:
    """How this customer bargains: the order's own haggle, or a 'dear' twist (the price called a rip-off)."""
    if t.get('_haggle'):
        return t['_haggle']
    tw = t.get('twist')
    return dict(pct=tw['pct'], wants=tw['wants']) if isinstance(tw, dict) and tw.get('kind') == 'dear' else None


def _dear_line(c: dict, t: dict) -> str | None:
    tw = t.get('twist')
    if not (isinstance(tw, dict) and tw.get('kind') == 'dear' and t['bag']):
        return None
    item = t['bag'][0]['i']
    return DEAR_LINES[tw['n']].format(kg=max(1, _price_kg(c, item) * tw['pct'] // 100))


def _street_trust(c: dict, delta: int) -> None:
    box = c.get('incidents')
    if isinstance(box, dict) and isinstance(box.get('trust'), int):
        box['trust'] = max(0, min(100, box['trust'] + delta))


def _offer(s, c, d, p):
    """The player names the price: the customer decides by themselves (budget, stinginess, mood)."""
    t = _task(c, p, ('buy', 'altar', 'bulk'))
    h = _haggle_of(t)
    kit.need(t['stage'] == 'haggle' and h, 'Khách không trả giá.')
    price = kit.integer(p.get('price'), 1, 10 ** 4)
    hg = t.setdefault('hg', dict(tries=0))
    r = folk.haggle(_tr(t), t['price'], t['offer'], price, hg['tries'])
    who = _who(t)
    d['today']['bargains'] += 1
    if r['kind'] == 'counter':
        hg['tries'] += 1
        t['offer'] = r['counter']
        return dict(message=f'🤝 {who}: “{price} xu vẫn đắt. {r["counter"]} xu, chốt không?”')
    if r['kind'] == 'walk':
        for x in list(t['bag']):
            _put_back(c, x['i'], x['e'], x['c']) if not x['b'] else kit.waste(c, x['i'], 1, x['c'], 'Trái dập lựa ra')
        t['bag'], t['cost'], t['deal'] = [], 0, 'own'
        react = cq.react(s, c, t, 0, who=who)
        msg = _finish(s, c, d, t, 0, f'{who} đặt túi xuống: “Thôi, đi chỗ khác.” {react["message"]}'.strip())
        return dict(message='🚶 ' + msg, correct=False)
    t['price'], t['deal'] = price, 'own'
    line = f'{who} cười tươi: “Vậy mới được chứ!”' if r['kind'] == 'glad' else f'{who} gật: “Ừ, {price} xu.”'
    if price < t['cost']:
        line += ' (bán dưới giá vốn)'
    return _to_pay(c, t, f'🤝 {line}')


def _credit(s, c, d, p):
    """A customer who wants it on credit, or walks off with the bag: the player's move."""
    t = _task(c, p, ('buy', 'altar', 'bulk'))
    st = _tw(t, 'tab', 'dash')
    kit.need(st and st['state'] == 'on' and t['stage'] == 'credit', 'Khách không xin nợ.')
    kind = t['twist']['kind']
    choice = kit.one_of(p.get('choice'), CREDIT[kind], 'Chọn cách xử lý.')
    tr, who, price = _tr(t), _who(t), t['price']
    cash = price * (tr['budget'] + 20) // 100
    st.update(state='done', choice=choice)

    def till_now(line):
        t['stage'] = 'pay'
        t['cash'] = till.new(price, t['id'], c=c, t=t)
        return dict(message=f'{line} Khách đưa {sum(t["cash"]["tender"])} xu: thối lại cho đúng.')

    def goes_home(line, back=True, review=None):
        # No sale: the fruit goes back in its baskets (or is gone with a runner).
        if back:
            for x in list(t['bag']):
                _put_back(c, x['i'], x['e'], x['c']) if not x['b'] else kit.waste(c, x['i'], 1, x['c'], 'Trái dập lựa ra')
            t['bag'], t['cost'] = [], 0
        if review:
            kit.review(s, c, t['npc'], review[0], review[1], t['id'])
        react = cq.react(s, c, t, 0, who=who)
        return dict(message=_finish(s, c, d, t, 0, f'{line} {react["message"]}'.strip()), correct=False)

    if kind == 'tab':
        if choice == 'refuse':
            if cash >= price:
                return till_now(f'🙅 Không bán chịu. {who} lục túi: “Ơ còn tiền nè, thôi trả luôn.”')
            return goes_home(f'🙅 Không bán chịu. {who} đặt túi xuống: “Keo vl, đi chỗ khác.”')
        kit.need(len(folk.open_debts(d['debts'])) < folk.DEBT_MAX, 'Sổ nợ đầy rồi: đòi bớt nợ cũ đã.')
        now = min(kit.integer(p.get('amount'), 1, price), cash) if choice == 'part' else 0
        react = cq.react(s, c, t, now, who=who)
        rest = max(0, price - react['cut'] - now)
        if rest:
            d['debts'] = folk.trim_debts(d['debts'] + [folk.debt_line(f'no-{t["id"]}', _npc_index(t), who, t['id'], c['day'], rest, t['title'])])
        _sold(d, t)
        head = f'💵 {who} đưa trước {react["pay"]} xu' if now else f'📒 Ghi nợ cho {who}'
        return dict(message=_finish(s, c, d, t, react['pay'], (f'{head}, còn nợ {rest} xu. ' + react['message']).strip()))
    # dash: the bag is already walking away
    if choice == 'hold':
        if tr['honest'] >= 40:
            return till_now(f'✋ Bạn giữ túi lại. {who} quay ra xe lấy ví, lát sau trở lại.')
        if tr['proud'] > 60:
            return goes_home(f'✋ Bạn giữ túi lại. {who}: “Nghi người ta ăn quỵt à? Không mua nữa!”',
                             review=(2, 'Mua có túi trái mà bị giữ lại như kẻ trộm, bực mình.'))
        return till_now(f'✋ Bạn giữ túi lại. {who} lầm bầm rồi móc tiền ra.')
    if choice == 'trust':
        if tr['honest'] >= 55:
            return till_now(f'🙂 Bạn để khách cầm đi. Mười phút sau {who} quay lại thật.')
        cost = t['cost']
        d['stats']['dashed'] += 1
        _sold(d, t)
        return goes_home(f'🏃 Bạn để khách cầm đi. {who} đi mất hút, mất trắng túi trái ({cost} xu tiền vốn).', back=False)
    # call the market guard
    if tr['honest'] < 55:
        d['stats']['caught'] += 1
        return till_now(f'👮 Bảo vệ chợ chặn lại ở cổng. {who} đỏ mặt quay lại trả tiền.')
    t['mistakes'] += 1
    cq.slip(t, 'accuse', 1, 'Chạy ra xe lấy ví thôi mà gọi bảo vệ như bắt trộm, xấu hổ ghê.', 'nghi oan khách')
    return till_now(f'👮 Bảo vệ chợ chặn lại. {who} giơ cái ví: “Lấy ví thật mà, làm gì dữ vậy!”')


def _sold(d: dict, t: dict) -> None:
    grams = sum(x['g'] for x in t['bag'])
    d['today']['sold_g'] += grams
    d['stats']['sold_g'] += grams
    d['today']['customers'] += 1
    d['stats']['customers'] += 1


def _chase(s, c, d, p):
    return folk.chase_action(s, c, ID, d['debts'], p, lambda i: PEOPLE[i][3] if 0 <= i < len(PEOPLE) else None)


# ---------------------------------------------------------------- troubles at the stall: a runtime scene with the player's own move
TROUBLE = ('thief', 'shame')
TROUBLE_CHOICES = {'thief': ('remind', 'demand', 'guard', 'ignore'), 'shame': ('scale', 'taste', 'argue', 'ignore')}
THIEVES = ('Một bà khách lạ', 'Một cậu thanh niên đội mũ lưỡi trai', 'Hai cô bé mặc đồng phục', 'Một ông đeo kính râm')


def _trouble_tick(s: dict, c: dict, d: dict) -> bool:
    tb = d['trouble']
    if not d['stall']['open'] or d['desk']['ev'] is not None or not folk.trouble_due(tb, ID, c['day'], c['day_completed'], 45):
        return False
    k = 'thief' if folk.roll('tc-trouble', c['day'], tb['fired']) < 65 else 'shame'
    if k == 'thief':
        have = [x['id'] for x in FRUITS if kit.stock(c, x['id']) >= 2]
        if not have:
            return False
        item = have[folk.roll('tc-thief-item', c['day'], tb['seq']) % len(have)]
        qty = 1 + folk.roll('tc-thief-qty', c['day'], tb['seq']) % 3
        cost = kit.take(c, item, qty)
        f = FRUIT[item]
        value = max(1, qty * f['g'] * _price_kg(c, item) // 1000)
        facts = dict(item=item, qty=qty, value=value, cost=cost, who=THIEVES[folk.roll('tc-thief-who', c['day'], tb['seq']) % len(THIEVES)])
        text = f'{facts["who"]} lựa lựa rồi nhét {qty} {f["unit"]} {_lower(f["name"])} vào túi riêng, lững thững bước đi.'
    else:
        facts = dict(who='Một chị khách lạ', item='', qty=0, value=0, cost=0)
        text = 'Một chị khách giơ điện thoại quay sạp: “Cả nhà xem nè, trái cây gì mà bán đắt vl, chợ mạng rẻ bằng nửa!”'
    folk.trouble_open(tb, k, c['day'], 0, facts)
    kit.log(s, c, 'surprise', text, kit.npc_id(ID, 0), tb['ev']['id'])
    return True


def _trouble(s, c, d, p):
    tb = d['trouble']
    ev = tb['ev']
    kit.need(ev, 'Không có chuyện gì ở sạp.')
    choice = kit.one_of(p.get('choice'), TROUBLE_CHOICES[ev['kind']], 'Chọn cách xử lý.')
    f, tr = ev['facts'], folk.traits(ev['id'], None)
    who = f['who']
    good = None
    if ev['kind'] == 'thief':
        value, item, qty = f['value'], f['item'], f['qty']
        got = 0
        if choice == 'remind':
            if tr['proud'] < 60 and tr['honest'] >= 35:
                got, good, out = value, True, f'Bạn nhắc khéo: “Chị ơi, quên tính tiền kìa.” {who} đỏ mặt trả {value} xu.'
            else:
                good, out = None, f'Bạn nhắc khéo. {who}: “Quên cái gì? Nói vậy là vu khống đó nha!” rồi đi thẳng.'
        elif choice == 'demand':
            asked = kit.integer(p.get('amount'), 1, value * 3)
            if asked > value * 3 // 2:
                _street_trust(c, -1)
                good, out = False, f'Bạn đòi {asked} xu. Người xung quanh xì xào “bắt đền cắt cổ”, {who} được thể cãi lấy cãi để rồi bỏ đi.'
            elif tr['honest'] >= 25 or asked <= value:
                got, good, out = asked, True, f'Bạn giữ lại, đòi {asked} xu. {who} lí nhí xin lỗi, trả đủ.'
            else:
                good, out = None, f'{who}: “Làm như ghê lắm!” rồi giằng túi chạy mất.'
        elif choice == 'guard':
            for x in c['tasks']:
                if x.get('career') == ID and x['status'] not in ('completed', 'referred', 'cancelled') and 'patience' in x:
                    x['patience'] = max(25, x['patience'] - 6)
            if folk.roll('tc-guard', ev['id']) < 60:
                got, good, out = value, True, f'Bảo vệ chợ chặn ở cổng. {who} trả {value} xu, bị ghi tên vào sổ.'
            else:
                good, out = None, f'Bảo vệ tới thì {who} đã lẫn vào dòng người. Khách chờ ở sạp mặt dài ra.'
        else:
            out = f'Bạn làm ngơ. Sạp bên cạnh lắc đầu: “Thế mai nó lại tới.” Mất {qty} {FRUIT[item]["unit"]} {_lower(FRUIT[item]["name"])}.'
        if got:
            kit.money(s, c, got, f'{who} trả tiền trái lấy lén'[:120], ev['id'], 'sales')
        else:
            kit.waste(c, item, qty, f['cost'], 'Bị chôm')
            d['stats']['stolen'] += qty
    else:
        if choice == 'scale':
            if tr['honest'] >= 40:
                good, out = True, 'Bạn mời cân lại bằng cân đối chứng, chỉ bảng giá. Chị khách tắt máy: “Ờ, trái ngon thật, giá vậy cũng được.”'
            else:
                good, out = None, 'Bạn mời cân lại. Chị khách vẫn đăng clip, nhưng bên dưới có người bênh sạp.'
        elif choice == 'taste':
            c['xp'] += 3
            kit.take(c, 'cam', 1) if kit.stock(c, 'cam') else None
            good, out = True, 'Bạn bổ trái cam mời nếm. Chị khách nhai nhai: “Ngọt thật, thôi xóa clip.” Còn mua một ký.'
        elif choice == 'argue':
            _street_trust(c, -2)
            kit.review(s, c, kit.npc_id(ID, 1), 2, 'Hôm qua có người quay clip sạp này, chủ sạp cãi um cả chợ.', ev['id'])
            good, out = False, 'Hai bên cãi nhau to, clip có thêm đoạn “chủ sạp nổi điên”. Cô Năm lắc đầu.'
        else:
            good, out = None, 'Bạn kệ. Clip có vài chục lượt xem rồi chìm.'
    folk.trouble_close(tb, out, good, choice, 'Kẻ chôm trái' if ev['kind'] == 'thief' else 'Bị quay clip “bán đắt”', '🥷' if ev['kind'] == 'thief' else '📱')
    return dict(message=('🥷 ' if ev['kind'] == 'thief' else '📱 ') + out, correct=good is not False, celebrate=good is True)


ACTIONS = {
    'tc_cover': _cover, 'tc_scale_test': _scale_test, 'tc_scale_fix': _scale_fix, 'tc_sort': _sort, 'tc_open': _open,
    'tc_pick': _pick_fruit, 'tc_unpick': _unpick, 'tc_tare': _tare, 'tc_weigh': _weigh, 'tc_deal': _deal, 'tc_decline': _decline,
    'tc_pay': _pay, 'tc_look': _look, 'tc_return': _settle_return, 'tc_xa': _xa,
    'tc_short': lambda s, c, d, p: _short(s, c, p),
    'tc_offer': _offer, 'tc_credit': _credit, 'tc_chase': _chase, 'tc_trouble': _trouble,
}


# ================================================================ day start and close
def _bruise_today(c: dict, d: dict) -> dict:
    mod = mod_of(c['day'])['id']
    out = {}
    if c['day'] == 1:
        return {'cam': 1}
    for x in FRUITS:
        q = kit.stock(c, x['id'])
        if q < 3:
            continue
        roll = _hash('tc-bruise', c['day'], x['id']) % 100
        n = 1 if roll < (45 if mod == 'heat' else 30) else 0
        if n and roll < 10:
            n = 2
        if n:
            out[x['id']] = min(n, q)
    return out


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    if not d['seeded']:
        d['seeded'] = True
        for item, qty, left in FIRST_MORNING:
            kit.add_lot(c, item, qty, 0, left, 'opening')
    d['stall'] = _fresh_stall(day)
    d['today'] = _fresh_today(day)
    d['scale'] = dict(off=drift_of(day), day=day)
    d['bruise'] = _bruise_today(c, d)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
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
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')
    # Honest debtors turn up with the money by themselves; the rest wait to be chased (the debt book).
    for note in folk.auto_repay(s, c, ID, d['debts'], lambda i: PEOPLE[i][3] if 0 <= i < len(PEOPLE) else None):
        kit.log(s, c, 'surprise', note)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK, hook=_desk_hook)
    today = d['today']
    lines = [f'🧺 Bán {kg_text(today["sold_g"]) if today["sold_g"] else "0 ký"} trái cho {today["customers"]} khách.']
    if today['xa_sold']:
        lines.append(f'📣 Rao xả {today["xa_sold"]} trái, thu {today["xa_money"]} xu.')
    # Bruised fruit nobody picked out spoils the fruit next to it overnight.
    rotted = 0
    for item, n in list(d['bruise'].items()):
        q = min(kit.stock(c, item), n * 2)
        if q:
            lost = kit.take(c, item, q)
            kit.waste(c, item, q, lost, 'Trái dập lây sang trái lành')
            rotted += q
    d['bruise'] = {}
    if rotted:
        today['rotted'] += rotted
        d['stats']['rotted'] += rotted
        lines.append(f'🪰 Trái dập để trong rổ làm hư thêm {rotted} trái.')
    if today['over_xu']:
        lines.append(f'⚖️ Dì Tư dò lại: hôm nay khách bị cân thiếu {kg_text(today["over_g"])}, thiệt {today["over_xu"]} xu. Mai trừ bì, chỉnh cân kỹ nghe con.')
    elif today['customers']:
        lines.append('⚖️ Dì Tư dò cân: đủ lạng đủ ký cho khách. Giỏi!')
    b = baskets(c)
    ripe = sum(q for v in b.values() for st, q in v.items() if st in ('chin', 'ky'))
    green = sum(q for k, v in b.items() for st, q in v.items() if st == 'xanh')
    if desk_note:
        lines.append(desk_note)
    d['stall'].update(open=False, cover=None, tested=False, xa=False)
    return dict(lines=lines, note=f'Mai trong rổ: {ripe} trái chín, {green} trái còn xanh. Trái về hôm nay mai vẫn còn xanh.',
                sold_g=today['sold_g'], customers=today['customers'], xa=today['xa_money'], rotted=rotted, over=today['over_xu'])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 85 else 4 if p >= 65 else 3 if p >= 45 else 2
    codes = {x['code'] for x in cq.slips(t)}
    if t['kind'] == 'setup':
        ready = 5 - len(codes & {'untested', 'drift', 'bruised_left'})
        return dict(criteria=[dict(key='cover', label='Che sạp hợp trời', score=3 if 'cover' in codes else 5, note='đúng trời' if 'cover' not in codes else 'che chưa hợp'),
                              dict(key='ready', label='Cân chuẩn, rổ sạch', score=max(2, ready), note='thử cân, lựa trái dập' if ready == 5 else 'còn thiếu khâu chuẩn bị')])
    if t['kind'] == 'return':
        manner = 2 if codes & {'argue', 'excuse'} else 5
        return dict(criteria=[dict(key='care', label='Xem kỹ trái', score=3 if 'no_look' in codes else 5, note='xem trái rồi mới nói' if 'no_look' not in codes else 'chưa xem trái'),
                              dict(key='manner', label='Giải quyết thật lòng', score=manner, note='nhận đúng phần lỗi' if manner == 5 else 'đổ lỗi, cãi khách')])
    if t.get('choice') == 'decline':
        return dict(criteria=[dict(key='honest', label='Nói thật', score=5, note='hết hàng đúng ý thì nói thật'),
                              dict(key='order', label='Có hàng đúng ý', score=3, note='lần này chưa có')])
    ripe = 3 if any(k.startswith('ripe_') for k in codes) else 5
    fruit = 2 if 'bruised' in codes else ripe
    weight = 2 if 'cheat_scale' in codes else 3 if any(k.startswith('short_') for k in codes) else 5
    manner = 4 if 'stiff' in codes else 5
    return dict(criteria=[dict(key='order', label='Đúng trái', score=5, note='đúng loại, đủ số'),
                          dict(key='fruit', label='Trái ngon, đúng độ chín', score=fruit, note='đúng độ chín khách cần' if fruit == 5 else 'trái chưa đúng ý'),
                          dict(key='weight', label='Cân đủ, trung thực', score=weight, note='cân đủ lạng đủ ký' if weight == 5 else 'cân chưa đủ'),
                          dict(key='manner', label='Vui vẻ khi trả giá', score=manner, note='mềm mỏng' if manner == 5 else 'cứng giá quá'),
                          dict(key='speed', label='Nhanh gọn', score=speed, note=f'chờ còn {p}% kiên nhẫn')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return ('Dì Tư dặn: ' + ('căng bạt che kín, ' if n['cover'] == 'bat' else 'dựng dù, ') +
                'thử cân với quả cân 1 ký (lệch thì chỉnh), lựa trái dập ra rồi mở hàng. ' + n['note'])
    if t['kind'] == 'return':
        return f'{_who(t)} mang {_lower(FRUIT[n["ret"]]["name"])} hôm qua lại. {n["note"]} Xem trái rồi giải quyết cho đúng lẽ.'
    if t['kind'] == 'bulk':
        return f'{_who(t)} gom trái chín kỹ (xoài, chuối, bơ), từ {n["min"]} tới {n["max"]} trái, giá xả. {n["note"]}'
    lines = ', '.join(_line_text(x) for x in n['lines'])
    check = ' · Khách mang cân riêng, sẽ cân lại.' if n.get('check') else ''
    return f'{_who(t)} mua: {lines}.{check} {n["note"]}'


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
    v['haggles'] = bool(_haggle_of(t)) and t['stage'] in ('haggle', 'credit', 'pay', 'done')
    tw = t.get('twist')
    v.pop('twist', None)
    v.pop('tw', None)
    v.pop('hg', None)
    if isinstance(tw, dict) and t['tw']['state'] != 'wait' and tw['kind'] in ('tab', 'dash'):
        v['twist'] = dict(kind=tw['kind'], state=t['tw']['state'], choice=t['tw']['choice'],
                          line=(TAB_LINES if tw['kind'] == 'tab' else DASH_LINES)[tw['n']])
    if t['kind'] == 'return' and t.get('look'):
        v['seen'] = t['_look']
    v['cash'] = till.public(t.get('cash'))
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    b = baskets(c) if c['ext'].get('inv') else {}
    sc = d['scale']
    return dict(intro=d['intro'], stall=d['stall'], bruise=d['bruise'], baskets=b, basket=BASKET,
                scale=dict(off=sc.get('off', 0), tested=bool(d['stall'].get('tested'))),   # a drifted needle shows on the empty scale
                mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                today=d['today'], stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                desk=kit.desk_public(d['desk'], DESK, ID), debts=folk.public_debts(d['debts']),
                trouble=dict(ev=d['trouble']['ev'], last=d['trouble']['last']))


def content() -> dict:
    return dict(fruits=[dict(id=x['id'], name=x['name'], emoji=x['emoji'], unit=x['unit'], g=x['g'], kg=x['kg'], stages=list(x['stages']))
                        for x in FRUITS], stages=STAGE_LABEL, cheap=list(CHEAP), xa_off=XA_OFF, basket=BASKET, short=SHORT,
                denoms=list(till.DENOMS), intro=INTRO, deals=list(DEALS), debt_max=folk.DEBT_MAX,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    k = t.get('kind')
    if k == 'setup':
        return 'Dựng dù (mưa thì căng bạt) → thử cân, lệch thì chỉnh → lựa trái dập → Mở hàng.'
    if k == 'return':
        return 'Xem trái → lỗi ở sạp thì đổi hoặc hoàn tiền; khách để chưa tới độ thì giải thích nhẹ nhàng.'
    return 'Hỏi khách → trừ bì rổ → chọn trái đúng độ chín → cân → trả giá (nếu có) → thu tiền, thối đúng.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = _data(c)
    if e.get('role') == 'sort':
        item = next((k for k, v in d['bruise'].items() if v), None)
        if item:
            n = min(d['bruise'].pop(item), kit.stock(c, item))
            if n:
                lost = kit.take(c, item, n)
                kit.waste(c, item, n, lost, 'Trái dập lựa ra')
            return f'Đã lựa {n} trái {_lower(FRUIT[item]["name"])} dập ra.'
        return 'Đã lau sạp, xếp lại mấy rổ cho đẹp.'
    if e.get('role') == 'call':
        return 'Đã rao mời khách qua đường ghé xem trái.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu sạp trái cây sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc sạp trái cây không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc sạp trái cây sai.')
    bag = t.get('bag')
    kit.need(isinstance(bag, list) and len(bag) <= BAG_MAX, 'Rổ trái sai.')
    for x in bag:
        kit.need(isinstance(x, dict) and set(x) == {'i', 's', 'g', 'e', 'c', 'b'} and x['i'] in FRUIT and x['s'] in STAGE_LABEL, 'Trái trong rổ sai.')
        kit.integer(x['g'], 10, 5000)
        kit.integer(x['e'], 0, 10 ** 7)
        kit.integer(x['c'], 0, 10000)
        _vbool(x['b'])
    kit.integer(t.get('seq'), 0, 1000)
    for k in ('tare', 'look'):
        _vbool(t.get(k))
    for k in ('weighed', 'price', 'offer'):
        if t.get(k) is not None:
            kit.integer(t[k], 0, 10 ** 6)
    kit.integer(t.get('cost'), 0, 10 ** 6)
    kit.need(t.get('deal') in (None, *DEALS, 'own'), 'Cách trả giá sai.')
    kit.need(t.get('choice') in (None, 'decline', 'swap', 'refund', 'explain', 'argue'), 'Cách giải quyết sai.')
    kit.need(t.get('extra') in (None, 'cam'), 'Quà tặng thêm sai.')
    till.validate(t.get('cash'), t)
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách quen sai.')
    # 0.9.16 fields: absent on older customers; when present they must be what twist_of gives and well formed.
    if 'twist' in t or 'tw' in t:
        tw, st = t.get('twist'), t.get('tw')
        kit.need(tw is not None and tw == twist_of(t), 'Chuyện của khách không khớp.')
        kit.need(isinstance(st, dict) and set(st) == {'state', 'choice'} and st['state'] in TW_STATES
                 and st['choice'] in (None, *CREDIT.get(tw['kind'], ())), 'Chuyện của khách sai.')
    kit.need(t.get('stage') != 'credit' or (_tw(t, 'tab', 'dash') or {}).get('state') == 'on', 'Khách xin nợ sai.')
    if 'hg' in t:
        kit.need(isinstance(t['hg'], dict) and set(t['hg']) == {'tries'}, 'Trả giá sai.')
        kit.integer(t['hg']['tries'], 0, 9)


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    _vbool(d['seeded'])
    till.validate_book(c)
    st = d['stall']
    kit.need(isinstance(st, dict) and st.get('cover') in (None, 'du', 'bat'), 'Sạp trái cây sai.')
    kit.integer(st['day'], 0, 10 ** 7)
    for k in ('open', 'tested', 'xa'):
        _vbool(st[k])
    sc = d['scale']
    kit.need(isinstance(sc, dict), 'Cân sai.')
    kit.integer(sc.get('off'), -500, 500)
    kit.integer(sc.get('day'), 0, 10 ** 7)
    kit.need(isinstance(d['bruise'], dict) and set(d['bruise']) <= set(FRUIT), 'Trái dập sai.')
    for v in d['bruise'].values():
        kit.integer(v, 0, 99)
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu sạp sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)
    folk.validate_debts(d['debts'], len(PEOPLE), kit.need)
    folk.validate_trouble(d['trouble'], TROUBLE, kit.need)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='tc_', category='shop',
    meta=dict(short='Bán trái cây', place='Sạp trái cây Dì Tư', tagline='Trái chín đúng độ, cân đủ từng lạng.', icon='basket',
              color='#e0892b', light='#fff1dc', weather='Nắng sớm đầu chợ', work='Khách mua', station='Sạp trái cây',
              greeting='Dựng dù, thử cân, lựa trái dập rồi mở hàng. Hỏi khách ăn liền hay để dành để chọn trái đúng độ chín nhé.',
              caption='Mỗi rổ trái một độ chín', map_label='19 · SẠP TRÁI CÂY DÌ TƯ'),
    people=PEOPLE,
    staff=[('Hiếu', 'sort', 'Cháu dì Tư, lựa trái dập nhanh như máy.', 80, 88),
           ('Lành', 'call', 'Giọng rao vang cả dãy chợ.', 84, 76),
           ('Ngân', 'sort', 'Sinh viên làm thêm, lựa từng trái rất kỹ.', 70, 94),
           ('Phát', 'call', 'Quen mặt cả chợ, ai đi qua cũng chào.', 78, 80)],
    roles={'sort': 'Lựa hàng', 'call': 'Rao hàng'},
    inventory=dict(items=ITEMS, capacity=40),
    prices=PRICES,
    tip=1,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('🧺', 'Sạp trái gọn gàng', [('Xoài chín', 'Rổ bán ngay'), ('Xoài xanh', 'Rổ để dành'), ('Trái dập', 'Rổ lựa riêng'), ('Quả cân 1 ký', 'Mặt cân')],
              ['Dựng dù, bày rổ', 'Thử cân, chỉnh kim', 'Trừ bì rổ, cân trái', 'Thu tiền, thối đúng']),
    stories=[('Cái cân của dì Tư', ('Cái cân đồng hồ của dì Tư đã dùng mười lăm năm, kim hơi rung.',
                                   'Sáng nào dì cũng đặt quả cân 1 ký lên thử, lệch thì vặn con ốc bên dưới.',
                                   'Dì bảo: “Cân đúng thì khách quay lại, cân sai thì bán được một lần.”')),
             ('Xoài chín cây', ('Cô Năm dạy bạn phân biệt xoài chín tự nhiên và xoài ủ thuốc.',
                                'Xoài chín cây cuống thơm, vỏ vàng không đều, bóp mềm đều tay.',
                                'Từ đó bạn chỉ lấy xoài xanh về tự để chín trong rổ thoáng.')),
             ('Mâm ngũ quả ngày rằm', ('Chú Bảy dặn mâm ngũ quả phải có trái chắc, bày được ba ngày.',
                                       'Bạn chọn bưởi, nải chuối xanh, cam, xoài xanh, thanh long.',
                                       'Qua rằm, chú Bảy mang tặng lại sạp một trái bưởi: “Lộc của ông bà.”'))],
    review_asides=['Trái ngon đúng độ, về ăn liền ngọt lịm.', 'Cân đủ, trừ bì rổ đàng hoàng.', 'Trả giá vui vẻ, còn được tặng thêm.',
                   'Lựa trái kỹ, không có trái dập.'],
    situations=SITUATIONS,
    guide='Dọn sạp → thử cân → lựa trái dập → mở hàng. Mỗi khách: hỏi ăn liền hay để dành → trừ bì rổ → chọn trái đúng độ chín → cân → trả giá → thu tiền.',
)
