"""Static content of 🎖️ Thăng tiến and 🧑‍💼 Ca quản lý (game/promotion.py): titles, the boss's
questions, the shift's small crises and the lines a finished job shows. Short on purpose: every
line fits a phone at a glance. Everything is fictional.
"""
from __future__ import annotations

# Employee careers: the titles above the hired one (step 1 → 4; a longer ladder, promotion.TOP_BY_CAREER, goes on
# past step 4: pilot to 7, teacher to 5).
EMP_TITLES = {
    'corp_accounting': ('Kế toán viên chính', 'Kế toán phụ trách phần hành', 'Phó phòng kế toán', 'Kế toán trưởng'),
    'tax_payroll': ('Chuyên viên lương bậc 2', 'Trưởng nhóm lương', 'Phó phòng thuế – lương', 'Trưởng phòng thuế – lương'),
    'group_accounting': ('Chuyên viên hợp nhất bậc 2', 'Trưởng nhóm hợp nhất', 'Phó phòng tài chính TĐ', 'Kế toán trưởng tập đoàn'),
    'hr_admin': ('Chuyên viên chính', 'Trưởng nhóm C&B', 'Phó phòng HCNS', 'Trưởng phòng HCNS'),
    'secretary': ('Thư ký chính', 'Trợ lý giám đốc', 'Phó chánh văn phòng', 'Chánh văn phòng'),
    'it_helpdesk': ('KTV bậc 2', 'Trưởng ca hỗ trợ', 'Trưởng nhóm hạ tầng', 'Trưởng phòng CNTT'),
    'pharmacy': ('Dược sĩ đứng quầy chính', 'Phụ trách ca', 'Phó quản lý nhà thuốc', 'Dược sĩ quản lý'),
    'customer_care': ('Chuyên viên CSKH', 'Trưởng ca', 'Giám sát CSKH', 'Trưởng phòng CSKH'),
    'teacher': ('GV giỏi cấp trường', 'Tổ phó chuyên môn', 'Tổ trưởng chuyên môn', 'Phó hiệu trưởng', 'Hiệu trưởng'),
    'tour_guide': ('HDV chính', 'Trưởng đoàn', 'Điều hành tour', 'Trưởng phòng hướng dẫn'),
    'repair': ('Thợ chính', 'Thợ cả', 'Tổ trưởng xưởng', 'Quản đốc xưởng'),
    'delivery': ('Shipper tin cậy', 'Trưởng nhóm khu vực', 'Điều phối viên', 'Quản lý bưu cục'),
    'pet_care': ('Thợ chăm chính', 'Thợ cả', 'Trưởng ca', 'Quản lý tiệm'),
    'salon': ('Thợ chính', 'Thợ cả', 'Stylist trưởng', 'Quản lý salon'),
    'pilot': ('Cơ phó cao cấp', 'Cơ trưởng', 'Cơ trưởng Huấn luyện', 'Trưởng đội bay',
              'Phó Giám đốc Khối khai thác bay', 'Giám đốc Khối khai thác bay', 'Phó Tổng Giám đốc'),
    'flight_attendant': ('TV hạng thương gia', 'Tiếp viên phó', 'Tiếp viên trưởng', 'Trưởng ban tiếp viên'),
    'oil': ('Kỹ thuật viên bậc 2', 'Trưởng nhóm vận hành', 'Trưởng ca giàn', 'Quản đốc giàn'),
    'railway': ('Gác chắn chính', 'Trưởng ca gác chắn', 'Đội phó cung đường', 'Cung trưởng cung đường'),
    'nurse': ('Điều dưỡng chính', 'Trưởng ca điều dưỡng', 'Điều dưỡng trưởng khoa', 'Trưởng phòng Điều dưỡng'),
}

