"""Phi công Cánh Cò: first officer on the small turboprop of Hãng bay Cánh Cò (plugin career).

The player rides out of the lane before dawn and flies short hops from the city
to the islands and the delta beside Cơ trưởng Vân, who has flown these routes for
twenty years. One task is one hop (game/careers/airline.py picks the route):

* ``brief``: the weather at the destination and the fuel plan. Fuel = the hop +
  the flight to the alternate + 30 minutes of reserve, plus 20 minutes of holding
  when storms are forecast for the arrival. Too little and the captain says no;
  full tanks on a full aircraft put it over its take-off weight. Morning fog at
  the destination is waited out on the ground (a delay);
* ``walk``: the walk-around, four points. A pitot cover or an unlatched hold door
  the player sorts out; a worn tyre or an oil leak is the engineer's (a delay);
* ``start``: the before-start checklist, switch by switch in the card's order, and
  the passenger announcement whenever the hop is late;
* ``cruise``: sometimes a decision on the way (turbulence ahead, a storm cell on
  the track, a passenger taken ill);
* ``approach``: storm over the field (hold if the fuel allows, else the
  alternate), then two gates, 1,000 ft and the 200 ft decision height: continue
  only when stable and the runway is in sight, otherwise go around. Going around
  is never a failure; landing unstable is;
* ``landed``: park and write the log.

Safety over punctuality: delays cost a little patience, a clear announcement
keeps it; unsafe choices are safety slips (consequences.slip). The job is
salaried (employment); a flight flown by the book adds a small bonus.
Everything random is rolled from (day, slot) or the task id.

Around the flights (kept out of the generated tasks, so hops made by an older
release still validate):

* chuyện oái oăm (game/careers/air_odd.py): passengers, captains, the office,
  family and the lane push, flirt, cut corners and bargain; the player answers
  in their own tone and words and decides whom to bring in. Giving in costs
  conduct points: a reminder, a warning, stood down for the day, demoted;
* the sky: some hops meet heavy rain or a squall on arrival (rolled from the
  task id at take-off). The player reads the airport's report and sets the
  approach: wipers, autobrake, speed for the gusts, which side of the cell,
  and whether the runway is fit to land on at all.
"""
from __future__ import annotations

import copy

from ..jsoncopy import tree_copy
from . import kit
from . import airline as air
from . import air_odd as ao
from .air_odd_content import PILOT as ODD
from .. import consequences as cq
from .. import archive as ar

ID = 'pilot'
GEN = 1

RESERVE = 350          # kg: 30 minutes of final reserve
HOLD = 250             # kg: 20 minutes of holding over the destination
TANKS = 2000           # kg: full tanks
FULL_PAX = 64          # from this many passengers full tanks are over the take-off weight
BONUS = 12             # legacy saved hops keep their original bonus
DELAY = dict(fog=30, tech=30, recheck=10, hold=20, around=10, divert=45, caught=15)
LOG_MAX = 12
MAX_AROUNDS = 2

POINTS = [
    dict(id='gear', emoji='🛞', name='Bánh & càng', ok='Lốp đủ hơi, gai còn sâu, chốt càng đã rút.'),
    dict(id='engine', emoji='⚙️', name='Động cơ & cánh quạt', ok='Cánh quạt không sứt, dưới động cơ khô ráo.'),
    dict(id='wing', emoji='🪽', name='Cánh & ống pitot', ok='Mép cánh nhẵn, ống pitot đã tháo vỏ che.'),
    dict(id='hold', emoji='📦', name='Cửa khoang hàng', ok='Cửa khoang hàng đóng khít, chốt đã sập.'),
]
POINT = {p['id']: p for p in POINTS}
DEFECTS = {
    'cover': dict(point='wing', own=True, text='Vỏ che ống pitot màu đỏ vẫn còn cắm.', fix='Tháo vỏ che, cất vào túi đồ nghề.',
                  danger='Bay mà còn vỏ che ống pitot thì đồng hồ tốc độ bị mù.'),
    'latch': dict(point='hold', own=True, text='Chốt cửa khoang hàng chưa sập hẳn.', fix='Đóng lại, ấn chốt nghe “tách”.',
                  danger='Cửa khoang hàng bung giữa trời là tai nạn.'),
    'tyre': dict(point='gear', own=False, text='Lốp bánh trái mòn tới vạch đỏ.', fix='Chú Mẫn thay lốp, ghi sổ kỹ thuật.',
                 danger='Lốp mòn tới vạch đỏ dễ nổ khi hạ cánh.'),
    'oil': dict(point='engine', own=False, text='Có vệt dầu nhỏ giọt dưới động cơ phải.', fix='Chú Mẫn mở nắp kiểm tra, siết lại khớp nối.',
                danger='Rò dầu động cơ có thể làm tắt máy trên không.'),
}
CHECKLIST = [
    dict(id='doors', emoji='🚪', name='Cửa khoang', state='ĐÓNG'),
    dict(id='belts', emoji='💺', name='Biển thắt dây', state='BẬT'),
    dict(id='beacon', emoji='🔴', name='Đèn chống va', state='BẬT'),
    dict(id='brake', emoji='🅿️', name='Phanh đỗ', state='KÉO'),
]
ORDER = [x['id'] for x in CHECKLIST]
PANEL = ['beacon', 'brake', 'doors', 'belts']      # where the switches sit on the panel (not the card's order)
PA = [
    dict(id='clear', label='Nói rõ vì sao chậm, chậm bao lâu, xin lỗi và hẹn báo lại'),
    dict(id='vague', label='“Vì lý do khách quan, chuyến bay tạm hoãn.”'),
    dict(id='hide', label='“Tàu sắp cất cánh rồi, quý khách chờ chút.”'),
]
PA_IDS = [x['id'] for x in PA]
WX = {
    'clear': dict(emoji='☀️', name='Trời quang', text='Gió nhẹ 6 kt, tầm nhìn trên 10 km.'),
    'cloud': dict(emoji='⛅', name='Mây thấp', text='Chân mây 900 ft, tầm nhìn 5 km: vẫn trên mức tối thiểu.'),
    'wind': dict(emoji='🌬️', name='Gió ngang giật', text='Gió ngang 20 kt, có lúc giật tới 30 kt. Giới hạn của tàu: 28 kt.'),
    'storm': dict(emoji='⛈️', name='Giông lúc tới', text='Giông đi qua sân bay đúng giờ tới, tan sau khoảng 20 phút.'),
    'fog': dict(emoji='🌫️', name='Sương mù sáng', text='Tầm nhìn 300 m, dưới mức tối thiểu. Dự báo tan sau 30 phút.'),
}
EVENTS = {
    'turb': dict(emoji='〰️', title='Vùng rung lắc phía trước', text='Radar báo vùng mây rung lắc sau 5 phút nữa. Chị Thu đang rót nước nóng cho khách.',
                 options=[dict(id='belts', label='Bật đèn thắt dây, báo chị Thu tạm dừng phục vụ', grade='good'),
                          dict(id='climb', label='Xin lên cao thêm 2.000 ft cho êm, bật đèn thắt dây', grade='good'),
                          dict(id='ignore', label='Bay thẳng, rung chút thôi', grade='bad')]),
    'cell': dict(emoji='⛈️', title='Mây giông trên đường bay', text='Radar thấy một đám giông đỏ rực ngay trên đường bay, cách 30 dặm.',
                 options=[dict(id='deviate', label='Xin vòng tránh 20 dặm (thêm 5 phút)', grade='good'),
                          dict(id='through', label='Bay xuyên qua cho kịp giờ', grade='unsafe'),
                          dict(id='over', label='Leo cao vượt qua đỉnh mây', grade='bad')]),
    'medical': dict(emoji='🩺', title='Khách ốm trên tàu', text='',
                    options=[dict(id='continue', label='Bay tiếp tới nơi, báo mặt đất cho xe cấp cứu chờ sẵn', grade=''),
                             dict(id='divert', label='Chuyển hướng xuống sân bay gần nhất, báo xe cấp cứu', grade=''),
                             dict(id='wait', label='Chờ thêm 15 phút xem khách đỡ chưa', grade='bad')]),
}
ARRIVE = ('hold', 'divert', 'land')
KINDS = ('flight', 'storm', 'fog', 'tech', 'medical')
STAGES = ('brief', 'walk', 'start', 'cruise', 'approach', 'landed', 'done')

# The portraits give odd ids (_npc_01, _03…) long hair: the women sit on those.
PEOPLE = [
    ('Cơ trưởng Vân', 'Cơ trưởng, người kèm bạn bay', 'Hai mươi năm bay tuyến đảo. Hiền, nhưng không bỏ qua một dòng checklist.', 'picky'),
    ('Anh Lộc', 'Điều phái bay', 'Đưa bản tin thời tiết và kế hoạch dầu, nói nhanh như đọc radio.', 'quiet'),
    ('Chị Thu', 'Tiếp viên trưởng', 'Báo tình hình khoang khách, dặn bạn đọc thông báo cho rõ.', 'warm'),
    ('Chú Mẫn', 'Thợ máy trưởng', 'Người trong phố, mê máy bay từ nhỏ. Thấy vết dầu là không cho bay.', 'bossy'),
    ('Bà Chín', 'Hành khách đi thăm cháu', 'Lần đầu đi máy bay, sợ nhất là rung lắc.', 'warm'),
    ('Anh Kiệt', 'Hành khách đi công tác', 'Sáng đi chiều về, rất ghét trễ chuyến.', 'sour'),
    ('Bé Na', 'Học sinh lớp 6 bay về quê', 'Mơ làm phi công, xin xem buồng lái sau khi hạ cánh.', 'genz'),
]
CAPTAIN, DISPATCH, PURSER, ENGINEER, GRANNY, KIET, NA = range(7)

MODS = [
    dict(id='clear', emoji='🌤️', label='Trời đẹp', hint='Nắng nhẹ, gió êm. Hợp để làm quen tàu.', weight=3),
    dict(id='storms', emoji='⛈️', label='Mùa giông chiều', hint='Chiều hay có giông ở đảo: dự báo giông thì mang thêm dầu chờ.', min_day=2, weight=2),
    dict(id='fog', emoji='🌫️', label='Sương sớm', hint='Sáng sương dày ở cao nguyên, trưa mới tan.', min_day=2, weight=2),
    dict(id='wind', emoji='🌬️', label='Gió mùa', hint='Gió ngang giật ở sân bay ven biển. Canh giới hạn gió.', min_day=3, weight=2),
    dict(id='busy', emoji='🧳', label='Cao điểm hè', hint='Chuyến nào cũng kín chỗ: tàu nặng, đừng đổ dầu thừa.', min_day=3, weight=1),
]

# Small stories of the people you fly with: one line per finished hop, on across days.
REG_STORY = {
    CAPTAIN: ('Chị Vân: “Chị bay tuyến này từ hồi đường băng Côn Đảo còn là đường đất đỏ.”',
              'Chị Vân chỉ cho bạn con đường mòn trên đảo nhìn từ trên cao: “Kia là chỗ chị đi bơi mỗi sáng.”',
              'Chị Vân kể con gái chị học lớp 9, cũng muốn làm phi công: “Chị bảo nó học Toán cho chắc đã.”',
              'Chị Vân để bạn đọc toàn bộ thông báo cho khách: “Giọng em nghe yên tâm đấy.”',
              'Chị Vân ghi vào sổ huấn luyện: “Quyết định an toàn, bình tĩnh. Sẵn sàng bay chặng khó.”'),
    PURSER: ('Chị Thu: “Hôm nay khoang khách có một cụ bà lần đầu bay, lúc hạ cánh cụ vỗ tay to nhất.”',
             'Chị Thu mang vào buồng lái hai ly trà gừng: “Uống cho ấm, đêm qua mưa cả đêm.”',
             'Chị Thu bảo cả tổ tiếp viên thích bay với bạn: “Báo trước rung lắc, tụi chị kịp cất xe đẩy.”'),
    GRANNY: ('Bà Chín dúi cho bạn túi xoài cát: “Của nhà bà trồng, phi công ăn cho khỏe.”',
             'Bà Chín bảo lần này không còn sợ rung nữa: “Nghe cậu phi công nói trước là bà yên bụng.”',
             'Bà Chín khoe cháu nội vừa thi đỗ, bà bay ra đảo ăn mừng.'),
    KIET: ('Anh Kiệt càu nhàu: “Trễ thế này là lỡ cuộc họp đấy.”',
           'Anh Kiệt bảo lần trước nghe thông báo rõ ràng nên gọi điện dời họp kịp.',
           'Anh Kiệt đọc được bài báo về vụ lốp mòn, tự dưng nhắn cảm ơn tổ bay.',
           'Anh Kiệt giờ ngồi ghế cửa sổ, ngắm biển thay vì mở máy tính.'),
    NA: ('Bé Na hỏi: “Chú phi công ơi, sao máy bay không rơi ạ?” Bạn vẽ cho bé cái cánh lên giấy ăn.',
         'Bé Na mang theo cuốn vở vẽ đầy máy bay, xin chữ ký của cả tổ bay.',
         'Bé Na được điểm 10 bài thuyết trình “Một ngày của phi công”, ảnh chụp buồng lái in to trên bìa.'),
}

