"""🏫 Ngành Kinh tế và Kế toán: 12 môn đại học (game/school.py question bank). Pure data, see game/school_q.py."""
from .school_q import C, T, O, N, L, S

SUBJECTS = {
    # ───────────── Ngành Kinh tế ─────────────
    'kt_vimo': S('Kinh tế vi mô', '📈', (
        L('Cung và cầu', (
            'Cầu là lượng hàng người mua muốn và có tiền để mua; giá càng cao thì người ta thường mua ít đi.',
            'Cung là lượng hàng người bán muốn bán; giá càng cao thì người bán càng muốn bán nhiều hơn.',
            'Hàng khan hiếm mà nhiều người muốn mua thì giá thường tăng; hàng thừa ế thì giá thường giảm.',
        ), (
            C('Mùa mưa bão, xoài về chợ ít mà khách vẫn đông. Giá xoài ở sạp thường sẽ thế nào?',
              ('Giảm mạnh', 'Tăng lên', 'Không đổi chút nào'), 1,
              'Hàng ít mà người mua nhiều thì giá thường tăng lên.'),
            T('Khi giá một món hàng tăng, người mua thường muốn mua nhiều hơn.', False,
              'Thường thì giá tăng, người ta mua ít đi, đó là quy luật cầu.'),
            C('Chiều tối, sạp còn nhiều rau sắp héo. Chủ sạp nên làm gì để bán nhanh hết hàng?',
              ('Tăng giá lên gấp đôi', 'Cất đi để mai bán tiếp', 'Giảm giá cho khách'), 2,
              'Hàng thừa thì hạ giá giúp bán nhanh, đỡ bỏ phí.'),
        )),
        L('Chi phí cơ hội', (
            'Chi phí cơ hội là thứ tốt nhất bạn phải bỏ qua khi chọn làm một việc khác.',
            'Thời gian cũng có giá: một giờ đi chơi có thể là một giờ không đi làm kiếm tiền.',
            'Ra quyết định khôn ngoan: kể ra các lựa chọn, so sánh được và mất, rồi chọn cách có lợi nhất.',
        ), (
            C('Chi phí cơ hội là gì?',
              ('Tiền thuế phải nộp', 'Lựa chọn tốt nhất bị bỏ qua khi chọn việc khác', 'Tiền lãi ngân hàng',
               'Giá gốc của món hàng'), 1,
              'Chi phí cơ hội là cái bạn mất đi vì đã chọn việc này thay vì việc kia.'),
            N('Bé Na nghỉ một buổi bán hàng (thường kiếm 200 nghìn đồng) để đi xem phim vé 100 nghìn đồng. '
              'Cái giá thật của buổi xem phim là bao nhiêu nghìn đồng?', 300,
              'Tiền vé 100 nghìn cộng 200 nghìn tiền công bị bỏ lỡ là 300 nghìn đồng.'),
            O('Sắp xếp các bước ra một quyết định khôn ngoan:',
              ('Kể ra các lựa chọn có thể', 'So sánh cái được và cái mất của từng lựa chọn', 'Chọn cách có lợi nhất'),
              'Phải biết có những lựa chọn nào, so sánh chúng rồi mới chọn.'),
        )),
        L('Cạnh tranh trên thị trường', (
            'Khi nhiều người cùng bán một món, họ cạnh tranh bằng giá, chất lượng và cách phục vụ.',
            'Cạnh tranh lành mạnh giúp khách có hàng tốt hơn với giá hợp lý hơn.',
            'Nếu chỉ có một người bán duy nhất (độc quyền), người đó dễ đặt giá cao.',
        ), (
            C('Đầu hẻm mở thêm hai tiệm tạp hóa mới. Tiệm cũ của cô Hạ nên làm gì?',
              ('Phục vụ chu đáo hơn, giá hợp lý hơn', 'Đi nói xấu tiệm mới', 'Đóng cửa ngay cho đỡ mệt'), 0,
              'Cạnh tranh lành mạnh là làm tốt hơn để giữ khách.'),
            T('Khi chỉ có một người bán duy nhất, người đó thường dễ đặt giá cao.', True,
              'Đúng, không có ai cạnh tranh nên khách khó tìm chỗ mua khác.'),
            C('Cạnh tranh lành mạnh mang lại gì cho khách hàng?',
              ('Giá lúc nào cũng tăng', 'Ít hàng để chọn hơn', 'Hàng tốt hơn, giá hợp lý hơn'), 2,
              'Người bán phải cố gắng hơn nên khách được lợi.'),
        )),
    ), extra=(
        C('Mẫu xe máy mới ra, ai cũng muốn mua mà đại lý chỉ có vài chiếc. Điều gì dễ xảy ra?',
          ('Đại lý giảm giá thật mạnh', 'Giá bị đẩy lên hoặc khách phải chờ hàng', 'Không ai thèm mua'), 1,
          'Cầu lớn hơn cung thì giá dễ tăng hoặc khách phải xếp hàng chờ.'),
    )),

    'kt_marketing': S('Marketing căn bản', '📣', (
        L('Khách hàng mục tiêu', (
            'Khách hàng mục tiêu là nhóm người hợp nhất với món hàng của bạn, không phải "bán cho tất cả mọi người".',
            'Hãy tìm hiểu họ: tuổi, thu nhập, thói quen, họ hay mua ở đâu và đang cần gì.',
        ), (
            C('Quán trà sữa ngay cạnh trường cấp ba nên chọn khách hàng mục tiêu nào?',
              ('Các cụ ông về hưu', 'Học sinh quanh trường', 'Công ty xây dựng'), 1,
              'Học sinh đi ngang quán mỗi ngày và rất thích trà sữa.'),
            T('Bán cho "tất cả mọi người" là cách chọn khách hàng mục tiêu tốt nhất.', False,
              'Nhắm vào một nhóm khách rõ ràng thì mới hiểu và phục vụ họ tốt được.'),
            C('Muốn hiểu khách hàng mục tiêu, việc nào hữu ích nhất?',
              ('Đoán bừa cho nhanh', 'Chép y nguyên tiệm bên cạnh', 'Chỉ hỏi người trong nhà',
               'Hỏi han, quan sát thói quen mua của khách'), 3,
              'Quan sát và hỏi chính khách hàng mới biết họ thật sự cần gì.'),
        )),
        L('4P: sản phẩm, giá, kênh, xúc tiến', (
            '4P gồm: Sản phẩm (bán gì), Giá (bán bao nhiêu), Kênh (bán ở đâu), Xúc tiến (cho khách biết bằng cách nào).',
            'Bốn chữ P phải hợp nhau: hàng xịn mà bán quá rẻ, bày lộn xộn thì khách sẽ nghi ngờ.',
            'Thứ tự hợp lý: biết rõ khách là ai, rồi chọn hàng và giá, cuối cùng mới đi quảng bá.',
        ), (
            C('Trong 4P, chữ "Kênh" nói về điều gì?',
              ('Giá bán bao nhiêu', 'Bán ở đâu, đưa hàng tới khách thế nào', 'Màu sắc của bao bì'), 1,
              'Kênh là nơi bán và cách đưa hàng đến tay khách.'),
            C('Treo băng rôn "Mua 2 tặng 1" trước tiệm thuộc chữ P nào?',
              ('Sản phẩm', 'Kênh', 'Giá', 'Xúc tiến (quảng bá, khuyến mãi)'), 3,
              'Quảng bá và khuyến mãi để khách biết đến tiệm là phần Xúc tiến.'),
            O('Sắp xếp các bước làm marketing cho một sạp trái cây mới:',
              ('Xác định khách hàng mục tiêu', 'Chọn loại trái cây và đặt giá phù hợp', 'Quảng bá cho khách biết đến sạp'),
              'Biết bán cho ai trước, rồi mới chọn hàng, giá và đi quảng bá.'),
        )),
        L('Khuyến mãi và thương hiệu nhỏ', (
            'Khuyến mãi giúp kéo khách, nhưng giảm giá quá sâu và quá lâu có thể làm lỗ vốn.',
            'Thương hiệu nhỏ là cái tên, logo và cảm giác mà khách nhớ về tiệm của bạn.',
            'Giữ chữ tín, hàng luôn đều chất lượng là cách xây thương hiệu rẻ mà bền nhất.',
        ), (
            N('Hộp bánh giá 50 nghìn đồng, tiệm giảm 10 nghìn đồng mỗi hộp. Khách mua 3 hộp phải trả bao nhiêu nghìn đồng?',
              120, '(50 − 10) × 3 = 120 nghìn đồng.'),
            T('Giảm giá thật sâu suốt cả năm luôn giúp tiệm lời nhiều hơn.', False,
              'Giảm quá sâu, quá lâu thì tiền lời bị ăn mòn, dễ lỗ vốn.'),
            C('Cách bền nhất để xây thương hiệu cho một tiệm nhỏ là gì?',
              ('Đổi tên tiệm mỗi tháng', 'Quảng cáo nói quá sự thật', 'Giữ chữ tín, chất lượng đều đặn'), 2,
              'Khách nhớ và quay lại vì hàng tốt và chữ tín.'),
        )),
    ), extra=(
        C('Tiệm bánh mì Mây muốn khách nhớ tên mình. Việc nào giúp ích nhất?',
          ('Logo dễ nhớ và bánh lúc nào cũng ngon như nhau', 'Mỗi ngày bán một kiểu giá', 'Không treo bảng hiệu'), 0,
          'Tên dễ nhớ cộng chất lượng đều đặn tạo nên thương hiệu.'),
    )),

    'kt_banhang': S('Kỹ năng bán hàng', '🤝', (
        L('Chào khách và hỏi nhu cầu', (
            'Chào khách bằng nụ cười, ánh mắt thân thiện; đừng vồ vập hay kéo tay khách.',
            'Hỏi câu mở như "Anh chị đang tìm món gì ạ?" rồi lắng nghe nhiều hơn nói.',
            'Hiểu đúng nhu cầu thì mới gợi ý đúng món, khách thấy mình được quan tâm.',
        ), (
            C('Câu nào là câu hỏi mở giúp hiểu nhu cầu của khách?',
              ('"Anh lấy cái này hả?"', '"Anh chị định dùng xe để đi đâu nhiều ạ?"', '"Mua không?"'), 1,
              'Câu hỏi mở để khách kể nhiều hơn, không chỉ trả lời có hay không.'),
            T('Khi khách vừa bước vào, nên nói liên tục để khách không kịp rời đi.', False,
              'Nói liên tục làm khách ngại; chào thân thiện rồi lắng nghe mới đúng.'),
            C('Khách vào đại lý xe, cần xe tiết kiệm xăng để đi làm hằng ngày. Nhân viên nên gợi ý gì?',
              ('Xe phân khối lớn đắt nhất', 'Xe đua thể thao', 'Mẫu xe tiết kiệm xăng, bền bỉ'), 2,
              'Gợi ý đúng nhu cầu khách vừa nói thì khách mới ưng.'),
        )),
        L('Xử lý lời từ chối', (
            'Khách nói "đắt quá" là chuyện bình thường; đừng cãi, hãy lắng nghe và hỏi khách lo điều gì.',
            'Giải thích giá trị của món hàng: dùng bền, có bảo hành, tiết kiệm về lâu dài.',
            'Nếu khách vẫn không mua, cứ cảm ơn vui vẻ để lần sau khách còn quay lại.',
        ), (
            C('Khách chê "Sao đắt vậy?". Cách đáp nào khéo nhất?',
              ('"Dạ, món này bền và có bảo hành, để em chỉ anh chị xem ạ"', '"Không mua thì thôi!"',
               '"Tiệm khác còn đắt hơn nhiều"'), 0,
              'Bình tĩnh giải thích giá trị món hàng giúp khách hiểu vì sao đáng tiền.'),
            O('Sắp xếp cách xử lý khi khách chê giá đắt:',
              ('Bình tĩnh lắng nghe khách nói hết', 'Hỏi xem khách đang lo điều gì', 'Giải thích giá trị của món hàng'),
              'Nghe trước, hiểu lý do, rồi mới giải thích cho đúng chỗ khách lo.'),
            T('Khách không mua lần này thì vẫn nên cảm ơn vui vẻ.', True,
              'Đúng, khách nhớ thái độ tốt và có thể quay lại lần sau.'),
        )),
        L('Chốt đơn và chăm sóc sau bán', (
            'Khi khách đã ưng, hỏi nhẹ nhàng để chốt: "Em gói cho chị cái màu xanh nhé?".',
            'Sau khi bán, hướng dẫn cách dùng, đưa hóa đơn và nói rõ chuyện bảo hành.',
            'Hỏi thăm khách sau vài ngày giúp giữ khách quen và được giới thiệu thêm khách mới.',
        ), (
            C('Câu nào giúp chốt đơn một cách tự nhiên?',
              ('"Mua lẹ đi, sắp hết rồi!"', '"Chị suy nghĩ gì mà lâu quá"', '"Em gói cho chị cái màu xanh nhé?"'), 2,
              'Hỏi nhẹ nhàng, cụ thể giúp khách dễ gật đầu mà không thấy bị ép.'),
            N('Anh Tư bán 3 chiếc nón, mỗi chiếc 80 nghìn đồng. Khách đưa 300 nghìn đồng. '
              'Anh phải thối lại bao nhiêu nghìn đồng?', 60,
              '3 × 80 = 240, rồi 300 − 240 = 60 nghìn đồng.'),
            C('Việc nào là chăm sóc khách sau bán?',
              ('Tránh mặt khi khách quay lại', 'Gọi hỏi thăm xe chạy có ổn không', 'Xóa số điện thoại của khách'), 1,
              'Hỏi thăm sau bán giúp khách tin và quay lại.'),
        )),
    ), extra=(
        C('Điều gì quan trọng nhất trong suốt quá trình bán hàng?',
          ('Nói thật nhanh, thật nhiều', 'Lắng nghe và hiểu khách', 'Ép khách mua bằng được'), 1,
          'Hiểu khách thì mới tư vấn đúng, chốt đơn dễ và giữ được khách.'),
    )),

    'kt_taichinh': S('Tài chính cá nhân & ngân hàng', '🏦', (
        L('Lập ngân sách và tiết kiệm', (
            'Ngân sách là kế hoạch chia tiền: bao nhiêu cho ăn ở, đi lại, tiết kiệm và vui chơi.',
            'Mẹo đơn giản: vừa nhận lương là để riêng phần tiết kiệm trước, rồi mới tiêu.',
            'Ghi lại các khoản chi giúp bạn biết tiền "đi đâu mất" mỗi tháng.',
        ), (
            N('Lương tháng 8.000 nghìn đồng, bạn để dành 20%. Mỗi tháng bạn tiết kiệm được bao nhiêu nghìn đồng?', 1600,
              '20% của 8.000 là 1.600 nghìn đồng.'),
            C('Cách tiết kiệm dễ thành công nhất là gì?',
              ('Tiêu trước, cuối tháng dư thì để dành', 'Để riêng phần tiết kiệm ngay khi nhận lương',
               'Không cần ghi chép gì cả'), 1,
              'Để dành trước thì không lo tiêu lố hết tiền.'),
            T('Ghi chép chi tiêu giúp bạn biết tiền mình đã tiêu vào đâu.', True,
              'Đúng, có ghi chép thì mới thấy khoản nào nên cắt bớt.'),
        )),
        L('Ngân hàng và lãi đơn', (
            'Gửi tiết kiệm ở ngân hàng thì được trả lãi; vay tiền thì phải trả lãi cho ngân hàng.',
            'Lãi đơn: tiền lãi = tiền gốc × lãi suất × số kỳ, tiền lãi không được cộng dồn vào gốc.',
            'Lãi suất càng cao thì tiền gửi được lãi nhiều, nhưng tiền vay cũng phải trả nhiều hơn.',
        ), (
            N('Gửi 10.000 nghìn đồng, lãi đơn 6% một năm. Sau 1 năm được bao nhiêu nghìn đồng tiền lãi?', 600,
              '10.000 × 6% = 600 nghìn đồng tiền lãi.'),
            C('Khi bạn vay tiền ngân hàng thì sao?',
              ('Ngân hàng trả lãi cho bạn', 'Không phải trả lại gì', 'Bạn phải trả cả gốc lẫn lãi cho ngân hàng'), 2,
              'Vay thì phải trả lại tiền gốc kèm tiền lãi.'),
            T('Với lãi đơn, tiền lãi năm trước được cộng vào gốc để tính lãi năm sau.', False,
              'Đó là lãi kép; lãi đơn chỉ tính trên tiền gốc ban đầu.'),
        )),
        L('An toàn thẻ, chống lừa đảo OTP', (
            'Mã OTP là mật khẩu dùng một lần ngân hàng gửi cho bạn; không đọc cho ai, kể cả người xưng nhân viên ngân hàng.',
            'Ngân hàng không gọi điện hay nhắn tin xin mã OTP, mật khẩu hay mã PIN của bạn.',
            'Thấy dấu hiệu lạ thì khóa thẻ ngay qua ứng dụng hoặc gọi số tổng đài in trên thẻ.',
        ), (
            C('Có người gọi xưng nhân viên ngân hàng, xin mã OTP để "nâng hạng thẻ". Bạn làm gì?',
              ('Đọc mã OTP cho nhanh', 'Gửi ảnh hai mặt thẻ cho họ', 'Từ chối, cúp máy, tự gọi tổng đài trên thẻ'), 2,
              'Ngân hàng không bao giờ xin OTP; đây là chiêu lừa đảo quen thuộc.'),
            O('Sắp xếp việc cần làm khi lỡ làm mất thẻ ngân hàng:',
              ('Khóa thẻ ngay qua ứng dụng hoặc tổng đài', 'Kiểm tra lịch sử giao dịch xem có gì lạ',
               'Đến ngân hàng làm lại thẻ mới'),
              'Khóa thẻ trước để chặn kẻ gian, rồi mới kiểm tra và làm thẻ mới.'),
            T('Ngân hàng đôi khi gọi điện xin mã OTP của khách để xác minh.', False,
              'Sai, ai xin mã OTP của bạn thì gần như chắc chắn là lừa đảo.'),
        )),
    ), extra=(
        C('Thói quen nào giúp quản lý tiền tốt?',
          ('Lập ngân sách và để dành đều đặn', 'Vay tiền để mua đồ theo trend', 'Cho người lạ mượn thẻ'), 0,
          'Có kế hoạch chi tiêu và tiết kiệm đều thì tiền mới dư dả.'),
    )),

    'kt_khoinghiep': S('Khởi nghiệp kinh doanh nhỏ', '🚀', (
        L('Ý tưởng và vốn', (
            'Ý tưởng tốt giải quyết một nhu cầu thật, ví dụ khu trọ đông người mà chưa có tiệm giặt.',
            'Vốn là tiền bỏ ra ban đầu: mua hàng, thuê chỗ, sắm dụng cụ; nên chừa thêm một khoản dự phòng.',
            'Bắt đầu nhỏ, bán thử một ít trước để xem khách có thật sự mua hay không.',
        ), (
            C('Ý tưởng kinh doanh nào có vẻ hợp lý nhất?',
              ('Bán áo len dày ở nơi nắng nóng quanh năm', 'Bán đồ thật đắt ở nơi vắng người',
               'Mở tiệm giặt sấy ở khu trọ đông người chưa có tiệm'), 2,
              'Ý tưởng tốt đáp ứng một nhu cầu có thật mà chưa ai phục vụ.'),
            T('Khi khởi nghiệp, nên dồn hết tiền vào hàng hóa, không cần chừa tiền dự phòng.', False,
              'Luôn nên chừa một khoản dự phòng cho chuyện bất ngờ.'),
            O('Sắp xếp các bước bắt đầu một việc kinh doanh nhỏ:',
              ('Tìm nhu cầu thật của khách', 'Tính số vốn cần có', 'Bán thử một ít', 'Xem khách phản hồi rồi điều chỉnh'),
              'Có ý tưởng, tính vốn, bán thử rồi sửa dần cho hợp khách.'),
        )),
        L('Đặt giá bán', (
            'Giá bán = chi phí làm ra một món + tiền lời bạn muốn có.',
            'Chi phí gồm nguyên liệu, bao bì, cả tiền điện, tiền thuê chỗ chia ra cho mỗi món; đừng quên tính.',
            'Giá còn phải so với thị trường: đắt quá thì khách bỏ đi, rẻ quá thì không đủ lời.',
        ), (
            N('Một ly nước mía tốn 6 nghìn đồng chi phí, bạn muốn lời 4 nghìn đồng mỗi ly. '
              'Giá bán mỗi ly là bao nhiêu nghìn đồng?', 10,
              'Giá bán = chi phí + lời = 6 + 4 = 10 nghìn đồng.'),
            C('Khi tính chi phí một món hàng, khoản nào hay bị quên nhất?',
              ('Tiền điện, tiền thuê chỗ chia cho mỗi món', 'Tên của món hàng', 'Màu của bảng hiệu'), 0,
              'Chi phí chung như điện, mặt bằng cũng phải chia vào giá từng món.'),
            C('Giá bán cao hơn hẳn các sạp xung quanh mà hàng y hệt nhau thì sao?',
              ('Khách sẽ xếp hàng mua', 'Khách dễ bỏ sang sạp khác', 'Không ảnh hưởng gì'), 1,
              'Hàng giống nhau thì khách chọn chỗ giá hợp lý hơn.'),
        )),
        L('Điểm hòa vốn và sổ thu chi', (
            'Điểm hòa vốn: số món cần bán để tiền lời mỗi món cộng lại vừa đủ bù chi phí, không lời không lỗ.',
            'Ví dụ: tiền thuê 1.000 nghìn đồng, mỗi món lời 10 nghìn đồng thì cần bán 100 món mới hòa vốn.',
            'Sổ thu chi ghi mỗi ngày: thu bao nhiêu, chi bao nhiêu, còn bao nhiêu; ghi ngay, đừng để dồn.',
        ), (
            N('Tiền thuê sạp 2.000 nghìn đồng một tháng, mỗi ly nước lời 5 nghìn đồng. '
              'Cần bán bao nhiêu ly để đủ tiền thuê?', 400,
              '2.000 ÷ 5 = 400 ly là hòa vốn tiền thuê.'),
            T('Sổ thu chi nên ghi ngay mỗi ngày thay vì để dồn tới cuối tháng.', True,
              'Đúng, ghi ngay thì nhớ rõ, ít sai sót.'),
            C('Điểm hòa vốn là lúc nào?',
              ('Lúc tiệm lời nhiều nhất', 'Lúc vừa đủ bù chi phí, không lời không lỗ', 'Lúc tiệm phải đóng cửa'), 1,
              'Hòa vốn nghĩa là thu vừa bằng chi, chưa lời mà cũng không lỗ.'),
        )),
    ), extra=(
        N('Mở sạp nước mía cần máy ép 3.000 nghìn đồng, xe đẩy 1.500 nghìn đồng, nguyên liệu ban đầu 500 nghìn đồng. '
          'Tổng vốn là bao nhiêu nghìn đồng?', 5000,
          '3.000 + 1.500 + 500 = 5.000 nghìn đồng.'),
    )),

    'kt_tmdt': S('Thương mại điện tử', '🛒', (
        L('Mở gian hàng online', (
            'Gian hàng online cần tên dễ nhớ, mô tả rõ ràng, giá niêm yết và cách liên hệ.',
            'Ảnh sản phẩm nên chụp nơi đủ sáng, nền gọn, nhiều góc và đúng màu thật.',
            'Mô tả trung thực về kích cỡ, chất liệu, tình trạng hàng để khách khỏi thất vọng.',
        ), (
            C('Ảnh sản phẩm thế nào giúp khách tin tưởng?',
              ('Ảnh mờ, chụp trong chỗ tối', 'Ảnh lấy trên mạng, khác hàng thật', 'Ảnh thật, đủ sáng, nhiều góc'), 2,
              'Ảnh thật, rõ ràng giúp khách thấy đúng món mình sẽ nhận.'),
            T('Chỉnh màu ảnh cho đẹp hơn hẳn hàng thật là cách bán hàng online tốt.', False,
              'Hàng khác ảnh làm khách thất vọng, đánh giá xấu và đòi trả hàng.'),
            O('Sắp xếp các bước đăng bán một món hàng online:',
              ('Chuẩn bị hàng và chụp ảnh', 'Viết mô tả, đặt giá', 'Bấm đăng bán', 'Trả lời tin nhắn của khách'),
              'Có ảnh và mô tả rồi mới đăng, đăng rồi mới có khách nhắn hỏi.'),
        )),
        L('Đánh giá và giao hàng', (
            'Đánh giá của khách là "lời truyền miệng" trên mạng; nhiều đánh giá tốt giúp bán chạy hơn.',
            'Gặp đánh giá xấu, hãy trả lời lịch sự, xin lỗi và đề nghị cách sửa sai, đừng cãi nhau.',
            'Gói hàng chắc chắn, giao đúng hẹn và báo mã vận đơn để khách tự theo dõi.',
        ), (
            C('Khách đánh giá 1 sao vì hàng giao trễ. Shop nên làm gì?',
              ('Viết lời lẽ nặng nề đáp trả khách', 'Xin lỗi lịch sự và đề nghị cách bù đắp',
               'Mua đánh giá ảo để che đi'), 1,
              'Xin lỗi chân thành giúp giữ uy tín và có khi khách đổi ý.'),
            N('Shop bán 4 áo, mỗi áo 150 nghìn đồng, cộng phí giao hàng 30 nghìn đồng. '
              'Khách trả tổng bao nhiêu nghìn đồng?', 630,
              '4 × 150 = 600, cộng 30 phí giao là 630 nghìn đồng.'),
            C('Món đồ gốm dễ vỡ thì nên gói thế nào?',
              ('Bọc chống sốc nhiều lớp, ghi "Hàng dễ vỡ"', 'Bỏ vào túi nilon mỏng', 'Không cần gói gì'), 0,
              'Gói kỹ và ghi chú rõ giúp hàng tới tay khách nguyên vẹn.'),
        )),
        L('Đổi trả và cảnh giác lừa đảo', (
            'Ghi rõ chính sách đổi trả: đổi trong bao lâu, hàng cần còn nguyên tem, ai trả phí giao hàng.',
            'Cảnh giác tin nhắn "trúng thưởng", đường link lạ, hay người lạ đòi chuyển tiền cọc gấp.',
            'Chỉ trao đổi và thanh toán qua kênh chính thức của sàn hoặc cách đã thỏa thuận rõ ràng.',
        ), (
            T('Một chính sách đổi trả rõ ràng giúp khách yên tâm mua hàng hơn.', True,
              'Đúng, khách biết lỡ có trục trặc vẫn được đổi nên dễ chốt đơn hơn.'),
            C('Bạn nhận tin "Shop trúng thưởng, bấm link và nhập mật khẩu để nhận quà". Bạn làm gì?',
              ('Bấm vào ngay kẻo lỡ', 'Nhập mật khẩu cho nhanh', 'Không bấm, xóa tin và báo cho sàn'), 2,
              'Link lạ đòi mật khẩu là chiêu lừa chiếm tài khoản.'),
            C('Chính sách đổi trả nên ghi rõ điều gì?',
              ('Số người theo dõi shop', 'Thời hạn đổi và điều kiện hàng còn nguyên tem', 'Màu sắc logo của shop'), 1,
              'Thời hạn và điều kiện rõ ràng giúp tránh tranh cãi với khách.'),
        )),
    ), extra=(
        C('Điều gì giúp một shop online giữ được khách lâu dài?',
          ('Ảnh đẹp nhưng hàng khác hẳn', 'Hàng đúng mô tả, giao đúng hẹn', 'Lờ đi tin nhắn của khách'), 1,
          'Trung thực và đúng hẹn tạo niềm tin để khách quay lại.'),
    )),

    # ───────────── Ngành Kế toán ─────────────
    'ktn_nguyenly': S('Nguyên lý kế toán', '🧮', (
        L('Phương trình kế toán', (
            'Tài sản là thứ doanh nghiệp đang có và kiểm soát: tiền, hàng hóa, máy móc, khoản người khác nợ mình.',
            'Tài sản = Nợ phải trả + Vốn chủ sở hữu; hai bên luôn bằng nhau.',
            'Nợ phải trả là tiền mình còn nợ người khác; vốn chủ sở hữu là phần thuộc về chủ.',
        ), (
            N('Tiệm có tài sản 500 triệu đồng, nợ phải trả 200 triệu đồng. Vốn chủ sở hữu là bao nhiêu triệu đồng?', 300,
              'Vốn chủ = tài sản − nợ phải trả = 500 − 200 = 300 triệu đồng.'),
            C('Khoản nào là tài sản của tiệm?',
              ('Tiền còn nợ nhà cung cấp', 'Hàng hóa đang có trong kho', 'Lương còn nợ nhân viên'), 1,
              'Hàng trong kho là thứ tiệm đang có, còn hai khoản kia là nợ phải trả.'),
            T('Trong kế toán, tổng tài sản luôn bằng nợ phải trả cộng vốn chủ sở hữu.', True,
              'Đúng, đó là phương trình kế toán cơ bản.'),
        )),
        L('Ghi Nợ và ghi Có', (
            'Ghi sổ kép: mỗi nghiệp vụ ghi vào ít nhất hai tài khoản, một bên Nợ, một bên Có, số tiền bằng nhau.',
            'Với tài khoản tài sản như tiền mặt: tăng thì ghi bên Nợ, giảm thì ghi bên Có.',
            'Với tài khoản nguồn vốn như nợ phải trả: tăng thì ghi bên Có, giảm thì ghi bên Nợ.',
        ), (
            C('Tiền mặt của công ty tăng thêm thì ghi vào bên nào của tài khoản Tiền mặt?',
              ('Bên Có', 'Bên Nợ', 'Không cần ghi'), 1,
              'Tiền mặt là tài sản, tài sản tăng thì ghi bên Nợ.'),
            C('Công ty Cánh Diều mua chịu hàng, nợ người bán tăng lên. Ghi vào bên nào của tài khoản Phải trả người bán?',
              ('Bên Nợ', 'Ghi vào sổ nháp là đủ', 'Bên Có'), 2,
              'Nợ phải trả là nguồn vốn, tăng thì ghi bên Có.'),
            T('Trong ghi sổ kép, tổng bên Nợ và tổng bên Có của một nghiệp vụ có thể lệch nhau.', False,
              'Sai, hai bên Nợ và Có của một nghiệp vụ luôn bằng nhau.'),
        )),
        L('Nguyên tắc thận trọng', (
            'Thận trọng: chưa chắc có lời thì chưa ghi lời, nhưng thấy có khả năng lỗ thì phải tính đến sớm.',
            'Không thổi phồng tài sản hay thu nhập, không giấu bớt nợ phải trả và chi phí.',
            'Kế toán phải trung thực, mỗi con số ghi vào sổ đều cần có chứng từ đi kèm.',
        ), (
            C('Theo nguyên tắc thận trọng, khoản lời "có lẽ sẽ có" mà chưa chắc chắn thì xử lý sao?',
              ('Chưa ghi nhận cho tới khi chắc chắn', 'Ghi ngay cho báo cáo đẹp', 'Ghi gấp đôi cho chắc'), 0,
              'Lời chưa chắc thì chưa ghi, để báo cáo không bị thổi phồng.'),
            T('Kế toán thận trọng nghĩa là có thể giấu bớt nợ để công ty trông khỏe hơn.', False,
              'Sai, thận trọng là không thổi phồng tài sản và không giấu nợ.'),
            O('Sắp xếp các bước xử lý một nghiệp vụ kế toán:',
              ('Nhận và kiểm tra chứng từ', 'Xác định tài khoản ghi Nợ, ghi Có', 'Ghi vào sổ sách'),
              'Có chứng từ hợp lệ rồi mới định khoản và ghi sổ.'),
        )),
    ), extra=(
        C('Công ty vay ngân hàng 100 triệu đồng tiền mặt. Điều gì xảy ra?',
          ('Tài sản giảm, vốn chủ tăng', 'Không có gì thay đổi', 'Tiền mặt tăng, nợ phải trả cũng tăng'), 2,
          'Có thêm tiền nhưng cũng thêm khoản nợ, hai bên phương trình cùng tăng.'),
    )),

    'ktn_chungtu': S('Chứng từ & sổ sách', '🧾', (
        L('Hóa đơn, phiếu thu, phiếu chi', (
            'Chứng từ là giấy tờ chứng minh một nghiệp vụ đã xảy ra: hóa đơn, phiếu thu, phiếu chi, phiếu nhập kho...',
            'Phiếu thu lập khi nhận tiền vào quỹ; phiếu chi lập khi xuất tiền ra khỏi quỹ.',
            'Chứng từ cần đủ ngày tháng, nội dung, số tiền và chữ ký của những người liên quan.',
        ), (
            C('Tiệm nhận 2 triệu đồng tiền mặt khách trả nợ. Kế toán lập phiếu gì?',
              ('Phiếu chi', 'Phiếu thu', 'Phiếu xuất kho'), 1,
              'Tiền vào quỹ thì lập phiếu thu.'),
            C('Trả tiền điện tháng này bằng tiền mặt thì lập phiếu gì?',
              ('Phiếu thu', 'Phiếu nhập kho', 'Phiếu chi'), 2,
              'Tiền ra khỏi quỹ thì lập phiếu chi.'),
            T('Phiếu chi thiếu chữ ký người nhận tiền vẫn đầy đủ, không cần bổ sung.', False,
              'Sai, chứng từ phải có đủ chữ ký người liên quan mới đầy đủ.'),
        )),
        L('Ghi sổ và lưu trữ', (
            'Ghi sổ theo thứ tự thời gian, rõ ràng; ghi sai thì sửa đúng cách, không tẩy xóa bôi bẩn.',
            'Chứng từ được đánh số, xếp theo ngày và cất vào bìa hồ sơ hoặc thư mục điện tử riêng.',
            'Chứng từ phải được lưu trữ nhiều năm theo quy định, không tự ý vứt bỏ.',
        ), (
            O('Sắp xếp đường đi của một chứng từ trong phòng kế toán:',
              ('Lập hoặc nhận chứng từ', 'Kiểm tra chứng từ', 'Ghi vào sổ sách', 'Lưu trữ chứng từ'),
              'Chứng từ được lập, kiểm tra, dùng để ghi sổ rồi mới cất lưu trữ.'),
            T('Ghi sai trong sổ thì cứ dùng bút xóa tẩy đi cho sạch.', False,
              'Sai, phải sửa theo cách đúng quy định, không tẩy xóa.'),
            C('Cách sắp xếp chứng từ nào giúp dễ tìm lại nhất?',
              ('Đánh số, xếp theo ngày, cất theo bìa từng tháng', 'Nhét chung vào một thùng', 'Để luôn trên bàn cho tiện'),
              0, 'Có số và có thứ tự thì tìm lại rất nhanh.'),
        )),
        L('Đối chiếu sổ sách', (
            'Đối chiếu là so số trong sổ với thực tế: tiền đếm trong két, sao kê ngân hàng, công nợ của khách.',
            'Cuối ngày đếm quỹ: tồn đầu ngày + thu − chi phải bằng số tiền thật có trong két.',
            'Lệch số thì tìm nguyên nhân và báo lại, không tự bù tiền hay sửa số cho khớp.',
        ), (
            N('Đầu ngày quỹ có 500 nghìn đồng, thu thêm 1.200 nghìn đồng, chi ra 300 nghìn đồng. '
              'Cuối ngày két phải còn bao nhiêu nghìn đồng?', 1400,
              '500 + 1.200 − 300 = 1.400 nghìn đồng.'),
            C('Đếm két thấy thiếu 50 nghìn đồng so với sổ. Kế toán nên làm gì?',
              ('Sửa số trong sổ cho khớp', 'Lấy tiền túi bù vào rồi im lặng',
               'Kiểm tra lại chứng từ, tìm nguyên nhân và báo lại'), 2,
              'Phải tìm ra lý do lệch, không che giấu sai sót.'),
            C('Số dư tiền gửi trong sổ nên đem so với giấy tờ nào?',
              ('Hóa đơn tiền điện', 'Sao kê tài khoản ngân hàng', 'Bảng chấm công'), 1,
              'Sao kê ngân hàng cho biết số tiền thật trong tài khoản.'),
        )),
    ), extra=(
        C('Vì sao phải giữ chứng từ cẩn thận?',
          ('Để làm giấy nháp', 'Để chứng minh các khoản thu chi khi cần kiểm tra', 'Để trang trí văn phòng'), 1,
          'Chứng từ là bằng chứng cho mọi con số trong sổ sách.'),
    )),

    'ktn_excel': S('Tin học kế toán (bảng tính)', '📊', (
        L('Ô, hàng, cột và công thức', (
            'Bảng tính chia thành cột (A, B, C...) và hàng (1, 2, 3...); mỗi ô có địa chỉ như B3.',
            'Công thức luôn bắt đầu bằng dấu "=", ví dụ =B2*C2 để tính thành tiền.',
            'Dùng =SUM(B2:B10) để cộng nhanh cả dãy ô từ B2 đến B10.',
        ), (
            C('Ô nằm ở cột C, hàng 5 có địa chỉ là gì?',
              ('5C', 'C5', 'CC5'), 1,
              'Địa chỉ ô ghi chữ cột trước, số hàng sau: C5.'),
            C('Công thức trong bảng tính bắt đầu bằng ký tự nào?',
              ('Dấu "="', 'Dấu "#"', 'Dấu "?"'), 0,
              'Gõ dấu "=" trước thì bảng tính mới hiểu đó là công thức.'),
            N('Ô B2 = 30, B3 = 45, B4 = 25. Công thức =SUM(B2:B4) cho ra kết quả bao nhiêu?', 100,
              '30 + 45 + 25 = 100.'),
        )),
        L('Lọc và định dạng số', (
            'Chức năng Lọc (Filter) giúp chỉ hiện những dòng bạn cần, ví dụ chỉ những khách còn nợ tiền.',
            'Lọc chỉ tạm ẩn bớt dòng, không xóa dữ liệu; bỏ lọc là thấy lại đầy đủ.',
            'Định dạng số có dấu phân cách hàng nghìn giúp đọc 1.250.000 dễ hơn 1250000.',
        ), (
            T('Dùng Lọc để chỉ hiện khách còn nợ sẽ xóa mất các dòng khách khác.', False,
              'Sai, Lọc chỉ tạm ẩn, bỏ lọc là các dòng hiện lại đủ.'),
            C('Muốn xem nhanh chỉ các hóa đơn tháng 3 trong một bảng dài, nên dùng gì?',
              ('Xóa các tháng khác đi', 'Đổi màu chữ', 'Chức năng Lọc (Filter)'), 2,
              'Lọc giúp hiện đúng dòng cần xem mà không mất dữ liệu.'),
            C('Vì sao nên định dạng số tiền có dấu phân cách hàng nghìn?',
              ('Cho dễ đọc, khỏi nhầm số', 'Để số tự tăng lên', 'Để bảng tính chạy nhanh hơn'), 0,
              'Số dài dễ đọc sai; có dấu phân cách thì nhìn là biết ngay.'),
        )),
        L('Sao lưu và bảo vệ dữ liệu', (
            'Lưu file thường xuyên và sao lưu thêm một bản ở nơi khác như ổ cứng rời hoặc lưu trữ đám mây.',
            'Đặt tên file rõ ràng, ví dụ "SoThuChi_thang03", để không nhầm bản cũ với bản mới.',
            'File có lương hay số liệu nhạy cảm nên đặt mật khẩu và không gửi bừa qua mạng.',
        ), (
            O('Sắp xếp các bước làm bảng thu chi cuối tháng:',
              ('Nhập số liệu thu chi vào bảng', 'Dùng công thức SUM tính tổng', 'Lưu file và sao lưu thêm một bản'),
              'Có số liệu mới tính tổng được, xong việc thì lưu và sao lưu.'),
            T('Chỉ cần lưu một bản duy nhất trên máy là đủ an toàn.', False,
              'Máy hỏng là mất hết, nên luôn có thêm một bản sao lưu.'),
            C('Tên file nào giúp dễ tìm lại nhất?',
              ('"Moi.xlsx"', '"abc123.xlsx"', '"SoThuChi_thang03.xlsx"'), 2,
              'Tên có nội dung và tháng giúp nhận ra file ngay.'),
        )),
    ), extra=(
        C('Số lượng ở ô B2, đơn giá ở ô C2. Công thức nào tính đúng thành tiền?',
          ('=B2+C2', 'B2xC2', '=B2*C2'), 2,
          'Thành tiền = số lượng × đơn giá, công thức bắt đầu bằng "=" và dùng dấu *.'),
    )),

    'ktn_thue': S('Thuế căn bản', '🏛️', (
        L('Thuế là gì? Thuế GTGT', (
            'Thuế là khoản tiền người dân và doanh nghiệp nộp cho Nhà nước để làm đường, trường, bệnh viện...',
            'Thuế giá trị gia tăng (GTGT) tính trên phần giá trị tăng thêm của hàng hóa, dịch vụ qua mỗi khâu.',
            'Thuế GTGT là thuế gián thu: người mua cuối cùng trả kèm trong giá, doanh nghiệp thu rồi nộp thay.',
        ), (
            C('Ai là người thật sự gánh thuế GTGT?',
              ('Người tiêu dùng cuối cùng', 'Chỉ nhân viên thu ngân', 'Người giao hàng'), 0,
              'Thuế GTGT nằm trong giá, người mua cuối cùng là người trả.'),
            T('Thuế GTGT thường đã nằm sẵn trong giá khi bạn mua hàng.', True,
              'Đúng, thuế GTGT là thuế gián thu, cộng vào giá bán.'),
            N('Giả sử thuế suất GTGT là 10%. Món hàng giá chưa thuế 200 nghìn đồng thì tiền thuế GTGT là bao nhiêu nghìn đồng?',
              20, '10% của 200 nghìn là 20 nghìn đồng.'),
        )),
        L('Thuế thu nhập cá nhân', (
            'Thuế thu nhập cá nhân (TNCN) đánh trên thu nhập của từng người, như tiền lương, tiền công.',
            'Giảm trừ gia cảnh là khoản được trừ khỏi thu nhập trước khi tính thuế, nên thu nhập thấp có thể không phải nộp.',
            'Công ty thường khấu trừ thuế TNCN từ lương rồi nộp thay cho nhân viên.',
        ), (
            C('Thuế TNCN đánh vào đâu?',
              ('Giá trị một món hàng', 'Thu nhập của từng người, như tiền lương', 'Diện tích căn nhà'), 1,
              'TNCN là thuế trên thu nhập của mỗi cá nhân.'),
            T('Ai đi làm cũng phải nộp thuế TNCN, dù lương thấp đến đâu.', False,
              'Sai, nhờ giảm trừ gia cảnh, người thu nhập thấp có thể không phải nộp.'),
            C('Giảm trừ gia cảnh là gì?',
              ('Tiền thưởng Tết', 'Phí chuyển tiền ngân hàng', 'Khoản được trừ khỏi thu nhập trước khi tính thuế'), 2,
              'Đó là phần thu nhập được trừ ra cho bản thân và người phụ thuộc trước khi tính thuế.'),
        )),
        L('Hạn nộp và hóa đơn hợp lệ', (
            'Thuế có hạn kê khai và nộp rõ ràng; trễ hạn có thể bị phạt và bị tính tiền chậm nộp.',
            'Hóa đơn hợp lệ ghi đủ: tên, mã số thuế người bán, thông tin người mua, hàng hóa, số tiền, tiền thuế.',
            'Nên ghi hạn nộp thuế vào lịch và chuẩn bị chứng từ sớm, đừng để sát ngày.',
        ), (
            C('Nộp tờ khai thuế trễ hạn có thể dẫn đến điều gì?',
              ('Được thưởng vì cẩn thận', 'Bị phạt và tính tiền chậm nộp', 'Không sao cả'), 1,
              'Trễ hạn thì có thể bị phạt, nên luôn nộp đúng hạn.'),
            O('Sắp xếp cách chuẩn bị nộp thuế cho đúng hạn:',
              ('Ghi hạn nộp vào lịch', 'Gom và kiểm tra hóa đơn, chứng từ', 'Lập tờ khai thuế',
               'Nộp tờ khai và tiền thuế trước hạn'),
              'Nhớ hạn, gom chứng từ, lập tờ khai rồi nộp sớm cho chắc.'),
            C('Hóa đơn nào có vẻ KHÔNG hợp lệ?',
              ('Hóa đơn thiếu mã số thuế người bán, không rõ hàng gì', 'Hóa đơn ghi đủ tên, mã số thuế, số tiền',
               'Hóa đơn điện tử đầy đủ thông tin'), 0,
              'Thiếu mã số thuế và nội dung hàng hóa thì hóa đơn không hợp lệ.'),
        )),
    ), extra=(
        C('Vì sao công ty nên lấy hóa đơn khi mua hàng?',
          ('Để gấp máy bay giấy', 'Để làm chứng từ ghi sổ và kê khai thuế', 'Không có lý do gì'), 1,
          'Hóa đơn là chứng từ cần cho sổ sách và việc kê khai thuế.'),
    )),

    'ktn_luong': S('Tiền lương & bảo hiểm', '💵', (
        L('Bảng chấm công và lương ngày', (
            'Bảng chấm công ghi mỗi ngày nhân viên đi làm, nghỉ phép, đi trễ hay làm thêm giờ.',
            'Cách tính đơn giản: lương một ngày = lương tháng ÷ số ngày công chuẩn của tháng.',
            'Lương theo công = lương một ngày × số ngày đi làm thực tế.',
        ), (
            N('Lương tháng 6.500 nghìn đồng, tháng có 26 ngày công chuẩn. Lương một ngày là bao nhiêu nghìn đồng?', 250,
              '6.500 ÷ 26 = 250 nghìn đồng một ngày.'),
            N('Lương một ngày 300 nghìn đồng, bạn đi làm 22 ngày. Lương theo công là bao nhiêu nghìn đồng?', 6600,
              '300 × 22 = 6.600 nghìn đồng.'),
            T('Bảng chấm công chỉ cần ghi ngày nghỉ, không cần ghi giờ làm thêm.', False,
              'Sai, làm thêm giờ cũng phải ghi để tính lương cho đúng.'),
        )),
        L('Phụ cấp và khấu trừ', (
            'Phụ cấp là khoản cộng thêm vào lương, như tiền ăn trưa, xăng xe, điện thoại.',
            'Khấu trừ là khoản trừ khỏi lương, như phần bảo hiểm người lao động đóng, thuế TNCN, tiền tạm ứng.',
            'Thực lãnh = lương + phụ cấp − các khoản khấu trừ.',
        ), (
            N('Lương 7.000 nghìn đồng, phụ cấp 1.000 nghìn đồng, khấu trừ 800 nghìn đồng. Thực lãnh bao nhiêu nghìn đồng?',
              7200, '7.000 + 1.000 − 800 = 7.200 nghìn đồng.'),
            C('Khoản nào là phụ cấp?',
              ('Tiền tạm ứng phải trừ lại', 'Phần bảo hiểm trừ vào lương', 'Tiền ăn trưa công ty hỗ trợ'), 2,
              'Phụ cấp là khoản cộng thêm, như tiền ăn trưa.'),
            C('Khoản nào thường bị trừ vào lương nhân viên?',
              ('Tiền xăng xe hỗ trợ', 'Phần bảo hiểm bắt buộc người lao động đóng', 'Thưởng doanh số'), 1,
              'Phần bảo hiểm của người lao động được trừ thẳng từ lương.'),
        )),
        L('Bảo hiểm và bảo mật bảng lương', (
            'Bảo hiểm xã hội, y tế, thất nghiệp giúp người lao động khi ốm đau, nghỉ hưu hay mất việc.',
            'Cả công ty và người lao động đều đóng một phần; kế toán tính và nộp đúng hạn.',
            'Bảng lương là thông tin riêng tư: không để lộ, không gửi nhầm, nên đặt mật khẩu cho file.',
        ), (
            C('Bảo hiểm y tế giúp gì cho người lao động?',
              ('Được hỗ trợ chi phí khi khám chữa bệnh', 'Được tăng lương mỗi tháng', 'Được nghỉ làm tùy ý'), 0,
              'Có bảo hiểm y tế thì đi khám chữa bệnh được hỗ trợ chi phí.'),
            T('Kế toán lương có thể thoải mái gửi bảng lương cả công ty vào nhóm chat chung.', False,
              'Sai, bảng lương là thông tin riêng tư, phải giữ kín.'),
            O('Sắp xếp các bước làm lương cuối tháng:',
              ('Tổng hợp bảng chấm công', 'Tính lương, phụ cấp và khấu trừ', 'Gửi bảng lương cho quản lý duyệt',
               'Chuyển lương cho nhân viên'),
              'Có ngày công mới tính lương, được duyệt rồi mới chuyển tiền.'),
        )),
    ), extra=(
        C('Bạn lỡ thấy bảng lương của đồng nghiệp khi đang làm việc. Nên làm gì?',
          ('Kể cho cả phòng nghe', 'Giữ kín, không bàn tán', 'Chụp lại đăng lên mạng'), 1,
          'Lương của người khác là chuyện riêng tư, cần giữ kín.'),
    )),

    'ktn_baocao': S('Báo cáo tài chính', '📑', (
        L('Bảng cân đối kế toán', (
            'Bảng cân đối kế toán như "tấm ảnh" chụp tài sản, nợ và vốn của công ty tại một thời điểm.',
            'Bên tài sản luôn bằng bên nguồn vốn, tức nợ phải trả cộng vốn chủ sở hữu.',
        ), (
            C('Bảng cân đối kế toán cho biết điều gì?',
              ('Tài sản, nợ và vốn tại một thời điểm', 'Lịch họp của công ty', 'Danh sách khách hàng thân thiết'), 0,
              'Nó cho thấy công ty có gì, nợ ai và vốn của chủ là bao nhiêu.'),
            T('Trên bảng cân đối, tổng tài sản có thể lớn hơn tổng nguồn vốn mà vẫn đúng.', False,
              'Sai, tài sản luôn bằng nguồn vốn; lệch là có chỗ ghi sai.'),
            N('Công ty có tài sản 900 triệu đồng, vốn chủ sở hữu 600 triệu đồng. Nợ phải trả là bao nhiêu triệu đồng?', 300,
              'Nợ phải trả = 900 − 600 = 300 triệu đồng.'),
        )),
        L('Kết quả kinh doanh: lời hay lỗ', (
            'Báo cáo kết quả kinh doanh cho biết trong một kỳ công ty bán được bao nhiêu và lời hay lỗ.',
            'Lợi nhuận = doanh thu − chi phí; nếu ra số âm thì công ty đang lỗ.',
            'Doanh thu cao chưa chắc đã lời, vì chi phí có thể còn cao hơn.',
        ), (
            N('Tháng này tiệm vàng có doanh thu 50 triệu đồng, chi phí 38 triệu đồng. Lợi nhuận là bao nhiêu triệu đồng?', 12,
              '50 − 38 = 12 triệu đồng tiền lời.'),
            C('Doanh thu 30 triệu đồng, chi phí 35 triệu đồng. Kết quả là gì?',
              ('Lời 5 triệu đồng', 'Hòa vốn', 'Lỗ 5 triệu đồng'), 2,
              '30 − 35 ra số âm, nghĩa là lỗ 5 triệu đồng.'),
            T('Doanh thu cao nhưng chi phí còn cao hơn thì công ty vẫn có thể lỗ.', True,
              'Đúng, lời hay lỗ phụ thuộc vào cả doanh thu lẫn chi phí.'),
        )),
        L('Dòng tiền', (
            'Dòng tiền là tiền thật chảy vào và chảy ra khỏi công ty trong một kỳ.',
            'Có lời trên giấy mà khách chưa trả tiền thì công ty vẫn có thể thiếu tiền mặt để trả lương.',
            'Theo dõi dòng tiền giúp biết lúc nào đủ tiền trả nợ, trả lương, nhập hàng.',
        ), (
            C('Vì sao công ty có lời vẫn có thể thiếu tiền mặt?',
              ('Vì lời quá nhiều', 'Vì khách mua chịu, chưa trả tiền', 'Vì báo cáo in sai màu'), 1,
              'Lời ghi trên sổ nhưng tiền chưa về thì vẫn thiếu tiền mặt.'),
            O('Sắp xếp thứ tự lập báo cáo tài chính cuối kỳ:',
              ('Ghi chép đủ các nghiệp vụ trong kỳ', 'Khóa sổ, đối chiếu số liệu', 'Lập các báo cáo tài chính',
               'Kiểm tra lại và nộp cho quản lý'),
              'Số liệu phải đủ và khớp rồi mới lập báo cáo, kiểm tra xong mới nộp.'),
            C('Tiền khách chuyển khoản vào tài khoản công ty được xem là gì?',
              ('Dòng tiền ra', 'Nợ phải trả', 'Dòng tiền vào'), 2,
              'Tiền chảy vào công ty là dòng tiền vào.'),
        )),
    ), extra=(
        C('Báo cáo nào cho biết công ty lời hay lỗ trong kỳ?',
          ('Bảng chấm công', 'Phiếu nhập kho', 'Báo cáo kết quả kinh doanh'), 2,
          'Báo cáo kết quả kinh doanh so doanh thu với chi phí để ra lời hoặc lỗ.'),
    )),
}
