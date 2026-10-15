"""🛃 Hải quan cửa khẩu Bến Mây: people, cases and the game's own rules (owner spec 14/10, I. Bổ sung cập nhật nghề Hải
quan). Every place, company, person, rate and threshold here is invented for the game; the duty rates and the
allowances are game rules, not real tariffs. Read by game/careers/customs.py.
"""
from __future__ import annotations

PEOPLE = [
    ('Chị Lam Thục', 'Đội trưởng Đội Thủ tục', 'Thuộc từng mã hàng, nhắc ai cũng “đúng luồng, đủ giấy”.', 'warm'),
    ('Anh Tạ Bền', 'Chủ hàng xuất khẩu nông sản', 'Thanh long, xoài, chuối: lô nào cũng vội cho kịp tàu.', 'bossy'),
    ('Cô Mạc Hà', 'Nhân viên đại lý làm thủ tục', 'Khai tờ khai điện tử cho cả chục doanh nghiệp mỗi ngày.', 'quiet'),
    ('Ông Kha Lũy', 'Hành khách từ chuyến bay quốc tế', 'Đi công tác về, hành lý lỉnh kỉnh quà biếu.', 'sour'),
    ('Bé Na và mẹ', 'Hành khách đi du lịch về', 'Lần đầu qua cửa khẩu, cái gì cũng hỏi.', 'genz'),
    ('Anh Dư Tín', 'Tài xế xe quá cảnh', 'Chạy tuyến xuyên biên giới mười năm, thuộc từng cái kẹp chì.', 'picky'),
    ('Chú Bảy Cò', 'Môi giới “dịch vụ trọn gói”', 'Lúc nào cũng có “cách cho nhanh”.', 'bossy'),
]

# The game's own rules (shown on the 📘 Sổ tay nghiệp vụ; the tasks' numbers follow them exactly).
VAT = 10                  # % thuế giá trị gia tăng (game rule) on (trị giá tính thuế + thuế nhập khẩu), rounded down
GIFT_FREE = 2000          # a gift (quà biếu) worth at most this many xu: no import duty, no VAT (game rule)
CASH_FREE = 5000          # foreign currency a passenger may carry without declaring (in xu, game rule)
CIG_FREE = 1              # cartons of cigarettes a passenger may bring duty-free (game rule)
NOTEBOOK = [
    'Sổ tay nghiệp vụ của Chi cục Bến Mây: thuế suất, định mức ghi ở đây là quy định của Chi cục.',
    'Doanh nghiệp khai và truyền tờ khai hải quan điện tử lên hệ thống trước, hàng hóa đến cửa khẩu sau.',
    '🟢 Luồng xanh: miễn kiểm tra hồ sơ giấy và miễn kiểm tra thực tế hàng hóa; nộp thuế (nếu có) rồi thông quan.',
    '🟡 Luồng vàng: kiểm tra chi tiết hồ sơ, chứng từ; không kiểm tra thực tế hàng hóa.',
    '🔴 Luồng đỏ: kiểm tra hồ sơ và kiểm tra thực tế hàng hóa.',
    f'Hành khách mang ngoại tệ quá định mức ({CASH_FREE:,} xu quy đổi) hoặc hàng phải khai thì đi cửa báo Hải quan (luồng đỏ).'.replace(',', '.'),
    'Hàng thực tế nhiều hơn, khác loại hơn tờ khai: có dấu hiệu gian lận thương mại. Lập biên bản, tạm giữ, chuyển xử lý.',
    f'Thuế nhập khẩu = trị giá tính thuế × thuế suất. Thuế GTGT = (trị giá + thuế nhập khẩu) × {VAT}%, làm tròn xuống.',
    'Có C/O ưu đãi hợp lệ (đúng mẫu, còn hạn, đúng lô) thì áp thuế suất ưu đãi; thiếu hoặc sai thì áp thuế suất thông thường.',
    f'Quà biếu trị giá không quá {GIFT_FREE:,} xu: miễn thuế nhập khẩu và thuế GTGT.'.replace(',', '.'),
    'Hàng đã nộp thuế nhập khẩu rồi tái xuất trả lại người bán: hoàn đúng số thuế nhập khẩu đã nộp.',
    'Hàng cấm, động vật hoang dã, chất cấm: tạm giữ, lập biên bản, bàn giao cơ quan điều tra. Không “phạt cho xong”.',
    'Khám người, khám hành lý chỉ khi có dấu hiệu và đúng thẩm quyền; không nghi ngờ thì cho đi, nói rõ lý do.',
    'Không nhận bất kỳ thứ gì của ai. Biên bản ghi đúng điều đã thấy. Hàng tạm giữ có biên lai, niêm phong, vào sổ.',
]

