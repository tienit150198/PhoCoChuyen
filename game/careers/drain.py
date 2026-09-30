"""Thông cống chú Hai: drain and sewer cleaning callouts (plugin career).

Chú Hai has cleared the neighbourhood's drains for twenty-five years; the player rides out with
his toolkit on the back of the motorbike. What the job is:

* in the morning (``setup`` task) read the day's appointment book and pack the bike: it carries
  five tools out of eight (plunger, hand snake, electric snake, water jetter, inspection camera,
  long grabber, sludge shovel and bucket, gas meter with fan). A tool left at the shop means a
  trip back while the customer waits;
* a callout (``call`` task): the customer describes the symptom. The player finds the cause by
  asking, looking, running water and (with the camera) seeing inside: hair and soap, congealed
  grease, wet wipes, a fallen object, tree roots, a blocked vent pipe, a cracked trap;
* quote before touching anything, from chú Hai's price list for that job. Quoting high is lying,
  quoting low is working for nothing; when the cause turns out bigger, quote again and ask;
* safety gear (gloves, mask, boots, goggles for the jetter) and, at a manhole (``manhole``
  task), the confined-space rules: barrier, gas reading, fan, someone standing by at the top;
* clear it with the right tool (the wrong one wastes time; a stopgap flows today and blocks again),
  or replace the cracked trap; run water to test, clean up, tell the customer how to keep it
  clear, then take the cash (the ward pays manholes by transfer);
* night emergencies (``emergency``: a surcharge that is fair only when said up front) and warranty
  calls (``recall``: yesterday's stopgap is ours to fix for free; a new clog is not);
* surprises on the road and small stories of the regulars;
* the awkward people around the job (0.9.16): the homeowner who stands over you and grumbles (put up
  with it, answer back, ask them to step away, or refuse the job), the "while you're here" free extra
  job, the customer with no cash (wait, trust them, or ask for a deposit), a price the player names
  (overcharging included: some pay, some argue, word spreads in the street, some come back with a
  neighbour for the difference), a debt book to chase or write off, and many more surprises.
  Every one of them decides by itself from hidden traits (street_folk.py): the same move on the
  same job always goes the same way.

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

ID = 'drain'
GEN = 1

BIKE_SLOTS = 5
NIGHT = 150               # % of the list price for a night emergency, when said up front
HIGH, LOW = 180, 60       # the dishonest and the loss-making quote, % of the list price

TOOLS = [
    dict(id='pit_tong', name='Pít-tông cao su', emoji='🪠', note='Hút đẩy chỗ tắc gần miệng: bồn rửa, bồn cầu.'),
    dict(id='lo_xo', name='Dây lò xo tay 5 m', emoji='🌀', note='Móc tóc, cặn xà phòng trong đoạn ống ngắn.'),
    dict(id='may_lo_xo', name='Máy lò xo điện 15 m', emoji='⚙️', note='Đường ống dài, giấy vón cục, rễ cây.'),
    dict(id='may_phun', name='Máy phun áp lực', emoji='💦', note='Rửa trôi mỡ đông, bùn đặc bám thành ống.'),
    dict(id='camera', name='Camera nội soi', emoji='📹', note='Nhìn tận chỗ tắc, biết chắc nguyên nhân.'),
    dict(id='moc', name='Móc gắp dài', emoji='🪝', note='Gắp đồ rơi, tổ chim trong ống thông hơi.'),
    dict(id='gau', name='Xẻng, xô, gầu múc bùn', emoji='🪣', note='Múc bùn, rác lắng dưới hố ga.'),
    dict(id='do_khi', name='Máy đo khí, quạt thông gió', emoji='🌬️', note='Bắt buộc trước khi xuống hố ga.'),
]
TOOL = {x['id']: x for x in TOOLS}

PLACES = {
    'bon_rua': dict(name='Bồn rửa bát', emoji='🍽️', price=15), 'lavabo': dict(name='Lavabo rửa mặt', emoji='🚰', price=12),
    'thoat_san': dict(name='Thoát sàn nhà tắm', emoji='🚿', price=12), 'bon_cau': dict(name='Bồn cầu', emoji='🚽', price=20),
    'ong_chinh': dict(name='Ống thoát chính', emoji='🕳️', price=35), 'ho_ga': dict(name='Hố ga ngõ', emoji='⚫', price=45),
    'mai': dict(name='Ống thông hơi trên mái', emoji='🏠', price=18),
}
# cause: name, tools that clear it, tools that only get it flowing for now, what the camera shows, extra on the price
CAUSES = {
    'toc': dict(name='Tóc, cặn xà phòng', fix=('lo_xo',), temp=('pit_tong',), extra=0,
                camera='Camera thấy một búi tóc quấn cặn xà phòng trắng đục, cách miệng ống một gang tay.'),
    'mo': dict(name='Mỡ đông bám ống', fix=('may_phun',), temp=('lo_xo', 'may_lo_xo'), extra=10,
               camera='Thành ống phủ một lớp mỡ vàng đặc quánh, lòng ống chỉ còn bằng ngón tay.'),
    'giay': dict(name='Giấy ướt, băng vệ sinh', fix=('may_lo_xo', 'pit_tong'), temp=('lo_xo',), extra=0,
                 camera='Một cục giấy ướt, băng vệ sinh vón lại chặn ngay khúc cua đầu tiên.'),
    'vat': dict(name='Đồ vật rơi vào ống', fix=('moc',), temp=(), extra=0,
                camera='Một món đồ chơi nhựa màu đỏ kẹt ngang ống.'),
    're': dict(name='Rễ cây đâm vào ống', fix=('may_lo_xo',), temp=(), extra=15,
               camera='Rễ cây như bộ râu chui qua mối nối, đan kín lòng ống.'),
    'bun': dict(name='Bùn, rác lắng trong hố ga', fix=('gau',), temp=('may_phun',), extra=0,
                camera='Đáy hố ga đầy bùn đen, túi ni-lông, lá cây, nước không thoát được.'),
    'thong_hoi': dict(name='Ống thông hơi bị tắc', fix=('moc',), temp=(), extra=0,
                      camera='Trong ống thoát không có gì tắc. Nước chảy chậm vì thiếu hơi.'),
    'xi_phong': dict(name='Ống xi-phông nứt, lỏng', fix=(), temp=(), extra=0, part=True,
                     camera='Ống xi-phông dưới bồn nứt một đường, gioăng mục, nước rỉ ra ngoài.'),
}
HOWS = ('hoi', 'nhin', 'xa', 'camera')
HOW_LABEL = {'hoi': 'Hỏi thêm', 'nhin': 'Mở nắp, soi đèn', 'xa': 'Xả nước thử', 'camera': 'Soi camera'}
GEAR = ('gang_tay', 'khau_trang', 'ung', 'kinh')
GEAR_LABEL = {'gang_tay': 'Găng tay', 'khau_trang': 'Khẩu trang', 'ung': 'Ủng', 'kinh': 'Kính bảo hộ'}
SAFETY = ('rao', 'khi', 'quat', 'canh')
SAFETY_LABEL = {'rao': 'Đặt rào chắn, biển báo', 'khi': 'Đo khí độc dưới hố', 'quat': 'Bật quạt thông gió 10 phút', 'canh': 'Người canh trên miệng hố'}
ADVICE = {'toc': 'Gắn lưới chặn tóc ở thoát sàn, tuần xả nước nóng một lần.', 'mo': 'Đừng đổ dầu mỡ xuống bồn, lau chảo bằng giấy trước khi rửa.',
          'giay': 'Giấy ướt, băng vệ sinh bỏ thùng rác, đừng thả bồn cầu.', 'vat': 'Đậy nắp bồn cầu, để đồ chơi của bé xa nhà tắm.',
          're': 'Gốc cây sát đường ống nên chặn rễ; ống cũ nên thay đoạn nứt.', 'bun': 'Nhắc cả ngõ đừng quét rác xuống hố ga.',
          'thong_hoi': 'Ống thông hơi trên mái nên có chụp lưới chống chim làm tổ.', 'xi_phong': 'Xi-phông nhựa mới, thỉnh thoảng siết lại khớp nối.'}

ITEMS = [
    dict(id='xi_phong', name='Ống xi-phông nhựa', emoji='🔧', group='part', unit='cái', cost=6, life=365, start=3),
    dict(id='bot', name='Bột thông cống (xút)', emoji='🧪', group='chem', unit='gói', cost=2, life=365, start=4),
    dict(id='gang_tay', name='Găng tay cao su', emoji='🧤', group='gear', unit='đôi', cost=2, life=90, start=6),
]

PEOPLE = [
    ('Chú Hai', 'Thợ thông cống lâu năm', 'Hai mươi lăm năm thông cống cả phường, nhìn vết nước là đoán ra bệnh.', 'warm'),
    ('Chị Hồng', 'Chủ quán bún bò', 'Bếp nấu từ ba giờ sáng, bồn rửa ngập mỡ là cả quán đứng hình.', 'picky'),
    ('Bà Ngọc', 'Nhà phố cổ ống gang', 'Nhà xây từ thời Pháp, ống gang cũ, tiếc từng đồng.', 'sour'),
    ('Anh Phong', 'Chủ nhà trọ mười hai phòng', 'Muốn làm nhanh, rẻ, hay mặc cả.', 'bossy'),
    ('Chị Mai', 'Mẹ của bé Bin ba tuổi', 'Bé Bin hay thả đồ chơi vào đủ chỗ trong nhà.', 'quiet'),
    ('Ông Lộc', 'Tổ trưởng dân phố', 'Lo chuyện ngập úng của cả ngõ, gọi thợ bằng tiền quỹ phường.', 'bossy'),
    ('Hùng', 'Sinh viên ở trọ', 'Lần đầu gặp cảnh bồn cầu trào, cuống cuồng gọi điện.', 'genz'),
    ('Cô Diệp', 'Chủ tiệm làm tóc', 'Gội đầu cả ngày, thoát sàn tiệm lúc nào cũng đầy tóc.', 'picky'),
]

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Việc đều tay: bồn rửa, thoát sàn, bồn cầu.', weight=3),
    dict(id='rain', emoji='⛈️', label='Mưa lớn', hint='Hố ga ngõ dễ tràn: mang gầu, máy đo khí, ủng.', min_day=2, weight=2),
    dict(id='feast', emoji='🍲', label='Sau đám tiệc', hint='Quán xá rửa nhiều dầu mỡ: máy phun áp lực đắt việc.', min_day=2, weight=2),
    dict(id='dry', emoji='🌵', label='Hanh khô', hint='Cây tìm nước, rễ đâm vào ống: máy lò xo điện.', min_day=3, weight=1),
]
MOD = {m['id']: m for m in MODS}

# (npc, kind, place, cause, title, opening, clues {hoi, nhin, xa}, old pipe, min_day, mod)
CALLS = [
    (7, 'call', 'thoat_san', 'toc', 'Thoát sàn tiệm tóc', 'Thoát sàn chỗ gội đầu nước đọng lênh láng, khách đứng ướt cả chân!',
     dict(hoi='Cô Diệp: “Ngày gội cả chục đầu, lưới chặn tóc gãy từ tuần trước.”', nhin='Mở nắp thoát sàn: lổn nhổn tóc quấn cặn trắng.',
          xa='Đổ một xô nước: rút chậm, sủi bọt xà phòng.'), False, 1, None),
    (1, 'call', 'bon_rua', 'mo', 'Bồn rửa quán bún bò', 'Bồn rửa bát tắc từ sáng, nước mỡ ngập lênh láng. Quán sắp bán trưa rồi!',
     dict(hoi='Chị Hồng: “Nồi nước lèo xong là rửa luôn, dầu mỡ chảy hết xuống bồn.”', nhin='Miệng ống có mảng mỡ trắng đông cứng, mùi ôi.',
          xa='Xả nước nóng: rút được một chút rồi lại đứng.'), False, 1, None),
    (6, 'call', 'bon_cau', 'giay', 'Bồn cầu phòng trọ', 'Anh ơi bồn cầu trào lên rồi, em không biết làm sao hết!',
     dict(hoi='Hùng: “Em lỡ thả cả gói giấy ướt lau mặt xuống bồn.”', nhin='Mực nước trong bồn dâng cao, lờ mờ thấy giấy trắng.',
          xa='Giật nước: nước dâng lên sát miệng bồn, không rút.'), False, 1, None),
    (4, 'call', 'bon_cau', 'vat', 'Bé Bin thả đồ chơi', 'Bồn cầu nhà chị cứ giật là nước rút chậm, hình như bé Bin thả gì vào…',
     dict(hoi='Chị Mai: “Mất con khủng long nhựa đỏ từ hôm qua, bé chỉ vào nhà tắm.”', nhin='Nhìn vào lòng bồn không thấy gì lạ.',
          xa='Giật nước: nước xoáy chậm, nghe tiếng lọc cọc.'), False, 2, None),
    (2, 'call', 'ong_chinh', 're', 'Ống thoát nhà phố cổ', 'Cả nhà dưới tầng trệt nước rút ì ạch, tầng hai xả là tầng một trào!',
     dict(hoi='Bà Ngọc: “Cây bàng trước nhà to lắm rồi, ống gang từ đời ông bà.”', nhin='Hố kiểm tra sân trước có vài sợi rễ trắng mảnh.',
          xa='Xả nước ở tầng hai: tầng một sủi lên ùng ục.'), True, 2, None),
    (3, 'call', 'lavabo', 'xi_phong', 'Lavabo nhà trọ rỉ nước', 'Lavabo phòng số 6 chậu nước rút chậm, sàn lúc nào cũng ướt, lại có mùi.',
     dict(hoi='Anh Phong: “Khách trọ bảo sáng nào cũng thấy vũng nước dưới chân.”', nhin='Soi đèn dưới gầm lavabo: ống cong chữ U có vết nứt, nhỏ giọt.',
          xa='Xả nước: nước rút được nhưng rỉ ra dưới gầm.'), False, 2, None),
    (2, 'call', 'bon_rua', 'thong_hoi', 'Bồn rửa ọc ọc', 'Bồn rửa nhà bà cứ kêu ọc ọc, nước rút chậm, thợ khác thông rồi vẫn thế.',
     dict(hoi='Bà Ngọc: “Thợ trước đổ cả gói bột thông cống, mà vẫn thế.”', nhin='Miệng ống sạch, không thấy cặn.',
          xa='Xả nước: sủi bọt, ọc ọc, bồn cầu bên cạnh cũng rung nước.'), True, 3, None),
    (1, 'call', 'bon_rua', 'mo', 'Quán bún sau đám cỗ', 'Đêm qua nấu cỗ ba trăm suất, sáng nay cả dãy bồn rửa đứng nước!',
     dict(hoi='Chị Hồng: “Rửa mấy chục nồi mỡ, chị quên chặn lưới.”', nhin='Hố tách mỡ đầy ứ, mỡ tràn sang ống.',
          xa='Nước nóng cũng không rút.'), False, 2, 'feast'),
    (3, 'call', 'ong_chinh', 'giay', 'Nhà trọ tắc ống chung', 'Cả dãy phòng trọ tầng trệt trào ngược, khách trọ đòi trả phòng!',
     dict(hoi='Anh Phong: “Mười hai phòng dùng chung một đường ống, ai cũng thả giấy.”', nhin='Hố kiểm tra đầy giấy vón.',
          xa='Xả nước phòng cuối dãy: nước dâng ở phòng đầu.'), False, 3, None),
    (2, 'call', 'ong_chinh', 're', 'Rễ cây mùa khô', 'Mùa khô mà ống thoát nhà bà lại tắc, lạ thật.',
     dict(hoi='Bà Ngọc: “Năm nào tầm này cũng thế.”', nhin='Hố kiểm tra có rễ cây mọc thành chùm.', xa='Nước rút rất chậm.'), True, 3, 'dry'),
    (5, 'manhole', 'ho_ga', 'bun', 'Hố ga đầu ngõ tràn', 'Mưa có tí mà hố ga đầu ngõ tràn lên đường, rác nổi lềnh bềnh. Phường nhờ tổ thợ xử lý.',
     dict(hoi='Ông Lộc: “Cả năm chưa ai nạo vét hố ga này.”', nhin='Nắp hố ga nhấc lên: bùn đen gần miệng, mùi trứng thối xộc lên.',
          xa='Đổ nước vào hố: nước đứng im.'), False, 2, None),
    (5, 'manhole', 'ho_ga', 'bun', 'Hố ga ngập sau mưa', 'Mưa lớn quá, hố ga trước chợ ngập tới bắp chân, xe máy chết máy hàng loạt!',
     dict(hoi='Ông Lộc: “Nước từ ba ngõ dồn về đây.”', nhin='Miệng hố ga đầy túi ni-lông và lá.', xa='Nước không rút.'), False, 2, 'rain'),
    (6, 'emergency', 'bon_cau', 'giay', 'Nửa đêm bồn cầu trào', 'Mười một giờ đêm, bồn cầu trào ra cả phòng, cứu em với!',
     dict(hoi='Hùng: “Bạn cùng phòng thả băng vệ sinh xuống bồn.”', nhin='Nước bẩn tràn ra sàn.', xa='Không dám giật nước nữa.'), False, 3, None),
    (1, 'emergency', 'bon_rua', 'mo', 'Bếp quán bún đứng nước', 'Bốn giờ sáng, nồi nước lèo sắp xong mà bồn rửa ngập, không rửa được gì!',
     dict(hoi='Chị Hồng: “Hôm qua đổ nguyên chảo mỡ hành xuống bồn.”', nhin='Mỡ đông trắng xóa ở miệng ống.', xa='Không rút.'), False, 4, None),
]
RECALLS = [
    dict(npc=1, place='bon_rua', cause='mo', fault='shop', title='Chị Hồng gọi lại', opening='Hôm kia thông bằng dây lò xo xong, giờ bồn rửa lại tắc y như cũ!',
         clue='Sổ của chú Hai ghi: hôm đó chỉ thông tạm bằng dây lò xo, chưa phun rửa mỡ.'),
    dict(npc=3, place='bon_cau', cause='giay', fault='new', title='Anh Phong gọi bảo hành', opening='Tuần trước thợ tiệm thông bồn cầu phòng 3 rồi, giờ tắc lại. Bảo hành đi!',
         clue='Bồn cầu phòng 3 tắc vì khách trọ mới thả cả cuộn giấy ướt sáng nay.'),
]
KINDS = ('setup', 'call', 'manhole', 'emergency', 'recall')
STAGES = ('prep', 'work', 'pay', 'done')
LEVELS = ('list', 'high', 'low', 'warranty', 'own')   # own: a price the player names (cg_price)

REG_STORY = {
    1: ('Chị Hồng: “Bếp đứng nước là chị đứng tim luôn á.”', 'Chị Hồng lắp thêm hố tách mỡ theo lời dặn.', 'Chị Hồng mời cả tiệm tô bún bò đặc biệt.'),
    2: ('Bà Ngọc: “Nhà này ông bà để lại, ống gang to như cột đình.”', 'Bà Ngọc kể ngày xưa phố ngập tới đầu gối.',
        'Bà Ngọc bảo chỉ tin thợ nói thật như tiệm mình.'),
    3: ('Anh Phong: “Làm nhanh giúp anh, khách trọ kêu quá.”', 'Anh Phong dán giấy “Không thả giấy ướt” ở mọi phòng.',
        'Anh Phong giới thiệu tiệm cho cả hội chủ nhà trọ.'),
    4: ('Chị Mai: “Bé Bin nhà chị nghịch lắm.”', 'Bé Bin vẫy tay chào “chú thợ thông cống” mỗi lần gặp.', 'Chị Mai gửi hộp bánh bé tự nặn.'),
    5: ('Ông Lộc: “Hố ga sạch thì mưa không sợ.”', 'Ông Lộc xin phường lịch nạo vét hố ga hằng quý.', 'Ông Lộc khen tổ thợ trong buổi họp tổ dân phố.'),
    6: ('Hùng: “Em ở trọ năm đầu, chưa biết gì hết.”', 'Hùng học được cách tự dùng pít-tông.', 'Hùng rủ bạn cùng phòng đọc giấy dặn dò của thợ.'),
    7: ('Cô Diệp: “Tiệm tóc mà, tóc rụng như rơm.”', 'Cô Diệp thay lưới chặn tóc inox.', 'Cô Diệp giảm giá gội đầu cho cả tiệm thợ.'),
}

INTRO = dict(
    title='Giới thiệu nghề: thợ thông cống',
    lead='Một chiếc xe máy chở hộp đồ nghề, dây lò xo cuộn tròn và cái máy phun áp lực. Chú Hai thông cống cả phường hai mươi lăm năm; bạn theo chú học nghề.',
    work=[('📒', 'Đọc sổ hẹn, xếp đồ nghề lên xe (tối đa 5 món)'), ('👂', 'Hỏi, nhìn, xả nước thử để đoán nguyên nhân'),
          ('📹', 'Soi camera khi chưa chắc'), ('🧾', 'Báo giá theo bảng giá trước khi làm'), ('🧤', 'Găng tay, khẩu trang, ủng, kính khi phun'),
          ('🪠', 'Chọn đúng đồ nghề: pít-tông, lò xo, máy phun, móc gắp'), ('⚫', 'Hố ga: rào chắn, đo khí, thông gió, có người canh'),
          ('💧', 'Xả nước thử, dọn sạch, dặn khách giữ ống thông')],
    meet=[('🍲', 'Chị Hồng: quán bún, bồn rửa ngập mỡ'), ('🏚️', 'Bà Ngọc: ống gang cũ, rễ cây'), ('🏠', 'Anh Phong: nhà trọ, muốn rẻ'),
          ('🧸', 'Chị Mai: bé Bin thả đồ chơi'), ('⚫', 'Ông Lộc: hố ga của cả ngõ'), ('🎓', 'Hùng: sinh viên, bồn cầu trào lúc nửa đêm'),
          ('💇', 'Cô Diệp: thoát sàn đầy tóc'), ('⛈️', 'Mưa ngập, thợ dạo nói thách, ống cũ nứt')],
    stars=[('🔍', 'Đoán đúng nguyên nhân'), ('🧾', 'Báo giá thật, trước khi làm'), ('🧰', 'Đúng đồ nghề, không đổ hóa chất bừa'),
           ('🦺', 'Đồ bảo hộ, an toàn hố ga'), ('💧', 'Xả thử, dọn sạch chỗ làm'), ('🙏', 'Bảo hành lỗi của mình')],
)

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='rat', title='Chuột chui ra từ cống', emoji='🐀', npc=4, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Vừa mở nắp cống, một con chuột to phóng ra, chạy thẳng vào bếp nhà khách. Chị chủ nhà hét lên.',
         options=[dict(id='calm', label='Bình tĩnh đóng cửa bếp, đuổi chuột ra ngoài, đậy nắp cống', hint='', effects=dict(xp=4, patience=-2), good=True,
                       outcome='Chuột chạy ra ngõ. Bạn đậy lưới chắn ở miệng cống, dặn khách thay nắp có lưới.'),
                  dict(id='chase', label='Cầm chổi rượt khắp nhà', hint='', effects=dict(patience=-6), good=None,
                       outcome='Rượt một hồi đổ cả chồng bát. Con chuột chui gầm tủ lạnh mất.'),
                  dict(id='ignore', label='Kệ nó, làm tiếp', hint='', effects=dict(review=[3, 'Chuột chạy vào bếp mà thợ cứ tỉnh bơ.']), good=False,
                       outcome='Tối đó khách gọi điện than chuột lục đồ ăn.')],
         default='ignore'),
    dict(id='quack', title='Thợ dạo báo giá trên trời', emoji='📞', npc=3, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Anh Phong đưa điện thoại: “Thằng thợ dán số trên cột điện báo 150 xu mới thông bồn cầu, còn bảo phải đục nền. Thật không em?”',
         options=[dict(id='truth', label='Nói thật bảng giá của tiệm, giải thích không cần đục nền', hint='', effects=dict(xp=5), good=True,
                       outcome='Anh Phong gọi tiệm làm với giá 20 xu. Anh kể cho cả hội chủ trọ nghe.'),
                  dict(id='match', label='Báo 140 xu, rẻ hơn tí cho dễ ăn', hint='Lời to', effects=dict(review=[1, 'Hỏi giá thợ tiệm mà cũng nói thách như thợ dạo.']),
                       good=False, outcome='Anh Phong hỏi thêm chỗ khác, biết giá thật, giận không thèm gọi nữa.'),
                  dict(id='skip', label='Không bình luận chuyện thợ khác', hint='', effects={}, good=None,
                       outcome='Anh Phong gật gù, vẫn phân vân không biết tin ai.')],
         default='skip'),
    dict(id='crack', title='Ống gang cũ nứt', emoji='🧱', npc=2, min_day=3, tone='tense', at='between', weight=2, mods=('dry', 'normal'),
         text='Đi ngang nhà bà Ngọc, bà gọi: “Tường nhà bà thấm nước, có phải ống nứt không cháu?”',
         options=[dict(id='check', label='Xem giúp, nói thật mức độ, báo giá thay đoạn nứt', hint='', effects=dict(xp=4), good=True,
                       outcome='Ống nứt một đoạn ngắn. Bà Ngọc hẹn cuối tháng thay, cảm ơn cháu nói thật.'),
                  dict(id='scare', label='Dọa phải đục cả nền nhà thay hết ống', hint='Việc to…', effects=dict(review=[2, 'Thợ dọa đục cả nhà, hỏi thợ khác chỉ cần thay một đoạn.']),
                       good=False, outcome='Bà Ngọc hoảng, gọi con trai về. Anh con trai hỏi thêm thợ khác.'),
                  dict(id='later', label='Hẹn hôm khác ghé xem', hint='', effects={}, good=None, outcome='Bà Ngọc gật đầu, dặn đừng quên.')],
         default='later'),
    dict(id='flood', title='Mưa to, cả ngõ gọi', emoji='⛈️', npc=5, min_day=2, tone='tense', at='between', weight=3, mods=('rain',),
         text='Mưa như trút, điện thoại réo liên tục: ba nhà cùng báo nước trào, ông Lộc báo hố ga đầu ngõ tràn.',
         options=[dict(id='triage', label='Hỏi từng nhà, ưu tiên nhà có người già, trẻ nhỏ, hẹn giờ rõ ràng', hint='', effects=dict(xp=5, patience=-2), good=True,
                       outcome='Nhà bà cụ ở một mình được làm trước. Các nhà khác biết giờ, yên tâm chờ.'),
                  dict(id='first', label='Ai gọi trước làm trước', hint='', effects=dict(patience=-5), good=None,
                       outcome='Làm xong nhà đầu thì nhà bà cụ đã ngập tới mắt cá.'),
                  dict(id='price', label='Nhà nào trả cao làm trước', hint='', effects=dict(money=10, review=[1, 'Mưa ngập mà thợ đòi ai trả cao làm trước.']),
                       good=False, outcome='Được thêm tiền, nhưng cả ngõ bàn tán về tiệm.')],
         default='first'),
    dict(id='tip', title='Khách dúi thêm tiền', emoji='💵', npc=3, min_day=3, tone='gentle', at='between', weight=1, mods=None,
         text='Anh Phong dúi 10 xu: “Ghi hóa đơn cao lên giúp anh, anh đòi tiền sửa chữa của khách trọ.”',
         options=[dict(id='refuse', label='Từ chối, ghi đúng số tiền', hint='', effects=dict(xp=4), good=True,
                       outcome='Anh Phong cười trừ: “Thôi được, em thẳng quá.”'),
                  dict(id='take', label='Nhận tiền, ghi khống', hint='', effects=dict(money=10, review=[1, 'Nghe nói tiệm thông cống ghi hóa đơn khống cho chủ trọ.']),
                       good=False, outcome='Khách trọ phát hiện hóa đơn ghi sai, làm ầm lên.')],
         default='refuse'),
]

# The awkward people around the job (0.9.16): more surprises, each with its own way out.
DESK += [
    dict(id='shoes', title='Chủ nhà bắt bọc giày', emoji='🥿', npc=2, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Bà Ngọc chặn ở cửa: “Bọc hai lớp ni-lông vào giày, trải báo từ cổng tới nhà tắm. Bẩn một vết là lau cho sạch nha cháu.”',
         options=[dict(id='cover', label='Bọc giày, trải báo, làm gọn', hint='Mất thêm chút thời gian', effects=dict(patience=-3, xp=3), good=True,
                       outcome='Bà Ngọc kiểm từng viên gạch, gật gù: “Thợ này được, sạch sẽ.”'),
                  dict(id='bare', label='Cởi giày đi chân đất vào', hint='Nhanh, nhưng bẩn chân', effects={}, good=None,
                       outcome='Chân dẫm phải nước cống, bạn rửa mất nửa buổi. Bà Ngọc vẫn lầm bầm.'),
                  dict(id='argue', label='“Nhà cháu chứ có phải khách sạn đâu bà”', hint='', effects=dict(review=[2, 'Thợ gì mà cãi chủ nhà như hát hay.']), good=False,
                       outcome='Bà Ngọc đứng khoanh tay canh từng bước, cả buổi không ai nói với ai câu nào.')],
         default='cover'),
    dict(id='livestream', title='Khách livestream chê thợ', emoji='📱', npc=6, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Hùng giơ điện thoại quay thẳng mặt bạn: “Cả nhà ơi, thợ thông cống nè, xem thử có chặt chém không nha, hóng đi mọi người!”',
         options=[dict(id='explain', label='Bình thản giải thích từng bước, báo giá ngay trên sóng', hint='', effects=dict(xp=5), good=True,
                       outcome='Người xem khen thợ nói rõ ràng. Có hai người nhắn xin số tiệm.'),
                  dict(id='ask_stop', label='Nhờ tắt máy cho tập trung làm', hint='Hên xui', effects={},
                       luck=dict(p=0.5, win=dict(effects={}, good=None, outcome='Hùng tắt máy, lầm bầm “làm gì căng”.'),
                                 lose=dict(effects=dict(review=[3, 'Thợ không cho quay, chắc có gì mờ ám.']), good=False,
                                           outcome='Hùng càng quay hăng: “Thấy chưa, thợ sợ lộ kìa mọi người!”'))),
                  dict(id='mad', label='Gạt điện thoại: “Quay cái gì mà quay!”', hint='', effects=dict(review=[1, 'Thợ gạt điện thoại khách, thái độ như giang hồ.']), good=False,
                       outcome='Clip “thợ thông cống nổi điên” có vài nghìn lượt xem. Chú Hai gọi điện hỏi chuyện.')],
         default='explain'),
    dict(id='boss_neighbour', title='Hàng xóm đứng chỉ đạo', emoji='👉', npc=5, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Ông hàng xóm chống nạnh đứng sau lưng: “Sai rồi, phải chọc chỗ kia cơ! Hồi xưa tôi làm thế này này…” rồi giật luôn dây lò xo.',
         options=[dict(id='thank', label='Cảm ơn bác, mời bác ngồi uống nước xem cho vui', hint='', effects=dict(xp=3, patience=-2), good=True,
                       outcome='Ông ngồi xuống, kể chuyện thời trẻ. Bạn làm xong trong yên bình.'),
                  dict(id='let', label='Cho bác thử chọc', hint='Mất thời gian, lỡ hỏng dây', effects=dict(patience=-6),
                       luck=dict(p=0.4, win=dict(effects={}, good=None, outcome='Ông chọc một hồi rồi trả lại: “Thôi, cháu làm đi.”'),
                                 lose=dict(effects=dict(money=-6), good=False, outcome='Ông chọc gãy đầu lò xo, bạn phải thay đầu mới.'))),
                  dict(id='shoo', label='“Bác để cháu làm, bác đứng đó vướng lắm”', hint='', effects=dict(review=[3, 'Thợ trẻ mà ăn nói cộc lốc với người già.']), good=False,
                       outcome='Ông bỏ về, đi kể khắp ngõ là thợ bây giờ láo.')],
         default='thank'),
    dict(id='dog', title='Chó nhà khách cắn ống quần', emoji='🐕', npc=4, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Con chó nhỏ nhà chị Mai cứ lao vào cắn ống quần, chị cười: “Nó hiền lắm, không sao đâu, kệ nó!”',
         options=[dict(id='ask_leash', label='Nhờ chị giữ chó lại rồi mới làm', hint='', effects=dict(patience=-2, xp=2), good=True,
                       outcome='Chị Mai bế chó vào phòng. Bạn làm xong trong mười phút.'),
                  dict(id='endure', label='Kệ, vừa làm vừa né', hint='Chậm, dễ trượt tay', effects=dict(patience=-6), good=None,
                       outcome='Ống quần rách một mảng. Chị Mai vẫn cười: “Nó quý cháu đấy.”'),
                  dict(id='kick', label='Hất chân cho nó chạy', hint='', effects=dict(review=[1, 'Thợ đá chó nhà tôi! Không bao giờ gọi nữa.']), good=False,
                       outcome='Con chó kêu ăng ẳng. Chị Mai mặt tối sầm, trả tiền mà không nhìn mặt.')],
         default='ask_leash'),
    dict(id='faucet', title='Tiện tay sửa luôn vòi nước', emoji='🚰', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Anh Phong kéo tay: “Thợ cống với thợ nước cũng như nhau cả, sửa luôn cái vòi rỉ với cái bình nóng lạnh kêu lạch cạch đi.”',
         options=[dict(id='refer', label='Nói rõ không phải nghề mình, cho số thợ nước quen', hint='', effects=dict(xp=3), good=True,
                       outcome='Anh Phong gọi thợ nước. Hôm sau còn cảm ơn vì không làm ẩu.'),
                  dict(id='try', label='Thử sửa đại', hint='Hên xui', effects={},
                       luck=dict(p=0.35, win=dict(effects=dict(money=5), good=None, outcome='Siết lại gioăng, vòi hết rỉ. Anh Phong dúi 5 xu.'),
                                 lose=dict(effects=dict(money=-10, review=[2, 'Nhờ sửa vòi mà làm nước phun khắp nhà, phải đền.']), good=False,
                                           outcome='Vặn quá tay, vòi gãy, nước phun như suối.'))),
                  dict(id='no', label='“Việc ai nấy làm anh ơi”', hint='', effects={}, good=None, outcome='Anh Phong nhún vai: “Làm giá dữ.”')],
         default='refer'),
    dict(id='blame_tile', title='Khách đổ tại thợ làm nứt gạch', emoji='🧱', npc=2, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Bà Ngọc chỉ viên gạch nứt ở góc nhà tắm: “Lúc nãy chưa có vết này! Thợ làm nứt thì đền đi, 30 xu.”',
         options=[dict(id='photo', label='Mở ảnh chụp lúc mới tới cho bà xem', hint='May mà có chụp', effects=dict(xp=4), good=True,
                       outcome='Ảnh chụp lúc tới đã có vết nứt đó. Bà Ngọc ngượng: “À ừ, chắc bà nhớ nhầm.”'),
                  dict(id='pay', label='Đền cho yên chuyện', hint='Mất 30 xu', effects=dict(money=-30), good=None,
                       outcome='Bạn đền 30 xu cho một viên gạch nứt từ đời nào.'),
                  dict(id='fight', label='Cãi tay đôi: “Bà vu khống à?”', hint='', effects=dict(review=[2, 'Thợ làm nứt gạch còn cãi.']), good=False,
                       outcome='Hàng xóm kéo sang xem. Chẳng ai tin ai.')],
         default='pay'),
    dict(id='spam_calls', title='Khách gọi liên tục “tới chưa”', emoji='📞', npc=3, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Anh Phong gọi cuộc thứ năm trong mười phút: “Tới chưa? Tới đâu rồi? Nhanh lên, khách trọ chửi anh nãy giờ nè!”',
         options=[dict(id='eta', label='Nhắn giờ tới cụ thể, gửi định vị', hint='', effects=dict(xp=2), good=True,
                       outcome='Anh Phong thôi gọi. Tới nơi đúng giờ đã hẹn.'),
                  dict(id='mute', label='Tắt chuông cho đỡ phiền', hint='', effects=dict(patience=-5), good=None,
                       outcome='Tới nơi thấy anh Phong mặt hằm hằm: “Gọi hai chục cuộc không nghe!”'),
                  dict(id='snap', label='“Gọi nữa là em quay xe đó nha”', hint='', effects=dict(review=[2, 'Hối thợ có tí mà thợ dọa bỏ, láo toét.']), good=False,
                       outcome='Anh Phong im, nhưng lúc trả tiền không thèm nói cảm ơn.')],
         default='eta'),
    dict(id='no_show', title='Tới nơi khách không có nhà', emoji='🚪', npc=6, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Gõ cửa mười phút không ai mở. Gọi điện, Hùng ngái ngủ: “Ơ em quên, em đi chơi rồi. Anh đợi xíu, nửa tiếng nữa em về.”',
         options=[dict(id='fee', label='Báo phí đi lại 5 xu, hẹn lại giờ khác', hint='', effects=dict(money=5, xp=2), good=True,
                       outcome='Hùng chuyển khoản 5 xu phí đi lại, hẹn chiều mai. Rõ ràng, sòng phẳng.'),
                  dict(id='wait', label='Ngồi đợi ở cửa', hint='Mất cả buổi', effects=dict(patience=-8), good=None,
                       outcome='Hùng về muộn gần tiếng, còn hỏi “đợi lâu chưa anh”.'),
                  dict(id='leave', label='Bỏ về, chặn số luôn', hint='', effects=dict(review=[3, 'Hẹn thợ rồi thợ bỏ về, không thèm đợi.']), good=False,
                       outcome='Hùng lên nhóm cư dân kể thợ “bùng hẹn”.')],
         default='wait'),
    dict(id='smell_blame', title='Hàng xóm chửi vì mùi cống', emoji='🤢', npc=5, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Mở nắp hố ga ra, bà nhà bên thò đầu qua cửa sổ: “Hôi quá trời! Làm gì thì làm lẹ lên, bốc mùi vô tận nhà người ta rồi nè!”',
         options=[dict(id='cover', label='Xin lỗi, đậy tạm nắp, làm nhanh gọn', hint='', effects=dict(xp=3, patience=-2), good=True,
                       outcome='Bà nhà bên đóng cửa sổ. Làm xong bạn xịt khử mùi quanh miệng hố.'),
                  dict(id='ignore', label='Làm lơ', hint='', effects={}, good=None, outcome='Bà ấy chửi đổng thêm mấy câu rồi cũng thôi.'),
                  dict(id='back', label='“Cống nhà bà cũng thải ra đây đó bà”', hint='', effects=dict(review=[2, 'Thợ cống ăn nói xấc xược với người già.']), good=False,
                       outcome='Hai bên to tiếng. Ông Lộc phải ra can.')],
         default='cover'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='CG-S01', title='Đổ hóa chất cho nhanh', npc=2, tone='tense', min_day=1,
         opening='Bà Ngọc giục: “Đổ nguyên gói bột thông cống vào cho nhanh, thợ trước cũng làm thế mà!”',
         swap='Bạn là bà Ngọc, sợ tốn tiền, nghĩ bột thông cống là cách rẻ nhất.',
         facts=[dict(id='pipe', title='Đường ống', source='Nhìn kỹ', text='Ống gang cũ gỉ sét, mối nối đã rạn.'),
                dict(id='chem', title='Bột thông cống', source='Nhãn gói bột', text='Xút ăn mòn mạnh, sinh nhiệt, bắn vào mắt có thể mù; ống cũ dễ thủng.'),
                dict(id='kid', title='Trong nhà', source='Bà Ngọc', text='Cháu nội bà hai tuổi hay chạy vào nhà tắm.')],
         options=[dict(id='tool', label='Giải thích rủi ro, thông bằng dây lò xo, không dùng hóa chất', requires=['pipe', 'chem'], quality='good', stars=5,
                       review='Thợ nói kỹ vì sao không nên đổ hóa chất vào ống cũ. Làm bằng dụng cụ, sạch sẽ.',
                       outcome='Ống thông, không mùi xút. Bà Ngọc cất gói bột lên cao, xa tầm tay cháu.',
                       perspectives=[dict(who='Bà Ngọc', emoji='🏚️', text='Thì ra ống cũ mà đổ xút là thủng.'),
                                     dict(who='Chú Hai', emoji='🧰', text='Hóa chất là đường tắt, mà đường tắt hay đi lạc.')]),
                  dict(id='half', label='Đổ nửa gói cho bà vui', requires=['chem'], quality='bad', stars=2,
                       review='Nước rút được một hôm, rồi ống rỉ nước ra tường.', outcome='Tuần sau tường nhà tắm thấm ố vàng.',
                       perspectives=[dict(who='Bà Ngọc', emoji='😟', text='Rẻ được mấy đồng, giờ tốn gấp mười.'),
                                     dict(who='Chú Hai', emoji='🧰', text='Chiều khách mà hại khách là không nên.')]),
                  dict(id='all', label='Đổ cả gói, làm cho nhanh', quality='bad', stars=1,
                       review='Hơi xút bốc lên cay mắt, cháu tôi suýt chạy vào. Làm ăn ẩu!', outcome='Hơi nóng bốc lên, ống gang rò một chỗ.',
                       perspectives=[dict(who='Cháu nội', emoji='👶', text='(Suýt chạm vào vũng nước xút.)'),
                                     dict(who='Bà Ngọc', emoji='😠', text='Thế này thì gọi thợ làm gì.')])],
         lesson='Hóa chất thông cống ăn mòn ống cũ và nguy hiểm cho người: dùng dụng cụ cơ học trước.'),
    dict(id='CG-S02', title='Xuống hố ga cho kịp', npc=5, tone='tense', min_day=2,
         opening='Trời sắp mưa tiếp, ông Lộc giục: “Xuống múc luôn đi cháu, đo đạc gì cho mất thời gian!”',
         facts=[dict(id='gas', title='Mùi dưới hố', source='Miệng hố', text='Mùi trứng thối xộc lên: khí H₂S sinh ra từ bùn phân hủy, nồng độ cao gây ngất.'),
                dict(id='news', title='Chuyện cũ', source='Chú Hai', text='Chú Hai kể năm ngoái có hai thợ ở phường bên ngất dưới hố ga vì không đo khí.'),
                dict(id='time', title='Thời gian', source='Máy đo khí', text='Đo khí và thông gió chỉ mất khoảng mười phút.')],
         options=[dict(id='safe', label='Rào chắn, đo khí, bật quạt, có người canh rồi mới xuống', requires=['gas', 'time'], quality='good', stars=5,
                       review='Tổ thợ làm đúng quy trình an toàn, hố ga sạch trước cơn mưa.', outcome='Mười phút sau khí an toàn. Hố ga sạch trước khi mưa lại.',
                       perspectives=[dict(who='Ông Lộc', emoji='📒', text='Chờ mười phút mà yên tâm cả đời.'),
                                     dict(who='Chú Hai', emoji='🧰', text='Không đo khí thì chú không cho ai xuống.')]),
                  dict(id='rush', label='Nín thở xuống nhanh múc vài xô', quality='bad', stars=1,
                       review='Thợ xuống hố ga không đo khí, suýt ngất. Nguy hiểm quá!', outcome='Xuống được một lúc thì choáng váng, chú Hai phải kéo lên.',
                       perspectives=[dict(who='Chú Hai', emoji='😱', text='Tim chú muốn rớt ra ngoài.'),
                                     dict(who='Ông Lộc', emoji='😟', text='Tôi giục bậy, xin lỗi cháu.')]),
                  dict(id='top', label='Chỉ múc từ trên miệng hố, không xuống', requires=['gas'], quality='ok', stars=4,
                       review='Làm an toàn nhưng chưa sạch hẳn.', outcome='Nước rút tạm được, đáy hố còn bùn.',
                       perspectives=[dict(who='Ông Lộc', emoji='📒', text='Tạm được, mưa to chắc lại tràn.'),
                                     dict(who='Chú Hai', emoji='🧰', text='Đúng là không xuống thì an toàn, nhưng việc chưa xong.')])],
         lesson='Hố ga là không gian hạn chế: rào chắn, đo khí, thông gió và có người canh trước khi xuống.'),
    dict(id='CG-S03', title='Báo giá thật hay nói thách', npc=3, tone='gentle', min_day=2,
         opening='Anh Phong hỏi giá thông ống chính nhà trọ. Chú Hai vắng, bạn tự báo giá.',
         facts=[dict(id='list', title='Bảng giá của tiệm', source='Tờ giấy dán trong hộp đồ nghề', text='Ống thoát chính: 35 xu, thêm 10 xu nếu phải phun rửa mỡ.'),
                dict(id='rich', title='Khách', source='Nhìn quanh', text='Nhà trọ mười hai phòng, anh Phong đi xe hơi.'),
                dict(id='word', title='Tiếng tăm', source='Chú Hai', text='Chú Hai dặn: “Tiệm sống được là nhờ người ta giới thiệu nhau.”')],
         options=[dict(id='list', label='Báo đúng bảng giá, nói rõ phần phát sinh nếu có', requires=['list'], quality='good', stars=5,
                       review='Báo giá rõ ràng, làm xong đúng như báo.', outcome='Anh Phong gật đầu, còn đặt lịch vệ sinh ống định kỳ.',
                       perspectives=[dict(who='Anh Phong', emoji='🏠', text='Giá rõ ràng thì làm ăn lâu dài.'),
                                     dict(who='Chú Hai', emoji='🧰', text='Một khách tin mình bằng mười khách mới.')]),
                  dict(id='high', label='Nhà giàu, báo gấp đôi', requires=['rich'], quality='bad', stars=2,
                       review='Hỏi thêm mới biết bị nói thách gấp đôi. Mất lòng tin.', outcome='Anh Phong hỏi giá chỗ khác, gọi lại trách.',
                       perspectives=[dict(who='Anh Phong', emoji='😒', text='Tôi có xe hơi thì phải trả gấp đôi à?'),
                                     dict(who='Chú Hai', emoji='🧰', text='Giá không đổi theo cái xe của khách.')]),
                  dict(id='cheap', label='Báo rẻ cho được việc', quality='ok', stars=4, review='Rẻ, được việc.',
                       outcome='Được việc, nhưng tính ra tiệm lỗ tiền máy.',
                       perspectives=[dict(who='Anh Phong', emoji='🙂', text='Rẻ thế thì tốt quá.'),
                                     dict(who='Chú Hai', emoji='🧰', text='Rẻ quá thì lấy gì mua máy mới.')])],
         lesson='Báo giá theo bảng giá, trước khi làm; phát sinh thì nói rõ và hỏi lại khách.'),
    dict(id='CG-S04', title='Thông tạm hay làm tới nơi', npc=1, tone='gentle', min_day=2,
         opening='Chị Hồng giục: “Làm sao cho nước rút là được, quán sắp bán rồi, không cần kỹ!”',
         facts=[dict(id='grease', title='Trong ống', source='Camera', text='Mỡ đông bám dày cả đoạn ống, dây lò xo chỉ khoét được một lỗ nhỏ.'),
                dict(id='time', title='Thời gian', source='Chú Hai', text='Phun áp lực mất thêm hai mươi phút.'),
                dict(id='recur', title='Nếu thông tạm', source='Kinh nghiệm', text='Thông tạm bằng lò xo thì vài hôm mỡ lại bít kín.')],
         options=[dict(id='jet', label='Nói rõ, xin thêm hai mươi phút phun rửa tận gốc', requires=['grease', 'recur'], quality='good', stars=5,
                       review='Thợ giải thích dễ hiểu, làm tận gốc, cả tháng không tắc lại.', outcome='Quán bán trễ mười lăm phút, nhưng cả tháng bồn rửa thông thoáng.',
                       perspectives=[dict(who='Chị Hồng', emoji='🍲', text='Trễ chút mà khỏi lo cả tháng.'),
                                     dict(who='Chú Hai', emoji='🧰', text='Làm tới nơi thì khách mới gọi lại.')]),
                  dict(id='temp', label='Thông tạm, hẹn hôm khác phun', requires=['time'], quality='ok', stars=4,
                       review='Kịp giờ bán, nhưng phải hẹn thợ lần nữa.', outcome='Kịp giờ bán. Ba hôm sau chị Hồng gọi lại.',
                       perspectives=[dict(who='Chị Hồng', emoji='🙂', text='Được, nhớ quay lại nha.'),
                                     dict(who='Chú Hai', emoji='🧰', text='Hẹn rồi thì phải giữ lời.')]),
                  dict(id='hide', label='Thông tạm, không nói gì', quality='bad', stars=2, review='Thông xong hai hôm lại tắc, thợ không nói gì.',
                       outcome='Hai hôm sau bồn tắc lúc đông khách nhất.',
                       perspectives=[dict(who='Chị Hồng', emoji='😠', text='Biết vậy nói trước chứ.'),
                                     dict(who='Khách ăn', emoji='🍜', text='Quán đóng cửa giữa trưa.')])],
         lesson='Nói rõ đâu là thông tạm, đâu là làm tận gốc để khách tự chọn.'),
    dict(id='CG-S05', title='Đồ rơi quý trong bồn cầu', npc=4, tone='gentle', min_day=3,
         opening='Chị Mai hốt hoảng: bé Bin thả chiếc nhẫn cưới của chị vào bồn cầu, rồi giật nước.',
         facts=[dict(id='where', title='Chỗ rơi', source='Xả nước thử', text='Nước vẫn rút bình thường: nhẫn nhỏ, có thể nằm ở khúc cua đầu.'),
                dict(id='cam', title='Camera', source='Đồ nghề', text='Camera nội soi luồn vào được, móc gắp có thể lấy ra mà không tháo bồn.'),
                dict(id='price', title='Bảng giá', source='Tiệm', text='Soi và gắp đồ trong bồn cầu: 20 xu.')],
         options=[dict(id='careful', label='Soi camera, dùng móc gắp, báo giá trước', requires=['cam', 'price'], quality='good', stars=5,
                       review='Lấy được nhẫn cưới mà không phải đập bồn. Cảm ơn thợ!', outcome='Chiếc nhẫn sáng lấp lánh trên móc gắp. Chị Mai rưng rưng.',
                       perspectives=[dict(who='Chị Mai', emoji='💍', text='Nhẫn cưới đó, mất thì buồn cả đời.'),
                                     dict(who='Bé Bin', emoji='🧸', text='Con xin lỗi mẹ…')]),
                  dict(id='break', label='Tháo bồn cầu cho chắc, tính thêm tiền', quality='bad', stars=2, review='Tháo cả bồn cầu, tốn thêm tiền mà không cần.',
                       outcome='Lấy được nhẫn, nhưng mất nửa ngày và thêm tiền gioăng, xi măng.',
                       perspectives=[dict(who='Chị Mai', emoji='😣', text='Biết có camera thì đâu cần tháo.'),
                                     dict(who='Chú Hai', emoji='🧰', text='Dùng dao mổ trâu giết gà.')]),
                  dict(id='give', label='Bảo chắc trôi mất rồi, thôi', quality='bad', stars=1, review='Thợ không thèm thử, bảo trôi mất rồi.',
                       outcome='Chị Mai gọi thợ khác, họ gắp ra trong mười phút.',
                       perspectives=[dict(who='Chị Mai', emoji='😢', text='Thử một chút cũng không.'),
                                     dict(who='Chú Hai', emoji='🧰', text='Nghề mình là phải thử cho hết cách.')])],
         lesson='Dùng đúng dụng cụ để khỏi phá thêm; báo giá trước khi làm.'),
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


def list_price(place: str, cause: str | None, kind: str = 'call') -> int:
    """Chú Hai's price list for this job, as the player diagnosed it."""
    if cause == 'xi_phong':
        base = 10 + ITEMS[0]['cost']
    elif cause == 'thong_hoi':
        base = PLACES['mai']['price']
    else:
        base = PLACES[place]['price'] + (CAUSES[cause]['extra'] if cause else 0)
    return base * NIGHT // 100 if kind == 'emergency' else base


