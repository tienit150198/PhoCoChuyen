# Chưa phát hành — Thăng tiến rõ ràng, cấp hàm Phó Tổng Giám đốc (WP-C)

- 🏢 "Ngày điều hành tốt" (F#206): Thăng tiến ghi tiến độ "Ngày điều hành tốt: 2/5" kèm thanh và điều kiện (tự xếp ít nhất 1 việc ở 🗓️ Điều phối, cuối ngày điểm điều hành từ 60/100). Phòng điều hành có mục 🎯 "Hôm nay tính ngày tốt?" (đã tự xếp chưa, còn việc cần quyết, ô trống, quỹ lương). Tổng kết ngày ghi điểm và cách tính ("📊 Điểm điều hành 72/100 (đúng giờ 40 + tinh thần 22 + 20 − phàn nàn 12) → ✓ tính 1 ngày điều hành tốt", hoặc lý do chưa tính) và tiến độ n/5. Nhật ký phòng ghi điểm từng ngày. "Xem thêm" giải thích công thức. Thẻ cấp hàm phi công ghi thêm n/5.
- 🎖️ Phỏng vấn lên chức hụt không còn im lặng (#11): báo câu nào bị chấm 0 điểm và bạn đã chọn gì, hoặc "Xin cao" khi chưa có hai câu tốt nhất; ghi rõ hẹn xét lại sau 3 ngày làm. Thăng tiến hiện thẻ "📋 Lần xét vừa rồi" (từng câu: ✅ tốt nhất / 🟡 tạm được / ❌ chưa ưng) và cách đếm ngày tới lần xét sau. Nút "?" ở câu hỏi và phần xin lương nói rõ luật.
- ✈️ Cấp hàm Phó Tổng Giám đốc (F#207, chủ game duyệt): một ngôi sao lớn trên cánh chim vàng, kiểu hàng không, thay cho 4 gạch + 3 sao + cành tùng. Nhãn: "1 sao lớn · cánh chim vàng".
- Không thêm khóa lưu, không đổi tiền. Máy chủ gửi thêm vài trường chỉ để hiển thị (`review` khi hoãn xét, `office.score/good`, `me`, `good_score`, `got/need` ở yêu cầu phòng điều hành, cờ `big/wing` của cấp hàm); bản 1.9.1 bỏ qua chúng.

# v1.9.2 — 2026-10-06: giao diện cũ trở lại

- 🎨 Theo chủ game: giao diện cổ điển (bản đồ phố 2D, cảnh từng tiệm, như 1.8.1) là giao diện mặc định. Máy chủ giữ nguyên 1.9.1 (quầy có nhân viên +50%, sửa tip kế toán ngày 1, dữ liệu Thư giãn trên đảo vẫn được giữ). Đảo 2.5D sẽ quay lại dưới dạng tuỳ chọn ở bản sau.
- Có gì mới: thay mục 1.9.0 (đảo 2.5D) bằng 1.9.2: giao diện quen thuộc, quầy +50%.

# v1.9.1 — 2026-10-06 (hotfix)

- Người chơi mới thi đạt kế toán ngày 1 rồi làm Kế toán doanh nghiệp / tập đoàn: nộp việc đầu tiên bị từ chối "Kết quả tip của công việc sai." (lời chào việc đầu thành tip 0 xu ở nghề không có tip tiền). Giờ là một món quà. Không có "Có gì mới".

# v1.9.0 — 2026-10-06

Có gì mới (chủ game duyệt): đảo 2.5D, Chỉ đường, quầy có nhân viên lãi hơn 50%.

## Phố 2.5D

- 🏝️ Cả game là đảo 2.5D (Phaser): mọi lần mở game đều đứng giữa phố; người chơi mới chọn ngoại hình, đặt tên rồi ra thẳng đảo. Đi tự do mọi hướng bằng cần điều khiển, phím W A S D / mũi tên hoặc chạm đường; chạm cửa tiệm là vào làm, "Ra đảo" để quay lại (đứng ngay trước cửa tiệm vừa làm). Đảo nhớ chỗ bạn đứng trên máy này.
- 🧭 Chỉ đường: chọn nơi muốn tới (mọi nghề, Nhà, Ngân hàng, Bảng xếp hạng, Phố nghề, Hội chợ, Lịch cưới, Quầy, Nhóm phố, Đi dạo, Hẹn hò, Hôn nhân, câu cá, chèo thuyền, bơi) hoặc gõ tìm; nhân vật tự đi theo đường vẽ sẵn, chạm đất hay di chuyển là dừng, tới nơi là mở luôn. Các nơi không phải tiệm có biển chỉ đường trên đảo.
- Cửa tiệm cho mọi nghề, kể cả thư viện, điều dưỡng, dầu khí, đường sắt, hải đăng, tổng đài cứu hộ, cứu hộ bể bơi, công an.
- Thanh trên (tên, ví, quỹ, cài đặt), thẻ việc tiếp theo, Sổ việc, Người quen, Thư giãn (câu cá, chèo thuyền, bơi: miễn phí, không tiền thưởng), Trò chuyện, góc nhìn và thanh dưới Phố · Công việc · Nhân vật · Túi đồ · Thêm. Điện thoại dọc và ngang: không nút nào đè nút nào, tránh tai thỏ; thông báo hiện ở khoảng trống phía trên cần điều khiển.
- Bỏ giao diện cũ (cảnh vẽ 2D của từng tiệm, bản đồ phố 2D): tải nhẹ hơn. Phần Phaser (~360 KB gzip) tải song song với khung hình đầu và chạy ngay sau; mạng chập chờn thì tự thử lại, rồi có nút "Thử lại".
- Hiện người chơi khác trên đảo: `LIVE_TOWN=1` cho dịch vụ live (mặc định tắt).
- Bản lưu: thêm khóa tùy chọn `journey.leisure` (chỉ có khi đã chơi câu cá / chèo thuyền / bơi); bản lưu cũ vẫn đọc bình thường, bản 1.8 đọc bản lưu mới cũng không lỗi. Không đổi tiền, không thêm bảng.
## Quầy: nhân viên bán lãi hơn 50%

- 🧑‍🍳 Ở Quầy của bạn, mỗi đơn nhân viên bán giờ được thưởng 110% phần lãi sau chi phí và thuế (trước đây 40%). Cùng giá, cùng hàng, tiền bạn thực nhận mỗi ngày từ quầy có nhân viên tăng khoảng 50% ở cả Xe đẩy, Sạp chợ và Ki-ốt.
- Đơn bạn tự đứng quầy, đơn online tự đóng gói và đơn khách là người chơi vẫn thưởng 40% như cũ. Quầy đang lỗ (ví dụ Ki-ốt chỉ một nhân viên) không có lãi nên không có thưởng: thuê đủ người hoặc chỉnh giá trước.
- Chỉ áp dụng cho đơn bán từ lúc cập nhật; tiền đã ghi sổ giữ nguyên. Ghi chú trong thẻ quầy và mục Hướng dẫn “Quầy của bạn” ghi rõ hai mức thưởng.

# v1.8.1 — 2026-10-06

## Nghề mới: Người gác hải đăng

- 🗼 Nghề mới ở chương 4 (Được tin cậy): giữ đèn biển Hòn Gió trên một hòn đảo đá cho Xí nghiệp Bảo đảm hàng hải Vịnh Ngọc, cùng chú Bảy Đèn và mèo Mun. Việc làm thuê: ứng tuyển, có lương ngày và thưởng mỗi việc làm đúng quy trình. Chứng chỉ Gác đèn biển giúp dễ được nhận.
- Ca sáng: tắt đèn đúng giờ theo giờ mặt trời mọc, thử sáu thiết bị, tắt mô-tơ rồi mới lau kính, ghi sổ dầu đúng số đo; hỏng thì tự xử lý hoặc báo đúng nơi (sổ trực, phiếu báo hỏng, báo đài khi ảnh hưởng tín hiệu đèn, còi).
- Quan trắc 7 giờ: đọc máy đo gió, mặt biển, các mốc tầm xa, áp kế; báo đài bốn số liệu; gió từ cấp 6 hoặc áp giảm nhanh thì phát cảnh báo cho tàu thuyền. Chạng vạng: thắp đèn đúng giờ, đếm chớp so với danh mục đèn, sương mù chạy còi, đèn sai thì báo đài, ghi sổ đúng sự thật.
- Canh biển: pháo hiệu đỏ giữa bão, tàu chết máy trôi dạt, người rơi xuống nước, tụi nhỏ thách nhau bơi ra đảo, tàu lao về bãi đá ngầm, tàu cố ra khơi khi có lệnh cấm, đánh cá bằng chất nổ. Nhìn kỹ, gọi tàu, ném phao, báo đài đúng mức (MAYDAY RELAY, PAN-PAN, biên phòng) và đúng phương vị, canh giữ mục tiêu. Không bao giờ tự lấy xuồng ra khơi; thuyền trưởng nghe hay không là tùy tính họ.
- Khách ra đảo (17 kiểu): đoàn có giấy, khách sống ảo đòi lên đỉnh tháp, cặp đôi đòi cầu hôn lúc nửa đêm, Vy Vlog livestream, kênh ma đòi tắt đèn, nhà văn xin ở một tuần, kayak lạc lúc chiều tối… Xem giấy tờ rồi tự chọn cách trả lời; khách nài thêm, có người lẻn lên cầu thang tháp. Người gặp nạn luôn được trú tạm.
- Tàu tiếp tế mỗi bảy ngày: đo bồn trước và sau, kiểm từng món, ghi món thiếu hỏng, ký đúng số lít dù chú Tư Lực nài ký đủ 200; trả giá giỏ đồ tươi của chú bằng tiền túi.
- Đời sống trên đảo: nhớ nhà tăng dần, đồ tươi hết giữa hai chuyến tàu; chơi với Mun, tưới vườn rau trên đá, gọi điện về nhà (má hỏi bao giờ lấy vợ lấy chồng). 35 chuyện oái oăm (ông Sáu Ghe xin quay đèn về phía lưới, anh Khôi đòi sơn tháp màu hồng, đếm hải âu, ký khống dầu, ở đảo thêm ba tuần, quấy rối trên kênh 16…), 17 chuyện bất ngờ, 6 tình huống, truyện nghề “Cái giẻ da của chú Bảy”, thang thăng tiến 4 bậc, cảnh đảo và tòa nhà ở Ngoại ô.

## Nghề mới: Nhân viên trực tổng đài cứu hộ

- 📞 Tổng đài Cứu hộ phường Mây (mở ở chương 4 “Được tin cậy”, việc làm thuê): trực đường dây cháy, ngập, tai nạn, kẹt thang máy, thú cưng mắc kẹt, cấp cứu cùng chị Thảo. Chứng chỉ Tiếp nhận cuộc gọi khẩn cấp giúp dễ được nhận; thang thăng tiến 4 bậc.
- Nhận ca: gọi bộ đàm sáu đội, đánh dấu đội tạm ngưng trên bảng đội; quên đánh dấu thì lát gọi đội đó không ai trả lời.
- Mỗi cuộc gọi: hỏi địa chỉ trước, rồi chuyện gì, mấy người, nguy hiểm gì, số gọi lại; người gọi không biết chỗ thì hỏi mốc, gửi định vị, nhờ người đi đường; người đang hoảng thì trấn an (mỗi người hợp một cách, quát là hỏng). Cuộc nghi ngờ (giọng cười, im lặng, bé con, ông Ba gọi lần thứ mười) phải nghe, hỏi kỹ, gọi lại rồi mới quyết: có cuộc thật, có cuộc đùa, do tính ẩn của người gọi.
- Tự chọn mức ưu tiên và đội để gửi, hoặc chuyển đúng nơi với giọng mình chọn (nhẹ, dứt khoát, gắt): khách say đòi taxi, mèo kẹt trên cây từ ba giờ sáng, karaoke, DJ xin “một câu”, “người quan trọng” đòi ưu tiên, gọi nhầm đặt phở… Gửi xe cho chuyện không khẩn thì đội bị giữ chân, ca thật sau phải chờ phường bên.
- Trong lúc chờ: đọc thẻ hướng dẫn an toàn (có thẻ nghe hợp lý mà nguy hiểm: dội nước vào chảo dầu, đi thang máy khi cháy, tháo mũ bảo hiểm), giữ máy với người gọi một mình. Mùa mưa nhiều đường dây réo cùng lúc: nghe nhanh, xếp ưu tiên. Không bao giờ có hướng dẫn cho uống thuốc.
- 42 chuyện oái oăm quanh tổng đài (sếp ép KPI, đồng nghiệp rủ cúp máy khỏi hỏi, tắt ghi âm, sửa giờ nhật ký, fan cuồng giọng tổng đài, họ hàng xin ưu tiên…), 14 chuyện bất ngờ ở phòng trực, 6 tình huống, truyện nghề “Chiếc tai nghe của chị Thảo”, sổ nhật ký cuối ca, cảnh phòng trực và tòa nhà ở Phố dịch vụ.

## Nghề mới: Nhân viên cứu hộ hồ bơi

- 🛟 Nghề mới **Nhân viên cứu hộ hồ bơi** ở Hồ bơi Sóng Xanh (chương 4 “Được tin cậy”): ứng tuyển, phỏng vấn, thử việc; lương ngày cộng thưởng nhỏ cho mỗi việc làm đúng. Anh Hải kèm ba việc đầu, nhắc trước mỗi lỗi một lần.
- Mở hồ: kiểm từng món (độ trong của nước, que thử Clo & pH so “Bảng mẫu Sóng Xanh”, nắp hút đáy, phao ống, phao tròn & sào, hộp sơ cứu, biển độ sâu, điện thoại khẩn), tự gõ số vào sổ nước, tự sửa hoặc báo đúng người; chưa an toàn thì hoãn mở. Cứu hộ không tự đổ hóa chất.
- Canh hồ có hẹn giờ: quét đủ năm khu trong một phút, thổi còi đúng luật (chạy trên bờ, nhảy cắm đầu chỗ cạn, chai thủy tinh, trẻ không người lớn, nhào lộn, quay lén, giả vờ kêu cứu, dìm đầu…). Người đuối nước thật thì im lặng: báo động, gọi hỗ trợ, với hoặc ném trước, xuống nước luôn mang phao ống, xem thở rồi sơ cứu; không bao giờ dốc ngược.
- Soát người ở cổng (say bia, vết thương hở, đau mắt đỏ, không mũ bơi…), lớp bơi trẻ em (bơi thử rồi mới phát vòng tay, bé Bon nói dối biết bơi), sơ cứu không dùng thuốc, dông chiều (lên bờ, trú sảnh có mái, đếm người, ba mươi phút sau tiếng sấm cuối mới mở lại dù sếp giục).
- Hơn năm mươi người oái oăm quanh hồ: ông Tư không chịu đội mũ bơi, cô Hằng nhảy aerobic ở làn nhanh, Kha nhào lộn quay TikTok, phụ huynh dán mắt điện thoại, đại gia đòi làn riêng, khách tán tỉnh xin dạy riêng, quản lý không cho đóng hồ vì doanh thu… Bạn tự chọn giọng, lời nói và báo ai; chiều theo không bao giờ có thưởng. Cuối ca tự ghi sổ trực từ những gì thật sự xảy ra.
- Chứng chỉ Cứu hộ hồ bơi giúp dễ được nhận; thang thăng tiến Cứu hộ chính → Quản lý an toàn hồ bơi.

## Nghề mới: Công an phường

- 👮 Nghề mới **Công an phường** ở Công an phường Mây (chương 4 “Được tin cậy”, mở cùng điều dưỡng, gác chắn): ứng tuyển, phỏng vấn, thử việc; lương ngày cộng thưởng nhỏ cho mỗi việc làm đúng. Nghề người chơi xin, giữ nhẹ nhàng: giúp dân, không có vũ khí hay chiến thuật, không trích luật thật.
- Một ca gồm: giao ban (đọc sổ trực ban, chọn việc gấp làm trước), bàn cư trú (xem từng giấy, nhận hoặc chỉ đúng giấy cần bổ sung), đồ thất lạc (kiểm đếm cùng người nhặt, hỏi kỹ người tới nhận; có người nhận vơ), hòa giải hàng xóm (karaoke, xe đậu chắn cửa, tường nứt, con chó Lu, cây xoài: nghe từng bên rồi tự đề xuất, hai bên tự quyết theo tính), trẻ lạc (dỗ bé, không đăng ảnh, xác minh người đón), tuần tra chợ, cổng trường, hội chợ, đám cưới (nhắc trước, biên bản sau, nguy hiểm thì xử lý ngay), nói chuyện chống lừa đảo cho các cụ, điện thoại trực ban (ai gặp nguy đi trước, gọi lại trước khi coi là tin báo sai).
- Hơn bốn mươi người “oái oăm”: phong bì “cà phê”, cháu “sếp quận”, karaoke nửa đêm, cô Thoa ngày nào cũng có “người khả nghi”, Kha livestream cả bàn tiếp dân, chú say quậy, bà Năm mang chè ngồi kể chuyện cả tiếng, tố bừa nhà bên, sếp đòi đủ chỉ tiêu biên bản… Bạn tự chọn giọng, lời nói và báo ai; nhận phong bì hay chiều theo không bao giờ có thưởng.
- Cuối ca tự ghi sổ trực ban từ những gì thật sự đã xảy ra (dòng “lập thêm biên bản” cho đủ chỉ tiêu là ghi khống). Anh Định kèm ba việc đầu; Chứng chỉ Tiếp dân & hòa giải giúp dễ được nhận; thang thăng tiến Cán bộ khu vực chính thức → Phó trưởng Công an phường; truyện nghề “Cuốn sổ hẻm của anh Định”.

# v1.8.0 — 2026-10-06

Có gì mới (chủ game duyệt): "Cập nhật toàn bộ UI UX", "Thêm Top tài phú trên Bảng xếp hạng".

## Ông Hai 10.000 xu (đã lên trước ở 1.7.16)

- 🪨 Ô ăn quan: thắng Ông Hai được 10.000 xu (trước 500). Bé Bi giữ nguyên (50 xu, cách chơi cũ).
- Ông Hai đi trước và mạnh hơn hẳn: tìm kiếm alpha-beta có bảng chuyển vị, ưu tiên nước ăn, nước "sát thủ", đào sâu dần đến khoảng 8 lượt, giải chính xác khi gần hết quân. Ngân sách tính bằng số nước mô phỏng (20.000), không theo đồng hồ; không cố ý đi nước kém.
- Bản lưu không đổi khóa; bản 1.7.15 cũ vẫn đọc được ván thắng 10.000 xu và ván Ông Hai đã đi trước.

## Sửa: kiểm tra theo phần (tắt mặc định)

- Kiểm tra rút gọn (SCOPED_CAREER_VALIDATION): tiệm có hồ sơ an ninh đang mở, khi sổ an ninh không đổi mà tiệm vẫn bị tính lương/sổ thu chi, không còn bị từ chối nhầm "Tham chiếu hồ sơ an ninh sai." (mã hồ sơ bỏ qua vẫn được đếm). Mặc định vẫn tắt; bật lên thì kết quả giống hệt kiểm tra đầy đủ.

## Nghề mới: Cán bộ thư viện – lưu trữ

- 📚 Thư viện – Lưu trữ phường Mây (mở ở chương 4 “Được tin cậy”): phụ cô Nguyệt giữ sách và hồ sơ của phường. Sáng xem ẩm kế kho (trên 60% bật máy hút ẩm), soi bẫy mọt, chuột, gián, mở phòng đọc.
- Quầy mượn trả: tra ký hiệu, kiểm thẻ (hết hạn, đủ 3 cuốn, còn nợ phí), sách tra cứu chỉ đọc tại chỗ, đặt trước sách đang có người mượn; gợi ý sách theo gu ẩn của bạn đọc.
- Trả sách: tự đề xuất tiền phạt (1 xu/ngày, tối đa 15, cộng phí hỏng), bạn đọc tự quyết theo tính (trả, mặc cả, khất, cãi); miễn khi có lý do chính đáng, ghi sổ nợ, đòi nợ; sửa sách đúng cách.
- Biên mục: xếp 10 lớp, ký hiệu tác giả, lọc sách tặng mốc, lậu, lỗi thời mà giữ sách cũ quý. Phòng đọc: nhắc ồn ào, ăn uống, ngủ ngáy, đôi bạn tình tứ, hút thuốc cạnh kho… mỗi người phản ứng một kiểu.
- Kho lưu trữ: tập huấn trước lượt đầu, kiểm giấy tờ, mức tiếp cận, đúng hộp, tìm hồ sơ kẹp nhầm, cấp bản sao (bản gốc không rời kho), ghi sổ. Hơn 60 kiểu nhờ vả oái oăm, 16 chuyện bất ngờ, 6 tình huống, truyện nghề, Chứng chỉ nghiệp vụ lưu trữ.

## Nghề mới: Thợ dầu khí

- Nghề mới 🛢️ Thợ dầu khí (chương 4, cạnh phi công): kỹ thuật viên vận hành trên giàn Hải Âu của Dầu khí Sóng Bạc, việc làm thuê lương đi biển cao. Đợt 14 ngày: ngày bay trực thăng ra giàn, bốn ngày ca 12 tiếng, ngày bàn giao về bờ; bão tới thì ở lại thêm trên giàn hoặc chờ ở bờ.
- Ngày bay: soạn túi (không bật lửa, bình xịt, dao, rượu, thuốc lá điện tử, tối đa 15 kg), mặc đồ bơi giữ nhiệt, áo phao, bình thở, chụp tai, trả lời câu thoát hiểm trực thăng, sương mù thì ngồi chờ. Lên giàn: gắn thẻ bảng đếm người, nhận xuồng cứu sinh theo biển cửa phòng, nhớ ba tiếng còi.
- Mỗi ca: họp an toàn (đồ bảo hộ, thử khí mẫu máy đo, mối nguy), bảo dưỡng có giấy phép (đúng loại giấy phép, đối chiếu việc cẩu, khóa và treo thẻ từng điểm, xả áp, kiểm về không, đo khí, người canh lửa/canh bồn), đi tuần đọc đồng hồ, báo động đi ngược gió về đúng xuồng. Có lúc van lọt, khí rò, thiếu ôxy, cẩu trên đầu, cầu dao ghi nhầm: ✋ Dừng việc luôn đúng, dừng mà không có gì sai cũng không bị trừ; báo suýt sự cố được cảm ơn.
- Ngày về bờ: bàn giao thật cho ca sau, rồi cả nhà nhờ tiền: hỏi rõ, gửi số mình chọn hoặc không gửi, mặc cả với người nhà; có khoản cần thật, có khoản là trò lừa.
- 42 chuyện oái oăm (sếp ép bỏ bước đo khí, nhà thầu ký khống checklist, bạn cùng phòng ngáy, chê cơm nhà ăn, Má gọi lúc mất sóng, em đòi điện thoại mới, anh họ rủ góp tiền ảo, ở lại thêm ca, quấy rối và bắt nạt…), 15 chuyện bất ngờ theo ngày đi biển, 6 tình huống; chứng chỉ An toàn cơ bản ngoài khơi, thang thăng tiến 4 bậc, truyện nghề, hướng dẫn, cảnh giàn khoan và tòa nhà ở khu Sân bay.

## Nghề mới: Gác chắn đường sắt

- Nghề mới ở chương 4 (Được tin cậy): nhân viên gác chắn đường ngang Bến Mây kiêm tuần đường cho Xí nghiệp Đường sắt Sông Mây. Việc làm thuê: ứng tuyển, có lương ngày và thưởng mỗi chuyến gác đúng quy trình. Chứng chỉ An toàn đường ngang giúp dễ được nhận.
- Nhận ca: đọc sổ giao ca, thử từng thiết bị (chuông đèn, cần chắn, bộ đàm, cờ đèn…), hỏng thì tự xử lý (thay pin, lắp tay quay) và báo đúng nơi: sổ giao ca, phiếu báo hỏng hay gọi ga.
- Mỗi chuyến tàu: nghe ga gọi và nhắc lại lệnh, dẹp người trên ray (khách chụp ảnh, tụi nhỏ, chú Hớn ngủ quên, con bò, xe ba gác kẹt…), chuông trước chắn sau, hạ chắn đúng lúc, giữ chắn trước gần 30 kiểu người đòi qua (xe ôm, đám tang, xe hoa, xe cứu thương, người dúi tiền, TikToker…); bạn tự chọn cách trả lời, người ta tự quyết theo tính. Không dẹp kịp thì báo dừng tàu: luôn đúng.
- Tàu chậm giữa chừng, tàu thứ hai chạy ngược chiều, toa thiếu đèn đuôi, bầu trục bốc khói: nhìn hết đoàn tàu, hỏi ga trước khi nâng chắn, ghi sổ nhật ký đúng sự thật.
- Tuần đường Km 7 – Km 8: bu lông lỏng, tà vẹt nứt, đá ba-lát trôi, ray nứt, ray cong vì nắng, đèn tín hiệu tắt, nong ớt trên ray… tự xử lý, cắm cờ phòng vệ, điện khẩn hay ghi đúng phiếu.
- Chuyện oái oăm quanh chòi gác: lời mời “có ý”, quấy rối, sếp bảo sửa giờ cho đẹp, đồng nghiệp nhờ ký sổ khống, gác thêm ca đêm; ca đêm làm mệt, mệt thì phải tỉnh táo trước khi nghe lệnh. Có truyện nghề “Cái còi đồng của chú Sáu”.

## Nghề mới: Điều dưỡng

- 🏥 Nghề mới **Điều dưỡng khoa Nội** ở Bệnh viện phường Lá Sen (chương 4, mở cùng nhà thuốc, phi công): ứng tuyển, phỏng vấn, thử việc; lương ngày cộng thưởng nhỏ cho mỗi việc làm đúng. Cũng là nghề “bệnh viện” người chơi xin.
- Một ca gồm: nhận giao ca (đọc sổ, chọn giường xem trước), đo dấu hiệu sinh tồn rồi tự gõ số vào phiếu, so thẻ báo động và báo bác sĩ, cho thuốc theo y lệnh (hỏi tên + ngày sinh, vòng dị ứng, nhãn khay, đường huyết, biển nhịn ăn), chuông gọi, phân loại ở quầy tiếp đón theo thẻ màu, chuẩn bị thủ thuật (giấy cam đoan, nhịn ăn, trang sức), ra viện (giấy ra viện, BHYT, rút kim luồn, dặn dò, nhờ nhắc lại).
- Chị Hoa kèm ba việc đầu, nhắc trước mỗi lỗi một lần. Người bệnh có quyền từ chối: hỏi, giải thích, báo bác sĩ; ép là lỗi. Không có liều thuốc nào trong game: bác sĩ quyết điều trị.
- Hơn bốn mươi người “oái oăm” quanh khoa: phong bì, 500 xu đổi giường đẹp, đòi bác sĩ giỏi nhất, cả họ vào thăm, “thần y” mang thuốc nam, quay clip, khách say ca tối, đồng nghiệp rủ làm tắt, ép trực thêm ca, người nhà xin giấy nghỉ ốm giả… Bạn tự chọn giọng, lời nói và báo ai; chiều theo không bao giờ có thưởng.
- Cuối ca tự viết sổ giao ca từ những gì thật sự đã xảy ra (ghi khống bị trừ điểm hồ sơ). Chứng chỉ An toàn người bệnh giúp dễ được nhận; thang thăng tiến Điều dưỡng chính → Trưởng phòng Điều dưỡng.

## Kiểm tra giao diện trước phát hành (tiệc cưới, hội chợ, màn live)

- Tiệc cưới khi xoay ngang: lễ đường lại hiện trọn cả sân (cô dâu chú rể, sân khấu, múa lân, pháo hoa), không bám theo khách đứng ở cổng hoa nữa; thanh trên cùng gọn một hàng, mâm cỗ một hàng 8 món, bảng chọn nhạc 4 bài một hàng.
- Hội chợ xoay ngang: bản đồ hội chợ không lấn xuống thanh vuốt ở đáy màn hình.
- Điện thoại hẹp (360 px): tiêu đề dài nhường chỗ cho số xu ở thanh trên (Bày trí phòng không còn cắt "860 xu").

## WP1 Nhân viên tiệm & nhập hàng

- Nhân viên bán theo cả danh mục hàng của tiệm (Mẹ & Bé, tạp hóa, thú cưng, trái cây, hoa, trà đá, kem, cơm, phở, mì cay, cà phê, salon, nail, sửa chữa…), chỉ món còn hàng, ưu tiên món còn nhiều; hết thỏ bông vẫn bán món khác.
- Đơn riêng của nhân viên tính theo giá kệ của chính nghề và luôn có lãi sau lương, vật tư; món lãi mỏng thì bán theo lố (vài ký gạo, chục trứng), kem bán nguyên hộp 1,2 kg thay vì giá một viên.
- Sổ tiệm hiện đơn tiếp theo: giá thu, lương, vật tư, giá vốn, lãi ước tính; tiền vào quỹ nghề; khi đội dừng thì nói rõ đang hết món gì hoặc giá không đủ bù lương.
- Tiệm Mẹ & Bé đặt đơn gộp nhiều mã một lần (tối đa 12 mã, một chuyến xe, trả một lần).
- Đơn gộp ở kho: tối đa 20 dòng, nhiều size của cùng một món trong một đơn, 12 đơn đang giao cùng lúc; báo rõ tiền nhập hàng trừ vào quỹ nghề.

## WP2 Đánh giá, kiểm duyệt & an toàn

- Đánh giá NPC: mọi đánh giá đều báo cáo được. Đánh giá lạc đề, nhầm quán, chưa ghé, cài cắm, chê chuyện ngoài lề và "hùa theo" bị gỡ khỏi điểm trung bình (vẫn giữ, có đánh dấu). Báo cáo không được duyệt giữ nguyên sao, không kéo thêm 1★; hùa theo không bao giờ kéo hùa theo.
- Khách lạ viết đánh giá là khách cùng nghề; đánh giá "nhầm quán" ít hơn. Bù xu cho đánh giá không thể đổi (nhầm quán, chưa ghé…) được cảnh báo trước, không trừ xu; khung trả lời ghi "khách trả lời sau ~2 lượt làm".
- Đánh giá giữa người chơi (Phố nghề, dịch vụ chỗ làm): chỉ tính đánh giá mới nhất của mỗi người, tài khoản từ 3 ngày tuổi, không tính đánh giá trong 24 giờ quanh lúc chủ quán chuyển xu/tặng quà xu. Không xóa đánh giá nào.
- Tên hiển thị: đổi tên ở Cài đặt và Hành trình dùng chung bộ lọc tên tài khoản, chặn thêm cách viết không dấu/viết liền (concac, dcm…). Quản trị có danh sách tên vi phạm và nút "Đổi tên an toàn"; không tự đổi tên ai.
- Chat: nhắc nhở an toàn thân thiện (một lần) khi tin nhắn có hẹn gặp, địa chỉ, số điện thoại, zalo/fb/ig/tiktok; lý do báo cáo "An toàn / trẻ vị thành niên" lên đầu hàng chờ quản trị; khóa chat theo phút và chế độ chậm cho từng người hoặc cả Cả phố; @tên người chơi đang có trong Cả phố không bị che. Không tự cấm ai.
## WP3 Nghề & hàng tiệm

- Tiệm áo, salon: bill/phương án lố ngân sách mở 💬 Trao đổi: gợi ý món rẻ hơn hoặc dời dịch vụ, xin thêm ngân sách (khách tự quyết theo tính, chỉ hỏi một lần), bớt giá trong mức chủ cho, hoặc nói thật. Lờ khách hay thất hứa vẫn bị trừ.
- Tiệm áo thêm 14 món: đầm maxi, váy babydoll, set áo + chân váy, blazer, cardigan, polo, chân váy chữ A, quần tây, quần short, sneaker, sandal, túi xách, bông tai, khăn lụa; khách quen hay dặn thêm (lấy thêm món, muốn mặc đầm, không jean, giày đi biển). Món mới nhập qua Kho; tủ đồ có thêm đồ tương ứng.
- Lớp học: lời học trò hiện ngay sau tối đa 2 giây (AI viết lại thì thay sau); phiếu cuối tiết có dòng hướng dẫn chấm.
- Giữ trẻ: tính bé hiện rõ dưới “🙂 Chào bé”, chào sai thì nhắc đúng tính bé.
- Buồng ảnh: mã phòng gõ được R, S, F, X, J, W, DD dù đang bật Telex.
- Giao hàng: đơn mới hiện giờ hẹn trước khi nhận (ngày 1: giao trong bao nhiêu phút).
- Thú cưng: thẻ việc có nút Khép ca khi đang để lát nữa, hết giờ hoặc thiếu hàng (kèm dòng “Hết …”).
- Homestay: 📥 Hộp đơn OTA có huy hiệu số đơn trùng và hướng dẫn xử lý.
## WP4 Thăng tiến dài hơn

- Phi công: cấp hàm có gạch/sao (Cơ phó cấp thấp 1 gạch → Trưởng đội bay 4 gạch 1 sao), thêm Phó Giám đốc, Giám đốc Khối khai thác bay và Phó Tổng Giám đốc (trần).
- Giáo viên lên tới Hiệu trưởng. Các nghề khác giữ thang 4 bậc; không ai bị hạ bậc, bậc cũ giữ nguyên.
- 🏢 Phòng điều hành cho bậc lãnh đạo: điều phối chuyến bay/phân công, nhân sự NPC (nói chuyện, khen, nhắc nhở, cảnh cáo, kiểm điểm, đình chỉ, thăng/giáng chức, tăng/hạ bậc lương) theo tính cách ẩn, việc khó cần quyết; ảnh hưởng đúng giờ, phàn nàn, tinh thần, quỹ lương và thưởng điều hành.
- Bản lưu: bậc trên 4 và phòng điều hành nằm ở khóa phụ, bản cũ vẫn đọc được khi lùi phiên bản.
## WP5 Nhà, nội thất & cuộn ổn định

- Thêm 55 món nội thất cho mọi phòng (phòng khách, ngủ, bếp, tắm, ban công, sân vườn) và đồ nhỏ: đèn, cây, thảm, khung ảnh, kệ, đồ chơi, đồ bếp; kệ mới "Bếp & ăn uống", ba bộ góc mới, máy chiếu dải ngân hà phủ sao lên tường.
- Xoay mặt trước/mặt sau cho 29 món (giường, bàn, ghế, tủ, tủ lạnh, piano…), không chỉ ti vi và sofa.
- Mỗi phòng bày được gấp rưỡi số món; khi đầy, báo đúng số món tối đa và cách bày thêm.
- Nhà của bạn có mục "Đồ đạc của bạn": mọi món đang có (nội thất từng phòng và trong túi, quần áo, xe, đồ ăn trong tủ lạnh, giấy dán tường) kèm tên và thông tin.
- Thanh trượt đồ trong Bày trí kéo được tới món cuối, nút ‹ › không bị khóa khi đang chờ máy chủ, không nhảy về đầu khi cập nhật.
- Danh sách trong các bảng không còn giật về đầu khi đang cuộn hoặc sau khi bấm; chi tiết đánh giá trên màn rộng cuộn được.
- Không đổi tiền hay dữ liệu cũ; bản lưu mới vẫn đọc được trên bản 1.7.15 (đồ vượt sức chứa cũ và hướng xoay mới nằm ở khóa riêng).
## WP10 💰 Top tài phú

Chủ game (05/10): "thêm top tài phú nhé … thêm top tài phú cho toàn server". Không có "Có gì mới", không thông báo. Chuyển từ nhánh lb-wealth-17 sang đúng cây đang chạy (7b3b72c, 1.7.15) và tính thêm tiền/tài sản có từ 1.5–1.7.

- Bảng xếp hạng có tab mới 💰 **Tài phú** (`board=wealth`): ai giàu nhất phố. Điểm = tài sản ròng tính trên server từ bản lưu (`game/wealth.py` `worth()`):
  - đúng như "Tiền của bạn" (`public/js/v4/wealth.js` pockets(): Tổng tài sản − Tổng nợ): ví (âm thì là nợ), quỹ mọi nơi làm đã mở, ngân hàng (tài khoản + tiết kiệm không kỳ hạn + các sổ có kỳ hạn − nợ vay còn lại − dư nợ thẻ), mọi căn nhà đang sở hữu theo giá thị trường hôm nay (`housing.value_of` với hệ số thị trường nhà lúc mua) − nợ vay mua nhà còn lại;
  - cộng thêm những gì bảng tiền chưa liệt kê nhưng bản lưu giữ sẵn bằng số: sổ tiết kiệm Mây (`invest.saving.balance`), Mây Coin và vàng theo **giá vốn** đã lưu (`invest.coin.basis` khi còn `units`, `vang.cost` khi còn `phan`: số xu đã trả, gồm phí/chênh lệch; không tra giá thị trường), mọi xe theo giá cửa hàng mua lại (`garage.sell_price`), mọi quầy riêng theo giá sang nhượng (`quay.sell_back`: giá chỗ × 50 % + đồ lắp × 30 % + két + vốn), trừ tiền quầy còn nợ (`due`, phạt chưa nộp) và vay nóng hội chợ (`fair_cash`: khoản đang vay + nợ còn lại).
  - Mua coin/vàng không đổi tài sản ròng (xu chỉ chuyển túi); bán ra thì tài sản ròng đổi đúng bằng phần lãi/lỗ đã chốt.
  - Không tính: Quỹ chung vợ chồng (ở ngoài bản lưu, của hai người), tiền đang chuyển khoản / lương giữ trước / tiền thuê nhà trả trước (nằm trong bảng dữ liệu, không trong bản lưu). Dòng luật trên bảng nói rõ điều này.
- Chỉ người chơi theo câu chuyện; tài sản ròng ≤ 0 thì không có dòng. Bằng nhau: ai nhiều tổng tài sản hơn, rồi ai đạt mức đó trước. Ẩn tên / khách tự bật giống các bảng khác. Số trên bảng cập nhật mỗi khi bản lưu được ghi (giá nhà theo lịch đổi thì bảng theo ở lệnh kế tiếp).
- Danh hiệu tuần (top 1 / 2–3 / 4–10): 💎 Đại gia của phố, 💰 Đại gia mới nổi, 🤑 Hội nhà giàu; cập nhật hằng ngày, chốt tuần 0:00 thứ Hai như các bảng khác.
- `leaderboard.VERSION` 2 → 3: lần khởi động đầu tiên dựng lại mọi dòng ở nền (danh hiệu tuần chờ dựng xong). Không có DDL, không đổi bản lưu (bảng chỉ đọc bản lưu).
- Ghi bảng: khi các bảng của một bản lưu không đổi và bản tóm tắt trước đó được biết là khớp với bảng (`lb.synced()`: tiến trình này vừa ghi các dòng đó, hoặc lệnh trước không đổi số nào trên các dòng đã khớp; cùng revision), chỉ ghi những dòng có số thay đổi (tài phú đổi theo hầu hết lệnh có tiền: 1 câu lệnh thay vì 1 câu/bảng). Thêm hoặc mất một bảng, lệnh đầu tiên của tiến trình với bản lưu đó, hay bảng hội chợ cần tự chữa (`lb.heal`): đồng bộ đủ như cũ.
- Tab trên điện thoại (390 px): 4 tab xếp 2 × 2, có 💍 Khách mời thì 5 tab xếp 3 + 2, đủ chữ.
- Thẻ bạn bè (`game/friends.py`) chỉ lấy nghề chính từ bảng nơi làm (bảng danh hiệu, tài phú, hội chợ `fair…xu` không lọt vào).
- Hướng dẫn › Bảng xếp hạng thêm dòng Top tài phú (`public/js/tutorial/guide-content.js` tạo lại). Chưa có bản tiếng Anh cho các dòng mới.
## WP6 Quầy, hội chợ, tiền & luồng

- Quầy: camera, chuông, két sắt, bảo vệ giảm đúng khả năng bị trộm như nhãn ghi; két sắt giữ lại ít nhất nửa két. Thẻ quầy hiện "Rủi ro trộm" và chi phí mở quầy chạy trực tiếp.
- Thuê bạn: lời mời có huy hiệu trong game, lời mời chưa nhận được hiện lý do; nói rõ hàng nhập dùng quỹ nghề của người làm thêm; ghi "chỗ đứng" thay cho số người.
- "3 ngày tuổi": nói rõ tài khoản của ai, còn bao nhiêu giờ (đời thực), phiên khách có câu riêng; kết bạn từ chat báo lý do cụ thể.
- Bỏ dở việc: máy chủ kiểm tra trước rồi mới hỏi "Vẫn đi", không lặp hộp thoại; "Xin nghỉ việc" chờ một nhịp mới bấm được "Đồng ý".
- Bảng giá tiệm vẽ đủ món cho mọi nghề có bảng giá (quán cơm, phở, tạp hóa…). Kết kỳ thuế có thông báo kèm phép tính.
- Hội chợ: khoảng 65% ván may rủi là thắng (thắng liền 4 ván thì nguội còn 55%); phóng dao màn mới nhẹ hơn, tính giờ theo lúc chạm; ném vòng rơi đúng gần chỗ ném; lô tô chưa đủ hàng chỉ nhắc, không phạt.
## WP8 Điện thoại gọn + xoay ngang

- Điện thoại dọc: đầu màn hình làm việc còn một hàng (~56 px: tên, quỹ, ❔ ⋯ ✕); 16 thanh nút của các nghề dùng chung một thanh gọn (~60 px) sát đáy, có khoảng cuộn khớp.
- Thông báo trên màn làm việc nằm trong hàng tiêu đề, không còn đè nút hay thanh nút; chỉ một dòng, chạm ▾ để xem hết.
- Màn chính: bỏ "Đổi nghề" trùng (vẫn ở Thêm), thẻ việc 64 px với "Khách ghé" bên cạnh, thanh dưới 64 px: cảnh được ~70% chiều cao.
- Tab Chuẩn bị, khung bên, ô xem trước tủ đồ không còn ghim trên điện thoại; menu Thêm 3 cột, cao tối đa 60%, thanh dưới vẫn thấy; nút chạm tối thiểu 44 px.
- Xoay ngang: thanh nghề chuyển sang cột trái (kèm chat), thanh trên 44 px, thẻ việc nổi góc phải, Thêm thành ngăn kéo bên phải; màn hình làm việc tràn toàn màn, hai cột như máy tính, chừa tai thỏ và thanh home.
- Đi dạo xoay ngang: phố được vẽ to hơn và camera đi theo nhân vật; khi bàn phím mở (kb-open) đầu màn hình gọn lại, ô chat tối đa 2 dòng, chat/đi dạo chỉ còn tin nhắn và ô nhập.
- Bản đồ phố gọn hơn trên điện thoại (mục tiêu thu nhỏ, ô tìm đường một hàng, nút phóng to tránh thanh home); hội chợ xoay ngang bỏ dây cờ, bản đồ to hơn. Máy tính bảng và máy tính giữ nguyên.
## WP7 Phase-0 performance

- Lệnh nhanh hơn với bản lưu lớn: nghề chỉ đổi phần tiền/sổ thu chi do nhân viên chạy đơn thì chỉ kiểm tra lại phần đã đổi (sổ thu chi: chỉ các dòng mới); bản lưu ghi ra giữ nguyên từng byte.
- Ảnh chụp chỗ làm cho bạn bè ghé (work visits) được tính trước khi khóa bản lưu; khóa giữ ngắn hơn.
- Bản lưu đi thẳng dạng UTF-8 từ lúc đọc tới lúc ghi PostgreSQL, không giải mã/mã hóa lại 1–7 MB mỗi lệnh.
- Cưới hỏi, chuyển khoản, quỹ đôi, thuê quầy, ghé chỗ làm: chỉ kiểm tra lại các nghề bị thay đổi thay vì cả 41 nghề.
- Kiểm tra toàn bộ định kỳ mỗi 200 lệnh (VALIDATE_FULL_EVERY, trước 50); mã BUILD chỉ đổi khi mã di trú/kiểm tra bản lưu có thể đổi (lên số phiên bản, hướng dẫn, quan sát hệ thống không còn ép kiểm tra lại mọi bản lưu).
- Thêm scripts/bench_command.py đo từng pha của một lệnh trên bản lưu tổng hợp 225 KB / 1.4 MB / 3 MB.

# 1.7.15 — 2026-10-05

- Coin/vàng chung thị trường theo giờ thực: 10 phút một phiên, 1 giờ một ngày thị trường; giữ tài sản và giá vốn khi chuyển đổi.
- Tối ưu sổ giao dịch khi xử lý nhiều đơn NPC, kiểm tra lịch sử và vẽ hội chợ/buồng ảnh/cào vé.
- Quầy hiển thị khách thật và lượt mua vừa xác nhận; giữ bảng doanh thu, thông tin, vị trí cuộn khi cập nhật.
- Cược trò có phí tối đa 500 xu/lượt; phóng dao mới tăng số dao/tốc độ bia, giữ xác suất thắng và ván đang dở.
- Bổ sung đề nghị lương gấp đôi của NPC và các lựa chọn chi phí kinh doanh; giữ kiểm tra số dư và chống trừ lặp.
- Có gì mới gồm đúng bốn dòng chủ game cung cấp; không phát lại quà.

# 1.7.14 — 2026-10-05

- Quầy có trạng thái mở/đóng thật, giữ đơn đã nhận và không cộng bù khách trong thời gian đóng.
- Thị trường thay đổi lượng khách; bổ sung thuế thu nhập, phí môi trường, gói bảo vệ và vật dụng giảm rủi ro có tác dụng cụ thể.
- Rủi ro trộm/hack tăng theo bậc tài sản, thêm thiết bị phòng vệ; giữ giới hạn thiệt hại và không truy thu sự cố cá nhân offline.
- Nhân viên NPC có chuyện tăng lương, cưới, xin nghỉ; chất lượng phục vụ tạo đánh giá và lịch sử chi phí rõ ràng.
- Phát hành yên lặng: không thêm Có gì mới, không phát lại quà.

# 1.7.13 — 2026-10-05

- Giảm tải khi ghé chỗ làm và xử lý đơn nhân viên tích lũy; giữ nguyên tiền, lịch sử và bảo vệ giao dịch.
- Chat giữ danh sách tin khi nội dung không đổi; Nhà không khóa điều hướng trong lúc tải chợ thuê.
- Không thêm Có gì mới hoặc phát lại quà.

# 1.7.12 — 2026-10-05

- Thêm tình huống có lựa chọn cho chủ tiệm và Quầy riêng; camera giảm nguy cơ trộm, lịch sử lưu kết quả xử lý.
- Chủ nhà tự đặt giá cho NPC hoặc người chơi thuê; hợp đồng trả trước, gia hạn và nội thất nhà thuê riêng.
- Tin bất động sản trong game ảnh hưởng giá bán lại và giá thuê, có giai đoạn hồi phục.
- Phát hành yên lặng: giữ thông báo ba dòng đã chỉnh, không tạo Có gì mới và không phát lại quà.

# 1.7.11 — 2026-10-05

- Thêm mục Đầu tư trực tiếp trong menu, gom Mây Coin và Vàng với giá, tài sản, lãi/lỗ và giao dịch trên cùng màn hình.
- Tin thị trường trong game tạo xu hướng 2–5 ngày; khoảng 70% đợt tin có chiều tăng. Giữ nguyên tài sản và giá vốn đã lưu.
- Giữ lịch sử vàng đến 05/10; cơ chế mới áp dụng từ 06/10. Coin tiếp tục đổi giá theo ngày sống.
- Phát hành yên lặng: không thêm Có gì mới, không tặng lại quà hội chợ.

# 1.7.10 — 2026-10-05

- Tặng toàn server 300 xu hội chợ, xác nhận một lần cho mỗi bản lưu; giữ quà chờ cho người offline.
- Tăng xác suất hội chợ, giảm khi lặp một trò; giữ Ô ăn quan. Giảm 20% xác suất bị bắt tại hội chợ.
- Thêm 40% lợi nhuận đủ điều kiện, khách xếp hàng liên tục, nhân viên bán đa dạng hàng thay vì chỉ áo thun.
- Bản đồ, chỉ đường và điều khiển giao hàng rõ hơn; sửa đồng hồ đèn giao thông bị tạo lặp.
- Sửa kết nối live tự phục hồi, thưởng/lịch phi công biến thiên, bán nhẫn dư và hướng dẫn đón bé.

# v1.7.9 — giảm xử lý API và thu gọn khách ghé

- Dựng dịch vụ chỉ sao chép nghề cần dùng; bỏ tải lại bản lưu khi hỏi hộp đơn rỗng và khi xác thực API ghé tiệm.
- Dùng chung dữ liệu trước thay đổi trong transaction; dùng kết quả tính tiền nhân viên đã commit cho API trạng thái.
- Giảm hỏi đơn nền khi không có đơn đang xử lý, tạm dừng khi tab ẩn; vẫn theo dõi nhanh các đơn đang phục vụ.
- Khách ghé nằm trong bố cục, không đè nút Làm tiếp/Hoàn thành; giữ nguyên chiều rộng phiếu công việc trên điện thoại.
- Nút chat và ghé tiệm trong danh sách bạn bè cùng kích thước, nằm cùng hàng.
- Có gì mới thông báo ba mục tốc độ, khách ghé và danh sách bạn bè; chưa thiết kế lại toàn bộ màn ghé tiệm.

# v1.7.8 — tiệm tự vận hành, ghé thăm bạn và trò chuyện

- Nhân viên tự động của Quầy riêng và Sổ tiệm phục vụ liên tục, tính cả thời gian offline tới khi thiếu hàng hoặc quỹ; mở không giới hạn quầy, chọn menu và định giá từng món.
- Trang bị tăng tốc cho các nghề; ghé chỗ làm, đặt dịch vụ người chơi và đánh giá sau khi hoàn thành.
- Bạn bè mời ghé nhà hoặc ở chung lâu dài, kể cả khi chủ offline; quyền vào nhà theo lời mời đã chấp nhận.
- Trả lời từng tin nhắn; tên nhân vật cập nhật trong bạn bè, chat và phòng chung, giữ nguyên username.
- Shop thú cưng tách cá theo bể; sửa đọc bản lưu café cũ thiếu bar_pace.
- Có gì mới giới thiệu các phần trên cùng xưởng gấu bông và trải nghiệm gia đình đã phát hành ở 1.7.5–1.7.7.
- Chưa bao gồm lỗi vốn góp của chủ Quầy riêng không liên kết quỹ nghề của người chơi làm thuê; các nghề mới vẫn để đợt riêng.

# v1.7.7 — nhà dễ tìm, cử chỉ có lời đáp

- Đưa Nhà & Gia đình, Vào nhà, Mời về ở và Con chung ngay dưới nhân vật trong Hành trình; lời mời cần trả lời nằm đầu trang gia đình.
- Làm rõ điều kiện đón con của cả hai, trạng thái đang chờ, cùng chăm bé và các lối vào nhà; gom tùy chọn phụ để thao tác chính dễ thấy trên điện thoại.
- Người gửi bước tới và thực sự ôm, hôn hoặc thả tim. Người nhận chọn Đáp lại để cả hai cùng tương tác, hoặc Ngại ngùng, Giận dỗi, Để sau.
- Cử chỉ đồng bộ hai màn hình, tự khép lại khi hết hạn, di chuyển hay rời phòng; có hỗ trợ giảm chuyển động và bàn phím.

# v1.7.6 — tự tay may bạn gấu

- Xưởng handmade có gấu bông: đo vải, cắt hai mặt, may viền, nhồi bông và gắn mặt, nơ, dấu trang trí.
- Bàn thủ công có hướng dẫn trực tiếp, thao tác kéo hoặc bàn phím, làm lại từng bước và giữ bản nháp trên máy theo tài khoản.
- Gốm, vòng tay và thiệp có công đoạn tương ứng; thành phẩm giữ dấu trang trí trên kệ. Chỉ trả vật liệu khi hoàn thiện và xác nhận thanh toán.

# v1.7.5 — cùng ở trong nhà

- Người sống chung thấy nhân vật của nhau trong cùng phòng, cùng di chuyển và gửi ôm, hôn, thả tim.
- Nội thất, màu tường/sàn và phần sửa sang hiển thị thống nhất; thay đổi trang trí cập nhật sang người kia.
- Giữ đồ mua riêng của từng người; đổi tường/sàn lưu cùng thanh toán, không trừ lặp. Rời nhà, đổi phòng, nối lại mạng và nhiều tab được đồng bộ.

# v1.7.4 — thông báo cập nhật trong game

- Bổ sung bảng “Có gì mới” cho đợt sửa vừa phát hành: con chung, ở chung, nội thất, chuyển khoản/quỹ chung, chat và thao tác nghề.
- Người chơi quay lại thấy thông báo một lần vào lúc nghỉ phù hợp; có thể mở lại trong Cài đặt → Cách chơi → Có gì mới. Có bản tiếng Anh.
- Các nghề mới vẫn ở đợt sau.

# v1.7.3 — sửa phản hồi, gia đình và PostgreSQL

- Admin có danh sách người chơi, tìm theo tên hoặc username; chat riêng giữ đủ tin mới khi mở phòng, tải lịch sử và nối lại mạng.
- PostgreSQL là cơ sở dữ liệu duy nhất cho game, live và công cụ vận hành; bỏ nhánh SQLite và công cụ chuyển đổi cũ.
- Vợ chồng có con chung, cùng chăm bé và gửi lời mời về ở chung; bảo toàn nhà riêng, tiền cọc và dữ liệu con khi thay đổi quan hệ.
- Bỏ giới hạn tổng 60 món nội thất; thêm hướng trước/sau cho TV và sofa, dùng đồ trong nhà chung và cập nhật bạn cùng nhà.
- Bỏ hạn mức ngày của chuyển khoản và rút quỹ chung; vẫn kiểm tra số dư, người nhận và chống xử lý lặp.
- Cà phê có tốc độ máy 1×/2×/4×; nhập áo chọn đúng size; làm rõ lương, nhân viên quầy, đánh giá cần trả lời và chỉ số tình làng nghĩa xóm.
- Bổ sung hoạt động gặp NPC trong phố; cải thiện đổi nghề, hướng dẫn, thao tác bảng trên điện thoại và điều khiển tự lái giao hàng.
- Các nghề mới theo đề xuất được tách sang đợt sau.

# v1.7.2 — công an thu hồi tiền bị hack

- Sau khi xử lý sự cố, công an có 30% cơ hội bắt được kẻ hack; kết quả sau 2 ngày sống. Bắt được thì hoàn đủ khoản mất vào tài khoản ngân hàng và ghi lịch sử.
- Hồ sơ riêng không đè việc thu hồi tiền mặt; giữ kết quả qua tải lại, không hoàn lặp. Bổ sung trạng thái đang chờ, hướng dẫn và EN.

# v1.7.1 — rủi ro hack ngân hàng

- Thêm cảnh báo đăng nhập lạ trước 1–2 ngày sống; đổi mã và khóa phiên lạ miễn phí để chặn sự cố.
- Nếu bỏ qua, mất 8% tài khoản thanh toán, tối đa 3.000 xu và chịu giới hạn rủi ro chung. Ghi lịch sử ngân hàng/rủi ro, không trừ lặp khi tải lại; không trừ ví, tiết kiệm, thẻ hay quỹ chung.
- Hướng dẫn VI/EN nêu rõ nguồn tiền bị mất, cách phòng và bảo hiểm không bồi thường hack. Không phát sinh khi offline.

# v1.7.0 — phản hồi người chơi và đời sống trong phố

- Homestay kiểm tra cả lịch đặt, giữ phòng điện thoại và OTA trước khi nhận cọc; giao ngày trả/nhận phòng đúng theo đêm lưu trú.
- Đánh giá có lời đe dọa tống tiền có thể lưu bằng chứng và báo công an trong game; không tự đổi sao hoặc trừ xu.
- Quỹ chung tăng giới hạn chi/rút lên 1.000 xu mỗi người trong 24 giờ; bổ sung hướng dẫn trả bằng quỹ chung và cách tính lời quầy.
- Thanh toán mua sắm cá nhân trực tiếp từ tài khoản ngân hàng; thiếu số dư sẽ dừng nếu chọn cách này. Giữ nguyên các lựa chọn ví, thẻ và quỹ chung.
- Cà phê có nhịp máy 1×/2×; Hộ chiếu chỉ rõ tiến độ và cách nhận huy hiệu Hẹn ở ngày hội.
- Ba kiểu tóc búi, ba mẫu đầm mới, hiển thị đồng nhất trên nhân vật và ảnh đại diện.
- Thuê người chơi ở quầy hiển thị cả bạn mới, mời riêng ngay sau khi kết bạn; bỏ giới hạn giao diện chỉ hiện 8 bạn.
- Không giới hạn số quầy, phân trang 12 quầy. Sổ quầy ghi chi phí ngày bán, thuế xu chung toàn chuỗi, trộm/cướp, kiểm tra vệ sinh/chứng từ và đòi bảo kê; kiểm tra đạt không phạt, có cách phòng ngừa và báo công an. Không truy thu ngày cũ khi nâng cấp.
- Chọn nguồn trả cho từng giao dịch cá nhân và lương thuê người chơi; lương được giữ trước, hoàn về đúng nguồn khi hủy/hết hạn. Quỹ chung cũ đã đóng thì hoàn về ví người chi.
- Sổ shipper có hợp đồng, bậc nghề, trang bị và thưởng theo đơn thực sự giao; không nhận thưởng lặp. Tự lái giao hàng có đèn giao thông và phạt vượt đèn đỏ.
- Hướng dẫn tự lái máy bay theo từng giai đoạn, có thể mở lại; thẻ nghề chỉ rõ tiến độ thăng chức và phần quản lý.
- Góc gia đình: tự chọn nhận nuôi em bé, mèo hoặc cún, đặt tên, chăm sóc theo ngày sống, tiến trình trưởng thành và đồ mặc cho bé. Lưu riêng theo nhân vật, không tự phát sinh phí khi offline.
- Đi làm tóc, làm nail với vai trò khách và tự làm đồ DIY, xem mẫu/giá trước khi xác nhận.
- Kết bạn từ tin nhắn chat, mời bạn vào buồng chụp qua tin nhắn riêng; nhập mã hỗ trợ bộ gõ đang ghép chữ. Kiểm tra quyền xem tin và chặn hai chiều.
- Trang trí giữ vị trí thanh phòng khi chọn phòng cuối, thêm nút cuộn phòng/cửa hàng; ghi lời báo thú cưng có chỉ dẫn chọn đúng việc đã quan sát.
- Xe và máy bay chưa sử dụng không tự gặp sự cố hỏng theo ngày; đổi màu/trưng xe không tính là chuyến đi.
- Chạm tủ quần áo hoặc giá treo trong nhà để xem và thử đồ đã sở hữu, mở Tủ đồ để mặc.
- Cập nhật hướng dẫn Việt/Anh. Bản này giữ các sửa lỗi đã phát hành ở 1.6.8.

Rollback: giữ hỗ trợ mã tóc/đầm, bank.pref=account, số quầy và sổ thu chi mới; giữ bộ xử lý hoàn lương theo nguồn cho các ca đã giữ tiền. Không chạy nguyên bản 1.6.8 trên save đã dùng tính năng mới. Xem docs/FEEDBACK_2026-10-04.md để biết kiểm tra và triển khai.

# v1.6.8 — ✈️ hộp Bỏ dở việc ở Hãng bay

- `abandon.js`/`abandon.css`: hàng nút đổi class `.ab-row` → `.ab-btns`; `careers/air_kit.css` có `.ab-row` (bảng giờ bay, lưới nền tối) nên rời Hãng bay khi làm dở thì hai nút bị bóp thành cột hẹp trên nền đen.

# v1.6.7 — 🎁 quà cả phố 100 xu, 💰 hoàn phí "Nơi làm khác"

- `system_gift.BROADCASTS`: mọi người chơi (khách, tài khoản cũ và mới) nhận 100 xu một lần khi tải game, tới 11/10 21:00; test tắt bằng MNL_BROADCAST_OFF. Không chèn hàng loạt: lúc tải, save tự có dòng `system_gifts` riêng (`all1004-<hash sid>`), rồi đi đường quà sẵn có (pending → applied → seen, có thiệp).
- `journey._refund_upkeep()` trong `upgrade()`: lần tải đầu, `stats.upkeep_paid` (tổng phí duy trì nơi vắng chủ đã trả) cộng vào ví với dòng "Hoàn phí duy trì nơi vắng chủ 💰", rồi về 0. Không thêm trường save; tải lại không hoàn lần hai.

# v1.6.6 — 🧭 giao đơn quầy: nút theo hướng bản đồ

- `quay-ride.js` `turnChoices()`: nút ở ngã tư hiện hướng trên bản đồ (⬆️ ⬇️ ⬅️ ➡️) tính từ hướng xe, vẫn gửi L/S/R như cũ (feedback #144: xe chạy ngang thì không có nút đi xuống).

# v1.6.5 — 💼 nơi làm cũ không trừ tiền nữa

- `journey.upkeep()` = 0: bỏ phí "duy trì khi vắng chủ" (4/7/11 xu mỗi ngày cho mọi nơi đã mở, chip "Nơi làm khác −X"); mở lại nơi tạm đóng miễn phí (REOPEN_FEE 0), bỏ nút Tạm đóng. Kho, nhân viên, hóa đơn nơi cũ đứng yên chờ quay lại. Không hoàn tiền quá khứ.
- Phạt bỏ dở ca ghi rõ "Phạt bỏ dở ca ở <nơi>", nguồn trả (quỹ/ví/lương) trong hộp xác nhận. Save không thêm trường mới.

# v1.6.4 — 📸 buồng chụp: 49 dáng, 14 biểu cảm, 50 sticker kéo thả

- Buồng chụp hội chợ: tab Biểu cảm riêng (14 mặt), 49 dáng; sau khi chụp mở trình trang trí dải ảnh: chạm để dán, kéo để dời, ↻ xoay/đổi cỡ, hoàn tác, lên trên, xoá; sticker lưu vào ảnh tải về. Trang trí mặc định giữ nguyên.

# v1.6.3 — 💑 vợ chồng chung xe, 🛡️ admin chuyển khoản không giới hạn

- Xe của vợ/chồng (`GET /api/garage/spouse`); live quyết ai lái trước; `back`/`fair_back` để ngồi sau; trường mới đều tùy chọn, cờ `coride` trong welcome (feedback #136).
- Chuyển khoản: tài khoản trong ADMIN_USERS chuyển ngay, không hạn mức ngày, không chờ kết bạn, không điều kiện tuổi tài khoản/ngày sống; tối đa 1.000.000 xu mỗi lần.

# v1.6.2 — 🛒 quán quá giờ đóng cửa không giữ chân, 🏡 mua nhà không tự dọn, 📖 hướng dẫn 1.6

- `game/abandon.py`: chỗ làm đã quá giờ đóng cửa thì đổi chỗ không hỏi, không phạt, việc dở giữ nguyên (feedback #140: Tạp hóa 21:30 dở ca làm "Ở lại làm nốt" kéo về mãi). Bản xem trước/kết quả thêm khóa tùy chọn `closing`.
- Nhà: mua nhà khi đang ở (nhà mình hoặc nhà chung) không tự dọn; thẻ "Nhà chung với …" và nút "💞 Về ở chung" (`jr_home_move` `to=shared`, feedback #137). Bản đồ phố: tiệm tạm đóng kéo cửa, nhãn ⏸, nút Mở lại vào làm luôn.
- Hướng dẫn: chuyển khoản (số lấy từ `bank_xfer.py`), bản đồ phố, đi xe, chụp ảnh hội chợ, tự lái/tự bay/nông trại.

# v1.6.1 — ✈️ phi công tự bay, 📸 buồng chụp một màn, 💸 chuyển khoản cần 1 ngày, 🎁 admin tặng xu

- Phi công tự bay góc nhìn thứ nhất (`public/js/careers/pilot_fly.js`), trường `flown` tùy chọn; ⏩ Bay nhanh làm đường lui.
- Buồng chụp hội chợ: xem trước dính trên cùng, tab Dáng / Khung ảnh / Phông nền / Đạo cụ cuộn bên dưới; máy tính hai cột.
- Chuyển khoản: `ACCOUNT_DAYS` 3 → 1, chữ "ngày chơi game (đời thực)".
- Admin: trang 🎁 Tặng xu (danh sách user, tặng qua `system_gifts`, cột `granted_by`, PG schema 16).
- Test: `test_live_wedding` chờ xu phút tiệc ghi xong (không đổi game).

# v1.6.0 — 🗺️ phố đi dạo, 🛵 tự lái & đi xe, 🚜 nông trại góc nhìn, 🏪 quầy v2 + bán online, 📸 photobooth đẹp, 💸 chuyển khoản bạn bè

- Màn hình chính là bản đồ phố (`public/js/v4/town-walk.js`); danh sách Hành trình vẫn còn (📋 Danh sách, Cài đặt → Màn hình chính).
- Giao hàng Tự lái góc nhìn thứ nhất (`public/js/careers/delivery_drive.js`), lệnh server giữ nguyên (`dl_plan`/`dl_ride`); ⏩ Đi nhanh làm đường lui.
- Nông trại góc nhìn thứ nhất/thứ ba, chạy xe máy giao hàng.
- Đi xe của mình trong phố, hội chợ, đi dạo (`public/js/v4/ride.js`); live: trường tùy chọn `r`/`v`, frame `ride`. Không tốn xăng.
- Quầy v2 (`game/quay.py`): tự đứng quầy, menu & giá, trang trí, hình quầy canvas, bán online, 26 tình huống; sửa lỗi bấm tự cuộn lên.
- Photobooth hội chợ: 30 dáng (9 dáng nhóm, `booth_set` thêm `all` tùy chọn), khung, nền, sticker, lọc màu, chữ & ngày trên dải ảnh.
- Chuyển khoản bạn bè (`game/bank_xfer.py`, bảng `bank_xfers`, `bank_xfer_days`, PG schema 15): hạn mức gửi 2.000/ngày, nhận 3.000/ngày, tài khoản ≥3 ngày & ≥10 ngày sống, bạn ≥60 phút; 30 ngày chưa nhận thì hoàn.
- Sửa: gợi ý câu chọn nhiều đáp án nói đúng chỗ sai (`game/procedures.py`, feedback #124); hoàn tiền/xin lỗi có thể làm khách sửa sao (`feedback.amends`); trông trẻ/giúp việc/nấu cơm hiện tiền công.

# v1.5.4 — 📸 buồng chụp hội chợ luôn mở, tự nối lại; 🧋 trà sữa không khựng; 🧑‍🏫 lớp học không đứng

- Buồng chụp hội chợ: sảnh vẽ lại theo trạng thái socket live, nối lại ngay khi mở buồng (`live.reconnect(true)`), bỏ chữ "đang nghỉ"; rớt mạng trong phòng bạn bè thì tự `booth_join` lại. `live/booth.py`: người cuối mất socket được giữ chỗ 120 giây (`GRACE_SECS`, `away`), mã phòng vẫn dùng được.
- Lớp học: câu trả lời học sinh không chờ AI (`later`, chờ tối đa 2 giây). Trà sữa: chọn nguyên liệu hiện ngay (optimistic).

# v1.5.3 — 🧮 ô số kế toán nhận số âm, phép tính, đơn vị; 💍 chờ 3 tiếng sau ly hôn

- `public/js/v4/amount-parse.js`: ô số của Học TT99, kế toán doanh nghiệp/tập đoàn, thuế-lương là ô chữ (bàn phím đầy đủ), hiểu `-`/`−`/(…), dấu nghìn, đ/k/tr/tỷ, + − × / ( ), đơn vị cuối áp cho cả phép tính; xem trước "= …". Server không đổi.
- Hôn nhân: sau ly hôn chờ `REMARRY_HOURS` = 3 tiếng (trước 3 ngày); 26 người đang chờ đã được đưa về mốc mới trên prod (sao lưu /root/remarry_backup_20261003.csv).

# v1.5.2 — 🎁 Quà hệ thống tới 100.000 xu

- `game/system_gift.py`: MAX_COINS 1000 → 100000 (chủ game tặng một người chơi 100k xu, 03/10); `scripts/grant_gift.py` đòi `--large` khi trên 1000 xu để vẫn chặn gõ nhầm.

# v1.5.1 — 🎖️ Thăng tiến & ca quản lý, 🏪 quầy riêng, 🧹🍲👶 ba nghề nội trợ, 🛡️ rủi ro & tiệm vàng, ✨ UI gọn

- Thăng tiến mọi nghề (`game/promotion.py`): 4 bậc, không giáng chức; làm thuê tăng lương 8–35%, chủ quán thêm tip khách quen; từ bậc 3 mở Ca quản lý (chia việc, kiểm việc, gỡ rối, chốt ca).
- Quầy riêng (`game/quay.py`): xe đẩy / sạp / ki-ốt, nhân viên NPC tự đặt lương, thu két; thuê người chơi khác một ca (bảng `quay_jobs`), lương là chuyển khoản giữ trước, trả một lần.
- Nghề mới: Giúp việc theo giờ (`giupviec`), Nấu cơm gia đình (`naucom`), Bảo mẫu trông trẻ (`babysitter`). Lịch x3 của các nghề cũ không đổi.
- Rủi ro đời sống (`game/rui.py`): luôn báo trước, có cách phòng, trần theo tài sản, không bao giờ nợ, người mới được miễn; bảo hiểm sức khỏe / xe / nhà, đồ an toàn. Tiệm vàng Kim Phát (`game/vang.py`).
- UI gọn: toast ≤8 chữ bấm để mở đủ, thẻ ví cuối ngày dạng chip (có chip 🔥 x3), x3 / ngân hàng / chip "Hôm nay" gấp chi tiết.

# v1.5.0 — 🍜 Bán phở, 🍚 Bán cơm, 📸 Photobooth, 🏠 vào nhà & tủ lạnh, 🧧 phong bì

- Nghề mới: Bán phở (quán phở Cây Si), Bán cơm (Cơm tấm Dì Bảy), Photobooth (Tiệm ảnh Tách Tách). Tuần x3 đang chạy giữ nguyên lịch các nghề cũ.
- Hội chợ: photobooth chụp một mình / với người lạ / với bạn bằng mã, dải ảnh có khung tải về PNG.
- Vào nhà, phòng trọ, KTX; tủ lạnh (`game/fridge.py`) cất đồ ăn.
- Đám cưới: phong bì không giới hạn, mức 500 xu từ ngày sống 3. Nút gửi tự quản trạng thái bận (không bị tap guard chung nuốt), mất phản hồi thì gửi lại cùng request id, server trả "đã gửi" thay vì "không đủ xu" cho lần gửi lại (e63e643).
- Nông trại: phân bón lá thúc. 🌅 Ngày mai trong tổng kết ngày cho các nghề; năm đợt chỉnh UI theo nghề.
- Tổng kết ngày: dòng 🔥 Thưởng ngày x3 (`summary.journey.x3`); thưởng đã trả nhưng thẻ không hiện (chủ game thử gom rác 03/10).
- Đánh giá: nhãn "Đã trả lời" chỉ khi người chơi đã trả lời; nhận xét của tổ bay (đóng ngay, `fb.own`) ghi "không cần trả lời" (Yuika, chat 03/10).

# v1.4.33 — 🌐 Cốc Cốc / trình chặn quảng cáo không còn kẹt màn hình tải

Chủ game: "game vào bằng Cốc Cốc không được… tới bước tải cuối thấy dừng luôn".

- `public/js/scenes/reads.js` chứa chuỗi `ads.js` ("re-ads.js"): luật chặn quảng cáo chung (bộ chặn có sẵn của Cốc Cốc, uBlock, AdGuard) chặn file này, cả đồ thị module của `app.js` hỏng, trang đứng ở màn hình tải (thống kê lỗi client: ~135 lần/ngày `app.js` + `reads.js`). Đổi tên `scenes/room-watch.js`; `v4/popup-gate.js` → `v4/break-gate.js` (chữ "popup").
- `tests/test_asset_names.py`: không file nào trang tải có tên mà bộ chặn quảng cáo bắt (trừ `telemetry.js`, `analytics-preferences.js`: tải sau, lỗi được bắt).
- Kiểm bằng trình duyệt với luật chặn `ads.js|popup`: 1.4.32 kẹt màn hình tải, 1.4.33 vào game.

# v1.4.32 — 🧑‍🍳 Nhân viên kiếm thêm cho tiệm

Chủ game: "cho nhân viên làm có thêm tiền thưởng khi thuê nhân viên", đổi tên nhóm menu.

- `operations.on_close`: mỗi việc nhân viên làm xong trong ca (đếm ở `attendance[day][id].jobs`) +3 xu (+4 khi tinh thần ≥80 hoặc cẩn thận ≥90), tối đa 12 việc/người/ngày, một dòng "Thu khác" mỗi ngày (ref `staff-jobs-<day>`), tính vào thu nhập/lời ngày (cả x3). Người tạm dừng/nghỉ/không ca không có.
- Sự cố nhân viên thật: cách sự cố trước ≥4 ngày tiệm và xác suất mỗi việc giảm một nửa (≈1 lần/4–5 ngày thay vì gần như mỗi ngày). Diễn tập giữ nguyên.
- Menu: nhóm "Tiền & nhà" → "Ngân hàng & nhà" (#110).

# v1.4.31 — ⏱️ Kim dừng đúng chỗ, nhân viên rõ ràng, nút Ngân hàng

Từ góp ý và tin nhắn nhóm 03/10 (Rizz, kattie #100, Cô Cả, Suzy, Cá Voi Xanh #110) và thống kê lỗi client.

- Canh mức (máy may, tắm thú, ép nắp…): `dayclock.daylight` chạy theo giờ thật (cảnh không còn vẽ lại mỗi khung hình khi bảng mở); màu/chữ thanh cập nhật mỗi khung hình; `TAP_LAG` 3 → 30 s (dung sai giữ nguyên); đồng hồ server ước lượng kiểu NTP (`server_recv`, `api.clockSample`); máy may chấm theo `sew_zone(t)` như trang vẽ, bấm trước vạch báo ngay không gửi.
- Nhân viên: người bị tạm dừng vì sự cố của mình không còn chấm công, tính lương, tăng mệt; thẻ nhân viên ghi việc hôm nay và lý do nghỉ; tổng kết ngày có dòng "Đội hôm nay" (`attendance[day][id].jobs` tùy chọn).
- Tiền của bạn: nút "🏦 Vào Ngân hàng" / "Mở tài khoản" (#110: ngân hàng nằm trong Thêm › Tiền & nhà từ 01/10).
- `/api/ai/review`, `/api/ai/feedback`: `_internal` lấy 4 giá trị từ `store.read()` (chỉ có 3) khi review đã được xử lý trước → 400 `invalid_data` (~70/giờ). Bạn quen qua hẹn hò được cấp mã PCC (`friends.ensure_codes`) nên Hủy kết bạn/Chặn/Cầu hôn chạy. Tên hồ sơ trùng đánh dấu ô tên, không gửi lặp; các từ chối hợp lệ không còn báo là lỗi client.
- Sổ tiệm: hướng dẫn khép sự cố ghi đúng tên tab "Nhân viên".

# v1.4.30 — 💞 Nhà chung thấy đồ của nhau

Phản ánh của người chơi (TrangChit, góp ý #109): "Mình trang trí nhà nhưng Minh Hưng không thấy đồ đạc trong nhà".

- Đồ đạc thuộc bản lưu của từng người, nên ở nhà chung mỗi người chỉ thấy đồ mình bày. `GET /api/deco/mate` (`game/deco_mate.py`): khi hai vợ chồng (còn kết hôn) cùng ở một nhà (một người đứng tên `own`, người kia `shared` qua cặp này, cùng id và loại nhà), trả các món người kia đã đặt, đọc bản lưu của họ một lần, không ghi gì, không thêm khóa nào vào bản lưu (1.4.28 vẫn nhận mọi bản lưu). `reno.js` vẽ chúng cùng đồ của mình (cả ảnh chụp), chỉ để xem: không chọn, không kéo, không vào túi, không tính Ấm cúng.
- Sổ tiệm (Suzy, homestay): cho nhân viên nghỉ khi họ còn sự cố đang mở giờ báo rõ các bước khép sự cố thay vì "Cần trao đổi sự cố đang mở…".

# v1.4.29 — 📒 Học kế toán: bản lưu cũ không còn bị khóa

Phản ánh của người chơi (num_cute, góp ý #108): "cứ hiện đáp án đã lưu chưa được chấm đúng… ấn vào học bằng cũng không cho vào".

- Mã phương án đúng của câu trắc nghiệm suy từ chữ của đề (`accounting_content.choice`). 1.4.27 thêm lại dấu cách nên 3 câu đổi mã (`vn_business_vouchers_practice_2` o1→o2, `vn_business_b01_practice_3` o2→o0, `vn_business_demanddeposit_exam` o1→o0). Người đã làm đúng các câu này trước 1.4.27 bị `validate` từ chối cả bản lưu → mọi thao tác báo lỗi.
- `accounting_school.LEGACY_KEYS`: đáp án đã lưu đúng theo mã cũ vẫn hợp lệ; điểm thi/chứng nhận chấm theo mã cũ vẫn khớp; thẻ bài đã giải hiện phương án đúng hiện tại; trả lời mới vẫn chấm theo mã hiện tại.
- `tests/accounting_released_keys.json`: ảnh chụp mọi mã đáp án đã phát hành; sửa chữ làm đổi mã sẽ làm test đỏ.

# v1.4.28 — 🔥 Thưởng x3 tính đủ cả ngày

Chủ game: "nghe bảo lương x3 nhưng mà chưa tăng đúng kìa".

- `engine.end_day`: tổng kết (thu, chi, lời) đọc sau khi đã trả lương (`emp.on_close`) và khép ca riêng của nghề; lời = thu − chi (rút/góp vốn đã bị loại khỏi thu/chi). Trước đây lời lấy trước khi trả lương và bằng quỹ − `day_start_money`; rút quá vốn đầu ngày làm mốc kẹt ở 0 và mất phần lời. Ví dụ: vốn 320, bán 300, rút 540 → thưởng 160 thay vì 600; nghề có lương gần như không được thưởng x3. Save không đổi.

# v1.4.27 — 📚 Đề kế toán TT99 hết dính số

Người chơi (Viên Nhu trên Cả phố, góp ý #104): "phần 11 câu 2 bài ôn kế toán doanh nghiệp… số nó kì kì".

- `accounting_vn_content.py`: mất dấu cách trước chữ số trên toàn khóa TT99: số tài khoản dính số tiền ("Nguồn cũ 4416.000.000đ" = 441 6.000.000đ, "Có 33125.000.000đ" = 331 25.000.000đ, 21 chỗ, tách theo từng bài) và chữ dính số ("36tháng", "VAT10%", "xem128", "100bộ"). Đáp án, id, số câu không đổi.

# v1.4.26 — 🛒 Thu gom rác: túi dán phiếu không làm kẹt ngõ

Phản ánh của người chơi (tieuthuki): "thu gom rác bấm không được nữa".

- `garbage.js roundSteps()`: "Tới nhà sau" chờ mọi túi `loaded`; túi đã dán phiếu (sự cố chủ nhà chặn xe → "Dán phiếu", hoặc tự từ chối) không bao giờ lên xe, nên ở nhà chưa phải cuối ngõ không còn nút nào để bấm. Giờ túi `refused` tính là đã xử lý (cả ô đếm x/y trên dải nhà). Server không đổi.

# v1.4.25 — ⚡ Gửi state theo phần (delta), vẽ nền quán trà sữa một lần

Chủ game: "có gì tối ưu lại k chậm thì vẫn tiếp tục tối ưu"; góp ý #100 (chậm, lag).

- feat/state-delta (f9846f5, 46a05fe, a862c4c, 08ba757): `game/state_delta.py`; trang gửi `X-Game-Delta: 1` và `known` (hash các phần đang giữ); server chia dict/list > 2 KB thành phần (tới 6 tầng), phần trang đã có ghi `0` + `delta.refs`; không nhớ gì về trang. 409 và export luôn trả đủ. Trang cũ / server cũ: như trước. Trả lời gzip p50 ~28 KB → ~5,8 KB; parse JSON p50 84 → 11 ms (4x CPU). `api.js inflate()`, thiếu phần thì đọc `GET /api/state`. Dev `?deltacheck=1`: đóng băng state, so với `/api/state`; 0 lệch trên first_day 7 nghề, hội chợ, nhà, garage.
- Nền phòng (`boba-world.js backdrop()`): khóa cache theo những gì phòng đọc (`scenes/reads.js`), không theo `rev`; mây/đèn trà sữa vẽ chồng bằng `ambient()`. Phiên 30 lệnh: vẽ nền 189 → 10 lần, script main-thread 10,2 → 4,0 s.

# v1.4.24 — 🗡️ Phóng dao thay phi tiêu

Chủ game (03/10): "game phi tiêu đổi thành game này đi: càng ngày càng khó, chơi 1 màn xong chọn chơi tiếp hoặc dừng, chơi tiếp mà thua thì thua hết, dừng thì nhận thưởng hiện tại. Lâu lâu thì hiển thị "màn sau x2"".

- feat/fair-knife (b347631, 8171336): `game/fair_knife.py`, lệnh `fair_kn_*`, `v4/fair-knife.js`; gỡ `fair_darts.py`/`fair-darts.js`. Cược 2/5/10/20 xu, 10 màn (bia xoay nhanh dần, đảo chiều, khựng; 6–7 dao, có dao cắm sẵn), qua màn chọn Dừng/Chơi tiếp, thua mất hết; từ màn 2, 25 % màn là 🔥 x2 (không liền nhau). Thang × cược: 1.1, 1.2, 1.6, 2.1, 2.8, 3.9, 5.4, 8, 12, 19. Server giữ seed, client chỉ gửi thời điểm phóng, server chấm lại; quá 60 s là thua; lượt bỏ dở được trả như Dừng cuối ngày VN. Lời hội chợ > 2000 xu: bia khó hơn tới 3 bậc. Lưu ở `journey.fair_kn` (bộ kiểm 1.4.20 bỏ qua). Client cũ: gian phi tiêu ẩn, lệnh cũ trả "tải lại trang".

# v1.4.23 — 📚 Việc làm kế toán TT99 (x3, lễ x5), 📦 Kho & đếm nhanh, 🪟 một thẻ một lúc, 👆 nút chính chỉ chỗ

Chủ game (03/10): "coi code kế toán thông tư 99, làm xong giới thiệu việc làm ở đâu nữa nhé, với check kiến thức này kia, bắt học thi qua mới làm được nhé, và ở đó kế toán lương x3 bình thường, đôi khi lễ tăng lên x5"; gói UI/UX WP-2/3/4 (tham khảo bộ nghiên cứu, giữ thiết kế hiện tại).

- 📚 feat/acct-jobs (4f6141e, ce27e21, ce1eaca): `game/accounting_jobs.py`. Hành trình: Mây Tre Xanh cần chứng nhận Kế toán cơ bản, Sông Hồng Group cần Kế toán DN Việt Nam (TT99); máy chủ chặn `need_cert`, thẻ 🔒 + "Đi học". Người đã làm/đã nộp hồ sơ giữ quyền cũ (x1, không kiểm tra). Kiểm tra đầu ca 3 câu từ ngân hàng đề (đúng 2/3), đề theo seed, không lưu gì. Lương x3, ngày lễ VN x5 (1/1, Tết, Giỗ Tổ, 30/4, 1/5, 2/9 + ngày liền kề; bảng 2026–2028), trần 600 xu/ngày, chỉ nhân dòng lương; x3_week cộng riêng. Giới thiệu việc làm trong tab Thi & chứng nhận. Không thêm khóa save.
- 📦 feat/ui-wp3 (ef9b569…e55eede): hóa đơn ngay dưới số lượng, nhà cung cấp dạng chip, giữ để đếm (~7 món/giây, D4, góp ý #97), Chuẩn bị trà sữa mở Kho trước, tổng kết ngày mở đầu "🌅 Ngày mai". `public/css/stock.css` mới.
- 🪟 feat/ui-wp2 (3ae8a17, 2dac23b, 7316f0c): `v4/popup-gate.js` một quy tắc chung (quà → Có gì mới → x3 → truyện), không mở trên tổng kết/khách đang chờ; mẹo lần đầu cạnh thanh dưới; dòng ví/quỹ nằm trong header sheet.
- 👆 feat/ui-wp4 (ee0b12f): từ khách thứ 2 nút chính dạng viền "👆 Chạm: …", cuộn tới + mũi tên ▼, không làm thay; toast một dòng ngay trên thanh dưới. D1: khách đầu giữ như cũ.

# v1.4.22 — 📱 Thanh dưới 5 nút, 🧭 Hành trình gọn, 👫 đứng tại gian ở bãi hội

Chủ game (03/10): "các bạn chơi trò gì thì bên ngoài thấy người ta đứng trò đó nhé, chứ đừng biến mất".

- 📱 feat/ui-wp1 (9b716d1, a754368, c0cafa0): thanh dưới điện thoại cố định 5 ô (Khách · bàn nghề · Kho · Sổ tiệm · Thêm), Kho mở đúng trang theo nghề, huy hiệu hàng sắp hết; HUD chip 44 px, < 360 px chỉ icon + số; Thêm không lặp lại thanh dưới; phụ đề một dòng cho Khu phố (D5: giữ tên).
- 🧭 feat/ui-wp5 (466aa94): Hành trình mở đầu bằng "Tiếp tục ở …", nơi làm việc dạng ô 2 cột trên điện thoại, nơi chưa mở cuộn ngang; Chuẩn bị chung: Kho trước, "Hôm nay · thời tiết / Nhiệm vụ" gộp một dòng gập, cấp & XP lên đầu, tab 44 px cuộn ngang.
- feat/fair-stand (be8274a, 47c71b0): client không còn gửi `fair_out` khi mở trang gian (chỉ khi đóng hội chợ/hết hội); `fair_mv`/`fair_in` thêm trường tùy chọn `s` (gian đang chơi, chữ thường ngắn; sai thì bỏ qua), gửi cho người khác trong `in`/`mv` và snapshot. Người chơi đứng ở điểm đứng của gian, bong bóng emoji trò (xe ăn vặt 🍡/🥤; vay nóng không có bong bóng). Live cũ: vẫn đứng, không bong bóng; client cũ bỏ qua `s`.

# v1.4.21 — ⏱️ Bấm dừng chấm đúng lúc chạm (#100)

Góp ý #100: bấm dừng bị trễ, thanh chạy quá chỗ đã bấm.

- feat/tap-lag (cefe0c0…e27f67a): client gửi `tap_at` (thời điểm chạm) kèm lệnh dừng; server `kit.tap_now(p)` chấm theo đó, kẹp trong [lúc tới − 3 s, lúc tới + 0,25 s], sai kiểu thì dùng giờ tới. Áp dụng: tea_seal, pc_rinse/pc_dry, cb_stop/cb_milk_stop/cb_unload, ao_sew_stop, hs_plate/hs_clean, rs_drain, sl_rinse. Thanh chạy bằng Web Animations (translateX), đóng băng ngay lúc pointerdown. Client cũ/server cũ: chấm lúc tới như trước.

# v1.4.20 — 🔥 Nghề x3 trong tuần, 🎟️ vé số cào, 🏮 35 món nhà, 💬 xóa tin nhắn & bỏ chặn, góp ý người chơi

Chủ game (03/10): "mỗi ngày x3 cho … trò bất kì", "làm liên tiếp, đầu tuần thông báo và tự áp dụng, mấy trò mà chia ra 1 tuần là đủ tất cả trò", "thêm trò cào xổ số… cào bằng tay thật", "thêm phụ kiện ở nhà", "bạn bè cho chọn xóa tin nhắn", "thông báo lâu quá, người ta có thể bấm tắt được"; góp ý #93–#99.

- 🔥 Nghề x3 trong tuần (`game/x3_week.py`): mỗi tuần (thứ Hai → Chủ nhật, giờ VN) chia 35 nghề cho 7 ngày (5 nghề/ngày, seed theo ngày thứ Hai); khép ca đúng ngày của nghề → thưởng thêm 2 × tiền lời ròng của ngày (net của ca, gồm lương; ≥ 0, tối đa 3000) vào ví, dòng Sổ ví "🔥 Thưởng ngày x3" (kind salary). Không lưu gì trong save; `public_state.x3 {x, week, days, day, today}`; `v4/x3week.js` bật lịch tuần một lần mỗi tuần, nút "Hôm nay lời x3" + chip trên thẻ nơi làm việc. `MNL_X3_OFF=1` tắt thưởng (test đặt sẵn). (Bản nháp x3 cho gian hội chợ đã gỡ: chủ game nói x3 là cho nghề.)
- 🎟️ Vé số cào (feat/fair-scratch 1263dd8): `fair_xs {price}`, vé 2/5/10/20 xu, thắng ~42 % (sàn 39 %), ~1,03 xu trả lại mỗi xu; cào bằng tay trên canvas, 70 % là lộ. Chuỗi vé giữ ở `journey.fair_run2`.
- 🏮 Trang trí nhà (feat/home-decor2 c98de6f): 35 món mới, kệ "Trung thu & Tết", 5 bộ; `deco_content.KNOWN_1419`; máy 1.4.19 vẫn nhận save có món mới.
- 💬 Chat (feat/chat-delete 4b8809d): giữ tin → "Xóa ở phía tôi" / "Thu hồi" (24 giờ); "Chọn" xóa nhiều cuộc trò chuyện; "🚫 Đã chặn" + Bỏ chặn (#93). Bảng mới `chat_hides`, `chat_clears` (SCHEMA_VERSION 13, chỉ thêm).
- 🔔 Thông báo (#95, #96): chạm để tắt, thời gian hiện theo độ dài chữ.
- 🗂️ Bàn văn phòng (#94): cuộc gọi đổi ý về một thẻ đã xếp trả thẻ về "chưa xếp", ghi chú 📞 in trên thẻ, thẻ đó mở trước.
- 🍡 Hàng ăn vặt (chủ game 03/10: "kẹo bông, nước mía… hội chợ không mua được, sửa cho mua nhé"): bỏ chặn "no rồi" (người vừa ăn sáng đã ở FULL_CAP 90 nên xe nào cũng khóa); chỉ còn chặn khi ví thiếu, no bụng/tỉnh táo vẫn tối đa 100.
- TikTok login (fix/tiktok-login 2ae19dc, phiên khác) gộp vào 1.4.20.
- 🪨 Ô ăn quan (#99): câu "quan non" nói rõ cần đủ 5 dân, không tính theo vòng.

# v1.4.19 — 🏆 Bảng vàng theo tiền lời, 👫 thấy nhau ở bãi hội

Chủ game (03/10): "thay vì tính điểm, tính tổng tiền mọi người thắng… tiền thắng nhiều xếp top", "mọi người vào hội chợ thì cho thấy nhau… (k thông báo)".

- Bảng vàng (feat/fair-money c14b8f8): điểm = `money_of(j)` = stats won − lost + earned (không tính quà 500 xu, vay nóng, ăn vặt). Bảng mới `fair20261003xu`, chỉ người đang lời; hàng cũ theo điểm không đọc nữa, xóa dần khi người chơi ghi lại. `lb.heal()` ghi lại hàng khi tiến trình gặp save lần đầu. Bỏ điểm khỏi UI.
- Bãi hội nhiều người (feat/fair-crowd 5df2ec2): `live/fair.py` phòng tối đa 30, vị trí theo tỉ lệ sàn, giới hạn như phố, chặn được tôn trọng, không thông báo. `LIVE_FAIR` mặc định theo `LIVE_STREET`. Client `fair-crowd.js`.

# v1.4.18 — 🍡 Hàng ăn vặt hội chợ

Chủ game (03/10): "người ta mua đồ ăn, uống nước mía được nữa nhé".

- `game/fair_food.py`, lệnh `fair_snack {item}` (chỉ khi hội mở): cô Út (kẹo bông 2, bắp nướng 3, bánh tráng nướng 4 xu), chú Năm (nước mía 2, chè 3, tàu hũ 2 xu). Tác dụng theo luật Ăn thêm (`needs` full/wake), từ chối khi đã no/tỉnh hoặc ví thiếu. Một dòng Sổ ví mỗi ngày "🍡 Ăn vặt hội chợ · N món". Không lưu gì trong `journey.fair` (feat/fair-food 0a111bb).

# v1.4.17 — 🦀 Bầu cua 5 giây, chơi dồn nguội tới 25%, 🎱 lô tô 53%

Chủ game (03/10): "bầu cua dễ thắng quá, spam mãi cái đó thì giảm tỷ lệ thắng… có thể thấp hơn 30%, mỗi lần bấm đợi 5s để mở", "gánh lô tô -> 53%", "bên ngoài luôn hiện hôm nay kiếm 0 xu => lỗi".

- Bầu cua: `RUN_RULES['bc'] = (.02, .25)` (sau 10 ván liên tiếp giảm 2 điểm %/ván, sàn 25%); bát mở sau `BC_OPEN_MS` 5 s, máy chủ đòi các ván cách ≥ `BC_GAP_MS` 4,8 s (`fair_slow`).
- Lô tô (feat/fair-food ea869e7): thắng/thua bốc trước bằng `luck_p(j, f, 'lt', t)`, rồi chọn `rs` cho ván khớp kết quả; Kinh = 2,2× tiền tờ (hũ đêm 2,3×), LOTO_PRIZE 23 → 11 cho tờ cũ.
- `fair.js` strip: "Hôm nay kiếm" = tổng `today_xu` mọi gian (trước đó đọc meter ô ăn quan/ném vòng, ra 0 từ khi bỏ trần).

# v1.4.16 — 🎲 Hội chợ: 53%, phi tiêu 51%, chơi dồn thì nguội vận

Chủ game (03/10): "giảm tỷ lệ thắng… hiện tại cao quá làm mất giá xu", "bầu cua, chiếu trong, gánh lô tô -> 53%", "ném vòng -> không tính điểm", "phóng phi tiêu -> 51%", "chơi liên tục 1 game thì tỷ lệ thắng sẽ giảm dần xuống, tối thiểu 40%".

- `game/fair.py`: WIN_P .60 → .53 (taper tới .45 giữ nguyên). `luck_p()`: sau RUN_FREE=10 ván liên tiếp cùng một gian (mỗi ván cách ≤ RUN_GAP=180 s) giảm RUN_STEP=1 điểm % mỗi ván, sàn P_FLOOR=.40. Chuỗi ván ở `journey.fair_run` {g, n, at} (tùy chọn, ngoài `journey.fair`).
- `game/fair_darts.py`: P_HI/P_LO .40/.30 → .51/.45.
- Ném vòng: PT_RING3/PT_RING5 = 0 (không điểm Bảng vàng); tỉ lệ giữ nguyên. Lô tô 53% ở bản sau (feat/fair-food).

# v1.4.15 — 📚 Học kế toán TT99, 🧾 hồ sơ lương, 🛕 giọng chùa, 🛁 nhà tắm & hồ bơi

Chủ game (02–03/10): "kế toán có cái thông tư 99 đưa lên luôn", "thông tư 99 gợi ý nhiều lên", "giao diện xấu quá, làm sao dễ coi hơn" (hồ sơ lương), "cách trả lời của chùa khác các bên còn lại mới đúng", "nhà chưa có nhà tắm, biệt thự 60k cũng k có hồ bơi".

- Học kế toán (TT99): trường + công ty thực hành Mây Tre Xanh, 84 bài, thi chứng nhận, gợi ý, tra cứu tài khoản; migration lười, payload công khai nhỏ, không lộ đáp án (374d610, 6f18bc5, a958ac0, 730bc5d).
- Bàn lương: mỗi ô một thẻ, một thẻ kết quả, gợi ý sâu theo số người chơi nhập (dc39d25, 6dc6d4c, a0ffed1).
- Chùa: cảm nhận/hồi đáp/quà biếu/danh hiệu tuần bằng giọng nhà chùa, không từ buôn bán (feat/pagoda-voice).
- Nhà: phòng tắm cho mọi chỗ ở, hồ bơi cho biệt thự, 15 món đồ, thư giãn mỗi ngày (feat/home-rooms).

# v1.4.14 — 🎲 Hội chợ hên xui, phi tiêu khó hơn, xu hôm nay

Chủ game (03/10): "tỷ lệ thắng đang cao quá, chỉnh tỷ lệ thắng là 60% và hên xui", "phi tiêu thì làm sao cho người ta khó trúng hơn", "sao xu kiếm hôm nay không hiển thị ở loto, rồi điểm nữa sao không thấy tính khi win".

- Bãi hội đi dạo được (feat/fair-walk 77eee50): `public/js/scenes/fair-place.js`, `public/js/v4/fair-walk.js`; bấm gian nào thì đi tới rồi mở gian đó, "📋 Danh sách trò" là lối phụ. `fair.odds(net, hi, lo)` dùng chung cho phi tiêu.
- `game/fair.py`: WIN_P .70 → .60 (taper tới .45 ở +5000 giữ nguyên).
- `game/fair_darts.py`: P_HI/P_LO .70/.45 → .40/.30; `fair-darts.js`: tâm ngắm chạy nhanh hơn (chu kỳ ~1,7×).
- Lô tô thắng: kết quả mang `points` (thẻ Kinh hiện "+N điểm hội chợ"; trước đó máy chủ vẫn cộng điểm nhưng không báo).
- `public.fair.today_xu`: xu từng gian trong ngày đời (đọc từ dòng Sổ ví, không lưu gì mới); `fair.js` hiện "💰 Hôm nay kiếm ở …".

# v1.4.13 — 🎪 Hội chợ: dễ ăn, không giới hạn, nhanh hơn

Chủ game (03/10): "lâu dài người chơi ăn", "thắng 70% số ván", "thắng khoảng 2000 xu thì cho thua dần bớt đi", "riêng ô ăn quan vẫn giữ như hiện tại", "mỗi ngày chơi không giới hạn tiền", "không giới hạn lượt chơi", "kiếm k giới hạn, điểm và lượt chơi không giới hạn", "kinh hụt thoải mái", "đọc số nào thì bảng của người ta màu phải sáng lên", "ném vòng là 1 chai có thể có nhiều vòng", "đẩy tốc độ hội chợ lên", "bấm 1 ô rồi bỏ chọn ô đó để qua ô khác được chứ".

- Bầu cua / xóc đĩa (feat/fair-walk 4cca065): máy chủ bốc thắng/thua theo `win_p` (70% khi lãi thử vận hôm nay ≤ +2000, giảm tuyến tính còn 45% ở +5000 rồi giữ), rồi chọn xúc xắc/đồng xu khớp kết quả. Xóc đĩa 1:1, công an 2% (từ 4%), phạt stake//4 (tối thiểu 3).
- Bỏ: trần thua 150 xu/ngày, 400 lượt/ngày, 80 lượt ném vòng/ngày, trần xu kiếm ô ăn quan/ném vòng, trần điểm/ngày. Chỉ ví giới hạn (không bao giờ âm). Các bộ đếm trong save dừng ở mốc cũ để máy chủ 1.4.12 (rolling release) vẫn nhận save.
- Ném vòng: một chai ăn nhiều vòng, 3 xu mỗi vòng trúng, +8 khi đủ 5.
- Lô tô (feat/fair-loto2 eef4a92, d2fe874): kinh hụt không giới hạn (phạt 1 xu, không quá ví), số vừa gọi sáng lên trên tờ dò (không tự đánh dấu).
- Quà vào hội 500 xu (một lần mỗi save mỗi kỳ hội) và Vay nóng của Bà Sáu: 50–500 xu, lãi 20%, một khoản một lúc, trả bất cứ lúc nào; hội tàn thì `fh.settle` thu từ ví, rồi ngân hàng, phần còn lại ghi nợ (ví không bao giờ âm). Save: `journey.fair_cash` (5e6738d).
- Phóng phi tiêu (game/fair_darts.py, 26ab755): đặt 2–50 xu, 1:1, 70%→45% như trên, +1 điểm mỗi phát trúng, danh hiệu hồng tâm.
- Nhanh hơn: GAP_MS 1200 → 400, lắc bát 850 → 450 ms.
- Ô ăn quan: luật như cũ; chọn ô rồi vẫn đổi / bỏ chọn được tới khi bấm hướng rải (máy chủ vẫn chặn đi hai lần bằng ply).

# v1.4.12 — 🏮 Hội chợ: mượt, rõ, không chọn lại

- Bấm không nhảy trang: vá DOM tại chỗ thay vì dựng lại cả trang (`fair.js`). Lắc bát / rải quân nhanh hơn, nút chờ máy chủ hiện đang làm.
- Chiếu trong: không còn bấm Xóc rồi bị từ chối (hạn mức ngày < cược + phạt): khóa nút và nói rõ lý do; dải "mấy ván gần đây"; kết quả ghi bên đã chọn.
- Ô ăn quan: đã bốc quân thì không chọn lại; máy chủ không cho đi hai lần trên cùng một bàn.

# v1.4.11 — 🏮 Hội chợ: sửa nhanh

- Chủ game (03/10 00:0x): "bấm vào đặt thì tự nhiên nó scroll lên", "chơi xong 1 trận làm sao chơi lại, bầu cua". `fair.js keep()` giữ cả `scrollTop` của dialog; dưới kết quả bầu cua có "🔁 Lắc tiếp" / "Đặt lại"; hết hạn mức ngày thì ghi lý do cạnh nút.
- Đếm ngược về 0 thì client tự `api.refresh()` để mở hội chợ, không cần tải lại trang.

# v1.4.10 — 🛕 Vào chùa Gió Lành

Chủ game (02/10): "chùa là phải mở cái chùa luôn chứ", "vào đó tự bấm khấn… có trụ trì, có tụng kinh", "đi tới đâu có đấy", "chùa có nhạc chùa nữa".

- Màn "Vào chùa" (Đời thường → Đi chùa): sân chùa, chánh điện, nhà ăn; mỗi việc ở đúng chỗ. Khấn tự chọn (sức khỏe, bình an), tụng kinh tự gõ mõ 12 nhịp (+1…+4 tinh thần), Thầy Huệ Minh nói chuyện theo ngày âm lịch. Miễn phí, 4 việc/ngày (trước 3).
- Âm thanh CC0/public domain thật (Freesound, Wikimedia Commons; nguồn trong `public/music/CREDITS.md`): chuông, mõ, chuông gia trì, tiếng tụng, tiếng sáng ở sân; theo công tắc "Âm thanh", tải khi vào chùa.
- Lùi bản trong ngày: save đã khấn/tụng hoặc làm 4 việc bị 1.4.9 từ chối tới hết ngày sống đó.

# v1.4.9 — 💍 Cầu hôn lại sau 3 tiếng, 📦 sửa đơn gộp

- Chủ game (02/10): "cầu hôn bị từ chối thì 3 tiếng sau mới được cầu hôn lại" — `wedding_content.DECLINE_HOURS = 3` (thay `DECLINE_DAYS = 3`).
- Tiệm nail báo lỗi "Danh sách hàng không hợp lệ." khi bấm "Gộp N món thiếu": gợi ý gửi 20 dòng, đơn tối đa 8. Server nhận tới 40 dòng khi `fit` (phần dư báo lại như cũ); client `fitDraft` (`public/js/v4/restock.js`) soạn đơn vừa chỗ và vừa quỹ.

# v1.4.8 — 🏘️ Nhiều nhà, 🛫 bên trong nơi làm việc

Chủ game (02/10): "cho phép sở hữu nhiều bất động sản/nhà nhé"; góp ý người chơi về sân bay: "nên làm thêm phần bên trong nữa ạ" → "mấy map cụ thể thì có bên trong bên ngoài, bổ sung này kia vào đa dạng lên".

- `game/housing.py` VERSION 2: `own` là nhà đang ở, các căn khác trong `props` (để trống hoặc cho thuê, tiền thuê mỗi tháng = 5%/năm giá niêm yết). Tối đa 4 căn. Hạn mức vay 40% tính mọi khoản vay nhà. Dọn nhà 20 xu. Save v1 nâng cấp tại chỗ, không mất gì.
- Khu bên trong (`public/js/scenes/areas.js`, `interior.js`, `airport.js`, `backroom.js`): sân bay 5 khu; milk tea, cafe, quán ăn, tạp hoá, hoa, mẹ & bé, quần áo, salon, thú cưng, sửa chữa, homestay, shipper có thêm khu. Chỉ phía client, không đổi nhiệm vụ/kinh tế/save.
- Lùi bản: save có nhà v2 bị bản cũ từ chối — lùi bản phải khôi phục dữ liệu.

# v1.4.7 — 💅 Tiệm nail, 🛕 chùa, 🎱 lô tô, 🧑‍🎤 avatar chat

Chủ game (02/10): "có 1 cái làm móng hay nail đi", "thêm thầy chùa nữa, mn đi chùa được nhé", "loto thì có nhạc, có mc, có người biểu diễn…", "avatar cho mọi người chat ấy, set nhiều hơn và đa dạng hơn".

- Nghề `nail` (`game/careers/nail.py`): tiệm chị Diệp, mở ở chương 2. Gel, móng úp, đính đá, dưỡng da tay; vệ sinh dụng cụ; hoàn tiền bong gel theo số tiền khách thật sự trả.
- Nghề `pagoda` (`game/careers/pagoda.py`, `pagoda_content.py`): phụ việc chùa, phụ cấp cố định 6–10 xu, không nhận tiền khách, không bán "đồ được ban phước". Ngày ở chùa không hiện thẻ bia, thịt, thất tình.
- Đi chùa (`game/chua.py`, `public/js/v4/chua.js`): trong mục Đời sống, miễn phí, tối đa 3 việc/ngày.
- Gánh lô tô (`game/fair.py`, `public/js/v4/fair-loto.js`): MC cô Bảy Lô Tô, 118 câu thơ tự viết, nhạc CC0 `wedding-funk.mp3`. Tổng cược ≤ 50 xu/ván, trần theo ngày, Kinh sai phạt 1 xu (không quá ví).
- Ảnh đại diện chat (`game/avatar.py`, `live/faces.py`, `public/js/v4/face.js`, `avatar.js`): SCHEMA 11→12 thêm bảng `chat_faces` (chỉ CREATE TABLE IF NOT EXISTS). Mã mặt được server dựng lại từ danh sách cho phép. Deploy game server trước live.
- Lùi bản: save có `nail`/`pagoda` trong `careers` bị 1.4.6 từ chối — lùi bản phải khôi phục, không chỉ đổi code.

# v1.4.6 — 🚗 Xe, máy bay, du thuyền

Chủ game (02/10): "thêm cả cái xe, máy bay, du thuyền cho mọi người mua nhé".

- `game/garage.py` + `public/js/v4/garage.js`: 11 phương tiện, 120 xu (xe đạp) tới 90.000 xu (phản lực riêng). Trả đủ một lần (ví trước, rồi tài khoản ngân hàng), không vay, không quẹt thẻ, ví không âm; mỗi mẫu một chiếc; 11 màu sơn; biển tên chỉ chủ thấy.
- Chip xe "đang đi" trên hồ sơ, xe đậu trước nhà, trên thẻ Phố nghề. Một chuyến đi chơi mỗi ngày sống (+tinh thần, tiền xăng ghi trên nút). Bán lại 70%.
- Save cũ không đổi (`journey.garage` chỉ tạo khi mua chiếc đầu tiên). Không phí ngầm.

# v1.4.5 — 💼 Lương nghề văn phòng ổn hơn cho người mới

Chủ game duyệt (02/10): "để tiền ổn xíu cho mn chơi game này, tăng xíu nhé". Áp dụng cho Thuế & lương, Kế toán doanh nghiệp, Kế toán hợp nhất (`game/careers/office.py`: `pay`, `rookie`, `wrong_min`).

- **Tăng chung:** mỗi hồ sơ +2 xu (`RAISE`), sàn thưởng 14 xu thay vì 10 (khay chứng từ, bàn đối chiếu trước là 8). Hồ sơ sạch 32 xu; bảng lương 32 xu trước phản ứng của chị Hồng.
- **Đang thử việc** (hạng 0 của lộ trình, tới lần thăng chức đầu): mỗi lỗi trừ một nửa (2 xu, khay 2 xu), không bao giờ dưới nửa thưởng; nộp trễ −4 xu thay vì −8; trả lời sai tốn 8 phút văn phòng thay vì 15. Thăng chức rồi thì luật như cũ.
- Không đổi cách sinh hồ sơ (check_task_compat OK), không đổi dạng save. Thẻ tờ khai hiện đúng số thưởng mới (`pay`, tùy chọn).
- Hướng dẫn trong game cập nhật số mới. Sửa lỗi JS `e.target.closest is not a function` khi bấm vào nút không phải phần tử HTML.

# v1.4.4 — 💡 Bớt khó hiểu: nút ghi lý do, Hỏi nhanh, thanh toán tất cả

Theo chat người chơi và số thao tác bị từ chối trên máy chủ (stat_actions). Nguyên tắc chủ game: chỉ gợi ý, người chơi tự làm (không tự điền, không chọn sẵn, không lộ đáp án).

- **Nút ghi lý do** (server vẫn là nguồn luật; trường public mới đều tùy chọn):
  - **Trà sữa:** Ủ/đặt hàng ghi "Thiếu N xu", "Kho đầy", "Đang chờ N/N đơn"; dòng quỹ tiệm/ví; chặn bấm đúp. `boba.py` thêm `held`, `shelf_cap`, `max_orders`, `cup_cap`.
  - **Chứng chỉ:** lớp không trả được thì khóa, tự học miễn phí lên đầu; sửa lỗi chặn người trả bằng thẻ.
  - **Sớm Mai:** rót hình chỉ khi đã chiết shot và đánh sữa.
  - **Tạp hóa:** "Soạn giỏ" chỉ khi soạn được (`_pack_gate`), nếu không thì "Kệ hết …: nhập ở Kho" và nút Sang Kho.
  - **Kho (mọi nghề):** một dòng cách nhập hàng; đếm sai thùng gộp báo trước. **Giỏ đặt hàng** đủ 8 món thì nút chuyển sang xem đơn; gộp nhiều món thêm phần vừa giỏ (`cart_lines`).
  - **Mẹ & bé:** đổi món đã hợp thì chị Ly giải thích tại chỗ (`fits`); tiệm chưa mở thì khóa tư vấn quà; giá hiện khoảng cho phép.
  - **Salon:** hết hàng thì khóa gội/keratin; thẻ 🎨 Bảng màu (tra cứu chung).
  - **Trạm lắng nghe:** mỗi phương án ghi "khi nào dùng".
- **Thuế và kế toán (chỉnh nhẹ):** dòng 📐 dưới mỗi ô; ô sai được đánh dấu (`bad` trong kết quả `ca_step`/`ga_step`); văn phòng đóng cửa thì chỉ còn Khép ca; bàn kế toán khóa nút khi chưa đủ điều kiện. Lương và cách chấm không đổi.
- **❓ Hỏi nhanh:** 15 câu trong Hướng dẫn, nút ở cuối menu và Cài đặt → Cách chơi; "Đi tới" chỉ mở màn hình. Màn mở đầu: "Vào làm thôi" không còn bấm mà không có phản ứng gì khi chưa chọn Nam/Nữ.
- **🧾 Thanh toán tất cả** (`ops_pay_all`): khoản quá hạn trước, khoản quỹ không đủ thì để lại, không âm quỹ.

# v1.4.3 — 🍢 Ăn thêm, số liệu giữ mãi mãi

**🍢 Ăn thêm (góp ý của chủ game sau #72).** Trong ngày làm, người chơi chủ động mua thêm đồ ăn bất cứ lúc nào, trả bằng ví: bánh bao 3 xu (+20 no bụng), xôi mặn 5 xu (+35), tô phở 8 xu (+50), cà phê sữa đá 3 xu (+15 tỉnh táo). Không giới hạn số lần; chỉ từ chối khi đã no (≥ 90) / đã tỉnh (≥ 90) hoặc ví không đủ (không bao giờ nợ). Không cộng tinh thần, không thêm trường nào vào bản lưu (`jr_needs_snack`). Hiện trong ô việc đang làm khi no bụng < 50 hoặc tỉnh táo < 40, và luôn có trong trang Đời thường.

**📊 Số liệu người chơi giữ mãi mãi.** Không còn xoá theo hạn (`stat_active`, `stat_play`, `stat_actions`, `stat_leaves`, `stat_client_errors`, `stat_loads`…): `ADMIN_STATS_*_DAYS`, `RETENTION_*_DAYS` mặc định 0 = giữ mãi. Bản lưu bị xoá không còn kéo theo số liệu: trigger `*_gone` của SQLite bỏ, hàm `*_gone` của PostgreSQL thay bằng hàm rỗng một lần khi khởi động (chỉ khi còn DELETE), `retention.forget` không xoá. `stat_play` vẫn được cộng dồn theo ngày sau 60 ngày cho trang nhanh. Trang Quyền riêng tư ghi rõ số liệu ẩn danh được giữ lâu dài.

# v1.4.2 — 📊 Tổng quan đầu tư cho admin, sửa lỗi quán trà sữa

**📊 Admin: Tổng quan đầu tư.** Mục mới 9 tab (tổng quan, tăng trưởng, hoạt động, giữ chân, gắn bó, kinh tế, chất lượng, nguồn, hạ tầng), chọn kỳ 7/30/90 ngày/tất cả, ⓘ định nghĩa + cách tính, khoảng tin cậy 95% cho tỉ lệ, nhãn "ít dữ liệu" khi dưới 30 người; doanh thu ghi "Chưa bật". Xuất CSV và báo cáo in (không dữ liệu cá nhân, ô dưới 5 người ghi "<5"). Định nghĩa đầy đủ: `docs/ADMIN_METRICS.md`; đối chiếu trên DB: `scripts/verify_admin_metrics.sql` (chỉ đọc, 5 s). Bộ đếm mới (bắt đầu từ bản này): xu vào/ra, thiết bị/HĐH/trình duyệt/ngôn ngữ, độ trễ p50/p95/p99, 5xx, thời gian hoạt động, đỉnh online, lượt AI. DDL thêm (idempotent): `stat_counters`, `stat_kpi_daily`, `stat_players` + chỉ mục `stat_players_first`, `stat_players_last`. Sửa cách tính: save chỉ được nâng phiên bản (chưa thao tác) không còn tính là người chơi; "người chơi mới" chỉ tính ai chơi ngay trong ngày tạo; giữ 60 ngày bắt đầu (D30 tính được); lượt AI cộng mọi tiến trình qua DB; góp ý theo ngày VN; trang admin luôn hiện giờ VN; nhãn D1 và nhãn mẫu đúng; số mỗi ngày đông cứng một lần. Bảo vệ hiệu năng 30/09 giữ nguyên.

**Đo lường tùy chọn (Firebase/Google Analytics).** Chỉ bật khi đặt `SITE_URL` và cấu hình `FIREBASE_*` công khai, và chỉ sau khi người chơi đồng ý; tôn trọng Do Not Track/GPC; không gửi định danh, chữ hay save. Thêm canonical, robots.txt, sitemap.xml. Hiện chưa cấu hình trên production nên chưa thu gì.

**🧋 Quán trà sữa.** Màn Kho & đặt hàng / Bảng giá và thẻ chờ khách không còn lỗi "reading 'data'" khi phòng chưa tải xong (~40 lần/ngày từ 01/10).

# v1.4.1 — 🍚 No bụng và 😴 Tỉnh táo

**Ăn uống và giấc ngủ (hành trình, feedback #72).** Cạnh thanh Tinh thần có thêm 🍚 No bụng và 😴 Tỉnh táo (`game/needs.py`, `journey.needs`), giảm theo giờ quán (−7/giờ và −4/giờ). Bữa sáng tự động, miễn phí. Từ 11:30 có dải chọn bữa trưa một chạm trong thẻ ca (cơm hộp miễn phí, cơm bình dân 4 xu, bánh mì + cà phê 3 xu, hoặc nhịn); không chọn thì 13:30 tự ăn cơm hộp; ăn không làm chạy đồng hồ quán. Khép ca xong, màn Buổi tối (nút 🌙) cho chọn bữa tối (món miễn phí theo chỗ ở: cơm Bà Tám, mì gói KTX, tự nấu; bún riêu 4 xu, cơm tấm 9 xu, ăn cùng vợ/chồng) và giờ đi ngủ 22:00–01:00 (tỉnh táo sáng mai 100/91/82/73); nút "Như mọi khi"; quên chọn thì sáng hôm sau tự lấy lựa chọn quen, không tốn xu. Tinh thần: −1 mỗi thanh mỗi ngày khi dưới 25, +1 ăn đủ bữa, +1 ngủ trước 23:00 (hoặc +1 thư giãn khi thức khuya). Cơm nhà đã nằm trong tiền cơm nước nên không thu hai lần; món trả tiền ghi Sổ ví loại `living`, thiếu tiền thì không mua được. Lệnh `jr_needs_lunch`, `jr_needs_eve` chống bấm lặp. Chế độ không cốt truyện không có. Không DDL; 1.4.0 bỏ qua `journey.needs`.

# v1.4.0 — 🪴 Bày trí tự do kiểu Nhà Có Mèo

**Bày trí phòng tự do** (owner 02/10: "linh động hơn… thoải mái kéo thả như Nhà Có Mèo"). Giữ món đồ rồi kéo thả đi đâu cũng được trong nhà riêng, phòng trọ, gác lửng và góc giường KTX; tọa độ số nguyên nhỏ (20 đơn vị một ô), một lệnh `jr_deco_put` khi thả. Đồ chồng lên nhau, vẽ theo chiều sâu với thứ tự `z` riêng; đồ nhỏ đứng trên bàn, kệ treo, kệ bếp, gối, kệ đầu giường và đi theo (lật theo) khi dời món bên dưới. Lật, Lên, Xuống, Đổi phòng, Cất túi, Bán 50%, Hoàn tác, 🎨 Màu (bảng màu chung 1.3.3; màu vẫn ở `colors.deco[uid]`, bán đồ thì xóa màu). Tab "Tường & sàn": 22 kiểu sơn, giấy dán tường, sàn và ga giường (miễn phí hoặc 20–60 xu, mua một lần dùng mọi phòng, không cộng Ấm cúng). Nắng theo giờ, đèn sáng ban đêm, bóng đổ mềm; Mochi đi dạo, ngủ trưa, bé mèo Bơ tới khi phòng đạt 24 điểm. Thêm "Kệ gỗ treo trơn" (66 món). Server kiểm tra vùng đặt, chặn cửa ra vào/cửa sổ/cầu thang, giới hạn đồ mỗi chỗ và 60 món mỗi phòng, chống bấm lặp, `DECO_PER_MINUTE` (150). Save: khối mới `journey.decor = {v, at, sig, items, skins, owned, ops}`; `journey.deco` giữ định dạng 1.3.2 (bản lưới) nên 1.3.2 vẫn đọc được (bố cục làm tròn theo ô). Save 1.3.2 tự chuyển sang, không mất món. Sửa lỗi 1.3.2: class `dc-bar`/`dc-chip`/`dc-card`/`dc-note` trùng `dayclock.css` làm ẩn thanh Hoàn tác / Cất hết / Xong. Không DDL.

# v1.3.4 — 🎓 Giấy chứng nhận và ảnh lưu niệm

**Giấy chứng nhận & ảnh lưu niệm.** Mỗi chứng chỉ thi đạt có một Giấy chứng nhận đầy đủ do trung tâm hư cấu "Trung tâm Đào tạo Nghề Phố Có Chuyện" cấp (không quốc huy, không tên cơ quan thật): viền hoa văn, tên người chơi, ngành, điểm và xếp loại (Xuất sắc ≥90, Giỏi ≥80, Khá ≥70, Đạt), ngày sống và ngày cấp thật, số hiệu `PCC-…` tính từ dữ liệu sẵn có, chữ ký và mộc đỏ, ghi chú "không có giá trị pháp lý ngoài đời thực". Thi đạt hiện màn chúc mừng có confetti. Giấy xem được từ Trung tâm chứng chỉ và huy hiệu hồ sơ, kể cả chứng chỉ thi đạt trước bản này. Tab "📸 Ảnh lưu niệm" vẽ nhân vật theo trang phục hiện tại, đội mũ cử nhân cầm giấy trong lễ trao chứng chỉ. Tải về máy: PNG trên desktop, bảng chia sẻ trên điện thoại, nhấn giữ để lưu trên iPhone; ảnh lưu niệm lưu được vào Kỷ niệm (album nhận thêm JPEG). Save thêm trường tùy chọn `earned_on`. Không DDL.

# v1.3.3 — 🎨 Bảng màu chung

**Bảng màu chung.** Màu không còn mua riêng cho từng món: mở khóa một màu (40 xu, Vàng gold và Bạc ánh kim 60 xu, nhân viên Tiệm Áo Chỉ Mây giảm 20%) là dùng miễn phí cho mọi áo, quần, giày dép, phụ kiện và đồ nội thất, ở nhà riêng, phòng trọ, gác lửng lẫn ký túc xá. Màu gốc luôn miễn phí. Món đổi màu hiện tên "tên trơn · màu". Đồ đạc giữ màu khi cất vào túi hay dọn nhà, màu hiện cả trong ảnh polaroid. Người đi dạo cùng phố thấy đúng màu bạn mặc (`look.tint` tối đa 8 mục). Màu đã mua theo từng phụ kiện ở 1.3.1 tự chuyển vào bảng màu. Save: khóa gốc `colors = {v, have, wear, deco}` (màu đồ nội thất theo uid, không đụng khối deco/reno); `wardrobe_colors` giữ dạng 1.3.1. Quay lui về 1.3.2: áo quần và đồ nội thất hiện màu gốc, phụ kiện giữ màu. Không DDL.

# v1.3.2 — 🪴 Bày trí phòng

**🪴 Bày trí phòng.** Trang trí nhà giờ là một căn phòng thật (`game/deco.py`, SVG góc 3/4): lưới ô, tường và sàn riêng, cửa sổ đổi theo ngày/đêm. Chọn món trong Túi đồ hoặc Cửa hàng (65 món, 6 nhóm: 27 món cũ giữ giá và điểm, 38 món mới), chạm hoặc kéo để đặt; dời, lật, thu hồi về túi, bán lại 50%, hoàn tác, thu hồi tất cả; phím mũi tên/F/Delete/Esc trên máy tính. Bày trí được ở nhà riêng (mọi phòng), nhà vợ/chồng, gác Bà Tám, phòng trọ (cả gác lửng) và góc giường ký túc xá; chỗ thuê chỉ trang trí, không sửa nhà; chuyển chỗ ở thì đồ tự vào túi. Điểm Ấm cúng = số loại đồ + 9 bộ góc (+2/+3) + nâng cấp nhà (+2 mỗi cấp); nhà riêng +1 tinh thần mỗi sáng từ 10 điểm, +2 từ 24 (độ bền ≥ 50, không trễ góp), chỗ thuê tối đa +1. Mèo Mochi chấm điểm, hàng xóm thỉnh thoảng ghé khen (không thưởng). Chụp polaroid (webp) vào album nghề hoặc tải về. Save thêm `journey.deco` (bản cũ bỏ qua); khối `reno` giữ dạng 1.2.0, đồ đặt theo slot tự chuyển sang lưới; lệnh `jr_reno_*` của trang cũ vẫn chạy. Không DDL.

# v1.3.1 — 🎨 Phụ kiện đổi màu

**Màu phụ kiện (feedback #70).** Kính gọng tròn, kính râm, nón lá, mũ len, nơ cài tóc và túi đeo chéo đổi được 11 màu (Đen tuyền, Nâu gỗ, Vàng gold, Bạc ánh kim, Hồng pastel, Đỏ son, Cam đào, Xanh bạc hà, Xanh navy, Tím lavender, Trắng kem). Màu gốc miễn phí; mỗi màu khác mở khóa một lần cho từng món (20 xu, ánh kim 30 xu, nhân viên Chỉ Mây giảm 20%, trả qua `bank.pay`, một dòng sổ ví `life`), sau đó đổi qua lại miễn phí. Xem trước trên gương, gợi ý màu hợp tóc. Màu hiện ở mọi nơi có nhân vật (avatar, đi dạo, phòng cưới, ảnh Kỷ niệm, thẻ người chơi, bảng xếp hạng). Save thêm khóa gốc `wardrobe_colors` (bản cũ bỏ qua); lệnh mới `jr_wd_color`, `jr_wd_wear` nhận `tint`; khung trực tiếp mang `look.tint` đã kiểm tra (`live/street.py clean_look`): web và live phải lên/quay lui cùng nhau. Không DDL.

# v1.3.0 — 🏮 Hội chợ dân gian, 🍨 nghề bán kem, 🛏️ ký túc xá, 🔔 ting ting, 🦁 tiệc cưới sôi động

**🏮 Hội chợ dân gian (03/10–07/10, feedback #63).** Khu phố mở hội 5 ngày, chơi bằng xu trong game (`game/fair*.py`, `public/js/v4/fair.js`). Cổng hội vào từ banner Hành trình và mục Khu phố. Chơi kiếm xu, không cần cược: Ô ăn quan với Bé Bi (+15 xu) hoặc Ông Hai (+30 xu, nhìn trước 3 nước), tối đa 90 xu/ngày; Ném vòng cổ chai 2 xu mỗi chai, đủ 5 chai thêm 5 xu, tối đa 45 xu/ngày (server tạo ván và chấm). Thử vận may: Bầu cua 1–20 xu (bão ăn 10), Lô tô tờ 5 xu ăn 23, Chiếu trong 10–50 xu với 4% công an phường ghé (mất cược, phạt max(5, nửa cược), dẹp chiếu 2 phút). Thua tối đa 150 xu/ngày, 400 ván/ngày, không cho vay, chống gửi trùng. Bảng vàng (board `fair20261003`, tối đa 30 điểm/ngày); hội tàn 60 giây thì Top 1 nhận 👑 Vua trò chơi, Top 2–10 nhận 🎪 Cao thủ hội chợ (một lần, `leaderboard_meta` `fair:<edition>`). Năm danh hiệu riêng của hội. Env: `MNL_FAIR_START` (mặc định 2026-10-03), `MNL_FAIR_DAYS` (5), `FAIR_PER_MINUTE` (40). Save thêm `journey.fair` và loại Sổ ví `fair`: mọi worker phải chạy bản này trước giờ mở hội.

**🍨 Nghề bán kem: Tiệm kem Góc Phượng (chương 3).** Cô Hiền kèm ba khách đầu (cân viên kem, đậy nắp tủ, lời dặn, tiền thối; lỗi được nhắc trước khi đưa kem, không ghi điểm). Mỗi ngày nấu một mẻ theo sổ cô Hiền: kem dừa, kem bơ, kem khoai môn (cần Chứng chỉ làm kem; sandbox từ ngày 5): đong theo lon, ly, muỗng; nấu 76–88 °C (89 °C tách dầu, 96 °C khét đổ bỏ); ngâm đá dưới 10 °C; đánh kem đúng phút. Hộp đông qua đêm, hôm sau bán, viên nhà làm +1 xu, tủ tối đa 3 hộp. Chứng chỉ làm kem mới (8 ghi chú, đề 6 câu, đúng 4 đạt, 15 xu), không cộng tỷ lệ nhận việc mà mở công thức khoai môn. Đánh giá của khách thêm "Kem mịn, lạnh".

**🛏️ Ký túc xá Hẻm 7.** Chỗ ở thuê rẻ nhất: giường tầng 7 xu/ngày, cọc 20 xu, ở chung với Quân, anh Tuấn và My (10 khoảnh khắc cùng phòng). Không thêm trường save mới; `rent.kind = 'ky_tuc_xa'` (bản cũ không nhận id này, quay lui cần script).

**🔔 Chat và Góc hẹn hò (feedback #64, #66).** Nhóm chat nhận web push như tin riêng; nút 🔔/🔕 trên đầu mỗi cuộc trò chuyện: Bật / Tắt 8 giờ / Tắt (`chat_members.muted_until`, không DDL). Góc hẹn hò cho biết ai đang chờ, ai vừa ngồi và giờ đông nhất; nút "📣 Rủ mọi người" (10 phút một lần). Sửa số đếm trong danh sách chat bị vẽ lệch ra góc.

**💸 Ting ting.** Tiền về là nghe tiếng chuông CC0 (`public/audio/sfx/ting.mp3`, ghi công trong CREDITS) kèm giọng đọc số tiền của trình duyệt ("Đã nhận 50 xu", dưới 10 xu chỉ ting). Hai công tắc mới trong Cài đặt → Âm thanh. Thư mục `audio` vào VERSIONED_DIRS.

**🧾 Bàn tính lương minh bạch hơn (feedback #71).** Sau khi chuyển bảng lương, mỗi ô được tô theo kết quả (bỏ sót / đánh dấu nhầm / bắt đúng); chạm vào ô để xem giá trị đúng, cách tính từng bước và hồ sơ, quy định làm căn cứ. Thông báo trả lương và phiếu lương ghi tên ô sai. Các phiếu khác nêu ô chưa khớp mà không lộ đáp án; bước tính thuế hiện cách tính theo bậc. Thêm "Xem lại hồ sơ đã làm". Sửa lý do của lỗi "thiếu người phụ thuộc" khi có hồ sơ mới nộp đúng hạn. Cách chấm điểm không đổi.

**📅 Ô ngày giờ ở văn phòng.** Gõ bằng bàn phím số thì tự thêm "/" và ":"; nút 📅 mở lịch chọn ngày (`office_work.js`). Máy chủ vốn đã nhận các định dạng này.

**💇 Tiệm tóc (feedback #67).** Khách chê "còn dài" thì luôn cắt thêm được, kể cả sau khi tỉa tầng; lời chê được lưu qua tải lại trang; nhật ký dài không còn chặn mọi bước.

**🦁 Tiệc cưới sôi động.**
- 👰 Bảng tên cô dâu chú rể: viên thuốc vàng – hồng, chữ đậm 14px, 👰/🤵 (💍 khi chưa rõ), "Cô dâu"/"Chú rể" bên dưới; chữ màu mận đậm trên nền sáng nên đọc rõ cả giao diện sáng lẫn tối. Hai người đứng sát nhau thì hai bảng tự dạt sang hai bên, không đè lên nhau.
- 🦁 Múa lân mới (public/js/scenes/stroll.js `paintLion`, vẽ canvas 2D, không ảnh): đầu lân to nhiều màu (bờm, sừng có quả bông, tai xanh, gương trán, lông mày trắng, mắt chớp, má hồng, hàm mở/đóng có răng và lưỡi, râu), thân vải đỏ vảy vàng có tua viền, hai cặp chân bước (người múa đầu và đuôi), đuôi phe phẩy. Lắc đầu, gật theo trống, chồm lên và đớp phong bao lì xì treo trên cột rồi ngậm đi. Ba lượt lân dài hơn: 40–110 s, 280–350 s, 450–505 s của tiệc (cũ là hai lượt ngắn), xe trống đi theo. Lân dạo phố (sự kiện đường phố) dùng chung hình mới.
- 🔊 Bốn loa ở bốn góc sân rung theo nhịp (đèn LED, sóng âm). 🪩 Sân khấu: quả cầu disco lấp lánh, 6 luồng đèn màu quét từ sân khấu, đổi màu theo phách, sàn nhảy ô màu sáng theo nhịp; nháy tối đa ~2 lần/giây và chỉ trong vùng sân khấu; bật "giảm chuyển động" (hệ thống hoặc cài đặt) thì đèn đứng yên, chỉ đổi màu chậm, không pháo giấy.
- 🎶 Nhạc cưới thu sẵn thay nhạc tổng hợp (public/music/wedding-*.mp3, mono 64 kbps, tổng ~2,3 MB, tất cả CC0/phạm vi công cộng, ghi công ở public/music/CREDITS.md): "Funky House" (Of Far Different Nature), "Funky Disco Beats to Boogie/Woogie to" (Fupi), Wagner "Treulich geführt" (bản thu Musopen, CC0) lúc rước dâu, trống chiêng lân (Jor92, Freesound, CC0) khi lân múa. Vị trí bài = giây của tiệc chia lấy dư độ dài bài nên mọi khách nghe cùng chỗ, cùng nhịp với đèn (BPM cố định của từng bài); lệch quá 0,35 s thì tự chỉnh. Giữ nguyên mở khóa âm thanh, nút tắt nhạc; nhạc nền game tự nhỏ đi khi đang ở tiệc (`audio.duck`).
- 🍲 Mâm cỗ: chạm vào một bàn tiệc là mở mâm (8 món, 🍺 bia, 🥤 nước ngọt) và ngồi vào chỗ trống. Gắp món +1 tinh thần (tối đa 3 lần mỗi tiệc), bia −1 tinh thần (tối đa 2 lần) và cả phòng thấy hai ly cụng "Dzô! 🍻", nước ngọt không tính gì. Máy chủ live quyết định: khung `wed_eat {k, d}` (8 lần/10 giây), phải đang ở trong tiệc, tiệc đang mở và chưa tàn; mỗi lần trả là một dòng `live_effects` khóa cố định `weat:{tiệc}:{sid24}:{n}` / `wbeer:…` nên khởi động lại không trả hai lần (đọc lại theo khóa chính, không quét bảng). `live_effects` nay nhận tinh thần âm tới −10 (chỉ kind spirit). Bàn tiệc vẽ đầy đủ hơn: mâm xoay, gà, xôi gấc, nem, tôm, bò xào, nồi lẩu, bát cơm, đũa, ly bia từng chỗ.
- 🎧 Chú rể chọn nhạc (owner 02/10: "nhạc remix gì đó, nhiều nhạc không bản quyền rồi cho chú rể chọn nhạc"): nút 🎧 trên thanh tiêu đề mở danh sách "Chọn nhạc cho tiệc": Theo chương trình, Funky house, Disco sôi động, Quẩy EDM, Remix bay phòng 140, Electro house, House Latin, Funk nhún nhảy, Nhạc chậm cho cặp đôi. Chú rể giữ quyền chọn (nhân vật nam trong cặp); chú rể không có trong phòng thì cô dâu chọn; cặp cùng giới thì ai cũng chọn được. Máy chủ live quyết định: khung `wed_music {k}` (6 lần/20 giây mỗi kết nối, mỗi tiệc 20 giây mới đổi một lần `MUSIC_GAP`, chỉ bài trong `WL.MUSIC`, tiệc đang mở và chưa tàn), cả phòng nhận `wed_music {k, at, by, name, who}`, người vào sau nhận lựa chọn trong thông tin phòng. Mọi khách phát bài đó từ `at` (vị trí = giây hiện tại − `at`, chia lấy dư độ dài bài); nhạc rước dâu và trống lân vẫn ưu tiên rồi quay lại bài đã chọn; đèn, sàn nhảy và loa theo BPM của bài; MC nói "Chú rể đổi nhạc rồi: …! Quẩy lên nào! 🎧". Lựa chọn chỉ giữ trong bộ nhớ (khởi động lại dịch vụ live thì về "Theo chương trình").
- 🎶 Sáu bài mới cho danh sách (public/music/wedding-{edm,remix,electro,latin,funk,love}.mp3, tổng ~3,6 MB, mono 64 kbps, cắt tròn ô nhịp và nối vòng mượt; tất cả CC0 trên OpenGameArt, ghi công ở public/music/CREDITS.md và THIRD_PARTY_NOTICES.md): "Joyfully" (MintoDog, 170 BPM), "Melodic EDM Loops" (Fupi, 140 BPM), "Vengeance Electro" (Of Far Different Nature, 128 BPM), "OMW to beat the big bad" (Fupi, 120 BPM), "Funked Up" (Joth, 87 BPM), "Love Song [instrumental]" (nene, 95 BPM). Không dùng nhạc có bản quyền, không dùng bài "NCS" trên YouTube.
- 💐 Tung hoa: phút 8:45 của tiệc MC mời tung hoa; cô dâu chú rể có nút "💐 Tung hoa" (60 giây, không bấm thì tự tung). Máy chủ chọn ngẫu nhiên một khách đang có mặt có tài khoản (đứng gần sân khấu dễ trúng hơn), +20 xu một lần mỗi tiệc (`wtoss:{tiệc}`), cả phòng thấy bó hoa bay và tên người bắt được.
- 💃 Đứng trên sân khấu là nhảy theo nhịp; nút "💃 Nhảy" (cảm xúc `dance`, chỉ trong tiệc cưới) xoay một vòng cho cả phòng thấy. 🎊 Pháo giấy khi cô dâu chú rể bước vào, 🎆 pháo hoa 25 giây cuối tiệc. MC có thêm lời dẫn cho lân, mâm cỗ, sàn nhảy, tung hoa, pháo hoa.
- Không có DDL, không sửa dữ liệu người chơi. Tệp tĩnh mới public/music/wedding-*.mp3 (10 tệp, ~5,9 MB) đi theo đường /music/ sẵn có (có `?v=`, nginx `location ~ ^/(js|css|i18n|icons|music)/`, CSP `media-src 'self' blob:`), không cần đổi nginx/CSP.
- "Có gì mới": lân mới, loa và đèn sân khấu, nhạc mới và chú rể chọn nhạc, mâm cỗ, nhảy, tung hoa, pháo hoa, bảng tên cô dâu chú rể.

# v1.2.3 — Sửa lỗi tab Kế hoạch cưới

- 💍 Lỗi (stat_client_errors, 22 lần 01–02/10: `Cannot read properties of null (reading 'venue')`): cặp đã đính hôn có kế hoạch cưới đã gửi/đã chốt, mở lại tab Kế hoạch thì `planner()` đọc `S.plan` khi chưa có bản nháp nên màn Hôn nhân không vẽ được. Giờ xét trạng thái đám cưới trước, không có bản nháp thì hiện lời nhắc sang mục "Hai bạn".
- "Có gì mới": sửa lỗi tab Kế hoạch cưới.

# v1.2.2 — 😍 Thả cảm xúc trong chat; màn quản lý chat cho quản trị (tìm kiếm, xem chữ gốc)

- 😍 Cảm xúc (owner 01/10: "nhấn giữ là reaction"): nhấn giữ ~0,45 giây một tin ở Cả phố, nhắn riêng, nhóm (chạm hoặc chuột; kéo/cuộn là hủy; không bôi chữ, không hiện menu iOS) để mở thanh ❤️ 😂 😮 😢 👍 🔥. Mỗi người một cảm xúc mỗi tin: chọn lại cái đang có là bỏ, chọn cái khác là đổi. Dưới bong bóng hiện số đếm, cái của mình được tô; bấm vào một ô để thả/bỏ. Chạm (không giữ) vẫn mở hàng thao tác cũ (báo cáo, thu hồi, 📌 ghim cho quản trị).
- Máy chủ live: khung `react {id, e}` (30 lần/10 giây), chỉ thành viên của nhắn riêng/nhóm, không với tin đã ẩn/thu hồi, người đang bị khóa chat và khách không thả được; báo cho cả kênh `reacts {ch, id, r, by, e}`. Bảng `chat_reacts` (khóa (msg, pid), chỉ mục theo pid). Tin gửi theo trang (`joined`, `history`, `missed`) kèm `r` (đếm) và `my`; đếm được nhớ trong bộ nhớ (LRU 20.000 tin), đọc bằng một truy vấn gom nhóm theo id của trang. Dọn Cả phố xóa luôn cảm xúc của các tin bị dọn; xóa dữ liệu người chơi xóa cảm xúc của họ.
- 🔎 Quản trị › Chat › "Tin nhắn" (thay tab "Cả phố"): mọi kênh, 200 tin một trang, "Tải cũ hơn" theo id; lọc Cả phố / Nhắn riêng / Nhóm, theo người (bấm tên) và theo cuộc trò chuyện; ô tìm chữ, tên hoặc mã người chơi (`GET /api/admin/chat/messages`, chỉ ADMIN_USERS, mỗi lần chỉ xét tối đa 20.000 id theo khóa chính).
- Chữ gốc: từ bản này tin bị bộ lọc che (•••) lưu thêm chữ người chơi gõ ở cột chỉ quản trị đọc `chat_messages.raw` (NULL khi không bị che); màn quản trị hiện "Gốc: …". Không bao giờ gửi cho người chơi. Tin cũ chỉ còn bản đã che. Thu hồi tin hoặc xóa dữ liệu thì xóa luôn chữ gốc.
- SCHEMA_VERSION 11: `chat_reacts`, `chat_reacts_pid`, `ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS raw` (không mặc định, không ghi lại bảng). Dịch vụ live chờ bảng `chat_reacts`: khởi động game server trước.
- 🌞 Thẻ "Nhiệm vụ hôm nay" (góp ý #69): mỗi nhiệm vụ chưa xong có dòng nói cách tính (mở cửa rồi làm xong việc; tab Trò nhỏ; bấm 💬 ở công việc hoặc Người quen → Trò chuyện với 2 người khác nhau, chat Cả phố không tính) và lời nhắc đóng ca là tính lại, nhận quà trước khi đóng ca.
- "Có gì mới": thả cảm xúc trong chat; cách tính nhiệm vụ hôm nay.

# v1.2.1 — 📌 Ghim tin nhắn và tin quản trị ở Cả phố (cập nhật âm thầm)

- 📢 Tài khoản quản trị (`ADMIN_USERS`, cùng giá trị với game.env, nay cũng đặt trong live.env) nhắn ở Cả phố không qua bộ lọc, không giới hạn tần suất; tin mang huy hiệu "📢 Quản trị", liên kết bấm được (`chat_messages.adm`, hàng pid `admin` cũng tính là quản trị).
- 📌 Quản trị bấm vào một tin ở Cả phố để "Ghim tin này" / "Bỏ ghim"; thanh ghim ở đầu Cả phố cho mọi người (bảng `chat_pins`, SCHEMA_VERSION 10). `scripts/chat_pin.py --msg/--unpin/--show` ghim từ máy chủ; dịch vụ live nhận qua PG NOTIFY và đọc lại mỗi 30 giây.
- Không có mục "Có gì mới" (owner 01/10: không cần thông báo).

# v1.2.0 — Vào nhà, sửa nhà, trang trí; nghề Nội trợ; ba vị trí văn phòng

- 🏠 Trong nhà (game/reno.py, public/js/v4/reno.js): nhà đã mua có nút "Vào nhà": xem từng phòng (SVG, xuống cấp và nâng cấp hiện trong hình), sửa 5 hạng mục (tường, trần mái, sàn, điện nước, bếp; giá theo mức hư và độ rộng nhà), nâng cấp 2 bậc, trang trí 27 món (mua, dời, cất kho, bán lại 50%). Xuống cấp 1 điểm mỗi 4/6/8 ngày sống (không dưới 30%). Ấm cúng ≥10: +1 tinh thần mỗi sáng, ≥24: +2. Khối `journey.reno` chỉ tạo khi người chơi thao tác lần đầu.
- 🧹 Nghề Nội trợ (`homemaker`, nhà chị Thảo, mở chương 2): đi chợ (5 kiểu, nhớ danh sách, chọn đồ tươi, mặc cả, sổ chợ khớp từng xu), nấu ăn theo khẩu vị và dị ứng, rửa bát, giặt phơi, lau dọn, chăm bà, đưa đón trẻ, tủ lạnh, cây, sự cố, dọn Tết; truyện "Cuốn sổ chợ bìa xanh"; tiếng Anh.
- 💼 Ba vị trí văn phòng ở Công ty CP Cánh Diều (mở chương 5, phải ứng tuyển): Hành chính – Nhân sự, Thư ký giám đốc, IT văn phòng; máy chủ chấm điểm và trả lương; mỗi nghề truyện 5 đoạn, chứng chỉ "Hành chính văn phòng". Ba nghề kế toán thêm 6 tình huống.
- "Có gì mới": nhà, Nội trợ, văn phòng, tình huống kế toán.

# v1.1.4 — Đi ăn cưới tính từ 2 phút, sửa đơn sỉ bà Sáu bị treo

- Khách được tính là "đi ăn cưới" khi có mặt ít nhất 2 phút trong tiệc (`GUEST_MIN_MINUTES`, owner 01/10): 15 xu mỗi khách của cô dâu chú rể, số khách trên thẻ cuối tiệc, bảng Khách mời của tuần. Vẫn ghi `wedding_guests` ngay khi vào (lộc 20 xu/phút, phong bì không đổi). Khách thấy "✅ Đã ghi nhận bạn đi ăn cưới" sau phút thứ 2.
- Lỗi (góp ý #57): đơn sỉ tạp hóa báo giá ở mức bớt sâu nhất (hoặc lần thứ 2) luôn được trả lời dứt khoát; bản lưu đang kẹt được trả lời khi tải (`grocery.heal_save` trong `migrate_state`), tiền cọc ghi như một lần chốt thường. Sửa đồ điện: hết 6 lần báo giá thì phần khách chưa duyệt coi như từ chối, không còn kẹt ở "Trả máy".
- "Có gì mới": luật 2 phút, sửa đơn sỉ bà Sáu; dòng 1.1.3 về ghi nhận sửa cho khớp.

# v1.1.3 — Tiệc cưới 10 phút, ai vào cũng được ghi nhận, phong bì mừng cưới

- Lỗi: tiệc #14 (01/10 14:15) có 14 khách nói chuyện nhưng chỉ 4 người được ghi nhận: khách phải ở đủ 5 phút (đếm trong bộ nhớ) và bản 1.1.2 khởi động lại dịch vụ live lúc 14:20 giữa tiệc, mất hết thời gian đã ngồi; người chơi dưới 1 ngày tuổi không được tính. Nay khách được ghi vào `wedding_guests` ngay khi bước vào (cả người đứng ngoài cổng; chưa có tài khoản thì ok=0), bỏ luật 1 ngày tuổi.
- Tiệc 10 phút (mở trước 5 phút để khách tụ lại). Mỗi phút ai có mặt trong phút đó +20 xu (cả cô dâu chú rể), khách nhận tiền ở tối đa 2 đám/ngày; khóa mỗi phút cố định nên khởi động lại dịch vụ live không mất gì. Cô dâu chú rể mỗi người +15 xu mỗi khách (tối đa 360), danh hiệu "Đám cưới đông vui" ở 20 khách; thưởng trên 2.000 xu chia nhiều dòng. Bảng Khách mời của tuần: đám có mặt ít nhất 1 phút.
- "Tổ chức tiệc cưới" trong Hôn nhân: cặp đã cưới (kể cả cưới trước 1.1.0, chưa có ngày giờ) hoặc đính hôn đã chốt kế hoạch tự chọn ngày giờ tiệc (10 phút đến 14 ngày tới), miễn phí, một lần; giờ đó thành ngày cưới trên thẻ (`wedding_dates` source party). "Mời khách" miễn phí, một lần: bạn bè hai người nhận hộp thư + thông báo đẩy, cả phố nhận dòng tin. Thiệp cưới trong kế hoạch: miễn phí (các kế hoạch đã chốt giữ nguyên giá).
- Tiệc sinh động (public/js/v4/wedfeast.js, theo đồng hồ tiệc, mọi khách thấy như nhau): MC dẫn chương trình, 6 hàng xóm nói chuyện, 4 bạn nhỏ chạy quanh hát đồng dao và nói câu GenZ, 2 lượt múa lân, đèn nháy, cỗ trên bàn, bánh cưới và tháp ly, nhạc cưới tổng hợp (Wagner, Bridal Chorus, phạm vi công cộng; nhạc vui viết riêng; trống lân), nút tắt nhạc.
- 🧧 Phong bì mừng cưới (góp ý #56): khách đang dự (có tài khoản, đã ghi nhận, không phải cô dâu chú rể) chọn 10/20/50/100/200 xu và một lời chúc soạn sẵn; trừ ví khách (`marriage_effects` `wenv:<đám>:<rid>`), mỗi người trong đôi nhận một nửa (`live_effects` `wedenv:`), tối đa 500 xu mỗi khách mỗi đám, bấm hai lần không trừ hai lần. Dịch vụ live đọc lại dòng trừ tiền rồi báo cả phòng (`wed_env`); thẻ riêng cuối tiệc của cô dâu chú rể ghi tổng phong bì.
- 📜 Bảng "Lời chúc" trong tiệc cưới: lời mọi người nói và phong bì được giữ lại (3 dòng mới nhất, bấm "Xem hết" để xem 40 dòng), vì bong bóng chat biến mất nhanh và bàn phím che màn hình. Thanh trên cùng của tiệc thành 2 hàng để tên cô dâu chú rể không bị che.
- "Có gì mới": tiệc cưới mới, 20 xu/phút, ghi nhận ngay, phong bì mừng cưới, bảng lời chúc, tổ chức tiệc cho mọi cặp.

# v1.1.2 — Danh hiệu tuần của Bảng xếp hạng, đeo nhiều danh hiệu

- Bảng xếp hạng có thêm bảng 🎖️ Danh hiệu (số danh hiệu trò chơi đã có; bằng nhau thì nhiều danh hiệu bí mật hơn, rồi có sớm hơn). Bảng xếp hạng VERSION 2: lần khởi động đầu dựng lại mọi dòng (backfill nền).
- 🏅 Danh hiệu tuần (game/lb_titles.py, bảng `lb_weekly`, schema 9): top 1 / top 2–3 / top 4–10 của Trải nghiệm (Tất cả), Danh hiệu, Chứng chỉ và top 1 mỗi nơi làm ("🏆 Trùm …"). Tính lại mỗi ngày (giờ Việt Nam), chốt tuần lúc 0:00 thứ Hai (giữ mãi, không xóa). Hiện trên bảng (ai đang giữ, lần cập nhật cuối, tuần trước), cạnh tên ở Hành trình, Phố nghề và bảng tên khi Đi dạo / dự cưới. Không có xu thưởng.
- Đeo cùng lúc tối đa 3 danh hiệu và chứng chỉ (`journey.worn`); bản lưu cũ: danh hiệu đang đeo thành cái đầu tiên. Bảng tên Đi dạo: cái đầu hiện tên, các cái sau hiện biểu tượng.
- Không có "Có gì mới".

# v1.1.1 — Hotfix kế hoạch cưới

- Gửi kế hoạch cưới: lỗi từ máy chủ hiện ngay cạnh nút gửi (trước đây chỉ hiện ở đầu hộp thoại, người chơi tưởng không gửi được); chọn giờ cách chưa tới 1 tiếng thì báo trước và khóa nút gửi.
- Hai bạn cùng chọn báo tin cưới thì cả phố nhận tin "💌 A & B sẽ cưới lúc DD/MM/YYYY · HH:MM tại …" (news kind booked). Không có "Có gì mới".

# v1.1.0 — Đám cưới trực tiếp

- Đặt bàn cưới có ngày giờ thật (lưu mãi, hiện trên thẻ), Lịch cưới trong Khu phố, tiệc cưới trực tiếp 30 phút (live/wedding.py): khách có tài khoản +15 xu mỗi 5 phút (tối đa 60 xu/đám, 2 đám/ngày), cô dâu chú rể +30 xu/khách ở lại ≥5 phút, mốc 10 và 20 khách, ảnh chụp chung vào Kỷ niệm; người chưa có tài khoản xem từ ngoài cổng. Kỷ niệm 100 ngày/1 năm/500/1000 ngày cưới có quà, danh hiệu, lì xì NPC. Thi đua "Khách mời của tuần" (scripts/wedding_week.py). Schema 8. Bật bằng LIVE_WEDDING=1.
- "Có gì mới": đám cưới trực tiếp, kỷ niệm, khách mời của tuần.

# v1.0.6 — Hotfix đơn sỉ tạp hóa

- Báo giá sỉ tính theo bảng giá gốc, không theo giá kệ: tiệm tăng giá kệ (vd gạo 20 thay vì 18, trứng 4 thay vì 3) thì trước đây kể cả bớt 15% vẫn cao hơn mức khách chịu, đơn sỉ không bao giờ chốt được (góp ý #49/#52 của ShinMi). Màn báo giá ghi "giá gốc". Không có "Có gì mới".

# v1.0.5 — Lỗi lúc tải game, bấm hai lần

- Người chơi quay lại mà mã hoặc phần dữ liệu bàn làm việc của nghề tải hỏng trên mạng yếu (game vẫn mở): mở việc của khách ném "Cannot read properties of undefined (reading 'filter')" (163 lần ngày 01/10, app.js jobView rơi xuống màn chăm sóc khách hàng, supportJob). Nay hiện khung chờ và tự tải lại sau 2, 4, 8… 30 giây; mã nghề tải lại bằng URL khác (trình duyệt nhớ lần import hỏng).
- Bấm hai lần, tab khác (revision_conflict): bản đọc trạng thái cũ không ghi đè trạng thái mới hơn; bước giống hệt vừa xong ở tab này không gửi lại; xung đột lần hai không hiện lỗi, chỉ đồng bộ màn hình.
- Lỗi phía người chơi: kèm chỗ ném lỗi (file:dòng:cột của 3 khung đầu, không query), giữ tên thuộc tính trong "reading '…'"; bỏ lỗi không phải của game (zaloJSV2 của Zalo, tiện ích trình duyệt, file site khác) ở trình duyệt, máy chủ và bảng admin; "Đang tải" chỉ khi màn chờ còn hiện, sau khung hình đầu là "Vừa vào game".
- Không có "Có gì mới".
# v1.0.4 — Bớt chỗ bấm là lỗi

- Từ log 01/10: hết giờ/đủ khách thì nút thành "Làm nốt việc dở" hoặc "Khép ca" (sửa lệch 20 phút ở giờ đóng cửa); tạp hóa chưa mở ca thì nút mờ + "Mở ca"; quầy hết hàng ghi "hết hàng · nhập thêm"; thiếu nguyên liệu ghi ngay trên nút (thú cưng, tiệm bánh, homestay); "🚚 n/8 đơn đang về" và nút nhận thùng; đếm thùng chỉ ra dòng lệch; thiếu xu thì nút mờ "thiếu N xu"; trà sữa đổi món đúng ly, giá thử có khoảng cho phép; Trạm Lắng Nghe ghi tên từng bước và căn cứ; sự cố nhân viên đang mở thì dẫn tới đó.
- Sửa lỗi báo giá sỉ ở tạp hóa (góp ý #49): mức giảm cao nhất bị từ chối thì khách rời đi thay vì kẹt đơn mãi. Không có "Có gì mới".

# v1.0.3 — Góc hẹn hò

- Hẹn hò trong game (live/ DatingFeature, v4 dating): ghế đá ở mọi nơi đi dạo và mục "Góc hẹn hò" đầu nhóm Quan hệ; chọn gặp bạn nam/nữ/ai cũng được, ghép người online chưa chặn nhau và chưa hẹn trong 24 giờ; buổi hẹn 5 phút: 3 thẻ làm quen (94 câu), "chọn món cho nhau", 1 phút chat, thả ❤️ hoặc 👋 riêng tư; cùng ❤️ thành "Đang tìm hiểu 💕" và kết bạn, +5 tinh thần (tối đa 15/ngày); không ai biết ai từ chối. Chỉ tài khoản mới hẹn hò được. Bảng mới (schema 7): live_dates, date_bonds. Bật bằng LIVE_DATING=1.
- "Có gì mới": góc hẹn hò.

# v1.0.2 — Gộp đơn nhập hàng

- Kho: giỏ theo từng nhà cung cấp ("🛒 Thêm vào đơn", một lần "Đặt đơn" = một phí ship, một lần giao, một thùng), phí ship 2–5 xu và miễn ship theo ngưỡng (chủ game duyệt), giá sỉ theo số lượng, xin bớt 5/10/15% (nhà cung cấp tự quyết, mỗi ngày một lần), hết hàng một món, xe giao muộn, đơn tối thiểu; giao thiếu/khiếu nại theo cả đơn hoặc từng dòng. Tạp hóa có "🛒 +N vào đơn" ở Kho & giá. Đơn cũ đang giao giữ nguyên. Không có "Có gì mới".

# v1.0.1 — Chat ra ngoài menu

- Chat đứng đầu menu, bấm một lần là vào (không còn nằm trong nhóm Quan hệ). Không có "Có gì mới".
- Chỉ tài khoản mới được nhắn (Cả phố, bạn bè, nhóm, bong bóng khi đi dạo); khách vẫn đọc, đi dạo, vẫy tay, và có nút "Tạo tài khoản" ngay chỗ ô nhắn. Tạo xong là nhắn được ngay, không cần tải lại.
- Cả phố giữ 2.000 tin mới nhất (dịch vụ live xóa tin cũ hơn theo lô nhỏ mỗi 5 phút; tin bị báo cáo chưa xử lý được giữ tới khi duyệt). Tin bạn bè và nhóm giữ mãi.
- Mỗi lần tải 30 tin (lần đầu và mỗi "Xem cũ hơn"), mọi kênh.

# v1.0.0 — Chat

- Dịch vụ live riêng (live/, asyncio + websockets, mnl-live.service, nginx /live): chat bạn bè, nhóm (≤20), kênh Cả phố (online, 10 giây/tin, người mới 10 phút chỉ đọc), chấm online (tắt được), lọc số điện thoại/link/tục nặng (tiếng lóng GenZ được), báo cáo (3 báo cáo tự ẩn), chặn, tab Chat trong admin (ẩn tin, cấm chat 1 giờ/24 giờ/7 ngày). Bảng mới (schema 6): chat_channels, chat_members, chat_messages, chat_mutes, chat_prefs, live_effects. Bật bằng LIVE_URL=/live ở game và LIVE_CHAT=1 ở live.env. Không có hướng dẫn cho chat.
- Đi dạo khu phố (live/street.py, v4/walk.js): 4 nơi, ≤20 người mỗi khu, bong bóng, biểu cảm, bàn tám chuyện (72 chủ đề), múa lân, hàng rong, lì xì (≤30 xu/ngày, game/live_effects.py, POST /api/live/effects). Bật bằng LIVE_STREET=1.
- "Có gì mới": chat, Cả phố, chấm online, đi dạo.

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

## Dễ nhìn hơn

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
