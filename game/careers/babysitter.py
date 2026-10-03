"""Bảo mẫu trông trẻ: a day minding one family's child (plugin career).

Cô Tâm runs a small babysitting service, "Tổ trông trẻ Mèo Con", from her flat in ngõ Hoa Sữa: parents book
her for a day, she sends someone she trusts. The player is that someone. Each day is one family and one child,
and the day is a schedule the player runs block by block (one task per block, in order):

* ``arrive`` (slot 0): wash your hands, read the parents' note (allergy, nap time, the comfort toy, the screen
  rule, the child's temper), greet the child the way that child needs, check the bag and ask for what is missing;
* ``snack`` / ``meal``: build a plate from the kitchen counter (every dish says what is in it: the allergy is the
  player's to catch), prepare each dish for the child's age (grapes cut small, porridge cooled, fish deboned),
  wash the child's hands, seat the child, serve;
* ``play``: read the child's mood, pick an activity that fits it (and the child's age: small parts are for big
  children only; screens only when the note allows), then three small moments of play answered warmly;
* ``safety``: sweep the room before the child plays: tap the hazards (an open socket, a hot cup, the stairs
  gate, beads on the floor…) among harmless things;
* ``nap``: the bedtime routine (potty, curtains, the right comfort toy, a lullaby), then pat gently in time with
  the child's breathing (a stop tap, kit.tap_now) until the child is asleep;
* ``moment``: a small moment handled with care moves on a calm meter: tears after the nap, a scraped knee
  (basic first aid, in order), a tantrum;
* ``handover``: the day log for the parent, built from what really happened (ticking a line that is not true,
  or leaving out the scrape, is not honest), then the parent pays for the day.

Pay is per day, at the handover: the family's day rate, a bonus for good care, a loyalty bonus that grows with
each good day for the same family, and a small tip from a happy parent. Nothing frightening happens: safety is
taught through choices. For the first two days cô Tâm stops each kind of mistake once before it is made.

Mistakes go through consequences (cq.slip / cq.react); money only through the engine's money().
Everything random is rolled from the day, slot or task id: make_task is pure.
"""
from __future__ import annotations

import copy
import hashlib

from ..jsoncopy import tree_copy
from . import kit
from .. import consequences as cq

ID = 'babysitter'
GEN = 1
OPEN = 7 * 60 + 30          # the first parent drops the child off at 7:30
CLOSE = 18 * 60             # and picks the child up at 18:00

# ---------------------------------------------------------------- the people
PEOPLE = [
    ('Cô Tâm', 'Chủ tổ trông trẻ Mèo Con', 'Hai mươi năm làm cô nuôi dạy trẻ, giờ nhận gửi bé theo ngày ở ngõ Hoa Sữa.', 'warm'),
    ('Chị Hạnh', 'Mẹ bé Bin, 3 tuổi', 'Làm y tá ca ngày, dặn dò ngắn mà kỹ, tin người là tin hẳn.', 'parent_kind'),
    ('Anh Quân', 'Bố bé Na, 5 tuổi', 'Lần đầu gửi con cho người ngoài, cứ nhắn hỏi “bé ổn không em”.', 'parent_worried'),
    ('Chị Mai', 'Mẹ bé Sóc, 18 tháng', 'Kế toán, giấy dặn đánh máy in sẵn, giờ nào ra giờ đó.', 'parent_strict'),
    ('Bà Tư', 'Bà ngoại bé Mít, 6 tuổi', 'Đi tái khám mắt cả ngày, gửi cháu kèm hộp bánh tự làm.', 'warm'),
    ('Anh Duy', 'Bố bé Bông, 2 tuổi', 'Thợ điện, ít nói, về là hỏi đúng một câu: “Hôm nay con ăn ngủ sao?”', 'quiet'),
]

ALLERGENS = {'egg': 'trứng', 'peanut': 'đậu phộng', 'milk': 'sữa bò', 'shrimp': 'tôm'}
BANDS = ('baby', 'small', 'big')                 # under 2 · 2-3 years · 4-6 years
YOUNG = ('baby', 'small')                         # under 4: food cut small, nothing hard, no small parts
LOVEYS = {'gau': ('🧸', 'Gấu bông nâu'), 'chan': ('🟦', 'Chăn nhỏ màu xanh'), 'nuc': ('⭐', 'Núm ti ngôi sao'),
          'tho': ('🐰', 'Thỏ bông hồng'), 'khan': ('🧣', 'Khăn sữa hình thỏ'), 'vit': ('🦆', 'Vịt cao su vàng')}
TEMPERS = {'shy': ('🙈', 'nhút nhát, hay nép sau lưng mẹ', 'squat'),
           'lively': ('⚡', 'hiếu động, mê đập tay', 'hi5'),
           'clingy': ('🤱', 'bám mẹ, chưa quen người lạ', 'wait'),
           'chatty': ('💬', 'nói nhiều, thích kể chuyện', 'ask'),
           'stubborn': ('😤', 'bướng, không thích bị bế', 'squat')}
GREETS = {'squat': ('🧎', 'Ngồi ngang tầm mắt, chào nhỏ nhẹ'), 'hi5': ('✋', 'Đập tay chào thật vui'),
          'wait': ('🤗', 'Để bé ôm mẹ thêm, chìa đồ chơi ra'), 'ask': ('💬', 'Hỏi bé hôm qua đi chơi đâu'),
          'grab': ('🙆', 'Bế xốc bé lên cho nhanh')}

# The families: who, the child, and what the note says. Day rate in xu.
FAMILIES = {
    'bin': dict(npc=1, kid='Bin', age='3 tuổi', band='small', temper='shy', allergy='egg', nap=12 * 60 + 30, lovey='gau',
                screen=0, likes='chuoi', rate=70, home='flat', parent='chị Hạnh'),
    'na': dict(npc=2, kid='Na', age='5 tuổi', band='big', temper='lively', allergy='peanut', nap=13 * 60, lovey='chan',
               screen=20, likes='dua_hau', rate=75, home='tube', parent='anh Quân'),
    'soc': dict(npc=3, kid='Sóc', age='18 tháng', band='baby', temper='clingy', allergy=None, nap=12 * 60, lovey='nuc',
                screen=0, likes='chao_ga', rate=85, home='flat', parent='chị Mai'),
    'mit': dict(npc=4, kid='Mít', age='6 tuổi', band='big', temper='chatty', allergy='shrimp', nap=13 * 60, lovey='tho',
                screen=30, likes='tao', rate=65, home='garden', parent='bà Tư'),
    'bong': dict(npc=5, kid='Bông', age='2 tuổi', band='small', temper='stubborn', allergy='milk', nap=12 * 60 + 30, lovey='khan',
                 screen=0, likes='banh_gao', rate=75, home='tube', parent='anh Duy'),
}
FAM_ROWS = [dict(id='bin', weight=3), dict(id='na', min_day=2, weight=3), dict(id='mit', min_day=2, weight=2),
            dict(id='soc', min_day=3, weight=2), dict(id='bong', min_day=4, weight=2)]

# What a child's bag should hold (the comfort toy is the child's own, see LOVEYS).
BAG = {'nuoc': ('🍼', 'Bình nước'), 'ao': ('👕', 'Bộ đồ thay'), 'bim': ('🩲', 'Bỉm'), 'khan_uot': ('🧻', 'Khăn ướt'),
       'mu': ('🧢', 'Mũ'), 'lovey': ('🧸', 'Đồ ôm ngủ')}
BAG_FOR = {'baby': ['nuoc', 'ao', 'bim', 'khan_uot', 'lovey'], 'small': ['nuoc', 'ao', 'bim', 'khan_uot', 'lovey'],
           'big': ['nuoc', 'ao', 'khan_uot', 'mu', 'lovey']}

# ---------------------------------------------------------------- the kitchen counter
# group: snack / drink / main / veg · al: what is in it that a child can be allergic to · prep: what a dish needs
# before a child eats it (cut: only for under-4s; cool and bone: always) · hard: never for under-4s.
FOODS = {
    'chuoi': dict(name='Chuối', emoji='🍌', group='snack', al=[], prep=None, hard=False),
    'nho': dict(name='Nho', emoji='🍇', group='snack', al=[], prep='cut', hard=False),
    'tao': dict(name='Táo', emoji='🍎', group='snack', al=[], prep='cut', hard=False),
    'dua_hau': dict(name='Dưa hấu', emoji='🍉', group='snack', al=[], prep='cut', hard=False),
    'banh_gao': dict(name='Bánh gạo', emoji='🍘', group='snack', al=[], prep=None, hard=False),
    'bong_lan': dict(name='Bánh bông lan', emoji='🍰', group='snack', al=['egg', 'milk'], prep=None, hard=False),
    'quy_lac': dict(name='Bánh quy bơ đậu phộng', emoji='🍪', group='snack', al=['peanut', 'milk'], prep=None, hard=False),
    'sua_chua': dict(name='Sữa chua', emoji='🍶', group='snack', al=['milk'], prep=None, hard=False),
    'lac_rang': dict(name='Đậu phộng rang', emoji='🥜', group='snack', al=['peanut'], prep=None, hard=True),
    'keo_cung': dict(name='Kẹo cứng', emoji='🍬', group='snack', al=[], prep=None, hard=True),
    'nuoc': dict(name='Nước lọc ấm', emoji='💧', group='drink', al=[], prep=None, hard=False),
    'sua_dau': dict(name='Sữa đậu nành', emoji='🥤', group='drink', al=[], prep=None, hard=False),
    'sua_bo': dict(name='Sữa tươi', emoji='🥛', group='drink', al=['milk'], prep=None, hard=False),
    'chao_ga': dict(name='Cháo gà', emoji='🍲', group='main', al=[], prep='cool', hard=False),
    'com_ca': dict(name='Cơm cá kho', emoji='🐟', group='main', al=[], prep='bone', hard=False),
    'chao_tom': dict(name='Cháo tôm', emoji='🦐', group='main', al=['shrimp'], prep='cool', hard=False),
    'trung_hap': dict(name='Trứng hấp', emoji='🥚', group='main', al=['egg'], prep=None, hard=False),
    'com_xuc_xich': dict(name='Cơm xúc xích', emoji='🌭', group='main', al=[], prep='cut', hard=False),
    'canh_bi': dict(name='Canh bí đỏ', emoji='🎃', group='veg', al=[], prep='cool', hard=False),
    'rau_cu': dict(name='Cà rốt, bông cải luộc', emoji='🥕', group='veg', al=[], prep='cut', hard=False),
    'dau_hu': dict(name='Đậu hũ non sốt cà', emoji='🍅', group='veg', al=[], prep=None, hard=False),
}
GROUPS = {'snack': 'Món ăn vặt', 'drink': 'Đồ uống', 'main': 'Món chính', 'veg': 'Rau, canh'}
PREP = {'cut': ('✂️', 'Cắt nhỏ'), 'cool': ('🌬️', 'Để nguội bớt'), 'bone': ('🦴', 'Gỡ xương')}
MEALS = {'snack': ['snack', 'drink'], 'meal': ['main', 'veg', 'drink']}

# ---------------------------------------------------------------- play
MOODS = {'tired': ('🥱', 'Bé dụi mắt, ngáp nhỏ'), 'bouncy': ('🤸', 'Bé chạy vòng vòng, cười khanh khách'),
         'grumpy': ('😣', 'Bé phụng phịu, ném gấu xuống sàn'), 'curious': ('🧐', 'Bé chỉ trỏ, hỏi “cái gì đây?”')}
ACTS = {
    'blocks': dict(name='Xếp khối gỗ', emoji='🧱', fits=['tired', 'curious'], min='baby', small=False, screen=False),
    'book': dict(name='Đọc truyện tranh', emoji='📚', fits=['tired', 'curious'], min='baby', small=False, screen=False),
    'song': dict(name='Hát vỗ tay', emoji='🎵', fits=['tired', 'grumpy'], min='baby', small=False, screen=False),
    'ball': dict(name='Lăn bóng vải', emoji='⚽', fits=['bouncy'], min='baby', small=False, screen=False),
    'water': dict(name='Đong nước, thả vịt', emoji='🛁', fits=['grumpy', 'bouncy'], min='baby', small=False, screen=False),
    'dance': dict(name='Nhảy theo nhạc', emoji='💃', fits=['bouncy'], min='small', small=False, screen=False),
    'hide': dict(name='Trốn tìm', emoji='🙈', fits=['bouncy'], min='small', small=False, screen=False),
    'draw': dict(name='Vẽ sáp màu', emoji='🖍️', fits=['grumpy', 'curious'], min='small', small=False, screen=False),
    'clay': dict(name='Nặn đất nặn', emoji='🎨', fits=['grumpy', 'curious'], min='small', small=False, screen=False),
    'puzzle': dict(name='Ghép tranh 9 mảnh', emoji='🧩', fits=['curious'], min='small', small=False, screen=False),
    'lego': dict(name='Lego mảnh nhỏ', emoji='🏗️', fits=['curious'], min='big', small=True, screen=False),
    'beads': dict(name='Xâu hạt cườm', emoji='📿', fits=['curious', 'tired'], min='big', small=True, screen=False),
    'tv': dict(name='Xem hoạt hình', emoji='📺', fits=['tired'], min='baby', small=False, screen=True),
}
# Small moments of play; the warm answer (2) lifts the joy most, a curt one (0) dims it.
BEATS = {
    'fall': ('Bé làm đổ cả chồng đồ chơi, mếu máo.', [('cheer', 'Cùng bé làm lại, khen bé cố gắng', 2),
                                                      ('fix', 'Làm lại giùm bé cho nhanh', 1), ('stop', 'Thôi, không chơi nữa', 0)]),
    'ask': ('Bé hỏi: “Sao con mèo kêu meo meo?”', [('answer', 'Kêu meo meo theo bé, hỏi lại con gì kêu gâu gâu', 2),
                                                   ('short', 'Ừ, mèo thì kêu vậy', 1), ('hush', 'Đừng hỏi nữa, chơi đi', 0)]),
    'self': ('Bé giành lấy: “Con tự làm!”', [('let', 'Để bé tự làm, ngồi cạnh đỡ khi cần', 2),
                                             ('half', 'Cầm tay bé làm chung', 1), ('take', 'Lấy lại làm cho nhanh', 0)]),
    'show': ('Bé giơ lên khoe: “Nhìn nè!”', [('praise', 'Khen cụ thể: “Con chọn màu xanh đẹp quá!”', 2),
                                             ('ok', 'Ừ, đẹp', 1), ('phone', 'Đang nhắn tin, không ngẩng lên', 0)]),
    'bored': ('Bé bắt đầu chán, nhìn quanh.', [('twist', 'Thêm bạn gấu vào trò chơi', 2),
                                               ('wait', 'Chờ bé tự tìm trò khác', 1), ('sit', 'Bảo bé ngồi yên', 0)]),
    'share': ('Bé không chịu cho bạn gấu chơi chung.', [('turns', 'Chơi lần lượt: bé một lượt, gấu một lượt', 2),
                                                       ('skip', 'Kệ, chơi một mình cũng được', 1), ('grab', 'Giật đồ chơi đưa cho gấu', 0)]),
    'mess': ('Đồ chơi vương khắp sàn.', [('game', 'Biến dọn dẹp thành trò thi nhặt', 2),
                                        ('later', 'Để lát dọn', 1), ('yell', 'La bé bày bừa', 0)]),
}
PLAY_BEATS = 3
JOY_FIT, JOY_MISFIT, JOY_TV = 40, 20, 45
JOY_STEP = {2: 20, 1: 8, 0: -10}