def quote_for(level: str, place: str, cause: str | None, kind: str) -> int:
    base = list_price(place, cause, kind)
    return {'list': base, 'high': base * HIGH // 100, 'low': max(1, base * LOW // 100), 'warranty': 0}[level]


# ================================================================ tasks
def _kind(day: int, slot: int, mod: str) -> str:
    if slot == 0:
        return 'setup'
    if day == 1:
        return 'call'
    if mod == 'rain' and slot == 1:
        return 'manhole'
    if slot == 2 and day % 4 == 0:
        return 'recall'
    if slot == 3 and day >= 3 and _hash('cg-night', day) % 3 == 0:
        return 'emergency'
    if slot == 2 and day % 3 == 2:
        return 'manhole'
    return 'call'


def _pick(day: int, slot: int, kind: str, mod: str) -> tuple:
    if day == 1:
        return CALLS[[0, 2, 1][(slot - 1) % 3]]
    pool = [x for x in CALLS if x[1] == kind and x[8] <= day and x[9] in (None, mod)]
    if not pool:
        pool = [x for x in CALLS if x[1] == 'call' and x[9] is None and x[8] <= day]
    weighted = [x for x in pool for _ in range(3 if x[9] else 1)]
    return weighted[kit.rng(ID, day, slot).randrange(len(weighted))]


def _booked(day: int) -> list:
    """The day's appointment book: what the first three callouts are about (read at the morning packing)."""
    mod = mod_of(day)['id']
    out = []
    for slot in (1, 2, 3):
        k = _kind(day, slot, mod)
        if k == 'recall':
            r = RECALLS[kit.rng(ID, 'recall', day, slot).randrange(len(RECALLS))]
            out.append(dict(who=PEOPLE[r['npc']][0], place=r['place'], text=r['title']))
        else:
            x = _pick(day, slot, k, mod)
            out.append(dict(who=PEOPLE[x[0]][0], place=x[2], text=x[4]))
    return out


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    kind = _kind(day, slot, mod)
    common = dict(gen=GEN, stage='prep', checked=[], diag=None, quote=None, level=None, quoted_for=None, tools=[], tries=0,
                  cleared=None, part=False, chem=False, safety=[], tested=False, cleaned=False, advised=False, cash=None,
                  story=None)
    if kind == 'setup':
        book = _booked(day)
        needs = dict(setup=True, book=book, note='Mưa lớn: hố ga dễ tràn, nhớ ủng, gầu, máy đo khí.' if mod == 'rain' else
                     'Đọc sổ hẹn, chọn đồ nghề hợp với việc hôm nay.')
        return kit.base_task(ID, day, slot, serial, 0, 'Xếp đồ nghề lên xe', 'Chú Hai: “Đọc sổ hẹn đi, xe chỉ chở được năm món. Mang gì thì tính cho kỹ.”',
                             kind='setup', needs=needs, **common)
    if kind == 'recall':
        r = RECALLS[kit.rng(ID, 'recall', day, slot).randrange(len(RECALLS))]
        needs = dict(place=r['place'], old=False, clues=dict(hoi=r['clue'], nhin='Miệng ống có cặn cũ.', xa='Nước rút rất chậm.'),
                     note='Gọi lại bảo hành: xem đúng lỗi của ai rồi mới tính tiền.')
        return kit.base_task(ID, day, slot, serial, r['npc'], r['title'], r['opening'], kind='recall', needs=needs, _cause=r['cause'],
                             _fault=r['fault'], **common)
    npc, k, place, cause, title, opening, clues, old, _, _ = _pick(day, slot, kind, mod)
    needs = dict(place=place, old=old, clues=dict(clues), note={'manhole': 'Hố ga của phường: an toàn trước, phường chuyển khoản sau.',
                                                                'emergency': 'Gọi đêm: phụ phí đêm phải báo trước.'}.get(k, 'Tìm nguyên nhân, báo giá rồi mới làm.'))
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind=k, needs=needs, _cause=cause, **common)


