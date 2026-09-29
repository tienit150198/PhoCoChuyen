"""Hiring content for the careers that joined the job hunt in v0.5.

Pharmacy and tour guide start with a licence exam, customer care ends with a
situational test (the shift lead plays a difficult customer), and the hired
trades (salon, pet care, repair, delivery) take you on after a short hands-on
trial with the owner. Everything is fictional; wages are game coins.

Shapes (read by game/employment.py):
* postings: the usual posting dict plus `stages`, `boss`, `wage_note` and,
  depending on the stages, `exam` (career id of the exam), `test` or `trial`
  (lists of step ids, same shape as interview questions).
* QUESTIONS: interview questions, test scenarios and trial steps:
  {text, options[{id, label, score 0..3, note, fatal?}]}; `fatal` = unsafe move.
* EXAMS: {id, name, issuer, pass_mark, draw, bank[{id, text, options[{id, label}], answer, why}]}.
"""
from __future__ import annotations


def _o(oid, label, score, note, fatal=False):
    row = dict(id=oid, label=label, score=score, note=note)
    if fatal:
        row['fatal'] = True
    return row


def _q(text, *options):
    return dict(text=text, options=list(options))


def _e(qid, text, options, answer, why):
    return dict(id=qid, text=text, options=[dict(id=k, label=v) for k, v in options], answer=answer, why=why)