# ---------------------------------------------------------------- the room sweep
# (emoji, what you see, hazard?, what you do about it)
HAZ = {
    'socket': ('🔌', 'Ổ điện sát sàn không có nắp', True, 'Cắm nắp che ổ điện'),
    'cup': ('☕', 'Cốc trà nóng sát mép bàn', True, 'Cất cốc trà lên cao'),
    'stairs': ('🪜', 'Cửa chặn cầu thang đang mở', True, 'Đóng cửa chặn cầu thang'),
    'beads': ('📿', 'Hạt cườm rơi dưới gầm ghế', True, 'Nhặt hạt cườm vào hộp'),
    'scissors': ('✂️', 'Cây kéo để trên ghế', True, 'Cất kéo vào ngăn kéo'),
    'cord': ('🪟', 'Dây rèm thòng xuống sàn', True, 'Buộc gọn dây rèm lên cao'),
    'meds': ('💊', 'Vỉ thuốc trên bàn thấp', True, 'Cất thuốc lên tủ cao'),
    'chair': ('🪑', 'Ghế đẩu kê sát cửa sổ', True, 'Kéo ghế ra xa cửa sổ'),
    'bucket': ('🪣', 'Xô nước đầy ngoài sân', True, 'Đổ nước, úp xô xuống'),
    'coin': ('🪙', 'Đồng xu trên kệ thấp', True, 'Cất đồng xu vào hũ'),
    'wet': ('💦', 'Sàn ướt chỗ cửa ra vào', True, 'Lau khô sàn'),
    'pillow': ('🛋️', 'Gối ôm trên sofa', False, ''),
    'book': ('📚', 'Sách tranh trên kệ', False, ''),
    'teddy': ('🧸', 'Thú bông to', False, ''),
    'plant': ('🪴', 'Chậu cây trên kệ cao', False, ''),
    'clock': ('🕰️', 'Đồng hồ treo tường', False, ''),
    'mat': ('🟩', 'Thảm xốp lót sàn', False, ''),
    'softball': ('⚽', 'Bóng vải mềm', False, ''),
    'bottle': ('🍼', 'Bình nước của bé, nắp đậy kín', False, ''),
    'lamp': ('💡', 'Đèn ngủ gắn tường', False, ''),
}
HOMES = {'flat': dict(name='Căn hộ chung cư', haz=['socket', 'cup', 'cord', 'meds', 'chair', 'coin', 'scissors', 'beads']),
         'tube': dict(name='Nhà ống ba tầng', haz=['stairs', 'socket', 'cup', 'meds', 'scissors', 'coin', 'beads']),
         'garden': dict(name='Nhà có sân trước', haz=['bucket', 'socket', 'cup', 'cord', 'scissors', 'meds', 'beads'])}
SAFE_ITEMS = ['pillow', 'book', 'teddy', 'plant', 'clock', 'mat', 'softball', 'bottle', 'lamp']
ROOM_SIZE = 8

# ---------------------------------------------------------------- nap
NAP_STEPS = {'potty': ('🚽', 'Cho bé đi vệ sinh'), 'dark': ('🌙', 'Kéo rèm, tắt đèn'), 'song': ('🎵', 'Hát ru một bài')}
CYCLE = 4.0                 # one breath of a child settling down (seconds)
PAT_WIN = (0.50, 0.85)      # the slow breath out: a pat here soothes
PAT_WIN_EASY = (0.40, 0.95)
SLEEP_PATS = 3

# ---------------------------------------------------------------- small moments: care moves on a calm meter
# (emoji, label, calm change, slip code or None); scrape steps carry their order.
MOVES = {
    'cry': {'hug': ('🤗', 'Ôm bé vào lòng', 35, None), 'name': ('💬', 'Nói: “Bé nhớ mẹ phải không?”', 30, None),
            'lovey': ('🧸', 'Đưa đồ ôm quen thuộc', 25, None), 'window': ('🪟', 'Bế ra cửa sổ xem chim sẻ', 20, None),
            'scold': ('😠', 'Bảo: “Nín ngay!”', -25, 'harsh'), 'phone': ('📱', 'Đưa điện thoại cho bé xem', -10, 'give_in')},
    'scrape': {'wash': ('🧼', 'Rửa tay mình thật sạch', 20, None), 'rinse': ('🚿', 'Rửa vết xước bằng nước sạch', 20, None),
               'dry': ('🩹', 'Thấm khô bằng gạc sạch', 20, None), 'plaster': ('🩹', 'Dán băng cá nhân', 20, None),
               'hug': ('🤗', 'Ôm, dỗ bé, cho uống ngụm nước', 20, None),
               'paste': ('🪥', 'Bôi kem đánh răng lên vết xước', -15, 'folk'), 'blow': ('💨', 'Thổi phù phù rồi cho chơi tiếp', -10, 'aid')},
    'tantrum': {'breath': ('😮‍💨', 'Hít một hơi, giữ giọng nhẹ', 20, None), 'sit': ('🧎', 'Ngồi xuống cạnh bé', 25, None),
                'name': ('💬', 'Nói: “Con đang bực vì muốn kẹo”', 25, None), 'choice': ('🎨', 'Cho bé chọn: tô màu hay xếp hình?', 30, None),
                'shout': ('📢', 'Quát to cho bé sợ', -25, 'harsh'), 'give': ('🍬', 'Đưa kẹo cho bé nín', -5, 'give_in'),
                'threat': ('👻', 'Dọa: “Ông kẹ bắt bây giờ!”', -20, 'scare')},
}
SCRAPE_ORDER = ['wash', 'rinse', 'dry', 'plaster']
MOMENT_TITLE = {'cry': 'khóc nhớ mẹ', 'scrape': 'ngã trầy đầu gối', 'tantrum': 'ăn vạ đòi kẹo'}
MOMENT_OPEN = {'cry': '{Kid} ngủ dậy không thấy mẹ, mếu máo rồi khóc to.',
               'scrape': '{Kid} chạy vấp thảm, ngã sấp, đầu gối trầy một vệt nhỏ, rơm rớm máu. Bé nhìn bạn, môi run run.',
               'tantrum': '{Kid} thấy hũ kẹo trên tủ, đòi lấy. Bạn chưa cho, bé lăn ra sàn ăn vạ.'}

# ---------------------------------------------------------------- the handover log
LOG_IDS = ('food', 'nap', 'play', 'safe', 'moment', 'oops', 'fine', 'tv')

KINDS = ('arrive', 'snack', 'meal', 'play', 'safety', 'nap', 'moment', 'handover')
STAGES = ('work', 'done')

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Bố mẹ đi làm sớm, đón bé lúc 18:00.', weight=3),
    dict(id='rain', emoji='🌧️', label='Mưa cả ngày', hint='Bé chơi trong nhà cả ngày: sàn chỗ cửa dễ ướt, soát kỹ.', min_day=2, weight=2),
    dict(id='sniffle', emoji='🤧', label='Bé hơi sổ mũi', hint='Bố mẹ dặn: chỉ uống nước ấm, không sữa lạnh.', min_day=3, weight=2),
]

# A family's story, one line per good day with them (loyalty).
FAM_STORY = {
    'bin': ('Bé Bin vẫy tay chào bạn tới tận cổng chung cư.', 'Chị Hạnh dán số của bạn lên tủ lạnh: “Gọi khi cần trông Bin.”',
            'Bé Bin vẽ tặng bạn một bức tranh: hai người nắm tay, một con gấu nâu.'),
    'na': ('Anh Quân nhắn: “Lần đầu anh đi làm mà không lo.”', 'Bé Na đòi bố cho “cô bảo mẫu” qua chơi cuối tuần.',
           'Anh Quân giới thiệu bạn cho cả nhóm phụ huynh lớp Lá.'),
    'soc': ('Chị Mai gật đầu: “Đúng giờ, đúng giấy dặn. Mai em trông tiếp nhé.”', 'Bé Sóc giơ tay đòi bạn bế ngay ở cửa.',
            'Chị Mai in giấy dặn mới, dòng cuối ghi: “Tin em.”'),
    'mit': ('Bà Tư dúi cho bạn hộp bánh da lợn: “Bà làm đó, con ăn.”', 'Bé Mít kể cả xóm nghe chuyện cô bảo mẫu biết trốn tìm giỏi.',
            'Bà Tư nói: “Có con trông, bà đi khám mắt yên tâm hẳn.”'),
    'bong': ('Anh Duy nói đúng một câu: “Cảm ơn em.” Rồi cười.', 'Bé Bông chịu cho bạn bế mà không vùng ra.',
             'Anh Duy sửa giùm cô Tâm cái ổ điện, không lấy tiền: “Em trông con anh kỹ quá.”'),
}
TRUST_MAX = 3
LOYAL = 4                   # xu more a day per level of a family's trust
CARE_BONUS = ((90, 12), (70, 6))
TIP = (4, 12)

INTRO = dict(
    title='Giới thiệu nghề: bảo mẫu trông trẻ',
    lead='Cô Tâm nhận gửi bé theo ngày ở ngõ Hoa Sữa. Mỗi sáng bạn tới một nhà, trông một bé tới chiều bố mẹ về.',
    work=[('📝', 'Đọc giấy dặn: dị ứng, giờ ngủ, đồ ôm, màn hình'), ('🍽️', 'Dọn món hợp tuổi, tránh món bé dị ứng'),
          ('🧸', 'Chọn trò chơi hợp tâm trạng bé'), ('🔌', 'Soát nhà: ổ điện, cốc nóng, cầu thang, đồ nhỏ'),
          ('😴', 'Ru ngủ: vỗ nhẹ theo nhịp thở'), ('🩹', 'Dỗ bé khóc, sơ cứu vết xước, bé ăn vạ'),
          ('👋', 'Bàn giao: kể đúng những gì đã xảy ra')],
    meet=[('👩‍⚕️', 'Chị Hạnh và bé Bin 3 tuổi, nhút nhát'), ('👨', 'Anh Quân và bé Na 5 tuổi, hiếu động'),
          ('👩‍💼', 'Chị Mai và bé Sóc 18 tháng'), ('👵', 'Bà Tư và bé Mít 6 tuổi, hay hỏi'),
          ('🔧', 'Anh Duy và bé Bông 2 tuổi, bướng'), ('👩‍🏫', 'Cô Tâm, người dạy bạn nghề')],
    stars=[('🛡️', 'Bé an toàn cả ngày'), ('🍽️', 'Ăn đúng món, hợp tuổi'), ('😴', 'Ngủ đúng giờ, ngủ ngon'),
           ('😊', 'Bé vui, được chơi đúng ý'), ('📝', 'Bàn giao rõ ràng, trung thực')],
)