FIXED = ('needs', '_cause', '_fault')


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'
    tw = twist_of(t)
    if tw:
        # Jobs made before 0.9.16 have no twist; a new one carries it from the start (and it must match twist_of).
        t['twist'], t['tw'] = tw, dict(state='wait', choice=None, price=None, counter=None, tries=0)


# ================================================================ the shop's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, jobs=0, cleared=0, temp=0, trips=0, overcharged=0, warranty=0, earned=0)


def initial() -> dict:
    return dict(v=1, intro=False, bike=[], gear=[], out=False, regulars={}, temp_fixes=[], today=_fresh_today(0),
                stats=dict(jobs=0, cleared=0, temp=0, overcharged=0, fair=0, safety_ok=0, chem=0, chopped=0, refunds=0, walked=0, freebies=0),
                desk=kit.desk_initial(), debts=[], comebacks=[], trouble=folk.trouble_initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    for k, v in folk.trouble_initial().items():
        d['trouble'].setdefault(k, copy.deepcopy(v))
    return d


# ================================================================ the actions
FREE = ('cg_intro', 'cg_chase')
NO_TICK = ('cg_intro', 'cg_pack', 'cg_gear', 'cg_diag', 'cg_quote', 'cg_advise', 'cg_pay', 'cg_short', 'cg_desk', 'cg_safety',
           'cg_price', 'cg_watch', 'cg_nocash', 'cg_chase', 'cg_trouble')
PHYSICAL = ('cg_check', 'cg_work', 'cg_chem', 'cg_part', 'cg_fetch', 'cg_test', 'cg_clean')
JOBS = ('call', 'manhole', 'emergency', 'recall')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'cg_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Chú Hai đang chờ ở tiệm.')
    desk = d['desk']
    if name == 'cg_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
    if name in ('cg_chase', 'cg_trouble'):
        return ACTIONS[name](s, c, d, p)
    kit.desk_block(desk, 'Có chuyện giữa đường, quyết xong rồi làm tiếp nhé.')
    kit.need(d['trouble']['ev'] is None, 'Khách cũ quay lại đòi tiền: giải quyết trước đã.', 'surprise_open')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở tiệm thông cống.')
    if name not in ('cg_watch', 'cg_extra', 'cg_nocash'):
        t = next((x for x in c['tasks'] if x['id'] == p.get('task') and x.get('career') == ID), None)
        if t:
            _need_calm(t)      # someone is talking to you: answer them first
    result = fn(s, c, d, p)
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
    if _comeback_open(s, c, d):
        result['message'] = f'{result.get("message", "")} 🔔 Có khách cũ quay lại đòi tiền chênh lệch.'.strip()
        result['surprise'] = True
    return result


