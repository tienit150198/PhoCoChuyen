"""Teacher v2 period ("Tiết học"): a real class with individual kids, a plan
that has to fit the day, classroom moments with trade-offs, exit tickets with
feedback choices, and small ongoing arcs for each kid.

The v1 task from game/extra_content.make_task keeps every fixed field. The v2
layer lives under t['room'] and its fixed facts are rolled from (day, slot)
only, so it is identical whenever it is created (start of day, first click,
or a later reload) and validation can regenerate it. Tasks that already made
v1 progress keep the v1 rules in game/experiences.py.

Texts may contain {Title}/{title}: the player's title as a teacher
("Cô"/"Thầy", "cô"/"thầy"). The client replaces them in projections; the
server replaces them in messages and feed posts it writes itself.
"""
from __future__ import annotations

import copy
import functools
import itertools
import random

PLAN_MINUTES = 35
PLAN_MIN = 25
STAGES = ('roll', 'plan', 'teach', 'check', 'ready')
MAX_TRUST = 12
V1_KIDS = ('minh', 'an', 'vy', 'bao')

KIDS = [
    dict(id='minh', name='Minh', emoji='👦', style='look', guardian='Mẹ Minh', trait='Nhút nhát, thích xem tranh vẽ'),
    dict(id='an', name='An', emoji='👧', style='hands', guardian='Bố An', trait='Thích tự tay làm thử'),
    dict(id='vy', name='Vy', emoji='👧', style='talk', guardian='Mẹ Vy', trait='Nói nhiều, thích kể chuyện'),
    dict(id='bao', name='Bảo', emoji='👦', style='short', guardian='Mẹ Bảo', trait='Hiếu động, mau chán việc dài'),
    dict(id='khoa', name='Khoa', emoji='🧒', style='look', guardian='Bà nội Khoa', trait='Mê xem sơ đồ máy móc'),
    dict(id='linh', name='Linh', emoji='👧', style='short', guardian='Mẹ Linh', trait='Cầu toàn, rối khi bài dài'),
    dict(id='tu', name='Tú', emoji='👦', style='hands', guardian='Bố Tú', trait='Mới chuyển trường, khéo tay'),
    dict(id='mai', name='Mai', emoji='👧', style='talk', guardian='Mẹ Mai', trait='Phụ mẹ bán phở, rất hay hỏi'),
]
KID = {k['id']: k for k in KIDS}
KID_IDS = [k['id'] for k in KIDS]
# Carrier NPCs for feed posts (the four original kids exist as NPCs; the
# others write through the parent NPC with their guardian as author).
CARRIER = dict(minh='teacher_npc_02', an='teacher_npc_03', vy='teacher_npc_04', bao='teacher_npc_05')
PARENT_NPC = 'teacher_npc_06'
COLLEAGUE_NPC = 'teacher_npc_01'

METHODS = [
    dict(id='look', emoji='🖼️', name='Vẽ hình mẫu cho xem'),
    dict(id='hands', emoji='🧩', name='Đưa đồ vật cho tự thử'),
    dict(id='talk', emoji='💬', name='Kể ví dụ, cho nói lại'),
    dict(id='short', emoji='⏱️', name='Chia nhỏ từng bước'),
]
METHOD_IDS = [m['id'] for m in METHODS]
STYLE_LABEL = dict(look='Học bằng mắt', hands='Học bằng tay', talk='Học bằng lời', short='Học từng bước ngắn')

# What a kid looks like when lost, and what they say when the help does not fit.
CLUES = {
    'minh': ('Minh nhìn bảng, bút vẫn chưa chạm giấy.', 'Minh lí nhí: “{Title} vẽ cho con xem được không ạ?”'),
    'khoa': ('Khoa nghiêng đầu nhìn lên bảng, nhíu mày.', 'Khoa lắc đầu: “Con muốn xem hình mẫu cơ.”'),
    'an': ('An mân mê mấy cái nắp chai trên bàn.', 'An hỏi nhỏ: “Cho con cầm thử được không ạ?”'),
    'tu': ('Tú lấy que tính ra xếp thử, rồi dừng lại.', 'Tú gãi đầu: “Con phải làm bằng tay mới hiểu.”'),
    'vy': ('Vy quay sang hỏi bạn bên cạnh.', 'Vy nhăn mặt: “Kể con nghe một ví dụ đi ạ.”'),
    'mai': ('Mai chống cằm, môi mấp máy đọc đề.', 'Mai nói: “{Title} nói lại bằng một ví dụ nha.”'),
    'bao': ('Bảo làm được nửa câu rồi bỏ dở.', 'Bảo thở dài: “Nhiều quá, con rối.”'),
    'linh': ('Linh tẩy đi tẩy lại chữ đầu tiên.', 'Linh rụt rè: “Làm từng câu một được không ạ?”'),
}

CONDITIONS = [
    dict(id='fresh', emoji='☀️', text='Sáng đầu tuần, lớp tươi tỉnh', want=('calm', 'game', 'move'), tip='Lớp đang sẵn sàng: mở đầu kiểu nào cũng hợp.'),
    dict(id='noisy', emoji='🔔', text='Vừa hết giờ ra chơi, lớp còn ồn', want=('calm',), tip='Lớp còn ồn: mở đầu bằng hoạt động nhẹ nhàng.'),
    dict(id='sleepy', emoji='🌧️', text='Trời mưa rả rích, lớp lờ đờ', want=('move',), tip='Lớp buồn ngủ: mở đầu bằng vận động.'),
    dict(id='nervous', emoji='📝', text='Sắp kiểm tra, lớp hơi căng', want=('game',), tip='Lớp đang lo: mở đầu bằng một trò chơi nhỏ.'),
    dict(id='hot', emoji='🥵', text='Phòng nóng, quạt kêu to', want=('calm', 'game'), tip='Trời nóng: tránh vận động mạnh lúc đầu.'),
    dict(id='friday', emoji='🎈', text='Chiều thứ Sáu, lớp nôn về', want=('game', 'move'), tip='Lớp nôn về: mở đầu thật vui để giữ nhịp.'),
]
COND = {x['id']: x for x in CONDITIONS}
ENERGY = dict(calm=('🧘', 'Nhẹ nhàng'), move=('🏃', 'Vận động'), game=('🎲', 'Trò chơi'))

CARDS = [
    dict(id='breath', emoji='🧘', name='Hít thở, hát nhỏ', minutes=4, energy='calm', styles=('talk',), role='open'),
    dict(id='dance', emoji='💃', name='Vận động theo bài hát', minutes=5, energy='move', styles=('hands',), role='open'),
    dict(id='riddle', emoji='❓', name='Câu đố mở màn', minutes=5, energy='game', styles=('talk', 'short'), role='open'),
    dict(id='demo', emoji='🖼️', name='Làm mẫu trên bảng', minutes=8, energy='calm', styles=('look',), role='core'),
    dict(id='cards', emoji='🧩', name='Thẻ và đồ vật theo nhóm', minutes=12, energy='game', styles=('hands', 'short'), role='core'),
    dict(id='story', emoji='📖', name='Kể chuyện có ví dụ', minutes=10, energy='calm', styles=('talk', 'look'), role='core'),
    dict(id='relay', emoji='🏃', name='Tiếp sức lên bảng', minutes=12, energy='move', styles=('hands', 'short'), role='core'),
    dict(id='pairs', emoji='👫', name='Hỏi – đáp cặp đôi', minutes=8, energy='game', styles=('talk', 'short'), role='core'),
    dict(id='poster', emoji='🎨', name='Vẽ sơ đồ theo nhóm', minutes=15, energy='calm', styles=('look', 'hands'), role='core'),
    dict(id='board', emoji='✋', name='Giơ bảng con', minutes=5, energy='game', styles=('look', 'short'), role='check'),
    dict(id='ticket', emoji='🎫', name='Phiếu 3 câu cuối tiết', minutes=7, energy='calm', styles=('short',), role='check'),
    dict(id='share', emoji='🗣️', name='Nói một điều mình học được', minutes=5, energy='calm', styles=('talk',), role='check'),
]
CARD = {x['id']: x for x in CARDS}
CARD_IDS = [x['id'] for x in CARDS]

