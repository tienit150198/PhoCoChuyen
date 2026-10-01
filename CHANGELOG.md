# v0.9.19 — Menu gọn, pha màu dễ

- Menu "Thêm" từ 25 xuống 11–12 mục: Công việc (Hành trình, Chuẩn bị, Sổ tiệm, Đánh giá) và Đời sống (Khu phố, Quan hệ, Tiền & nhà, Chuyện của bạn, Của mình), chấm đỏ cộng dồn lên nhóm. Bỏ "Hướng dẫn" khỏi menu: lần đầu vào một nghề hiện một lần "Bỏ qua / Xem hướng dẫn", màn làm việc nghề nào cũng có nút "?", Cài đặt giữ một đường dẫn hướng dẫn.
- Tiệm tóc: bảng pha màu dự tính (xem trước màu bát, so với màu khách cần, oxy có nâng nổi không) và bảng 6×6 các kiểu phối; cùng công thức với máy chủ (test so 527.000 trường hợp).
- Không có "Có gì mới".

# v0.9.18 — Admin: giữ chân người chơi

- Ghi mốc hành trình (stat_milestones), thao tác theo ngày (stat_actions, 60 ngày rồi gộp), tín hiệu rời game và tốc độ tải thật (POST /api/beacon: stat_leaves, stat_loads), lỗi phía người chơi (stat_client_errors), nguồn người chơi (stat_acquisition). Admin có mục "Giữ chân": quay lại D1–D30 theo ngày bắt đầu, phễu người mới, rớt ở đâu, theo nghề, theo nguồn, tốc độ tải, lỗi, dung lượng log. ~3 µs mỗi lệnh; RETENTION_LOG=0 để tắt. Người chơi không thấy thay đổi; không có "Có gì mới".

# v0.9.17 — Đời không như mơ: 5 nghề mới thêm oái oăm

- Thông ống cống, bán trái cây, thu gom rác (game/careers/street_folk.py): người chơi tự báo giá và tự ra giá, NPC có tính cách ẩn tự quyết và tự đánh giá; chặt chém khách và hậu quả, chủ nhà lèm bèm (nhịn/cãi/mời ra/bỏ việc), quỵt, ghi nợ và sổ nợ, chôm chỉa, chê bán đắt, rác nguy hiểm, phá hoại ca đêm, sổ thu phí vệ sinh; 31 tình huống bất ngờ mới. Sửa 5 lỗi của nghề thông cống (lộ giá trước khi nghe khách, kẹt hướng dẫn…).
- Phi công và tiếp viên (game/careers/air_odd.py): 57 tình huống người xung quanh ép, dụ, quấy rối, ép KPI, ép tập gym…; người chơi chọn giọng, câu đáp và người hỗ trợ; kỷ luật tới cách chức nếu chiều theo; báo cáo quấy rối luôn được bảo vệ; phi công hạ cánh trong mưa bão.
- Không có "Có gì mới".

# v0.9.16 — Bắt đầu nhanh và vui hơn

- Người mới: một màn chào + tên + chọn chỗ làm (gợi ý Trà sữa); ngày 1 mở cửa là có khách; hướng dẫn thành gợi ý ngay trên nút. Giao ly đầu tiên sau 10 lần bấm (trước 23).
- Không popup nào trước khách thứ 3; người mới không nhận "Có gì mới"; danh hiệu ngày đầu là thông báo nhỏ; truyện nghề chờ hết ngày 1.
- Khách đầu tiên cho tip, "còn N khách nữa là lên cấp", lên cấp 2 ở khách thứ 3 (trà sữa: 3 ly thay vì 4), quà chào mừng +20 xu cuối ngày 1.
- Gợi ý đúng lúc: đổi nghề, tiền ở đâu, đồng hồ, nút khép ca; tiệm bánh ghi rõ nguyên liệu còn thiếu. Không có "Có gì mới".

# v0.9.15 — Năm nghề mới: trái cây, thu gom rác, thông cống, phi công, tiếp viên

