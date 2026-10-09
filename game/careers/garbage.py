"""Tổ thu gom rác phường Mây: the evening rubbish round with a hand cart (plugin career).

Chị Hạnh leads the ward's collection crew; the player pushes the cart. What the job is:

* the start of the shift (``setup`` task): put on the gloves, the mask, the reflective vest and,
  on a wet evening, the boots; check the cart (tyre, lid) and bring it out. Gloves and masks are
  used up (one of each per shift, bought in the storeroom);
* a round (``route`` task) is one lane: a few houses, each with one to three bags put out by the
  door. Households sort by bag colour (green organic, yellow recyclable, black the rest), but not
  everyone does it right: a battery in the green bag, food in the yellow one, broken glass loose
  in the black one, a needle or a fluorescent tube poking out. The player reads what shows from
  outside, opens the bags that look wrong, pulls hazardous things into the red box (never a needle
  bare-handed), wraps broken glass, loads each bag into the right compartment of the cart and
  leaves a friendly reminder at the houses that did not sort. Every lane has its collection
  time: pushing into it late means bags torn open by cats and a street to sweep;
* the cart has three compartments that fill up: push it to the collection point (``rac_dump``)
  where the compactor takes the rest and cô Tám buys the clean recyclables (ve chai money);
  dirty recyclables are worth nothing to her;
* residents' complaints (``complaint`` tasks): a missed bag, rubbish dumped at night on the
  corner, the smell of the cart stand, a food stall that will not sort. Look into it, then answer
  the way that is fair and true;
* surprises on the round and a book of the crew's small stories;
* the awkward people (0.9.16): a razor or needle hidden in a bag that looks fine, a heap dumped at the end
  of the lane, a resident who will not sort and picks a fight (the player may refuse the bag, by the
  rules), vandals and a collection point overflowing at night, and the monthly fee: households that
  haggle, make excuses or refuse, and the player names the amount and the tone.

The crew is paid per round by the ward's cooperative (money through the engine's money() and the
reviewer's reaction in consequences.react); mistakes go through cq.slip.
Everything random is rolled from the day, slot or task id.
"""
from __future__ import annotations

import copy
import hashlib

from ..jsoncopy import tree_copy
from . import kit
from . import street_folk as folk
from .. import consequences as cq
from .. import inventory as inv

ID = 'garbage'
GEN = 1

BINS = ('huu_co', 'tai_che', 'con_lai')
BIN_LABEL = {'huu_co': 'Hữu cơ', 'tai_che': 'Tái chế', 'con_lai': 'Còn lại', 'nguy_hai': 'Nguy hại'}
BIN_EMOJI = {'huu_co': '🟢', 'tai_che': '🟡', 'con_lai': '⚫', 'nguy_hai': '🔴'}
CART = {'huu_co': 8, 'tai_che': 8, 'con_lai': 10}
HAZ_MAX = 8
COLOR_BIN = {'xanh': 'huu_co', 'vang': 'tai_che', 'den': 'con_lai'}
COLOR_LABEL = {'xanh': 'Túi xanh', 'vang': 'Túi vàng', 'den': 'Túi đen'}
VE_CHAI = 2                # xu cô Tám pays for a clean bag of recyclables
ROUTE_PAY, STOP_PAY = 14, 3
CASE_PAY = 6
GEAR = ('gang_tay', 'khau_trang', 'ao', 'ung')
GEAR_LABEL = {'gang_tay': 'Găng tay', 'khau_trang': 'Khẩu trang', 'ao': 'Áo phản quang', 'ung': 'Ủng'}
USED = ('gang_tay', 'khau_trang')        # used up each shift, from the storeroom

# id: (name, emoji, where it belongs, sharp)
WASTE = {
    'vo_trai': ('Vỏ trái cây', '🍌', 'huu_co', False), 'rau_ua': ('Rau úa, lá cây', '🥬', 'huu_co', False),
    'com_thua': ('Cơm canh thừa', '🍚', 'huu_co', False), 'ba_cafe': ('Bã cà phê, bã trà', '☕', 'huu_co', False),
    'chai_nhua': ('Chai nhựa', '🧴', 'tai_che', False), 'lon': ('Lon nhôm', '🥫', 'tai_che', False),
    'giay': ('Giấy, thùng các-tông', '📦', 'tai_che', False), 'chai_tt': ('Chai thủy tinh', '🍾', 'tai_che', False),
    'nilon': ('Túi ni-lông bẩn', '🛍️', 'con_lai', False), 'ta': ('Tã giấy', '🧻', 'con_lai', False),
    'xop': ('Hộp xốp dính dầu', '🥡', 'con_lai', False), 'kinh_vo': ('Mảnh kính vỡ', '🪟', 'con_lai', True),
    'pin': ('Pin cũ', '🔋', 'nguy_hai', False), 'bong_den': ('Bóng đèn tuýp', '💡', 'nguy_hai', True),
    'binh_xit': ('Vỏ bình xịt côn trùng', '🧯', 'nguy_hai', False), 'kim_tiem': ('Kim tiêm', '💉', 'nguy_hai', True),
    'dao_lam': ('Lưỡi dao lam', '🔪', 'nguy_hai', True),   # only ever hidden in a bag (a 0.9.16 'sharp' twist)
}
MAIN = {'huu_co': ('vo_trai', 'rau_ua', 'com_thua', 'ba_cafe'), 'tai_che': ('chai_nhua', 'lon', 'giay', 'chai_tt'),
        'con_lai': ('nilon', 'ta', 'xop')}
# What a wrong item looks like from outside the bag.
CLUE = {'pin': 'Túi nặng bất thường, kêu lọc cọc.', 'bong_den': 'Một ống dài màu trắng thò ra miệng túi.',
        'binh_xit': 'Sờ thấy một vỏ lon tròn cứng, có mùi thuốc xịt.', 'kim_tiem': 'Lấp ló một cái nắp nhựa nhỏ màu cam.',
        'kinh_vo': 'Góc túi bị thủng, có cạnh sắc lòi ra.', 'com_thua': 'Túi rỉ nước, bốc mùi chua.',
        'chai_nhua': 'Túi phồng, sột soạt tiếng nhựa.', 'lon': 'Túi kêu leng keng tiếng lon.', 'ta': 'Túi nặng, mùi khai.'}
NEAT = ('Túi buộc gọn, đúng màu.', 'Túi cột chặt, khô ráo.', 'Túi nhẹ, buộc kỹ.')
# (wrong item, bag colour): the ways households get it wrong, the easy ones first.
WRONGS = [('chai_nhua', 'xanh'), ('com_thua', 'vang'), ('lon', 'den'), ('pin', 'xanh'), ('kinh_vo', 'den'),
          ('pin', 'den'), ('bong_den', 'den'), ('binh_xit', 'vang'), ('ta', 'vang'), ('kim_tiem', 'den')]

ITEMS = [
    dict(id='gang_tay', name='Găng tay cao su dày', emoji='🧤', group='gear', unit='đôi', cost=2, life=90, start=5),
    dict(id='khau_trang', name='Khẩu trang', emoji='😷', group='gear', unit='cái', cost=1, life=90, start=6),
    dict(id='bao', name='Bao bọc mảnh vỡ', emoji='🧷', group='gear', unit='cái', cost=1, life=180, start=8),
]

PEOPLE = [
    ('Chị Hạnh', 'Tổ trưởng tổ thu gom', 'Đẩy xe rác mười hai năm, thuộc từng nhà, từng con chó trong phường.', 'warm'),
    ('Bác Tâm', 'Tổ trưởng dân phố ngõ 12', 'Cầm sổ ghi chép mọi chuyện trong ngõ, nói một là một.', 'bossy'),
    ('Cô Lài', 'Chủ quán cơm bình dân', 'Tối nào cũng ra ba bao rác to, vội quá hay đổ chung.', 'picky'),
    ('Ông Thước', 'Cụ ông nhà số 7', 'Về hưu, đứng cửa canh xe rác, hay phàn nàn chuyện mùi.', 'sour'),
    ('Cô Tám', 'Thu mua ve chai', 'Đạp xe ba gác đi khắp phường, cân giấy, lon, chai nhựa.', 'quiet'),
    ('Anh Khôi', 'Nhân viên văn phòng', 'Về muộn, hay xách túi rác chạy theo xe.', 'quiet'),
    ('Bé Na', 'Học sinh lớp 8, đội “Phố xanh”', 'Hăng hái đi dán tờ hướng dẫn phân loại rác.', 'genz'),
    ('Chú Sáu', 'Tài xế xe ép rác', 'Xe tới điểm tập kết đúng giờ, không chờ ai.', 'bossy'),
]

MODS = [
    dict(id='normal', emoji='🌙', label='Tối thường', hint='Ngõ yên, rác vừa phải. Hợp để làm quen.', weight=3),
    dict(id='rain', emoji='🌧️', label='Mưa tối', hint='Đường trơn, túi rác ướt: mang ủng, buộc túi kỹ.', min_day=2, weight=2),
    dict(id='heat', emoji='🥵', label='Oi nồng', hint='Rác hữu cơ bốc mùi nhanh: đeo khẩu trang, đi đúng giờ.', min_day=2, weight=2),
    dict(id='party', emoji='🎉', label='Ngõ có đám cưới', hint='Nhiều chai lọ, vỏ lon: ngăn tái chế mau đầy.', min_day=3, weight=1),
]
MOD = {m['id']: m for m in MODS}

LANES = [
    dict(id='ngo12', name='Ngõ 12 Hàng Mây', npc=1, houses=('Nhà bác Tâm', 'Nhà số 5', 'Nhà ông Thước', 'Nhà số 9', 'Nhà có giàn hoa giấy')),
    dict(id='cho', name='Dãy hàng quán đầu chợ', npc=2, houses=('Quán cơm cô Lài', 'Tiệm tạp hóa', 'Xe bánh mì', 'Quán nước mía', 'Tiệm sửa xe')),
    dict(id='tapthe', name='Khu tập thể B2', npc=3, houses=('Cầu thang số 1', 'Nhà ông Thước', 'Cầu thang số 2', 'Phòng bảo vệ', 'Cầu thang số 3')),
    dict(id='hem5', name='Hẻm 5 bờ kênh', npc=5, houses=('Nhà trọ sinh viên', 'Nhà anh Khôi', 'Nhà bé Na', 'Nhà số 14', 'Tiệm giặt ủi')),
]
LANE = {x['id']: x for x in LANES}
WINDOWS = {1: 19 * 60 + 30, 2: 21 * 60, 3: 22 * 60, 4: 22 * 60 + 30}   # the lane's collection time ends (minute of day)

CASES = [
    dict(id='missed', npc=3, title='Ông Thước kêu sót rác', opening='Tối qua xe rác bỏ sót túi nhà tôi! Để nguyên trước cửa, chó mèo bới tung!',
         facts=[dict(id='time', title='Giờ ông đổ rác', text='Hàng xóm kể ông Thước mang túi ra lúc gần mười giờ đêm, xe đã qua từ tám giờ.'),
                dict(id='bag', title='Túi rác', text='Túi đen buộc lỏng, bị bới tung một góc, vẫn còn trước cửa.'),
                dict(id='sign', title='Bảng giờ thu gom', text='Đầu ngõ có bảng: “Đổ rác từ 18:00 đến 19:30”.')],
         options=[dict(id='collect', label='Thu luôn túi rác, nhẹ nhàng nhắc giờ thu gom', requires=('time', 'bag'), q='good',
                       outcome='Ông Thước lầm bầm, nhưng từ hôm sau mang rác ra đúng giờ.'),
                  dict(id='explain', label='Giải thích ông đổ muộn, hẹn tối nay thu', requires=('time',), q='ok',
                       outcome='Ông Thước im lặng, túi rác nằm thêm một ngày trước cửa.'),
                  dict(id='blame', label='“Ông đổ muộn thì ông tự chịu!”', q='bad', outcome='Ông Thước lên phường phản ánh tổ thu gom thái độ.')]),
    dict(id='dump', npc=1, title='Bác Tâm báo đổ trộm', opening='Góc ngõ sáng nay có ai đổ nguyên đống xà bần với cái nệm cũ. Tổ thu gom xử lý đi!',
         facts=[dict(id='what', title='Đống rác', text='Gạch vụn, vữa, một tấm nệm mục: rác xây dựng và rác cồng kềnh.'),
                dict(id='rule', title='Quy định', text='Xà bần, đồ cồng kềnh phải đặt lịch thu riêng, không cho vào xe ép rác sinh hoạt.'),
                dict(id='who', title='Ai đổ', text='Chưa ai thấy người đổ. Có nhà trong ngõ đang sửa bếp.')],
         options=[dict(id='report', label='Chụp ảnh, báo phường, dán thông báo, hẹn xe thu riêng', requires=('what', 'rule'), q='good',
                       outcome='Phường cho xe tải nhỏ tới dọn. Bác Tâm dán thêm biển “Camera giám sát”.'),
                  dict(id='haul', label='Hốt hết lên xe đẩy cho nhanh', q='bad', hurt=True,
                       outcome='Gạch vụn làm kẹt lưỡi ép của xe, chú Sáu phải dừng xe gỡ cả tiếng.'),
                  dict(id='accuse', label='Đổ cho nhà đang sửa bếp', requires=('who',), q='bad',
                       outcome='Nhà kia nổi giận, hai bên cãi nhau to. Hóa ra họ thuê xe chở xà bần đàng hoàng.')]),
    dict(id='smell', npc=3, title='Mùi ở chỗ đậu xe rác', opening='Xe rác đậu ngay trước nhà tôi cả buổi, hôi không chịu nổi!',
         facts=[dict(id='spot', title='Chỗ đậu xe', text='Xe đẩy đậu sát cửa nhà ông Thước vì chỗ đó bằng phẳng.'),
                dict(id='water', title='Nước rỉ', text='Dưới gầm xe có vũng nước rỉ từ rác hữu cơ.'),
                dict(id='alt', title='Chỗ khác', text='Cách đó mười bước có góc tường trống, xa cửa sổ nhà dân.')],
         options=[dict(id='wash', label='Rửa sạch chỗ đậu, dời xe ra góc tường, đậy nắp kín', requires=('water', 'alt'), q='good',
                       outcome='Ông Thước ra xem, gật đầu. Tối đó mùi đỡ hẳn.'),
                  dict(id='move', label='Dời xe đi chỗ khác', requires=('spot',), q='ok', outcome='Đỡ mùi, nhưng vũng nước rỉ vẫn còn đó.'),
                  dict(id='argue', label='“Rác nhà ông cũng ở trong xe đấy!”', q='bad', outcome='Ông Thước đóng sầm cửa, sáng mai gửi đơn lên phường.')]),
    dict(id='stall', npc=2, title='Quán cơm không chịu phân loại', opening='Cô Lài xua tay: “Quán cô bận lắm, đổ chung hết vào ba bao, con lấy giùm đi!”',
         facts=[dict(id='bags', title='Ba bao rác', text='Cơm thừa lẫn chai nhựa, lon bia, hộp xốp, nước canh rỉ ra.'),
                dict(id='rule', title='Quy định', text='Từ năm nay hộ kinh doanh phải phân loại rác; không phân loại có thể bị từ chối thu gom.'),
                dict(id='help', title='Cách làm gọn', text='Chỉ cần ba thùng có nắp ở góc bếp, dán nhãn màu: hữu cơ, tái chế, còn lại.')],
         options=[dict(id='guide', label='Hướng dẫn cô Lài cách để ba thùng, tối nay nhận tạm, hẹn tối mai', requires=('rule', 'help'), q='good',
                       outcome='Tối hôm sau quán cơm đã có ba thùng dán nhãn. Cô Lài còn dặn nhân viên làm theo.'),
                  dict(id='refuse', label='Từ chối thu, dán giấy nhắc quy định', requires=('rule',), q='ok',
                       outcome='Đúng quy định, nhưng ba bao rác nằm lại trước quán, bốc mùi cả đêm.'),
                  dict(id='take', label='Lấy luôn cho xong chuyện', q='bad', outcome='Cô Lài vui, nhưng từ đó tối nào cũng đổ chung.')]),
    dict(id='needle', npc=6, title='Kim tiêm ở bồn cây', opening='Anh ơi, bồn cây đầu ngõ có mấy cái kim tiêm, tụi em nhỏ hay ngồi chơi ở đó!',
         facts=[dict(id='count', title='Bồn cây', text='Ba ống kim tiêm, một cái còn nguyên kim trần, lẫn trong lá khô.'),
                dict(id='kids', title='Người qua lại', text='Chiều nào lũ trẻ cũng ngồi bệt ở bồn cây chơi bi.'),
                dict(id='tool', title='Đồ nghề', text='Trên xe có kẹp gắp và hộp nhựa cứng có nắp cho đồ sắc nhọn.')],
         options=[dict(id='tongs', label='Đeo găng, dùng kẹp gắp bỏ vào hộp cứng, báo trạm y tế', requires=('count', 'tool'), q='good',
                       outcome='Bồn cây sạch. Trạm y tế phường cử người ra xem lại cả khu vườn hoa.'),
                  dict(id='sweep', label='Quét luôn vào xe cùng lá khô', q='bad', hurt=True,
                       outcome='Kim đâm thủng bao, suýt trúng tay chú Sáu lúc đổ rác vào xe ép.'),
                  dict(id='later', label='Căng dây chắn, hẹn mai xử lý', requires=('kids',), q='ok',
                       outcome='Tạm an toàn qua đêm, nhưng sáng sớm vẫn có đứa trẻ chui qua dây.')]),
    dict(id='wallet', npc=5, title='Anh Khôi tìm ví', opening='Anh lỡ vứt nhầm cái ví trong túi rác tối qua, có thẻ ngân hàng với giấy tờ!',
         facts=[dict(id='found', title='Ở điểm tập kết', text='Chị Hạnh nhớ có một cái ví da nâu rơi ra từ túi đen, đã cất vào hộc xe.'),
                dict(id='check', title='Giấy tờ', text='Trong ví có căn cước tên Nguyễn Minh Khôi, 60 xu tiền mặt.'),
                dict(id='rule', title='Cách làm', text='Của rơi trả lại phải có người chứng kiến, đối chiếu giấy tờ.')],
         options=[dict(id='return', label='Đối chiếu căn cước, trả ví trước mặt chị Hạnh', requires=('found', 'check'), q='good',
                       outcome='Anh Khôi rối rít cảm ơn, gửi cả tổ mấy chai nước mát.'),
                  dict(id='hand', label='Đưa luôn cái ví cho anh', requires=('found',), q='ok', outcome='Anh Khôi nhận ví. Không ai đối chiếu, may mà đúng người.'),
                  dict(id='deny', label='Bảo không thấy, cho khỏi rắc rối', q='bad', outcome='Hôm sau chị Hạnh biết chuyện, buồn lắm.')]),
]
CASE = {x['id']: x for x in CASES}