# ---------------------------------------------------------------- học nghề: the first days with cô Tâm on the phone
APPRENTICE = 2
LESSONS = [
    ('Ngày 1 · Giấy dặn là trên hết', 'Cô Tâm dặn: “Đọc giấy dặn trước khi làm gì. Dị ứng, giờ ngủ, đồ ôm: nhớ hết, lỡ quên thì mở ra coi lại.”'),
    ('Ngày 2 · Nhìn bằng mắt của bé', 'Cô Tâm nhắc: “Ngồi xuống ngang tầm bé mà nhìn. Ổ điện, cốc nóng, hạt nhỏ: thấy là xử lý liền.”'),
]
CATCH = {
    'note': 'Khoan đã con, đọc giấy dặn của bố mẹ bé trước rồi hẵng nhận bé.',
    'allergy': 'Dừng lại con! Món này có thứ bé dị ứng. Đọc kỹ thành phần trên từng món rồi chọn lại.',
    'choke': 'Khoan, bé dưới bốn tuổi không ăn đồ cứng, hạt nhỏ. Bỏ món đó ra.',
    'prep': 'Chưa sơ chế kìa con: cắt nhỏ cho bé nhỏ, cháo canh để nguội, cá gỡ xương.',
    'small': 'Đồ chơi mảnh nhỏ chỉ cho bé lớn. Bé này còn nhỏ, chọn trò khác nghe.',
    'screen': 'Giấy dặn ghi giờ này không xem màn hình. Chọn trò khác con.',
    'hazard': 'Còn chỗ nguy hiểm trong phòng đó con. Ngồi xuống ngang tầm bé nhìn lại.',
    'routine': 'Ru bé ngủ thì đủ bước: đi vệ sinh, kéo rèm, đồ ôm, hát ru.',
    'harsh': 'Nhẹ giọng thôi con. Bé sợ thì bé không nghe đâu.',
    'scare': 'Đừng dọa bé con. Bé nhớ cái sợ lâu lắm.',
    'folk': 'Không bôi kem đánh răng nghe con. Rửa nước sạch, thấm khô, dán băng là đủ.',
    'aid': 'Vết xước phải rửa sạch trước đã con.',
    'aid_order': 'Sơ cứu theo thứ tự: rửa tay mình, rửa vết xước, thấm khô, rồi mới dán băng.',
    'hide': 'Chuyện bé ngã, bé khóc phải kể với bố mẹ con. Giấu là mất lòng tin.',
}

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='neighbor_snack', title='Bác hàng xóm cho bé bánh', emoji='🍪', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Bác hàng xóm ghé cửa, chìa cho bé gói bánh quy: “Cho cháu ăn lấy thảo nè.” Trên vỏ có chữ “bơ đậu phộng”.',
         options=[dict(id='thank', label='Cảm ơn bác, cất lại để bố mẹ bé xem; đưa bé món bé ăn được', hint='', effects=dict(xp=4), good=True,
                       outcome='Bác cười: “Ờ phải, giờ tụi nhỏ hay dị ứng.” Bé vui với miếng chuối.'),
                  dict(id='half', label='Bẻ cho bé một miếng nhỏ thôi', hint='',
                       effects=dict(review=[2, 'Con tôi ăn đồ người lạ cho mà không ai hỏi một câu.']), good=False,
                       outcome='Bạn kịp nhớ ra, lấy lại miếng bánh. Hú vía.'),
                  dict(id='refuse', label='Từ chối thẳng, đóng cửa', hint='', effects=dict(patience=-2), good=None,
                       outcome='Bác hơi phật ý, đi về.')],
         default='refuse'),
    dict(id='doorbell', title='Có người bấm chuông', emoji='🔔', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Chuông cửa reo. Một chị đứng ngoài: “Chị là bạn mẹ bé, cho chị vào chờ mẹ bé chút.” Giấy dặn không nhắc ai cả.',
         options=[dict(id='call', label='Nói chuyện qua cửa, nhắn hỏi bố mẹ bé trước khi mở', hint='', effects=dict(xp=5), good=True,
                       outcome='Mẹ bé nhắn lại: “Đúng bạn chị, nhưng em cứ để bạn ấy chờ ngoài quán nước nhé.” Chị kia cười, đi ra quán.'),
                  dict(id='open', label='Mở cửa mời vào, người quen mà', hint='',
                       effects=dict(review=[2, 'Ai bấm chuông cũng mở cửa cho vào khi đang trông con tôi.']), good=False,
                       outcome='Không sao cả, nhưng bố mẹ bé nghe kể thì nhíu mày.'),
                  dict(id='ignore', label='Im lặng, không trả lời', hint='', effects=dict(patience=-2), good=None,
                       outcome='Chị kia chờ một lúc rồi đi. Bé hỏi “ai vậy cô?” mãi.')],
         default='ignore'),
    dict(id='photo', title='Ảnh bé dễ thương quá', emoji='📸', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Bé đội cái nồi lên đầu làm mũ, cười tít mắt. Ảnh đẹp quá, đăng lên mạng chắc nhiều người thích.',
         options=[dict(id='parent', label='Chụp gửi riêng cho bố mẹ bé', hint='', effects=dict(xp=4), good=True,
                       outcome='Mẹ bé thả tim liền: “Trời ơi dễ thương quá, cảm ơn em!”'),
                  dict(id='post', label='Đăng lên trang cá nhân, che mặt bé', hint='',
                       effects=dict(review=[2, 'Ảnh con tôi lên mạng mà không hỏi tôi một câu.']), good=False,
                       outcome='Mẹ bé thấy bài đăng, nhắn nhẹ: “Em gỡ giúp chị nha.”'),
                  dict(id='none', label='Thôi khỏi chụp', hint='', effects={}, good=None, outcome='Bé tự cười một mình với cái nồi.')],
         default='none'),
    dict(id='warm_head', title='Trán bé hơi ấm', emoji='🌡️', npc=0, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Bé dụi vào người bạn, trán hơi ấm hơn mọi khi. Bé vẫn chơi, vẫn cười.',
         options=[dict(id='check', label='Đo nhiệt độ, cho uống nước, nhắn bố mẹ bé', hint='', effects=dict(xp=5), good=True,
                       outcome='37,4 độ. Mẹ bé dặn cứ theo dõi, chiều về chị đưa đi khám. Tối bé vẫn ngủ ngon.'),
                  dict(id='medicine', label='Tự lấy thuốc hạ sốt trong tủ cho bé uống', hint='',
                       effects=dict(review=[1, 'Tự ý cho con tôi uống thuốc, không hỏi một câu.']), good=False,
                       outcome='Mẹ bé gọi điện ngay, giọng lo lắng: thuốc phải đúng liều theo cân nặng.'),
                  dict(id='wait', label='Chắc do chạy nhiều, để xem sao', hint='', effects=dict(patience=-2), good=None,
                       outcome='Chiều bé hết ấm, nhưng bạn vẫn kể lại khi bàn giao.')],
         default='wait'),
    dict(id='friend_call', title='Bạn gọi rủ đi chơi', emoji='📞', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Bạn thân gọi video, rủ tối đi ăn, nói mãi chưa dứt. Bé đang chơi một mình ở góc phòng.',
         options=[dict(id='later', label='“Mình đang trông bé, tối gọi lại nha”', hint='', effects=dict(xp=3), good=True,
                       outcome='Bạn quay lại chơi với bé. Bé khoe cái tháp vừa xếp xong.'),
                  dict(id='talk', label='Nói thêm chút, bé chơi ngoan mà', hint='', effects=dict(patience=-3), good=False,
                       outcome='Ngẩng lên thì bé đã leo lên ghế, may mà bạn kịp đỡ xuống.')],
         default='later'),
    dict(id='rain_wash', title='Mưa đổ, đồ phơi ngoài sân', emoji='🌧️', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=('rain',),
         text='Trời đổ mưa ào ào. Quần áo bố mẹ bé phơi ngoài sân sắp ướt hết.',
         options=[dict(id='together', label='Dắt bé theo, đứng mái hiên, rút đồ thật nhanh', hint='', effects=dict(xp=4), good=True,
                       outcome='Bé giúp ôm mấy cái khăn, cười khoái chí. Đồ khô ráo.'),
                  dict(id='leave', label='Để bé một mình trong nhà, chạy ra rút đồ', hint='', effects=dict(patience=-2), good=False,
                       outcome='Rút xong quay vào, bé đang đứng khóc ở cửa tìm bạn.'),
                  dict(id='skip', label='Thôi kệ đồ, ở với bé', hint='', effects={}, good=None, outcome='Mẹ bé về phải giặt lại mấy cái áo.')],
         default='skip'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='BM-S01', title='Bà nội muốn cho cháu ăn bánh trứng', npc=1, tone='gentle', min_day=2,
         opening='Bà nội bé Bin ghé thăm, mang hộp bánh bông lan: “Cháu bà phải ăn bánh bà làm. Dị ứng gì, hồi xưa có ai dị ứng đâu.”',
         facts=[dict(id='note', title='Giấy dặn', source='Chị Hạnh', text='Bé Bin dị ứng trứng, từng nổi mẩn khắp người khi ăn bánh có trứng.'),
                dict(id='box', title='Hộp bánh', source='Nhìn kỹ', text='Bánh bông lan làm từ trứng gà, bột mì, sữa.'),
                dict(id='bin', title='Bé Bin', source='Bé', text='Bé thích bánh gạo và chuối lắm.')],
         options=[dict(id='kind', label='Cảm ơn bà, nói nhẹ về giấy dặn, mời bà cùng cho bé ăn chuối', requires=['note', 'box'], quality='good', stars=5,
                       review='Em trông bé giữ đúng lời dặn mà vẫn khéo với bà. Chị yên tâm lắm.',
                       outcome='Bà gật gù, bóc chuối đút cháu, còn hỏi bánh nào không có trứng để lần sau làm.',
                       perspectives=[dict(who='Bà nội', emoji='👵', text='Ừ, bà không biết. Lần sau bà làm bánh gạo.'),
                                     dict(who='Chị Hạnh', emoji='👩‍⚕️', text='May có em. Mẹ chồng chị thương cháu quá.')]),
                  dict(id='call', label='Gọi chị Hạnh nói chuyện với bà', requires=['note'], quality='ok', stars=4,
                       review='Em gọi chị là đúng, nhưng lần sau em cứ nói với bà nhẹ nhàng trước.',
                       outcome='Chị Hạnh giải thích qua điện thoại, bà hơi buồn nhưng hiểu.',
                       perspectives=[dict(who='Bà nội', emoji='👵', text='Gọi tận cho mẹ nó, bà hơi ngại.'),
                                     dict(who='Chị Hạnh', emoji='👩‍⚕️', text='Không sao, em làm đúng giấy dặn.')]),
                  dict(id='give', label='Bà nội nói vậy thì chắc không sao', quality='bad', stars=1,
                       review='Giấy dặn ghi rõ dị ứng trứng. Chiều về bé nổi mẩn đỏ, phải đưa đi khám.',
                       outcome='Tối đó bé nổi mẩn, chị Hạnh phải đưa đi khám. May không nặng.',
                       perspectives=[dict(who='Chị Hạnh', emoji='😟', text='Chị viết rõ trong giấy rồi mà em.'),
                                     dict(who='Cô Tâm', emoji='👩‍🏫', text='Giấy dặn của bố mẹ là trên hết, kể cả với ông bà.')])],
         lesson='Giấy dặn của bố mẹ là trên hết. Từ chối nhẹ nhàng, mời món khác bé ăn được.'),
    dict(id='BM-S02', title='“Hôm nay bé có khóc không em?”', npc=2, tone='gentle', min_day=2,
         opening='Anh Quân về, câu đầu tiên: “Hôm nay bé Na có khóc không em? Nó mà khóc là anh xót lắm.”',
         facts=[dict(id='cry', title='Buổi trưa', source='Bạn nhớ', text='Bé Na khóc nhớ bố khoảng mười phút lúc ngủ dậy, ôm một lúc thì nín.'),
                dict(id='after', title='Buổi chiều', source='Bạn nhớ', text='Sau đó bé chơi vẽ tranh rất vui, còn vẽ tặng bố một bức.'),
                dict(id='dad', title='Anh Quân', source='Nhìn', text='Anh lo lắm, lần đầu gửi con cho người ngoài.')],
         options=[dict(id='honest', label='Kể thật: bé khóc lúc ngủ dậy, dỗ cách nào, rồi chiều bé vui ra sao', requires=['cry', 'after'], quality='good', stars=5,
                       review='Em kể rõ từng chuyện, anh thấy yên tâm hơn là nghe “bé ngoan lắm”.',
                       outcome='Anh Quân thở ra, cầm bức tranh bé vẽ: “Vậy là ổn rồi.”',
                       perspectives=[dict(who='Anh Quân', emoji='👨', text='Nghe thật mới yên tâm được.'),
                                     dict(who='Bé Na', emoji='👧', text='Bố ơi con vẽ bố nè!')]),
                  dict(id='soft', label='Nói bé “hơi mếu chút xíu” cho anh đỡ lo', requires=['cry'], quality='ok', stars=3,
                       review='Bé kể lại là khóc to lắm. Lần sau em cứ nói thật nha.',
                       outcome='Tối bé Na kể bố nghe “con khóc to lắm”. Anh Quân hơi chững lại.',
                       perspectives=[dict(who='Anh Quân', emoji='😐', text='Sao em không nói thẳng với anh?')]),
                  dict(id='deny', label='“Bé ngoan lắm, không khóc chút nào”', quality='bad', stars=1,
                       review='Con tôi kể nó khóc cả buổi trưa mà người trông bảo không có gì.',
                       outcome='Anh Quân nghe con kể lại, hỏi cô Tâm có nên đổi người trông không.',
                       perspectives=[dict(who='Anh Quân', emoji='😟', text='Chuyện nhỏ mà giấu thì chuyện lớn sao tin?'),
                                     dict(who='Cô Tâm', emoji='👩‍🏫', text='Bố mẹ cần nghe thật, kể cả chuyện bé khóc.')])],
         lesson='Bàn giao là kể thật: bé khóc, bé ngã, bé ăn ít. Kể kèm cách mình đã làm.'),
    dict(id='BM-S03', title='Bố cho xem điện thoại, mẹ thì không', npc=5, tone='gentle', min_day=3,
         opening='Anh Duy dặn nhỏ lúc đưa bé: “Bé quấy thì cho xem điện thoại cũng được.” Giấy dặn của mẹ bé ghi: “Không màn hình.”',
         facts=[dict(id='note', title='Giấy dặn', source='Mẹ bé Bông', text='Bé dưới 2 tuổi rưỡi: không xem màn hình, kể cả lúc ăn.'),
                dict(id='dad', title='Anh Duy', source='Lời dặn miệng', text='Anh chỉ muốn em đỡ vất vả, không muốn cãi vợ.'),
                dict(id='bong', title='Bé Bông', source='Bé', text='Bé mê sách tranh có hình xe cứu hỏa.')],
         options=[dict(id='note', label='Theo giấy dặn, kể lại với cả hai: bé chơi sách xe cứu hỏa thay điện thoại', requires=['note', 'bong'], quality='good', stars=5,
                       review='Em làm đúng giấy dặn mà còn tìm được trò bé mê. Cả nhà khen.',
                       outcome='Tối đó anh Duy mua thêm cuốn sách xe cứu hỏa thứ hai.',
                       perspectives=[dict(who='Anh Duy', emoji='🔧', text='Ờ, sách cũng được. Bé thích là được.'),
                                     dict(who='Mẹ bé Bông', emoji='👩', text='Cảm ơn em đã giữ đúng lời dặn.')]),
                  dict(id='ask', label='Nhắn hỏi lại mẹ bé cho chắc', requires=['note'], quality='ok', stars=4,
                       review='Hỏi lại cũng được, nhưng giấy dặn ghi rõ rồi mà em.',
                       outcome='Mẹ bé trả lời: “Không màn hình nha em.” Anh Duy cười trừ.',
                       perspectives=[dict(who='Anh Duy', emoji='🔧', text='Thôi nghe mẹ nó.')]),
                  dict(id='phone', label='Bố cho phép thì cho xem', quality='bad', stars=2,
                       review='Giấy dặn ghi không màn hình mà con tôi xem điện thoại cả buổi.',
                       outcome='Tối bé khó ngủ, mẹ bé hỏi ra mới biết.',
                       perspectives=[dict(who='Mẹ bé Bông', emoji='😕', text='Chị viết giấy dặn là để làm theo mà.')])],
         lesson='Lời dặn khác nhau thì theo giấy dặn, rồi kể lại với cả bố lẫn mẹ.'),
]