ROLL = {
    'here': dict(emoji='🪑', clue='Đang ngồi ở chỗ', options=[dict(id='present', label='Có mặt')]),
    'sick': dict(emoji='📩', clue='Mẹ nhắn: “Con sốt, xin cho con nghỉ.”',
                 options=[dict(id='excused', label='Ghi vắng có phép'), dict(id='present', label='Ghi có mặt')]),
    'late': dict(emoji='🏃', clue='Gõ cửa ở phút thứ năm, thở hổn hển.',
                 options=[dict(id='let_in', label='Cho vào chỗ, hỏi riêng sau'), dict(id='front', label='Hỏi lý do trước lớp'), dict(id='outside', label='Đứng ngoài năm phút cho nhớ')]),
    'missing': dict(emoji='❔', clue='Ghế trống, chưa có tin nhắn nào.',
                    options=[dict(id='report', label='Báo văn phòng, nhắn phụ huynh ngay'), dict(id='mark', label='Ghi vắng rồi dạy tiếp')]),
}
# (focus, trust, mistake, message)
ROLL_EFFECT = {
    ('here', 'present'): (0, 0, False, '{name} có mặt.'),
    ('sick', 'excused'): (0, 0, False, 'Đã ghi {name} vắng có phép. Chúc {name} mau khỏe.'),
    ('sick', 'present'): (0, 0, True, 'Đã ghi {name} có mặt.'),
    ('late', 'let_in'): (0, 1, False, '{name} vào chỗ, nói nhỏ: “Con cảm ơn ạ.”'),
    ('late', 'front'): (-3, -1, False, '{name} đỏ mặt kể trước cả lớp: sáng nay xe hỏng.'),
    ('late', 'outside'): (-3, -2, True, '{name} đứng ngoài cửa năm phút, lỡ phần mở bài.'),
    ('missing', 'report'): (0, 1, False, 'Văn phòng gọi được nhà {name}: xe hỏng, bố đưa {name} vào sau giờ ra chơi.'),
    ('missing', 'mark'): (0, 0, True, 'Đã ghi {name} vắng. Tiết học tiếp tục.'),
}
GOOD_ROLL = {('here', 'present'), ('sick', 'excused'), ('late', 'let_in'), ('late', 'front'), ('missing', 'report')}


def _o(id, label, text, focus=0, trust=None, mistake=False, flag=None, note=None):
    return dict(id=id, label=label, text=text, focus=focus, trust=trust or {}, mistake=mistake, flag=flag or {}, note=note)