- Ba nghề đường phố, mở ở chương 3 (nhánh careers-street): 🍉 Bán trái cây (Sạp trái cây Dì Tư: dọn sạp, thử cân với quả cân 1 ký, lựa trái dập, chọn đúng độ chín, trừ bì, trả giá, xả hàng chiều tối), 🗑️ Thu gom rác (Tổ thu gom phường Mây, ca tối: đồ bảo hộ, kiểm xe, mở túi lạ, tách đồ nguy hại, ba ngăn, điểm tập kết và tiền ve chai của cô Tám, phản ánh của cư dân), 🪠 Thông ống cống (Thông cống chú Hai: xếp đồ nghề theo sổ hẹn, tìm nguyên nhân, báo giá trước khi làm, xuống hố ga đủ quy trình an toàn, bảo hành). Mỗi nghề có màn hình làm việc riêng (street_kit), cảnh `lane`, cốt truyện, chuyện bất ngờ, ngày khó và hướng dẫn.
- Hai nghề của Hãng bay Cánh Cò, mở ở chương 4, phải ứng tuyển (CV, thư, phỏng vấn) (nhánh careers-air): ✈️ Phi công (cơ phó: bản tin và nhiên liệu, kiểm tra quanh tàu, checklist trước khởi động, quyết định giữa chặng, bay chờ, sân bay dự bị, bay lại không bao giờ là lỗi) và 💺 Tiếp viên hàng không (đón khách ở cửa, hướng dẫn an toàn, xe phục vụ với suất ăn đặc biệt, đèn thắt dây, khách khó, sơ cứu). Giao diện riêng: thẻ lên tàu, bảng giờ bay, phòng tổ bay, Sổ bay (air_kit), cảnh `airfield`, nhóm chứng chỉ An toàn bay.
- Bản lưu cũ chỉ được thêm năm nơi làm mới (chưa nhận việc); các nghề khác không đổi gì: scripts/check_task_compat.py khớp toàn bộ nhiệm vụ mà bản đang chạy (0.9.14) sinh ra cho 23 nghề hiện có.
- 🎁 Quà từ Phố Có Chuyện (nhánh system-gift): quà riêng từ hệ thống (xu vào ví + một thẻ lời nhắn), trả một lần khi mở game, không bao giờ trả hai lần; bảng system_gifts (PostgreSQL SCHEMA_VERSION 4, tạo lúc khởi động), POST /api/gift/seen, scripts/grant_gift.py để tặng. Dùng cho quà xin lỗi sự cố 01/10 00:33–00:36. Không có trong "Có gì mới".
- "Có gì mới" 0.9.15: một dòng cho mỗi nghề mới (chủ game yêu cầu; chỉ tính năng mới), kèm bản tiếng Anh trong i18n/overrides.json. Nguồn dịch i18n/source.json được trích lại.


# v0.9.14 — Admin: thời gian chơi

- Trang admin có mục "Thời gian chơi": phút mỗi người mỗi ngày, độ dài một lượt, người mới ngày đầu, phân bố thời gian và người chơi theo giờ. Đo chính xác bằng trigger trên receipts (bảng stat_play, ~12 µs mỗi lệnh); 2 ngày trước đó ước tính từ biên nhận (scripts/playtime_backfill.py). Người chơi không thấy thay đổi; không có "Có gì mới".

# v0.9.13 — Biệt thự, căn hộ, giá nhà mới; tiền của bạn; sửa lỗi 0.9.5

