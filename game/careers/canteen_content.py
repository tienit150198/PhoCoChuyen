"""🍱 Căn tin trường Tiểu học Phố Mây: the words and tables of the school canteen (game/careers/canteen.py).

Player #482: "nghề bán căn tin trường học… đúng nghề ngoài đời". The day follows a real school canteen: the rush before
the morning bell (xôi, bánh mì, mì ly, sữa), the twenty minutes of recess (nước, ăn vặt, a group of friends sharing),
and the lunch trays (cơm phần) the class teachers order for the children who stay at school. Prices are the canteen
board the school approved (fixed, never haggled); a student pays from pocket money; an allergy or a vegetarian day is
said once at the counter; the day's lunch is sampled and kept 24 hours before the first tray goes out.

Every table is static: an order is a pure function of (day, slot), so validate_state can rebuild it.
"""
from __future__ import annotations

PLACE = 'Căn tin trường Tiểu học Phố Mây'
OWNER = 'Cô Sáu Mận'

PEOPLE = [
    ('Cô Sáu Mận', 'Bếp chính căn tin', 'Nấu cơm trưa cho học trò hai mươi năm. Dặn hoài: rửa tay, đeo găng, hỏi dị ứng trước khi đưa đồ ăn.', 'warm'),
    ('Chú Tư Gác', 'Bảo vệ, người đánh trống', 'Giữ cổng trường và đánh trống đúng giờ, không trễ một phút.', 'quiet'),
    ('Bé Na', 'Học sinh lớp 2A', 'Chạy tới căn tin là hỏi “hôm nay có xôi không cô”. Hay quên tiền thối.', 'warm'),
    ('Tí', 'Học sinh lớp 4B', 'Lúc nào cũng vội, mua cho cả nhóm bạn đá cầu.', 'genz'),
    ('Khoa', 'Học sinh lớp 5A', 'Lớp trưởng, đếm tiền kỹ, hỏi giá trước khi mua.', 'picky'),
    ('Bé Bông', 'Học sinh lớp 1C', 'Bị dị ứng sữa, mẹ dặn kỹ: không sữa, không bánh có sữa.', 'quiet'),
    ('Minh', 'Học sinh lớp 3A', 'Nhà ăn chay ngày rằm, mùng một; có hôm quên mang cơm.', 'quiet'),
    ('Cô Hạnh', 'Giáo viên chủ nhiệm lớp 2A', 'Đặt cơm trưa cho các bạn ở lại trường, đếm từng phần.', 'parent_strict'),
    ('Thầy Lâm', 'Giáo viên thể dục', 'Đặt cơm cho đội bóng của trường sau giờ tập.', 'warm'),
    ('Chị Thảo', 'Mẹ bé Na', 'Hay ghé hỏi con ăn uống thế nào, lo con ăn nhiều đồ ngọt.', 'parent_worried'),
]
MENTOR = 0
GUARD = 1
STUDENTS = (2, 3, 4, 5, 6)
TEACHERS = (7, 8)
PARENT = 9

WRONG_COST = 10         # quality lost per tray handed over wrong
QUALITY_FLOOR = 40
MILESTONES = (2, 4, 8)  # days: lunch trays, allergies at recess, the bigger classes
MASTER = (100, 30)
EXPERT = (180, 45)
BELL = {'sang': 24, 'ra_choi': 18}   # beats (turns) a rush customer waits before the bell takes them back to class

