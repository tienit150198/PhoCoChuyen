"""Tiếp viên Cánh Cò: the cabin of Hãng bay Cánh Cò's turboprop (plugin career).

The player works the 68-seat cabin with chị Thu, the purser, on the same short hops
the pilot career flies (game/careers/airline.py). One task is one moment of a
flight's cabin work:

* ``board``: four passengers at the door, one at a time. Read the boarding pass and
  what they carry: show the seat, send an oversized case to the hold, keep a power
  bank on the passenger, move someone off the exit row (rows 1 and 17: able adults
  from 15) or back to their own seat;
* ``demo``: the safety demonstration in the card's order, then walk the aisle and
  put right what is not ready for take-off (belt, tray table, seat back, a bag in
  the aisle, a closed window blind), then tell the flight deck the cabin is ready;
* ``service``: the cart, row by row. Drinks and snacks by seat, the special meals
  on the purser's list (a vegetarian meal, a peanut allergy row where nobody gets
  peanuts), no hot drinks to small children, and a sleeping passenger is left to
  sleep. Some days the seat-belt sign comes on mid-service: a real-seconds
  countdown to brake the cart, stow the hot water and sit down;
* ``calm``: a difficult passenger in three beats (listen, the rule, a way out);
* ``medical``: a passenger taken ill: ask, use the right things from the kit,
  never your own medicine, and tell the captain when it is serious.

Mistakes go through consequences.slip; money only through kit (the salary is the
pay, a smooth job adds a small bonus). Everything random is rolled from
(day, slot) or the task id.

Between jobs come the chuyện oái oăm (game/careers/air_odd.py, kept out of the
generated tasks): passengers who harass or bully, the office's KPI, extra night
rotations and gym orders, crew who cut corners, family and the lane. The player
answers in their own tone and words, and brings in chị Thu or the company;
harassment is always worth reporting, and the company backs the report.
"""
from __future__ import annotations

import copy

from ..jsoncopy import tree_copy
from . import kit
from . import airline as air
from . import air_odd as ao
from .air_odd_content import CABIN as ODD
from .. import consequences as cq
from .. import archive as ar

ID = 'flight_attendant'
GEN = 1
BONUS = 8              # xu for a job done by the book (the salary is the pay)
TURB_FIRST, TURB_LATER = 25, 20   # seconds to secure the cabin when the belt sign comes on
LOG_MAX = 12

# The portraits give odd ids (_npc_01, _03…) long hair: the women sit on those (Vy wears it short).
PEOPLE = [
    ('Chị Thu', 'Tiếp viên trưởng', 'Mười lăm năm bay, nói nhỏ mà cả khoang nghe rõ.', 'picky'),
    ('Anh Kiệt', 'Hành khách đi công tác', 'Vali to, muốn để ngay trên đầu ghế mình.', 'sour'),
    ('Bà Chín', 'Hành khách lần đầu đi máy bay', 'Mang túi xoài ra đảo cho cháu, sợ nhất là rung lắc.', 'warm'),
    ('Ông Tư', 'Cựu chiến binh về thăm đảo', 'Bị tiểu đường, hay quên ăn sáng.', 'bossy'),
    ('Chị Mai', 'Mẹ bế bé Bơ mười tháng', 'Bé hay khóc lúc máy bay hạ độ cao.', 'warm'),
    ('Chú Hải', 'Khách quen tuyến Rạch Giá', 'Đi biển cả đời, vậy mà sợ độ cao.', 'quiet'),
    ('Cơ trưởng Vân', 'Cơ trưởng', 'Quyết mọi chuyện an toàn của chuyến bay.', 'warm'),
    ('Vy', 'Nhóm bạn đi phượt', 'Thích chụp ảnh, hay đứng dậy khi đèn thắt dây còn sáng.', 'genz'),
]
THU, KIET, CHIN, TU, MAI, HAI, VAN, VY = range(8)

DRINKS = [dict(id='water', name='Nước suối', emoji='💧', hot=False), dict(id='tea', name='Trà nóng', emoji='🍵', hot=True),
          dict(id='coffee', name='Cà phê sữa', emoji='☕', hot=True), dict(id='juice', name='Nước cam', emoji='🧃', hot=False)]
SNACKS = [dict(id='banhmi', name='Bánh mì pa-tê', emoji='🥖'), dict(id='veg', name='Bánh mì chay', emoji='🥬'),
          dict(id='nuts', name='Đậu phộng rang', emoji='🥜'), dict(id='cake', name='Bánh bông lan', emoji='🍰')]
ITEM = {x['id']: x for x in DRINKS + SNACKS}
DRINK_IDS = [x['id'] for x in DRINKS]
SNACK_IDS = [x['id'] for x in SNACKS]
HOT = {x['id'] for x in DRINKS if x['hot']}

# At the door: what each passenger needs from you.
DOOR = [dict(id='seat', emoji='👉', name='Chỉ chỗ ngồi'), dict(id='hold', emoji='🏷️', name='Gửi khoang hàng'),
        dict(id='move', emoji='🔁', name='Đổi chỗ ngồi'), dict(id='battery', emoji='🔋', name='Pin sạc mang theo người')]
DOOR_IDS = [x['id'] for x in DOOR]
ISSUE_ACT = {None: 'seat', 'bag': 'hold', 'wrong': 'move', 'exit': 'move', 'power': 'battery'}
BOARDERS = [   # (npc index or None, who, bag, issue, what they say) — {seat} is their boarding pass
    (CHIN, 'Bà Chín', 'bag', None, 'Cô ơi, ghế {seat} của bà ở đâu?'),
    (HAI, 'Chú Hải', 'bag', None, 'Ghế {seat}. Chú đi tuyến này hoài mà vẫn quên chỗ.'),
    (None, 'Cô giáo trẻ', 'bag', None, 'Chào em, chị ngồi {seat} nhé.'),
    (KIET, 'Anh Kiệt', 'case', 'bag', 'Vali này anh để trên đầu ghế {seat} được mà, nhét chút là vừa.'),
    (None, 'Anh thợ xây', 'case', 'bag', 'Thùng đồ nghề hơi to, em cho anh để lên hộc nhé. Ghế {seat}.'),
    (VY, 'Vy', 'case', 'power', 'Vali của em gửi khoang hàng nha. Trong đó có hai cục sạc dự phòng thôi. Ghế {seat}.'),
    (None, 'Chú đi câu', 'case', 'power', 'Gửi giúp chú cái thùng này, có cục pin sạc cho cái đèn câu. Chú ngồi {seat}.'),
    (MAI, 'Chị Mai bế bé Bơ', 'bag', 'exit', 'Vé chị ghế {seat}, hàng đầu rộng chân cho bé nằm.'),
    (TU, 'Ông Tư chống gậy', 'bag', 'exit', 'Ghế {seat} đây, hàng cạnh cửa cho ông duỗi chân.'),
    (None, 'Cậu bé lớp 5', 'bag', 'exit', 'Con ngồi {seat} ạ! Bố mẹ con ngồi đằng sau.'),
    (None, 'Chị nhân viên văn phòng', 'bag', 'wrong', 'Em ơi, có người ngồi ghế {seat} của chị rồi.'),
    (HAI, 'Chú Hải', 'bag', 'wrong', 'Ghế {seat} của chú có cậu nào ngồi mất rồi, cháu xem giúp.'),
]

DEMO = [dict(id='belt', emoji='🔗', name='Thắt dây an toàn', line='Để thắt dây an toàn, quý khách cài khóa và kéo dây cho vừa.'),
        dict(id='exits', emoji='🚪', name='Chỉ cửa thoát hiểm', line='Tàu có hai cửa thoát hiểm phía trước và hai cửa phía sau.'),
        dict(id='mask', emoji='😷', name='Mặt nạ dưỡng khí', line='Khi mặt nạ rơi xuống, quý khách đeo cho mình trước rồi mới giúp người bên cạnh.'),
        dict(id='vest', emoji='🦺', name='Áo phao', line='Áo phao để dưới ghế. Chỉ thổi phồng khi đã ra khỏi tàu.'),
        dict(id='card', emoji='📄', name='Tờ hướng dẫn an toàn', line='Mời quý khách đọc tờ hướng dẫn an toàn ở túi ghế phía trước.')]
DEMO_IDS = [x['id'] for x in DEMO]
CABIN = {'ok': dict(emoji='🙂', name='Sẵn sàng'), 'belt': dict(emoji='🔓', name='Chưa thắt dây'), 'tray': dict(emoji='🍽️', name='Bàn ăn chưa gập'),
         'recline': dict(emoji='💺', name='Ghế còn ngả'), 'bag': dict(emoji='🎒', name='Túi để ở lối đi'),
         'shade': dict(emoji='🌑', name='Rèm cửa sổ đang đóng')}
FIX_LINE = {'belt': 'Nhắc khách thắt dây, chờ nghe “tách”.', 'tray': 'Mời khách gập bàn ăn lên.', 'recline': 'Mời khách dựng thẳng lưng ghế.',
            'bag': 'Cất túi vào gầm ghế phía trước.', 'shade': 'Mở rèm cửa sổ cho khách.'}

SECURE = [dict(id='brake', emoji='🛑', name='Khóa phanh xe đẩy'), dict(id='hot', emoji='♨️', name='Cất bình nước nóng'),
          dict(id='sit', emoji='💺', name='Về ghế, thắt dây')]
SECURE_IDS = [x['id'] for x in SECURE]