LANES = dict(green=('🟢', 'Luồng xanh'), yellow=('🟡', 'Luồng vàng'), red=('🔴', 'Luồng đỏ'))
ROUTE_OPTS = [('green', 'Miễn kiểm hồ sơ và thực tế: thu thuế (nếu có), thông quan'),
              ('yellow', 'Kiểm tra chi tiết hồ sơ giấy, chứng từ'),
              ('red', 'Kiểm tra hồ sơ và kiểm tra thực tế hàng hóa'),
              ('skip', 'Cho qua luôn, không cần xem gì')]
DOC_OPTS = [('ok', 'Hồ sơ đủ, khớp nhau'), ('value', 'Trị giá trên hóa đơn khác hợp đồng'), ('co', 'C/O sai mẫu hoặc hết hạn'),
            ('name', 'Tên hàng khai khác chứng từ')]
GOODS_OPTS = [('ok', 'Thực tế khớp tờ khai'), ('excess', 'Thực tế nhiều hơn khai báo'), ('short', 'Thực tế ít hơn khai báo'),
              ('other', 'Hàng thực tế khác loại khai báo')]
DECIDE_OPTS = [('clear', 'Thông quan'), ('amend', 'Yêu cầu khai bổ sung, thu thuế chênh lệch rồi thông quan'),
               ('hold', 'Tạm giữ, lập biên bản, chuyển xử lý theo quy định')]