# ================================================================ small helpers
def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def family_of(day: int) -> str:
    if int(day) <= 1:
        return 'bin'
    return kit.daily(ID + '-family', day, FAM_ROWS)['id']


def fam(fid: str) -> dict:
    return FAMILIES[fid]


def kid(f: dict, cap: bool = False) -> str:
    return f'{"Bé" if cap else "bé"} {f["kid"]}'


def hhmm(m: int) -> str:
    return f'{m // 60}:{m % 60:02d}'


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def young(f: dict) -> bool:
    return f['band'] in YOUNG


def _band_ok(f: dict, act: dict) -> bool:
    return BANDS.index(f['band']) >= BANDS.index(act['min'])


def plan_of(day: int) -> list:
    """The day's schedule: [(kind, minute)], from the child's arrival to the handover. Pure from the day."""
    f = fam(family_of(day))
    if day <= 1:
        kinds = ['arrive', 'play', 'snack', 'nap', 'handover']
    elif day == 2:
        kinds = ['arrive', 'safety', 'meal', 'nap', 'play', 'handover']
    else:
        r = kit.rng(ID, 'plan', day)
        am = ['safety', 'play']
        r.shuffle(am)
        pm = ['moment'] + ([r.choice(['snack', 'play'])] if kit.tier(day) >= 2 else [])
        kinds = ['arrive'] + am + ['meal', 'nap'] + pm + ['handover']
    nap = kinds.index('nap')
    pre = kinds[1:nap]
    post = kinds[nap + 1:-1]
    out = [('arrive', OPEN)]
    end = f['nap'] - 45
    step = (end - 8 * 60) // max(1, len(pre) - 1) if len(pre) > 1 else 0
    for i, k in enumerate(pre):
        m = 8 * 60 + i * step
        out.append((k, m - m % 15))
    out.append(('nap', f['nap']))
    for i, k in enumerate(post):
        out.append((k, f['nap'] + 120 + i * 60))
    out.append(('handover', CLOSE))
    return out


def _slot(t: dict) -> int:
    return int(t['id'].rsplit('-', 1)[1])


def _parent(t_or_fid) -> str:
    fid = t_or_fid if isinstance(t_or_fid, str) else t_or_fid['needs']['fam']
    return PEOPLE[fam(fid)['npc']][0]


# ================================================================ tasks
def _menu(day: int, slot: int, f: dict, kind: str) -> list:
    """The kitchen counter for this meal: a safe choice in every group, and the dishes a careful sitter leaves out."""
    r = kit.rng(ID, 'menu', day, slot)
    out = []
    for g in MEALS[kind]:
        pool = [k for k, x in FOODS.items() if x['group'] == g]
        safe = [k for k in pool if f['allergy'] not in FOODS[k]['al'] and not (young(f) and FOODS[k]['hard'])]
        trap = [k for k in pool if k not in safe]
        r.shuffle(safe)
        r.shuffle(trap)
        n_safe = 3 if g in ('snack', 'main') else 2
        if g == 'drink':
            safe = ['nuoc'] + [k for k in safe if k != 'nuoc']
        pick = safe[:n_safe] + trap[:1]
        if f['likes'] in pool and f['likes'] in safe and f['likes'] not in pick:
            pick[0] = f['likes']
        out += [k for k in dict.fromkeys(pick)]
    r.shuffle(out)
    return out[:9]


def _room(day: int, slot: int, f: dict) -> list:
    r = kit.rng(ID, 'room', day, slot)
    haz = list(HOMES[f['home']]['haz'])
    r.shuffle(haz)
    n = 2 if kit.tier(day) == 0 else 3
    pick = haz[:n]
    if mod_of(day)['id'] == 'rain':
        pick.append('wet')
    safe = list(SAFE_ITEMS)
    r.shuffle(safe)
    items = pick + safe[:ROOM_SIZE - len(pick)]
    r.shuffle(items)
    return items


def _acts(day: int, slot: int, f: dict, mood: str, screen_ok: bool) -> list:
    r = kit.rng(ID, 'acts', day, slot)
    fit = [k for k, a in ACTS.items() if mood in a['fits'] and _band_ok(f, a) and not a['screen']]
    other = [k for k, a in ACTS.items() if mood not in a['fits'] and _band_ok(f, a) and not a['screen'] and not a['small']]
    r.shuffle(fit)
    r.shuffle(other)
    out = fit[:2] + other[:2]
    if young(f):
        out.append(r.choice(['lego', 'beads']))     # small parts on the shelf: not for this child
    out.append('tv')
    r.shuffle(out)
    return out


def _needs(kind: str, day: int, slot: int, f: dict, plan: list) -> dict:
    r = kit.rng(ID, 'needs', kind, day, slot)
    if kind == 'arrive':
        bag = list(BAG_FOR[f['band']])
        return dict(bag=bag, missing=r.choice(bag[:-1] if day <= 1 else bag))
    if kind in ('snack', 'meal'):
        return dict(menu=_menu(day, slot, f, kind), groups=list(MEALS[kind]))
    if kind == 'play':
        after_nap = [k for k, _ in plan].index('nap') < slot if slot < len(plan) else True
        mood = 'bouncy' if day <= 1 else r.choice(sorted(MOODS))
        screen_ok = bool(f['screen']) and after_nap
        beats = sorted(BEATS)
        r.shuffle(beats)
        return dict(mood=mood, acts=_acts(day, slot, f, mood, screen_ok), screen_ok=screen_ok, beats=beats[:PLAY_BEATS],
                    order=[r.sample(range(3), 3) for _ in range(PLAY_BEATS)])
    if kind == 'safety':
        return dict(items=_room(day, slot, f), home=f['home'])
    if kind == 'nap':
        others = [k for k in LOVEYS if k != f['lovey']]
        r.shuffle(others)
        choices = [f['lovey']] + others[:2]
        r.shuffle(choices)
        return dict(loveys=choices)
    if kind == 'moment':
        mk = r.choice(sorted(MOVES))
        moves = list(MOVES[mk])
        r.shuffle(moves)
        return dict(mk=mk, moves=moves)
    return {}


def _words(kind: str, f: dict, needs: dict) -> tuple[str, str]:
    k, K = kid(f), kid(f, True)
    p = _lower(PEOPLE[f['npc']][0])
    if kind == 'arrive':
        tm = TEMPERS[f['temper']]
        return (f'Nhận {k} lúc {hhmm(OPEN)}', f'{PEOPLE[f["npc"]][0]} bế {k} tới cửa, đưa túi đồ và tờ giấy dặn. {K} {tm[1]}.')
    if kind == 'snack':
        return (f'Bữa phụ của {k}', f'{K} kéo tay bạn vào bếp: “Con đói rồi!”')
    if kind == 'meal':
        return (f'Bữa trưa của {k}', f'Mười một giờ, {k} ngồi gõ thìa xuống bàn chờ cơm.')
    if kind == 'play':
        return (f'Giờ chơi với {k}', f'{MOODS[needs["mood"]][1]}.')
    if kind == 'safety':
        return ('Soát phòng trước khi bé chơi', f'{K} sắp ra phòng khách chơi. Ngồi xuống ngang tầm bé, nhìn quanh một lượt.')
    if kind == 'nap':
        return (f'Giờ ngủ trưa của {k}', f'{hhmm(f["nap"])} rồi, {k} dụi mắt, ngáp liên tục.')
    if kind == 'moment':
        mk = needs['mk']
        return (f'{K} {MOMENT_TITLE[mk]}', MOMENT_OPEN[mk].format(Kid=K))
    return (f'Bàn giao {k} cho {p}', f'Sáu giờ chiều, {p} bấm chuông: “Hôm nay bé sao em?”')


def _fresh_st(kind: str) -> dict:
    return {
        'arrive': lambda: dict(wash=False, greet=None, note=False, bag=False, ask=None, asks=0),
        'snack': lambda: dict(plate=[], prep=[], kidwash=False, seat=False),
        'meal': lambda: dict(plate=[], prep=[], kidwash=False, seat=False),
        'play': lambda: dict(act=None, beat=0, joy=0, answers=[], tidy=False),
        'safety': lambda: dict(fixed=[], wrong=[]),
        'nap': lambda: dict(potty=False, dark=False, lovey=None, song=False, pat=None, good=0, fuss=0),
        'moment': lambda: dict(calm=0, used=[], bad=[], order_err=0),
        'handover': lambda: dict(ticks=[]),
    }[kind]()


def make_task(day: int, slot: int, serial: int) -> dict:
    plan = plan_of(day)
    fid = family_of(day)
    f = fam(fid)
    kind, minute = plan[slot] if slot < len(plan) else ('play', CLOSE)
    needs = dict(fam=fid, time=minute, **_needs(kind, day, slot, f, plan))
    title, opening = _words(kind, f, needs)
    return kit.base_task(ID, day, slot, serial, f['npc'], title, opening, kind=kind, needs=needs, gen=GEN, stage='work',
                         st=_fresh_st(kind), story=None)


FIXED = ('needs',)


def on_task(s: dict, c: dict, t: dict) -> None:
    t['known'] = True
    if t['status'] == 'new':
        t['status'] = 'understood'


# ================================================================ the career's data
def _fresh_today(day: int, fid: str = 'bin') -> dict:
    return dict(day=day, fam=fid, note=0, food=[], nap=0, play='', tv=0, moment='', hazards=0, missed=0, oops='',
                pts=0, safe_slip=0, blocks=0, joy=0, handed=0)


def initial() -> dict:
    return dict(v=1, intro=False, today=_fresh_today(0), fams={},
                stats=dict(days=0, blocks=0, meals=0, naps=0, hazards=0, moments=0, care=0, tips=0),
                desk=kit.desk_initial(), learn=dict(task=None, codes=[], done=False))


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'learn'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, copy.deepcopy(v))
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    return d


def _today(c: dict, d: dict) -> dict:
    td = d['today']
    if td.get('day') != c['day']:
        d['today'] = td = _fresh_today(c['day'], family_of(c['day']))
    return td


def learning(d: dict) -> bool:
    return not d['learn']['done'] and d['stats']['days'] < APPRENTICE


# ================================================================ the actions
FREE = ('bm_intro',)
FINALS = ('bm_take', 'bm_serve', 'bm_play_done', 'bm_safe_done', 'bm_nap_done', 'bm_moment_done', 'bm_hand')
PHYSICAL = FINALS
NO_TICK = ('bm_intro', 'bm_desk', 'bm_wash', 'bm_greet', 'bm_note', 'bm_bag', 'bm_ask', 'bm_food', 'bm_prep', 'bm_kidwash',
           'bm_seat', 'bm_play', 'bm_beat', 'bm_tidy', 'bm_check', 'bm_nap', 'bm_lovey', 'bm_pat', 'bm_care', 'bm_log')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    _today(c, d)
    if name == 'bm_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Bố mẹ bé sắp tới, rửa tay sẵn đi nào.')
    desk = d['desk']
    if name == 'bm_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở nhà bé, quyết xong rồi làm tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở nghề trông trẻ.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    if learning(d):
        return
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc nghề trông trẻ.')
    kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    kit.need(t['stage'] == 'work', 'Việc này xong rồi.')
    before = [x for x in c['tasks'] if x.get('career') == ID and x['day'] == t['day'] and _slot(x) < _slot(t)
              and x['status'] not in ('completed', 'referred', 'cancelled')]
    kit.need(not before, f'Làm xong việc trước đã: {before[0]["title"]}.' if before else '')
    if t['kind'] != 'arrive':
        kit.need(_today(c, _data(c))['note'], 'Đọc giấy dặn của bố mẹ bé trước đã nhé.')
    return t


