"""Quirky and unfair gripes in reviews (the "xéo xắt" layer).

Real reviewers mark a perfect job down for things that have nothing to do with it:
the shop looked dusty, nobody smiled, no parking for the scooter, the cat on the
counter, "đắt hơn quán đầu hẻm 2 nghìn", the horoscope said today was unlucky…
and now and then they give five stars for an equally trivial reason.

`roll()` is called by feedback.make_review for completed jobs that are not already a
twist, a memory mix-up or a slip. Gripes are tied to real state when possible (dirty
counter, worn equipment, small or garden premises, the weather, festival or calm days,
crowding, a long day, the pet shop's cats, decor) and otherwise picked at random, all
seeded from the task id so a reload never rerolls. A gripe that drops a star is stored
as `unfair` (key 'gripe'), so the owner can answer or argue it through the existing
review_followup / feedback_decision flow and `_bounds` lets a good reply restore the
fair grade. Everything else (twists, moods, styles, tones) is unchanged.
"""
from __future__ import annotations

import re

GROUP = {'milk_tea': 'shop', 'cafe_bakery': 'shop', 'restaurant': 'shop', 'grocery': 'shop', 'mother_baby': 'shop',
         'pharmacy': 'shop', 'florist': 'shop', 'salon': 'shop', 'pet_care': 'shop', 'repair': 'shop',
         'accounting': 'office', 'corp_accounting': 'office', 'tax_payroll': 'office', 'group_accounting': 'office',
         'customer_care': 'support', 'tour_guide': 'tour', 'homestay': 'stay', 'teacher': 'teacher',
         'delivery': 'delivery', 'farm': 'farm', 'clothing': 'shop', 'tra_da': 'shop',
         'fruit': 'shop', 'garbage': 'delivery', 'drain': 'shop', 'homemaker': 'stay', 'ice_cream': 'shop', 'pho': 'shop', 'com': 'shop', 'nail': 'shop', 'pagoda': 'pagoda', 'photobooth': 'shop', 'giupviec': 'stay', 'naucom': 'stay', 'babysitter': 'stay', 'library': 'support', 'pilot': 'air', 'flight_attendant': 'air', 'railway': 'rail',
         'hr_admin': 'office', 'secretary': 'office', 'it_helpdesk': 'office', 'nurse': 'office', 'lighthouse': 'sea', 'rescue': 'office', 'lifeguard': 'stay', 'police': 'office'}
CUST = ('shop', 'office', 'support', 'tour', 'stay', 'delivery', 'farm')
# 'pagoda' has no gripe of its own: its visitors never write the shops' ones (game/pagoda_voice.py).
LABEL = 'Chuyện ngoài lề'
CLUE = 'Trừ sao vì chuyện ngoài lề'


def _G(gid, groups, claim, word, lines, signal=None, pos=False):
    return gid, dict(id=gid, groups=tuple(groups), claim=claim, word=word, lines=list(lines), signal=signal, pos=pos)