# Difficult passengers: three beats (listen, the rule, a way out), each one choice.
CALM = {
    'bin': dict(npc=KIET, emoji='🧳', title='Vali trên hộc hàng đầu',
                beats=[dict(text='Anh Kiệt ngồi hàng 15 nhưng cố nhét vali vào hộc hàng 2: “Để đây tí xuống cho nhanh!”',
                            options=[dict(id='a', label='Chào anh, em hiểu anh vội. Để em xem giúp anh nhé.', grade='good', reply='Anh Kiệt dịu giọng: “Ừ, anh có cuộc họp lúc mười giờ.”'),
                                     dict(id='b', label='Anh ơi không được đâu, anh để đúng chỗ đi.', grade='ok', reply='Anh Kiệt cau mày, tay vẫn giữ vali.'),
                                     dict(id='c', label='Anh không đọc quy định à?', grade='bad', reply='Anh Kiệt đỏ mặt: “Cô nói kiểu gì thế?”')]),
                       dict(text='“Hộc này còn trống mà, sao lại không được?”',
                            options=[dict(id='a', label='Hộc hàng 2 là của khách hàng 2, họ đang lên tàu.', grade='good', reply='Anh Kiệt nhìn ra cửa, thấy hai cụ già đang xách túi.'),
                                     dict(id='b', label='Tại quy định nó vậy anh ạ.', grade='ok', reply='“Quy định gì kỳ vậy.” Anh vẫn chưa buông vali.'),
                                     dict(id='c', label='Thôi được, anh cứ để đi cho nhanh.', grade='bad', reply='Lát sau hai cụ hàng 2 không còn chỗ để túi.')]),
                       dict(text='“Thế giờ anh để đâu? Xuống tàu anh phải đi ngay.”',
                            options=[dict(id='a', label='Em cất vali trên hộc hàng 15 cho anh, hạ cánh em mời anh xuống trước.', grade='good', reply='Anh Kiệt gật đầu: “Vậy được, cảm ơn em.”'),
                                     dict(id='b', label='Anh tự tìm chỗ nào còn trống nhé.', grade='ok', reply='Anh Kiệt đi ngược dòng người tìm chỗ, lối đi tắc năm phút.'),
                                     dict(id='c', label='Không có chỗ thì em gửi khoang hàng, xuống tàu anh chờ băng chuyền.', grade='ok', reply='“Chờ băng chuyền thì lỡ họp!” Anh càu nhàu mãi.')])]),
    'photo': dict(npc=VY, emoji='📸', title='Đứng dậy chụp ảnh khi hạ độ cao',
                  beats=[dict(text='Đèn thắt dây đã sáng, tàu đang hạ độ cao. Vy đứng dậy, giơ điện thoại chụp biển qua cửa sổ bên kia.',
                              options=[dict(id='a', label='Tới gần, nói nhỏ: “Em ơi, tàu sắp hạ cánh, em ngồi xuống giúp chị nhé.”', grade='good', reply='Vy giật mình: “Dạ, em quên mất.”'),
                                       dict(id='b', label='Nói to từ cuối khoang: “Ngồi xuống!”', grade='bad', reply='Cả khoang quay lại nhìn. Vy xấu hổ, mặt đỏ bừng.'),
                                       dict(id='c', label='Kệ, chụp xong em ấy sẽ ngồi', grade='bad', reply='Tàu chao nhẹ, Vy loạng choạng suýt ngã vào lối đi.')]),
                         dict(text='“Chị ơi cho em chụp một tấm thôi, biển đẹp quá!”',
                              options=[dict(id='a', label='Tàu có thể rung bất cứ lúc nào, đứng lúc này dễ ngã lắm.', grade='good', reply='Vy ngồi xuống, cài dây.'),
                                       dict(id='b', label='Quy định là quy định em ạ.', grade='ok', reply='Vy ngồi xuống, lầm bầm.'),
                                       dict(id='c', label='Nhanh lên nhé, một tấm thôi.', grade='bad', reply='Tấm đó thành ba tấm, rồi năm tấm.')]),
                         dict(text='Vy ngồi xuống nhưng vẫn tiếc: “Mất tấm ảnh đẹp rồi.”',
                              options=[dict(id='a', label='Hạ cánh rồi, lúc lăn vào bến em chụp qua cửa sổ vẫn đẹp mà.', grade='good', reply='Vy cười: “Dạ, em chờ.” Lúc lăn vào bến, Vy có tấm ảnh hoàng hôn trên đường băng.'),
                                       dict(id='b', label='Lần sau em ngồi ghế cửa sổ.', grade='ok', reply='“Lần sau thì biết lần sau.” Vy vẫn tiu nghỉu.'),
                                       dict(id='c', label='Ảnh thì lúc nào chẳng chụp được.', grade='ok', reply='Vy im lặng cả chuyến.')])]),
    'recline': dict(npc=TU, emoji='💺', title='Ghế ngả đổ ly trà',
                    beats=[dict(text='Cậu thanh niên hàng 8 ngả ghế đánh rầm, ly trà trên bàn của ông Tư hàng 9 đổ ra quần. Ông quát ầm lên.',
                                options=[dict(id='a', label='Đưa ông khăn khô trước, hỏi ông có bị bỏng không.', grade='good', reply='Ông Tư lau quần: “Không bỏng, nhưng ướt hết rồi.”'),
                                         dict(id='b', label='Bảo cậu thanh niên xin lỗi ông ngay.', grade='ok', reply='Cậu thanh niên lí nhí xin lỗi, ông Tư vẫn giận.'),
                                         dict(id='c', label='Nói ông bình tĩnh, chuyện nhỏ thôi.', grade='bad', reply='“Chuyện nhỏ à?” Ông Tư càng to tiếng.')]),
                           dict(text='Ông Tư: “Ngả ghế mà không nhìn phía sau à? Bắt nó dựng ghế lên cả chuyến!”',
                                options=[dict(id='a', label='Ghế được ngả, nhưng lúc phục vụ ăn uống thì nên dựng lên. Để em nói với cậu ấy.', grade='good', reply='Cậu thanh niên dựng ghế: “Cháu xin lỗi ông, cháu không để ý.”'),
                                         dict(id='b', label='Ông ơi, ghế thì ai cũng được ngả ạ.', grade='bad', reply='Ông Tư đứng bật dậy, lối đi tắc.'),
                                         dict(id='c', label='Em bắt cậu ấy dựng ghế cả chuyến ạ.', grade='ok', reply='Cậu thanh niên bực bội, chuyện chuyển sang hàng 8.')]),
                           dict(text='Ông Tư ngồi xuống, vẫn hậm hực: “Quần ướt thế này xuống tàu sao được.”',
                                options=[dict(id='a', label='Mang ly trà mới và thêm khăn, hạ cánh em mời ông vào phòng chờ lau khô.', grade='good', reply='Ông Tư dịu hẳn: “Thôi được, cháu chu đáo.”'),
                                         dict(id='b', label='Mang ly trà mới cho ông.', grade='ok', reply='Ông Tư nhận ly trà, vẫn chưa vui.'),
                                         dict(id='c', label='Không làm gì thêm.', grade='bad', reply='Ông Tư ngồi im, mặt hầm hầm tới lúc hạ cánh.')])]),
    'vape': dict(npc=VY, emoji='💨', title='Thuốc lá điện tử trong nhà vệ sinh', serious=True,
                 beats=[dict(text='Chuông báo khói trong nhà vệ sinh kêu. Một bạn trong nhóm của Vy bước ra, mùi thơm ngọt, tay giấu cái bút hút.',
                             options=[dict(id='a', label='Vào kiểm tra nhà vệ sinh ngay: có khói, có lửa ở thùng rác không.', grade='good', reply='Không có lửa, chỉ còn chút khói. Bạn bật quạt hút.'),
                                      dict(id='b', label='Hỏi bạn ấy trước đã.', grade='ok', reply='Bạn ấy chối. Nhà vệ sinh chưa ai kiểm.'),
                                      dict(id='c', label='Tắt chuông rồi thôi.', grade='bad', reply='Không ai biết thùng rác có tàn lửa hay không.')]),
                        dict(text='Bạn ấy cười trừ: “Có tí khói thôi mà chị, đâu phải thuốc lá thật.”',
                             options=[dict(id='a', label='Nói rõ: trên tàu cấm mọi loại thuốc lá, kể cả điện tử. Xin bạn giữ tắt thiết bị cả chuyến.', grade='good', reply='Bạn ấy cất thiết bị vào túi, gật đầu.'),
                                      dict(id='b', label='Thôi lần sau đừng thế nhé.', grade='bad', reply='Bạn ấy nhún vai, quay về chỗ.'),
                                      dict(id='c', label='Mắng bạn ấy trước cả khoang.', grade='bad', reply='Cả nhóm bạn cãi lại, khoang khách ồn ào.')]),
                        dict(text='Chuyến bay còn hai mươi phút.',
                             options=[dict(id='a', label='Báo chị Thu và cơ trưởng, ghi biên bản để bàn giao khi hạ cánh.', grade='good', reply='Chị Thu gật đầu: “Đúng quy trình. Cơ trưởng sẽ báo mặt đất.”'),
                                      dict(id='b', label='Chỉ báo chị Thu.', grade='ok', reply='Chị Thu phải tự đi báo cơ trưởng.'),
                                      dict(id='c', label='Không báo ai, chuyện nhỏ.', grade='bad', reply='Chuông báo khói đã ghi vào máy. Sau chuyến bay, phòng an toàn hỏi vì sao không ai báo.')])]),
    'fear': dict(npc=CHIN, emoji='😰', title='Bà Chín sợ rung lắc',
                 beats=[dict(text='Tàu rung nhẹ. Bà Chín nắm chặt tay vịn, mặt tái đi: “Máy bay có sao không cô?”',
                             options=[dict(id='a', label='Ngồi xuống cạnh bà một chút, nói chậm rãi, cười với bà.', grade='good', reply='Bà Chín thở ra một hơi dài.'),
                                      dict(id='b', label='“Không sao đâu bà.” rồi đi tiếp.', grade='ok', reply='Bà Chín vẫn nắm chặt tay vịn.'),
                                      dict(id='c', label='“Bà đừng làm khách khác sợ theo.”', grade='bad', reply='Bà Chín im bặt, mắt rưng rưng.')]),
                        dict(text='“Sao nó cứ rung hoài vậy cô?”',
                             options=[dict(id='a', label='Tàu đi qua vùng gió, như xe chạy qua đoạn đường sóc. Tổ bay biết trước và đã bật đèn thắt dây.', grade='good', reply='Bà Chín gật gù: “Như xe đò chạy đường đất hả.”'),
                                      dict(id='b', label='Cháu cũng không biết nữa bà ạ.', grade='bad', reply='Bà Chín càng lo hơn.'),
                                      dict(id='c', label='Bình thường thôi bà.', grade='ok', reply='Bà Chín gật, nhưng vẫn chưa yên.')]),
                        dict(text='Bà Chín đỡ hơn, nhưng tay vẫn run.',
                             options=[dict(id='a', label='Kiểm lại dây an toàn cho bà, mang ly nước ấm, dặn bà cứ bấm chuông gọi.', grade='good', reply='Bà Chín cầm ly nước ấm: “Có cô đây bà yên tâm rồi.”'),
                                      dict(id='b', label='Mang cho bà ly nước.', grade='ok', reply='Bà cảm ơn, vẫn nhìn ra cửa sổ lo lắng.'),
                                      dict(id='c', label='Để bà ngồi yên cho quen.', grade='bad', reply='Suốt chặng còn lại bà Chín không dám nhìn ra ngoài.')])]),
}
CALM_IDS = list(CALM)

# Passengers taken ill: what they show, what you can ask, what helps.
KIT = [dict(id='water', emoji='💧', name='Nước lọc'), dict(id='juice', emoji='🧃', name='Nước cam'), dict(id='cake', emoji='🍰', name='Bánh ngọt'),
       dict(id='bag', emoji='🛍️', name='Túi nôn, khăn ướt'), dict(id='oxygen', emoji='🫁', name='Bình dưỡng khí'),
       dict(id='doctor', emoji='📢', name='Tìm bác sĩ trên chuyến bay'), dict(id='captain', emoji='☎️', name='Báo cơ trưởng'),
       dict(id='own_med', emoji='💊', name='Đưa thuốc của mình')]
KIT_IDS = [x['id'] for x in KIT]
QUESTIONS = [dict(id='feel', emoji='🗣️', name='Hỏi khách thấy thế nào'), dict(id='history', emoji='📋', name='Hỏi bệnh nền, thuốc đang dùng'),
             dict(id='eat', emoji='🍽️', name='Hỏi đã ăn uống gì chưa')]
Q_IDS = [x['id'] for x in QUESTIONS]
CASES = {
    'hypo': dict(npc=TU, title='Ông Tư run tay, vã mồ hôi', seen='Ông Tư run tay, mồ hôi túa ra, nói hơi lẫn.',
                 answers=dict(feel='“Ông chóng mặt, tay chân bủn rủn.”', history='“Ông bị tiểu đường, sáng nay có tiêm thuốc.”', eat='“Vội ra sân bay, ông chưa ăn gì.”'),
                 need={'juice': 2, 'cake': 2, 'captain': 2}, why='hạ đường huyết: cần đường ngay'),
    'chest': dict(npc=HAI, title='Chú Hải đau ngực', seen='Chú Hải ôm ngực, thở gấp, mặt tái, vã mồ hôi.',
                  answers=dict(feel='“Chú đau thắt ở ngực, lan ra tay trái.”', history='“Chú bị huyết áp cao, thuốc để trong vali gửi khoang hàng.”', eat='“Chú có ăn sáng rồi.”'),
                  need={'oxygen': 2, 'doctor': 3, 'captain': 3}, why='nghi đau tim: cần dưỡng khí, bác sĩ và cơ trưởng'),
    'sick': dict(npc=CHIN, title='Bà Chín say máy bay', seen='Bà Chín nôn nao, mặt xanh, tay bịt miệng.',
                 answers=dict(feel='“Bà chóng mặt, buồn nôn quá.”', history='“Bà không có bệnh gì, chỉ hay say xe.”', eat='“Sáng bà ăn tô bún mắm.”'),
                 need={'bag': 2, 'water': 1}, why='say máy bay: túi nôn, khăn ướt, nước'),
    'ear': dict(npc=MAI, title='Bé Bơ khóc thét lúc hạ độ cao', seen='Bé Bơ khóc thét, tay kéo tai. Chị Mai luống cuống.',
                answers=dict(feel='“Bé cứ kéo tai, chắc bé đau tai.”', history='“Bé khỏe, không bệnh gì.”', eat='“Bé bú từ lúc lên tàu tới giờ chưa bú lại.”'),
                need={'water': 2}, why='đau tai khi hạ độ cao: cho bé bú hoặc uống từng ngụm'),
}
CASE_IDS = list(CASES)

KINDS = ('board', 'demo', 'service', 'calm', 'medical')
STAGES = ('work', 'secure', 'done')

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Khách vừa phải, trời êm. Hợp để làm quen khoang khách.', weight=3),
    dict(id='rough', emoji='〰️', label='Mùa gió', hint='Hay rung lắc giữa chuyến: đèn thắt dây sáng là cất xe ngay.', min_day=2, weight=2),
    dict(id='family', emoji='👨‍👩‍👧', label='Nghỉ hè', hint='Nhiều gia đình có con nhỏ: trẻ nhỏ không uống đồ nóng.', min_day=2, weight=2),
    dict(id='early', emoji='🌅', label='Chuyến sớm', hint='Khách ngủ gà ngủ gật: ai ngủ thì để khách ngủ.', min_day=2, weight=2),
    dict(id='busy', emoji='🧳', label='Cao điểm lễ', hint='Kín chỗ, hộc hành lý chật: vali to gửi khoang hàng.', min_day=3, weight=1),
]

REG_STORY = {
    THU: ('Chị Thu: “Tay run là chuyện thường. Nói chậm lại, khách sẽ tin mình.”',
          'Chị Thu chỉ bạn mẹo cất xe đẩy gọn trong mười giây.',
          'Chị Thu kể hồi mới bay, chị làm đổ nguyên bình cà phê. “Ai mà chẳng có lần đầu.”',
          'Chị Thu giao cho bạn đọc thông báo chào mừng: “Giọng em ấm, khách thích lắm.”'),
    CHIN: ('Bà Chín dúi cho bạn quả xoài: “Cháu ăn cho có sức.”',
           'Bà Chín bảo giờ đi máy bay không sợ nữa, “có cô tiếp viên quen”.',
           'Bà Chín kể cháu nội ở đảo mới sinh con, bà lên chức cố.'),
    KIET: ('Anh Kiệt vẫn cau có, nhưng lần này tự cất vali lên hộc của mình.',
           'Anh Kiệt gật đầu chào bạn ở cửa tàu. Lần đầu anh cười.',
           'Anh Kiệt gửi lời khen lên hãng: “Tiếp viên nói có lý, tôi phục.”'),
    MAI: ('Bé Bơ nín khóc, nắm ngón tay bạn ngủ ngon lành.',
          'Chị Mai gửi ảnh bé Bơ tập đi: “Lần sau bay chị lại tìm em.”'),
    TU: ('Ông Tư kể chuyện những năm ở đảo, ai đi ngang cũng dừng lại nghe.',
         'Ông Tư giờ luôn mang theo gói kẹo: “Cháu dặn thì ông nhớ.”',
         'Ông Tư tặng tổ bay tấm ảnh cũ chụp sân bay Côn Đảo ngày xưa.'),
    VY: ('Vy đăng ảnh hoàng hôn trên đường băng, kèm dòng “cảm ơn chị tiếp viên”.',
         'Cả nhóm của Vy giờ cài dây trước cả khi đèn sáng.'),
    HAI: ('Chú Hải khỏe lại, lần sau bay mang theo một túi khô cá cho tổ bay.',
          'Chú Hải bảo giờ chú đỡ sợ độ cao: “Nghe tiếng cô tiếp viên là yên tâm.”'),
}

ARC = [
    dict(id='scarf', emoji='🧣', title='Chiếc khăn quàng màu cò trắng', served=1, day=1,
         text=('Chị Thu thắt chiếc khăn quàng cổ cho bạn: “Đồng phục là lời hứa với khách.”',
               'Sáng sớm, cô Ba đầu hẻm trầm trồ: “Ui, tiếp viên hàng không của hẻm mình đây!”')),
    dict(id='demo', emoji='🦺', title='Lần đầu làm mẫu', served=3, day=1,
         text=('Sáu mươi tám đôi mắt nhìn bạn đeo áo phao làm mẫu. Tay bạn run một chút.',
               'Chị Thu giơ ngón cái từ cuối khoang. Một em bé vỗ tay theo.')),
    dict(id='name', emoji='👋', title='Khách gọi đúng tên', served=8, day=2,
         text=('Bà Chín lên tàu, nhìn bảng tên rồi reo: “A, cô tiếp viên quen!”',
               'Bạn nhận ra mình đã nhớ ghế quen của mấy khách hay bay tuyến này.')),
    dict(id='letter', emoji='💌', title='Lá thư khen', served=16, day=4,
         text=('Hãng dán lên bảng tin lá thư của một hành khách, kể về cô tiếp viên cho con họ ly nước ấm lúc bé đau tai.',
               'Bà Tám in lá thư ra, dán lên tủ lạnh nhà trọ.')),
    dict(id='purser', emoji='🎙️', title='Cầm micro trưởng khoang', served=30, day=7,
         text=('Chị Thu đưa bạn chiếc micro: “Chuyến này em làm trưởng khoang. Chị làm phụ.”',
               '“Kính chào quý khách…” Giọng bạn vang khắp khoang, bình tĩnh và ấm.')),
]
ARC_INDEX = {x['id']: x for x in ARC}