def _catch(d: dict, t: dict, codes) -> dict | None:
    """While learning, cô Tâm stops the first mistake of each kind before it is made (nothing recorded)."""
    if not learning(d):
        return None
    lr = d['learn']
    if lr['task'] != t['id']:
        lr['task'], lr['codes'] = t['id'], []
    for code in codes:
        if code in CATCH and code not in lr['codes']:
            lr['codes'].append(code)
            return dict(message=f'📞 Cô Tâm: “{CATCH[code]}”', correct=False, lesson=code)
    return None


def _slip_all(c: dict, d: dict, t: dict, rows: list) -> None:
    td = _today(c, d)
    for code, sev, text, note, safe in rows:
        if not any(r['code'] == code for r in cq.slips(t)):
            t['mistakes'] += 1
            td['pts'] = min(99, td['pts'] + sev)
            if safe:
                td['safe_slip'] = 1
        cq.slip(t, code, sev, text, note, safe)


def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str, tip: int = 0) -> str:
    """Close a block: the parent's reaction to what went wrong, the review, then the next block of the day."""
    who = _parent(t)
    react = cq.react(s, c, t, reward, who=who)
    if tip:
        t['tip_given'] = tip
    t['stage'] = 'done'
    td = _today(c, d)
    td['blocks'] = min(20, td['blocks'] + 1)
    d['stats']['blocks'] += 1
    kit.complete(s, c, t, max(0, int(react['pay'])), (narrative or t['title'])[:300])
    _ensure(s, c)
    return ' '.join(x for x in (narrative, react['message']) if x).strip()


# ---------------------------------------------------------------- arrive
def _wash(s, c, d, p):
    t = _task(c, p, ('arrive',))
    t['st']['wash'] = True
    kit.start_work(t)
    return dict(message='🧼 Rửa tay bằng xà phòng, đếm tới hai mươi, lau khô.')


def _note(s, c, d, p):
    t = _task(c, p, ('arrive',))
    t['st']['note'] = True
    _today(c, d)['note'] = 1
    kit.start_work(t)
    f = fam(t['needs']['fam'])
    al = f'dị ứng {ALLERGENS[f["allergy"]]}' if f['allergy'] else 'không dị ứng gì'
    return dict(message=f'📝 Giấy dặn: {kid(f, True)} {al}, ngủ trưa {hhmm(f["nap"])} với {_lower(LOVEYS[f["lovey"]][1])}.')


def _greet(s, c, d, p):
    t = _task(c, p, ('arrive',))
    g = kit.one_of(p.get('greet'), GREETS, 'Cách chào này không có.')
    kit.need(t['st']['greet'] is None, 'Chào bé rồi mà.')
    t['st']['greet'] = g
    kit.start_work(t)
    f = fam(t['needs']['fam'])
    ok = g == TEMPERS[f['temper']][2]
    k = kid(f, True)
    if ok:
        return dict(message=f'{GREETS[g][0]} {k} nhìn bạn một lúc, rồi cười, chìa tay ra.', correct=True)
    return dict(message=f'{GREETS[g][0]} {k} nép sau lưng {_lower(PEOPLE[f["npc"]][0])}, chưa chịu theo bạn.', correct=False)


def _bag(s, c, d, p):
    t = _task(c, p, ('arrive',))
    t['st']['bag'] = True
    kit.start_work(t)
    n = t['needs']
    have = [x for x in n['bag'] if x != n['missing']]
    return dict(message='🎒 Trong túi có: ' + ', '.join(_lower(_bag_name(t, x)) for x in have) + '.')


def _bag_name(t: dict, x: str) -> str:
    if x == 'lovey':
        return LOVEYS[fam(t['needs']['fam'])['lovey']][1]
    return BAG[x][1]


def _ask(s, c, d, p):
    t = _task(c, p, ('arrive',))
    kit.need(t['st']['bag'], 'Mở túi đồ ra xem trước đã.')
    x = kit.one_of(p.get('item'), BAG, 'Món này không có trong danh sách.')
    kit.need(x in t['needs']['bag'], 'Bé này không cần món đó.')
    kit.need(t['st']['ask'] != t['needs']['missing'], 'Hỏi rồi, bố mẹ bé đưa rồi mà.')
    t['st']['asks'] = min(9, t['st']['asks'] + 1)
    who = PEOPLE[fam(t['needs']['fam'])['npc']][0]
    if x == t['needs']['missing']:
        t['st']['ask'] = x
        return dict(message=f'🙋 “Túi còn thiếu {_lower(_bag_name(t, x))} ạ?” {who}: “À quên, đây em!”', correct=True)
    return dict(message=f'🙋 {who}: “{_bag_name(t, x)} có trong túi rồi mà em.”', correct=False)


def arrive_slips(t: dict) -> list:
    st, f = t['st'], fam(t['needs']['fam'])
    out = []
    if not st['note']:
        out.append(('note', 2, 'Em chưa đọc giấy dặn của chị à?', 'chưa đọc giấy dặn', False))
    if not st['wash']:
        out.append(('wash', 1, 'Em bế bé mà chưa rửa tay.', 'chưa rửa tay', False))
    if st['greet'] != TEMPERS[f['temper']][2]:
        out.append(('greet', 1, f'{kid(f, True)} nép sau lưng tôi, mãi mới chịu theo em.', 'chào chưa hợp tính bé', False))
    if st['ask'] != t['needs']['missing']:
        out.append(('bag', 1, f'Túi thiếu {_lower(_bag_name(t, t["needs"]["missing"]))} mà em không hỏi.', 'chưa hỏi đồ còn thiếu', False))
    return out


def _take(s, c, d, p):
    t = _task(c, p, ('arrive',))
    rows = arrive_slips(t)
    caught = _catch(d, t, [r[0] for r in rows])
    if caught:
        return caught
    _slip_all(c, d, t, rows)
    kit.start_work(t)
    f = fam(t['needs']['fam'])
    ok = not rows
    msg = _finish(s, c, d, t, 0, f'Nhận {kid(f)} từ tay {_lower(PEOPLE[f["npc"]][0])}.')
    head = f'👋 {kid(f, True)} vẫy tay chào {"bố" if f["npc"] in (2, 5) else "bà" if f["npc"] == 4 else "mẹ"}.'
    return dict(message=f'{head} {msg}', celebrate=ok)


# ---------------------------------------------------------------- snack and meal
def _food(s, c, d, p):
    t = _task(c, p, ('snack', 'meal'))
    k = kit.one_of(p.get('food'), t['needs']['menu'], 'Món này không có trên bàn bếp.')
    plate = t['st']['plate']
    kit.start_work(t)
    if k in plate:
        plate.remove(k)
        if k in t['st']['prep']:
            t['st']['prep'].remove(k)
        return dict(message=f'↩️ Cất {_lower(FOODS[k]["name"])} lại.')
    kit.need(len(plate) < len(t['needs']['groups']) + 1, 'Đĩa của bé đầy rồi, bớt món khác ra trước.')
    plate.append(k)
    x = FOODS[k]
    return dict(message=f'{x["emoji"]} Lấy {_lower(x["name"])} ra đĩa.')


def _prep(s, c, d, p):
    t = _task(c, p, ('snack', 'meal'))
    k = kit.one_of(p.get('food'), t['st']['plate'], 'Món này chưa có trên đĩa.')
    x = FOODS[k]
    kit.need(x['prep'], f'{x["name"]} ăn được luôn, không cần sơ chế.')
    kit.need(k not in t['st']['prep'], 'Sơ chế xong rồi.')
    t['st']['prep'].append(k)
    word = {'cut': f'✂️ Cắt {_lower(x["name"])} thành miếng nhỏ vừa miệng bé.', 'cool': f'🌬️ Múc {_lower(x["name"])} ra bát, khuấy cho nguội bớt.',
            'bone': f'🦴 Gỡ hết xương cá, dầm nhỏ.'}[x['prep']]
    return dict(message=word)


def _kidwash(s, c, d, p):
    t = _task(c, p, ('snack', 'meal'))
    t['st']['kidwash'] = True
    kit.start_work(t)
    return dict(message='🧼 Bế bé rửa tay, bé nghịch bọt xà phòng cười khúc khích.')


def _seat(s, c, d, p):
    t = _task(c, p, ('snack', 'meal'))
    t['st']['seat'] = True
    kit.start_work(t)
    return dict(message='🪑 Cho bé ngồi ghế ăn, đeo yếm, kéo ghế sát bàn.')


def _needs_prep(f: dict, k: str) -> bool:
    p = FOODS[k]['prep']
    return p in ('cool', 'bone') or (p == 'cut' and young(f))


def food_slips(c: dict, t: dict) -> list:
    st, n, f = t['st'], t['needs'], fam(t['needs']['fam'])
    plate = st['plate']
    out = []
    bad = next((k for k in plate if f['allergy'] in FOODS[k]['al']), None)
    if bad:
        al = ALLERGENS[f['allergy']]
        out.append(('allergy', 3, f'{kid(f, True)} dị ứng {al} mà em, {_lower(FOODS[bad]["name"])} có {al}!', f'món có {al}', True))
    hard = next((k for k in plate if FOODS[k]['hard'] and young(f)), None)
    if hard:
        out.append(('choke', 2, f'{FOODS[hard]["name"]} cứng, bé nhỏ vậy dễ hóc lắm.', 'đồ dễ hóc cho bé nhỏ', True))
    raw = [k for k in plate if _needs_prep(f, k) and k not in st['prep']]
    if raw:
        x = FOODS[raw[0]]
        words = {'cut': f'{x["name"]} để nguyên miếng to, bé dễ hóc.', 'cool': f'{x["name"]} còn nóng hổi, bé phỏng miệng mất.',
                 'bone': 'Cá còn xương mà em.'}[x['prep']]
        out.append(('prep', 2, words, 'chưa sơ chế món ăn', True))
    have = {FOODS[k]['group'] for k in plate}
    if any(g not in have for g in n['groups']):
        out.append(('meal', 1, f'{kid(f, True)} ăn chưa đủ bữa, thiếu {_lower(GROUPS[next(g for g in n["groups"] if g not in have)])}.', 'thiếu món', False))
    if mod_of(t['day'])['id'] == 'sniffle' and any(FOODS[k]['group'] == 'drink' and k != 'nuoc' for k in plate):
        out.append(('drink', 1, 'Bé đang sổ mũi, chị dặn uống nước ấm thôi mà.', 'đồ uống chưa hợp lúc bé sổ mũi', False))
    if not st['kidwash']:
        out.append(('kidwash', 1, 'Chưa rửa tay cho bé trước khi ăn.', 'chưa rửa tay cho bé', False))
    if not st['seat']:
        out.append(('seat', 1, 'Cho bé vừa chạy vừa ăn dễ sặc lắm.', 'chưa cho bé ngồi ghế', False))
    return out


def _serve(s, c, d, p):
    t = _task(c, p, ('snack', 'meal'))
    st = t['st']
    kit.need(st['plate'], 'Đĩa của bé còn trống, chọn món đã.')
    rows = food_slips(c, t)
    caught = _catch(d, t, [r[0] for r in rows])
    if caught:
        return caught
    _slip_all(c, d, t, rows)
    kit.start_work(t)
    f = fam(t['needs']['fam'])
    td = _today(c, d)
    td['food'] = (td['food'] + [k for k in st['plate'] if k not in td['food']])[:10]
    bad = next((k for k in st['plate'] if f['allergy'] in FOODS[k]['al']), None)
    if bad:
        td['oops'] = f['allergy']
    d['stats']['meals'] += 1
    names = ', '.join(_lower(FOODS[k]['name']) for k in st['plate'])
    if bad:
        head = f'🍽️ Bạn kịp nhìn ra món có {ALLERGENS[f["allergy"]]}, cất đi trước khi bé ăn. Bé ăn phần còn lại.'
    elif not rows:
        head = f'🍽️ {kid(f, True)} ăn ngon lành, hết sạch đĩa.' + (' Món bé thích nhất!' if f['likes'] in st['plate'] else '')
    else:
        head = f'🍽️ {kid(f, True)} ăn được một ít.'
    msg = _finish(s, c, d, t, 0, f'Cho {kid(f)} ăn: {names}.')
    return dict(message=f'{head} {msg}'.strip(), celebrate=not rows)


# ---------------------------------------------------------------- play
def play_slips(t: dict) -> list:
    st, n, f = t['st'], t['needs'], fam(t['needs']['fam'])
    out = []
    a = ACTS.get(st['act']) if st['act'] else None
    if a and a['small'] and young(f):
        out.append(('small', 2, f'{a["name"]} mảnh nhỏ, bé cho vào miệng là hóc.', 'đồ chơi mảnh nhỏ', True))
    if a and a['screen'] and not n['screen_ok']:
        out.append(('screen', 1, 'Giấy dặn ghi giờ này không xem màn hình mà em.', 'cho bé xem màn hình', False))
    if a and n['mood'] not in a['fits']:
        words = {'tired': 'Bé đang buồn ngủ mà em rủ chơi trò đó.', 'bouncy': 'Bé đang muốn chạy nhảy mà bắt ngồi yên.',
                 'grumpy': 'Bé đang dỗi, trò đó bé chẳng thiết.', 'curious': 'Bé đang tò mò muốn học mà chơi trò đó.'}[n['mood']]
        out.append(('mood', 1, words, 'trò chưa hợp tâm trạng bé', False))
    if 0 in st['answers']:
        out.append(('harsh', 1, 'Nghe em nói với bé hơi cộc.', 'nói với bé hơi cộc', False))
    return out