# id, unlock day, lane, title, opening, declared, docs answer, goods answer, decision, evidence lines, temptation
LANE_CASES = [
    ('fruit_green', 1, 'green', 'Thanh long đi tàu chiều', 'Anh Tạ Bền giục: tàu chiều nay chạy, tờ khai đã truyền lên hệ thống.',
     '40 tấn thanh long tươi', None, None, 'clear', ('Hệ thống phân: 🟢 Luồng xanh.',), None),
    ('rice_yellow', 1, 'yellow', 'Gạo thơm xuất khẩu', 'Cô Mạc Hà nộp bộ hồ sơ gạo xuất khẩu qua đại lý.',
     '200 tấn gạo thơm', 'ok', None, 'clear', ('Hợp đồng: 200 tấn, 600.000 xu.', 'Hóa đơn: 200 tấn, 600.000 xu.', 'Phiếu đóng gói: 8.000 bao × 25 kg.'), None),
    ('shoe_yellow', 2, 'yellow', 'Giày vải nhập khẩu', 'Lô giày vải của một cửa hàng trong phố, đại lý khai hộ.',
     '3.000 đôi giày vải', 'value', None, 'amend', ('Hợp đồng: 3.000 đôi × 40 xu = 120.000 xu.', 'Hóa đơn: 3.000 đôi × 25 xu = 75.000 xu.',
                                                     'Phiếu đóng gói: 150 thùng × 20 đôi.'), 'collude'),
    ('fan_red', 3, 'red', 'Quạt điện từ cảng', 'Container quạt điện bị hệ thống phân luồng đỏ.',
     '100 thùng quạt điện', 'ok', 'excess', 'hold', ('Hồ sơ: 100 thùng × 10 cái, khớp nhau.', 'Đếm thực tế: 120 thùng × 10 cái.'), 'bribe'),
    ('toy_red', 3, 'red', 'Đồ chơi gỗ', 'Lô đồ chơi gỗ cho tiệm quà lưu niệm, hệ thống phân luồng đỏ.',
     '50 thùng đồ chơi gỗ', 'ok', 'ok', 'clear', ('Hồ sơ: 50 thùng, khớp nhau.', 'Đếm thực tế: 50 thùng, đúng đồ chơi gỗ, tem nhãn đủ.'), None),
    ('cash_pax', 2, 'red', 'Hành khách và phong bì ngoại tệ', 'Ông Kha Lũy kéo vali đi thẳng về phía cửa miễn khai báo.',
     'Hành lý cá nhân', None, 'excess', 'hold', ('Máy soi: một xấp ngoại tệ dày trong ngăn vali.',
                                                 'Ông Kha nói: “Mang theo khoảng 9.000 xu quy đổi, có sao đâu.”'), 'bribe'),
    ('seal_truck', 4, 'red', 'Xe quá cảnh và kẹp chì', 'Anh Dư Tín lái xe quá cảnh dừng ở bãi kiểm soát.',
     'Xe tải quá cảnh 30 kiện vải', 'ok', 'other', 'hold', ('Hồ sơ quá cảnh: 30 kiện vải, kẹp chì số HQ-0412.',
                                                            'Thực tế: kẹp chì bị cắt, dán lại; trong thùng có 12 kiện điện thoại.'), 'collude'),
]
# id, unlock, title, opening, bag shadows (3), suspicious index, identify options, identify answer, decision, temptation
SMUGGLE_CASES = [
    ('scale', 1, 'Vali nặng bất thường', 'Ông Kha Lũy làm thủ tục nhập cảnh, vali nặng hơn hẳn đồ cá nhân.',
     ('Quần áo gấp gọn', 'Khối dày đặc như vảy, xếp lớp', 'Hộp bánh quà biếu'), 1,
     [('scale', 'Vảy tê tê: động vật hoang dã cấm buôn bán'), ('chips', 'Khoai tây chiên'), ('tiles', 'Gạch men mẫu')], 'scale', 'handover', 'keep'),
    ('phones', 2, 'Linh kiện nhựa hay điện thoại?', 'Tờ khai ghi “linh kiện nhựa”, container của một công ty thương mại.',
     ('Bao tải hạt nhựa', 'Hàng trăm khối chữ nhật có pin và màn hình', 'Pallet gỗ rỗng'), 1,
     [('phones', 'Điện thoại di động: khai sai tên hàng'), ('plastic', 'Linh kiện nhựa đúng khai báo'), ('books', 'Sách in')], 'phones', 'hold', 'bribe'),
    ('cigs', 1, 'Thuốc lá quá tiêu chuẩn', 'Hai mẹ con đi du lịch về, mẹ xách thêm túi lớn “mua giúp hàng xóm”.',
     ('Đồ chơi của bé', 'Mười cây thuốc lá xếp thẳng hàng', 'Áo khoác'), 1,
     [('cigs', 'Thuốc lá vượt định mức miễn thuế'), ('candy', 'Kẹo'), ('tea', 'Trà khô')], 'cigs', 'hold', 'keep'),
    ('clean', 1, 'Thùng sách cũ', 'Một sinh viên về nước với thùng sách cũ, máy soi báo “cần xem lại”.',
     ('Sách xếp dày', 'Hộp bút chì', 'Áo len'), -1,
     [('books', 'Sách cũ, đúng như khai'), ('drug', 'Chất cấm'), ('ivory', 'Ngà voi')], 'books', 'release', None),
    ('fireworks', 3, 'Kiện hàng “đồ trang trí Tết”', 'Bưu kiện gửi về phố ghi “đồ trang trí Tết”, chó nghiệp vụ dừng lại đánh hơi.',
     ('Đèn lồng giấy', 'Ống trụ có dây ngòi xếp chặt', 'Câu đối vải'), 1,
     [('fireworks', 'Pháo nổ: hàng cấm'), ('lantern', 'Đèn lồng giấy'), ('candle', 'Nến thơm')], 'fireworks', 'handover', 'keep'),
]
SMUGGLE_DECIDE = [('release', 'Cho thông quan, nói rõ lý do kiểm tra'), ('hold', 'Tạm giữ, lập biên bản vi phạm, xử lý theo quy định'),
                  ('handover', 'Tạm giữ, lập biên bản, bàn giao cơ quan điều tra'), ('fine_go', 'Phạt tiền tại chỗ rồi cho đi')]