# ---------------------------------------------------------------- exams
EXAMS = {
    'pharmacy': dict(
        id='ph-cert', name='Chứng chỉ Nhân viên quầy thuốc', issuer='Tổ y tế phường (bài kiểm tra giả lập)',
        pass_mark=4, draw=5, emoji='💊',
        intro='Năm câu về quy trình an toàn ở quầy: đọc mã, soát lô, hạn dùng, bảo mật. Không có câu nào hỏi liều thuốc — việc đó của người có chuyên môn.',
        bank=[
            _e('ph_e_code', 'Phiếu ghi mã P-03. Trên kệ có hai hộp cùng màu xanh. Bạn lấy hộp nào?',
               [('a', 'Hộp màu giống nhất với lần trước khách mua'), ('b', 'Hộp in đúng mã P-03, đọc đủ cả mã'),
                ('c', 'Hộp gần tay nhất rồi hỏi khách đúng không')], 'b',
               'Bao bì có thể trùng màu; chỉ mã in trên hộp mới chắc chắn.'),
            _e('ph_e_lot', 'Hộp đúng mã nhưng lô đang dán nhãn “tạm giữ”. Bạn làm gì?',
               [('a', 'Không giao lô đó; lấy lô đủ điều kiện hoặc báo người phụ trách'), ('b', 'Giao vì mã vẫn đúng'),
                ('c', 'Giao nhưng giảm giá cho khách')], 'a',
               'Lô tạm giữ đang chờ kiểm tra, chưa được bán ra.'),
            _e('ph_e_expiry', 'Hộp hết hạn từ hôm qua. Khách nói: “Dùng ngay thôi, không sao đâu.”',
               [('a', 'Giao vì khách đã đồng ý'), ('b', 'Giao và ghi chú lại vào sổ'),
                ('c', 'Không giao hộp hết hạn; đổi hộp còn hạn')], 'c',
               'Hạn dùng không phụ thuộc vào việc khách đồng ý.'),
            _e('ph_e_dose', 'Khách hỏi “uống mấy viên thì mau khỏi?”, phiếu không ghi liều. Bạn làm gì?',
               [('a', 'Không tự đưa liều; mời cô Thu hoặc hướng dẫn khách hỏi lại nơi kê phiếu'),
                ('b', 'Nói theo kinh nghiệm của nhà mình'), ('c', 'Khuyên uống gấp đôi cho mau khỏi')], 'a',
               'Nhân viên quầy không tự tư vấn liều; việc đó thuộc người có chuyên môn.'),
            _e('ph_e_current', 'Trước khi giao thêm một món mới, bạn nên hỏi khách điều gì?',
               [('a', 'Có muốn mua thêm vitamin không'), ('b', 'Đang dùng thuốc nào khác, có dị ứng gì không'),
                ('c', 'Không cần hỏi, có phiếu là đủ')], 'b',
               'Thuốc trùng hoặc dị ứng phải báo người phụ trách trước khi giao.'),
            _e('ph_e_privacy', 'Hàng xóm hỏi nhỏ: “Bà Sáu vừa mua thuốc gì vậy con?”',
               [('a', 'Kể vì ai cũng là hàng xóm'), ('b', 'Nói úp mở cho vui'),
                ('c', 'Không tiết lộ; chuyện mua thuốc là thông tin riêng')], 'c',
               'Phiếu và món khách mua là thông tin riêng tư.'),
            _e('ph_e_store', 'Hộp ghi “bảo quản dưới 25°C, tránh ánh nắng”. Bạn đặt ở đâu?',
               [('a', 'Kệ mát, khuất nắng, đúng khu đã quy định'), ('b', 'Cạnh cửa kính cho khách dễ thấy'),
                ('c', 'Trên nóc tủ lạnh cho mát')], 'a',
               'Nóc tủ lạnh thường nóng vì dàn tản nhiệt; cửa kính thì nắng rọi.'),
            _e('ph_e_unclear', 'Phiếu viết tay, một chữ trong tên hộp đọc không ra. Bạn làm gì?',
               [('a', 'Đoán theo chữ gần giống nhất'), ('b', 'Không đoán; hỏi lại nơi kê phiếu hoặc nhờ cô Thu xem'),
                ('c', 'Hỏi khách “chắc là hộp này ha?”')], 'b',
               'Không bao giờ giao theo phỏng đoán.'),
            _e('ph_e_child', 'Một bạn nhỏ chừng 10 tuổi cầm phiếu tới mua một mình.',
               [('a', 'Giao luôn vì đã có phiếu'), ('b', 'Không bán và bảo về nhà'),
                ('c', 'Hỏi người lớn đi cùng hoặc gọi phụ huynh trước khi giao')], 'c',
               'Trẻ nhỏ không nên tự nhận và tự dùng thuốc; người lớn cần biết.'),
        ]),
    'tour_guide': dict(
        id='tg-card', name='Thẻ hướng dẫn viên khu phố', issuer='Ban Du lịch phường (bài kiểm tra giả lập)',
        pass_mark=4, draw=5, emoji='🧭',
        intro='Năm câu về các điểm trong phố và an toàn khi dẫn đoàn: đếm người, mưa, nắng, qua đường, lạc đoàn.',
        bank=[
            _e('tg_e_rain', 'Trời đổ mưa rào. Điểm nào trong phố tạm đóng?',
               [('a', 'Nhà Gốm Kể Chuyện'), ('b', 'Lối Bờ Mây'), ('c', 'Hiên Trà Nghỉ Chân')], 'b',
               'Lối Bờ Mây đi dọc bờ sông, trơn khi mưa; chọn điểm có mái che.'),
            _e('tg_e_indoor', 'Điểm nào có mái che, hợp để đưa đoàn vào khi mưa?',
               [('a', 'Chợ Mây Sớm'), ('b', 'Vườn Lá Nhỏ'), ('c', 'Bến Mây')], 'a',
               'Chợ Mây Sớm, Nhà Gốm và Hiên Trà đều có mái che.'),
            _e('tg_e_symbol', 'Biểu tượng của Nhà Gốm Kể Chuyện là gì?',
               [('a', 'Thuyền giấy màu xanh'), ('b', 'Đèn lồng hình ngôi sao'), ('c', 'Chiếc bình có ba chiếc lá')], 'c',
               'Thuyền giấy ở Bến Mây, đèn lồng sao ở chợ, bình ba lá ở Nhà Gốm.'),
            _e('tg_e_count', 'Khi nào người dẫn đoàn phải đếm đủ người?',
               [('a', 'Chỉ lúc xuất phát'), ('b', 'Trước khi khởi hành và sau mỗi điểm dừng'), ('c', 'Khi có ai hỏi')], 'b',
               'Lạc đoàn thường xảy ra lúc rời một điểm dừng.'),
            _e('tg_e_lost', 'Một khách lạc đoàn ở chợ. Việc đầu tiên?',
               [('a', 'Cả đoàn tản ra đi tìm'),
                ('b', 'Giữ đoàn ở điểm hẹn an toàn, gọi điện cho khách, báo quầy thông tin chợ'),
                ('c', 'Đi tiếp, lát khách tự tìm về')], 'b',
               'Không để lạc thêm người; có điểm hẹn và người báo tin.'),
            _e('tg_e_cross', 'Đoàn cần qua một con đường đông xe.',
               [('a', 'Dừng đoàn, qua ở vạch hoặc chỗ có đèn; người dẫn đi đầu, người phụ đi cuối'),
                ('b', 'Bảo mọi người tự băng qua cho nhanh'), ('c', 'Qua trước rồi vẫy tay gọi')], 'a',
               'Đoàn đi thành một khối, có người đầu và người cuối.'),
            _e('tg_e_heat', 'Một bác lớn tuổi trong đoàn chóng mặt dưới nắng.',
               [('a', 'Động viên đi tiếp cho kịp lịch'), ('b', 'Đưa bác thuốc của mình'),
                ('c', 'Đưa vào chỗ mát, cho nghỉ, uống nước; không đỡ thì gọi cấp cứu 115')], 'c',
               'Sức khỏe trước lịch trình; không tự cho thuốc.'),
            _e('tg_e_free', 'Điểm nào vào cửa miễn phí?',
               [('a', 'Vườn Lá Nhỏ'), ('b', 'Nhà Gốm Kể Chuyện'), ('c', 'Hiên Trà Nghỉ Chân')], 'a',
               'Bến Mây, Vườn Lá Nhỏ và Lối Bờ Mây không thu phí.'),
            _e('tg_e_commission', 'Tiệm lưu niệm đề nghị trả hoa hồng nếu bạn dẫn đoàn ghé.',
               [('a', 'Ghé mọi chuyến và kéo dài giờ mua sắm'), ('b', 'Nói với khách đó là điểm bắt buộc'),
                ('c', 'Chỉ ghé khi hợp nhu cầu đoàn, nói rõ, không ép mua')], 'c',
               'Đoàn trả tiền cho trải nghiệm, không phải cho hoa hồng của người dẫn.'),
        ]),
}