def _play(s, c, d, p):
    t = _task(c, p, ('play',))
    st, n = t['st'], t['needs']
    kit.need(st['act'] is None, 'Đang chơi rồi.')
    a = kit.one_of(p.get('act'), n['acts'], 'Trò này không có ở đây.')
    x = ACTS[a]
    f = fam(n['fam'])
    pre = [code for code in ('small', 'screen') if (code == 'small' and x['small'] and young(f)) or (code == 'screen' and x['screen'] and not n['screen_ok'])]
    caught = _catch(d, t, pre)
    if caught:
        return caught
    st['act'] = a
    kit.start_work(t)
    if x['screen']:
        st['joy'] = JOY_TV
        st['beat'] = PLAY_BEATS
        if n['screen_ok']:
            return dict(message=f'📺 Bật một tập hoạt hình {f["screen"]} phút như giấy dặn, ngồi xem cùng bé.')
        return dict(message='📺 Bật hoạt hình. Bé dán mắt vào màn hình.', correct=False)
    st['joy'] = JOY_FIT if n['mood'] in x['fits'] else JOY_MISFIT
    fits = n['mood'] in x['fits']
    return dict(message=f'{x["emoji"]} {x["name"]}! ' + ('Bé reo lên, chạy lại ngay.' if fits else 'Bé ngó qua, chưa hào hứng lắm.'), correct=fits or None)


def _beat(s, c, d, p):
    t = _task(c, p, ('play',))
    st, n = t['st'], t['needs']
    kit.need(st['act'] and st['beat'] < PLAY_BEATS, 'Chọn trò chơi trước đã.')
    b = n['beats'][st['beat']]
    opts = {o[0]: o for o in BEATS[b][1]}
    o = opts.get(p.get('opt'))
    kit.need(o, 'Cách này không có.')
    if o[2] == 0:
        caught = _catch(d, t, ['harsh'])
        if caught:
            return caught
    st['answers'].append(o[2])
    st['beat'] += 1
    st['joy'] = max(0, min(100, st['joy'] + JOY_STEP[o[2]]))
    word = {2: '😄 Bé cười tít mắt.', 1: '🙂 Bé gật gù.', 0: '😕 Bé xịu mặt.'}[o[2]]
    return dict(message=f'{word} Vui: {st["joy"]}%.', correct=o[2] == 2 or None)


def _tidy(s, c, d, p):
    t = _task(c, p, ('play',))
    st = t['st']
    kit.need(st['act'] and st['beat'] >= PLAY_BEATS, 'Chơi xong rồi hẵng dọn.')
    kit.need(not st['tidy'], 'Dọn xong rồi.')
    st['tidy'] = True
    st['joy'] = min(100, st['joy'] + 5)
    return dict(message='🧺 Hai cô cháu thi nhau nhặt đồ chơi bỏ vào rổ. Gọn gàng!')


def _play_done(s, c, d, p):
    t = _task(c, p, ('play',))
    st = t['st']
    kit.need(st['act'], 'Chọn trò chơi cho bé trước đã.')
    kit.need(st['beat'] >= PLAY_BEATS, 'Chơi với bé thêm chút nữa đã.')
    rows = play_slips(t)
    caught = _catch(d, t, [r[0] for r in rows])
    if caught:
        return caught
    _slip_all(c, d, t, rows)
    f = fam(t['needs']['fam'])
    td = _today(c, d)
    td['play'] = st['act']
    td['joy'] = st['joy']
    if ACTS[st['act']]['screen']:
        td['tv'] = 1
    joy = st['joy']
    head = '🎈 Bé chơi vui hết cỡ!' if joy >= 80 else '🙂 Bé chơi vui.' if joy >= 50 else '😐 Bé chơi chưa vui lắm.'
    msg = _finish(s, c, d, t, 0, f'Chơi {_lower(ACTS[st["act"]]["name"])} với {kid(f)}.')
    return dict(message=f'{head} {msg}'.strip(), celebrate=joy >= 80 and not rows)


# ---------------------------------------------------------------- the room sweep
def _check(s, c, d, p):
    t = _task(c, p, ('safety',))
    st = t['st']
    k = kit.one_of(p.get('item'), t['needs']['items'], 'Món này không có trong phòng.')
    kit.need(k not in st['fixed'] and k not in st['wrong'], 'Xem món này rồi.')
    kit.start_work(t)
    x = HAZ[k]
    if x[2]:
        st['fixed'].append(k)
        return dict(message=f'{x[0]} {x[3]}. An toàn rồi!', correct=True)
    st['wrong'].append(k)
    return dict(message=f'{x[0]} {x[1]}: món này an toàn mà.', correct=False)


def hazards(t: dict) -> list:
    return [k for k in t['needs']['items'] if HAZ[k][2]]


def safety_slips(t: dict) -> list:
    missed = [k for k in hazards(t) if k not in t['st']['fixed']]
    if not missed:
        return []
    return [('hazard', 2, f'Nhà còn {_lower(HAZ[missed[0]][1])} mà em không thấy.', 'còn chỗ nguy hiểm', False)]


def _safe_done(s, c, d, p):
    t = _task(c, p, ('safety',))
    rows = safety_slips(t)
    caught = _catch(d, t, [r[0] for r in rows])
    if caught:
        return caught
    _slip_all(c, d, t, rows)
    td = _today(c, d)
    fixed = len(t['st']['fixed'])
    missed = len(hazards(t)) - fixed
    td['hazards'] = min(20, td['hazards'] + fixed)
    td['missed'] = min(20, td['missed'] + missed)
    d['stats']['hazards'] += fixed
    f = fam(t['needs']['fam'])
    head = f'🛡️ Phòng an toàn rồi, {kid(f)} ra chơi thôi.' if not missed else f'🛡️ Bé ra chơi. (Còn {missed} chỗ chưa xử lý.)'
    msg = _finish(s, c, d, t, 0, f'Soát phòng: xử lý {fixed} chỗ nguy hiểm.')
    return dict(message=f'{head} {msg}'.strip(), celebrate=not missed)


# ---------------------------------------------------------------- nap
def pat_window(day: int) -> tuple:
    return PAT_WIN_EASY if kit.tier(day) == 0 else PAT_WIN


def _nap(s, c, d, p):
    t = _task(c, p, ('nap',))
    step = kit.one_of(p.get('step'), NAP_STEPS, 'Bước này không có.')
    st = t['st']
    kit.need(not st[step], 'Làm bước này rồi.')
    st[step] = True
    kit.start_work(t)
    _maybe_pat(t)
    return dict(message={'potty': '🚽 Cho bé đi vệ sinh, rửa tay, thay bộ đồ ngủ mềm.', 'dark': '🌙 Kéo rèm, tắt đèn, bật quạt nhẹ.',
                         'song': '🎵 Bạn hát khẽ “À ơi…”, bé chớp mắt chậm dần.'}[step])


def _lovey(s, c, d, p):
    t = _task(c, p, ('nap',))
    k = kit.one_of(p.get('item'), t['needs']['loveys'], 'Món này không có.')
    st = t['st']
    f = fam(t['needs']['fam'])
    kit.start_work(t)
    if k == f['lovey']:
        st['lovey'] = k
        _maybe_pat(t)
        return dict(message=f'{LOVEYS[k][0]} Bé ôm chặt {_lower(LOVEYS[k][1])}, rúc vào gối.', correct=True)
    st['fuss'] = min(99, st['fuss'] + 1)
    return dict(message=f'{LOVEYS[k][0]} Bé lắc đầu, đẩy ra: “Không phải cái này!”', correct=False)


def _maybe_pat(t: dict) -> None:
    st = t['st']
    if st['pat'] is None and st['lovey'] and st['dark']:
        st['pat'] = round(kit.now(), 3)


def pat_phase(t: dict, at: float) -> float:
    return ((at - t['st']['pat']) % CYCLE) / CYCLE


def _pat(s, c, d, p):
    t = _task(c, p, ('nap',))
    st = t['st']
    kit.need(st['lovey'], 'Bé chưa có đồ ôm, chưa chịu nằm yên.')
    kit.need(st['dark'], 'Phòng còn sáng, kéo rèm tắt đèn đã.')
    kit.need(st['good'] < SLEEP_PATS, 'Bé ngủ say rồi.')
    if st['pat'] is None:
        st['pat'] = round(kit.now(), 3)
    ph = pat_phase(t, kit.tap_now(p))
    lo, hi = pat_window(t['day'])
    if lo <= ph <= hi:
        st['good'] += 1
        left = SLEEP_PATS - st['good']
        return dict(message='🤲 Vỗ nhẹ đúng nhịp thở ra. ' + (f'Mắt bé díp lại… (còn {left})' if left else '😴 Bé ngủ say rồi.'), correct=True)
    st['fuss'] = min(99, st['fuss'] + 1)
    return dict(message='🤲 Vỗ lệch nhịp, bé cựa mình. Chờ bé thở ra chậm rồi hẵng vỗ.', correct=False)


def nap_slips(t: dict) -> list:
    st = t['st']
    miss = [k for k in ('potty', 'dark', 'song') if not st[k]]
    if not miss:
        return []
    words = {'potty': 'Bé chưa đi vệ sinh đã ngủ, dậy ướt cả giường.', 'dark': 'Phòng sáng trưng, bé ngủ chập chờn.',
             'song': 'Bé ngủ mà chẳng ai ru, nằm trằn trọc mãi.'}
    return [('routine', 1, words[miss[0]], 'ru ngủ thiếu bước', False)]


def _nap_done(s, c, d, p):
    t = _task(c, p, ('nap',))
    st = t['st']
    kit.need(st['good'] >= SLEEP_PATS, 'Bé chưa ngủ: vỗ nhẹ theo nhịp thở thêm chút nữa.')
    rows = nap_slips(t)
    caught = _catch(d, t, [r[0] for r in rows])
    if caught:
        return caught
    _slip_all(c, d, t, rows)
    td = _today(c, d)
    td['nap'] = 1
    d['stats']['naps'] += 1
    f = fam(t['needs']['fam'])
    msg = _finish(s, c, d, t, 0, f'Ru {kid(f)} ngủ trưa lúc {hhmm(f["nap"])}.')
    return dict(message=f'😴 {kid(f, True)} ngủ ngon lành, thở đều. {msg}'.strip(), celebrate=not rows and st['fuss'] <= 1)


# ---------------------------------------------------------------- small moments
def _care(s, c, d, p):
    t = _task(c, p, ('moment',))
    st, n = t['st'], t['needs']
    m = kit.one_of(p.get('move'), n['moves'], 'Cách này không có.')
    kit.need(m not in st['used'], 'Làm rồi mà.')
    kit.need(st['calm'] < 100, 'Bé ổn rồi.')
    emoji, label, delta, code = MOVES[n['mk']][m]
    kit.start_work(t)
    if code:
        caught = _catch(d, t, [code])
        if caught:
            return caught
        st['used'].append(m)
        if code not in st['bad']:
            st['bad'].append(code)
        st['calm'] = max(0, st['calm'] + delta)
        return dict(message=f'{emoji} {label}… Bé càng khóc to hơn.', correct=False)
    if n['mk'] == 'scrape' and m in SCRAPE_ORDER:
        due = next(x for x in SCRAPE_ORDER if x not in st['used'])
        if m != due:
            caught = _catch(d, t, ['aid_order'])
            if caught:
                return caught
            st['order_err'] = min(9, st['order_err'] + 1)
            return dict(message=f'✋ Khoan, {_lower(MOVES["scrape"][due][1])} trước đã.', correct=False)
    st['used'].append(m)
    st['calm'] = min(100, st['calm'] + delta)
    tail = ' Bé nín hẳn, dụi đầu vào vai bạn.' if st['calm'] >= 100 else ''
    return dict(message=f'{emoji} {label}.{tail} Bình tĩnh: {st["calm"]}%.', correct=True)


def moment_slips(t: dict) -> list:
    st = t['st']
    words = {'harsh': ('Nghe nói em quát bé à?', 2, 'lớn tiếng với bé'), 'scare': ('Em dọa bé ông kẹ, tối bé không dám ngủ một mình.', 1, 'dọa bé'),
             'give_in': ('Bé khóc là được chiều, mai bé lại khóc tiếp.', 1, 'chiều theo bé'),
             'folk': ('Kem đánh răng không bôi vết thương được đâu em.', 1, 'sơ cứu sai cách'),
             'aid': ('Vết xước chưa rửa sạch đã cho chơi tiếp.', 1, 'chưa rửa vết xước')}
    out = [(code, words[code][1], words[code][0], words[code][2], False) for code in st['bad'] if code in words]
    if st['order_err']:
        out.append(('aid_order', 1, 'Sơ cứu lộn thứ tự rồi em.', 'sơ cứu lộn thứ tự', False))
    return out


def _moment_done(s, c, d, p):
    t = _task(c, p, ('moment',))
    st, n = t['st'], t['needs']
    kit.need(st['calm'] >= 100, 'Bé chưa ổn hẳn, dỗ bé thêm chút nữa.')
    rows = moment_slips(t)
    _slip_all(c, d, t, rows)
    td = _today(c, d)
    td['moment'] = n['mk']
    d['stats']['moments'] += 1
    f = fam(n['fam'])
    msg = _finish(s, c, d, t, 0, f'Dỗ {kid(f)} lúc bé {MOMENT_TITLE[n["mk"]]}.')
    return dict(message=f'💛 {kid(f, True)} ổn rồi, lại cười. {msg}'.strip(), celebrate=not rows)