INTRO = dict(
    title='Giới thiệu nghề: tiếp viên hàng không',
    lead='Bạn là tiếp viên của Hãng bay Cánh Cò, cùng chị Thu lo khoang khách 68 chỗ trên những chặng bay ngắn ra đảo. Sáng đi từ hẻm, tối về kịp cơm.',
    work=[('🚪', 'Đón khách ở cửa: chỉ chỗ, hành lý, pin sạc, hàng ghế thoát hiểm'),
          ('🦺', 'Làm mẫu hướng dẫn an toàn, đi dọc lối kiểm tra khoang'),
          ('🛒', 'Đẩy xe phục vụ từng hàng ghế, đúng món, đúng suất đặc biệt'),
          ('🗣️', 'Giữ bình tĩnh với khách khó chịu'),
          ('🩺', 'Sơ cứu khi khách ốm, báo cơ trưởng khi nặng')],
    meet=[('💁', 'Chị Thu tiếp viên trưởng: nói nhỏ mà ai cũng nghe'),
          ('👵', 'Bà Chín lần đầu đi máy bay'),
          ('💼', 'Anh Kiệt và cái vali to'),
          ('👶', 'Chị Mai với bé Bơ mười tháng'),
          ('〰️', 'Rung lắc giữa lúc đang phục vụ')],
    stars=[('💺', 'Hàng 1 và 17 cạnh cửa thoát hiểm: chỉ người lớn đi lại được'),
           ('🔋', 'Pin sạc dự phòng mang theo người, không gửi khoang hàng'),
           ('🥜', 'Hàng có khách dị ứng đậu phộng: không phát đậu phộng'),
           ('♨️', 'Trẻ nhỏ không uống đồ nóng'),
           ('💊', 'Không đưa thuốc của mình cho khách')],
)

DESK = [
    dict(id='mango', title='Túi xoài của bà Chín', emoji='🥭', npc=CHIN, min_day=2, tone='gentle', at='between', weight=2,
         text='Xuống tàu, bà Chín dúi cả túi xoài vào tay bạn: “Cầm lấy, cả tổ ăn cho vui!”',
         options=[dict(id='one', label='Cảm ơn bà, xin một quả chia cả tổ', hint='Vừa lòng bà, vừa đúng mực',
                       effects=dict(xp=6), good=True, outcome='Bà Chín cười móm mém. Cả tổ bay chia nhau quả xoài chín thơm lừng.'),
                  dict(id='all', label='Nhận cả túi', hint='Bà đã có lòng',
                       effects=dict(review=[3, 'Tôi cho thì cô nhận hết, cháu tôi ở đảo chẳng còn quả nào.']), good=False,
                       outcome='Tối đó bà Chín gọi cho cháu, bảo xoài “cho cô tiếp viên hết rồi”.'),
                  dict(id='no', label='Từ chối, hãng không cho nhận quà', hint='Giữ đúng quy định', effects={}, good=None,
                       outcome='Bà Chín hơi buồn, cất túi xoài lại.')],
         default='no'),
    dict(id='anniv', title='Kỷ niệm ngày cưới trên tàu', emoji='💐', npc=THU, min_day=2, tone='gentle', at='between', weight=2,
         text='Cặp vợ chồng già hàng 6 thì thầm hôm nay tròn bốn mươi năm ngày cưới, lần đầu đi máy bay cùng nhau.',
         options=[dict(id='pa', label='Xin chị Thu đọc lời chúc trên loa, tặng hai ông bà tấm thiệp', hint='Một phút thôi',
                       effects=dict(review=[5, 'Bốn mươi năm mới đi máy bay cùng nhau, cả khoang vỗ tay chúc mừng. Nhớ mãi.'], xp=6), good=True,
                       outcome='Cả khoang vỗ tay. Bà cụ đỏ mặt, ông cụ nắm tay bà không buông.'),
                  dict(id='skip', label='Chúc mừng nhỏ riêng hai ông bà', hint='Kín đáo', effects=dict(xp=3), good=None,
                       outcome='Hai ông bà cảm ơn, cười hiền.')],
         default='skip'),
    dict(id='phone', title='Điện thoại rơi vào khe ghế', emoji='📱', npc=HAI, min_day=3, tone='tense', at='between', weight=2,
         text='Chú Hải làm rơi điện thoại vào khe ghế, đang định ngả ghế để thò tay móc.',
         options=[dict(id='stop', label='Nhờ chú đừng ngả ghế, báo chị Thu và thợ máy lấy ra khi hạ cánh', hint='Ghế có cơ cấu, pin có thể bị kẹp',
                       effects=dict(xp=8), good=True, outcome='Hạ cánh xong, chú Mẫn tháo ghế lấy ra chiếc điện thoại nguyên vẹn.'),
                  dict(id='dig', label='Để chú tự móc cho nhanh', hint='Không mất công ai',
                       effects=dict(review=[2, 'Điện thoại bị kẹp dưới ghế, nóng ran, tổ bay phải cầm bình chữa cháy đứng chờ.']), good=False,
                       outcome='Ghế ngả kẹp trúng điện thoại, pin phồng lên nóng ran. Chị Thu phải xử lý như nguy cơ cháy.')],
         default='stop'),
    dict(id='front', title='Khách xin lên hàng đầu cho rộng', emoji='🎫', npc=KIET, min_day=2, tone='gentle', at='between', weight=2,
         text='Anh Kiệt thấy hàng 1 còn trống: “Cho anh lên đó ngồi, chân anh dài.” Tay anh đang bó bột.',
         options=[dict(id='rule', label='Giải thích hàng 1 cạnh cửa thoát hiểm, người bó bột không ngồi được; mời anh ghế lối đi', hint='Đúng quy định',
                       effects=dict(xp=6), good=True, outcome='Anh Kiệt gãi đầu: “Ừ, tay thế này mở cửa sao nổi.”'),
                  dict(id='ok', label='Cho anh lên, còn trống mà', hint='Khách vui',
                       effects=dict(review=[3, 'Tiếp viên cho khách bó bột ngồi hàng thoát hiểm, chị trưởng phải ra đổi lại.']), good=False,
                       outcome='Chị Thu đi ngang, nhẹ nhàng mời anh Kiệt về chỗ cũ.')],
         default='rule'),
    dict(id='baby', title='Bé Bơ khóc cả chuyến', emoji='👶', npc=MAI, min_day=2, tone='tense', at='between', weight=1,
         text='Bé Bơ khóc ngằn ngặt. Khách hàng sau bắt đầu thở dài, chị Mai luống cuống xin lỗi mọi người.',
         options=[dict(id='help', label='Mang nước ấm cho bé, chỉ chị Mai chỗ thay tã, nói với khách xung quanh vài lời', hint='Đỡ cho cả hai phía',
                       effects=dict(review=[5, 'Tiếp viên giúp tôi dỗ bé, còn nói đỡ với khách xung quanh. Tôi đỡ ngại hẳn.'], xp=6), good=True,
                       outcome='Bé Bơ nín dần. Ông khách hàng sau còn làm mặt hề cho bé cười.'),
                  dict(id='quiet', label='Nhắc chị Mai dỗ bé cho khách khác nghỉ', hint='Giữ yên khoang',
                       effects=dict(review=[2, 'Tôi đã cố hết sức, tiếp viên còn nhắc tôi làm phiền người khác.']), good=False,
                       outcome='Chị Mai rơm rớm nước mắt, bé càng khóc to.')],
         default='quiet'),
]

