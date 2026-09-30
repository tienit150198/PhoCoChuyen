"""Tiệm Sửa Đồ Chú Tư — a neighbourhood repair shop (plugin career).

Real work of the job: take the device in with a written intake slip (the symptom
in the customer's words, the visible condition, the accessories actually handed
over and — for phones — whether the customer allows data access), make the
device safe (unplug, discharge the capacitor, let the hot plate cool, put the
bike on the stand), run tests and measurements that rule hypotheses in or out
(each costs a turn and the customer's patience), write a QUOTE the customer must
accept BEFORE any repair, pick genuine or compatible parts from stock, repair,
close the case, run the final test, write a warranty slip and hand the device
back with its accessories.

Real consequences instead of hard walls: a wrong diagnosis shows up at the final
test (the wrong part is wasted and the shop must re-diagnose and re-quote);
opening a device that is still plugged in is a safety mistake; repairing without
an accepted quote is possible but serious; so is handing a device back without
the final test. What went wrong is recorded as consequences slips at the counter
(the customer may grumble, cut the bill or walk out; opening a live device is a
safety mistake with a complaint and an inspection). Real refusals: no data test on a phone without consent, and a
repair that is not worth the money can be returned honestly for a check fee.

v0.5 (tasks marked 'gen'): luck of the day, laptops, used parts with hidden unit
quality (test before fitting), a warranty book that customers come back to, the
"never got it wet" phone, rush jobs, second-hand phone buy-ins that may be stolen,
data requests that cross the line, and surprise desk events between customers.
Tasks saved before v0.5 keep the old generator (kit.LEGACY_TURN band).
"""
from __future__ import annotations
import copy
from . import kit
from .. import consequences as cq

ID = 'repair'
CHECK_FEE = 10           # posted at the counter: fee when a checked device is returned unrepaired
QUOTE_ROUNDS = 6
WARRANTY = (0, 7, 30, 90)
DONE = ('completed', 'referred', 'cancelled')
DATA_DEVICES = ('phone', 'laptop')
GEN = 2

GRADES = {
    'genuine': dict(name='Chính hãng', short='Hãng', warranty=90, note='Đắt hơn, bền, bảo hành 90 ngày.', durable='bền'),
    'compatible': dict(name='Tương thích', short='Tương thích', warranty=30, note='Rẻ hơn, độ bền vừa, bảo hành 30 ngày.',
                       durable='khá bền'),
    'standard': dict(name='Linh kiện thay', short='Thay mới', warranty=30, note='Chỉ có một loại, bảo hành 30 ngày.', durable='khá bền'),
    'used': dict(name='Đồ tháo máy', short='Tháo máy', warranty=7, note='Rẻ nhất nhưng hên xui: cắm thử trước khi lắp, bảo hành 7 ngày.',
                 durable='hên xui'),
    'none': dict(name='Vệ sinh / chỉnh', short='Không thay đồ', warranty=7, note='Chỉ tính công, bảo hành 7 ngày.', durable='khá bền'),
}
MARKS = {
    'crack': ('💥', 'Vết nứt'), 'scratch': ('〰️', 'Trầy xước'), 'dent': ('🔨', 'Móp méo'), 'rust': ('🟤', 'Gỉ sét'),
    'sticker': ('🏷️', 'Dán decal / tem'), 'scorch': ('🔥', 'Cháy xém'), 'tape': ('🩹', 'Quấn băng keo'), 'bent': ('↪️', 'Cong vênh'),
}
ACCESSORIES = {
    'case': ('🧳', 'Ốp lưng / hộp đựng'), 'charger': ('🔌', 'Củ & cáp sạc'), 'sim': ('💳', 'Thẻ SIM'), 'box': ('📦', 'Hộp máy'),
    'remote': ('🎛️', 'Điều khiển từ xa'), 'inner_pot': ('🥘', 'Lòng nồi'), 'cup': ('🥛', 'Cốc đong gạo'), 'spatula': ('🥄', 'Muôi xới'),
    'cord': ('➰', 'Dây nguồn rời'), 'basket': ('🧺', 'Giỏ xe'), 'lock': ('🔒', 'Ổ khóa xe'), 'pump': ('🎈', 'Bơm tay'),
    'cable': ('🔗', 'Cáp sạc'), 'tips': ('👂', 'Nút tai dự phòng'),
}
SAFETY = {
    'power_off': ('📴', 'Tắt nguồn & ngắt cáp pin'), 'unplug': ('🔌', 'Rút điện / cáp sạc'),
    'discharge': ('⚡', 'Xả tụ bằng điện trở'), 'cool': ('🧊', 'Chờ mâm nhiệt nguội'), 'stand': ('🛠️', 'Dựng xe lên giá, khóa bánh'),
}

DEVICES = {
    'phone': dict(name='Điện thoại', emoji='📱', safety=['power_off'], open='Sấy keo, tách màn', close='Dán keo, lắp màn',
                  marks=['crack', 'scratch', 'dent', 'sticker'], accessories=['case', 'charger', 'sim', 'box'], labor=30),
    'fan': dict(name='Quạt đứng', emoji='🌀', safety=['unplug', 'discharge'], open='Mở hộp tụ & motor', close='Bắt vít, lắp lồng quạt',
                marks=['bent', 'crack', 'rust', 'tape'], accessories=['remote', 'box'], labor=18),
    'cooker': dict(name='Nồi cơm điện', emoji='🍚', safety=['unplug', 'cool'], open='Lật đáy, mở vỏ nồi', close='Lắp đáy, siết vít',
                   marks=['dent', 'scorch', 'rust', 'crack'], accessories=['inner_pot', 'cup', 'spatula', 'cord'], labor=20),
    'bike': dict(name='Xe đạp', emoji='🚲', safety=['stand'], open='Tháo bánh & xích', close='Lắp bánh, căn phanh',
                 marks=['rust', 'scratch', 'bent', 'sticker'], accessories=['basket', 'lock', 'pump'], labor=12),
    'headphone': dict(name='Tai nghe bluetooth', emoji='🎧', safety=['unplug'], open='Tách vỏ củ tai', close='Ép vỏ, dán lưới loa',
                      marks=['scratch', 'crack', 'sticker', 'tape'], accessories=['case', 'cable', 'tips'], labor=15),
    'laptop': dict(name='Laptop', emoji='💻', safety=['unplug', 'power_off'], open='Tháo ốc, cạy nắp đáy', close='Đậy nắp đáy, bắt đủ ốc',
                   marks=['scratch', 'dent', 'sticker', 'crack'], accessories=['charger', 'case', 'box'], labor=26),
}

# Hypotheses the bench can test for. `left` is what the final test shows if it is still there.
FAULTS = {
    'phone': [
        dict(id='screen', name='Hỏng tấm màn hình', parts={'genuine': 'screen_g', 'compatible': 'screen_c', 'used': 'screen_u'}, supplies=[], mult=1.0,
             fix='Tách màn cũ, cắm thử màn mới, kiểm cảm ứng rồi mới dán keo.', left='Gọi vào vẫn đổ chuông mà màn vẫn tối thui.'),
        dict(id='battery', name='Pin chai', parts={'genuine': 'battery_g', 'compatible': 'battery_c', 'used': 'battery_u'}, supplies=[], mult=0.8,
             fix='Gỡ keo pin, cho pin cũ vào thùng cát chống cháy, lắp pin mới.', left='Pin vẫn tụt vèo vèo, 30% là sập nguồn.'),
        dict(id='lint', name='Cổng sạc kẹt bụi vải', parts={'none': None}, supplies=[], mult=0.4,
             fix='Khều bụi vải bằng tăm nhựa, xịt khí nén, lau cồn chân sạc.', left='Cắm sạc vẫn chập chờn, phải cầm nghiêng.'),
        dict(id='port', name='Gãy chân cổng sạc', parts={'standard': 'port'}, supplies=['solder'], mult=1.2,
             fix='Khò tháo cụm chân sạc cũ, hàn cụm mới, đo lại dòng sạc.', left='Cắm sạc vẫn chập chờn, phải cầm nghiêng.'),
        dict(id='water', name='Chập mạch do vào nước', parts={'none': None}, supplies=['ipa'], mult=1.3,
             fix='Tháo main, rửa bể siêu âm với cồn, sấy khô, chà sạch muối gỉ quanh IC.', left='Máy vẫn tự tắt, quanh chân sạc còn ẩm.'),
    ],
    'fan': [
        dict(id='capacitor', name='Tụ khởi động yếu', parts={'genuine': 'cap_g', 'compatible': 'cap_c'}, supplies=[], mult=0.8,
             fix='Cắt tụ cũ, nối tụ 1,5 µF mới, bọc mối nối cẩn thận.', left='Bật lên vẫn ù ù, cánh không tự quay.'),
        dict(id='motor', name='Cháy cuộn dây motor', parts={'standard': 'fan_motor', 'used': 'motor_u'}, supplies=[], mult=1.5,
             fix='Tháo motor cháy, lắp motor mới, đấu lại dây theo sơ đồ.', left='Cánh vẫn đứng im, vỏ motor nóng dần.'),
        dict(id='bearing', name='Bạc đạn khô dầu', parts={'none': None}, supplies=['oil'], mult=0.8,
             fix='Lau sạch bạc đạn, tra dầu, xoay tay cho dầu thấm đều.', left='Cánh vẫn quay ì ạch, kêu rít.'),
    ],
    'cooker': [
        dict(id='fuse', name='Đứt cầu chì nhiệt', parts={'standard': 'fuse'}, supplies=[], mult=0.8,
             fix='Bấm cos cầu chì nhiệt mới (không hàn — mối hàn sẽ chảy khi nóng).', left='Bấm nấu, mâm vẫn nguội ngắt.'),
        dict(id='heater', name='Đứt mâm nhiệt', parts={'standard': 'heater'}, supplies=[], mult=1.2,
             fix='Tháo mâm nhiệt cũ, lắp mâm mới, siết đều bốn ốc.', left='Bấm nấu, mâm vẫn nguội ngắt.'),
        dict(id='sensor', name='Kẹt lò xo cảm biến nhiệt', parts={'none': None}, supplies=['paste'], mult=0.8,
             fix='Cạo cặn cơm, chỉnh lò xo, bôi keo tản nhiệt mặt cảm biến.', left='Cơm vẫn nhảy nút sớm, khê đáy.'),
    ],
    'bike': [
        dict(id='tube', name='Thủng săm', parts={'standard': 'tube'}, supplies=[], mult=1.0,
             fix='Thay săm mới, kiểm vỏ xem còn gai đinh không.', left='Bánh sau lại mềm dần.'),
        dict(id='chain', name='Xích giãn, nhảy líp', parts={'standard': 'chain'}, supplies=['oil'], mult=1.0,
             fix='Cắt xích theo số mắt, nối xích mới, tra dầu.', left='Đạp mạnh vẫn lạch cạch nhảy líp.'),
        dict(id='brake', name='Mòn má phanh', parts={'standard': 'brake'}, supplies=[], mult=0.8,
             fix='Thay cặp má phanh, căn cho má ôm đều vành.', left='Bóp phanh vẫn lạch cạch, xe vẫn trôi.'),
    ],
    'headphone': [
        dict(id='hp_battery', name='Pin tai nghe chai', parts={'standard': 'hp_battery'}, supplies=['solder'], mult=1.2,
             fix='Tách vỏ, hàn pin mới, dán băng cách điện.', left='Nghe được 15 phút lại tự tắt.'),
        dict(id='driver', name='Rách màng củ loa', parts={'standard': 'driver'}, supplies=['solder'], mult=1.2,
             fix='Hàn củ loa mới, dán lưới, cân tiếng hai bên.', left='Bên trái vẫn nhỏ và rè.'),
        dict(id='dirt', name='Lưới loa bít ráy tai', parts={'none': None}, supplies=[], mult=0.5,
             fix='Tháo lưới, chải sạch, lau cồn, phơi khô rồi lắp lại.', left='Bên trái vẫn nhỏ hơn hẳn.'),
    ],
    'laptop': [
        dict(id='ram', name='Chân RAM bị oxi hóa', parts={'none': None}, supplies=[], mult=0.6,
             fix='Tháo thanh RAM, chà chân đồng bằng gôm, lau cồn, cắm lại cho khít.', left='Bấm nguồn vẫn kêu bíp bíp, màn đen.'),
        dict(id='ssd', name='Ổ SSD hỏng', parts={'standard': 'ssd'}, supplies=[], mult=1.0,
             fix='Thay ổ SSD mới, cài lại hệ điều hành, chép lại tài liệu khách mang theo.', left='Vẫn báo không tìm thấy ổ khởi động.'),
        dict(id='thermal', name='Quạt bám bụi, keo tản nhiệt khô', parts={'none': None}, supplies=['paste'], mult=0.9,
             fix='Vệ sinh quạt, thổi bụi lá tản nhiệt, cạo keo cũ, tra keo mới.', left='Dùng mười phút lại nóng ran rồi tắt.'),
    ],
}
# Hidden second problems that are only seen once the case is open (never a test hypothesis).
EXTRAS = {
    'fan': [dict(id='wire', name='Dây điện trong thân nứt vỏ', parts={'none': None}, supplies=['shrink'], mult=0.4,
                 found='Mở ra mới thấy dây điện trong thân quạt nứt vỏ, lòi lõi đồng — phải bọc lại kẻo giật điện.',
                 fix='Bọc lại mối dây bằng ống co nhiệt, khò cho ôm kín.', left='Dây điện nứt vỏ trong thân vẫn chưa bọc.')],
    'cooker': [dict(id='terminal', name='Cọc đấu dây nguồn cháy đen', parts={'standard': 'terminal'}, supplies=[], mult=0.5,
                    found='Mở đáy mới thấy cọc đấu dây nguồn cháy đen, lỏng — thủ phạm làm nóng và đứt cầu chì.',
                    fix='Thay cọc đấu mới, siết chặt đầu cos.', left='Cọc đấu dây nguồn cháy đen vẫn chưa thay.')],
    'bike': [dict(id='rimtape', name='Dây lót vành rách', parts={'standard': 'rimtape'}, supplies=[], mult=0.3,
                  found='Tháo lốp ra mới thấy dây lót vành rách, đầu nan hoa đâm thẳng vào săm — thay săm mà không thay cái này thì mai lại thủng.',
                  fix='Lót dây lót vành mới che kín đầu nan hoa.', left='Dây lót vành rách vẫn chưa thay, săm sẽ lại thủng.')],
}

TESTS = {
    'phone': [
        dict(id='call_test', name='Gọi thử vào máy', emoji='📞', mode='live', consent=False,
             read={'screen': 'Máy rung, đổ chuông nhưng màn vẫn tối đen', 'battery': 'Màn sáng, đổ chuông bình thường',
                   'lint': 'Màn sáng, đổ chuông bình thường', 'port': 'Màn sáng, đổ chuông bình thường',
                   'water': 'Lúc lên lúc tắt, màn chớp rồi sập nguồn'}),
        dict(id='usb_meter', name='Đo dòng sạc bằng USB tester', emoji='🔋', mode='live', consent=False,
             read={'screen': 'Dòng sạc 1,2 A ổn định', 'battery': 'Dòng 1,1 A ổn định nhưng % pin nhảy cóc',
                   'lint': 'Dòng nhảy 0 ↔ 0,6 A mỗi khi lay cáp', 'port': 'Dòng nhảy 0 ↔ 0,6 A mỗi khi lay cáp',
                   'water': 'Chưa bật máy đã hút 0,4 A — có chỗ chạm chập'}),
        dict(id='loupe', name='Soi cổng sạc bằng kính lúp', emoji='🔍', mode='any', consent=False,
             read={'screen': 'Cổng sạch, chân thẳng đều', 'battery': 'Cổng sạch, chân thẳng đều',
                   'lint': 'Đáy cổng nén chặt bụi vải túi quần', 'port': 'Chân tiếp xúc cong, một chân gãy lìa',
                   'water': 'Chân sạc lấm tấm gỉ xanh'}),
        dict(id='battery_health', name='Xem tình trạng pin trong Cài đặt', emoji='📊', mode='live', consent=True,
             read={'screen': 'Dung lượng tối đa 91% — bình thường', 'battery': 'Dung lượng tối đa 68% — pin đã chai',
                   'lint': 'Dung lượng tối đa 91% — bình thường', 'port': 'Dung lượng tối đa 91% — bình thường',
                   'water': 'Máy sập nguồn trước khi kịp mở Cài đặt'}),
        dict(id='battery_look', name='Soi pin & đo áp khi tải', emoji='🔎', mode='open', consent=False,
             read={'screen': 'Pin phẳng, giữ 3,9 V khi tải', 'battery': 'Pin tụt còn 3,4 V khi tải, tem pin đã 3 năm',
                   'lint': 'Pin phẳng, giữ 3,9 V khi tải', 'port': 'Pin phẳng, giữ 3,9 V khi tải',
                   'water': 'Pin phẳng, nhưng quanh đầu cáp pin có muối trắng'}),
        dict(id='water_tag', name='Soi tem báo nước trong máy', emoji='💧', mode='open', consent=False,
             read={'screen': 'Tem báo nước còn trắng tinh', 'battery': 'Tem báo nước còn trắng tinh',
                   'lint': 'Tem báo nước còn trắng tinh', 'port': 'Tem báo nước còn trắng tinh',
                   'water': 'Tem báo nước chuyển đỏ, main có muối trắng quanh IC'}),
    ],
    'fan': [
        dict(id='power', name='Cắm điện, bật số 1', emoji='🔌', mode='live', consent=False,
             read={'capacitor': 'Cánh đứng im, motor kêu ù nhẹ', 'motor': 'Cánh đứng im, motor kêu ù nhẹ', 'bearing': 'Cánh quay ì ạch, kêu rít'}),
        dict(id='push', name='Bật máy, mồi cánh bằng que', emoji='🥢', mode='live', consent=False,
             read={'capacitor': 'Mồi một cái là cánh quay đều, gió mạnh', 'motor': 'Mồi thế nào cũng không quay, thoảng mùi khét',
                   'bearing': 'Quay được nhưng rít, chậm dần'}),
        dict(id='spin', name='Xoay cánh bằng tay', emoji='🔄', mode='any', consent=False,
             read={'capacitor': 'Cánh nhẹ, quay trơn vài vòng', 'motor': 'Cánh nhẹ, quay trơn vài vòng', 'bearing': 'Cánh nặng, rít, dừng ngay'}),
        dict(id='cap_meter', name='Đo điện dung tụ', emoji='📏', mode='open', consent=False,
             read={'capacitor': '0,4 µF — tụ ghi 1,5 µF', 'motor': '1,5 µF — đạt', 'bearing': '1,5 µF — đạt'}),
        dict(id='coil_meter', name='Đo điện trở cuộn dây', emoji='🧮', mode='open', consent=False,
             read={'capacitor': '≈ 420 Ω — bình thường', 'motor': 'Không thông mạch (∞ Ω) — cuộn đứt', 'bearing': '≈ 420 Ω — bình thường'}),
    ],
    'cooker': [
        dict(id='power', name='Cắm điện, bấm nấu', emoji='🔌', mode='live', consent=False,
             read={'fuse': '3 phút sau mâm vẫn nguội ngắt', 'heater': '3 phút sau mâm vẫn nguội ngắt', 'sensor': 'Nóng nhanh, 5 phút đã nhảy sang ủ'}),
        dict(id='cord_check', name='Đo thông mạch dây nguồn', emoji='➰', mode='any', consent=False,
             read={'fuse': 'Dây nguồn thông mạch tốt', 'heater': 'Dây nguồn thông mạch tốt', 'sensor': 'Dây nguồn thông mạch tốt'}),
        dict(id='fuse_meter', name='Đo thông mạch cầu chì nhiệt', emoji='📏', mode='open', consent=False,
             read={'fuse': 'Không thông mạch (∞) — cầu chì đã đứt', 'heater': 'Thông mạch 0 Ω', 'sensor': 'Thông mạch 0 Ω'}),
        dict(id='heater_meter', name='Đo điện trở mâm nhiệt', emoji='🧮', mode='open', consent=False,
             read={'fuse': '≈ 70 Ω — bình thường', 'heater': '∞ Ω — mâm nhiệt đứt', 'sensor': '≈ 70 Ω — bình thường'}),
        dict(id='sensor_look', name='Nhấn thử lò xo cảm biến đáy', emoji='👆', mode='open', consent=False,
             read={'fuse': 'Cảm biến nhún êm, mặt sạch', 'heater': 'Cảm biến nhún êm, mặt sạch', 'sensor': 'Lò xo kẹt cứng, mặt cảm biến bám cặn cháy'}),
    ],
    'bike': [
        dict(id='ride', name='Đạp thử một vòng sân', emoji='🚲', mode='live', consent=False,
             read={'tube': 'Bánh sau mềm, đạp nặng như kéo cày', 'chain': 'Đạp mạnh có tiếng lạch cạch', 'brake': 'Đạp mạnh có tiếng lạch cạch'}),
        dict(id='squeeze', name='Bơm căng rồi bóp lốp', emoji='✊', mode='any', consent=False,
             read={'tube': 'Bơm căng, 2 phút sau mềm hẳn', 'chain': 'Lốp căng, giữ hơi tốt', 'brake': 'Lốp căng, giữ hơi tốt'}),
        dict(id='chain_gauge', name='Thước đo độ giãn xích', emoji='📏', mode='any', consent=False,
             read={'tube': 'Giãn 0,3% — ổn', 'chain': 'Giãn 1% — quá giới hạn 0,75%', 'brake': 'Giãn 0,3% — ổn'}),
        dict(id='brake_look', name='Soi má phanh', emoji='👀', mode='any', consent=False,
             read={'tube': 'Má phanh còn rãnh rõ', 'chain': 'Má phanh còn rãnh rõ', 'brake': 'Má phanh mòn trơ, lỏng ốc, hết rãnh'}),
        dict(id='water', name='Tháo săm, nhúng chậu nước', emoji='💧', mode='open', consent=False,
             read={'tube': 'Sủi bọt đều ở một lỗ nhỏ', 'chain': 'Không sủi bọt', 'brake': 'Không sủi bọt'}),
    ],
    'headphone': [
        dict(id='sound', name='Phát nhạc thử từng bên', emoji='🎵', mode='live', consent=False,
             read={'hp_battery': 'Hai bên trong trẻo, 15 phút sau tự tắt', 'driver': 'Bên trái nhỏ hơn hẳn bên phải', 'dirt': 'Bên trái nhỏ hơn hẳn bên phải'}),
        dict(id='mesh', name='Soi lưới loa bằng đèn pin', emoji='🔦', mode='any', consent=False,
             read={'hp_battery': 'Lưới loa sạch', 'driver': 'Lưới loa sạch', 'dirt': 'Lưới loa trái bít kín ráy tai'}),
        dict(id='batt_meter', name='Đo áp pin khi phát to', emoji='📏', mode='open', consent=False,
             read={'hp_battery': 'Tụt còn 3,2 V khi phát to', 'driver': 'Giữ 3,8 V ổn định', 'dirt': 'Giữ 3,8 V ổn định'}),
        dict(id='driver_meter', name='Đo trở kháng củ loa', emoji='🧮', mode='open', consent=False,
             read={'hp_battery': 'Hai bên đều 32 Ω', 'driver': 'Trái 9 Ω, phải 32 Ω — màng loa rách', 'dirt': 'Hai bên đều 32 Ω'}),
    ],
    'laptop': [
        dict(id='boot', name='Bấm nguồn, nghe tiếng máy', emoji='🔊', mode='live', consent=False,
             read={'ram': 'Kêu bíp bíp liên hồi, màn đen thui', 'ssd': 'Lên logo rồi báo không tìm thấy ổ khởi động',
                   'thermal': 'Vào máy bình thường, quạt rít to'}),
        dict(id='bios', name='Vào BIOS xem phần cứng', emoji='🧭', mode='live', consent=False,
             read={'ram': 'Không vào được BIOS', 'ssd': 'BIOS không thấy ổ SSD nào', 'thermal': 'Đủ RAM, đủ ổ — CPU đã 92°C'}),
        dict(id='temp', name='Mở máy, xem nhiệt độ trong phần mềm', emoji='🌡️', mode='live', consent=True,
             read={'ram': 'Không vào được máy để xem', 'ssd': 'Không vào được máy để xem', 'thermal': 'CPU 98°C chỉ với một trình duyệt'}),
        dict(id='fan_look', name='Soi quạt & lá tản nhiệt', emoji='🔦', mode='open', consent=False,
             read={'ram': 'Quạt sạch, quay êm', 'ssd': 'Quạt sạch, quay êm', 'thermal': 'Lá tản nhiệt bít kín bụi, keo khô nứt'}),
        dict(id='ram_swap', name='Cắm thanh RAM thử của tiệm', emoji='🧩', mode='open', consent=False,
             read={'ram': 'Đổi RAM thử là máy lên hình ngay', 'ssd': 'Đổi RAM thử vẫn báo không có ổ', 'thermal': 'Đổi RAM thử không khác gì'}),
    ],
}
TEST_INDEX = {dev: {x['id']: x for x in rows} for dev, rows in TESTS.items()}