# ---------------------------------------------------------------- the counter (inventory items; canteen.GOODS)
# group: the shelf on the counter; tags: what an allergy or a vegetarian day says no to; start: on the opening shelf.
GROUPS = (('sang', '🍙 Đồ ăn sáng'), ('uong', '🥤 Nước uống'), ('vat', '🍪 Ăn vặt'), ('trua', '🍱 Cơm phần trưa'))
GOODS = {
    'ct_xoi': dict(name='Xôi gà', emoji='🍙', group='sang', price=12, cost=7, unit='hộp', start=12, life=3, tags=('meat',)),
    'ct_banh_mi': dict(name='Bánh mì trứng', emoji='🥖', group='sang', price=12, cost=7, unit='ổ', start=12, life=3, tags=('egg',)),
    'ct_mi_ly': dict(name='Mì ly chay', emoji='🍜', group='sang', price=10, cost=6, unit='ly', start=12, tags=()),
    'ct_com_nam': dict(name='Cơm nắm muối mè', emoji='🍘', group='sang', price=8, cost=4, unit='nắm', start=12, tags=()),
    'ct_nuoc_suoi': dict(name='Nước suối', emoji='💧', group='uong', price=5, cost=2, unit='chai', start=24, tags=()),
    'ct_tra_tac': dict(name='Trà tắc', emoji='🍋', group='uong', price=6, cost=2, unit='ly', start=20, tags=()),
    'ct_sua_dau': dict(name='Sữa đậu nành', emoji='🫘', group='uong', price=7, cost=3, unit='bịch', start=16, tags=()),
    'ct_sua_hop': dict(name='Sữa hộp', emoji='🥛', group='uong', price=9, cost=5, unit='hộp', start=20, tags=('milk',)),
    'ct_snack': dict(name='Snack khoai tây', emoji='🥔', group='vat', price=6, cost=3, unit='gói', start=20, tags=()),
    'ct_keo_dau': dict(name='Kẹo đậu phộng', emoji='🥜', group='vat', price=4, cost=2, unit='thanh', start=20, tags=('peanut',)),
    'ct_bong_lan': dict(name='Bánh bông lan', emoji='🧁', group='vat', price=7, cost=4, unit='cái', start=16, tags=('milk', 'egg')),
    'ct_sua_chua': dict(name='Sữa chua', emoji='🍶', group='vat', price=7, cost=4, unit='hũ', start=16, life=3, tags=('milk',)),
    'ct_trai_cay': dict(name='Trái cây cắt ly', emoji='🍉', group='vat', price=8, cost=4, unit='ly', start=12, life=3, tags=()),
    'ct_com': dict(name='Cơm trắng', emoji='🍚', group='trua', price=4, cost=2, unit='phần', start=30, life=3, tags=()),
    'ct_ga_kho': dict(name='Gà kho gừng', emoji='🍗', group='trua', price=12, cost=7, unit='phần', start=20, life=3, tags=('meat',)),
    'ct_ca_chien': dict(name='Cá chiên sốt cà', emoji='🐟', group='trua', price=12, cost=7, unit='phần', start=16, life=3, tags=('meat', 'fish')),
    'ct_dau_hu': dict(name='Đậu hũ sốt cà (chay)', emoji='🧈', group='trua', price=8, cost=4, unit='phần', start=16, life=3, tags=()),
    'ct_rau': dict(name='Rau muống xào', emoji='🥬', group='trua', price=3, cost=1, unit='phần', start=30, life=3, tags=()),
    'ct_canh': dict(name='Canh bí đỏ', emoji='🥣', group='trua', price=3, cost=1, unit='chén', start=30, life=3, tags=()),
}
FOODS = ('ct_xoi', 'ct_banh_mi', 'ct_mi_ly', 'ct_com_nam')
DRINKS = ('ct_nuoc_suoi', 'ct_tra_tac', 'ct_sua_dau', 'ct_sua_hop')
SNACKS = ('ct_snack', 'ct_keo_dau', 'ct_bong_lan', 'ct_sua_chua', 'ct_trai_cay')
MAINS = ('ct_ga_kho', 'ct_ca_chien')
SAY = {   # how a student names it
    'ct_xoi': 'hộp xôi gà', 'ct_banh_mi': 'ổ bánh mì trứng', 'ct_mi_ly': 'ly mì chay', 'ct_com_nam': 'nắm cơm muối mè',
    'ct_nuoc_suoi': 'chai nước suối', 'ct_tra_tac': 'ly trà tắc', 'ct_sua_dau': 'bịch sữa đậu nành', 'ct_sua_hop': 'hộp sữa',
    'ct_snack': 'gói snack khoai tây', 'ct_keo_dau': 'thanh kẹo đậu phộng', 'ct_bong_lan': 'cái bánh bông lan',
    'ct_sua_chua': 'hũ sữa chua', 'ct_trai_cay': 'ly trái cây',
}
NUM = {1: 'một', 2: 'hai', 3: 'ba', 4: 'bốn', 5: 'năm', 6: 'sáu'}
CLASSES = ('1A', '1C', '2A', '2B', '3A', '3C', '4B', '5A')