# ---------------------------------------------------------------- the handover
def log_lines(c: dict, d: dict | None = None) -> list:
    """Today's day log as the parent will read it: (id, text, true?, must?)."""
    d = d or _data(c)
    td = _today(c, d)
    f = fam(td['fam'])
    k = kid(f, True)
    rows = []
    if td['food']:
        rows.append(('food', f'{k} ăn {", ".join(_lower(FOODS[x]["name"]) for x in td["food"][:5] if x in FOODS)}.', True, True))
    if td['nap']:
        rows.append(('nap', f'{k} ngủ trưa lúc {hhmm(f["nap"])}, ôm {_lower(LOVEYS[f["lovey"]][1])}.', True, True))
    if td['play'] in ACTS:
        rows.append(('play', f'Hai cô cháu chơi {_lower(ACTS[td["play"]]["name"])}.', True, False))
    if td['hazards']:
        rows.append(('safe', f'Đã cất, che {td["hazards"]} chỗ dễ nguy hiểm trong nhà.', True, False))
    if td['moment'] in MOMENT_TITLE:
        line = {'cry': f'{k} khóc nhớ nhà lúc ngủ dậy, ôm dỗ một lúc thì nín.',
                'scrape': f'{k} ngã trầy đầu gối, đã rửa sạch, dán băng.',
                'tantrum': f'{k} ăn vạ đòi kẹo, đã dỗ bằng cách cho bé chọn trò chơi.'}[td['moment']]
        rows.append(('moment', line, True, True))
    if td['oops'] in ALLERGENS:
        rows.append(('oops', f'Lỡ dọn món có {ALLERGENS[td["oops"]]}, đã lấy ra trước khi bé ăn.', True, True))
    rows.append(('fine', 'Cả ngày bé ngoan, không có chuyện gì.', not td['moment'] and not td['oops'], False))
    if not td['tv']:
        rows.append(('tv', 'Bé xem hoạt hình gần cả buổi chiều.', False, False))
    order = sorted(rows, key=lambda r: _hash('bm-log', c['day'], r[0]))
    return order


def handover_slips(c: dict, t: dict) -> list:
    ticks = set(t['st']['ticks'])
    out = []
    for lid, text, true, must in log_lines(c):
        if must and lid not in ticks:
            if lid in ('moment', 'oops'):
                out.append(('hide', 2, 'Sao chuyện đó em không kể với chị?', 'giấu chuyện trong ngày', False))
            else:
                out.append(('log', 1, 'Em kể thiếu chuyện ăn ngủ của bé.', 'nhật ký thiếu', False))
        if not true and lid in ticks:
            if lid == 'fine':
                out.append(('hide', 2, 'Bé kể có chuyện mà em ghi “không có gì”.', 'giấu chuyện trong ngày', False))
            else:
                out.append(('false_log', 1, 'Nhật ký ghi chuyện không có thật.', 'ghi sai nhật ký', False))
    return out


def _log(s, c, d, p):
    t = _task(c, p, ('handover',))
    ids = [r[0] for r in log_lines(c, d)]
    lid = kit.one_of(p.get('line'), ids, 'Dòng này không có trong nhật ký.')
    ticks = t['st']['ticks']
    kit.start_work(t)
    if lid in ticks:
        ticks.remove(lid)
        return dict(message='↩️ Bỏ dòng này khỏi nhật ký.')
    ticks.append(lid)
    return dict(message='✍️ Ghi vào nhật ký.')


def pay_of(c: dict, d: dict, fid: str) -> dict:
    """The day's pay as it stands now: rate, loyalty, care bonus."""
    td = _today(c, d)
    f = fam(fid)
    trust = (d['fams'].get(fid) or {}).get('trust', 0)
    care = max(0, 100 - 10 * td['pts'])
    bonus = 0 if td['safe_slip'] else next((b for lo, b in CARE_BONUS if care >= lo), 0)
    return dict(rate=f['rate'], loyal=LOYAL * trust, bonus=bonus, care=care, total=f['rate'] + LOYAL * trust + bonus)


def _hand(s, c, d, p):
    t = _task(c, p, ('handover',))
    rows = handover_slips(c, t)
    caught = _catch(d, t, [r[0] for r in rows])
    if caught:
        return caught
    _slip_all(c, d, t, rows)
    fid = t['needs']['fam']
    f = fam(fid)
    td = _today(c, d)
    pay = pay_of(c, d, fid)
    care = pay['care']
    fr = d['fams'].setdefault(fid, dict(visits=0, trust=0))
    tip = 0
    if care >= 80 and not rows:
        tip = kit.rng(ID, 'tip', t['id']).randint(*TIP) + 2 * fr['trust']
        kit.money(s, c, tip, f'Bồi dưỡng của {_lower(PEOPLE[f["npc"]][0])}', t['id'], 'tip')
        d['stats']['tips'] += tip
    fr['visits'] = min(999, fr['visits'] + 1)
    up = 0
    if care >= 80 and not cq.safety(t) and not td['safe_slip']:
        up = 1 if fr['trust'] < TRUST_MAX else 0
        fr['trust'] = min(TRUST_MAX, fr['trust'] + 1)
    elif care < 50:
        fr['trust'] = max(0, fr['trust'] - 1)
    story = FAM_STORY[fid][min(fr['visits'], len(FAM_STORY[fid])) - 1] if care >= 70 else ''
    t['story'] = story or None
    td['handed'] = 1
    d['stats']['days'] += 1
    d['stats']['care'] = min(10 ** 7, d['stats']['care'] + care)
    msg = _finish(s, c, d, t, pay['total'], f'Trông {kid(f)} trọn ngày, bàn giao cho {_lower(PEOPLE[f["npc"]][0])}.', tip)
    extra = [x for x in (f'{pay["loyal"]} xu khách quen' if pay['loyal'] else '', f'{pay["bonus"]} xu chăm kỹ' if pay['bonus'] else '') if x]
    parts = [f'👋 {PEOPLE[f["npc"]][0]} nhận bé, đọc nhật ký. Tiền công {pay["total"]} xu' + (f' (có {", ".join(extra)})' if extra else '') + '.']
    if tip:
        parts.append(f'💌 Gửi thêm {tip} xu bồi dưỡng.')
    if up:
        parts.append('💛 Gia đình hẹn gửi bé lần sau.')
    parts.append(msg)
    if story:
        parts.append(f'💬 {story}')
    grad = _graduate(d)
    return dict(message=' '.join(x for x in parts if x) + grad, celebrate=care >= 80 and not rows)


def _graduate(d: dict) -> str:
    if d['learn']['done'] or d['stats']['days'] < APPRENTICE:
        return ''
    d['learn'].update(done=True, task=None, codes=[])
    return ' 🎓 Học nghề xong! Cô Tâm: “Giờ con tự nhận bé được rồi. Có gì cứ gọi cô.”'


ACTIONS = {
    'bm_wash': _wash, 'bm_note': _note, 'bm_greet': _greet, 'bm_bag': _bag, 'bm_ask': _ask, 'bm_take': _take,
    'bm_food': _food, 'bm_prep': _prep, 'bm_kidwash': _kidwash, 'bm_seat': _seat, 'bm_serve': _serve,
    'bm_play': _play, 'bm_beat': _beat, 'bm_tidy': _tidy, 'bm_play_done': _play_done,
    'bm_check': _check, 'bm_safe_done': _safe_done,
    'bm_nap': _nap, 'bm_lovey': _lovey, 'bm_pat': _pat, 'bm_nap_done': _nap_done,
    'bm_care': _care, 'bm_moment_done': _moment_done,
    'bm_log': _log, 'bm_hand': _hand,
}


# ================================================================ the schedule
def _open_today(c: dict) -> list:
    return [t for t in c['tasks'] if t.get('career') == ID and t['day'] == c['day'] and t['status'] not in ('completed', 'referred', 'cancelled')]


def _ensure(s: dict, c: dict) -> None:
    """Keep the next block of the day on the list (the engine's closing time never blocks the handover)."""
    if not c.get('open'):
        return
    if not _open_today(c):
        plan = plan_of(c['day'])
        slots = [_slot(t) for t in c['tasks'] if t.get('career') == ID and t['day'] == c['day']]
        nxt = max(slots, default=-1) + 1
        if nxt < len(plan):
            t = make_task(c['day'], nxt, c['turn'])
            c['tasks'].append(t)
            on_task(s, c, t)
    if not c.get('active_task') or not any(t['id'] == c['active_task'] for t in _open_today(c)):
        kit.eng().next_active(c)