# Classroom moments. `kids` must be present for the moment to be rolled.
INCIDENTS = [
    dict(id='phone', emoji='📱', title='Chuông điện thoại trong cặp', kids=('khoa',), tier=1,
         text='Chuông reo từ cặp của Khoa. Màn hình sáng hai chữ “Bà nội”. Cả lớp quay xuống nhìn.',
         options=[_o('step_out', 'Cho Khoa ra cửa nghe nhanh, vào thì tắt chuông', 'Bà dặn chiều nay đón muộn. Khoa vào lớp, tự tắt chuông, ngồi ngay ngắn.', focus=-5, trust=dict(khoa=2), note='khoa_thanks'),
                  _o('take', 'Thu điện thoại ngay, cuối buổi trả', 'Lớp im phắc. Chiều đó bà đứng chờ ở cổng mà Khoa không hề biết.', trust=dict(khoa=-1), note='khoa_worry'),
                  _o('ignore', 'Kệ chuông, giảng to hơn', 'Chuông reo thêm hai lần. Cả lớp cười rúc rích, bài học đứt mạch.', focus=-10)]),
    dict(id='shy', emoji='🙈', title='Biết mà không dám giơ tay', kids=('minh',), tier=1,
         text='Minh viết đúng đáp án ra nháp, nhưng tay vẫn giấu dưới bàn.',
         options=[_o('call', 'Gọi tên Minh đứng lên trả lời', 'Minh đỏ mặt, nói lí nhí rồi cúi gằm xuống bàn.', trust=dict(minh=-1)),
                  _o('boards', 'Cả lớp giơ bảng con, khen bảng của Minh', 'Minh thấy bảng mình được khen, khẽ mỉm cười.', focus=5, trust=dict(minh=2)),
                  _o('whisper', 'Nói nhỏ: “Lát nữa con đọc câu con viết nhé?”', 'Minh gật đầu. Đến lượt, Minh đọc rõ từng chữ.', trust=dict(minh=2))]),
    dict(id='copy', emoji='👀', title='Liếc bài bạn', kids=('vy', 'linh'), tier=1,
         text='Lúc làm bài, Vy cứ nghiêng người nhìn sang vở của Linh.',
         options=[_o('name', 'Nêu tên Vy trước lớp: “Không được nhìn bài!”', 'Vy òa khóc. Cả lớp xì xào suốt phần còn lại.', trust=dict(vy=-2), mistake=True, flag=dict(vy='copy'), note='vy_upset'),
                  _o('move', 'Lặng lẽ đổi chỗ Vy lên bàn đầu, hẹn nói chuyện sau', 'Vy tự làm bài, chậm hơn, nhưng là bài của Vy.', trust=dict(vy=1)),
                  _o('blind', 'Coi như không thấy', 'Linh lấy tay che vở, khó chịu ra mặt.', trust=dict(linh=-1), flag=dict(vy='copy'))]),
    dict(id='push', emoji='🥊', title='Xô nhau vì thua trò chơi', kids=('bao', 'tu'), tier=1,
         text='Đội thua, Bảo đẩy ghế Tú: “Tại mày chậm!” Tú ôm cánh tay.',
         options=[_o('talk', 'Tách hai bạn, cho mỗi bạn kể lại, cùng tìm cách sửa', 'Bảo xin lỗi, Tú gật đầu. Hai bạn cùng kê lại ghế.', focus=-5, trust=dict(bao=1, tu=1)),
                  _o('punish', 'Phạt cả hai đứng cuối lớp', 'Tú bị phạt dù bị đẩy. Tú không nói thêm câu nào cả buổi.', trust=dict(bao=-1, tu=-2), mistake=True, note='tu_dad'),
                  _o('replay', 'Cho đội thua chơi lại cho vui', 'Bảo hết cáu. Tay Tú vẫn đỏ, không ai hỏi han.', focus=5, trust=dict(bao=1, tu=-1))]),
    dict(id='accent', emoji='🗣️', title='Bị nhại giọng quê', kids=('tu',), tier=1,
         text='Tú đọc bài bằng giọng Quảng Ngãi. Vài bạn nhại theo rồi cười ồ.',
         options=[_o('teach', 'Nhắc quy ước lớp, mời Tú dạy cả lớp một từ quê mình', '“Mô, tê, răng, rứa!” Cả lớp đọc theo Tú, cười vui chứ không chê.', trust=dict(tu=3)),
                  _o('hush', 'Bảo cả lớp trật tự rồi đọc tiếp', 'Tiếng cười tắt, nhưng Tú đọc nhỏ dần.', trust=dict(tu=-1)),
                  _o('laugh', 'Cười theo cho lớp vui', 'Tú cúi đầu. Giờ ra chơi Tú ngồi một mình.', trust=dict(tu=-3), mistake=True, note='tu_dad')]),
    dict(id='tears', emoji='😢', title='Sai một câu là khóc', kids=('linh',), tier=1,
         text='Linh làm sai câu thứ hai, gạch xóa đến rách giấy rồi bật khóc.',
         options=[_o('grow', 'Ngồi cạnh: “Chỗ sai là chỗ đầu óc đang lớn đó con”, cho sửa bằng bút màu', 'Linh sửa bằng bút xanh, còn vẽ thêm một ngôi sao nhỏ.', trust=dict(linh=2)),
                  _o('scold', '“Có vậy mà cũng khóc!”', 'Linh nín, nhưng không viết thêm chữ nào nữa.', trust=dict(linh=-3), mistake=True, note='linh_mom'),
                  _o('nurse', 'Cho Linh xuống phòng y tế nghỉ', 'Linh ngồi ở phòng y tế, lỡ mất phần luyện tập.', flag=dict(linh='miss'))]),
    dict(id='projector', emoji='🔌', title='Máy chiếu tắt phụt', kids=(), tier=1,
         text='Đang chiếu hình minh họa thì máy chiếu tắt phụt. Cả lớp “ồ” lên.',
         options=[_o('draw', 'Vẽ nhanh lên bảng, cho lớp đoán hình', 'Hình vẽ tay hơi méo, cả lớp đoán đúng và cười vui.', focus=5),
                  _o('wait', 'Chờ bác kỹ thuật lên sửa', 'Mười phút chờ đợi, lớp bắt đầu nói chuyện riêng.', focus=-15),
                  _o('read', 'Cho cả lớp đọc sách tự do', 'Lớp yên, nhưng bài học bị đứt mạch.', focus=-5)]),
    dict(id='bee', emoji='🐝', title='Ong bay vào lớp', kids=(), tier=1,
         text='Một con ong bay vào qua cửa sổ. Mấy bạn bàn đầu hét toáng lên.',
         options=[_o('window', 'Bình tĩnh bảo lớp ngồi yên, mở rộng cửa sổ', 'Ong lượn hai vòng rồi bay ra. Cả lớp vỗ tay.', focus=-5),
                  _o('swat', 'Cầm sách đập', 'Ong hoảng, bay loạn xạ. Một bạn suýt bị đốt.', focus=-10, mistake=True),
                  _o('out', 'Cho cả lớp ra hành lang', 'An toàn, nhưng mất gần mười phút mới vào lại.', focus=-15)]),
    dict(id='sleepy', emoji='😴', title='Ngủ gật giữa giờ', kids=('mai',), tier=1,
         text='Mai gục đầu xuống bàn, mắt díp lại.',
         options=[_o('ask', 'Hỏi nhỏ: “Sáng nay con dậy sớm à?”, cho đi rửa mặt', 'Mai kể sáng nào cũng dậy phụ mẹ bán phở. Rửa mặt xong, Mai tỉnh hẳn.', trust=dict(mai=2)),
                  _o('ruler', 'Gõ thước xuống bàn cho tỉnh', 'Mai giật mình, cả lớp giật mình theo.', focus=-5, trust=dict(mai=-2)),
                  _o('let', 'Để Mai ngủ, lát tính', 'Mai ngủ qua cả phần luyện tập.', flag=dict(mai='miss'))]),
    dict(id='toilet', emoji='🚻', title='Xin ra ngoài lần thứ ba', kids=('an',), tier=1,
         text='An ôm bụng, giơ tay xin đi vệ sinh lần thứ ba trong tiết.',
         options=[_o('buddy', 'Cho đi, nhờ một bạn đi cùng, báo phòng y tế nếu còn đau', 'An đau bụng thật. Cô y tế cho uống nước ấm, An đỡ hẳn.', trust=dict(an=1), note='an_dad'),
                  _o('deny', '“Ra ngoài nhiều rồi, ngồi yên đi!”', 'An ngồi co ro, nhăn nhó suốt tiết.', trust=dict(an=-2), mistake=True),
                  _o('alone', 'Cho đi một mình', 'An đi khá lâu mới về, lỡ một đoạn bài.', flag=dict(an='miss'))]),
    dict(id='candy', emoji='🍬', title='Chuyền kẹo trong giờ', kids=('bao',), tier=1,
         text='Bảo mang một túi kẹo me, lén chuyền khắp dãy bàn.',
         options=[_o('keep', 'Giữ túi kẹo, hẹn cuối giờ cả lớp chia đều', 'Bảo hơi tiếc, nhưng cuối giờ được làm “người chia kẹo”, vui ra mặt.', focus=5, trust=dict(bao=1)),
                  _o('bin', 'Tịch thu, bỏ vào thùng rác', 'Bảo mếu máo cả buổi.', trust=dict(bao=-2), note='bao_mom'),
                  _o('allow', 'Để các bạn ăn cho vui', 'Cả lớp nhai kẹo rôm rốp, không ai nghe giảng.', focus=-10)]),
    dict(id='visit', emoji='👩‍💼', title='Ban giám hiệu ghé dự giờ', kids=(), tier=2,
         text='Cô Hiệu phó khẽ mở cửa, ngồi xuống cuối lớp và mở sổ dự giờ.',
         options=[_o('same', 'Giữ đúng giáo án, vẫn gọi cả những bạn đang chậm', 'Cô Hiệu phó ghi vào sổ: “Quan tâm đến từng học sinh.”', focus=5, note='visit_good'),
                  _o('stars', 'Chỉ gọi mấy bạn học nhanh cho tiết trôi', 'Tiết học trôi chảy, nhưng các bạn chậm ngồi im cả buổi.', mistake=True),
                  _o('show', 'Đổi sang trò chơi cho lớp sôi nổi', 'Lớp rất vui, nhưng mục tiêu bài học bị bỏ quên.', focus=5, mistake=True)]),
    dict(id='leak', emoji='💧', title='Mái dột ngay chỗ ngồi', kids=('an', 'tu'), tier=2,
         text='Mưa to, nước dột xuống bàn của An và Tú, vở ướt nhẹp.',
         options=[_o('fix', 'Kê lại bàn, đặt chậu hứng, phơi vở, báo bác bảo vệ', 'Hai bạn ngồi chỗ khô, vở được phơi bên cửa sổ.', focus=-5, trust=dict(an=1, tu=1)),
                  _o('stay', 'Bảo hai bạn chịu khó ngồi tạm', 'Vở ướt, hai bạn không viết được chữ nào.', focus=-5, mistake=True, flag=dict(an='miss', tu='miss')),
                  _o('stop', 'Cho cả lớp nghỉ tiết', 'Lớp reo lên, nhưng bài hôm nay bỏ dở.', focus=-15)]),
]
INCIDENT = {x['id']: x for x in INCIDENTS}

NOTES = {
    'khoa_thanks': ('khoa', 'Bà nội Khoa', 'Bà cảm ơn {title} đã cho cháu nghe máy. Chiều nay bà đón muộn, may mà cháu biết để đợi.'),
    'khoa_worry': ('khoa', 'Bà nội Khoa', 'Chiều nay bà gọi cháu mãi không được, đứng ở cổng lo quá. Lần sau {title} cho cháu nghe máy một chút được không?'),
    'vy_upset': ('vy', 'Mẹ Vy', 'Tôi không bênh con, nhưng bị nêu tên trước lớp làm con khóc cả tối. Có gì mong {title} nói riêng với cháu.'),
    'tu_dad': ('tu', 'Bố Tú', 'Cháu mới chuyển trường, về nhà không chịu nói chuyện. Nhờ {title} để ý giúp cháu với.'),
    'linh_mom': ('linh', 'Mẹ Linh', 'Linh về kể bị chê “có vậy mà cũng khóc”. Nhà đang tập cho cháu bớt sợ sai, mong {title} nhẹ nhàng với cháu.'),
    'visit_good': (None, 'Cô Hạ', 'Nghe nói tiết dự giờ vừa rồi được ghi “quan tâm đến từng học sinh”. Chúc mừng nha!'),
    'bao_mom': ('bao', 'Mẹ Bảo', 'Túi kẹo là quà bà ngoại cho cháu. Lần sau {title} giữ giúp rồi trả cháu cuối buổi được không ạ?'),
    'an_dad': ('an', 'Bố An', 'Tối qua cháu ăn đồ lạ nên đau bụng. Cảm ơn {title} đã cho cháu xuống y tế kịp thời.'),
}