ITEMS = [
    dict(id='screen_c', name='Màn hình tương thích', emoji='📱', group='phone', unit='tấm', cost=22, price=38, start=3),
    dict(id='screen_g', name='Màn hình chính hãng', emoji='📲', group='phone', unit='tấm', cost=40, price=62, start=1, unlock=2),
    dict(id='battery_c', name='Pin điện thoại tương thích', emoji='🔋', group='phone', unit='viên', cost=9, price=18, start=3),
    dict(id='battery_g', name='Pin điện thoại chính hãng', emoji='🔋', group='phone', unit='viên', cost=16, price=30, start=2),
    dict(id='port', name='Cụm chân sạc', emoji='🔌', group='phone', unit='cụm', cost=5, price=12, start=3),
    dict(id='cap_c', name='Tụ quạt 1,5 µF loại thường', emoji='🥫', group='fan', unit='con', cost=2, price=6, start=5),
    dict(id='cap_g', name='Tụ quạt 1,5 µF hàng hãng', emoji='🥫', group='fan', unit='con', cost=4, price=10, start=3),
    dict(id='fan_motor', name='Motor quạt đứng', emoji='⚙️', group='fan', unit='cái', cost=30, price=48, start=1, unlock=3),
    dict(id='fuse', name='Cầu chì nhiệt nồi cơm', emoji='🧷', group='cooker', unit='con', cost=2, price=6, start=4),
    dict(id='terminal', name='Cọc đấu dây nguồn', emoji='🔩', group='cooker', unit='bộ', cost=2, price=5, start=3),
    dict(id='heater', name='Mâm nhiệt nồi cơm', emoji='♨️', group='cooker', unit='cái', cost=28, price=45, start=1, unlock=2),
    dict(id='tube', name='Săm xe đạp', emoji='⭕', group='bike', unit='cái', cost=4, price=8, start=4),
    dict(id='rimtape', name='Dây lót vành', emoji='🎗️', group='bike', unit='sợi', cost=1, price=4, start=4),
    dict(id='chain', name='Xích xe đạp', emoji='⛓️', group='bike', unit='sợi', cost=9, price=16, start=2),
    dict(id='brake', name='Má phanh (cặp)', emoji='🟫', group='bike', unit='cặp', cost=3, price=7, start=4),
    dict(id='hp_battery', name='Pin tai nghe', emoji='🪫', group='headphone', unit='viên', cost=7, price=14, start=2),
    dict(id='driver', name='Củ loa tai nghe', emoji='🔊', group='headphone', unit='củ', cost=8, price=16, start=2),
    dict(id='solder', name='Thiếc hàn', emoji='🧵', group='supply', unit='đoạn', cost=1, start=12),
    dict(id='paste', name='Keo tản nhiệt', emoji='🧴', group='supply', unit='lần bôi', cost=1, start=8, life=30),
    dict(id='oil', name='Dầu bôi trơn', emoji='🛢️', group='supply', unit='lần tra', cost=1, start=10),
    dict(id='shrink', name='Ống co nhiệt', emoji='🌡️', group='supply', unit='đoạn', cost=1, start=8),
    # v0.5 — old saves get these opening lots once (see _topup_stock).
    dict(id='screen_u', name='Màn hình tháo máy', emoji='📱', group='phone', unit='tấm', cost=8, price=20, start=3),
    dict(id='battery_u', name='Pin tháo máy', emoji='🔋', group='phone', unit='viên', cost=3, price=8, start=3),
    dict(id='motor_u', name='Motor quạt tháo máy', emoji='⚙️', group='fan', unit='cái', cost=10, price=22, start=2),
    dict(id='ssd', name='Ổ SSD 256 GB', emoji='💽', group='laptop', unit='ổ', cost=18, price=32, start=2),
    dict(id='ipa', name='Cồn rửa main', emoji='🧪', group='supply', unit='lần rửa', cost=1, start=6),
]
NEW_ITEMS = ('screen_u', 'battery_u', 'motor_u', 'ssd', 'ipa')
USED_BAD_READ = {'screen_u': 'sọc xanh một góc, cảm ứng liệt nửa màn', 'battery_u': 'áp tụt còn 3,3 V khi tải nhẹ',
                 'motor_u': 'quay rung bần bật, nóng lên rất nhanh'}
ITEM_INDEX = {x['id']: x for x in ITEMS}

PEOPLE = [
    ('Chị Diệp', 'Nhân viên ngân hàng', 'Máy nào cũng dán cường lực, rất giữ dữ liệu riêng.', 'picky'),
    ('Ông Bảy', 'Hưu trí, hàng xóm', 'Quạt dùng từ hồi con gái út còn đi mẫu giáo.', 'bossy'),
    ('Bé Ngân', 'Sinh viên năm hai', 'Tai nghe là mạng sống, ví thì mỏng như lưới loa.', 'genz'),
    ('Cô Sáu', 'Bán xôi đầu hẻm', 'Nồi cơm là cần câu cơm, hỏng là cuống.', 'warm'),
    ('Anh Khoa', 'Shipper xe đạp', 'Nói ít, cần xe chạy lại ngay.', 'quiet'),
    ('Bà Tám', 'Chủ nhà trọ', 'Hỏi giá ba lần, trả giá bốn lần.', 'sour'),
    ('Lâm Linh Kiện', 'Mối buôn linh kiện', 'Giao hàng tận tiệm, nói nhanh như máy khâu.', 'bossy'),
    ('Chị Hạnh', 'Nhân viên văn phòng', 'Đổi máy mới, muốn bán lại máy cũ cho gọn.', 'warm'),
    ('Khách lạ bán máy', 'Ghé tiệm một lần', 'Nói nhanh, mắt cứ liếc ra đường.', 'quiet'),
]

# (npc, device, fault, extra, title, opening, symptom, marks, accessories, budget, genuine_only, data_ok, min_day, note)
JOBS = [
    (0, 'phone', 'screen', None, 'Điện thoại đen màn mà vẫn đổ chuông', 'Chú Tư ơi, cứu cái điện thoại của con với!',
     'Tự nhiên màn hình tối thui, gọi vào vẫn rung, chuông vẫn reo.', ['scratch', 'sticker'], ['case', 'sim'], 80, False, True, 1,
     'Chị cần máy trước giờ họp chiều. Trong máy toàn dữ liệu công việc, đừng làm mất gì nhé.'),
    (1, 'fan', 'capacitor', 'wire', 'Quạt kêu ù ù mà không quay', 'Cái quạt của tôi lại dở chứng rồi, cậu xem giùm.',
     'Bật lên nó cứ ù ù, cánh đứng im. Lấy que đẩy một cái thì nó lại quay!', ['bent', 'tape'], ['remote'], 45, False, None, 1,
     'Quạt này theo tôi mười hai năm rồi, sửa được thì sửa, đừng bảo mua cái mới.'),
    (2, 'headphone', 'dirt', None, 'Tai nghe bên trái nhỏ tiếng', 'Anh ơi tai nghe em bị bệnh lạ lắm ạ.',
     'Bên trái nghe nhỏ xíu à, bên phải thì bình thường.', ['scratch'], ['case', 'tips'], 30, False, None, 1,
     'Ví em đang mỏng như lưới loa, anh báo giá nhẹ nhàng thôi nha 😭'),
    (3, 'cooker', 'fuse', 'terminal', 'Nồi cơm cắm điện mà không nóng', 'Chú Tư ơi, cái nồi của cô đình công rồi!',
     'Sáng nay cắm điện bấm nấu mà mâm cứ nguội ngắt.', ['dent', 'scorch'], ['inner_pot', 'cup'], 60, False, None, 1,
     'Chiều nay cô phải đồ mẻ xôi mới, cứu cô với.'),
    (4, 'bike', 'tube', 'rimtape', 'Xe đạp xẹp bánh sau', 'Anh sửa xe giùm em.',
     'Bánh sau sáng bơm, chiều xẹp.', ['rust', 'scratch'], ['basket', 'lock'], 45, False, None, 1,
     'Nhanh giúp em, còn chạy đơn.'),
    (5, 'phone', 'lint', None, 'Sạc chập chờn, phải cầm nghiêng', 'Này cậu, xem cái máy sạc không vào của tôi.',
     'Cắm sạc phải nghiêng nghiêng mới vào. Chắc hư chân sạc rồi hả?', ['crack'], ['charger'], 60, False, False, 1,
     'Nói trước: tôi không cho ai mở khóa xem dữ liệu đâu nhé.'),
    (0, 'phone', 'battery', None, 'Pin tụt nhanh, 30% là sập nguồn', 'Em ơi, pin chị dạo này yếu quá.',
     'Pin tụt nhanh lắm, còn 30% là sập nguồn cái rụp.', ['scratch'], ['case', 'charger', 'box'], 70, True, True, 2,
     'Chị muốn pin chính hãng thôi, còn dùng máy này hai năm nữa.'),
    (2, 'headphone', 'driver', None, 'Tai nghe bên trái lúc to lúc nhỏ', 'Anh ơi cứu con tai nghe em với ạ.',
     'Bên trái nhỏ hơn hẳn, nghe nhạc bass thấy lạ lạ.', ['sticker', 'scratch'], ['case', 'cable'], 40, False, None, 2,
     'Mai em có buổi thuyết trình online, cần tai nghe gấp.'),
    (4, 'bike', 'chain', None, 'Xe đạp kêu lạch cạch khi đạp mạnh', 'Anh xem giùm, xe kêu quá.',
     'Đạp mạnh lên dốc là kêu lạch cạch.', ['rust'], ['basket', 'pump'], 35, False, None, 2,
     'Xe chở hàng cả ngày, đừng để hỏng giữa dốc.'),
    (3, 'cooker', 'heater', None, 'Nồi cơm bấm nấu mà mâm nguội', 'Lại là cô đây, cái nồi thứ hai của cô…',
     'Bấm nấu được mà mâm chẳng nóng lên chút nào.', ['dent'], ['inner_pot', 'spatula', 'cord'], 80, False, None, 3,
     'Nồi này nấu xôi ngon nhất, sửa giùm cô.'),
    (5, 'phone', 'port', None, 'Cắm sạc lỏng lẻo, lúc vào lúc không', 'Cậu xem cái máy của tôi, lại hư sạc.',
     'Cắm sạc phải cầm nghiêng, buông tay là mất.', ['crack', 'dent'], ['charger', 'sim'], 55, False, False, 3,
     'Đừng có mở khóa máy tôi ra coi, sửa phần cứng thôi.'),
    (1, 'fan', 'bearing', None, 'Quạt quay chậm, kêu rít', 'Cậu nghe cái quạt nó rên này.',
     'Bật lên nó quay chậm rì, kêu rít như cửa cũ.', ['rust'], ['remote', 'box'], 25, False, None, 2,
     'Tra dầu là hết chứ gì, tôi biết mà.'),
    (2, 'headphone', 'hp_battery', None, 'Tai nghe nghe 15 phút là tắt', 'Anh ơi tai nghe em sống không quá 15 phút ạ.',
     'Sạc đầy mà nghe tầm 15 phút là tự tắt.', ['scratch', 'tape'], ['case', 'cable', 'tips'], 40, False, None, 3,
     'Em đi xe buýt 40 phút, tai nghe tắt giữa đường buồn lắm.'),
    (4, 'bike', 'brake', None, 'Phanh xe bóp không ăn', 'Anh ơi phanh xe em có vấn đề.',
     'Bóp phanh xe vẫn trôi, lâu lâu kêu lạch cạch.', ['scratch', 'sticker'], ['lock'], 25, False, None, 3,
     'Chở hàng xuống dốc mà phanh không ăn là toang.'),
    (3, 'cooker', 'sensor', None, 'Cơm khê đáy, nồi nhảy nút sớm', 'Nồi cô nấu cơm khê hoài.',
     'Nấu chưa chín đã nhảy nút, đáy thì khê.', ['scorch'], ['inner_pot', 'cup'], 30, False, None, 4,
     'Khách ăn xôi khen dạo này hơi cháy cạnh.'),
    (1, 'fan', 'motor', None, 'Quạt có mùi khét, không quay', 'Quạt của tôi bốc mùi khét, cậu xem sao.',
     'Hôm qua nó bốc mùi khét, giờ bật lên chỉ ù ù.', ['bent', 'rust'], ['remote'], 40, False, None, 5,
     'Sửa bao nhiêu cũng được… mà thôi, đừng quá 40 xu.'),
]

LEVEL_BY_DAY = lambda day: 1 + (day - 1) // 2   # rough level hint used only to avoid locked-part jobs early


def _round(v: float) -> int:
    return int(v + 0.5)


def _fault_def(device: str, fault: str) -> dict | None:
    return next((f for f in FAULTS[device] + EXTRAS.get(device, []) if f['id'] == fault), None)


def _hyp(device: str) -> list[str]:
    return [f['id'] for f in FAULTS[device]]


V1_HYP = {'phone': ['screen', 'battery', 'lint', 'port'], 'fan': ['capacitor', 'motor', 'bearing'],
          'cooker': ['fuse', 'heater', 'sensor'], 'bike': ['tube', 'chain', 'brake'], 'headphone': ['hp_battery', 'driver', 'dirt']}


def _make_v1(day: int, slot: int, serial: int) -> dict:
    """The generator saves made before v0.5 were validated against (do not change)."""
    pool = [j for j in JOBS if j[12] <= day]
    order = list(pool)
    kit.rng(ID, day).shuffle(order)
    npc, device, fault, extra, title, opening, symptom, marks, acc, budget, genuine, data_ok, _, note = order[slot % len(order)]
    needs = dict(device=device, symptom=symptom, marks=list(marks), accessories=list(acc), budget=budget,
                 genuine_only=genuine, note=note, hypotheses=list(V1_HYP[device]))
    return kit.base_task(ID, day, slot, serial, npc, title, opening, needs=needs, bench=_empty_bench(),
                         _fault=fault, _extra=extra, _data_ok=data_ok, _value=budget)


# ------------------------------------------------------------------------------ v0.5 jobs
# Luck of the day: rolled from (career, day) only, stored in data at the day start.
TODAY = [
    dict(id='steady', title='Phố yên ả', emoji='☀️', text='Khách tới thong thả, hợp để làm kỹ từng máy.', weight=2),
    dict(id='rain', title='Mưa dầm cả ngày', emoji='🌧️', text='Hay gặp máy vô nước và xe xẹp bánh.', min_day=2, weight=2),
    dict(id='heat', title='Nắng nóng đỉnh điểm', emoji='🥵', text='Quạt với nồi cơm hỏng dồn dập.', min_day=2),
    dict(id='exams', title='Mùa thi cử', emoji='📚', text='Học sinh mang tai nghe, laptop tới — ví thì mỏng.', min_day=3),
    dict(id='outage', title='Cúp điện luân phiên', emoji='🔌', text='Chạy thử có điện phải nổ máy phát: 2 xu mỗi lần.', min_day=3),
    dict(id='market', title='Phiên chợ cuối tuần', emoji='🛒', text='Đông khách, ai cũng muốn lấy máy gấp.', min_day=4),
]
TODAY_INDEX = {x['id']: x for x in TODAY}
SPECIAL_P = (0.0, 0.34, 0.45, 0.55)       # chance a slot (after the first) is a special case, by tier
USED_BAD = (0.25, 0.3, 0.35, 0.4)        # chance a used part unit is dead, by tier
CASES = {
    'water': dict(emoji='💧', label='Khách nói chưa từng dính nước'),
    'warranty': dict(emoji='📒', label='Mang phiếu bảo hành cũ tới'),
    'rush': dict(emoji='⏱️', label='Cần lấy gấp'),
    'buyin': dict(emoji='🤝', label='Muốn bán lại máy cũ'),
    'privacy': dict(emoji='🔐', label='Nhờ thêm chuyện dữ liệu'),
    'bargain': dict(emoji='🪙', label='Ví mỏng'),
}


def _j(key, npc, device, fault, title, opening, symptom, marks, acc, budget, note, min_day=1, extra=None, genuine=False,
       data_ok=None, case=None, mods=(), weight=1, **more):
    return dict(key=key, npc=npc, device=device, fault=fault, extra=extra, title=title, opening=opening, symptom=symptom,
                marks=list(marks), acc=list(acc), budget=budget, genuine=genuine, data_ok=data_ok, min_day=min_day,
                note=note, case=case, mods=tuple(mods), weight=weight, more=more)


JOBS2 = [
    # Everyday repairs (the classic bench loop). The customer speaks to whoever is at the bench.
    _j('c_screen', 0, 'phone', 'screen', 'Điện thoại đen màn mà vẫn đổ chuông', 'Em ơi, cứu cái điện thoại của chị với!',
       'Tự nhiên màn hình tối thui, gọi vào vẫn rung, chuông vẫn reo.', ['scratch', 'sticker'], ['case', 'sim'], 80,
       'Chị cần máy trước giờ họp chiều. Trong máy toàn dữ liệu công việc, đừng làm mất gì nhé.', data_ok=True),
    _j('c_cap', 1, 'fan', 'capacitor', 'Quạt kêu ù ù mà không quay', 'Cái quạt của ông lại dở chứng rồi, cháu xem giùm.',
       'Bật lên nó cứ ù ù, cánh đứng im. Lấy que đẩy một cái thì nó lại quay!', ['bent', 'tape'], ['remote'], 45,
       'Quạt này theo ông mười hai năm rồi, sửa được thì sửa, đừng bảo mua cái mới.', extra='wire', mods=('heat',)),
    _j('c_dirt', 2, 'headphone', 'dirt', 'Tai nghe bên trái nhỏ tiếng', 'Tiệm ơi, tai nghe của em bị bệnh lạ lắm ạ.',
       'Bên trái nghe nhỏ xíu à, bên phải thì bình thường.', ['scratch'], ['case', 'tips'], 30,
       'Ví em đang mỏng như lưới loa, báo giá nhẹ nhàng thôi nha 😭', mods=('exams',)),
    _j('c_fuse', 3, 'cooker', 'fuse', 'Nồi cơm cắm điện mà không nóng', 'Cháu ơi, cái nồi của cô đình công rồi!',
       'Sáng nay cắm điện bấm nấu mà mâm cứ nguội ngắt.', ['dent', 'scorch'], ['inner_pot', 'cup'], 60,
       'Chiều nay cô phải đồ mẻ xôi mới, cứu cô với.', extra='terminal', mods=('heat',)),
    _j('c_tube', 4, 'bike', 'tube', 'Xe đạp xẹp bánh sau', 'Sửa xe giùm mình với, đang chạy đơn.',
       'Bánh sau sáng bơm, chiều xẹp.', ['rust', 'scratch'], ['basket', 'lock'], 45, 'Nhanh giúp mình, còn chạy đơn.',
       extra='rimtape', mods=('rain',)),
    _j('c_lint', 5, 'phone', 'lint', 'Sạc chập chờn, phải cầm nghiêng', 'Này cháu, xem cái máy sạc không vào của bà.',
       'Cắm sạc phải nghiêng nghiêng mới vào. Chắc hư chân sạc rồi hả?', ['crack'], ['charger'], 60,
       'Nói trước: bà không cho ai mở khóa xem dữ liệu đâu nhé.', data_ok=False),
    _j('c_battery', 0, 'phone', 'battery', 'Pin tụt nhanh, 30% là sập nguồn', 'Em ơi, pin chị dạo này yếu quá.',
       'Pin tụt nhanh lắm, còn 30% là sập nguồn cái rụp.', ['scratch'], ['case', 'charger', 'box'], 70,
       'Chị muốn pin chính hãng thôi, còn dùng máy này hai năm nữa.', min_day=2, genuine=True, data_ok=True),
    _j('c_driver', 2, 'headphone', 'driver', 'Tai nghe bên trái lúc to lúc nhỏ', 'Tiệm ơi, cứu con tai nghe của em với ạ.',
       'Bên trái nhỏ hơn hẳn, nghe nhạc bass thấy lạ lạ.', ['sticker', 'scratch'], ['case', 'cable'], 40,
       'Mai em có buổi thuyết trình online, cần tai nghe gấp.', min_day=2, mods=('exams',)),
    _j('c_chain', 4, 'bike', 'chain', 'Xe đạp kêu lạch cạch khi đạp mạnh', 'Xe kêu quá, xem giùm mình với.',
       'Đạp mạnh lên dốc là kêu lạch cạch.', ['rust'], ['basket', 'pump'], 35, 'Xe chở hàng cả ngày, đừng để hỏng giữa dốc.', min_day=2),
    _j('c_bearing', 1, 'fan', 'bearing', 'Quạt quay chậm, kêu rít', 'Cháu nghe cái quạt nó rên này.',
       'Bật lên nó quay chậm rì, kêu rít như cửa cũ.', ['rust'], ['remote', 'box'], 25, 'Tra dầu là hết chứ gì, ông biết mà.',
       min_day=2, mods=('heat',)),
    _j('c_heater', 3, 'cooker', 'heater', 'Nồi cơm bấm nấu mà mâm nguội', 'Lại là cô đây, cái nồi thứ hai của cô…',
       'Bấm nấu được mà mâm chẳng nóng lên chút nào.', ['dent'], ['inner_pot', 'spatula', 'cord'], 80,
       'Nồi này nấu xôi ngon nhất, sửa giùm cô.', min_day=3, mods=('heat',)),
    _j('c_port', 5, 'phone', 'port', 'Cắm sạc lỏng lẻo, lúc vào lúc không', 'Cháu xem cái máy của bà, lại hư sạc.',
       'Cắm sạc phải cầm nghiêng, buông tay là mất.', ['crack', 'dent'], ['charger', 'sim'], 55,
       'Đừng có mở khóa máy bà ra coi, sửa phần cứng thôi.', min_day=3, data_ok=False),
    _j('c_hpbat', 2, 'headphone', 'hp_battery', 'Tai nghe nghe 15 phút là tắt', 'Tiệm ơi, tai nghe em sống không quá 15 phút ạ.',
       'Sạc đầy mà nghe tầm 15 phút là tự tắt.', ['scratch', 'tape'], ['case', 'cable', 'tips'], 40,
       'Em đi xe buýt 40 phút, tai nghe tắt giữa đường buồn lắm.', min_day=3, mods=('exams',)),
    _j('c_brake', 4, 'bike', 'brake', 'Phanh xe bóp không ăn', 'Phanh xe mình có vấn đề rồi.',
       'Bóp phanh xe vẫn trôi, lâu lâu kêu lạch cạch.', ['scratch', 'sticker'], ['lock'], 25,
       'Chở hàng xuống dốc mà phanh không ăn là toang.', min_day=3, mods=('rain',)),
    _j('c_sensor', 3, 'cooker', 'sensor', 'Cơm khê đáy, nồi nhảy nút sớm', 'Nồi cô nấu cơm khê hoài.',
       'Nấu chưa chín đã nhảy nút, đáy thì khê.', ['scorch'], ['inner_pot', 'cup'], 30,
       'Khách ăn xôi khen dạo này hơi cháy cạnh.', min_day=4),
    _j('c_motor', 1, 'fan', 'motor', 'Quạt có mùi khét, không quay', 'Quạt của ông bốc mùi khét, cháu xem sao.',
       'Hôm qua nó bốc mùi khét, giờ bật lên chỉ ù ù.', ['bent', 'rust'], ['remote'], 40,
       'Sửa bao nhiêu cũng được… mà thôi, đừng quá 40 xu.', min_day=5),
    _j('c_ram', 2, 'laptop', 'ram', 'Laptop bật lên kêu bíp bíp', 'Tiệm ơi, mai em nộp đồ án mà laptop kêu bíp bíp!',
       'Bấm nguồn thì đèn sáng, quạt quay, kêu bíp bíp liên hồi mà màn đen thui.', ['sticker', 'scratch'], ['charger'], 45,
       'Đồ án nằm trong máy hết, đừng làm mất file của em nha.', min_day=3, data_ok=True, mods=('exams',)),
    _j('c_ssd', 0, 'laptop', 'ssd', 'Laptop báo không tìm thấy ổ', 'Em ơi, laptop của chị không vào được nữa.',
       'Lên logo rồi hiện dòng chữ tiếng Anh gì đó, không vào được máy.', ['scratch'], ['charger', 'case'], 70,
       'Tài liệu chị có bản sao rồi, chỉ cần máy chạy lại để làm việc.', min_day=3, data_ok=True),
    _j('c_thermal', 6, 'laptop', 'thermal', 'Laptop nóng ran, tự tắt', 'Tiệm ơi, laptop mình dùng mười phút là tắt phụt.',
       'Mở máy làm sổ sách được mười phút là nóng ran rồi tự tắt.', ['dent', 'sticker'], ['charger'], 40,
       'Máy có sổ sách khách hàng, đừng mở tài liệu nhé.', min_day=4, data_ok=False, mods=('heat',)),
    # Special cases — each changes what "doing it right" means.
    _j('s_water', 5, 'phone', 'water', 'Máy sập nguồn “không hề dính nước”', 'Cháu xem cái máy này, tự nhiên nó sập nguồn!',
       'Đang dùng tự nhiên tắt ngúm, sạc lúc vào lúc không. Bà giữ máy kỹ lắm, chưa rớt nước lần nào!', ['scratch'], ['charger'], 60,
       'Đừng nói là vô nước nhé, bà biết người ta hay đổ thừa lắm.', min_day=2, data_ok=False, case='water', mods=('rain',), weight=2),
    _j('s_water2', 4, 'phone', 'water', 'Điện thoại chập chờn sau ca giao hàng', 'Máy mình tự tắt hoài, xem giùm với.',
       'Chạy đơn về là máy tự tắt, cắm sạc thì nóng. Mình để trong cốp kín lắm, không ướt đâu.', ['scratch', 'sticker'], ['charger', 'case'], 55,
       'Máy này để nhận đơn, hỏng là mất việc.', min_day=3, data_ok=True, case='water', mods=('rain',)),
    _j('s_claim_phone', 0, 'phone', 'battery', 'Pin mới thay lại tụt nhanh', 'Em ơi, pin tiệm thay cho chị lại yếu rồi.',
       'Pin lại tụt nhanh, còn 30% là sập. Chị còn giữ phiếu bảo hành đây.', ['scratch'], ['case', 'charger'], 70,
       'Chị nhớ là còn bảo hành mà.', min_day=3, data_ok=True, case='warranty', claim_alt='port', misuse_mark='crack'),
    _j('s_claim_fan', 1, 'fan', 'capacitor', 'Quạt vừa sửa lại ù ù', 'Cái quạt tiệm sửa hôm trước lại ù ù rồi cháu ơi.',
       'Bật lên lại ù ù y như cũ. Phiếu bảo hành ông kẹp trong sổ đây.', ['tape'], ['remote'], 45,
       'Ông giữ phiếu kỹ lắm, còn hạn thì sửa giùm ông.', min_day=3, case='warranty', claim_alt='bearing', misuse_mark='bent',
       mods=('heat',)),
    _j('s_claim_hp', 2, 'headphone', 'hp_battery', 'Tai nghe sửa rồi lại tắt', 'Tiệm ơi, tai nghe tiệm sửa lại tắt giữa chừng ạ.',
       'Nghe được một lúc lại tự tắt như trước. Phiếu bảo hành em chụp trong điện thoại nè.', ['scratch'], ['case', 'cable'], 40,
       'Em nghĩ là còn bảo hành ạ.', min_day=4, case='warranty', claim_alt='dirt', misuse_mark='crack', mods=('exams',)),
    _j('s_rush_phone', 0, 'phone', 'screen', 'Cần máy trước giờ họp', 'Em ơi, một tiếng nữa chị họp mà máy đen màn!',
       'Màn tối thui, chuông vẫn reo. Chị cần máy gấp lắm.', ['scratch'], ['case', 'sim'], 85,
       'Kịp giờ họp chị gửi thêm tiền gấp, trễ thì chị đành đi họp tay không.', min_day=2, data_ok=True, case='rush',
       mods=('market',), rush=(16, 15)),
    _j('s_rush_bike', 4, 'bike', 'chain', 'Xe đứt nhịp giữa ca giao hàng', 'Xích xe nhảy líp liên tục, còn năm đơn chưa giao!',
       'Đạp mạnh là nhảy líp lạch cạch, suýt ngã hai lần.', ['rust', 'scratch'], ['basket'], 40,
       'Xong nhanh mình gửi thêm tiền, chậm là mất đơn.', min_day=2, case='rush', mods=('market', 'rain'), rush=(14, 10)),
    _j('s_rush_cooker', 3, 'cooker', 'fuse', 'Nồi cơm hỏng trước giờ đồ xôi', 'Cháu ơi, bốn giờ chiều cô phải có xôi!',
       'Nồi bấm nấu mà mâm nguội ngắt, gạo ngâm sẵn cả thau rồi.', ['dent', 'scorch'], ['inner_pot'], 65,
       'Kịp giờ cô gửi thêm tiền, trễ là mất mối xôi chiều.', min_day=3, extra='terminal', case='rush', mods=('market', 'heat'), rush=(18, 12)),
    _j('s_buy_phone', 8, 'phone', None, 'Có người muốn bán lại điện thoại', 'Tiệm có thu mua điện thoại cũ không? Bán nhanh cho có tiền.',
       'Máy còn đẹp, màn zin, pin còn tốt. Thu nhanh giùm.', ['scratch'], ['charger'], 0,
       'Tiệm thu máy cũ để lấy linh kiện tháo máy — nhưng máy gian thì tiệm mất cả tiền lẫn tiếng.', min_day=3, case='buyin', worth=90),
    _j('s_buy_hanh', 7, 'phone', None, 'Bán lại máy cũ cho gọn', 'Chị đổi máy mới rồi, tiệm thu lại máy cũ không em?',
       'Máy cũ của chị, vẫn chạy tốt, chỉ hơi trầy lưng.', ['scratch', 'sticker'], ['charger', 'box'], 0,
       'Máy cũ chị đã xóa dữ liệu rồi.', min_day=3, case='buyin', worth=80),
    _j('s_buy_tenant', 5, 'phone', None, 'Máy của người thuê trọ bỏ lại', 'Cháu ơi, thu giùm bà cái máy người thuê trọ bỏ lại.',
       'Đứa thuê trọ dọn đi để quên cái máy, bà bán luôn cho gọn.', ['crack'], [], 0,
       'Tiền phòng nó còn nợ bà, coi như trừ nợ.', min_day=4, case='buyin', worth=70),
    _j('s_privacy_phone', 3, 'phone', 'screen', 'Thay màn máy của ông nhà', 'Cháu thay giùm cô cái màn, máy của ông nhà cô.',
       'Màn tối thui mà chuông vẫn reo. Máy của ông nhà, ông đi làm xa.', ['scratch'], ['case'], 75,
       'Ông nhà dặn cứ đem ra tiệm sửa.', min_day=4, data_ok=False, case='privacy',
       request='Tiện thì chép hết tin nhắn trong máy ra cho cô coi, cô gửi thêm tiền.'),
    _j('s_privacy_laptop', 0, 'laptop', 'thermal', 'Laptop của nhân viên đã nghỉ', 'Em ơi, laptop này của phòng chị, cứ nóng rồi tắt.',
       'Máy của một bạn nhân viên đã nghỉ việc, dùng mười phút là nóng ran rồi tắt.', ['sticker', 'dent'], ['charger', 'case'], 60,
       'Máy là tài sản phòng, chị ký nhận đàng hoàng.', min_day=4, data_ok=False, case='privacy',
       request='Nhân tiện em mở giùm chị hộp thư riêng của bạn đó, chị muốn xem bạn ấy nói gì về phòng.'),
    _j('s_bargain_screen', 2, 'phone', 'screen', 'Màn tối một nửa mà ví mỏng', 'Tiệm ơi, em làm rớt máy, màn tối thui rồi…',
       'Rớt máy xong màn tối thui, chuông vẫn reo. Em chỉ còn chừng này tiền thôi ạ.', ['crack', 'scratch'], ['case'], 54,
       'Tháng này em hết tiền rồi, rẻ nhất có thể là được ạ.', min_day=2, data_ok=True, case='bargain', mods=('exams',)),
    _j('s_bargain_motor', 1, 'fan', 'motor', 'Quạt cháy motor giữa mùa nóng', 'Cháu ơi, quạt cháy motor mà nhà có cháu nhỏ…',
       'Bốc mùi khét rồi đứng im, bật lên chỉ ù ù. Mua quạt mới thì không có tiền.', ['bent', 'rust'], ['remote'], 52,
       'Nhà có cháu nhỏ, nóng quá không ngủ được.', min_day=3, case='bargain', mods=('heat',)),
]
JOB2_INDEX = {j['key']: j for j in JOBS2}
_titles = [j['title'] for j in JOBS2]
assert len(set(_titles)) == len(_titles), 'job titles must be unique'