# The career's own story: from the first badge to the left seat.
ARC = [
    dict(id='badge', emoji='🪪', title='Thẻ tổ bay đầu tiên', landings=1, day=1,
         text=('Năm giờ sáng, bà Tám dúi cho ổ bánh mì: “Bay cẩn thận nghe con.”',
               'Chị Vân đeo thẻ tổ bay lên cổ bạn: “Ở đây không ai giỏi hơn checklist. Nhớ nhé.”')),
    dict(id='wings', emoji='🪽', title='Đôi cánh bạc', landings=3, day=1,
         text=('Sau chuyến thứ ba, chị Vân gắn lên ngực áo bạn đôi cánh bạc nhỏ.',
               '“Cánh này không phải để khoe. Nó nhắc em sáu mươi tám người phía sau.”')),
    dict(id='solo', emoji='🛬', title='Tự tay hạ cánh', landings=8, day=2,
         text=('Chị Vân buông tay khỏi cần lái: “Chặng này em hạ cánh. Chị chỉ ngồi xem.”',
               'Bánh chạm đường băng êm ru. Khoang khách vỗ tay, chú Mẫn đứng dưới giơ ngón cái.')),
    dict(id='night', emoji='🌙', title='Chuyến bay đêm đầu tiên', landings=16, day=4,
         text=('Đèn đường băng Côn Đảo sáng thành hai hàng như chuỗi hạt.',
               'Về tới đầu hẻm đã chín giờ tối. Cả xóm vẫn để đèn chờ nghe bạn kể chuyện.')),
    dict(id='left', emoji='🧑‍✈️', title='Ngồi ghế trái', landings=30, day=7,
         text=('Chị Vân đổi chỗ, cho bạn ngồi ghế trái của cơ trưởng trong chuyến huấn luyện.',
               '“Còn nhiều giờ bay nữa. Nhưng chị tin em rồi.”')),
]
ARC_INDEX = {x['id']: x for x in ARC}

INTRO = dict(
    title='Giới thiệu nghề: phi công tàu cánh quạt',
    lead='Bạn là cơ phó của Hãng bay Cánh Cò, bay chặng ngắn ra đảo và về miền Tây cùng cơ trưởng Vân. Sáng đi từ đầu hẻm, tối về kịp cơm.',
    work=[('📋', 'Đọc bản tin thời tiết, tính dầu cho chặng bay'),
          ('🚶', 'Đi một vòng quanh tàu: bánh, động cơ, cánh, cửa khoang hàng'),
          ('✅', 'Đọc checklist, bật từng công tắc đúng thứ tự'),
          ('📢', 'Chậm chuyến thì thông báo cho khách thật rõ ràng'),
          ('🛬', 'Tiếp cận, qua hai cổng kiểm tra rồi mới hạ cánh')],
    meet=[('🧑‍✈️', 'Cơ trưởng Vân: hiền, nhưng không bỏ qua dòng nào'),
          ('📡', 'Anh Lộc điều phái: bản tin, kế hoạch dầu'),
          ('🔧', 'Chú Mẫn thợ máy: người trong phố'),
          ('💁', 'Chị Thu tiếp viên trưởng: tin tức từ khoang khách'),
          ('⛈️', 'Giông chiều, sương sớm, gió ngang giật')],
    stars=[('⛽', 'Dầu đủ: chặng + dự bị + 30 phút, có giông thêm dầu chờ'),
           ('🔍', 'Không bỏ sót điểm nào quanh tàu'),
           ('✅', 'Checklist đúng thứ tự'),
           ('↗️', 'Chưa ổn định thì bay lại, không cố hạ cánh'),
           ('📢', 'Chậm chuyến thì nói thật với khách')],
)

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='birds', title='Đàn cò trên đường băng', emoji='🐦', npc=DISPATCH, min_day=2, tone='tense', at='between', weight=3,
         text='Anh Lộc gọi: “Một đàn cò đang kiếm ăn ở đầu đường băng. Đài hỏi tổ bay có chờ đội xua chim không.”',
         options=[dict(id='wait', label='Chờ đội xua chim, báo khách chậm 10 phút', hint='An toàn, trễ một chút',
                       effects=dict(patience=-4, xp=6), good=True, outcome='Cò bay lên thành một dải trắng. Tàu cất cánh sạch sẽ.'),
                  dict(id='go', label='Cất cánh luôn, cò thấy tàu là bay', hint='Không trễ… nếu may',
                       effects=dict(review=[2, 'Cất cánh khi đàn chim còn ở đầu đường băng, cả khoang nghe tiếng “bộp”. Hú vía.']), good=False,
                       outcome='Một con cò va vào mép cánh. Chú Mẫn phải kiểm tra cả buổi chiều.')],
         default='wait'),
    dict(id='drone', title='Flycam gần đầu đường băng', emoji='🛸', npc=DISPATCH, min_day=3, tone='tense', at='between', weight=2,
         text='Lúc lăn ra, bạn thấy một chiếc flycam lơ lửng gần hàng rào đầu đường băng.',
         options=[dict(id='report', label='Báo ngay đài kiểm soát, chờ họ xử lý', hint='Trễ vài phút',
                       effects=dict(patience=-3, xp=6), good=True, outcome='Đài cho dừng mọi chuyến 10 phút. Công an sân bay tìm ra cậu thanh niên quay phim.'),
                  dict(id='ignore', label='Kệ, nó còn xa', hint='Không mất thời gian',
                       effects={}, good=False, outcome='Chiếc flycam bay ngang ngay lúc chuyến sau cất cánh. Đài bực vì không ai báo.')],
         default='report'),
    dict(id='coffee', title='Ly cà phê của chú Mẫn', emoji='☕', npc=ENGINEER, min_day=2, tone='gentle', at='between', weight=2,
         text='Chú Mẫn bưng ra hai ly cà phê sữa đá: “Ngồi xíu đi cháu, chú kể chuyện cái tàu này hồi mới về.”',
         options=[dict(id='sit', label='Ngồi nghe chú kể năm phút', hint='Quen thêm người trong đội',
                       effects=dict(xp=8, mark='man_story'), good=True, outcome='Chú kể hồi tàu mới về, cả đội ngủ lại sân đỗ canh bão.'),
                  dict(id='later', label='Hẹn chú hôm khác', hint='Tập trung chuyến sau', effects={}, good=None,
                       outcome='Chú cười: “Ừ, bay đi, chiều về kể tiếp.”')],
         default='later'),
    dict(id='boss', title='Sếp gọi: “Bay đúng giờ bằng mọi giá”', emoji='📞', npc=DISPATCH, min_day=3, tone='tense', at='between', weight=2,
         text='Trưởng phòng khai thác gọi xuống: tuần này hãng bị chê trễ chuyến nhiều, “đừng để chậm thêm chuyến nào nữa”.',
         options=[dict(id='safety', label='Vâng, nhưng an toàn vẫn đi trước. Trễ thì em báo rõ lý do.', hint='Đúng nguyên tắc',
                       effects=dict(xp=8), good=True, outcome='Chị Vân nghe được, gật đầu: “Nói vậy là đúng.”'),
                  dict(id='yes', label='Dạ, em sẽ cố không để chậm', hint='Dễ nghe',
                       effects=dict(review=[3, 'Cậu cơ phó hứa không trễ chuyến nào. Nghe thì vui, mà chị lo cậu ấy sẽ vội.']), good=False,
                       outcome='Chị Vân nhắc riêng: “Đừng hứa điều mình không được phép hứa.”')],
         default='safety'),
    dict(id='visit', title='Bé Na xin xem buồng lái', emoji='👧', npc=NA, min_day=2, tone='gentle', at='between', weight=2,
         text='Tàu đỗ xong, Bé Na đứng ở cửa buồng lái, mắt sáng rỡ: “Cho con nhìn một chút thôi ạ!”',
         options=[dict(id='show', label='Xin phép chị Vân, cho Na ngồi ghế và chụp một tấm ảnh', hint='Tàu đã đỗ hẳn',
                       effects=dict(review=[5, 'Chú phi công cho con ngồi ghế lái, còn chỉ con đồng hồ độ cao. Lớn lên con sẽ lái máy bay!'], xp=6),
                       good=True, outcome='Na ngồi thẳng lưng, tay đặt lên cần lái, cười không khép miệng.'),
                  dict(id='no', label='Hẹn Na lần sau, hôm nay tổ bay vội', hint='Chuyến sau sắp tới', effects={}, good=None,
                       outcome='Na hơi tiu nghỉu, nhưng vẫn vẫy tay chào.')],
         default='no'),
    dict(id='tired', title='Chị Vân ngáp liên tục', emoji='😴', npc=CAPTAIN, min_day=4, tone='tense', at='between', weight=1,
         text='Chị Vân kể đêm qua con ốm, chị gần như không ngủ. Còn hai chặng nữa.',
         options=[dict(id='say', label='Nói thẳng, đề nghị gọi tổ bay dự bị', hint='Khó mở lời',
                       effects=dict(xp=10), good=True, outcome='Chị Vân im một lúc rồi gật đầu. Tổ bay dự bị lên thay, chị về với con.'),
                  dict(id='coffee', label='Pha ly cà phê đặc, bay tiếp', hint='Không ai phải đổi lịch', effects={}, good=None,
                       outcome='Chặng sau chị Vân chậm một nhịp khi đáp lời đài. Không sao, lần này.'),
                  dict(id='silent', label='Im lặng, chị là cơ trưởng mà', hint='Không phải việc của mình',
                       effects=dict(review=[3, 'Hôm đó tôi rất mệt. Tôi mong cơ phó của mình đã lên tiếng.']), good=False,
                       outcome='Chị Vân bảo sau chuyến: “Lần sau thấy chị không ổn thì phải nói, nghe chưa.”')],
         default='coffee'),
]