# Three beats per kid, unlocked by trust 3 / 6 / 9 (never go back).
ARCS = {
    'minh': [('Minh tự giơ tay trả lời câu đầu tiên.', 'Tối qua Minh khoe con đã tự giơ tay. Cả nhà mừng lắm, cảm ơn {title}!'),
             ('Minh xin lên bảng vẽ hình minh họa cho cả lớp.', 'Minh về nhà vẽ lại hình trên bảng cho em xem. Con tự tin hẳn.'),
             ('Minh dẫn chuyện trong giờ sinh hoạt lớp.', 'Mẹ không tin nổi Minh dám cầm micro. Cảm ơn {title} đã kiên nhẫn với con.')],
    'an': [('An tự dọn gọn góc đồ dùng sau giờ học.', 'An bảo ở lớp con được giao giữ góc đồ dùng, về nhà cũng tự dọn bàn.'),
           ('An làm bộ thẻ đếm bằng nắp chai cho cả lớp.', 'Cả tuần An gom nắp chai khắp nhà, hóa ra để làm đồ dùng cho lớp.'),
           ('An hướng dẫn nhóm làm một thí nghiệm nhỏ.', 'An nói muốn làm nhà khoa học. Cảm ơn {title} đã cho con được thử.')],
    'vy': [('Vy chuyền micro cho bạn, không nói lấn lượt nữa.', 'Vy kể hôm nay con biết chờ bạn nói xong. Nhà cũng thấy con bớt nói lấn.'),
           ('Vy tự làm hết bài, không nhìn sang ai.', 'Vy khoe bài tự làm, sai hai câu nhưng con vui lắm.'),
           ('Vy làm “phóng viên nhí” phỏng vấn cả lớp.', 'Vy ghi chép cả cuốn sổ phỏng vấn. Cảm ơn {title} đã tìm đúng chỗ cho cái miệng của con.')],
    'bao': [('Bảo ngồi yên được trọn một hoạt động.', 'Lần đầu Bảo kể được trọn một bài học. Cả nhà ngạc nhiên lắm.'),
            ('Bảo nhận vai trọng tài, thổi còi rất công bằng.', 'Bảo đòi mua còi để làm trọng tài cho em. Con thích được tin tưởng.'),
            ('Bảo tự xin lỗi bạn trước khi được nhắc.', 'Hôm nay Bảo tự xin lỗi em khi giành đồ chơi. Cảm ơn {title} nhiều.')],
    'khoa': [('Khoa tự bỏ điện thoại vào hộp của lớp.', 'Khoa bảo ở lớp có hộp điện thoại, con tự giác lắm. Bà yên tâm hơn.'),
             ('Khoa giúp cắm lại dây máy chiếu cho lớp.', 'Khoa kể được làm “kỹ thuật viên” của lớp, về khoe bà suốt.'),
             ('Khoa viết về bà nội trong bài văn “Người em yêu quý”.', 'Bà đọc bài văn của cháu mà khóc. Cảm ơn {title} đã dạy cháu viết.')],
    'linh': [('Linh cười được khi làm sai một câu.', 'Linh về kể “sai là đầu óc đang lớn”. Con bớt khóc hẳn.'),
             ('Linh thử làm bài khó mà không sợ sai.', 'Linh tự chọn bài khó để làm. Mẹ mừng vì con dám thử.'),
             ('Linh giúp bạn sửa bài thật nhẹ nhàng.', 'Nghe nói Linh giảng bài cho bạn rất kiên nhẫn. Giống {title} lắm.')],
    'tu': [('Tú dạy cả lớp một từ quê mình.', 'Tú về kể cả lớp học nói “mô, tê”. Lần đầu con cười khi kể chuyện trường mới.'),
           ('Tú có người bạn thân đầu tiên ở lớp mới.', 'Cuối tuần Tú xin sang nhà bạn chơi. Bố yên tâm rồi.'),
           ('Tú kể chuyện quê trong giờ Tiếng Việt, cả lớp vỗ tay.', 'Cảm ơn {title}. Cháu bảo giờ lớp này là nhà thứ hai.')],
    'mai': [('Mai kể chuyện phụ mẹ bán phở mỗi sáng.', 'Cảm ơn {title} đã hỏi han cháu. Nhà bận thật, sáng nào cháu cũng phụ mẹ.'),
            ('Lớp đổi giờ trực nhật để Mai kịp đến lớp.', 'Nghe cháu kể lớp đổi lịch trực cho cháu, mẹ cảm động lắm.'),
            ('Mai nhận giấy khen chuyên cần.', 'Tờ giấy khen được treo ngay ở quán phở. Khách nào cũng hỏi thăm.')],
}

# Neutral notes: the answer itself, not the note, tells right from wrong.
TICKET_NOTES = ('Trình bày gọn, có vẽ hình kèm theo.', 'Viết nhanh, chữ hơi nghiêng.', 'Gạch xóa một chỗ rồi viết lại.', 'Tự khoanh tròn đáp án.', 'Viết thêm một dòng giải thích.', 'Vẽ một ngôi sao nhỏ ở góc phiếu.', 'Chữ to, rõ từng nét.')
MARKS = [
    dict(id='praise', emoji='🌟', label='Khen cụ thể'),
    dict(id='hint', emoji='🪜', label='Gợi ý một bước'),
    dict(id='private', emoji='🤝', label='Gặp riêng sau giờ'),
]
MARK_FOR = dict(right='praise', wrong='hint', slip='hint', copy='private')
MARK_IDS = [m['id'] for m in MARKS]
MARK_WRONG = dict(
    praise='Phiếu này chưa đúng. Khen lúc này làm bạn tưởng mình đã hiểu.',
    hint='Phiếu này đã đúng rồi. Hãy khen cụ thể điều bạn làm tốt.',
    private='Không cần gặp riêng. Phiếu này là bài của chính bạn ấy.',
)
MARK_WRONG_COPY = 'Phiếu này giống hệt phiếu bạn bên cạnh. Nên gặp riêng để hỏi chuyện, đừng chấm như bình thường.'


def tier_for(day: int) -> int:
    return 1 if day <= 2 else 2 if day <= 5 else 3


def _rng(day: int, slot: int) -> random.Random:
    return random.Random(f'mnl-teacher-room|{day}|{slot}')


def _stars(plan, cond: str, need_styles) -> tuple[int, dict]:
    cards = [CARD[i] for i in plan]
    reach = set()
    for x in cards:
        reach.update(x['styles'])
    parts = dict(open=cards[0]['energy'] in COND[cond]['want'], reach=set(need_styles) <= reach, check=cards[-1]['role'] == 'check')
    parts['missing'] = sorted(set(need_styles) - reach, key=METHOD_IDS.index)
    return int(parts['open']) + int(parts['reach']) + int(parts['check']), parts


def _minutes(plan) -> int:
    return sum(CARD[i]['minutes'] for i in plan)


def plan_error(plan) -> str | None:
    minutes = _minutes(plan)
    if minutes > PLAN_MINUTES:
        return f'Tiết học chỉ có {PLAN_MINUTES} phút. Bớt một hoạt động dài nhé.'
    if not any(CARD[i]['role'] == 'core' for i in plan):
        return 'Tiết học cần ít nhất một hoạt động chính.'
    if minutes < PLAN_MIN:
        return f'Giáo án mới {minutes} phút, lớp sẽ ngồi không. Cần ít nhất {PLAN_MIN} phút.'
    return None


def _best(hand, cond, need_styles) -> int:
    best = 0
    for combo in itertools.permutations(hand, 3):
        if plan_error(combo) is None:
            best = max(best, _stars(combo, cond, need_styles)[0])
    return best