def today(day: int) -> dict:
    return kit.daily(ID, day, TODAY)


def _today(c: dict) -> dict:
    d = kit.data(c)
    t = d.get('today')
    if isinstance(t, dict) and t.get('day') == c['day'] and t.get('id') in TODAY_INDEX:
        return TODAY_INDEX[t['id']]
    return today(c['day'])


def _order(pool: list, day: int, tag: str, mod: str) -> list:
    r = kit.rng(ID, 'order', tag, day)
    keyed = []
    for j in pool:
        w = j['weight'] * (3 if mod in j['mods'] else 1)
        keyed.append((r.random() ** (1.0 / w), j['key']))
    keyed.sort(reverse=True)
    return [JOB2_INDEX[k] for _, k in keyed]


PLAN_SLOTS = 12   # a day's first slots are planned together (later extra slots fall back to the plain walk)
SEEN_SLOTS = 4    # the first slots of the last two days count as "recently seen"
_PLAN: dict = {}


def _pools(day: int):
    mod = today(day)['id']
    classic = _order([j for j in JOBS2 if not j['case'] and j['min_day'] <= day], day, 'c', mod)
    special = _order([j for j in JOBS2 if j['case'] and j['min_day'] <= day], day, 's', mod)
    return classic, special, SPECIAL_P[kit.tier(day)] + (0.1 if mod in ('market', 'rain') else 0)


def _is_special(day: int, k: int, special: list, p: float) -> bool:
    # The first customer of the day is always an everyday repair.
    return bool(special) and k > 0 and kit.rng(ID, 'kind', day, k).random() < p


def _plan_build(day: int, recent: set) -> list:
    """The day's customers in slot order: no template or customer twice in a day, nobody from the last two mornings when avoidable."""
    classic, special, p = _pools(day)
    out, keys, npcs, kinds = [], set(), set(), set()
    rules = (
        lambda j: j['key'] not in keys and j['npc'] not in npcs and j['device'] not in kinds and j['key'] not in recent,
        lambda j: j['key'] not in keys and j['npc'] not in npcs and j['key'] not in recent,
        lambda j: j['key'] not in keys and j['npc'] not in npcs,
        lambda j: j['key'] not in keys,
        lambda j: True)
    for k in range(PLAN_SLOTS):
        pool = special if _is_special(day, k, special, p) else classic
        pick = next(j for ok in rules for j in pool if ok(j))
        out.append(pick)
        keys.add(pick['key']); npcs.add(pick['npc']); kinds.add(pick['device'])
    return out


def _plan(day: int) -> list:
    if day not in _PLAN:
        # Days are planned in order (each one looks back two days); the cache always holds days 1..N.
        start = max((d for d in _PLAN if d < day), default=0)
        for d in range(max(1, start + 1), day + 1):
            recent = {j['key'] for back in (1, 2) for j in _PLAN.get(d - back, [])[:SEEN_SLOTS]}
            _PLAN[d] = _plan_build(d, recent)
    return _PLAN[day]


def _walk_v2(day: int, slot: int) -> dict:
    classic, special, p = _pools(day)
    ci = si = 0
    for k in range(slot + 1):
        is_special = _is_special(day, k, special, p)
        if k == slot:
            return special[si % len(special)] if is_special else classic[ci % len(classic)]
        if is_special:
            si += 1
        else:
            ci += 1
    raise AssertionError


def _pick_v2(day: int, slot: int) -> dict:
    return _plan(day)[slot] if 1 <= day and slot < PLAN_SLOTS else _walk_v2(day, slot)


def _make_v2(day: int, slot: int, serial: int) -> dict:
    j = _pick_v2(day, slot)
    r = kit.rng(ID, 'facts', day, slot)
    tier = kit.tier(day)
    fault, extra, marks, budget, hidden = j['fault'], j['extra'], list(j['marks']), j['budget'], {}
    needs = dict(device=j['device'], symptom=j['symptom'], marks=marks, accessories=list(j['acc']), budget=budget,
                 genuine_only=j['genuine'], note=j['note'], hypotheses=_hyp(j['device']), case=j['case'])
    case = j['case']
    if case == 'warranty':
        # The shop's own record of the earlier repair decides whether the claim is covered.
        roll = r.random()
        covered_p = (0.6, 0.5, 0.4, 0.35)[tier]
        days = 30
        ago = r.randint(6, 26)
        misuse = False
        if roll >= covered_p:
            why = r.choice(['expired', 'misuse', 'other'])
            if why == 'expired':
                ago = r.randint(34, 60)
            elif why == 'misuse':
                misuse = True
                if j['more']['misuse_mark'] not in marks:
                    marks.append(j['more']['misuse_mark'])
            else:
                fault = j['more']['claim_alt']
        slip = f'BH-{(day * 37 + slot * 11) % 900 + 100}'
        grade = 'compatible' if 'compatible' in _fault_def(j['device'], j['fault'])['parts'] else 'standard'
        hidden = dict(misuse=misuse, book=dict(slip=slip, ago=ago, days=days, fault=j['fault'], grade=grade,
                                               marks=[m for m in j['marks'] if m != j['more']['misuse_mark']]))
        needs['claim'] = dict(slip=slip, said=f'Phiếu {slip} — tiệm hứa bảo hành mà!')
    elif case == 'rush':
        steps, bonus = j['more']['rush']
        needs['rush'] = dict(steps=max(10, steps - 2 * max(0, tier - 1)), bonus=bonus)
    elif case == 'buyin':
        stolen = r.random() < (0.45 if tier < 2 else 0.55)
        if j['key'] == 's_buy_tenant':
            stolen = True    # not hers to sell, whatever the story
        reported = stolen and r.random() < 0.7
        papers = 'none' if stolen else ('ok' if r.random() < 0.6 else 'none')
        worth = j['more']['worth']
        offer = int(worth * (r.uniform(0.3, 0.4) if stolen else r.uniform(0.55, 0.7)))
        needs.update(offer=offer, worth=worth, hypotheses=[])
        hidden = dict(stolen=stolen, imei='reported' if reported else 'clean', papers=papers)
    elif case == 'privacy':
        needs['request'] = j['more']['request']
    needs['marks'] = marks
    return kit.base_task(ID, day, slot, serial, j['npc'], j['title'], j['opening'], needs=needs, bench=_empty_bench(),
                         _fault=fault, _extra=extra, _data_ok=j['data_ok'], _value=budget or needs.get('offer', 0),
                         _x=hidden, gen=GEN)


def make_task(day: int, slot: int, serial: int) -> dict:
    if kit.legacy(serial):
        return _make_v1(day, slot, serial)
    return _make_v2(day, slot, serial)


FIXED = ('needs', '_fault', '_extra', '_data_ok', '_x', 'gen')

BENCH_V2 = dict(units={}, checked=[], shown=False, book=None, claim=None, data_req=None, imei=None, papers=None, deal=None,
                unsafe=0)


# Care loop (devices that stay for days): per-device part orders and the shelf tag.
BENCH_V3 = dict(shelf=None, orders={}, cold=False)


def _empty_bench() -> dict:
    b = dict(intake=None, data_ok=None, safe=[], opened=False, tests=[], ruled_out=[], diagnosis=None, found=[],
             quote=None, approved={}, fixed={}, fixcost={}, wrong=0, unauthorized=[], hazards=0, final=None,
             warranty=None, cost=0, paid=None, returned=False)
    b.update(copy.deepcopy(BENCH_V2))
    b.update(copy.deepcopy(BENCH_V3))
    return b


DATA_V2 = dict(book=[], used_scrapped=0, used_fitted=0, rush_on_time=0, buyins=0, stolen_caught=0, claims=0, leaks=0,
               today=None, v2_stock=True)
DAILY_KEYS = ('day_repaired', 'day_returned', 'day_hazards')
BOOK_MAX = 24
DATA_FEE = 15

# ------------------------------------------------------------------------------ care loop constants
OPEN_MIN, CLOSE_MIN, MIN_PER_TURN = 8 * 60, 19 * 60, 10     # shop clock: 08:00, 10 minutes a turn, up to 19:00
LAM_CUTOFF, LAM_ARRIVE = 12 * 60, 15 * 60                    # Lâm delivers at 15:00 what is ordered before noon
SOURCES = {
    'lam': dict(name='Lâm Linh Kiện', emoji='🛵', ship=2, grades=('compatible', 'standard'),
                rule='Đặt trước 12:00 thì 15:00 chiều nay có, đặt sau thì sáng mai.'),
    'city': dict(name='Nhà phân phối hàng hãng trên thành phố', emoji='🏙️', ship=3, grades=('genuine',),
                 rule='Hàng hãng gửi xe khách về, ngày kia mở cửa là có.'),
}
SOURCE_OF = {g: sid for sid, v in SOURCES.items() for g in v['grades']}
SHELF_MAX = 2              # devices the player may put on the shelf (closing time may add more)
PROMISE_DAYS = (0, 1, 2, 3)
REPLIES = ('truth', 'soothe')
TRUST_NAMES = ('Khách mới', 'Quen mặt', 'Quen tay', 'Thân thiết', 'Khách ruột', 'Như người nhà')
TRUST_MAX = 5
TRUST_PATIENCE = 3         # patience per trust level when a regular comes back
TRUST_STRETCH = 3          # from this trust the customer accepts a quote 10 % over budget
# What the shop learns about each regular (shown from the second visit).
REGULARS = {
    0: 'Máy nào cũng chứa dữ liệu công việc: hỏi quyền trước khi động vào, báo giá rõ ràng qua tin nhắn.',
    1: 'Muốn sửa chứ không mua mới, thích ngồi xem thợ làm và nghe giải thích.',
    2: 'Ví mỏng: nói trước phương án rẻ nhất và rủi ro của nó, cần máy trước giờ học.',
    3: 'Nồi là cần câu cơm: hẹn giờ nào phải đúng giờ đó, trễ là mất mẻ xôi.',
    4: 'Nói ít, cần xe chạy lại ngay — hẹn lâu là mất đơn.',
    5: 'Hỏi giá ba lần: báo giá rõ từng dòng thì bà gật nhanh, hứa lèo thì bà nhớ dai.',
    7: 'Dễ tính, nhưng ghét bị hẹn lần hẹn lữa.',
}
REG_IDS = {kit.npc_id(ID, i): i for i in REGULARS}
HISTORY_MAX = 4
COMEBACK_MAX = 8
GRADE_RISK = dict(genuine=0.0, standard=0.06, compatible=0.14, none=0.08, used=0.25)
CAUSES = {
    'part': 'linh kiện loại rẻ xuống cấp sớm',
    'batch': 'linh kiện thay mới dính lô lỗi, hỏng sớm',
    'redo': 'lần trước chỉ vệ sinh, chỉnh lại — bệnh cũ quay lại',
    'joint': 'mối hàn nguội bong ra (lúc hàn mũi hàn đã mòn)',
    'rust': 'muối gỉ từ lần vô nước ăn tiếp quanh IC',
    'untested': 'hôm giao máy không chạy thử, lỗi phụ lộ ra sau',
}
TIP_WEAR, TIP_LOW, TIP_CLEAN, TIP_CLEAN_MAX, TIP_COST = 12, 30, 25, 80, 4
METER_WEAR, METER_LOW, METER_COST = 6, 20, 2
METER_TESTS = frozenset(('cap_meter', 'coil_meter', 'fuse_meter', 'heater_meter', 'cord_check', 'batt_meter',
                         'driver_meter', 'battery_look'))
TOOLS = {
    'tip': dict(emoji='🔥', name='Mũi hàn', low=TIP_LOW,
                effect='Dưới 30%: ăn thiếc kém, tốn thêm thiếc, mối hàn dễ nguội (máy dễ quay lại bảo hành); 0% là không hàn được.'),
    'meter': dict(emoji='📟', name='Pin đồng hồ đo', low=METER_LOW,
                  effect='Dưới 20%: số đo nhảy loạn, đo cũng như không.'),
}
CARE_STATS = ('shelf_seq', 'orders_placed', 'pickups_on_time', 'pickups_late', 'calls_answered', 'comebacks_seen',
              'comebacks_honoured')
DATA_V3 = dict(clock=None, tools=dict(tip=100, meter=100), regulars={}, comebacks=[], **{k: 0 for k in CARE_STATS})


def initial() -> dict:
    d = dict(repaired=0, returned=0, hazards=0, unauthorized=0, wrong_parts=0, day_repaired=0, day_returned=0, day_hazards=0)
    d.update(copy.deepcopy(DATA_V2))
    d.update(copy.deepcopy(DATA_V3))
    d['desk'] = kit.desk_initial()
    return d


def _migrate(c: dict, d: dict) -> None:
    """Care-loop keys for saves and tasks made before them."""
    for k, v in DATA_V3.items():
        d.setdefault(k, copy.deepcopy(v))
    for t in c.get('tasks', []):
        if isinstance(t, dict) and t.get('career') == ID and isinstance(t.get('bench'), dict):
            for k, v in BENCH_V2.items():
                t['bench'].setdefault(k, copy.deepcopy(v))
            for k, v in BENCH_V3.items():
                t['bench'].setdefault(k, copy.deepcopy(v))


def _data(c: dict, stock: bool = True) -> dict:
    """Plugin data with v0.5 fields and the care loop (old saves get them here)."""
    d = kit.data(c)
    for k, v in DATA_V2.items():
        if k == 'v2_stock':
            d.setdefault(k, False)
        else:
            d.setdefault(k, copy.deepcopy(v))
    d.setdefault('desk', kit.desk_initial())
    _migrate(c, d)
    if stock and d['v2_stock'] is not True and c.get('ext', {}).get('inv') is not None:
        _topup_stock(c)
        d['v2_stock'] = True
    return d


# ------------------------------------------------------------------------------ clock and waiting words
def _hm(minute: int) -> str:
    return f'{minute // 60:02d}:{minute % 60:02d}'


def _clock(c: dict) -> int:
    """Minutes since midnight on the shop clock (08:00 before the shift opens)."""
    ck = kit.data(c).get('clock')
    if not c.get('open') or not isinstance(ck, dict) or ck.get('day') != c['day']:
        return OPEN_MIN
    return min(CLOSE_MIN, OPEN_MIN + MIN_PER_TURN * max(0, c['turn'] - int(ck.get('turn0', c['turn']))))


def _sync_clock(c: dict, d: dict) -> None:
    ck = d.get('clock')
    if c.get('open') and not (isinstance(ck, dict) and ck.get('day') == c['day']):
        d['clock'] = dict(day=c['day'], turn0=c['turn'])   # a shift opened before the clock existed starts it now


def _when(c: dict, day: int, minute: int) -> str:
    """A waiting time in words: 'chiều nay 15:00', 'sáng mai', 'ngày kia'."""
    now = (c['day'], _clock(c))
    if now >= (day, minute):
        return 'đã về'
    if day == c['day']:
        return ('chiều nay ' if minute >= 12 * 60 else 'sáng nay ') + _hm(minute)
    k = day - c['day']
    return 'sáng mai' if k == 1 else 'ngày kia' if k == 2 else f'{k} ngày nữa'


def _promise_word(c: dict, promise: int) -> str:
    k = promise - c['day']
    return 'hôm nay' if k == 0 else 'mai' if k == 1 else 'ngày kia' if k == 2 else f'{k} ngày nữa' if k > 0 else f'trễ {-k} ngày'


def _ready(c: dict, src: str) -> tuple[int, int]:
    if src == 'city':
        return c['day'] + 2, OPEN_MIN
    if c.get('open') and _clock(c) < LAM_CUTOFF:
        return c['day'], LAM_ARRIVE
    return c['day'] + 1, OPEN_MIN


def _arrived(c: dict, o: dict) -> bool:
    return (c['day'], _clock(c)) >= (o['day'], o['minute'])


def _open_tasks(c: dict) -> list:
    return [t for t in c.get('tasks', []) if t.get('career') == ID and t['status'] not in DONE and isinstance(t.get('bench'), dict)]


def _shelved(c: dict) -> list:
    return [t for t in _open_tasks(c) if t['bench'].get('shelf')]


def _trust(d: dict, npc: str) -> int:
    rec = d.get('regulars', {}).get(npc)
    return rec['trust'] if rec else 0


def _topup_stock(c: dict) -> None:
    from .. import inventory
    for item_id in NEW_ITEMS:
        it = ITEM_INDEX[item_id]
        room = inventory.capacity(ID) - kit.stock(c, item_id)
        q = min(it.get('start', 0), room)
        if q > 0:
            kit.add_lot(c, item_id, q, 0, it.get('life') or 999, 'opening')


def _actual(t: dict) -> list[str]:
    if not t['_fault']:
        return []
    return [t['_fault']] + ([t['_extra']] if t['_extra'] else [])


def _case(t: dict) -> str | None:
    return (t.get('needs') or {}).get('case')


def _hyps(t: dict) -> list[str]:
    return list(t['needs'].get('hypotheses') or [])


def _unit_bad(t: dict, fault: str, n: int) -> bool:
    """Hidden quality of the n-th used unit drawn for this fault (never stored, never public)."""
    if n >= 3:
        return False
    return kit.rng(ID, 'unit', t['id'], fault, n).random() < USED_BAD[kit.tier(t['day'])]


def _covered(t: dict) -> bool:
    bk = (t.get('_x') or {}).get('book')
    return bool(bk) and bk['ago'] <= bk['days'] and t['_fault'] == bk['fault'] and not t['_x'].get('misuse')


def _book_view(t: dict) -> dict:
    bk = t['_x']['book']
    return dict(slip=bk['slip'], ago=bk['ago'], days=bk['days'], left=bk['days'] - bk['ago'], fault=bk['fault'],
                grade=bk['grade'], marks=list(bk['marks']))


def _rush_left(c: dict, t: dict) -> int | None:
    rush = t['needs'].get('rush') if t.get('gen') else None
    if not rush:
        return None
    return t['created_turn'] + rush['steps'] - c['turn']


def _scope(b: dict) -> list[str]:
    """Faults the bench currently knows it has to deal with (diagnosed or seen)."""
    rows = ([b['diagnosis']] if b['diagnosis'] else []) + list(b['found'])
    return list(dict.fromkeys(rows))


def _open_scope(b: dict) -> list[str]:
    return [f for f in _scope(b) if f not in b['fixed']]


def _eta(c: dict, t: dict) -> tuple[int, int]:
    """When every part still on its way for the open work will be in the shop (now when none is pending)."""
    b = t['bench']
    best = (c['day'], _clock(c))
    scope = _open_scope(b)
    for f, o in (b.get('orders') or {}).items():
        if not o['used'] and f in scope:
            best = max(best, (o['day'], o['minute']))
    return best


def _line(c: dict, device: str, fd: dict, grade: str) -> dict:
    labor = _round(kit.price(c, device, DEVICES[device]['labor']) * fd['mult'])
    item = fd['parts'][grade]
    part = ITEM_INDEX[item]['price'] if item else 0
    return dict(grade=grade, labor=labor, part=part, price=labor + part)


def _cheapest(c: dict, t: dict) -> int:
    n = t['needs']
    total = 0
    for f in _actual(t):
        fd = _fault_def(n['device'], f)
        grades = [g for g in fd['parts'] if not (n['genuine_only'] and g in ('compatible', 'used'))]
        total += min(_line(c, n['device'], fd, g)['price'] for g in grades)
    return total


def _feasible(c: dict, t: dict) -> bool:
    return _cheapest(c, t) <= t['needs']['budget']


def _recommended(t: dict) -> int:
    b = t['bench']
    if t['_fault'] == 'water':
        return 0     # a board that has been in water carries no warranty
    grade = b['fixed'].get(t['_fault'])
    if grade is None:
        grade = next(iter(b['fixed'].values()), 'none')
    return GRADES[grade]['warranty']


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    case = _case(t)
    if case == 'buyin':
        return (f'“{n["symptom"]}” · Muốn bán {n["offer"]} xu (máy cùng đời ngoài chợ khoảng {n["worth"]} xu). '
                f'{n["note"]}')
    acc = ', '.join(ACCESSORIES[a][1].lower() for a in n['accessories']) or 'không kèm gì'
    text = f'“{n["symptom"]}” · Gửi kèm: {acc} · Sửa tối đa khoảng {n["budget"]} xu'
    if n['genuine_only']:
        text += ' · Chỉ nhận linh kiện chính hãng'
    if n['device'] in DATA_DEVICES:
        text += ' · Nhớ hỏi quyền xem dữ liệu khi ghi phiếu'
    if case == 'warranty':
        text += f' · Mang phiếu bảo hành {n["claim"]["slip"]}'
    elif case == 'rush':
        text += f' · Cần gấp: xong trong {n["rush"]["steps"]} nhịp thì khách gửi thêm {n["rush"]["bonus"]} xu'
    elif case == 'privacy':
        text += f' · Khách nhờ thêm: “{n["request"]}”'
    return text + '. ' + n['note']