def _task(c: dict, p: dict, kinds=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tiệm thông cống.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    return t


def _need_out(d: dict) -> None:
    kit.need(d['out'], 'Chưa ra xe: xếp đồ nghề rồi bấm “Lên đường” nhé.')


# ---------------------------------------------------------------- the morning: packing the bike
def _pack(s, c, d, p):
    tool = kit.one_of(p.get('tool'), TOOL, 'Đồ nghề không có.')
    if tool in d['bike']:
        d['bike'].remove(tool)
        return dict(message=f'Cất {_lower(TOOL[tool]["name"])} lại tiệm.')
    kit.need(len(d['bike']) < BIKE_SLOTS, f'Xe chỉ chở được {BIKE_SLOTS} món. Bỏ bớt một món đã.')
    d['bike'].append(tool)
    return dict(message=f'{TOOL[tool]["emoji"]} Buộc {_lower(TOOL[tool]["name"])} lên xe ({len(d["bike"])}/{BIKE_SLOTS}).')


def _gear(s, c, d, p):
    item = kit.one_of(p.get('item'), GEAR, 'Đồ bảo hộ không có.')
    if item in d['gear']:
        kit.need(item != 'gang_tay', 'Găng tay đã đeo rồi, dùng xong mới bỏ.')
        d['gear'].remove(item)
        return dict(message=f'Tháo {_lower(GEAR_LABEL[item])}.')
    if item == 'gang_tay':
        kit.need(kit.stock(c, 'gang_tay') > 0, 'Hết găng tay rồi. Mở kho mua thêm nhé.')
        kit.take(c, 'gang_tay', 1)
    d['gear'].append(item)
    return dict(message={'gang_tay': '🧤 Đeo găng tay cao su.', 'khau_trang': '😷 Đeo khẩu trang.', 'ung': '🥾 Xỏ ủng cao su.',
                         'kinh': '🥽 Đeo kính bảo hộ.'}[item])


def _setout(s, c, d, p):
    t = _task(c, p, ('setup',))
    kit.need(d['bike'], 'Xe còn trống trơn. Xếp đồ nghề đã.')
    need = {x['place'] for x in t['needs']['book']}
    miss = []
    if need & {'bon_cau', 'bon_rua', 'lavabo'} and not {'pit_tong', 'lo_xo', 'may_lo_xo'} & set(d['bike']):
        miss.append('đồ thông bồn')
    if 'ho_ga' in need and not {'gau', 'do_khi'} <= set(d['bike']):
        miss.append('gầu và máy đo khí cho hố ga')
    if miss:
        t['mistakes'] += 1
        cq.slip(t, 'pack', 1, f'Sổ hẹn có việc mà xe thiếu {", ".join(miss)}.', 'xếp đồ nghề chưa hợp sổ hẹn')
    if 'gang_tay' not in d['gear']:
        t['mistakes'] += 1
        cq.slip(t, 'no_gloves', 2, 'Đi thông cống mà không đeo găng tay.', 'thiếu găng tay')
    d['out'] = True
    kit.start_work(t)
    ok = not cq.slips(t)
    kit.complete(s, c, t, 0, 'Xếp đồ nghề, lên đường.')
    return dict(message='🛵 Lên đường! ' + ('Chú Hai gật gù: “Đồ nghề hợp việc đấy.”' if ok else 'Chú Hai nhắc: “Thiếu đồ là phải quay về lấy đấy nhé.”'),
                celebrate=ok)


def _fetch(s, c, d, p):
    """Ride back to the shop for a tool that was left behind (the customers wait)."""
    _need_out(d)
    tool = kit.one_of(p.get('tool'), TOOL, 'Đồ nghề không có.')
    kit.need(tool not in d['bike'], 'Món này đang ở trên xe.')
    if len(d['bike']) >= BIKE_SLOTS:
        drop = kit.one_of(p.get('drop'), d['bike'], f'Xe đầy {BIKE_SLOTS} món: chọn món để lại tiệm.')
        d['bike'].remove(drop)
    d['bike'].append(tool)
    d['today']['trips'] += 1
    for t in c['tasks']:
        if t.get('career') == ID and t['status'] not in ('completed', 'referred', 'cancelled') and 'patience' in t:
            t['patience'] = max(25, t['patience'] - 8)
    return dict(message=f'🛵 Chạy về tiệm lấy {_lower(TOOL[tool]["name"])}. Khách phải chờ thêm một lúc.')


# ---------------------------------------------------------------- finding the cause
def _check(s, c, d, p):
    t = _task(c, p, JOBS)
    _need_out(d)
    kit.need(t['known'], 'Nghe khách kể đã nhé.')
    how = kit.one_of(p.get('how'), HOWS, 'Cách kiểm tra không có.')
    kit.need(how not in t['checked'], 'Đã kiểm tra cách này rồi.')
    if how == 'camera':
        kit.need('camera' in d['bike'], 'Camera không có trên xe. Về tiệm lấy nếu cần.')
    t['checked'].append(how)
    t['stage'] = 'work'
    kit.start_work(t)
    text = CAUSES[t['_cause']]['camera'] if how == 'camera' else t['needs']['clues'][how]
    return dict(message=f'🔍 {HOW_LABEL[how]}: {text}')


def _diag(s, c, d, p):
    t = _task(c, p, JOBS)
    kit.need(t['known'], 'Nghe khách kể đã nhé.')
    kit.need(t['checked'], 'Kiểm tra một chút đã, đừng đoán mò.')
    cause = kit.one_of(p.get('cause'), CAUSES, 'Nguyên nhân không có trong sổ.')
    kit.need(t['cleared'] is None or t['cleared'] == 'fail', 'Đã thông xong rồi.')
    t['diag'] = cause
    if t['cleared'] == 'fail':
        t['cleared'] = None     # a new idea after a failed try: on to the tools again (the tries stay counted)
    return dict(message=f'📝 Ghi sổ: nghi {_lower(CAUSES[cause]["name"])}.')


def _quote(s, c, d, p):
    t = _task(c, p, JOBS)
    kit.need(t['diag'], 'Đoán nguyên nhân trước rồi mới báo giá.')
    level = kit.one_of(p.get('level'), LEVELS, 'Chọn mức báo giá.')
    kit.need(t['cleared'] in (None, 'fail'), 'Đã làm xong, không báo giá lại được.')
    price = quote_for(level, t['needs']['place'], t['diag'], t['kind'])
    who = _who(t)
    again = t['quote'] is not None
    if again:
        t['patience'] = max(25, t.get('patience', 100) - 5)   # asking again costs the customer's patience
    if level == 'high' and _hash('cg-refuse', t['id']) % 100 < 60:
        t['mistakes'] += 1
        cq.slip(t, 'greedy', 2, f'Báo giá {price} xu, gấp mấy lần chỗ khác. Thôi, tôi gọi thợ khác.', 'nói thách')
        react = cq.react(s, c, t, 0, who=who)
        msg = _finish(s, c, d, t, 0, f'{who} lắc đầu trước giá {price} xu, gọi thợ khác. {react["message"]}'.strip())
        return dict(message='🧾 ' + msg, correct=False)
    t.update(quote=price, level=level, quoted_for=t['diag'])
    head = f'🧾 Báo lại giá: {price} xu.' if again else f'🧾 Báo giá: {price} xu.'
    tail = {'list': f' {who} gật đầu: “Được, làm đi em.”', 'high': f' {who} nhăn mặt nhưng gật đầu.',
            'low': f' {who} mừng ra mặt.', 'warranty': f' {who}: “Vậy mới là bảo hành chứ!”'}[level]
    if t['kind'] == 'emergency' and level == 'list':
        tail = f' Đã nói rõ phụ phí gọi đêm. {who} gật đầu.'
    return dict(message=head + tail)


# ---------------------------------------------------------------- safety at a manhole
def _safety(s, c, d, p):
    t = _task(c, p, ('manhole',))
    _need_out(d)
    step = kit.one_of(p.get('step'), SAFETY, 'Bước an toàn không có.')
    kit.need(step not in t['safety'], 'Đã làm bước này rồi.')
    if step in ('khi', 'quat'):
        kit.need('do_khi' in d['bike'], 'Máy đo khí và quạt không có trên xe. Về tiệm lấy đã.')
    if step == 'quat':
        kit.need('khi' in t['safety'], 'Đo khí trước để biết cần thông gió bao lâu.')
    t['safety'].append(step)
    kit.start_work(t)
    text = {'rao': '🚧 Đặt rào chắn, cắm biển “Đang thi công” quanh miệng hố.',
            'khi': '🌬️ Thả đầu đo xuống hố: khí H₂S vượt ngưỡng an toàn! Chưa được xuống.',
            'quat': '🌀 Bật quạt thổi khí mười phút, đo lại: an toàn.',
            'canh': '🧍 Chú Hai đứng trên miệng hố, cầm dây an toàn.'}[step]
    return dict(message=text)


# ---------------------------------------------------------------- the work
def _need_quote(t: dict) -> None:
    kit.need(t['quote'] is not None, 'Báo giá cho khách trước khi làm.')


def _hands_in(t: dict, d: dict) -> None:
    """Gear and safety, checked the first time the hands go in."""
    g = set(d['gear'])
    if 'gang_tay' not in g:
        t['mistakes'] += 1
        cq.slip(t, 'bare', 1, 'Thò tay trần vào ống cống, bẩn hết cả bồn rửa.', 'thiếu găng tay')
    if t['kind'] == 'manhole':
        if not {'khi', 'quat'} <= set(t['safety']):
            t['mistakes'] += 1
            cq.slip(t, 'gas', 3, 'Xuống hố ga không đo khí, không thông gió: choáng váng phải kéo lên.', 'bỏ qua đo khí hố ga', safety=True)
        if 'canh' not in t['safety']:
            t['mistakes'] += 1
            cq.slip(t, 'alone', 2, 'Xuống hố ga một mình, không ai canh trên miệng hố.', 'không có người canh')
        if 'rao' not in t['safety']:
            t['mistakes'] += 1
            cq.slip(t, 'barrier', 1, 'Miệng hố mở toang giữa ngõ, suýt có người sụt chân.', 'không rào chắn')
        if 'ung' not in g or 'khau_trang' not in g:
            t['mistakes'] += 1
            cq.slip(t, 'gear', 1, 'Xuống bùn mà thiếu ủng, khẩu trang.', 'thiếu đồ bảo hộ')


def _work(s, c, d, p):
    t = _task(c, p, JOBS)
    _need_out(d)
    _need_quote(t)
    kit.need(t['cleared'] in (None, 'fail'), 'Đã thông rồi. Xả nước thử nhé.')
    stop = _twist_now(t, 'watch')
    if stop:
        return stop
    tool = kit.one_of(p.get('tool'), TOOL, 'Đồ nghề không có.')
    kit.need(tool in d['bike'], f'{TOOL[tool]["name"]} để ở tiệm. Về lấy đã.')
    kit.need(tool not in ('camera', 'do_khi'), 'Món này để kiểm tra, không dùng để thông.')
    t['stage'] = 'work'
    kit.start_work(t)
    if not t['tools'] and not t['part']:
        _hands_in(t, d)
    if tool == 'may_phun' and 'kinh' not in d['gear']:
        t['mistakes'] += 1
        cq.slip(t, 'splash', 2, 'Phun áp lực mà không đeo kính, nước bẩn bắn vào mắt.', 'thiếu kính bảo hộ')
    if tool not in t['tools']:
        t['tools'].append(tool)
    cause = CAUSES[t['_cause']]
    if tool in cause['fix']:
        t['cleared'] = 'full'
        return dict(message=f'{TOOL[tool]["emoji"]} {_clear_line(t["_cause"], tool)} Nước rút ào ào.', celebrate=True)
    if tool in cause['temp']:
        t['cleared'] = 'temp'
        return dict(message=f'{TOOL[tool]["emoji"]} Khoét được một lỗ, nước rút được… nhưng hơi chậm. Chưa sạch tận gốc.')
    t['cleared'] = 'fail'
    t['tries'] += 1
    t['mistakes'] += 1
    return dict(message=f'{TOOL[tool]["emoji"]} Loay hoay mãi không ăn thua. Chưa đúng bệnh: kiểm tra lại xem.', correct=False)


def _clear_line(cause: str, tool: str) -> str:
    return {'toc': 'Móc ra cả búi tóc quấn cặn xà phòng.', 'mo': 'Tia nước áp lực cuốn trôi lớp mỡ đông.', 'giay': 'Cục giấy ướt vỡ ra, trôi tuột.',
            'vat': 'Gắp ra được món đồ chơi nhựa đỏ!', 're': 'Đầu cắt xoay nát chùm rễ trong ống.', 'bun': 'Múc lên mấy chục xô bùn, rác.',
            'thong_hoi': 'Lôi ra cái tổ chim khô chặn ống thông hơi trên mái.'}.get(cause, 'Thông rồi.')


def _chem(s, c, d, p):
    t = _task(c, p, JOBS)
    _need_out(d)
    _need_quote(t)
    kit.need(t['cleared'] in (None, 'fail'), 'Đã thông rồi.')
    stop = _twist_now(t, 'watch')
    if stop:
        return stop
    kit.need(kit.stock(c, 'bot') > 0, 'Hết bột thông cống.')
    kit.take(c, 'bot', 1)
    t['chem'] = True
    d['stats']['chem'] += 1
    kit.start_work(t)
    g = set(d['gear'])
    if not {'gang_tay', 'kinh'} <= g:
        t['mistakes'] += 1
        cq.slip(t, 'chem_burn', 3, 'Đổ xút không kính, không găng, hơi nóng bốc lên cay xè mắt.', 'dùng hóa chất thiếu bảo hộ', safety=True)
    if t['needs']['old']:
        t['mistakes'] += 1
        cq.slip(t, 'chem_pipe', 2, 'Đổ xút vào ống gang cũ, mấy hôm sau ống rò nước ra tường.', 'hóa chất làm hỏng ống cũ')
    if t['_cause'] in ('toc', 'giay'):
        t['cleared'] = 'temp'
        return dict(message='🧪 Đổ bột thông cống, nước sôi sùng sục… rút được, nhưng chỉ tạm thời.')
    t['cleared'] = 'fail'
    t['tries'] += 1
    t['mistakes'] += 1
    return dict(message='🧪 Đổ bột thông cống, chờ mãi vẫn không rút. Bột không làm gì được thứ đang chặn.', correct=False)


def _part(s, c, d, p):
    t = _task(c, p, JOBS)
    _need_out(d)
    _need_quote(t)
    kit.need(not t['part'], 'Đã thay rồi.')
    stop = _twist_now(t, 'watch')
    if stop:
        return stop
    kit.need(kit.stock(c, 'xi_phong') > 0, 'Hết ống xi-phông. Mở kho nhập thêm nhé.')
    kit.take(c, 'xi_phong', 1)
    t['part'] = True
    kit.start_work(t)
    if not t['tools']:
        _hands_in(t, d)
    if t['_cause'] == 'xi_phong':
        t['cleared'] = 'full'
        return dict(message='🔧 Tháo ống xi-phông nứt, lắp ống mới, siết gioăng. Hết rỉ nước.', celebrate=True)
    t['cleared'] = 'fail'
    t['tries'] += 1
    t['mistakes'] += 1
    return dict(message='🔧 Thay ống xi-phông mới… mà nước vẫn không rút. Chỗ tắc nằm chỗ khác.', correct=False)


def _test(s, c, d, p):
    t = _task(c, p, JOBS)
    kit.need(t['cleared'] in ('full', 'temp'), 'Chưa thông được, xả nước thử cũng vậy thôi.')
    t['tested'] = True
    if t['cleared'] == 'temp':
        return dict(message='💧 Xả nước thử: rút được nhưng còn hơi chậm. Nên nói rõ với khách đây là thông tạm.')
    return dict(message='💧 Xả nước thử: rút ào ào, không còn tiếng ọc ọc.')


def _clean(s, c, d, p):
    t = _task(c, p, JOBS)
    kit.need(t['cleared'] in ('full', 'temp'), 'Làm xong việc chính đã.')
    kit.need(not t['cleaned'], 'Đã dọn rồi.')
    t['cleaned'] = True
    return dict(message='🧽 Lau sạch nền, gom bùn rác vào bao buộc kín, rửa dụng cụ.')


def _advise(s, c, d, p):
    t = _task(c, p, JOBS)
    kit.need(t['cleared'] in ('full', 'temp'), 'Làm xong việc chính đã.')
    kit.need(not t['advised'], 'Đã dặn rồi.')
    t['advised'] = True
    line = ADVICE.get(t['_cause'], 'Giữ ống sạch, thấy chậm thì gọi sớm.')
    if t['cleared'] == 'temp':
        line = 'Nói rõ: đây mới là thông tạm, vài hôm có thể tắc lại, nên làm tận gốc. ' + line
    return dict(message=f'🗣️ Dặn {_who(t)}: {line}')


def _giveup(s, c, d, p):
    """Cannot clear it today: say so, charge nothing and hand the job on honestly."""
    t = _task(c, p, JOBS)
    kit.need(t['known'], 'Nghe khách kể đã nhé.')
    kit.need(t['cleared'] not in ('full', 'temp'), 'Đã thông được rồi.')
    kit.start_work(t)
    react = cq.react(s, c, t, 0, who=_who(t))
    msg = _finish(s, c, d, t, 0, f'Nói thật với {_who(t)}: hôm nay chưa xử lý được, không lấy tiền, hẹn chú Hai tới xem. {react["message"]}'.strip())
    return dict(message='🙏 ' + msg)


def _bill(s, c, d, p):
    t = _task(c, p, JOBS)
    kit.need(t['cleared'] in ('full', 'temp'), 'Chưa thông được thì chưa thu tiền.')
    kit.need(t['stage'] == 'work', 'Đã tính tiền rồi.')
    stop = _twist_now(t, 'extra') or (t['kind'] != 'manhole' and _twist_now(t, 'nocash'))
    if stop:
        return stop
    price = _bill_checks(s, c, d, t)
    return _collect(s, c, d, t, price)


def _bill_checks(s: dict, c: dict, d: dict, t: dict) -> int:
    """What the customer sees when the bill comes (slips), the day's counts, and the price asked."""
    cause, fair = t['_cause'], list_price(t['needs']['place'], t['_cause'], t['kind'])
    if not t['tested']:
        t['mistakes'] += 1
        cq.slip(t, 'untested', 1, 'Chưa xả nước thử đã thu tiền, thợ đi rồi mới thấy còn chậm.', 'chưa xả nước thử')
    if not t['cleaned']:
        t['mistakes'] += 1
        cq.slip(t, 'mess', 1, 'Thông xong để bùn đất bẩn hết sàn nhà.', 'chưa dọn chỗ làm')
    if t['cleared'] == 'temp' and not t['advised']:
        t['mistakes'] += 1
        cq.slip(t, 'recur', 2, 'Thông tạm mà không nói, hai hôm sau tắc lại y nguyên.', 'thông tạm không nói rõ')
    if t['kind'] == 'recall':
        if t['_fault'] == 'shop' and t['quote']:
            t['mistakes'] += 1
            cq.slip(t, 'warranty', 2, 'Lỗi thợ thông tạm hôm trước mà giờ lại thu tiền.', 'không bảo hành lỗi của mình')
        fair = 0 if t['_fault'] == 'shop' else fair
    if t['level'] == 'own':
        _own_price_checks(s, c, d, t, fair)
    if t['quote'] > fair and t['level'] == 'list':
        # Quoted for a bigger job than it was (a wrong diagnosis never quoted again): the customer pays for work not done.
        t['mistakes'] += 1
        cq.slip(t, 'misquote', 1, f'Báo giá việc {_lower(CAUSES[t["quoted_for"]]["name"])}, mà hóa ra chỉ là {_lower(CAUSES[cause]["name"])}.', 'báo giá theo bệnh đoán sai')
    if t['quote'] > fair and t['level'] == 'high':
        t['mistakes'] += 1
        d['today']['overcharged'] += t['quote'] - fair
        d['stats']['overcharged'] += t['quote'] - fair
        cq.slip(t, 'overcharge', 2, f'Hỏi hàng xóm mới biết việc này giá {fair} xu, bị lấy {t["quote"]}.', 'nói thách')
    price = t['quote'] + (_extra_price(t) or 0)   # a quote below the real job is the shop's own loss
    d['today']['jobs'] += 1
    d['stats']['jobs'] += 1
    d['today']['cleared' if t['cleared'] == 'full' else 'temp'] += 1
    d['stats']['cleared' if t['cleared'] == 'full' else 'temp'] += 1
    if t['kind'] == 'manhole' and {'rao', 'khi', 'quat', 'canh'} <= set(t['safety']):
        d['stats']['safety_ok'] += 1
    if t['cleared'] == 'temp':
        d['temp_fixes'] = (d['temp_fixes'] + [dict(day=c['day'], task=t['id'], cause=cause)])[-10:]
    return price


def _collect(s: dict, c: dict, d: dict, t: dict, price: int) -> dict:
    who = _who(t)
    if not price:
        react = cq.react(s, c, t, 0, who=who)
        msg = _finish(s, c, d, t, 0, ('Bảo hành, không lấy tiền. ' + react['message']).strip())
        return dict(message='✅ ' + msg, celebrate=not cq.slips(t))
    if t['kind'] == 'manhole':
        react = cq.react(s, c, t, price, who=who)
        if react['pay']:
            kit.bank(react['pay'])
        d['today']['earned'] += react['pay']
        if not cq.slips(t):
            d['stats']['fair'] += 1
        msg = _finish(s, c, d, t, react['pay'], (f'Phường chuyển khoản {react["pay"]} xu. ' + react['message']).strip())
        return dict(message='🏦 ' + msg, celebrate=not cq.slips(t))
    t['stage'] = 'pay'
    t['cash'] = till.new(price, t['id'], c=c, t=t)
    return dict(message=f'💵 Tính tiền: {price} xu như đã báo. {who} đưa {sum(t["cash"]["tender"])} xu: thối lại cho đúng.')


def _pay(s, c, d, p):
    t = _task(c, p, JOBS)
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    who = _who(t)
    rec = t['cash']
    chk = till.check(s, c, t, rec, p.get('change'), who)
    if chk['stop']:
        return dict(message='💵 ' + chk['message'], correct=False)
    react = cq.react(s, c, t, rec['price'], who=who)
    st = till.settle(s, c, t, rec, react, who)
    net = react['pay'] - st['loss']
    d['today']['earned'] += max(0, net)
    if not cq.slips(t):
        d['stats']['fair'] += 1
    parts = [x for x in (react['message'], st['message']) if x]
    msg = _finish(s, c, d, t, max(0, net), ' '.join(parts))
    if net < 0:
        lost = min(-net, c['money'])
        if lost:
            kit.money(s, c, -lost, f'Thối dư cho khách: {t["title"]}'[:120], t['id'], 'change_loss')
    given = sum(rec['change'])
    return dict(message=(f'💵 Thu {rec["price"]} xu' + (f', thối {given} xu.' if given else '.') + f' {msg}').strip(), celebrate=not cq.slips(t))


def _short(s, c, p):
    t = _task(c, p)
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    return till.short_action(s, c, t, t['cash'], p, _who(t))


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


# ================================================================ the awkward people around the job (0.9.16)
# A job made from 0.9.16 on may carry a twist (twist_of, from the task id: never regenerated, only checked):
# the homeowner who stands over you and grumbles, the free extra job, the customer with no cash.
# The player answers in their own way; each person decides from hidden traits (street_folk).
TWISTS = ('watch', 'extra', 'nocash')
TW_STATES = ('wait', 'on', 'done')
TW_CHOICES = {'watch': ('bear', 'answer', 'away', 'refuse'), 'extra': ('free', 'charge', 'refuse'), 'nocash': ('wait', 'trust', 'deposit')}
EXTRA_FAIR = 12
WATCH_LINES = (
    '“Ơ sao chọc mãi chưa xong? Thợ gì chậm như rùa, tính giờ công à?”',
    '“Cẩn thận cái gạch nhà tôi! Nứt một viên là đền nha, gạch nhập đó.”',
    '“Ông thợ hôm trước đổ gói bột là xong, bày vẽ lắm thế, làm màu à?”',
    '“Để tôi quay clip làm bằng chứng. Làm ẩu là tôi đăng nhóm cư dân liền.”',
)
EXTRA_ASKS = (
    '“Tiện tay thông luôn cái lavabo trên lầu nha, có tí xíu, tính tiền gì.”',
    '“Xong thì sửa giùm cái vòi rỉ luôn, thợ nước thợ cống cũng như nhau thôi.”',
    '“Hút luôn hố ga trước nhà bà bên cạnh nha, bà ấy nhờ, tiền thì tính sau.”',
    '“Thông luôn bồn cầu tầng ba đi, nhanh nha, chiều nhà có khách.”',
)
NOCASH_LINES = (
    '“Chết, hết tiền mặt rồi, mai chuyển khoản nha. Tin nhau tí đi.”',
    '“Ví để ở cơ quan rồi, ghi nợ đi, thiếu gì mà sợ.”',
    '“App ngân hàng đang lỗi, hẹn cuối tuần nha, bùng đâu mà lo.”',
    '“Đang kẹt, tuần sau vợ về đưa. Ai quỵt đâu mà nhìn dữ vậy.”',
)
WATCH_OUT = {
    ('answer', 'calm'): 'Nghe bạn giải thích đâu ra đấy, {who} gật gù: “Ừ thì làm đi.”',
    ('answer', 'sulk'): '{who} lầm bầm “thợ bây giờ cãi hay ghê” rồi đứng xa ra một chút.',
    ('answer', 'blowup'): '{who} gân cổ: “Cãi hả? Làm không xong thì cút mẹ mày đi, tao gọi thợ khác!”',
    ('away', 'calm'): '{who} ra phòng khách ngồi xem ti vi. Bạn làm nhanh hẳn.',
    ('away', 'sulk'): '{who} bỏ ra ngoài, đóng cửa hơi mạnh.',
    ('away', 'blowup'): '{who}: “Nhà tôi mà tôi không được đứng hả? Láo vl!”',
}


def twist_of(t: dict) -> dict | None:
    """The twist a job carries (a pure function of the job: the validator checks a stored twist against it)."""
    if t.get('kind') not in ('call', 'emergency', 'recall') or t.get('day', 1) < 2:
        return None
    r = folk.roll('cg-twist', t['id'])
    kind = 'watch' if r < 30 else 'extra' if r < 45 else 'nocash' if r < 58 and t['kind'] != 'recall' else None
    return dict(kind=kind, n=folk.roll('cg-twist-n', t['id']) % 4) if kind else None


def _tr(t: dict) -> dict:
    i = _npc_index(t)
    return folk.traits(t['id'], PEOPLE[i][3] if 0 <= i < len(PEOPLE) else None)


def _tw(t: dict, kind: str) -> dict | None:
    """The job's twist state when it is of that kind."""
    tw = t.get('twist')
    return t.get('tw') if isinstance(tw, dict) and tw.get('kind') == kind else None


def _twist_now(t: dict, kind: str) -> dict | None:
    """A waiting twist of that kind starts now: the action stops here with the person's words."""
    st = _tw(t, kind)
    if not st or st['state'] == 'done':
        return None
    st['state'] = 'on'
    n, who = t['twist']['n'], _who(t)
    line = {'watch': WATCH_LINES, 'extra': EXTRA_ASKS, 'nocash': NOCASH_LINES}[kind][n]
    head = {'watch': '🗯️ Chủ nhà đứng sau lưng lèm bèm', 'extra': '🙏 Khách nhờ “tiện tay”', 'nocash': '💸 Khách không có tiền mặt'}[kind]
    return dict(message=f'{head}: {who} {line}', surprise=True)


def _need_calm(t: dict) -> None:
    for k in TWISTS:
        st = _tw(t, k)
        kit.need(not st or st['state'] != 'on', 'Khách đang nói chuyện với bạn: trả lời trước đã.')


def _extra_price(t: dict) -> int:
    st = _tw(t, 'extra')
    return st['price'] if st and st['state'] == 'done' and st['price'] else 0


def _street_trust(c: dict, delta: int) -> None:
    box = c.get('incidents')
    if isinstance(box, dict) and isinstance(box.get('trust'), int):
        box['trust'] = max(0, min(100, box['trust'] + delta))


def _price(s, c, d, p):
    """The player names a price (any number): the customer decides by themselves."""
    t = _task(c, p, JOBS)
    kit.need(t['diag'], 'Đoán nguyên nhân trước rồi mới báo giá.')
    kit.need(t['cleared'] in (None, 'fail'), 'Đã làm xong, không báo giá lại được.')
    price = kit.integer(p.get('price'), 0, 500)
    fair = list_price(t['needs']['place'], t['_cause'], t['kind'])
    if t['kind'] == 'recall' and t['_fault'] == 'shop':
        fair = max(1, fair // 3)            # a warranty job: people know it should cost next to nothing
    bid = t.setdefault('bid', dict(tries=0, counter=None, ratio=None, grudge=False))
    r = folk.judge_price(_tr(t), fair, price, bid['tries'])
    who = _who(t)
    if t['quote'] is not None:
        t['patience'] = max(25, t.get('patience', 100) - 5)
    if r['kind'] == 'counter':
        bid.update(tries=bid['tries'] + 1, counter=r['counter'])
        line = ('“{p} xu á? Ăn cướp à! {c} xu thôi, không thì thôi.”' if r['ratio'] > 150 else '“Bớt đi, {c} xu làm luôn.”').format(p=price, c=r['counter'])
        return dict(message=f'🧾 {who}: {line}')
    if r['kind'] == 'walk':
        t['mistakes'] += 1 if r['ratio'] > 130 else 0
        if r['ratio'] > 130:
            cq.slip(t, 'greedy', 2, f'Hét giá {price} xu, chặt chém trắng trợn. Gọi thợ khác cho lành.', 'nói thách')
            _street_trust(c, -1)
        react = cq.react(s, c, t, 0, who=who)
        msg = _finish(s, c, d, t, 0, f'{who} xua tay trước giá {price} xu: “Thôi, cảm ơn, tôi gọi người khác.” {react["message"]}'.strip())
        return dict(message='🧾 ' + msg, correct=False)
    bid.update(counter=None, ratio=r['ratio'], grudge=bool(r['grudge']))
    t.update(quote=price, level='own', quoted_for=t['diag'])
    tail = {'cheap': f'{who} mừng ra mặt: “Rẻ vậy, làm liền đi em!”', 'accept': f'{who} gật: “Ừ, làm đi.”'}[r['kind']]
    return dict(message=f'🧾 Báo giá: {price} xu. {tail}')


def _own_price_checks(s: dict, c: dict, d: dict, t: dict, fair: int) -> None:
    """Consequences of a price the player named: fair, a bit steep, or chặt chém."""
    bid = t.get('bid') or {}
    ratio = t['quote'] * 100 // max(1, fair) if fair else (999 if t['quote'] else 0)
    tr = _tr(t)
    if ratio <= 115:
        return
    extra = t['quote'] - fair
    d['stats']['chopped'] += max(0, extra)
    d['today']['overcharged'] += max(0, extra)
    if ratio > 160:
        t['mistakes'] += 1
        cq.slip(t, 'chop', 2, f'Việc này người ta lấy {fair} xu, thợ hét {t["quote"]}. Chặt chém vừa thôi.', 'chặt chém')
        _street_trust(c, -3)
        kit.review(s, c, kit.npc_id(ID, 5), 2, f'Nghe đồn thợ thông cống lấy {t["quote"]} xu một việc {fair} xu. Cả ngõ cẩn thận nha.', t['id'])
    elif tr['savvy'] >= 55:
        t['mistakes'] += 1
        cq.slip(t, 'overcharge', 1, 'Giá hơi chặt đấy nhé, tôi biết giá thị trường mà.', 'giá cao hơn thường')
    if bid.get('grudge') or (ratio > 160 and folk.roll('cg-back', t['id']) < 55):
        # They pay today; a neighbour tells them the real price and they come back for the difference.
        cb = dict(id=f'cb-{t["id"]}', task=t['id'], npc=_npc_index(t), due=c['day'] + 1 + folk.roll('cg-back-d', t['id']) % 2,
                  extra=max(1, extra), state='wait')
        d['comebacks'] = [x for x in d['comebacks'] if x['state'] == 'wait'][-7:] + [cb]


def _watch(s, c, d, p):
    """The homeowner grumbling over your shoulder: put up with it, answer back, ask them away, or refuse."""
    t = _task(c, p, JOBS)
    st = _tw(t, 'watch')
    kit.need(st and st['state'] == 'on', 'Không có ai lèm bèm.')
    choice = kit.one_of(p.get('choice'), TW_CHOICES['watch'], 'Chọn cách xử lý.')
    tr, who = _tr(t), _who(t)
    st.update(state='done', choice=choice)
    if choice == 'bear':
        c['xp'] += 2
        return dict(message=f'😮‍💨 Bạn nhịn, làm tiếp. {who} lèm bèm thêm một lúc rồi cũng chán. Bấm làm tiếp nhé.')
    if choice == 'refuse':
        abusive = tr['rude'] >= 65
        d['stats']['walked'] += 1
        if not abusive:
            t['mistakes'] += 1
            cq.slip(t, 'walked', 2, 'Mới nói có mấy câu mà thợ bỏ ngang, nước vẫn ngập.', 'bỏ dở việc')
        react = cq.react(s, c, t, 0, who=who)
        line = ('Bạn xin phép không làm nữa: chửi bới như vậy thì tiền nào cũng không làm. Chú Hai nghe xong gật đầu: “Đúng.”' if abusive
                else f'Bạn thu đồ nghề đi về. {who} đứng chống nạnh giữa nhà tắm ngập nước.')
        return dict(message='🎒 ' + _finish(s, c, d, t, 0, f'{line} {react["message"]}'.strip()), correct=abusive)
    how = folk.word(tr, choice)
    line = WATCH_OUT[(choice, how)].format(who=who)
    if how == 'blowup':
        t['mistakes'] += 1
        cq.slip(t, 'argue', 2 if choice == 'answer' else 1, 'Thợ đứng cãi tay đôi với chủ nhà giữa nhà tắm.', 'to tiếng với chủ nhà')
    elif how == 'sulk' and choice == 'away':
        cq.slip(t, 'offended', 1, 'Nhà mình mà bị mời ra ngoài, khó chịu ghê.', 'mời chủ nhà ra ngoài')
    if choice == 'away' and how == 'calm':
        t['patience'] = min(100, t.get('patience', 100) + 5)
    return dict(message=f'🗯️ {line} Bấm làm tiếp nhé.', correct=how != 'blowup')


def _extra(s, c, d, p):
    """"Tiện tay làm luôn": do it free, name a price, or say no."""
    t = _task(c, p, JOBS)
    st = _tw(t, 'extra')
    kit.need(st and st['state'] == 'on', 'Khách không nhờ gì thêm.')
    choice = kit.one_of(p.get('choice'), TW_CHOICES['extra'], 'Chọn cách trả lời.')
    tr, who = _tr(t), _who(t)
    if choice == 'free':
        st.update(state='done', choice='free', price=0)
        d['stats']['freebies'] += 1
        c['xp'] += 4
        return dict(message=f'🤲 Làm luôn cho vui lòng khách. {who}: “Đấy, thợ phải thế chứ!” Bấm tính tiền nhé.')
    if choice == 'refuse':
        st.update(state='done', choice='refuse', price=0)
        if folk.word(tr, 'refuse') == 'blowup':
            t['mistakes'] += 1
            cq.slip(t, 'petty', 1, 'Nhờ có tí việc cũng không giúp, keo vl.', 'từ chối việc nhỏ')
            return dict(message=f'🙅 {who}: “Có tí mà cũng không làm, keo vl!” Bấm tính tiền nhé.', correct=False)
        return dict(message=f'🙅 Nói rõ việc khác tính riêng. {who} nhún vai. Bấm tính tiền nhé.')
    price = kit.integer(p.get('price'), 1, 200)
    r = folk.judge_price(tr, EXTRA_FAIR, price, st['tries'])
    if r['kind'] == 'counter':
        st.update(tries=st['tries'] + 1, counter=r['counter'])
        return dict(message=f'🧾 {who}: “{price} xu cho có tí việc? {r["counter"]} xu thôi.”')
    if r['kind'] == 'walk':
        st.update(state='done', choice='charge', price=0, counter=None)
        return dict(message=f'🧾 {who}: “Thôi khỏi, để tôi tự làm.” Bấm tính tiền nhé.')
    st.update(state='done', choice='charge', price=price, counter=None)
    return dict(message=f'🧾 {who} gật: thêm {price} xu cho việc phụ. Làm xong bấm tính tiền nhé.')


def _nocash(s, c, d, p):
    """No cash: wait while they go to the ATM, trust them (a debt), or ask for a deposit now."""
    t = _task(c, p, JOBS)
    st = _tw(t, 'nocash')
    kit.need(st and st['state'] == 'on', 'Khách có tiền mặt mà.')
    choice = kit.one_of(p.get('choice'), TW_CHOICES['nocash'], 'Chọn cách xử lý.')
    tr, who = _tr(t), _who(t)
    st.update(state='done', choice=choice)
    if choice == 'wait':
        t['patience'] = max(25, t.get('patience', 100) - 10)
        r = _bill(s, c, d, p)
        return dict(r, message=f'🏧 Bạn đợi {who} chạy ra cây ATM đầu ngõ. {r["message"]}')
    kit.need(len(folk.open_debts(d['debts'])) < folk.DEBT_MAX, 'Sổ nợ đầy rồi: đòi bớt nợ cũ đã.')
    price = _bill_checks(s, c, d, t)
    cash = price * (tr['budget'] + 20) // 100
    now = asked = 0
    if choice == 'deposit':
        asked = kit.integer(p.get('amount'), 1, max(1, price))
        now = min(asked, cash)
    react = cq.react(s, c, t, now, who=who)
    rest = max(0, price - react['cut'] - now) if react['kind'] not in ('refuse', 'walkout') else 0
    if rest:
        d['debts'] = folk.trim_debts(d['debts'] + [folk.debt_line(f'no-{t["id"]}', _npc_index(t), who, t['id'], c['day'], rest, t['title'])])
    d['today']['earned'] += react['pay']
    head = f'💵 {who} đưa trước {react["pay"]} xu' if now else f'📒 Ghi nợ cho {who}'
    msg = _finish(s, c, d, t, react['pay'], (f'{head}, còn nợ {rest} xu. ' + react['message']).strip())
    if choice == 'deposit' and now < asked:
        msg = f'{who}: “Có {now} xu thôi à.” ' + msg
    return dict(message=msg)


def _chase(s, c, d, p):
    return folk.chase_action(s, c, ID, d['debts'], p, lambda i: PEOPLE[i][3] if 0 <= i < len(PEOPLE) else None)


# ---------------------------------------------------------------- a customer comes back for the difference
TROUBLE = ('comeback',)
COMEBACK_CHOICES = ('refund', 'part', 'explain', 'refuse')


def _comeback_open(s: dict, c: dict, d: dict) -> bool:
    tb = d['trouble']
    if tb['ev'] is not None or not c.get('open'):
        return False
    cb = next((x for x in d['comebacks'] if x['state'] == 'wait' and x['due'] <= c['day']), None)
    if not cb:
        return False
    cb['state'] = 'open'
    tb['seq'] += 1
    tb['ev'] = dict(id=f'tr-{tb["seq"]}', kind='comeback', day=c['day'], npc=cb['npc'], step=0, tries=0,
                    facts=dict(cb=cb['id'], extra=cb['extra'], who=PEOPLE[cb['npc']][0]))
    kit.log(s, c, 'surprise', f'{PEOPLE[cb["npc"]][0]} quay lại cùng ông Lộc: “Hỏi ra việc đó rẻ hơn {cb["extra"]} xu, trả lại đi!”',
            kit.npc_id(ID, cb['npc']), tb['ev']['id'])
    return True


def _trouble(s, c, d, p):
    tb = d['trouble']
    ev = tb['ev']
    kit.need(ev and ev['kind'] == 'comeback', 'Không có ai quay lại.')
    choice = kit.one_of(p.get('choice'), COMEBACK_CHOICES, 'Chọn cách giải quyết.')
    f = ev['facts']
    who, extra = f['who'], f['extra']
    tr = folk.traits(f['cb'], PEOPLE[ev['npc']][3])
    good = None
    if choice == 'refund':
        back = min(extra, c['money'])
        if back:
            kit.money(s, c, -back, f'Trả lại tiền chênh cho {who}'[:120], f['cb'], 'refund')
        d['stats']['refunds'] += back
        _street_trust(c, 1)
        good, out = True, f'Bạn trả lại {back} xu, xin lỗi. {who} dịu giọng: “Biết sai mà sửa thì còn gọi lại.”'
    elif choice == 'part':
        amount = kit.integer(p.get('amount'), 1, extra)
        want = extra * (50 + tr['stingy'] // 2) // 100
        back = min(amount, c['money'])
        if back:
            kit.money(s, c, -back, f'Trả bớt tiền chênh cho {who}'[:120], f['cb'], 'refund')
        d['stats']['refunds'] += back
        if amount >= want:
            good, out = None, f'{who} cầm {back} xu: “Thôi được, lần sau nói giá cho thật.”'
        else:
            _street_trust(c, -2)
            kit.review(s, c, kit.npc_id(ID, ev['npc']), 2, f'Chặt chém xong trả lại có {back} xu, coi như bố thí à?', f['cb'])
            good, out = False, f'{who} ném lại câu “bố thí à?” rồi bỏ đi kể khắp ngõ.'
    elif choice == 'explain':
        if tr['savvy'] < 45 and tr['rude'] < 60:
            good, out = None, f'{who} nghe giải thích một hồi, lẩm bẩm “thôi kệ” rồi về.'
        else:
            _street_trust(c, -2)
            kit.review(s, c, kit.npc_id(ID, ev['npc']), 1, 'Chặt chém rồi còn cãi lý. Cả ngõ né thợ này ra.', f['cb'])
            good, out = False, f'{who}: “Giải thích cái gì, chặt chém thì nhận đi!” Ông Lộc lắc đầu.'
    else:
        _street_trust(c, -4)
        kit.review(s, c, kit.npc_id(ID, 5), 1, f'Thợ thông cống chặt chém {who} rồi không chịu trả lại. Ai gọi thì cẩn thận.', f['cb'])
        good, out = False, f'Bạn không trả. Tối đó nhóm cư dân phường Mây có bài đăng dài về “thợ chặt chém”.'
    for x in d['comebacks']:
        if x['id'] == f['cb']:
            x['state'] = 'done'
    folk.trouble_close(tb, out, good, choice, 'Khách quay lại đòi tiền chênh', '🔁')
    return dict(message='🔁 ' + out, correct=good is not False, celebrate=good is True)


ACTIONS = {
    'cg_pack': _pack, 'cg_gear': _gear, 'cg_setout': _setout, 'cg_fetch': _fetch,
    'cg_check': _check, 'cg_diag': _diag, 'cg_quote': _quote, 'cg_safety': _safety,
    'cg_work': _work, 'cg_chem': _chem, 'cg_part': _part, 'cg_test': _test, 'cg_clean': _clean, 'cg_advise': _advise,
    'cg_giveup': _giveup, 'cg_bill': _bill, 'cg_pay': _pay,
    'cg_short': lambda s, c, d, p: _short(s, c, p),
    'cg_price': _price, 'cg_watch': _watch, 'cg_extra': _extra, 'cg_nocash': _nocash, 'cg_chase': _chase, 'cg_trouble': _trouble,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['gear'], d['out'] = [], False
    d['today'] = _fresh_today(day)
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
    # Honest debtors turn up with the money by themselves; the rest wait to be chased (the debt book).
    for note in folk.auto_repay(s, c, ID, d['debts'], lambda i: PEOPLE[i][3] if 0 <= i < len(PEOPLE) else None):
        kit.log(s, c, 'surprise', note)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    today = d['today']
    lines = [f'🛵 Làm {today["jobs"]} việc: {today["cleared"]} thông tận gốc' + (f', {today["temp"]} thông tạm.' if today['temp'] else '.')]
    if today['trips']:
        lines.append(f'🔁 Chạy về tiệm lấy đồ {today["trips"]} lần.')
    if today['overcharged']:
        lines.append(f'🧾 Chú Hai dò sổ: hôm nay nói thách khách {today["overcharged"]} xu. “Tiền đó không giữ được khách đâu con.”')
    elif today['jobs']:
        lines.append('🧾 Chú Hai dò sổ: báo giá đúng bảng giá. Tốt!')
    if today['earned']:
        lines.append(f'💵 Thu {today["earned"]} xu tiền công.')
    if desk_note:
        lines.append(desk_note)
    d['gear'], d['out'] = [], False
    return dict(lines=lines, note='Sáng mai đọc sổ hẹn rồi hẵng xếp đồ lên xe.', jobs=today['jobs'], cleared=today['cleared'],
                temp=today['temp'], earned=today['earned'], overcharged=today['overcharged'])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 80 else 4 if p >= 60 else 3 if p >= 40 else 2
    codes = {x['code'] for x in cq.slips(t)}
    if t['kind'] == 'setup':
        return dict(criteria=[dict(key='pack', label='Đồ nghề hợp việc', score=3 if 'pack' in codes else 5, note='mang đủ đồ' if 'pack' not in codes else 'thiếu đồ nghề'),
                              dict(key='gear', label='Bảo hộ', score=2 if 'no_gloves' in codes else 5, note='đeo găng tay' if 'no_gloves' not in codes else 'thiếu găng tay')])
    if t.get('cleared') not in ('full', 'temp') and not codes:
        return dict(criteria=[dict(key='honest', label='Nói thật', score=5, note='chưa làm được thì không lấy tiền'),
                              dict(key='fix', label='Thông được ống', score=2, note='hẹn thợ khác tới')])
    fix = 5 if t.get('cleared') == 'full' else 3 if t.get('cleared') == 'temp' else 1
    fix = max(1, fix - min(2, t.get('tries', 0)))
    honest = 2 if codes & {'overcharge', 'greedy', 'warranty'} else 3 if codes & {'recur', 'misquote'} else 5
    safe = 1 if codes & {'gas', 'chem_burn'} else 3 if codes & {'alone', 'barrier', 'splash', 'gear', 'bare'} else 5
    tidy = 3 if codes & {'mess', 'untested'} else 5
    return dict(criteria=[dict(key='fix', label='Thông tận gốc', score=fix, note='đúng bệnh, đúng đồ nghề' if fix == 5 else 'chưa đúng bệnh hoặc thông tạm'),
                          dict(key='honest', label='Báo giá thật', score=honest, note='đúng bảng giá, nói rõ' if honest == 5 else 'giá chưa thật'),
                          dict(key='safe', label='An toàn', score=safe, note='đủ bảo hộ' if safe == 5 else 'chưa an toàn'),
                          dict(key='tidy', label='Xả thử, dọn sạch', score=tidy, note='gọn gàng' if tidy == 5 else 'để bẩn hoặc chưa thử'),
                          dict(key='speed', label='Nhanh', score=speed, note=f'chờ còn {p}% kiên nhẫn')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return 'Sổ hẹn hôm nay: ' + '; '.join(f'{x["who"]} · {PLACES[x["place"]]["name"].lower()}' for x in n['book']) + '. ' + n['note']
    pl = PLACES[n['place']]
    old = ' · Ống gang cũ.' if n['old'] else ''
    return f'{_who(t)} · {pl["name"]}: “{t["opening"]}”{old} {n["note"]}'


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    for k in ('twist', 'tw', 'bid'):
        v.pop(k, None)
    if isinstance(t.get('bid'), dict):
        v['bid'] = dict(tries=t['bid']['tries'], counter=t['bid']['counter'])   # never whether they feel cheated
    if not v['known']:
        v['needs'] = None
        return v
    if t['kind'] != 'setup':
        v['needs']['clues'] = {k: (t['needs']['clues'][k] if k in t['checked'] else None) for k in ('hoi', 'nhin', 'xa')}
        v['camera'] = CAUSES[t['_cause']]['camera'] if 'camera' in t['checked'] else None
        v['prices'] = {lv: quote_for(lv, t['needs']['place'], t['diag'], t['kind']) for lv in LEVELS if lv != 'own'} if t['diag'] else None
    tw = t.get('twist')
    if isinstance(tw, dict) and t['tw']['state'] != 'wait':
        # A twist shows once it has started; what the person will do stays hidden.
        st = t['tw']
        line = {'watch': WATCH_LINES, 'extra': EXTRA_ASKS, 'nocash': NOCASH_LINES}[tw['kind']][tw['n']]
        v['twist'] = dict(kind=tw['kind'], state=st['state'], choice=st['choice'], price=st['price'], counter=st['counter'], line=line)
    v['cash'] = till.public(t.get('cash'))
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    tb = d['trouble']
    return dict(intro=d['intro'], bike=d['bike'], slots=BIKE_SLOTS, gear=d['gear'], out=d['out'],
                mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']), today=d['today'], stats=d['stats'],
                regulars={k: dict(v) for k, v in d['regulars'].items()}, desk=kit.desk_public(d['desk'], DESK, ID),
                debts=folk.public_debts(d['debts']), trouble=dict(ev=tb['ev'], last=tb['last']))


def content() -> dict:
    return dict(tools=TOOLS, places=PLACES, causes={k: dict(name=v['name']) for k, v in CAUSES.items()}, hows=HOW_LABEL, gear=GEAR_LABEL,
                safety=SAFETY_LABEL, levels=list(LEVELS), slots=BIKE_SLOTS, night=NIGHT, denoms=list(till.DENOMS), intro=INTRO,
                extra_fair=EXTRA_FAIR, debt_max=folk.DEBT_MAX,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    k = t.get('kind')
    if k == 'setup':
        return 'Đọc sổ hẹn → xếp tối đa 5 món đồ nghề lên xe → đeo găng tay → Lên đường.'
    if k == 'manhole':
        return 'Rào chắn → đo khí → thông gió → người canh → báo giá → múc bùn → xả thử, dọn sạch.'
    return 'Hỏi, nhìn, xả nước thử (chưa chắc thì soi camera) → ghi nguyên nhân → báo giá → thông bằng đúng đồ nghề → xả thử → dọn → dặn khách → thu tiền.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'guard':
        if t and t.get('career') == ID and t.get('kind') == 'manhole' and t['status'] not in ('completed', 'cancelled') and 'canh' not in t.get('safety', []):
            t['safety'].append('canh')
            return 'Đã đứng canh trên miệng hố ga, cầm dây an toàn.'
        return 'Đã rửa sạch dây lò xo, lau máy phun.'
    if e.get('role') == 'haul':
        return 'Đã chở bùn rác ra điểm tập kết.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu tiệm thông cống sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc thông cống không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc thông cống sai.')
    for k, allowed in (('checked', HOWS), ('tools', TOOL), ('safety', SAFETY)):
        v = t.get(k)
        kit.need(isinstance(v, list) and len(v) == len(set(v)) and all(x in allowed for x in v), 'Việc thông cống sai.')
    kit.need(t.get('diag') in (None, *CAUSES) and t.get('quoted_for') in (None, *CAUSES), 'Chẩn đoán sai.')
    kit.need(t.get('level') in (None, *LEVELS), 'Mức báo giá sai.')
    if t.get('quote') is not None:
        kit.integer(t['quote'], 0, 10 ** 5)
    kit.need(t.get('cleared') in (None, 'full', 'temp', 'fail'), 'Kết quả thông cống sai.')
    kit.integer(t.get('tries'), 0, 99)
    for k in ('part', 'chem', 'tested', 'cleaned', 'advised'):
        _vbool(t.get(k))
    till.validate(t.get('cash'), t)
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách quen sai.')
    _validate_twist(t)


def _validate_twist(t: dict) -> None:
    """0.9.16 fields: absent on older jobs; when present they must be what twist_of gives and well formed."""
    if 'twist' in t or 'tw' in t:
        tw, st = t.get('twist'), t.get('tw')
        kit.need(tw is not None and tw == twist_of(t), 'Chuyện của khách không khớp.')
        kit.need(isinstance(st, dict) and set(st) == {'state', 'choice', 'price', 'counter', 'tries'} and st['state'] in TW_STATES
                 and st['choice'] in (None, *TW_CHOICES[tw['kind']]), 'Chuyện của khách sai.')
        for k in ('price', 'counter'):
            if st[k] is not None:
                kit.integer(st[k], 0, 500)
        kit.integer(st['tries'], 0, 9)
    if 'bid' in t:
        b = t['bid']
        kit.need(isinstance(b, dict) and set(b) == {'tries', 'counter', 'ratio', 'grudge'}, 'Giá tự báo sai.')
        kit.integer(b['tries'], 0, 9)
        for k in ('counter', 'ratio'):
            if b[k] is not None:
                kit.integer(b[k], 0, 10 ** 5)
        _vbool(b['grudge'])


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    _vbool(d['out'])
    till.validate_book(c)
    kit.need(isinstance(d['bike'], list) and len(d['bike']) <= BIKE_SLOTS and len(set(d['bike'])) == len(d['bike']) and set(d['bike']) <= set(TOOL), 'Đồ trên xe sai.')
    kit.need(isinstance(d['gear'], list) and len(set(d['gear'])) == len(d['gear']) and set(d['gear']) <= set(GEAR), 'Đồ bảo hộ sai.')
    kit.need(isinstance(d['temp_fixes'], list) and len(d['temp_fixes']) <= 10, 'Sổ thông tạm sai.')
    for x in d['temp_fixes']:
        kit.need(isinstance(x, dict) and x.get('cause') in CAUSES, 'Sổ thông tạm sai.')
        kit.integer(x.get('day'), 1, 10 ** 7)
        kit.text(x.get('task'), 60)
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu tiệm sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)
    folk.validate_debts(d['debts'], len(PEOPLE), kit.need)
    folk.validate_trouble(d['trouble'], TROUBLE, kit.need)
    kit.need(isinstance(d['comebacks'], list) and len(d['comebacks']) <= 8, 'Sổ khách quay lại sai.')
    for x in d['comebacks']:
        kit.need(isinstance(x, dict) and set(x) == {'id', 'task', 'npc', 'due', 'extra', 'state'} and x['state'] in ('wait', 'open', 'done'), 'Sổ khách quay lại sai.')
        kit.integer(x['npc'], 0, len(PEOPLE) - 1)
        kit.integer(x['due'], 1, 10 ** 7)
        kit.integer(x['extra'], 1, 10 ** 5)
        kit.text(x['id'], 80)
        kit.text(x['task'], 60)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='cg_', category='service',
    meta=dict(short='Thông ống cống', place='Thông cống chú Hai', tagline='Đúng bệnh, đúng đồ nghề, đúng giá.', icon='wrench',
              color='#3f6f8f', light='#e3eef5', weather='Nắng, nước cống rút ào ào', work='Việc gọi', station='Hộp đồ nghề',
              greeting='Đọc sổ hẹn, xếp đồ nghề lên xe. Tới nơi thì hỏi, nhìn, xả nước thử, báo giá rồi mới làm nhé.',
              caption='Mỗi đường ống một căn bệnh', map_label='21 · THÔNG CỐNG CHÚ HAI'),
    people=PEOPLE,
    staff=[('Tâm', 'guard', 'Cẩn thận, đứng canh miệng hố ga không rời mắt.', 76, 92),
           ('Lực', 'haul', 'Khỏe, xách hai xô bùn một lúc.', 86, 74),
           ('Vy', 'guard', 'Học an toàn lao động, luôn mang máy đo khí.', 72, 94),
           ('Sơn', 'haul', 'Thuộc hết ngõ ngách, chạy về tiệm nhanh như chớp.', 84, 78)],
    roles={'guard': 'Canh an toàn', 'haul': 'Chở đồ'},
    inventory=dict(items=ITEMS, capacity=20),
    tip=2,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('🧰', 'Hộp đồ nghề', [('Pít-tông', 'Bồn cầu tắc gần'), ('Dây lò xo', 'Tóc trong thoát sàn'), ('Máy phun', 'Mỡ đông'), ('Máy đo khí', 'Hố ga')],
              ['Đọc sổ hẹn, xếp đồ', 'Hỏi, nhìn, xả nước thử', 'Báo giá, thông đúng đồ', 'Xả thử, dọn sạch, dặn khách']),
    stories=[('Cuộn dây lò xo của chú Hai', ('Cuộn dây lò xo đã theo chú Hai hai mươi năm, mòn bóng ở chỗ tay cầm.',
                                            'Chú dạy bạn nghe tiếng nước: ọc ọc là thiếu hơi, ì ạch là tắc xa.',
                                            'Lần đầu bạn tự đoán đúng bệnh, chú Hai tặng lại cuộn dây cũ.')),
             ('Hố ga đầu ngõ', ('Trời sắp mưa, hố ga đầu ngõ đầy bùn đen.',
                                'Chú Hai bắt cả tổ đo khí, bật quạt, đứng canh rồi mới cho xuống.',
                                'Cơn mưa tới, nước rút ào ào. Ông Lộc đứng dưới ô, giơ ngón cái.')),
             ('Bảng giá dán trong hộp đồ nghề', ('Trong nắp hộp đồ nghề dán tờ bảng giá viết tay, chữ đã mờ.',
                                                 'Chú Hai bảo: “Giá nào việc nấy, không đổi theo mặt khách.”',
                                                 'Bạn chép lại tờ bảng giá mới, dán cạnh tờ cũ.'))],
    review_asides=['Đoán bệnh trúng phóc, thông một phát ăn ngay.', 'Báo giá rõ ràng, làm xong đúng giá.', 'Dọn sạch sẽ như chưa từng tắc.',
                   'Dặn dò kỹ, cả tháng không tắc lại.'],
    situations=SITUATIONS,
    guide='Sáng: đọc sổ hẹn, xếp đồ nghề lên xe. Mỗi việc: hỏi, nhìn, xả thử (hoặc soi camera) → ghi nguyên nhân → báo giá → thông đúng đồ nghề → xả thử → dọn → dặn khách → thu tiền.',
)