def _hand(r: random.Random, tier: int, cond: str, need_styles) -> list[str]:
    size = 5 if tier < 3 else 6
    for _ in range(300):
        hand = r.sample(CARD_IDS, size)
        if _best(hand, cond, need_styles) == 3:
            return hand
    # A fitting hand always exists: an opener that fits, two broad cards, a check.
    opener = next(c['id'] for c in CARDS if c['energy'] in COND[cond]['want'] and c['role'] == 'open')
    return [opener, 'story', 'cards', 'board', 'relay'][:size] + (['poster'] if size > 5 else [])


def present_ids(room: dict) -> list[str]:
    return [k['id'] for k in room['kids'] if k['status'] in ('here', 'late')]


def need_styles(room: dict) -> list[str]:
    return sorted({KID[k]['style'] for k in present_ids(room)}, key=METHOD_IDS.index)


def roll(day: int, slot: int) -> dict:
    """Fixed facts of one period. Depends on (day, slot) only."""
    return copy.deepcopy(_roll(day, slot))


@functools.lru_cache(maxsize=256)
def _roll(day: int, slot: int) -> dict:
    r = _rng(day, slot)
    tier = tier_for(day)
    cond = 'fresh' if (day, slot) == (1, 0) else r.choice([c['id'] for c in CONDITIONS])
    ids = sorted(r.sample(KID_IDS, {1: 5, 2: 6, 3: 7}[tier]), key=KID_IDS.index)
    status = {k: 'here' for k in ids}
    pool = ('sick', 'late') if tier == 1 else ('sick', 'late', 'missing')
    for k in r.sample(ids, {1: 1, 2: 2, 3: 2}[tier]):
        status[k] = r.choice(pool)
    # Keep a real class in the room: at least four kids present.
    for k in ids:
        if sum(v in ('here', 'late') for v in status.values()) >= 4:
            break
        if status[k] in ('sick', 'missing'):
            status[k] = 'here'
    kids = [dict(id=k, status=status[k]) for k in ids]
    present = [k for k in ids if status[k] in ('here', 'late')]
    eligible = [x['id'] for x in INCIDENTS if x['tier'] <= tier and all(k in present for k in x['kids'])]
    r.shuffle(eligible)
    count = min(tier, len(eligible))
    phases = sorted(r.sample([0, 1, 2], count))
    events = [dict(id=eid, phase=ph) for eid, ph in zip(eligible[:count], phases)]
    stuck = sorted(r.sample(present, {1: 1, 2: 1, 3: 2}[tier]), key=KID_IDS.index)
    slip = r.choice([k for k in present if k not in stuck])
    styles = sorted({KID[k]['style'] for k in present}, key=METHOD_IDS.index)
    hand = _hand(r, tier, cond, styles)
    return dict(v=2, tier=tier, cond=cond, kids=kids, events=events, stuck=stuck, slip=slip, hand=hand)


FIXED = ('v', 'tier', 'cond', 'kids', 'events', 'stuck', 'slip', 'hand')


def fresh(day: int, slot: int) -> dict:
    room = roll(day, slot)
    room.update(stage='roll', roll={}, plan=[], stars=0, parts={}, lost=[], phase=0, calls={}, helped={}, flags={},
                tickets={}, marks={}, notes=[], arcs=[], reward=0)
    return room


def slot_of(t: dict) -> int:
    return int(t['id'].rsplit('-', 1)[1])


def eligible(t: dict) -> bool:
    """A v1 task that has not started any v1 step can run the v2 period."""
    return (t.get('career') == 'teacher' and 'room' not in t and t.get('stage') == 'plan' and not t.get('plan')
            and not t.get('attendance') and not t.get('taught') and not t.get('grades') and t.get('status') not in ('completed', 'referred', 'cancelled'))


def ensure(t: dict) -> dict:
    if 'room' not in t:
        t['room'] = fresh(t['day'], slot_of(t))
    return t['room']


def titles(s: dict) -> tuple[str, str]:
    gender = (s.get('journey') or {}).get('gender') if isinstance(s.get('journey'), dict) else None
    return ('Thầy', 'thầy') if gender == 'male' else ('Cô', 'cô')


def say(s: dict, text: str) -> str:
    big, small = titles(s)
    return text.replace('{Title}', big).replace('{title}', small)


# ------------------------------------------------------------------ class data
def kids_data(c: dict) -> dict:
    d = c['ext']['data'].setdefault('class', dict(active=None, done={}, history=[]))
    return d.setdefault('kids', {})


def kid_row(c: dict, kid: str) -> dict:
    return kids_data(c).setdefault(kid, dict(trust=0, beat=0, known=False))


def _trust(c: dict, room: dict, kid: str, delta: int) -> None:
    row = kid_row(c, kid)
    row['trust'] = max(0, min(MAX_TRUST, row['trust'] + delta))
    while row['beat'] < 3 and row['trust'] >= (row['beat'] + 1) * 3:
        row['beat'] += 1
        room['arcs'].append(f'{kid}:{row["beat"]}')


def _focus(t: dict, delta: int) -> None:
    t['patience'] = max(25, min(100, t.get('patience', 100) + delta))