# ---------------------------------------------------------------- interview / test / trial steps
QUESTIONS = {
    # Pharmacy: interview with cô Thu.
    'ph_rush': _q('Giờ tan tầm, năm người xếp hàng, một khách giục “lấy nhanh giùm, khỏi kiểm”. Cô Thu hỏi: con làm sao?',
                  _o('steady', 'Chào khách, xin chờ một chút; vẫn đọc mã, soát lô, đếm số lượng rồi mới giao', 3, 'Cô Thu gật đầu: “Chậm một nhịp, đúng từng chi tiết.”'),
                  _o('skip', 'Bỏ bước soát lô cho kịp', 0, 'Cô Thu lắc đầu: “Sai một hộp là không rút lại được.”'),
                  _o('send', 'Mời khách qua nhà thuốc khác', 1, 'Không sai quy trình nhưng mất khách của quầy.')),
    'ph_advice': _q('Cô Thu đang bận. Một khách xin con “chọn giùm thuốc ho cho con nít”.',
                    _o('wait', 'Mời khách chờ cô Thu, hoặc khuyên đưa bé đi khám; con không tự chọn thuốc', 3, 'Cô Thu: “Biết mình được làm tới đâu là điều cô cần nhất.”'),
                    _o('pick', 'Chọn chai siro nhiều người mua', 0, 'Trẻ nhỏ mỗi bé mỗi khác; việc này không phải của nhân viên quầy.'),
                    _o('search', 'Tra mạng rồi đưa theo', 0, 'Thông tin trên mạng không thay được người có chuyên môn.')),
    'ph_why': _q('Vì sao con muốn làm ở quầy thuốc?',
                 _o('care', 'Con thích việc cần cẩn thận, muốn người trong phố lấy đúng thứ họ cần', 3, 'Cô Thu mỉm cười.'),
                 _o('pay', 'Vì lương ổn định', 1, 'Thật thà, nhưng cô muốn nghe thêm.'),
                 _o('easy', 'Vì nghe nói việc nhẹ, chỉ đưa hộp', 0, 'Cô Thu nhướng mày: việc nhẹ tay nhưng nặng trách nhiệm.')),
    # Customer care: interview with chị Mai…
    'cc_listen': _q('Một khách gọi lần thứ ba về cùng một việc. Câu đầu tiên của bạn?',
                    _o('read', 'Đọc lịch sử trước, tóm tắt lại điều đã biết để khách không phải kể lại', 3, 'Chị Mai: “Đúng thứ khách cần nghe nhất.”'),
                    _o('again', 'Xin khách kể lại từ đầu cho chắc', 1, 'Khách thở dài lần thứ ba.'),
                    _o('transfer', 'Chuyển ngay sang bộ phận khác', 0, 'Việc lại đi thêm một vòng.')),
    'cc_promise': _q('Bạn chưa chắc kho xử lý kịp trong hôm nay. Bạn hẹn khách thế nào?',
                     _o('milestone', 'Hẹn một mốc mình kiểm soát được và gọi lại đúng hẹn', 3, 'Lời hẹn nhỏ mà giữ được.'),
                     _o('sure', '“Trong hôm nay chắc chắn xong ạ.”', 0, 'Hứa điều ngoài tầm tay là nợ khách một lần giận nữa.'),
                     _o('none', 'Không hẹn gì, xong thì báo', 1, 'Khách không biết chờ tới bao giờ.')),
    # …then the situational test: chị Mai plays a difficult customer.
    'cc_t_open': _q('Chị Mai đóng vai khách: “Tôi đặt hàng năm ngày rồi chưa tới! Các người làm ăn kiểu gì vậy?”',
                    _o('ack', 'Xin lỗi vì khách phải chờ, xác nhận mã đơn và nói mình kiểm ngay', 3, 'Khách vẫn bực, nhưng đã chịu đọc mã đơn.'),
                    _o('lecture', 'Giải thích dài về quy trình kho', 1, 'Khách ngắt lời: “Tôi không cần nghe quy trình.”'),
                    _o('calm', '“Anh bình tĩnh lại đã.”', 0, 'Bảo người đang giận “bình tĩnh” thường làm họ giận hơn.')),
    'cc_t_manager': _q('Khách: “Lần trước cũng hứa rồi! Cho tôi gặp quản lý ngay!”',
                       _o('own', 'Ghi nhận, nói rõ việc mình làm được ngay; nếu khách vẫn muốn thì chuyển quản lý kèm tóm tắt', 3, 'Khách: “Ừ… vậy cô làm đi, tôi nghe.”'),
                       _o('block', '“Quản lý bận, không gặp được đâu.”', 0, 'Khách dọa đăng lên mạng.'),
                       _o('dump', 'Chuyển máy luôn, không ghi chú', 1, 'Quản lý lại bắt khách kể từ đầu.')),
    'cc_t_demand': _q('Khách: “Bồi thường gấp đôi tiền hàng thì tôi mới thôi!”',
                      _o('policy', 'Nói rõ điều trạm làm được (hoàn phí ship, mã bù), không hứa ngoài quyền, hẹn mốc cập nhật', 3, 'Khách im một lúc rồi đồng ý chờ.'),
                      _o('yes', 'Đồng ý gấp đôi cho xong chuyện', 0, 'Hứa ngoài quyền: trạm phải gánh, lần sau khách lại đòi.'),
                      _o('no', '“Không có chuyện đó.”', 1, 'Đúng chính sách nhưng khách thấy bị gạt đi.')),
    'cc_t_abuse': _q('Khách bắt đầu xúc phạm: “Đồ vô dụng!”',
                     _o('boundary', 'Giữ giọng bình tĩnh, nhắc nhẹ ranh giới, đề nghị tiếp tục khi khách sẵn sàng', 3, 'Khách xin lỗi và nói tiếp chuyện đơn hàng.'),
                     _o('hangup', 'Cúp máy ngay', 1, 'Tự bảo vệ mình, nhưng việc của khách chưa xong.'),
                     _o('fight', 'Cãi lại cho khách biết', 0, 'Chị Mai dừng bài thử: “Ở trạm, mình không đáp trả xúc phạm.”', fatal=True)),
    # Tour guide: interview with anh Hải at the travel company.
    'tg_pace': _q('Đoàn có bác lớn tuổi đi chậm và hai bạn trẻ muốn đi nhanh. Bạn sắp nhịp thế nào?',
                  _o('split', 'Điểm dừng có ghế nghỉ, cho nhóm trẻ tự khám phá trong khu vực, hẹn giờ gom đoàn', 3, 'Anh Hải: “Ai cũng có phần của mình trong chuyến đi.”'),
                  _o('fast', 'Đi theo nhóm nhanh', 0, 'Bác lớn tuổi bị bỏ lại phía sau.'),
                  _o('slow', 'Bắt cả đoàn đi thật chậm', 1, 'An toàn nhưng nhóm trẻ chán.')),
    'tg_unknown': _q('Khách hỏi một chuyện về Nhà Gốm mà bạn không biết.',
                     _o('honest', 'Nói thật là chưa rõ, hỏi cô Gốm tại chỗ hoặc hẹn tìm hiểu rồi gửi lại', 3, 'Người dẫn đoàn đáng tin là người không bịa.'),
                     _o('invent', 'Bịa một chuyện cho vui', 0, 'Chuyện bịa sẽ theo khách về nhà và lên mạng.'),
                     _o('dodge', 'Lảng sang chuyện khác', 1, 'Khách nhận ra.')),
    'tg_rainplan': _q('Mưa đổ khi đoàn đang ở Vườn Lá Nhỏ.',
                      _o('shelter', 'Dẫn đoàn tới điểm có mái che gần nhất, đổi lộ trình, báo điều phối', 3, 'Anh Hải ghi chú: có kế hoạch B.'),
                      _o('wait', 'Đứng dưới gốc cây chờ tạnh', 1, 'Đứng dưới cây khi mưa giông không an toàn.'),
                      _o('go', 'Đi tiếp theo lịch, ướt chút không sao', 0, 'Lối Bờ Mây trơn trượt khi mưa.')),
    # Salon: trial with chị Phượng.
    'sl_consult': _q('Chị Phượng: “Khách này muốn tẩy lên màu khói. Em tư vấn thử đi.”',
                     _o('history', 'Hỏi lịch sử tóc (nhuộm, uốn, duỗi gần đây), xem tận mắt, thử thuốc sau tai trước', 3, 'Chị Phượng gật: “Hỏi trước khi làm, đúng nghề.”'),
                     _o('change', 'Khuyên khách chọn màu khác cho dễ', 1, 'Khách hơi tiếc; chị Phượng muốn em hỏi thêm.'),
                     _o('mix', 'Pha thuốc làm liền cho khách vui', 0, 'Tóc khách vừa duỗi tuần trước; tẩy liền là gãy tóc.', fatal=True)),
    'sl_wash': _q('Gội đầu cho một bác lớn tuổi hay đau cổ.',
                  _o('gentle', 'Hỏi nhiệt độ nước, lót khăn đỡ gáy, gội nhẹ, hỏi lại giữa chừng', 3, 'Bác khen êm tay.'),
                  _o('quick', 'Gội nhanh cho kịp khách sau', 1, 'Sạch nhưng bác nhăn mặt vì mỏi cổ.'),
                  _o('hot', 'Xả nước thật nóng cho sạch dầu', 0, 'Nước nóng làm bác giật mình, da đầu đỏ lên.')),
    'sl_clean': _q('Khách vừa đứng dậy, khách mới đã tới cửa.',
                   _o('sanitize', 'Thay khăn, khử khuẩn lược kéo, quét tóc rồi mới mời ngồi', 3, 'Chị Phượng: “Sạch sẽ là lời chào đầu tiên.”'),
                   _o('rush', 'Mời ngồi luôn, lau ghế sơ', 0, 'Khách thấy tóc người trước còn trên áo choàng.'),
                   _o('long', 'Bắt khách chờ hai mươi phút để tổng vệ sinh', 1, 'Kỹ quá mức cần, khách chờ lâu.')),
    'sl_timer': _q('Thuốc màu trên tóc khách đã đủ giờ nhà sản xuất ghi, nhưng thợ màu đang bận.',
                   _o('check', 'Thử một lọn, báo thợ màu, xả đúng giờ', 3, 'Màu lên đều, đúng mẫu.'),
                   _o('longer', 'Để thêm hai mươi phút cho màu đậm', 0, 'Quá giờ thuốc làm tóc khô cháy.'),
                   _o('alone', 'Tự xả, không báo ai', 1, 'Kịp giờ, nhưng thợ màu không biết để kiểm lại.')),
    # Pet care: trial with chị Nhàn.
    'pc_check': _q('Chị Nhàn giao cho bạn một bé Poodle để tắm. Việc đầu tiên?',
                   _o('intake', 'Xem sổ tiêm, hỏi chủ về dị ứng, kiểm da lông trước khi tắm', 3, 'Chị Nhàn: “Kiểm trước, làm sau. Được.”'),
                   _o('name', 'Hỏi tên bé rồi bắt đầu', 1, 'Thân thiện, nhưng thiếu bước kiểm.'),
                   _o('go', 'Tắm luôn cho kịp lịch', 0, 'Bé có vết xước ở chân, sữa tắm làm bé rát.')),
    'pc_scared': _q('Con mèo sợ máy sấy, bắt đầu gồng người và rít lên.',
                    _o('pause', 'Tắt máy, cho bé nghỉ, quấn khăn, sấy chế độ nhẹ để xa', 3, 'Bé dịu lại, chị Nhàn gật đầu.'),
                    _o('wet', 'Để ướt rồi trả chủ', 1, 'Bé không bị hoảng nhưng dễ lạnh.'),
                    _o('force', 'Giữ chặt để sấy cho nhanh', 0, 'Chị Nhàn dừng buổi thử: “Không bao giờ ép một bé đang hoảng.”', fatal=True)),
    'pc_nails': _q('Cắt móng cho chó móng đen, không thấy lòng móng.',
                   _o('bits', 'Cắt từng chút đầu móng, soi mặt cắt, dừng khi thấy chấm tối; để sẵn bột cầm máu', 3, 'Gọn, không chảy máu.'),
                   _o('skip', 'Bỏ qua, không cắt, không báo chủ', 1, 'An toàn nhưng chủ không biết.'),
                   _o('once', 'Cắt một nhát cho gọn', 0, 'Chạm lòng móng, bé kêu đau.')),
    'pc_lump': _q('Đang tắm, bạn thấy một cục u nhỏ dưới da bé.',
                  _o('tell', 'Báo chủ khi trả bé, khuyên đưa đi bác sĩ thú y; không tự chẩn đoán', 3, 'Chủ cảm ơn vì được báo sớm.'),
                  _o('guess', 'Nói với chủ là u lành, không sao đâu', 0, 'Bạn không phải bác sĩ thú y.'),
                  _o('quiet', 'Không nói gì cho chủ khỏi lo', 0, 'Chủ mất cơ hội đưa bé đi khám sớm.')),
    # Repair: trial with Chú Tư.
    'rp_fan': _q('Chú Tư đưa bạn cái quạt không quay: “Làm thử coi.”',
                 _o('measure', 'Hỏi khách bệnh, rút điện rồi mới mở, đo tụ và dây trước khi thay', 3, 'Chú Tư: “Đo trước, thay sau. Có nghề đó.”'),
                 _o('swap', 'Thay luôn tụ mới', 1, 'Có khi đúng, nhưng đoán mò tốn tiền khách.'),
                 _o('live', 'Cắm điện rồi thò tay xoay cánh xem kẹt không', 0, 'Chú Tư giật phích ra: “Mất an toàn điện, nghỉ thử!”', fatal=True)),
    'rp_quote': _q('Đã tìm ra lỗi: phải thay mô-tơ, tiền gần bằng quạt mới.',
                   _o('honest', 'Báo giá rõ, nói thật mua mới có thể hợp hơn, để khách chọn', 3, 'Khách tin tiệm hơn.'),
                   _o('fix', 'Cứ sửa rồi tính tiền sau', 0, 'Khách sốc khi nhận hóa đơn.'),
                   _o('refuse', 'Nói không sửa được', 1, 'Khách mất một lựa chọn.')),
    'rp_phone': _q('Khách gửi điện thoại thay màn hình, máy không khóa.',
                   _o('scope', 'Chỉ làm đúng phần màn hình; không mở ảnh, tin nhắn; ghi tình trạng máy vào phiếu', 3, 'Chú Tư: “Đồ của khách là của khách.”'),
                   _o('reset', 'Cài lại máy cho sạch', 0, 'Khách mất hết ảnh con.'),
                   _o('peek', 'Mở thư viện ảnh xem máy chạy chưa', 0, 'Tò mò dữ liệu khách là mất nghề.', fatal=True)),
    'rp_cord': _q('Nồi cơm điện có mùi khét, dây nguồn chảy nhựa.',
                  _o('replace', 'Báo khách ngưng dùng, thay dây đúng loại, đo cách điện trước khi giao', 3, 'An toàn trước.'),
                  _o('return', 'Trả máy, bảo khách tự lo', 1, 'Không nguy hiểm thêm, nhưng khách vẫn cần nồi.'),
                  _o('tape', 'Quấn băng keo lại cho nhanh', 0, 'Dây chảy nhựa quấn băng keo vẫn có thể chập cháy.', fatal=True)),
    # Delivery: a practice run with chị Hạnh.
    'dl_route': _q('Chị Hạnh giao bốn đơn: hai đơn hẹn giờ, một đơn hàng dễ vỡ, một đơn thu hộ (COD). Bạn xếp thế nào?',
                   _o('plan', 'Đơn hẹn giờ trước theo cụm đường, hàng dễ vỡ chằng riêng, đếm tiền COD ngay khi nhận', 3, 'Chị Hạnh: “Có lộ trình trong đầu rồi đó.”'),
                   _o('order', 'Đi theo thứ tự nhận đơn', 1, 'Một đơn hẹn giờ bị trễ.'),
                   _o('near', 'Đơn gần nhất trước, trễ hẹn thì gọi xin lỗi', 0, 'Hai khách hẹn giờ phải chờ.')),
    'dl_address': _q('Tới chung cư, đơn thiếu số phòng, khách không nghe máy.',
                     _o('try', 'Nhắn tin và gọi lại, hỏi bảo vệ quy định giữ hàng, báo điều phối', 3, 'Khách gọi lại sau năm phút, nhận hàng.'),
                     _o('leave', 'Để hàng ở sảnh, chụp ảnh là xong', 0, 'Hàng mất, bạn phải đền.'),
                     _o('cancel', 'Báo hủy đơn luôn', 1, 'Khách lỡ món đang cần.')),
    'dl_cod': _q('Đơn COD 327 xu, khách đưa tờ 500 xu.',
                 _o('count', 'Đếm trước mặt khách, thối 173 xu, ghi phiếu', 3, 'Tiền khớp khi nộp về bưu cục.'),
                 _o('round', 'Thối 170 cho chẵn', 0, 'Thiếu tiền khách là mất uy tín của cả bưu cục.'),
                 _o('transfer', 'Nhờ khách chuyển khoản lại', 1, 'Được, nhưng khách phải chờ.')),
    'dl_flood': _q('Mưa to, đường phía trước ngập nửa bánh xe.',
                   _o('safe', 'Tấp vào chỗ an toàn, bọc hàng, báo điều phối và khách giờ giao mới', 3, 'Chị Hạnh: “Người về an toàn là đơn quan trọng nhất.”'),
                   _o('wait', 'Tắt máy chờ, không báo ai', 1, 'An toàn nhưng khách và điều phối không biết.'),
                   _o('ride', 'Chạy băng qua cho kịp giờ', 0, 'Chị Hạnh gọi dừng: “Không đơn nào đáng để liều.”', fatal=True)),
}