# id, unlock, title, opening, item, value, normal rate, preferential rate, C/O ('ok' | 'bad' | None), policy, paid (refund), temptation
TAX_CASES = [
    ('tv', 1, 'Lô ti vi nhập khẩu', 'Cô Mạc Hà nộp tờ khai lô ti vi cho một cửa hàng điện máy trong phố.', 'Ti vi 43 inch', 12000, 20, 10, None, 'collect', 0, 'falsify'),
    ('coffee_co', 2, 'Máy pha cà phê có C/O', 'Máy pha cà phê cho chuỗi quán, kèm C/O ưu đãi mẫu Sông Mây còn hạn.', 'Máy pha cà phê', 8000, 15, 5, 'ok', 'collect', 0, None),
    ('bike_co', 3, 'Xe đạp, C/O hết hạn', 'Lô xe đạp trẻ em, C/O nộp kèm đã hết hạn từ tuần trước.', 'Xe đạp trẻ em', 6400, 15, 5, 'bad', 'collect', 0, 'falsify'),
    ('gift', 1, 'Quà biếu từ người thân', 'Bé Na nhận thùng quà bánh kẹo của bà ngoại gửi từ nước ngoài.', 'Quà biếu bánh kẹo', 1500, 20, 20, None, 'exempt', 0, None),
    ('refund', 4, 'Hàng tái xuất trả người bán', 'Lô máy bơm đã nộp thuế, bị lỗi kỹ thuật nên tái xuất trả lại người bán.', 'Máy bơm nước', 9000, 10, 10, None, 'refund', 900, 'skim'),
]
POLICY_OPTS = [('collect', 'Thu thuế nhập khẩu và GTGT như đã tính'), ('exempt', 'Miễn thuế (đúng diện miễn)'),
               ('refund', 'Hoàn thuế nhập khẩu đã nộp')]
# id, unlock, title, opening, profile options, profile answer, found, decision, temptation
CONTROL_CASES = [
    ('courier', 2, 'Hành khách xách hộ', 'Một hành khách mua vé bằng tiền mặt sát giờ bay, đi một mình, xách hộ “túi quà của người quen”.',
     [('risk', 'Vé mua sát giờ bằng tiền mặt, xách hộ đồ không rõ, khai báo lúng túng'), ('look', 'Mặc áo khoác đen'), ('age', 'Còn trẻ')], 'risk',
     'Chó nghiệp vụ ngồi xuống cạnh túi; soi chiếu thấy gói bột nén giấu trong hộp bánh.', 'handover', 'bribe'),
    ('birds', 3, 'Tiếng chim trong thùng', 'Thùng hàng khai “đồ gốm” phát ra tiếng sột soạt.',
     [('noise', 'Tiếng động, lỗ thở khoét trên thùng, khai “đồ gốm”'), ('heavy', 'Thùng nặng'), ('color', 'Thùng màu nâu')], 'noise',
     'Mở kiểm tra có biên bản: 30 con chim hoang dã nhốt trong ống nhựa.', 'handover', None),
    ('false_alarm', 1, 'Người khách lo lắng', 'Một cụ bà run run, tay ôm chặt túi xách khi qua cửa.',
     [('none', 'Không có dấu hiệu vi phạm: cụ chỉ sợ đi máy bay'), ('nervous', 'Lo lắng nên chắc chắn giấu gì đó'), ('bag', 'Ôm túi chặt')], 'none',
     'Soi chiếu bình thường, chó nghiệp vụ không phản ứng.', 'release', None),
    ('knives', 4, 'Bưu kiện lưỡi dao', 'Bưu kiện khai “dụng cụ nhà bếp” gửi cho một tài khoản bán hàng trên mạng.',
     [('shape', 'Hình soi là lưỡi dao găm có cán bọc, số lượng lớn, khai sai'), ('light', 'Kiện nhẹ'), ('cheap', 'Phí gửi rẻ')], 'shape',
     'Mở kiểm tra có biên bản: 40 con dao găm, không giấy phép.', 'handover', 'bribe'),
]
METHOD_OPTS = [('lawful', 'Soi chiếu, chó nghiệp vụ; mở kiểm tra có biên bản, có người chứng kiến'),
               ('force', 'Khám người ngay tại chỗ, không cần quyết định'), ('skip', 'Thôi, để họ đi cho nhanh')]
CONTROL_DECIDE = [('release', 'Cho đi, xin lỗi vì đã làm mất thời gian'), ('fine_go', 'Phạt hành chính tại chỗ rồi cho đi'),
                  ('handover', 'Tạm giữ người và tang vật, lập biên bản, bàn giao cơ quan điều tra')]

