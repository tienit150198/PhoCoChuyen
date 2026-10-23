"""🏫 Ngành Thiết kế thời trang và Du lịch – Khách sạn (game/school.py question bank). Pure data, see game/school_q.py."""
from .school_q import C, T, O, N, L, S

SUBJECTS = {
    # ---------------- Ngành Thiết kế thời trang (shop quần áo, tiệm nail, salon tóc, photobooth) ----------------
    'tt_hinhhoa': S('Hình họa thời trang', '✏️', (
        L('Dáng người thời trang', (
            'Người thật cao khoảng 7–8 lần chiều dài cái đầu, còn dáng vẽ thời trang thường kéo dài tới khoảng 9 đầu.',
            'Kéo dài phần chân một chút giúp bộ đồ trông thanh thoát và dễ nhìn hơn trên giấy.',
            'Đường trọng tâm là đường dọc từ hõm cổ xuống chân, giúp dáng đứng vững, không bị nghiêng đổ.',
        ), (
            C('Dáng vẽ thời trang thường cao khoảng bao nhiêu đầu?', ('5 đầu', '14 đầu', '9 đầu'), 2,
              'Dáng thời trang thường dài khoảng 9 đầu, cao hơn người thật một chút.'),
            T('Trong hình họa thời trang, người ta thường vẽ chân ngắn lại cho chắc chắn.', False,
              'Ngược lại, chân thường được kéo dài để bộ đồ trông thanh thoát.'),
            C('Đường trọng tâm giúp gì cho bản vẽ dáng người?', ('Tô màu nhanh hơn', 'Vẽ mặt đẹp hơn', 'Dáng đứng vững, không bị đổ'), 2,
              'Đường trọng tâm giữ cho dáng đứng cân bằng, không bị nghiêng.'),
        )),
        L('Tỷ lệ cơ thể', (
            'Người ta dùng chiều dài cái đầu làm thước đo để chia cơ thể thành các phần cho đều.',
            'Dáng nam thường có vai rộng hơn hông; dáng nữ thường có vai và hông rộng gần bằng nhau.',
            'Khi tay buông xuôi, khuỷu tay nằm khoảng ngang eo.',
        ), (
            C('Đơn vị đo thường dùng để chia tỷ lệ cơ thể khi vẽ là gì?', ('Chiều dài cái đầu', 'Chiều dài bàn tay', 'Chiều rộng tờ giấy'), 0,
              'Chiều dài cái đầu là "thước đo" quen thuộc khi chia tỷ lệ dáng người.'),
            C('Khi tay buông xuôi, khuỷu tay thường nằm ngang chỗ nào?', ('Ngang cằm', 'Ngang eo', 'Ngang đầu gối'), 1,
              'Khuỷu tay nằm khoảng ngang eo khi tay thả lỏng.'),
            T('Dáng nam trong bản vẽ thường có vai rộng hơn hông.', True,
              'Đúng rồi, vai nam thường rộng hơn hông.'),
        )),
        L('Phác thảo nhanh', (
            'Phác thảo bắt đầu bằng nét chì thật nhẹ cho khung dáng, để dễ tẩy và chỉnh lại.',
            'Vẽ từ khối lớn đến chi tiết nhỏ: dáng người, rồi form đồ, cuối cùng là nút, túi, đường may.',
            'Ghi chú tên vải và màu bên cạnh bản vẽ để thợ may hiểu đúng ý tưởng.',
        ), (
            O('Sắp xếp các bước phác thảo một mẫu áo theo đúng thứ tự:',
              ('Vẽ khung dáng người bằng nét nhẹ', 'Vẽ form áo lên dáng', 'Thêm nút, túi, đường may'),
              'Vẽ từ khối lớn đến chi tiết nhỏ: dáng, form đồ rồi mới tới chi tiết.'),
            C('Vì sao nét khung dáng nên vẽ chì thật nhẹ?', ('Để tiết kiệm chì', 'Để dễ tẩy và chỉnh lại', 'Để bản vẽ tối hơn'), 1,
              'Nét nhẹ dễ tẩy, sai đâu chỉnh đó mà không bẩn giấy.'),
            C('Ghi chú tên vải và màu bên cạnh bản phác giúp ai hiểu ý tưởng?', ('Thợ may', 'Khách đi ngang', 'Người giao hàng'), 0,
              'Ghi chú giúp thợ may làm đúng vải, đúng màu bạn muốn.'),
        )),
    ), extra=(
        C('Bạn vẽ mẫu đồ cho shop quần áo. Cách nào giúp bộ đồ trông thanh thoát?',
          ('Vẽ đầu thật to', 'Vẽ dáng ngồi khom', 'Kéo dài phần chân một chút'), 2,
          'Kéo dài chân một chút là mẹo quen thuộc của hình họa thời trang.'),
    )),

    'tt_chatlieu': S('Vải & chất liệu', '🧵', (
        L('Vải tự nhiên quen thuộc', (
            'Cotton (vải bông) thấm mồ hôi tốt, mặc thoáng, hợp áo thun và đồ mặc ngày hè.',
            'Lụa mềm, mịn, mặc mát nhưng dễ nhăn và cần giặt nhẹ tay.',
            'Linen (vải lanh) rất thoáng mát nhưng nhăn khá nhanh.',
        ), (
            C('Khách muốn áo thun mặc hè thấm mồ hôi tốt. Bạn gợi ý vải gì?', ('Nhựa PVC', 'Da thuộc', 'Cotton'), 2,
              'Cotton thấm mồ hôi tốt, mặc thoáng mát.'),
            T('Lụa là loại vải nên giặt mạnh tay và vắt thật kỹ.', False,
              'Lụa mỏng, mềm nên cần giặt nhẹ tay.'),
            C('Nhược điểm hay gặp của vải linen là gì?', ('Nhăn nhanh', 'Rất nóng', 'Không giặt được'), 0,
              'Linen thoáng mát nhưng dễ nhăn.'),
        )),
        L('Jean và vải tổng hợp', (
            'Vải jean dệt dày, chắc, bền, hợp quần áo mặc hằng ngày và đi làm việc chân tay.',
            'Polyester là sợi tổng hợp: ít nhăn, nhanh khô nhưng thấm mồ hôi kém hơn cotton.',
            'Vải có pha sợi thun (spandex) thì co giãn, ôm dáng và dễ cử động.',
        ), (
            C('Vì sao quần jean hợp để mặc khi làm việc chân tay?', ('Vì mỏng như lụa', 'Vì không bao giờ phai màu', 'Vì dày, chắc và bền'), 2,
              'Jean dệt dày, chắc nên rất bền.'),
            C('Ưu điểm của vải polyester là gì?', ('Thấm mồ hôi hơn cotton', 'Ít nhăn, nhanh khô', 'Mềm mát như lụa'), 1,
              'Polyester ít nhăn và nhanh khô, nhưng thấm mồ hôi kém hơn cotton.'),
            T('Vải pha sợi thun giúp quần áo co giãn và dễ cử động hơn.', True,
              'Đúng, sợi thun làm vải co giãn, ôm dáng.'),
        )),
        L('Đọc nhãn giặt', (
            'Hình chậu nước là giặt, tam giác là tẩy, bàn ủi là là ủi, hình vuông là phơi sấy.',
            'Ký hiệu nào bị gạch chéo nghĩa là KHÔNG được làm việc đó.',
            'Hình bàn ủi có càng nhiều chấm thì được ủi ở nhiệt độ càng cao.',
        ), (
            C('Trên nhãn giặt, hình bàn ủi bị gạch chéo nghĩa là gì?', ('Ủi thật nóng', 'Không được ủi', 'Chỉ ủi mặt trong'), 1,
              'Dấu gạch chéo nghĩa là không được làm việc đó, ở đây là không ủi.'),
            C('Hình tam giác trên nhãn giặt nói về việc gì?', ('Phơi khô', 'Giặt máy', 'Tẩy'), 2,
              'Tam giác là ký hiệu về tẩy.'),
            O('Sắp xếp ký hiệu bàn ủi từ nhiệt độ thấp đến cao:', ('Bàn ủi 1 chấm', 'Bàn ủi 2 chấm', 'Bàn ủi 3 chấm'),
              'Càng nhiều chấm thì nhiệt độ ủi càng cao.'),
        )),
    ), extra=(
        C('Khách cần áo ít nhăn, phơi nhanh khô khi đi công tác. Vải nào hợp nhất?', ('Linen', 'Polyester', 'Lụa'), 1,
          'Polyester ít nhăn, nhanh khô, rất tiện khi đi xa.'),
    )),

    'tt_catmay': S('Cắt may căn bản', '🪡', (
        L('Lấy số đo', (
            'Số đo cơ bản gồm vòng ngực, vòng eo, vòng mông, dài áo và dài tay.',
            'Đo bằng thước dây, quấn vừa sát người, không kéo căng cũng không để lỏng.',
            'Ghi số đo ngay vào sổ, kèm tên khách và ngày đo để khỏi nhầm.',
        ), (
            C('Khi lấy số đo, thước dây nên quấn thế nào?',
              ('Vừa sát người, không căng không lỏng', 'Kéo thật căng cho gọn', 'Thả thật lỏng cho thoải mái'), 0,
              'Quấn vừa sát người thì số đo mới chính xác.'),
            T('Vòng eo là một trong các số đo cơ bản khi may quần áo.', True,
              'Đúng, vòng eo là số đo cơ bản bên cạnh vòng ngực, vòng mông.'),
            C('Dụng cụ chính để lấy số đo cơ thể là gì?', ('Thước kẻ thẳng', 'Compa', 'Thước dây'), 2,
              'Thước dây mềm, quấn quanh người được.'),
        )),
        L('Rập và cắt vải', (
            'Rập là bản mẫu bằng giấy làm theo số đo, đặt lên vải để cắt cho đúng hình.',
            'Khi cắt nhớ chừa đường may, thường khoảng 1 cm, để có chỗ khâu các mảnh lại với nhau.',
            'Đặt rập theo đúng chiều canh sợi vải để đồ may xong không bị xéo, vặn.',
        ), (
            C('Rập trong nghề may là gì?', ('Một loại chỉ may', 'Bản mẫu giấy để cắt vải', 'Máy ủi hơi nước'), 1,
              'Rập là bản mẫu giấy theo số đo, dùng để cắt vải.'),
            C('Vì sao cần chừa đường may khi cắt vải?', ('Để có chỗ khâu các mảnh lại', 'Để vải đẹp màu hơn', 'Để tiết kiệm vải'), 0,
              'Phần chừa khoảng 1 cm là chỗ để may ráp các mảnh.'),
            T('Đặt rập lệch chiều canh sợi vải không ảnh hưởng gì đến đồ may xong.', False,
              'Lệch canh sợi làm đồ may xong dễ bị xéo, vặn.'),
        )),
        L('May và là ủi', (
            'Thứ tự may cơ bản: lấy số đo, làm rập, cắt vải, may ráp, rồi là ủi hoàn thiện.',
            'Ủi từng đường may ngay sau khi may giúp đường may phẳng và đẹp hơn.',
            'Chỉnh nhiệt bàn ủi theo chất liệu: lụa ủi nhiệt thấp, nhẹ tay; cotton chịu nóng hơn.',
        ), (
            O('Sắp xếp các bước may một chiếc áo theo đúng thứ tự:', ('Lấy số đo', 'Làm rập', 'Cắt vải', 'May ráp và là ủi'),
              'Có số đo mới làm được rập, có rập mới cắt vải rồi may.'),
            C('Khi ủi áo lụa, bạn nên làm gì?', ('Để bàn ủi nóng nhất', 'Xịt thật nhiều nước rồi ủi mạnh', 'Ủi nhiệt thấp, nhẹ tay'), 2,
              'Lụa mỏng, dễ hỏng nên ủi nhiệt thấp và nhẹ tay.'),
            C('Ủi từng đường may ngay sau khi may giúp gì?', ('Vải đổi màu', 'Đường may phẳng, đẹp', 'May nhanh gấp đôi'), 1,
              'Ủi ngay giúp đường may phẳng, thành phẩm gọn đẹp.'),
        )),
    ), extra=(
        C('Khách đặt may váy ở shop. Việc đầu tiên bạn làm là gì?', ('Lấy số đo của khách', 'Cắt vải luôn', 'Ủi vải thật nóng'), 0,
          'Mọi bước sau đều dựa trên số đo, nên đo trước tiên.'),
    )),

    'tt_phoimau': S('Phối màu & phong cách', '🎨', (
        L('Vòng tròn màu', (
            'Trong pha màu vẽ, ba màu cơ bản là đỏ, vàng và xanh dương.',
            'Trộn hai màu cơ bản ra màu mới: đỏ + vàng = cam, vàng + xanh dương = xanh lá, đỏ + xanh dương = tím.',
            'Màu nóng (đỏ, cam, vàng) cho cảm giác sôi động; màu lạnh (xanh, tím) cho cảm giác dịu mát.',
        ), (
            C('Pha màu vàng với màu xanh dương sẽ ra màu gì?', ('Tím', 'Cam', 'Xanh lá'), 2,
              'Vàng + xanh dương = xanh lá.'),
            T('Xanh dương là màu nóng, tạo cảm giác sôi động.', False,
              'Xanh dương là màu lạnh, cho cảm giác dịu mát.'),
            C('Màu nào KHÔNG thuộc ba màu cơ bản trong pha màu vẽ?', ('Đỏ', 'Xanh lá', 'Vàng'), 1,
              'Xanh lá là màu pha từ vàng và xanh dương, không phải màu cơ bản.'),
        )),
        L('Màu bổ túc và trung tính', (
            'Màu bổ túc nằm đối diện nhau trên vòng màu: đỏ – xanh lá, cam – xanh dương, vàng – tím.',
            'Đặt hai màu bổ túc cạnh nhau tạo độ tương phản mạnh, rất nổi bật.',
            'Màu trung tính như đen, trắng, xám, be dễ phối với hầu hết các màu khác.',
        ), (
            C('Màu bổ túc của màu cam là màu nào?', ('Xanh dương', 'Đỏ', 'Vàng'), 0,
              'Cam nằm đối diện xanh dương trên vòng màu.'),
            C('Khách có chân váy đỏ rực, muốn phối áo dễ mặc. Màu áo nào an toàn nhất?', ('Cam neon', 'Trắng', 'Hồng cánh sen'), 1,
              'Trắng là màu trung tính, phối với màu nào cũng dễ.'),
            T('Hai màu bổ túc đặt cạnh nhau tạo độ tương phản mạnh, rất nổi bật.', True,
              'Đúng, vì chúng nằm đối diện nhau trên vòng màu.'),
        )),
        L('Phối đồ theo dịp', (
            'Đi phỏng vấn, đi làm văn phòng: chọn màu trung tính, kiểu dáng gọn gàng, lịch sự.',
            'Đi biển, dã ngoại: chọn màu sáng, vải thoáng, kiểu dáng dễ vận động.',
            'Mẹo dễ nhớ: một bộ đồ không nên quá 3 màu chính để trông hài hòa.',
        ), (
            C('Bạn sắp đi phỏng vấn xin việc. Bộ nào hợp nhất?', ('Áo kim tuyến lấp lánh', 'Đồ ngủ hoạt hình', 'Sơ mi trắng, quần tối màu'), 2,
              'Màu trung tính, kiểu gọn gàng là lựa chọn lịch sự khi phỏng vấn.'),
            N('Theo mẹo dễ nhớ, một bộ đồ hài hòa không nên quá mấy màu chính?', 3,
              'Tối đa 3 màu chính là bộ đồ trông gọn mắt.'),
            O('Sắp xếp các bước tư vấn phối đồ cho khách theo thứ tự hợp lý:',
              ('Hỏi khách mặc đi dịp gì', 'Chọn món đồ chính', 'Phối màu và phụ kiện đi kèm'),
              'Biết dịp trước, rồi chọn món chính, sau cùng mới phối thêm.'),
        )),
    ), extra=(
        C('Đi chơi biển ngày nắng, bộ nào hợp nhất?', ('Vest len dày màu đen', 'Áo sáng màu, vải thoáng', 'Áo khoác da kín cổ'), 1,
          'Đi biển nên chọn màu sáng, vải thoáng cho mát.'),
    )),

    'tt_suutap': S('Thiết kế bộ sưu tập', '👗', (
        L('Ý tưởng và cảm hứng', (
            'Bộ sưu tập là một nhóm mẫu đồ cùng chung một ý tưởng, gọi là chủ đề.',
            'Cảm hứng có thể đến từ thiên nhiên, phố phường, một mùa trong năm hay một bộ phim.',
            'Nghĩ trước khách hàng là ai: tuổi, phong cách, mặc đi đâu, để mẫu đồ đúng người.',
        ), (
            C('Bộ sưu tập thời trang là gì?', ('Một mẫu áo duy nhất', 'Đống vải còn thừa trong kho', 'Nhóm mẫu đồ chung một chủ đề'), 2,
              'Bộ sưu tập là nhiều mẫu cùng chung một chủ đề.'),
            T('Cảm hứng thiết kế chỉ được lấy từ các bộ sưu tập nổi tiếng khác.', False,
              'Cảm hứng có thể đến từ thiên nhiên, phố phường, mùa, phim ảnh...'),
            C('Trước khi thiết kế, vì sao cần nghĩ khách hàng là ai?', ('Để mẫu đồ hợp đúng người mặc', 'Để tốn thêm vải', 'Để vẽ chậm lại'), 0,
              'Hiểu khách giúp mẫu đồ đúng tuổi, đúng phong cách, đúng dịp.'),
        )),
        L('Bảng mood', (
            'Bảng mood (moodboard) là tấm bảng ghép ảnh, mẫu vải, màu sắc để thể hiện cảm xúc của bộ sưu tập.',
            'Nhìn bảng mood, cả nhóm hiểu chung một hướng, tránh mỗi người làm một kiểu.',
            'Từ bảng mood, nhà thiết kế chọn ra bảng màu chính và các loại vải sẽ dùng.',
        ), (
            C('Thứ gì thường KHÔNG cần ghim lên bảng mood?', ('Ảnh cảm hứng', 'Mẫu vải nhỏ', 'Hóa đơn tiền điện'), 2,
              'Bảng mood chỉ gồm ảnh, vải, màu tạo cảm xúc cho bộ sưu tập.'),
            C('Lợi ích lớn của bảng mood khi làm việc nhóm là gì?', ('Không cần vẽ mẫu nữa', 'Cả nhóm hiểu chung một hướng', 'Bán được hàng ngay'), 1,
              'Bảng mood giúp mọi người cùng nhìn về một hướng.'),
            T('Từ bảng mood, nhà thiết kế chọn ra bảng màu chính và loại vải.', True,
              'Đúng, bảng mood là nền để chọn màu và chất liệu.'),
        )),
        L('Đồng bộ và trình diễn', (
            'Các mẫu nên đồng bộ: lặp lại màu, chất liệu hoặc chi tiết để nhìn là biết cùng một bộ sưu tập.',
            'Một bộ sưu tập nhỏ thường có khoảng 6–12 mẫu, đủ để kể trọn một câu chuyện.',
            'Trước buổi trình diễn cần chạy thử: thứ tự người mẫu ra sân khấu, nhạc, ánh sáng.',
        ), (
            O('Sắp xếp quá trình làm một bộ sưu tập theo đúng thứ tự:',
              ('Chọn chủ đề và cảm hứng', 'Làm bảng mood', 'Vẽ và may mẫu', 'Trình diễn ra mắt'),
              'Có chủ đề mới làm bảng mood, rồi vẽ, may và cuối cùng là ra mắt.'),
            C('Điều gì giúp các mẫu trong bộ sưu tập trông đồng bộ?',
              ('Mỗi mẫu một phong cách khác hẳn', 'Lặp lại màu, chất liệu hoặc chi tiết', 'Dùng thật nhiều màu khác nhau'), 1,
              'Lặp lại màu, chất liệu, chi tiết giúp cả bộ trông như một nhà.'),
            C('Việc nào nên làm trước buổi trình diễn?', ('Đổi chủ đề vào phút cuối', 'Bỏ qua buổi thử đồ', 'Chạy thử thứ tự, nhạc, ánh sáng'), 2,
              'Chạy thử giúp buổi diễn suôn sẻ, không bị rối.'),
        )),
    ), extra=(
        C('Một bộ sưu tập nhỏ thường có khoảng bao nhiêu mẫu?', ('1–2 mẫu', '6–12 mẫu', '200 mẫu'), 1,
          'Khoảng 6–12 mẫu là đủ kể một câu chuyện trọn vẹn.'),
    )),

    'tt_kinhdoanh': S('Kinh doanh thời trang', '🛍️', (
        L('Bảng size', (
            'Bảng size ghi rõ số đo (ngực, eo, mông, chiều cao, cân nặng) ứng với từng size S, M, L, XL.',
            'Mỗi xưởng may có form khác nhau, nên size M chỗ này có thể khác size M chỗ khác.',
            'Tư vấn size bằng số đo thật của khách sẽ ít bị đổi trả hơn là đoán bằng mắt.',
        ), (
            C('Cách nào giúp tư vấn size chính xác nhất?', ('Đoán bằng mắt', 'Hỏi số đo thật của khách', 'Luôn chọn size lớn nhất'), 1,
              'Số đo thật so với bảng size là cách chắc ăn nhất.'),
            T('Size M ở mọi cửa hàng luôn có số đo giống hệt nhau.', False,
              'Mỗi xưởng có form riêng nên size M có thể khác nhau.'),
            O('Sắp xếp các size áo từ nhỏ đến lớn:', ('S', 'M', 'L', 'XL'),
              'S nhỏ nhất, rồi đến M, L và XL.'),
        )),
        L('Tồn kho theo mùa', (
            'Nhập hàng theo mùa: mùa hè cần áo thun, váy mỏng; mùa đông cần áo khoác, áo len.',
            'Hàng tồn cuối mùa nên xả giảm giá sớm để thu tiền về và nhường chỗ cho hàng mới.',
            'Lãi gộp mỗi món = giá bán – giá nhập; còn phải trừ tiền mặt bằng, vận chuyển nữa.',
        ), (
            C('Sắp vào đông, shop nên nhập thêm món gì?', ('Đồ bơi', 'Váy hai dây mỏng', 'Áo khoác, áo len'), 2,
              'Mùa đông khách cần đồ ấm như áo khoác, áo len.'),
            N('Áo nhập giá 120 nghìn, bán 200 nghìn. Mỗi áo lãi gộp bao nhiêu nghìn?', 80,
              'Lãi gộp = 200 – 120 = 80 nghìn.'),
            C('Cuối mùa còn nhiều hàng tồn, cách hợp lý là gì?', ('Xả giảm giá sớm để thu tiền về', 'Cất kho đến 5 năm sau', 'Tăng giá lên gấp đôi'), 0,
              'Xả sớm giúp quay vòng vốn và có chỗ cho hàng mới.'),
        )),
        L('Ảnh sản phẩm và đổi trả', (
            'Chụp ảnh sản phẩm ở ánh sáng tự nhiên, nền gọn, đúng màu thật để khách không bị bất ngờ.',
            'Nên có ảnh chụp cận chất vải và ảnh người mặc thật để khách dễ hình dung.',
            'Chính sách đổi trả cần ghi rõ: đổi trong bao nhiêu ngày, còn tem mác, giữ hóa đơn.',
        ), (
            C('Vì sao ảnh sản phẩm cần đúng màu thật?', ('Để ảnh nặng hơn', 'Để chụp nhanh hơn', 'Để khách nhận hàng không bị bất ngờ'), 2,
              'Ảnh đúng màu giúp khách nhận đúng món mình mong đợi.'),
            T('Chính sách đổi trả nên ghi rõ thời hạn và điều kiện như còn tem mác.', True,
              'Ghi rõ ràng giúp khách yên tâm và shop đỡ tranh cãi.'),
            C('Ảnh nào giúp khách hình dung rõ chất vải?', ('Ảnh chụp từ rất xa', 'Ảnh chụp cận chất vải', 'Ảnh mờ có hiệu ứng'), 1,
              'Ảnh cận cho khách thấy rõ bề mặt và độ dày của vải.'),
        )),
    ), extra=(
        C('Khách online hỏi áo có vừa người cao 1m60, nặng 50 kg không. Bạn làm gì?',
          ('Dò bảng size rồi tư vấn size hợp', 'Bảo khách cứ mua đại', 'Không trả lời'), 0,
          'So số đo của khách với bảng size để tư vấn đúng.'),
    )),

    # ---------------- Ngành Du lịch – Khách sạn (khách sạn, lễ tân, hướng dẫn viên, homestay, nhà hàng tiệc) ----------------
    'dl_tongquan': S('Tổng quan du lịch', '🧳', (
        L('Các loại hình du lịch', (
            'Du lịch nghỉ dưỡng là đi để thư giãn, nghỉ ngơi, như nghỉ ở khu nghỉ ven biển.',
            'Du lịch sinh thái gắn với thiên nhiên như rừng, núi, vườn quốc gia, và chú trọng bảo vệ môi trường.',
            'Du lịch văn hóa là đi tìm hiểu di tích, lễ hội, làng nghề và ẩm thực địa phương.',
        ), (
            C('Đoàn khách muốn thăm làng gốm và xem lễ hội. Đây là loại hình nào?', ('Du lịch nghỉ dưỡng', 'Du lịch văn hóa', 'Du lịch thể thao'), 1,
              'Làng nghề và lễ hội thuộc du lịch văn hóa.'),
            C('Đi bộ trong vườn quốc gia, ngắm chim và cây rừng là loại hình gì?', ('Du lịch sinh thái', 'Du lịch mua sắm', 'Du lịch công vụ'), 0,
              'Gắn với thiên nhiên và bảo vệ môi trường là du lịch sinh thái.'),
            T('Du lịch nghỉ dưỡng chủ yếu là đi để thư giãn, nghỉ ngơi.', True,
              'Đúng, nghỉ dưỡng là đi để nạp lại năng lượng.'),
        )),
        L('Du lịch có trách nhiệm', (
            'Du lịch có trách nhiệm là đi chơi vui mà không làm hại thiên nhiên và người dân nơi mình đến.',
            'Mang rác bỏ đúng chỗ, không bẻ cây, bẻ san hô, không khắc tên lên di tích.',
            'Mua đồ, ăn quán của người dân địa phương giúp họ có thêm thu nhập.',
        ), (
            C('Việc nào là du lịch có trách nhiệm?', ('Khắc tên lên tường di tích', 'Bẻ san hô làm kỷ niệm', 'Mua đặc sản của người dân địa phương'), 2,
              'Mua đồ của người dân giúp họ có thêm thu nhập.'),
            T('Bẻ một cành san hô nhỏ mang về làm kỷ niệm thì không sao.', False,
              'San hô lớn rất chậm, bẻ là làm hại thiên nhiên biển.'),
            C('Hướng dẫn viên thấy khách vứt vỏ chai xuống suối. Nên làm gì?',
              ('Lờ đi cho khách vui', 'Nhẹ nhàng nhắc khách nhặt lại bỏ đúng chỗ', 'Mắng khách trước cả đoàn'), 1,
              'Nhắc nhẹ nhàng vừa giữ môi trường vừa giữ thể diện cho khách.'),
        )),
        L('Mùa cao điểm', (
            'Mùa cao điểm là lúc đông khách nhất: dịp hè, Tết và các kỳ nghỉ lễ dài.',
            'Mùa cao điểm giá phòng, giá vé thường tăng và dễ hết chỗ, nên cần đặt trước sớm.',
            'Mùa thấp điểm vắng khách, nhiều nơi giảm giá, tặng ưu đãi để kéo khách.',
        ), (
            C('Gia đình muốn đi biển dịp nghỉ hè. Lời khuyên nào hợp lý?', ('Đến nơi mới tìm phòng', 'Đặt phòng và vé sớm', 'Chờ sát ngày cho rẻ'), 1,
              'Hè là mùa cao điểm, đặt sớm mới có chỗ và giá tốt.'),
            C('Mùa thấp điểm, nhiều khách sạn thường làm gì để kéo khách?', ('Giảm giá, tặng ưu đãi', 'Đóng cửa vĩnh viễn', 'Tăng giá gấp ba'), 0,
              'Vắng khách thì giảm giá, tặng ưu đãi để thu hút khách.'),
            O('Sắp xếp các bước chuẩn bị một chuyến du lịch dịp Tết:', ('Chọn điểm đến', 'Đặt vé và phòng sớm', 'Soạn hành lý', 'Lên đường'),
              'Chọn nơi đi trước, đặt chỗ sớm, soạn đồ rồi mới lên đường.'),
        )),
    ), extra=(
        C('Điều nào đúng về mùa cao điểm du lịch?', ('Giá thường rẻ nhất năm', 'Không ai đi du lịch', 'Khách đông, dễ hết phòng'), 2,
          'Mùa cao điểm đông khách nên phòng, vé dễ hết.'),
    )),

    'dl_letan': S('Nghiệp vụ lễ tân', '🛎️', (
        L('Nhận phòng', (
            'Chào khách bằng nụ cười, hỏi tên để tìm thông tin đặt phòng.',
            'Kiểm tra giấy tờ tùy thân của khách theo quy định trước khi giao phòng.',
            'Giao thẻ phòng, nói rõ số phòng, giờ ăn sáng, mật khẩu wifi và giờ trả phòng.',
        ), (
            O('Sắp xếp các bước làm thủ tục nhận phòng:',
              ('Chào khách, hỏi tên đặt phòng', 'Kiểm tra giấy tờ tùy thân', 'Giao thẻ phòng và dặn thông tin'),
              'Chào và tìm đặt phòng, xem giấy tờ, rồi mới giao thẻ phòng.'),
            C('Khi giao thẻ phòng, lễ tân nên dặn khách điều gì?',
              ('Chuyện riêng của lễ tân', 'Giờ ăn sáng, wifi, giờ trả phòng', 'Giá phòng khách sạn khác'), 1,
              'Dặn thông tin cần thiết giúp khách ở thoải mái.'),
            T('Lễ tân có thể giao phòng cho khách mà không cần xem giấy tờ tùy thân.', False,
              'Phải kiểm tra giấy tờ tùy thân theo quy định trước khi giao phòng.'),
        )),
        L('Đặt phòng và trả phòng', (
            'Khi nhận đặt phòng, ghi đủ: tên, số điện thoại, ngày đến, ngày đi, số người, loại phòng.',
            'Số đêm lưu trú = ngày trả phòng – ngày nhận phòng.',
            'Lúc trả phòng: thu lại thẻ, kiểm tra minibar, in hóa đơn, cảm ơn và mời khách quay lại.',
        ), (
            N('Khách nhận phòng ngày 12, trả phòng ngày 15 cùng tháng. Khách ở bao nhiêu đêm?', 3,
              '15 – 12 = 3 đêm.'),
            C('Thông tin nào KHÔNG cần ghi khi nhận đặt phòng?', ('Ngày đến và ngày đi', 'Số điện thoại', 'Màu áo khách thích'), 2,
              'Màu áo không liên quan gì đến việc đặt phòng.'),
            C('Lúc khách trả phòng, lễ tân cần làm gì?',
              ('Thu thẻ, kiểm tra minibar, in hóa đơn', 'Hỏi khách sao không ở thêm', 'Để khách tự đi, không cần chào'), 0,
              'Thu thẻ, kiểm minibar, in hóa đơn rồi cảm ơn khách.'),
        )),
        L('Xử lý phàn nàn', (
            'Khi khách phàn nàn, hãy lắng nghe hết, không ngắt lời và không cãi lại.',
            'Xin lỗi chân thành, đưa ra cách xử lý cụ thể như đổi phòng hoặc gọi kỹ thuật lên sửa.',
            'Sau khi xử lý xong, gọi hỏi lại khách xem mọi thứ đã ổn chưa.',
        ), (
            O('Sắp xếp các bước xử lý khi khách phàn nàn máy lạnh hỏng:',
              ('Lắng nghe hết ý khách', 'Xin lỗi chân thành', 'Gọi kỹ thuật sửa hoặc đổi phòng', 'Hỏi lại khách xem đã ổn chưa'),
              'Nghe, xin lỗi, xử lý, rồi hỏi lại cho chắc khách hài lòng.'),
            T('Khi khách đang bực, lễ tân nên cãi lại để chứng minh mình đúng.', False,
              'Cãi lại chỉ làm khách bực hơn; hãy lắng nghe và xử lý.'),
            C('Khách báo phòng có mùi thuốc lá khó chịu. Cách xử lý tốt nhất?',
              ('Xin lỗi và đề nghị đổi phòng khác', 'Bảo khách mở cửa sổ là xong', 'Nói khách sạn hết cách'), 0,
              'Xin lỗi và đưa cách xử lý cụ thể như đổi phòng.'),
        )),
    ), extra=(
        C('Khách đến quầy lúc đang đông người. Lễ tân nên làm gì đầu tiên?',
          ('Cúi mặt làm việc tiếp', 'Chỉ tay bảo khách tự xếp hàng', 'Mỉm cười chào và xin khách đợi một chút'), 2,
          'Một nụ cười và lời chào giúp khách thấy mình được quan tâm.'),
    )),

    'dl_huongdan': S('Nghiệp vụ hướng dẫn viên', '🚩', (
        L('Điểm danh và giờ giấc', (
            'Điểm danh khi lên xe và sau mỗi điểm dừng, đủ người mới cho xe chạy.',
            'Nói rõ giờ tập trung và nơi tập trung, nhắc lại 2 lần cho cả đoàn cùng nghe.',
            'Hướng dẫn viên luôn có mặt ở điểm hẹn trước giờ tập trung.',
        ), (
            N('Đoàn có 30 khách, lúc điểm danh lên xe đếm được 28. Còn thiếu bao nhiêu khách?', 2,
              '30 – 28 = 2 khách, phải tìm đủ rồi mới cho xe chạy.'),
            C('Khi nào xe được phép chạy sau điểm dừng chân?', ('Khi tài xế muốn', 'Khi đã điểm danh đủ người', 'Khi hết giờ dù thiếu khách'), 1,
              'Đủ người mới cho xe chạy, không bỏ sót ai.'),
            T('Hướng dẫn viên nên đến điểm hẹn trước giờ tập trung.', True,
              'Đúng, đến trước để đón và điểm danh đoàn.'),
        )),
        L('An toàn cho đoàn', (
            'Luôn mang túi sơ cứu nhỏ, danh sách số điện thoại khách và số cứu hộ ở địa phương.',
            'Đi biển, leo núi: nhắc khách chỗ nguy hiểm, không xuống bơi ở nơi có cờ cấm.',
            'Khách bị lạc: bình tĩnh gọi điện cho khách, cử một người ở lại chỗ hẹn rồi mới đi tìm.',
        ), (
            C('Đi biển thấy cờ báo cấm bơi. Hướng dẫn viên nên làm gì?',
              ('Cho khách bơi xa cho vui', 'Không nói gì', 'Nhắc khách không xuống bơi chỗ đó'), 2,
              'Cờ cấm là báo nguy hiểm, phải nhắc khách ngay.'),
            O('Sắp xếp cách xử lý khi một khách bị lạc đoàn:',
              ('Gọi điện cho khách bị lạc', 'Cử một người ở lại chỗ hẹn', 'Đi tìm quanh khu vực'),
              'Gọi trước, giữ người ở chỗ hẹn để khách quay lại có người đón, rồi mới đi tìm.'),
            C('Vật dụng nào hướng dẫn viên nên luôn mang theo?',
              ('Túi sơ cứu và danh sách số điện thoại', 'Loa kéo hát karaoke', 'Thật nhiều bánh kẹo'), 0,
              'Sơ cứu và số điện thoại giúp xử lý nhanh khi có sự cố.'),
        )),
        L('Kể chuyện điểm đến', (
            'Tìm hiểu kỹ điểm đến từ trước: lịch sử, chuyện dân gian, món ngon, phong tục.',
            'Kể ngắn gọn, vui, thêm câu hỏi nhỏ cho khách đoán để cả đoàn cùng tham gia.',
            'Thông tin chưa chắc chắn thì nói rõ là "tương truyền", không bịa như chuyện thật.',
        ), (
            C('Gặp chuyện dân gian chưa rõ thật hay không, nên giới thiệu thế nào?',
              ('Khẳng định chắc chắn là thật', 'Nói rõ đây là chuyện tương truyền', 'Bịa thêm cho hay'), 1,
              'Nói rõ "tương truyền" là trung thực với khách.'),
            T('Hướng dẫn viên có thể bịa thêm số liệu cho câu chuyện hấp dẫn hơn.', False,
              'Không bịa; chưa chắc thì nói rõ là tương truyền.'),
            C('Mẹo nào giúp đoàn khách chú ý khi nghe thuyết minh?', ('Đọc thật dài một mạch', 'Nói thật nhỏ', 'Đặt câu hỏi nhỏ cho khách đoán'), 2,
              'Câu hỏi nhỏ giúp cả đoàn cùng tham gia, đỡ buồn ngủ.'),
        )),
    ), extra=(
        C('Việc quan trọng nhất trước khi xe rời mỗi điểm tham quan là gì?', ('Chụp ảnh check-in', 'Điểm danh đủ khách', 'Mua quà lưu niệm'), 1,
          'Điểm danh đủ khách để không ai bị bỏ lại.'),
    )),

    'dl_buongphong': S('Nghiệp vụ buồng phòng', '🛏️', (
        L('Thứ tự dọn phòng', (
            'Gõ cửa, báo "Buồng phòng đây ạ", chờ một chút rồi mới vào; phòng treo biển "Xin đừng làm phiền" thì không vào.',
            'Thứ tự dọn: mở rèm cho thoáng, thu rác và khăn bẩn, làm giường, lau bụi, dọn phòng tắm, hút bụi sàn sau cùng.',
            'Lau bụi từ trên xuống dưới để bụi không rơi lên chỗ đã lau sạch.',
        ), (
            O('Sắp xếp các bước dọn một phòng khách sạn:', ('Thu rác và khăn bẩn', 'Làm giường', 'Lau bụi', 'Hút bụi sàn'),
              'Thu dọn đồ bẩn trước, làm giường, lau bụi rồi hút bụi sàn sau cùng.'),
            T('Phòng treo biển "Xin đừng làm phiền" thì nhân viên vẫn vào dọn bình thường.', False,
              'Phải tôn trọng biển báo của khách, không vào phòng.'),
            C('Vì sao lau bụi nên đi từ trên xuống dưới?', ('Để tay đỡ mỏi', 'Để bụi không rơi lên chỗ đã sạch', 'Để đỡ tốn khăn'), 1,
              'Lau từ trên xuống thì bụi rơi xuống chỗ chưa lau, không làm bẩn lại.'),
        )),
        L('Thay ga và vệ sinh', (
            'Ga, vỏ gối, khăn tắm cho khách mới luôn phải được thay đồ sạch, đã giặt.',
            'Dùng khăn riêng cho bồn cầu và khăn khác cho bồn rửa, ly cốc, không dùng lẫn.',
            'Đeo găng tay khi dọn phòng tắm và rửa tay sạch sau khi làm xong.',
        ), (
            C('Có nên dùng chung một khăn để lau bồn cầu và ly cốc không?', ('Có, cho nhanh', 'Có, nếu khăn còn khô', 'Không, phải dùng khăn riêng'), 2,
              'Dùng lẫn khăn sẽ mang vi khuẩn sang ly cốc của khách.'),
            C('Khi dọn phòng tắm, nhân viên nên làm gì để giữ vệ sinh?', ('Đeo găng tay', 'Đi chân trần', 'Dùng khăn mặt của khách'), 0,
              'Găng tay bảo vệ tay mình và giữ vệ sinh cho phòng.'),
            T('Ga giường cho khách mới nhận phòng luôn phải là ga sạch, đã giặt.', True,
              'Đúng, khách mới luôn được dùng đồ vải sạch.'),
        )),
        L('Đồ khách để quên', (
            'Thấy đồ khách để quên thì không tự giữ, không tự vứt, kể cả món đồ nhỏ.',
            'Ghi vào sổ đồ thất lạc: món gì, phòng số mấy, ngày giờ, ai tìm thấy.',
            'Giao đồ cho bộ phận quản lý cất giữ để trả lại khi khách liên hệ.',
        ), (
            C('Dọn phòng thấy chiếc nhẫn khách để quên. Bạn làm gì?',
              ('Giữ lại làm kỷ niệm', 'Ghi sổ đồ thất lạc và giao quản lý', 'Bỏ vào thùng rác'), 1,
              'Ghi sổ và giao quản lý để trả lại đúng chủ.'),
            O('Sắp xếp cách xử lý đồ khách để quên:',
              ('Phát hiện đồ khách để quên', 'Ghi vào sổ đồ thất lạc', 'Giao cho quản lý cất giữ', 'Trả lại khi khách liên hệ'),
              'Thấy đồ thì ghi sổ, giao quản lý giữ, rồi trả khi khách hỏi.'),
            C('Sổ đồ thất lạc cần ghi những gì?', ('Chỉ ghi "có đồ"', 'Giá ước đoán để bán lại', 'Món gì, phòng số mấy, ngày giờ'), 2,
              'Ghi đủ thông tin để tra lại và trả đúng khách.'),
        )),
    ), extra=(
        C('Bước nào thường làm sau cùng khi dọn phòng?', ('Thu rác', 'Làm giường', 'Hút bụi sàn'), 2,
          'Hút bụi sàn sau cùng để gom hết bụi rơi xuống.'),
    )),

    'dl_nhahang': S('Nghiệp vụ nhà hàng – tiệc', '🍽️', (
        L('Bày bàn', (
            'Bày bàn kiểu Âu cơ bản: nĩa bên trái đĩa, dao và thìa súp bên phải, lưỡi dao quay vào đĩa.',
            'Ly nước đặt phía trên, bên phải đĩa, thẳng hàng với mũi dao.',
            'Khăn ăn gấp gọn đặt trên đĩa hoặc bên trái nĩa; khăn, ly phải sạch, không ố.',
        ), (
            C('Khi bày bàn kiểu Âu, nĩa đặt ở đâu?', ('Bên phải đĩa', 'Bên trái đĩa', 'Trong ly nước'), 1,
              'Nĩa nằm bên trái, dao và thìa súp bên phải.'),
            C('Lưỡi dao khi bày bàn nên quay về phía nào?', ('Quay vào đĩa', 'Quay ra phía khách', 'Quay lên trên'), 0,
              'Lưỡi dao quay vào đĩa cho an toàn và đúng chuẩn.'),
            T('Ly nước thường đặt phía trên, bên phải đĩa ăn.', True,
              'Đúng, ly nằm phía trên bên phải, thẳng mũi dao.'),
        )),
        L('Phục vụ món', (
            'Thứ tự món thường gặp: khai vị, món chính, tráng miệng, cuối cùng là trà hoặc cà phê.',
            'Bưng món ra thì nói tên món, đặt nhẹ nhàng, không với tay qua mặt khách.',
            'Món nóng phục vụ khi còn nóng, món lạnh phục vụ khi còn lạnh.',
        ), (
            O('Sắp xếp thứ tự phục vụ món của một bữa ăn:', ('Món khai vị', 'Món chính', 'Món tráng miệng', 'Trà hoặc cà phê'),
              'Khai vị mở màn, món chính ở giữa, tráng miệng rồi trà, cà phê.'),
            C('Khi đặt món lên bàn, nhân viên nên làm gì?',
              ('Với tay qua mặt khách cho nhanh', 'Đặt món rồi đi ngay không nói', 'Nói tên món và đặt nhẹ nhàng'), 2,
              'Nói tên món, đặt nhẹ nhàng là lịch sự và chuyên nghiệp.'),
            T('Để súp nóng nguội bớt rồi mới mang ra cho khách là đúng chuẩn.', False,
              'Món nóng phải phục vụ khi còn nóng.'),
        )),
        L('Khách dị ứng và tiệc cưới', (
            'Khi khách báo dị ứng (tôm, đậu phộng, sữa...), ghi rõ vào phiếu gọi món và báo bếp ngay.',
            'Không chắc món có chứa thứ khách dị ứng thì hỏi lại bếp, tuyệt đối không đoán bừa.',
            'Tiệc cưới đông khách: chia khu, mỗi nhân viên phụ trách vài bàn, ra món đồng loạt theo hiệu lệnh.',
        ), (
            C('Khách nói bị dị ứng đậu phộng. Việc đúng là gì?',
              ('Bảo khách tự gỡ đậu phộng ra', 'Ghi vào phiếu và báo bếp ngay', 'Không cần quan tâm'), 1,
              'Ghi phiếu và báo bếp để bếp nấu món an toàn cho khách.'),
            C('Khách hỏi món gỏi có đậu phộng không mà bạn không chắc. Bạn làm gì?', ('Hỏi lại bếp cho chắc', 'Đoán là không có', 'Bảo khách cứ ăn thử'), 0,
              'Dị ứng có thể nguy hiểm, không chắc thì phải hỏi bếp.'),
            C('Ở tiệc cưới đông khách, cách phục vụ nào hợp lý?',
              ('Ai thích bàn nào bưng bàn đó', 'Đợi khách gọi mới mang món', 'Chia khu, ra món đồng loạt theo hiệu lệnh'), 2,
              'Chia khu và ra món đồng loạt giúp tiệc gọn gàng, không sót bàn.'),
        )),
    ), extra=(
        N('Tiệc có 10 bàn, mỗi nhân viên phụ trách 2 bàn. Cần bao nhiêu nhân viên?', 5,
          '10 : 2 = 5 nhân viên.'),
    )),

    'dl_diali': S('Địa lý du lịch Việt Nam', '🗺️', (
        L('Miền Bắc', (
            'Vịnh Hạ Long ở tỉnh Quảng Ninh nổi tiếng với hàng nghìn đảo đá vôi, là di sản thiên nhiên thế giới.',
            'Sa Pa thuộc tỉnh Lào Cai, vùng núi Tây Bắc, có ruộng bậc thang và khí hậu mát lạnh.',
            'Gần Sa Pa có đỉnh Fansipan, được gọi là "nóc nhà Đông Dương".',
        ), (
            C('Vịnh Hạ Long thuộc tỉnh nào?', ('Quảng Ninh', 'Lào Cai', 'Lâm Đồng'), 0,
              'Vịnh Hạ Long nằm ở tỉnh Quảng Ninh.'),
            C('Đỉnh núi được gọi là "nóc nhà Đông Dương" là đỉnh nào?', ('Bà Đen', 'Fansipan', 'Lang Biang'), 1,
              'Fansipan gần Sa Pa là "nóc nhà Đông Dương".'),
            T('Sa Pa nổi tiếng với ruộng bậc thang và khí hậu mát lạnh.', True,
              'Đúng, Sa Pa ở vùng núi Tây Bắc nên mát lạnh quanh năm.'),
        )),
        L('Miền Trung và cao nguyên', (
            'Huế là cố đô xưa, có Đại Nội, nhiều lăng tẩm và dòng sông Hương thơ mộng.',
            'Hội An nổi tiếng với phố cổ, nhà cổ mái ngói và đèn lồng rực rỡ về đêm.',
            'Đà Lạt thuộc tỉnh Lâm Đồng, nằm trên cao nguyên, khí hậu mát mẻ, được gọi là "thành phố ngàn hoa".',
        ), (
            C('Dòng sông nổi tiếng chảy qua cố đô Huế là sông nào?', ('Sông Hồng', 'Sông Hương', 'Sông Tiền'), 1,
              'Sông Hương là biểu tượng của Huế.'),
            C('Khách muốn dạo phố cổ và ngắm đèn lồng. Bạn gợi ý đi đâu?', ('Hội An', 'Sa Pa', 'Hạ Long'), 0,
              'Hội An nổi tiếng với phố cổ và đèn lồng.'),
            C('Thành phố nào được gọi là "thành phố ngàn hoa"?', ('Huế', 'Hội An', 'Đà Lạt'), 2,
              'Đà Lạt mát mẻ, trồng nhiều hoa nên có tên gọi này.'),
        )),
        L('Miền Nam và biển đảo', (
            'Phú Quốc là đảo lớn nhất Việt Nam, nổi tiếng với biển xanh và nước mắm.',
            'Mũi Cà Mau là điểm cực Nam trên đất liền của Việt Nam.',
            'Miền Tây sông nước có chợ nổi Cái Răng ở Cần Thơ, nơi người dân mua bán ngay trên ghe thuyền.',
        ), (
            C('Đảo lớn nhất Việt Nam là đảo nào?', ('Côn Đảo', 'Cát Bà', 'Phú Quốc'), 2,
              'Phú Quốc là đảo lớn nhất nước ta.'),
            T('Mũi Cà Mau là điểm cực Bắc của Việt Nam.', False,
              'Mũi Cà Mau là điểm cực Nam trên đất liền.'),
            O('Sắp xếp các điểm đến theo hướng từ Bắc vào Nam:', ('Sa Pa', 'Huế', 'Đà Lạt', 'Mũi Cà Mau'),
              'Sa Pa ở Tây Bắc, Huế miền Trung, Đà Lạt trên cao nguyên phía Nam, Cà Mau ở cực Nam.'),
        )),
    ), extra=(
        C('Ở chợ nổi Cái Răng, người dân mua bán bằng cách nào?', ('Trong trung tâm thương mại', 'Ngay trên ghe thuyền', 'Chỉ bán qua mạng'), 1,
          'Chợ nổi là mua bán ngay trên ghe thuyền trên sông.'),
    )),
}