SITUATIONS = [
    dict(id='FA-S01', title='Bị quay phim đăng lên mạng', npc=VY, tone='tense', min_day=1,
         opening='Lúc bạn nhắc một khách tắt đèn đọc sách, Vy giơ điện thoại quay. Tối đó đoạn video lên mạng với dòng “tiếp viên thái độ”.',
         swap='Bạn là Vy: thấy cảnh ấy, tưởng tiếp viên đang làm khó khách.',
         facts=[dict(id='video', title='Đoạn video', source='Mạng xã hội', text='Video chỉ có tám giây, không có tiếng, cắt mất đoạn khách cãi trước.'),
                dict(id='rule', title='Quy định của hãng', source='Sổ tay tiếp viên', text='Tiếp viên không tự trả lời trên mạng. Báo trưởng khoang và phòng truyền thông.'),
                dict(id='witness', title='Người chứng kiến', source='Chị Thu', text='Chị Thu đứng cạnh và nghe hết từ đầu.')],
         options=[dict(id='report', label='Báo chị Thu và phòng truyền thông, kể đầu đuôi, không tự trả lời trên mạng', requires=['video', 'rule'], quality='good', stars=5,
                       review='Hãng đăng giải thích đầy đủ. Hóa ra tiếp viên chỉ nhắc nhẹ nhàng thôi. Tôi xin lỗi vì đã vội đăng.',
                       outcome='Phòng truyền thông đăng lời giải thích kèm lời kể của chị Thu. Vy tự gỡ video và nhắn xin lỗi.',
                       perspectives=[dict(who='Vy', emoji='📱', text='Tôi chỉ quay được một đoạn, đã vội nghĩ xấu.'),
                                     dict(who='Chị Thu', emoji='💁', text='Em im lặng đúng lúc, rồi báo đúng người.')]),
                  dict(id='reply', label='Tự vào bình luận giải thích cho rõ', quality='bad', stars=2,
                       review='Tiếp viên vào cãi tay đôi với khách trên mạng. Chuyện càng to.',
                       outcome='Bình luận của bạn bị chụp lại, chuyện thành “tiếp viên cãi khách”.',
                       perspectives=[dict(who='Phòng truyền thông', emoji='📰', text='Một bình luận nóng làm hỏng cả tuần dập lửa.'),
                                     dict(who='Vy', emoji='📱', text='Tôi đã định gỡ, nhưng giờ thì phải cãi cho bằng được.')]),
                  dict(id='ignore', label='Kệ, rồi người ta cũng quên', quality='ok', stars=3,
                       review='Không ai giải thích gì, nhiều người vẫn tin tiếp viên thái độ.',
                       outcome='Video lặng dần, nhưng vài khách quen nhìn bạn khác đi.',
                       perspectives=[dict(who='Chị Thu', emoji='💁', text='Lẽ ra em nên báo để hãng lên tiếng đúng cách.'),
                                     dict(who='Bà Chín', emoji='👵', text='Bà không tin cô tiếp viên như thế.')])],
         lesson='Bị quay phim oan thì giữ bình tĩnh, kể đầu đuôi cho đúng người; đừng cãi tay đôi trên mạng.'),
    dict(id='FA-S02', title='Đồng nghiệp đi bay khi đang sốt', npc=THU, tone='gentle', min_day=2,
         opening='Linh, tiếp viên mới, mặt đỏ bừng, ho khan. Linh nói nhỏ: “Chị đừng báo ai, em sợ bị trừ ngày công.”',
         swap='Bạn là Linh: mới vào nghề, sợ bị nghĩ là lười.',
         facts=[dict(id='fever', title='Tình trạng của Linh', source='Nhiệt kế', text='Linh sốt 38,5 độ, ho liên tục.'),
                dict(id='rule', title='Quy định', source='Sổ tay tiếp viên', text='Tiếp viên ốm được nghỉ, không bị trừ điểm. Có tiếp viên dự bị trực ở sân bay.'),
                dict(id='cabin', title='Chuyến bay', source='Chị Thu', text='Chuyến này kín khách, có mấy cụ già và em bé.')],
         options=[dict(id='tell', label='Nói với Linh quy định cho nghỉ ốm, cùng Linh báo chị Thu gọi người dự bị', requires=['fever', 'rule'], quality='good', stars=5,
                       review='Chị đi cùng em báo trưởng khoang, em không bị trách gì. Về ngủ một giấc là đỡ.',
                       outcome='Tiếp viên dự bị lên thay trong hai mươi phút. Linh về nghỉ, hai hôm sau đi bay lại.',
                       perspectives=[dict(who='Linh', emoji='🤒', text='Em cứ tưởng nghỉ ốm là bị đánh giá kém.'),
                                     dict(who='Chị Thu', emoji='💁', text='Người ốm mà gắng thì cả khoang chịu.')]),
                  dict(id='cover', label='Làm đỡ phần việc của Linh, để Linh ngồi nghỉ ở cuối khoang', quality='ok', stars=3,
                       review='Chị làm giúp em cả chuyến, em thương chị lắm. Nhưng em ho suốt, khách hàng cuối nhìn em ngại.',
                       outcome='Chuyến bay xong, nhưng khoang thiếu một người, ai cũng mệt.',
                       perspectives=[dict(who='Linh', emoji='🤒', text='Em vẫn thấy có lỗi với cả tổ.'),
                                     dict(who='Khách hàng cuối', emoji='🙎', text='Tiếp viên ho cả chuyến, tôi hơi lo.')]),
                  dict(id='silent', label='Không nói gì, chuyện của Linh', quality='bad', stars=2,
                       review='Tôi ngất ở khu bếp giữa chuyến bay. Giá mà có ai bảo tôi về nghỉ.',
                       outcome='Giữa chuyến Linh choáng, phải ngồi thở dưỡng khí. Cả khoang thiếu người phục vụ.',
                       perspectives=[dict(who='Chị Thu', emoji='💁', text='Lẽ ra chị phải biết sớm hơn.'),
                                     dict(who='Linh', emoji='🤒', text='Em sợ bị trừ công, giờ lại làm phiền cả tổ.')])],
         lesson='Đồng đội ốm thì nói với nhau quy định cho nghỉ, và báo trưởng khoang; gắng quá là rủi ro cho cả chuyến.'),
    dict(id='FA-S03', title='Chiếc ví bỏ quên dưới ghế', npc=HAI, tone='gentle', min_day=2,
         opening='Khách xuống hết, bạn nhặt được chiếc ví dày cộm dưới ghế 12A, trong có giấy tờ của chú Hải và một xấp tiền.',
         swap='Bạn là chú Hải: về tới nhà mới biết mất ví.',
         facts=[dict(id='rule', title='Đồ thất lạc', source='Sổ tay tiếp viên', text='Đồ khách để quên giao trưởng khoang, lập biên bản có hai người ký, chuyển quầy đồ thất lạc.'),
                dict(id='cash', title='Trong ví', source='Bạn đếm cùng chị Thu', text='Có căn cước của chú Hải, 1.200 xu và tấm ảnh cũ chụp một con tàu cá.'),
                dict(id='call', title='Chú Hải gọi tới', source='Quầy thủ tục', text='Chú Hải đang ở quầy thủ tục, hỏi có ai thấy ví không.')],
         options=[dict(id='log', label='Đếm cùng chị Thu, lập biên bản, trao lại chú Hải ở quầy có chữ ký', requires=['rule', 'cash'], quality='good', stars=5,
                       review='Ví về đủ từng xu, cả tấm ảnh con tàu của bố tôi. Hãng làm việc đàng hoàng quá.',
                       outcome='Chú Hải cầm ví, mở ra xem tấm ảnh trước cả tiền.',
                       perspectives=[dict(who='Chú Hải', emoji='🧓', text='Tiền thì kiếm lại được, tấm ảnh thì không.'),
                                     dict(who='Chị Thu', emoji='💁', text='Có biên bản thì không ai nghi ai.')]),
                  dict(id='hand', label='Chạy ra quầy đưa tận tay chú Hải luôn cho nhanh', quality='ok', stars=4,
                       review='Nhận lại ví nhanh lắm, cảm ơn cô. Mà hình như không ai đếm lại với tôi.',
                       outcome='Chú Hải nhận ví, nhưng không có biên bản; nếu thiếu gì cũng không ai nói được.',
                       perspectives=[dict(who='Chú Hải', emoji='🧓', text='Nhanh là quý, nhưng giá có tờ giấy thì chắc hơn.'),
                                     dict(who='Chị Thu', emoji='💁', text='Tốt bụng, nhưng quy trình để bảo vệ cả em.')]),
                  dict(id='keep', label='Rút bớt ít tiền, chắc chú không nhớ', quality='bad', stars=1, cost=20,
                       review='Ví về thiếu tiền. Tôi nhớ rõ từng tờ.',
                       outcome='Chú Hải đếm lại ngay ở quầy. Hãng mở điều tra, bạn phải bồi hoàn và bị kỷ luật.',
                       perspectives=[dict(who='Chú Hải', emoji='🧓', text='Tôi không tiếc tiền, tôi tiếc lòng tin.'),
                                     dict(who='Chị Thu', emoji='💁', text='Chị không bao giờ nghĩ em làm vậy.')])],
         lesson='Đồ của khách để quên: đếm có người chứng kiến, ghi biên bản, trao đúng người.'),
    dict(id='FA-S04', title='Khách đòi ngồi hàng thoát hiểm', npc=KIET, tone='tense', min_day=2,
         opening='Anh Kiệt đổi được vé hàng 17 cạnh cửa thoát hiểm. Tay trái anh bó bột tới khuỷu. “Anh trả thêm tiền chỗ này rồi đấy!”',
         swap='Bạn là anh Kiệt: trả thêm tiền để ngồi rộng chân, giờ bị mời đổi chỗ.',
         facts=[dict(id='rule', title='Hàng thoát hiểm', source='Sổ tay tiếp viên', text='Người ngồi cạnh cửa thoát hiểm phải mở được cửa nặng mười lăm ký khi cần.'),
                dict(id='arm', title='Tay của anh Kiệt', source='Nhìn thấy', text='Tay trái bó bột, không cầm nắm được.'),
                dict(id='seat', title='Ghế còn trống', source='Sơ đồ khoang', text='Còn ghế 4C lối đi, cũng rộng chân, gần cửa trước.')],
         options=[dict(id='swap', label='Giải thích vì sao, mời anh ghế 4C rộng chân, báo mặt đất hoàn phần tiền chênh', requires=['rule', 'arm', 'seat'], quality='good', stars=5,
                       review='Cô tiếp viên nói có lý, lại tìm cho tôi chỗ rộng chân. Tiền chênh cũng được hoàn.',
                       outcome='Anh Kiệt ngồi 4C, duỗi chân. Hàng 17 có một cậu thanh niên khỏe mạnh ngồi.',
                       perspectives=[dict(who='Anh Kiệt', emoji='💼', text='Tôi chỉ cần chỗ rộng, đâu cần đúng hàng đó.'),
                                     dict(who='Chị Thu', emoji='💁', text='Giữ quy định mà khách vẫn vui, vậy là khéo.')]),
                  dict(id='order', label='“Quy định không cho, anh đổi chỗ đi.”', requires=['rule'], quality='ok', stars=3,
                       review='Bắt đổi chỗ mà không giải thích, tiền tôi trả thêm thì sao?',
                       outcome='Anh Kiệt đổi chỗ, nhưng gửi phàn nàn về tiền chỗ ngồi.',
                       perspectives=[dict(who='Anh Kiệt', emoji='💼', text='Tôi không cãi quy định, tôi cần người nói cho ra lẽ.'),
                                     dict(who='Quầy thủ tục', emoji='🧾', text='Lỗi của chúng tôi khi bán chỗ đó. Lẽ ra phải hoàn tiền.')]),
                  dict(id='let', label='Cho anh ngồi, chắc không có chuyện gì đâu', quality='bad', stars=2,
                       review='Tiếp viên để người bó bột ngồi hàng thoát hiểm. Có chuyện thì ai mở cửa?',
                       outcome='Chị Thu đi kiểm khoang, phải tự mời anh Kiệt đổi chỗ ngay trước giờ cất cánh.',
                       perspectives=[dict(who='Chị Thu', emoji='💁', text='Hàng thoát hiểm là hàng của cả khoang.'),
                                     dict(who='Khách hàng 16', emoji='🙎', text='Tôi ngồi ngay sau, nghĩ tới mà rùng mình.')])],
         lesson='Hàng thoát hiểm dành cho người mở được cửa; giữ quy định và tìm cho khách một chỗ khác vừa ý.'),
    dict(id='FA-S05', title='Nhấc giúp vali nặng', npc=TU, tone='gentle', min_day=3,
         opening='Ông Tư chỉ chiếc vali nặng trịch: “Cháu nhấc lên hộc giúp ông, lưng ông đau.” Vali chừng hai mươi lăm ký.',
         swap='Bạn là ông Tư: lưng đau, không nhấc nổi vali.',
         facts=[dict(id='weight', title='Cái vali', source='Nhấc thử', text='Nặng khoảng hai mươi lăm ký, quá mức hành lý xách tay bảy ký.'),
                dict(id='back', title='An toàn cho tiếp viên', source='Sổ tay tiếp viên', text='Tiếp viên không một mình nhấc đồ quá nặng lên cao; vali quá khổ gửi khoang hàng.'),
                dict(id='hold', title='Khoang hàng', source='Nhân viên mặt đất', text='Vẫn kịp gửi vali xuống khoang hàng, miễn phí cho hành lý quá khổ ở cửa tàu.')],
         options=[dict(id='hold', label='Gửi vali xuống khoang hàng miễn phí, dặn ông lấy ở băng chuyền', requires=['weight', 'hold'], quality='good', stars=5,
                       review='Cô tiếp viên cho gửi vali ở cửa tàu, không mất đồng nào. Ông nhẹ cả người.',
                       outcome='Vali xuống khoang hàng, ông Tư ngồi thoải mái cả chuyến.',
                       perspectives=[dict(who='Ông Tư', emoji='👴', text='Ông cứ ngại làm phiền người ta.'),
                                     dict(who='Chị Thu', emoji='💁', text='Lưng em còn phải bay mấy chục năm nữa.')]),
                  dict(id='two', label='Gọi thêm một đồng nghiệp, hai người cùng nhấc', requires=['back'], quality='ok', stars=4,
                       review='Hai cô nhấc giúp, vất vả quá. Hộc hành lý chật cứng.',
                       outcome='Vali lên hộc, nhưng chiếm chỗ của ba khách khác.',
                       perspectives=[dict(who='Đồng nghiệp', emoji='💁', text='Nặng thật, may mà có hai người.'),
                                     dict(who='Khách hàng 7', emoji='🙎', text='Tôi không còn chỗ để túi.')]),
                  dict(id='alone', label='Tự nhấc một mình cho nhanh', quality='bad', stars=3,
                       review='Cô tiếp viên nhấc giúp tôi, mà tôi thấy cô nhăn mặt ôm lưng.',
                       outcome='Bạn đau lưng suốt ba ngày, phải nghỉ bay.',
                       perspectives=[dict(who='Ông Tư', emoji='👴', text='Ông áy náy quá.'),
                                     dict(who='Chị Thu', emoji='💁', text='Giúp khách không có nghĩa là liều cái lưng của mình.')])],
         lesson='Giúp khách đúng cách: vali quá nặng gửi khoang hàng, đừng một mình nhấc đồ nặng lên cao.'),
]


# ================================================================ small helpers
def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


# ================================================================ tasks
def _kind(day: int, slot: int, mod: str) -> str:
    if slot == 0:
        return 'board'
    if day == 1:
        return ('board', 'demo', 'service')[slot % 3]
    if slot == 2:
        return 'service'
    if slot == 1 and day in (2, 3):
        return 'calm' if day == 2 else 'medical'     # the first difficult passenger, then the first one taken ill
    deck = ['demo', 'calm', 'medical', 'calm', 'demo', 'medical']
    kit.rng(ID, 'deck', day).shuffle(deck)
    if slot == 1:
        return deck[0]
    more = ['medical', 'calm', 'service', 'board', 'demo']
    kit.rng(ID, 'more', day).shuffle(more)
    return more[(slot - 3) % len(more)]


def _board(r, day: int, mod: str) -> tuple[list, int]:
    """Four passengers at the door; returns (queue, the reviewer's npc index)."""
    issues = [None, 'bag', None, None] if day == 1 else [None, None] + r.sample(['bag', 'wrong', 'exit', 'power'], 2)
    if day > 1:
        if mod == 'busy' and 'bag' not in issues:
            issues[1] = 'bag'
        r.shuffle(issues)
        if issues[0] is not None and None in issues:   # the first one at the door is a plain one: time to say hello
            i = issues.index(None)
            issues[0], issues[i] = issues[i], issues[0]
    queue, used = [], set()
    for issue in issues:
        pool = [b for b in BOARDERS if b[3] == issue and b[1] not in used] or [b for b in BOARDERS if b[3] == issue]
        npc, who, bag, _, say = pool[r.randrange(len(pool))]
        used.add(who)
        row = r.choice(air.EXIT_ROWS) if issue == 'exit' else r.randint(2, air.ROWS - 1)
        s = f'{row}{r.choice(air.SEATS)}'
        queue.append(dict(npc=npc, who=who, seat=s, bag=bag, say=say.format(seat=s), issue=issue))
    notable = next((q['npc'] for q in queue if q['issue'] and q['npc'] is not None), None)
    return queue, notable if notable is not None else next((q['npc'] for q in queue if q['npc'] is not None), CHIN)


def _cabin(r, day: int) -> dict:
    r0 = r.randint(3, air.ROWS - 3)
    rows = [r0, r0 + 1, r0 + 2]
    kinds = ['belt', 'tray'] if day == 1 else r.sample(['belt', 'tray', 'recline', 'bag', 'shade'], r.choice((2, 3)))
    seats = [f'{row}{x}' for row in rows for x in air.SEATS]
    bad = r.sample(seats, len(kinds))
    return dict(rows=rows, state={s: (kinds[bad.index(s)] if s in bad else 'ok') for s in seats})


def _service(r, day: int, mod: str) -> dict:
    r0 = r.randint(2, air.ROWS - 3)
    rows = []
    specials = dict(veg=None, nut=None)
    want_kid = day == 1 or r.random() < (0.8 if mod == 'family' else 0.45)
    want_sleep = day > 1 and r.random() < (0.8 if mod == 'early' else 0.3)
    want_nut = day > 1 and r.random() < 0.45
    all_seats = []
    for i in range(3):
        row = r0 + i
        n = r.randint(2, 4)
        letters = sorted(r.sample(list(air.SEATS), n))
        seats = []
        for x in letters:
            drink = r.choice(DRINK_IDS)
            snack = r.choice(('banhmi', 'cake', 'nuts', None))
            seats.append(dict(seat=f'{row}{x}', who='Khách', drink=drink, snack=snack, kind=None))
        rows.append(dict(row=row, seats=seats))
        all_seats += seats
    # The purser's list and the cabin's special cases, each on its own seat.
    free = list(all_seats)
    r.shuffle(free)
    veg = free.pop()
    veg.update(snack='banhmi', kind='veg')
    specials['veg'] = veg['seat']
    if want_kid and free:
        k = free.pop()
        k.update(who='Em bé', drink=r.choice(('tea', 'coffee')), kind='kid')
    if want_sleep and free:
        z = free.pop()
        z.update(who='Khách đang ngủ', kind='sleep')
    if want_nut:
        rowd = next((x for x in rows if len([s for s in x['seats'] if s['kind'] is None]) >= 2), None)
        if rowd:
            plain = [s for s in rowd['seats'] if s['kind'] is None]
            for x in rowd['seats']:
                if x['snack'] == 'nuts':
                    x['snack'] = 'cake'      # in the allergy row only one passenger still asks for peanuts
            plain[0].update(kind='allergy', snack='cake')
            plain[1].update(snack='nuts', kind='nutrow')
            specials['nut'] = rowd['row']
            specials['allergic'] = plain[0]['seat']
    for x in rows:
        for s in x['seats']:
            s['say'] = _order_line(s)
    return dict(rows=rows, ssr=specials)


def _order_line(s: dict) -> str:
    d = ITEM[s['drink']]['name'].lower()
    if s['kind'] == 'sleep':
        return 'Khách đang ngủ say, gối đầu vào cửa sổ.'
    if s['kind'] == 'kid':
        return f'“Con muốn uống {d} giống bố!”'
    if s['kind'] == 'veg':
        return f'“Cho chị phần ăn với ly {d} nhé.”'
    if s['kind'] == 'allergy':
        return f'“Cho tôi {d} với bánh bông lan. Tôi dị ứng đậu phộng đấy.”'
    snack = ITEM[s['snack']]['name'].lower() if s['snack'] else None
    return f'“Cho tôi {d}' + (f' với {snack}.”' if snack else '.”')