# lines are clauses that fit "tiếc là {line}" (negative) or "5 sao vì {line}" (positive).
GRIPES = dict((
    # ---- shops and premises
    _G('dusty', ('shop', 'stay'), 'quán nhìn hơi bụi', 'Bụi.', ['kệ phía sau còn bám một lớp bụi mỏng', 'mặt quầy hơi dính, nhìn là biết lâu chưa lau'], 'messy'),
    _G('no_smile', CUST, 'nhân viên không cười', 'Cười cái coi.', ['cả buổi không ai cười với tôi một cái', 'mặt người phục vụ nghiêm như đang đi họp']),
    _G('music', ('shop', 'stay', 'tour'), 'nhạc không hợp gu', 'Nhạc dở.', ['nhạc mở to quá, toàn bài tôi không thích', 'nhạc buồn thiu, nghe muốn khóc luôn']),
    _G('parking', ('shop', 'office'), 'không có chỗ để xe máy', 'Xe để đâu?', ['không có chỗ để xe máy, phải dựng tận đầu hẻm', 'dắt xe vào hẻm muốn gãy tay'], 'small_place'),
    _G('hot', ('shop', 'office', 'stay'), 'nóng, không có máy lạnh', 'Nóng.', ['nóng muốn chảy mỡ mà không có máy lạnh', 'cái quạt quay đâu đâu, tôi ngồi mồ hôi nhễ nhại'], 'sunny'),
    _G('sleepy', ('shop', 'office', 'support', 'delivery'), 'nhân viên nhìn buồn ngủ', 'Ngáp.', ['người làm ngáp liên tục trong lúc làm', 'nhìn mặt người làm như thức trắng đêm'], 'busy_day'),
    _G('cat', ('shop',), 'con mèo nằm trên quầy', 'Mèo.', ['con mèo nằm chễm chệ trên quầy, lông bay tứ tung', 'con mèo cứ nhìn tôi như muốn đòi tiền'], 'cat'),
    _G('chair', ('shop', 'office'), 'ghế chờ lung lay', 'Ghế lắc.', ['cái ghế chờ lung lay như sắp gãy', 'ghế kêu cót két mỗi lần tôi nhúc nhích'], 'worn'),
    _G('queue', ('shop', 'office'), 'phải chờ sau khách khác', 'Chờ.', ['phải đứng sau một vị khách chọn lâu như chọn nhà', 'khách trước tôi hỏi han cả buổi, tôi đứng mỏi cả chân'], 'crowded'),
    _G('wifi', ('shop', 'stay', 'office'), 'không có wifi', 'Wifi đâu?', ['không có wifi, tôi không check-in được', 'wifi yếu, lướt video cứ quay vòng vòng']),
    _G('price', ('shop',), 'đắt hơn quán đầu hẻm 2 nghìn', 'Đắt.', ['đắt hơn quán đầu hẻm 2 nghìn, tôi tính kỹ rồi', 'quán đầu hẻm rẻ hơn 2 nghìn đấy nhé']),
    _G('design', ('shop', 'delivery', 'farm'), 'ly, túi nhìn quê', 'Túi xấu.', ['cái túi đựng in hình nhìn quê quê', 'ly với túi thiết kế chưa đủ sang để chụp hình']),
    _G('face', ('shop', 'office', 'delivery', 'stay'), 'nhìn mặt chủ quán khó ưa', 'Mặt khó ưa.', ['nhìn mặt chủ quán khó ưa sao đó, không giải thích được', 'chủ quán có gương mặt… hơi khó gần']),
    _G('horoscope', CUST, 'tử vi nói hôm nay xui', 'Xui.', ['tử vi bảo hôm nay tôi kỵ ra đường, vậy mà vẫn ghé', 'hôm nay sao xấu chiếu, trừ sao cho cân bằng vũ trụ']),
    _G('rain', ('shop', 'delivery', 'tour', 'stay'), 'trời mưa, không chỗ trú', 'Ướt.', ['mưa ướt hết mà không có mái hiên để trú', 'trời mưa mà không có dù cho khách mượn'], 'rain'),
    _G('noise', ('shop', 'stay', 'tour'), 'phố ồn ào', 'Ồn.', ['ngoài phố ồn như vỡ chợ', 'hội phố ồn ào, nói gì cũng phải hét'], 'festival'),
    _G('empty', ('shop',), 'quán vắng tanh', 'Vắng.', ['quán vắng tanh, tôi hơi nghi nghi', 'vắng quá, không khí buồn hiu'], 'calm'),
    _G('bare', ('shop',), 'quán trống trơn, không góc chụp ảnh', 'Trống.', ['quán trống trơn, không có góc nào để sống ảo'], 'bare'),
    _G('mosquito', ('shop', 'stay'), 'muỗi ở sân vườn', 'Muỗi.', ['sân vườn đẹp nhưng muỗi cắn sưng cả chân'], 'garden'),
    _G('dark', ('shop',), 'hiên trước tối om', 'Tối.', ['trước hiên tối om, tôi suýt vấp'], 'dark_porch'),
    _G('name', ('shop',), 'tên quán khó nhớ', 'Tên gì?', ['tên quán khó nhớ, lần sau chắc tìm không ra']),
    # ---- office clients
    _G('cold_ac', ('office',), 'phòng lạnh cóng', 'Lạnh.', ['máy lạnh phòng làm việc lạnh cóng, tôi run cầm cập']),
    _G('lift', ('office',), 'thang máy chờ lâu', 'Thang máy.', ['thang máy tòa nhà chờ muốn mọc rễ']),
    _G('coffee', ('office',), 'cà phê tiếp khách dở', 'Cà phê dở.', ['ly cà phê tiếp khách nhạt như nước lọc']),
    _G('font', ('office',), 'biểu mẫu in font chữ xấu', 'Font xấu.', ['biểu mẫu in font chữ nhìn như từ thế kỷ trước']),
    _G('dress', ('office',), 'nhân viên ăn mặc chưa đủ sang', 'Áo nhăn.', ['người tiếp tôi mặc áo hơi nhăn, nhìn chưa chuyên nghiệp']),
    # ---- support callers
    _G('hold_music', ('support',), 'nhạc chờ tổng đài chán', 'Nhạc chờ.', ['nhạc chờ tổng đài nghe hoài một bài, ám ảnh', 'nhạc chờ vui quá, không hợp tâm trạng đang bực của tôi']),
    _G('keys', ('support',), 'phải bấm phím nhiều lần', 'Bấm phím.', ['phải bấm phím mấy lượt mới gặp được người thật']),
    _G('echo', ('support',), 'đường truyền rè', 'Rè.', ['đường truyền rè rè như radio cũ']),
    _G('lunch', ('support',), 'gọi đúng giờ trưa', 'Đói.', ['tôi gọi đúng giờ ăn trưa nên đói, bực lây sang tổng đài']),
    # ---- tour guests
    _G('bus_ac', ('tour',), 'máy lạnh xe yếu', 'Nóng.', ['máy lạnh trên xe yếu xìu, cả đoàn quạt tay'], 'sunny'),
    _G('sun', ('tour',), 'trời nắng quá', 'Nắng.', ['trời nắng gắt, ảnh chụp ai cũng nhăn mặt'], 'sunny'),
    _G('no_ghost', ('tour',), 'không kể chuyện ma', 'Thiếu ma.', ['hướng dẫn viên không kể chuyện ma nào, tôi hơi hụt hẫng']),
    _G('backlight', ('tour',), 'ảnh check-in bị ngược sáng', 'Ngược sáng.', ['điểm check-in toàn ngược sáng, ảnh tôi đen thui']),
    _G('lunch_salty', ('tour',), 'cơm trưa hơi mặn', 'Mặn.', ['cơm trưa ở quán dọc đường hơi mặn, dù chẳng phải lỗi ai']),
    _G('walk', ('tour',), 'đi bộ nhiều mỏi chân', 'Mỏi chân.', ['đi bộ nhiều quá, về tới nơi chân như cục chì']),
    # ---- homestay guests
    _G('rooster', ('stay',), 'gà nhà bên gáy sớm', 'Gà gáy.', ['gà nhà bên gáy từ lúc trời còn tối om']),
    _G('hot_water', ('stay',), 'nước nóng lâu', 'Nước lạnh.', ['nước nóng chờ lâu, tôi tắm run cầm cập']),
    _G('view_tree', ('stay',), 'cây che mất view', 'View đâu?', ['cái cây to che mất nửa view, chụp hình không đẹp']),
    _G('dog', ('stay',), 'chó hàng xóm sủa', 'Chó sủa.', ['chó nhà hàng xóm sủa cả đêm']),
    _G('blanket', ('stay',), 'chăn màu không hợp gu', 'Chăn hồng.', ['chăn màu hồng cánh sen, không hợp gu tôi']),
    _G('dryer', ('stay',), 'không có máy sấy tóc', 'Máy sấy?', ['không có máy sấy tóc, tôi đi chơi với mái tóc ướt']),
    # ---- pupils' parents
    _G('gate_sun', ('teacher',), 'cổng trường nắng, không có mái che', 'Nắng.', ['đứng đón con ở cổng trường nắng mà không có mái che'], 'sunny'),
    _G('no_smile_t', ('teacher',), 'cô/thầy ít cười', 'Ít cười.', ['con về kể hôm nay cô/thầy ít cười']),
    _G('hot_class', ('teacher',), 'lớp học nóng', 'Nóng.', ['lớp nóng, quạt trần lại kêu to']),
    _G('faint_print', ('teacher',), 'phiếu bài tập in mờ', 'In mờ.', ['phiếu bài tập in hơi mờ, tôi đọc phải đeo kính']),
    _G('desk', ('teacher',), 'bàn ghế lung lay', 'Bàn lắc.', ['bàn của con hơi lung lay, viết chữ bị nghiêng'], 'worn'),
    _G('zalo', ('teacher',), 'nhóm lớp nhắn tối muộn', 'Nhắn khuya.', ['nhóm lớp có tin nhắn tối muộn, tôi giật mình tỉnh giấc']),
    _G('uniform', ('teacher',), 'đồng phục màu chói', 'Màu chói.', ['đồng phục năm nay màu hơi chói']),
    _G('horoscope_t', ('teacher',), 'thầy bói nói con hợp thầy cô tuổi khác', 'Không hợp tuổi.', ['thầy bói bảo năm nay con hợp thầy cô tuổi khác, tôi hơi lăn tăn']),
    # ---- delivery and farm
    _G('helmet', ('delivery',), 'mũ bảo hiểm màu không hợp', 'Mũ xấu.', ['shipper đội mũ bảo hiểm màu không hợp với áo']),
    _G('early', ('delivery',), 'giao sớm quá', 'Sớm quá.', ['giao sớm quá, tôi còn chưa kịp dậy']),
    _G('knot', ('delivery',), 'túi buộc nút chặt', 'Nút buộc.', ['túi buộc nút chặt quá, tôi phải lấy kéo mới mở được']),
    _G('stern_call', ('delivery',), 'gọi điện giọng nghiêm', 'Giọng nghiêm.', ['gọi điện giọng nghiêm như gọi đi thi']),
    _G('soil', ('farm',), 'rau còn dính đất', 'Đất.', ['rau còn dính chút đất, rau sạch mà nhìn chưa sạch']),
    _G('worm', ('farm',), 'lá có lỗ sâu', 'Lỗ sâu.', ['lá rau có mấy lỗ sâu, biết là rau sạch nhưng nhìn không sang']),
    _G('label', ('farm',), 'nhãn in xấu', 'Nhãn xấu.', ['cái nhãn dán in chữ hơi xấu']),
    _G('far', ('farm',), 'chợ phiên xa', 'Xa.', ['chợ phiên xa quá, đi muốn hết xăng']),
    # ---- over-the-top praise for trivial reasons
    _G('cat_cute', ('shop', 'stay'), 'con mèo dễ thương', '', ['con mèo trên quầy quá dễ thương', 'con mèo nhìn tôi một cái là tôi xiêu lòng'], 'cat', True),
    _G('cat_street', ('shop', 'stay', 'delivery'), 'con mèo nhà bên', '', ['con mèo nhà bên ghé ngồi cạnh tôi suốt buổi'], None, True),
    _G('music_good', ('shop', 'stay', 'tour'), 'nhạc đúng gu', '', ['nhạc đúng gu, bài nào cũng muốn hát theo'], None, True),
    _G('name_cute', ('shop',), 'tên quán dễ thương', '', ['tên quán nghe dễ thương'], None, True),
    _G('plant_nice', ('shop', 'office'), 'chậu cây xanh', '', ['chậu cây bên cửa sổ xanh mướt'], 'plant', True),
    _G('lucky', CUST, 'tử vi nói hôm nay hên', '', ['tử vi nói hôm nay hợp màu áo của chủ quán, lấy hên'], None, True),
    _G('rain_cozy', ('shop', 'stay'), 'ngồi nghe mưa', '', ['trời mưa ngồi trong quán nghe mưa rơi, chill hết sức'], 'rain', True),
    _G('fest_vibe', ('shop', 'tour'), 'không khí hội phố', '', ['không khí hội phố vui quá trời'], 'festival', True),
    _G('pen', ('office',), 'bút ký trơn tay', '', ['cây bút ký trơn tay, ký sướng hết sức'], None, True),
    _G('candy', ('office',), 'đĩa kẹo tiếp khách', '', ['đĩa kẹo trên bàn tiếp khách ngon bất ngờ'], None, True),
    _G('nice_voice', ('support',), 'giọng tổng đài dễ thương', '', ['giọng tổng đài viên dễ thương như đọc truyện đêm khuya'], None, True),
    _G('photo', ('tour',), 'ảnh sống ảo đẹp', '', ['chụp được tấm ảnh sống ảo đẹp nhất đời'], None, True),
    _G('sing', ('tour',), 'hướng dẫn viên hát hay', '', ['hướng dẫn viên hát trên xe hay như ca sĩ'], None, True),
    _G('stay_cat', ('stay',), 'con mèo của homestay', '', ['con mèo của homestay ngủ cạnh tôi cả buổi chiều'], None, True),
    _G('breakfast', ('stay',), 'bữa sáng có trứng ốp la', '', ['bữa sáng có trứng ốp la lòng đào đúng ý'], None, True),
    _G('name_remember', ('teacher',), 'cô/thầy nhớ tên con', '', ['cô/thầy nhớ tên con ngay từ buổi đầu'], None, True),
    _G('handwriting', ('teacher',), 'chữ cô/thầy đẹp', '', ['chữ cô/thầy viết trên bảng đẹp như in'], None, True),
    _G('ship_smile', ('delivery',), 'shipper cười duyên', '', ['shipper cười duyên quá trời'], None, True),
    _G('egg_shape', ('farm',), 'trứng tròn đẹp', '', ['quả trứng nào cũng tròn đẹp như tranh'], None, True),
    # ---- ✈️ passengers of Hãng bay Cánh Cò
    _G('knees', ('air',), 'ghế chật chân', 'Chật.', ['ghế chật, đầu gối tôi chạm lưng ghế trước suốt chuyến']),
    _G('wing_view', ('air',), 'ngồi đúng chỗ cánh che', 'Cánh che.', ['tôi ngồi cửa sổ mà đúng ngay cánh, chẳng thấy biển đâu']),
    _G('ears', ('air',), 'ù tai khi hạ cánh', 'Ù tai.', ['lúc hạ cánh tai tôi ù đặc, dù chẳng phải lỗi ai']),
    _G('bus_gate', ('air',), 'xe buýt ra tàu chạy vòng', 'Xe buýt.', ['xe buýt từ cổng ra tàu chạy vòng vèo mãi mới tới']),
    _G('sea_view', ('air',), 'thấy biển từ trên cao', '', ['nhìn qua cửa sổ thấy biển xanh ngắt, đẹp như tranh'], None, True),
    _G('long_freight', ('rail',), 'tàu hàng dài lê thê', 'Dài.', ['đoàn tàu hàng ba chục toa, đếm mãi không hết']),
    _G('bell_loud', ('rail',), 'chuông đường ngang to', 'Ồn.', ['cái chuông đường ngang kêu to quá, ù cả tai']),
    _G('sun_wait', ('rail',), 'đứng chờ giữa nắng', 'Nắng.', ['đứng chờ tàu giữa trưa nắng, không có lấy một bóng cây']),
    _G('horn', ('rail',), 'còi tàu rúc to', 'Còi.', ['còi tàu rúc ngay lúc tôi đang nghe điện thoại']),
    _G('train_wave', ('rail',), 'lái tàu vẫy tay', '', ['lái tàu vẫy tay chào, tụi nhỏ nhà tôi thích mê'], None, True),
    _G('sunrise', ('air',), 'bay lúc bình minh', '', ['bay đúng lúc bình minh, mặt trời đỏ au ngay cánh tàu'], None, True),
    # ---- 🗼 boats and visitors around đèn biển Hòn Gió
    _G('seasick', ('sea',), 'say sóng trên đường ra đảo', 'Say sóng.', ['ra tới đảo thì tôi đã say sóng ói hai lần']),
    _G('stairs', ('sea',), 'cầu thang đá trơn', 'Trơn.', ['bậc đá lên trạm rêu trơn, tôi phải bò lên']),
    _G('gulls', ('sea',), 'hải âu kêu inh ỏi', 'Ồn.', ['đàn hải âu kêu inh ỏi, nói gì cũng không nghe']),
    _G('wind_hair', ('sea',), 'gió thổi rối tóc', 'Gió.', ['gió trên đảo thổi rối tung mái tóc mới làm']),
    _G('cat_mun', ('sea',), 'mèo Mun ra đón', '', ['con mèo đen của trạm ra tận bến đón, dễ thương hết sức'], None, True),
))