- Nhà của bạn: thêm 4 loại căn hộ (Studio Nắng Mai 2.400 xu, Căn hộ Mây Xanh 1 phòng ngủ 5.400, Căn hộ Cánh Diều 2 phòng ngủ 10.200, Penthouse Mây Xanh 21.600) và 2 biệt thự (Biệt thự Vườn Cau 36.000, Biệt thự Sông Hồng 60.000), mỗi căn có tinh thần, điện nước và một dòng giới thiệu riêng; biệt thự có vườn, hồ bơi.
- Giá nhà rao bán tăng 20%: căn tập thể 1.800, căn hộ mini 3.600, nhà phố nhỏ 7.800, nhà có sân 14.400 xu. Tiền thuê phòng trọ giữ nguyên (14 xu/ngày, cọc 60) vì là chi phí sinh hoạt hằng ngày, không phải giá nhà.
- Nhà đã mua trước 0.9.13 giữ nguyên giá đã trả, khoản vay và lịch trả góp; giá thị trường khi bán vẫn tính từ giá đã trả (+3%/năm, tối đa +30%), không tự nhảy theo giá rao mới.
- Vay mua penthouse cần điểm tín dụng từ 670, Biệt thự Vườn Cau từ 700, Biệt thự Sông Hồng từ 740; mỗi kỳ trả góp vẫn không quá 40% thu nhập một tháng. Vợ chồng góp quỹ chung mua được mọi loại nhà.
- Nhà đang rao chia theo Phòng thuê / Căn hộ / Nhà phố / Biệt thự, mỗi loại một biểu tượng và màu; mỗi căn ghi giá, số tiền trả trước, góp mỗi tháng (3 năm) và "thiếu N xu". "Bước tiếp theo" gợi ý căn đắt nhất vừa sức (tính cả điểm tín dụng căn đó cần).
- 💰 Thanh trên cùng có hai ô có chữ: "🏪 Quỹ" (quỹ nơi đang làm) và "👛 Ví" (ví riêng, đỏ khi nợ). Bấm vào mở "Tiền của bạn": ví, ngân hàng (tài khoản, tiết kiệm, sổ kỳ hạn và ngày đáo hạn, khoản vay, thẻ), quỹ từng nơi làm kèm nút "Rút về ví · tối đa N", quỹ chung vợ chồng, nhà (giá hôm nay, còn nợ vay), Tổng tài sản và Tổng nợ. Ô 👛 trong bảng trạng thái và ô Ví ở Hành trình cũng mở bảng này.
- Sửa lỗi sau 0.9.5: vợ chồng tặng quà / chuyển quỹ không còn làm lượt bấm tiếp theo của người kia báo "tab khác" (tự thử lại một lần khi lệch phiên bản); quỹ chung hiện đúng dấu tiền rút; nhãn thang điểm tín dụng; dòng "Đến giờ đóng cửa" trên điện thoại; tab Hôn nhân; biểu tượng cho 3 nghề mới; dấu phân cách hàng nghìn; "Free size" thay cho "size F" trên màn hình.
- Tiếng Anh: thêm ~450 câu và ~350 mẫu cho các màn 0.9.5, cùng nhà mới, danh sách nhà theo nhóm, bảng Tiền của bạn và "Có gì mới" 0.9.6–0.9.10; tra cứu lồng nhau không còn làm hỏng bộ nhớ đệm dịch.
- Trước mỗi bản phát hành: scripts/check_task_compat.py so từng nhiệm vụ mà bản đang chạy sinh ra (mọi nghề, ngày 1–40, lượt 0–11) với bản mới; khác một trường là dừng (lỗi "Dữ kiện gốc của nhiệm vụ không hợp lệ" của 0.9.6). Bản này khớp 23.520/23.520 với bản đang chạy.
- Phát hành lặng lẽ: không có mục "Có gì mới" cho 0.9.13 (chủ game quyết định có thông báo hay không).

# v0.9.12 — Làm thử chứng chỉ không nhảy lên đầu

- Thi chứng chỉ: bấm đáp án làm thử hoặc 💡 gợi ý giữ nguyên vị trí cuộn và mục đang mở (public/js/v4/certificates.js: renderSheet() thay vì renderSheet(false)).

# v0.9.11 — Thất tình không bịa người yêu

- Chuyện đời "thất tình": bỏ các thẻ ngầm cho rằng bạn đang có người yêu (bị chia tay, yêu xa, bị cắm sừng, quên sinh nhật; vẫn định nghĩa để bản lưu cũ đang giữ thẻ đó chơi tiếp). Người đã đính hôn/kết hôn với người chơi khác không gặp thẻ thất tình; lời đồn "bị bỏ" chỉ sau khi bị ghost (game/life.py PARTNER_STORIES, DUMPED, _taken; tests/test_life_heartbreak.py).

# v0.9.10 — Đã chuyển sang máy chủ mới

- "Có gì mới" báo nâng cấp hạ tầng đã xong (30/09 21:00: máy chủ mới 9 vCPU, 15 GB RAM; gián đoạn 11 giây, dữ liệu giữ nguyên). Không đổi logic game.

# v0.9.9 — Thông báo bảo trì ngắn

- "Có gì mới" báo bảo trì 21:00–21:10 ngày 30/09 để chuyển sang máy chủ mới; dữ liệu giữ nguyên. Không đổi logic game.

# v0.9.8 — Thông báo nâng cấp máy chủ

- "Có gì mới" báo trước: từ 20:00 đến 0:00 ngày 30/09 hệ thống nâng cấp hạ tầng; vẫn chơi bình thường, trải nghiệm có thể bị ảnh hưởng một chút. Không đổi logic game.

# v0.9.5 — Mua nhà, tủ đồ, tiền luôn trong tầm mắt