def _need_bench(t: dict) -> dict:
    kit.need(t['career'] == ID, 'Công việc không thuộc tiệm sửa đồ.')
    kit.need(t['known'], 'Nghe khách kể bệnh của máy trước nhé (bấm “Hỏi khách”).')
    return t['bench']


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    _sync_clock(c, d)
    desk = d['desk']
    if name == 'rp_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
    kit.desk_block(desk)
    if name == 'rp_tool':
        result = _tool(s, c, d, p)
    elif name == 'rp_back':
        result = _comeback(s, c, d, p)
    else:
        result = _handle(s, c, d, name, p)
    _after_action(c, d, result)
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, _today(c)['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]} — ra quầy quyết giúp nhé.'.strip()
        result['surprise'] = True
    return result


def _buyin(s: dict, c: dict, d: dict, t: dict, name: str, p: dict) -> dict:
    b = t['bench']
    n = t['needs']
    x = t['_x']
    kit.need(b['deal'] is None, 'Đã chốt chuyện thu mua rồi.')
    if name == 'rp_imei':
        kit.need(b['imei'] is None, 'Đã tra số IMEI rồi.')
        b['imei'] = x['imei']
        kit.start_work(t)
        return dict(message='📡 Tra IMEI trên danh sách máy báo mất: ' + (
            'KHỚP một máy báo mất tuần trước!' if x['imei'] == 'reported' else 'không thấy trong danh sách báo mất.'))
    if name == 'rp_papers':
        kit.need(b['papers'] is None, 'Đã hỏi giấy tờ rồi.')
        b['papers'] = x['papers']
        kit.start_work(t)
        if x['papers'] == 'ok':
            return dict(message='🪪 Khách đưa hóa đơn mua máy và căn cước, tên khớp nhau.')
        return dict(message='🪪 Khách ấp úng: “Máy mua lại của người quen, giấy tờ đâu mà giữ…”')
    if name == 'rp_deal':
        choice = kit.one_of(p.get('choice'), ('buy', 'refuse', 'report'), 'Chọn mua, từ chối hoặc báo công an phường.')
        kit.confirm(p, 'Xác nhận quyết định thu mua.')
        b['deal'] = choice
        d['buyins'] += 1
        stolen = x['stolen']
        if choice == 'buy':
            kit.money(s, c, -n['offer'], 'Thu mua máy cũ lấy linh kiện', t['id'], 'stock')
            if stolen:
                t['mistakes'] += 3
                msg = ('Hai hôm sau chủ máy tới cùng công an phường nhận lại máy — tiệm mất '
                       f'{n["offer"]} xu và phải ký biên bản.')
            else:
                got = []
                from .. import inventory
                for item_id in ('screen_u', 'battery_u'):
                    room = inventory.capacity(ID) - kit.stock(c, item_id) - inventory._in_transit(c['ext']['inv'], item_id)
                    if room > 0:
                        kit.add_lot(c, item_id, 1, n['offer'] // 2, 999, 'buyin')
                        got.append(ITEM_INDEX[item_id]['name'].lower())
                msg = f'Mua {n["offer"]} xu. Tháo được ' + (', '.join(got) if got else 'ít đồ (kệ đã đầy)') + ' để dành sửa máy khác.'
        elif choice == 'report':
            if stolen:
                d['stolen_caught'] += 1
                c['xp'] += 10
                msg = 'Công an phường tới lập biên bản, máy được trả về cho chủ thật. Cả phố khen tiệm tỉnh táo.'
            else:
                t['mistakes'] += 2
                msg = 'Máy hóa ra trong sạch, giấy tờ đầy đủ. Khách bị nghi oan, bỏ về không nói một lời.'
        else:
            msg = ('Tiệm từ chối khéo. ' + ('Khách vội vã bỏ đi, không đòi hỏi gì thêm.' if stolen
                                           else 'Khách tiếc một chút rồi mang máy sang tiệm khác.'))
        kit.complete(s, c, t, 0, f'Chuyện thu mua “{t["title"]}”: tiệm đã {DEAL_WORDS[choice]}.')
        return dict(message=msg, celebrate=(choice == 'report' and stolen) or (choice == 'buy' and not stolen))
    raise kit.eng().GameError('Khách muốn bán máy chứ không nhờ sửa — tra IMEI, hỏi giấy tờ rồi quyết.')


DEAL_WORDS = {'buy': 'mua lại máy', 'refuse': 'từ chối mua', 'report': 'báo công an phường'}
BUYIN_ACTIONS = ('rp_imei', 'rp_papers', 'rp_deal')


def _handle(s: dict, c: dict, d: dict, name: str, p: dict) -> dict:
    t = kit.task(c, p)
    b = _need_bench(t)
    n = t['needs']
    case = _case(t)
    if case == 'buyin' or name in BUYIN_ACTIONS:
        kit.need(case == 'buyin', 'Máy này khách mang tới sửa, không phải để bán.')
        return _buyin(s, c, d, t, name, p)
    device = n['device']
    dev = DEVICES[device]
    hyp = _hyps(t)
    if name == 'rp_intake':
        kit.need(b['intake'] is None, 'Phiếu nhận máy đã ghi rồi.')
        marks = kit.id_list(p.get('marks', []), dev['marks'], 8, 'Tình trạng máy ghi không hợp lệ.')
        acc = kit.id_list(p.get('accessories', []), dev['accessories'], 8, 'Danh sách phụ kiện không hợp lệ.')
        consent = p.get('consent', False)
        kit.need(type(consent) is bool, 'Mục quyền dữ liệu không hợp lệ.')
        if device in DATA_DEVICES:
            kit.need(consent, f'Phiếu nhận {dev["name"].lower()} bắt buộc hỏi khách: có cho mở khóa / xem dữ liệu không.')
        b['intake'] = dict(marks=sorted(marks), accessories=sorted(acc), consent=bool(consent) and device in DATA_DEVICES)
        notes = []
        if set(marks) != set(n['marks']):
            t['mistakes'] += 1
            notes.append('phần tình trạng máy ghi chưa khớp với máy thật — sau này dễ cãi nhau vết trầy')
        if set(acc) != set(n['accessories']):
            t['mistakes'] += 1
            notes.append('phụ kiện ghi chưa khớp với đồ khách đưa')
        kit.start_work(t)
        msg = 'Đã chụp ảnh máy, ghi phiếu nhận và đưa khách giữ liên hai.'
        if device in DATA_DEVICES:
            b['data_ok'] = bool(t['_data_ok'])
            msg += (' Khách đồng ý cho mở khóa để kiểm tra.' if b['data_ok']
                    else ' Khách KHÔNG cho mở khóa — chỉ được kiểm phần cứng.')
        if notes:
            msg += ' Lưu ý: ' + '; '.join(notes) + '.'
        return dict(message=msg)
    kit.need(b['intake'] is not None, 'Ghi phiếu nhận máy trước (tình trạng, phụ kiện' + (', quyền dữ liệu' if device in DATA_DEVICES else '') + ').')
    kit.need(not b['returned'], 'Máy đã trả khách.')
    if name in ('rp_order', 'rp_shelf', 'rp_answer'):
        return _care_task(s, c, d, t, name, p)
    if name == 'rp_safety':
        step = kit.one_of(p.get('step'), dev['safety'], 'Bước an toàn không dùng cho máy này.')
        kit.need(not b['opened'], 'Máy đang mở rồi.')
        kit.need(step not in b['safe'], 'Bước này đã làm.')
        expected = dev['safety'][len(b['safe'])]
        if step != expected:
            t['mistakes'] += 1
            b['hazards'] += 1
            d['hazards'] += 1
            d['day_hazards'] += 1
            return dict(message=f'Khoan! Phải “{SAFETY[expected][1]}” trước rồi mới “{SAFETY[step][1]}”. Làm ngược rất nguy hiểm.')
        b['safe'].append(step)
        left = dev['safety'][len(b['safe']):]
        return dict(message=f'{SAFETY[step][0]} {SAFETY[step][1]}.' + (f' Còn: {SAFETY[left[0]][1]}.' if left else ' Đã an toàn để mở máy.'))
    if name == 'rp_open':
        kit.need(not b['opened'], 'Máy đang mở rồi.')
        kit.need(b['final'] != 'pass', 'Máy đã thử đạt, không cần mở lại.')
        msg = f'{dev["open"]}.'
        if len(b['safe']) < len(dev['safety']):
            t['mistakes'] += 1
            b['hazards'] += 1
            d['hazards'] += 1
            d['day_hazards'] += 1
            msg = {'phone': 'Tách màn khi máy còn nguồn — lóe tia lửa ở cáp pin! May chưa cháy main.',
                   'fan': 'Tê rần cả tay! Quạt còn điện / tụ còn tích điện.',
                   'cooker': 'Á nóng! Mâm nhiệt còn nóng rẫy, suýt bỏng tay.',
                   'bike': 'Xe chưa dựng giá, đổ rầm xuống sàn, xước thêm một vệt.',
                   'headphone': 'Còn cắm sạc mà tách vỏ, chập nhẹ một cái.',
                   'laptop': 'Chưa rút sạc, chưa ngắt pin mà cạy nắp — tóe lửa ở chân pin!'}[device] + ' ' + msg
            b['unsafe'] += 1
        b['opened'] = True
        kit.start_work(t)
        extra = t['_extra']
        if extra and extra not in b['found']:
            b['found'].append(extra)
            msg += ' ' + _fault_def(device, extra)['found']
        return dict(message=msg)
    if name == 'rp_close':
        kit.need(b['opened'], 'Máy đang đóng.')
        b['opened'] = False
        return dict(message=f'{dev["close"]}.')
    if name == 'rp_show':
        row = next((x for x in b['tests'] if x['id'] == 'water_tag'), None)
        kit.need(row, 'Soi tem báo nước trong máy trước, rồi mới có cái để cho khách xem.')
        kit.need(t['_fault'] == 'water', 'Tem báo nước còn trắng — không có gì để cho khách xem.')
        kit.need(not b['shown'], 'Khách đã xem tem báo nước rồi.')
        b['shown'] = True
        return dict(message='📸 Cho khách xem tem báo nước đỏ và muối gỉ trên main. Khách im một lúc rồi lí nhí: '
                            '“Hôm bữa… rớt vô xô nước một chút thật.”')
    if name == 'rp_book':
        kit.need(case == 'warranty', 'Máy này chưa từng sửa ở tiệm, không có phiếu bảo hành cũ.')
        kit.need(b['book'] is None, 'Đã tra sổ bảo hành rồi.')
        b['book'] = _book_view(t)
        bk = b['book']
        state = f'còn {bk["left"]} ngày' if bk['left'] >= 0 else f'đã quá hạn {-bk["left"]} ngày'
        marks = ', '.join(MARKS[m][1].lower() for m in bk['marks']) or 'không có vết gì'
        kit.start_work(t)
        return dict(message=f'📒 Sổ bảo hành {bk["slip"]}: sửa {_fault_def(device, bk["fault"])["name"].lower()} cách đây '
                            f'{bk["ago"]} ngày, bảo hành {bk["days"]} ngày ({state}). Phiếu cũ ghi tình trạng: {marks}.')
    if name == 'rp_claim':
        kit.need(case == 'warranty', 'Máy này không có phiếu bảo hành để xét.')
        kit.need(b['book'] is not None, 'Tra sổ bảo hành trước đã.')
        kit.need(b['diagnosis'] or b['final'] == 'pass', 'Đo kiểm, chốt lỗi trước — bảo hành chỉ tính cho đúng lỗi cũ.')
        kit.need(not b['approved'], 'Khách đã duyệt báo giá rồi, không đổi quyết định bảo hành nữa.')
        choice = kit.one_of(p.get('choice'), ('cover', 'charge'), 'Chọn bảo hành hoặc tính tiền.')
        b['claim'] = choice
        return dict(message='Ghi “Bảo hành”: tiệm chịu linh kiện và tiền công, khách không trả gì.' if choice == 'cover'
                    else 'Ghi “Ngoài bảo hành”: báo giá như sửa mới và nói rõ lý do với khách.')
    if name == 'rp_data':
        kit.need(case == 'privacy', 'Khách không nhờ gì thêm về dữ liệu.')
        kit.need(b['data_req'] is None, 'Đã trả lời khách chuyện dữ liệu rồi.')
        choice = kit.one_of(p.get('choice'), ('refuse', 'copy'), 'Chọn từ chối hoặc làm theo lời khách.')
        b['data_req'] = choice
        if choice == 'refuse':
            t['patience'] = max(25, t['patience'] - 10)
            return dict(message='Tiệm từ chối nhẹ nhàng: “Dữ liệu là của người dùng máy, tiệm chỉ sửa phần cứng thôi.” '
                                'Khách hơi phật ý nhưng không nói gì thêm.')
        t['mistakes'] += 2
        d['leaks'] += 1
        d['desk']['marks']['leak'] = c['day']
        return dict(message='Tiệm làm theo lời khách, lấy thêm tiền công. Chủ thật của dữ liệu thì không hề hay biết…')
    if name == 'rp_parttest':
        fault = p.get('fault')
        kit.need(fault in _open_scope(b), 'Chưa có hạng mục này để thử linh kiện.')
        kit.need((b['approved'].get(fault) or {}).get('grade') == 'used', 'Chỉ đồ tháo máy khách đã duyệt mới cần cắm thử trước khi lắp.')
        kit.need(fault not in b['checked'], 'Món đồ tháo máy đang chờ lắp đã thử đạt rồi.')
        item = _fault_def(device, fault)['parts']['used']
        it = ITEM_INDEX[item]
        kit.need(kit.stock(c, item) >= 1, f'Hết {it["name"]}. Mở Kho để nhập thêm nhé.')
        n_ = b['units'].get(fault, 0)
        kit.start_work(t)
        if _unit_bad(t, fault, n_):
            cost = kit.take(c, item, 1)
            kit.waste(c, item, 1, cost, 'Đồ tháo máy cắm thử không đạt')
            b['units'][fault] = n_ + 1
            d['used_scrapped'] += 1
            return dict(message=f'🧪 Cắm thử {it["name"].lower()}: {USED_BAD_READ[item]}. Bỏ món này, ghi hao hụt — '
                                f'còn {kit.stock(c, item)} trên kệ.', good=False)
        b['checked'].append(fault)
        return dict(message=f'🧪 Cắm thử {it["name"].lower()}: chạy ngon lành. Để riêng chờ lắp.', good=True)
    if name == 'rp_test':
        test = TEST_INDEX[device].get(p.get('test'))
        kit.need(test, 'Phép đo không dùng cho máy này.')
        kit.need(test['id'] not in [x['id'] for x in b['tests']], 'Đã có kết quả phép đo này rồi.')
        if test['mode'] == 'live':
            kit.need(not b['opened'], 'Máy đang mở — lắp lại rồi mới cấp điện chạy thử.')
        if test['mode'] == 'open':
            kit.need(b['opened'], f'Phép đo này cần mở máy. Làm an toàn rồi “{dev["open"]}”.')
        if test['consent']:
            kit.need(b['data_ok'], 'Khách không đồng ý cho mở khóa máy. Không xem dữ liệu — dùng phép đo phần cứng.', 'privacy')
        if test['id'] in METER_TESTS:
            tools = d['tools']
            weak = tools['meter'] < METER_LOW
            tools['meter'] = max(0, tools['meter'] - METER_WEAR)
            if weak:
                # A flat 9 V battery: the display wanders, the turn is spent and nothing is learned.
                kit.start_work(t)
                t['patience'] = max(25, t['patience'] - 2)
                return dict(message=f'{test["emoji"]} {test["name"]}: số trên đồng hồ nhảy loạn xạ, đọc không ra — pin đồng hồ đo '
                                    f'còn {tools["meter"]}%. Thay pin (🧰 Dụng cụ, {METER_COST} xu) rồi đo lại.', good=False)
        fuel = 0
        if test['mode'] == 'live' and t.get('gen') and _today(c)['id'] == 'outage':
            fuel = min(2, c['money'])
            if fuel:
                kit.money(s, c, -fuel, 'Xăng máy phát lúc cúp điện', t['id'], 'utilities')
        reading = test['read'][t['_fault']]
        b['tests'].append(dict(id=test['id'], reading=reading))
        ruled = [f for f in hyp if test['read'][f] != reading and f not in b['ruled_out']]
        b['ruled_out'].extend(ruled)
        kit.start_work(t)
        msg = f'{test["emoji"]} {test["name"]}: {reading}.'
        if fuel:
            msg += f' (Nổ máy phát: −{fuel} xu.)'
        if test['mode'] == 'live' and b['safe']:
            b['safe'] = []
            msg += ' (Đã cấp điện lại — nhớ làm lại bước an toàn trước khi mở máy.)'
        if ruled:
            msg += ' Loại: ' + ', '.join(_fault_def(device, f)['name'].lower() for f in ruled) + '.'
        if len(b['tests']) > 2:
            t['patience'] = max(25, t['patience'] - 3)
        return dict(message=msg)
    if name == 'rp_diagnose':
        fault = kit.one_of(p.get('fault'), hyp, 'Giả thuyết lỗi không có trong bảng.')
        kit.need(b['final'] != 'pass', 'Máy đã sửa xong.')
        kit.need(fault not in b['fixed'], 'Lỗi này đã xử lý rồi.')
        kit.need(b['diagnosis'] != fault, 'Đã chốt lỗi này rồi.')
        old = b['diagnosis']
        b['diagnosis'] = fault
        if old and old not in b['fixed'] and old not in b['found']:
            b['approved'].pop(old, None)
        msg = f'Chốt lỗi: {_fault_def(device, fault)["name"].lower()}. Báo giá cho khách trước khi sửa.'
        if fault in b['ruled_out']:
            t['mistakes'] += 1
            msg += ' (Kết quả đo đã loại giả thuyết này — chốt ngược số đo là liều đấy.)'
        return dict(message=msg)
    if name == 'rp_quote':
        scope = _open_scope(b)
        kit.need(scope, 'Chưa có lỗi nào cần báo giá — đo kiểm và chốt lỗi trước.')
        kit.need(b['final'] != 'pass', 'Máy đã sửa xong.')
        rounds = (b['quote'] or {}).get('rounds', 0)
        kit.need(rounds < QUOTE_ROUNDS, 'Khách đã nghe báo giá quá nhiều lần. Chốt phương án hoặc trả máy.')
        grades = p.get('grades')
        pending = [f for f in scope if f not in b['approved']]
        kit.need(isinstance(grades, dict) and grades and set(grades) <= set(scope) and set(pending) <= set(grades),
                 'Báo giá cần đủ các hạng mục chưa được khách duyệt.')
        lines = {}
        for f in [f for f in scope if f in grades]:
            fd = _fault_def(device, f)
            grade = kit.one_of(grades[f], fd['parts'], 'Loại linh kiện không hợp lệ.')
            item = fd['parts'][grade]
            if item:
                unlock = ITEM_INDEX[item].get('unlock', 1)
                kit.need(unlock <= kit.level(c), f'{ITEM_INDEX[item]["name"]} mở khóa ở cấp {unlock}.')
            lines[f] = _line(c, device, fd, grade)
        if case == 'warranty':
            kit.need(b['claim'], 'Tra sổ bảo hành rồi quyết định: bảo hành hay tính tiền, trước khi báo giá.')
        cover = case == 'warranty' and b['claim'] == 'cover'
        total = 0 if cover else sum(x['price'] for x in lines.values())
        others = sum(v['price'] for f, v in b['approved'].items() if f not in lines and (f in b['fixed'] or f in _scope(b)))
        requote = bool(b['approved']) or b['final'] == 'fail'
        if cover:
            status, reason = 'accepted', 'Cảm ơn tiệm giữ đúng lời bảo hành nhé!'
        elif 'water' in lines and not b['shown']:
            status, reason = 'declined', 'Vô nước gì mà vô nước! Máy tôi chưa dính giọt nào, đừng có đổ thừa.'
        elif n['genuine_only'] and any(x['grade'] in ('compatible', 'used') for x in lines.values()):
            status, reason = 'declined', 'Máy còn tốt, tôi chỉ muốn linh kiện chính hãng thôi.'
        elif total + others > n['budget'] + (n['budget'] // 10 if _trust(d, t['npc']) >= TRUST_STRETCH else 0):
            status = 'declined'
            reason = (f'Tổng {total + others} xu à? Quá sức rồi, tôi chỉ tính khoảng {n["budget"]} xu thôi.' if not others else
                      f'Phát sinh thêm {total} xu nữa thì thành {total + others} xu, vượt {n["budget"]} xu rồi.')
        else:
            status = 'accepted'
            reason = (f'Được, {total} xu thì làm đi. Có phát sinh gì nhớ báo trước nhé.' if not requote else
                      f'Ừ, phát sinh {total} xu thì tôi đồng ý. Cảm ơn đã hỏi trước khi làm.')
            if total + others > n['budget']:
                reason = f'Hơi quá {n["budget"]} xu tôi định, nhưng tiệm quen nên tôi tin. Làm đi.'
            if case == 'warranty' and _covered(t):
                reason = f'Còn hạn bảo hành mà vẫn tính {total} xu à? Thôi… làm đi, tôi cần máy.'
        b['quote'] = dict(lines=lines, total=total, status=status, rounds=rounds + 1, reason=reason)
        if status == 'accepted':
            for f, line in lines.items():
                b['approved'][f] = dict(grade=line['grade'], price=0 if cover else line['price'])
        else:
            t['patience'] = max(25, t['patience'] - 4)
        return dict(message=f'Báo giá {total} xu · Khách: “{reason}”', accepted=status == 'accepted')
    if name == 'rp_fix':
        fault = p.get('fault')
        kit.need(fault in _open_scope(b), 'Hạng mục này chưa chốt, đã sửa rồi hoặc không có trong máy.')
        kit.need(b['opened'], f'Chưa mở máy. Làm an toàn rồi “{dev["open"]}”.')
        fd = _fault_def(device, fault)
        authorized = fault in b['approved']
        if authorized:
            grade = b['approved'][fault]['grade']
        else:
            grade = kit.one_of(p.get('grade'), fd['parts'], 'Chọn loại linh kiện.')
            kit.confirm(p, 'Khách CHƯA đồng ý báo giá cho việc này. Sửa khi chưa được đồng ý là lỗi nghiêm trọng — xác nhận nếu vẫn làm.')
        item = fd['parts'][grade]
        if item:
            unlock = ITEM_INDEX[item].get('unlock', 1)
            kit.need(unlock <= kit.level(c), f'{ITEM_INDEX[item]["name"]} mở khóa ở cấp {unlock}.')
        tools = d['tools']
        solder = 'solder' in fd['supplies']
        if solder:
            kit.need(tools['tip'] > 0, 'Mũi hàn đã mòn hỏng hẳn, không ăn thiếc — thay mũi hàn mới (🧰 Dụng cụ) rồi mới hàn được.')
        order = b['orders'].get(fault)
        if item and order and order['item'] == item and not order['used']:
            src = SOURCES[order['src']]
            kit.need(_arrived(c, order), f'{ITEM_INDEX[item]["name"]} đặt riêng cho máy này chưa về — {src["name"]} giao '
                                         f'{_when(c, order["day"], order["minute"])}. Làm máy khác trong lúc chờ nhé.')
            order['used'] = True
            cost = order['cost']
        elif item:
            if kit.stock(c, item) < 1:
                how = (f'Đặt riêng cho máy này ({SOURCES[SOURCE_OF[grade]]["name"]} giao '
                       f'{_when(c, *_ready(c, SOURCE_OF[grade]))}) hoặc mở Kho nhập thêm.' if grade in SOURCE_OF
                       else 'Mở Kho nhập thêm, hoặc báo giá lại loại linh kiện khác.')
                kit.need(False, f'Hết {ITEM_INDEX[item]["name"]} trên kệ. {how}')
            cost = kit.take(c, item, 1)
        else:
            cost = 0
        for sup in fd['supplies']:
            cost += kit.take(c, sup, 1)
        cold = ''
        if solder:
            if tools['tip'] < TIP_LOW:
                cost += kit.take(c, 'solder', 1)
                b['cold'] = True
                cold = ' (Mũi hàn mòn đen, ăn thiếc kém: tốn thêm thiếc, mối hàn dễ nguội — lau hoặc thay mũi hàn đi.)'
            tools['tip'] = max(0, tools['tip'] - TIP_WEAR)
        if grade == 'used':
            d['used_fitted'] += 1
        b['fixed'][fault] = grade
        b['fixcost'][fault] = cost
        b['cost'] += cost
        msg = fd['fix'] + cold
        if grade == 'used' and fault not in b['checked']:
            msg += ' (Đồ tháo máy này chưa cắm thử — hên xui lúc chạy thử.)'
        if not authorized:
            t['mistakes'] += 2
            b['unauthorized'].append(fault)
            d['unauthorized'] += 1
            msg += ' ⚠️ Khách chưa đồng ý khoản này — lúc trả máy sẽ có chuyện.'
        if b['final'] == 'fail':
            b['final'] = None
        return dict(message=msg)
    if name == 'rp_final':
        kit.need(not b['opened'], f'Lắp máy lại trước ({dev["close"]}) rồi mới chạy thử.')
        kit.need(b['fixed'], 'Chưa sửa gì — chạy thử lúc này vẫn y như cũ.')
        kit.need(b['final'] != 'pass', 'Máy đã chạy thử đạt rồi.')
        b['safe'] = []
        actual = _actual(t)
        wrong = [f for f in b['fixed'] if f not in actual]
        for f in wrong:
            fd = _fault_def(device, f)
            item = fd['parts'][b['fixed'][f]]
            kit.waste(c, item or 'job', 1, b['fixcost'][f], 'Thay nhầm do chẩn đoán sai — tiệm tự chịu')
            del b['fixed'][f]
            del b['fixcost'][f]
            b['approved'].pop(f, None)
            if f in hyp and f not in b['ruled_out']:
                b['ruled_out'].append(f)
            if b['diagnosis'] == f:
                b['diagnosis'] = None
            b['wrong'] += 1
            t['mistakes'] += 1
            d['wrong_parts'] += 1
            if f in b['checked']:
                b['checked'].remove(f)
        # Hidden quality of an untested used part shows up now.
        dud = [f for f, g in b['fixed'].items() if g == 'used' and f in actual and f not in b['checked']
               and _unit_bad(t, f, b['units'].get(f, 0))]
        for f in dud:
            kit.waste(c, _fault_def(device, f)['parts']['used'], 1, b['fixcost'][f], 'Đồ tháo máy lắp vào không chạy')
            del b['fixed'][f]
            del b['fixcost'][f]
            b['units'][f] = b['units'].get(f, 0) + 1
            d['used_scrapped'] += 1
        missing = [f for f in actual if f not in b['fixed']]
        if not missing:
            b['final'] = 'pass'
            msg = 'Chạy thử đạt! Máy hoạt động bình thường.'
            if wrong:
                msg += f' Nhưng có {len(wrong)} hạng mục thay thừa — tháo ra ghi hao hụt, không tính tiền khách.'
            return dict(message=msg)
        b['final'] = 'fail'
        if not wrong:
            t['mistakes'] += 1
        t['patience'] = max(25, t['patience'] - 5)
        seen = [f for f in missing if f in b['found']]
        left = _fault_def(device, seen[0] if seen else missing[0])['left']
        msg = f'Chạy thử CHƯA đạt: {left}'
        if dud:
            item = _fault_def(device, dud[0])['parts']['used']
            msg = (f'Chạy thử CHƯA đạt: {ITEM_INDEX[item]["name"].lower()} vừa lắp bị {USED_BAD_READ[item]}. '
                   'Tháo ra ghi hao hụt — lần này cắm thử trước khi lắp nhé.')
        if wrong:
            msg += ' Phần vừa thay không phải thủ phạm — linh kiện ghi hao hụt. Đo lại, chốt lỗi và báo giá lại cho khách.'
        return dict(message=msg)
    if name == 'rp_warranty':
        kit.need(b['final'] == 'pass', 'Chạy thử đạt rồi mới ghi phiếu bảo hành.')
        kit.need(b['warranty'] is None, 'Phiếu bảo hành đã ghi rồi.')
        days = kit.one_of(p.get('days'), WARRANTY, 'Số ngày bảo hành không hợp lệ.')
        rec = _recommended(t)
        b['warranty'] = days
        if days > rec:
            t['mistakes'] += 1
            return dict(message=f'Đã ghi {days} ngày. Linh kiện chỉ được nhà cung cấp bảo hành {rec} ngày — phần vượt tiệm tự gánh.')
        if days < rec:
            return dict(message=f'Đã ghi {days} ngày (linh kiện được bảo hành tới {rec} ngày — khách có thể thắc mắc).')
        return dict(message=f'Đã ghi phiếu bảo hành {days} ngày, ghim kèm phiếu nhận máy.')
    if name == 'rp_handover':
        kit.confirm(p, 'Xác nhận bàn giao máy và thu tiền.')
        tested = b['final'] == 'pass'
        kit.need(b['fixed'], 'Máy chưa sửa gì — không sửa thì trả máy nguyên trạng cho khách.')
        if tested:
            kit.need(b['warranty'] is not None, 'Ghi phiếu bảo hành trước khi bàn giao.')
        kit.need(not b['opened'], 'Máy còn đang mở.')
        if case == 'privacy':
            kit.need(b['data_req'] is not None, 'Khách còn chờ câu trả lời chuyện dữ liệu — từ chối hay làm theo?')
        pay = 0
        for f, grade in b['fixed'].items():
            if f in b['approved'] and f not in b['unauthorized']:
                pay += b['approved'][f]['price']
            else:   # done without an accepted quote: billed at the list price, the customer decides at the counter
                pay += _line(c, device, _fault_def(device, f), grade)['price']
        extra_notes = []
        math = f'sửa {pay}'
        bonus = 0
        left = _rush_left(c, t)
        if left is not None and left >= 0:
            d['rush_on_time'] += 1
            bonus = n['rush']['bonus']
        if case == 'privacy' and b['data_req'] == 'copy':
            pay += DATA_FEE
            math += f' + dữ liệu {DATA_FEE}'
        if case == 'warranty':
            d['claims'] += 1
            if b['claim'] == 'charge' and _covered(t):
                t['mistakes'] += 2
            elif b['claim'] == 'cover' and not _covered(t):
                extra_notes.append('Lần này tiệm chịu thiệt, bảo hành cả phần ngoài phiếu cho vui lòng khách.')
        _handover_slips(c, t, b, tested, pay)
        r = cq.react(s, c, t, pay)
        if r['pay'] < pay:
            math += f' − khách bớt {pay - r["pay"]}'
        # The rush money is a thank-you on top of the bill: an unhappy customer keeps it, and it is never cut.
        if bonus and r['kind'] in ('accept', 'grumble'):
            extra_notes.append(f'Kịp giờ! Khách gửi thêm {bonus} xu tiền gấp.')
            math += f' + tiền gấp {bonus}'
        else:
            bonus = 0
        pay = r['pay'] + bonus
        bill = f' ({math})' if math.count(' ') > 1 else ''   # the line math, when there is more than the repair
        b['paid'] = pay
        d['repaired'] += 1
        d['day_repaired'] += 1
        kit.metric(c, 'repairs_done')
        if not b['unauthorized'] and not b['wrong'] and b['hazards'] == 0 and tested:
            kit.metric(c, 'clean_repairs')
        if t.get('gen') and b['warranty'] is not None:
            main = t['_fault'] if t['_fault'] in b['fixed'] else next(iter(b['fixed']), t['_fault'])
            slip = 'BH-' + t['id'][-7:].replace('-', '')
            d['book'] = (d['book'] + [dict(slip=slip, day=c['day'], npc=t['npc'], device=device, fault=main,
                                           grade=b['fixed'].get(main, 'none'), days=b['warranty'], title=t['title'])])[-BOOK_MAX:]
        acc = ', '.join(ACCESSORIES[a][1].lower() for a in b['intake']['accessories'])
        shelf_note = _pickup_note(c, d, t)
        if tested:
            kit.complete(s, c, t, pay, f'Tiệm đã sửa “{t["title"]}”, trả máy kèm {acc or "phiếu"} và phiếu bảo hành {b["warranty"]} ngày.')
        else:
            kit.complete(s, c, t, pay, f'Tiệm giao lại “{t["title"]}” kèm {acc or "phiếu"} mà chưa chạy thử, không có phiếu bảo hành.')
        _release_orders(c, t)
        trust_note = _regular_after(c, d, t, returned=False)
        _schedule_back(c, d, t, tested)
        tail = (' ' + ' '.join(extra_notes)) if extra_notes else ''
        tail += (' ' + r['message']) if r['message'] else ''
        tail += shelf_note + trust_note
        if not tested:
            return dict(message=f'Đã giao máy khi chưa chạy thử · +{pay} xu{bill}.{tail}')
        if cq.slips(t):
            return dict(message=f'Đã bàn giao máy, phụ kiện và phiếu bảo hành · +{pay} xu{bill}.{tail}')
        return dict(message=f'Đã bàn giao máy, phụ kiện và phiếu bảo hành · +{pay} xu{bill}.{tail}', celebrate=True)
    if name == 'rp_return':
        kit.confirm(p, 'Xác nhận trả máy không sửa.')
        kit.need(not b['fixed'], 'Máy đã thay/sửa một phần — chạy thử rồi bàn giao nhé.')
        kit.need(not b['opened'], f'Lắp máy lại nguyên trạng trước khi trả ({dev["close"]}).')
        fee = CHECK_FEE if b['tests'] else 0
        _common_slips(t, b)
        if _feasible(c, t):
            if fee:
                cq.slip(t, 'gave_up', 2, 'Máy sửa được mà tiệm trả về, tôi mất công đi lại còn mất phí kiểm tra.', 'sửa được mà tiệm trả máy')
            else:
                cq.slip(t, 'gave_up', 2, 'Máy sửa được mà tiệm trả về, tôi mất công mang đi mang lại.', 'sửa được mà tiệm trả máy')
        r = cq.react(s, c, t, fee)
        fee = r['pay']
        b['returned'] = True
        b['paid'] = fee
        d['returned'] += 1
        d['day_returned'] += 1
        kit.metric(c, 'repairs_returned')
        shelf_note = _pickup_note(c, d, t)
        kit.complete(s, c, t, fee, f'Tiệm trả lại “{t["title"]}” nguyên trạng và giải thích vì sao không sửa.')
        _release_orders(c, t)
        trust_note = _regular_after(c, d, t, returned=True)
        tail = (' ' + r['message']) if r['message'] else ''
        tail += shelf_note + trust_note
        return dict(message=f'Đã trả máy nguyên trạng kèm phụ kiện' + (f' · phí kiểm tra {fee} xu.' if fee else ', không thu phí.') + tail)
    raise kit.eng().GameError('Thao tác sửa chữa không hợp lệ.')


# ------------------------------------------------------------------------------ care loop: orders, shelf, calls
def _low(name: str) -> str:
    """Lower-case the first letter only (keeps units like µF)."""
    return name[:1].lower() + name[1:]


def _tag(t: dict) -> str:
    sh = t['bench'].get('shelf')
    return sh['tag'] if sh else DEVICES[t['needs']['device']]['name'].lower()


def _who(t: dict) -> str:
    return PEOPLE[int(t['npc'].rsplit('_', 1)[1]) - 1][0]


def _care_task(s: dict, c: dict, d: dict, t: dict, name: str, p: dict) -> dict:
    b = t['bench']
    device = t['needs']['device']
    if name == 'rp_order':
        fault = p.get('fault')
        kit.need(fault in _open_scope(b), 'Hạng mục này chưa chốt hoặc đã sửa xong — không cần đặt đồ.')
        ap = b['approved'].get(fault)
        kit.need(ap, 'Khách chưa duyệt báo giá cho hạng mục này. Đặt đồ sau khi khách gật đầu, kẻo khách không sửa thì tiệm ôm đồ.')
        grade = ap['grade']
        src = SOURCE_OF.get(grade)
        kit.need(src, 'Đồ tháo máy và việc vệ sinh không đặt riêng được — dùng đồ trên kệ tiệm.')
        item = _fault_def(device, fault)['parts'][grade]
        old = b['orders'].get(fault)
        kit.need(not (old and old['item'] == item and not old['used']), 'Đã đặt món này cho máy rồi, chờ hàng về nhé.')
        kit.confirm(p, 'Xác nhận đặt riêng linh kiện cho máy này (trả tiền hàng và phí giao ngay).')
        it, sv = ITEM_INDEX[item], SOURCES[src]
        cost = it['cost'] + sv['ship']
        kit.money(s, c, -cost, f'Đặt riêng {_low(it["name"])} cho {_tag(t)}', t['id'], 'stock')
        if old and not old['used']:
            _release_one(c, old)      # the customer changed the part grade: the first unit goes to the shelf
        day, minute = _ready(c, src)
        b['orders'][fault] = dict(item=item, src=src, day=day, minute=minute, cost=cost, used=False, told=False)
        d['orders_placed'] += 1
        kit.start_work(t)
        when = _when(c, day, minute)
        tip = '' if b.get('shelf') else ' Chờ lâu thì hẹn khách để máy lại tiệm (🗄️ Hẹn khách).'
        return dict(message=f'{sv["emoji"]} Đã đặt {_low(it["name"])} ({cost} xu, gồm {sv["ship"]} xu giao) — {sv["name"]} giao {when}.{tip}')
    if name == 'rp_shelf':
        kit.need(_case(t) != 'buyin', 'Máy khách muốn bán không để lên kệ sửa.')
        kit.need(not b.get('shelf'), 'Máy đã nằm trên kệ rồi.')
        days = kit.one_of(p.get('days'), PROMISE_DAYS, 'Chọn ngày hẹn: hôm nay, mai, ngày kia hoặc 3 ngày nữa.')
        kit.need(len(_shelved(c)) < SHELF_MAX, f'Kệ máy chờ đã đủ {SHELF_MAX} máy. Làm xong bớt một máy rồi hẹn thêm nhé.')
        kit.confirm(p, 'Xác nhận hẹn khách và để máy lại tiệm.')
        _put_on_shelf(c, d, t, c['day'] + days, auto=False)
        eta_day, _ = _eta(c, t)
        warn = ' ⚠️ Đồ chưa về kịp ngày hẹn — nhớ gọi báo khách nếu phải dời.' if eta_day > c['day'] + days else ''
        return dict(message=f'🏷️ Dán tem {b["shelf"]["tag"]} lên máy, xếp lên kệ. Hẹn {_who(t)} {_promise_word(c, c["day"] + days)} '
                            f'tới lấy.{warn}')
    # rp_answer — a phone call from the owner of a shelved device (no turn).
    sh = b.get('shelf')
    kit.need(sh and sh['call'] == c['day'], 'Không có cuộc gọi nào của khách đang chờ trả lời.')
    reply = kit.one_of(p.get('reply'), REPLIES, 'Chọn nói thật tiến độ hoặc trấn an khách.')
    sh['call'] = None
    d['calls_answered'] += 1
    eta_day, eta_min = _eta(c, t)
    who = _who(t)
    if reply == 'truth':
        waiting = eta_day > c['day'] or (eta_day, eta_min) > (c['day'], _clock(c))
        said = f'đồ về {_when(c, eta_day, eta_min)}' if waiting else 'đồ đã đủ, đang làm'
        if eta_day > sh['promise']:
            sh['promise'] = eta_day
            sh['moved'] += 1
            return dict(message=f'📞 Nói thật với {who}: {said}. Khách hơi tiếc nhưng cảm ơn tiệm báo trước. '
                                f'Hẹn lại: {_promise_word(c, eta_day)}.')
        return dict(message=f'📞 Nói thật với {who}: {said}. Khách yên tâm, vẫn hẹn {_promise_word(c, sh["promise"])}.')
    sh['promise'] = c['day']
    if eta_day > c['day']:
        sh['lied'] = True
        return dict(message=f'📞 Bảo {who} “chiều nay xong”. Khách mừng rỡ… nhưng đồ thay {_when(c, eta_day, eta_min)} mới về.')
    return dict(message=f'📞 Hẹn {who} chiều nay ghé lấy — nhớ làm kịp trước giờ đóng cửa.')


def _put_on_shelf(c: dict, d: dict, t: dict, promise: int, auto: bool) -> None:
    d['shelf_seq'] += 1
    t['bench']['shelf'] = dict(tag=f'#{d["shelf_seq"] % 1000:03d}', since=c['day'], promise=promise, late=0, moved=0,
                               missed=0, calls=0, call=None, lied=False, auto=auto)
    t['deferred'] = True
    if c.get('active_task') == t['id']:
        kit.eng().next_active(c)


def _after_action(c: dict, d: dict, result: dict) -> None:
    """Shelved devices never wait at the counter; a part that just arrived is announced once."""
    news = []
    for t in _open_tasks(c):
        b = t['bench']
        if b.get('shelf'):
            t['deferred'] = True
        for o in (b.get('orders') or {}).values():
            if not o['used'] and not o['told'] and _arrived(c, o):
                o['told'] = True
                news.append(f'{SOURCES[o["src"]]["emoji"]} {ITEM_INDEX[o["item"]]["name"]} cho {_tag(t)} đã về.')
    if news:
        result['message'] = (result.get('message', '') + ' ' + ' '.join(news)).strip()


def _release_one(c: dict, o: dict) -> None:
    from .. import inventory
    o['used'] = True
    it = ITEM_INDEX[o['item']]
    if inventory.capacity(ID) - kit.stock(c, o['item']) > 0:
        kit.add_lot(c, o['item'], 1, it['cost'], it.get('life') or 999, 'order')
    else:
        kit.waste(c, o['item'], 1, o['cost'], 'Linh kiện đặt riêng còn thừa, kệ đã đầy')


def _release_orders(c: dict, t: dict) -> None:
    """A part ordered for this device but not fitted goes to the shop's stock when the job ends."""
    for o in (t['bench'].get('orders') or {}).values():
        if not o['used']:
            _release_one(c, o)


def _pickup_note(c: dict, d: dict, t: dict) -> str:
    sh = t['bench'].get('shelf')
    if not sh:
        return ''
    if sh['late']:
        d['pickups_late'] += 1
        return f' 📞 Gọi {_who(t)} tới lấy máy — trễ hẹn {sh["late"]} ngày.'
    d['pickups_on_time'] += 1
    return f' 📞 Gọi {_who(t)} tới lấy máy — đúng hẹn.'


def _regular_after(c: dict, d: dict, t: dict, returned: bool) -> str:
    """The regulars' card: visits, trust and what was done to their things."""
    if t['npc'] not in REG_IDS or _case(t) == 'buyin':
        return ''
    rec = d['regulars'].setdefault(t['npc'], dict(visits=0, trust=0, ontime=0, late=0, history=[]))
    b = t['bench']
    rec['visits'] += 1
    delta = 0
    sh = b.get('shelf')
    if sh:
        if sh['late']:
            rec['late'] += 1
            delta -= 1
        else:
            rec['ontime'] += 1
    if not returned and not cq.slips(t):
        delta += 1
    before = rec['trust']
    rec['trust'] = max(0, min(TRUST_MAX, before + delta))
    if not returned and b['fixed']:
        main = t['_fault'] if t['_fault'] in b['fixed'] else next(iter(b['fixed']))
        rec['history'] = (rec['history'] + [dict(day=c['day'], device=t['needs']['device'], fault=main, grade=b['fixed'][main],
                                                 days=b['warranty'] or 0, title=t['title'])])[-HISTORY_MAX:]
    if rec['trust'] > before:
        return f' 💛 {_who(t)}: {TRUST_NAMES[rec["trust"]].lower()}.'
    if rec['trust'] < before:
        return f' 💔 {_who(t)} bớt tin tiệm ({TRUST_NAMES[rec["trust"]].lower()}).'
    return ''


def _schedule_back(c: dict, d: dict, t: dict, tested: bool) -> None:
    """A repair that fixed everything may still come back days later (cheap part, no final test, water, cold joint)."""
    if not t.get('gen') or len(d['comebacks']) >= COMEBACK_MAX:
        return
    b = t['bench']
    actual = _actual(t)
    if not actual or t['_fault'] not in b['fixed']:
        return
    dud = [f for f, g in b['fixed'].items() if g == 'used' and f not in b['checked'] and _unit_bad(t, f, b['units'].get(f, 0))]
    if any(f not in b['fixed'] or f in dud for f in actual):
        return     # still broken: the customer already said so at the counter
    main = t['_fault']
    grade = b['fixed'][main]
    risk, cause = GRADE_RISK[grade], {'standard': 'batch', 'none': 'redo'}.get(grade, 'part')
    if not tested:
        risk, cause = risk + 0.3, 'untested'
    if main == 'water':
        risk, cause = risk + 0.15, 'rust'
    if b.get('cold'):
        risk, cause = risk + 0.2, 'joint'
    r = kit.rng(ID, 'back', t['id'])
    if r.random() >= min(0.6, risk):
        return
    handed = c['day']
    d['comebacks'].append(dict(id='BL-' + t['id'][-7:].replace('-', ''), task=t['id'], npc=t['npc'], device=t['needs']['device'],
                               fault=main, grade=grade, days=b['warranty'] or 0, paid=int(b['paid'] or 0), handed=handed,
                               due=handed + r.randint(2, 5), cause=cause, state='wait', title=t['title']))


def _back_covered(row: dict) -> bool:
    return row['days'] > 0 and row['due'] - row['handed'] <= row['days']


def _back_fee(c: dict, row: dict) -> tuple[int, int]:
    """(part cost the shop pays for a free redo, what a charged redo bills: the part plus half the
    labor on today's price board, the same labor the quote uses)."""
    fd = _fault_def(row['device'], row['fault'])
    item = fd['parts'].get(row['grade'])
    cost = ITEM_INDEX[item]['cost'] if item else 1
    price = (ITEM_INDEX[item]['price'] if item else 0) + _round(kit.price(c, row['device'], DEVICES[row['device']]['labor']) * fd['mult'] / 2)
    return cost, price


def _comeback(s: dict, c: dict, d: dict, p: dict) -> dict:
    row = next((x for x in d['comebacks'] if x['id'] == p.get('id') and x['state'] == 'here'), None)
    kit.need(row, 'Không có máy bảo hành nào đang chờ ở quầy.')
    choice = kit.one_of(p.get('choice'), ('redo', 'charge'), 'Chọn sửa lại miễn phí hoặc tính tiền.')
    kit.confirm(p, 'Xác nhận cách xử lý máy quay lại.')
    covered = _back_covered(row)
    cost, price = _back_fee(c, row)
    who = PEOPLE[int(row['npc'].rsplit('_', 1)[1]) - 1][0]
    rec = d['regulars'].get(row['npc'])
    trust = 0
    if choice == 'redo':
        kit.money(s, c, -cost, f'Bảo hành lại “{row["title"]}”', row['id'], 'stock')
        d['comebacks_honoured'] += 1
        if covered:
            kit.review(s, c, row['npc'], 4, 'Máy sửa rồi lại hỏng, nhưng tiệm nhận lại, sửa ngay không kỳ kèo. Giữ đúng lời bảo hành.', row['id'])
            msg = f'🛡️ Bảo hành cho {who}: tiệm chịu {cost} xu linh kiện, sửa lại ngay. Khách yên tâm ra về.'
        else:
            trust = 1
            kit.review(s, c, row['npc'], 5, 'Hết hạn bảo hành rồi mà tiệm vẫn sửa lại miễn phí. Quý hóa quá!', row['id'])
            msg = f'🎁 Đã hết hạn bảo hành, tiệm vẫn sửa miễn phí cho {who} ({cost} xu linh kiện). Khách cảm động lắm.'
    else:
        kit.money(s, c, price, f'Sửa lại máy quay lại “{row["title"]}”', row['id'], 'revenue')
        if covered:
            trust = -2
            kit.review(s, c, row['npc'], 1, 'Còn hạn bảo hành mà tiệm bắt trả tiền sửa lại. Phiếu bảo hành để làm gì?', row['id'])
            msg = f'🧾 Thu {price} xu dù phiếu còn hạn — {who} trả tiền mà mặt nặng như chì.'
        else:
            msg = f'🧾 Phiếu đã hết hạn: báo giá sửa lại {price} xu, {who} gật đầu.'
    if rec is not None and trust:
        rec['trust'] = max(0, min(TRUST_MAX, rec['trust'] + trust))
    d['comebacks'] = [x for x in d['comebacks'] if x is not row]
    return dict(message=msg, celebrate=choice == 'redo')


def _tool(s: dict, c: dict, d: dict, p: dict) -> dict:
    tools = d['tools']
    tool = kit.one_of(p.get('tool'), tuple(TOOLS), 'Dụng cụ không có trên bàn thợ.')
    if tool == 'tip':
        how = kit.one_of(p.get('how'), ('clean', 'replace'), 'Chọn lau mũi hàn hoặc thay mũi mới.')
        if how == 'clean':
            kit.need(tools['tip'] < TIP_CLEAN_MAX, f'Mũi hàn còn sáng ({tools["tip"]}%), chưa cần lau.')
            kit.take(c, 'solder', 1)
            tools['tip'] = min(TIP_CLEAN_MAX, tools['tip'] + TIP_CLEAN)
            return dict(message=f'🧽 Lau mũi hàn qua bọt biển ướt, tráng một lớp thiếc mới: mũi hàn {tools["tip"]}%.')
        kit.need(tools['tip'] < 100, 'Mũi hàn đang mới tinh.')
        kit.confirm(p, f'Thay mũi hàn mới ({TIP_COST} xu)?')
        kit.money(s, c, -TIP_COST, 'Thay mũi hàn', None, 'upkeep')
        tools['tip'] = 100
        return dict(message='🔥 Lắp mũi hàn mới, tráng thiếc lần đầu. Mối hàn lại bóng đẹp.')
    kit.one_of(p.get('how'), ('battery',), 'Đồng hồ đo chỉ cần thay pin.')
    kit.need(tools['meter'] < 100, 'Pin đồng hồ đo còn đầy.')
    kit.confirm(p, f'Thay pin 9V cho đồng hồ đo ({METER_COST} xu)?')
    kit.money(s, c, -METER_COST, 'Pin 9V cho đồng hồ đo', None, 'upkeep')
    tools['meter'] = 100
    return dict(message='📟 Thay pin 9V mới: đồng hồ đo lại số chắc nịch.')


UNSAFE_SLIP = {
    'phone': 'Tiệm tách màn lúc máy còn nguồn, tóe lửa ở cáp pin — lỡ cháy nổ thì sao?',
    'laptop': 'Tiệm cạy nắp laptop khi còn cắm sạc, chưa ngắt pin, tóe lửa ngay trước mặt tôi.',
    'fan': 'Tiệm mở quạt khi chưa rút điện, chưa xả tụ, thợ bị giật tê cả tay.',
    'cooker': 'Tiệm mở nồi cơm khi còn cắm điện, mâm nhiệt còn nóng rẫy, suýt bỏng.',
    'headphone': 'Tiệm tách tai nghe khi còn cắm sạc, chập một cái nghe rõ.',
    'bike': 'Tiệm không dựng xe lên giá, xe đổ rầm xuống sàn, xước thêm một vệt mới.',
}


def _common_slips(t: dict, b: dict) -> None:
    """What the customer sees whatever the outcome: the shop's safety and the intake slip."""
    n = t['needs']
    device = n['device']
    if b['unsafe']:
        if device == 'bike':
            cq.slip(t, 'unsafe', 2, UNSAFE_SLIP[device], 'để xe đổ, xước thêm')
        else:
            cq.slip(t, 'unsafe', 3, UNSAFE_SLIP[device], 'mở máy khi còn điện', safety=True)
    sh = b.get('shelf')
    if sh and sh['late']:
        if sh['lied']:
            cq.slip(t, 'late_pickup', 2, 'Tiệm bảo “chiều nay xong”, tôi tới thì máy vẫn nằm trên kệ, còn chưa có đồ thay.',
                    'hứa lèo ngày trả máy')
        else:
            cq.slip(t, 'late_pickup', 2 if sh['late'] >= 2 else 1,
                    f'Tiệm hẹn trả máy mà trễ {sh["late"]} ngày, tôi phải gọi hỏi mãi.', 'trễ hẹn trả máy')
    intake = b['intake'] or dict(marks=[], accessories=[])
    lost = [a for a in n['accessories'] if a not in intake['accessories']]
    if lost:
        names = ', '.join(ACCESSORIES[a][1].lower() for a in lost)
        cq.slip(t, 'lost_acc', 2, f'Tôi gửi kèm {names} mà phiếu nhận không ghi, lúc lấy máy phải đứng đòi mãi.',
                'phiếu nhận ghi thiếu phụ kiện')
    elif set(intake['marks']) != set(n['marks']) or set(intake['accessories']) != set(n['accessories']):
        cq.slip(t, 'intake', 1, 'Phiếu nhận ghi sai tình trạng máy tôi, sau này có vết gì lại khó nói.',
                'phiếu nhận ghi sai tình trạng máy')


def _handover_slips(c: dict, t: dict, b: dict, tested: bool, pay: int) -> None:
    """Compare what goes back over the counter with what the customer asked and agreed to."""
    device = t['needs']['device']
    _common_slips(t, b)
    if not tested:
        actual = _actual(t)
        dud = [f for f, g in b['fixed'].items() if g == 'used' and f in actual and f not in b['checked']
               and _unit_bad(t, f, b['units'].get(f, 0))]
        missing = [f for f in actual if f not in b['fixed'] or f in dud]
        wrong = [f for f in b['fixed'] if f not in actual]
        if missing:
            left = _fault_def(device, missing[0])['left']
            cq.slip(t, 'not_fixed', 3, f'Tiệm giao máy mà chưa chạy thử, về nhà vẫn y bệnh cũ: {left}', 'máy giao về vẫn hỏng')
        if wrong:
            cq.slip(t, 'wrong_part', 2, f'Tiệm tính tiền “{_fault_def(device, wrong[0])["name"].lower()}” mà bệnh đâu phải ở đó.',
                    'thay nhầm linh kiện vẫn tính tiền')
        if not missing and not wrong:
            cq.slip(t, 'no_test', 1, 'Tiệm không chạy thử trước mặt tôi, cũng không có phiếu bảo hành.',
                    'không chạy thử, không phiếu bảo hành')
    elif b['wrong']:
        cq.slip(t, 'misdiag', 1, 'Tiệm thay nhầm một lần rồi mới ra bệnh, tôi phải chờ thêm và nghe báo giá lại.',
                'thay nhầm rồi mới ra bệnh')
    if b['unauthorized']:
        cq.slip(t, 'unauthorized', 3, 'Tôi chưa đồng ý mà tiệm tự ý sửa rồi tính tiền.', 'sửa khi khách chưa đồng ý')
    if _case(t) == 'warranty' and b['claim'] == 'charge' and _covered(t):
        cq.slip(t, 'overcharge', 3, f'Còn hạn bảo hành mà tiệm vẫn thu tôi {pay} xu.', 'còn bảo hành mà vẫn tính tiền')
    rec = _recommended(t)
    if tested and (b['warranty'] or 0) < rec:
        cq.slip(t, 'short_warranty', 1, f'Linh kiện được bảo hành {rec} ngày mà tiệm chỉ ghi cho tôi {b["warranty"] or 0} ngày.',
                'phiếu bảo hành ngắn hơn mức linh kiện')
    left = _rush_left(c, t)
    if left is not None and left < 0:
        cq.slip(t, 'late', 1, 'Hẹn lấy gấp mà tiệm trễ giờ, tôi lỡ cả việc.', 'trễ giờ hẹn gấp')


def feedback(c: dict, t: dict) -> dict:
    b = t['bench']
    n = t['needs']
    case = _case(t)
    patience = t.get('patience', 100)
    speed = 5 if patience >= 90 else 4 if patience >= 70 else 3 if patience >= 50 else 2
    if case == 'buyin':
        x = t['_x']
        checks = (b['imei'] is not None) + (b['papers'] is not None)
        right = {'buy': not x['stolen'], 'report': x['stolen'], 'refuse': True}[b['deal'] or 'refuse']
        deal_score = 5 if right and b['deal'] != 'refuse' else 4 if right else 1
        rows = [dict(key='check', label='Kiểm tra nguồn gốc', score=5 if checks == 2 else 4 if checks else 2,
                     note='tra IMEI và hỏi giấy tờ đàng hoàng' if checks == 2 else 'kiểm một nửa' if checks else 'không kiểm gì đã quyết'),
                dict(key='deal', label='Quyết định thu mua', score=deal_score,
                     note={'buy': 'mua đúng máy sạch' if right else 'mua phải máy gian',
                           'report': 'báo đúng máy gian' if right else 'nghi oan người bán ngay thẳng',
                           'refuse': 'từ chối cho chắc'}[b['deal'] or 'refuse']),
                dict(key='speed', label='Thời gian chờ', score=speed, note=f'kiên nhẫn còn {patience}%')]
        return dict(criteria=rows)
    intake = b['intake'] or dict(marks=[], accessories=[])
    intake_ok = set(intake['marks']) == set(n['marks']) and set(intake['accessories']) == set(n['accessories'])
    rows = []
    if b['returned']:
        feasible = _feasible(c, t)
        diag_ok = b['diagnosis'] == t['_fault']
        rows.append(dict(key='diagnosis', label='Chẩn đoán', score=5 if diag_ok else 3 if b['tests'] else 2,
                         note='đo đúng bệnh rồi mới tư vấn' if diag_ok else 'chưa tìm ra bệnh' if b['tests'] else 'chưa kiểm đã trả máy'))
        rows.append(dict(key='honesty', label='Tư vấn thật lòng', score=5 if not feasible else 3,
                         note='nói thật: sửa không đáng tiền' if not feasible else 'sửa được mà tiệm lại trả máy'))
        rows.append(dict(key='result', label='Kết quả', score=4 if not feasible else 2,
                         note='không sửa nhưng hiểu vì sao' if not feasible else 'máy vẫn hỏng, về tay không'))
    else:
        tests = len(b['tests'])
        diag = 5 if not b['wrong'] and tests <= 3 else 4 if not b['wrong'] else 3 if b['wrong'] == 1 else 2
        if case in ('water', 'warranty') and not b['wrong']:
            diag = 5 if tests <= 4 else 4     # these cases need one more look
        rows.append(dict(key='diagnosis', label='Chẩn đoán', score=diag,
                         note='đo đúng, chốt nhanh' if diag == 5 else f'đo tới {tests} lần mới chốt' if diag == 4 else 'thay nhầm rồi mới ra bệnh'))
        rows.append(dict(key='honesty', label='Báo giá & đồng ý', score=1 if b['unauthorized'] else 5,
                         note='sửa khi khách chưa đồng ý' if b['unauthorized'] else 'báo giá rõ, sửa sau khi khách gật đầu'))
        grade = b['fixed'].get(t['_fault'], 'none')
        used_ok = grade != 'used' or t['_fault'] in b['checked']
        rows.append(dict(key='result', label='Linh kiện & độ bền',
                         score=4 if grade in ('compatible', 'used') and used_ok else 3 if grade == 'used' else 5,
                         note={'genuine': 'linh kiện chính hãng', 'compatible': 'linh kiện tương thích, bảo hành ngắn hơn',
                               'standard': 'linh kiện mới đúng loại', 'none': 'vệ sinh, chỉnh kỹ, không thay bừa',
                               'used': 'đồ tháo máy đã cắm thử, giá mềm' if used_ok else 'đồ tháo máy lắp mà chưa thử'}[grade]))
        rec = _recommended(t)
        days = b['warranty'] or 0
        rows.append(dict(key='warranty', label='Phiếu bảo hành', score=5 if days == rec else 4 if days > rec else 3,
                         note=f'{days} ngày đúng loại linh kiện' if days == rec else f'hứa {days} ngày, quá mức linh kiện' if days > rec else f'chỉ {days} ngày, ít hơn mức {rec} ngày'))
        if case == 'warranty':
            covered = _covered(t)
            ok = (b['claim'] == 'cover') == covered
            rows.append(dict(key='claim', label='Xét bảo hành', score=5 if ok else 3 if covered is False else 1,
                             note=('đối chiếu sổ, xét đúng quyền lợi' if ok else
                                   'bảo hành cả phần ngoài phiếu' if not covered else 'còn bảo hành mà vẫn tính tiền')))
        if case == 'rush':
            left = _rush_left(c, t)
            speed = 5 if left is not None and left >= 0 else 2
        if case == 'privacy':
            rows.append(dict(key='privacy', label='Chuyện dữ liệu', score=5,
                             note='giữ nguyên tắc dữ liệu' if b['data_req'] == 'refuse' else 'chiều khách chuyện dữ liệu'))
    rows.append(dict(key='intake', label='Phiếu nhận máy', score=5 if intake_ok else 3,
                     note='ghi đủ tình trạng và phụ kiện' if intake_ok else 'ghi thiếu/sai tình trạng hoặc phụ kiện'))
    rows.append(dict(key='care', label='An toàn & cẩn thận', score=5 if b['hazards'] == 0 else 3,
                     note='làm đúng thứ tự an toàn' if b['hazards'] == 0 else 'có lúc thao tác thiếu an toàn'))
    sh = b.get('shelf')
    if sh:
        # The customer went home: what counts is the promised pickup day, not waiting at the counter.
        if sh['late']:
            score = 2 if sh['late'] >= 2 or sh['lied'] else 3
            note = 'hứa lèo ngày trả máy' if sh['lied'] else f'trễ hẹn {sh["late"]} ngày'
        else:
            score = max(3, (4 if sh['moved'] else 5) - sh['missed'])
            note = ('đúng hẹn' if not sh['moved'] else 'báo dời hẹn trước') + (f', {sh["missed"]} lần gọi không ai nghe' if sh['missed'] else '')
        rows.append(dict(key='promise', label='Giữ hẹn', score=score, note=note))
    else:
        rows.append(dict(key='speed', label='Thời gian chờ', score=speed,
                         note=f'kiên nhẫn còn {patience}%' if case != 'rush' else ('kịp giờ hẹn gấp' if speed == 5 else 'trễ giờ hẹn gấp')))
    if cq.slips(t) and len(rows) >= 8:
        # the recorded mistakes add their own line; the review holds at most 8
        rows.remove(max(reversed(rows), key=lambda x: x['score']))
    out = dict(criteria=rows)
    if b['unauthorized'] or (case == 'warranty' and b['claim'] == 'charge' and _covered(t)):
        out['cap'] = 2
    return out


def _strip(v):
    if isinstance(v, dict):
        return {k: _strip(x) for k, x in v.items() if not k.startswith('_')}
    if isinstance(v, list):
        return [_strip(x) for x in v]
    return v


def public_task(t: dict) -> dict:
    v = _strip(copy.deepcopy(t))
    if not t['known']:
        v['needs'] = None
        return v
    b = t['bench']
    v['scope'] = _scope(b)
    v['open_scope'] = _open_scope(b)
    v['recommended'] = _recommended(t) if b['final'] == 'pass' else None
    rush = t['needs'].get('rush') if t.get('gen') else None
    v['due_turn'] = t['created_turn'] + rush['steps'] if rush else None
    if t['status'] in DONE:
        v['solved'] = _actual(t)
        if _case(t) == 'buyin':
            v['truth'] = dict(stolen=t['_x']['stolen'])
        elif _case(t) == 'warranty':
            v['truth'] = dict(covered=_covered(t))
    return v


def validate_task(t: dict, original: dict) -> None:
    b = t['bench']
    kit.need(isinstance(b, dict) and set(_empty_bench()) <= set(b), 'Bàn sửa thiếu dữ liệu.')
    device = t['needs']['device']
    kit.need(device in DEVICES, 'Loại máy sai.')
    dev = DEVICES[device]
    hyp = _hyps(t)
    kit.need(set(hyp) <= set(_hyp(device)), 'Bảng giả thuyết sai.')
    every = _hyp(device) + [x['id'] for x in EXTRAS.get(device, [])]
    case = _case(t)
    kit.need(case in (None, *CASES), 'Loại việc sai.')

    def ids(value, allowed, limit=12):
        kit.need(isinstance(value, list) and len(value) <= limit and len(set(value)) == len(value) and all(x in allowed for x in value),
                 'Danh sách trên bàn sửa không hợp lệ.')

    if b['intake'] is not None:
        kit.need(isinstance(b['intake'], dict) and type(b['intake'].get('consent')) is bool, 'Phiếu nhận máy sai.')
        ids(b['intake'].get('marks'), dev['marks'])
        ids(b['intake'].get('accessories'), dev['accessories'])
    kit.need(b['data_ok'] in (None, t['_data_ok']) and (b['data_ok'] is None or device in DATA_DEVICES), 'Quyền dữ liệu sai.')
    kit.need(isinstance(b['safe'], list) and b['safe'] == dev['safety'][:len(b['safe'])], 'Bước an toàn sai thứ tự.')
    for k in ('opened', 'returned', 'shown'):
        kit.need(type(b[k]) is bool, 'Trạng thái máy sai.')
    kit.need(isinstance(b['tests'], list) and len(b['tests']) <= len(TESTS[device]), 'Kết quả đo sai.')
    kit.need(case != 'buyin' or (not b['tests'] and not b['fixed'] and b['quote'] is None and b['intake'] is None),
             'Máy thu mua không qua bàn sửa.')
    seen = set()
    for row in b['tests']:
        kit.need(isinstance(row, dict) and row.get('id') in TEST_INDEX[device] and row['id'] not in seen, 'Phép đo sai.')
        kit.need(row.get('reading') == TEST_INDEX[device][row['id']]['read'][t['_fault']], 'Số đo không khớp máy.')
        seen.add(row['id'])
    ids(b['ruled_out'], hyp)
    kit.need(b['diagnosis'] is None or b['diagnosis'] in hyp, 'Chẩn đoán sai.')
    kit.need(b['found'] in ([], [t['_extra']]) and (not b['found'] or t['_extra']), 'Lỗi phát hiện sai.')
    q = b['quote']
    if q is not None:
        kit.need(isinstance(q, dict) and q.get('status') in ('accepted', 'declined') and isinstance(q.get('lines'), dict), 'Báo giá sai.')
        kit.integer(q.get('rounds'), 1, QUOTE_ROUNDS)
        kit.integer(q.get('total'), 0, 5000)
        kit.text(q.get('reason'), 300)
        kit.need(len(q['lines']) <= len(every), 'Báo giá sai.')
        for f, line in q['lines'].items():
            kit.need(f in every and isinstance(line, dict) and line.get('grade') in _fault_def(device, f)['parts'], 'Dòng báo giá sai.')
            for k in ('labor', 'part', 'price'):
                kit.integer(line.get(k), 0, 5000)
            kit.need(line['price'] == line['labor'] + line['part'], 'Dòng báo giá sai.')
    kit.need(isinstance(b['approved'], dict) and len(b['approved']) <= len(every), 'Khoản đã duyệt sai.')
    for f, row in b['approved'].items():
        kit.need(f in every and isinstance(row, dict) and row.get('grade') in _fault_def(device, f)['parts'], 'Khoản đã duyệt sai.')
        kit.integer(row.get('price'), 0, 5000)
    kit.need(isinstance(b['fixed'], dict) and isinstance(b['fixcost'], dict) and set(b['fixed']) == set(b['fixcost']), 'Hạng mục đã sửa sai.')
    for f, grade in b['fixed'].items():
        kit.need(f in every and grade in _fault_def(device, f)['parts'], 'Hạng mục đã sửa sai.')
        kit.integer(b['fixcost'][f], 0, 5000)
    ids(b['unauthorized'], every)
    kit.integer(b['wrong'], 0, 50)
    kit.integer(b['hazards'], 0, 100)
    kit.integer(b['cost'], 0, 100000)
    kit.need(b['final'] in (None, 'pass', 'fail'), 'Kết quả chạy thử sai.')
    kit.need(b['warranty'] is None or b['warranty'] in WARRANTY, 'Bảo hành sai.')
    kit.need(b['paid'] is None or 0 <= kit.integer(b['paid'], 0, 5000), 'Tiền thu sai.')
    # v0.5 bench
    kit.need(isinstance(b['units'], dict) and all(f in every and kit.integer(n, 0, 10) >= 0 for f, n in b['units'].items()),
             'Lượt thử linh kiện sai.')
    ids(b['checked'], every)
    kit.integer(b['unsafe'], 0, 50)
    kit.need(not b['shown'] or (t['_fault'] == 'water' and any(r['id'] == 'water_tag' for r in b['tests'])), 'Bằng chứng tem nước sai.')
    kit.need(b['book'] is None or (case == 'warranty' and b['book'] == _book_view(t)), 'Sổ bảo hành sai.')
    kit.need(b['claim'] in (None, 'cover', 'charge') and (b['claim'] is None or b['book'] is not None), 'Quyết định bảo hành sai.')
    kit.need(b['data_req'] in (None, 'refuse', 'copy') and (b['data_req'] is None or case == 'privacy'), 'Trả lời dữ liệu sai.')
    x = t.get('_x') or {}
    kit.need(b['imei'] is None or (case == 'buyin' and b['imei'] == x.get('imei')), 'Kết quả tra IMEI sai.')
    kit.need(b['papers'] is None or (case == 'buyin' and b['papers'] == x.get('papers')), 'Giấy tờ sai.')
    kit.need(b['deal'] in (None, 'buy', 'refuse', 'report') and (b['deal'] is None or case == 'buyin'), 'Quyết định thu mua sai.')
    # care loop
    kit.need(type(b['cold']) is bool, 'Mối hàn sai.')
    orders = b['orders']
    kit.need(isinstance(orders, dict) and len(orders) <= len(every) and (case != 'buyin' or not orders), 'Đơn linh kiện riêng sai.')
    for f, o in orders.items():
        kit.need(f in every and isinstance(o, dict), 'Đơn linh kiện riêng sai.')
        ok = [(g, item) for g, item in _fault_def(device, f)['parts'].items() if item and g in SOURCE_OF]
        kit.need(any(o.get('item') == item and o.get('src') == SOURCE_OF[g] for g, item in ok), 'Đơn linh kiện riêng sai.')
        kit.integer(o.get('day'), 1, 10**7)
        kit.integer(o.get('minute'), 0, 24 * 60)
        kit.integer(o.get('cost'), 0, 5000)
        kit.need(type(o.get('used')) is bool and type(o.get('told')) is bool, 'Đơn linh kiện riêng sai.')
    sh = b['shelf']
    if sh is not None:
        kit.need(isinstance(sh, dict) and case != 'buyin' and b['intake'] is not None, 'Tem kệ máy chờ sai.')
        kit.text(sh.get('tag'), 12)
        since = kit.integer(sh.get('since'), 1, 10**7)
        kit.integer(sh.get('promise'), since, since + 365)
        for k in ('late', 'moved', 'missed', 'calls'):
            kit.integer(sh.get(k), 0, 999)
        kit.need(sh.get('call') is None or kit.integer(sh['call'], since, 10**7) >= since, 'Cuộc gọi của khách sai.')
        kit.need(type(sh.get('lied')) is bool and type(sh.get('auto')) is bool, 'Tem kệ máy chờ sai.')


def validate_data(c: dict) -> None:
    d = _data(c, stock=False)
    kit.mark_legacy(c, ID)
    for t in c.get('tasks', []):
        if isinstance(t, dict) and t.get('career') == ID and isinstance(t.get('bench'), dict):
            for k, v in BENCH_V2.items():
                t['bench'].setdefault(k, copy.deepcopy(v))
    for k in ('repaired', 'returned', 'hazards', 'unauthorized', 'wrong_parts', 'day_repaired', 'day_returned', 'day_hazards',
              'used_scrapped', 'used_fitted', 'rush_on_time', 'buyins', 'stolen_caught', 'claims', 'leaks'):
        kit.integer(d.get(k), 0, 10**9)
    kit.need(type(d['v2_stock']) is bool, 'Cờ kho sai.')
    kit.need(d['today'] is None or (isinstance(d['today'], dict) and d['today'].get('id') in TODAY_INDEX), 'Chuyện hôm nay sai.')
    kit.need(isinstance(d['book'], list) and len(d['book']) <= BOOK_MAX, 'Sổ bảo hành sai.')
    for row in d['book']:
        kit.need(isinstance(row, dict) and row.get('device') in DEVICES and row.get('grade') in GRADES, 'Dòng sổ bảo hành sai.')
        kit.need(row.get('fault') in [f['id'] for f in FAULTS[row['device']] + EXTRAS.get(row['device'], [])], 'Dòng sổ bảo hành sai.')
        kit.need(row.get('days') in WARRANTY, 'Dòng sổ bảo hành sai.')
        kit.integer(row.get('day'), -999, 10**7)
        kit.text(row.get('slip'), 20)
        kit.text(row.get('title'), 200)
    kit.desk_validate(d['desk'], DESK)
    # care loop
    for k in CARE_STATS:
        kit.integer(d.get(k), 0, 10**9)
    ck = d['clock']
    kit.need(ck is None or (isinstance(ck, dict) and set(ck) == {'day', 'turn0'}), 'Đồng hồ tiệm sai.')
    if ck is not None:
        kit.integer(ck['day'], 1, 10**7)
        kit.integer(ck['turn0'], 0, 10**9)
    tools = d['tools']
    kit.need(isinstance(tools, dict) and set(tools) == set(TOOLS), 'Dụng cụ sai.')
    for k in TOOLS:
        kit.integer(tools[k], 0, 100)
    regs = d['regulars']
    kit.need(isinstance(regs, dict) and len(regs) <= len(REG_IDS) and all(k in REG_IDS for k in regs), 'Sổ khách quen sai.')
    for rec in regs.values():
        kit.need(isinstance(rec, dict), 'Sổ khách quen sai.')
        kit.integer(rec.get('visits'), 0, 10**6)
        kit.integer(rec.get('trust'), 0, TRUST_MAX)
        kit.integer(rec.get('ontime'), 0, 10**6)
        kit.integer(rec.get('late'), 0, 10**6)
        hist = rec.get('history')
        kit.need(isinstance(hist, list) and len(hist) <= HISTORY_MAX, 'Sổ khách quen sai.')
        for h in hist:
            kit.need(isinstance(h, dict) and h.get('device') in DEVICES and h.get('grade') in GRADES and h.get('days') in WARRANTY,
                     'Sổ khách quen sai.')
            kit.need(_fault_def(h['device'], h.get('fault')) is not None, 'Sổ khách quen sai.')
            kit.integer(h.get('day'), 1, 10**7)
            kit.text(h.get('title'), 200)
    backs = d['comebacks']
    npcs = {kit.npc_id(ID, i) for i in range(len(PEOPLE))}
    kit.need(isinstance(backs, list) and len(backs) <= COMEBACK_MAX, 'Sổ máy quay lại sai.')
    for row in backs:
        kit.need(isinstance(row, dict) and row.get('npc') in npcs and row.get('device') in DEVICES and row.get('grade') in GRADES
                 and row.get('days') in WARRANTY and row.get('cause') in CAUSES and row.get('state') in ('wait', 'here'),
                 'Sổ máy quay lại sai.')
        kit.need(_fault_def(row['device'], row.get('fault')) is not None and row['grade'] in _fault_def(row['device'], row['fault'])['parts'],
                 'Sổ máy quay lại sai.')
        kit.text(row.get('id'), 30)
        kit.text(row.get('task'), 60)
        kit.text(row.get('title'), 200)
        kit.integer(row.get('paid'), 0, 5000)
        handed = kit.integer(row.get('handed'), 1, 10**7)
        kit.integer(row.get('due'), handed + 1, handed + 10)
    kit.need(len({x['id'] for x in backs}) == len(backs), 'Sổ máy quay lại sai.')


def on_task(s: dict, c: dict, t: dict) -> None:
    d = _data(c)
    if not t.get('gen') or t['career'] != ID:
        return
    tier = kit.tier(t['day'])
    start = 100 - 4 * tier - (8 if _today(c)['id'] == 'market' else 0)
    t['patience'] = max(60, min(t.get('patience', 100), start))
    # A regular who trusts the shop waits more calmly.
    t['patience'] = min(100, t['patience'] + TRUST_PATIENCE * _trust(d, t['npc']))
    if _case(t) == 'warranty':
        bk = t['_x']['book']
        if not any(r['slip'] == bk['slip'] for r in d['book']):
            d['book'] = (d['book'] + [dict(slip=bk['slip'], day=t['day'] - bk['ago'], npc=t['npc'], device=t['needs']['device'],
                                           fault=bk['fault'], grade=bk['grade'], days=bk['days'],
                                           title=f'{DEVICES[t["needs"]["device"]]["name"]} — {_fault_def(t["needs"]["device"], bk["fault"])["name"].lower()}')])[-BOOK_MAX:]


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    mod = today(c['day'])
    d['today'] = dict(id=mod['id'], day=c['day'])
    d['clock'] = dict(day=c['day'], turn0=c['turn'])
    kit.log(s, c, 'today', f'{mod["emoji"]} Hôm nay: {mod["title"]} — {mod["text"]}')
    # Devices on the shelf: their owners phone to ask, parts that came overnight are on the counter.
    for t in _open_tasks(c):
        b = t['bench']
        sh = b.get('shelf')
        if sh:
            t['deferred'] = True
            if b['final'] != 'pass' and sh['since'] < c['day']:
                sh['call'] = c['day']
                sh['calls'] += 1
                kit.log(s, c, 'repair', f'📞 {_who(t)} gọi hỏi: “{DEVICES[t["needs"]["device"]]["name"]} ({sh["tag"]}) xong chưa?”',
                        t['npc'], t['id'])
        for o in (b.get('orders') or {}).values():
            if not o['used'] and not o['told'] and _arrived(c, o):
                o['told'] = True
                kit.log(s, c, 'repair', f'{SOURCES[o["src"]]["emoji"]} Đồ về: {ITEM_INDEX[o["item"]]["name"]} cho {_tag(t)}.', ref=t['id'])
    for row in d['comebacks']:
        if row['state'] == 'wait' and row['due'] <= c['day']:
            row['state'] = 'here'
            d['comebacks_seen'] += 1
            kit.log(s, c, 'repair', f'📒 {PEOPLE[int(row["npc"].rsplit("_", 1)[1]) - 1][0]} mang “{row["title"]}” quay lại tiệm.',
                    row['npc'], row['id'])
    active = next((t for t in c['tasks'] if t['id'] == c.get('active_task')), None)
    if active and active.get('deferred'):
        kit.eng().next_active(c)
    kit.desk_start(s, c, ID, d['desk'], DESK, mod['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    note = kit.desk_close(s, c, ID, d['desk'], DESK)
    out = dict(repaired=d['day_repaired'], returned=d['day_returned'], hazards=d['day_hazards'])
    # The day summary lists `lines` under the career's notebook.
    lines = [f'Hôm nay sửa xong {d["day_repaired"]} máy, trả lại nguyên trạng {d["day_returned"]} máy.']
    if d['day_hazards']:
        lines.append(f'Thao tác nguy hiểm: {d["day_hazards"]} lần — rút điện, xả tụ rồi mới mở máy.')
    lines += _close_care(s, c, d)
    if note:
        out['surprise'] = note
        lines.append(note)
    nxt = today(c['day'] + 1)
    lines.append(f'Dự báo ngày mai: {nxt["emoji"]} {nxt["title"]} — {nxt["text"]}')
    out['lines'] = lines
    d['day_repaired'] = d['day_returned'] = d['day_hazards'] = 0
    return out


def _close_care(s: dict, c: dict, d: dict) -> list[str]:
    """Closing time: late promises, unanswered calls, comebacks nobody saw, devices left overnight."""
    lines = []
    for t in _shelved(c):
        sh = t['bench']['shelf']
        if sh['call'] == c['day']:
            sh['missed'] += 1
            sh['call'] = None
            lines.append(f'📵 {_who(t)} gọi hỏi máy {sh["tag"]} mà không ai trả lời.')
        if sh['promise'] <= c['day']:
            sh['late'] += 1
            lines.append(f'⚠️ Hẹn {_who(t)} trả máy {sh["tag"]} mà tới giờ đóng cửa vẫn chưa xong.')
    for t in _open_tasks(c):
        b = t['bench']
        if b['intake'] is not None and not b['returned'] and not b.get('shelf') and _case(t) != 'buyin':
            _put_on_shelf(c, d, t, c['day'] + 1, auto=True)
            lines.append(f'🏷️ {DEVICES[t["needs"]["device"]]["name"]} của {_who(t)} ở lại qua đêm (tem {b["shelf"]["tag"]}), hẹn mai.')
    for row in [x for x in d['comebacks'] if x['state'] == 'here']:
        who = PEOPLE[int(row['npc'].rsplit('_', 1)[1]) - 1][0]
        kit.review(s, c, row['npc'], 2, 'Mang máy bảo hành tới mà tiệm bận tối mắt, chẳng ai tiếp. Hẹn lần hẹn lữa.', row['id'])
        rec = d['regulars'].get(row['npc'])
        if rec:
            rec['trust'] = max(0, rec['trust'] - 1)
        lines.append(f'😞 {who} chờ bảo hành “{row["title"]}” cả ngày không ai tiếp, đành mang về.')
    d['comebacks'] = [x for x in d['comebacks'] if x['state'] != 'here']
    # Tomorrow: what arrives and who is promised.
    tomorrow = c['day'] + 1
    for t in _shelved(c):
        sh = t['bench']['shelf']
        parts = [_low(ITEM_INDEX[o['item']]['name']) for o in t['bench']['orders'].values() if not o['used'] and o['day'] == tomorrow]
        if parts:
            lines.append(f'📦 Mai về: {", ".join(parts)} cho máy {sh["tag"]}.')
        if sh['promise'] == tomorrow:
            lines.append(f'🗓️ Mai hẹn trả: {DEVICES[t["needs"]["device"]]["name"].lower()} của {_who(t)} ({sh["tag"]}).')
    tools = d['tools']
    if tools['tip'] < TIP_LOW:
        lines.append(f'🔥 Mũi hàn còn {tools["tip"]}% — lau hoặc thay trước khi hàn tiếp.')
    if tools['meter'] < METER_LOW:
        lines.append(f'📟 Pin đồng hồ đo còn {tools["meter"]}% — thay pin trước khi đo.')
    return lines


def public_data(c: dict) -> dict:
    d = copy.deepcopy(kit.data(c))
    desk = d.pop('desk', None) or kit.desk_initial()
    for k, v in DATA_V2.items():
        d.setdefault(k, copy.deepcopy(v))
    mod = _today(c)
    d['today'] = dict(id=mod['id'], title=mod['title'], emoji=mod['emoji'], text=mod['text'])
    d['desk'] = kit.desk_public(desk, DESK, ID)
    if d['desk']['ev']:
        # Options come in a shuffled order so the careful answer is not always the first button.
        kit.rng(ID, 'desk-order', d['desk']['ev']['id'], c['day']).shuffle(d['desk']['ev']['options'])
    d['tier'] = kit.tier(c['day'])
    d['book'] = d['book'][-10:]
    for k, v in DATA_V3.items():
        d.setdefault(k, copy.deepcopy(v))
    # A comeback that has not happened yet stays a secret.
    d['comebacks'] = [x for x in d['comebacks'] if x.get('state') == 'here']
    for x in d['comebacks']:
        cost, price = _back_fee(c, x)
        x.update(covered=_back_covered(x), cost=cost, price=price, cause_text=CAUSES[x['cause']],
                 left=_fault_def(x['device'], x['fault'])['left'], who=PEOPLE[int(x['npc'].rsplit('_', 1)[1]) - 1][0])
    d['care'] = _care_view(c)
    return d


def _care_view(c: dict) -> dict:
    """Clock words, part arrivals and promises, computed here so the client never re-implements the rules."""
    now = _clock(c)
    tasks, shelf = {}, []
    for t in _open_tasks(c):
        b = t['bench']
        view = dict(orders={f: dict(item=o['item'], src=o['src'], used=o['used'], arrived=_arrived(c, o),
                                    when=_when(c, o['day'], o['minute']))
                            for f, o in (b.get('orders') or {}).items()})
        eta_day, eta_min = _eta(c, t)
        view['eta_days'] = max(0, eta_day - c['day'])
        view['eta'] = _when(c, eta_day, eta_min) if (eta_day, eta_min) > (c['day'], now) else None
        sh = b.get('shelf')
        if sh:
            view.update(promise=_promise_word(c, sh['promise']), due=sh['promise'] - c['day'], call=sh['call'] == c['day'])
            shelf.append(t['id'])
        tasks[t['id']] = view
    return dict(minute=now, clock=_hm(now), open=bool(c.get('open')), shelf=shelf, tasks=tasks, shelf_max=SHELF_MAX,
                sources={sid: dict(when=_when(c, *_ready(c, sid))) for sid in SOURCES})


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    role = e['role']
    if role == 'front':
        return 'Đã dán tem tên khách lên máy, bỏ phụ kiện vào túi zip có ghi số phiếu.'
    if role == 'parts':
        tools = _data(c)['tools']
        if tools['meter'] < METER_LOW:
            return f'Pin đồng hồ đo còn {tools["meter"]}% — số sẽ nhảy loạn, nên thay pin 9V ({METER_COST} xu) trước khi đo.'
        if tools['tip'] < TIP_LOW:
            return f'Mũi hàn còn {tools["tip"]}%, đen sì — lau qua bọt biển hoặc thay mũi mới trước khi hàn.'
        low = [i['name'] for i in ITEMS if i['group'] != 'supply' and i.get('unlock', 1) <= kit.level(c) and kit.stock(c, i['id']) == 0]
        return ('Kiểm kệ linh kiện: hết ' + ', '.join(low[:3]) + ' — nhớ đặt thêm.') if low else 'Đã xếp linh kiện theo ngăn, kiểm hạn keo tản nhiệt.'
    if not t or t['career'] != ID or not t['known'] or t['status'] in DONE:
        return None
    b = t['bench']
    if role == 'apprentice' and b['intake'] and not b['opened'] and b['final'] != 'pass' and b['diagnosis']:
        safety = DEVICES[t['needs']['device']]['safety']
        if len(b['safe']) < len(safety):
            step = safety[len(b['safe'])]
            b['safe'].append(step)
            return f'Đã “{SAFETY[step][1].lower()}” cho máy đang sửa. Bạn vẫn là người mở máy và thay đồ.'
    return None


def hint(c: dict, t: dict) -> str:
    case = _case(t)
    if case == 'buyin':
        return 'Máy khách muốn bán: tra IMEI, hỏi hóa đơn và căn cước, so giá với giá chợ — rồi mới quyết mua, từ chối hay báo công an phường.'
    tip = {'water': ' Khách nói chưa dính nước: soi tem báo nước trong máy rồi cho khách xem trước khi báo giá.',
           'warranty': ' Có phiếu bảo hành: tra sổ, so tình trạng máy với phiếu cũ, chốt đúng lỗi rồi mới quyết bảo hành hay tính tiền.',
           'rush': ' Việc gấp: đo ít mà trúng, làm liền tay để kịp giờ hẹn.',
           'privacy': ' Khách nhờ chuyện dữ liệu: nghĩ xem dữ liệu đó là của ai.',
           'bargain': ' Ví mỏng: đồ tháo máy rẻ nhưng phải cắm thử trước khi lắp.'}.get(case, '')
    return ('Hỏi khách → ghi phiếu nhận (tình trạng, phụ kiện, quyền dữ liệu) → đo kiểm loại dần giả thuyết → chốt lỗi → '
            'báo giá, chờ khách gật → làm an toàn, mở máy → thay/sửa → lắp lại → chạy thử → ghi bảo hành → bàn giao. '
            'Thiếu đồ thì đặt riêng cho máy và hẹn khách để máy lại tiệm — hẹn ngày nào giữ ngày đó.' + tip)


def content() -> dict:
    return dict(
        devices={k: dict(v) for k, v in DEVICES.items()},
        faults={dev: [dict(id=f['id'], name=f['name'], parts=f['parts'], supplies=f['supplies'], mult=f['mult']) for f in rows]
                for dev, rows in FAULTS.items()},
        extras={dev: [dict(id=f['id'], name=f['name'], parts=f['parts'], supplies=f['supplies'], mult=f['mult']) for f in rows]
                for dev, rows in EXTRAS.items()},
        tests={dev: [dict(id=x['id'], name=x['name'], emoji=x['emoji'], mode=x['mode'], consent=x['consent']) for x in rows]
               for dev, rows in TESTS.items()},
        marks={k: dict(emoji=v[0], label=v[1]) for k, v in MARKS.items()},
        accessories={k: dict(emoji=v[0], label=v[1]) for k, v in ACCESSORIES.items()},
        safety={k: dict(emoji=v[0], label=v[1]) for k, v in SAFETY.items()},
        grades=GRADES, warranty=list(WARRANTY), check_fee=CHECK_FEE, quote_rounds=QUOTE_ROUNDS,
        data_devices=list(DATA_DEVICES), cases=CASES, data_fee=DATA_FEE,
        today=[dict(id=x['id'], title=x['title'], emoji=x['emoji'], text=x['text']) for x in TODAY],
        sources={k: dict(name=v['name'], emoji=v['emoji'], ship=v['ship'], grades=list(v['grades']), rule=v['rule'])
                 for k, v in SOURCES.items()},
        source_of=SOURCE_OF, promise_days=list(PROMISE_DAYS), shelf_max=SHELF_MAX, trust_names=list(TRUST_NAMES),
        trust_stretch=TRUST_STRETCH, habits={kit.npc_id(ID, i): h for i, h in REGULARS.items()},
        tools={k: dict(v) for k, v in TOOLS.items()}, tool_costs=dict(tip=TIP_COST, meter=METER_COST),
        tip_clean=dict(add=TIP_CLEAN, max=TIP_CLEAN_MAX), causes=CAUSES,
    )


# ------------------------------------------------------------------------------ surprises at the counter
DESK = [
    dict(id='used_lot', title='Mối đồ tháo máy chào hàng', emoji='📦', npc=6, min_day=2, tone='gentle', weight=2,
         text='Lâm Linh Kiện mở cốp xe: “Lô màn với pin tháo máy, có hóa đơn thanh lý đàng hoàng. Tiệm lấy không? Hàng hên xui, thử rồi hãy lắp.”',
         options=[dict(id='buy', label='Lấy cả lô: 2 màn + 3 pin', hint='20 xu', good=True,
                       effects=dict(money=-20, stock=dict(screen_u=2, battery_u=3)),
                       outcome='Kệ đồ tháo máy đầy lên. Khách ví mỏng sẽ có lựa chọn rẻ — nhớ cắm thử từng món.'),
                  dict(id='haggle', label='Trả giá xuống 14 xu', hint='Hên xui',
                       luck=dict(p=0.5, win=dict(effects=dict(money=-14, stock=dict(screen_u=2, battery_u=3)), good=True,
                                                 outcome='Lâm cười khà: “Tiệm này mặc cả giỏi!” — lô hàng về với giá mềm.'),
                                 lose=dict(outcome='Lâm phẩy tay: “Thôi để mối khác.” Xe nổ máy đi mất.', good=None))),
                  dict(id='skip', label='Thôi, chưa cần', hint='Không tốn gì', outcome='Lâm gật đầu, hẹn tuần sau ghé.')],
         default='skip'),
    dict(id='shady_lot', title='Màn “bao đẹp” không hóa đơn', emoji='🕶️', npc=6, min_day=3, tone='tense', no_mark='no_invoice',
         text='Một người lạ chìa túi màn hình: “Rẻ một nửa, khỏi hóa đơn cho nhẹ. Bán ghi hàng tương thích ai biết.”',
         options=[dict(id='take', label='Lấy 2 tấm cho rẻ', hint='12 xu, không hóa đơn', good=False,
                       effects=dict(money=-12, stock=dict(screen_c=2), mark='no_invoice'),
                       outcome='Được hai tấm màn rẻ. Trong sổ nhập hàng có một dòng trống không hóa đơn…'),
                  dict(id='refuse', label='Chỉ nhập hàng có hóa đơn', hint='An toàn', good=True, effects=dict(xp=4),
                       outcome='Người lạ nhún vai bỏ đi. Sổ nhập hàng của tiệm vẫn sạch sẽ.')],
         default='refuse'),
    dict(id='inspect_ok', title='Đoàn kiểm tra hóa đơn linh kiện', emoji='📋', npc=6, min_day=3, tone='tense', no_mark='no_invoice',
         text='Đoàn quản lý thị trường ghé tiệm: “Cho xem hóa đơn nhập linh kiện và sổ bảo hành.”',
         options=[dict(id='show', label='Mở sổ nhập hàng, đưa hóa đơn', hint='Sổ sạch', good=True, effects=dict(xp=10),
                       outcome='Đoàn đối chiếu từng dòng, ký biên bản “đạt”, còn dặn tiệm giữ thói quen tốt.'),
                  dict(id='stall', label='Hẹn mai mới đưa, đang bận', hint='Rủi ro', good=False,
                       luck=dict(p=0.4, win=dict(outcome='Đoàn đồng ý quay lại sau, dặn chuẩn bị đầy đủ.', good=None),
                                 lose=dict(effects=dict(money=-15), outcome='Đoàn lập biên bản “không hợp tác”: phạt 15 xu.', good=False)))],
         default='show'),
    dict(id='inspect_bad', title='Đoàn kiểm tra hỏi lô màn không hóa đơn', emoji='🚨', npc=6, min_day=3, tone='tense', need_mark='no_invoice',
         weight=3,
         text='Đoàn quản lý thị trường lật sổ nhập hàng, chỉ vào dòng trống: “Hai tấm màn này nhập từ đâu? Hóa đơn đâu?”',
         options=[dict(id='pay', label='Nhận lỗi, nộp phạt', hint='30 xu', good=None,
                       effects=dict(money=-30, unmark='no_invoice'), outcome='Nộp phạt 30 xu, ký biên bản. Bài học đắt giá về nguồn hàng.'),
                  dict(id='surrender', label='Giao nộp lô màn, phạt nhẹ', hint='10 xu + mất 2 màn', good=None,
                       effects=dict(money=-10, stock=dict(screen_c=-2), unmark='no_invoice'),
                       outcome='Tiệm giao nộp hai tấm màn không rõ nguồn gốc, bị phạt nhẹ vì thành khẩn.'),
                  dict(id='argue', label='Cãi là hàng tồn từ lâu', hint='Hên xui', good=False,
                       luck=dict(p=0.25, win=dict(effects=dict(unmark='no_invoice'), outcome='Đoàn tạm tin, dặn bổ sung giấy tờ trong tuần.', good=None),
                                 lose=dict(effects=dict(money=-45, unmark='no_invoice',
                                                        review=[1, 'Tiệm sửa đồ đầu hẻm bị phạt vì bán linh kiện không rõ nguồn gốc. Tránh xa!']),
                                           outcome='Nói dối bị phát hiện: phạt 45 xu, chuyện lan khắp phố.', good=False)))],
         default='pay'),
    dict(id='outage', title='Cúp điện cả dãy phố', emoji='🔌', npc=1, min_day=2, tone='tense', at='any',
         text='Phụt một cái, cả dãy phố tối om. Máy hàn nguội dần, khách đang chờ nhìn nhau.',
         options=[dict(id='generator', label='Thuê máy phát của nhà bên', hint='8 xu', good=True, effects=dict(money=-8),
                       outcome='Máy phát nổ giòn, bàn thợ sáng đèn trở lại. Khách không phải chờ lâu.'),
                  dict(id='wait', label='Chờ có điện, pha trà mời khách', hint='Khách sốt ruột', good=None, effects=dict(patience=-15),
                       outcome='Nửa tiếng sau mới có điện. Khách uống trà nhưng ai cũng sốt ruột.')],
         default='wait'),
    dict(id='kid_toy', title='Bé Bin ôm xe đồ chơi gãy bánh', emoji='🧸', npc=1, min_day=2, tone='gentle',
         text='Cháu nội ông Bảy rụt rè đặt chiếc xe đồ chơi lên quầy, bánh xe gãy lìa: “Tiệm sửa được không ạ?”',
         options=[dict(id='free', label='Dán lại miễn phí', hint='Tốn 1 xu keo', good=True,
                       effects=dict(money=-1, review=[5, 'Tiệm sửa xe đồ chơi cho cháu tôi mà không lấy tiền. Thằng bé cười cả buổi.']),
                       outcome='Bé Bin ôm xe chạy ra cửa, ông Bảy đứng ngoài cười móm mém.'),
                  dict(id='charge', label='Sửa, lấy 4 xu công', hint='+4 xu', good=None, effects=dict(money=4),
                       outcome='Ông Bảy trả tiền cho cháu. Xe chạy lại, bé vui, tiệm có thêm chút công.'),
                  dict(id='later', label='Hẹn khi rảnh', hint='Không tốn gì', good=None,
                       outcome='Bé gật đầu, ôm xe về. Chiếc xe nằm trong hộp chờ.')],
         default='later'),
    dict(id='fee_review', title='Review 1★: “Mất 10 xu oan”', emoji='⭐', npc=5, min_day=3, tone='tense',
         text='Bà Tám đăng review 1 sao: “Mang máy tới xem rồi không sửa, tiệm vẫn thu 10 xu. Báo giá một đằng lấy tiền một nẻo!”',
         options=[dict(id='explain', label='Trả lời, chỉ bảng giá dán ở quầy', hint='Hên xui',
                       luck=dict(p=0.65, win=dict(effects=dict(review=[4, 'Đọc bảng giá dán ở quầy mới hiểu phí kiểm tra. Tiệm trả lời lịch sự, bà sửa lại đánh giá.']),
                                                 outcome='Bà Tám đọc lại bảng giá, sửa review lên 4 sao.', good=True),
                                 lose=dict(effects=dict(review=[2, 'Giải thích thì giải thích, bà vẫn thấy mất 10 xu oan.']),
                                           outcome='Bà Tám vẫn chưa nguôi, chỉ nâng lên 2 sao.', good=None))),
                  dict(id='refund', label='Hoàn phí kiểm tra, xin lỗi vì chưa nói rõ', hint='10 xu', good=True,
                       effects=dict(money=-10, review=[4, 'Tiệm hoàn lại phí kiểm tra, còn xin lỗi vì chưa nói rõ. Biết điều.']),
                       outcome='Bà Tám nhận lại 10 xu, còn khoe với hàng xóm là tiệm “biết điều”.'),
                  dict(id='argue', label='Đáp trả: “Bà không đọc bảng giá à?”', hint='Nóng', good=False,
                       effects=dict(review=[1, 'Chủ tiệm cãi tay đôi với khách trên mạng. Hết muốn quay lại.']),
                       outcome='Cuộc cãi nhau dưới review thu hút cả phố vào xem. Không ai nhớ ai đúng.')],
         default='explain'),
    dict(id='swollen', title='Viên pin trên kệ phồng lên', emoji='🔋', npc=6, min_day=3, tone='tense',
         text='Lúc kiểm kệ, một viên pin điện thoại tương thích phồng vênh cả vỏ.',
         options=[dict(id='isolate', label='Cho vào thùng cát, ghi hao hụt', hint='Mất 1 pin', good=True,
                       effects=dict(stock=dict(battery_c=-1)), outcome='Viên pin nằm yên trong thùng cát. Kệ an toàn.'),
                  dict(id='return', label='Gọi Lâm đổi trả', hint='Hên xui',
                       luck=dict(p=0.6, win=dict(effects=dict(stock=dict(battery_c=-1), money=9), good=True,
                                                 outcome='Lâm nhận lại, hoàn 9 xu: “Lô này lỗi, cảm ơn tiệm báo.”'),
                                 lose=dict(effects=dict(stock=dict(battery_c=-1)), good=None,
                                           outcome='Lâm bảo quá hạn đổi trả. Pin vào thùng cát, tiệm chịu mất.'))),
                  dict(id='keep', label='Để lại, chắc còn dùng được', hint='Rủi ro', good=False, effects=dict(mark='risky_battery'),
                       outcome='Viên pin phồng vẫn nằm trên kệ, lẫn với pin tốt…')],
         default='isolate'),
    dict(id='hot_battery', title='Khách báo pin mới thay nóng ran', emoji='🔥', npc=0, min_day=4, tone='tense', need_mark='risky_battery',
         weight=3, text='Chị Diệp quay lại, tay cầm điện thoại nóng ran: “Pin tiệm mới thay hôm trước, sạc có chút mà nóng muốn bỏng tay!”',
         options=[dict(id='replace', label='Thay pin mới miễn phí, xin lỗi', hint='16 xu', good=True,
                       effects=dict(money=-16, unmark='risky_battery', review=[4, 'Pin có vấn đề nhưng tiệm nhận lỗi, thay ngay pin mới. Đáng tin.']),
                       outcome='Tiệm thay pin mới, bỏ viên cũ vào thùng cát. Chị Diệp yên tâm ra về.'),
                  dict(id='deny', label='Bảo tại chị sạc qua đêm', hint='Chối', good=False,
                       effects=dict(unmark='risky_battery', review=[1, 'Pin tiệm thay nóng ran, tiệm còn đổ lỗi cho khách. Nguy hiểm!']),
                       outcome='Chị Diệp bỏ đi, tối đó đăng bài cảnh báo cả nhóm cư dân.')],
         default='deny'),
    dict(id='price_hike', title='Giá linh kiện sắp tăng', emoji='📈', npc=6, min_day=4, tone='gentle',
         text='Lâm nhắn: “Tuần sau hàng về giá tăng. Hôm nay tiệm gom thì bên mình để giá cũ.”',
         options=[dict(id='stock_up', label='Gom trước một mớ', hint='30 xu', good=True,
                       effects=dict(money=-30, stock=dict(screen_c=1, battery_c=2, cap_c=3, tube=2, brake=2)),
                       outcome='Kệ đầy ắp linh kiện giá cũ. Két mỏng đi một chút.'),
                  dict(id='wait', label='Giữ tiền mặt, mua khi cần', hint='Không tốn gì', good=None,
                       outcome='Tiệm giữ tiền mặt. Mua khi cần, không lo đọng vốn.')],
         default='wait'),
    dict(id='lost_phone', title='Điện thoại ai bỏ quên trên ghế chờ', emoji='📱', npc=0, min_day=2, tone='gentle',
         text='Dọn ghế chờ, bạn thấy một chiếc điện thoại lạ kẹt dưới đệm, màn hình khóa sáng lên vài tin nhắn.',
         options=[dict(id='keep', label='Cất vào tủ, ghi sổ đồ thất lạc', hint='Chờ chủ',
                       luck=dict(p=0.8, win=dict(effects=dict(review=[5, 'Bỏ quên điện thoại ở tiệm, tiệm cất kỹ, gọi tôi tới nhận. Cảm ơn nhiều!']),
                                                 outcome='Chiều đó chị Diệp hớt hải quay lại — máy của chị. Chị cảm ơn rối rít.', good=True),
                                 lose=dict(outcome='Chưa ai tới nhận. Máy nằm trong tủ, sổ đồ thất lạc ghi rõ ngày giờ.', good=True))),
                  dict(id='unlock', label='Mở khóa đọc tin nhắn tìm chủ', hint='Xâm phạm', good=False,
                       effects=dict(review=[2, 'Để quên máy ở tiệm, tới nhận thì biết tiệm đã tự mở máy đọc tin nhắn. Ghê!']),
                       outcome='Chủ máy tới nhận, biết máy bị mở, mặt lạnh tanh.')],
         default='keep'),
    dict(id='leak_found', title='Chủ máy phát hiện dữ liệu bị chép', emoji='🔓', npc=0, min_day=4, tone='tense', need_mark='leak',
         weight=4, text='Một người đàn ông đứng trước quầy, giọng run run: “Tiệm chép tin nhắn máy tôi đưa cho người khác đúng không?”',
         options=[dict(id='apologize', label='Nhận lỗi, xin lỗi, bồi thường', hint='20 xu', good=None,
                       effects=dict(money=-20, unmark='leak', review=[2, 'Tiệm chép tin nhắn máy tôi cho người khác. Xin lỗi rồi nhưng tôi không quên.']),
                       outcome='Tiệm xin lỗi và bồi thường. Uy tín về chuyện dữ liệu sứt một mảng.'),
                  dict(id='deny', label='Chối: “Tiệm không biết gì”', hint='Chối', good=False,
                       effects=dict(unmark='leak', review=[1, 'Tiệm sửa điện thoại tiếp tay đọc trộm tin nhắn, còn chối. Tránh xa!']),
                       outcome='Ông ấy bỏ đi, tối đó bài cảnh báo lan khắp nhóm cư dân.')],
         default='deny'),
    dict(id='roof_leak', title='Mái tôn dột ngay kệ linh kiện', emoji='☔', npc=4, min_day=2, tone='tense', mods=('rain',), weight=3,
         text='Mưa quất mạnh, nước nhỏ tong tong ngay trên kệ màn hình và pin.',
         options=[dict(id='tarp', label='Chạy mua tấm bạt che', hint='5 xu', good=True, effects=dict(money=-5),
                       outcome='Tấm bạt xanh căng lên, kệ linh kiện khô ráo.'),
                  dict(id='move', label='Bê kệ sang góc khác', hint='Khách chờ lâu hơn', good=None, effects=dict(patience=-8),
                       outcome='Kệ được dời đi kịp, nhưng khách phải chờ thêm một lúc.'),
                  dict(id='ignore', label='Kệ, mưa chút rồi tạnh', hint='Rủi ro', good=False,
                       effects=dict(stock=dict(screen_c=-1, battery_c=-1)), outcome='Nước ngấm vào hộp — một màn, một pin hỏng luôn.')],
         default='ignore'),
    dict(id='apprentice_exam', title='Tí xin về sớm ôn thi nghề', emoji='📘', npc=1, min_day=3, tone='gentle',
         text='Tí gãi đầu: “Mai em thi chứng chỉ điện dân dụng, cho em về sớm ôn bài được không ạ?”',
         options=[dict(id='let_go', label='Cho về, dặn thi tốt', hint='Làm một mình, khách chờ lâu hơn', good=True,
                       effects=dict(patience=-6, xp=6), outcome='Tí cảm ơn rối rít. Tối đó bạn làm một mình, hơi mệt nhưng vui.'),
                  dict(id='quiz', label='Giữ lại, vừa làm vừa kèm bài', hint='Hên xui',
                       luck=dict(p=0.5, win=dict(effects=dict(xp=10), outcome='Vừa sửa máy vừa ôn, Tí hiểu bài hơn đọc sách.', good=True),
                                 lose=dict(effects=dict(patience=-8), outcome='Tí lơ đễnh, làm rơi ốc lung tung — khách chờ lâu hơn.', good=None))),
                  dict(id='no', label='Không cho, tiệm đang đông', hint='Tí buồn', good=False,
                       outcome='Tí ở lại, mắt cứ dán vào cuốn sách dưới gầm bàn.')],
         default='no'),
]
DESK_INDEX = {x['id']: x for x in DESK}


SITUATIONS = [
    dict(id='RP-S01', title='Mở khóa giùm cái điện thoại “của bạn gái”', npc=0, tone='tense', min_day=1,
         opening='Một thanh niên đội mũ lưỡi trai đặt điện thoại lên quầy: “Máy của bạn gái em, quên mật khẩu. Tiệm mở khóa giùm, em trả gấp đôi.”',
         swap='Bạn là chị Diệp — hôm qua vừa mất điện thoại ở trạm xe buýt, đang nhờ người quen dò các tiệm sửa.',
         facts=[dict(id='lock', title='Màn hình khóa', source='Điện thoại', text='Màn hình khóa hiện dòng “Máy bị mất — liên hệ D…p” kèm số điện thoại khác số của cậu thanh niên.'),
                dict(id='papers', title='Giấy tờ', source='Cậu thanh niên', text='Không có hóa đơn, không có hộp máy, không gọi được “bạn gái” để xác nhận.'),
                dict(id='rule', title='Nội quy tiệm', source='Bảng dán ở quầy', text='“Tiệm chỉ mở khóa khi chủ máy có mặt, xuất trình giấy tờ hoặc hóa đơn.”')],
         options=[dict(id='verify', label='Từ chối mở khóa, mời chủ máy tới cùng giấy tờ; giữ bình tĩnh, gọi số trên màn hình khóa', requires=['lock', 'rule'], quality='good', stars=5,
                       review='Tiệm chú Tư giữ nguyên tắc, nhờ vậy tôi lấy lại được điện thoại. Cảm ơn tiệm nhiều lắm!',
                       outcome='Cậu thanh niên lầm bầm bỏ đi, để quên luôn cái máy. Số trên màn hình khóa là của chị Diệp — chiều đó chị tới nhận lại máy, mắt đỏ hoe.',
                       perspectives=[dict(who='Chị Diệp', emoji='🙏', text='Trong máy có ảnh con gái hồi nhỏ. Tiệm mà mở khóa là tôi mất trắng.'),
                                     dict(who='Cậu thanh niên', emoji='🧢', text='Tưởng tiệm nhỏ dễ dụ, ai ngờ có nội quy rõ ràng quá.'),
                                     dict(who='Thợ học việc Tí', emoji='🧑‍🔧', text='Giờ em mới hiểu vì sao phải dán cái bảng nội quy đó.')]),
                  dict(id='refuse', label='Chỉ nói “tiệm không làm” rồi trả máy cho cậu ta', requires=['papers'], quality='ok',
                       outcome='Tiệm không dính vào chuyện xấu, nhưng cái máy lại theo cậu ta đi sang tiệm khác.',
                       perspectives=[dict(who='Chị Diệp', emoji='😢', text='Giá mà tiệm giữ lại hoặc gọi cho tôi thì tốt biết mấy.'),
                                     dict(who='Chú Tư', emoji='🤔', text='Mình không làm sai, nhưng cũng chưa làm hết phần đúng.')]),
                  dict(id='unlock', label='Nhận gấp đôi tiền, bẻ khóa luôn', quality='bad', reward=30, stars=1,
                       review='Tiệm này nhận mở khóa máy người khác. Máy tôi bị bán qua tay chỉ sau một buổi. Cảnh báo cả phố!',
                       outcome='Vài hôm sau công an phường tới hỏi về chiếc máy trộm đã được “làm sạch” tại tiệm. Tiền công thành tiền mang tiếng.',
                       perspectives=[dict(who='Chị Diệp', emoji='😠', text='Ảnh, tin nhắn, tài khoản… tất cả mất vì một lần mở khóa.'),
                                     dict(who='Hàng xóm', emoji='👀', text='Từ đó ai đưa máy vào tiệm cũng ngần ngừ.')])],
         lesson='Không mở khóa, không xóa dữ liệu khi chưa chứng minh được ai là chủ máy — tiền công không đáng bằng uy tín.'),
    dict(id='RP-S02', title='Cục pin phồng đội cả màn hình', npc=5, tone='tense', min_day=1,
         opening='Bà Tám đưa điện thoại, màn hình bị đẩy vênh lên: “Pin nó hơi phồng thôi, cháu ép màn xuống dán lại giùm, cuối tháng tôi mới thay pin.”',
         swap='Bạn là bà Tám: tiền trọ chưa thu đủ, thay pin lúc này thấy tiếc.',
         facts=[dict(id='swell', title='Nhìn cạnh máy', source='Điện thoại', text='Khe hở cạnh máy khoảng 4 mm, mặt lưng ấm dù máy đang tắt.'),
                dict(id='sand', title='Góc an toàn', source='Tiệm', text='Tiệm có thùng cát và hộp kim loại chống cháy để cô lập pin hỏng.'),
                dict(id='habit', title='Thói quen sạc', source='Bà Tám', text='Bà hay cắm sạc qua đêm cạnh gối.')],
         options=[dict(id='isolate', label='Tắt máy, tháo pin ngay vào thùng cát; giải thích nguy cơ cháy, cho bà mượn pin tạm giá vốn', requires=['swell', 'sand'], cost=8, quality='good', stars=5,
                       review='Thợ ở tiệm cẩn thận, giải thích dễ hiểu, còn cho mượn pin tạm. Tối nay tôi ngủ yên rồi.',
                       outcome='Pin cũ được cô lập an toàn. Bà Tám dùng pin tạm, cuối tháng quay lại thay pin chính hãng.',
                       perspectives=[dict(who='Bà Tám', emoji='👵', text='Nghe tới cháy nổ cạnh gối là tôi sợ thật, may mà tiệm nói.'),
                                     dict(who='Thợ học việc Tí', emoji='🧑‍🔧', text='Lần đầu em tận mắt thấy pin phồng, chú Tư làm từng bước chậm rãi.'),
                                     dict(who='Hàng xóm cạnh tiệm', emoji='🏠', text='Tiệm có thùng cát riêng, tụi tôi yên tâm hơn.')]),
                  dict(id='press', label='Chiều khách: ép màn, dán keo lại', quality='bad', reward=10, stars=2,
                       review='Dán được hai hôm thì màn lại bung, máy nóng ran. Sợ quá!',
                       outcome='Hai hôm sau máy nóng bốc mùi, bà Tám hoảng hốt mang ra — may chưa bắt lửa.',
                       perspectives=[dict(who='Bà Tám', emoji='😨', text='Nó nóng như cục than trong tay tôi.'),
                                     dict(who='Chú Tư', emoji='😓', text='Chiều khách kiểu đó là đánh cược tính mạng người ta.')]),
                  dict(id='refuse', label='Từ chối đụng vào, bảo bà mang về', requires=['swell'], quality='ok',
                       outcome='Tiệm an toàn, nhưng bà Tám mang cục pin phồng về cắm sạc tiếp cạnh gối.',
                       perspectives=[dict(who='Bà Tám', emoji='😒', text='Không sửa thì thôi, tôi về sạc tiếp.'),
                                     dict(who='Chú Tư', emoji='😟', text='Đẩy nguy hiểm ra khỏi tiệm đâu có nghĩa là hết nguy hiểm.')])],
         lesson='Pin phồng là chuyện an toàn cháy nổ: cô lập ngay và nói rõ nguy cơ, đừng chiều khách “dán tạm”.'),
    dict(id='RP-S03', title='Khôi phục ảnh và những bức ảnh riêng tư', npc=0, tone='gentle', min_day=2,
         opening='Chị Diệp nhờ lấy lại ảnh từ chiếc máy cũ vỡ màn. Lúc chép dữ liệu, thư mục ảnh tự mở ra — có cả những tấm ảnh rất riêng tư.',
         facts=[dict(id='consent', title='Phiếu nhận máy', source='Phiếu', text='Chị đồng ý cho tiệm chép toàn bộ thư mục ảnh sang ổ của chị, không ghi cho phép xem.'),
                dict(id='apprentice', title='Tí đang đứng cạnh', source='Quầy', text='Tí tò mò ngó sang màn hình máy tính.'),
                dict(id='drive', title='Ổ cứng của khách', source='Chị Diệp', text='Chị mang theo ổ cứng riêng và muốn nhận lại luôn trong ngày.')],
         options=[dict(id='blind', label='Tắt xem trước, chép thẳng sang ổ của chị, mời chị tự kiểm tra; xóa bản tạm trước mặt chị', requires=['consent', 'drive'], quality='good', stars=5,
                       review='Tiệm chép ảnh mà không xem, còn xóa bản tạm trước mặt tôi. Đây mới là tiệm đáng tin.',
                       outcome='Chị Diệp tự mở kiểm tra, nhận ổ cứng và cảm ơn vì được tôn trọng.',
                       perspectives=[dict(who='Chị Diệp', emoji='🔐', text='Tôi hồi hộp suốt, tới lúc thấy xóa bản tạm mới thở ra.'),
                                     dict(who='Thợ học việc Tí', emoji='🙈', text='Chú Tư bảo em quay đi — dữ liệu khách không phải để tò mò.')]),
                  dict(id='peek', label='Cho Tí xem “học hỏi” cách khôi phục, lướt qua vài ảnh', quality='bad', stars=1,
                       review='Tôi nhìn thấy nhân viên cười cười khi xem máy tôi. Không bao giờ quay lại.',
                       outcome='Chị Diệp bắt gặp ánh mắt của Tí, lặng lẽ lấy máy về, tối đó đăng bài cảnh báo.',
                       perspectives=[dict(who='Chị Diệp', emoji='😡', text='Cảm giác như bị lục túi xách.'),
                                     dict(who='Tí', emoji='😳', text='Em chỉ tò mò chút thôi… giờ em thấy xấu hổ quá.')]),
                  dict(id='copy', label='Giữ thêm một bản trên máy tiệm “phòng khi khách làm mất”', quality='bad',
                       outcome='Bản sao nằm trong máy tiệm không ai quản — một rủi ro rò rỉ dữ liệu treo lơ lửng.',
                       perspectives=[dict(who='Chú Tư', emoji='🤦', text='Giữ hộ dữ liệu khi khách không nhờ là tự ôm rủi ro vào người.'),
                                     dict(who='Chị Diệp', emoji='❓', text='Tôi đâu có nhờ giữ bản sao nào?')])],
         lesson='Được phép chép không có nghĩa là được phép xem: làm đúng phạm vi đồng ý, xóa bản tạm trước mặt khách.'),
    dict(id='RP-S04', title='Bảo hành chiếc máy “không hề vô nước”', npc=5, tone='tense', min_day=3,
         opening='Bà Tám mang lại chiếc điện thoại mới thay màn hai tuần: “Còn bảo hành 30 ngày! Máy chết đứng, tôi không làm rơi, không làm ướt gì hết!”',
         facts=[dict(id='sticker', title='Tem báo nước', source='Bên trong máy', text='Tem báo nước chuyển đỏ, chân sạc có vệt gỉ xanh.'),
                dict(id='intake', title='Phiếu nhận máy lần trước', source='Sổ tiệm', text='Phiếu có ảnh chụp tem báo nước còn trắng lúc nhận máy.'),
                dict(id='rain', title='Chuyện hôm qua', source='Hàng xóm', text='Hôm qua mưa lớn, bà Tám chạy xe về, túi áo ướt sũng.')],
         options=[dict(id='evidence', label='Cho bà xem ảnh phiếu cũ và tem hiện tại, giải thích nhẹ nhàng; đề nghị sửa ngoài bảo hành, giảm công', requires=['sticker', 'intake'], cost=6, quality='good', stars=4,
                       review='Tiệm có ảnh chụp đàng hoàng, tôi hết cãi. Được giảm tiền công, cũng biết điều.',
                       outcome='Bà Tám nhìn hai tấm ảnh, im một lúc rồi nhớ ra cơn mưa. Bà đồng ý sửa, tiệm bớt tiền công.',
                       perspectives=[dict(who='Bà Tám', emoji='😶', text='Tôi quên béng vụ mưa. Có ảnh rõ ràng thì tôi chịu.'),
                                     dict(who='Chú Tư', emoji='📸', text='Cái ảnh chụp lúc nhận máy hôm đó đáng giá hơn trăm câu cãi.')]),
                  dict(id='free', label='Sửa miễn phí cho êm chuyện', cost=25, quality='ok', stars=5,
                       review='Tiệm bảo hành nhanh, không hỏi han gì. Tốt!',
                       outcome='Bà Tám vui, nhưng tiệm gánh lỗi không phải của mình, và bà nghĩ máy hỏng là do tiệm.',
                       perspectives=[dict(who='Bà Tám', emoji='😊', text='Thấy chưa, tôi nói máy lỗi do tiệm mà.'),
                                     dict(who='Thợ học việc Tí', emoji='🤨', text='Vậy phiếu nhận máy chụp ảnh để làm gì hả chú?')]),
                  dict(id='accuse', label='Nói lớn: “Bà làm vô nước rồi còn chối!”', quality='bad', stars=1,
                       review='Chủ tiệm la khách như la con nít. Đừng tới!',
                       outcome='Cả dãy nhà trọ nghe tiếng cãi. Đúng sai chưa ai hiểu, chỉ nhớ tiệm to tiếng.',
                       perspectives=[dict(who='Bà Tám', emoji='😤', text='Có sai thì cũng không ai muốn bị quát trước bàn dân thiên hạ.'),
                                     dict(who='Khách đang chờ', emoji='😬', text='Tôi lặng lẽ cầm máy mình đi tiệm khác.')])],
         lesson='Phiếu nhận máy có ảnh là “trí nhớ” của tiệm: dùng nó để giải thích, không để thắng cãi.'),
    dict(id='RP-S05', title='Trả giá kiểu “đầu hẻm rẻ hơn 20 xu”', npc=5, tone='gentle', min_day=2,
         opening='Bà Tám nghe báo giá thay màn 68 xu liền phẩy tay: “Tiệm đầu hẻm có 48 thôi! Cháu lấy 48, mà vẫn phải bảo hành 90 ngày như hàng hãng nhé.”',
         facts=[dict(id='quote', title='Chi tiết báo giá', source='Phiếu báo giá', text='Màn tương thích 38 xu + công 30 xu. Màn chính hãng 62 xu + công 30 xu.'),
                dict(id='other', title='Tiệm đầu hẻm', source='Anh Khoa kể', text='Tiệm đầu hẻm dùng màn tháo máy cũ, bảo hành “miệng” 7 ngày.')],
         options=[dict(id='explain', label='Giải thích từng dòng báo giá, bớt 3 xu tiền công; bảo hành đúng 30 ngày của màn tương thích', requires=['quote'], cost=3, quality='good', stars=4,
                       review='Thợ ở tiệm giải thích rõ từng đồng, bớt chút đỉnh. Bảo hành đúng như giấy.',
                       outcome='Bà Tám gật gù, sửa ở tiệm. Không ai phải nói dối về loại màn.',
                       perspectives=[dict(who='Bà Tám', emoji='🧾', text='Có giấy tờ rõ ràng, tôi trả giá cho vui thôi.'),
                                     dict(who='Chú Tư', emoji='🙂', text='Giảm chút công được, giảm sự thật thì không.')]),
                  dict(id='fake', label='Đồng ý 48 xu nhưng lén dùng màn tháo máy, ghi “chính hãng”', quality='bad', reward=10, stars=1,
                       review='Màn ghi chính hãng mà hai tuần đã ám vàng. Lừa đảo!',
                       outcome='Màn ám vàng sau hai tuần, bà Tám mang tới thợ khác kiểm tra và phát hiện màn tháo máy.',
                       perspectives=[dict(who='Bà Tám', emoji='🤬', text='Tôi trả giá chứ đâu có bảo tiệm lừa tôi.'),
                                     dict(who='Lâm Linh Kiện', emoji='📦', text='Hàng tháo máy thì phải nói là hàng tháo máy chứ.')]),
                  dict(id='firm', label='Giữ giá, không bớt đồng nào', requires=['quote'], quality='ok', stars=3,
                       review='Giá thì đúng, mỗi tội cứng nhắc quá.',
                       outcome='Bà Tám vẫn sửa nhưng về kể “tiệm đó khó tính”.',
                       perspectives=[dict(who='Bà Tám', emoji='😑', text='Mua bán mà không cho trả giá thì mất vui.'),
                                     dict(who='Chú Tư', emoji='🧮', text='Giá đúng rồi, nhưng nói thêm một câu mềm mỏng thì khách ở lại vui hơn.')])],
         lesson='Trả giá được, đánh tráo linh kiện thì không: bớt công chứ không bớt sự thật.'),
    dict(id='RP-S06', title='Lô màn “zin bóc máy” giá nửa tiền', npc=6, tone='tense', min_day=3,
         opening='Lâm Linh Kiện mở cốp xe: “Màn zin bóc máy, rẻ một nửa, không hóa đơn. Tiệm lấy chục cái, bán ghi hàng hãng là lời to.”',
         facts=[dict(id='invoice', title='Giấy tờ', source='Lâm', text='Không hóa đơn, không nguồn gốc, nói “hàng máy thanh lý”.'),
                dict(id='serial', title='Soi mặt sau', source='Màn hình', text='Vài tấm còn dán tem kiểm kê của một cửa hàng điện thoại khác.'),
                dict(id='margin', title='Lợi nhuận', source='Sổ tiệm', text='Nếu bán như hàng hãng, mỗi tấm lời thêm khoảng 30 xu.')],
         options=[dict(id='decline', label='Từ chối, chỉ nhập hàng có hóa đơn từ nhà phân phối', requires=['invoice'], quality='good',
                       outcome='Lâm nhún vai đi mối khác. Tiệm giữ nguồn hàng sạch, giá không rẻ nhất nhưng ngủ ngon.',
                       perspectives=[dict(who='Lâm Linh Kiện', emoji='🤷', text='Tiệm này khó, nhưng mối có hóa đơn thì tôi vẫn giao.'),
                                     dict(who='Chú Tư', emoji='😌', text='Hàng không rõ gốc có khi là máy của ai đó bị giật.')]),
                  dict(id='honest', label='Mua vài tấm, bán đúng tên “màn tháo máy”, bảo hành 7 ngày', requires=['serial'], cost=20, quality='ok',
                       outcome='Khách biết mình mua gì, nhưng tiệm vẫn có thể đang tiêu thụ hàng từ máy gian.',
                       perspectives=[dict(who='Khách mua màn rẻ', emoji='🙂', text='Rẻ, nói rõ, tôi chịu.'),
                                     dict(who='Chủ tiệm bị mất trộm', emoji='😔', text='Tem kiểm kê đó là của tiệm tôi…')]),
                  dict(id='resell', label='Lấy cả chục, dán nhãn chính hãng bán giá hãng', cost=40, reward=40, quality='bad', stars=1,
                       review='Mua màn “chính hãng” ở tiệm này, hóa ra là màn tháo máy trộm. Tránh xa!',
                       outcome='Một khách mang màn đi đối chiếu tem kiểm kê. Chuyện lan khắp phố.',
                       perspectives=[dict(who='Khách', emoji='😠', text='Tôi trả tiền hàng hãng cho một tấm màn có thể là đồ gian.'),
                                     dict(who='Thợ học việc Tí', emoji='😟', text='Em không muốn học nghề kiểu này.')])],
         lesson='Linh kiện rẻ bất thường, không hóa đơn là dấu hiệu đỏ: nguồn hàng sạch là một phần của tay nghề.'),
    dict(id='RP-S07', title='Tí làm rách cáp màn của khách', npc=0, tone='gentle', min_day=2,
         opening='Đang thay màn cho chị Diệp, Tí run tay kéo mạnh — cáp nối màn rách một đường. Cậu đứng chết trân, mặt tái mét.',
         facts=[dict(id='damage', title='Thiệt hại', source='Bàn sửa', text='Cáp nối của màn MỚI bị rách; main máy khách không sao.'),
                dict(id='ti', title='Tí', source='Thợ học việc', text='Tí mới học ba tuần, lần đầu tự tháo cáp màn.'),
                dict(id='stock', title='Kho', source='Kệ linh kiện', text='Còn một tấm màn cùng loại trên kệ.')],
         options=[dict(id='own', label='Thay tấm màn khác bằng tiền tiệm, báo chị Diệp chậm 30 phút vì lỗi của tiệm; kèm Tí làm lại từng bước', requires=['damage', 'stock'], cost=22, quality='good', stars=5,
                       review='Tiệm nhận lỗi thẳng thắn, lấy màn mới thay, còn xin lỗi vì chậm. Đáng tin!',
                       outcome='Chị Diệp chờ thêm 30 phút, nhận máy như mới. Tí được chú Tư kèm tay làm lại.',
                       perspectives=[dict(who='Chị Diệp', emoji='⏱️', text='Chậm chút mà được nói thật thì tôi còn quý hơn.'),
                                     dict(who='Tí', emoji='🥺', text='Chú không la em, chỉ bảo “làm lại, chậm thôi”.'),
                                     dict(who='Chú Tư', emoji='🧓', text='Hồi mới học tôi cũng làm rách cả chục sợi cáp.')]),
                  dict(id='hide', label='Dán băng keo cáp rách, lắp vào trả khách, không nói gì', quality='bad', stars=1,
                       review='Máy mới thay màn một tuần đã sọc, mở ra thấy cáp dán băng keo. Hết nói!',
                       outcome='Một tuần sau màn sọc, chị Diệp mang tới thợ khác. Uy tín tiệm rách theo sợi cáp.',
                       perspectives=[dict(who='Chị Diệp', emoji='😤', text='Làm hỏng không sao, giấu mới là chuyện lớn.'),
                                     dict(who='Tí', emoji='😞', text='Em thấy tội lỗi cả tuần.')]),
                  dict(id='wage', label='Thay màn mới nhưng trừ trọn tiền màn vào lương Tí', requires=['damage'], quality='ok', stars=4,
                       review='Tiệm thay màn mới, làm nhanh. Ổn.',
                       outcome='Khách không thiệt, nhưng Tí mất nửa tháng lương và bắt đầu giấu lỗi thay vì báo.',
                       perspectives=[dict(who='Tí', emoji='😔', text='Lần sau em làm hỏng chắc em không dám nói nữa.'),
                                     dict(who='Chị Diệp', emoji='🙂', text='Tôi thì nhận máy tốt, không biết chuyện phía sau.')])],
         lesson='Lỗi của tiệm thì tiệm nhận với khách; thợ mới cần được kèm, không phải bị phạt đến mức giấu lỗi.'),
]

SPEC = dict(
    id=ID, prefix='rp_', category='service',
    meta=dict(short='Tiệm sửa đồ', place='Tiệm Sửa Đồ Chú Tư', tagline='Đo trước, báo giá sau, sửa cho tới nơi.', icon='wrench',
              color='#3f7f8c', light='#e3f1f2', weather='Nắng xiên qua mái tôn', work='Máy chờ sửa', station='Bàn thợ',
              greeting='Nghe khách kể bệnh, ghi phiếu nhận, đo kiểm tìm đúng lỗi, báo giá cho khách gật đầu rồi mới sửa nhé.',
              caption='Mỗi món đồ cũ là một kỷ niệm còn chạy được', map_label='12 · TIỆM SỬA ĐỒ CHÚ TƯ'),
    people=PEOPLE,
    staff=[('Tí', 'apprentice', 'Thợ học việc, tay còn run nhưng rất chịu hỏi.', 72, 78),
           ('Hương', 'front', 'Nhận máy, ghi phiếu, nhớ mặt khách quen.', 84, 86),
           ('Bảo', 'parts', 'Quản kệ linh kiện, nhớ hạn keo tản nhiệt.', 76, 92),
           ('Sang', 'apprentice', 'Thợ phụ lâu năm, làm an toàn rất kỹ.', 80, 90)],
    roles={'apprentice': 'Thợ phụ', 'front': 'Nhận máy', 'parts': 'Kho linh kiện'},
    inventory=dict(items=ITEMS, capacity=40),
    prices={k: v['labor'] for k, v in DEVICES.items()},
    tip=2,
    physical=('rp_test', 'rp_open', 'rp_fix', 'rp_final', 'rp_parttest'),
    free_actions=(),
    no_tick=('rp_warranty', 'rp_desk', 'rp_answer'),
    waste_items=('job',),
    activity=('🔧', 'Bàn thợ ngăn nắp', [('Tụ quạt 1,5 µF', 'Ngăn đồ điện'), ('Săm xe đạp', 'Ngăn xe đạp'),
                                         ('Cầu chì nhiệt', 'Ngăn đồ điện'), ('Má phanh', 'Ngăn xe đạp')],
              ['Ghi phiếu nhận máy', 'Đo kiểm tìm lỗi', 'Báo giá, khách đồng ý', 'Sửa, chạy thử, ghi bảo hành']),
    stories=[('Chiếc quạt mười hai năm của ông Bảy', ('Ông Bảy kể chiếc quạt là quà cưới con gái út. Ông muốn nó chạy thêm vài mùa hè nữa.',
                                                       'Bạn thay tụ, bọc lại dây, tra dầu. Ông Bảy ngồi canh suốt, kể chuyện hồi quạt còn mới.',
                                                       'Ông mang tới một đĩa bánh ít: “Quạt chạy êm như hồi con Út còn nhỏ.”')),
             ('Tí và sợi cáp đầu tiên', ('Tí xin tập tháo cáp màn trên máy hỏng của tiệm, sau giờ đóng cửa.',
                                         'Bạn chỉ Tí sấy keo, cắm móng gảy, nhấc cáp thật chậm. Rách hai sợi mới được một sợi lành.',
                                         'Tí tự thay màn cho khách đầu tiên, tay vẫn run nhưng làm đúng từng bước.')),
             ('Nồi cơm của gánh xôi Cô Sáu', ('Cô Sáu kể nồi cơm hỏng là cả sáng không có xôi bán.',
                                              'Bạn chỉ cô cách lau đáy nồi, không để cặn cơm kẹt lò xo cảm biến.',
                                              'Gánh xôi treo tấm bảng nhỏ: “Nồi được chú Tư chăm, xôi dẻo đều.”'))],
    review_asides=['Máy chạy êm như mới đập hộp 🔧', 'Có phiếu bảo hành ghim sẵn, yên tâm ghê.', 'Chú thợ giải thích dễ hiểu hơn sách giáo khoa.',
                   'Trả máy còn lau sạch sẽ, thơm mùi cồn!'],
    situations=SITUATIONS,
    guide='Phiếu nhận → đo kiểm → chốt lỗi → báo giá → an toàn, mở máy → sửa → lắp → chạy thử → bảo hành → bàn giao.',
)