SITUATIONS = [
    dict(id='PL-S01', title='Ép cất cánh cho đúng giờ', npc=DISPATCH, tone='tense', min_day=1,
         opening='Anh Lộc chuyển lời trưởng phòng: “Chuyến này chở đoàn khách của đối tác lớn, trễ nữa là mất hợp đồng. Cất cánh đúng giờ nhé!” Côn Đảo đang có giông.',
         swap='Bạn là anh Lộc điều phái, kẹt giữa sếp và tổ bay.',
         facts=[dict(id='wx', title='Bản tin thời tiết', source='Điều phái', text='Giông trên đảo tới 10:20 mới tan. Giờ tới dự kiến là 10:05.'),
                dict(id='fuel', title='Dầu trên tàu', source='Phiếu nạp dầu', text='Tàu mang đủ dầu để bay chờ 20 phút trên đảo.'),
                dict(id='rule', title='Quy định của hãng', source='Sổ tay khai thác', text='Quyết định cất cánh và hạ cánh là của cơ trưởng. Không ai được ép tổ bay bay vào thời tiết nguy hiểm.')],
         options=[dict(id='delay', label='Hoãn 15 phút, báo khách lý do, báo trưởng phòng bằng số liệu thời tiết', requires=['wx', 'rule'], quality='good', stars=5,
                       review='Trễ mười lăm phút nhưng được nói rõ vì sao. Tới nơi trời vừa tạnh, hạ cánh êm ru.',
                       outcome='Tàu tới đảo đúng lúc giông vừa tan. Trưởng phòng đọc bản tin rồi không nói gì thêm.',
                       perspectives=[dict(who='Anh Lộc', emoji='📡', text='Có số liệu trong tay, tôi báo lên sếp dễ hơn nhiều.'),
                                     dict(who='Khách đoàn đối tác', emoji='💼', text='Trễ chút mà được giải thích rõ, tôi thấy hãng làm ăn đàng hoàng.')]),
                  dict(id='hold', label='Cất cánh đúng giờ, tới nơi thì bay chờ cho giông tan', requires=['wx', 'fuel'], quality='ok', stars=4,
                       review='Đi đúng giờ nhưng lượn trên đảo hai chục phút, bụng hơi nôn nao.',
                       outcome='Tàu bay vòng chờ 20 phút rồi hạ cánh an toàn, hơi tốn dầu.',
                       perspectives=[dict(who='Chị Vân', emoji='🧑‍✈️', text='Có dầu chờ thì không sai. Nhưng chờ dưới đất vẫn êm hơn.'),
                                     dict(who='Bà Chín', emoji='👵', text='Lượn mãi, tôi cứ tưởng có chuyện gì.')]),
                  dict(id='push', label='Cất cánh đúng giờ, tới nơi cố hạ cánh cho kịp', quality='bad', stars=1,
                       review='Hạ cánh giữa trời giông, tàu sụt một cái cả khoang hét lên. Không bao giờ bay hãng này nữa.',
                       outcome='Gió đứt làm tàu sụt độ cao sát đường băng. May chị Vân kịp cho bay lại. Cả chuyến phải báo cáo sự cố.',
                       perspectives=[dict(who='Chị Vân', emoji='🧑‍✈️', text='Hợp đồng nào cũng không đáng bằng một mạng người.'),
                                     dict(who='Chị Thu', emoji='💁', text='Cả khoang khách khóc. Tôi phải ngồi với từng người.'),
                                     dict(who='Anh Lộc', emoji='📡', text='Đáng lẽ tôi phải đưa bản tin lên sếp ngay từ đầu.')])],
         lesson='Đúng giờ là lời hứa, an toàn là điều kiện. Có số liệu thì nói bằng số liệu, và nói thật với khách.'),
    dict(id='PL-S02', title='Cơ trưởng không đủ sức', npc=CAPTAIN, tone='tense', min_day=2,
         opening='Chị Vân thức trắng đêm vì con ốm. Chị bảo: “Không sao, chị bay được.” Tay chị hơi run khi cài dây an toàn.',
         swap='Bạn là chị Vân: con ốm, cả đêm không ngủ, sáng vẫn phải ra sân bay.',
         facts=[dict(id='sleep', title='Giấc ngủ đêm qua', source='Chị Vân', text='Chị ngủ chưa được ba tiếng, lúc lên tàu còn ngáp liên tục.'),
                dict(id='reserve', title='Tổ bay dự bị', source='Phòng trực', text='Hôm nay có một cơ trưởng dự bị đang trực, có thể thay trong 20 phút.'),
                dict(id='rule', title='Quy định sức khỏe tổ bay', source='Sổ tay khai thác', text='Ai thấy mình hoặc đồng đội không đủ sức khỏe đều có quyền và có trách nhiệm lên tiếng.')],
         options=[dict(id='speak', label='Nói riêng với chị, đề nghị gọi cơ trưởng dự bị', requires=['sleep', 'reserve'], quality='good', stars=5,
                       review='Em nói nhỏ nhẹ mà chắc chắn. Chị về ngủ một giấc, chiều bay tiếp. Cảm ơn em.',
                       outcome='Chuyến bay trễ 20 phút. Chị Vân về nhà với con, ngày mai quay lại tươi tỉnh.',
                       perspectives=[dict(who='Chị Vân', emoji='🧑‍✈️', text='Chị cứ nghĩ mình chịu được. Em nói đúng.'),
                                     dict(who='Cơ trưởng dự bị', emoji='🧑‍✈️', text='Trực dự bị là để cho những ngày thế này.')]),
                  dict(id='watch', label='Bay cùng, tự mình để mắt mọi thứ gấp đôi', quality='ok', stars=3,
                       review='Chuyến bay ổn, nhưng hai lần chị suýt quên đổi tần số. Em đã phải nhắc.',
                       outcome='Chuyến bay an toàn, nhưng cả hai về tới nơi đều mệt rã rời.',
                       perspectives=[dict(who='Chị Vân', emoji='🧑‍✈️', text='May có em nhắc. Nhưng đáng lẽ chị không nên ngồi đó.'),
                                     dict(who='Chị Thu', emoji='💁', text='Tôi thấy buồng lái im lặng hơn mọi ngày.')]),
                  dict(id='silent', label='Im lặng, chị là cơ trưởng mà', quality='bad', stars=2,
                       review='Không ai lên tiếng. Tôi bay trong tình trạng không nên bay.',
                       outcome='Lúc hạ cánh chị Vân phản ứng chậm, tàu chạm đường băng khá mạnh.',
                       perspectives=[dict(who='Chị Vân', emoji='🧑‍✈️', text='Chị không trách em, nhưng lần sau phải nói.'),
                                     dict(who='Chú Mẫn', emoji='🔧', text='Lại phải kiểm tra càng sau cú chạm mạnh đó.')])],
         lesson='Trong buồng lái, lên tiếng khi đồng đội không ổn là giúp chứ không phải hỗn.'),
    dict(id='PL-S03', title='Hành khách say xỉn đòi lên tàu', npc=PURSER, tone='tense', min_day=2,
         opening='Chị Thu báo: một khách nam say khướt, nói to, đòi lên tàu cùng nhóm bạn. Nhóm bạn năn nỉ: “Anh ấy ngủ một giấc là hết.”',
         swap='Bạn là chị Thu, đứng ở cửa tàu giữa nhóm khách đang to tiếng.',
         facts=[dict(id='state', title='Tình trạng của khách', source='Chị Thu', text='Khách đi loạng choạng, nói lè nhè, vừa làm đổ ly cà phê ở phòng chờ.'),
                dict(id='rule', title='Quyền của cơ trưởng', source='Sổ tay khai thác', text='Tổ bay được từ chối chở khách say xỉn có thể gây mất an toàn cho chuyến bay.'),
                dict(id='ground', title='Nhân viên mặt đất', source='Quầy thủ tục', text='Có thể đổi vé cho khách sang chuyến chiều, khi khách đã tỉnh.')],
         options=[dict(id='offload', label='Từ chối chở chuyến này, nhờ mặt đất đổi sang chuyến chiều', requires=['state', 'ground'], quality='good', stars=5,
                       review='Hôm đó tôi say thật. Tỉnh ra mới thấy xấu hổ. Cảm ơn tổ bay đã đổi vé chứ không bỏ mặc.',
                       outcome='Khách ngủ một giấc ở phòng chờ, bay chuyến chiều, lúc lên tàu còn xin lỗi chị Thu.',
                       perspectives=[dict(who='Chị Thu', emoji='💁', text='Cả khoang được một chuyến bay yên ổn.'),
                                     dict(who='Bạn của khách', emoji='🧑', text='Lúc đầu tôi bực, sau thấy họ làm vậy là đúng.')]),
                  dict(id='back', label='Cho lên, xếp ngồi cuối tàu, dặn chị Thu để ý', quality='ok', stars=3,
                       review='Ông khách say ngồi sau lưng tôi hát suốt chuyến bay. Tiếp viên phải ra nhắc năm lần.',
                       outcome='Chuyến bay ồn ào nhưng không có chuyện gì lớn.',
                       perspectives=[dict(who='Chị Thu', emoji='💁', text='Tôi đứng cạnh hàng ghế cuối cả chuyến, không phục vụ được ai.'),
                                     dict(who='Bà Chín', emoji='👵', text='Tôi sợ cứ quay lại nhìn.')]),
                  dict(id='let', label='Cho lên như thường, nhóm bạn trông anh ấy mà', quality='bad', stars=2,
                       review='Có ông say làm loạn trên tàu, đòi mở cửa sổ. Không biết tổ bay nghĩ gì mà cho lên.',
                       outcome='Giữa chuyến khách nôn thốc nôn tháo rồi gây gổ. Tới nơi công an sân bay lên tàu.',
                       perspectives=[dict(who='Chị Thu', emoji='💁', text='Tôi bị xô ngã khi can.'),
                                     dict(who='Chị Vân', emoji='🧑‍✈️', text='Lẽ ra phải từ chối từ cửa tàu.')])],
         lesson='An toàn cả chuyến bay đứng trước sự tiện cho một người. Từ chối cho khéo và có phương án thay.'),
    dict(id='PL-S04', title='Nhầm độ cao khi nhắc lại', npc=CAPTAIN, tone='gentle', min_day=3,
         opening='Đài cho xuống 5.000 ft, bạn nhắc lại “3.000 ft” và cho tàu xuống. Chị Vân kịp phát hiện, kéo lại. Ngoài hai người, không ai biết.',
         swap='Bạn là chị Vân, người vừa thấy cơ phó của mình nhầm.',
         facts=[dict(id='what', title='Chuyện gì đã xảy ra', source='Máy ghi chuyến bay', text='Tàu xuống thấp hơn lệnh 300 ft trong vài giây rồi được kéo lên.'),
                dict(id='report', title='Báo cáo an toàn tự nguyện', source='Phòng an toàn bay', text='Người tự báo không bị phạt. Cả hãng dùng báo cáo để rút kinh nghiệm.'),
                dict(id='van', title='Chị Vân nói', source='Chị Vân', text='“Chuyện của em, em quyết định. Nhưng chị sẽ hỏi em vì sao nhầm.”')],
         options=[dict(id='report', label='Tự viết báo cáo an toàn, kể rõ vì sao nhầm', requires=['what', 'report'], quality='good', stars=5,
                       review='Em tự báo cáo, lại chỉ ra được vì sao hai con số dễ nghe nhầm. Phòng an toàn đã sửa quy trình nhắc lại.',
                       outcome='Tháng sau, cả hãng đổi cách đọc độ cao cho khỏi nhầm. Tên bạn không bị nêu, chỉ bài học được nêu.',
                       perspectives=[dict(who='Phòng an toàn bay', emoji='🛡️', text='Mỗi báo cáo thật là một tai nạn không xảy ra.'),
                                     dict(who='Chị Vân', emoji='🧑‍✈️', text='Chị thích người dám nói mình sai.')]),
                  dict(id='sorry', label='Chỉ xin lỗi chị Vân, hứa lần sau cẩn thận', quality='ok', stars=3,
                       review='Em biết lỗi là tốt. Nhưng bài học chỉ nằm trong buồng lái này.',
                       outcome='Tuần sau một tổ bay khác nhầm y hệt.',
                       perspectives=[dict(who='Chị Vân', emoji='🧑‍✈️', text='Lỗi của một người có thể là cái bẫy cho người khác.'),
                                     dict(who='Phòng an toàn bay', emoji='🛡️', text='Giá mà chúng tôi biết sớm hơn.')]),
                  dict(id='hide', label='Thôi, không ai biết thì cho qua', quality='bad', stars=2,
                       review='Em im lặng. Chị buồn vì chuyện đó hơn là vì cái lỗi.',
                       outcome='Máy ghi chuyến bay vẫn lưu lại. Phòng an toàn hỏi tới, bạn phải giải trình.',
                       perspectives=[dict(who='Chị Vân', emoji='🧑‍✈️', text='Giấu một lỗi nhỏ là tập giấu lỗi lớn.'),
                                     dict(who='Phòng an toàn bay', emoji='🛡️', text='Tự báo thì không bị phạt. Bị phát hiện thì khác.')])],
         lesson='Trong nghề bay, tự báo lỗi của mình là cách giữ an toàn cho người sau.'),
    dict(id='PL-S05', title='Quay video trong buồng lái', npc=NA, tone='gentle', min_day=2,
         opening='Lúc khách đang lên tàu, Bé Na đứng ở cửa buồng lái: “Chú cho con quay video đăng lên lớp được không ạ? Một chút thôi!”',
         swap='Bạn là Bé Na, lần đầu thấy buồng lái thật.',
         facts=[dict(id='door', title='Cửa buồng lái', source='Sổ tay khai thác', text='Khi khách đang lên tàu và suốt chuyến bay, cửa buồng lái phải đóng.'),
                dict(id='after', title='Sau khi đỗ', source='Chị Vân', text='Tàu đỗ hẳn, tắt máy, cơ trưởng đồng ý thì khách nhỏ được vào xem và chụp ảnh.'),
                dict(id='na', title='Bé Na', source='Mẹ của Na', text='Na mê máy bay, đang làm bài thuyết trình “Một ngày của phi công”.')],
         options=[dict(id='later', label='Hẹn Na sau khi hạ cánh, tàu đỗ hẳn, xin phép chị Vân rồi chụp ảnh', requires=['door', 'after'], quality='good', stars=5,
                       review='Chú hẹn con sau khi hạ cánh, rồi giữ lời thật! Con được ngồi ghế lái chụp ảnh.',
                       outcome='Na chụp tấm ảnh đội mũ cơ phó, dán lên bìa bài thuyết trình.',
                       perspectives=[dict(who='Mẹ của Na', emoji='👩', text='Người ta vừa giữ quy định vừa giữ lời hứa với con tôi.'),
                                     dict(who='Chị Vân', emoji='🧑‍✈️', text='Biết đâu mười năm nữa Na ngồi ghế này thật.')]),
                  dict(id='no', label='“Không được đâu con.” rồi đóng cửa', requires=['door'], quality='ok', stars=3,
                       review='Chú phi công nói không được rồi đóng cửa luôn. Con buồn cả chuyến.',
                       outcome='Đúng quy định, nhưng một cô bé mê máy bay xuống tàu với đôi mắt đỏ hoe.',
                       perspectives=[dict(who='Bé Na', emoji='👧', text='Con chỉ muốn nhìn thôi mà.'),
                                     dict(who='Chị Thu', emoji='💁', text='Giá mà hẹn bé lúc hạ cánh.')]),
                  dict(id='quick', label='Cho Na vào quay nhanh một phút lúc khách đang lên', quality='bad', stars=2,
                       review='Có em bé chạy vào buồng lái quay phim lúc khách đang lên tàu. Vậy mà cũng được à?',
                       outcome='Đoạn video lộ cả bảng mã cửa buồng lái. Hãng phải đổi mã và nhắc nhở tổ bay.',
                       perspectives=[dict(who='An ninh hãng', emoji='🛡️', text='Mã cửa buồng lái không bao giờ được lên mạng.'),
                                     dict(who='Mẹ của Na', emoji='👩', text='Tôi không ngờ chuyện nhỏ vậy mà phiền tới thế.')])],
         lesson='Giữ quy định buồng lái và vẫn giữ được niềm vui cho người khác: hẹn đúng lúc, đúng chỗ.'),
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
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Tổ bay'


def _kg(n: int) -> str:
    return f'{n:,}'.replace(',', '.') + ' kg'


def _where(t: dict) -> str:
    """Where this hop ends: the destination, the alternate or the airfield of a medical diversion."""
    return t.get('at') or t['needs']['leg']['to']


# ================================================================ tasks
def daily_task_count(day: int) -> int:
    """Dispatch sets the roster once per day; day one keeps all three lessons."""
    return 3 if day == 1 else kit.rng(ID, 'roster', day).randint(2, 5)


def _flight_bonus(t: dict) -> int:
    """A separate seed leaves every existing route, defect and weather roll intact."""
    return kit.rng(ID, 'flight-bonus', t['id']).randint(8, 20) + (2 if t['needs']['full'] else 0)


def on_task(s: dict, c: dict, t: dict) -> None:
    # Only newly dispatched flights reach this hook. Never rewrite legacy saves.
    t.setdefault('flight_bonus', _flight_bonus(t))


def _kind(day: int, slot: int, mod: str) -> str:
    if day == 1:
        return {2: 'tech'}.get(slot, 'flight')
    if slot == 0:
        return 'fog' if mod == 'fog' else 'flight'
    deck = ['flight', 'flight', 'storm', 'tech', 'medical', 'flight']
    if mod == 'storms':
        deck += ['storm', 'storm']
    kit.rng(ID, 'deck', day).shuffle(deck)
    return deck[(slot - 1) % len(deck)]


def _gate(r, gid: str, bad: str | None = None) -> dict:
    """One approach gate: three readings with their limits (lists only: the task is compared after a JSON round trip)."""
    if gid == 'g1':
        spd = 115 + r.randint(-3, 3)
        dots = r.choice((0, 0, 1))
        sink = r.choice((650, 700, 750, 800))
        if bad == 'fast':
            spd = 131 + r.randint(0, 5)
        elif bad == 'high':
            dots = 2
        elif bad == 'sink':
            sink = 1400 + 100 * r.randint(0, 3)
        rows = [['Tốc độ', f'{spd} kt', '110–120', 110 <= spd <= 120],
                ['Đường trượt', f'lệch {dots} chấm', 'tối đa 1', dots <= 1],
                ['Tốc độ xuống', f'{sink:,} ft/phút'.replace(',', '.'), 'tối đa 1.000', sink <= 1000]]
        name = 'Cổng 1.000 ft'
    else:
        rwy = bad != 'no_rwy'
        wind = 32 + r.randint(0, 3) if bad == 'gust' else r.choice((6, 9, 12, 15))
        spd = 114 + r.randint(-3, 4)
        rows = [['Đường băng', 'Thấy rõ đèn' if rwy else 'Chưa thấy', 'phải thấy', rwy],
                ['Gió ngang', f'{wind} kt', 'tối đa 28', wind <= 28],
                ['Tốc độ', f'{spd} kt', '110–120', True]]
        name = 'Độ cao quyết định 200 ft'
    return dict(id=gid, name=name, rows=rows, stable=all(x[3] for x in rows), bad=bad)


def _event(r, kind: str, day: int, leg: dict) -> dict | None:
    if kind == 'medical':
        near = leg['alt']
        close = r.random() < 0.5
        return dict(kind='medical', seat=f'{r.randint(3, 16)}{r.choice("ABCD")}', left=12 if close else 35, near=near, near_min=15,
                    want='continue' if close else 'divert')
    if day == 1:
        return None
    if kind == 'storm':
        return dict(kind='cell') if r.random() < 0.5 else None
    return dict(kind='turb') if r.random() < (0.35 if kind == 'flight' else 0.25) else None


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    kind = _kind(day, slot, mod)
    leg = air.leg(day, slot)
    r = kit.rng(ID, day, slot)
    if kind == 'storm':
        wx = 'storm'
    elif kind == 'fog':
        wx = 'fog'
    elif day == 1:
        wx = 'cloud' if slot == 1 else 'clear'
    else:
        pool = ['clear', 'clear', 'cloud'] + (['wind', 'wind'] if mod == 'wind' and leg['coast'] else ['wind'] if day >= 3 and leg['coast'] else [])
        wx = r.choice(pool)
    busy = mod == 'busy' or r.random() < 0.15
    pax = r.randint(FULL_PAX, 68) if busy else r.randint(38, 60)
    # The walk-around: day one teaches the pitot cover; a tech hop always has the engineer's kind.
    if day == 1 and slot == 0:
        defect = 'cover'
    elif kind == 'tech':
        defect = 'tyre' if day == 1 else r.choice(('tyre', 'oil'))
    else:
        defect = r.choice(('cover', 'latch')) if r.random() < (0.4 if kind == 'flight' else 0.25) else None
    # The first approach: at most one gate out of limits; the second approach is always stable.
    bad1 = bad2 = None
    if day == 1:
        bad1 = 'fast' if slot == 1 else None
    elif wx == 'wind' and r.random() < 0.6:
        bad2 = 'gust'
    elif wx == 'cloud' and r.random() < 0.2:
        bad2 = 'no_rwy'
    elif kind != 'storm' and r.random() < 0.12:
        bad1 = r.choice(('fast', 'high', 'sink'))
    gates = [[_gate(r, 'g1', bad1), _gate(r, 'g2', bad2)], [_gate(r, 'g1'), _gate(r, 'g2')]]
    plan = leg['trip'] + leg['alt_fuel'] + RESERVE
    fuel = dict(trip=leg['trip'], alt=leg['alt_fuel'], reserve=RESERVE, hold=HOLD, plan=plan, need=plan + HOLD if wx == 'storm' else plan,
                options=[leg['trip'] + RESERVE, plan, plan + HOLD, TANKS])
    needs = dict(leg=leg, pax=pax, full=pax >= FULL_PAX, wx=wx, fuel=fuel, defect=defect, event=_event(r, kind, day, leg), gates=gates)
    if kind == 'medical':
        npc = PURSER
    elif kind in ('tech', 'fog'):
        npc = KIET
    elif kind == 'flight' and day >= 2:
        npc = (CAPTAIN, CAPTAIN, GRANNY, NA)[r.randrange(4)]
    else:
        npc = CAPTAIN
    title = {'flight': f'Chuyến {leg["code"]} đi {leg["to"]}', 'storm': f'{leg["code"]} đi {leg["to"]}: giông lúc tới',
             'fog': f'{leg["code"]} đi {leg["to"]}: sương sớm', 'tech': f'{leg["code"]} đi {leg["to"]}: kiểm tra kỹ thuật',
             'medical': f'Chuyến {leg["code"]} đi {leg["to"]}'}[kind]
    opening = {CAPTAIN: f'Chị Vân: “Chặng {leg["to"]} nhé em. Nhận bản tin, tính dầu, rồi mình đi một vòng quanh tàu.”',
               KIET: 'Anh Kiệt nhìn đồng hồ lần thứ ba: “Chuyến này có đi đúng giờ không đấy?”',
               PURSER: f'Chị Thu ló vào buồng lái: “{pax} khách, có vài cụ lớn tuổi. Chị báo trước để em biết.”',
               GRANNY: 'Bà Chín nắm chặt quai túi xoài: “Máy bay có rung không cậu?”',
               NA: 'Bé Na áp mặt vào cửa kính phòng chờ, chỉ vào chiếc Cò Trắng: “Tàu của chú đấy ạ?”'}[npc]
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind=kind, needs=needs, gen=GEN, stage='brief', fuel=None, fog=None,
                         checked=[], found=None, handled=None, switches=[], pa=None, delay=0, decision=None, arrive=None, at=None,
                         ap=0, gate=0, arounds=0, gates_log=[], extra=False, reason=None, air_late=0, story=None)