KINDS = ('setup', 'route', 'complaint')
STAGES = ('prep', 'round', 'done')

# The crew's small stories: one line per finished job with that person, on and on across days.
REG_STORY = {
    1: ('Bác Tâm: “Ngõ này sạch nhất phường là nhờ tổ thu gom đấy.”', 'Bác Tâm dán bảng giờ đổ rác mới, chữ to rõ.',
        'Bác Tâm đề nghị phường khen tổ thu gom cuối năm.'),
    2: ('Cô Lài: “Quán đông quá, cô quên mất phân loại.”', 'Cô Lài đặt thêm ba thùng rác có nắp ở góc bếp.',
        'Cô Lài gửi tổ thu gom hộp cơm sườn nóng hổi.'),
    3: ('Ông Thước: “Ngày xưa ngõ này làm gì có xe rác đâu.”', 'Ông Thước kể hồi trẻ làm công nhân nhà máy giấy.',
        'Ông Thước đứng đầu ngõ, giơ tay chào xe rác.'),
    5: ('Anh Khôi: “Anh về muộn quá, cho anh gửi túi rác với!”', 'Anh Khôi đặt báo thức giờ đổ rác trên điện thoại.',
        'Anh Khôi rủ cả nhà trọ phân loại rác.'),
    6: ('Bé Na khoe tờ rơi “Phân loại rác tại nguồn” tự vẽ.', 'Bé Na được thầy giáo khen trước cờ.',
        'Bé Na theo xe một tối, ghi chép làm báo tường.'),
}

INTRO = dict(
    title='Giới thiệu nghề: thu gom rác khu phố',
    lead='Một chiếc xe đẩy ba ngăn, bộ đồ bảo hộ và những con ngõ lúc lên đèn. Chị Hạnh đẩy xe rác mười hai năm, tối nay bạn đi cùng chị.',
    work=[('🧤', 'Vào ca: găng tay, khẩu trang, áo phản quang, trời mưa thì ủng'), ('🛒', 'Kiểm xe đẩy: bánh xe, nắp ngăn'),
          ('🏠', 'Đi từng nhà trong ngõ, đúng giờ thu gom'), ('👀', 'Nhìn túi, túi nào lạ thì mở ra xem'),
          ('🔋', 'Tách pin, bóng đèn, kim tiêm vào hộp nguy hại'), ('🟢', 'Bỏ túi vào đúng ngăn: hữu cơ, tái chế, còn lại'),
          ('📝', 'Nhắc nhà chưa phân loại, nói nhẹ nhàng'), ('🚛', 'Đẩy ra điểm tập kết đổ xe, bán ve chai sạch')],
    meet=[('🧹', 'Chị Hạnh: tổ trưởng, thuộc từng nhà'), ('📒', 'Bác Tâm: tổ trưởng dân phố'), ('🍚', 'Cô Lài: quán cơm hay đổ chung'),
          ('👴', 'Ông Thước: hay phàn nàn chuyện mùi'), ('♻️', 'Cô Tám ve chai: mua đồ tái chế sạch'), ('🚛', 'Chú Sáu: xe ép rác đúng giờ'),
          ('🌧️', 'Mưa tối, oi nồng, đổ trộm, kim tiêm, chó sủa')],
    stars=[('🧤', 'Đủ đồ bảo hộ, không tay trần với đồ sắc'), ('🟢', 'Đúng ngăn, không trộn lẫn'), ('🔴', 'Tách đồ nguy hại'),
           ('⏰', 'Đúng giờ, không để rác qua đêm'), ('🙏', 'Nhắc khéo, không cãi dân'), ('🧹', 'Rơi vãi thì quét sạch')],
)

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='bike', title='Xe máy lao vào ngõ tối', emoji='🏍️', npc=0, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Một chiếc xe máy phóng nhanh vào ngõ, đèn pha chói lóa, đúng lúc bạn đang kéo xe rác ra giữa lối.',
         options=[dict(id='wall', label='Kéo xe sát tường, giơ tay ra hiệu', hint='', effects=dict(xp=4, vest=1), good=True,
                       outcome='Người lái phanh kịp, lí nhí xin lỗi rồi đi chậm lại.'),
                  dict(id='shout', label='Hét lên cho người lái nghe', hint='', effects=dict(patience=-3, vest=1), good=None,
                       outcome='Người lái giật mình, loạng choạng nhưng không sao. Tim bạn đập thình thịch.'),
                  dict(id='freeze', label='Đứng yên giữa ngõ', hint='', effects=dict(patience=-6, vest=2), good=False,
                       outcome='Xe máy lách sát, móc vào góc xe rác làm đổ một bao.')],
         default='freeze'),
    dict(id='dog', title='Chó nhà ai xổng ra', emoji='🐕', npc=1, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Một con chó to chạy ra sủa ầm, cắn xé túi rác đầu ngõ, vương vãi khắp nơi.',
         options=[dict(id='owner', label='Đứng yên, gọi chủ nhà ra giữ chó', hint='Chờ một chút', effects=dict(patience=-4, xp=3), good=True,
                       outcome='Chủ nhà chạy ra xích chó, xin lỗi rồi cầm chổi quét cùng.'),
                  dict(id='shoo', label='Vung chổi đuổi', hint='', effects={}, luck=dict(p=0.5,
                       win=dict(effects={}, good=None, outcome='Con chó bỏ chạy. Bạn quét lại chỗ rác vương vãi.'),
                       lose=dict(effects=dict(patience=-8), good=False, outcome='Con chó càng hung, bạn phải lùi lại chờ mãi.'))),
                  dict(id='leave', label='Bỏ qua túi đó, đi tiếp', hint='', effects=dict(review=[2, 'Chó bới rác tung tóe mà tổ thu gom bỏ đi luôn.']), good=False,
                       outcome='Sáng hôm sau đầu ngõ ngập rác vương vãi.')],
         default='leave'),
    dict(id='treasure', title='Nhẫn vàng trong túi rác', emoji='💍', npc=0, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Lúc buộc lại túi rác rách, bạn thấy một chiếc nhẫn vàng nhỏ lẫn trong vỏ trái cây.',
         options=[dict(id='return', label='Cất kỹ, báo chị Hạnh, hỏi nhà vừa đổ rác', hint='', effects=dict(xp=6), good=True,
                       outcome='Bà cụ nhà số 5 khóc òa: nhẫn cưới của bà rơi lúc gọt trái cây. Cả ngõ khen tổ thu gom.'),
                  dict(id='post', label='Đăng lên nhóm cư dân tìm chủ', hint='', effects=dict(xp=3), good=None,
                       outcome='Có ba người nhận là của mình. Mãi mới tìm đúng bà cụ nhà số 5.'),
                  dict(id='keep', label='Bỏ túi, không ai biết', hint='Của trời cho?', effects=dict(review=[1, 'Nghe nói nhẫn cưới của bà cụ rơi vào rác, tổ thu gom nhặt được mà im.']),
                       good=False, outcome='Mấy hôm sau chuyện lộ ra. Chị Hạnh buồn, không nói một lời.')],
         default='return'),
    dict(id='flood', title='Mưa to, cống ngập', emoji='🌊', npc=1, min_day=2, tone='tense', at='between', weight=3, mods=('rain',),
         text='Mưa như trút, nước dâng lên ngang mắt cá. Mấy túi rác trôi lềnh bềnh, chặn ngay miệng cống.',
         options=[dict(id='clear', label='Vớt rác chắn miệng cống cho nước rút', hint='Ướt hết người', effects=dict(patience=-4, xp=5), good=True,
                       outcome='Nước rút ào xuống cống. Bác Tâm cầm ô đứng xem, gật đầu.'),
                  dict(id='wait', label='Trú mưa, chờ tạnh rồi làm', hint='', effects=dict(patience=-6), good=None,
                       outcome='Mưa tạnh, rác đã trôi ra tận đầu ngõ. Phải đi gom lại từng túi.'),
                  dict(id='go', label='Mặc kệ, đẩy xe về', hint='', effects=dict(review=[2, 'Mưa ngập mà rác chắn cống, tổ thu gom đi thẳng.']), good=False,
                       outcome='Nước ngập vào mấy nhà đầu ngõ. Sáng mai có người gọi thợ thông cống.')],
         default='wait'),
    dict(id='tip', title='Quán nhậu nhờ lấy rác ngoài', emoji='🍻', npc=2, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Chủ quán nhậu đầu ngõ dúi 10 xu: “Lấy giùm anh mười bao đồ chưa phân loại, khỏi ghi sổ phí nha!”',
         options=[dict(id='rule', label='Từ chối tiền, hướng dẫn đăng ký thu gom theo khối lượng', hint='', effects=dict(xp=4), good=True,
                       outcome='Chủ quán cằn nhằn, nhưng hôm sau ra phường đăng ký hợp đồng thu gom.'),
                  dict(id='take', label='Nhận tiền, lấy hết cho xong', hint='Thêm 10 xu…', effects=dict(money=10, review=[2, 'Tổ thu gom nhận tiền ngoài, rác quán nhậu đổ chung hết.']),
                       good=False, outcome='Xe đầy ứ, ngăn tái chế lẫn nước bia. Chị Hạnh cau mày.')],
         default='rule'),
    dict(id='water', title='Bà cụ mời nước', emoji='🥤', npc=0, min_day=2, tone='gentle', at='between', weight=1, mods=('heat', 'normal'),
         text='Bà cụ nhà có giàn hoa giấy chờ sẵn ở cửa với hai chai nước mát: “Nóng thế này, uống đi các cháu.”',
         options=[dict(id='thank', label='Cảm ơn bà, uống nước rồi làm tiếp', hint='', effects=dict(xp=3), good=True,
                       outcome='Nước mát lạnh. Bà cụ bảo tối nào cũng nghe tiếng xe rác là biết giờ đi ngủ.'),
                  dict(id='hurry', label='Cảm ơn, xin mang theo vì đang vội', hint='', effects={}, good=None,
                       outcome='Bà cụ cười, dặn đi đường cẩn thận.')],
         default='thank'),
]