# ------------------------------------------------------------------ actions
def handle(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    from . import engine as e
    need = e.need
    room = ensure(t)
    stage = room['stage']
    if name == 'roll':
        need(stage == 'roll', 'Điểm danh đã xong rồi.')
        kid = p.get('kid')
        if kid == 'all':
            todo = [k['id'] for k in room['kids'] if k['status'] == 'here' and k['id'] not in room['roll']]
            need(todo, 'Các bạn đang ngồi ở chỗ đều đã được điểm danh.')
            for k in todo:
                room['roll'][k] = 'present'
            msg = f'Đã điểm danh {len(todo)} bạn đang ngồi ở chỗ.'
        else:
            row = next((k for k in room['kids'] if k['id'] == kid), None)
            need(row, 'Bạn này không có trong danh sách lớp hôm nay.')
            need(kid not in room['roll'], 'Bạn này đã được điểm danh.')
            choice = p.get('choice')
            need(choice in [o['id'] for o in ROLL[row['status']]['options']], 'Lựa chọn điểm danh không hợp lệ.')
            focus, trust, mistake, text = ROLL_EFFECT[(row['status'], choice)]
            msg = text.format(name=KID[kid]['name'])
            if mistake:
                # Allowed, like in a real register: the parents hear about it after the period.
                t['mistakes'] += 1
            room['roll'][kid] = choice
            _focus(t, focus)
            if trust:
                _trust(c, room, kid, trust)
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'
        if len(room['roll']) == len(room['kids']):
            room['stage'] = 'plan'
            msg += ' Điểm danh xong: chọn ba hoạt động cho tiết nhé.'
        return dict(message=msg)
    if name == 'plan':
        need(stage == 'plan', 'Điểm danh xong rồi mới chọn hoạt động nhé.' if stage == 'roll' else 'Tiết học đã bắt đầu.')
        plan = p.get('steps')
        need(isinstance(plan, list) and len(plan) == 3 and all(isinstance(x, str) for x in plan) and len(set(plan)) == 3, 'Chọn đúng ba hoạt động khác nhau.')
        need(all(x in room['hand'] for x in plan), 'Hoạt động này không có trong giáo án hôm nay.')
        reason = plan_error(plan)
        need(reason is None, reason or '')
        stars, parts = _stars(plan, room['cond'], need_styles(room))
        present = present_ids(room)
        lost = [k for k in present if KID[k]['style'] in parts['missing'] or k in room['stuck']]
        room.update(plan=list(plan), stars=stars, parts=parts, lost=lost, stage='teach', phase=0)
        _focus(t, (stars - 3) * 12)
        t['status'] = 'in_progress'
        return dict(message=f'Giáo án đã chốt: {stars}/3 sao. Vào tiết thôi!', celebrate=stars == 3)
    if name == 'call':
        need(stage == 'teach', 'Chưa tới phần dạy trên lớp.')
        eid = p.get('event')
        ev = next((x for x in room['events'] if x['id'] == eid), None)
        need(ev and ev['phase'] == room['phase'], 'Chuyện này không xảy ra lúc này.')
        need(eid not in room['calls'], 'Chuyện này đã xử lý xong.')
        opt = next((o for o in INCIDENT[eid]['options'] if o['id'] == p.get('option')), None)
        need(opt, 'Cách xử lý không hợp lệ.')
        room['calls'][eid] = opt['id']
        _focus(t, opt['focus'])
        for kid, d in opt['trust'].items():
            _trust(c, room, kid, d)
        for kid, flag in opt['flag'].items():
            room['flags'][kid] = flag
        if opt['note'] and opt['note'] not in room['notes']:
            room['notes'].append(opt['note'])
        if opt['mistake']:
            t['mistakes'] += 1
        e.metric(c, 'class_moments')
        return dict(message=say(s, opt['text']), correct=not opt['mistake'])
    if name == 'help':
        need(stage == 'teach', 'Giúp các bạn trong lúc dạy trên lớp nhé.')
        kid = p.get('kid')
        need(kid in room['lost'], 'Bạn này đang theo kịp bài.')
        need(kid not in room['helped'], 'Bạn này đã hiểu bài rồi.')
        need(room['flags'].get(kid) != 'miss', 'Bạn này đang không ở trong lớp.')
        method = p.get('method')
        need(method in METHOD_IDS, 'Cách giúp không hợp lệ.')
        if method != KID[kid]['style']:
            t['mistakes'] += 1
            tries = room.setdefault('tries', {})
            tries[kid] = min(9, tries.get(kid, 0) + 1)
            return dict(message=say(s, CLUES[kid][1]), correct=False)
        room['helped'][kid] = method
        kid_row(c, kid)['known'] = True
        _trust(c, room, kid, 1)
        return dict(message=f'{KID[kid]["name"]} gật gù: đã hiểu rồi! Sổ lớp ghi: {STYLE_LABEL[method].lower()}.')
    if name == 'next':
        need(stage == 'teach', 'Chưa tới phần dạy trên lớp.')
        pending = [x['id'] for x in room['events'] if x['phase'] == room['phase'] and x['id'] not in room['calls']]
        need(not pending, 'Còn một chuyện trong lớp cần xử lý trước.')
        room['phase'] += 1
        if room['phase'] < 3:
            return dict(message=f'Sang hoạt động {room["phase"] + 1}: {CARD[room["plan"][room["phase"]]]["name"]}.')
        room['stage'] = 'check'
        room['tickets'] = _tickets(t, room)
        return dict(message='Hết giờ luyện tập. Thu phiếu cuối tiết và phản hồi từng bạn nhé.')
    if name == 'mark':
        need(stage == 'check', 'Chưa tới lúc chấm phiếu cuối tiết.')
        kid = p.get('kid')
        need(kid in room['tickets'], 'Không có phiếu của bạn này.')
        need(kid not in room['marks'], 'Phiếu này đã có phản hồi.')
        mark = p.get('mark')
        need(mark in MARK_IDS, 'Cách phản hồi không hợp lệ.')
        kind = room['tickets'][kid]['kind']
        room['marks'][kid] = mark
        right = mark == MARK_FOR[kind]
        if right:
            _trust(c, room, kid, 1)
        else:
            # The mark stands, as on a real sheet; the parent reads it at home.
            t['mistakes'] += 1
        if len(room['marks']) == len(room['tickets']):
            room['stage'] = 'ready'
            return dict(message='Mọi phiếu đều có lời phản hồi riêng. Khép tiết thôi!')
        if kind == 'slip' and right:
            return dict(message=f'{KID[kid]["name"]} nhìn lại, sửa ngay: hiểu bài rồi, chỉ chép nhầm thôi!')
        return dict(message=f'Đã gửi lời phản hồi cho {KID[kid]["name"]}.')
    if name == 'complete':
        need(stage == 'ready', 'Còn phiếu chưa có phản hồi.')
        need(p.get('confirm') is True, 'Xác nhận khép tiết trước nhé.')
        return _finish(s, c, t, room)
    raise e.GameError('Thao tác tiết học không hợp lệ.')


def _tickets(t: dict, room: dict) -> dict:
    lesson = t['lesson']
    answer = lesson['answer']
    wrongs = [x for x in lesson['choices'] if x != answer]
    out = {}
    for i, kid in enumerate(present_ids(room)):
        flag = room['flags'].get(kid)
        note = TICKET_NOTES[(i + t['day']) % len(TICKET_NOTES)]
        if flag == 'miss' or (kid in room['lost'] and kid not in room['helped']):
            kind, value = 'wrong', wrongs[i % len(wrongs)]
        elif kid == room['slip']:
            kind, value = 'slip', wrongs[(i + 1) % len(wrongs)]
        else:
            kind, value = 'right', answer
        out[kid] = dict(kind=kind, answer=value, note=note)
    if 'vy' in out and room['flags'].get('vy') == 'copy':
        src = out.get('linh') or dict(answer=out['vy']['answer'])
        out['vy'] = dict(kind='copy', answer=src['answer'], note='Giống hệt phiếu của Linh, cả chỗ gạch xóa.')
    return out


def understood(room: dict) -> tuple[int, int]:
    tickets = room['tickets']
    return sum(1 for x in tickets.values() if x['kind'] in ('right', 'slip')), len(tickets)


def reward_for(t: dict, room: dict) -> int:
    got, total = understood(room)
    return 45 + 5 * room['stars'] + (round(10 * got / total) if total else 0) + (5 if t.get('patience', 100) >= 80 else 0)


def _post(s: dict, c: dict, kid: str | None, author: str, text: str, ref: str) -> None:
    from . import engine as e
    npc = COLLEAGUE_NPC if kid is None else CARRIER.get(kid, PARENT_NPC)
    post = e.add_feed(s, c, npc, say(s, text), ref, kind='post')
    if kid is not None:
        post['author'] = author


# What a parent tells the school when the period went wrong for their child:
# (code, severity, text, note, safety). "cô/thầy" becomes the player's title once known.
ROLL_SLIPS = {
    ('sick', 'present'): ('roll_sick', 1, 'Bé {name} ốm nghỉ ở nhà, mẹ đã nhắn xin phép mà sổ lớp vẫn ghi có mặt.', 'điểm danh sai bạn nghỉ ốm', False),
    ('late', 'outside'): ('roll_outside', 2, 'Bé {name} đi trễ vì xe hỏng mà bị bắt đứng ngoài cửa, lỡ cả phần đầu bài.', 'bắt học sinh đứng ngoài lớp', False),
    ('missing', 'mark'): ('roll_missing', 3, 'Bé {name} không tới lớp mà cả buổi không ai gọi báo nhà, lỡ có chuyện gì thì sao.', 'không báo khi học sinh vắng không rõ lý do', True),
}
CALL_SLIPS = {
    ('copy', 'name'): ('shamed', 1, 'Bé Vy bị nêu tên trước cả lớp, về nhà khóc cả tối.', 'nêu tên học sinh trước lớp'),
    ('push', 'punish'): ('punish', 1, 'Bé Tú bị bạn xô mà lại bị phạt đứng cùng bạn.', 'phạt cả bạn bị xô'),
    ('accent', 'laugh'): ('mock', 2, 'Các bạn nhại giọng quê của bé Tú, vậy mà cô/thầy còn cười theo.', 'cười theo khi học sinh bị trêu'),
    ('tears', 'scold'): ('scold', 1, 'Bé Linh sai một câu bật khóc thì bị chê “có vậy mà cũng khóc”.', 'chê học sinh khi con khóc'),
    ('bee', 'swat'): ('bee', 2, 'Cô/thầy cầm sách đập ong, ong bay loạn, suýt nữa một bạn bị đốt.', 'đập ong giữa lớp'),
    ('toilet', 'deny'): ('toilet', 2, 'Bé An đau bụng xin ra ngoài mà không được cho đi, ngồi co ro cả tiết.', 'không cho học sinh đau bụng ra ngoài'),
    ('visit', 'stars'): ('visit', 1, 'Hôm có dự giờ, các bạn học chậm chỉ ngồi im cả buổi.', 'chỉ gọi bạn học nhanh'),
    ('visit', 'show'): ('visit', 1, 'Hôm có dự giờ lớp chỉ chơi, về nhà con chẳng nói được hôm nay học gì.', 'bỏ mục tiêu bài học'),
    ('leak', 'stay'): ('leak', 1, 'Mái dột ướt hết vở mà bé An, bé Tú vẫn phải ngồi yên chỗ đó.', 'để học sinh ngồi chỗ dột'),
}


def judge(s: dict, t: dict, room: dict) -> None:
    """At the end of the period: record what the parents will complain about."""
    from . import consequences as cq
    from .feedback import teacher_title
    add = lambda code, sev, text, note, safety=False: cq.slip(t, code, sev, teacher_title(s, text), note, safety)
    status = {k['id']: k['status'] for k in room['kids']}
    for kid, choice in room['roll'].items():
        row = ROLL_SLIPS.get((status[kid], choice))
        if row:
            add(row[0], row[1], row[2].format(name=KID[kid]['name']), row[3], row[4])
    for kid, mark in room['marks'].items():
        kind = room['tickets'][kid]['kind']
        name = KID[kid]['name']
        if mark == MARK_FOR[kind]:
            continue
        if mark == 'praise' and kind in ('wrong', 'slip'):
            add('grade_praise', 2, f'Bài của bé {name} sai mà vẫn được khen đúng, về nhà con cứ tưởng mình hiểu bài rồi.', 'chấm bài sai thành đúng')
        elif mark == 'private' and kind != 'copy':
            add('grade_private', 2, f'Bé {name} tự làm bài mà bị gọi gặp riêng như thể chép bài của bạn.', 'nghi oan học sinh chép bài')
        elif kind == 'copy':
            add('grade_copy', 1, f'Phiếu của bé {name} chép y bài bạn mà vẫn được chấm như thường, chẳng ai hỏi han.', 'bỏ qua phiếu chép bài')
        else:
            add('grade_hint', 1, f'Bé {name} làm đúng mà bị bảo làm lại, con buồn cả tối.', 'chấm bài đúng thành sai')
    for key, opt in room['calls'].items():
        row = CALL_SLIPS.get((key, opt))
        if row:
            add(*row)
    left = [k for k in room['lost'] if k not in room['helped'] and room['flags'].get(k) != 'miss']
    if left:
        add('unhelped', 2 if len(left) >= 2 else 1, f'Bé {KID[left[0]]["name"]} không theo kịp bài mà cả tiết chẳng ai kèm.', 'để học sinh chậm tự xoay xở')
    tries = room.get('tries') or {}
    slow = max(tries, key=lambda k: (tries[k], k), default=None)
    if slow and tries[slow] >= 2:
        add('method', 1, f'Bé {KID[slow]["name"]} bảo cô/thầy phải đổi mấy cách giảng con mới hiểu, mất cả phần luyện tập.', 'giảng chưa hợp cách học của con')
    if cq.slips(t) and t['mistakes'] == 0:
        t['mistakes'] = 1


def _finish(s: dict, c: dict, t: dict, room: dict) -> dict:
    from . import engine as e
    from . import consequences as cq
    reward = reward_for(t, room)
    room['reward'] = reward
    present = set(present_ids(room))
    # Keep the v1 fields meaningful for the shared review criteria.
    t['attendance'] = {st['id']: st['id'] in present and bool(st.get('present', True)) for st in t['students']}
    t['feedback'] = {st['id']: ('specific' if room['marks'].get(st['id']) == 'praise' else 'retry' if room['marks'].get(st['id']) == 'hint' else 'encourage') for st in t['students']}
    got, total = understood(room)
    e.metric(c, 'class_periods')
    judge(s, t, room)
    r = cq.react(s, c, t, reward, who='Phụ huynh')
    e.task_done(s, c, t, r['pay'], f'Tiết {t["lesson"]["title"].lower()}: {got}/{total} bạn hiểu bài.')
    for key in room['notes'][:2]:
        kid, author, text = NOTES[key]
        _post(s, c, kid, author, text, t['id'] + ':' + key)
    for tag in room['arcs'][:2]:
        kid, beat = tag.split(':')
        line, parent = ARCS[kid][int(beat) - 1]
        _post(s, c, kid, KID[kid]['guardian'], parent, f'{t["id"]}:arc:{tag}')
        e.remember(s, c, CARRIER.get(kid, PARENT_NPC), line, t['id'])
    msg = f'Khép tiết: {got}/{total} bạn hiểu bài · +{r["pay"]} xu.'
    if cq.slips(t):
        msg += ' ' + parent_reaction(s, t, r)
    return dict(message=msg, celebrate=got == total and not cq.slips(t))


# A parent does not "pay less": they take it to the school, and the school docks the period's pay.
PARENT_SAYS = dict(
    accept='Lần sau cô/thầy để ý giúp con nhé.',
    grumble='Tôi mong chuyện này đừng lặp lại.',
    discount='Tôi đã báo với nhà trường.',
    refund='Tôi đã báo với nhà trường, mong có câu trả lời rõ ràng.',
    walkout='Tôi đã làm đơn gửi nhà trường.',
    refuse='Chuyện an toàn của con không đùa được, tôi sẽ làm việc với nhà trường.',
)


def parent_reaction(s: dict, t: dict, r: dict) -> str:
    from . import consequences as cq
    from .feedback import teacher_title
    worst = max(cq.slips(t), key=lambda x: x['sev'])
    line = teacher_title(s, f'{worst["text"]} {PARENT_SAYS.get(r["kind"], PARENT_SAYS["grumble"])}')
    if isinstance(t.get('reaction'), dict):
        t['reaction']['line'] = line[:300]
    out = f'Phụ huynh: “{line}”'
    if r['cut']:
        out += f' Nhà trường trừ {r["cut"]} xu thù lao tiết này.'
    if '📣' in r['message']:
        out += ' 📣 Phụ huynh gửi phản ánh lên nhà trường.'
    if 'kiểm tra' in r['message']:
        out += ' Nhà trường sẽ kiểm tra lại chuyện này.'
    return out


# ------------------------------------------------------------------ projection
def _event_view(room: dict, ev: dict) -> dict:
    inc = INCIDENT[ev['id']]
    out = dict(id=inc['id'], emoji=inc['emoji'], title=inc['title'], text=inc['text'], phase=ev['phase'],
               options=[dict(id=o['id'], label=o['label']) for o in inc['options']])
    chosen = room['calls'].get(ev['id'])
    if chosen:
        o = next(x for x in inc['options'] if x['id'] == chosen)
        out.update(chosen=chosen, outcome=o['text'], focus=o['focus'], mistake=o['mistake'],
                   trust=[dict(kid=k, name=KID[k]['name'], delta=d) for k, d in o['trust'].items()])
    return out


def public(t: dict) -> dict:
    room = copy.deepcopy(t['room']) if 'room' in t else fresh(t['day'], slot_of(t))
    stage = room['stage']
    cond = COND[room['cond']]
    kids = []
    for k in room['kids']:
        info = ROLL[k['status']]
        kids.append(dict(id=k['id'], name=KID[k['id']]['name'], emoji=KID[k['id']]['emoji'], trait=KID[k['id']]['trait'],
                         status=k['status'], clue=info['clue'], mark_emoji=info['emoji'], options=info['options'], done=room['roll'].get(k['id'])))
    shown = [_event_view(room, ev) for ev in room['events'] if stage == 'teach' and ev['phase'] == room['phase']]
    lost = []
    if stage in ('teach', 'check', 'ready'):
        for kid in room['lost']:
            lost.append(dict(id=kid, name=KID[kid]['name'], emoji=KID[kid]['emoji'], clue=CLUES[kid][0],
                             helped=kid in room['helped'], away=room['flags'].get(kid) == 'miss'))
    tickets = [dict(kid=k, name=KID[k]['name'], emoji=KID[k]['emoji'], answer=v['answer'], note=v['note'], mark=room['marks'].get(k))
               for k, v in room['tickets'].items()]
    view = dict(v=2, tier=room['tier'], stage=stage, stages=list(STAGES),
                cond=dict(id=cond['id'], emoji=cond['emoji'], text=cond['text'], tip=cond['tip']),
                kids=kids, hand=[dict(CARD[i], styles=list(CARD[i]['styles'])) for i in room['hand']], plan=room['plan'],
                minutes=_minutes(room['plan']) if room['plan'] else 0, limit=PLAN_MINUTES, min=PLAN_MIN, stars=room['stars'],
                parts=room['parts'], phase=room['phase'], events=shown,
                pending=[x['id'] for x in shown if 'chosen' not in x], lost=lost, tickets=tickets,
                marks=MARKS, methods=METHODS, reward=room['reward'] or None,
                log=[_event_view(room, ev) for ev in room['events'] if ev['id'] in room['calls']])
    if stage in ('check', 'ready'):
        got, total = understood(room)
        view.update(understood=got, of=total, estimate=reward_for(t, room) if stage == 'ready' else None)
    return view


def content() -> dict:
    return dict(kids=[{k: v for k, v in x.items() if k != 'style'} for x in KIDS], methods=METHODS, styles=STYLE_LABEL,
                energy={k: dict(emoji=v[0], label=v[1]) for k, v in ENERGY.items()},
                arcs={k: [line for line, _ in v] for k, v in ARCS.items()})


# ------------------------------------------------------------------ validation
def validate(t: dict) -> None:
    from .engine import need, integer
    room = t['room']
    need(isinstance(room, dict), 'Tiết học không hợp lệ.')
    keys = set(FIXED) | {'stage', 'roll', 'plan', 'stars', 'parts', 'lost', 'phase', 'calls', 'helped', 'flags', 'tickets', 'marks', 'notes', 'arcs', 'reward'}
    need(set(room) - {'tries'} == keys, 'Dữ liệu tiết học thiếu hoặc lạ.')
    tries = room.get('tries', {})
    need(isinstance(tries, dict) and all(k in KID and type(v) is int and 1 <= v <= 9 for k, v in tries.items()), 'Số lần đổi cách giảng không hợp lệ.')
    base = roll(t['day'], slot_of(t))
    for k in FIXED:
        need(room[k] == base[k], 'Dữ kiện gốc của tiết học bị thay đổi: ' + k)
    need(room['stage'] in STAGES, 'Bước tiết học không hợp lệ.')
    ids = [k['id'] for k in room['kids']]
    status = {k['id']: k['status'] for k in room['kids']}
    present = present_ids(room)
    need(isinstance(room['roll'], dict) and all(k in ids and v in [o['id'] for o in ROLL[status[k]]['options']] for k, v in room['roll'].items()), 'Điểm danh không hợp lệ.')
    need(isinstance(room['plan'], list) and len(room['plan']) in (0, 3) and len(set(room['plan'])) == len(room['plan']) and all(x in room['hand'] for x in room['plan']), 'Giáo án không hợp lệ.')
    integer(room['stars'], 0, 3)
    integer(room['phase'], 0, 3)
    integer(room['reward'], 0, 200)
    order = STAGES.index(room['stage'])
    if order >= 1:
        need(len(room['roll']) == len(room['kids']), 'Điểm danh chưa xong.')
    if order >= 2:
        need(len(room['plan']) == 3 and plan_error(room['plan']) is None, 'Giáo án chưa chốt.')
        stars, parts = _stars(room['plan'], room['cond'], need_styles(room))
        need(room['stars'] == stars and room['parts'] == parts, 'Điểm giáo án không khớp.')
        need(room['lost'] == [k for k in present if KID[k]['style'] in parts['missing'] or k in room['stuck']], 'Danh sách cần giúp không khớp.')
    else:
        need(not room['plan'] and room['stars'] == 0 and room['parts'] == {} and room['lost'] == [] and room['phase'] == 0, 'Giáo án chưa được chốt.')
    events = {x['id']: x for x in room['events']}
    need(isinstance(room['calls'], dict) and all(k in events and v in [o['id'] for o in INCIDENT[k]['options']] for k, v in room['calls'].items()), 'Cách xử lý không hợp lệ.')
    if room['stage'] == 'teach':
        need(all(events[k]['phase'] <= room['phase'] for k in room['calls']), 'Chuyện trong lớp chưa xảy ra.')
    if order >= 3:
        need(room['phase'] == 3 and len(room['calls']) == len(room['events']), 'Tiết học chưa dạy xong.')
    need(isinstance(room['helped'], dict) and all(k in room['lost'] and v == KID[k]['style'] for k, v in room['helped'].items()), 'Hỗ trợ học sinh không hợp lệ.')
    need(isinstance(room['flags'], dict) and all(k in present and v in ('copy', 'miss') for k, v in room['flags'].items()), 'Ghi chú học sinh không hợp lệ.')
    need(isinstance(room['tickets'], dict), 'Phiếu cuối tiết không hợp lệ.')
    if order >= 3:
        need(room['tickets'] == _tickets(t, room), 'Phiếu cuối tiết không khớp.')
    else:
        need(room['tickets'] == {} and room['marks'] == {}, 'Chưa tới lúc thu phiếu.')
    need(isinstance(room['marks'], dict) and all(k in room['tickets'] and v in MARK_IDS for k, v in room['marks'].items()), 'Phản hồi phiếu không hợp lệ.')
    if room['stage'] == 'ready':
        need(len(room['marks']) == len(room['tickets']), 'Còn phiếu chưa phản hồi.')
    need(isinstance(room['notes'], list) and len(room['notes']) <= 8 and all(n in NOTES for n in room['notes']), 'Lời nhắn phụ huynh không hợp lệ.')
    need(isinstance(room['arcs'], list) and len(room['arcs']) <= 30, 'Câu chuyện học sinh không hợp lệ.')
    for tag in room['arcs']:
        need(isinstance(tag, str) and tag.count(':') == 1 and tag.split(':')[0] in KID and tag.split(':')[1] in ('1', '2', '3'), 'Câu chuyện học sinh không hợp lệ.')


def validate_kids(d: dict) -> None:
    from .engine import need, integer
    kids = d.get('kids', {})
    need(isinstance(kids, dict) and all(k in KID for k in kids), 'Sổ lớp không hợp lệ.')
    for row in kids.values():
        need(isinstance(row, dict) and set(row) == {'trust', 'beat', 'known'} and type(row['known']) is bool, 'Sổ lớp không hợp lệ.')
        integer(row['trust'], 0, MAX_TRUST)
        integer(row['beat'], 0, 3)


def notebook(d: dict) -> list[dict]:
    kids = d.get('kids', {}) if isinstance(d, dict) else {}
    out = []
    for k in KIDS:
        row = kids.get(k['id'], dict(trust=0, beat=0, known=False))
        out.append(dict(id=k['id'], name=k['name'], emoji=k['emoji'], trait=k['trait'], trust=row['trust'], beat=row['beat'],
                        style=k['style'] if row['known'] else None, style_label=STYLE_LABEL[k['style']] if row['known'] else None,
                        story=[ARCS[k['id']][i][0] for i in range(row['beat'])],
                        next=(row['beat'] + 1) * 3 if row['beat'] < 3 else None))
    return out


def known_request(t: dict) -> str:
    room = t.get('room') or roll(t['day'], slot_of(t))
    cond = COND[room['cond']]
    return ('Mục tiêu tiết học: ' + t['lesson']['prompt'] + ' Hôm nay: ' + cond['text'].lower() +
            '. Điểm danh, chọn ba hoạt động hợp lớp rồi giúp từng bạn theo cách riêng.')