PRAISE = {
    'shop': ['{item} thì ngon thật', '{item} làm đúng ý', 'phần chính thì không chê được', '{item} ổn áp'],
    'office': ['hồ sơ làm chuẩn chỉnh', 'giấy tờ đâu ra đó', 'phần việc chính thì chuẩn'],
    'support': ['vấn đề của tôi được giải quyết', 'giải quyết đúng việc', 'người nghe máy làm việc tới nơi'],
    'tour': ['chuyến đi đúng lịch', 'hướng dẫn viên kể chuyện có duyên', 'đoàn đi an toàn, đủ người'],
    'stay': ['phòng sạch sẽ', 'chủ nhà chu đáo', 'giường êm'],
    'teacher': ['con học có tiến bộ', 'buổi học nhìn chung ổn', 'con về kể học vui'],
    'delivery': ['hàng tới nguyên vẹn', 'giao đúng chỗ', 'đơn đủ món'],
    'farm': ['rau tươi, trứng ngon', 'hàng tươi rói', 'đóng gói cẩn thận'],
    'air': ['chuyến bay an toàn', 'tổ bay chu đáo', 'hạ cánh êm'],
}
DROP = dict(yes=['Trừ một sao, không bàn.', 'Một sao trừ đi là vì chuyện đó.', 'Trừ một sao cho nhớ.'],
            no=['Sao thì vẫn để nguyên, tôi rộng lượng mà.', 'Không trừ sao đâu, nói cho biết thôi.', 'Vẫn đủ sao, nhưng nhớ đấy.'])