def right_items(s: dict) -> list:
    """What this seat should get (the rules: special meals, peanut row, children, sleepers)."""
    if s['kind'] == 'sleep':
        return []
    drink = 'juice' if s['kind'] == 'kid' and s['drink'] in HOT else s['drink']
    snack = s['snack']
    if s['kind'] == 'veg':
        snack = 'veg'
    elif s['kind'] == 'nutrow':
        snack = 'cake'
    return [drink] + ([snack] if snack else [])


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    kind = _kind(day, slot, mod)
    leg = air.leg(day, slot)
    r = kit.rng(ID, day, slot)
    common = dict(gen=GEN, stage='work', step=0, done=[], wrong=[], given={}, skipped=[], row=0, walked=False, fixed=[], answers=[],
                  used=[], choices=[], ready=False, story=None)
    if kind == 'board':
        queue, npc = _board(r, day, mod)
        needs = dict(leg=leg, queue=queue)
        title = f'Đón khách chuyến {leg["code"]}'
        opening = f'Chị Thu mở cửa tàu: “Chuyến {leg["code"]} đi {leg["to"]}, khách lên rồi đấy em. Xem kỹ thẻ lên tàu nhé.”'
    elif kind == 'demo':
        needs = dict(leg=leg, cabin=_cabin(r, day))
        npc = THU
        title = f'Hướng dẫn an toàn · {leg["code"]}'
        opening = 'Chị Thu đưa bạn áo phao mẫu: “Làm mẫu theo đúng thẻ nhé. Xong đi dọc lối kiểm tra khoang.”'
    elif kind == 'service':
        needs = dict(leg=leg, **_service(r, day, mod))
        cand = [CHIN, KIET, TU, HAI, VY]
        npc = cand[r.randrange(len(cand))]
        title = f'Đẩy xe phục vụ · {leg["code"]}'
        opening = f'Chị Thu đẩy xe ra: “Em lo hàng {needs["rows"][0]["row"]} tới {needs["rows"][-1]["row"]}. Phiếu suất ăn đặc biệt đây.”'
    elif kind == 'calm':
        script = CALM_IDS[r.randrange(len(CALM_IDS))]
        needs = dict(leg=leg, script=script)
        npc = CALM[script]['npc']
        title = CALM[script]['title']
        opening = CALM[script]['beats'][0]['text']
    else:
        case = CASE_IDS[r.randrange(len(CASE_IDS))]
        needs = dict(leg=leg, case=case)
        npc = CASES[case]['npc']
        title = CASES[case]['title']
        opening = CASES[case]['seen']
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind=kind, needs=needs, **common)


FIXED = ('needs',)


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'demo':
        # The demonstration is the purser's job for you, not a customer's order: nothing to ask.
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the career's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, jobs=0, pax=0, served=0, fixed=0, turb=0, medical=0)