- Cập nhật máy chủ không làm mất thao tác: trình duyệt tự gửi lại khi gặp 502/503/504 và hiện "Đang cập nhật máy chủ…"; máy chủ trả 503 `db_unavailable` thay vì lỗi, khóa bảo trì cho lúc chuyển bản; triển khai cuốn chiếu không gián đoạn (deploy/rolling_release.sh, docs/DEPLOY_ROLLING.md); sửa thêm vài điểm SQLite.
- Nhà của bạn: thuê phòng tốt hơn, mua nhà trả trước 30% và vay Ngân hàng Phố trả góp mỗi tháng (tới 3 năm), bán nhà; ở nhà mình thì hết tiền phòng. Vợ chồng góp quỹ chung mua nhà rồi về ở chung.
- Ngân hàng: tiết kiệm có kỳ hạn tới 3 năm, lãi tính theo năm (1 năm = 60 ngày sống, 1 tháng = 5 ngày), tới hạn tự tái tục nếu chọn; sổ cũ giữ nguyên lãi đã hứa.
- Tủ đồ: kiểu tóc, áo quần, giày, phụ kiện cho nhân vật; làm ở Tiệm Áo Chỉ Mây được giảm 20%. Bản lưu cũ giữ đúng dáng nhân vật đang có.
- Khách kiên nhẫn hơn một chút (PATIENCE_FACTOR 1,2 ở game/patience.py: chờ lâu hơn khoảng 20% mới bực hay bỏ về; hai việc đầu ở mỗi nơi vẫn không mất kiên nhẫn).
- Tiền đền nhẹ hơn (COMPENSATION_FACTOR 0,8 ở game/compensation.py): đền hư hỏng, bỏ dở việc, đền cho khách trong chuyện đời và từng nghề giảm khoảng 20%; tiền người chơi nhận về giữ nguyên.
- Người trong phố có chính kiến hơn (khen có gai, chê có lý); cha mẹ nói đúng giới của mình.
- Chip 💰 Ví · Quỹ tiệm trên đầu mọi màn tiêu tiền (ở ngân hàng và Nhà của bạn: Ví · Tài khoản · Quỹ chung); hộp xác nhận ghi "còn thiếu N xu".
- Hàng giao thiếu: nút "Khiếu nại phần thiếu" ngay trong Kho. Tiệm sửa đồ ghi sẵn phụ kiện khách đưa kèm; pet care và shop quần áo hiện lời dặn cạnh chỗ chọn.
- Giao diện yên hơn: thông báo nhiều dòng có biểu tượng, trang Đánh giá theo từng ô, Tổng kết ngày, Chuyện phố, Sổ tiệm và quầy trà sữa bớt ô màu, mỗi màn một nút chính.
- Trang admin: việc thống kê bản lưu không tranh tài nguyên với người chơi.
- Popup "Có gì mới" chỉ còn các điểm của 0.9.5.

# v0.9.4 — Kết hôn, ngân hàng, 3 nghề mới

- Hết giật lag: chạy trên PostgreSQL (từ 0.9.3); 0.9.4 thêm các bảng mới lúc khởi động, không khóa bảng lớn.
- Chương 3 thêm Shop quần áo, Shop thú cưng và quán trà đá vỉa hè.
- Kết hôn (cần tài khoản): nhẫn, cầu hôn bằng mã người chơi, tiệc cưới, tiền mừng, tin trên phố; quỹ chung và thẻ chung vợ chồng; ly hôn.
- Ngân hàng Phố: tiết kiệm, thẻ, khoản vay, điểm tín dụng.
- Bạn bè (tìm theo tên tài khoản) và điểm thân quen với người quen trong phố.
- Chứng chỉ nghề (thi 6 câu, đúng 4 là đạt, có gợi ý 💡) và "Đi cửa sau" khi trượt phỏng vấn.
- Bảng xếp hạng: Top trải nghiệm (cả phố, từng nghề) và Top chứng chỉ; ẩn/hiện tên trong Cài đặt.
- Đồng hồ trong ngày, sáng/tối, giờ mở cửa và đóng cửa; bỏ dở việc giữa chừng có phạt.
- Khách bo tip, khách đưa thiếu tiền (đếm lại, nhắc, cho nợ, báo công an), đánh giá nhiều góc hơn.
- Sách hướng dẫn đầy đủ (87 mục), màn hình gọn hơn trên điện thoại, thông báo hiện lâu hơn, tải nhanh hơn (lazy-load, file nén sẵn).
- Popup "Có gì mới" liệt kê các điểm trên.