DROP_FORMAL = dict(yes='Tôi xin phép trừ một sao.', no='Tôi vẫn giữ nguyên số sao để ghi nhận thiện chí.')
DROP_PARENT = dict(yes='Gia đình xin trừ một sao.', no='Gia đình vẫn giữ nguyên đánh giá.')
FORMS = {
    'backhanded': ['{Praise} đấy, tiếc là {line}. {drop}', '{Praise}, có điều {line}. {drop}',
                   'Mọi thứ đều ổn, trừ việc {line}. {drop}', 'Công nhận {praise}. Tiếc là {line}. {drop}'],
    'passive': ['{stars} sao. Không có gì để nói. Ngoài việc {line}.', 'Ổn. Rất ổn. Nếu không tính chuyện {line}.',
                '{Praise}. {Line}. Vậy thôi.'],
    'genz': ['{praise} nha, mỗi tội {line} 🥲', 'ủa {line} là sao z trời 😵 {praise} thì oke', 'vibe ổn áp mà {line} nên tụt mood xíu 📉'],
    'formal': ['Kính gửi quý cửa hàng. Nhìn chung {praise}. Tuy nhiên, {line}. {drop_formal}',
               'Tôi xin góp ý chân thành: {praise}, song {line}. {drop_formal}'],
    'offtopic': ['{Line}. À, còn {item} thì cũng được.', '{Line}. Vậy đó. {Praise}, nhưng tôi nhớ chuyện kia hơn.'],
    'p_formal': ['Kính gửi cô/thầy. {Praise}. Tuy nhiên, {line}. {drop_parent}',
                 'Gia đình xin góp ý: {praise}, có điều {line}. {drop_parent}'],
    'p_passive': ['{stars} sao. {Praise}. Chỉ là {line}.', 'Vâng, ổn ạ. Nếu không tính chuyện {line}.'],
    # positive quirks
    'pos_fan': ['5 sao vì {line}. Còn {item} thì… ừ, cũng ổn.', '{Line}, nên 5 sao, khỏi bàn.', 'Không nhớ rõ {item} thế nào, chỉ nhớ {line}. 5 sao.'],
    'pos_genz': ['{line} ✨ 5 sao không bàn cãi', 'đến vì {item}, ở lại vì {line} 🫶'],
    'pos_short': ['{Line}. 5 sao.'],
    'p_pos': ['5 sao vì {line} ạ. Buổi học thì con kể cũng vui.', 'Gia đình chấm 5 sao, lý do chính là {line} 😊'],
}
ESSAY = dict(
    intro=['Tôi viết hơi dài, mọi người thông cảm.', 'Chuyện là chiều nay tôi tan làm sớm, định ghé cho vui.',
           'Tôi vốn ít khi đánh giá, nhưng hôm nay phải nói.', 'Mở đầu bằng một lời khen cho công bằng.'],
    tangent=['Trên đường tới đây tôi còn gặp con chó nhà ai đuổi theo xe.', 'Nhân tiện, hôm nay tôi mặc áo mới, ai để ý thì cảm ơn.',
             'Tôi kể thêm là sáng nay tôi làm rơi chìa khóa, nhưng cái đó không liên quan.', 'Mẹ tôi dặn đi đâu cũng phải nhận xét cho công tâm.'],
    end_yes=['Vì vậy, với tất cả sự công tâm, tôi trừ một sao.', 'Tóm lại là tốt, nhưng một sao kia tôi giữ lại vì chuyện đó.'],
    end_no=['Tóm lại vẫn đủ sao, chỉ mong quán để ý.', 'Viết dài vậy thôi chứ tôi vẫn quý, sao để nguyên.'],
    p_intro=['Tôi xin phép nhắn dài một chút.', 'Tối qua con ăn cơm xong cứ ngồi kể chuyện lớp mãi.'],
    p_tangent=['Nhân tiện, bà nội cháu gửi lời hỏi thăm cô/thầy.', 'Hôm qua cháu còn đòi mua cặp mới giống bạn cùng bàn.'],
    p_end_yes=['Vì vậy gia đình xin trừ một sao để cô/thầy lưu ý.'], p_end_no=['Gia đình vẫn giữ nguyên đánh giá, chỉ mong cô/thầy để ý.'],
)
# Which forms fit a review temperament (weights).
FORM_WEIGHTS = {
    'quiet': (('one_word', 4), ('passive', 3), ('backhanded', 1)),
    'genz': (('genz', 5), ('backhanded', 1), ('one_word', 1), ('offtopic', 1)),
    'sour': (('backhanded', 4), ('passive', 3), ('one_word', 1), ('offtopic', 1)),
    'bossy': (('essay', 3), ('formal', 2), ('backhanded', 2)),
    'picky': (('formal', 4), ('passive', 2), ('backhanded', 1)),
    'warm': (('backhanded', 3), ('essay', 2), ('offtopic', 1)),
    'knowitall': (('essay', 3), ('formal', 2)), 'rude': (('one_word', 3), ('passive', 3)),
    'entitled': (('formal', 2), ('passive', 2), ('backhanded', 1)), 'drama': (('essay', 2), ('genz', 1), ('backhanded', 1)),
    'troll': (('offtopic', 3), ('one_word', 2), ('genz', 1)),
}
PARENT_FORMS = (('p_formal', 3), ('p_passive', 2), ('p_essay', 2))
# How gripe reviewers answer when the owner replies (merged into feedback.TWIST_REPLY).
REPLY = {
    'gripe_soft': ['Ừ thì chuyện đó cũng không phải lỗi bên bạn. Thôi trả lại sao cho công bằng.',
                   'Đọc trả lời thấy dễ chịu, thôi bỏ qua chuyện kia, sửa sao nè.',
                   'Công nhận phần chính làm tốt. Tôi hơi khó tính vụ kia thôi, sửa lại sao.'],
    'gripe_soft_parent': ['Vâng, chuyện đó cũng không phải lỗi của cô/thầy. Gia đình sửa lại đánh giá ạ.',
                          'Nghe cô/thầy nói vậy tôi thấy mình hơi khắt khe. Tôi sửa lại ạ.'],
}
SITUATION = ('Bạn làm được việc chính như ý, nhưng trừ sao vì một chuyện ngoài lề (unfair_claim.claim) chẳng liên quan dịch vụ. '
             'Nếu chủ quán trả lời dễ thương, xin lỗi khéo hoặc nêu sự thật nhẹ nhàng, bạn có thể bỏ qua và trả lại sao; '
             'nếu bị cãi hoặc mỉa, bạn cãi cố cho vui, xéo xắt nhưng không tục.')