def clock_minutes(c: dict) -> int | None:
    """The time of the block at hand (the schedule is the clock); the handover is at closing time."""
    if not c.get('open'):
        return None
    plan = plan_of(c['day'])
    today = [t for t in c['tasks'] if t.get('career') == ID and t['day'] == c['day']]
    slots = {_slot(t) for t in today}
    if len(plan) - 1 in slots:
        return CLOSE
    open_ = [t for t in today if t['status'] not in ('completed', 'referred', 'cancelled')]
    if open_:
        return min(int(t['needs'].get('time', OPEN)) for t in open_)
    nxt = max(slots, default=-1) + 1
    return plan[nxt][1] if nxt < len(plan) else CLOSE


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['today'] = _fresh_today(day, family_of(day))
    for t in c['tasks']:
        if t.get('career') == ID and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    _ensure(s, c)
    first = next((t for t in sorted(_open_today(c), key=_slot)), None)
    if first:
        c['active_task'] = first['id']
        first['deferred'] = False
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    td = _today(c, d)
    f = fam(td['fam'])
    lines = []
    half = 0
    if not td['handed'] and td['blocks'] > 0:
        half = f['rate'] // 2
        kit.money(s, c, half, f'Nửa ngày công: {_lower(PEOPLE[f["npc"]][0])} tự đón {kid(f)}')
        lines.append(f'⏰ {PEOPLE[f["npc"]][0]} tự đón {kid(f)} khi bạn chưa kịp bàn giao: gửi nửa ngày công, {half} xu.')
    care = max(0, 100 - 10 * td['pts'])
    if td['blocks']:
        lines.append(f'👶 Trông {kid(f)} ({f["age"]}): {td["blocks"]} việc trong ngày, chăm kỹ {care}%.')
    if td['hazards']:
        lines.append(f'🛡️ Xử lý {td["hazards"]} chỗ dễ nguy hiểm trong nhà.')
    if desk_note:
        lines.append(desk_note)
    nf = fam(family_of(c['day'] + 1))
    tm = mod_of(c['day'] + 1)
    trust = (d['fams'].get(family_of(c['day'] + 1)) or {}).get('trust', 0)
    return dict(tomorrow=dict(emoji=tm['emoji'], label=tm['label'], hint=tm['hint']), lines=lines,
                note=f'Mai trông {kid(nf)} ({nf["age"]}) nhà {_lower(PEOPLE[nf["npc"]][0])}' + (' · khách quen' if trust else '') + '.',
                kid=f['kid'], care=care, blocks=td['blocks'], handed=bool(td['handed']), half=half,
                next=dict(kid=nf['kid'], age=nf['age'], parent=PEOPLE[nf['npc']][0], trust=trust))


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    codes = {x['code'] for x in cq.slips(t)}
    k = t['kind']
    if k == 'arrive':
        ready = 5 - len(codes & {'note', 'wash', 'bag'})
        warm = 3 if 'greet' in codes else 5
        return dict(criteria=[dict(key='ready', label='Nhận bé chu đáo', score=max(2, ready), note='đọc giấy dặn, kiểm túi' if ready == 5 else 'còn sót khâu nhận bé'),
                              dict(key='warm', label='Bé chịu theo', score=warm, note='chào hợp tính bé' if warm == 5 else 'bé còn ngại')])
    if k in ('snack', 'meal'):
        safe = 1 if 'allergy' in codes else 2 if codes & {'choke', 'prep'} else 5
        meal = 5 - min(3, len(codes & {'meal', 'seat', 'kidwash', 'drink'}))
        return dict(criteria=[dict(key='safe', label='Món ăn an toàn', score=safe, note='đúng giấy dặn, hợp tuổi' if safe == 5 else 'món chưa an toàn cho bé'),
                              dict(key='meal', label='Bữa ăn đàng hoàng', score=meal, note='đủ món, ngồi ăn tử tế' if meal == 5 else 'bữa ăn còn thiếu sót')])
    if k == 'play':
        joy = t['st']['joy']
        fun = 5 if joy >= 80 else 4 if joy >= 60 else 3 if joy >= 40 else 2
        safe = 2 if 'small' in codes else 3 if 'screen' in codes else 5
        return dict(criteria=[dict(key='fun', label='Bé chơi vui', score=fun, note=f'vui {joy}%'),
                              dict(key='safe', label='Trò chơi hợp tuổi', score=safe, note='đúng tuổi, đúng giấy dặn' if safe == 5 else 'trò chưa hợp')])
    if k == 'safety':
        safe = 3 if 'hazard' in codes else 5
        return dict(criteria=[dict(key='safe', label='Nhà an toàn', score=safe, note='soát kỹ từng góc' if safe == 5 else 'còn sót chỗ nguy hiểm')])
    if k == 'nap':
        fuss = t['st']['fuss']
        sleep = 5 if fuss <= 1 else 4 if fuss <= 3 else 3
        routine = 4 if 'routine' in codes else 5
        return dict(criteria=[dict(key='sleep', label='Bé ngủ ngon', score=sleep, note='ngủ nhanh, ngủ sâu' if sleep == 5 else 'bé ngủ hơi khó'),
                              dict(key='routine', label='Đủ bước ru ngủ', score=routine, note='đủ bước' if routine == 5 else 'thiếu bước')])
    if k == 'moment':
        gentle = 2 if codes & {'harsh', 'scare'} else 4 if codes else 5
        return dict(criteria=[dict(key='gentle', label='Dỗ bé nhẹ nhàng', score=gentle, note='bình tĩnh, ân cần' if gentle == 5 else 'chưa thật nhẹ nhàng')])
    honest = 2 if 'hide' in codes else 4 if codes else 5
    return dict(criteria=[dict(key='honest', label='Bàn giao trung thực', score=honest, note='kể rõ, kể thật' if honest == 5 else 'nhật ký chưa đúng'),
                          dict(key='care', label='Cả ngày chăm bé', score=5, note='bé về nhà vui vẻ')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    return hint(c, t)


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if t['kind'] == 'nap':
        lo, hi = pat_window(t['day'])
        v['breath'] = dict(cycle=CYCLE, lo=lo, hi=hi, need=SLEEP_PATS)
    if t['kind'] == 'play':
        v['joy_fit'] = JOY_FIT
    return v


def _fam_public(fid: str) -> dict:
    f = fam(fid)
    return dict(id=fid, kid=f['kid'], age=f['age'], band=f['band'], young=young(f), temper=f['temper'], allergy=f['allergy'],
                nap=hhmm(f['nap']), lovey=f['lovey'], screen=f['screen'], parent=PEOPLE[f['npc']][0], home=f['home'])


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    for k, v in base['today'].items():
        d['today'].setdefault(k, v)
    day = c['day']
    td = d['today'] if d['today'].get('day') == day else _fresh_today(day, family_of(day))
    mod = mod_of(day)
    on = not d['learn']['done'] and d['stats']['days'] < APPRENTICE
    n = min(d['stats']['days'], APPRENTICE - 1)
    lines = []
    if c.get('open') and any(t.get('career') == ID and t['day'] == day and t['kind'] == 'handover' and t['status'] not in ('completed', 'cancelled')
                             for t in c['tasks']):
        lines = [dict(id=i, text=x) for i, x, _, _ in log_lines(c, dict(raw, today=td))]
    fid = td['fam'] if td['fam'] in FAMILIES else family_of(day)
    pay = None
    if c.get('open'):
        try:
            pay = pay_of(dict(c, day=day), dict(raw, today=td, fams=raw.get('fams', {})), fid)
        except Exception:  # noqa: BLE001  a view never blocks play
            pay = None
    return dict(intro=d['intro'], today=td, fam=_fam_public(fid), plan=[dict(kind=k, time=hhmm(m)) for k, m in plan_of(day)],
                fams={k: dict(v) for k, v in d['fams'].items()}, stats=d['stats'], log=lines, pay=pay,
                mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                desk=kit.desk_public(d['desk'], DESK, ID),
                learn=dict(on=on, n=d['stats']['days'], of=APPRENTICE, title=LESSONS[n][0] if on else None, text=LESSONS[n][1] if on else None))


def content() -> dict:
    return dict(foods=FOODS, groups=GROUPS, prep=PREP, meals=MEALS, acts=ACTS, moods=MOODS, beats={k: dict(line=v[0], opts=[list(o) for o in v[1]]) for k, v in BEATS.items()},
                haz={k: dict(emoji=v[0], name=v[1], fix=v[3]) for k, v in HAZ.items()}, homes={k: v['name'] for k, v in HOMES.items()},
                loveys={k: list(v) for k, v in LOVEYS.items()}, bag={k: list(v) for k, v in BAG.items()}, greets={k: list(v) for k, v in GREETS.items()},
                tempers={k: list(v[:2]) for k, v in TEMPERS.items()}, allergens=ALLERGENS, nap_steps={k: list(v) for k, v in NAP_STEPS.items()},
                moves={mk: {k: [v[0], v[1], v[2] > 0] for k, v in mv.items()} for mk, mv in MOVES.items()}, scrape_order=SCRAPE_ORDER,
                moment_title=MOMENT_TITLE, play_beats=PLAY_BEATS, sleep_pats=SLEEP_PATS, intro=INTRO, apprentice=APPRENTICE,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    return {'arrive': 'Rửa tay → đọc giấy dặn → chào bé hợp tính → mở túi, hỏi món còn thiếu → nhận bé.',
            'snack': 'Chọn món (xem thành phần) → sơ chế hợp tuổi → rửa tay, cho bé ngồi ghế → dọn cho bé ăn.',
            'meal': 'Món chính, rau canh, đồ uống (xem thành phần) → sơ chế hợp tuổi → rửa tay, cho bé ngồi ghế → dọn cơm.',
            'play': 'Nhìn tâm trạng bé → chọn trò hợp tâm trạng, hợp tuổi → chơi cùng bé → dọn đồ chơi.',
            'safety': 'Ngồi ngang tầm bé, chạm vào những chỗ dễ nguy hiểm để xử lý → xong.',
            'nap': 'Đi vệ sinh → kéo rèm → đúng đồ ôm → hát ru → vỗ nhẹ lúc bé thở ra.',
            'moment': 'Bình tĩnh, ân cần: chọn từng cách dỗ (sơ cứu theo thứ tự) tới khi bé ổn.',
            'handover': 'Đánh dấu những dòng đúng sự thật trong nhật ký → bàn giao bé.'}.get(t.get('kind'), '')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'tidy':
        return 'Đã rửa bình sữa, xếp đồ chơi vào rổ.'
    if e.get('role') == 'cook':
        return 'Đã nấu sẵn nồi cháo, để nguội bớt trên bếp.'
    return None


# ================================================================ saves
def _bad(cond) -> None:
    kit.need(cond, 'Dữ liệu nghề trông trẻ sai.')


def _vbool(x) -> None:
    _bad(type(x) is bool)


def _vlist(x, allowed, n) -> None:
    _bad(isinstance(x, list) and len(x) <= n and len(set(x)) == len(x) and all(isinstance(i, str) and i in allowed for i in x))


ST_KEYS = {k: set(_fresh_st(k)) for k in KINDS}


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc trông trẻ không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc trông trẻ sai.')
    st, n, k = t.get('st'), t['needs'], t['kind']
    kit.need(isinstance(st, dict) and set(st) == ST_KEYS[k], 'Tiến độ việc trông trẻ sai.')
    if k == 'arrive':
        for x in ('wash', 'note', 'bag'):
            _vbool(st[x])
        _bad(st['greet'] is None or st['greet'] in GREETS)
        _bad(st['ask'] is None or st['ask'] in n['bag'])
        kit.integer(st['asks'], 0, 9)
    elif k in ('snack', 'meal'):
        _vlist(st['plate'], n['menu'], len(n['groups']) + 1)
        _vlist(st['prep'], st['plate'], len(n['groups']) + 1)
        _bad(all(FOODS[x]['prep'] for x in st['prep']))
        _vbool(st['kidwash'])
        _vbool(st['seat'])
    elif k == 'play':
        _bad(st['act'] is None or st['act'] in n['acts'])
        kit.integer(st['beat'], 0, PLAY_BEATS)
        kit.integer(st['joy'], 0, 100)
        _bad(isinstance(st['answers'], list) and len(st['answers']) <= PLAY_BEATS and all(type(a) is int and 0 <= a <= 2 for a in st['answers']))
        _bad(st['act'] is not None or (st['beat'] == 0 and not st['answers']))
        _vbool(st['tidy'])
    elif k == 'safety':
        _vlist(st['fixed'], [x for x in n['items'] if HAZ[x][2]], ROOM_SIZE)
        _vlist(st['wrong'], [x for x in n['items'] if not HAZ[x][2]], ROOM_SIZE)
    elif k == 'nap':
        for x in ('potty', 'dark', 'song'):
            _vbool(st[x])
        _bad(st['lovey'] is None or st['lovey'] == fam(n['fam'])['lovey'])
        _bad(st['pat'] is None or (type(st['pat']) in (int, float) and 0 <= st['pat'] <= 10 ** 11))
        kit.integer(st['good'], 0, SLEEP_PATS)
        kit.integer(st['fuss'], 0, 99)
    elif k == 'moment':
        kit.integer(st['calm'], 0, 100)
        _vlist(st['used'], n['moves'], len(n['moves']))
        _vlist(st['bad'], ['harsh', 'scare', 'give_in', 'folk', 'aid'], 5)
        kit.integer(st['order_err'], 0, 9)
    else:
        _vlist(st['ticks'], LOG_IDS, len(LOG_IDS))
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện gia đình sai.')
    if 'tip_given' in t:
        kit.integer(t['tip_given'], 0, 1000)


TODAY_INT = ('day', 'note', 'nap', 'tv', 'hazards', 'missed', 'pts', 'safe_slip', 'blocks', 'joy', 'handed')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    td = d['today']
    _bad(isinstance(td, dict) and set(td) == set(_fresh_today(0)))
    for k in TODAY_INT:
        kit.integer(td[k], 0, 10 ** 7)
    _bad(td['fam'] in FAMILIES)
    _vlist(td['food'], FOODS, 10)
    _bad(td['play'] == '' or td['play'] in ACTS)
    _bad(td['moment'] == '' or td['moment'] in MOVES)
    _bad(td['oops'] == '' or td['oops'] in ALLERGENS)
    _bad(isinstance(d['fams'], dict) and set(d['fams']) <= set(FAMILIES))
    for v in d['fams'].values():
        _bad(isinstance(v, dict) and set(v) == {'visits', 'trust'})
        kit.integer(v['visits'], 0, 999)
        kit.integer(v['trust'], 0, TRUST_MAX)
    _bad(isinstance(d['stats'], dict) and len(d['stats']) <= 20)
    for v in d['stats'].values():
        kit.integer(v, 0, 10 ** 9)
    lr = d['learn']
    _bad(isinstance(lr, dict) and set(lr) == {'task', 'codes', 'done'})
    _bad(lr['task'] is None or (isinstance(lr['task'], str) and len(lr['task']) <= 80))
    _vlist(lr['codes'], CATCH, len(CATCH))
    _vbool(lr['done'])
    kit.desk_validate(d['desk'], DESK)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='bm_', category='service',
    meta=dict(short='Bảo mẫu', place='Tổ trông trẻ Mèo Con', tagline='Ăn ngon, ngủ yên, chơi vui, về nhà an toàn.', icon='bear',
              color='#e0875a', light='#fdeee4', weather='Nắng nhẹ ngõ Hoa Sữa', work='Lịch trông bé', station='Nhà của bé',
              greeting='Rửa tay, đọc giấy dặn rồi mới nhận bé. Mỗi việc trong ngày làm theo lịch, cuối ngày kể thật với bố mẹ bé.',
              caption='Một ngày bình yên của bé', map_label='26 · TỔ TRÔNG TRẺ MÈO CON'),
    people=PEOPLE,
    staff=[('Thảo', 'tidy', 'Sinh viên sư phạm mầm non, gọn gàng, hát hay.', 80, 86),
           ('Hương', 'cook', 'Từng nấu bếp nhà trẻ, cháo nào cũng vừa miệng bé.', 76, 90),
           ('Ngân', 'tidy', 'Nhanh nhẹn, nhìn đâu cũng thấy chỗ cần dọn.', 86, 78),
           ('Liên', 'cook', 'Nhớ hết món bé nào dị ứng gì.', 72, 94)],
    roles={'tidy': 'Dọn đồ chơi, rửa bình', 'cook': 'Nấu cháo, sơ chế món ăn'},
    tip=0,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    wait=True,
    activity=('📝', 'Giấy dặn của bố mẹ', [('Bé Bin', 'Dị ứng trứng'), ('Bé Na', 'Dị ứng đậu phộng'), ('Bé Mít', 'Dị ứng tôm'), ('Bé Bông', 'Dị ứng sữa bò')],
              ['Đọc giấy dặn, nhận bé', 'Ăn đúng món, hợp tuổi', 'Chơi vui, ngủ ngon, nhà an toàn', 'Bàn giao kể thật']),
    stories=[('Tổ trông trẻ Mèo Con', ('Cô Tâm làm cô nuôi dạy trẻ hai mươi năm, về hưu vẫn không xa được tụi nhỏ.',
                                      'Cô mở tổ trông trẻ trong căn hộ tầng hai, cửa sổ dán đầy tranh bút sáp.',
                                      'Cô bảo: “Trông con người ta là giữ cả trái tim của bố mẹ nó.”')),
             ('Tờ giấy dặn', ('Ngày đầu, cô Tâm đưa bạn xấp giấy dặn cũ của các nhà, mép giấy quăn hết.',
                              'Dòng nào cũng có chữ in đậm: dị ứng, giờ ngủ, đồ ôm.',
                              'Cô nói: “Đọc như đọc thư của người thân. Mỗi dòng là một nỗi lo.”')),
             ('Con gấu bông nâu', ('Bé Bin chỉ ngủ khi ôm con gấu bông nâu đã sờn tai.',
                                   'Hôm đầu bạn đưa nhầm con thỏ, bé khóc mãi.',
                                   'Giờ bạn nhớ đồ ôm của từng bé, như nhớ tên các bé vậy.'))],
    review_asides=['Bé về nhà vui vẻ, kể về cô suốt buổi tối.', 'Giấy dặn nhớ từng dòng, không phải nhắc.',
                   'Nhật ký trong ngày rõ ràng, kể thật từng chuyện.', 'Bé ăn ngoan, ngủ ngon.'],
    situations=SITUATIONS,
    more_line='Tới giờ việc tiếp theo trong lịch của bé.',
    open_line='Bố mẹ bé sắp tới. Rửa tay, chuẩn bị đón bé nhé.',
    guide='Mỗi ngày trông một bé theo lịch: rửa tay, đọc giấy dặn, chào bé, kiểm túi → bữa ăn hợp tuổi, tránh món bé dị ứng → '
          'trò chơi hợp tâm trạng → soát nhà → ru ngủ, vỗ nhẹ theo nhịp thở → dỗ bé khi khóc, ngã, ăn vạ → bàn giao, kể thật.',
)
