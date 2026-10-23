"""🏫 Du học: Pháp · Lyon, Úc · Melbourne, Trung Quốc · Thượng Hải (game/school.py question bank). Pure data, see game/school_q.py."""
from .school_q import C, T, O, N, L, S

SUBJECTS = {
    # ── Pháp · Lyon (Trường bếp Ánh Sáng Lyon) ──
    'dh_fr_ngu': S('Tiếng Pháp giao tiếp', '🇫🇷', (
        L('Chào hỏi và cảm ơn', (
            'Bonjour nghĩa là "xin chào", dùng suốt cả ngày; buổi tối người ta hay chào bonsoir.',
            'Merci là "cảm ơn", còn au revoir là "tạm biệt" khi ra về.',
            "S'il vous plaît nghĩa là \"làm ơn\", thêm vào cuối câu nhờ vả cho lịch sự.",
        ), (
            C('Bước vào tiệm bánh ở Lyon buổi sáng, bạn chào thế nào?', ('Au revoir', 'Bonjour', 'Merci'), 1,
              'Bonjour là "xin chào", câu chào quen thuộc nhất.'),
            C('"Merci" nghĩa là gì?', ('Xin lỗi', 'Tạm biệt', 'Cảm ơn', 'Làm ơn'), 2,
              'Merci là "cảm ơn", nói nhiều cũng không thừa.'),
            T('"Au revoir" dùng để chào khi vừa gặp nhau.', False,
              'Au revoir là "tạm biệt", dùng khi chia tay ra về.'),
        )),
        L('Gọi món và xin tính tiền', (
            'Je voudrais... nghĩa là "tôi muốn...", cách gọi món lịch sự, ví dụ: Je voudrais un croissant.',
            "Muốn tính tiền ở quán, bạn nói: L'addition, s'il vous plaît.",
            'Excusez-moi là "xin lỗi, cho tôi hỏi", dùng khi muốn gọi người phục vụ.',
        ), (
            C('Muốn gọi một ly cà phê thật lịch sự, bạn mở đầu câu bằng gì?', ('Je voudrais...', 'Au revoir...', 'Bonsoir...'), 0,
              'Je voudrais nghĩa là "tôi muốn", rất lịch sự khi gọi món.'),
            C('Trong quán ăn, "l\'addition" là gì?', ('Thực đơn', 'Món tráng miệng', 'Hóa đơn tính tiền'), 2,
              "L'addition là hóa đơn, nói kèm s'il vous plaît để xin tính tiền."),
            O('Sắp xếp một lần ghé quán cà phê theo đúng thứ tự:', (
                'Bonjour',
                "Je voudrais un café, s'il vous plaît.",
                "L'addition, s'il vous plaît.",
                'Merci, au revoir',
            ), 'Chào khi vào, gọi món, xin tính tiền, rồi cảm ơn và tạm biệt.'),
        )),
        L('Số đếm và phép lịch sự nhỏ', (
            'Đếm 1, 2, 3 tiếng Pháp là un, deux, trois.',
            'Oui là "vâng, có", non là "không".',
            'Nói với người lớn hay người mới gặp, dùng vous cho lịch sự; tu dành cho bạn bè thân.',
        ), (
            C('"Deux croissants" là mấy cái bánh?', ('Một cái', 'Hai cái', 'Ba cái'), 1,
              'Deux là 2, nên deux croissants là hai cái bánh sừng bò.'),
            N('Bạn mua un croissant và trois baguettes. Tổng cộng bạn mua mấy cái bánh?', 4,
              'Un là 1, trois là 3, cộng lại là 4 cái.'),
            T('Nói chuyện với cô bán hàng lần đầu gặp, dùng "vous" là lịch sự.', True,
              'Vous dùng với người lớn và người mới quen, nghe lễ phép hơn tu.'),
        )),
    ), extra=(
        C('Câu nào nghĩa là "làm ơn" trong tiếng Pháp?', ('Bonsoir', 'Oui', "S'il vous plaît", 'Merci'), 2,
          "S'il vous plaît là \"làm ơn\", thêm vào là câu nào cũng lịch sự."),
    )),

    'dh_fr_vh': S('Văn hóa & đời sống Pháp', '🥖', (
        L('Phép lịch sự ở tiệm', (
            'Ở Pháp, vào tiệm là chào "Bonjour" với người bán trước rồi mới hỏi mua.',
            'Quên chào khi vào tiệm dễ bị xem là hơi thiếu lịch sự, dù bạn không cố ý.',
            'Ra về nói "Merci, au revoir" kèm nụ cười là ai cũng vui.',
        ), (
            C('Vào tiệm bánh ở Pháp, điều đầu tiên nên làm là gì?', ('Chỉ ngay vào món cần mua', 'Chào "Bonjour" với người bán', 'Đứng im chờ người bán hỏi'), 1,
              'Chào Bonjour trước rồi mới mua là phép lịch sự quen thuộc ở Pháp.'),
            T('Ở Pháp, vào tiệm mà không chào ai là chuyện hoàn toàn bình thường.', False,
              'Người Pháp rất coi trọng lời chào Bonjour khi bước vào tiệm.'),
            O('Sắp xếp một lần mua bánh thật lịch sự:', (
                'Chào "Bonjour" với người bán',
                'Nói món mình muốn mua',
                'Trả tiền',
                'Cảm ơn và chào tạm biệt',
            ), 'Chào trước, mua và trả tiền, cuối cùng cảm ơn rồi tạm biệt.'),
        )),
        L('Bánh mì và bữa ăn', (
            'Baguette là ổ bánh mì dài, vỏ giòn; nhiều nhà mua bánh mới mỗi ngày.',
            'Bữa ăn ở Pháp thường thong thả, cả nhà ngồi ăn và trò chuyện khá lâu.',
            'Lyon nổi tiếng là thành phố ẩm thực, có rất nhiều quán ăn nhỏ ấm cúng.',
        ), (
            C('Baguette là gì?', ('Bánh ngọt nhân kem', 'Một loại phô mai', 'Ổ bánh mì dài vỏ giòn'), 2,
              'Baguette là ổ bánh mì dài, vỏ giòn, gần như nhà nào cũng ăn.'),
            C('Bữa ăn gia đình ở Pháp thường diễn ra thế nào?', ('Ăn thong thả, vừa ăn vừa trò chuyện', 'Ăn thật nhanh trong 5 phút', 'Mỗi người ăn một phòng riêng'), 0,
              'Người Pháp thích ăn chậm, vừa ăn vừa trò chuyện.'),
            T('Nhiều gia đình Pháp mua bánh mì mới mỗi ngày.', True,
              'Bánh baguette ngon nhất khi còn mới, nên nhiều nhà mua hằng ngày.'),
        )),
        L('Chợ phiên và đi lại', (
            'Chợ phiên họp vài buổi mỗi tuần ở quảng trường, bán rau, trái cây, phô mai tươi.',
            'Trong thành phố, nhiều người đi bộ, đi xe đạp hoặc xe điện cho tiện và đỡ kẹt xe.',
            'Đi xe đạp thì đi đúng làn dành cho xe đạp và nên đội mũ bảo hiểm.',
        ), (
            C('Chợ phiên ở Pháp thường bán gì?', ('Chỉ bán đồ điện tử', 'Rau, trái cây, phô mai tươi', 'Chỉ bán xe máy cũ'), 1,
              'Chợ phiên là nơi mua đồ tươi: rau, trái cây, phô mai.'),
            C('Đạp xe trong thành phố ở Pháp, bạn nên làm gì?', ('Phóng lên vỉa hè cho nhanh', 'Đi ngược chiều cho dễ nhìn xe', 'Đi đúng làn xe đạp, đội mũ bảo hiểm'), 2,
              'Đi đúng làn và đội mũ bảo hiểm thì an toàn cho mình và người khác.'),
            C('Vì sao nhiều người ở thành phố Pháp chọn đi bộ hoặc đạp xe?', ('Vì bị cấm mua ô tô', 'Vì tiện và đỡ kẹt xe', 'Vì đường không có đèn'), 1,
              'Đi bộ, đạp xe vừa tiện vừa khỏe, lại đỡ kẹt xe.'),
        )),
    ), extra=(
        C('Học kỳ ở Lyon, thói quen nào giúp bạn hòa nhập nhanh nhất?', ('Không chào ai cho đỡ ngại', 'Chỉ ăn mì gói trong phòng', 'Chào Bonjour khi vào tiệm, đi chợ phiên'), 2,
          'Chào hỏi lịch sự và đi chợ phiên giúp bạn quen phố, quen người.'),
    )),

    'dh_fr_bep': S('Ẩm thực & bánh Pháp', '🥐', (
        L('Mise en place', (
            'Mise en place nghĩa là "mọi thứ vào chỗ": cân, sơ chế, bày đủ nguyên liệu và dụng cụ trước khi nấu.',
            'Chuẩn bị trước giúp bếp chạy êm, ít quên món và đỡ cuống khi quán đông.',
            'Ở Trường bếp Ánh Sáng Lyon, buổi học nào cũng mở đầu bằng mise en place.',
        ), (
            C('"Mise en place" là gì?', ('Một món tráng miệng', 'Chuẩn bị đủ nguyên liệu, dụng cụ trước khi nấu', 'Cách trang trí đĩa'), 1,
              'Mise en place là chuẩn bị mọi thứ vào chỗ trước khi bắt tay nấu.'),
            O('Sắp xếp các bước bắt đầu một ca bếp:', (
                'Rửa tay, mặc tạp dề',
                'Đọc kỹ công thức',
                'Cân và sơ chế nguyên liệu',
                'Bắt đầu nấu',
            ), 'Sạch sẽ trước, hiểu công thức, chuẩn bị đủ rồi mới nấu.'),
            T('Mise en place giúp bếp bớt rối khi quán đông khách.', True,
              'Đồ đã sẵn sàng thì lúc đông khách chỉ việc nấu, không phải chạy tìm.'),
        )),
        L('Bột nghỉ và gấp bơ croissant', (
            'Bột cần được nghỉ, thường trong tủ lạnh, cho bột dịu lại, dễ cán và không co.',
            'Croissant làm bằng cách gói bơ lạnh vào bột rồi cán gấp nhiều lần để tạo thật nhiều lớp mỏng.',
            'Khi nướng, hơi nước từ bơ đẩy các lớp tách ra, nên bánh xốp và giòn.',
        ), (
            C('Vì sao cần cho bột nghỉ?', ('Cho bột đổi màu', 'Cho bột hết mùi bơ', 'Cho bột dịu lại, dễ cán, không co'), 2,
              'Bột nghỉ thì dịu lại, cán dễ và không bị co rút.'),
            C('Croissant có nhiều lớp mỏng là nhờ đâu?', ('Gói bơ lạnh vào bột rồi cán gấp nhiều lần', 'Trộn thật nhiều đường', 'Nướng thật lâu ở lửa nhỏ'), 0,
              'Cán gấp bơ nhiều lần tạo ra hàng chục lớp bột xen lớp bơ.'),
            O('Sắp xếp các bước làm croissant:', (
                'Nhào bột rồi cho nghỉ lạnh',
                'Gói bơ, cán gấp nhiều lần',
                'Cắt tam giác và cuộn bánh',
                'Ủ nở rồi nướng',
            ), 'Bột phải nghỉ trước, gấp bơ, tạo hình, rồi ủ nở và nướng.'),
        )),
        L('Vệ sinh bếp và dị ứng', (
            'Rửa tay, buộc tóc, lau bàn sạch sẽ trước và sau khi làm bánh.',
            'Nhiều người dị ứng thực phẩm như đậu phộng, các loại hạt, sữa, trứng hay gluten trong bột mì.',
            'Khách báo dị ứng thì ghi rõ, báo bếp, làm món bằng dụng cụ sạch, không để lẫn nguyên liệu đó.',
        ), (
            T('Khách báo dị ứng hạt, chỉ cần nhặt hạt ra khỏi bánh là an toàn.', False,
              'Nhặt ra vẫn còn sót; phải làm món riêng, dụng cụ sạch, không để lẫn.'),
            C('Khách nói mình dị ứng sữa. Bạn làm gì?', ('Cười cho qua', 'Bảo khách cứ ăn thử ít thôi', 'Ghi rõ, báo bếp và kiểm tra thành phần món'), 2,
              'Dị ứng có thể rất nguy hiểm, nên phải ghi rõ và báo bếp ngay.'),
            C('Gluten có nhiều trong nguyên liệu nào?', ('Muối', 'Bột mì', 'Nước lọc'), 1,
              'Gluten là chất đạm có trong bột mì.'),
        )),
    ), extra=(
        C('Trước giờ quán mở, việc nào giúp bếp chạy êm nhất?', ('Chờ khách gọi mới đi tìm nguyên liệu', 'Làm mise en place đầy đủ', 'Ngủ thêm một chút'), 1,
          'Chuẩn bị đủ từ sớm thì giờ đông khách bếp vẫn nhịp nhàng.'),
    )),

    # ── Úc · Melbourne (Học viện Cây Keo Vàng) ──
    'dh_au_ngu': S('Tiếng Anh đời sống ở Úc', '🇦🇺', (
        L('Chào kiểu Úc', (
            "G'day là \"xin chào\" kiểu Úc, rút gọn từ Good day.",
            'Mate nghĩa là "bạn", người Úc gọi cả người mới quen là mate cho thân thiện.',
            '"How are you going?" nghĩa là "Bạn khỏe không?", đáp: "Good, thanks!"',
        ), (
            C("\"G'day, mate!\" nghĩa là gì?", ('Tạm biệt nhé!', 'Chào bạn!', 'Cảm ơn nhiều!'), 1,
              "G'day là xin chào, mate là bạn: \"Chào bạn!\""),
            C('Ai đó hỏi "How are you going?", bạn đáp thế nào?', ('Good, thanks! And you?', 'I am going by bus.', 'Bye!'), 0,
              'Câu này là hỏi thăm sức khỏe, không phải hỏi bạn đi bằng gì.'),
            T('Ở Úc, "mate" chỉ dùng cho bạn thân lâu năm.', False,
              'Người Úc gọi cả người mới quen là mate cho thân thiện.'),
        )),
        L('Từ rút gọn: brekkie, arvo', (
            'Brekkie là "bữa sáng" (breakfast), arvo là "buổi chiều" (afternoon).',
            '"See you this arvo!" nghĩa là "Hẹn gặp chiều nay!"',
            'Người Úc thích rút gọn từ: brekkie, arvo, barbie (tiệc nướng BBQ).',
        ), (
            C('"Arvo" là lúc nào trong ngày?', ('Buổi sáng', 'Buổi tối', 'Buổi chiều'), 2,
              'Arvo là cách nói gọn của afternoon, tức buổi chiều.'),
            C('"Let\'s grab brekkie!" là rủ đi làm gì?', ('Đi ăn sáng', 'Đi bơi', 'Đi ăn tối'), 0,
              'Brekkie là bữa sáng, nên đây là lời rủ đi ăn sáng.'),
            O('Sắp xếp các mốc trong ngày theo thứ tự:', (
                'Ăn brekkie',
                'Ăn trưa (lunch)',
                'Đi chơi this arvo',
                'Ăn tối (dinner)',
            ), 'Sáng ăn brekkie, trưa ăn lunch, chiều là arvo, tối ăn dinner.'),
        )),
        L('No worries và cảm ơn', (
            '"No worries" nghĩa là "không sao đâu, không có gì", dùng khi ai cảm ơn hay xin lỗi bạn.',
            '"Cheers" hay "Thanks heaps" là cách cảm ơn thân mật kiểu Úc.',
            'Lỡ va vào ai thì nói "Sorry", cần đi qua chỗ đông thì nói "Excuse me".',
        ), (
            C('Khách nói "Thanks heaps!", bạn đáp tự nhiên nhất là gì?', ("G'day!", 'No worries!', 'See you this arvo!'), 1,
              'No worries là "không có gì đâu", câu đáp quen thuộc khi được cảm ơn.'),
            T('Ở Úc, "Cheers" có thể dùng để nói cảm ơn.', True,
              'Cheers vừa là lời cảm ơn thân mật, vừa là lời chúc khi nâng ly.'),
            C('Cần đi qua chỗ đông người, bạn nói gì?', ('No worries', 'Brekkie', 'Excuse me'), 2,
              'Excuse me là "xin lỗi, cho tôi đi qua", rất lịch sự.'),
        )),
    ), extra=(
        O('Sắp xếp cuộc trò chuyện ngắn theo đúng thứ tự:', (
            "G'day, mate!",
            'How are you going?',
            'Good, thanks!',
            'See you this arvo!',
        ), 'Chào, hỏi thăm, trả lời, rồi hẹn gặp lại chiều nay.'),
    )),

    'dh_au_vh': S('Văn hóa & đời sống Úc', '🦘', (
        L('Động vật đặc trưng', (
            'Kangaroo (chuột túi) nuôi con nhỏ trong túi trước bụng và di chuyển bằng cách nhảy.',
            'Koala trông giống gấu nhưng không phải gấu; chúng ăn lá bạch đàn và ngủ rất nhiều.',
            'Gặp thú hoang thì ngắm từ xa, không cho ăn đồ của người, lái xe chậm ở chỗ có biển báo.',
        ), (
            C('Kangaroo nuôi con nhỏ ở đâu?', ('Trong tổ trên cây', 'Trong túi trước bụng', 'Trong hang dưới đất'), 1,
              'Kangaroo con lớn lên trong túi trước bụng mẹ.'),
            C('Koala thích ăn gì?', ('Cá biển', 'Bánh mì', 'Lá bạch đàn'), 2,
              'Koala ăn lá bạch đàn và ngủ rất nhiều mỗi ngày.'),
            T('Nên cho kangaroo hoang ăn bánh snack để làm quen.', False,
              'Đồ ăn của người có thể làm thú hoang bị bệnh; chỉ nên ngắm từ xa.'),
        )),
        L('Nắng, biển và thời tiết', (
            'Nắng ở Úc rất gắt, nên thoa kem chống nắng, đội mũ, đeo kính râm khi ra ngoài.',
            'Chỉ bơi ở bãi có cứu hộ, và bơi giữa hai lá cờ đỏ – vàng.',
            'Thời tiết Melbourne đổi rất nhanh, một ngày có thể vừa nắng vừa mưa lạnh, nên mang thêm áo khoác.',
        ), (
            C('Ở bãi biển Úc, bạn nên bơi ở đâu?', ('Giữa hai lá cờ đỏ – vàng của cứu hộ', 'Chỗ vắng, thật xa người', 'Chỗ sóng to cho vui'), 0,
              'Khu giữa hai cờ đỏ – vàng là nơi cứu hộ đang canh chừng.'),
            C('Đi chơi cả ngày ở Melbourne, nên mang theo gì?', ('Không cần mang gì', 'Thêm một đôi dép lê', 'Áo khoác mỏng phòng trời trở lạnh'), 2,
              'Thời tiết Melbourne đổi nhanh, có áo khoác là yên tâm.'),
            T('Ra ngoài nắng ở Úc nên thoa kem chống nắng và đội mũ.', True,
              'Nắng Úc rất gắt, che chắn kỹ để không bị cháy nắng.'),
        )),
        L('Xếp hàng và tiệc nướng', (
            'Người Úc rất coi trọng việc xếp hàng; chen ngang bị xem là bất lịch sự.',
            'Tiệc BBQ ngoài trời rất phổ biến; nhiều công viên có bếp nướng công cộng.',
            'Dùng bếp nướng công cộng xong thì lau sạch, dọn rác cho người sau.',
        ), (
            C('Đến quầy cà phê đông người, bạn làm gì?', ('Chen lên trước vì đang vội', 'Xếp hàng chờ đến lượt', 'Gọi to từ cuối hàng'), 1,
              'Xếp hàng là phép lịch sự người Úc rất coi trọng.'),
            O('Sắp xếp các bước dùng bếp nướng ở công viên:', (
                'Chờ đến lượt dùng bếp',
                'Nướng đồ ăn cùng bạn bè',
                'Lau sạch bếp, dọn rác rồi về',
            ), 'Chờ lượt, nướng, rồi dọn sạch cho người đến sau.'),
            T('Nhiều công viên ở Úc có bếp nướng BBQ công cộng.', True,
              'Tiệc nướng ngoài trời rất phổ biến, nên công viên hay có bếp chung.'),
        )),
    ), extra=(
        C('Ngày đầu ra biển ở Úc, việc nào đúng nhất?', ('Bơi xa bờ một mình', 'Thoa kem chống nắng, bơi giữa cờ đỏ – vàng', 'Ngủ trưa giữa nắng không đội mũ'), 1,
          'Che nắng kỹ và bơi trong khu có cứu hộ là an toàn nhất.'),
    )),

    'dh_au_ks': S('Quản trị nhà hàng – khách sạn', '🏨', (
        L('Đón khách nhận phòng', (
            'Đón khách: mỉm cười, chào hỏi, hỏi tên đặt phòng và kiểm tra giấy tờ.',
            'Giới thiệu ngắn giờ ăn sáng, mật khẩu wifi và cách gọi lễ tân.',
            'Ở Học viện Cây Keo Vàng, sinh viên tập đón khách bằng tiếng Anh mỗi sáng.',
        ), (
            O('Sắp xếp các bước làm thủ tục nhận phòng:', (
                'Chào khách, mỉm cười',
                'Hỏi tên đặt phòng, kiểm tra giấy tờ',
                'Giao thẻ phòng, giới thiệu giờ ăn sáng',
                'Chúc khách nghỉ ngơi vui vẻ',
            ), 'Chào trước, kiểm tra đặt phòng, giao thẻ, rồi chúc khách nghỉ ngon.'),
            C('Câu nào hợp để chào khách ở quầy lễ tân?', ('"What do you want?"', '"Good afternoon, welcome! May I have your name?"', '"Wait there."'), 1,
              'Chào lịch sự rồi hỏi tên đặt phòng là chuẩn lễ tân.'),
            T('Lễ tân nên giới thiệu giờ ăn sáng và wifi cho khách mới.', True,
              'Vài thông tin ngắn giúp khách đỡ phải hỏi lại.'),
        )),
        L('Phòng chưa dọn xong', (
            'Nếu phòng chưa sẵn sàng, xin lỗi khách và báo rõ thời gian chờ dự kiến.',
            'Mời khách gửi hành lý, ngồi nghỉ, uống nước trong lúc chờ.',
            'Báo ngay bộ phận buồng phòng để ưu tiên dọn phòng đó.',
        ), (
            C('Khách đến mà phòng chưa dọn xong. Bạn nên làm gì?', ('Bảo khách cứ ra ngoài đi dạo', 'Giao luôn phòng còn bừa bộn', 'Xin lỗi, báo giờ chờ, mời gửi đồ và uống nước'), 2,
              'Xin lỗi, báo giờ rõ ràng và chăm khách lúc chờ giữ được thiện cảm.'),
            C('Ngoài xin lỗi khách, lễ tân nên báo ngay cho bộ phận nào?', ('Buồng phòng', 'Kế toán', 'Bảo vệ bãi xe'), 0,
              'Buồng phòng là bộ phận dọn phòng, cần ưu tiên phòng đó.'),
            N('Phòng cần 40 phút để dọn, đã dọn được 25 phút. Khách còn chờ bao nhiêu phút?', 15,
              '40 trừ 25 còn 15 phút.'),
        )),
        L('An toàn thực phẩm và chia ca', (
            'Dùng thớt, dao riêng cho đồ sống và đồ chín để không lây vi khuẩn.',
            'Đồ cần giữ lạnh phải cất tủ lạnh; rửa tay sau khi cầm thịt sống.',
            'Quản lý chia ca nghỉ xen kẽ để lúc nào cũng có người trực mà nhân viên không bị kiệt sức.',
        ), (
            C('Vì sao cần thớt riêng cho thịt sống và đồ chín?', ('Cho bếp trông đẹp hơn', 'Tránh lây vi khuẩn từ đồ sống sang đồ chín', 'Cho thớt bền hơn'), 1,
              'Thớt riêng giúp vi khuẩn từ đồ sống không dính sang món đã chín.'),
            T('Cả nhóm phục vụ nghỉ cùng lúc giờ cao điểm là cách chia ca tốt.', False,
              'Nghỉ cùng lúc thì không ai trực; phải chia nhóm nghỉ xen kẽ.'),
            C('Nhà hàng có 6 phục vụ. Cách chia ca nghỉ trưa hợp lý là gì?', ('Cả 6 người nghỉ cùng lúc', 'Không ai được nghỉ', 'Chia 2–3 nhóm nghỉ xen kẽ'), 2,
              'Nghỉ xen kẽ thì luôn có người phục vụ khách, ai cũng được nghỉ.'),
        )),
    ), extra=(
        C('Việc nào thể hiện một quản lý nhà hàng – khách sạn giỏi?', ('Chăm khách chu đáo, bếp sạch, ca nghỉ hợp lý', 'Để nhân viên làm liền 14 tiếng', 'Dùng chung một thớt cho mọi thứ'), 0,
          'Khách vui, bếp an toàn, nhân viên khỏe là nền của nghề quản trị.'),
    )),

    # ── Trung Quốc · Thượng Hải (Học viện Trà Xanh Thượng Hải) ──
    'dh_cn_ngu': S('Tiếng Trung giao tiếp', '🇨🇳', (
        L('Chào hỏi', (
            '你好 (nǐ hǎo) nghĩa là "xin chào", câu chào dùng được với hầu hết mọi người.',
            '谢谢 (xièxie) là "cảm ơn"; đáp lại bằng 不客气 (bú kèqi) là "không có gì".',
            '再见 (zàijiàn) là "tạm biệt, hẹn gặp lại".',
        ), (
            C('Chào cô bán trà sữa ở Thượng Hải, bạn nói gì?', ('再见 zàijiàn', '你好 nǐ hǎo', '谢谢 xièxie'), 1,
              '你好 nǐ hǎo là "xin chào", câu mở đầu thân thiện nhất.'),
            C('Ai đó nói 谢谢 (xièxie) với bạn, bạn đáp thế nào?', ('不客气 bú kèqi', '你好 nǐ hǎo', '再见 zàijiàn'), 0,
              '不客气 bú kèqi nghĩa là "không có gì", đáp lại lời cảm ơn.'),
            T('再见 (zàijiàn) nghĩa là "tạm biệt".', True,
              '再见 zàijiàn dùng khi chia tay, hẹn gặp lại.'),
        )),
        L('Mua sắm và xin lỗi', (
            '多少钱 (duōshao qián) nghĩa là "bao nhiêu tiền?", dùng khi hỏi giá.',
            '对不起 (duìbuqǐ) là "xin lỗi"; người kia hay đáp 没关系 (méi guānxi) là "không sao".',
            'Khi nói chuyện hằng ngày, người ta hay gọi một đồng nhân dân tệ là 块 (kuài).',
        ), (
            C('Muốn hỏi giá một món quà lưu niệm, bạn nói gì?', ('对不起 duìbuqǐ', '你好 nǐ hǎo', '多少钱 duōshao qián'), 2,
              '多少钱 duōshao qián là "bao nhiêu tiền?".'),
            C('Lỡ giẫm vào chân người khác, bạn nói gì?', ('多少钱 duōshao qián', '对不起 duìbuqǐ', '谢谢 xièxie'), 1,
              '对不起 duìbuqǐ là "xin lỗi", người kia sẽ đáp 没关系 méi guānxi.'),
            O('Sắp xếp một lần mua bánh bao ở quầy:', (
                '你好！(Xin chào)',
                '多少钱？(Bao nhiêu tiền?)',
                '谢谢！(Cảm ơn)',
                '再见！(Tạm biệt)',
            ), 'Chào, hỏi giá, cảm ơn khi nhận bánh, rồi tạm biệt.'),
        )),
        L('Số đếm và thanh điệu', (
            '一 (yī) là 1, 二 (èr) là 2, 三 (sān) là 3.',
            '四 (sì) là 4, 五 (wǔ) là 5; biết đếm giúp bạn hỏi giá, mua đồ dễ hơn.',
            'Tiếng Trung phổ thông có 4 thanh điệu và thanh nhẹ; sai thanh dễ thành từ khác, nên nghe và nhại theo nhiều.',
        ), (
            C('Chữ 三 (sān) là số mấy?', ('1', '2', '3'), 2,
              '三 sān là số 3, dễ nhớ vì có ba nét ngang.'),
            N('Bạn mua 二 (èr) cái bánh bao, rồi mua thêm 三 (sān) cái nữa. Tổng cộng mấy cái?', 5,
              '二 là 2, 三 là 3, cộng lại là 5 cái.'),
            T('Tiếng Trung phổ thông không có thanh điệu.', False,
              'Tiếng Trung phổ thông có 4 thanh điệu cùng thanh nhẹ, giống tiếng Việt cũng có dấu.'),
        )),
    ), extra=(
        C('Chữ Hán nào nghĩa là "cảm ơn"?', ('再见', '谢谢', '你好', '对不起'), 1,
          '谢谢 đọc là xièxie, nghĩa là "cảm ơn".'),
    )),

    'dh_cn_vh': S('Văn hóa & đời sống Trung Hoa', '🏮', (
        L('Lễ Tết', (
            'Tết Nguyên Đán (Xuân Tiết) là dịp sum họp lớn nhất; nhà nhà dán câu đối đỏ, trao bao lì xì đỏ.',
            'Tết Trung thu vào rằm tháng Tám âm lịch, cả nhà ngắm trăng và ăn bánh trung thu.',
            'Màu đỏ tượng trưng cho may mắn và niềm vui trong ngày lễ.',
        ), (
            C('Tết Trung thu người ta thường ăn bánh gì?', ('Bánh bao', 'Bánh trung thu', 'Bánh mì baguette'), 1,
              'Trung thu là dịp ngắm trăng và ăn bánh trung thu.'),
            T('Tết Nguyên Đán là dịp các gia đình sum họp.', True,
              'Đây là dịp đoàn tụ lớn nhất trong năm, ai cũng mong về nhà.'),
            C('Màu nào thường thấy trên câu đối và bao lì xì ngày Tết?', ('Màu đỏ', 'Màu đen', 'Màu xám'), 0,
              'Màu đỏ tượng trưng cho may mắn, vui vẻ.'),
        )),
        L('Mời trà và bàn ăn', (
            'Mời trà là cách tiếp khách thân thiện; người trẻ thường rót trà mời người lớn trước.',
            'Không cắm đứng đũa vào bát cơm, vì trông giống nén hương và bị coi là kém may mắn.',
            'Muốn nghỉ tay, hãy gác đũa lên giá đũa hoặc đặt ngang trên miệng bát.',
        ), (
            C('Ăn giữa chừng muốn nghỉ tay, bạn để đũa thế nào?', ('Cắm đứng vào giữa bát cơm', 'Chĩa đũa vào người đối diện', 'Gác lên giá đũa hoặc đặt ngang bát'), 2,
              'Gác đũa lên giá hoặc đặt ngang bát là lịch sự.'),
            T('Cắm đứng đũa vào bát cơm là cách để đũa lịch sự.', False,
              'Đũa cắm đứng trông giống nén hương, nên người ta tránh.'),
            O('Sắp xếp các bước mời trà khi có khách đến nhà:', (
                'Đun nước nóng',
                'Cho trà vào ấm, rót nước pha',
                'Rót trà mời người lớn tuổi trước',
                'Rót cho những người còn lại',
            ), 'Đun nước, pha trà, mời người lớn trước rồi đến mọi người.'),
        )),
        L('Đời sống hiện đại và di sản', (
            'Ở thành phố lớn, trả tiền bằng cách quét mã QR qua điện thoại rất phổ biến, từ quán ăn đến sạp trái cây.',
            'Tàu cao tốc nối nhiều thành phố, đi nhanh, êm và đúng giờ.',
            'Vạn Lý Trường Thành là di sản thế giới nổi tiếng, nhiều đoạn mở cửa cho du khách tham quan.',
        ), (
            C('Ở Thượng Hải, mua ly trà sữa người ta hay trả tiền bằng cách nào?', ('Đổi bằng gạo', 'Quét mã QR bằng điện thoại', 'Chỉ dùng tiền xu'), 1,
              'Quét mã QR rất phổ biến, từ quán lớn tới sạp nhỏ.'),
            C('Muốn đi nhanh giữa hai thành phố lớn, bạn có thể chọn gì?', ('Tàu cao tốc', 'Xe đạp', 'Thuyền chèo'), 0,
              'Tàu cao tốc nối nhiều thành phố, vừa nhanh vừa êm.'),
            C('Công trình nào là di sản thế giới nổi tiếng ở Trung Quốc?', ('Tháp Eiffel', 'Nhà hát Opera Sydney', 'Vạn Lý Trường Thành'), 2,
              'Vạn Lý Trường Thành là di sản nổi tiếng, khách khắp nơi đến thăm.'),
        )),
    ), extra=(
        C('Được mời đến nhà bạn dịp Trung thu, món quà dễ thương là gì?', ('Một hộp bánh trung thu', 'Một túi rác', 'Một đôi giày cũ'), 0,
          'Bánh trung thu là món quà quen thuộc, hợp dịp ngắm trăng.'),
    )),

    'dh_cn_tm': S('Thương mại & xuất nhập khẩu', '📦', (
        L('Báo giá và hợp đồng', (
            'Báo giá là bảng gửi khách, ghi giá, số lượng, thời gian giao hàng và thời hạn hiệu lực của giá.',
            'Hai bên đồng ý thì ký hợp đồng mua bán, ghi rõ hàng, giá, cách thanh toán và ngày giao.',
            'Ở Học viện Trà Xanh Thượng Hải, sinh viên tập viết báo giá bằng cả tiếng Trung và tiếng Anh.',
        ), (
            C('Báo giá gửi khách nên có những gì?', ('Chỉ một con số', 'Giá, số lượng, thời gian giao, hạn hiệu lực', 'Ảnh chụp văn phòng'), 1,
              'Báo giá rõ ràng giúp khách quyết nhanh và tránh hiểu lầm.'),
            O('Sắp xếp một thương vụ theo đúng thứ tự:', (
                'Khách hỏi hàng',
                'Gửi báo giá',
                'Ký hợp đồng mua bán',
                'Giao hàng và thanh toán',
            ), 'Có hỏi mới báo giá, đồng ý thì ký hợp đồng, rồi giao hàng và thanh toán.'),
            T('Hợp đồng mua bán chỉ cần ghi tên hai bên là đủ.', False,
              'Hợp đồng phải ghi rõ hàng, giá, cách thanh toán và ngày giao.'),
        )),
        L('Mẫu hàng và kiểm hàng', (
            'Trước khi đặt số lượng lớn, khách thường xin mẫu hàng để xem chất lượng.',
            'Kiểm hàng là đối chiếu hàng thật với mẫu đã duyệt và hợp đồng: số lượng, màu, kích thước, lỗi.',
            'Phát hiện lỗi trước khi xuất kho thì sửa rẻ và nhanh hơn nhiều so với khi hàng đã sang nước khác.',
        ), (
            C('Vì sao khách xin mẫu hàng trước khi đặt lô lớn?', ('Để được tặng hàng miễn phí mãi', 'Để khỏi phải ký hợp đồng', 'Để xem chất lượng có đúng ý không'), 2,
              'Xem mẫu trước giúp khách yên tâm về chất lượng.'),
            C('Khi kiểm hàng, bạn so sánh hàng với gì?', ('Hàng của tiệm bên cạnh', 'Mẫu đã duyệt và hợp đồng', 'Ảnh trên mạng bất kỳ'), 1,
              'Hàng phải giống mẫu đã duyệt và đúng như hợp đồng.'),
            N('Một lô có 20 thùng, mỗi thùng 50 cái cốc. Lô hàng có bao nhiêu cái cốc?', 1000,
              '20 nhân 50 là 1000 cái cốc.'),
        )),
        L('Vận đơn, hải quan, đóng gói', (
            'Vận đơn là chứng từ của bên vận chuyển, xác nhận đã nhận hàng lên tàu và dùng để nhận hàng ở cảng đến.',
            'Hàng gửi ra nước ngoài phải làm thủ tục hải quan, khai đúng tên hàng, số lượng và giá trị.',
            'Đóng gói chống ẩm: bọc màng nilon, bỏ gói hút ẩm, kê hàng trên pallet, dán kín thùng.',
        ), (
            C('Vận đơn dùng để làm gì?', ('Ghi thực đơn của thủy thủ', 'Quảng cáo sản phẩm', 'Xác nhận hàng đã lên tàu, dùng để nhận hàng'), 2,
              'Vận đơn là giấy tờ quan trọng để nhận hàng ở cảng đến.'),
            T('Khai hải quan cần ghi đúng tên hàng, số lượng và giá trị.', True,
              'Khai đúng giúp hàng thông quan suôn sẻ, không bị giữ lại.'),
            C('Hàng đi tàu biển nhiều ngày, cách nào giúp chống ẩm?', ('Bọc màng, bỏ gói hút ẩm, dán kín thùng', 'Để thùng mở cho thoáng', 'Tưới nước lên thùng cho mát'), 0,
              'Bọc kín và có gói hút ẩm thì hàng khô ráo suốt chuyến đi.'),
        )),
    ), extra=(
        C('Hàng tới cảng nhưng thiếu giấy tờ khai báo. Khâu nào sẽ bị vướng?', ('Viết báo giá', 'Thủ tục hải quan', 'Gửi mẫu hàng'), 1,
          'Thiếu giấy tờ khai báo thì hàng khó làm xong thủ tục hải quan.'),
    )),
}