EXTRA_OPEN = {
    'sour': {5: ['Năm sao. Đừng quen.', 'Ngon. Lạ thật đấy.'], 4: ['Được, tiếc là tôi không tìm ra chỗ chê cho đủ năm câu.'],
             3: ['Ba sao, một sao cho sự cố gắng, hai sao cho… thôi khỏi.']},
    'bossy': {4: ['Khá. Tôi mà mở quán thì còn khá hơn.']},
    'picky': {5: ['Đạt. Tôi đã kiểm hai lần cho chắc.']},
    'genz': {5: ['ăn một miếng thấy đời bớt deadline 🥹'], 3: ['cx đc, nma chưa đủ để kể với hội bạn 🤷']},
    'quiet': {5: ['Ừ.', 'Được.'], 4: ['Tạm.']},
    'knowitall': {5: ['Được. Anh gật đầu, hiếm lắm đấy.']},
    'rude': {4: ['Được. Lần sau cười lên một chút.'], 3: ['Ổn. Như một ngày thứ hai.']},
}


def gripe_rate(day: int) -> float:
    """Share of completed jobs whose reviewer brings up something off-topic (before other kinds take their share).
    None on the first day: the first reviews a new player reads stay plain."""
    return 0.0 if day <= 1 else 0.2 if day == 2 else 0.27