# ---------------------------------------------------------------- the day (kit.daily)
MODS = [
    dict(id='normal', emoji='🏫', label='Ngày học bình thường', hint='Trống vào lớp lúc 7 giờ, ra chơi 9 giờ 20. Mời từng bạn lên quầy, giao đủ trước khi trống đánh.', weight=4),
    dict(id='monday', emoji='🇻🇳', label='Thứ Hai chào cờ', hint='Học sinh tới sớm xếp hàng chào cờ, căn tin đông từ sáu giờ rưỡi.', weight=2, min_day=2),
    dict(id='exam', emoji='📝', label='Tuần kiểm tra học kỳ', hint='Học sinh ăn vội để vào phòng thi, ít nói, hay mua nước suối.', weight=1, min_day=3),
    dict(id='rain', emoji='🌧️', label='Mưa đầu giờ', hint='Mưa lất phất, học sinh đứng chờ dưới mái hiên căn tin. Lau sàn cho khỏi trơn.', weight=2, min_day=2),
    dict(id='sports', emoji='⚽', label='Hội khỏe Phù Đổng của trường', hint='Đội bóng tập buổi trưa: thầy Lâm có thể đặt thêm cơm phần.', weight=1, min_day=4),
]

# ---------------------------------------------------------------- the notebook (content().rules)
RULES = [
    'Bảng giá căn tin do nhà trường duyệt: bán đúng giá niêm yết, không tăng giá giờ cao điểm.',
    'Trống vào lớp lúc 7 giờ, ra chơi 20 phút: bạn nào chưa mua kịp thì phải về lớp, đừng để các bạn trễ giờ.',
    'Hỏi dị ứng trước khi đưa đồ ăn. Bé dị ứng sữa: không sữa hộp, sữa chua, bánh bông lan. Dị ứng đậu phộng: không kẹo đậu phộng.',
    'Ngày ăn chay: không xôi gà, không gà kho, cá chiên. Phần chay là đậu hũ sốt cà; cơm nắm muối mè, mì ly chay là đồ chay.',
    'Học sinh trả bằng tiền tiêu vặt: tổng khay không được quá số tiền bé có. Nói rõ giá từng món.',
    'Một phần cơm trưa gồm: cơm trắng, một món mặn (hoặc phần chay), rau xào và canh. Đếm đủ theo số bạn của lớp.',
    'Lưu mẫu thức ăn: mỗi trưa giữ một mẫu từng món trong hộp có nhãn, cất tủ mát 24 giờ, trước khi phát phần cơm đầu tiên.',
    'Rửa tay, đeo găng, đội mũ khi chia cơm. Đồ hết hạn dùng thì bỏ, không bán giảm giá.',
    'Không bán nước ngọt có ga, đồ ăn vặt không rõ nguồn gốc trong trường.',
]