# The awkward people on the round (0.9.16): more surprises, each with its own way out.
DESK += [
    dict(id='rubble', title='Túi rác nặng trịch xà bần', emoji='🧱', npc=1, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Nhà đang sửa nhét gạch vụn vào túi đen, buộc chặt, đặt cạnh thùng rác. Nhấc lên rách toạc, gạch văng đầy chân.',
         options=[dict(id='sticker', label='Dán phiếu: xà bần phải thuê xe riêng, để lại', hint='', effects=dict(xp=4), good=True,
                       outcome='Sáng hôm sau chủ nhà gọi xe ba gác chở đi, còn xin lỗi tổ thu gom.'),
                  dict(id='take', label='Khuân lên xe cho xong', hint='Nặng, dễ hỏng xe', effects=dict(money=-5, patience=-4), good=False,
                       outcome='Gạch làm cong thanh chắn ngăn xe, sửa mất 5 xu. Chú Sáu càu nhàu vì xe ép kêu rắc rắc.'),
                  dict(id='leave', label='Để nguyên, đi tiếp', hint='', effects=dict(review=[2, 'Túi rác nhà tôi để nguyên không ai lấy, tổ thu gom làm ăn kiểu gì?']), good=None,
                       outcome='Túi xà bần nằm chềnh ềnh trước cửa thêm ba ngày.')],
         default='leave'),
    dict(id='dead_rat', title='Con chuột chết trong túi', emoji='🐀', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=('heat', 'normal', 'rain'),
         text='Mở túi rác nhà ông Thước ra, một con chuột chết đã trương, ruồi bay ra kín mặt. Ông đứng cửa: “Thì rác chứ sao, lấy đi!”',
         options=[dict(id='bag', label='Đeo khẩu trang, bọc hai lớp bao, bỏ ngăn còn lại', hint='Tốn một bao', effects=dict(stock={'bao': -1}, xp=3), good=True,
                       outcome='Gọn gàng, không ai bị gì. Ông Thước lần đầu nói câu “cảm ơn cháu”.'),
                  dict(id='hold', label='Nín thở xách luôn', hint='', effects=dict(patience=-3), good=None, outcome='Mùi bám tay tới tận sáng.'),
                  dict(id='back', label='“Ông bọc lại cho kỹ rồi hãy đem ra”', hint='', effects=dict(review=[2, 'Có con chuột chết mà công nhân cũng làm khó.']), good=False,
                       outcome='Ông Thước sập cửa, sáng mai gọi lên phường.')],
         default='hold'),
    dict(id='late_lady', title='Bà cụ gọi lúc mười một giờ đêm', emoji='☎️', npc=0, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Chị Hạnh chuyển máy: bà cụ nhà số 9 gọi, giọng run run: “Bà quên đổ rác, cháu quay lại lấy giúp bà được không?”',
         options=[dict(id='go', label='Quay lại lấy, dặn bà giờ đổ rác lần sau', hint='Đi thêm một vòng', effects=dict(patience=-4, xp=5), good=True,
                       outcome='Bà cụ đứng chờ ở cửa với cái túi nhỏ xíu, dúi cho gói kẹo gừng.'),
                  dict(id='tomorrow', label='Hẹn bà tối mai', hint='', effects={}, good=None, outcome='Bà “ừ” nhỏ, túi rác nằm trong bếp thêm một ngày.'),
                  dict(id='rule', label='“Qua giờ rồi bà ơi, quy định là quy định”', hint='', effects=dict(review=[3, 'Người già quên có lần mà cũng không linh động.']), good=False,
                       outcome='Bà cụ cúp máy. Con trai bà viết một bài dài trên nhóm cư dân.')],
         default='tomorrow'),
    dict(id='dog_owner', title='Chủ chó mắng vì xe rác đi qua', emoji='🐕', npc=5, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Xe rác vừa qua, con chó nhà bên sủa ầm. Chủ nhà xồng xộc ra: “Đi đứng kiểu gì làm chó tao sủa cả tối, cút đi chỗ khác mà đẩy!”',
         options=[dict(id='sorry', label='Xin lỗi, đẩy xe nhẹ tay qua đoạn đó', hint='', effects=dict(xp=3), good=True,
                       outcome='Anh ta lầm bầm rồi vào nhà. Lần sau bạn đẩy xe sát lề bên kia.'),
                  dict(id='ignore', label='Làm như không nghe', hint='', effects={}, good=None, outcome='Anh ta chửi với theo tới hết ngõ.'),
                  dict(id='back', label='“Ngõ chung chứ có phải nhà anh đâu”', hint='', effects=dict(review=[2, 'Công nhân vệ sinh láo, cãi dân tay đôi.']), good=False,
                       outcome='Hai bên cãi nhau, chó sủa to hơn, cả ngõ thức giấc.')],
         default='ignore'),
    dict(id='shop_block', title='Chủ tiệm cấm đậu xe rác', emoji='🏪', npc=2, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Chủ tiệm quần áo đứng chắn cửa: “Không được đậu xe rác trước tiệm tôi! Khách thấy là mất hết mối, đẩy ra chỗ khác!”',
         options=[dict(id='move', label='Đậu sát góc tường, gom nhanh, rắc vôi khử mùi', hint='', effects=dict(xp=3, patience=-2), good=True,
                       outcome='Chủ tiệm gật: “Thế thì được.” Còn nhờ gom giúp mấy thùng các-tông.'),
                  dict(id='far', label='Đậu tít đầu ngõ, xách bộ từng túi', hint='Mất sức', effects=dict(patience=-6), good=None,
                       outcome='Xách bộ mười mấy túi, mỏi rã tay.'),
                  dict(id='stay', label='“Rác tiệm chị cũng đổ vào xe này đấy”', hint='', effects=dict(review=[2, 'Xe rác đậu lì trước tiệm, nhắc còn cãi.']), good=False,
                       outcome='Chủ tiệm gọi điện thẳng cho tổ trưởng.')],
         default='far'),
    dict(id='oil', title='Quán nhậu đổ dầu mỡ vào xe', emoji='🛢️', npc=2, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Nhân viên quán nhậu xách can dầu chiên cũ đổ thẳng vào ngăn hữu cơ: “Rác thì rác, chê gì!” Dầu chảy lênh láng đáy xe.',
         options=[dict(id='stop', label='Chặn lại, hướng dẫn để dầu vào can cho người thu mua riêng', hint='', effects=dict(xp=4), good=True,
                       outcome='Quán gọi người thu mua dầu cũ. Ngăn xe khỏi bốc mùi cả tuần.'),
                  dict(id='wash', label='Để yên, về rửa xe sau', hint='Tốn nước rửa', effects=dict(money=-3), good=None, outcome='Rửa mãi mùi dầu ôi vẫn còn.'),
                  dict(id='yell', label='Quát ầm lên', hint='', effects=dict(review=[2, 'Công nhân rác quát nhân viên quán giữa phố.']), good=False,
                       outcome='Nhân viên quán cãi lại, khách nhậu quay ra xem.')],
         default='wash'),
    dict(id='party', title='Đám cưới xong bỏ rác đầy ngõ', emoji='💒', npc=1, min_day=3, tone='gentle', at='between', weight=2, mods=('party', 'normal'),
         text='Đám cưới tan, nhà chủ để lại ba mươi bao rác, bàn ghế gãy, hoa héo: “Tiện thì dọn luôn giùm nha, cho mấy chục nghìn uống nước.”',
         options=[dict(id='contract', label='Báo giá thu gom theo khối lượng, có biên lai', hint='', effects=dict(money=10, xp=3), good=True,
                       outcome='Nhà chủ đóng phí đúng quy định, tổ gọi thêm người dọn trong một giờ.'),
                  dict(id='tip', label='Nhận tiền uống nước, dọn không biên lai', hint='', effects=dict(money=6, review=[3, 'Tổ thu gom nhận tiền ngoài, không biên lai.']), good=False,
                       outcome='Dọn xong mệt nhoài, chị Hạnh biết chuyện thì không vui.'),
                  dict(id='no', label='Chỉ lấy rác sinh hoạt, đồ cồng kềnh hẹn xe riêng', hint='', effects={}, good=None,
                       outcome='Nhà chủ cằn nhằn nhưng gọi xe riêng.')],
         default='no'),
    dict(id='villa', title='Biệt thự đòi thu riêng', emoji='🏡', npc=1, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Bà chủ biệt thự đầu ngõ: “Rác nhà tôi thu trước, thu riêng, đừng để lẫn với rác mấy nhà nghèo kia. Đây, cầm lấy 10 xu.”',
         options=[dict(id='equal', label='Cảm ơn, từ chối tiền: nhà nào cũng thu như nhau', hint='', effects=dict(xp=4), good=True,
                       outcome='Bà chủ hơi phật ý, nhưng từ đó phân loại rác kỹ nhất ngõ.'),
                  dict(id='take', label='Nhận tiền, thu riêng nhà bà trước', hint='+10 xu', effects=dict(money=10, review=[3, 'Tổ thu gom ưu tiên nhà giàu, nhà khác chờ dài cổ.']), good=False,
                       outcome='Các nhà khác xì xào “có tiền là được ưu tiên”.')],
         default='equal'),
    dict(id='toy', title='Bé đòi lại đồ chơi trong túi rác', emoji='🧸', npc=6, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một bé gái mếu máo chạy theo xe: “Mẹ vứt con gấu bông của con rồi, chú ơi tìm giúp con với!” Túi đã lên xe.',
         options=[dict(id='find', label='Đeo găng lục ngăn còn lại, tìm con gấu', hint='Mất chút thời gian', effects=dict(patience=-4, xp=5), good=True,
                       outcome='Con gấu dính chút vỏ cam, bé ôm chầm lấy. Mẹ bé cảm ơn mãi.'),
                  dict(id='mom', label='Nói bé về hỏi mẹ, mai tính', hint='', effects={}, good=None, outcome='Bé đứng khóc ở đầu ngõ.'),
                  dict(id='no', label='“Vứt rồi thì thôi con”', hint='', effects={}, good=False, outcome='Bé khóc òa. Bé Na đứng cạnh nhìn bạn trách móc.')],
         default='mom'),
    dict(id='hotline', title='Bị gọi đường dây nóng vì ồn', emoji='📢', npc=3, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Phường gọi: có người phản ánh “xe rác ồn, công nhân nói chuyện to lúc mười giờ đêm”. Người phản ánh là ông Thước.',
         options=[dict(id='quiet', label='Nhận góp ý, tra dầu bánh xe, nói nhỏ lại', hint='', effects=dict(money=-2, xp=3), good=True,
                       outcome='Bánh xe hết kêu. Ông Thước tối sau không gọi nữa.'),
                  dict(id='explain', label='Giải thích giờ thu gom theo lịch phường', hint='', effects={}, good=None, outcome='Phường ghi nhận, ông Thước vẫn lầm bầm.'),
                  dict(id='bang', label='Cố tình đập nắp xe thật to trước nhà ông', hint='', effects=dict(review=[1, 'Công nhân cố tình gây ồn trả đũa người già.']), good=False,
                       outcome='Lần này phường mời cả tổ lên làm việc.')],
         default='explain'),
    dict(id='selfie', title='Bị chụp ảnh chê “nghề rác”', emoji='🤳', npc=6, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Hai cô cậu chụp ảnh bạn đang bốc rác, cười khúc khích: “Đăng story caption ‘không học thì như này nè’, flex vl.”',
         options=[dict(id='smile', label='Mỉm cười, làm tiếp cho gọn', hint='', effects=dict(xp=3), good=True,
                       outcome='Bé Na đi ngang thấy hết, về viết bài “người giữ phố sạch” được cô khen.'),
                  dict(id='talk', label='Nói nhẹ: “Xóa giùm cái ảnh nha”', hint='', effects={}, luck=dict(p=0.5,
                       win=dict(effects={}, good=None, outcome='Hai đứa ngượng, xóa ảnh.'),
                       lose=dict(effects={}, good=None, outcome='“Thích thì đăng đấy!” rồi bỏ chạy.'))),
                  dict(id='chase', label='Đuổi theo giật điện thoại', hint='', effects=dict(review=[1, 'Công nhân rác đuổi đánh học sinh!']), good=False,
                       outcome='Clip “công nhân rác nổi điên” lên mạng.')],
         default='smile'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='RC-S01', title='Người nhặt ve chai bới túi rác', npc=4, tone='gentle', min_day=1,
         opening='Một bác nhặt ve chai đi trước xe, mở từng túi rác lấy chai lọ, để lại rác vương vãi khắp ngõ.',
         swap='Bạn là bác nhặt ve chai, mỗi tối nhặt vài ký chai lọ đổi tiền mua gạo.',
         facts=[dict(id='mess', title='Ngõ sau khi bới', source='Nhìn quanh', text='Ba túi bị xé toang, cơm thừa đổ ra đường.'),
                dict(id='why', title='Bác ấy là ai', source='Chị Hạnh', text='Chị Hạnh bảo bác sống một mình, nhặt ve chai kiếm sống.'),
                dict(id='yellow', title='Túi vàng', source='Quy định phân loại', text='Túi vàng là đồ tái chế sạch, có thể để riêng cho người thu mua.')],
         options=[dict(id='share', label='Mời bác lấy túi vàng, nhờ đừng xé túi khác', requires=['why', 'yellow'], quality='good', stars=5,
                       review='Tổ thu gom vừa tử tế với bác ve chai vừa giữ ngõ sạch. Hay quá.',
                       outcome='Bác gật đầu, từ đó chỉ lấy túi vàng, còn giúp buộc lại túi rách.',
                       perspectives=[dict(who='Bác ve chai', emoji='🧓', text='Được chỉ chỗ lấy đàng hoàng, tôi đâu muốn bới.'),
                                     dict(who='Chị Hạnh', emoji='🧹', text='Ai cũng có miếng ăn, mà ngõ vẫn sạch.')]),
                  dict(id='sweep', label='Lặng lẽ quét sạch rồi đi tiếp', requires=['mess'], quality='ok', stars=4,
                       review='Ngõ sạch, nhưng mai chắc lại bị bới.', outcome='Ngõ sạch tối nay. Tối mai chuyện lại y như cũ.',
                       perspectives=[dict(who='Bác Tâm', emoji='📒', text='Quét hoài thì mệt, phải nói với nhau chứ.'),
                                     dict(who='Bác ve chai', emoji='🧓', text='Không ai nói gì, tôi cứ làm như mọi khi.')]),
                  dict(id='chase', label='Quát đuổi bác đi', quality='bad', stars=2, review='Quát một ông già nghèo giữa ngõ, nghe mà buồn.',
                       outcome='Bác đi, nhưng tối sau lại tới, còn tránh mặt tổ thu gom.',
                       perspectives=[dict(who='Bác ve chai', emoji='😞', text='Tôi có ăn cắp của ai đâu.'),
                                     dict(who='Bé Na', emoji='🎒', text='Em thấy tội bác ấy quá.')])],
         lesson='Người thu mua ve chai cũng là một mắt xích tái chế: chỉ chỗ lấy đồ tái chế sạch thay vì xua đuổi.'),
    dict(id='RC-S02', title='Bị quay clip “đổ chung rác”', npc=6, tone='tense', min_day=2,
         opening='Một người quay clip lúc bạn đổ ba ngăn xe vào khu tập kết, đăng lên mạng: “Phân loại làm gì, công nhân đổ chung hết!”',
         facts=[dict(id='truck', title='Xe ép rác', source='Chú Sáu', text='Xe ép chỉ nhận rác còn lại; rác hữu cơ lên xe riêng buổi sáng, đồ tái chế cô Tám thu.'),
                dict(id='clip', title='Đoạn clip', source='Điện thoại', text='Clip chỉ quay đúng lúc đổ ngăn “còn lại”, cắt mất đoạn trước.'),
                dict(id='board', title='Bảng lịch', source='Điểm tập kết', text='Điểm tập kết có dán lịch từng xe: hữu cơ, tái chế, còn lại.')],
         options=[dict(id='explain', label='Mời người quay xem lịch xe, chụp bảng lịch gửi nhóm cư dân', requires=['truck', 'board'], quality='good', stars=5,
                       review='Hóa ra mỗi loại rác đi một xe riêng. Cảm ơn tổ thu gom đã giải thích.',
                       outcome='Người quay đăng thêm bài đính chính. Nhiều người hỏi thêm cách phân loại.',
                       perspectives=[dict(who='Người quay clip', emoji='📱', text='Tôi thấy một đoạn là tưởng cả câu chuyện.'),
                                     dict(who='Bé Na', emoji='🎒', text='Em chia sẻ bài giải thích cho cả lớp.')]),
                  dict(id='ignore', label='Mặc kệ, làm việc của mình', quality='ok', stars=3, review='Tổ thu gom không nói gì, chẳng biết đâu mà lần.',
                       outcome='Clip lan truyền mấy hôm, vài nhà thôi không phân loại nữa.',
                       perspectives=[dict(who='Bác Tâm', emoji='📒', text='Im lặng thì người ta tin clip.'),
                                     dict(who='Chị Hạnh', emoji='🧹', text='Mình làm đúng thì cứ nói cho người ta hiểu.')]),
                  dict(id='grab', label='Giật điện thoại bắt xóa clip', quality='bad', stars=1, review='Công nhân vệ sinh giật điện thoại người dân, quá đáng!',
                       outcome='Thêm một clip mới, lần này còn tệ hơn.',
                       perspectives=[dict(who='Người quay clip', emoji='😠', text='Có gì mờ ám mà phải giật?'),
                                     dict(who='Chị Hạnh', emoji='🧹', text='Nóng một phút, mất uy tín cả tổ.')])],
         lesson='Khi bị hiểu lầm, đưa ra sự thật dễ kiểm chứng (lịch xe, bảng phân loại) thay vì tranh cãi.'),
    dict(id='RC-S03', title='Trời oi, không đeo khẩu trang', npc=0, tone='gentle', min_day=2,
         opening='Tối oi nồng, khẩu trang ướt đẫm mồ hôi, bạn muốn tháo ra cho dễ thở. Ngăn hữu cơ bốc mùi nồng nặc.',
         facts=[dict(id='smell', title='Mùi rác', source='Ngăn hữu cơ', text='Rác hữu cơ để cả ngày trong nóng bốc hơi khó thở, nhiều vi khuẩn.'),
                dict(id='spare', title='Khẩu trang dự phòng', source='Hộc xe', text='Chị Hạnh luôn để hai cái khẩu trang khô trong hộc xe.'),
                dict(id='rest', title='Nghỉ tay', source='Chị Hạnh', text='Cứ hết một ngõ được nghỉ năm phút uống nước.')],
         options=[dict(id='swap', label='Thay khẩu trang khô, nghỉ uống nước rồi làm tiếp', requires=['spare', 'rest'], quality='good', stars=5,
                       review='Tổ thu gom làm việc cẩn thận, giữ sức khỏe mà vẫn đúng giờ.', outcome='Dễ thở hơn hẳn, đi hết ngõ không mệt.',
                       perspectives=[dict(who='Chị Hạnh', emoji='🧹', text='Nghề này sức khỏe là vốn.'),
                                     dict(who='Bác sĩ trạm y tế', emoji='🩺', text='Hít mùi rác lâu ngày dễ viêm họng, viêm phổi.')]),
                  dict(id='off', label='Tháo khẩu trang cho nhanh', quality='bad', stars=3, review='Làm nhanh nhưng về ho khù khụ cả đêm.',
                       outcome='Về tới nhà thì cổ họng rát, ho cả đêm.',
                       perspectives=[dict(who='Chị Hạnh', emoji='🧹', text='Chị từng viêm phổi một mùa vì chủ quan.'),
                                     dict(who='Bé Na', emoji='🎒', text='Giữ sức khỏe nha, đừng tháo khẩu trang.')]),
                  dict(id='stop', label='Dừng hẳn, chờ trời mát', quality='ok', stars=4, review='Rác thu muộn hơn thường lệ một chút.',
                       outcome='Đỡ mệt, nhưng ngõ sau thu trễ giờ, có nhà phàn nàn.',
                       perspectives=[dict(who='Ông Thước', emoji='👴', text='Hôm nay xe tới muộn thế.'),
                                     dict(who='Chị Hạnh', emoji='🧹', text='Nghỉ thì nghỉ ngắn thôi em.')])],
         lesson='Đồ bảo hộ là để giữ sức khỏe lâu dài: có dự phòng thì thay, mệt thì nghỉ ngắn, đừng tháo bỏ.'),
    dict(id='RC-S04', title='Túi rác có bóng đèn vỡ', npc=5, tone='tense', min_day=2,
         opening='Túi đen nhà anh Khôi rách một góc, lòi ra bóng đèn tuýp vỡ đôi, bột trắng rơi xuống đất.',
         facts=[dict(id='mercury', title='Bóng đèn tuýp', source='Tờ hướng dẫn', text='Bóng đèn huỳnh quang có hơi thủy ngân, vỡ ra thì độc, phải gom riêng.'),
                dict(id='gear', title='Đồ bảo hộ', source='Trên người', text='Bạn đang đeo găng tay dày và khẩu trang.'),
                dict(id='box', title='Hộp nguy hại', source='Xe đẩy', text='Xe có hộp đỏ có nắp cho pin, bóng đèn, kim tiêm.')],
         options=[dict(id='safe', label='Gom mảnh vỡ bằng giấy cứng vào hộp đỏ, nhắc anh Khôi lần sau để riêng', requires=['mercury', 'box'], quality='good', stars=5,
                       review='Được hướng dẫn cách bỏ bóng đèn hỏng. Lần sau tôi để riêng.', outcome='Chỗ vỡ sạch sẽ, anh Khôi hứa sẽ để riêng.',
                       perspectives=[dict(who='Anh Khôi', emoji='💼', text='Tôi đâu biết bóng đèn cũng là rác nguy hại.'),
                                     dict(who='Chị Hạnh', emoji='🧹', text='Hộp đỏ là để cho những thứ này.')]),
                  dict(id='bag', label='Buộc túi lại, bỏ vào ngăn còn lại', quality='bad', stars=2, review='Bóng đèn vỡ bỏ chung xe ép, nguy hiểm cho người đổ rác.',
                       outcome='Lúc ép rác, bột trắng bay mù mịt, chú Sáu ho sặc sụa.',
                       perspectives=[dict(who='Chú Sáu', emoji='🚛', text='Bột đèn bay vào mặt, cay xè.'),
                                     dict(who='Anh Khôi', emoji='💼', text='Tôi tưởng vậy là được rồi.')]),
                  dict(id='leave', label='Để lại, dán giấy nhắc anh Khôi tự xử lý', requires=['mercury'], quality='ok', stars=3,
                       review='Nhắc đúng, nhưng để đống mảnh vỡ trước cửa cả đêm.', outcome='Sáng ra anh Khôi phải tự gom, trẻ con đi qua suýt dẫm phải.',
                       perspectives=[dict(who='Anh Khôi', emoji='😬', text='Tôi đâu có đồ mà gom.'),
                                     dict(who='Bé Na', emoji='🎒', text='Em suýt dẫm phải lúc đi học.')])],
         lesson='Pin, bóng đèn, kim tiêm là rác nguy hại: gom riêng vào hộp có nắp, không cho vào xe ép.'),
    dict(id='RC-S05', title='Rác qua đêm ở điểm tập kết', npc=7, tone='tense', min_day=3,
         opening='Xe đẩy còn nửa ngăn rác, nhưng xe ép của chú Sáu sắp chạy. Chú bấm còi: “Nhanh lên, xe không chờ đâu!”',
         facts=[dict(id='left', title='Rác còn lại', source='Xe đẩy', text='Còn hai ngõ chưa gom, mỗi ngõ chừng năm túi.'),
                dict(id='next', title='Chuyến sau', source='Chú Sáu', text='Chú Sáu quay lại lúc mười giờ đêm đón chuyến cuối.'),
                dict(id='rule', title='Quy định', text='Không để rác qua đêm ở điểm tập kết.')],
         options=[dict(id='plan', label='Đổ nửa xe bây giờ, gom nốt hai ngõ, đón chuyến mười giờ', requires=['left', 'next'], quality='good', stars=5,
                       review='Đúng giờ, không để rác qua đêm.', outcome='Chuyến cuối lúc mười giờ mang đi sạch sẽ.',
                       perspectives=[dict(who='Chú Sáu', emoji='🚛', text='Hẹn giờ rõ ràng là chú chờ được.'),
                                     dict(who='Ông Thước', emoji='👴', text='Sáng ra điểm tập kết sạch trơn.')]),
                  dict(id='skip', label='Bỏ hai ngõ, mai gom luôn', quality='bad', stars=2, review='Hai ngõ bị bỏ, rác để qua đêm.',
                       outcome='Sáng ra chó mèo bới tung hai ngõ.',
                       perspectives=[dict(who='Bác Tâm', emoji='📒', text='Ngõ tôi hôm qua không ai gom.'),
                                     dict(who='Chị Hạnh', emoji='🧹', text='Để qua đêm là mai gấp đôi việc.')]),
                  dict(id='pile', label='Đổ đống ở điểm tập kết, mai xe ép lấy', requires=['left'], quality='bad', stars=2,
                       review='Điểm tập kết thành bãi rác cả đêm, hôi không chịu nổi.', outcome='Sáng ra cả dãy phố phàn nàn.',
                       perspectives=[dict(who='Ông Thước', emoji='👴', text='Hôi thấu trời.'),
                                     dict(who='Chú Sáu', emoji='🚛', text='Đống đó phải xúc tay, mất cả tiếng.')])],
         lesson='Rác thu trong ngày đi hết trong ngày: sắp xếp chuyến theo giờ xe ép, không để rác qua đêm.'),
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
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Cư dân'


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def hm(minute: int) -> str:
    return f'{minute // 60:02d}:{minute % 60:02d}'


def bag_bin(bag: dict) -> str:
    """Where the bag belongs once the hazardous things are out: one kind → its compartment; food
    with recyclables spoils them → the rest; anything else mixed → the rest."""
    kinds = {WASTE[i][2] for i in bag['items'] if WASTE[i][2] != 'nguy_hai'}
    return kinds.pop() if len(kinds) == 1 else 'con_lai'


def _hazards(bag: dict) -> list:
    return [i for i in bag['items'] if WASTE[i][2] == 'nguy_hai']


def _glass(bag: dict) -> bool:
    return 'kinh_vo' in bag['items']


def _sorted_ok(bag: dict) -> bool:
    """The household sorted this bag right: everything in it belongs to its colour."""
    return all(WASTE[i][2] == COLOR_BIN[bag['color']] for i in bag['items'])


# ================================================================ tasks
def _kind(day: int, slot: int) -> str:
    if slot == 0:
        return 'setup'
    if day == 1:
        return 'route'
    if slot == 2 and day % 2 == 0:
        return 'complaint'
    return 'route'


def _route(day: int, slot: int, mod: str) -> dict:
    r = kit.rng(ID, 'route', day, slot)
    tier = kit.tier(day)
    lane = LANES[(day + slot) % len(LANES)] if day > 1 else LANES[slot - 1 if slot <= len(LANES) else 0]
    n_stops = 3 if day == 1 else min(5, 3 + (tier + r.randrange(2)) // 2)
    wrongs = 1 if day == 1 else min(4, 1 + tier + r.randrange(2))
    pool = WRONGS[:3] if day == 1 else WRONGS[:min(len(WRONGS), 4 + 2 * tier)]
    stops, bags = [], []
    for si in range(n_stops):
        nb = 1 + r.randrange(2) + (1 if mod == 'party' and si % 2 == 0 else 0)
        row = []
        for bi in range(nb):
            color = ('xanh', 'vang', 'den')[(si + bi + r.randrange(3)) % 3]
            main = MAIN[COLOR_BIN[color]]
            items = sorted({main[r.randrange(len(main))] for _ in range(1 + r.randrange(2))})
            if mod == 'party' and color == 'vang':
                items = sorted(set(items) | {'lon', 'chai_tt'})
            bag = dict(id=f'b{si}{bi}', color=color, items=items, clue=NEAT[r.randrange(len(NEAT))])
            row.append(bag)
            bags.append(bag)
        stops.append(dict(house=lane['houses'][si % len(lane['houses'])], bags=row))
    # Some households get it wrong: one wrong thing in a bag of its colour.
    order = list(range(len(bags)))
    r.shuffle(order)
    used = 0
    for k in order:
        if used >= wrongs:
            break
        wrong, color = pool[r.randrange(len(pool))]
        bag = bags[k]
        if day == 1:
            wrong, color = 'chai_nhua', 'xanh'   # the first evening: a plastic bottle in the green bag
        if bag['color'] != color:
            bag['color'] = color
            main = MAIN[COLOR_BIN[color]]
            bag['items'] = [main[_hash(day, slot, k) % len(main)]]
        if wrong in bag['items']:
            continue
        bag['items'] = sorted(set(bag['items']) | {wrong})
        bag['clue'] = CLUE.get(wrong, bag['clue'])
        used += 1
    smelly = mod == 'heat' or any('com_thua' in b['items'] for b in bags)
    return dict(route=True, lane=lane['id'], name=lane['name'], until=WINDOWS.get(slot, WINDOWS[4]), stops=stops, smelly=smelly,
                note=f'Thu gom trước {hm(WINDOWS.get(slot, WINDOWS[4]))}. Túi nào trông lạ thì mở ra xem.'), lane['npc']


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    kind = _kind(day, slot)
    common = dict(gen=GEN, stage='prep', at=0, loaded={}, opened=[], pulled={}, wrapped=[], noted=[], arrived=None,
                  late=False, swept=False, read=[], answer=None, story=None, hurt=False)
    if kind == 'setup':
        rain = mod == 'rain'
        needs = dict(setup=True, gear=['gang_tay', 'khau_trang', 'ao'] + (['ung'] if rain else []),
                     note='Trời mưa: mang ủng, đường trơn đẩy xe chậm thôi.' if rain else
                     'Oi nồng: khẩu trang phải kín, mang theo nước uống.' if mod == 'heat' else 'Đồ bảo hộ đủ, xe đẩy chắc chắn rồi hẵng đi.')
        return kit.base_task(ID, day, slot, serial, 0, 'Vào ca tối mưa' if rain else 'Vào ca thu gom',
                             'Chị Hạnh: “Găng tay, khẩu trang, áo phản quang đâu? Kiểm cái xe rồi mình đi em.”', kind='setup', needs=needs, **common)
    if kind == 'complaint':
        x = CASES[kit.rng(ID, 'case', day, slot).randrange(len(CASES))] if day > 2 else CASES[0]
        needs = dict(case=x['id'], note='Hỏi rõ, xem tận nơi rồi mới trả lời.')
        return kit.base_task(ID, day, slot, serial, x['npc'], x['title'], x['opening'], kind='complaint', needs=needs, **common)
    needs, npc = _route(day, slot, mod)
    return kit.base_task(ID, day, slot, serial, npc, f'Thu gom {needs["name"]}',
                         f'Chị Hạnh: “{needs["name"]} đổ rác tới {hm(needs["until"])}. Mình đẩy xe vào nha em.”', kind='route', needs=needs, **common)


FIXED = ('needs',)


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'
    tw = twist_of(t)
    if tw:
        # Lanes made before 0.9.16 have no twist; a new one carries it from the start (and it must match twist_of).
        t['twist'], t['tw'] = tw, dict(state='wait', choice=None)


# ================================================================ the crew's data
def _empty_cart() -> dict:
    return {b: dict(n=0, bad=0) for b in BINS}


def _fresh_today(day: int) -> dict:
    return dict(day=day, bags=0, wrong=0, hazards=0, dumps=0, ve_chai=0, noted=0, late=0, overnight=0, fees=0)


def initial() -> dict:
    return dict(v=1, intro=False, gear=[], cart_ok=False, shift=False, cart=_empty_cart(), haz=[], regulars={},
                today=_fresh_today(0), stats=dict(bags=0, wrong=0, hazards=0, ve_chai=0, noted=0, hurt=0, routes=0, cases=0, fees=0),
                desk=kit.desk_initial(), fees=dict(week=-1, rows=[]), trouble=folk.trouble_initial())


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


def cart_load(d: dict) -> int:
    return sum(x['n'] for x in d['cart'].values())


def clock_min(c: dict) -> int:
    return inv.clock(c, ID)['minute']


# ================================================================ the actions
FREE = ('rac_intro',)
NO_TICK = ('rac_intro', 'rac_gear', 'rac_peek', 'rac_pull', 'rac_wrap', 'rac_load', 'rac_note', 'rac_read', 'rac_desk',
           'rac_grump', 'rac_trouble', 'rac_refuse')
PHYSICAL = ('rac_go', 'rac_next', 'rac_sweep', 'rac_dump')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'rac_intro':
        d['intro'] = True
        return dict(message='Vào ca thôi! Chị Hạnh đang chờ ở đầu ngõ.')
    desk = d['desk']
    if name == 'rac_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'), hook=_desk_hook)
    if name == 'rac_trouble':
        return _trouble(s, c, d, p)
    kit.desk_block(desk, 'Có chuyện giữa đường, quyết xong rồi đi tiếp nhé.')
    kit.need(d['trouble']['ev'] is None or name == 'rac_fee', 'Có chuyện ở ngõ: xử lý trước đã.', 'surprise_open')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở tổ thu gom.')
    result = fn(s, c, d, p)
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
    elif _trouble_tick(s, c, d):
        result['message'] = f'{result.get("message", "")} 🔔 Có chuyện ở ngõ!'.strip()
        result['surprise'] = True
    return result