def _weather(day: int) -> str:
    return ('sun', 'rain', 'breeze')[(max(1, int(day)) - 1) % 3]


def signals(s: dict, c: dict, t: dict) -> set:
    """What is really true today and could annoy (or charm) a picky reviewer."""
    out = set()
    career = t.get('career', '')
    day = int(c.get('day', 1) or 1)
    ops = c.get('ops') if isinstance(c.get('ops'), dict) else {}
    tier = ((ops.get('property') or {}).get('tier')) if isinstance(ops.get('property'), dict) else None
    cond = ((ops.get('equipment') or {}).get('condition')) if isinstance(ops.get('equipment'), dict) else None
    boba = (((c.get('ext') or {}).get('data') or {}).get('boba') or {}) if isinstance(c.get('ext'), dict) else {}
    if isinstance(boba, dict) and int(boba.get('mess', 0) or 0) >= 2 or (isinstance(cond, (int, float)) and cond < 50):
        out.add('messy')
    if isinstance(cond, (int, float)) and cond < 70:
        out.add('worn')
    if tier == 'cozy':
        out.add('small_place')
    if tier == 'garden':
        out.add('garden')
    items = ((ops.get('security') or {}).get('items') or []) if isinstance(ops.get('security'), dict) else []
    if ops and 'light' not in [x if isinstance(x, str) else (x or {}).get('id') for x in items] and day >= 3:
        out.add('dark_porch')
    decor = c.get('decor') if isinstance(c.get('decor'), dict) else {}
    if 'plant' in decor:
        out.add('plant')
    if not decor and day >= 4:
        out.add('bare')
    w = _weather(day)
    out.add('sunny' if w == 'sun' else 'rain' if w == 'rain' else 'breeze')
    mode = (c.get('life') or {}).get('mode') if isinstance(c.get('life'), dict) else None
    if mode == 'festival':
        out.update(('festival', 'crowded'))
    elif mode == 'calm':
        out.add('calm')
    waiting = [x for x in c.get('tasks') or [] if isinstance(x, dict) and x is not t and x.get('status') not in ('completed', 'referred', 'cancelled')]
    if len(waiting) >= 3:
        out.add('crowded')
    if int(c.get('day_completed', 0) or 0) >= 5:
        out.add('busy_day')
    if career == 'pet_care':
        out.add('cat')
    return out