# ---------------------------------------------------------------- surprises between customers (kit desk)
DESK = [
    dict(id='spill', title='Một ly trà tắc đổ tung tóe', emoji='💦', npc=3, min_day=1, tone='tense', at='between', weight=3, mods=None,
         text='Tí chạy vội, va vào bàn, ly trà tắc đổ ra sàn ngay trước quầy. Mấy bạn nhỏ đang chạy tới.',
         options=[dict(id='mop', label='Đặt biển “Sàn ướt”, lau khô ngay rồi mới bán tiếp', hint='',
                       effects=dict(xp=5, review=[5, 'Căn tin lau sàn liền, không bạn nào trượt ngã.', 0]), good=True,
                       outcome='Sàn khô ráo. Cô Sáu gật đầu: “Học trò chạy nhảy, sàn trơn là té liền.”'),
                  dict(id='later', label='Để đó, bán cho kịp giờ rồi lau sau', hint='',
                       effects=dict(patience=-4, review=[2, 'Sàn căn tin trơn trượt, bé nhà tôi suýt té.', 9]), good=False,
                       outcome='Một bạn lớp Một trượt chân, khóc òa. May không sao.')],
         default='later'),
    dict(id='soda', title='Học sinh đòi mua nước ngọt có ga', emoji='🥤', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Tí nài: “Cô bán nước ngọt có ga đi cô, căn tin trường bên có bán mà.” Chú giao hàng ngoài cổng cũng mời lấy vài thùng.',
         options=[dict(id='no', label='Từ chối, giải thích trường không bán nước có ga, mời bạn thử trà tắc', hint='',
                       effects=dict(xp=5, mark='rules_kept'), good=True, outcome='Tí phụng phịu rồi cũng lấy ly trà tắc.'),
                  dict(id='yes', label='Nhận vài thùng bán thử', hint='',
                       effects=dict(money=12, review=[1, 'Căn tin trường mà bán nước có ga cho con nít, phụ huynh không đồng ý.', 9]), good=False,
                       outcome='Chiều đó cô hiệu trưởng gọi lên nhắc nhở.')],
         default='no'),
    dict(id='expired', title='Một thùng sữa hộp sắp hết hạn', emoji='📅', npc=0, min_day=2, tone='tense', at='open', weight=2, mods=None,
         text='Kiểm hàng đầu ngày, cô Sáu thấy mấy hộp sữa đã quá hạn dùng hôm qua lẫn trong thùng.',
         options=[dict(id='bin', label='Bỏ riêng ra, ghi sổ, báo nhà cung cấp đổi lại', hint='',
                       effects=dict(xp=6, stock={'ct_sua_hop': -3}), good=True,
                       outcome='Nhà cung cấp hẹn mai đổi ba hộp mới. Kệ chỉ còn sữa trong hạn.'),
                  dict(id='sell', label='Bán giảm giá cho hết', hint='',
                       effects=dict(review=[1, 'Con tôi mua phải hộp sữa quá hạn ở căn tin.', 9]), good=False,
                       outcome='Một phụ huynh đọc hạn trên hộp, gọi điện cho nhà trường.')],
         default='bin'),
    dict(id='lost_coins', title='Bé làm rơi mất tiền ăn sáng', emoji='🪙', npc=2, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Bé Na mếu máo: tiền mẹ cho ăn sáng rớt đâu mất, trống sắp đánh mà bụng đói.',
         options=[dict(id='slip', label='Cho bé một hộp xôi, ghi sổ nhờ cô chủ nhiệm báo mẹ bé', hint='',
                       effects=dict(xp=6, stock={'ct_xoi': -1}, review=[5, 'Con quên tiền mà căn tin vẫn cho ăn, báo lại đàng hoàng. Cảm ơn cô.', 9]), good=True,
                       outcome='Chiều chị Thảo ghé gửi lại tiền, cảm ơn rối rít.'),
                  dict(id='no', label='Nói bé về lớp, mai mang tiền thì mua', hint='', effects=dict(), good=None,
                       outcome='Bé Na đói meo cả buổi sáng.')],
         default='no'),
    dict(id='inspection', title='Đoàn kiểm tra an toàn thực phẩm ghé căn tin', emoji='📋', npc=0, min_day=3, tone='tense', at='open', weight=2, mods=None,
         text='Phòng giáo dục cùng y tế phường kiểm tra bếp ăn: hỏi sổ lưu mẫu, giấy khám sức khỏe, hóa đơn nguồn hàng.',
         options=[dict(id='show', label='Đưa sổ lưu mẫu, hóa đơn nguồn hàng, mời đoàn xem tủ mát', hint='',
                       effects=dict(xp=8, review=[5, 'Bếp căn tin sạch sẽ, sổ sách đầy đủ.', 7]), good=True,
                       outcome='Đoàn ghi biên bản: đạt. Cô Sáu thở phào.'),
                  dict(id='stall', label='Xin đoàn hẹn hôm khác vì đang bận', hint='',
                       effects=dict(review=[2, 'Căn tin né đoàn kiểm tra, phụ huynh lo lắng.', 9]), good=False,
                       outcome='Đoàn ghi chú “chưa hợp tác”, hẹn kiểm tra đột xuất lần sau.')],
         default='show'),
    dict(id='sweets', title='Phụ huynh lo con ăn quá nhiều đồ ngọt', emoji='🍬', npc=9, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Chị Thảo ghé quầy: “Ngày nào bé Na cũng mua bánh ngọt với kẹo. Căn tin có món gì lành mạnh hơn không em?”',
         options=[dict(id='fruit', label='Giới thiệu ly trái cây, sữa chua; gợi ý chị dặn bé mua trái cây giờ ra chơi', hint='',
                       effects=dict(xp=5, review=[5, 'Căn tin tư vấn tận tình, có trái cây tươi cho học trò.', 9]), good=True,
                       outcome='Chị Thảo gửi trước tiền một tuần trái cây cho bé.'),
                  dict(id='shrug', label='Nói học trò thích gì thì bán nấy', hint='',
                       effects=dict(review=[2, 'Căn tin chỉ lo bán, không để ý sức khỏe học trò.', 9]), good=False,
                       outcome='Chị Thảo lắc đầu đi về.')],
         default='fruit'),
    dict(id='bread_late', title='Xe bánh mì giao trễ', emoji='🚚', npc=0, min_day=2, tone='tense', at='open', weight=2, mods=None,
         text='Sáu giờ bốn lăm rồi mà xe bánh mì chưa tới. Học sinh bắt đầu xếp hàng.',
         options=[dict(id='other', label='Bày thêm xôi, cơm nắm; dán giấy “bánh mì về lúc 7 giờ”', hint='',
                       effects=dict(xp=5), good=True, outcome='Hàng đi nhanh, không bạn nào phải chờ suông.'),
                  dict(id='wait', label='Đứng chờ xe tới rồi mới bán', hint='', effects=dict(patience=-5), good=False,
                       outcome='Hàng dài thêm, mấy bạn phải chạy vào lớp với bụng đói.')],
         default='wait'),
    dict(id='glove', title='Găng tay chia cơm bị rách', emoji='🧤', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Đang chia cơm thì chiếc găng tay rách một lỗ ở ngón trỏ.',
         options=[dict(id='new', label='Thay găng mới, rửa tay rồi chia tiếp', hint='', effects=dict(xp=4), good=True,
                       outcome='Cô Sáu đưa hộp găng mới: “Một chiếc găng rẻ hơn một bữa đau bụng của học trò.”'),
                  dict(id='keep', label='Chia nốt mấy phần rồi tính', hint='', effects=dict(review=[2, 'Thấy cô chia cơm găng tay rách, con kể lại mà lo.', 9]), good=False,
                       outcome='Một phụ huynh đứng ngoài cửa sổ trông thấy.')],
         default='keep'),
    dict(id='rain_floor', title='Mưa tạt ướt hành lang căn tin', emoji='🌧️', npc=1, min_day=2, tone='gentle', at='open', weight=2, mods=('rain',),
         text='Mưa tạt vào hành lang, nền gạch loáng nước ngay chỗ học sinh xếp hàng.',
         options=[dict(id='mat', label='Trải thảm chống trơn, nhờ chú Tư căng bạt che', hint='', effects=dict(xp=5), good=True,
                       outcome='Học sinh xếp hàng gọn dưới mái bạt, không ai trượt.'),
                  dict(id='none', label='Mưa chút xíu, kệ', hint='', effects=dict(patience=-3), good=None,
                       outcome='Học sinh chen vào trong, hàng lộn xộn.')],
         default='none'),
    dict(id='team_lunch', title='Thầy Lâm đặt thêm cơm cho đội bóng', emoji='⚽', npc=8, min_day=4, tone='gentle', at='between', weight=2, mods=('sports',),
         text='Đội bóng tập xong, thầy Lâm ghé: “Chiều nay đá giao hữu, em nấu thêm cho tụi nhỏ mười phần được không?”',
         options=[dict(id='yes', label='Nhận, hẹn giờ lấy và ghi rõ số phần', hint='', effects=dict(xp=6, money=20), good=True,
                       outcome='Đội bóng ăn no, thắng giao hữu hai bàn.'),
                  dict(id='no', label='Từ chối vì sợ không kịp', hint='', effects=dict(), good=None,
                       outcome='Thầy Lâm dẫn đội ra quán ngoài cổng.')],
         default='no'),
]