def _post(pid, org, kind, title, salary, probation, wants, perks, culture, boss, stages, reference=True,
          questions=(), wage_note=None, **more):
    row = dict(id=pid, org=org, kind=kind, title=title, salary=salary, probation_days=probation, wants=list(wants),
               perks=list(perks), culture=culture, questions=list(questions), reference=reference, boss=boss,
               stages=list(stages))
    if wage_note:
        row['wage_note'] = wage_note
    row.update(more)
    return row


TRADE_WAGE = 'Lương cứng mỗi ngày; tiền công và tiền bán hàng vẫn vào quỹ tiệm.'

POSTINGS = {
    'pharmacy': [
        _post('ph-day', 'Quầy thuốc Bình An', 'pharmacy', 'Nhân viên quầy thuốc (ca ngày)', (40, 55), 3,
              ['careful', 'calm', 'communication'], ['Cô Thu kèm từng phiếu', 'Lịch ổn định', 'Đông khách giờ tan tầm'],
              'Quầy nhỏ đầu hẻm. Cô Thu phụ trách chuyên môn; mọi phiếu đều đọc mã, soát lô, hỏi thuốc đang dùng.',
              'cô Thu', ('exam', 'cv', 'interview'), questions=['ph_rush', 'ph_advice', 'ph_why'], exam='pharmacy'),
        _post('ph-evening', 'Quầy thuốc Bình An · ca tối', 'parttime', 'Nhân viên quầy ca tối (bán thời gian)', (32, 42), 2,
              ['careful', 'patience'], ['Ca ngắn', 'Ít khách hơn', 'Lương thấp hơn'],
              'Ca tối vắng hơn nhưng hay có khách hỏi gấp; việc nào ngoài tầm thì gọi cô Thu.',
              'cô Thu', ('exam', 'cv', 'interview'), reference=False, questions=['ph_advice', 'mistake'], exam='pharmacy'),
    ],
    'customer_care': [
        _post('cc-station', 'Trạm Lắng Nghe', 'station', 'Nhân viên chăm sóc khách hàng', (38, 52), 3,
              ['communication', 'calm', 'patience'], ['Chị Mai kèm ca đầu', 'Có mẫu bàn giao', 'Khách khó tính mỗi ngày'],
              'Trạm hỗ trợ của khu phố: đổi trả, giao trễ, hóa đơn. Mỗi lời hẹn phải có người giữ.',
              'chị Mai', ('cv', 'letter', 'interview', 'test'), questions=['cc_listen', 'cc_promise', 'conflict'],
              test=['cc_t_open', 'cc_t_manager', 'cc_t_demand']),
        _post('cc-hotline', 'Trạm Lắng Nghe · tổng đài ca tối', 'parttime', 'Nhân viên tổng đài (bán thời gian)', (30, 40), 2,
              ['calm', 'patience'], ['Ca tối', 'Chỉ nghe máy', 'Lương thấp hơn'],
              'Tổng đài tối nhận cuộc gọi khi các tiệm đã đóng cửa; khách gọi giờ này thường đang bực.',
              'chị Mai', ('cv', 'interview', 'test'), reference=False, questions=['cc_listen'],
              test=['cc_t_open', 'cc_t_abuse', 'cc_t_demand']),
    ],
    'tour_guide': [
        _post('tg-company', 'Công ty Lữ hành Mây Lang Thang', 'agency', 'Hướng dẫn viên tour phố', (38, 55), 3,
              ['communication', 'teamwork', 'learning'], ['Tip của đoàn', 'Được đi khắp phố', 'Nắng mưa đều đi'],
              'Công ty nhỏ dẫn đoàn đi bộ quanh phố: bến, chợ, xưởng gốm, bờ sông. Anh Hải điều phối mọi chuyến.',
              'anh Hải', ('exam', 'cv', 'letter', 'interview'), questions=['tg_pace', 'tg_unknown', 'tg_rainplan'], exam='tour_guide'),
        _post('tg-collab', 'Mây Lang Thang · cộng tác viên cuối tuần', 'collab', 'Hướng dẫn viên cộng tác', (30, 42), 2,
              ['communication', 'learning'], ['Nhận đoàn nhỏ', 'Không cần thư ứng tuyển', 'Lương thấp hơn'],
              'Đoàn nhỏ cuối tuần, đi theo lộ trình mẫu của công ty.',
              'anh Hải', ('exam', 'cv', 'interview'), reference=False, questions=['tg_rainplan', 'tg_unknown'], exam='tour_guide'),
    ],
    'salon': [
        _post('sl-assist', 'Salon Tóc Gió', 'shop', 'Thợ phụ gội sấy', (18, 26), 2,
              ['patience', 'communication', 'creative'], ['Chị Phượng chỉ nghề', 'Được học cắt', 'Đứng cả ngày'],
              'Salon đầu dốc, bốn ghế, khách quen nhiều. Muốn cầm kéo thì phải gội sấy thật khéo trước đã.',
              'chị Phượng', ('cv', 'trial'), reference=False, trial=['sl_wash', 'sl_clean', 'sl_timer'], wage_note=TRADE_WAGE),
        _post('sl-color', 'Salon Tóc Gió · bàn màu', 'shop', 'Thợ phụ màu (học việc)', (20, 28), 2,
              ['careful', 'creative'], ['Học pha màu', 'Canh giờ từng phút', 'Khách kỹ tính'],
              'Bàn màu của salon: hỏi kỹ lịch sử tóc, thử thuốc, canh giờ.',
              'chị Phượng', ('cv', 'trial'), trial=['sl_consult', 'sl_timer', 'sl_clean'], wage_note=TRADE_WAGE),
    ],
    'pet_care': [
        _post('pc-groom', 'Pet Care Mèo Mập', 'shop', 'Phụ tắm sấy thú cưng', (16, 24), 2,
              ['patience', 'calm', 'careful'], ['Chị Nhàn chỉ nghề', 'Chó mèo dễ thương', 'Hay bị cào'],
              'Tiệm nhỏ đầu hẻm, máy sấy chạy cả ngày. Luật số một: không bé nào phải sợ.',
              'chị Nhàn', ('cv', 'trial'), reference=False, trial=['pc_check', 'pc_scared', 'pc_lump'], wage_note=TRADE_WAGE),
        _post('pc-kennel', 'Pet Care Mèo Mập · khu lưu trú', 'shop', 'Chăm chuồng lưu trú', (15, 22), 1,
              ['patience', 'careful'], ['Nhận ngay', 'Dọn chuồng, cho ăn, dắt đi dạo', 'Lương thấp hơn'],
              'Khu gửi thú khi chủ đi xa: đúng khẩu phần, đúng giờ, báo ngay điều bất thường.',
              'chị Nhàn', ('cv', 'trial'), reference=False, trial=['pc_check', 'pc_nails', 'pc_lump'], wage_note=TRADE_WAGE),
    ],
    'repair': [
        _post('rp-apprentice', 'Tiệm Sửa Đồ Chú Tư', 'shop', 'Thợ phụ học việc', (18, 26), 2,
              ['careful', 'tech', 'learning'], ['Chú Tư truyền nghề', 'Đồ nghề đủ', 'Mùa nóng quạt hư dồn dập'],
              'Tiệm dưới mái tôn, quạt, nồi cơm, điện thoại. Chú Tư dặn: đo trước, báo giá sau, sửa cho tới nơi.',
              'Chú Tư', ('cv', 'trial'), reference=False, trial=['rp_fan', 'rp_quote', 'rp_cord'], wage_note=TRADE_WAGE),
        _post('rp-phone', 'Tiệm Sửa Đồ Chú Tư · quầy điện thoại', 'shop', 'Thợ phụ sửa điện thoại', (20, 28), 2,
              ['careful', 'tech'], ['Việc tỉ mỉ', 'Dữ liệu khách phải giữ kín', 'Khách hỏi tiến độ liên tục'],
              'Góc quầy chuyên điện thoại: thay màn hình, pin, chân sạc. Máy khách, dữ liệu khách.',
              'Chú Tư', ('cv', 'trial'), trial=['rp_phone', 'rp_quote', 'rp_fan'], wage_note=TRADE_WAGE),
    ],
    'delivery': [
        _post('dl-rider', 'Giao Nhanh Mây Chiều', 'hub', 'Tài xế giao hàng khu phố', (15, 24), 2,
              ['calm', 'careful', 'communication'], ['Chị Hạnh điều phối', 'Thuộc đường nhanh', 'Nắng mưa đều chạy'],
              'Bưu cục nhỏ giao trong phố: đúng người, đúng giờ, đúng tiền. Chạy thử một vòng với chị Hạnh là biết.',
              'chị Hạnh', ('cv', 'trial'), reference=False, trial=['dl_route', 'dl_address', 'dl_cod'], wage_note=TRADE_WAGE,
              trial_title='Chạy thử một vòng'),
        _post('dl-evening', 'Giao Nhanh Mây Chiều · ca tối', 'parttime', 'Tài xế ca tối (bán thời gian)', (14, 20), 1,
              ['calm', 'careful'], ['Ca ngắn', 'Đường tối, trời hay mưa', 'Lương thấp hơn'],
              'Ca tối gom đơn gấp; trời đổi là phải báo điều phối.',
              'chị Hạnh', ('cv', 'trial'), reference=False, trial=['dl_route', 'dl_flood', 'dl_cod'], wage_note=TRADE_WAGE,
              trial_title='Chạy thử một vòng'),
    ],
}

# Lucky meetings with the owners of these places (never skip a licence exam).
BOSS_APPLY = [
    'Bạn vừa đưa hồ sơ, {boss} ngẩng lên: “Hôm trước con phụ bà Sáu khiêng đồ phải không? Mai tới làm luôn, khỏi thử.”',
    'Đúng lúc bạn tới, {org} đang rối vì đông khách. Bạn phụ một tay mười phút, và {boss} mời bạn ở lại làm luôn.',
]
BOSS_MEET = [
    'Cuối ngày, {boss} của {org} ghé ngang, nghe hàng xóm khen bạn, rồi mời bạn về làm {title}.',
    'Bạn chỉ đường cho một người đang tìm hẻm. Hóa ra đó là {boss} của {org}, và họ mời bạn về làm {title}.',
]