def _pick_gripe(career: str, sig: set, positive: bool, seed: int) -> tuple[str, str | None] | None:
    group = GROUP.get(career, 'shop')
    rows = [g for g in GRIPES.values() if group in g['groups'] and g['pos'] == positive]
    if not rows:
        return None
    tied = [g for g in rows if g['signal'] and g['signal'] in sig]
    free = [g for g in rows if not g['signal']]
    if tied and (not free or seed % 10 < 7):
        g = tied[(seed // 10) % len(tied)]
        return g['id'], g['signal']
    pool = free or rows
    g = pool[(seed // 10) % len(pool)]
    return g['id'], None


def _weighted(rows, seed: int) -> str:
    total = sum(w for _, w in rows)
    x = seed % total
    for k, w in rows:
        if x < w:
            return k
        x -= w
    return rows[-1][0]


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:] if text and text[0] not in '“"' else text


def _fill(tpl: str, **kw) -> str:
    out = tpl
    for k, v in kw.items():
        out = out.replace('{' + k + '}', v).replace('{' + k[:1].upper() + k[1:] + '}', _cap(v))
    return re.sub(r'\s{2,}', ' ', out).strip()


def write(gid: str, form: str, dropped: bool, stars: int, item: str, praise: str, seed: int) -> str:
    g = GRIPES[gid]
    line = g['lines'][(seed // 3) % len(g['lines'])]
    pick = lambda rows, k=0: rows[(seed // 7 + k) % len(rows)]
    yn = 'yes' if dropped else 'no'
    if form == 'one_word':
        return g['word'] or _cap(line) + '.'
    if form == 'essay':
        return ' '.join([pick(ESSAY['intro']), _cap(praise) + ', nói cho công bằng.', pick(ESSAY['tangent'], 1),
                         'Có điều ' + line + '.', pick(ESSAY['end_' + yn], 2)])
    if form == 'p_essay':
        return ' '.join([pick(ESSAY['p_intro']), _cap(praise) + '.', pick(ESSAY['p_tangent'], 1), 'Có điều ' + line + '.',
                         pick(ESSAY['p_end_' + yn], 2)])
    text = _fill(pick(FORMS[form]), line=line, praise=praise, item=item, stars=str(stars), drop=pick(DROP[yn], 3),
                 drop_formal=DROP_FORMAL[yn], drop_parent=DROP_PARENT[yn])
    return _cap(text) if form != 'genz' and form != 'pos_genz' else text


def roll(s: dict, c: dict, t: dict, persona: str, group: str, fair: int, stars: int, criteria: list, seed: int, item: str) -> dict | None:
    """Maybe give this review a gripe. Returns dict(gripe, stars, text, unfair|None, clue|None) or None."""
    from .feedback import _roll, _hash, HARSH
    day = int(c.get('day', 1) or 1)
    if stars < 3 or _roll('gripe', t['id'], day) >= gripe_rate(day):
        return None
    career = t.get('career', '')
    parent = group == 'parent'
    positive = fair >= 4 and _hash('gripe-pos', t['id']) % 100 < 22 and persona not in HARSH
    sig = signals(s, c, t)
    picked = _pick_gripe(career, sig, positive, _hash('gripe-kind', t['id'], day))
    if not picked:
        return None
    gid, tied = picked
    best = max(criteria, key=lambda x: x['score'])
    rows = PRAISE.get(GROUP.get(career, 'shop'), PRAISE['shop'])
    praise = rows[_hash('gripe-praise', t['id']) % len(rows)].replace('{item}', item)
    if positive:
        form = 'p_pos' if parent else 'pos_genz' if persona == 'genz' else 'pos_short' if persona == 'quiet' else 'pos_fan'
        new = 5
        dropped = False
    else:
        form = _weighted(PARENT_FORMS if parent else FORM_WEIGHTS.get(persona, (('backhanded', 3), ('passive', 1))), _hash('gripe-form', t['id']))
        harsh = persona in HARSH or persona in ('sour', 'picky')
        dropped = _hash('gripe-drop', t['id']) % 100 < (75 if harsh else 55)
        new = min(stars, max(1, fair - 1)) if dropped else stars  # one star at most, even on a bad day
    text = write(gid, form, dropped, new, item, praise, seed)
    g = GRIPES[gid]
    out = dict(gripe=dict(id=gid, form=form, positive=positive, dropped=dropped, tied=tied), stars=new, text=text[:600],
               unfair=None, clue=None)
    if dropped and new < fair:
        out['unfair'] = dict(key='gripe', label=LABEL, claim=g['claim'],
                             truth=(best.get('note') or 'phần việc chính làm đúng') + '; lời chê không liên quan tới dịch vụ', gripe=gid)
        out['clue'] = CLUE
    return out


def situation(fb: dict) -> str | None:
    return SITUATION if (fb.get('unfair') or {}).get('gripe') else None


def validate(fb: dict) -> None:
    from .engine import need
    g = fb.get('gripe')
    if g is None:
        return
    need(isinstance(g, dict) and g.get('id') in GRIPES and type(g.get('positive')) is bool and type(g.get('dropped')) is bool
         and (g.get('form') in FORMS or g.get('form') in ('one_word', 'essay', 'p_essay'))
         and (g.get('tied') is None or isinstance(g.get('tied'), str) and len(g['tied']) <= 20), 'Lời phàn nàn sai.')


def install(ns: dict) -> None:
    """Add gripe replies and a few extra sarcastic openers to feedback.py's tables."""
    for k, rows in REPLY.items():
        ns['TWIST_REPLY'].setdefault(k, list(rows))
    voice = ns['VOICE']
    for persona, opens in EXTRA_OPEN.items():
        for star, lines in opens.items():
            have = voice[persona]['open'][star]
            voice[persona]['open'][star] = have + [x for x in lines if x not in have]