# Owner careers: the place's own standing. By the character: '{chu}' Ông chủ / Bà chủ / Chủ tiệm, '{ong}' Ông chủ / Bà chủ / Chủ.
OWN_TITLES = {
    'shop': ('Chủ quầy vững tay', 'Chủ tiệm có tiếng', '{chu} được nể', '{ong} chuỗi tiệm'),
    'accounting': ('Sổ sách vững tay', 'Kế toán có tiếng', 'Trưởng nhóm sổ', 'Chủ văn phòng sổ sách'),
    'homemaker': ('Nội trợ khéo tay', 'Nội trợ có tiếng', 'Quản gia', 'Quản gia trưởng'),
    'pagoda': ('Công quả chăm chỉ', 'Công quả được tin', 'Trưởng ban công quả', 'Trưởng ban hộ tự'),
    'garbage': ('Tổ viên vững tay', 'Tổ viên gương mẫu', 'Tổ phó thu gom', 'Tổ trưởng thu gom'),
    'drain': ('Thợ thông cống vững tay', 'Thợ có tiếng', 'Trưởng nhóm thợ', 'Chủ đội thông cống'),
    'farm': ('Nhà nông chăm chỉ', 'Nhà nông có tiếng', 'Chủ trại', 'Chủ trang trại lớn'),
    'homestay': ('Chủ nhà vững tay', 'Homestay có tiếng', 'Chủ homestay được nể', '{ong} chuỗi homestay'),
}
# Home careers paid by the household (giúp việc theo giờ, nấu cơm gia đình, bảo mẫu): a homemaker's standing, not a shop's.
OWN_TITLES['giupviec'] = OWN_TITLES['naucom'] = OWN_TITLES['babysitter'] = OWN_TITLES['homemaker']
# The ward library: a public servant's standing, from the desk to running the library and the ward's records.
OWN_TITLES['library'] = ('Cán bộ thư viện vững tay', 'Thủ thư có tiếng', 'Phó phụ trách thư viện', 'Phụ trách Thư viện – Lưu trữ')
CHU = {'male': 'Ông chủ', 'female': 'Bà chủ', None: 'Chủ tiệm'}
ONG = {'male': 'Ông chủ', 'female': 'Bà chủ', None: 'Chủ'}
BASE_EMP = 'Nhân viên'      # an employee's title before step 1 is the posting's own title
BASE_BY_POSTING = {'pl-fo': 'Cơ phó cấp thấp'}   # ...unless the posting has a rank name of its own (F#193)

# The rank's insignia. Pilot (F#193): g gold stripes, s stars, w a gold wreath, by step 0..7.
INSIGNIA = {
    'pilot': (dict(g=1, s=0, w=False), dict(g=2, s=0, w=False), dict(g=3, s=0, w=False), dict(g=4, s=0, w=False),
              dict(g=4, s=1, w=False), dict(g=4, s=2, w=False), dict(g=4, s=3, w=False), dict(g=4, s=3, w=True)),
}
# Other careers: one emoji by step (0..top); every other career keeps 🎖️.
BADGE = {'teacher': ('🍎', '🏅', '📒', '📚', '🗝️', '🏫')}


def insignia_label(x: dict) -> str:
    bits = [f'{x["g"]} gạch']
    if x['s']:
        bits.append(f'{x["s"]} sao')
    if x['w']:
        bits.append('cành tùng vàng')
    return ' · '.join(bits)
BASE_OWN = 'Chủ mới'        # an owner before step 1

# Question banks of the review, by career group. score: 2 best · 1 ok · 0 not now.
GROUP = {
    'office': ('corp_accounting', 'tax_payroll', 'group_accounting', 'hr_admin', 'secretary', 'it_helpdesk',
               'accounting', 'customer_care'),
    'air': ('pilot', 'flight_attendant'),
    'rig': ('oil',),
    'rail': ('railway',),
    'service': ('pharmacy', 'teacher', 'tour_guide', 'pet_care', 'salon', 'nail', 'homestay', 'photobooth',
                'homemaker', 'giupviec', 'naucom', 'babysitter', 'library', 'pagoda',
                'mother_baby', 'nurse'),
}   # every other career: 'trade'


def _q(qid, text, *opts):
    return dict(id=qid, text=text, options=[dict(id=chr(97 + i), label=lab, score=sc) for i, (lab, sc) in enumerate(opts)])