def initial() -> dict:
    return dict(v=1, intro=False, stats=dict(jobs=0, pax=0, served=0, fixed=0, calm=0, medical=0, turb_ok=0, turb_late=0),
                log=[], regulars={}, arc=dict(seen=[], due=None), turb=None, turbs=[], today=_fresh_today(0), desk=kit.desk_initial(),
                odd=ao.initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k, v in base['stats'].items():
        d['stats'].setdefault(k, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    ao.ensure(d)
    return d


# The words of the encounters (air_odd): who to bring in, the office, the rank lost on a demotion.
CFG = dict(crew='Báo chị Thu', company='Báo phòng an toàn', union='Nhờ công đoàn', office='Phòng điều hành',
           demoted='tiếp viên dự bị', title='tiếp viên')


def _pressure(c: dict, d: dict) -> int:
    """How hard the airline leans on its crew today: the season, and a player who snapped at the office."""
    marks = d['odd']['marks']
    return {'busy': 2, 'rough': 1, 'family': 1}.get(mod_of(c['day'])['id'], 0) + ('strained' in marks) + ('kpi_black' in marks)


# ================================================================ the actions
FREE = ('fa_intro', 'fa_arc', 'fa_rest')
NO_TICK = ('fa_intro', 'fa_arc', 'fa_desk', 'fa_door', 'fa_demo', 'fa_fix', 'fa_give', 'fa_skip', 'fa_secure', 'fa_turb_end',
           'fa_calm', 'fa_ask', 'fa_care', 'fa_odd', 'fa_rest')
PHYSICAL = ('fa_door', 'fa_give', 'fa_fix', 'fa_care')
TURB_OK = ('fa_secure', 'fa_turb_end', 'fa_intro', 'fa_arc')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'fa_intro':
        d['intro'] = True
        return dict(message='Vào ca thôi! Chị Thu đang chờ ở cửa tàu.')
    if name == 'fa_arc':
        return _arc_seen(d)
    tb = d['turb']
    if tb and tb['stage'] == 'coming' and name not in TURB_OK:
        if kit.now() > tb['start'] + tb['limit']:
            _turb_resolve(s, c, d)
        else:
            kit.need(False, 'Đèn thắt dây đang sáng! Cất xe, về ghế trước đã.', 'turbulence')
    odd = d['odd']
    if name == 'fa_rest':
        return ao.rest(s, c, odd, p, _pressure(c, d), CFG)
    desk = d['desk']
    if name == 'fa_desk':
        result = kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
        _odd_tick(s, c, d, result)
        return result
    if name == 'fa_odd':
        result = ao.reply(s, c, ID, odd, ODD, p, CFG, _pressure(c, d))
        if odd['ev'] is None:
            _odd_tick(s, c, d, result)
        return result
    if name not in ('fa_secure', 'fa_turb_end'):
        kit.desk_block(desk, 'Có chuyện trong khoang, quyết xong rồi làm tiếp nhé.')
        ao.block(odd, 'Có người đang chờ bạn trả lời, xong rồi làm tiếp nhé.')
        kit.need(not ao.grounded(c, odd), 'Bạn đang tạm đình chỉ bay hết hôm nay. Tan ca, mai lên phòng an toàn trình bày.', 'grounded')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có trong khoang khách.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    _arc_tick(c, d)
    if d['turb'] and d['turb']['stage'] == 'coming':
        return
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
    """Someone around the job turns up when today's plan says so (never over a desk surprise or the belt sign)."""
    tb = d['turb']
    x = ao.tick(s, c, ID, d['odd'], ODD, busy=d['desk']['ev'] is not None or bool(tb and tb['stage'] == 'coming'))
    if x:
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: trả lời giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kind: str | tuple) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc khoang khách.')
    kit.need(t['kind'] in ((kind,) if isinstance(kind, str) else kind), 'Thao tác này không dành cho việc đang làm.')
    kit.need(t['known'], 'Hỏi chuyện khách trước đã nhé.' if t['kind'] != 'service' else 'Nhận phiếu suất ăn đặc biệt trước đã.')
    kit.need(t['stage'] == 'work', 'Việc này đã xong.')
    return t


def _miss(t: dict, code: str, sev: int, text: str, note: str, message: str, safety: bool = False) -> dict:
    t['mistakes'] += 1
    cq.slip(t, code, sev, text, note, safety=safety)
    return dict(message=message, correct=False)


# ---------------------------------------------------------------- boarding
def _door(s, c, d, p):
    t = _task(c, p, 'board')
    q = t['needs']['queue']
    kit.need(t['step'] < len(q), 'Khách đã lên đủ. Đóng cửa khoang thôi.')
    act = kit.one_of(p.get('act'), DOOR_IDS, 'Chọn cách giúp khách.')
    x = q[t['step']]
    kit.start_work(t)
    want = ISSUE_ACT[x['issue']]
    if act != want:
        t['wrong'] = (t['wrong'] + [t['step']])[-8:]
        if x['issue'] == 'power' and act == 'hold':
            return _miss(t, 'power', 3, 'Vali có pin sạc dự phòng mà vẫn gửi xuống khoang hàng.', 'gửi pin sạc xuống khoang hàng',
                         '✋ Chị Thu kéo vali lại: “Pin sạc dự phòng phải mang theo người, không được gửi khoang hàng. Dễ cháy lắm!”', safety=True)
        if x['issue'] == 'exit':
            return _miss(t, 'exit', 2, f'{x["who"]} được ngồi hàng thoát hiểm dù không mở nổi cửa.', 'xếp sai người vào hàng thoát hiểm',
                         f'✋ Chị Thu: “Ghế {x["seat"]} cạnh cửa thoát hiểm. {x["who"]} không mở được cửa nặng: mời sang ghế khác nhé.”')
        if x['issue'] == 'bag':
            return _miss(t, 'bag', 1, 'Vali to nhét mãi không vừa hộc, lối đi tắc cả chục người.', 'để vali quá khổ lên hộc',
                         '🧳 Vali không vừa hộc, nhét mãi không đóng được. Lối đi bắt đầu tắc.')
        if x['issue'] == 'wrong':
            return _miss(t, 'wrong_seat', 1, 'Ghế của khách bị người khác ngồi mà tiếp viên không xử lý.', 'không xếp khách về đúng ghế',
                         f'🎫 {x["who"]} vẫn đứng giữa lối: ghế {x["seat"]} đang có người ngồi nhầm. Mời người ngồi nhầm về đúng ghế đi.')
        return _miss(t, 'fuss', 1, 'Khách chỉ hỏi chỗ ngồi mà tiếp viên làm rối cả lên.', 'làm phiền khách không cần thiết',
                     f'🙂 {x["who"]} ngơ ngác: “Chị chỉ hỏi ghế {x["seat"]} thôi mà.”')
    t['done'].append(t['step'])
    t['step'] += 1
    d['today']['pax'] += 1
    d['stats']['pax'] += 1
    msg = {'seat': f'👉 “Mời {_lower(x["who"])} ghế {x["seat"]}, {air.seat_side(x["seat"])}.”',
           'hold': f'🏷️ Dán thẻ gửi khoang hàng cho vali của {_lower(x["who"])}, trả lại cuống thẻ.',
           'move': (f'🔁 Mời {_lower(x["who"])} sang ghế lối đi phía trên, giải thích hàng cạnh cửa thoát hiểm cần người mở được cửa.' if x['issue'] == 'exit'
                    else f'🔁 Xem lại thẻ: người ngồi nhầm về đúng ghế của mình. {x["who"]} ngồi ghế {x["seat"]}.'),
           'battery': f'🔋 Lấy pin sạc ra để {_lower(x["who"])} mang theo người, rồi mới gửi vali xuống khoang hàng.'}[act]
    if t['step'] >= len(q):
        msg += ' ✅ Khách lên đủ. Đóng cửa khoang nhé.'
    return dict(message=msg)


def _close(s, c, d, p):
    t = _task(c, p, 'board')
    q = t['needs']['queue']
    kit.need(t['step'] >= len(q), f'Còn {len(q) - t["step"]} khách ở cửa.')
    return _finish(s, c, d, t, f'Đón {len(q)} khách chuyến {t["needs"]["leg"]["code"]}.', '🚪 Đóng cửa khoang. Chị Thu gật đầu: “Gọn gàng.”')


# ---------------------------------------------------------------- the safety demonstration and the cabin check
def _demo(s, c, d, p):
    t = _task(c, p, 'demo')
    kit.need(t['step'] < len(DEMO), 'Đã làm mẫu xong.')
    part = kit.one_of(p.get('part'), DEMO_IDS, 'Phần này không có trong thẻ hướng dẫn.')
    kit.start_work(t)
    x = DEMO[t['step']]
    if part != x['id']:
        return _miss(t, 'demo_order', 1, 'Làm mẫu an toàn lộn thứ tự, khách nhìn không hiểu.', 'làm mẫu sai thứ tự',
                     f'✋ Chị Thu đọc tới phần “{x["name"]}”. Làm mẫu theo đúng thẻ nhé.')
    t['step'] += 1
    return dict(message=f'{x["emoji"]} “{x["line"]}”' + (' ✅ Xong phần làm mẫu. Giờ đi dọc lối kiểm tra.' if t['step'] == len(DEMO) else ''))


def _walk(s, c, d, p):
    t = _task(c, p, 'demo')
    kit.need(t['step'] >= len(DEMO), 'Làm mẫu xong đã rồi hãy đi kiểm tra.')
    kit.need(not t['walked'], 'Đã đi kiểm tra rồi.')
    t['walked'] = True
    bad = [k for k, v in t['needs']['cabin']['state'].items() if v != 'ok']
    return dict(message=f'🚶 Đi dọc lối hàng {t["needs"]["cabin"]["rows"][0]} tới {t["needs"]["cabin"]["rows"][-1]}: thấy {len(bad)} chỗ chưa sẵn sàng.')


def _fix(s, c, d, p):
    t = _task(c, p, 'demo')
    kit.need(t['walked'], 'Đi dọc lối kiểm tra trước đã.')
    st = t['needs']['cabin']['state']
    seat = kit.one_of(p.get('seat'), st, 'Ghế này không ở đoạn bạn kiểm.')
    kit.need(seat not in t['fixed'], 'Ghế này đã sẵn sàng.')
    kit.need(st[seat] != 'ok', f'Khách ghế {seat} đã sẵn sàng rồi.')
    t['fixed'].append(seat)
    d['today']['fixed'] += 1
    d['stats']['fixed'] += 1
    return dict(message=f'{CABIN[st[seat]]["emoji"]} Ghế {seat}: {FIX_LINE[st[seat]]}')


def _ready(s, c, d, p):
    t = _task(c, p, 'demo')
    kit.need(t['step'] >= len(DEMO), 'Chưa làm mẫu xong.')
    kit.need(t['walked'], 'Đi dọc lối kiểm tra trước đã.')
    st = t['needs']['cabin']['state']
    left = [k for k, v in st.items() if v != 'ok' and k not in t['fixed']]
    for seat in left:
        what = st[seat]
        if what == 'belt':
            cq.slip(t, 'belt', 3, f'Khách ghế {seat} chưa thắt dây mà khoang đã báo sẵn sàng cất cánh.', 'bỏ sót khách chưa thắt dây', safety=True)
        elif what == 'bag':
            cq.slip(t, 'aisle_bag', 2, f'Túi ở lối đi ghế {seat} lúc cất cánh, ai cũng có thể vấp.', 'để túi ở lối đi khi cất cánh')
        else:
            cq.slip(t, 'cabin_' + what, 1, f'Ghế {seat}: {_lower(CABIN[what]["name"])} lúc cất cánh.', 'khoang chưa sẵn sàng')
    if left:
        t['mistakes'] += len(left)
    head = '📞 “Buồng lái, khoang khách sẵn sàng.”' + (f' ⚠️ Còn sót {len(left)} ghế chưa sẵn sàng, chị Thu phải chạy lại xử lý.' if left else '')
    return _finish(s, c, d, t, f'Làm mẫu an toàn và kiểm tra khoang chuyến {t["needs"]["leg"]["code"]}.', head)


# ---------------------------------------------------------------- the cart
def _row(t: dict) -> dict:
    return t['needs']['rows'][t['row']]


def _seat(t: dict, sid) -> dict:
    s = next((x for x in _row(t)['seats'] if x['seat'] == sid), None)
    kit.need(s, 'Ghế này không ở hàng đang phục vụ.')
    return s


def _left_items(t: dict, s: dict) -> list:
    got = list(t['given'].get(s['seat'], []))
    out = []
    for it in right_items(s):
        if it in got:
            got.remove(it)
        else:
            out.append(it)
    return out


def _row_done(t: dict) -> bool:
    return all(not _left_items(t, s) or s['seat'] in t['skipped'] for s in _row(t)['seats'])


def _give(s, c, d, p):
    t = _task(c, p, 'service')
    st = _seat(t, p.get('seat'))
    item = kit.one_of(p.get('item'), ITEM, 'Trên xe không có món này.')
    kit.need(st['seat'] not in t['skipped'], 'Ghế này đã để khách ngủ.')
    kit.start_work(t)
    who = 'em bé' if st['kind'] == 'kid' else 'khách'
    if st['kind'] == 'sleep':
        t['skipped'].append(st['seat'])
        return _miss(t, 'woke', 1, 'Khách đang ngủ bị đánh thức chỉ để mời nước.', 'đánh thức khách đang ngủ',
                     f'😪 Khách ghế {st["seat"]} giật mình tỉnh giấc, xua tay: “Để tôi ngủ…”')
    if item == 'nuts' and t['needs']['ssr'].get('nut') == _row(t)['row']:
        return _miss(t, 'nut', 3, f'Phát đậu phộng ở hàng {_row(t)["row"]} dù có khách dị ứng đậu phộng.', 'phát đậu phộng cạnh khách dị ứng',
                     f'✋ Chị Thu giữ tay bạn lại: “Hàng {_row(t)["row"]} có khách dị ứng đậu phộng! Mời bánh bông lan thay nhé.”', safety=True)
    if item in HOT and st['kind'] == 'kid':
        return _miss(t, 'hot_kid', 2, 'Tiếp viên suýt đưa ly nước nóng cho em bé.', 'đưa đồ uống nóng cho trẻ nhỏ',
                     '✋ Chị Thu đỡ lấy ly: “Trẻ nhỏ không uống đồ nóng, dễ bỏng lắm. Mời bé nước cam nhé.”')
    left = _left_items(t, st)
    kit.need(item in left or item not in right_items(st), f'Ghế {st["seat"]} đã có {ITEM[item]["name"].lower()} rồi.')
    if item not in left:
        if st['kind'] == 'veg' and item == 'banhmi':
            return _miss(t, 'veg', 2, f'Khách ghế {st["seat"]} đặt suất chay mà suýt nhận bánh mì pa-tê.', 'nhầm suất ăn chay',
                         f'🥬 Khách ghế {st["seat"]} xua tay: “Chị đặt suất chay mà em!” Kiểm lại phiếu suất ăn đặc biệt nhé.')
        return _miss(t, 'wrong', 1, f'Mang nhầm món cho ghế {st["seat"]}.', 'mang nhầm món',
                     f'🙅 Ghế {st["seat"]}: “Tôi không gọi {ITEM[item]["name"].lower()}.”')
    t['given'][st['seat']] = (t['given'].get(st['seat'], []) + [item])[:3]
    d['today']['served'] += 1
    d['stats']['served'] += 1
    msg = f'{ITEM[item]["emoji"]} Mời {who} ghế {st["seat"]} {ITEM[item]["name"].lower()}.'
    if _row_done(t):
        msg += ' ✅ Xong hàng này.' if t['row'] < len(t['needs']['rows']) - 1 else ' ✅ Xong hàng cuối.'
    return dict(message=msg)


def _skip(s, c, d, p):
    t = _task(c, p, 'service')
    st = _seat(t, p.get('seat'))
    kit.need(st['seat'] not in t['skipped'], 'Đã để khách này nghỉ.')
    kit.need(st['kind'] == 'sleep', f'Khách ghế {st["seat"]} đang chờ đồ uống.')
    t['skipped'].append(st['seat'])
    return dict(message=f'😴 Để khách ghế {st["seat"]} ngủ, dán mẩu giấy “Bấm chuông khi cần nhé”.')


def _next(s, c, d, p):
    t = _task(c, p, 'service')
    kit.need(t['row'] < len(t['needs']['rows']) - 1, 'Đây là hàng cuối. Cất xe thôi.')
    missed = [x['seat'] for x in _row(t)['seats'] if _left_items(t, x) and x['seat'] not in t['skipped']]
    if missed:
        t['mistakes'] += 1
        cq.slip(t, f'missed_{_row(t)["row"]}', 1, f'Hàng {_row(t)["row"]} bị bỏ sót: ghế {", ".join(missed)} chưa có đồ.', 'bỏ sót khách khi phục vụ')
    t['row'] += 1
    msg = f'🛒 Đẩy xe lên hàng {_row(t)["row"]}.'
    if _turb_tick(s, c, d, t):
        msg += ' 〰️ Đèn thắt dây bật sáng, tàu bắt đầu rung! Cất xe, về ghế ngay!'
        return dict(message=msg, surprise=True)
    return dict(message=msg)


def _stow(s, c, d, p):
    t = _task(c, p, 'service')
    kit.need(t['row'] == len(t['needs']['rows']) - 1, 'Còn hàng chưa phục vụ.')
    missed = [x['seat'] for x in _row(t)['seats'] if _left_items(t, x) and x['seat'] not in t['skipped']]
    if missed:
        t['mistakes'] += 1
        cq.slip(t, f'missed_{_row(t)["row"]}', 1, f'Hàng {_row(t)["row"]} bị bỏ sót: ghế {", ".join(missed)} chưa có đồ.', 'bỏ sót khách khi phục vụ')
    n = sum(len(x['seats']) for x in t['needs']['rows'])
    return _finish(s, c, d, t, f'Phục vụ {n} khách hàng {t["needs"]["rows"][0]["row"]}–{t["needs"]["rows"][-1]["row"]}.',
                   '🛒 Thu ly, cất xe vào bếp, khóa phanh.')


# ---------------------------------------------------------------- turbulence (timed)
def turb_plan(day: int) -> int | None:
    """Seconds to secure the cabin if the belt sign comes on during today's first service, else None."""
    if day < 2:
        return None
    if day == 2:
        return TURB_FIRST
    p = 0.6 if mod_of(day)['id'] == 'rough' else 0.35
    return TURB_LATER if kit.rng(ID, 'turb', day).random() < p else None


def _turb_tick(s: dict, c: dict, d: dict, t: dict) -> bool:
    limit = turb_plan(c['day'])
    if not limit or d['desk']['ev'] is not None:
        return False
    if any(x['day'] == c['day'] for x in d['turbs']) or (d['turb'] and d['turb']['day'] == c['day']):
        return False
    d['turb'] = dict(day=c['day'], task=t['id'], stage='coming', start=kit.now(), limit=limit, done=[], result=None)
    kit.log(s, c, 'surprise', '〰️ Đèn thắt dây bật sáng giữa lúc đang phục vụ. Cơ trưởng: “Tiếp viên về ghế.”', kit.npc_id(ID, VAN), f'turb-{c["day"]}')
    return True


def _secure(s, c, d, p):
    tb = d['turb']
    kit.need(tb and tb['stage'] == 'coming', 'Tàu đang êm, không cần cất xe.')
    what = kit.one_of(p.get('what'), SECURE_IDS, 'Làm gì trước?')
    if kit.now() > tb['start'] + tb['limit']:
        return _turb_resolve(s, c, d)
    kit.need(what not in tb['done'], 'Việc này xong rồi.')
    tb['done'].append(what)
    if set(tb['done']) == set(SECURE_IDS):
        return _turb_resolve(s, c, d)
    x = next(r for r in SECURE if r['id'] == what)
    return dict(message=f'{x["emoji"]} {x["name"]}: xong. Còn {len(SECURE_IDS) - len(tb["done"])} việc!')


def _turb_end(s, c, d, p):
    tb = d['turb']
    kit.need(tb and tb['stage'] == 'coming', 'Tàu đang êm.')
    kit.need(kit.now() >= tb['start'] + tb['limit'] - 1, 'Vẫn còn thời gian, cất xe nhanh lên!')
    return _turb_resolve(s, c, d)


def _turb_resolve(s: dict, c: dict, d: dict) -> dict:
    tb = d['turb']
    miss = [x for x in SECURE_IDS if x not in tb['done']]
    t = next((x for x in c['tasks'] if x['id'] == tb['task']), None)
    if t is not None and t['status'] not in ('completed', 'referred', 'cancelled') and miss:
        t['mistakes'] += 1
        if 'hot' in miss:
            cq.slip(t, 'spill', 2, 'Nước nóng trên xe đổ trúng tay khách khi tàu rung.', 'không cất bình nước nóng khi rung lắc')
        if 'brake' in miss:
            cq.slip(t, 'cart', 2, 'Xe đẩy không khóa phanh trôi dọc lối, va vào đầu gối khách.', 'không khóa phanh xe đẩy')
        if 'sit' in miss:
            cq.slip(t, 'stand', 1, 'Tiếp viên còn đứng giữa lối khi tàu rung mạnh.', 'không về ghế khi rung lắc')
    tb.update(stage='done', result=dict(miss=len(miss)))
    d['turbs'] = ar.last(d['turbs'] + [dict(day=c['day'], miss=len(miss))], 20, 'flight_attendant.turbs', c)
    d['today']['turb'] += 1
    if miss:
        d['stats']['turb_late'] += 1
        names = ', '.join(_lower(next(r['name'] for r in SECURE if r['id'] == x)) for x in miss)
        msg = f'〰️ Tàu rung mạnh khi chưa kịp {names}. Tàu êm lại rồi, xử lý xong thì phục vụ tiếp.'
        kit.log(s, c, 'surprise', msg, kit.npc_id(ID, THU), f'turb-{c["day"]}')
        return dict(message=msg, correct=False)
    d['stats']['turb_ok'] += 1
    c['xp'] += 8
    msg = '✅ Xe đã khóa, bình nóng đã cất, bạn ngồi thắt dây kịp lúc tàu rung. Năm phút sau đèn tắt, phục vụ tiếp!'
    kit.log(s, c, 'surprise', 'Cất xe, về ghế kịp lúc tàu rung. Không ai bị gì.', kit.npc_id(ID, THU), f'turb-{c["day"]}')
    return dict(message=msg, celebrate=True)


# ---------------------------------------------------------------- a difficult passenger
def _calm(s, c, d, p):
    t = _task(c, p, 'calm')
    x = CALM[t['needs']['script']]
    kit.need(t['step'] < len(x['beats']), 'Đã nói chuyện xong.')
    beat = x['beats'][t['step']]
    opt = kit.one_of(p.get('option'), [o['id'] for o in beat['options']], 'Chọn một cách nói.')
    kit.start_work(t)
    o = next(o for o in beat['options'] if o['id'] == opt)
    t['choices'].append(opt)
    t['step'] += 1
    n = t['step']
    if o['grade'] == 'ok':
        t['mistakes'] += 1
        cq.slip(t, f'calm_{n}', 1, 'Tiếp viên nói chưa khéo, khách vẫn chưa vui.', 'nói chưa khéo')
    elif o['grade'] == 'bad':
        t['mistakes'] += 1
        serious = x.get('serious') and n != 2
        cq.slip(t, f'calm_{n}', 3 if serious else 2, 'Chuyện có thể nguy hiểm mà tiếp viên bỏ qua.' if serious else 'Tiếp viên làm khách bực thêm.',
                'bỏ qua chuyện an toàn' if serious else 'làm khách bực thêm', safety=bool(serious))
    msg = f'💬 {o["reply"]}'
    if t['step'] >= len(x['beats']):
        d['stats']['calm'] += 1
        return _finish(s, c, d, t, f'Giữ bình tĩnh với khách: {x["title"].lower()}.', msg)
    return dict(message=msg, correct=False) if o['grade'] == 'bad' else dict(message=msg)


# ---------------------------------------------------------------- a passenger taken ill
def _ask(s, c, d, p):
    t = _task(c, p, 'medical')
    q = kit.one_of(p.get('q'), Q_IDS, 'Câu hỏi không hợp lệ.')
    kit.need(q not in t['answers'], 'Đã hỏi rồi.')
    kit.start_work(t)
    t['answers'].append(q)
    return dict(message=f'🗣️ {CASES[t["needs"]["case"]]["answers"][q]}')


def _care(s, c, d, p):
    t = _task(c, p, 'medical')
    item = kit.one_of(p.get('item'), KIT_IDS, 'Trong túi sơ cứu không có thứ này.')
    kit.need(item not in t['used'], 'Đã làm rồi.')
    kit.start_work(t)
    t['used'].append(item)
    x = next(k for k in KIT if k['id'] == item)
    if item == 'own_med':
        return _miss(t, 'own_med', 3, 'Tiếp viên đưa thuốc của mình cho khách uống, không biết khách bị gì.', 'tự đưa thuốc cho khách',
                     '✋ Chị Thu ngăn lại: “Không bao giờ đưa thuốc của mình. Mình không phải bác sĩ.”', safety=True)
    line = {'water': 'Rót ly nước ấm, đưa khách uống từng ngụm.', 'juice': 'Mở hộp nước cam, đưa khách uống ngay.',
            'cake': 'Bóc bánh ngọt cho khách ăn vài miếng.', 'bag': 'Đưa túi nôn và khăn ướt, nới lỏng dây an toàn cho khách.',
            'oxygen': 'Đeo mặt nạ bình dưỡng khí cho khách, chỉnh dòng thở.', 'doctor': '“Trên chuyến bay có bác sĩ hay nhân viên y tế nào không ạ?” Một chị y tá giơ tay.',
            'captain': 'Gọi buồng lái: báo tình trạng khách, cơ trưởng liên lạc mặt đất.'}[item]
    return dict(message=f'{x["emoji"]} {line}')


def _medical_done(s, c, d, p):
    t = _task(c, p, 'medical')
    kit.need(t['used'], 'Chăm sóc khách trước đã.')
    case = CASES[t['needs']['case']]
    for item, sev in case['need'].items():
        if item not in t['used']:
            t['mistakes'] += 1
            name = next(k['name'] for k in KIT if k['id'] == item).lower()
            cq.slip(t, 'no_' + item, sev, f'Khách {case["why"]}, mà tiếp viên chưa {name}.' if item in ('captain', 'doctor') else
                    f'Khách {case["why"]}, mà thiếu {name}.', f'thiếu bước: {name}', safety=sev >= 3)
    d['today']['medical'] += 1
    d['stats']['medical'] += 1
    ok = not cq.slips(t)
    head = '🩺 Khách đỡ dần, thở đều lại.' if ok else '🩺 Khách qua cơn, nhưng chị Thu nhắc lại những bước còn thiếu.'
    return _finish(s, c, d, t, f'Chăm sóc khách: {case["title"].lower()}.', head)


# ---------------------------------------------------------------- finishing a job
def _finish(s: dict, c: dict, d: dict, t: dict, narrative: str, head: str) -> dict:
    t['stage'] = 'done'
    pts = cq.points(t)
    full = 0 if cq.safety(t) else max(0, BONUS - 2 * pts)
    reward = ao.bonus(d['odd'], full)
    d['today']['jobs'] += 1
    d['stats']['jobs'] += 1
    d['log'] = ar.last(d['log'] + [dict(day=c['day'], kind=t['kind'], title=t['title'][:80], ok=not cq.slips(t))], LOG_MAX, 'flight_attendant.log', c)
    story = ''
    i = _npc_index(t)
    if i in REG_STORY:
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        story = REG_STORY[i][min(r['visits'], len(REG_STORY[i])) - 1]
        t['story'] = story
    kit.complete(s, c, t, reward, narrative[:300])
    note = ao.flown(d['odd'], not cq.slips(t), CFG)
    cut = (' (Đang bị cách chức: không có thưởng.)' if not reward else ' (Mệt quá: nửa thưởng.)') if full and reward < full else ''
    msg = head + (f' Thưởng {reward} xu.' if reward else '') + cut + (f' {note}' if note else '') + (f' 💬 {story}' if story else '')
    out = dict(message=msg.strip(), celebrate=not cq.slips(t))
    if cq.safety(t):
        out['correct'] = False
    return out


# ================================================================ story and the day
def _arc_tick(c: dict, d: dict) -> None:
    a = d['arc']
    if a['due']:
        return
    nxt = next((x for x in ARC if x['id'] not in a['seen']), None)
    if nxt and c['day'] >= nxt['day'] and d['stats']['jobs'] >= nxt['served']:
        a['due'] = nxt['id']


def _arc_seen(d: dict) -> dict:
    a = d['arc']
    kit.need(a['due'], 'Chưa có chuyện mới.')
    x = ARC_INDEX[a['due']]
    a['seen'].append(a['due'])
    a['due'] = None
    return dict(message=f'{x["emoji"]} {x["title"]}')


ACTIONS = {
    'fa_door': _door, 'fa_close': _close, 'fa_demo': _demo, 'fa_walk': _walk, 'fa_fix': _fix, 'fa_ready': _ready,
    'fa_give': _give, 'fa_skip': _skip, 'fa_next': _next, 'fa_stow': _stow, 'fa_secure': _secure, 'fa_turb_end': _turb_end,
    'fa_calm': _calm, 'fa_ask': _ask, 'fa_care': _care, 'fa_done': _medical_done,
}


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    d['today'] = _fresh_today(c['day'])
    d['turb'] = None
    _arc_tick(c, d)
    ao.start(c, ID, d['odd'])
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(c['day'])['id'], c['life'].get('mode') == 'festival')
    ao.tick(s, c, ID, d['odd'], ODD, busy=d['desk']['ev'] is not None)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    tb = d['turb']
    if tb and tb['stage'] == 'coming':
        tb['done'] = list(SECURE_IDS)          # the day ends at the gate: the cabin was secured on the ground
        _turb_resolve(s, c, d)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    odd_note = ao.close(s, c, d['odd'], ODD)
    x = d['today']
    lines = [f'🧳 Đón {x["pax"]} khách ở cửa, mời {x["served"]} món trên xe đẩy.']
    if x['fixed']:
        lines.append(f'🦺 Chỉnh {x["fixed"]} ghế chưa sẵn sàng trước giờ cất cánh.')
    if x['medical']:
        lines.append(f'🩺 Chăm sóc {x["medical"]} khách không khỏe.')
    if x['turb']:
        last = d['turbs'][-1] if d['turbs'] else None
        lines.append('〰️ Cất xe kịp lúc tàu rung.' if last and not last['miss'] else '〰️ Rung lắc giữa giờ phục vụ, lần sau cất xe nhanh hơn nhé.')
    if desk_note:
        lines.append(desk_note)
    if odd_note:
        lines.append(odd_note)
    lines += ao.day_lines(c, d['odd'])
    lines.append('🏠 Tối về tới hẻm, cởi đôi giày bay, bà Tám hỏi hôm nay có gặp ai vui không.')
    return dict(lines=lines, note='Mai báo danh ở sân bay lúc 05:30.', jobs=x['jobs'], pax=x['pax'], served=x['served'], fixed=x['fixed'],
                medical=x['medical'], turb=x['turb'])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 85 else 4 if p >= 65 else 3 if p >= 45 else 2
    codes = {x['code'] for x in cq.slips(t)}
    k = t['kind']

    def score(bad: set, mid: set = frozenset()) -> int:
        return 2 if codes & bad else 3 if codes & mid else 5
    if k == 'board':
        order = score({'power', 'exit'}, {'bag', 'wrong_seat', 'fuss'})
        return dict(criteria=[dict(key='order', label='Đúng chỗ, đúng hành lý', score=order, note='xem thẻ kỹ' if order == 5 else 'xử lý chưa đúng ở cửa'),
                              dict(key='care', label='Niềm nở', score=5 if not codes else 4, note='chào hỏi, chỉ chỗ tận tình'),
                              dict(key='speed', label='Nhanh gọn', score=speed, note='lối đi thông thoáng')])
    if k == 'demo':
        secure = score({'belt', 'aisle_bag'}, {x for x in codes if x.startswith('cabin_')})
        return dict(criteria=[dict(key='demo', label='Hướng dẫn an toàn', score=3 if 'demo_order' in codes else 5, note='đúng thứ tự trên thẻ'),
                              dict(key='secure', label='Khoang sẵn sàng', score=secure, note='không sót ghế nào' if secure == 5 else 'còn sót ghế chưa sẵn sàng')])
    if k == 'service':
        special = score({'nut', 'hot_kid'}, {'veg'})
        order = score(set(), {'wrong', 'woke'} | {x for x in codes if x.startswith('missed_')})
        spill = codes & {'spill', 'cart', 'stand'}
        return dict(criteria=[dict(key='order', label='Đúng món', score=order, note='đúng từng ghế' if order == 5 else 'có ghế nhầm hoặc sót'),
                              dict(key='special', label='Suất đặc biệt, trẻ nhỏ', score=special, note='đúng phiếu suất ăn' if special == 5 else 'sót suất đặc biệt'),
                              dict(key='safe', label='An toàn khi rung', score=3 if spill else 5, note='cất xe kịp' if not spill else 'chưa kịp cất xe'),
                              dict(key='speed', label='Nhanh gọn', score=speed, note='xe đẩy đi đều')])
    if k == 'calm':
        ch = t.get('choices') or []
        beats = CALM[t['needs']['script']]['beats']
        grades = [next(o['grade'] for o in beats[i]['options'] if o['id'] == c_) for i, c_ in enumerate(ch[:len(beats)])]
        g = lambda i: {'good': 5, 'ok': 3, 'bad': 2}.get(grades[i] if i < len(grades) else 'good', 5)
        return dict(criteria=[dict(key='calm', label='Bình tĩnh, lắng nghe', score=g(0), note='mở lời nhẹ nhàng'),
                              dict(key='rule', label='Giữ quy định', score=g(1), note='nói rõ vì sao'),
                              dict(key='solve', label='Có cách giải quyết', score=g(2), note='có lối ra cho khách')])
    care = 1 if 'own_med' in codes else score({'no_oxygen', 'no_juice', 'no_cake', 'no_bag', 'no_water'})
    report = score({'no_captain', 'no_doctor'})
    return dict(criteria=[dict(key='care', label='Sơ cứu đúng', score=care, note='đúng thứ khách cần' if care == 5 else 'thiếu hoặc sai bước sơ cứu'),
                          dict(key='report', label='Báo đúng người', score=report, note='báo cơ trưởng, tìm bác sĩ' if report == 5 else 'chưa báo người cần báo'),
                          dict(key='calm', label='Bình tĩnh', score=speed, note='không để khách chờ lâu')])