FIXED = ('needs',)


# ================================================================ the career's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, flights=0, minutes=0, delays=0, arounds=0, diverts=0, holds=0, ontime=0)


def initial() -> dict:
    return dict(v=1, intro=False, logbook=dict(flights=0, minutes=0, landings=0, arounds=0, diverts=0, holds=0, delays=0, safe=0,
                                               ontime=0, fuel_ok=0),
                log=[], regulars={}, arc=dict(seen=[], due=None), today=_fresh_today(0), desk=kit.desk_initial(),
                odd=ao.initial(), sky=None)


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k, v in base['logbook'].items():
        d['logbook'].setdefault(k, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    ao.ensure(d)
    return d


# The words of the encounters (air_odd): who to bring in, the office, the rank lost on a demotion.
CFG = dict(crew='Báo cơ trưởng Vân', company='Báo phòng an toàn', union='Nhờ công đoàn', office='Điều phái',
           demoted='cơ phó dự bị', title='cơ phó')


def _pressure(c: dict, d: dict) -> int:
    """How hard the airline leans on its crew today: the season, and a player who snapped at the office."""
    marks = d['odd']['marks']
    return {'busy': 2, 'storms': 1, 'wind': 1}.get(mod_of(c['day'])['id'], 0) + ('strained' in marks) + ('kpi_black' in marks)


# ================================================================ the actions
FREE = ('pl_intro', 'pl_arc', 'pl_rest')
NO_TICK = ('pl_intro', 'pl_arc', 'pl_fuel', 'pl_check', 'pl_switch', 'pl_pa', 'pl_gate', 'pl_desk', 'pl_odd', 'pl_sky', 'pl_rest')
PHYSICAL = ('pl_takeoff', 'pl_park')
GROUNDED = ('pl_fuel', 'pl_fog', 'pl_check', 'pl_defect', 'pl_switch', 'pl_pa', 'pl_takeoff')   # a crew stood down starts no hop


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'pl_intro':
        d['intro'] = True
        return dict(message='Vào ca thôi! Chị Vân đang chờ ở phòng điều phái.')
    if name == 'pl_arc':
        return _arc_seen(d)
    odd = d['odd']
    if name == 'pl_rest':
        return ao.rest(s, c, odd, p, _pressure(c, d), CFG)
    desk = d['desk']
    if name == 'pl_desk':
        result = kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
        _odd_tick(s, c, d, result)
        return result
    if name == 'pl_odd':
        result = ao.reply(s, c, ID, odd, ODD, p, CFG, _pressure(c, d))
        if odd['ev'] is None:
            _odd_tick(s, c, d, result)
        return result
    kit.desk_block(desk, 'Có chuyện ở sân bay, quyết xong rồi làm tiếp nhé.')
    ao.block(odd, 'Có người đang chờ bạn trả lời, xong rồi làm tiếp nhé.')
    kit.need(not (ao.grounded(c, odd) and name in GROUNDED), 'Bạn đang tạm đình chỉ bay hết hôm nay. Tan ca, mai lên phòng an toàn trình bày.', 'grounded')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có trong buồng lái.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    _arc_tick(c, d)
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
        return
    _odd_tick(s, c, d, result)


def _odd_tick(s: dict, c: dict, d: dict, result: dict) -> None:
    """Someone around the job turns up when today's plan says so (never over an open desk surprise)."""
    x = ao.tick(s, c, ID, d['odd'], ODD, busy=d['desk']['ev'] is not None)
    if x:
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: trả lời giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, stage: str | tuple | None = None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tổ bay.')
    kit.need(t['known'], 'Nhận bản tin bay trước đã nhé.')
    if stage:
        kit.need(t['stage'] in ((stage,) if isinstance(stage, str) else stage), 'Chưa tới bước này của chuyến bay.')
    return t


def _refuse(t: dict, code: str, sev: int, text: str, note: str, message: str) -> dict:
    """A mistake that the captain stops: counted on the task, nothing else changes."""
    t['mistakes'] += 1
    cq.slip(t, code, sev, text, note)
    return dict(message=message, correct=False)


# ---------------------------------------------------------------- brief: fuel and fog
def _fuel(s, c, d, p):
    t = _task(c, p, 'brief')
    kit.need(t['fuel'] is None, 'Dầu đã nạp rồi.')
    f, n = t['needs']['fuel'], t['needs']
    kg = kit.one_of(p.get('kg'), f['options'], 'Chọn một mức dầu trong phiếu.')
    if kg < f['plan']:
        return _refuse(t, 'fuel_low', 2, 'Cơ phó định nạp thiếu dầu bay đi sân bay dự bị.', 'nạp thiếu dầu',
                       f'✋ Chị Vân lắc đầu: “Thiếu dầu đi {n["leg"]["alt"]}. Dầu chặng + dầu dự bị + 30 phút dự phòng. Tính lại nhé.”')
    if kg == TANKS and n['full']:
        return _refuse(t, 'overweight', 1, 'Tàu kín khách mà định đổ đầy bình, quá trọng lượng cất cánh.', 'đổ dầu quá tải',
                       f'✋ Anh Lộc: “{n["pax"]} khách với đầy bình là quá trọng lượng cất cánh. Chọn lại mức dầu!”')
    t['fuel'] = kg
    kit.start_work(t)
    msg = f'⛽ Xe dầu nạp {_kg(kg)}.'
    if kg == TANKS:
        t['mistakes'] += 1
        cq.slip(t, 'heavy', 1, 'Chặng ngắn mà đổ đầy bình, tàu nặng và tốn dầu.', 'đổ dầu thừa nhiều')
        msg += ' Anh Lộc nhăn mặt: “Đầy bình cho chặng ngắn, tốn lắm đấy.”'
    elif kg < f['need']:
        t['mistakes'] += 1
        cq.slip(t, 'no_hold', 1, 'Dự báo giông lúc tới mà không mang dầu chờ.', 'thiếu dầu chờ')
        msg += ' Chị Vân: “Giông lúc tới mà không có dầu chờ, tới nơi mình chỉ còn cách bay đi sân bay dự bị.”'
    elif kg > f['need']:
        t['extra'] = True
        msg += ' Dư một chút dầu chờ: yên tâm, hơi tốn.'
    else:
        msg += ' Chị Vân gật đầu: “Vừa đủ, có dự phòng.”'
    if n['wx'] != 'fog':
        t['stage'] = 'walk'
        msg += ' Giờ đi một vòng quanh tàu.'
    return dict(message=msg)


def _fog(s, c, d, p):
    t = _task(c, p, 'brief')
    kit.need(t['needs']['wx'] == 'fog', 'Hôm nay không có sương.')
    kit.need(t['fuel'] is not None, 'Tính dầu trước đã.')
    kit.need(t['fog'] is None, 'Đã quyết rồi.')
    wait = p.get('wait')
    kit.need(type(wait) is bool, 'Chờ hay đi?')
    t['stage'] = 'walk'
    if wait:
        t['fog'] = 'wait'
        _late(c, d, t, DELAY['fog'], f'chờ sương tan ở {t["needs"]["leg"]["to"]}')
        return dict(message=f'🌫️ Lùi giờ cất cánh {DELAY["fog"]} phút, chờ sương tan. Nhớ thông báo cho khách trước khi cất cánh.')
    t['fog'] = 'go'
    t['mistakes'] += 1
    cq.slip(t, 'rush', 1, 'Đích còn sương dưới mức tối thiểu mà vẫn cất cánh đúng giờ.', 'vội cất cánh khi đích còn sương')
    return dict(message='🛫 Giữ giờ cất cánh. Chị Vân: “Tới nơi mà sương chưa tan thì phải bay chờ hoặc đi sân bay dự bị đấy.”')


def _late(c: dict, d: dict, t: dict, minutes: int, reason: str) -> None:
    """Minutes late: on the ground before take-off (the passengers must be told why) or in the air."""
    if t['stage'] in ('brief', 'walk', 'start'):
        t['delay'] = min(600, t['delay'] + minutes)
        t['reason'] = reason[:120]
    else:
        t['air_late'] = min(600, t['air_late'] + minutes)
    d['today']['delays'] += minutes


# ---------------------------------------------------------------- the walk-around
def _check(s, c, d, p):
    t = _task(c, p, 'walk')
    pid = kit.one_of(p.get('point'), POINT, 'Điểm kiểm tra không có trên tàu.')
    kit.need(pid not in t['checked'], 'Điểm này kiểm rồi.')
    t['checked'].append(pid)
    kit.start_work(t)
    x = POINT[pid]
    df = t['needs']['defect']
    if df and DEFECTS[df]['point'] == pid:
        t['found'] = df
        return dict(message=f'⚠️ {x["emoji"]} {DEFECTS[df]["text"]} Xử lý trước khi bay.')
    msg = f'{x["emoji"]} {x["ok"]}'
    return _walk_done(t, msg)


def _walk_done(t: dict, msg: str) -> dict:
    if len(t['checked']) == len(POINTS) and (not t['found'] or t['handled']):
        t['stage'] = 'start'
        msg += ' ✅ Xong vòng quanh tàu. Lên buồng lái đọc checklist.'
    return dict(message=msg)


def _defect(s, c, d, p):
    t = _task(c, p, 'walk')
    kit.need(t['found'] and not t['handled'], 'Không có gì cần xử lý.')
    how = kit.one_of(p.get('how'), ('fix', 'report', 'ignore'), 'Chọn cách xử lý.')
    x = DEFECTS[t['found']]
    if how == 'fix':
        kit.need(x['own'], 'Việc này phải để thợ máy có chứng chỉ làm. Gọi chú Mẫn nhé.')
        t['handled'] = 'fix'
        return _walk_done(t, f'🔧 {x["fix"]}')
    if how == 'report':
        t['handled'] = 'report'
        if x['own']:
            _late(c, d, t, DELAY['recheck'], 'chờ thợ máy kiểm tra lại')
            return _walk_done(t, f'🔧 Chú Mẫn chạy ra, cười: “Cái này cháu tự làm được mà.” {x["fix"]}')
        _late(c, d, t, DELAY['tech'], 'thợ máy kiểm tra lại tàu')
        return _walk_done(t, f'🔧 Chú Mẫn: “May mà cháu thấy.” {x["fix"]} Chậm {DELAY["tech"]} phút: nhớ thông báo cho khách.')
    t['handled'] = 'caught'
    t['mistakes'] += 1
    cq.slip(t, 'ignored_' + t['found'], 3, f'Thấy lỗi ở tàu mà định bỏ qua cho kịp giờ. {x["danger"]}', 'bỏ qua lỗi khi kiểm tra tàu', safety=True)
    _late(c, d, t, DELAY['caught'] if x['own'] else DELAY['tech'], 'cơ trưởng cho kiểm tra lại tàu')
    return _walk_done(t, f'✋ Chị Vân đi kiểm lại, thấy ngay: “{x["danger"]} Không bao giờ bỏ qua.” {x["fix"]}')


# ---------------------------------------------------------------- checklist, announcement, take-off
def _switch(s, c, d, p):
    t = _task(c, p, 'start')
    sid = kit.one_of(p.get('id'), ORDER, 'Công tắc này không có trong checklist.')
    kit.need(sid not in t['switches'], 'Mục này đã xong.')
    want = ORDER[len(t['switches'])]
    x = next(r for r in CHECKLIST if r['id'] == want)
    if sid != want:
        return _refuse(t, 'order', 1, 'Checklist làm lộn thứ tự, cơ trưởng phải đọc lại từ đầu.', 'làm checklist sai thứ tự',
                       f'✋ Chị Vân: “Checklist đang ở dòng {x["name"]}. Đọc theo thẻ, từng dòng một.”')
    t['switches'].append(sid)
    left = len(ORDER) - len(t['switches'])
    return dict(message=f'{x["emoji"]} {x["name"]}: {x["state"]}.' + ('' if left else ' ✅ Checklist xong.'))


def _pa(s, c, d, p):
    t = _task(c, p, 'start')
    kit.need(t['delay'] > 0, 'Chuyến bay đúng giờ, chưa cần thông báo chậm.')
    kit.need(t['pa'] is None, 'Đã thông báo rồi.')
    opt = kit.one_of(p.get('option'), PA_IDS, 'Chọn một câu thông báo.')
    t['pa'] = opt
    n = t['needs']['leg']
    if opt == 'clear':
        return dict(message=f'📢 “Kính thưa quý khách, chuyến {n["code"]} đi {n["to"]} chậm khoảng {t["delay"]} phút vì {t.get("reason", "lý do an toàn")}. '
                            'An toàn là trên hết. Tổ bay xin lỗi và sẽ báo lại ngay khi sẵn sàng.” Khoang khách gật gù.')
    t['mistakes'] += 1
    if opt == 'vague':
        cq.slip(t, 'vague', 1, 'Thông báo chậm chuyến mà không nói vì sao, chậm bao lâu.', 'thông báo mập mờ')
        return dict(message='📢 “Vì lý do khách quan, chuyến bay tạm hoãn.” Vài khách lắc đầu, hỏi nhau chậm bao lâu.')
    cq.slip(t, 'untrue', 2, 'Tổ bay bảo sắp cất cánh mà chờ mãi không đi.', 'thông báo không đúng sự thật')
    return dict(message='📢 “Tàu sắp cất cánh rồi.” Mười phút sau vẫn chưa đi, khoang khách bắt đầu xì xào.')


def _takeoff_rules(t: dict, need=kit.need) -> None:
    """What pl_takeoff refuses (public_task: can.pl_takeoff, the "Cất cánh" button says why before it is pressed)."""
    need(len(t['switches']) == len(ORDER), 'Làm xong checklist trước khi cất cánh.')
    need(not t['delay'] or t['pa'], 'Chuyến bay chậm: thông báo cho khách trước đã.')


def _takeoff(s, c, d, p):
    t = _task(c, p, 'start')
    _takeoff_rules(t)
    if t['delay']:
        t['patience'] = max(25, t.get('patience', 100) - {'clear': 5, 'vague': 15, 'hide': 25}[t['pa']])
    ev = t['needs']['event']
    t['stage'] = 'cruise' if ev else 'approach'
    n = t['needs']['leg']
    msg = f'🛫 Cất cánh! {n["emoji"]} Hướng {n["to"]}, {n["minutes"]} phút bay.'
    if ev:
        x = EVENTS[ev['kind']]
        msg += f' {x["emoji"]} {x["title"]}!'
    sky = _sky_roll(c, d, t)
    if sky:
        msg += f' {SKY[sky["kind"]]["emoji"]} Đài báo {SKY[sky["kind"]]["name"].lower()} ở {n["to"]}.'
    return dict(message=msg)


# ---------------------------------------------------------------- on the way
def _event_text(t: dict) -> str:
    ev = t['needs']['event']
    if ev['kind'] == 'medical':
        return (f'Chị Thu gọi vào: khách ghế {ev["seat"]} đau ngực, vã mồ hôi. Còn {ev["left"]} phút nữa tới {t["needs"]["leg"]["to"]}; '
                f'sân bay {ev["near"]} cách {ev["near_min"]} phút, có bệnh viện.')
    return EVENTS[ev['kind']]['text']


def _decide(s, c, d, p):
    t = _task(c, p, 'cruise')
    ev = t['needs']['event']
    x = EVENTS[ev['kind']]
    opt = kit.one_of(p.get('option'), [o['id'] for o in x['options']], 'Chọn một cách xử lý.')
    t['decision'] = opt
    t['stage'] = 'approach'
    if ev['kind'] == 'medical':
        if opt == 'wait':
            t['mistakes'] += 1
            cq.slip(t, 'med_wait', 2, 'Khách đau ngực mà tổ bay chờ xem thêm mười lăm phút.', 'chần chừ khi khách đau ngực')
            return dict(message='⏳ Mười lăm phút sau khách vẫn đau. Chị Vân quyết: bay nhanh nhất tới chỗ có bệnh viện.', correct=False)
        if opt == 'continue' and ev['want'] == 'divert':
            t['mistakes'] += 1
            cq.slip(t, 'med_far', 3, f'Khách đau ngực còn {ev["left"]} phút bay mà tổ bay không chuyển hướng xuống {ev["near"]}.',
                    'không chuyển hướng khi khách nguy kịch', safety=True)
            return dict(message=f'🩺 Bay tiếp {ev["left"]} phút. Khách được đưa đi cấp cứu ngay khi tới nơi, nhưng bác sĩ bảo đến sớm hơn thì tốt hơn.',
                        correct=False)
        if opt == 'divert':
            t['at'] = ev['near']
            t['ap'] = 1
            d['today']['diverts'] += 1
            return dict(message=f'🩺 Chuyển hướng xuống {ev["near"]}. Chị Thu báo khách: xe cấp cứu đã chờ sẵn dưới đường băng.')
        return dict(message=f'🩺 Bay tiếp, còn {ev["left"]} phút. Mặt đất báo xe cấp cứu sẽ chờ sẵn ở chân cầu thang.')
    grade = next(o['grade'] for o in x['options'] if o['id'] == opt)
    if grade == 'good':
        return dict(message={'belts': '🔔 Đèn thắt dây bật. Chị Thu kịp cất bình nước nóng. Rung một chút rồi êm.',
                             'climb': '⬆️ Lên cao thêm 2.000 ft, đèn thắt dây bật. Tàu êm như ru.',
                             'deviate': '↪️ Vòng tránh đám giông. Mây đen trôi qua bên cánh trái.'}[opt])
    t['mistakes'] += 1
    if opt == 'through':
        cq.slip(t, 'cell', 3, 'Tổ bay cho tàu bay xuyên đám mây giông, cả khoang bị quăng quật.', 'bay xuyên mây giông', safety=True)
        return dict(message='⛈️ Tàu lao vào đám giông: rung dữ dội, mưa đá lộp độp trên kính. Một phút dài như một giờ.', correct=False)
    if opt == 'over':
        cq.slip(t, 'cell_over', 2, 'Tàu cánh quạt cố leo vượt đỉnh mây giông, không leo nổi mà vẫn bị rung.', 'leo vượt mây giông')
        return dict(message='⛰️ Tàu cánh quạt không leo nổi tới đỉnh đám giông. Cuối cùng vẫn phải vòng tránh, rung một trận.', correct=False)
    cq.slip(t, 'turb', 2, 'Rung lắc mạnh mà không bật đèn thắt dây, cà phê đổ lên áo khách.', 'không báo trước vùng rung lắc')
    return dict(message='〰️ Tàu rung mạnh. Một ly cà phê đổ lên áo khách, chị Thu suýt ngã.', correct=False)


# ---------------------------------------------------------------- arrival and the approach
def _arrival_problem(t: dict) -> str | None:
    """Weather over the field when the hop gets there (before any decision)."""
    if t['at'] or t['arrive']:
        return None
    wx = t['needs']['wx']
    if wx == 'storm' or (wx == 'fog' and t['fog'] == 'go'):
        return wx
    return None


def _arrive(s, c, d, p):
    t = _task(c, p, 'approach')
    wx = _arrival_problem(t)
    kit.need(wx, 'Trời ở đích đang tốt, cứ tiếp cận.')
    how = kit.one_of(p.get('how'), ARRIVE, 'Chọn: bay chờ, đi sân bay dự bị hay hạ cánh.')
    n = t['needs']
    if how == 'hold':
        kit.need(t['fuel'] >= n['fuel']['plan'] + HOLD, f'Không đủ dầu để bay chờ: dầu chờ chưa nạp từ đầu. Bay đi {n["leg"]["alt"]} thôi.')
        t['arrive'] = 'hold'
        d['today']['holds'] += 1
        _late(c, d, t, DELAY['hold'], 'bay chờ thời tiết')
        return dict(message=f'🔄 Bay vòng chờ {DELAY["hold"]} phút. {"Giông" if wx == "storm" else "Sương"} tan dần, đèn đường băng hiện ra.')
    if how == 'divert':
        t['arrive'] = 'divert'
        t['at'] = n['leg']['alt']
        t['ap'] = 1
        d['today']['diverts'] += 1
        _late(c, d, t, DELAY['divert'], 'thời tiết xấu ở sân bay đến')
        return dict(message=f'↪️ Bay đi sân bay dự bị {n["leg"]["alt"]}. Chị Vân: “Quyết định đúng. Khách về trễ còn hơn không về.”')
    t['arrive'] = 'land'
    t['mistakes'] += 1
    cq.slip(t, 'land_' + wx, 3, 'Tổ bay cố hạ cánh khi giông còn trên sân bay.' if wx == 'storm' else 'Tổ bay cố hạ cánh khi sương còn dày dưới mức tối thiểu.',
            'cố hạ cánh trong thời tiết xấu', safety=True)
    return dict(message='⚠️ Cố tiếp cận ngay. Gió giật làm tàu chao đảo, chị Vân nắm chặt cần lái.', correct=False)


def _current_gate(t: dict) -> dict:
    return t['needs']['gates'][t['ap']][t['gate']]


# ✈️ Tự bay (public/js/careers/pilot_fly.js): the player flies the approach in the cockpit view and the page sends how
# the gate was flown, `flown: {stable, touch}`. Read loosely: anything else reads as no field, and a page without it
# (⏩ Bay nhanh, an older page) has the gate judged on its rolled readings, as before. The weather at the gate (the
# runway still in cloud at 200 ft, a crosswind over the limit) stays the server's, however well it was flown.
WEATHER = ('no_rwy', 'gust')
TOUCH = ('soft', 'firm', 'long')
LANDED = {'firm': '🛬 Bánh chạm hơi mạnh ở {where}, tàu vẫn chạy thẳng tim đường băng. Chị Vân: “Ghìm mũi thêm chút nữa là êm.”',
          'long': '🛬 Chạm bánh hơi xa ở {where}, phanh vừa kịp. Chị Vân: “Lần sau chạm sớm hơn chút nhé.”'}


def _flown(p: dict) -> dict | None:
    f = p.get('flown')
    if not isinstance(f, dict) or type(f.get('stable')) is not bool:
        return None
    return dict(stable=f['stable'], touch=f.get('touch') if f.get('touch') in TOUCH else None)


def _stable(g: dict, fl: dict | None) -> bool:
    """Whether the gate counts as stable: as rolled, or as flown (the gate's weather still counts)."""
    return g['stable'] if fl is None else fl['stable'] and g['bad'] not in WEATHER


def _gate_ready(t: dict) -> None:
    kit.need(not _arrival_problem(t), 'Quyết trước: bay chờ, đi sân bay dự bị hay hạ cánh.')
    kit.need(t['gate'] < 2, 'Đã qua hết các cổng.')


def _continue(s, c, d, p):
    t = _task(c, p, 'approach')
    _gate_ready(t)
    _sky_ready(d, t)
    g = _current_gate(t)
    fl = _flown(p)
    t['gates_log'] = (t['gates_log'] + [dict(ap=t['ap'], g=g['id'], go='land')])[-8:]
    msg = ''
    if not _stable(g, fl):
        t['mistakes'] += 1
        if g['bad'] == 'no_rwy':
            cq.slip(t, 'minima', 3, 'Tới độ cao quyết định chưa thấy đường băng mà vẫn cố xuống.', 'xuống dưới mức tối thiểu', safety=True)
            msg = '⚠️ Chưa thấy đường băng mà vẫn xuống. May mây hở đúng lúc. Chị Vân im lặng rất lâu.'
        elif g['bad'] == 'gust':
            cq.slip(t, 'crosswind', 2, 'Gió ngang giật quá giới hạn mà vẫn hạ cánh, tàu bị đẩy lệch khỏi tim đường băng.', 'hạ cánh khi gió quá giới hạn')
            msg = '💨 Gió giật đẩy tàu lệch tim đường băng. Bánh chạm mạnh một bên.'
        else:
            cq.slip(t, 'unstable', 2, 'Tiếp cận chưa ổn định mà vẫn hạ cánh, tàu nảy lên hai lần.', 'hạ cánh khi chưa ổn định')
            msg = '💥 Chưa ổn định mà vẫn xuống: tàu chạm mạnh, nảy lên một lần. Khoang khách ồ lên.'
    t['gate'] += 1
    if t['gate'] >= 2:
        t['stage'] = 'landed'
        if not msg and t['arrive'] == 'land':
            msg = f'🛬 Hạ cánh ở {_where(t)} giữa gió giật, tàu chao mạnh. Khoang khách im phăng phắc.'
        touch = LANDED.get((fl or {}).get('touch'), '🛬 Chạm bánh êm ru ở {where}. Khoang khách vỗ tay.')   # a remark, never a slip
        out = dict(message=(msg or touch.format(where=_where(t))) + ' Lăn vào bến, tắt máy nhé.')
    else:
        out = dict(message=msg or f'✅ {g["name"]}: ổn định. Tiếp tục xuống.')
    if msg:
        out['correct'] = False
    return out


def _around_rules(t: dict, need=kit.need) -> None:
    """What pl_around refuses at a gate: at the alternate after the last go-around there is fuel for this approach
    only (public_task: can.pl_around, "Bay lại" dimmed with the reason)."""
    need(t['arounds'] < MAX_AROUNDS or not t['at'], 'Dầu chỉ còn đủ cho lần tiếp cận này ở sân bay dự bị: hạ cánh thôi.')


def _around(s, c, d, p):
    t = _task(c, p, 'approach')
    _gate_ready(t)
    _sky_ready(d, t)
    g = _current_gate(t)
    _around_rules(t)
    t['gates_log'] = (t['gates_log'] + [dict(ap=t['ap'], g=g['id'], go='around')])[-8:]
    d['today']['arounds'] += 1
    if t['arounds'] >= MAX_AROUNDS:
        # Two missed approaches: the book says the alternate.
        t['at'] = t['needs']['leg']['alt'] if not t['at'] else t['at']
        t.update(ap=1, gate=0)
        _late(c, d, t, DELAY['divert'], 'thời tiết xấu ở sân bay đến')
        d['today']['diverts'] += 1
        return dict(message=f'↗️ Bay lại lần thứ ba thì không tiếp cận nữa: đi sân bay dự bị {t["at"]}.')
    t['arounds'] += 1
    t.update(ap=1, gate=0)
    _late(c, d, t, DELAY['around'], 'bay lại để tiếp cận an toàn')
    if _stable(g, _flown(p)):
        cq.slip(t, 'needless', 1, 'Tiếp cận đã ổn định mà vẫn bay lại, khách chờ thêm mười phút.', 'bay lại khi đã ổn định')
        return dict(message='↗️ Bay lại. Chị Vân: “Cẩn thận là tốt, nhưng số liệu đã ổn định rồi. Tin vào con số nhé.”')
    return dict(message='↗️ Bay lại! Chị Vân: “Quyết định đúng. Không ổn định thì bay lại, không ai chê cả.” Vòng lại tiếp cận lần nữa.',
                celebrate=True)


# ---------------------------------------------------------------- parking and the debrief
def _park(s, c, d, p):
    t = _task(c, p, 'landed')
    n = t['needs']['leg']
    pts = cq.points(t)
    full = 0 if cq.safety(t) else max(0, t.get('flight_bonus', BONUS) - 3 * pts)
    reward = ao.bonus(d['odd'], full)
    t['stage'] = 'done'
    if d['sky'] and d['sky']['task'] == t['id']:
        d['sky'] = None
    lb = d['logbook']
    lb['flights'] += 1
    lb['landings'] += 1
    lb['minutes'] += n['minutes']
    lb['arounds'] += t['arounds']
    lb['delays'] += t['delay'] + t['air_late']
    lb['holds'] += t['arrive'] == 'hold'
    lb['diverts'] += bool(t['at'])
    lb['safe'] += not cq.safety(t)
    ontime = not (t['delay'] or t['air_late'])
    lb['ontime'] += ontime
    lb['fuel_ok'] += t['fuel'] == t['needs']['fuel']['need']
    for k in lb:
        lb[k] = min(10 ** 7, lb[k])
    d['today']['flights'] += 1
    d['today']['minutes'] += n['minutes']
    d['today']['ontime'] += ontime
    d['log'] = ar.last(d['log'] + [dict(day=c['day'], code=n['code'], to=_where(t), minutes=n['minutes'], late=t['delay'] + t['air_late'],
                                        arounds=t['arounds'], ok=not cq.slips(t))], LOG_MAX, 'pilot.log', c)
    story = ''
    i = _npc_index(t)
    if i in REG_STORY:
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        story = REG_STORY[i][min(r['visits'], len(REG_STORY[i])) - 1]
        t['story'] = story
    late = t['delay'] + t['air_late']
    line = f'Chuyến {n["code"]} hạ cánh ở {_where(t)}' + (f', trễ {late} phút' if late else ', đúng giờ') + '.'
    kit.complete(s, c, t, reward, line)
    head = '🅿️ Tắt máy, ghi sổ bay.' + (f' Thưởng chuyến bay {reward} xu.' if reward else '')
    if full and reward < full:
        head += ' (Đang bị cách chức: không có thưởng.)' if not reward else ' (Mệt quá: nửa thưởng.)'
    if cq.safety(t):
        head += ' 🛡️ Phòng an toàn bay sẽ đọc lại chuyến này cùng bạn.'
    note = ao.flown(d['odd'], not cq.slips(t), CFG)
    return dict(message=f'{head} {note} {("💬 " + story) if story else ""}'.strip(), celebrate=not cq.slips(t))


# ================================================================ story and surprises
def _arc_tick(c: dict, d: dict) -> None:
    a = d['arc']
    if a['due']:
        return
    nxt = next((x for x in ARC if x['id'] not in a['seen']), None)
    if nxt and c['day'] >= nxt['day'] and d['logbook']['landings'] >= nxt['landings']:
        a['due'] = nxt['id']


def _arc_seen(d: dict) -> dict:
    a = d['arc']
    kit.need(a['due'], 'Chưa có chuyện mới.')
    x = ARC_INDEX[a['due']]
    a['seen'].append(a['due'])
    a['due'] = None
    return dict(message=f'{x["emoji"]} {x["title"]}')


# ================================================================ the sky: rain and squalls on arrival
SKY = {'rain': dict(emoji='🌧️', name='Mưa lớn', text='Mưa to trên sân bay, đường băng ướt.'),
       'squall': dict(emoji='⛈️', name='Giông sát sân bay', text='Một ô giông đứng sát đường tiếp cận, gió giật mạnh.')}
BRAKING = {'good': 'Tốt', 'medium': 'Trung bình', 'poor': 'Kém'}
AUTOBRAKE = ('low', 'med', 'max')
ADDS = (0, 5, 10)
DODGE = ('left', 'right', 'keep')
SKY_CHANCE = {'storms': 0.55, 'wind': 0.4, 'busy': 0.3}


def _sky_roll(c: dict, d: dict, t: dict) -> dict | None:
    """At take-off: heavy rain or a squall waiting at the destination (from the task id; never on day one,
    never on top of a storm or fog hop, which have their own weather)."""
    mod = mod_of(c['day'])['id']
    if c['day'] < 2 or t['kind'] not in ('flight', 'tech') or t['needs']['wx'] in ('storm', 'fog') or t['at']:
        return None
    r = kit.rng(ID, 'sky', t['id'], t['day'])
    if r.random() >= SKY_CHANCE.get(mod, 0.25):
        return None
    kind = 'squall' if r.random() < (0.5 if mod == 'storms' else 0.3) else 'rain'
    if kind == 'rain':
        brake, gust, cell = r.choice(('good', 'medium', 'medium', 'poor')), r.choice((0, 5, 10, 12, 15)), None
    else:
        brake, gust, cell = r.choice(('good', 'medium', 'poor')), r.choice((12, 15, 18, 20)), r.choice(('left', 'right'))
    d['sky'] = dict(task=t['id'], day=c['day'], kind=kind, brake=brake, gust=gust, cell=cell, vis=r.choice((1200, 1500, 2000, 3000)),
                    set=None, ok=None)
    return d['sky']


def _sky_ready(d: dict, t: dict) -> None:
    sk = d['sky']
    kit.need(not (sk and sk['task'] == t['id'] and sk['set'] is None), 'Đài báo thời tiết xấu ở đích: cài đặt tiếp cận trước đã.')


def _sky_need(sk: dict) -> dict:
    """What the airport's report calls for."""
    add = 0 if sk['gust'] < 10 else 5 if sk['gust'] < 16 else 10
    return dict(wipers=True, brake=('low', 'med') if sk['brake'] == 'good' else ('med', 'max'), add=(0, 5) if add == 0 else (add,),
                dodge={'left': 'right', 'right': 'left', None: 'keep'}[sk['cell']], go='divert' if sk['brake'] == 'poor' else 'land')


def _sky(s, c, d, p):
    t = _task(c, p, 'approach')
    sk = d['sky']
    kit.need(sk and sk['task'] == t['id'] and sk['set'] is None, 'Không có báo cáo thời tiết nào chờ cài đặt.')
    kit.need(type(p.get('wipers')) is bool, 'Gạt mưa: bật hay tắt?')
    conf = dict(wipers=p['wipers'], brake=kit.one_of(p.get('brake'), AUTOBRAKE, 'Chọn mức phanh tự động.'),
                add=kit.one_of(p.get('add'), ADDS, 'Chọn tốc độ cộng thêm.'), dodge=kit.one_of(p.get('dodge', 'keep'), DODGE, 'Chọn hướng né.'),
                go=kit.one_of(p.get('go'), ('land', 'divert'), 'Tiếp cận hay đi sân bay dự bị?'))
    want = _sky_need(sk)
    wrong = []
    if not conf['wipers']:
        wrong.append(('wipers', 1, 'Mưa to mà không bật gạt mưa, kính mờ đặc lúc tiếp cận.', 'quên gạt mưa', False))
    if conf['go'] == 'land' and conf['brake'] not in want['brake']:
        wrong.append(('autobrake', 2, 'Đường băng ướt mà đặt phanh tự động chưa hợp.', 'phanh tự động chưa hợp đường băng', False))
    if conf['go'] == 'land' and conf['add'] not in want['add']:
        wrong.append(('vref', 1, 'Tốc độ tiếp cận chưa tính đúng gió giật.', 'tốc độ chưa tính gió giật', False))
    if sk['cell'] and conf['dodge'] == sk['cell']:
        wrong.append(('sky_cell', 3, 'Tiếp cận lệch về phía ô giông, tàu bị quăng quật.', 'lao về phía ô giông', True))
    if conf['go'] == 'land' and want['go'] == 'divert':
        wrong.append(('sky_poor', 3, 'Đường băng báo phanh kém mà vẫn hạ cánh, tàu trượt dài tới cuối đường băng.', 'hạ cánh khi phanh kém', True))
    for code, sev, text, note, safety in wrong:
        t['mistakes'] += 1
        cq.slip(t, code, sev, text, note, safety=safety)
    sk['set'] = conf
    sk['ok'] = not wrong
    where = t['needs']['leg']['to']
    if conf['go'] == 'divert':
        t['at'] = t['needs']['leg']['alt']
        t.update(ap=1, gate=0)
        d['today']['diverts'] += 1
        _late(c, d, t, DELAY['divert'], 'đường băng ở sân bay đến không an toàn')
        msg = f'↪️ Đi sân bay dự bị {t["at"]}.' + (' Chị Vân: “Phanh kém thì không cố. Đúng bài.”' if want['go'] == 'divert' else
                                                     ' Chị Vân: “Đường băng vẫn phanh được mà em… thôi, cẩn thận cũng không sai.”')
    else:
        msg = f'🛬 Cài đặt xong, tiếp cận {where}.' + ('' if wrong else ' Chị Vân gật đầu: “Chuẩn.”')
    if wrong:
        msg += ' ⚠️ ' + ' '.join(w[2] for w in wrong)
        return dict(message=msg, correct=False)
    return dict(message=msg, celebrate=True)


ACTIONS = {
    'pl_fuel': _fuel, 'pl_fog': _fog, 'pl_check': _check, 'pl_defect': _defect, 'pl_switch': _switch, 'pl_pa': _pa,
    'pl_takeoff': _takeoff, 'pl_decide': _decide, 'pl_arrive': _arrive, 'pl_gate': _continue, 'pl_around': _around, 'pl_park': _park,
    'pl_sky': _sky,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    d['today'] = _fresh_today(c['day'])
    _arc_tick(c, d)
    ao.start(c, ID, d['odd'])
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(c['day'])['id'], c['life'].get('mode') == 'festival')
    ao.tick(s, c, ID, d['odd'], ODD, busy=d['desk']['ev'] is not None)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    odd_note = ao.close(s, c, d['odd'], ODD)
    d['sky'] = None
    x = d['today']
    lines = [f'✈️ Bay {x["flights"]} chặng, {x["minutes"]} phút trên trời.']
    if x['arounds']:
        lines.append(f'↗️ Bay lại {x["arounds"]} lần. Không ổn định thì bay lại: đúng bài.')
    if x['holds']:
        lines.append(f'🔄 Bay chờ thời tiết {x["holds"]} lần.')
    if x['diverts']:
        lines.append(f'↪️ Chuyển hướng {x["diverts"]} lần.')
    if x['delays']:
        lines.append(f'⏱️ Tổng cộng trễ {x["delays"]} phút vì an toàn.')
    if desk_note:
        lines.append(desk_note)
    if odd_note:
        lines.append(odd_note)
    lines += ao.day_lines(c, d['odd'])
    lines.append('🏠 Tối về tới đầu hẻm, bà Tám để phần cơm trên bàn.')
    return dict(lines=lines, note='Mai báo danh ở sân bay lúc 05:30.', flights=x['flights'], minutes=x['minutes'], arounds=x['arounds'],
                diverts=x['diverts'], delays=x['delays'], ontime=x['ontime'])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    codes = {x['code'] for x in cq.slips(t)}
    prep = 2 if codes & {'fuel_low', 'overweight'} or any(k.startswith('ignored_') for k in codes) else \
        3 if codes & {'heavy', 'no_hold', 'rush'} else 4 if t.get('extra') else 5
    order = 3 if 'order' in codes else 5
    unsafe = codes & {'cell', 'med_far', 'minima', 'land_storm', 'land_fog', 'sky_cell', 'sky_poor'}
    rough = codes & {'unstable', 'crosswind', 'turb', 'cell_over', 'med_wait', 'autobrake', 'vref', 'wipers'}
    safe = 1 if unsafe else 3 if rough else 4 if 'needless' in codes else 5
    pa = t.get('pa')
    pax = 5 if not t.get('delay') or pa == 'clear' else 3 if pa == 'vague' else 2
    return dict(criteria=[
        dict(key='prep', label='Chuẩn bị chuyến bay', score=prep, note='dầu đủ, kiểm tàu kỹ' if prep == 5 else 'dầu hoặc vòng kiểm tàu chưa chuẩn'),
        dict(key='checklist', label='Checklist', score=order, note='đúng thứ tự' if order == 5 else 'làm lộn thứ tự'),
        dict(key='safety', label='Quyết định an toàn', score=safe, note='bình tĩnh, đúng bài' if safe == 5 else 'có quyết định chưa an toàn'),
        dict(key='pax', label='Thông báo cho khách', score=pax, note='rõ ràng, thật lòng' if pax == 5 else 'thông báo chưa rõ')])


# The reviewers' own words (feedback.make_review → review_text): the captain's debrief, the purser, passengers.
VOICES = {
    CAPTAIN: {5: ['Chặng {code} gọn gàng từ bản tin tới lúc tắt máy.', 'Bay với em chặng {code}, chị yên tâm.'],
              4: ['Chặng {code} ổn, còn một chỗ cần chắc tay hơn.', 'Nhìn chung tốt. Chị ghi lại một điều cho chặng sau.'],
              3: ['Chặng {code} chị phải nhắc nhiều.', 'Ngồi xem lại chặng {code} với chị nhé.'],
              1: ['Chặng {code} không đạt. Mai mình bay mô phỏng lại phần này.', 'Chị phải ghi chặng {code} vào sổ huấn luyện.']},
    PURSER: {5: ['Khoang khách chặng {code} yên ổn, tụi chị làm việc nhẹ cả người.'], 4: ['Chặng {code} ổn, khoang khách chỉ hơi xì xào một lúc.'],
             3: ['Chặng {code} khoang khách lo lắng khá lâu.'], 1: ['Chặng {code} cả khoang hoảng, tụi chị phải trấn an từng người.']},
    GRANNY: {5: ['Chuyến đi {to} êm ru, bà chẳng sợ gì cả.', 'Lần đầu đi máy bay mà dễ chịu ghê.'], 4: ['Chuyến bay tốt, chỉ có chút bà chưa ưng.'],
             3: ['Bay thì tới nơi, mà bà cứ thấp thỏm.'], 1: ['Chuyến này bà sợ quá, chắc không dám đi nữa.']},
    KIET: {5: ['Đi công tác mà được chuyến thế này là đủ.', 'Chuyến {code}: không có gì để phàn nàn. Hiếm đấy.'], 4: ['Chuyến {code}: tạm được.'],
           3: ['Chuyến {code}: không như mong đợi.'], 1: ['Chuyến {code}: một trải nghiệm tệ.']},
    NA: {5: ['Chuyến bay đỉnh quá ạ ✈️', 'Con thích tổ bay chuyến {code} nhất luôn!'], 4: ['Hay lắm ạ, chỉ có một chỗ con thấy hơi lạ.'],
         3: ['Con hơi sợ xíu ạ 😥'], 1: ['Con không thích chuyến này đâu 😢']},
}
PAX_LINES = {'pax': ('Thông báo rõ ràng, nghe là yên tâm.', 'Chậm mà không ai nói rõ vì sao.'),
             'safety': ('Hạ cánh êm, không rung lắc gì.', 'Có lúc tàu chao mạnh, cả khoang hoảng.')}


def review_text(c: dict, t: dict, persona: str, stars: int, criteria: list, seed: int) -> str:
    i = _npc_index(t)
    return air.review(t, stars, criteria, seed, VOICES.get(i, VOICES[KIET]), None if i in (CAPTAIN, PURSER) else PAX_LINES)


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    leg, wx, f = n['leg'], WX[n['wx']], n['fuel']
    return (f'Bản tin chuyến {leg["code"]} {leg["frm"]} → {leg["to"]}: {wx["emoji"]} {wx["name"]}. {wx["text"]} {n["pax"]} khách. '
            f'Dầu chặng {_kg(f["trip"])}, đi dự bị {leg["alt"]} {_kg(f["alt"])}, dự phòng 30 phút {_kg(f["reserve"])}.')


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    v['leg'] = t['needs']['leg']          # the departures board shows every hop, briefed or not
    v['expected_bonus'] = t.get('flight_bonus', BONUS)
    if not t['known']:
        v['needs'] = None
        return v
    n = t['needs']
    f = n['fuel']
    # Only the gates flown so far (and the one ahead) show their readings; whether they were stable never does.
    flown = {(x['ap'], x['g']) for x in t['gates_log']}
    ahead = (t['ap'], t['gate']) if t['stage'] == 'approach' and not _arrival_problem(t) and t['gate'] < 2 else None
    gates = [[dict(id=g['id'], name=g['name'], rows=[r[:3] for r in g['rows']]) if (ai, g['id']) in flown or (ai, gi) == ahead else None
              for gi, g in enumerate(row)] for ai, row in enumerate(n['gates'])]
    ev = n['event']
    event = None
    if ev and t['stage'] in ('cruise', 'approach', 'landed', 'done'):
        x = EVENTS[ev['kind']]
        event = dict(kind=ev['kind'], emoji=x['emoji'], title=x['title'], text=_event_text(t),
                     options=[dict(id=o['id'], label=o['label']) for o in x['options']])
    v['needs'] = dict(leg=n['leg'], pax=n['pax'], full=n['full'], wx=dict(id=n['wx'], **WX[n['wx']]),
                      fuel=dict(trip=f['trip'], alt=f['alt'], reserve=f['reserve'], hold=f['hold'], options=f['options']),
                      defect=dict(id=t['found'], point=DEFECTS[t['found']]['point'], own=DEFECTS[t['found']]['own'],
                                  text=DEFECTS[t['found']]['text'], fix=DEFECTS[t['found']]['fix']) if t['found'] else None,
                      event=event, gates=gates)
    v['problem'] = _arrival_problem(t) if t['stage'] == 'approach' else None
    v['where'] = _where(t)
    if t['stage'] == 'start':
        v['can'] = dict(pl_takeoff=kit.check(_takeoff_rules, t))
    elif t['stage'] == 'approach':
        v['can'] = dict(pl_around=kit.check(_around_rules, t))
    if t['stage'] == 'approach':
        v['fly'] = _fly_view(n['gates'][t['ap']])
    return v


def _num(s) -> int:
    digits = ''.join(ch for ch in str(s) if ch.isdigit())
    return int(digits) if digits else 0


def _fly_view(row: list) -> dict:
    """✈️ Tự bay: the approach in hand as the cockpit flies it, from the gates' readings (never whether they hold):
    how the autopilot hands the aircraft over (speed, dots off the glide path, sink) and the crosswind and the
    runway lights at 200 ft."""
    g1, g2 = row
    return dict(kt=_num(g1['rows'][0][1]), dots=_num(g1['rows'][1][1]), sink=_num(g1['rows'][2][1]),
                wind=_num(g2['rows'][1][1]), rwy=bool(g2['rows'][0][3]))


def public_data(c: dict) -> dict:
    d = tree_copy(c['ext']['data'])
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    arc = d['arc']
    due = ARC_INDEX.get(arc['due']) if arc.get('due') else None
    remaining = sum(t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks'])
    completed = d['today']['flights'] if d['today']['day'] == c['day'] else 0
    return dict(intro=d['intro'], logbook=d['logbook'], log=d['log'][-6:], today=d['today'],
                schedule=dict(total=completed + remaining, completed=completed, remaining=remaining),
                regulars={k: dict(v) for k, v in d['regulars'].items()},
                mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                arc=dict(seen=list(arc['seen']), total=len(ARC),
                         due=dict(id=due['id'], emoji=due['emoji'], title=due['title'], text=list(due['text'])) if due else None),
                desk=kit.desk_public(d['desk'], DESK, ID), odd=ao.public(c, ao.ensure(d), ODD, ID, CFG),
                sky=_sky_public(d.get('sky')))


def _sky_public(sk: dict | None) -> dict | None:
    if not sk:
        return None
    x = SKY[sk['kind']]
    return dict(sk, emoji=x['emoji'], name=x['name'], text=x['text'], braking=BRAKING[sk['brake']])


def content() -> dict:
    return dict(points=POINTS, checklist=CHECKLIST, panel=PANEL, pa=PA, wx=WX, arrive=list(ARRIVE), intro=INTRO,
                reserve=RESERVE, hold=HOLD, tanks=TANKS, full_pax=FULL_PAX, bonus=BONUS, airline=air.AIRLINE, plane=air.PLANE,
                arc=[dict(id=x['id'], emoji=x['emoji'], title=x['title'], landings=x['landings']) for x in ARC],
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    if (c['ext']['data'].get('odd') or {}).get('ev'):
        return 'Có người đang chờ bạn trả lời: chọn giọng, chọn ý, cần thì báo cơ trưởng hoặc phòng an toàn.'
    st = t.get('stage')
    if st == 'brief':
        return 'Đọc bản tin → dầu = chặng + dự bị + 30 phút (giông lúc tới: thêm dầu chờ) → sương ở đích thì chờ dưới đất.'
    if st == 'walk':
        return 'Kiểm đủ bốn điểm quanh tàu. Vỏ che, chốt cửa: tự xử lý. Lốp mòn, rò dầu: gọi chú Mẫn.'
    if st == 'start':
        return 'Bật công tắc đúng thứ tự trên thẻ checklist. Chuyến bay chậm thì thông báo thật rõ cho khách.'
    if st == 'approach':
        return 'Giông trên sân bay: bay chờ nếu đủ dầu, không thì đi sân bay dự bị. Cổng nào chưa ổn định thì bay lại.'
    return 'Nhận bản tin → dầu → vòng quanh tàu → checklist → cất cánh → qua hai cổng → hạ cánh.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'ops':
        return 'Đã in sẵn bản tin thời tiết cho chặng sau.'
    if e.get('role') == 'ramp':
        return 'Đã chèn bánh, cắm dây nối đất cho tàu.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu chuyến bay sai.')


def validate_task(t: dict, original: dict) -> None:
    if 'flight_bonus' in t:
        kit.integer(t['flight_bonus'], 8, 22)
        kit.need(t['flight_bonus'] == _flight_bonus(original), 'Thưởng chuyến bay sai.')
    kit.need(t.get('gen') == GEN, 'Phiên bản chuyến bay không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái chuyến bay sai.')
    n = t['needs']
    kit.need(t.get('fuel') is None or t['fuel'] in n['fuel']['options'], 'Lượng dầu sai.')
    kit.need(t.get('fog') in (None, 'wait', 'go'), 'Quyết định sương sai.')
    ck = t.get('checked')
    kit.need(isinstance(ck, list) and len(ck) == len(set(ck)) and all(x in POINT for x in ck), 'Vòng kiểm tàu sai.')
    kit.need(t.get('found') in (None, n['defect']) and (t['found'] is None or DEFECTS[t['found']]['point'] in ck), 'Lỗi tàu sai.')
    kit.need(t.get('handled') in (None, 'fix', 'report', 'caught'), 'Cách xử lý lỗi sai.')
    sw = t.get('switches')
    kit.need(isinstance(sw, list) and sw == ORDER[:len(sw)], 'Checklist sai.')
    kit.need(t.get('pa') in (None, *PA_IDS), 'Thông báo sai.')
    kit.integer(t.get('delay'), 0, 600)
    kit.integer(t.get('air_late'), 0, 600)
    ev = n['event']
    kit.need(t.get('decision') is None or (ev and t['decision'] in [o['id'] for o in EVENTS[ev['kind']]['options']]), 'Quyết định trên đường bay sai.')
    kit.need(t.get('arrive') in (None, *ARRIVE), 'Quyết định khi tới sai.')
    kit.need(t.get('at') is None or t['at'] in (n['leg']['alt'], (ev or {}).get('near')), 'Sân bay hạ cánh sai.')
    kit.integer(t.get('ap'), 0, 1)
    kit.integer(t.get('gate'), 0, 2)
    kit.integer(t.get('arounds'), 0, MAX_AROUNDS)
    gl = t.get('gates_log')
    kit.need(isinstance(gl, list) and len(gl) <= 8, 'Nhật ký tiếp cận sai.')
    for x in gl:
        kit.need(isinstance(x, dict) and set(x) == {'ap', 'g', 'go'} and x['g'] in ('g1', 'g2') and x['go'] in ('land', 'around'), 'Nhật ký tiếp cận sai.')
        kit.integer(x['ap'], 0, 1)
    _vbool(t.get('extra'))
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện tổ bay sai.')
    kit.need(t.get('reason') is None or (isinstance(t['reason'], str) and len(t['reason']) <= 120), 'Lý do chậm sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    lb = d['logbook']
    kit.need(isinstance(lb, dict) and set(lb) == set(initial()['logbook']), 'Sổ giờ bay sai.')
    for v in lb.values():
        kit.integer(v, 0, 10 ** 7)
    kit.need(isinstance(d['log'], list) and len(d['log']) <= LOG_MAX, 'Nhật ký chuyến bay sai.')
    for x in d['log']:
        kit.need(isinstance(x, dict) and set(x) == {'day', 'code', 'to', 'minutes', 'late', 'arounds', 'ok'}, 'Nhật ký chuyến bay sai.')
        for k in ('day', 'minutes', 'late', 'arounds'):
            kit.integer(x[k], 0, 10 ** 7)
        kit.text(x['code'], 12)
        kit.text(x['to'], 40)
        _vbool(x['ok'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ người quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ người quen sai.')
        kit.integer(v['visits'], 0, 999)
    a = d['arc']
    kit.need(isinstance(a, dict) and isinstance(a.get('seen'), list) and all(x in ARC_INDEX for x in a['seen'])
             and len(set(a['seen'])) == len(a['seen']) and a.get('due') in (None, *ARC_INDEX), 'Chuyện nghề sai.')
    kit.need(isinstance(d['today'], dict) and set(d['today']) == set(_fresh_today(0)), 'Số liệu trong ngày sai.')
    for v in d['today'].values():
        kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)
    ao.validate(d['odd'], ODD)
    sk = d['sky']
    if sk is not None:
        kit.need(isinstance(sk, dict) and set(sk) == {'task', 'day', 'kind', 'brake', 'gust', 'cell', 'vis', 'set', 'ok'} and sk['kind'] in SKY
                 and sk['brake'] in BRAKING and sk['cell'] in (None, 'left', 'right') and sk['ok'] in (None, True, False), 'Thời tiết ở đích sai.')
        kit.text(sk['task'], 60)
        kit.integer(sk['day'], 1, 10 ** 7)
        kit.integer(sk['gust'], 0, 40)
        kit.integer(sk['vis'], 0, 10000)
        conf = sk['set']
        kit.need(conf is None or (isinstance(conf, dict) and set(conf) == {'wipers', 'brake', 'add', 'dodge', 'go'} and type(conf['wipers']) is bool
                                  and conf['brake'] in AUTOBRAKE and conf['add'] in ADDS and conf['dodge'] in DODGE and conf['go'] in ('land', 'divert')),
                 'Cài đặt tiếp cận sai.')


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='pl_', category='service',
    meta=dict(short='Phi công', place='Hãng bay Cánh Cò', tagline='Đúng giờ là lời hứa, an toàn là điều kiện.', icon='send',
              color='#2f5d8a', light='#e6eef7', weather='Trời quang trên đường bay', work='Chuyến bay', station='Buồng lái',
              greeting='Sáng đi từ đầu hẻm ra sân bay. Đọc bản tin, tính dầu, đi một vòng quanh tàu rồi bay cùng chị Vân.',
              caption='Sáu mươi tám người phía sau, một checklist phía trước', map_label='19 · SÂN BAY CÁNH CÒ'),
    people=PEOPLE,
    staff=[('Tùng', 'ops', 'Điều phái tập sự, in bản tin nhanh thoăn thoắt.', 80, 86),
           ('Hạnh', 'ramp', 'Nhân viên sân đỗ, chèn bánh chưa bao giờ quên.', 78, 92),
           ('Phúc', 'ops', 'Thuộc lòng giờ giông của từng hòn đảo.', 72, 94),
           ('Bình', 'ramp', 'Khỏe, nhanh, hay hát khi kéo xe hành lý.', 88, 80)],
    roles={'ops': 'Điều phái phụ', 'ramp': 'Nhân viên sân đỗ'},
    tip=0,
    open_line='Báo danh xong. Chị Vân đang chờ ở phòng điều phái.',
    more_line='Điều phái xếp thêm một chặng bay.',
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    activity=('✈️', 'Chuẩn bị chuyến bay', [('Vỏ che ống pitot', 'Tháo trước khi bay'), ('Dầu chờ 20 phút', 'Khi dự báo giông'),
                                            ('Công tắc', 'Theo thứ tự checklist'), ('Chưa ổn định', 'Bay lại')],
              ['Nhận bản tin, tính dầu', 'Đi một vòng quanh tàu', 'Đọc checklist, cất cánh', 'Qua từng cổng, hạ cánh']),
    stories=[('Đôi cánh của chị Vân', ('Chị Vân kể hồi mới vào nghề chị sợ nhất là giông chiều trên đảo.',
                                       'Bạn bay thêm một chặng; chị chỉ cho bạn cách đọc radar thời tiết.',
                                       'Chị tặng bạn cuốn sổ tay cũ: “Chỗ nào chị từng sợ, chị ghi hết trong này.”')),
             ('Chuyến xe sớm', ('Bốn giờ rưỡi sáng, con hẻm còn tối. Chỉ có xe bánh mì của cô Ba đã sáng đèn.',
                                'Bạn chở thêm chú Mẫn ra sân bay, hai chú cháu nói chuyện máy bay suốt đường.',
                                'Từ đó sáng nào cô Ba cũng để phần hai ổ bánh mì: “Cho tổ bay đầu hẻm.”')),
             ('Bức thư của Bé Na', ('Bé Na gửi thư về hãng, nét chữ còn nguệch ngoạc.',
                                    'Bạn bay thêm một chặng rồi ngồi đọc thư cùng chị Thu.',
                                    '“Con sẽ học giỏi Toán để làm cơ phó như chú.” Lá thư được dán ở phòng điều phái.'))],
    review_asides=['Hạ cánh êm như đặt ly nước xuống bàn.', 'Thông báo rõ ràng, nghe là yên tâm.', 'Checklist đọc chậm rãi, đâu ra đấy.',
                   'Bay đúng giờ mà không vội vàng.'],
    situations=SITUATIONS,
    guide='Nhận bản tin → nạp dầu (chặng + dự bị + 30 phút, giông lúc tới: thêm dầu chờ) → kiểm bốn điểm quanh tàu → checklist đúng thứ tự → '
          'chậm thì thông báo thật cho khách → cất cánh → qua cổng 1.000 ft và 200 ft, chưa ổn định thì bay lại → tắt máy, ghi sổ.',
    employment=dict(
        postings=[
            dict(id='pl-fo', org='Hãng bay Cánh Cò · Sân bay thành phố', kind='company', title='Cơ phó tàu cánh quạt',
                 salary=(85, 110), probation_days=3, wants=['calm', 'careful', 'communication'],
                 perks=['Bay cùng cơ trưởng kèm cặp', 'Tối về ngủ ở nhà', 'Được học bay chặng khó'],
                 culture='Hãng bay nhỏ, hai chiếc tàu cánh quạt, bay đảo và miền Tây. Ai cũng quen tên nhau; an toàn nói trước, đúng giờ nói sau.',
                 questions=['pl_weather', 'pl_speak', 'pl_fuel', 'mistake'], reference=True),
            dict(id='pl-sim', org='Trung tâm huấn luyện Cánh Cò', kind='branch', title='Phi công huấn luyện trên buồng lái mô phỏng',
                 salary=(65, 85), probation_days=2, wants=['learning', 'careful'],
                 perks=['Nhận việc nhanh', 'Lịch cố định', 'Lương thấp hơn bay thật'],
                 culture='Trung tâm nhỏ cạnh sân bay, dạy tổ bay mới làm quen buồng lái trước khi lên tàu thật.',
                 questions=['pl_weather'], reference=False),
        ],
        questions={
            'pl_weather': dict(text='Dự báo giông ở sân bay đến đúng giờ bạn tới. Bạn chuẩn bị thế nào?', options=[
                dict(id='hold', label='Mang thêm dầu chờ, tính trước sân bay dự bị, báo khách có thể trễ', score=3, note='Chị Vân gật đầu: đúng cách người trong nghề chuẩn bị.'),
                dict(id='same', label='Nạp dầu như mọi ngày, tới đâu tính đó', score=1, note='Tới nơi sẽ chỉ còn một đường: đi sân bay dự bị.'),
                dict(id='rush', label='Cố bay sớm hơn để tới trước cơn giông', score=0, note='Đua với thời tiết là thói quen nguy hiểm.')]),
            'pl_speak': dict(text='Bạn thấy cơ trưởng quên một dòng checklist. Bạn làm gì?', options=[
                dict(id='say', label='Nói ngay, rõ ràng: “Chị ơi, còn dòng đèn chống va.”', score=3, note='Buồng lái hai người là để đỡ nhau.'),
                dict(id='later', label='Để sau chuyến bay mới góp ý', score=1, note='Chậm mất một nhịp quan trọng.'),
                dict(id='silent', label='Im lặng, cơ trưởng chắc có lý do', score=0, note='Im lặng trong buồng lái là nguy hiểm.')]),
            'pl_fuel': dict(text='Tàu kín khách, chặng ngắn. Anh điều phái hỏi bạn có muốn đổ đầy bình cho chắc không.', options=[
                dict(id='plan', label='Đổ đúng kế hoạch: chặng, dự bị, dự phòng', score=3, note='Đủ an toàn mà không quá tải.'),
                dict(id='full', label='Đổ đầy, dư còn hơn thiếu', score=0, note='Tàu kín khách mà đầy bình là quá trọng lượng cất cánh.'),
                dict(id='less', label='Bớt phần dự phòng cho nhẹ', score=0, note='Dầu dự phòng không bao giờ được bớt.')]),
        }),
)