QUESTIONS = {
    'office': [
        _q('o1', 'Đồng nghiệp nhờ bạn ký thay một chứng từ.', ('Từ chối, chỉ cách làm đúng', 2), ('Ký giúp lần này thôi', 0), ('Bảo bạn ấy hỏi sếp', 1)),
        _q('o2', 'Sát hạn nộp mà số liệu còn lệch.', ('Báo sếp sớm, xin thêm giờ', 2), ('Nộp đại cho kịp', 0), ('Thức khuya tự sửa, không báo', 1)),
        _q('o3', 'Bạn mới vào nhóm làm sai nhiều.', ('Kèm cặp, chỉ từng bước', 2), ('Làm thay cho nhanh', 1), ('Báo sếp đổi người', 0)),
        _q('o4', 'Khách gọi tới bực vì chờ lâu.', ('Xin lỗi, hẹn giờ trả lời rõ', 2), ('Chuyển máy cho người khác', 1), ('Bảo khách chờ tiếp', 0)),
        _q('o5', 'Sếp giao hai việc gấp cùng lúc.', ('Hỏi sếp việc nào trước', 2), ('Làm cả hai cho xong', 0), ('Chọn việc mình quen', 1)),
        _q('o6', 'Bạn thấy lỗi của chính mình tuần trước.', ('Báo ngay và sửa', 2), ('Sửa lặng lẽ', 1), ('Kệ, chưa ai thấy', 0)),
    ],
    'service': [
        _q('s1', 'Khách quen xin bớt giá quá nhiều.', ('Giữ giá, tặng thêm chút dịch vụ', 2), ('Bớt luôn cho vui', 1), ('Từ chối cộc lốc', 0)),
        _q('s2', 'Khách phàn nàn to trước mặt người khác.', ('Mời ra chỗ riêng, nghe hết', 2), ('Cãi lại cho rõ', 0), ('Im lặng cho qua', 1)),
        _q('s3', 'Đồng nghiệp đến trễ lần thứ ba.', ('Nói riêng, hỏi lý do', 2), ('Nhắc trước mọi người', 0), ('Làm thay, không nói gì', 1)),
        _q('s4', 'Một bước làm tắt có thể hại khách.', ('Dừng lại, làm đủ quy trình', 2), ('Làm nhanh cho xong', 0), ('Hỏi ý khách', 1)),
        _q('s5', 'Khách để quên đồ quý ở quầy.', ('Cất kỹ, ghi sổ, gọi khách', 2), ('Để nguyên chỗ cũ', 1), ('Đợi khách tự quay lại hỏi', 0)),
        _q('s6', 'Ngày đông khách, cả đội đều mệt.', ('Chia nhau nghỉ ngắn luân phiên', 2), ('Cố làm liền một mạch', 1), ('Đóng cửa sớm không báo', 0)),
    ],
    'trade': [
        _q('t1', 'Hàng về thiếu so với phiếu.', ('Đếm lại, ghi biên bản, báo nơi giao', 2), ('Ký nhận cho nhanh', 0), ('Gọi điện nhắc miệng', 1)),
        _q('t2', 'Khách muốn mua món sắp hỏng.', ('Nói thật, bớt giá hoặc đổi món', 2), ('Bán, không nói gì', 0), ('Không bán món đó', 1)),
        _q('t3', 'Người mới làm vỡ đồ.', ('Hỏi han, chỉ cách làm đúng', 2), ('Trừ lương ngay', 0), ('Cho qua, không nói gì', 1)),
        _q('t4', 'Quán bên cạnh hạ giá.', ('Giữ chất lượng, chăm khách quen', 2), ('Hạ giá thấp hơn nữa', 1), ('Nói xấu quán bên', 0)),
        _q('t5', 'Trời mưa, khách vắng.', ('Gọi khách quen, nhận giao tận nơi', 2), ('Về sớm nghỉ ngơi', 1), ('Tăng giá bù lỗ', 0)),
        _q('t6', 'Dụng cụ kêu lạ giữa ca.', ('Tắt máy, kiểm tra rồi làm tiếp', 2), ('Ghi lại, cuối ca xem', 1), ('Làm tiếp cho kịp', 0)),
    ],
    'air': [
        _q('a1', 'Hành khách không chịu thắt dây an toàn.', ('Giải thích nhẹ nhàng, nhờ tổ trưởng nếu cần', 2), ('Bỏ qua', 0), ('Nhắc to trước cả khoang', 1)),
        _q('a2', 'Chuyến bay trễ, khách bực.', ('Báo rõ lý do và giờ mới', 2), ('Hứa một giờ bay chưa chắc', 0), ('Xin lỗi chung chung', 1)),
        _q('a3', 'Đồng nghiệp mệt trước giờ bay.', ('Báo tổ trưởng, đổi ca nếu cần', 2), ('Kệ, ai cũng mệt', 0), ('Làm đỡ phần của bạn ấy', 1)),
        _q('a4', 'Danh sách kiểm còn sót một bước.', ('Dừng, làm đủ rồi mới ký', 2), ('Ký trước, kiểm sau', 0), ('Hỏi người bên cạnh', 1)),
        _q('a5', 'Khách xin đổi chỗ giữa chuyến.', ('Kiểm chỗ trống, đổi nếu an toàn', 2), ('Từ chối ngay', 1), ('Để khách tự đổi', 0)),
        _q('a6', 'Nghe tin đồn về một đồng nghiệp.', ('Không lan truyền, hỏi thẳng nếu cần', 2), ('Kể cho cả tổ', 0), ('Im lặng nhưng tránh mặt', 1)),
    ],
}
QUESTIONS['rig'] = [
    _q('r1', 'Giám sát giục bỏ bước đo khí cho kịp tàu dịch vụ.', ('Dừng việc, đo khí rồi mới làm, báo giờ xong', 2), ('Đo nhanh một điểm cho có', 1), ('Làm theo cho kịp tàu', 0)),
    _q('r2', 'Thợ nhà thầu đưa checklist giàn giáo đã ký sẵn.', ('Đi kiểm từng mục cùng họ rồi mới ký', 2), ('Kiểm vài mục chính', 1), ('Ký luôn cho nhanh', 0)),
    _q('r3', 'Bạn suýt làm rơi cờ lê từ sàn trên, không ai thấy.', ('Tự báo suýt sự cố, đề xuất dây cột dụng cụ', 2), ('Xin lỗi người dưới, hứa cẩn thận', 1), ('Im lặng cho qua', 0)),
    _q('r4', 'Đồng hồ không về 0 sau khi xả áp.', ('Dừng, báo trưởng ca, cô lập thêm một lớp', 2), ('Chờ thêm mười phút', 1), ('Nới bích từ từ cho xì hết', 0)),
    _q('r5', 'Người ca sau sắp lên, còn vài việc dở.', ('Ghi đủ mọi việc dở, kể cả lỗi của mình', 2), ('Chỉ ghi việc lớn', 1), ('Dặn miệng cho nhanh', 0)),
    _q('r6', 'Lính mới say sóng, nhờ bạn làm thay rồi giấu trưởng ca.', ('Đưa bạn ấy xuống y tế, báo trưởng ca xếp lại việc', 2), ('Làm thay lần này thôi', 1), ('Bảo cố mà làm', 0)),
]
QUESTIONS['rail'] = [
    _q('r1', 'Người dân xin mở chắn sớm “vì tàu còn xa”.', ('Giữ chắn, nói rõ còn mấy phút', 2), ('Mở nhanh cho một người', 0), ('Lờ đi không trả lời', 1)),
    _q('r2', 'Đồng nghiệp nhờ ký sổ giao ca khi chưa thử thiết bị.', ('Từ chối, cùng thử rồi mới ký', 2), ('Ký giúp lần này', 0), ('Ký nhưng ghi chú nhỏ', 1)),
    _q('r3', 'Đi tuần thấy ray nứt, mười phút nữa có tàu.', ('Phòng vệ hai đầu, điện khẩn cho ga', 2), ('Ghi phiếu báo hỏng', 0), ('Gọi tổ thợ hỏi ý kiến', 1)),
    _q('r4', 'Cung trưởng bảo ghi tàu chậm thành đúng giờ.', ('Ghi đúng, kèm lý do chậm', 2), ('Sửa cho đẹp báo cáo', 0), ('Ghi đúng nhưng không nói gì', 1)),
    _q('r5', 'Ca đêm thứ ba liền, bạn buồn ngủ díp mắt.', ('Báo đội trưởng, xin người thay hoặc nghỉ bù', 2), ('Chợp mắt giữa hai chuyến', 0), ('Uống thêm cà phê cố gác', 1)),
    _q('r6', 'Tàu qua mà không thấy đèn đuôi toa cuối.', ('Báo ngay trực ban ga', 2), ('Ghi sổ, cuối ca báo', 1), ('Cho qua, chắc đèn hỏng', 0)),
]
# Steps above 4 (the executive steps): the board's own questions.
EXEC_GROUP = {'pilot': 'exec_air', 'teacher': 'exec_school'}
QUESTIONS['exec_air'] = [
    _q('x1', 'Phòng thương mại muốn cắt giờ nghỉ tổ bay để thêm chuyến dịp lễ.', ('Giữ đúng giờ nghỉ, thuê thêm chuyến hoặc đổi lịch', 2), ('Cắt nhẹ, ai mệt thì báo', 0), ('Hỏi tổ bay ai tình nguyện', 1)),
    _q('x2', 'Một cơ trưởng giỏi nhất đội bị khách khiếu nại thái độ.', ('Xem lại sự việc, nghe hai phía rồi mới kết luận', 2), ('Bỏ qua vì anh ấy bay giỏi', 0), ('Bắt xin lỗi khách ngay', 1)),
    _q('x3', 'Quỹ lương quý này vượt kế hoạch.', ('Xem lại lịch bay và giờ làm thêm, không đụng dầu dự phòng', 2), ('Cắt phụ cấp bay đêm của cả đội', 0), ('Xin thêm ngân sách, chưa đổi gì', 1)),
    _q('x4', 'Phi công nộp báo cáo tự nguyện về một lỗi suýt gây sự cố.', ('Cảm ơn, không phạt, đưa thành bài học chung', 2), ('Kỷ luật cho cả đội sợ', 0), ('Cất báo cáo, không nói ai', 0)),
    _q('x5', 'Hai trưởng phòng tranh nhau một suất học lái tàu mới.', ('Đưa tiêu chí rõ ràng, chấm theo kết quả', 2), ('Chọn người thân với mình hơn', 0), ('Để hai bên tự thỏa thuận', 1)),
    _q('x6', 'Đối tác gửi “quà cảm ơn” mong được ưu tiên giờ bay đẹp.', ('Trả lại, ghi nhận công khai', 2), ('Nhận rồi tính sau', 0), ('Nhận, chia cho phòng điều phái', 0)),
]
QUESTIONS['exec_school'] = [
    _q('y1', 'Phụ huynh nhờ “nâng điểm” để con vào lớp chọn, kèm phong bì.', ('Từ chối, hướng dẫn phúc khảo đúng quy trình', 2), ('Nhận rồi tính', 0), ('Bảo giáo viên tự xử', 0)),
    _q('y2', 'Một giáo viên giỏi bị phụ huynh phản ánh nặng lời với học sinh.', ('Gặp riêng, nghe hai phía, cùng tìm cách sửa', 2), ('Bỏ qua vì cô ấy dạy giỏi', 0), ('Phê bình trước hội đồng ngay', 1)),
    _q('y3', 'Kinh phí sửa phòng học thiếu.', ('Lập kế hoạch công khai, xin hỗ trợ đúng quy định', 2), ('Thu thêm tiền phụ huynh bắt buộc', 0), ('Hoãn đến năm sau', 1)),
    _q('y4', 'Giáo viên trẻ xin nghỉ đúng tuần thi vì con ốm.', ('Duyệt, sắp xếp người dạy thay', 2), ('Không duyệt, tuần thi quan trọng hơn', 0), ('Duyệt nhưng trừ thi đua', 1)),
    _q('y5', 'Đoàn kiểm tra báo đến sáng mai.', ('Nhờ tổ trưởng rà hồ sơ trong giờ làm', 2), ('Bắt cả trường thức đêm làm lại hồ sơ', 0), ('Kệ, có sao nói vậy', 1)),
    _q('y6', 'Hai tổ chuyên môn tranh nhau phòng thực hành.', ('Xếp lịch luân phiên, công khai', 2), ('Ưu tiên tổ mình thân hơn', 0), ('Để hai tổ tự chia', 1)),
]
QUESTION_INDEX = {q['id']: q for rows in QUESTIONS.values() for q in rows}