# Temptations (owner spec 14/10, I.2): a choice before the decision. 'refuse' is the only right one.
TEMPT = {
    'bribe': dict(code='hq_abuse', who=6, amount=(300, 900), title='Phong bì “cho nhanh”',
                  text='Chủ hàng dúi phong bì {amount} xu: “Bỏ qua giúp em lần này, không ai biết đâu.”',
                  options=[('refuse', 'Từ chối, lập biên bản hành vi đưa hối lộ'), ('take', 'Nhận phong bì, cho qua')]),
    'collude': dict(code='hq_collude', who=6, amount=(0, 0), title='“Anh em cả mà”',
                    text='Chú Bảy Cò nhắn: “Doanh nghiệp này quen, anh để họ khai như cũ, cho qua luôn nhé.”',
                    options=[('refuse', 'Xử lý đúng như mọi tờ khai'), ('take', 'Nể tình, cho qua như họ khai')]),
    'falsify': dict(code='hq_falsify', who=6, amount=(0, 0), title='Sửa biên bản cho “đẹp”',
                    text='Đại lý xin: “Ghi trị giá trong biên bản thấp đi một chút, kết quả kiểm tra coi như khớp, đỡ phiền cả hai.”',
                    options=[('refuse', 'Ghi đúng trị giá, đúng kết quả đã kiểm'), ('take', 'Sửa biên bản theo lời nhờ')]),
    'skim': dict(code='hq_collude', who=6, amount=(0, 0), title='Hoàn thuế “gấp đôi”',
                 text='Doanh nghiệp đề nghị: “Hồ sơ hoàn thuế ghi gấp đôi đi, ngân sách nhiều tiền mà, phần dư mình tính sau.”',
                 options=[('refuse', 'Chỉ hoàn đúng số thuế đã nộp'), ('take', 'Ghi khống số hoàn theo đề nghị')]),
    'keep': dict(code='hq_abuse', who=0, amount=(150, 500), title='Giữ lại ít hàng tạm giữ',
                 text='Đồng nghiệp rủ: “Hàng tạm giữ nhiều, mình giữ lại vài món trị giá {amount} xu, không cần biên lai.”',
                 options=[('refuse', 'Niêm phong đủ, vào sổ, có biên lai'), ('take', 'Giữ lại không biên lai')]),
}

# 📮 After the shift: what people write about the day (game/npc_complaints.py). Real ones come from the day's slips.
REAL_LINES = {
    'route': 'Tờ khai của tôi bị xử lý sai luồng, phải chờ cả buổi.',
    'docs': 'Hồ sơ giấy bị bắt bẻ sai chỗ, tôi phải nộp lại.',
    'goods': 'Kiểm tra thực tế ghi sai số lượng lô hàng của tôi.',
    'decide': 'Lô hàng của tôi bị quyết định sai, mất cả ngày giải trình.',
    'scan': 'Hành lý của tôi bị lục tung không đúng chỗ.',
    'identify': 'Cán bộ gọi tên sai món hàng của tôi, làm tôi hoảng.',
    'rate': 'Tôi bị áp sai thuế suất, phải khiếu nại.',
    'duty': 'Số thuế nhập khẩu tính cho tôi bị sai.',
    'vat': 'Thuế giá trị gia tăng tính cho tôi bị sai.',
    'policy': 'Tôi đúng diện được miễn (hoặc hoàn) mà bị xử lý khác.',
    'profile': 'Tôi bị nghi ngờ vô cớ ở cửa kiểm soát.',
    'method': 'Cán bộ kiểm tra tôi không đúng quy trình.',
}
FAKE_LINES = {
    'demand': ['Làm thủ tục xong mà không ai xách vali ra taxi giúp tôi.', 'Tôi muốn được ưu tiên làm trước cả hàng chờ vì tôi là khách VIP.',
               'Cửa khẩu nên mở thêm quầy bán cà phê ngay chỗ soi chiếu.', 'Sao không giao hàng tận nhà cho tôi sau khi thông quan?'],
    'bocphot': ['Tôi sẽ đăng bài bóc phốt cửa khẩu nếu không đền tôi 5.000 xu vì phải chờ.', 'Đền ngay cho tôi cái vali mới, không thì lên mạng nói hết.',
                'Tôi quay clip rồi, chuyển khoản bồi thường thì tôi gỡ.'],
    'offtopic': ['Hôm nay trời nắng quá, ai chịu trách nhiệm?', 'Đồ ăn ở quán đối diện cửa khẩu dở quá.', 'Đội bóng của tôi thua, buồn ghê.',
                 'Wifi ở nhà tôi chập chờn mấy hôm nay.'],
}
MILESTONES = [
    dict(id='lane', label='Đúng luồng, đủ giấy', jobs=15, days=5),
    dict(id='guard', label='Người giữ cửa khẩu', jobs=60, days=20),
    dict(id='wall', label='Bức tường chống buôn lậu', jobs=160, days=45),
]