# The reviewers' own words (feedback.make_review → review_text): the purser, and passengers of the flight.
VOICES = {
    THU: {5: ['Việc chuyến {code} em làm đâu ra đấy.', 'Chuyến {code} chị không phải nhắc gì.'], 4: ['Chuyến {code} ổn, còn một chỗ em để ý thêm.'],
          3: ['Chuyến {code} chị phải chạy lại mấy chỗ.'], 1: ['Chuyến {code} mình phải ngồi rút kinh nghiệm.']},
    KIET: {5: ['Chuyến {code}: gọn, đúng, không phàn nàn.', 'Tiếp viên chuyến {code} làm việc có lý.'], 4: ['Chuyến {code}: tạm được.'],
           3: ['Chuyến {code}: không như mong đợi.'], 1: ['Chuyến {code}: dịch vụ trên tàu tệ.']},
    CHIN: {5: ['Cô tiếp viên dễ thương quá, bà đi {to} vui ghê.', 'Có cô tiếp viên quen, bà yên tâm cả chuyến.'], 4: ['Chuyến bay tốt, chỉ có chút bà chưa ưng.'],
           3: ['Bà hơi lo suốt chuyến.'], 1: ['Chuyến này bà buồn lắm.']},
    TU: {5: ['Tiếp viên chu đáo, ông đi {to} thoải mái.', 'Chuyến {code} tử tế, ông ghi nhận.'], 4: ['Được, nhưng còn chỗ phải chấn chỉnh.'],
         3: ['Chuyến {code} ông chưa hài lòng.'], 1: ['Chuyến {code} ông không chấp nhận được.']},
    MAI: {5: ['Bay với bé mà được giúp tận tình, cảm ơn tổ bay nhiều.', 'Chuyến {code} bé Bơ ngủ ngon, mẹ cũng nhẹ người.'],
          4: ['Chuyến bay tốt, chỉ có chút chị chưa yên tâm.'], 3: ['Bay với con nhỏ mà chị hơi vất vả.'], 1: ['Chuyến này chị với bé mệt quá.']},
    HAI: {5: ['Chuyến {code} êm, tiếp viên chu đáo.', 'Đi tuyến này hoài, chuyến nay dễ chịu nhất.'], 4: ['Được, chỉ có chút chưa ưng.'],
          3: ['Chuyến {code} chưa được như mọi lần.'], 1: ['Chuyến {code} lần này tệ.']},
    VY: {5: ['Chuyến bay chill xỉu, tiếp viên cute ✈️✨', 'Bay {to} mà vui như đi picnic 🥰'], 4: ['Ổn áp nha, chỉ có một xíu chưa ưng.'],
         3: ['Hơi toang xíu 🥲'], 1: ['Chuyến này không vui chút nào 😤']},
}
PAX_LINES = {
    'order': ('Đúng chỗ, đúng món, không phải nhắc.', 'Mang nhầm, phải gọi lại.'),
    'care': ('Tiếp viên niềm nở từ lúc ở cửa.', 'Tiếp viên hơi lúng túng lúc đón khách.'),
    'speed': ('Nhanh gọn.', 'Chờ hơi lâu.'),
    'special': ('Suất ăn đặc biệt được nhớ đúng ghế.', 'Suất ăn đặc biệt suýt bị nhầm.'),
    'safe': ('Rung lắc mà tiếp viên cất xe kịp, yên tâm.', 'Rung lắc mà xe đẩy vẫn còn giữa lối.'),
    'calm': ('Tiếp viên nói nhỏ nhẹ, nghe lọt tai.', 'Tiếp viên nói hơi gắt.'),
    'rule': ('Nói rõ quy định mà không làm khách mất mặt.', 'Quy định thì đúng, nhưng nói chưa rõ vì sao.'),
    'solve': ('Còn tìm cho khách cách khác, chu đáo.', 'Chưa có cách nào cho khách.'),
    'report': ('Báo cơ trưởng, tìm bác sĩ ngay.', 'Chậm báo người cần báo.'),
}


def review_text(c: dict, t: dict, persona: str, stars: int, criteria: list, seed: int) -> str:
    i = _npc_index(t)
    return air.review(t, stars, criteria, seed, VOICES.get(i, VOICES[KIET]), None if i == THU else PAX_LINES)


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    k = t['kind']
    if k == 'board':
        return f'Chuyến {n["leg"]["code"]} đi {n["leg"]["to"]}: {len(n["queue"])} khách đang chờ ở cửa. Xem thẻ lên tàu và hành lý từng người.'
    if k == 'demo':
        return 'Làm mẫu an toàn đúng thứ tự trên thẻ, rồi đi dọc lối kiểm tra khoang.'
    if k == 'service':
        ssr = n['ssr']
        bits = [f'suất chay ghế {ssr["veg"]}'] if ssr.get('veg') else []
        if ssr.get('nut'):
            bits.append(f'dị ứng đậu phộng ghế {ssr["allergic"]} (cả hàng {ssr["nut"]} không phát đậu phộng)')
        return f'Phiếu suất ăn đặc biệt: {"; ".join(bits) or "không có"}. Hàng {n["rows"][0]["row"]} tới {n["rows"][-1]["row"]}.'
    if k == 'calm':
        return CALM[n['script']]['beats'][0]['text']
    return CASES[n['case']]['seen']


def _pub_seat(t: dict, s: dict) -> dict:
    return dict(seat=s['seat'], who=s['who'], say=s['say'], kind=s['kind'] if s['kind'] in ('kid', 'sleep') else None,
                drink=s['drink'], snack=s['snack'], given=list(t['given'].get(s['seat'], [])), skipped=s['seat'] in t['skipped'])


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    v['leg'] = t['needs']['leg']          # the departures board shows every flight
    if not t['known']:
        v['needs'] = None
        return v
    n, k = t['needs'], t['kind']
    out = dict(leg=n['leg'])
    if k == 'board':
        # The one at the door and the ones already seated; what their trouble is stays for you to read.
        out['queue'] = [dict(npc=kit.npc_id(ID, q['npc']) if q['npc'] is not None else None, who=q['who'], seat=q['seat'], bag=q['bag'], say=q['say'], row=int(q['seat'][:-1]),
                             exit=int(q['seat'][:-1]) in air.EXIT_ROWS) if i <= t['step'] else None for i, q in enumerate(n['queue'])]
    elif k == 'demo':
        cab = n['cabin']
        out['cabin'] = dict(rows=cab['rows'], state={s: ('ok' if s in t['fixed'] else v_) for s, v_ in cab['state'].items()} if t['walked'] else None)
    elif k == 'service':
        out['ssr'] = n['ssr']
        out['rows'] = [dict(row=r['row'], seats=[_pub_seat(t, s) for s in r['seats']]) if i <= t['row'] else dict(row=r['row'], seats=None)
                       for i, r in enumerate(n['rows'])]
    elif k == 'calm':
        x = CALM[n['script']]
        beat = x['beats'][t['step']] if t['step'] < len(x['beats']) else None
        out['calm'] = dict(emoji=x['emoji'], title=x['title'], beats=len(x['beats']),
                           now=dict(text=beat['text'], options=[dict(id=o['id'], label=o['label']) for o in beat['options']]) if beat else None,
                           said=[next(o['label'] for o in x['beats'][i]['options'] if o['id'] == ch) for i, ch in enumerate(t['choices'])])
    else:
        x = CASES[n['case']]
        out['case'] = dict(title=x['title'], seen=x['seen'], answers={q: x['answers'][q] for q in t['answers']})
    v['needs'] = out
    return v