def _task(c: dict, p: dict, kinds=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tổ thu gom.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    return t


def _need_shift(d: dict) -> None:
    kit.need(d['shift'], 'Chưa vào ca: đồ bảo hộ, kiểm xe rồi bấm “Vào ca” nhé.')


# ---------------------------------------------------------------- starting the shift
def _gear(s, c, d, p):
    item = kit.one_of(p.get('item'), GEAR, 'Đồ bảo hộ không có.')
    if item in d['gear']:
        kit.need(item not in USED, f'{GEAR_LABEL[item]} đã dùng rồi, tháo ra là bỏ.')
        d['gear'].remove(item)
        return dict(message=f'Đã cởi {_lower(GEAR_LABEL[item])}.')
    if item in USED:
        kit.need(kit.stock(c, item) > 0, f'Hết {_lower(GEAR_LABEL[item])} rồi. Mở kho mua thêm nhé.')
        kit.take(c, item, 1)
    d['gear'].append(item)
    return dict(message={'gang_tay': '🧤 Đeo găng tay cao su dày.', 'khau_trang': '😷 Đeo khẩu trang kín mũi.',
                         'ao': '🦺 Mặc áo phản quang.', 'ung': '🥾 Xỏ ủng cao su.'}[item])


def _cart(s, c, d, p):
    kit.need(not d['cart_ok'], 'Xe đã kiểm rồi.')
    d['cart_ok'] = True
    return dict(message='🛒 Bơm lại bánh xe, siết nắp ba ngăn, treo hộp đỏ đựng đồ nguy hại. Xe chắc chắn rồi.')


def _open(s, c, d, p):
    t = _task(c, p, ('setup',))
    n = t['needs']
    missing = [g for g in n['gear'] if g not in d['gear']]
    if 'gang_tay' in missing:
        t['mistakes'] += 1
        cq.slip(t, 'no_gloves', 2, 'Tay trần mà đi gom rác, kim với mảnh chai đâu có chừa ai.', 'thiếu găng tay')
    if 'ao' in missing:
        t['mistakes'] += 1
        cq.slip(t, 'no_vest', 2, 'Không mặc áo phản quang, ngõ tối xe máy không thấy đâu.', 'thiếu áo phản quang')
    other = [g for g in missing if g not in ('gang_tay', 'ao')]
    if other:
        t['mistakes'] += 1
        cq.slip(t, 'gear', 1, f'Thiếu {", ".join(_lower(GEAR_LABEL[g]) for g in other)}.', 'thiếu đồ bảo hộ')
    if not d['cart_ok']:
        t['mistakes'] += 1
        cq.slip(t, 'cart', 1, 'Chưa kiểm xe đã đẩy đi, bánh xe xẹp lết cả ngõ.', 'chưa kiểm xe')
    d['shift'] = True
    kit.start_work(t)
    ok = not cq.slips(t)
    kit.complete(s, c, t, 0, 'Vào ca: đồ bảo hộ, xe đẩy.')
    return dict(message='🦺 Vào ca! ' + ('Chị Hạnh cười: “Gọn gàng đó, đi thôi em.”' if ok else 'Chị Hạnh lắc đầu: “Đi thì đi, nhưng lần sau đủ đồ nha em.”'),
                celebrate=ok)


# ---------------------------------------------------------------- the round
def _bag(t: dict, bid) -> tuple[int, dict]:
    kit.need(isinstance(bid, str), 'Túi rác không có.')
    for si, st in enumerate(t['needs']['stops']):
        for b in st['bags']:
            if b['id'] == bid:
                kit.need(si <= t['at'], 'Chưa tới nhà đó.')
                return si, b
    kit.need(False, 'Túi rác không có.')


def _on_round(t: dict) -> None:
    kit.need(t['stage'] == 'round', 'Đẩy xe vào ngõ đã nhé.')
    _need_calm(t)


def _go(s, c, d, p):
    t = _task(c, p, ('route',))
    _need_shift(d)
    kit.need(t['known'], 'Nghe chị Hạnh dặn đã nhé.')
    kit.need(t['stage'] == 'prep', 'Đã vào ngõ rồi.')
    now = clock_min(c)
    t['arrived'] = now
    t['stage'] = 'round'
    kit.start_work(t)
    if now > t['needs']['until']:
        t['late'] = True
        d['today']['late'] += 1
        return dict(message=f'🛒 Vào {t["needs"]["name"]} lúc {hm(now)}, trễ giờ thu gom. Mấy túi rác bị mèo bới tung ra đường: quét dọn đã.', correct=False)
    g = _grump_now(t)
    head = f'🛒 Đẩy xe vào {t["needs"]["name"]} lúc {hm(now)}. Nhà đầu tiên: {t["needs"]["stops"][0]["house"]}.'
    return dict(g, message=f'{head} {g["message"]}') if g else dict(message=head)


def _sweep(s, c, d, p):
    t = _task(c, p, ('route',))
    _on_round(t)
    kit.need(t['late'] and not t['swept'], 'Không có gì vương vãi.')
    t['swept'] = True
    return dict(message='🧹 Quét gom rác vương vãi, buộc lại túi rách. Ngõ sạch rồi.')


def _peek(s, c, d, p):
    t = _task(c, p, ('route',))
    _on_round(t)
    _, b = _bag(t, p.get('bag'))
    kit.need(b['id'] not in t['opened'], 'Túi này mở rồi.')
    kit.need(b['id'] not in t['loaded'], 'Túi đã lên xe rồi.')
    t['opened'].append(b['id'])
    names = ', '.join(f'{WASTE[i][1]} {_lower(WASTE[i][0])}' for i in b['items'])
    st = _tw(t, 'sharp')
    if st and t['twist']['bag'] == b['id'] and st['state'] == 'wait':
        w = WASTE[t['twist']['item']]
        names += f'… và ⚠️ {w[1]} {_lower(w[0])} gói hờ trong giấy báo'
    return dict(message=f'👀 Mở {_lower(COLOR_LABEL[b["color"]])}: {names}.')


def _pull(s, c, d, p):
    t = _task(c, p, ('route',))
    _on_round(t)
    _, b = _bag(t, p.get('bag'))
    kit.need(b['id'] in t['opened'], 'Mở túi ra xem đã.')
    kit.need(b['id'] not in t['loaded'], 'Túi đã lên xe rồi.')
    item = kit.one_of(p.get('item'), WASTE, 'Không có thứ này.')
    st = _tw(t, 'sharp')
    hidden = bool(st) and t['twist']['bag'] == b['id'] and t['twist']['item'] == item and st['state'] == 'wait'
    kit.need((item in b['items'] or hidden) and WASTE[item][2] == 'nguy_hai', 'Chỉ tách pin, bóng đèn, bình xịt, kim tiêm ra hộp đỏ.')
    if hidden:
        st['state'] = 'safe'
    done = t['pulled'].setdefault(b['id'], [])
    kit.need(item not in done, 'Đã tách ra rồi.')
    kit.need(len(d['haz']) < HAZ_MAX, 'Hộp đỏ đầy rồi: ra điểm tập kết giao cho điểm thu gom nguy hại đã.')
    done.append(item)
    d['haz'].append(item)
    d['today']['hazards'] += 1
    d['stats']['hazards'] += 1
    if WASTE[item][3] and 'gang_tay' not in d['gear']:
        t['hurt'] = True
        d['stats']['hurt'] += 1
        t['mistakes'] += 1
        cq.slip(t, 'hurt', 3, 'Tay trần gắp đồ sắc nhọn, bị đâm chảy máu phải ra trạm y tế.', 'bị thương vì thiếu găng', safety=item == 'kim_tiem')
        return dict(message=f'🩸 Tay trần nhặt {_lower(WASTE[item][0])}, bị đâm vào tay! Rửa, sát trùng, ra trạm y tế kiểm tra.', correct=False)
    return dict(message=f'🔴 Tách {_lower(WASTE[item][0])} bỏ vào hộp đỏ, đậy nắp.')


def _wrap(s, c, d, p):
    t = _task(c, p, ('route',))
    _on_round(t)
    _, b = _bag(t, p.get('bag'))
    kit.need(b['id'] in t['opened'], 'Mở túi ra xem đã.')
    kit.need(_glass(b), 'Túi này không có mảnh vỡ.')
    kit.need(b['id'] not in t['wrapped'], 'Đã bọc rồi.')
    kit.need(kit.stock(c, 'bao') > 0, 'Hết bao bọc mảnh vỡ. Mở kho mua thêm nhé.')
    kit.take(c, 'bao', 1)
    t['wrapped'].append(b['id'])
    return dict(message='🧷 Gói mảnh kính vỡ vào bao dày, dán chữ “Mảnh vỡ”.')


def _load_rules(t: dict, need=kit.need) -> None:
    """rac_load for any bag of this lane, before the bag and the cart are read: a lane left late was torn open by
    the dogs, sweep it first. public_task sends it as can.rac_load (live 04-06/10: 96 refusals)."""
    need(not t['late'] or t['swept'], 'Quét gom rác vương vãi trước đã.',
         fix=dict(cmd='rac_sweep', payload=dict(task=t['id']), label='🧹 Quét dọn'))


def _load(s, c, d, p):
    t = _task(c, p, ('route',))
    _on_round(t)
    _, b = _bag(t, p.get('bag'))
    kit.need(b['id'] not in t['loaded'], 'Túi đã lên xe rồi.')
    kit.need(b['id'] not in t.get('refused', []), 'Túi này đã dán phiếu không thu.')
    _load_rules(t)
    bin_ = kit.one_of(p.get('bin'), BINS, 'Chọn ngăn xe.')
    cell = d['cart'][bin_]
    kit.need(cell['n'] < CART[bin_], f'Ngăn {_lower(BIN_LABEL[bin_])} đầy rồi: đẩy xe ra điểm tập kết đổ đã.')
    left = [i for i in _hazards(b) if i not in t['pulled'].get(b['id'], [])]
    right = bag_bin(b)
    bad = bin_ != right or bool(left)
    cell['n'] += 1
    cell['bad'] += 1 if bad or (bin_ == 'tai_che' and right != 'tai_che') else 0
    t['loaded'][b['id']] = bin_
    d['today']['bags'] += 1
    d['stats']['bags'] += 1
    if bin_ != right:
        d['today']['wrong'] += 1
        d['stats']['wrong'] += 1
    st = _tw(t, 'sharp')
    if st and t['twist']['bag'] == b['id'] and st['state'] == 'wait':
        gloves = 'gang_tay' in d['gear']
        if not gloves or folk.roll('rac-prick', t['id']) < 40:
            st['state'] = 'on'
            t['hurt'] = True
            d['stats']['hurt'] += 1
            w = WASTE[t['twist']['item']]
            thru = 'xuyên qua găng' if gloves else 'vào tay trần'
            return dict(message=f'🩸 Túi trông bình thường mà có {_lower(w[0])} giấu bên trong, đâm {thru}! Xử lý vết thương đã.', correct=False, surprise=True)
        st['state'] = 'done'
    if _glass(b) and b['id'] not in t['wrapped'] and 'gang_tay' not in d['gear']:
        t['hurt'] = True
        d['stats']['hurt'] += 1
        t['mistakes'] += 1
        cq.slip(t, 'cut', 2, 'Xách túi có mảnh kính bằng tay trần, đứt tay rướm máu.', 'đứt tay vì thiếu găng')
        return dict(message=f'🩸 Mảnh kính đâm xuyên túi, đứt tay! Túi đã vào ngăn {_lower(BIN_LABEL[bin_])}.', correct=False)
    return dict(message=f'{BIN_EMOJI[bin_]} {COLOR_LABEL[b["color"]]} vào ngăn {_lower(BIN_LABEL[bin_])}.')


def _note(s, c, d, p):
    t = _task(c, p, ('route',))
    _on_round(t)
    si = kit.integer(p.get('stop'), 0, len(t['needs']['stops']) - 1)
    kit.need(si <= t['at'], 'Chưa tới nhà đó.')
    kit.need(si not in t['noted'], 'Đã nhắc nhà này rồi.')
    t['noted'].append(si)
    d['today']['noted'] += 1
    d['stats']['noted'] += 1
    return dict(message=f'📝 Dán tờ nhắc phân loại ở {_lower(t["needs"]["stops"][si]["house"])}, nói nhẹ nhàng với chủ nhà.')


def _next(s, c, d, p):
    t = _task(c, p, ('route',))
    _on_round(t)
    stops = t['needs']['stops']
    kit.need(t['at'] < len(stops) - 1, 'Đây là nhà cuối ngõ rồi. Bấm “Xong ngõ”.')
    kit.need(not t['late'] or t['swept'], 'Quét gom rác vương vãi trước đã.')
    t['at'] += 1
    g = _grump_now(t)
    head = f'🛒 Đẩy xe tới {stops[t["at"]]["house"]}.'
    return dict(g, message=f'{head} {g["message"]}') if g else dict(message=head)


def _finish_route(s, c, d, p):
    t = _task(c, p, ('route',))
    _on_round(t)
    n = t['needs']
    kit.need(t['at'] == len(n['stops']) - 1, 'Còn nhà chưa tới trong ngõ.')
    pst = _tw(t, 'pile')
    if pst and pst['state'] == 'wait':
        pst['state'] = 'on'
        return dict(message=f'🗑️ {PILE_LINES[t["twist"]["n"]]} Khoảng {t["twist"]["bags"]} bao, xe không chở hết một chuyến.', surprise=True)
    bags = [b for st in n['stops'] for b in st['bags']]
    refused = set(t.get('refused', []))
    if any(b['id'] in refused and _sorted_ok(b) for b in bags):
        t['mistakes'] += 1
        cq.slip(t, 'refused_ok', 1, 'Nhà tôi phân loại đúng mà cũng bị dán phiếu không thu.', 'từ chối nhầm túi đã phân loại')
    missed = [b for b in bags if b['id'] not in t['loaded'] and not (b['id'] in refused and not _sorted_ok(b))]
    if missed:
        t['mistakes'] += 1
        cq.slip(t, 'missed', 2, f'Bỏ sót {len(missed)} túi rác trước cửa, để qua đêm bốc mùi.', 'bỏ sót túi rác')
    wrong = [b for b in bags if b['id'] in t['loaded'] and t['loaded'][b['id']] != bag_bin(b)]
    if wrong:
        t['mistakes'] += 1
        cq.slip(t, 'bin', 2 if len(wrong) > 1 else 1, f'{len(wrong)} túi bỏ nhầm ngăn, phân loại xong lại trộn.', 'bỏ nhầm ngăn')
    haz = [i for b in bags if b['id'] in t['loaded'] for i in _hazards(b) if i not in t['pulled'].get(b['id'], [])]
    if haz:
        t['mistakes'] += 1
        cq.slip(t, 'hazard', 2, f'Để {_lower(WASTE[haz[0]][0])} lẫn trong túi lên xe ép, dễ cháy nổ, rò độc.', 'để lọt đồ nguy hại',
                safety='kim_tiem' in haz)
    loose = [b for b in bags if b['id'] in t['loaded'] and _glass(b) and b['id'] not in t['wrapped']]
    if loose:
        t['mistakes'] += 1
        cq.slip(t, 'glass', 1, 'Mảnh kính không bọc, người đổ rác ở điểm tập kết dễ đứt tay.', 'không bọc mảnh vỡ')
    messy = [si for si, st in enumerate(n['stops']) if any(not _sorted_ok(b) for b in st['bags'])]
    nag = [si for si in t['noted'] if si not in messy]
    if nag:
        t['mistakes'] += 1
        cq.slip(t, 'nag', 1, 'Nhà tôi phân loại đúng mà vẫn bị dán giấy nhắc.', 'nhắc nhầm nhà')
    if n['smelly'] and 'khau_trang' not in d['gear']:
        cq.slip(t, 'mask', 1, 'Không đeo khẩu trang, ho sặc sụa giữa ngõ.', 'thiếu khẩu trang')
    if t['late']:
        cq.slip(t, 'late', 1, f'Xe rác tới muộn, qua {hm(n["until"])} mới thấy.', 'thu gom trễ giờ')
    pay = ROUTE_PAY + STOP_PAY * len(n['stops'])
    d['stats']['routes'] += 1
    react = cq.react(s, c, t, pay, who=_who(t))
    good_notes = len([si for si in t['noted'] if si in messy])
    lines = [f'Gom {len(bags) - len(missed)}/{len(bags)} túi ở {n["name"]}.']
    if good_notes:
        c['xp'] += 3 * good_notes
        lines.append(f'Nhắc {good_notes} nhà phân loại lại.')
    msg = _finish(s, c, d, t, react['pay'], ' '.join(lines + ([react['message']] if react['message'] else [])))
    return dict(message=f'✅ Xong ngõ! {msg}', celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the collection point
def _dump(s, c, d, p):
    _need_shift(d)
    kit.need(cart_load(d) or d['haz'], 'Xe đang trống.')
    cart = d['cart']
    clean = max(0, cart['tai_che']['n'] - cart['tai_che']['bad'])
    money = clean * VE_CHAI
    parts = []
    if cart['huu_co']['n']:
        parts.append(f'{cart["huu_co"]["n"]} túi hữu cơ lên xe ủ phân')
    if cart['con_lai']['n']:
        parts.append(f'{cart["con_lai"]["n"]} túi còn lại lên xe ép')
    if cart['tai_che']['n']:
        parts.append(f'{cart["tai_che"]["n"]} túi tái chế cho cô Tám')
    if d['haz']:
        parts.append(f'{len(d["haz"])} món nguy hại giao điểm thu gom riêng')
    if money:
        kit.money(s, c, money, f'Cô Tám mua ve chai: {clean} túi tái chế sạch', f'rac-vechai-{c["day"]}-{d["today"]["dumps"]}', 'sales')
    d['today']['dumps'] += 1
    d['today']['ve_chai'] += money
    d['stats']['ve_chai'] += money
    dirty = cart['tai_che']['bad']
    d['cart'], d['haz'] = _empty_cart(), []
    tail = f' Cô Tám trả {money} xu tiền ve chai.' if money else ''
    if dirty:
        tail += f' Cô Tám lắc đầu với {dirty} túi tái chế lẫn đồ ăn: “Bẩn vậy không bán được.”'
    return dict(message=f'🚛 Đổ xe ở điểm tập kết: {", ".join(parts)}.{tail}', celebrate=bool(money) and not dirty)


# ---------------------------------------------------------------- complaints
def _read(s, c, d, p):
    t = _task(c, p, ('complaint',))
    kit.need(t['known'], 'Nghe cư dân nói đã nhé.')
    x = CASE[t['needs']['case']]
    f = next((f for f in x['facts'] if f['id'] == p.get('fact')), None)
    kit.need(f, 'Không có chuyện này.')
    if f['id'] not in t['read']:
        t['read'].append(f['id'])
    kit.start_work(t)
    return dict(message=f'🔍 {f["title"]}: {f["text"]}')


def _reply(s, c, d, p):
    t = _task(c, p, ('complaint',))
    kit.need(t['known'], 'Nghe cư dân nói đã nhé.')
    x = CASE[t['needs']['case']]
    o = next((o for o in x['options'] if o['id'] == p.get('option')), None)
    kit.need(o, 'Chọn cách trả lời.')
    missing = [f for f in o.get('requires', ()) if f not in t['read']]
    kit.need(not missing, 'Tìm hiểu thêm đã: ' + ', '.join(_lower(next(f['title'] for f in x['facts'] if f['id'] == m)) for m in missing) + '.')
    kit.start_work(t)
    t['answer'] = o['id']
    d['stats']['cases'] += 1
    if o['q'] == 'ok':
        t['mistakes'] += 1
        cq.slip(t, 'half', 1, 'Giải quyết được một nửa, còn để lửng.', 'giải quyết chưa trọn')
    elif o['q'] == 'bad':
        t['mistakes'] += 1
        cq.slip(t, 'bad_' + o['id'], 3 if o.get('hurt') else 2, o['outcome'], 'cách xử lý sai', safety=bool(o.get('hurt')))
    react = cq.react(s, c, t, CASE_PAY, who=_who(t))
    msg = _finish(s, c, d, t, react['pay'], (o['outcome'] + (' ' + react['message'] if react['message'] else '')).strip())
    return dict(message=('✅ ' if o['q'] == 'good' else '📝 ') + msg, celebrate=o['q'] == 'good', correct=o['q'] != 'bad')


# ---------------------------------------------------------------- finishing a job
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


def _desk_hook(s: dict, c: dict, key: str, v) -> str | None:
    d = _data(c)
    if key == 'vest':
        return 'May mà mặc áo phản quang, người lái thấy từ xa.' if 'ao' in d['gear'] else 'Không mặc áo phản quang, suýt nữa thì…'
    return None


# ================================================================ the awkward people on the round (0.9.16)
# A lane made from 0.9.16 on may carry a twist (twist_of, from the task id: never regenerated, only checked):
# 'sharp' a razor or a needle hidden in a bag that looks fine; 'pile' a heap dumped at the end of the lane,
# more than the cart holds; 'grump' a resident who will not sort and picks a fight. The player answers in
# their own way; each person decides from hidden traits (street_folk).
TWISTS = ('sharp', 'pile', 'grump')
TW_STATES = ('wait', 'on', 'done', 'safe')
TW_CHOICES = {'sharp': ('clean', 'clinic', 'ignore'), 'pile': ('trips', 'truck', 'report', 'cram'), 'grump': ('explain', 'refuse', 'take', 'report')}
HIDDEN = ('dao_lam', 'kim_tiem')
PILE_LINES = ('Cuối ngõ có ai đổ trộm cả đống: bao tải, nệm cũ, túi rác rách toác, tràn ra nửa lòng đường.',
              'Đống rác sau đám giỗ nhà số 9 cao ngang đầu gối, chó mèo bới tung, ruồi bu kín.',
              'Quán nhậu đầu ngõ vứt mười mấy bao vỏ lon, xương, đá tan chảy lênh láng.',
              'Nhà đang sửa chất xà bần lẫn rác sinh hoạt thành một đống, không ai nhận là của mình.')
GRUMP_LINES = ('“Tao đóng tiền rác rồi, phân loại là việc của mày chứ!”',
               '“Xanh vàng gì, rác nào chả là rác. Lấy đi, lắm chuyện vl.”',
               '“Phân loại xong xe ép cũng đổ chung, diễn cho ai xem?”',
               '“Mày nhìn cái gì? Có lấy không thì bảo, đứng đó giảng đạo à?”')


def twist_of(t: dict) -> dict | None:
    """The twist a lane carries (a pure function of the job: the validator checks a stored twist against it)."""
    if t.get('kind') != 'route' or t.get('day', 1) < 2:
        return None
    r, n = folk.roll('rac-twist', t['id']), folk.roll('rac-twist-n', t['id'])
    stops = t['needs']['stops']
    if r < 30:
        bags = [b['id'] for st in stops for b in st['bags'] if not _hazards(b) and not _glass(b)]
        return dict(kind='sharp', bag=bags[n % len(bags)], item=HIDDEN[n % 2], n=n % 4) if bags else None
    if r < 48:
        return dict(kind='pile', bags=4 + n % 4, n=n % 4)
    if r < 60:
        return dict(kind='grump', stop=n % len(stops), n=n % 4)
    return None


def _tr(t: dict, salt: str = '') -> dict:
    return folk.traits(t['id'] + salt, 'bossy' if (t.get('twist') or {}).get('kind') == 'grump' else None)


def _tw(t: dict, kind: str) -> dict | None:
    tw = t.get('twist')
    return t.get('tw') if isinstance(tw, dict) and tw.get('kind') == kind else None


def _need_calm(t: dict) -> None:
    st = t.get('tw')
    kit.need(not isinstance(st, dict) or st['state'] != 'on', 'Đang có chuyện ở ngõ: xử lý trước đã.')


def _grump_now(t: dict) -> dict | None:
    """Arriving at the grumpy resident's door: they come out first."""
    st = _tw(t, 'grump')
    if not st or st['state'] != 'wait' or t['at'] != t['twist']['stop']:
        return None
    st['state'] = 'on'
    return dict(message=f'😤 Chủ nhà {_lower(t["needs"]["stops"][t["at"]]["house"])} ra chặn xe: {GRUMP_LINES[t["twist"]["n"]]}', surprise=True)


def _hurt(s, c, d, p):
    """A hidden razor or needle pricked through: clean it yourself, go to the clinic, or carry on."""
    t = _task(c, p, ('route',))
    st = _tw(t, 'sharp')
    kit.need(st and st['state'] == 'on', 'Không ai bị thương.')
    choice = kit.one_of(p.get('choice'), TW_CHOICES['sharp'], 'Chọn cách xử lý.')
    item = t['twist']['item']
    st.update(state='done', choice=choice)
    if choice == 'clinic':
        cost = min(8, c['money'])
        if cost:
            kit.money(s, c, -cost, 'Trạm y tế: sát trùng, tiêm phòng', t['id'], 'medical')
        for x in c['tasks']:
            if x.get('career') == ID and x['status'] not in ('completed', 'referred', 'cancelled') and 'patience' in x:
                x['patience'] = max(25, x['patience'] - 5)
        return dict(message=f'🏥 Ra trạm y tế: rửa vết thương, tiêm phòng ({cost} xu). Chị Hạnh gom nốt giúp.')
    if choice == 'clean':
        if item == 'kim_tiem':
            t['mistakes'] += 1
            cq.slip(t, 'no_clinic', 2, 'Bị kim tiêm đâm mà chỉ băng tạm, không đi xét nghiệm, tiêm phòng.', 'bị kim đâm không đi khám')
            return dict(message='🩹 Rửa xà phòng, băng tạm. Chị Hạnh cau mày: “Kim tiêm thì phải đi khám, không đùa được đâu!”', correct=False)
        return dict(message='🩹 Rửa sạch, sát trùng, băng lại. Vết cắt nông, làm tiếp được.')
    t['mistakes'] += 1
    cq.slip(t, 'ignored', 3 if item == 'kim_tiem' else 2, 'Bị thương mà mặc kệ, máu rỏ xuống cả xe rác.', 'bị thương không sơ cứu', safety=item == 'kim_tiem')
    return dict(message='😬 Bạn chùi vào áo, làm tiếp. Tối về tay sưng tấy.', correct=False)


def _pile(s, c, d, p):
    """A heap more than the cart holds: two trips, call the truck, report it, or cram it in."""
    t = _task(c, p, ('route',))
    st = _tw(t, 'pile')
    kit.need(st and st['state'] == 'on', 'Không có đống rác nào.')
    choice = kit.one_of(p.get('choice'), TW_CHOICES['pile'], 'Chọn cách xử lý.')
    st.update(state='done', choice=choice)
    n = t['twist']['bags']
    if choice == 'trips':
        for x in c['tasks']:
            if x.get('career') == ID and x['status'] not in ('completed', 'referred', 'cancelled') and 'patience' in x:
                x['patience'] = max(25, x['patience'] - 8)
        c['xp'] += 4
        return dict(message=f'🛒🛒 Đi hai chuyến, gom sạch {n} bao. Mỏi nhừ tay, ngõ sạch bong. Bấm “Xong ngõ”.')
    if choice == 'truck':
        cost = min(10, c['money'])
        if cost:
            kit.money(s, c, -cost, 'Gọi xe ba gác chở đống rác đổ trộm', t['id'], 'service')
        return dict(message=f'🛻 Gọi xe ba gác ({cost} xu) chở {n} bao ra điểm tập kết. Bấm “Xong ngõ”.')
    if choice == 'report':
        cq.slip(t, 'pile_left', 1, 'Đống rác cuối ngõ vẫn nằm đó qua đêm, hôi ơi là hôi.', 'để lại đống rác')
        c['xp'] += 2
        return dict(message='📸 Chụp ảnh gửi tổ trưởng và phường, dựng biển “Cấm đổ rác”. Đống rác nằm lại chờ xe của phường. Bấm “Xong ngõ”.')
    if folk.roll('rac-cram', t['id']) < 55:
        cost = min(8, c['money'])
        if cost:
            kit.money(s, c, -cost, 'Sửa bản lề nắp xe đẩy', t['id'], 'equipment')
        t['mistakes'] += 1
        cq.slip(t, 'spill', 1, 'Nhồi quá tải, nắp xe bung, rác rơi dọc đường.', 'nhồi quá tải')
        return dict(message=f'💥 Nhồi cho bằng hết, nắp xe bung bản lề, rác rơi dọc ngõ. Sửa xe mất {cost} xu. Bấm “Xong ngõ”.', correct=False)
    return dict(message='🧱 Nhồi chặt, may mà xe chịu nổi. Bấm “Xong ngõ”.')


def _grump(s, c, d, p):
    """The resident who will not sort: explain, refuse the bag (with a sticker), take it anyway, or call the ward."""
    t = _task(c, p, ('route',))
    st = _tw(t, 'grump')
    kit.need(st and st['state'] == 'on', 'Không có ai chặn xe.')
    choice = kit.one_of(p.get('choice'), TW_CHOICES['grump'], 'Chọn cách xử lý.')
    tr = _tr(t, 'grump')
    st.update(state='done', choice=choice)
    si = t['twist']['stop']
    house = t['needs']['stops'][si]['house']
    if choice == 'explain':
        how = folk.word(tr, 'answer')
        if how == 'blowup':
            t['mistakes'] += 1
            cq.slip(t, 'quarrel', 1, 'Công nhân đứng cãi tay đôi với dân giữa ngõ.', 'cãi nhau với dân')
            return dict(message=f'😤 {house}: “Giảng đạo à? Cút mẹ mày đi!” Hàng xóm ló đầu ra xem.', correct=False)
        if how == 'calm':
            if si not in t['noted']:
                t['noted'].append(si)
            return dict(message=f'🗣️ Bạn giải thích nhẹ nhàng. {house}: “Ờ… để mai tao phân loại lại.”')
        return dict(message=f'🗣️ Bạn giải thích. {house} lầm bầm rồi đóng cửa đánh rầm.')
    if choice == 'refuse':
        bags = [b['id'] for b in t['needs']['stops'][si]['bags'] if b['id'] not in t['loaded']]
        t['refused'] = sorted(set(t.get('refused', []) + bags))
        if tr['honest'] >= 50:
            return dict(message=f'🏷️ Dán phiếu “Chưa phân loại, chưa thu”. {house} gãi đầu: “Ừ thì lần sau tao phân loại.”')
        kit.review(s, c, t['npc'], 2, 'Đóng tiền rác đầy đủ mà công nhân không thèm lấy, quá đáng!', t['id'])
        return dict(message=f'🏷️ Dán phiếu “Chưa phân loại, chưa thu”. {house}: “Không lấy thì tao vứt ra đầu ngõ, xem ai dọn!”', correct=False)
    if choice == 'report':
        for x in c['tasks']:
            if x.get('career') == ID and x['status'] not in ('completed', 'referred', 'cancelled') and 'patience' in x:
                x['patience'] = max(25, x['patience'] - 4)
        c['xp'] += 3
        return dict(message=f'📞 Gọi bác Tâm tổ trưởng. Bác ra nói mấy câu, {house} im re, hứa phân loại.')
    return dict(message=f'🤷 Lấy luôn cho xong. {house} đắc thắng: “Thấy chưa, lấy được mà!”')


def _refuse(s, c, d, p):
    """The player's own call: leave an unsorted bag with a sticker (the rules allow it). The household decides how to take it."""
    t = _task(c, p, ('route',))
    _on_round(t)
    si, b = _bag(t, p.get('bag'))
    kit.need(b['id'] in t['opened'], 'Mở túi ra xem đã rồi hẵng từ chối.')
    kit.need(b['id'] not in t['loaded'] and b['id'] not in t.get('refused', []), 'Túi này xử lý rồi.')
    t['refused'] = sorted(set(t.get('refused', []) + [b['id']]))
    house = t['needs']['stops'][si]['house']
    if _sorted_ok(b):
        return dict(message=f'🏷️ Dán phiếu không thu túi của {_lower(house)}… mà túi này phân loại đúng mà?', correct=False)
    tr = folk.traits(t['id'] + b['id'])
    if tr['honest'] >= 50:
        return dict(message=f'🏷️ Dán phiếu “Chưa phân loại, chưa thu”. {house} ra xem, gãi đầu: “Mai phân loại lại.”')
    kit.review(s, c, t['npc'], 2, 'Túi rác để trước cửa mà không lấy, dán cái phiếu như dán giấy phạt!', t['id'])
    return dict(message=f'🏷️ Dán phiếu “Chưa phân loại, chưa thu”. {house} gào theo: “Không lấy thì tao đổ ra đường!”', correct=False)


# ---------------------------------------------------------------- the rubbish fee book
FEE_STATES = ('open', 'paid', 'refused', 'waived')
FEE_EXCUSES = ('“Tháng này nhà đi vắng, không đổ rác mà cũng thu?”', '“Nhà có hai người, đóng bằng nhà mười người à?”',
               '“Tháng trước đóng rồi mà. Biên lai á? Mất rồi.”', '“Để cuối tháng lương về, gì mà gấp.”',
               '“Rác nhà tôi toàn tự xách ra điểm tập kết!”', '“Thu tiền mà rác vẫn bốc mùi thế kia, đóng làm gì?”')
FEE_ROWS = 5
FEE_OUT = {'paid': '{house} đếm đủ {paid} xu, nhận biên lai.', 'haggle': '{house}: “Đắt thế, {counter} xu thôi.”',
           'excuse': '{house}: {excuse}', 'refuse': '{house} đóng sầm cửa: “Không đóng! Kiện đi!”'}


def _fee_book(day: int) -> dict:
    """This week's households with the monthly fee due (deterministic from the week)."""
    week = max(0, (day - 1) // 7)
    rows = []
    for i in range(FEE_ROWS):
        lane = LANES[(week + i) % len(LANES)]
        house = lane['houses'][(week * 3 + i) % len(lane['houses'])]
        rows.append(dict(id=f'fee-{week}-{i}', house=house, lane=lane['name'], due=5 + folk.roll('rac-fee', week, i) % 4, paid=0, tries=0,
                         state='open', last=None, on=0, excuse=folk.roll('rac-fee-ex', week, i) % len(FEE_EXCUSES), counter=0))
    return dict(week=week, rows=rows)


def _fee(s, c, d, p):
    """Collect the monthly fee from a household: ask for an amount (a discount is your call), softly or by the rules."""
    _need_shift(d)
    row = next((x for x in d['fees']['rows'] if x['id'] == p.get('row')), None)
    kit.need(row and row['state'] == 'open', 'Hộ này không còn phải thu.')
    if p.get('waive') is True:
        row.update(state='waived', last='Miễn cho hộ khó khăn.')
        c['xp'] += 3
        return dict(message=f'🤝 Miễn phí tháng này cho {row["house"]}. Chị Hạnh gật đầu.')
    tone = kit.one_of(p.get('tone'), ('soft', 'strict'), 'Chọn cách nói.')
    left = row['due'] - row['paid']
    asked = kit.integer(p['amount'], 1, left) if p.get('amount') is not None else left
    if row['on'] == c['day']:
        # Once a day at each door; only a household's own counter-offer can still be taken on the spot.
        kit.need(row['counter'] and asked <= row['counter'], f'Hôm nay đã gõ cửa {row["house"]} rồi. Mai hẵng thu tiếp.')
        r = dict(kind='paid', paid=asked)
    else:
        r = folk.fee(folk.traits(row['id']), left, asked, tone, row['tries'])
    row['tries'] += 1
    row['on'] = c['day']
    row['counter'] = r.get('counter', 0) if r['kind'] == 'haggle' else 0
    if r['kind'] == 'paid':
        row['paid'] += r['paid']
        kit.money(s, c, r['paid'], f'Phí vệ sinh: {row["house"]}'[:120], row['id'], 'fee')
        d['today']['fees'] += r['paid']
        d['stats']['fees'] += r['paid']
        row['state'] = 'paid'   # a household that paid what you asked is done for the month
    elif r['kind'] == 'refuse':
        row['state'] = 'refused'
    line = FEE_OUT[r['kind']].format(house=row['house'], paid=r.get('paid', 0), counter=r.get('counter', 0), excuse=FEE_EXCUSES[row['excuse']])
    row['last'] = line[:200]
    head = {'paid': '🧾', 'haggle': '🤝', 'excuse': '🙄', 'refuse': '🚪'}[r['kind']]
    return dict(message=f'{head} {line}', correct=r['kind'] != 'refuse', celebrate=r['kind'] == 'paid')


def _validate_fees(f) -> None:
    kit.need(isinstance(f, dict) and set(f) == {'week', 'rows'} and isinstance(f['rows'], list) and len(f['rows']) <= FEE_ROWS, 'Sổ thu phí sai.')
    kit.integer(f['week'], -1, 10 ** 6)
    for x in f['rows']:
        kit.need(isinstance(x, dict) and set(x) == {'id', 'house', 'lane', 'due', 'paid', 'tries', 'state', 'last', 'on', 'excuse', 'counter'}
                 and x['state'] in FEE_STATES and (x['last'] is None or (isinstance(x['last'], str) and len(x['last']) <= 200)), 'Sổ thu phí sai.')
        for k in ('id', 'house', 'lane'):
            kit.text(x[k], 80)
        kit.integer(x['due'], 1, 100)
        kit.integer(x['paid'], 0, x['due'])
        kit.integer(x['tries'], 0, 999)
        kit.integer(x['on'], 0, 10 ** 7)
        kit.integer(x['excuse'], 0, len(FEE_EXCUSES) - 1)
        kit.integer(x['counter'], 0, x['due'])


# ---------------------------------------------------------------- troubles on the night round
TROUBLE = ('vandal', 'point')
TROUBLE_CHOICES = {'vandal': ('talk', 'photo', 'police', 'ignore'), 'point': ('wait', 'tidy', 'call', 'leave')}
VANDALS = (
    dict(v='kick', text='Nhóm thanh niên đi nhậu về đạp đổ xe rác cho vui, cười hô hố: “Rác rưởi mà cũng bày đặt đẩy xe!”', loss=8),
    dict(v='throw', text='Mấy đứa ngồi quán nhậu ném vỏ chai vào xe rác, trúng thành xe kêu choang: “Trúng rồi, 10 điểm!”', loss=4),
    dict(v='mock', text='Một cậu giơ điện thoại quay sát mặt bạn: “Anh em ơi, nghề nhặt rác nè, học dốt thì ra thế này nha!”', loss=0),
    dict(v='fire', text='Có đứa châm lửa đốt đống rác đầu ngõ, khói đen bốc lên, lửa liếm sát dây điện.', loss=0),
    dict(v='block', text='Hai chiếc xe máy độ dựng chắn ngang lối vào điểm tập kết, chủ xe ngồi rung đùi: “Đợi tí, tao đang nói chuyện.”', loss=0),
)
POINT_TEXT = 'Điểm tập kết đã tràn ra lòng đường, xe ép của chú Sáu kẹt xe chưa tới. Người đi đường bịt mũi, chửi om sòm.'


def _trouble_tick(s: dict, c: dict, d: dict) -> bool:
    tb = d['trouble']
    if not d['shift'] or d['desk']['ev'] is not None or not folk.trouble_due(tb, ID, c['day'], c['day_completed'], 50):
        return False
    k = 'vandal' if folk.roll('rac-trouble', c['day'], tb['fired']) < 70 else 'point'
    v = folk.roll('rac-vandal', c['day'], tb['seq']) % len(VANDALS)
    folk.trouble_open(tb, k, c['day'], 0, dict(v=v) if k == 'vandal' else dict(v=0))
    kit.log(s, c, 'surprise', VANDALS[v]['text'] if k == 'vandal' else POINT_TEXT, kit.npc_id(ID, 0), tb['ev']['id'])
    return True


def _trouble(s, c, d, p):
    tb = d['trouble']
    ev = tb['ev']
    kit.need(ev, 'Không có chuyện gì.')
    choice = kit.one_of(p.get('choice'), TROUBLE_CHOICES[ev['kind']], 'Chọn cách xử lý.')
    tr = folk.traits(ev['id'], 'bossy')
    good = None

    def wait_all(n):
        for x in c['tasks']:
            if x.get('career') == ID and x['status'] not in ('completed', 'referred', 'cancelled') and 'patience' in x:
                x['patience'] = max(25, x['patience'] - n)

    def lose(n, why):
        n = min(n, c['money'])
        if n:
            kit.money(s, c, -n, why, ev['id'], 'damage')
        return n
    if ev['kind'] == 'vandal':
        x = VANDALS[ev['facts']['v']]
        v = x['v']
        if v == 'fire':
            if choice == 'ignore':
                kit.review(s, c, kit.npc_id(ID, 1), 1, 'Lửa cháy đầu ngõ mà tổ thu gom đi ngang không dập, may mà hàng xóm kịp dội nước.', ev['id'])
                good, out = False, 'Bạn đi tiếp. Mười phút sau cả ngõ hò nhau xách nước dập lửa.'
            else:
                wait_all(4)
                c['xp'] += 5
                good, out = True, ('Bạn dội nước dập lửa, gọi 114 báo cho chắc.' if choice == 'police'
                                   else 'Bạn lấy xẻng xúc đất dập lửa, chụp ảnh gửi tổ dân phố.')
        elif choice == 'talk':
            how = folk.word(tr, 'answer')
            if how == 'calm':
                good, out = True, 'Bạn nói chuyện đàng hoàng. Tụi nó ngượng, dựng lại xe rác rồi đi.'
            elif how == 'sulk':
                n = lose(x['loss'] // 2, 'Sửa xe đẩy bị phá')
                good, out = None, 'Tụi nó cười khẩy bỏ đi.' + (f' Mất {n} xu sửa xe.' if n else '')
            else:
                n = lose(x['loss'], 'Sửa xe đẩy bị phá')
                good, out = False, (f'“Mày là cái thá gì mà dạy đời?” Tụi nó đạp thêm phát nữa. Mất {n} xu sửa xe.' if n
                                    else '“Mày là cái thá gì mà dạy đời? Rác rưởi mà cũng bày đặt!” Tụi nó cười hô hố, quay clip đăng lên mạng.')
        elif choice == 'photo':
            if tr['proud'] > 60:
                good, out = None, 'Bạn giơ điện thoại chụp. Tụi nó chửi um lên nhưng lảng đi.'
            else:
                good, out = True, 'Bạn chụp ảnh biển số, tụi nó vội vàng dựng lại xe rồi chuồn.'
            c['xp'] += 2
        elif choice == 'police':
            wait_all(6)
            good, out = True, 'Công an phường tới, lập biên bản. Tụi nó phải đền tiền sửa xe.'
            if x['loss']:
                kit.money(s, c, x['loss'], 'Đền tiền sửa xe đẩy', ev['id'], 'compensation')
        else:
            n = lose(x['loss'], 'Sửa xe đẩy bị phá')
            good, out = None, 'Bạn lặng lẽ làm tiếp, mặc kệ tụi nó.' + (f' Mất {n} xu sửa xe.' if n else '')
        title, emoji = 'Quậy phá lúc nửa đêm', '🛵'
    else:
        if choice == 'wait':
            wait_all(8)
            good, out = None, 'Bạn đứng đợi gần tiếng, xe ép mới tới. Người đi đường chửi cả tổ thu gom.'
        elif choice == 'tidy':
            wait_all(4)
            c['xp'] += 4
            good, out = True, 'Bạn xếp gọn bao rác sát tường, quét sạch lòng đường, rắc vôi khử mùi.'
        elif choice == 'call':
            if folk.roll('rac-point', ev['id']) < 60:
                good, out = True, 'Chú Sáu đổi lộ trình ghé trước. Điểm tập kết sạch sau nửa tiếng.'
            else:
                good, out = None, 'Chú Sáu tắt máy. Đành đợi.'
                wait_all(6)
        else:
            kit.review(s, c, kit.npc_id(ID, 3), 1, 'Điểm tập kết tràn ra đường cả đêm, tổ thu gom bỏ đi luôn.', ev['id'])
            good, out = False, 'Bạn bỏ về. Sáng ra ông Thước chụp ảnh gửi lên phường.'
        title, emoji = 'Điểm tập kết tràn', '🚛'
    folk.trouble_close(tb, out, good, choice, title, emoji)
    return dict(message=f'{emoji} {out}', correct=good is not False, celebrate=good is True)


ACTIONS = {
    'rac_gear': _gear, 'rac_cart': _cart, 'rac_open': _open,
    'rac_go': _go, 'rac_sweep': _sweep, 'rac_peek': _peek, 'rac_pull': _pull, 'rac_wrap': _wrap, 'rac_load': _load,
    'rac_note': _note, 'rac_next': _next, 'rac_finish': _finish_route, 'rac_dump': _dump,
    'rac_read': _read, 'rac_reply': _reply,
    'rac_refuse': _refuse, 'rac_hurt': _hurt, 'rac_pile': _pile, 'rac_grump': _grump, 'rac_fee': _fee, 'rac_trouble': _trouble,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['gear'], d['cart_ok'], d['shift'] = [], False, False
    d['today'] = _fresh_today(day)
    if day >= 2 and d['fees']['week'] != (day - 1) // 7:
        d['fees'] = _fee_book(day)   # a new week, a new round of the monthly fee
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


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK, hook=_desk_hook)
    today = d['today']
    lines = [f'🛒 Gom {today["bags"]} túi rác' + (f', {today["wrong"]} túi nhầm ngăn.' if today['wrong'] else ', túi nào vào ngăn nấy.')]
    if today['hazards']:
        lines.append(f'🔴 Tách {today["hazards"]} món nguy hại ra hộp đỏ.')
    if today['ve_chai']:
        lines.append(f'♻️ Cô Tám trả {today["ve_chai"]} xu tiền ve chai sạch.')
    if today['noted']:
        lines.append(f'📝 Nhắc {today["noted"]} nhà phân loại.')
    left = cart_load(d) + len(d['haz'])
    if left:
        today['overnight'] = left
        lines.append(f'🌙 Còn {left} túi, món trên xe lúc tan ca: chị Hạnh phải đẩy ra điểm tập kết giúp, không có tiền ve chai.')
        d['cart'], d['haz'] = _empty_cart(), []
    if today['late']:
        lines.append(f'⏰ {today["late"]} ngõ thu gom trễ giờ.')
    if desk_note:
        lines.append(desk_note)
    d['gear'], d['cart_ok'], d['shift'] = [], False, False   # gloves and masks worn today are thrown away
    stock = {g: kit.stock(c, g) for g in USED}
    low = [GEAR_LABEL[g] for g, q in stock.items() if q < 2]
    return dict(lines=lines, note=('Sắp hết ' + ', '.join(_lower(x) for x in low) + ': mở kho mua thêm.') if low else 'Găng tay, khẩu trang còn đủ cho ca sau.',
                bags=today['bags'], wrong=today['wrong'], hazards=today['hazards'], ve_chai=today['ve_chai'], overnight=left)


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    codes = {x['code'] for x in cq.slips(t)}
    if t['kind'] == 'setup':
        gear = 2 if codes & {'no_gloves', 'no_vest'} else 4 if 'gear' in codes else 5
        return dict(criteria=[dict(key='gear', label='Đồ bảo hộ', score=gear, note='đủ đồ bảo hộ' if gear == 5 else 'thiếu đồ bảo hộ'),
                              dict(key='cart', label='Kiểm xe', score=3 if 'cart' in codes else 5, note='xe chắc chắn' if 'cart' not in codes else 'chưa kiểm xe')])
    if t['kind'] == 'complaint':
        return dict(criteria=[dict(key='listen', label='Tìm hiểu kỹ', score=5 if len(t.get('read', [])) >= 2 else 3, note='hỏi rõ, xem tận nơi'),
                              dict(key='fair', label='Giải quyết công bằng', score=5 if not codes else 3 if 'half' in codes else 2,
                                   note='đúng lẽ, đúng quy định' if not codes else 'chưa trọn')])
    sort_ = 5 - (2 if 'bin' in codes else 0) - (2 if 'hazard' in codes else 0)
    time_ = 3 if 'late' in codes else 5 if p >= 60 else 4
    return dict(criteria=[dict(key='order', label='Gom đủ, không sót', score=3 if 'missed' in codes else 5, note='không sót túi nào' if 'missed' not in codes else 'bỏ sót túi'),
                          dict(key='sort', label='Đúng ngăn, tách nguy hại', score=max(1, sort_), note='phân loại chuẩn' if sort_ == 5 else 'lẫn ngăn hoặc lọt đồ nguy hại'),
                          dict(key='safe', label='An toàn', score=2 if codes & {'hurt', 'cut'} else 4 if codes & {'glass', 'mask'} else 5,
                               note='đồ sắc gói kỹ, đủ bảo hộ' if not codes & {'hurt', 'cut', 'glass', 'mask'} else 'chưa an toàn'),
                          dict(key='time', label='Đúng giờ', score=time_, note='đúng giờ thu gom' if time_ == 5 else 'trễ giờ')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return 'Chị Hạnh dặn: ' + ', '.join(_lower(GEAR_LABEL[g]) for g in n['gear']) + ', kiểm xe đẩy rồi vào ca. ' + n['note']
    if t['kind'] == 'complaint':
        return f'{_who(t)} phản ánh: “{t["opening"]}” {n["note"]}'
    bags = sum(len(st['bags']) for st in n['stops'])
    return f'{n["name"]}: {len(n["stops"])} nhà, {bags} túi rác. {n["note"]}'


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    v.pop('twist', None)     # where a razor hides and who will come out stay hidden
    v.pop('tw', None)
    if not v['known']:
        v['needs'] = None
        return v
    if t['kind'] == 'route':
        v['can'] = dict(rac_load=kit.check(_load_rules, t))
        # From outside a bag shows its colour and what pokes out; opening it shows what is inside.
        for si, st in enumerate(v['needs']['stops']):
            st['reached'] = si <= t['at'] and t['stage'] != 'prep'
            for b in st['bags']:
                b['open'] = b['id'] in t['opened']
                if not b['open']:
                    b['items'] = None
                b['loaded'] = t['loaded'].get(b['id'])
                b['pulled'] = list(t['pulled'].get(b['id'], []))
                b['wrapped'] = b['id'] in t['wrapped']
                b['refused'] = b['id'] in t.get('refused', [])
                tw = t.get('twist')
                if b['open'] and isinstance(tw, dict) and tw['kind'] == 'sharp' and tw['bag'] == b['id']:
                    b['items'] = list(b['items']) + [tw['item']]   # opened: the hidden razor or needle shows
    tw = t.get('twist')
    v.pop('twist', None)
    v.pop('tw', None)
    if isinstance(tw, dict) and t['tw']['state'] == 'on':
        # A twist shows once it happens; where it hides stays hidden.
        line = {'sharp': '', 'pile': PILE_LINES[tw['n']], 'grump': GRUMP_LINES[tw['n']]}[tw['kind']]
        v['twist'] = dict(kind=tw['kind'], state='on', line=line, item=tw.get('item') if tw['kind'] == 'sharp' else None,
                          bags=tw.get('bags'), stop=tw.get('stop'))
    if t['kind'] == 'complaint':
        x = CASE[t['needs']['case']]
        v['case'] = dict(facts=[dict(id=f['id'], title=f['title'], text=f['text'] if f['id'] in t['read'] else None) for f in x['facts']],
                         options=[dict(id=o['id'], label=o['label'], requires=list(o.get('requires', ()))) for o in x['options']])
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    return dict(intro=d['intro'], gear=d['gear'], cart_ok=d['cart_ok'], shift=d['shift'], cart=d['cart'], cap=CART, haz=d['haz'], haz_max=HAZ_MAX,
                mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']), clock=clock_min(c) if c['ext'].get('inv') else None,
                today=d['today'], stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()}, desk=kit.desk_public(d['desk'], DESK, ID),
                fees=dict(week=d['fees']['week'], rows=[dict(x, excuse=None) for x in d['fees']['rows']]),
                trouble=dict(ev=d['trouble']['ev'], last=d['trouble']['last'],
                             text=(VANDALS[d['trouble']['ev']['facts']['v']]['text'] if d['trouble']['ev']['kind'] == 'vandal' else POINT_TEXT) if d['trouble']['ev'] else None))


def content() -> dict:
    return dict(waste={k: dict(name=v[0], emoji=v[1], bin=v[2], sharp=v[3]) for k, v in WASTE.items()}, bins=list(BINS), bin_label=BIN_LABEL,
                bin_emoji=BIN_EMOJI, colors=COLOR_LABEL, color_bin=COLOR_BIN, gear=GEAR_LABEL, used=list(USED), cart=CART, haz_max=HAZ_MAX,
                ve_chai=VE_CHAI, intro=INTRO, people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE],
                choices=TW_CHOICES, troubles=TROUBLE_CHOICES)


def hint(c: dict, t: dict) -> str:
    k = t.get('kind')
    if k == 'setup':
        return 'Găng tay → khẩu trang → áo phản quang (mưa thì ủng) → kiểm xe → Vào ca.'
    if k == 'complaint':
        return 'Hỏi rõ, xem tận nơi → chọn cách giải quyết đúng lẽ, đúng quy định.'
    return 'Vào ngõ → nhìn túi, túi lạ thì mở → tách đồ nguy hại, bọc mảnh vỡ → bỏ đúng ngăn → nhắc nhà chưa phân loại → Xong ngõ.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = _data(c)
    if e.get('role') == 'sweep':
        if t and t.get('career') == ID and t.get('kind') == 'route' and t.get('late') and not t.get('swept') and t['stage'] == 'round':
            t['swept'] = True
            return 'Đã quét gom rác vương vãi ở đầu ngõ.'
        return 'Đã quét sạch quanh điểm tập kết.'
    if e.get('role') == 'push':
        return 'Đã đẩy phụ xe rác qua đoạn dốc.' if cart_load(d) else 'Đã rửa sạch ba ngăn xe đẩy.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu tổ thu gom sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc thu gom không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc thu gom sai.')
    n = t['needs']
    ids = {b['id'] for st in n.get('stops', []) for b in st['bags']} if isinstance(n, dict) else set()
    kit.integer(t.get('at'), 0, max(0, len(n.get('stops', [])) - 1) if isinstance(n, dict) else 0)
    kit.need(isinstance(t.get('loaded'), dict) and all(k in ids and v in BINS for k, v in t['loaded'].items()), 'Túi trên xe sai.')
    for k in ('opened', 'wrapped'):
        kit.need(isinstance(t.get(k), list) and len(t[k]) == len(set(t[k])) and set(t[k]) <= ids, 'Túi đã xem sai.')
    kit.need(isinstance(t.get('pulled'), dict) and all(k in ids and isinstance(v, list) and len(v) <= 4 and all(i in WASTE for i in v)
                                                       for k, v in t['pulled'].items()), 'Đồ nguy hại tách ra sai.')
    stops = len(n.get('stops', [])) if isinstance(n, dict) else 0
    kit.need(isinstance(t.get('noted'), list) and len(t['noted']) == len(set(t['noted'])) and all(type(i) is int and 0 <= i < max(1, stops) for i in t['noted']),
             'Nhà đã nhắc sai.')
    if t.get('arrived') is not None:
        kit.integer(t['arrived'], 0, 24 * 60 * 2)
    for k in ('late', 'swept', 'hurt'):
        _vbool(t.get(k))
    case = CASE.get(n.get('case')) if isinstance(n, dict) else None
    facts = {f['id'] for f in case['facts']} if case else set()
    kit.need(isinstance(t.get('read'), list) and set(t['read']) <= facts and len(t['read']) == len(set(t['read'])), 'Dữ kiện phản ánh sai.')
    kit.need(t.get('answer') is None or (case and t['answer'] in {o['id'] for o in case['options']}), 'Câu trả lời phản ánh sai.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện cư dân sai.')
    # 0.9.16 fields: absent on older lanes; when present they must be what twist_of gives and well formed.
    if 'twist' in t or 'tw' in t:
        tw, st = t.get('twist'), t.get('tw')
        kit.need(tw is not None and tw == twist_of(t), 'Chuyện của ngõ không khớp.')
        kit.need(isinstance(st, dict) and set(st) == {'state', 'choice'} and st['state'] in TW_STATES
                 and st['choice'] in (None, *TW_CHOICES[tw['kind']]), 'Chuyện của ngõ sai.')
    if 'refused' in t:
        kit.need(isinstance(t['refused'], list) and len(t['refused']) == len(set(t['refused'])) and set(t['refused']) <= ids, 'Túi từ chối thu sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    for k in ('intro', 'cart_ok', 'shift'):
        _vbool(d[k])
    kit.need(isinstance(d['gear'], list) and len(d['gear']) == len(set(d['gear'])) and set(d['gear']) <= set(GEAR), 'Đồ bảo hộ sai.')
    kit.need(isinstance(d['cart'], dict) and set(d['cart']) == set(BINS), 'Xe đẩy sai.')
    for b, x in d['cart'].items():
        kit.need(isinstance(x, dict) and set(x) == {'n', 'bad'}, 'Ngăn xe sai.')
        kit.integer(x['n'], 0, CART[b])
        kit.integer(x['bad'], 0, x['n'])
    kit.need(isinstance(d['haz'], list) and len(d['haz']) <= HAZ_MAX and all(i in WASTE for i in d['haz']), 'Hộp nguy hại sai.')
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ cư dân sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ cư dân sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu tổ thu gom sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)
    folk.validate_trouble(d['trouble'], TROUBLE, kit.need)
    _validate_fees(d['fees'])


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='rac_', category='outdoor',
    meta=dict(short='Thu gom rác', place='Tổ thu gom phường Mây', tagline='Ngõ sạch trước khi phố đi ngủ.', icon='truck',
              color='#2f8f5b', light='#e6f4ea', weather='Tối lên đèn trong ngõ', work='Ngõ thu gom', station='Xe đẩy ba ngăn',
              greeting='Đồ bảo hộ, kiểm xe, rồi đi từng ngõ đúng giờ. Túi nào lạ thì mở ra xem, pin với kim tiêm vào hộp đỏ nhé.',
              caption='Mỗi túi rác một ngăn', map_label='20 · TỔ THU GOM PHƯỜNG MÂY'),
    people=PEOPLE,
    staff=[('Tuyết', 'sweep', 'Quét đường mười năm, chổi đi tới đâu sạch tới đó.', 82, 86),
           ('Dũng', 'push', 'Khỏe như voi, đẩy xe lên dốc một mình.', 86, 74),
           ('Liên', 'sweep', 'Tỉ mỉ, không bỏ sót cọng rác nào.', 70, 94),
           ('Quang', 'push', 'Thuộc hết giờ xe ép của chú Sáu.', 80, 82)],
    roles={'sweep': 'Quét dọn', 'push': 'Đẩy xe'},
    inventory=dict(items=ITEMS, capacity=80),
    tip=0,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('🛒', 'Phân loại rác', [('Vỏ chuối', 'Ngăn hữu cơ'), ('Lon nhôm', 'Ngăn tái chế'), ('Hộp xốp dính dầu', 'Ngăn còn lại'), ('Pin cũ', 'Hộp đỏ')],
              ['Đeo găng, khẩu trang', 'Kiểm xe đẩy', 'Gom từng nhà đúng ngăn', 'Đổ xe ở điểm tập kết']),
    stories=[('Chiếc xe đẩy của chị Hạnh', ('Chiếc xe đẩy ba ngăn đã theo chị Hạnh mười hai năm, sơn xanh bong tróc.',
                                          'Chị dạy bạn nghe tiếng túi rác: lọc cọc là pin, leng keng là lon.',
                                          'Hết ca, chị rửa xe sạch bóng: “Xe sạch thì ngõ mới sạch.”')),
             ('Tờ hướng dẫn của bé Na', ('Bé Na vẽ tờ hướng dẫn phân loại rác bằng bút màu.',
                                        'Bạn dán giúp bé ở mỗi đầu ngõ, cạnh bảng giờ thu gom.',
                                        'Tháng sau, túi vàng ở ngõ 12 sạch hẳn, cô Tám khen mãi.')),
             ('Chuyến xe cuối', ('Mười giờ đêm, xe ép của chú Sáu tới điểm tập kết lần cuối.',
                                 'Bạn và chị Hạnh đổ nốt ngăn còn lại, rửa chỗ đậu xe.',
                                 'Chú Sáu bấm còi hai tiếng chào, phố đã sạch để đi ngủ.'))],
    review_asides=['Ngõ sạch bong trước giờ đi ngủ.', 'Nhắc phân loại nhẹ nhàng, dễ nghe.', 'Đúng giờ như đồng hồ.',
                   'Gói mảnh vỡ cẩn thận, ai đổ rác cũng yên tâm.'],
    situations=SITUATIONS,
    guide='Vào ca: găng tay, khẩu trang, áo phản quang, kiểm xe. Mỗi ngõ: vào đúng giờ → nhìn túi, túi lạ thì mở → tách đồ nguy hại → bỏ đúng ngăn → Xong ngõ. Xe đầy thì ra điểm tập kết.',
)