# ---------------------------------------------------------------- the career's coach line on the intro
INTRO = dict(
    title='Một ngày ở căn tin trường',
    lead='Bạn đứng quầy căn tin trường Tiểu học Phố Mây cùng cô Sáu: sáng bán đồ ăn sáng trước giờ vào lớp, giờ ra chơi bán nước, '
         'đồ ăn vặt, trưa chia cơm phần cho các lớp bán trú. Mọi món bày hết trên quầy: chạm để lấy, đủ rồi bấm Giao.',
    work=[['🍙', 'Sáng: xôi, bánh mì, mì ly, sữa trước giờ vào lớp'], ['🔔', 'Ra chơi 20 phút: nước, ăn vặt cho cả nhóm'],
          ['🍱', 'Trưa: chia cơm phần đủ cơm, mặn, rau, canh'], ['🧪', 'Lưu mẫu thức ăn, hỏi dị ứng, giữ giá niêm yết']],
    meet=[['👩‍🍳', 'Cô Sáu Mận bếp chính'], ['🥁', 'Chú Tư Gác đánh trống'], ['🎒', 'Học trò các lớp'], ['👩‍🏫', 'Cô Hạnh chủ nhiệm 2A']],
    stars=[['⏱️', 'Giao kịp trước trống'], ['🥛', 'Đúng dị ứng, đúng ngày chay'], ['💰', 'Vừa tiền tiêu vặt của bé']],
    short=[['🍙', 'Đồ ăn sáng trước trống'], ['🔔', 'Ra chơi bán nước, ăn vặt'], ['🍱', 'Trưa chia cơm phần']],   # the intro card's three rows
)