def _turb_public(d: dict) -> dict | None:
    tb = d.get('turb')
    if not tb:
        return None
    v = dict(tb)
    v['remain'] = max(0.0, round(tb['start'] + tb['limit'] - kit.now(), 1)) if tb['stage'] == 'coming' else 0
    return v


def public_data(c: dict) -> dict:
    d = tree_copy(c['ext']['data'])
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    arc = d['arc']
    due = ARC_INDEX.get(arc['due']) if arc.get('due') else None
    return dict(intro=d['intro'], stats=d['stats'], today=d['today'], log=d['log'][-6:], regulars={k: dict(v) for k, v in d['regulars'].items()},
                turb=_turb_public(d), turbs=d['turbs'][-5:],
                mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                arc=dict(seen=list(arc['seen']), total=len(ARC),
                         due=dict(id=due['id'], emoji=due['emoji'], title=due['title'], text=list(due['text'])) if due else None),
                desk=kit.desk_public(d['desk'], DESK, ID), odd=ao.public(c, ao.ensure(d), ODD, ID, CFG))


def content() -> dict:
    return dict(drinks=DRINKS, snacks=SNACKS, hot=sorted(HOT), door=DOOR, demo=DEMO, cabin=CABIN, secure=SECURE, kit=KIT, questions=QUESTIONS,
                exit_rows=list(air.EXIT_ROWS), rows=air.ROWS, bonus=BONUS, airline=air.AIRLINE, intro=INTRO,
                arc=[dict(id=x['id'], emoji=x['emoji'], title=x['title'], served=x['served']) for x in ARC],
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    if (c['ext']['data'].get('odd') or {}).get('ev'):
        return 'Có người đang chờ bạn trả lời: chọn giọng, chọn ý, cần thì báo chị Thu hoặc phòng an toàn.'
    k = t.get('kind')
    if k == 'board':
        return 'Đọc thẻ lên tàu: vali to gửi khoang hàng, pin sạc mang theo người, hàng 1 và 17 chỉ cho người lớn đi lại được.'
    if k == 'demo':
        return 'Làm mẫu đúng thứ tự trên thẻ → đi dọc lối → chỉnh từng ghế chưa sẵn sàng → báo buồng lái.'
    if k == 'service':
        return 'Từng hàng một: đúng món từng ghế, suất chay theo phiếu, hàng dị ứng không phát đậu phộng, trẻ nhỏ không uống đồ nóng.'
    if k == 'calm':
        return 'Lắng nghe trước, nói rõ quy định và vì sao, rồi tìm cho khách một lối ra.'
    return 'Hỏi khách trước, dùng đúng đồ trong túi sơ cứu, không đưa thuốc của mình, khách nặng thì báo cơ trưởng.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'galley':
        return 'Đã pha sẵn bình trà, xếp ly lên xe đẩy.'
    if e.get('role') == 'ground':
        return 'Đã gắn thẻ ưu tiên cho khách lớn tuổi và gia đình có con nhỏ.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu khoang khách sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc khoang khách không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc khoang khách sai.')
    n, k = t['needs'], t['kind']
    limit = {'board': len(n.get('queue', [])), 'demo': len(DEMO), 'calm': 3}.get(k, 0)
    kit.integer(t.get('step'), 0, limit)
    for key in ('done', 'wrong'):
        kit.need(isinstance(t.get(key), list) and len(t[key]) <= 8 and all(type(x) is int and 0 <= x < 8 for x in t[key]), 'Hàng khách ở cửa sai.')
    g = t.get('given')
    rows = n.get('rows') or []
    seats = {s['seat'] for r in rows for s in r['seats']}
    kit.need(isinstance(g, dict) and set(g) <= seats, 'Món đã phục vụ sai.')
    for v in g.values():
        kit.need(isinstance(v, list) and len(v) <= 3 and all(x in ITEM for x in v), 'Món đã phục vụ sai.')
    kit.need(isinstance(t.get('skipped'), list) and set(t['skipped']) <= seats and len(set(t['skipped'])) == len(t['skipped']), 'Ghế để khách ngủ sai.')
    kit.integer(t.get('row'), 0, max(0, len(rows) - 1))
    _vbool(t.get('walked'))
    cab = (n.get('cabin') or {}).get('state', {})
    kit.need(isinstance(t.get('fixed'), list) and set(t['fixed']) <= set(cab) and len(set(t['fixed'])) == len(t['fixed']), 'Ghế đã chỉnh sai.')
    kit.need(isinstance(t.get('answers'), list) and set(t['answers']) <= set(Q_IDS) and len(set(t['answers'])) == len(t['answers']), 'Câu hỏi sai.')
    kit.need(isinstance(t.get('used'), list) and set(t['used']) <= set(KIT_IDS) and len(set(t['used'])) == len(t['used']), 'Đồ sơ cứu sai.')
    ch = t.get('choices')
    kit.need(isinstance(ch, list) and len(ch) <= 3 and all(x in ('a', 'b', 'c') for x in ch) and (k != 'calm' or len(ch) == t['step']), 'Lời nói với khách sai.')
    _vbool(t.get('ready'))
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách quen sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    kit.need(isinstance(d['stats'], dict) and set(initial()['stats']) <= set(d['stats']), 'Sổ tiếp viên sai.')
    for v in d['stats'].values():
        kit.integer(v, 0, 10 ** 9)
    kit.need(isinstance(d['log'], list) and len(d['log']) <= LOG_MAX, 'Nhật ký khoang khách sai.')
    for x in d['log']:
        kit.need(isinstance(x, dict) and set(x) == {'day', 'kind', 'title', 'ok'} and x['kind'] in KINDS, 'Nhật ký khoang khách sai.')
        kit.integer(x['day'], 0, 10 ** 7)
        kit.text(x['title'], 80)
        _vbool(x['ok'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
    a = d['arc']
    kit.need(isinstance(a, dict) and isinstance(a.get('seen'), list) and all(x in ARC_INDEX for x in a['seen'])
             and len(set(a['seen'])) == len(a['seen']) and a.get('due') in (None, *ARC_INDEX), 'Chuyện nghề sai.')
    tb = d['turb']
    if tb is not None:
        kit.need(isinstance(tb, dict) and tb.get('stage') in ('coming', 'done'), 'Rung lắc sai.')
        kit.integer(tb.get('day'), 1, 10 ** 7)
        kit.text(tb.get('task'), 60)
        kit.need(isinstance(tb.get('start'), (int, float)) and not isinstance(tb.get('start'), bool) and 0 <= tb['start'] < 10 ** 11, 'Giờ rung lắc sai.')
        kit.integer(tb.get('limit'), 1, 120)
        kit.need(isinstance(tb.get('done'), list) and set(tb['done']) <= set(SECURE_IDS) and len(set(tb['done'])) == len(tb['done']), 'Việc cất xe sai.')
        r = tb.get('result')
        kit.need(r is None or (isinstance(r, dict) and type(r.get('miss')) is int), 'Kết quả rung lắc sai.')
    kit.need(isinstance(d['turbs'], list) and len(d['turbs']) <= 20, 'Lịch sử rung lắc sai.')
    for x in d['turbs']:
        kit.need(isinstance(x, dict), 'Lịch sử rung lắc sai.')
        for k in ('day', 'miss'):
            kit.integer(x.get(k), 0, 10 ** 7)
    kit.need(isinstance(d['today'], dict) and set(d['today']) == set(_fresh_today(0)), 'Số liệu trong ngày sai.')
    for v in d['today'].values():
        kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)
    ao.validate(d['odd'], ODD)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='fa_', category='service',
    meta=dict(short='Tiếp viên hàng không', place='Khoang khách Cánh Cò', tagline='Sáu mươi tám chỗ ngồi, một nụ cười và đủ mọi chuyện.', icon='bell',
              color='#1f7a78', light='#e3f4f1', weather='Nắng trên cánh tàu', work='Việc khoang khách', station='Khoang khách',
              greeting='Sáng đi từ hẻm ra sân bay. Đón khách ở cửa, làm mẫu an toàn, đẩy xe phục vụ từng hàng và chăm từng người cùng chị Thu.',
              caption='Bay cao mà vẫn nhớ tên từng người', map_label='20 · KHOANG KHÁCH CÁNH CÒ'),
    people=PEOPLE,
    staff=[('Linh', 'galley', 'Tiếp viên mới, pha trà khéo, hơi rụt rè.', 76, 90),
           ('Duy', 'ground', 'Nhân viên mặt đất, nhớ mặt khách quen.', 82, 84),
           ('Trâm', 'galley', 'Xếp xe đẩy gọn nhất tổ.', 88, 80),
           ('Khoa', 'ground', 'Nói ba thứ tiếng, dẫn khách lạc rất kiên nhẫn.', 72, 94)],
    roles={'galley': 'Tiếp viên phụ bếp', 'ground': 'Nhân viên mặt đất'},
    tip=0,
    open_line='Báo danh xong. Chị Thu đang chờ ở cửa tàu.',
    more_line='Chị Thu giao thêm một việc trong khoang.',
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    activity=('🛒', 'Khoang khách gọn gàng', [('Vali quá khổ', 'Khoang hàng'), ('Pin sạc dự phòng', 'Mang theo người'),
                                              ('Bé mười tháng', 'Không uống đồ nóng'), ('Hàng 17', 'Người lớn đi lại được')],
              ['Đón khách, xem thẻ', 'Làm mẫu an toàn', 'Đẩy xe từng hàng', 'Cất xe, về ghế']),
    stories=[('Chiếc khăn của chị Thu', ('Chị Thu kể chiếc khăn quàng đầu tiên của chị đã bạc màu vì nắng đảo.',
                                          'Bạn làm thêm một việc; chị chỉ cách thắt khăn trong mười giây.',
                                          'Chị tặng bạn chiếc ghim cài hình con cò: “Của chị hồi mới bay.”')),
             ('Chuyến bay của bà Chín', ('Bà Chín lần đầu đi máy bay, ôm túi xoài không rời.',
                                         'Bạn ngồi cạnh bà lúc cất cánh, kể chuyện đảo cho bà nghe.',
                                         'Xuống tàu, bà Chín ôm bạn: “Lần sau bà bay nữa, cô nhớ đón bà nghe.”')),
             ('Lá thư của chị Mai', ('Chị Mai bế bé Bơ khóc suốt chuyến đầu tiên.',
                                     'Bạn làm thêm một việc rồi chỉ chị cách cho bé bú lúc tàu hạ độ cao.',
                                     'Tuần sau hãng nhận lá thư cảm ơn, kèm ảnh bé Bơ ngủ ngon trên tàu.'))],
    review_asides=['Tiếp viên cười hiền, nói nhỏ mà rõ.', 'Đồ uống đúng từng ghế, không phải nhắc.', 'Làm mẫu an toàn dễ hiểu, không vội.',
                   'Có chuyện là tiếp viên tới liền.'],
    situations=SITUATIONS,
    guide='Đón khách: đọc thẻ, vali to gửi khoang hàng, pin sạc theo người, hàng 1 và 17 cho người lớn đi lại được → làm mẫu an toàn đúng thứ tự, '
          'đi dọc lối chỉnh từng ghế → đẩy xe từng hàng, đúng suất đặc biệt → đèn thắt dây sáng: khóa phanh, cất bình nóng, về ghế.',
    employment=dict(
        postings=[
            dict(id='fa-cabin', org='Hãng bay Cánh Cò · Sân bay thành phố', kind='company', title='Tiếp viên hàng không',
                 salary=(65, 85), probation_days=3, wants=['communication', 'patience', 'calm'],
                 perks=['Bay cùng tiếp viên trưởng kèm cặp', 'Tối về ngủ ở nhà', 'Đồng phục khăn quàng cò trắng'],
                 culture='Hãng bay nhỏ, khoang 68 chỗ, khách quen nhiều. An toàn trước, nụ cười sau, nhưng thiếu cái nào cũng không được.',
                 questions=['fa_exit', 'fa_angry', 'fa_medical', 'conflict'], reference=True),
            dict(id='fa-ground', org='Quầy phục vụ mặt đất Cánh Cò', kind='branch', title='Nhân viên phục vụ khách mặt đất',
                 salary=(50, 65), probation_days=2, wants=['patience', 'teamwork'],
                 perks=['Nhận việc nhanh', 'Không phải bay', 'Lương thấp hơn'],
                 culture='Quầy thủ tục và cửa ra tàu, đón khách từ sáng sớm.',
                 questions=['fa_angry'], reference=False),
        ],
        questions={
            'fa_exit': dict(text='Một cụ bà chống gậy có vé ngồi hàng cạnh cửa thoát hiểm. Bạn làm gì?', options=[
                dict(id='move', label='Giải thích nhẹ nhàng, mời cụ sang ghế rộng chân khác', score=3, note='Chị Thu gật đầu: đúng quy định mà vẫn chu đáo.'),
                dict(id='keep', label='Để cụ ngồi, vé đã mua rồi', score=0, note='Hàng thoát hiểm cần người mở được cửa.'),
                dict(id='ask', label='Hỏi cụ có muốn đổi không', score=1, note='Chuyện an toàn không để khách tự chọn.')]),
            'fa_angry': dict(text='Khách quát bạn vì chuyến bay trễ. Câu đầu tiên của bạn là gì?', options=[
                dict(id='listen', label='“Dạ em hiểu anh đang vội. Em xem giúp anh ngay.”', score=3, note='Lắng nghe trước, giải thích sau.'),
                dict(id='rule', label='“Trễ là do thời tiết, không phải lỗi của em.”', score=1, note='Đúng, nhưng khách chưa thấy được nghe.'),
                dict(id='back', label='“Anh nói nhỏ thôi ạ.”', score=0, note='Dễ làm khách nóng thêm.')]),
            'fa_medical': dict(text='Khách ngất trên tàu. Bạn nhớ nhất điều gì?', options=[
                dict(id='steps', label='Gọi đồng nghiệp, sơ cứu theo túi y tế, báo cơ trưởng, tìm bác sĩ trên tàu', score=3, note='Đúng trình tự, không làm một mình.'),
                dict(id='med', label='Đưa khách uống thuốc cảm của mình', score=0, note='Không bao giờ đưa thuốc của mình.'),
                dict(id='wait', label='Chờ khách tự tỉnh', score=0, note='Chần chừ là nguy hiểm.')]),
        }),
)