# The pay ask after the questions (employees only). extra: raise points on top of the step's,
# given only when both answers were the best ones.
ASKS = [
    dict(id='base', label='Xin như khung', extra=0),
    dict(id='fair', label='Xin hợp lý', extra=2),
    dict(id='high', label='Xin cao', extra=4),
]
ASK_INDEX = {a['id']: a for a in ASKS}

# 🧑‍💼 Ca quản lý: the four kinds of work, each teammate is good at one and weak at another.
KINDS = ('khach', 'tay', 'so', 'gap')
KIND_ICON = {'khach': '🗣️', 'tay': '🔧', 'so': '📋', 'gap': '⚡'}
RESULT = {   # what a finished job shows: (good line, flawed line)
    'khach': ('🙂 Khách hài lòng', '⚠️ Khách còn thắc mắc'),
    'tay': ('🎯 Làm đúng yêu cầu', '⚠️ Còn chỗ làm ẩu'),
    'so': ('📋 Sổ khớp, đủ chữ ký', '⚠️ Lệch một dòng'),
    'gap': ('⏱️ Kịp giờ hẹn', '⚠️ Trễ hẹn'),
}

# Gỡ rối: small crises of a manager shift. {a}, {b}: teammates; {k}: a customer.
# fx per option: pts (manager points), mood (whole team), a_mood ({a} only), off ({a} goes home).
ESCALATIONS = [
    dict(id='e1', kind='complaint', text='😠 {k} phàn nàn việc {a} làm.', options=[
        dict(id='a', label='Nghe hết, xin lỗi, cho làm lại', pts=2, mood=5),
        dict(id='b', label='Bênh {a} trước mặt khách', pts=1, mood=0),
        dict(id='c', label='Trách {a} ngay tại chỗ', pts=0, mood=0, a_mood=-15)]),
    dict(id='e2', kind='complaint', text='😠 {k} đòi gặp người phụ trách.', options=[
        dict(id='a', label='Ra gặp ngay, hỏi rõ chuyện', pts=2, mood=5),
        dict(id='b', label='Nhờ {a} ra nói giúp', pts=1, mood=0),
        dict(id='c', label='Bảo khách mình đang bận', pts=0, mood=-5)]),
    dict(id='e3', kind='clash', text='⚡ {a} và {b} cãi nhau chuyện chia việc.', options=[
        dict(id='a', label='Gọi riêng hai người, chia lại rõ', pts=2, mood=10),
        dict(id='b', label='Tự làm phần đang cãi', pts=1, mood=0),
        dict(id='c', label='Mặc kệ hai người', pts=0, mood=-10)]),
    dict(id='e4', kind='clash', text='⚡ {a} chê {b} làm chậm.', options=[
        dict(id='a', label='Khen điểm mạnh từng người', pts=2, mood=10),
        dict(id='b', label='Nhắc chung cả nhóm', pts=1, mood=0),
        dict(id='c', label='Đứng về phía {a}', pts=0, mood=-10)]),
    dict(id='e5', kind='sick', text='🤒 {a} thấy mệt, xin về sớm.', options=[
        dict(id='a', label='Cho về nghỉ, chia lại việc', pts=2, mood=10, off=True),
        dict(id='b', label='Cho ngồi nghỉ 15 phút', pts=1, mood=0),
        dict(id='c', label='Bảo cố nốt ca', pts=0, mood=0, a_mood=-20)]),
    dict(id='e6', kind='sick', text='🤒 {a} bị đứt tay nhẹ.', options=[
        dict(id='a', label='Sơ cứu ngay, cho nghỉ tay', pts=2, mood=10),
        dict(id='b', label='Dán băng rồi làm tiếp', pts=1, mood=0),
        dict(id='c', label='Bảo lần sau cẩn thận', pts=0, mood=0, a_mood=-15)]),
]
ESCALATION_INDEX = {x['id']: x for x in ESCALATIONS}
CUSTOMER = 'Một vị khách'   # when the career's task has no customer name
