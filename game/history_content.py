"""📜 Lịch sử Việt Nam (game/history_course.py): twelve short lessons in time order, each with two practice
questions (checked on the server, retried freely) and two exam questions (the key stays on the server).

Feedback #255 (07/10): "học kế toán khó quá admin oiii học lịch sử đi ạ"; the owner: look the facts up in reputable
sources. Every date, name and fact here is listed with its source in docs/HISTORY_COURSE.md; a fact sources tell
differently (the year Âu Lạc began or ended, the month of the Diên Hồng meeting) is left out or written without
the disputed detail. Plain, neutral wording, no commentary.

Shapes:
* LESSONS: [{id, emoji, era, title, body[str ×3–5], practice[q ×2], exam[q ×2]}], in time order.
* q: {id, text, options[{id, label}] (3), answer, why}: exactly one right option.
"""
from __future__ import annotations


def _q(qid, text, options, answer, why):
    return dict(id=qid, text=text, options=[dict(id=k, label=v) for k, v in options], answer=answer, why=why)


def _l(lid, emoji, era, title, body, practice, exam):
    return dict(id=lid, emoji=emoji, era=era, title=title, body=body, practice=practice, exam=exam)


LESSONS = [
    _l('hung', '🥁', 'Thời dựng nước', 'Văn Lang – Âu Lạc', [
        'Theo truyền thuyết, các vua Hùng dựng nước Văn Lang, nhà nước đầu tiên của người Việt, ở vùng đồng bằng sông Hồng.',
        'Cư dân Văn Lang trồng lúa nước và đúc đồ đồng; trống đồng Ngọc Lũ là hiện vật tiêu biểu nhất của văn hóa Đông Sơn, nay là bảo vật quốc gia.',
        'Khoảng thế kỷ 3 trước Công nguyên, Thục Phán hợp nhất người Lạc Việt và Âu Việt, lập nước Âu Lạc và xưng là An Dương Vương.',
        'An Dương Vương xây thành Cổ Loa, nay thuộc Hà Nội.',
        'Giỗ Tổ Hùng Vương ngày 10/3 âm lịch là ngày nghỉ lễ; tín ngưỡng thờ cúng Hùng Vương ở Phú Thọ được UNESCO ghi danh năm 2012.',
    ], [
        _q('hung_p1', 'Theo truyền thuyết, nhà nước đầu tiên của người Việt tên là gì?',
           [('a', 'Văn Lang'), ('b', 'Đại Việt'), ('c', 'Vạn Xuân')], 'a',
           'Các vua Hùng dựng nước Văn Lang ở vùng đồng bằng sông Hồng.'),
        _q('hung_p2', 'Ai cho xây thành Cổ Loa?',
           [('a', 'Ngô Quyền'), ('b', 'An Dương Vương'), ('c', 'Lý Công Uẩn')], 'b',
           'An Dương Vương (Thục Phán) lập nước Âu Lạc và xây thành Cổ Loa.'),
    ], [
        _q('hung_e1', 'Trống đồng Ngọc Lũ là hiện vật tiêu biểu của nền văn hóa nào?',
           [('a', 'Văn hóa Óc Eo'), ('b', 'Văn hóa Sa Huỳnh'), ('c', 'Văn hóa Đông Sơn')], 'c',
           'Trống đồng Ngọc Lũ là đỉnh cao của nghề đúc đồng thời Đông Sơn.'),
        _q('hung_e2', 'Giỗ Tổ Hùng Vương vào ngày nào?',
           [('a', 'Ngày 10/3 âm lịch'), ('b', 'Ngày 2/9'), ('c', 'Rằm tháng Tám')], 'a',
           'Giỗ Tổ Hùng Vương là ngày 10 tháng 3 âm lịch hằng năm.'),
    ]),
    _l('trung', '⚔️', 'Thế kỷ 1 – thế kỷ 6', 'Bắc thuộc và những cuộc khởi nghĩa', [
        'Sau thời Âu Lạc, đất nước bị các triều đại phương Bắc đô hộ hơn một nghìn năm, gọi là thời Bắc thuộc.',
        'Mùa xuân năm 40, Hai Bà Trưng (Trưng Trắc, Trưng Nhị) khởi nghĩa chống nhà Đông Hán; Trưng Trắc được tôn làm vua, đóng đô ở Mê Linh.',
        'Năm 43, quân Hán do Mã Viện chỉ huy dập tắt cuộc khởi nghĩa, nhưng Hai Bà vẫn được nhân dân đời đời thờ phụng.',
        'Năm 248, Bà Triệu (Triệu Thị Trinh) dựng cờ khởi nghĩa ở núi Nưa (Thanh Hóa) chống quân Ngô.',
        'Năm 544, Lý Bí lên ngôi, đặt tên nước là Vạn Xuân.',
    ], [
        _q('trung_p1', 'Hai Bà Trưng khởi nghĩa vào năm nào?',
           [('a', 'Năm 248'), ('b', 'Năm 40'), ('c', 'Năm 938')], 'b',
           'Mùa xuân năm 40, Hai Bà Trưng khởi nghĩa chống nhà Đông Hán.'),
        _q('trung_p2', 'Bà Triệu khởi nghĩa chống quân nào?',
           [('a', 'Quân Ngô'), ('b', 'Quân Mông – Nguyên'), ('c', 'Quân Thanh')], 'a',
           'Năm 248, Bà Triệu khởi nghĩa ở núi Nưa chống quân Ngô.'),
    ], [
        _q('trung_e1', 'Trưng Trắc lên làm vua, đóng đô ở đâu?',
           [('a', 'Hoa Lư'), ('b', 'Phú Xuân'), ('c', 'Mê Linh')], 'c',
           'Trưng Trắc được tôn làm vua và đóng đô ở Mê Linh.'),
        _q('trung_e2', 'Năm 544, Lý Bí đặt tên nước là gì?',
           [('a', 'Vạn Xuân'), ('b', 'Đại Cồ Việt'), ('c', 'Âu Lạc')], 'a',
           'Lý Bí lên ngôi năm 544 và đặt tên nước là Vạn Xuân.'),
    ]),
    _l('ngo', '🌊', 'Năm 938', 'Ngô Quyền và trận Bạch Đằng', [
        'Năm 938, quân Nam Hán do Lưu Hoằng Tháo chỉ huy theo đường biển kéo vào nước ta.',
        'Ngô Quyền cho cắm cọc gỗ vót nhọn, bịt sắt dưới lòng sông Bạch Đằng, rồi nhử thuyền giặc vào lúc nước triều lên.',
        'Khi nước triều rút, cọc nhô lên làm thuyền giặc vỡ đắm; quân mai phục hai bên bờ đánh ra và thắng lớn.',
        'Mùa xuân năm 939, Ngô Quyền xưng vương và đóng đô ở Cổ Loa.',
        'Chiến thắng Bạch Đằng chấm dứt hơn một nghìn năm Bắc thuộc, mở ra thời kỳ độc lập lâu dài.',
    ], [
        _q('ngo_p1', 'Năm 938, Ngô Quyền đánh thắng quân nào trên sông Bạch Đằng?',
           [('a', 'Quân Tống'), ('b', 'Quân Nam Hán'), ('c', 'Quân Minh')], 'b',
           'Quân Nam Hán do Lưu Hoằng Tháo chỉ huy bị đánh tan trên sông Bạch Đằng.'),
        _q('ngo_p2', 'Ngô Quyền dùng cách gì để phá thuyền giặc?',
           [('a', 'Cắm cọc nhọn dưới lòng sông và chờ nước triều rút'), ('b', 'Xây một bức tường đá chắn ngang sông'),
            ('c', 'Đào hào quanh kinh thành')], 'a',
           'Cọc nhọn bịt sắt cắm dưới sông, nước triều rút thì cọc nhô lên đâm thủng thuyền giặc.'),
    ], [
        _q('ngo_e1', 'Mùa xuân năm 939, Ngô Quyền đóng đô ở đâu?',
           [('a', 'Thăng Long'), ('b', 'Hoa Lư'), ('c', 'Cổ Loa')], 'c',
           'Ngô Quyền xưng vương và chọn Cổ Loa, kinh đô cũ của Âu Lạc.'),
        _q('ngo_e2', 'Chiến thắng Bạch Đằng năm 938 có ý nghĩa gì?',
           [('a', 'Mở đầu nhà Nguyễn'), ('b', 'Chấm dứt thời Bắc thuộc, mở ra thời kỳ độc lập lâu dài'),
            ('c', 'Dời kinh đô ra Thăng Long')], 'b',
           'Sau Bạch Đằng 938, nước ta bước vào thời kỳ độc lập lâu dài.'),
    ]),
    _l('dinh_le', '🐎', '968 – 1009', 'Nhà Đinh, nhà Tiền Lê', [
        'Sau khi Ngô Quyền mất, đất nước rơi vào cảnh mười hai sứ quân cát cứ.',
        'Đinh Bộ Lĩnh dẹp yên các sứ quân; năm 968 ông lên ngôi hoàng đế (Đinh Tiên Hoàng), đặt tên nước là Đại Cồ Việt và đóng đô ở Hoa Lư.',
        'Năm 970, nhà vua thôi dùng niên hiệu của hoàng đế phương Bắc, đặt niên hiệu riêng là Thái Bình.',
        'Năm 980, Lê Hoàn lên ngôi, lập nhà Tiền Lê; mùa xuân năm 981, ông lãnh đạo quân dân đánh thắng quân Tống.',
    ], [
        _q('dinh_le_p1', 'Năm 968, Đinh Tiên Hoàng đặt tên nước là gì?',
           [('a', 'Văn Lang'), ('b', 'Đại Nam'), ('c', 'Đại Cồ Việt')], 'c',
           'Nhà Đinh đặt tên nước là Đại Cồ Việt.'),
        _q('dinh_le_p2', 'Kinh đô của nhà Đinh ở đâu?',
           [('a', 'Hoa Lư'), ('b', 'Huế'), ('c', 'Cổ Loa')], 'a',
           'Đinh Tiên Hoàng đóng đô ở Hoa Lư.'),
    ], [
        _q('dinh_le_e1', 'Đinh Bộ Lĩnh thống nhất đất nước sau khi dẹp loạn gì?',
           [('a', 'Cuộc xâm lược của quân Mông – Nguyên'), ('b', 'Loạn mười hai sứ quân'), ('c', 'Cuộc khởi nghĩa Tây Sơn')], 'b',
           'Đinh Bộ Lĩnh dẹp yên mười hai sứ quân rồi lên ngôi năm 968.'),
        _q('dinh_le_e2', 'Năm 981, ai lãnh đạo kháng chiến chống Tống thắng lợi?',
           [('a', 'Lê Hoàn'), ('b', 'Lê Lợi'), ('c', 'Trần Hưng Đạo')], 'a',
           'Lê Hoàn lên ngôi năm 980 và đánh thắng quân Tống mùa xuân năm 981.'),
    ]),
    _l('ly', '🐉', '1009 – 1225', 'Nhà Lý và kinh đô Thăng Long', [
        'Năm 1009, Lý Công Uẩn lên ngôi, mở đầu nhà Lý.',
        'Năm 1010, nhà vua ban Chiếu dời đô, chuyển kinh đô từ Hoa Lư về thành Đại La và đặt tên mới là Thăng Long, nghĩa là rồng bay lên.',
        'Năm 1054, nhà Lý đổi tên nước thành Đại Việt; năm 1070 xây Văn Miếu, năm 1076 lập Quốc Tử Giám.',
        'Năm 1077, Lý Thường Kiệt chặn đứng quân Tống ở phòng tuyến sông Như Nguyệt; bài thơ Nam quốc sơn hà gắn với trận đánh này.',
        'Hoàng thành Thăng Long được UNESCO ghi danh là di sản văn hóa thế giới năm 2010.',
    ], [
        _q('ly_p1', 'Năm 1010, Lý Công Uẩn dời đô về đâu?',
           [('a', 'Phú Xuân'), ('b', 'Thành Đại La, đặt tên là Thăng Long'), ('c', 'Cổ Loa')], 'b',
           'Chiếu dời đô năm 1010 chuyển kinh đô từ Hoa Lư về Đại La, đổi tên là Thăng Long.'),
        _q('ly_p2', 'Tên Thăng Long có nghĩa là gì?',
           [('a', 'Rồng bay lên'), ('b', 'Sông dài'), ('c', 'Núi cao')], 'a',
           'Thăng Long nghĩa là rồng bay lên.'),
    ], [
        _q('ly_e1', 'Văn Miếu ở Thăng Long được xây dưới triều nào?',
           [('a', 'Nhà Nguyễn'), ('b', 'Nhà Đinh'), ('c', 'Nhà Lý')], 'c',
           'Văn Miếu được xây năm 1070, thời nhà Lý.'),
        _q('ly_e2', 'Năm 1077, Lý Thường Kiệt chặn quân Tống ở đâu?',
           [('a', 'Phòng tuyến sông Như Nguyệt'), ('b', 'Rạch Gầm – Xoài Mút'), ('c', 'Gò Đống Đa')], 'a',
           'Quân Tống bị chặn ở phòng tuyến sông Như Nguyệt (một đoạn sông Cầu).'),
    ]),
    _l('tran', '🛡️', '1226 – 1400', 'Nhà Trần và ba lần thắng quân Mông – Nguyên', [
        'Năm 1226, nhà Trần thay nhà Lý, vẫn đóng đô ở Thăng Long.',
        'Trong ba mươi năm, quân Mông – Nguyên ba lần sang xâm lược, vào các năm 1258, 1285 và 1288, và cả ba lần đều bị đánh bại.',
        'Trước cuộc kháng chiến lần thứ hai, các bô lão họp ở điện Diên Hồng đồng thanh hô: "Đánh!"',
        'Hưng Đạo Đại Vương Trần Quốc Tuấn thống lĩnh toàn quân và viết Hịch tướng sĩ để khích lệ binh sĩ.',
        'Năm 1288, quân dân nhà Trần lại dùng trận địa cọc trên sông Bạch Đằng, tiêu diệt đoàn thuyền quân Nguyên.',
    ], [
        _q('tran_p1', 'Nhà Trần đánh thắng quân Mông – Nguyên mấy lần?',
           [('a', 'Hai lần'), ('b', 'Ba lần'), ('c', 'Năm lần')], 'b',
           'Ba lần: năm 1258, 1285 và 1288.'),
        _q('tran_p2', 'Ai thống lĩnh toàn quân nhà Trần chống quân Nguyên?',
           [('a', 'Lê Hoàn'), ('b', 'Quang Trung'), ('c', 'Trần Hưng Đạo')], 'c',
           'Hưng Đạo Đại Vương Trần Quốc Tuấn thống lĩnh toàn quân.'),
    ], [
        _q('tran_e1', 'Ở hội nghị Diên Hồng, các bô lão đồng thanh nói gì?',
           [('a', '"Đánh!"'), ('b', '"Hòa!"'), ('c', '"Chờ thêm!"')], 'a',
           'Các bô lão đồng thanh hô "Đánh!".'),
        _q('tran_e2', 'Trận Bạch Đằng năm 1288 đánh bại quân nào?',
           [('a', 'Quân Nam Hán'), ('b', 'Quân Nguyên'), ('c', 'Quân Thanh')], 'b',
           'Năm 1288, đoàn thuyền quân Nguyên bị tiêu diệt trên sông Bạch Đằng.'),
    ]),
    _l('lam_son', '🗡️', '1418 – 1428', 'Lê Lợi và khởi nghĩa Lam Sơn', [
        'Đầu thế kỷ 15, nhà Minh sang đô hộ nước ta.',
        'Năm 1418, Lê Lợi dựng cờ khởi nghĩa chống quân Minh ở Lam Sơn (Thanh Hóa), xưng là Bình Định Vương; Nguyễn Trãi cùng ông bàn mưu kế.',
        'Sau mười năm, nghĩa quân thắng trận quyết định Chi Lăng – Xương Giang năm 1427.',
        'Năm 1428, Lê Lợi lên ngôi, lập nhà Hậu Lê, tên nước vẫn là Đại Việt; Nguyễn Trãi viết Bình Ngô đại cáo.',
        'Truyền thuyết kể rằng sau chiến thắng, Rùa Vàng đã đòi lại gươm báu, nên hồ Lục Thủy được gọi là hồ Hoàn Kiếm.',
    ], [
        _q('lam_son_p1', 'Lê Lợi khởi nghĩa chống quân nào?',
           [('a', 'Quân Tống'), ('b', 'Quân Xiêm'), ('c', 'Quân Minh')], 'c',
           'Khởi nghĩa Lam Sơn chống ách đô hộ của nhà Minh.'),
        _q('lam_son_p2', 'Ai viết Bình Ngô đại cáo?',
           [('a', 'Nguyễn Trãi'), ('b', 'Nguyễn Du'), ('c', 'Trần Hưng Đạo')], 'a',
           'Nguyễn Trãi viết Bình Ngô đại cáo năm 1428.'),
    ], [
        _q('lam_son_e1', 'Khởi nghĩa Lam Sơn bắt đầu năm nào?',
           [('a', 'Năm 1010'), ('b', 'Năm 1418'), ('c', 'Năm 1789')], 'b',
           'Lê Lợi dựng cờ khởi nghĩa năm 1418.'),
        _q('lam_son_e2', 'Trận quyết định của nghĩa quân Lam Sơn năm 1427 là trận nào?',
           [('a', 'Chi Lăng – Xương Giang'), ('b', 'Ngọc Hồi – Đống Đa'), ('c', 'Như Nguyệt')], 'a',
           'Chi Lăng – Xương Giang năm 1427 kết thúc mười năm kháng chiến.'),
    ]),
    _l('quang_trung', '🐘', '1771 – 1789', 'Quang Trung và Ngọc Hồi – Đống Đa', [
        'Mùa xuân năm 1771, ba anh em Nguyễn Nhạc, Nguyễn Huệ, Nguyễn Lữ khởi nghĩa ở Tây Sơn.',
        'Năm 1785, Nguyễn Huệ đánh tan quân Xiêm ở Rạch Gầm – Xoài Mút trên sông Mỹ Tho.',
        'Cuối năm 1788, Nguyễn Huệ lên ngôi hoàng đế, lấy niên hiệu Quang Trung, rồi tiến quân ra Bắc đánh quân Thanh.',
        'Mùa xuân Kỷ Dậu 1789, quân Tây Sơn đánh tan quân Thanh ở Ngọc Hồi – Đống Đa; sáng mùng 5 Tết, vua Quang Trung tiến vào Thăng Long.',
        'Ngày nay, hội gò Đống Đa ở Hà Nội vẫn mở vào mùng 5 Tết để tưởng nhớ chiến thắng này.',
    ], [
        _q('quang_trung_p1', 'Nguyễn Huệ lên ngôi lấy niên hiệu gì?',
           [('a', 'Gia Long'), ('b', 'Quang Trung'), ('c', 'Thuận Thiên')], 'b',
           'Cuối năm 1788, Nguyễn Huệ lên ngôi, niên hiệu Quang Trung.'),
        _q('quang_trung_p2', 'Chiến thắng Ngọc Hồi – Đống Đa đánh bại quân nào?',
           [('a', 'Quân Thanh'), ('b', 'Quân Minh'), ('c', 'Quân Xiêm')], 'a',
           'Mùa xuân 1789, quân Tây Sơn đánh tan quân Thanh.'),
    ], [
        _q('quang_trung_e1', 'Năm 1785, quân Tây Sơn đánh tan quân Xiêm ở đâu?',
           [('a', 'Sông Bạch Đằng'), ('b', 'Điện Biên Phủ'), ('c', 'Rạch Gầm – Xoài Mút')], 'c',
           'Trận Rạch Gầm – Xoài Mút diễn ra trên sông Mỹ Tho năm 1785.'),
        _q('quang_trung_e2', 'Năm 1789, vua Quang Trung tiến vào Thăng Long vào ngày nào?',
           [('a', 'Sáng mùng 5 Tết'), ('b', 'Rằm tháng Giêng'), ('c', 'Ngày 2/9')], 'a',
           'Sáng mùng 5 Tết Kỷ Dậu, vua Quang Trung vào Thăng Long.'),
    ]),
    _l('nguyen', '🏯', '1802 – 1945', 'Nhà Nguyễn và tên nước Việt Nam', [
        'Năm 1802, Nguyễn Ánh lên ngôi, lấy niên hiệu Gia Long, lập nhà Nguyễn và đóng đô ở Phú Xuân (Huế).',
        'Năm 1804, vua Gia Long đặt quốc hiệu là Việt Nam.',
        'Ngày 1/9/1858, liên quân Pháp – Tây Ban Nha nổ súng đánh Đà Nẵng, mở đầu cuộc xâm lược của thực dân Pháp.',
        'Quần thể di tích Cố đô Huế là di sản thế giới đầu tiên của Việt Nam, được UNESCO ghi danh năm 1993.',
        'Ngày 30/8/1945, vua Bảo Đại thoái vị ở Ngọ Môn (Huế), khép lại chế độ quân chủ.',
    ], [
        _q('nguyen_p1', 'Kinh đô của nhà Nguyễn ở đâu?',
           [('a', 'Hoa Lư'), ('b', 'Cổ Loa'), ('c', 'Phú Xuân (Huế)')], 'c',
           'Nhà Nguyễn đóng đô ở Phú Xuân, tức Huế.'),
        _q('nguyen_p2', 'Quốc hiệu Việt Nam được đặt năm nào?',
           [('a', 'Năm 1804'), ('b', 'Năm 1010'), ('c', 'Năm 1975')], 'a',
           'Năm 1804, vua Gia Long đặt quốc hiệu Việt Nam.'),
    ], [
        _q('nguyen_e1', 'Vị vua cuối cùng của nhà Nguyễn là ai?',
           [('a', 'Gia Long'), ('b', 'Bảo Đại'), ('c', 'Minh Mạng')], 'b',
           'Vua Bảo Đại thoái vị ngày 30/8/1945.'),
        _q('nguyen_e2', 'Di sản thế giới đầu tiên của Việt Nam được UNESCO ghi danh là gì?',
           [('a', 'Quần thể di tích Cố đô Huế'), ('b', 'Hoàng thành Thăng Long'), ('c', 'Thành Cổ Loa')], 'a',
           'Quần thể di tích Cố đô Huế được ghi danh năm 1993, sớm nhất ở Việt Nam.'),
    ]),
    _l('doc_lap', '🇻🇳', '1945 – 1954', 'Độc lập 1945 và Điện Biên Phủ', [
        'Tháng 8/1945, Cách mạng tháng Tám giành chính quyền trong cả nước.',
        'Ngày 2/9/1945, tại Quảng trường Ba Đình (Hà Nội), Chủ tịch Hồ Chí Minh đọc Tuyên ngôn Độc lập, khai sinh nước Việt Nam Dân chủ Cộng hòa; ngày 2/9 trở thành ngày Quốc khánh.',
        'Ngày 7/5/1954, sau 56 ngày đêm, chiến dịch Điện Biên Phủ toàn thắng.',
        'Tháng 7/1954, Hiệp định Giơ-ne-vơ được ký, chấm dứt chiến tranh ở Đông Dương và lấy vĩ tuyến 17 làm giới tuyến quân sự tạm thời.',
    ], [
        _q('doc_lap_p1', 'Tuyên ngôn Độc lập ngày 2/9/1945 được đọc ở đâu?',
           [('a', 'Ngọ Môn (Huế)'), ('b', 'Quảng trường Ba Đình (Hà Nội)'), ('c', 'Thành Cổ Loa')], 'b',
           'Chủ tịch Hồ Chí Minh đọc Tuyên ngôn Độc lập tại Quảng trường Ba Đình.'),
        _q('doc_lap_p2', 'Ngày Quốc khánh của Việt Nam là ngày nào?',
           [('a', 'Ngày 2/9'), ('b', 'Ngày 30/4'), ('c', 'Ngày 1/5')], 'a',
           'Ngày 2/9/1945 nước Việt Nam Dân chủ Cộng hòa ra đời, nay là ngày Quốc khánh.'),
    ], [
        _q('doc_lap_e1', 'Chiến dịch Điện Biên Phủ toàn thắng vào ngày nào?',
           [('a', 'Ngày 2/9/1945'), ('b', 'Ngày 30/4/1975'), ('c', 'Ngày 7/5/1954')], 'c',
           'Ngày 7/5/1954, sau 56 ngày đêm.'),
        _q('doc_lap_e2', 'Hiệp định Giơ-ne-vơ năm 1954 lấy vĩ tuyến nào làm giới tuyến quân sự tạm thời?',
           [('a', 'Vĩ tuyến 38'), ('b', 'Vĩ tuyến 17'), ('c', 'Vĩ tuyến 20')], 'b',
           'Vĩ tuyến 17 là giới tuyến quân sự tạm thời.'),
    ]),
    _l('thong_nhat', '🕊️', '1975 – 1976', 'Thống nhất đất nước', [
        'Sau năm 1954, đất nước tạm chia làm hai miền và chiến tranh kéo dài nhiều năm.',
        'Ngày 30/4/1975, chiến tranh kết thúc, đất nước thống nhất; ngày 30/4 là ngày nghỉ lễ của cả nước.',
        'Ngày 25/4/1976, cử tri cả nước đi bầu Quốc hội chung đầu tiên.',
        'Ngày 2/7/1976, Quốc hội đặt tên nước là Cộng hòa xã hội chủ nghĩa Việt Nam, thủ đô là Hà Nội, và đổi tên Sài Gòn thành Thành phố Hồ Chí Minh.',
    ], [
        _q('thong_nhat_p1', 'Đất nước thống nhất vào ngày nào?',
           [('a', 'Ngày 7/5/1954'), ('b', 'Ngày 30/4/1975'), ('c', 'Ngày 2/9/1945')], 'b',
           'Ngày 30/4/1975, chiến tranh kết thúc, đất nước thống nhất.'),
        _q('thong_nhat_p2', 'Năm 1976, Sài Gòn được đổi tên thành gì?',
           [('a', 'Gia Định'), ('b', 'Phú Xuân'), ('c', 'Thành phố Hồ Chí Minh')], 'c',
           'Ngày 2/7/1976, Quốc hội đổi tên Sài Gòn thành Thành phố Hồ Chí Minh.'),
    ], [
        _q('thong_nhat_e1', 'Năm 1976, Quốc hội đặt tên nước là gì?',
           [('a', 'Cộng hòa xã hội chủ nghĩa Việt Nam'), ('b', 'Đại Việt'), ('c', 'Việt Nam Dân chủ Cộng hòa')], 'a',
           'Tên nước Cộng hòa xã hội chủ nghĩa Việt Nam có từ ngày 2/7/1976.'),
        _q('thong_nhat_e2', 'Thủ đô của nước Việt Nam thống nhất là thành phố nào?',
           [('a', 'Huế'), ('b', 'Hà Nội'), ('c', 'Thành phố Hồ Chí Minh')], 'b',
           'Quốc hội năm 1976 chọn Hà Nội làm thủ đô.'),
    ]),
    _l('doi_moi', '🌱', 'Từ năm 1986', 'Đổi Mới và hội nhập', [
        'Tháng 12/1986, Đại hội VI của Đảng Cộng sản Việt Nam đề ra đường lối Đổi Mới, trước hết là đổi mới tư duy kinh tế.',
        'Nền kinh tế chuyển sang kinh tế thị trường định hướng xã hội chủ nghĩa và mở cửa hội nhập quốc tế.',
        'Ngày 28/7/1995, Việt Nam gia nhập ASEAN, là thành viên thứ bảy.',
        'Ngày 11/1/2007, Việt Nam chính thức trở thành thành viên thứ 150 của Tổ chức Thương mại Thế giới (WTO).',
    ], [
        _q('doi_moi_p1', 'Đường lối Đổi Mới được đề ra năm nào?',
           [('a', 'Năm 1975'), ('b', 'Năm 2007'), ('c', 'Năm 1986')], 'c',
           'Đại hội VI tháng 12/1986 đề ra đường lối Đổi Mới.'),
        _q('doi_moi_p2', 'Việt Nam gia nhập ASEAN năm nào?',
           [('a', 'Năm 1995'), ('b', 'Năm 1954'), ('c', 'Năm 1010')], 'a',
           'Ngày 28/7/1995, Việt Nam trở thành thành viên thứ bảy của ASEAN.'),
    ], [
        _q('doi_moi_e1', 'Việt Nam chính thức trở thành thành viên WTO năm nào?',
           [('a', 'Năm 1986'), ('b', 'Năm 2007'), ('c', 'Năm 1945')], 'b',
           'Ngày 11/1/2007, Việt Nam là thành viên thứ 150 của WTO.'),
        _q('doi_moi_e2', 'Đổi Mới trước hết là đổi mới điều gì?',
           [('a', 'Tư duy kinh tế'), ('b', 'Kinh đô'), ('c', 'Tên nước')], 'a',
           'Đại hội VI nhấn mạnh trước hết là đổi mới tư duy kinh tế.'),
    ]),
]