# v0.9.3 — Thông báo "Có gì mới" cho toàn máy chủ

- Máy chủ chạy PostgreSQL: mỗi thao tác dưới 0,1 giây, người chơi không phải chờ nhau.
- Bảng "Có gì mới" hiện giữa màn hình cho mọi người chơi (cả người mới), không chờ lúc rảnh.

# v0.9.2 — Máy chủ PostgreSQL, khắc phục giật lag

- Lưu trữ chuyển sang PostgreSQL (bật bằng DATABASE_URL; không có thì chạy SQLite như cũ). Mỗi người chơi chỉ khóa save của mình, không còn hàng đợi ghi chung.
- Công cụ chuyển dữ liệu (scripts/pg_migrate.py, deploy/pg/*): chép trước khi game chạy, đồng bộ, đối chiếu sha256 từng save, chuyển trong vài giây, quay về được.
- Trang admin: tóm tắt nhanh, các mục tải riêng, có cache; không làm chậm người chơi.
- Chịu tải: giới hạn theo IP chỉnh được (NEW_SESSIONS_PER_MINUTE, REGISTER_*, LOGIN_*, BOOTSTRAP_PER_MINUTE), MAX_THREADS mỗi worker; AI rớt kết nối thì dùng câu soạn sẵn.
- Popup "Có gì mới" giữa màn hình: thông báo đã khắc phục sự cố sáng 30/9.

# v0.9.1 — Sửa đặt phòng homestay trên điện thoại

- Chọn phòng đã có khách hoặc không đủ chỗ không còn làm khung "Bước tiếp theo" phình to che hết lịch; ghi chú xuống dòng gọn.
- Bấm cả hàng phòng để chọn (không chỉ ô tên), có dấu ✓ và thông báo "Đã chọn … · 1/2 chỗ"; màn 360px thấy đủ 7 đêm, cột tên phòng đứng yên.
- Thông báo nhỏ không còn đè lên lịch; màn ngang có chỗ để thao tác.

# Chưa phát hành — Dễ nhìn hơn

## Giao diện
- Quán mì cay: phiếu order giờ là danh sách từng dòng (nước dùng, topping, cấp cay, mang về, dị ứng) có dấu ✓/✗/○ theo tô đang làm, thay cho câu dài và mục "Kiểm tô" bị ẩn.
- Lời khách và câu chuyện được gập gọn thành một dòng, bấm để mở.
- Nút mới "📖 Thực đơn": giá, còn bao nhiêu, mở ở cấp mấy, món có hải sản/thịt/chay được và vài luật bếp cần nhớ.
- Trên máy tính, phiếu order đứng cạnh bếp; dải "Hôm nay" gọn một dòng khi đang làm.

## Nhạc nền
- Thay nhạc tự sinh bằng 6 bản nhạc CC0 (miễn bản quyền) từ OpenGameArt, mỗi nhóm nghề một bài, chuyển bài mượt khi đổi nghề. Nguồn và tác giả ở `public/music/CREDITS.md`.

## Âm thanh
- Loa báo tiền: khách chuyển khoản vào tiệm là nghe “ting ting · Đã nhận … xu”, đọc bằng giọng tiếng Việt của máy (tiếng Anh: “Received … coins”). Nhiều khoản về liền nhau gộp thành một lần đọc. Máy không có giọng tiếng Việt thì chỉ ting ting kèm chip “🔔 +… xu”.
- Giọng nhân vật: nhân vật “líu lo” vài âm tiết khi nói, mỗi người một giọng (trẻ con cao, ông bà trầm), dấu thanh tiếng Việt uốn giọng; bạn cũng có giọng riêng khi nhắn tin.
- Âm thanh chi tiết: tiền về, két tính tiền, xong một bước, chuông cửa khi khách tới, chuông nhẹ khi khép ca và lên cấp, tiếng lật giấy khi mở bảng.
- Cài đặt → Âm thanh có ba công tắc mới; tắt “Âm thanh thao tác” là tắt hết.

# v0.5.0 — Một người, một khu phố

## Hành trình của một nhân vật
- Vào game là bắt đầu một câu chuyện: bạn mới chuyển về khu phố, tự đặt tên và chọn giới tính (nam hoặc nữ, không có mặc định). Lời thoại, lời phụ huynh và học sinh gọi bạn theo giới tính đã chọn.
- Nghề mở dần theo 6 chương. Chương đầu có quán trà sữa, tạp hóa và giao hàng; về sau mở tiệm bánh, tiệm hoa, tiệm mẹ & bé, quán ăn, thú cưng, tiệm tóc, sửa đồ, nông trại, homestay, CSKH, nhà thuốc, hướng dẫn viên, giáo viên, kế toán và các văn phòng lớn.
- Tiền có hai tầng: ví riêng của bạn (trả tiền nhà và ăn uống mỗi ngày sống) và quỹ riêng của từng nơi làm (điện nước, mặt bằng, lương, hàng hóa). Có thể rút lãi về ví, góp vốn, tạm nghỉ hay mở lại một nơi làm.
- Nhân vật trưởng thành theo cấp, có kỹ năng và bộ sưu tập danh hiệu; có thể đeo một danh hiệu.
- Bỏ phần chọn "nhịp ngày" và độ khó. Mỗi ngày trời tự định: ngày thường, ngày thong thả hay ngày hội.

## Xin việc
- Nghề cần tuyển dụng phải nộp hồ sơ, phỏng vấn xong và ký thư mời mới được đi làm.
- Thỉnh thoảng gặp may: giám đốc (hay hiệu trưởng) đọc hồ sơ và mời thẳng, hoặc tình cờ gặp sếp cuối ngày và được mời vào làm.

## Nghề đa dạng hơn
- Quầy trà sữa làm tay: chồng ly M/L, bình trà, 12 ô topping có số lượng và ổ khóa, đá, đường, máy dán nắp; khách có thanh kiên nhẫn, khách quen có sổ riêng; mỗi ngày một chuyện riêng (ví dụ học sinh tan học) và bất ngờ ở quầy phải tự quyết.
- Tiệm mẹ & bé: gói quà đúng dịp, đọc nhãn tuổi trên hộp đồ chơi, soạn bộ đồ cho cha mẹ mới, đổi trả không hóa đơn, đơn tiệc nhiều món.
- Quán ăn, tiệm bánh và tiệm hoa: "hên xui của ngày" (mưa, giờ cao điểm, lễ hội…), bất ngờ có hậu quả thật (đoàn kiểm tra, mất hàng, đơn tiệc lớn, người viết review ngồi góc quán), khách có tính cách, chuỗi phục vụ liên tiếp và điểm cuối ngày.
- Nhà thuốc, kế toán và CSKH: bàn giấy tờ kiểu soi hồ sơ, đánh dấu dòng sai, đóng dấu và chịu kết quả.
- Văn phòng (kế toán doanh nghiệp, thuế – lương, tập đoàn): đồng hồ giờ làm, hạn nộp từng hồ sơ, độ tin của sếp, tăng ca và phạt nhỏ.
- Giáo viên có tiết học thật với từng học sinh, kế hoạch vừa khung giờ, phiếu cuối giờ; hướng dẫn viên có đoàn khách với mong muốn riêng, thời tiết, lộ trình và quỹ đoàn.
- Tạp hóa, giao hàng, nông trại và tiệm hoa có thêm tình huống và sửa lỗi nhập hàng, hạn dùng.
- Sửa đồ, tiệm tóc, thú cưng và homestay có thêm tình huống và cách làm mới.

## Giao diện và cảnh
- Nhân vật không còn đi xuyên quầy, kệ hay tường; mọi điểm tương tác đều đi tới được.
- Sắp lại menu: thao tác trong tiệm ở thanh dưới, sổ sách và khu phố ở menu bên (trên điện thoại là "Thêm").
- Bỏ các dòng giải thích hậu trường. Thông báo chồng nhau không còn che đầu thẻ trên điện thoại.
- Sổ thu chi hiện tên đúng cho các khoản mới (lương, hoàn tiền, tiền tip, tiền phạt, sinh hoạt, chuyển quỹ…).

## Ngôn ngữ
- Bản tiếng Anh phủ toàn bộ nội dung mới.

# v0.4.0 — Phố nghề mở cửa

Bản này chuẩn bị để mở game công khai cho mọi người chơi.

## Nghề và công việc thật
- Thêm các nghề mới dạng plugin (`game/careers/`). Mỗi nghề có quầy làm việc riêng, kho nguyên liệu với lô và hạn dùng, nhập hàng, giá bán, nhân viên, và nhiều tình huống ngoài đời kèm nhiều góc nhìn.
- Có bàn chế biến/lắp ráp (như quầy mì); các nghề kế toán, thuế và tập đoàn làm thủ tục nhiều bước (bút toán, đối chiếu, tờ khai); một số nghề như giáo viên và kế toán phải nộp hồ sơ và phỏng vấn mới được nhận vào làm.
- Giáo viên có thêm **Kế hoạch lớp**: bài học nhiều môn, chấm bài, gặp phụ huynh, và lịch năm học 9 tháng với Trung thu, sinh nhật chung trong tháng, 20/11, Hội khỏe Phù Đổng, góc Tết gói bánh chưng mini, dã ngoại nông trại và lễ tổng kết. Mỗi hoạt động kết thúc bằng tóm tắt từ góc nhìn học sinh, phụ huynh và đồng nghiệp.

## Phản hồi và AI nhân vật
- Khách để lại phản hồi sau khi mua hàng hay dùng món, chấm theo từng tiêu chí đúng với những gì đã xảy ra.
- Mỗi người phản hồi có tính cách riêng: chanh chua, bố đời, ấm áp vui tính, kỹ tính, Gen Z, kiệm lời. Với giáo viên, người phản hồi là phụ huynh (hay lo, khó tính, đồng hành).
- Chủ quán trả lời, có thể kèm bù đắp; khách tự quyết định sửa sao, giữ nguyên hay cãi lại (tối đa 3 lượt).
- AI tùy chọn (máy chủ cấu hình LLM, người chơi phải đồng ý), có kịch bản dự phòng. Số sao luôn được kẹp trong khoảng dữ kiện cho phép, và câu trả lời có chèn link hay chèn lệnh sẽ bị loại.

## Phố nghề — chơi cùng nhau
- Hồ sơ công khai, danh bạ quán, ghé thăm quán người khác, đánh giá (chỉ sau khi đã ghé) và trả lời đánh giá.
- Tặng quà (sticker + xu, có giới hạn), chợ nguyên liệu giữa người chơi (giữ hàng hộ, hàng giữ nguyên hạn dùng, giới hạn giá), bảng tin nghề có bình luận và biểu cảm, theo dõi, hộp thư, mục tiêu tuần cả phố.
- Có chặn, báo cáo (nội dung bị 3 người báo cáo sẽ tự ẩn), lọc link/số điện thoại/từ thô tục, giới hạn tần suất.

## Giao diện, âm thanh, ngôn ngữ
- Thiết kế lại giao diện: 5 phong cách (Kem, Trà xanh, Biển, Kẹo, Đêm), bố cục riêng cho điện thoại, máy tính bảng và máy tính (tự nhận hoặc tự chọn), font Be Vietnam Pro tự host.
- Nhạc nền tự sinh theo từng nghề (không dùng tệp nhạc ngoài), chỉnh âm lượng nhạc và hiệu ứng riêng.
- Chọn ngôn ngữ Tiếng Việt / English. Bản tiếng Anh phủ toàn bộ giao diện, nội dung 20 nghề, NPC, sự kiện và câu chuyện; câu ghép từ số, tên hay nhiều đoạn "·" vẫn được dịch từng phần. Thông báo đẩy cũng theo ngôn ngữ đã chọn.
- Cài đặt gom theo thẻ: Chơi, Giao diện, Âm thanh, Ngôn ngữ, Thông báo, Dữ liệu.

## Thông báo và PWA
- Web push (VAPID ES256 viết bằng Python thuần, push không mang nội dung). Thông báo khi có khách ghé, đánh giá, quà, hàng bán được, bình luận; tùy chọn nhắc mở quán mỗi ngày.
- Có manifest, icon, service worker, trang offline; cài được lên màn hình chính (iPhone cần "Thêm vào MH chính" để nhận thông báo).

## Mở công khai an toàn
- Có trang Chính sách quyền riêng tư (`/privacy`) và Điều khoản (`/terms`), liên hệ trachanhtv.works@gmail.com. Người chơi tự xóa được toàn bộ dữ liệu của mình.
- Chạy được sau reverse proxy HTTPS (`TRUST_PROXY`), cookie Secure, HSTS, CSP chặt hơn, gzip + ETag, giới hạn phiên mới, tự dọn phiên cũ. Có Docker healthcheck, compose kèm Caddy (HTTPS tự động) và hướng dẫn `docs/DEPLOY.md`.
- Bản lưu schema 4 (`save-v4`), tự chuyển từ v1–v3. Nghề mới được thêm vào bản lưu cũ ở trạng thái ban đầu.

---

# v0.3.0 — Những ngày nhiều chuyện

- Giữ bốn vòng chơi gốc; thêm giáo viên, hướng dẫn viên và trà sữa. Danh mục có 19 nghề, trong đó 7 nghề chơi được.
- Giao diện kem–hồng, menu bảng phấn, giấy dán, hội thoại khách và ly vector nguyên bản; sửa bố cục màn hình dọc để thanh chức năng không che mục tiêu.
- Ba vòng nghề mới có luật kiểm chứng: bài học/điểm danh/phản hồi; tuyến/thời tiết/kiểm đoàn; nguyên liệu/lô/giá chốt/hạn dùng.
- Thêm 28 bộ trò nhỏ thuộc bốn họ luật, 21 mẩu chuyện ba chặng, 12 loại huy hiệu, ba mục tiêu mỗi ngày, khu phố năm điểm và ngày hội tự chọn.
- Mở rộng thành 42 NPC, 28 ứng viên; vai trò và đạo cụ riêng cho nghề mới. Giữ nhân viên, thu chi, mặt bằng và an ninh v0.2.
- Sửa được lời phản hồi review mà không đổi sao của NPC; bổ sung câu nhận xét vui theo nghề, thưởng ngày chống trùng, combo, tip đội tách két và hao hụt không trừ tiền hai lần.
- Bản lưu v3, chuyển schema 1/2 lên 3. Thêm kiểm thử nghiệp vụ, kiểm thử lại các chức năng cũ và luồng UI bảy nghề; tài liệu đối chiếu phần đã có với phạm vi thiết kế.

## Lịch sử

# Changelog

## 0.2.0 — Boba & đời sống tiệm

### Added
- Operations notebook shared by four playable careers, with separate economy/staff/state.
- 16 hireable employees, career-specific roles and bounded automatic assistance, shift schedules, attendance, rest, training, bonuses, dismissal and scripted factual chat.
- Employee mistakes/misconduct scenarios, evidence, deferred repair invoices, recovery and training outcomes. No automatic wage deductions.
- Cash ledger, daily wages/utilities/coverage, per-shift rent, 7-close fictional tax periods, one extension/bill, receipts and a one-time emergency grant.
- Three premises, capacity guards, visible scene changes and migration-safe existing shelf upgrades.
- Fixed-truth security cases, proof-gated reports, NPC police, separate asset restitution and bounded rewards; pre-event insurance and no duplicate compensation.
- Camera/bell/lock/light props, mode-aware event director and isolated rehearsals.
- Original front-facing boba/pastel artwork for all four careers, dedicated portrait composition, larger touch hit areas, employee/officer sprites and financial hotspots.
- 53 new Python test cases and a dedicated browser operations workflow suite.

### Changed / fixed
- Save schema 2, import both old/new backup envelopes; lazy transactional migration preserves prior gameplay without retroactive bills.
- Every economic mutation goes through the same ledger and SQLite idempotency guard.
- Preserve expanded detail panels on state refresh; reset sheet scroll when switching views.
- Explicitly close SQLite connections after context-managed operations.
- Rehiring does not reset same-day training/bonus limits.

### Scope
Local/LAN playable prototype. No real-user community, public production release, full-autonomous LLM workforce or gameplay for 12 locked careers. Tax, police rewards and insurance are authored fictional game rules. See implementation matrix and test reports.

---

# v0.1.0 — playable prototype

- Bốn vòng nghề độc lập có state và lưu SQLite; 12 nghề tương lai có preview.
- Cảnh vector isometric có di chuyển, hitbox, NPC, trang trí, chụp ảnh.
- Bàn chọn hàng/gói quà; bàn kiểm lô hư cấu; bảng đối chiếu nguồn; màn xử lý CSKH.
- 24 NPC, chat kịch bản theo ngữ cảnh, memory liên kết sự kiện, feed/review/bình luận local.
- 96 vignette dựa trên baseline với evidence/choice/execute; practice không tạo thưởng.
- 12 tuyến mục tiêu/milestone, nâng cấp, nhịp ngày tự chọn, giữ việc qua ca.
- Export/import JSON, xác nhận hành động kinh tế, revision và command idempotency.
- Adapter AI rephrase tùy chọn có consent/fallback; chưa kết nối model thật.
- Script chạy Windows/macOS/Linux, test stdlib, browser test adapter, manifest và kiểm gói giải nén.
