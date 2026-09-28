# MỘT NGÀY LÀM NGHỀ

**Bộ thiết kế V1.0 · 27/09/2026**

> Tài liệu thiết kế và dữ liệu mẫu, không phải bản game đã triển khai.


---

## TÀI LIỆU THIẾT KẾ • V1.0 — MỘT NGÀY LÀM NGHỀ

Một tiệm nhỏ. Một công việc thật sự để chơi. Một khu phố biết phản hồi.

> 4 trò mở đầu đã chốt • 12 hướng mở rộng đề xuất • 96 tình huống mẫu • 24 NPC nòng cốt

### Bốn trải nghiệm mở đầu

Tiệm mẹ & bé / Nhà thuốc nhỏ / Một ngày làm kế toán / Chăm sóc khách hàng.

### Định hướng sản phẩm

Vào thẳng cảnh game, tự tay thao tác, nói chuyện có tác dụng, nhân vật có ký ức, review có căn cứ và câu chuyện tiếp tục qua nhiều ngày.

### Phạm vi tài liệu

Đặc tả trải nghiệm, nội dung, luật chơi, dữ liệu mẫu và tiêu chí nghiệm thu. Đây là bộ thiết kế để triển khai, không phải bản game hoặc mã nguồn game đã chạy.

Ngày biên soạn: 27/09/2026 • Ngôn ngữ: Tiếng Việt • Các tên nhân vật, cửa hàng, sản phẩm và tình huống mẫu đều là hư cấu.

Các con số về thời lượng, số lượng nội dung và hiệu năng trong tài liệu là mục tiêu thiết kế ban đầu; cần hiệu chỉnh bằng thử chơi, không phải kết quả đo hoặc cam kết phát hành.


---

## 01 • PHẠM VI & CÁCH ĐỌC — Một sản phẩm, nhiều nghề

### Điều đã chốt

Bốn trò mở đầu là Tiệm mẹ & bé, Nhà thuốc nhỏ, Kế toán và Chăm sóc khách hàng. Mỗi trò phải có vòng chơi hoàn chỉnh và nét riêng. Tiệm mẹ & bé được dùng làm lát cắt triển khai đầu tiên; bản mở đầu đầy đủ vẫn gồm cả bốn trò.

### Điều đang đề xuất

Danh mục 16 nghề là phạm vi của bản quy hoạch này, không phải tuyên bố phải có mọi nghề trên đời. Mười hai nghề phía sau được thiết kế hướng chơi, nhưng chưa chốt thời điểm mở hoặc ngân sách triển khai.

| Phần | Nội dung |
| --- | --- |
| Nền tảng chung | Danh mục nghề; nhịp chơi; hội thoại; sự kiện; giao diện. |
| Bốn trò mở đầu | Mỗi trò gồm cảnh chơi, thao tác, NPC, tuyến truyện, 24 sự kiện, 10 ngày đầu, nâng cấp và tiêu chí chất lượng. |
| Mười hai nghề mở rộng | Bối cảnh, vòng chơi, thao tác riêng, câu chuyện và cách phát triển. |
| Triển khai & kiểm chứng | Ranh giới AI/luật game; lưu trạng thái; cộng đồng; backlog; kiểm thử và đo trải nghiệm. |

### Năm nguyên tắc

1. Chơi trong thế giới, không quản lý qua dashboard. 2. Nói chuyện phải nối được với hành động. 3. Nhân vật chỉ nhớ sự kiện có thật trong game. 4. Sai có cơ hội sửa, không cần luôn chọn câu ngọt nhất. 5. Người chơi có thể nghỉ mà không bị phạt hay bị nhân vật gây cảm giác có lỗi.

### Không thuộc bản mở đầu

Không có tiền thật, đổi xu thành tiền, cá cược, PvP trộm đồ, livestream thật, tích hợp mạng xã hội ngoài game hoặc multiplayer thời gian thực. Hệ thống bài đăng trong game là hư cấu; cộng đồng người thật là một lớp riêng có nhãn và kiểm duyệt.

> Nghề nhà thuốc, kế toán và sửa chữa dùng dữ liệu mô phỏng. Không coi game là tư vấn y tế, tài chính, thuế hoặc hướng dẫn sửa thiết bị thật.


---

## 02 • DANH MỤC TOÀN BỘ — 16 nghề trong quy hoạch

| # | Trò / nghề | Trọng tâm | Trạng thái |
| --- | --- | --- | --- |
| 1 | Tiệm mẹ & bé | Tìm hàng, gói quà, phục vụ và chăm chút tiệm | Mở đầu |
| 2 | Nhà thuốc nhỏ | Kiểm phiếu giả lập, đối chiếu sản phẩm, số lượng, lô hàng | Mở đầu |
| 3 | Một ngày làm kế toán | Ghép chứng từ, tìm sai lệch, đối chiếu và giải thích số liệu | Mở đầu |
| 4 | Chăm sóc khách hàng | Hiểu yêu cầu, kiểm chứng, giải quyết và theo dõi lời hứa | Mở đầu |
| 5 | Quán ăn nhỏ | Nhận món, chuẩn bị, nấu theo công thức game, phục vụ | Mở sau |
| 6 | Cà phê & tiệm bánh | Pha chế, trang trí bánh, phối không gian, nhận đơn hẹn | Mở sau |
| 7 | Freelancer sáng tạo | Đọc brief, hỏi yêu cầu, làm sản phẩm nhỏ, quản lý sửa đổi | Mở sau |
| 8 | Nông trại ngoại ô | Gieo trồng, chăm sóc, thu hoạch, đóng giỏ và bán ở chợ | Mở sau |
| 9 | Chuyên viên tư vấn bán hàng | Khám phá nhu cầu, demo, so sánh, đề xuất và chăm sóc sau mua | Mở sau |
| 10 | Tạp hóa khu phố | Sắp kệ, tính tiền, giữ hàng, quản lý tồn và sổ hẹn | Mở sau |
| 11 | Tiệm thời trang | Phối đồ, tư vấn kích cỡ game, chỉnh sửa, trưng bày | Mở sau |
| 12 | Tiệm chăm sóc thú cưng | Làm quen, chải lông, chơi, vệ sinh nhẹ, bàn giao | Mở sau |
| 13 | Tiệm hoa | Hỏi dịp tặng, phối bó, viết thiệp, giữ hoa và giao hẹn | Mở sau |
| 14 | Salon tóc | Tư vấn mẫu, tạo kiểu bằng thao tác đơn giản, chăm sóc sau làm | Mở sau |
| 15 | Tiệm sửa chữa đồ dùng | Nhận đồ, kiểm tra bằng câu đố giả lập, báo phương án, sửa và thử | Mở sau |
| 16 | Homestay nhỏ | Chuẩn bị phòng, nhận khách, xử lý yêu cầu và tổ chức trải nghiệm | Mở sau |

### Màn chọn nghề

Bốn thẻ mở đầu dẫn thẳng vào cảnh chơi hoặc tiếp tục phiên cũ. Mười hai thẻ mở sau hiển thị khóa, giới thiệu ngắn và nội dung xem trước; không có nút chơi giả hoặc ngày ra mắt tự bịa.

### Một tài khoản, tiến trình riêng

Mỗi nghề có tiền, cấp, kho, nhiệm vụ và nhật ký riêng. Ngoại hình nhân vật và bộ sưu tập kỷ niệm có thể dùng chung. Bản đầu không chuyển tiền giữa nghề và không bắt cày nghề khác để mở tính năng cốt lõi.

> Các nghề tương lai không chỉ đổi hình: nấu ăn là phối hợp nhịp bếp; kế toán là câu đố chứng cứ; tư vấn bán hàng là khám phá nhu cầu; chăm sóc khách hàng là giải quyết và theo dõi vấn đề.


---

## 03 • VÒNG CHƠI CHUNG — Một ngày có đầu, giữa và kết quả

| Nhịp | Người chơi làm gì? | Phản hồi cần nhìn thấy |
| --- | --- | --- |
| Trở lại | Xem một câu nhắc việc gần nhất; chọn tiếp tục hoặc chơi tự do. | Biết ngay đang ở đâu, không bị chặn bởi chuỗi quà đăng nhập. |
| Chuẩn bị | Bố trí đồ, đọc hẹn, chọn mục tiêu, giao việc cho phụ tá. | Đồ vật, hàng đợi và nhân vật phản ứng với thay đổi. |
| Làm nghề | Thực hiện thao tác cốt lõi; gặp khách/đồng nghiệp; trao đổi và giải quyết. | Tiền, vật phẩm, chứng từ hoặc trạng thái công việc đổi đúng lúc. |
| Chuyện phát sinh | Một cơ hội hoặc vấn đề phù hợp bối cảnh xuất hiện. | Có dấu hiệu, lựa chọn và khả năng kiểm tra, không chỉ hộp thoại trừ tiền. |
| Khép ngày | Hoàn tất, hẹn lại hoặc bàn giao việc còn mở; xem kết quả. | Nhật ký giải thích vì sao có kết quả và gợi một việc tiếp theo. |

### Độ dài phiên và quyền chủ động

Mục tiêu thử nghiệm: ngày đầu khoảng 5–10 phút, về sau khoảng 8–15 phút nếu chơi trọn ca. Có thể tạm dừng bất cứ lúc nào và lưu giữa chừng. Ngày trong game không bị đồng nhất với ngày ngoài đời; chuyện chính chờ người chơi quay lại.

### Ba chế độ

Thư giãn: đọc hội thoại không tính chờ, ít sự kiện căng, có gợi ý. Đời thường: có khách vội, hiểu nhầm và sự kiện vừa phải. Thử thách: nhiều việc đồng thời, người chơi chủ động bật; không cần chế độ này để xem tuyến truyện chính.

### Không để công việc thành hình phạt

Không có năng lượng bắt chờ, mất tiền vì nghỉ đăng nhập, NPC trách móc hoặc mất chuỗi ngày chơi. Việc định kỳ chỉ là gợi ý tự chọn. Khi chậm, dùng nhận hẹn, nhờ hỗ trợ hoặc tạm ngừng nhận mới thay vì buộc xử lý vô hạn.

> Mục tiêu của một phiên: người chơi có thể kể lại ít nhất một điều đã làm thay đổi tiệm, công việc hoặc mối quan hệ; không chỉ đọc một con số tăng lên.


---

## 04 • HỘI THOẠI & KÝ ỨC — Chat là cách chơi, không phải đồ trang trí

| Lớp tương tác | Ví dụ | Tác dụng |
| --- | --- | --- |
| Tại cảnh | Hỏi ngân sách, hẹn lấy hàng, hỏi chứng từ thiếu. | Lộ thêm nhu cầu; tạo phương án hoặc yêu cầu thao tác. |
| Bình luận trong cảnh | Khách nhận ra kệ mới; đồng nghiệp thấy đã sửa lỗi. | Phản ứng theo vật thể và sự kiện có thật, giới hạn tần suất. |
| Điện thoại / bảng tin | Trả lời review, ảnh cảm ơn, đề nghị hợp tác. | Mở việc theo dõi, tuyến truyện hoặc hoạt động mới. |
| Trợ lý hệ thống | “Vì sao có ba khách bỏ về?” | Mở đúng dữ kiện và giải thích, không tự tạo sự thật. |

### Hai đường vào như nhau

Mọi tình huống cốt lõi có câu trả lời nhanh và ô tự gõ. Người không muốn chat vẫn hoàn thành toàn bộ trò. Gợi ý trả lời không tô màu “đáp án đạo đức đúng”; cho thấy hành động, chi phí và cam kết cụ thể.

### Lời nói thành hành động

“Tặng bạn một thiệp nhé” tạo đề nghị tặng thiệp. Hệ thống kiểm kho, quyền và ngữ cảnh, hiện xác nhận, rồi mới trừ kho và cho nhân vật trao thiệp. Nói “mình đã làm xong” không được tự cộng tiền hoặc đóng vụ việc.

### Ký ức có nguồn

Lưu sự kiện quan trọng: đơn đã mua, sở thích NPC đã tiết lộ, lời hẹn đã xác nhận, cách xử lý sự cố. Mỗi ký ức tham chiếu sự kiện gốc và nghề tương ứng. Phân biệt sự thật, điều người chơi tuyên bố và suy đoán của NPC; thông tin chưa kiểm chứng không được nâng thành sự thật.

### Không ép thân mật

Nhân vật có lịch, tính cách và mức quen biết, nhưng không ghen tuông, đòi đăng nhập hay thúc ép kể bí mật cá nhân. Có thể bỏ qua hội thoại, giảm độ dài, xóa lịch sử chat và xem các ký ức đang được dùng.

> Khi dịch vụ AI chậm hoặc lỗi: tiếp tục thao tác, hiện lựa chọn viết sẵn theo trạng thái. Không khóa ngày chơi và không gửi lặp hành động khi kết nối lại.


---

## 05 • SỰ KIỆN & TIẾN TRIỂN — Drama có căn cứ, không dồn người chơi

### Một sự kiện phải có đủ vòng đời

Dấu hiệu → tìm hiểu → kiểm tra bằng chứng → chọn phương án → thực hiện → hậu quả → lần gặp/bình luận tiếp theo. Không mở bằng kết luận “đây là kẻ trộm” khi nhân vật chỉ đang cầm món đồ.

| Quy tắc điều phối | Thiết kế ban đầu |
| --- | --- |
| Điều kiện | Chỉ chọn sự kiện phù hợp nghề, ngày trong game, công cụ đã mở, nhân vật có mặt và chuyện đã hoàn thành. |
| Nhịp nghỉ | Mặc định chỉ một sự kiện đáng chú ý đang cần xử lý; chờ hồi phục trước sự kiện căng tiếp theo. |
| Biến thể | Đổi khách, món, vị trí, thông tin thiếu và nguyên nhân; không chỉ thay tên của cùng một câu đố. |
| Sự thật cố định | Nguyên nhân được xác lập trước khi người chơi chọn. Không bí mật sửa đáp án để phản bác người chơi. |
| Thiệt hại | Có mức trần cấu hình; không mất vật phẩm kỷ niệm hiếm hoặc sạch tiền vì một lần ngẫu nhiên. |
| Khôi phục | Có cách hẹn lại, sửa sai, hoàn thành bổ sung hoặc nhờ hỗ trợ; không bắt trả tiền thật để thoát. |

### Tiền, kỹ năng và uy tín

Tiền mềm của từng nghề mua nâng cấp trong nghề. XP mở cơ chế mới, nhưng thao tác không bắt cày lặp vô nghĩa. Đánh giá theo nhiều mặt: chính xác, tôn trọng, đúng hẹn, chất lượng; không thưởng tốc độ nếu xử lý sai. Với kế toán/CSKH, tiền giao dịch của công ty không phải tiền cá nhân.

### Nâng cấp có hình và có tác dụng

Kệ mới tăng vị trí đặt hàng; bàn gói quà mở cách phối; khay chứng từ giúp chia vụ việc; công cụ theo dõi hẹn giúp quản lý nhiều ca. Người chơi thấy nhân vật sử dụng đồ mới, không chỉ nhận “+10%”.

### Bộ mục tiêu ba tầng

Trong phiên: giải một việc cụ thể. Qua vài ngày: tiếp tục chuyện khách quen, mở một dịch vụ. Dài hạn: xây phong cách tiệm/bàn làm việc, hoàn thành album và hoạt động cộng đồng. Không khóa toàn bộ tiến trình vì một review xấu.

> Sự kiện trộm/giật dùng bối cảnh giả lập, tập trung phát hiện và hỗ trợ; không có hướng dẫn trộm thật, truy đuổi bạo lực hoặc cho người chơi phá tiến trình của người khác.


---

## 06 • GIAO DIỆN & PHẢN HỒI — Nhìn thấy việc để làm, không ngập cửa sổ

| Khu vực | Nội dung |
| --- | --- |
| Cảnh trung tâm | Khoảng 70–80% vùng nhìn ở bố cục rộng: nhân vật, đồ vật, khách, bàn/kệ có tương tác. Tỷ lệ này là mục tiêu bố cục, không ràng buộc mọi màn hình. |
| HUD gọn | Tiền nghề, cấp, nhịp ngày và nút tạm dừng; biểu tượng phải kèm nhãn khi cần. |
| Nhiệm vụ đang làm | Một thẻ nhỏ có bước tiếp theo. Danh sách đầy đủ thu gọn, không chiếm cảnh. |
| Hội thoại | Bong bóng ngắn tại nhân vật; mở rộng khi chạm. Câu nhanh và ô nhập nằm cạnh nhau. |
| Điện thoại | Tin nhắn, review, bảng tin, hẹn và ảnh. Tin không khẩn cấp không ngắt thao tác. |
| Đồ vật là chức năng | Chạm biển để mở cửa; kệ để lấy hàng; máy tính để tra cứu; khay để nhận việc. |

### Cảm giác thao tác

Có trạng thái chỉ vào/chọn/đang làm/xong; âm thanh nhẹ, hoạt ảnh và nhãn kết quả ngắn. Đặt nhầm được trả lại hoặc hoàn tác khi chưa chốt. Nếu tay đang cầm món, cho thấy rõ món đó và vị trí có thể đặt; không dùng kéo thả mù.

### Dễ tiếp cận

Mọi thao tác kéo đều có cách bấm-chọn-bấm thay thế. Có tăng chữ, giảm chuyển động, tắt âm riêng, phụ đề, điều khiển bàn phím và trạng thái không chỉ dựa vào màu. Không bắt phản xạ nhanh để đọc truyện hoặc giải câu đố.

### Review có nguồn và có đường xử lý

NPC đánh giá sự kiện phục vụ của họ. Người thật đánh giá trải nghiệm ghé thăm được xác minh. Tách hai nhãn và hai tổng hợp; không trộn review AI vào đánh giá cộng đồng. Trả lời review có thể tạo việc bổ sung, nhưng không tự xóa lời chê hoặc tự tăng sao.

### Thử lại mà không mất mặt

Người chơi được xem nguyên nhân, chỉnh phương án và tiếp tục. Câu gợi ý mô tả bước kiểm tra tiếp theo, không chế giễu. Một NPC khó chịu không có quyền chặn mọi nội dung còn lại.

> Màn đầu tiên là chọn nghề gọn hoặc tiếp tục cảnh cũ. Không bắt đi qua trang quản trị, bảng KPI, đăng ký dài hoặc một loạt pop-up phần thưởng.


---

## MB • 1/6 • CẢNH & VÒNG CHƠI — Tiệm mẹ & bé

> Bán đúng nhu cầu, làm quà đẹp, tạo một tiệm có người nhớ tới.

### Không gian chơi

Tiệm Mây Nhỏ: quầy thu ngân, kệ đồ dùng/đồ mặc/đồ chơi, bàn gói quà, kho sau và góc cửa sổ. Ngoài cửa có điểm giao hàng, bảng tin khu phố và ghế nghỉ. Mèo tiệm là bạn đồng hành trang trí, không phải một thanh nhu cầu bắt chăm liên tục.

### Vòng chơi

Xem hẹn và kho → mở cửa → hỏi nhu cầu → chọn món → gói/kiểm → thanh toán → giao → đọc phản hồi → nhập/trang trí cho ngày sau.

| Chạm vào | Tương tác |
| --- | --- |
| Khách và giỏ | Nhận yêu cầu; hỏi thêm; xem ngân sách và lựa chọn đã xác nhận. |
| Kệ và kho | Lấy/đặt món, đọc nhãn, chuyển hàng; không tự trừ kho khi chỉ xem. |
| Bàn gói quà | Chọn hộp, giấy, nơ, thiệp; có mẫu nhanh và chế độ tự phối. |
| Quầy / máy tính | Kiểm đơn, áp dụng ưu đãi trong game, xác nhận tiền và bàn giao. |
| Điện thoại / cửa | Đặt nguồn hàng, đọc review, hẹn nhận; tạm ngừng nhận khách mới. |

### Một lượt chơi hoàn chỉnh

Khách mua quà chỉ nói “đừng màu hồng”. Bạn hỏi người nhận và ngân sách, chọn hai phương án, cho khách xem, phối giấy gói, kiểm giỏ và thu tiền. Nếu chọn quá ngân sách, khách nhắc; bạn sửa trước khi chốt. Cuối ca khách gửi ảnh, mở một lời nhờ mới thay vì chỉ nhận xu.

### Kỹ năng người chơi đang dùng

Quan sát, hỏi đúng điều còn thiếu, nhớ vị trí, phối màu, sắp xếp lượt và giữ lời hẹn. Không tư vấn sức khỏe hay lựa chọn dinh dưỡng cho trẻ ngoài phạm vi vật phẩm giả lập.


---

## MB • 2/6 • CƠ CHẾ CỐT LÕI — Sáu việc thật sự để chơi

### Khám phá nhu cầu

Yêu cầu ban đầu có thể thiếu dịp tặng, sở thích hoặc ngân sách. Câu hỏi phù hợp mở dữ kiện; khách không giấu điều thiết yếu để đánh đố vô lý. Có thể đề xuất hai món để khách chọn.

### Lấy và so hàng

Món đang cầm xuất hiện rõ; nhãn gồm mã, màu/cỡ game, giá. Kéo vào giỏ hoặc bấm-chọn-bấm. Đặt nhầm được bỏ ra trước thanh toán; lúc chốt kiểm số lượng và tồn thật.

### Gói quà sáng tạo

Ghép hộp, giấy, nơ và thiệp. Điểm phù hợp dựa trên điều khách đã nói; không có một màu luôn thắng. Tự phối tạo mẫu lưu lại; mẫu nhanh giúp người không thích trang trí vẫn chơi đủ.

### Hẹn và đơn online

Nhận đơn tạo khung giờ trong ngày game, khóa lượng hàng cần giữ. Có thể đề nghị giờ khác trước khi nhận. Việc chốt hẹn có nhắc và đường bàn giao, không chỉ nằm trong chat.

### Kho và nguồn hàng

Đặt theo khả năng bán và chỗ chứa, kiểm kiện trước khi nhập. Nhà cung cấp có thể giao thiếu theo sự kiện. Đặt hàng không được tự cộng kho; chỉ cộng lượng nhận đủ điều kiện.

### Trang trí và phụ việc

Kệ mới mở vị trí; bàn mới mở mẫu quà; phụ việc bổ sung hàng theo quy tắc. Nhân viên thực sự đi làm và có thể cần kiểm tra, không thay người chơi bằng nút auto thu tiền.

### Kinh tế và điều kiện thành công

Ví dụ cân bằng giả lập: bán bộ quà 140 xu, giá vốn 80 xu, vật liệu gói 10 xu → phần còn lại trước chi phí khác là 50 xu. Không gọi 140 xu là lợi nhuận. Hàng giữ cho đơn hẹn không được đồng thời bán cho khách khác.

### Trạng thái nghiệp vụ giả lập

requested → needs_known → reserved → picked → packed → checked → paid → delivered. Nhánh riêng: waiting_for_reply, rescheduled, cancelled, return_requested, remedied. Không bắt mọi đơn phải gói quà; bước packed có thể được bỏ qua theo loại đơn.


---

## MB • 3/6 • NHÂN VẬT & CÂU CHUYỆN — Những người sẽ quay lại

| NPC | Vai trò | Tính cách / cách tương tác |
| --- | --- | --- |
| Linh | Khách mua quà | Kỹ tính, thích màu kem; hỏi rõ trước khi mua. |
| Bác Tư | Hàng xóm | Điềm đạm, hay mua quà cho gia đình; thích được giải thích chậm. |
| Mai | Khách thường ghé | Thường vội; ưu tiên đặt trước và tới lấy nhanh. |
| An | Phụ việc | Nhiệt tình nhưng mới làm; cần nhãn và chỉ dẫn rõ. |
| Bảo | Người làm nội dung | Thích hình ảnh; có thể hợp tác tốt hoặc gây va chạm về cách quay. |
| Hạnh | Người giao nguồn hàng | Thực tế, có lịch giao và khả năng bổ sung hữu hạn. |

### Món quà của bác Tư

Gặp lần đầu và hỏi người nhận → cùng chọn quà → nhận phản hồi lần sau → chuẩn bị một món quà đặc biệt → nhận ảnh kỷ niệm. Chọn nhầm có nhánh đổi/sửa, không khóa tuyến truyện.

### Một clip, nhiều góc nhìn

Bảo đề nghị quay và xin tài trợ → người chơi đặt ranh giới/thỏa thuận → bài đăng và khách tới hỏi → trao đổi lại khi có đủ dữ kiện. Có đường hợp tác tử tế, từ chối bình thường hoặc xử lý gây rối; cộng đồng không tự bênh chủ tiệm.

### Buổi gói quà khu phố

Khách bình luận gợi ý hoạt động → bạn nhận hoặc để sau → đặt dụng cụ, bố trí bàn, mời khách → tổ chức → ảnh nhóm xuất hiện trên bảng tin. Không biến sự kiện thành kiểm tra doanh số.

> Linh: “Mình muốn tặng chị gái, khoảng 150 xu, chị không thích màu hồng.”
> Bạn: “Mình có bộ màu kem, mình lấy bạn xem nhé?”
> Hệ thống: làm nổi vị trí bộ quà, không tự hoàn thành lấy hàng.
> Linh: “Bộ này được, thêm thiệp nhỏ giúp mình.”
> Bạn chọn thiệp và xác nhận giá cuối trước khi thanh toán.

> Mọi ký ức đều liên kết một sự kiện đã diễn ra trong nghề này. Bỏ qua một câu chat không xóa nhiệm vụ; không ép gõ tự do để mở tuyến truyện.


---

## MB • 4/6 • TÌNH HUỐNG 01–12 — Chuyện đời thường • phần 1

Tình huống được mở khi đã có công cụ xử lý. Dữ kiện gốc được cố định trước khi chọn; hậu quả chỉ xảy ra sau hành động được xác nhận.

| Mã / tình huống | Người chơi làm gì? | Phản hồi / chuyện tiếp |
| --- | --- | --- |
| MB-E01<br>Quà đúng ngân sách | Hỏi người nhận, chọn bộ phù hợp và gói theo màu khách thích. | Khách gửi ảnh cảm ơn; lưu sở thích đã hỏi được. |
| MB-E02<br>Đơn thiếu một món | Đối chiếu đơn và khay đóng gói; gửi bù hoặc hoàn phần thiếu. | Chỉ cập nhật vụ việc khi hàng bù được giao hoặc tiền được hoàn. |
| MB-E03<br>Đổi cỡ đồ | Xem món còn nguyên, kiểm kho rồi đổi hoặc nhận hẹn. | Khách phản hồi dựa trên phương án thật sự được thực hiện. |
| MB-E04<br>Khách nói tiệm tính sai | Mở chi tiết hóa đơn và ưu đãi trước khi giải thích. | Tính sai thì sửa; tính đúng thì giải thích, không ép khách sửa review. |
| MB-E05<br>Hàng để nhầm kệ | Tìm trên các kệ, hỏi phụ việc, chưa vội kết luận trộm. | Tìm lại hàng và nhắc quy trình sắp xếp. |
| MB-E06<br>Lấy hàng chưa thanh toán | Kiểm bằng chứng trong cảnh; nhắc thanh toán hoặc gọi hỗ trợ. | Đồ được trả/đơn được thanh toán; không có đánh nhau. |
| MB-E07<br>Quay clip xin quà | Trao đổi đề nghị hợp tác, tặng có xác nhận hoặc từ chối. | Bài đăng sau đó phản ánh trao đổi; không bảo đảm quảng bá tích cực. |
| MB-E08<br>Quay sát khách khác | Nhắc quy định trong tiệm, chỉ khu quay hoặc yêu cầu dừng. | Khách được bảo vệ không gian; phản ứng của người quay tùy cách xử lý. |
| MB-E09<br>Review hiểu nhầm | Đọc đơn, xem thời điểm hẹn và giải thích công khai ở mức cần thiết. | Chuyển phần thông tin riêng sang tin nhắn; có thể hẹn lại. |
| MB-E10<br>Bom đơn quà | Liên hệ xác nhận, giữ đơn có hạn hoặc chuyển hàng về bán lẻ. | Không tự có doanh thu; giảm lãng phí bằng phương án bán lại. |
| MB-E11<br>Dùng thử nhiều lần | Hỏi nhu cầu, áp dụng giới hạn phần thử hoặc chủ động mời thêm. | Khách có thể mua, rời đi hoặc quay lại; không bảo đảm được đền đáp. |
| MB-E12<br>Khách thật sự cần giúp | Hỏi vừa đủ; tặng từ quỹ tiệm, giảm giá hoặc từ chối lịch sự. | Ghi nhận lựa chọn, không dùng điểm đạo đức ép người chơi tặng. |

> Bản JSON kèm theo bổ sung sự thật gốc, điều kiện chọn, ngày mở sớm nhất, khoảng nghỉ và hợp đồng xử lý. Đây là hạt nội dung để dựng kịch bản, chưa phải mã sự kiện thực thi.


---

## MB • 5/6 • TÌNH HUỐNG 13–24 — Chuyện đời thường • phần 2

Tình huống được mở khi đã có công cụ xử lý. Dữ kiện gốc được cố định trước khi chọn; hậu quả chỉ xảy ra sau hành động được xác nhận.

| Mã / tình huống | Người chơi làm gì? | Phản hồi / chuyện tiếp |
| --- | --- | --- |
| MB-E13<br>Khách quên ví | Giữ hàng, hẹn thanh toán hoặc chủ động tặng món đã chọn. | Nếu cho hẹn, tạo khoản hẹn riêng và lần quay lại. |
| MB-E14<br>Đơn hàng xóm lớn | Chốt số lượng, khả năng đáp ứng và giờ nhận trước khi nhận đơn. | Mở chuỗi chuẩn bị cộng đồng, không tăng tải vượt mức đã chấp nhận. |
| MB-E15<br>Giao hàng nhập bị thiếu | Kiểm kiện, đối chiếu phiếu và báo nhà cung cấp. | Nhận bù hoặc giảm đơn; kho không cộng số lượng chưa nhận. |
| MB-E16<br>Nhân viên lấy nhầm | Kiểm trước khi giao, sửa món rồi hướng dẫn phụ việc. | Mở quy tắc gắn nhãn hoặc kiểm hai bước. |
| MB-E17<br>Khách làm vỡ món | Dọn khu vực, hỏi thăm và xử lý theo quy định tiệm đã công bố. | Không tự kết luận phá hoại; ghi nhận thiệt hại có giới hạn. |
| MB-E18<br>Tranh lượt thanh toán | Xem thứ tự, giải thích, xin ý kiến nếu nhường lượt. | Hai khách phản ứng theo việc được xử lý công bằng và rõ ràng. |
| MB-E19<br>Mưa tạt vào hàng | Che kệ, chuyển hàng và tạm đóng khu vực bị ảnh hưởng. | Một số dịch vụ tạm dừng, mở lựa chọn nâng cấp mái che. |
| MB-E20<br>Khách để quên túi | Cất vào đồ thất lạc, xác minh bằng chi tiết trong game rồi trả. | Khách cảm ơn; không đăng vật riêng tư lên bảng tin. |
| MB-E21<br>Giật túi trước cửa | Trấn an khách, báo bảo vệ và cung cấp dữ kiện được nhìn thấy. | Mở vụ theo dõi; không truy đuổi hoặc mất đồ hiếm của người chơi. |
| MB-E22<br>Clip tích cực bất ngờ | Bật nhận hẹn, giới hạn lượt hoặc nhờ người hỗ trợ. | Lượng khách tăng có kiểm soát, không ép phục vụ tất cả. |
| MB-E23<br>Khách nhờ tư vấn chuyên môn | Giải thích phạm vi tiệm, chỉ hỗ trợ thông tin hàng giả lập và chuyển người phù hợp. | Không thưởng cho đoán cách dùng sản phẩm chăm sóc sức khỏe. |
| MB-E24<br>Buổi gói quà khu phố | Chọn chủ đề, chuẩn bị dụng cụ, mời khách rồi hỗ trợ từng bàn. | Nhận ảnh nhóm và đồ trang trí kỷ niệm, không phụ thuộc doanh số. |

> Bản JSON kèm theo bổ sung sự thật gốc, điều kiện chọn, ngày mở sớm nhất, khoảng nghỉ và hợp đồng xử lý. Đây là hạt nội dung để dựng kịch bản, chưa phải mã sự kiện thực thi.


---

## MB • 6/6 • TIẾN TRÌNH & NGHIỆM THU — Mười ngày đầu, rồi chơi theo cách riêng

| Ngày game | Trải nghiệm mới |
| --- | --- |
| 1 | Một khách, lấy đúng món, thu tiền, đóng cửa; luôn có gợi ý. |
| 2 | Hỏi nhu cầu và gói quà bằng mẫu có sẵn. |
| 3 | Nhập hàng, kiểm kiện, đặt lại kệ. |
| 4 | Đơn hẹn nhận sau và tin nhắn xác nhận. |
| 5 | Review đầu tiên; trả lời và làm việc bổ sung nếu có. |
| 6 | Khách quen quay lại; mở phối quà tự do. |
| 7 | Chọn một tình huống đời thường; có thể giảm độ căng. |
| 8 | Nhận phụ việc và hướng dẫn bổ sung hàng. |
| 9 | Chuẩn bị hoạt động cộng đồng hoặc một đơn lớn tự chọn. |
| 10 | Khép tuyến chuyện đầu, mở trang trí sâu và chơi tự do. |

### Những nâng cấp nhìn thấy được

Kệ hai mặt; nhãn vị trí; bàn gói quà; máy in thiệp giả lập; góc chụp ảnh; ghế khách; quầy nhận hẹn; phụ việc. Chỉ mở công cụ khi vòng chơi đã giới thiệu nhu cầu sử dụng.

### Chơi sau ngày 10

Luân phiên việc nghề, khách quen, tuyến chuyện còn mở và biến thể có căn cứ. Có thể chọn một ngày ít việc để trang trí/khám phá. Ngày 10 không phải kết thúc game; cũng không tự tăng độ căng vô hạn.

### Tiêu chí phải đạt

Đặt nhầm rồi sửa được; không bán hàng đã giữ hai lần; kho chỉ tăng sau kiểm nhận; tặng/hoàn tiền có xác nhận; review có đơn/sự kiện gốc; cả chọn nhanh và tự gõ đều hoàn thành được tuyến chính.

> Lịch 10 ngày là kịch bản giới thiệu để thử nghiệm, không bắt buộc người chơi đăng nhập 10 ngày ngoài đời. Có thể kéo dài một ngày hoặc tạm dừng giữa chừng.


---

## PH • 1/6 • CẢNH & VÒNG CHƠI — Nhà thuốc nhỏ

> Trò chơi về sự cẩn thận, kiểm chứng và biết giới hạn của mình.

### Không gian chơi

Quầy Bình An giả lập: bàn nhận phiếu, các kệ mã hàng, khay kiểm tra, khu tạm giữ lô, bàn của người phụ trách, kho và hàng chờ. Phiếu và bao bì chỉ dùng tên/mã hư cấu. Bố cục cho thấy người chơi đang thao tác tại quầy, không là bảng quản lý kho toàn màn hình.

### Vòng chơi

Nhận phiếu → kiểm dữ kiện → đối chiếu mã/số lượng/lô → hỏi hoặc chuyển khi thiếu → kiểm cuối → giao nhận → cập nhật kho → theo dõi phản hồi.

| Chạm vào | Tương tác |
| --- | --- |
| Khách / phiếu | Đọc yêu cầu và thông tin còn thiếu; không tự tạo chẩn đoán. |
| Kệ mã hàng | Chọn hộp theo mã giả lập; xoay xem nhãn bằng thao tác đơn giản. |
| Khay kiểm tra | So danh sách phiếu với các hộp đã chọn, số lượng và điều kiện lô. |
| Khu tạm giữ | Cách ly vật phẩm chưa đủ điều kiện game, không bán lẫn. |
| Người phụ trách | Hỏi lại, xin xác nhận hoặc chuyển yêu cầu ngoài phạm vi. |

### Một lượt chơi hoàn chỉnh

Một người mua hộ chỉ nhớ hộp màu xanh. Bạn hỏi phiếu hoặc mã thay vì đoán. Sau khi họ bổ sung, bạn chọn giữa hai hộp có bao bì gần giống, xem mã và lô, lấy đúng hai hộp, kiểm khay rồi giao. Cảm giác hoàn thành đến từ việc làm đúng và hỗ trợ rõ ràng, không phải bán được nhiều nhất.

### Kỹ năng người chơi đang dùng

Đối chiếu chi tiết, quản lý trạng thái, ưu tiên lượt, giải thích giới hạn và giữ thông tin riêng. Không có bài đoán bệnh từ triệu chứng, khuyến nghị thuốc thật hoặc chỉ dẫn liều dùng.


---

## PH • 2/6 • CƠ CHẾ CỐT LÕI — Sáu việc thật sự để chơi

### Phiếu đủ điều kiện

Phiếu có danh sách trường do nhiệm vụ quy định. Dữ kiện thiếu phải được hỏi lại hoặc chuyển người phụ trách. Trò luôn cho đường tiếp tục hợp lệ, không bắt người chơi bịa dữ liệu để thông qua.

### Tìm đúng mã

Kệ có các vật phẩm tên hư cấu và hình gần nhau. Thử thách là đọc mã, hình dấu và số lượng, không yêu cầu kiến thức y khoa. Có hỗ trợ đọc nhãn lớn để tránh thành bài kiểm tra thị lực.

### Quản lý lô

Mỗi lô có trạng thái hiệu lực theo ngày game. Lô tạm giữ không xuất được. Nhận nhập phải đối chiếu số lượng/lô; hộp nhận trả không tự trở thành hàng có thể bán.

### Kiểm hai bước

Khay đối chiếu hiển thị yêu cầu và vật đã lấy. Có thể sửa trước giao; chốt xuất kho chỉ chạy một lần. Nâng cấp hỗ trợ tìm sai khác, không loại bỏ trách nhiệm quyết định.

### Chuyển người phụ trách

Yêu cầu vượt dữ liệu nhiệm vụ chuyển cho NPC phù hợp. Khách có thể chưa hài lòng, nhưng game vẫn công nhận xử lý đúng; không thưởng bỏ kiểm tra để lấy review đẹp.

### Phản hồi và theo dõi

Review chỉ nói về giao nhận, sự rõ ràng, chờ và cách phục vụ. Sự kiện giao nhầm/giữ lô tạo công việc thực, không tự suy diễn tác dụng hay kết quả sức khỏe của khách.

### Kinh tế và điều kiện thành công

Thưởng chính xác và hoàn thành quy trình; không có hoa hồng để khuyến khích bán sai. Tồn theo lô được tách thành có thể dùng, đã giữ cho đơn và tạm giữ. Từ chối đúng phạm vi không làm người chơi mất đường nâng cấp.

### Trạng thái nghiệp vụ giả lập

received → checked / needs_clarification → authorized_in_simulation → picked → double_checked → handed_over. Nhánh: referred, waiting_for_stock, held_for_review, cancelled. “authorized_in_simulation” chỉ là điều kiện nhiệm vụ, không phải xác nhận pháp lý hay chuyên môn ngoài đời.


---

## PH • 3/6 • NHÂN VẬT & CÂU CHUYỆN — Những người sẽ quay lại

| NPC | Vai trò | Tính cách / cách tương tác |
| --- | --- | --- |
| Cô Thu | Người phụ trách | Cẩn thận, khuyến khích hỏi lại khi thiếu dữ kiện. |
| Bác Năm | Khách quen | Thích hướng dẫn rõ từng bước giao nhận; không thích bị giục. |
| Lan | Người mua hộ | Hay quên mã; sẵn lòng kiểm lại với người nhờ mua. |
| Khoa | Nhân viên mới | Nhanh nhưng dễ nhầm bao bì; cần quy trình đối chiếu. |
| Minh | Nhà cung cấp | Ưu tiên phiếu giao và kiểm đếm; có thể giao nhầm. |
| Vy | Người kể chuyện khu phố | Muốn giới thiệu nơi phục vụ cẩn thận; cần nhắc về quyền riêng tư. |

### Người mua hộ cẩn thận hơn

Lan tới với mô tả thiếu → được hướng dẫn lấy đúng thông tin → lần sau mang phiếu đủ → giúp chuẩn bị một danh mục vật dụng giả lập cho gia đình. Ký ức chỉ gồm quy trình, không lưu suy đoán bệnh.

### Khoa học cách kiểm hai bước

Bạn phát hiện Khoa chọn nhầm bao bì → cùng kiểm mã → thiết lập vị trí và nhãn → trong ca đông Khoa chủ động phát hiện sai khác. Sự tiến bộ được thể hiện qua hành động trong cảnh.

### Góc chia sẻ của khu phố

Vy muốn làm bài giới thiệu → bạn thống nhất vùng quay và dữ liệu được chia sẻ → thực hiện hoạt động danh mục vật dụng đã duyệt trong game → nhận phản hồi về sự cẩn thận. Không tạo nội dung tư vấn thuốc thật.

> Lan: “Mình chỉ nhớ hộp màu xanh.”
> Bạn: “Mình cần mã trên phiếu để lấy đúng, bạn kiểm tra lại giúp mình nhé.”
> Hệ thống: giữ yêu cầu ở trạng thái cần bổ sung; khách khác vẫn có thể được phục vụ.
> Lan cung cấp mã P-03, số lượng 2.
> Bạn chọn hộp, đối chiếu lô và kiểm khay trước khi chốt.

> Mọi ký ức đều liên kết một sự kiện đã diễn ra trong nghề này. Bỏ qua một câu chat không xóa nhiệm vụ; không ép gõ tự do để mở tuyến truyện.


---

## PH • 4/6 • TÌNH HUỐNG 01–12 — Chuyện đời thường • phần 1

Tình huống được mở khi đã có công cụ xử lý. Dữ kiện gốc được cố định trước khi chọn; hậu quả chỉ xảy ra sau hành động được xác nhận.

| Mã / tình huống | Người chơi làm gì? | Phản hồi / chuyện tiếp |
| --- | --- | --- |
| PH-E01<br>Phiếu đầu tiên | Đối chiếu mã, số lượng, thông tin lô rồi đóng gói. | Nhận phản hồi vì làm đúng, không cần tư vấn bệnh. |
| PH-E02<br>Phiếu thiếu trường | Chỉ ra thông tin còn thiếu, hỏi bổ sung hoặc chuyển người phụ trách. | Đơn được giữ chờ, không bị chấm sai vì chưa bán. |
| PH-E03<br>Khách mua hộ | Hỏi lại mã trong phiếu hoặc giữ yêu cầu để người mua xác nhận. | Không đoán theo lời mô tả mơ hồ. |
| PH-E04<br>Bao bì gần giống | Xoay hộp, đọc mã và đối chiếu trước khi đưa vào khay. | Lấy đúng mở điểm chính xác; sửa nhầm trước chốt không mất tiền. |
| PH-E05<br>Số lượng không khớp | So lại phiếu và khay; thêm hoặc bỏ đúng số hộp. | Chỉ hoàn thành khi số lượng đúng. |
| PH-E06<br>Lô không còn hợp lệ | Xem nhãn lô, tách khỏi kệ bán và chọn lô khác. | Kho bán được cập nhật, mở việc xử lý lô riêng. |
| PH-E07<br>Hộp bị móp | Kiểm tình trạng, giữ riêng và hỏi người phụ trách. | Khách nhận món đủ điều kiện; không cố bán để đạt chỉ tiêu. |
| PH-E08<br>Khách muốn lấy gấp | Giải thích bước kiểm tra, xin hỗ trợ hoặc nhận hẹn. | Nhanh không được lấn điều kiện xác minh. |
| PH-E09<br>Yêu cầu ngoài phạm vi | Từ chối đoán, chuyển người phụ trách chuyên môn của cảnh. | Kết quả đúng là chuyển tuyến trong game, không phải bán bằng mọi giá. |
| PH-E10<br>Hết đúng mã hàng | Thông báo tồn thực, nhận hẹn hoặc kết thúc yêu cầu. | Không tự thay mã khác như một chỉ dẫn chuyên môn. |
| PH-E11<br>Giá bị hiểu nhầm | So giá nhãn, hóa đơn và số lượng rồi giải thích hoặc sửa. | Review có thể cập nhật sau khi vấn đề được giải quyết. |
| PH-E12<br>Khách quên thanh toán | Kiểm giao dịch, giữ gói hoặc hẹn theo quy định tiệm. | Không ghi doanh thu khi chưa nhận tiền. |

> Bản JSON kèm theo bổ sung sự thật gốc, điều kiện chọn, ngày mở sớm nhất, khoảng nghỉ và hợp đồng xử lý. Đây là hạt nội dung để dựng kịch bản, chưa phải mã sự kiện thực thi.


---

## PH • 5/6 • TÌNH HUỐNG 13–24 — Chuyện đời thường • phần 2

Tình huống được mở khi đã có công cụ xử lý. Dữ kiện gốc được cố định trước khi chọn; hậu quả chỉ xảy ra sau hành động được xác nhận.

| Mã / tình huống | Người chơi làm gì? | Phản hồi / chuyện tiếp |
| --- | --- | --- |
| PH-E13<br>Giao nhập sai lô | Đối chiếu phiếu, cách ly kiện và yêu cầu điều chỉnh. | Không nhập lô sai vào tồn có thể bán. |
| PH-E14<br>Thông báo giữ lô | Tìm các hộp thuộc lô, chặn xuất và tạo việc liên hệ giả lập. | Mở chuỗi kiểm tra đã hoàn tất, không phát thông tin y tế thật. |
| PH-E15<br>Khách đổi trả | Xem trạng thái hộp và quy định giả lập, đề nghị phương án phù hợp. | Tách hàng nhận lại khỏi tồn bán cho đến khi kiểm tra. |
| PH-E16<br>Review đòi bỏ kiểm tra | Đọc vụ việc, giải thích lý do chưa thể xử lý và đề nghị bước tiếp. | Không mất tiến trình vì từ chối thao tác thiếu điều kiện. |
| PH-E17<br>Người quay clip | Nhắc không quay dữ liệu khách; chỉ khu được quay hoặc dừng. | Không đưa phiếu và thông tin riêng lên bài phản hồi công khai. |
| PH-E18<br>Đòi tặng sản phẩm | Thảo luận hợp tác hoặc tặng vật lưu niệm phù hợp; có thể từ chối. | Không dùng quà chuyên môn để đổi lấy review tích cực. |
| PH-E19<br>Nghi mất hàng | So kho, vị trí và giao dịch trước khi hỏi khách. | Có thể tìm hàng chuyển nhầm; không kết tội từ diện mạo. |
| PH-E20<br>Lấy hàng không trả | Kiểm bằng chứng, nhắc thanh toán hoặc nhờ bảo vệ. | Giới hạn thiệt hại, không có minigame đánh nhau. |
| PH-E21<br>Mất điện quầy | Lưu việc đang làm, tạm ngừng bước cần thiết và hướng dẫn khách chờ. | Khôi phục tiếp tục đúng phiếu, không xuất lặp. |
| PH-E22<br>Đơn bị giao nhầm | Đối chiếu hai đơn, liên hệ đúng khách riêng tư và sửa giao nhận. | Chỉ đóng vụ khi hàng được xử lý xong theo kịch bản. |
| PH-E23<br>Tủ vật dụng khu phố | Chuẩn bị bộ vật dụng giả lập theo danh mục được duyệt. | Mở hoạt động cộng đồng và ảnh kỷ niệm. |
| PH-E24<br>Khách quay lại cảm ơn | Trò chuyện về sự cẩn thận, nhận ảnh hoặc cây nhỏ trang trí. | Tăng mức quen biết từ việc đã làm thật trong game. |

> Bản JSON kèm theo bổ sung sự thật gốc, điều kiện chọn, ngày mở sớm nhất, khoảng nghỉ và hợp đồng xử lý. Đây là hạt nội dung để dựng kịch bản, chưa phải mã sự kiện thực thi.


---

## PH • 6/6 • TIẾN TRÌNH & NGHIỆM THU — Mười ngày đầu, rồi chơi theo cách riêng

| Ngày game | Trải nghiệm mới |
| --- | --- |
| 1 | Đọc một phiếu đủ và lấy một mã hàng. |
| 2 | Phân biệt bao bì giống, kiểm số lượng. |
| 3 | Phiếu thiếu dữ kiện và cách hỏi/chuyển. |
| 4 | Lô hàng, khu tạm giữ và kiểm nhận nhập. |
| 5 | Hai lượt khách, tạm dừng đọc và giải thích thời gian chờ. |
| 6 | Hỗ trợ Khoa, mở công cụ đối chiếu. |
| 7 | Review và quyền riêng tư khi quay clip. |
| 8 | Xử lý sai giao nhận bằng chứng cứ. |
| 9 | Tổ chức hoạt động vật dụng giả lập cho khu phố. |
| 10 | Kiểm một ca đầy đủ, nhận kỷ niệm và tiếp tục tự do. |

### Những nâng cấp nhìn thấy được

Kệ nhãn rõ; kính đọc nhãn giả lập; khay chia đơn; bàn kiểm hai bước; khu tạm giữ; bảng gọi lượt; ghế chờ; phụ tá kiểm kho. Tăng khả năng tổ chức, không mở quyền chẩn đoán hoặc bán thuốc thật.

### Chơi sau ngày 10

Luân phiên việc nghề, khách quen, tuyến chuyện còn mở và biến thể có căn cứ. Có thể chọn một ngày ít việc để trang trí/khám phá. Ngày 10 không phải kết thúc game; cũng không tự tăng độ căng vô hạn.

### Tiêu chí phải đạt

Không hoàn thành phiếu thiếu dữ kiện; không bán lô tạm giữ; không tự thay mã; trò vẫn tiếp tục khi chuyển người phụ trách; review không tiết lộ phiếu; không có tên/liều thuốc thật trong dữ liệu seed.

> Lịch 10 ngày là kịch bản giới thiệu để thử nghiệm, không bắt buộc người chơi đăng nhập 10 ngày ngoài đời. Có thể kéo dài một ngày hoặc tạm dừng giữa chừng.


---

## AC • 1/6 • CẢNH & VÒNG CHƠI — Một ngày làm kế toán

> Một bàn làm việc đầy câu đố, không phải công việc nhập liệu kéo dài.

### Không gian chơi

Góc Sổ Xinh: bàn nhận tài liệu, khay việc mới/đang kiểm/chờ bổ sung, bảng ghim nguồn, máy tính, máy in giả lập và bàn đồng nghiệp. Tài liệu nằm thành thẻ có thể lật, nhóm và đối chiếu. Máy tính chỉ mở bảng chi tiết đúng vụ đang chơi, không phủ toàn cảnh bằng biểu mẫu.

### Vòng chơi

Nhận vụ → đọc mục tiêu → gom chứng cứ → phân loại/ghép → hỏi nguồn thiếu → tìm sai lệch → đề xuất điều chỉnh → trình kết quả → nhận phản hồi và lưu nguồn.

| Chạm vào | Tương tác |
| --- | --- |
| Khay tài liệu | Nhận, phân loại và chuyển trạng thái từng vụ. |
| Bảng ghim | Đặt hai nguồn cạnh nhau, nối các khoản liên quan. |
| Máy tính | Lọc bảng nhỏ, xem tổng có diễn giải và lịch sử thay đổi. |
| Đồng nghiệp | Hỏi thông tin, yêu cầu bổ sung, bàn giao hoặc giải thích. |
| Kệ hồ sơ | Tra cứu nguồn đã xác minh, phiên bản và báo cáo mô phỏng. |

### Một lượt chơi hoàn chỉnh

Ba phiếu 120, 180 và 250 xu có tổng 550. Hai giao dịch 300 và 250 cũng có tổng 550, nhưng bản tổng hợp đang hiển thị 800 vì bản 250 bị tính hai lần. Bạn ghép 120+180 với 300, kiểm tham chiếu của hai bản 250, loại trùng có lý do rồi giải thích kết quả cho đồng nghiệp.

### Kỹ năng người chơi đang dùng

Đọc mục tiêu, phân loại, so khớp, tìm nguồn mâu thuẫn, giải thích và quản lý việc chờ. Số liệu và quy ước hạch toán chỉ là câu đố giả lập, không dùng chuẩn thuế hay chế độ kế toán thực tế để đánh giá người chơi.


---

## AC • 2/6 • CƠ CHẾ CỐT LÕI — Sáu việc thật sự để chơi

### Phân loại tài liệu

Thẻ có mã, ngày game, số xu và nguồn. Người chơi đặt vào khay theo mục đích nhiệm vụ. Khi chưa rõ, giữ “chờ xác minh”; không buộc mỗi thẻ phải vào một đáp án ngay.

### Ghép và tách giao dịch

Hỗ trợ một-một, nhiều-một và một-nhiều theo câu đố. Tổng cập nhật khi người chơi nối thẻ. Sai cho biết điều chưa khớp để kiểm tiếp, không hiện đáp án hoàn chỉnh ngay.

### Phát hiện lỗi có nguồn

So bản gốc, dữ liệu nhập và phiên bản. Loại trùng hoặc chỉnh số phải gắn lý do và nguồn. Không cho gõ số bất kỳ để biến bảng đỏ thành xanh rồi nhận thưởng.

### Hỏi bổ sung

Tin nhắn yêu cầu chọn đúng người, chứng từ và thông tin còn thiếu. Người nhận phản hồi theo tiến trình game; có thể chuyển vụ khác trong lúc chờ. Không chờ theo giờ ngoài đời.

### Trình bày kết quả

Chọn bảng, nhóm hoặc cách giải thích phù hợp câu hỏi. Báo cáo mẫu phải chỉ ra phạm vi, tổng và phần còn chờ. Không chấm đẹp hình cao hơn số liệu đúng.

### Bàn giao và sửa sau chốt

Bàn giao gồm nguồn, việc đã làm và bước tiếp. Kết quả đã chốt có phiên bản; thay đổi sau đó là điều chỉnh có nhật ký, không ghi đè âm thầm.

### Kinh tế và điều kiện thành công

Xu trong tài liệu là dữ liệu của khách/công ty giả lập, không vào ví người chơi. Ví nghề nhận thù lao hoàn thành vụ và dùng trang trí/nâng cấp công cụ. Không trả thưởng cao cho sửa dữ liệu sai hoặc giấu chênh lệch.

### Trạng thái nghiệp vụ giả lập

received → scoped → inspecting → needs_source / reconciled → reviewed → delivered → archived. Nhánh: handed_over, corrected_with_version, cancelled. Tách trạng thái công việc khỏi trạng thái từng tài liệu và từng dòng dữ liệu.


---

## AC • 3/6 • NHÂN VẬT & CÂU CHUYỆN — Những người sẽ quay lại

| NPC | Vai trò | Tính cách / cách tương tác |
| --- | --- | --- |
| Huy | Đồng nghiệp mới | Chịu học nhưng dễ vội; thích ví dụ cụ thể. |
| Chị Vân | Người quản lý | Muốn biết số liệu có căn cứ và việc nào còn chờ. |
| Cô Hoa | Khách thuê làm sổ | Giỏi bán hàng nhưng không quen thuật ngữ; hỏi thực tế. |
| Nam | Bộ phận mua hàng | Thường gửi tài liệu rời rạc; hợp tác khi yêu cầu cụ thể. |
| Lộc | Người giữ quỹ | Cẩn thận với bàn giao; khó chịu nếu bị kết luận vội. |
| Trâm | Người kiểm tra nội bộ | Đặt câu hỏi về nguồn và phiên bản; không phải đối thủ. |

### Huy hết sợ đối chiếu

Giúp Huy xử lý một lỗi nhập → cùng tạo thói quen kiểm nguồn → Huy nhận phần phân loại sơ bộ → hai người hoàn thành một kỳ giả lập. Nếu người chơi bỏ qua hướng dẫn, Huy vẫn cần hỗ trợ chứ không tự được nâng cấp.

### Sổ của cô Hoa

Cô Hoa gửi giấy tờ lộn xộn → bạn hỏi đúng phần thiếu → dựng bản tổng hợp dễ hiểu → cô chủ động chuẩn bị dữ liệu tốt hơn lần sau. Giá trị nằm ở hiểu dữ liệu, không bắt người chơi dùng nhiều thuật ngữ.

### Áp lực trước giờ chốt

Một vụ lệch số và lời đề nghị “sửa cho khớp” → bạn kiểm nguồn/chuyển quyền → tìm được bản thay thế hoặc giữ kết luận chưa đủ → trình bày minh bạch. Không cho đường gian lận thành đáp án bắt buộc để mở nội dung.

> Cô Hoa: “Sao bảng này nhiều tiền hơn số cô nhận?”
> Bạn: “Cháu đang kiểm bản 250 xu có bị tính lặp không, cô cho cháu xem phiếu gốc nhé.”
> Hệ thống: tạo yêu cầu nguồn, không tự sửa bảng.
> Có nguồn xác nhận → bạn đánh dấu trùng và kiểm lại tổng 550 xu.
> Cô Hoa nhận giải thích kèm các khoản đã đối chiếu.

> Mọi ký ức đều liên kết một sự kiện đã diễn ra trong nghề này. Bỏ qua một câu chat không xóa nhiệm vụ; không ép gõ tự do để mở tuyến truyện.


---

## AC • 4/6 • TÌNH HUỐNG 01–12 — Chuyện đời thường • phần 1

Tình huống được mở khi đã có công cụ xử lý. Dữ kiện gốc được cố định trước khi chọn; hậu quả chỉ xảy ra sau hành động được xác nhận.

| Mã / tình huống | Người chơi làm gì? | Phản hồi / chuyện tiếp |
| --- | --- | --- |
| AC-E01<br>Chứng từ đầu tiên | Kéo phiếu vào đúng nhóm, kiểm số và gắn nguồn giao dịch. | Hoàn thành một vụ nhỏ, có giải thích thay vì chỉ hiện đúng/sai. |
| AC-E02<br>Chứng từ trùng | So mã, thời điểm, nguồn và đánh dấu bản trùng. | Tổng được tính lại một lần, lưu lý do loại trùng. |
| AC-E03<br>Thiếu giấy tờ | Hỏi người gửi, tạo yêu cầu bổ sung và đặt việc ở trạng thái chờ. | Không bắt đoán hoặc bịa một chứng từ cho đủ. |
| AC-E04<br>Một chuyển khoản nhiều phiếu | Nhóm các phiếu hợp lệ rồi so tổng với giao dịch. | Mở cơ chế ghép nhiều-một, không ép một-một. |
| AC-E05<br>Một phiếu nhiều lần trả | Ghép từng lần thanh toán, tính phần còn lại. | Trạng thái phản ánh đã trả một phần, không tự coi thiếu tiền là gian. |
| AC-E06<br>Sai một chữ số | Đối chiếu bản gốc với dòng nhập, sửa có nhật ký. | Tổng khớp lại; người nhập được hướng dẫn, không bị bêu tên. |
| AC-E07<br>Khác mốc ngày | Kiểm ngày ghi nhận theo quy ước nhiệm vụ trước khi đối chiếu. | Đưa khoản về đúng kỳ game, có dấu vết thay đổi. |
| AC-E08<br>Khoản hoàn lại | Ghép chứng từ hoàn với giao dịch gốc, tránh đếm thành thu mới. | Bảng tổng hợp giải thích khoản điều chỉnh. |
| AC-E09<br>Quỹ không khớp | Kiểm các khoản đã xác nhận và khoản đang chờ, hỏi người giữ quỹ. | Chỉ kết luận từ chứng cứ, có thể giữ vụ chưa đủ dữ liệu. |
| AC-E10<br>Khách giục báo cáo | Nêu dữ liệu thiếu, đề nghị bản tạm gắn nhãn hoặc hẹn đủ dữ liệu. | Không xuất bản báo cáo hoàn chỉnh từ số liệu chưa kiểm tra. |
| AC-E11<br>Đồng nghiệp nhập sai | Cùng xem nguồn và sửa dòng, đề nghị bước kiểm tra mới. | Mức hợp tác tăng khi hỗ trợ rõ ràng, không phải chỉ khen. |
| AC-E12<br>Xin dùng lại chữ ký | Giữ quy trình xác nhận của game, yêu cầu người có quyền duyệt. | Không cho thao tác vượt quyền để nhận điểm tốc độ. |

> Bản JSON kèm theo bổ sung sự thật gốc, điều kiện chọn, ngày mở sớm nhất, khoảng nghỉ và hợp đồng xử lý. Đây là hạt nội dung để dựng kịch bản, chưa phải mã sự kiện thực thi.


---

## AC • 5/6 • TÌNH HUỐNG 13–24 — Chuyện đời thường • phần 2

Tình huống được mở khi đã có công cụ xử lý. Dữ kiện gốc được cố định trước khi chọn; hậu quả chỉ xảy ra sau hành động được xác nhận.

| Mã / tình huống | Người chơi làm gì? | Phản hồi / chuyện tiếp |
| --- | --- | --- |
| AC-E13<br>Nghi chứng từ giả | So dữ kiện nguồn, ghi vấn đề và chuyển người phụ trách. | Không hướng dẫn làm giả; giữ kết luận nghi vấn nếu chưa đủ bằng chứng. |
| AC-E14<br>Đề nghị giấu sai lệch | Từ chối sửa số cho khớp giả, ghi điều chỉnh hoặc chuyển xác minh. | Tiến trình không bị khóa vì giữ tính toàn vẹn dữ liệu. |
| AC-E15<br>Hai nguồn mâu thuẫn | Mở cả hai nguồn, hỏi bên sở hữu và ghi nguồn được xác nhận. | Báo cáo chỉ cập nhật sau khi có xác nhận. |
| AC-E16<br>Người lạ xin báo cáo | Kiểm quyền trong game, từ chối hoặc chuyển người phê duyệt. | Không lộ dữ liệu vì lời hứa hoặc tên hiển thị giống người quen. |
| AC-E17<br>Quay clip bàn làm việc | Che/tạm đóng tài liệu và đề nghị khu quay không có dữ liệu riêng. | Ảnh chia sẻ chỉ dùng dữ liệu mẫu đã làm sạch. |
| AC-E18<br>Yêu cầu chỉnh sau chốt | Mở quy trình điều chỉnh, giữ phiên bản cũ và giải thích thay đổi. | Không sửa âm thầm kết quả đã được xác nhận. |
| AC-E19<br>Nhầm tên tệp | So nội dung, mã khách và phạm vi trước khi gắn hồ sơ. | Trả tệp về đúng vụ; không coi tên file là sự thật. |
| AC-E20<br>Công việc đến dồn | Ưu tiên theo hạn và mức thiếu dữ liệu, thương lượng hoặc bàn giao. | Không buộc xử lý tất cả, lý do ưu tiên được lưu. |
| AC-E21<br>Mất kết nối lúc lưu | Giữ bản nháp, thử lại với cùng mã thao tác và kiểm kết quả. | Không cộng/ghi hai lần, người chơi không mất thao tác đã xác nhận. |
| AC-E22<br>Khách hiểu sai biểu đồ | Mở số nguồn, chọn cách trình bày và giải thích đơn vị/phạm vi. | Phản hồi tốt dựa trên hiểu đúng, không làm đẹp để che dữ kiện. |
| AC-E23<br>Hướng dẫn người mới | Cho đồng nghiệp thử một vụ nhỏ và giải thích chỗ sai. | Mở phụ tá có thể phân loại sơ bộ, vẫn cần duyệt bước quan trọng. |
| AC-E24<br>Khép kỳ khu phố | Hoàn thành chuỗi đối chiếu, trình bày kết quả và nhận phản hồi. | Nhận album thành quả và nâng cấp góc làm việc. |

> Bản JSON kèm theo bổ sung sự thật gốc, điều kiện chọn, ngày mở sớm nhất, khoảng nghỉ và hợp đồng xử lý. Đây là hạt nội dung để dựng kịch bản, chưa phải mã sự kiện thực thi.


---

## AC • 6/6 • TIẾN TRÌNH & NGHIỆM THU — Mười ngày đầu, rồi chơi theo cách riêng

| Ngày game | Trải nghiệm mới |
| --- | --- |
| 1 | Lật thẻ, phân loại và đối chiếu một cặp. |
| 2 | Tìm một lỗi nhập và ghi lý do sửa. |
| 3 | Ghép nhiều phiếu với một khoản trả. |
| 4 | Thiếu nguồn, gửi yêu cầu và chuyển vụ khác. |
| 5 | Đối chiếu khoản hoàn và thanh toán từng phần. |
| 6 | Giúp Huy, mở khay và bảng ghim mới. |
| 7 | Mâu thuẫn nguồn và phiên bản. |
| 8 | Trình bày một báo cáo giả lập có giải thích. |
| 9 | Xử lý áp lực, bàn giao và kiểm quyền. |
| 10 | Khép kỳ mô phỏng, nhận kỷ niệm và mở vụ biến thể. |

### Những nâng cấp nhìn thấy được

Khay phân loại; bảng ghim rộng; nhãn tài liệu; công cụ tìm trùng; mẫu yêu cầu bổ sung; góc báo cáo; tủ phiên bản; phụ tá. Công cụ gợi ý phải cho xem lý do, không tự làm hết bài.

### Chơi sau ngày 10

Luân phiên việc nghề, khách quen, tuyến chuyện còn mở và biến thể có căn cứ. Có thể chọn một ngày ít việc để trang trí/khám phá. Ngày 10 không phải kết thúc game; cũng không tự tăng độ căng vô hạn.

### Tiêu chí phải đạt

Tổng chỉ đổi từ nguồn/hành động hợp lệ; phát hiện cặp nhiều-một; tài liệu không mất khi bàn giao; thiếu dữ liệu có đường chờ; ví cá nhân không cộng tiền công ty; bản điều chỉnh giữ phiên bản cũ.

> Lịch 10 ngày là kịch bản giới thiệu để thử nghiệm, không bắt buộc người chơi đăng nhập 10 ngày ngoài đời. Có thể kéo dài một ngày hoặc tạm dừng giữa chừng.


---

## CS • 1/6 • CẢNH & VÒNG CHƠI — Chăm sóc khách hàng

> Giải quyết việc cho khách, không chỉ trả lời thật nhiều tin nhắn.

### Không gian chơi

Trạm Lắng Nghe: bàn máy tính, tai nghe, bảng hẹn, khay bàn giao, ghế trao đổi trưởng ca và khu phối hợp kho/giao nhận. Nhân vật vẫn hiện trong cảnh, đi trao đổi và phản ứng. Khi xử lý một vụ, màn chi tiết chia gọn hội thoại, chứng cứ và bước tiếp theo.

### Vòng chơi

Nhận yêu cầu → hỏi rõ vấn đề → xác minh dữ kiện/quyền → kiểm tra đơn → đề xuất phương án → xin duyệt khi cần → thực hiện/phối hợp → kiểm kết quả → theo dõi và đóng.

| Chạm vào | Tương tác |
| --- | --- |
| Hộp tin / chuông | Chọn vụ, xem mức cần xử lý và mục tiêu khách. |
| Bảng chứng cứ | So trạng thái đơn, ảnh game, giao dịch và lịch trao đổi. |
| Đầu mối phối hợp | Gửi yêu cầu đủ dữ kiện cho kho, giao nhận hoặc trưởng ca. |
| Bảng hẹn | Theo dõi lời hứa, đặt mốc cập nhật và bàn giao. |
| Khu tổng kết | Xem nhóm nguyên nhân, phản hồi thật và đề xuất cải tiến. |

### Một lượt chơi hoàn chỉnh

Khách nói chưa nhận hàng trong khi màn đơn ghi đã giao. Bạn hỏi mã giả lập, kiểm chứng cứ và thấy ảnh giao không khớp địa điểm. Bạn mở đối soát, hẹn cập nhật, xử lý một vụ ngắn khác, nhận kết quả rồi đưa phương án. Chỉ đóng khi hành động khắc phục đã thực hiện hoặc có kết luận được xác minh.

### Kỹ năng người chơi đang dùng

Lắng nghe, hỏi vừa đủ, nhận diện dữ liệu mâu thuẫn, lựa chọn phương án hợp lệ, phối hợp và giữ lời hẹn. Không thưởng đóng nhiều vụ bằng cách bỏ qua yêu cầu hoặc ép khách chấp nhận.


---

## CS • 2/6 • CƠ CHẾ CỐT LÕI — Sáu việc thật sự để chơi

### Hiểu vấn đề

Chat mở mục tiêu, bối cảnh và mong muốn. Câu trả lời nhanh gồm hỏi cần thiết, xác nhận và tra cứu; tự gõ có tác dụng tương đương. Không bắt hỏi lại thông tin đã có chỉ để kéo dài lượt chat.

### Kiểm chứng và quyền

Mỗi bằng chứng có nguồn và thời điểm game. Kiểm quyền trước khi mở thông tin đơn. Lời khách nói là lời khai; trạng thái công cụ có thể chưa đủ kết luận. Hai nguồn mâu thuẫn mở bước xác minh, không tự chọn một bên.

### Đề xuất phương án

Gửi bù, đổi, hoàn, chờ xác minh hoặc hướng dẫn theo chính sách giả lập. Mỗi phương án có điều kiện, chi phí thuộc hệ thống và quyền phê duyệt. Người chơi thấy vì sao chưa thể làm, không chỉ nút bị khóa.

### Phối hợp thực thi

Tạo công việc cho kho/giao nhận; NPC phải nhận việc và trả kết quả theo nhịp game. Câu “mình gửi bù rồi” không tự làm tồn hoặc giao nhận thay đổi. Có cách nhắc lại và chuyển hỗ trợ nếu bị chờ.

### Theo dõi lời hứa

Hẹn tạo mục trên bảng việc, liên kết vụ và người nhận bàn giao. Mốc quá hạn được giữ trong lịch sử; đổi hẹn phải thông báo và xác nhận, không xóa dấu vết cũ.

### Đóng và cải tiến

Điều kiện đóng kiểm kết quả theo loại vụ. Khách có thể đánh giá chưa tốt dù đã giải quyết; dùng phản hồi để nhận diện nguyên nhân lặp. Nâng cấp quy trình làm giảm lỗi cụ thể thay vì cộng sao vô điều kiện.

### Kinh tế và điều kiện thành công

Ví nghề là thu nhập/tiền thưởng giả lập cho chất lượng và hoàn thành ca. Giá trị đơn, tiền hoàn và bồi hoàn là ngân sách công ty trong nhiệm vụ, không phải tiền của người chơi. Điểm chất lượng cân bằng đúng dữ kiện, hiệu quả, tôn trọng và giữ hẹn.

### Trạng thái nghiệp vụ giả lập

new → understood → verifying → proposed → approved_if_needed → executing → awaiting_confirmation → resolved → closed. Nhánh: waiting_customer, waiting_internal, handed_over, reopened. Không bắt chờ khách vô hạn; từng loại vụ có điều kiện kết luận rõ do luật game quy định.


---

## CS • 3/6 • NHÂN VẬT & CÂU CHUYỆN — Những người sẽ quay lại

| NPC | Vai trò | Tính cách / cách tương tác |
| --- | --- | --- |
| Lan | Khách mới | Muốn biết rõ bước tiếp theo; không quen quy trình. |
| Phúc | Khách đang bức xúc | Nói ngắn, dễ nóng khi phải kể lại nhiều lần. |
| Hà | Khách quen | Lịch sự nhưng yêu cầu được xử lý chính xác. |
| Duy | Đầu mối kho | Có hàng đợi riêng; cần yêu cầu đủ mã và số lượng. |
| Ngọc | Đầu mối giao nhận | Chỉ xác nhận khi có chứng cứ giao; có thể cần đối soát. |
| Chị Mai | Trưởng ca | Hỗ trợ việc vượt quyền và bàn giao; không ép đóng cho đẹp số. |

### Khách phải kể lại quá nhiều lần

Phúc đã liên hệ nhiều lần → bạn đọc hồ sơ và xác định điểm thiếu → phối hợp một đầu mối → cập nhật đúng hẹn → nhận phản hồi. Lịch sự chỉ là bước đầu; cần xử lý điều còn dang dở.

### Bàn giao không đánh rơi lời hứa

Một ca phải chuyển → bạn tóm tắt và giao người nhận → người đó cần thông tin bổ sung hoặc xử lý tiếp → khách thấy không phải kể lại. Mở công cụ bàn giao sau khi hiểu vấn đề thực tế.

### Từ một review tới thay đổi quy trình

Hà phản hồi giao thiếu → bạn xử lý đúng vụ → phát hiện nhiều vụ cùng nguyên nhân → đề xuất kiểm đóng gói → ngày sau thấy loại lỗi giảm theo luật game. Phát hiện dựa trên hồ sơ, không do AI bịa một insight.

> Khách: “Mình chưa nhận, sao bên bạn ghi đã giao?”
> Bạn: “Mình sẽ kiểm chứng cứ giao, bạn cho mình mã đơn trong game nhé.”
> Hệ thống mở vụ và dữ kiện được phép xem.
> Bạn: “Mình thấy thông tin đang không khớp. Mình mở đối soát và cập nhật cho bạn ở mốc này.”
> Xác nhận hẹn → tạo việc theo dõi; chưa đóng vụ.

> Mọi ký ức đều liên kết một sự kiện đã diễn ra trong nghề này. Bỏ qua một câu chat không xóa nhiệm vụ; không ép gõ tự do để mở tuyến truyện.


---

## CS • 4/6 • TÌNH HUỐNG 01–12 — Chuyện đời thường • phần 1

Tình huống được mở khi đã có công cụ xử lý. Dữ kiện gốc được cố định trước khi chọn; hậu quả chỉ xảy ra sau hành động được xác nhận.

| Mã / tình huống | Người chơi làm gì? | Phản hồi / chuyện tiếp |
| --- | --- | --- |
| CS-E01<br>Đơn đầu tiên | Hỏi mã giả lập, xem trạng thái và trả lời đúng câu khách cần. | Khách xác nhận đã hiểu; chỉ đóng khi điều kiện vụ được đáp ứng. |
| CS-E02<br>Giao hàng chậm | Kiểm chặng hiện tại, liên hệ bên giao và hẹn mốc cập nhật. | Lời hứa tạo việc theo dõi, không tự đổi hàng thành đã giao. |
| CS-E03<br>Giao thiếu món | Đối chiếu đơn, ảnh/biên bản game và lựa chọn gửi bù hoặc hoàn phần thiếu. | Theo dõi thực hiện, không đóng ngay sau câu xin lỗi. |
| CS-E04<br>Giao sai món | Xác minh hai mã, đề nghị đổi hoặc phương án trong chính sách game. | Trạng thái đi qua xác nhận, thực hiện và kiểm tra kết quả. |
| CS-E05<br>Đã giao nhưng chưa nhận | Xem chứng cứ giao, hỏi thông tin cần thiết và chuyển đối soát. | Không cáo buộc khách nói dối hoặc người giao gian lận. |
| CS-E06<br>Khách đổi ý | Xem giai đoạn đơn và chính sách giả lập, đưa phương án còn khả dụng. | Không hứa hủy tức thì khi việc đã sang bước cần phối hợp. |
| CS-E07<br>Sản phẩm có vấn đề | Hỏi biểu hiện trong phạm vi game, lấy chứng cứ phù hợp và chuyển xử lý. | Không tự hứa kết quả chuyên môn hoặc phê duyệt vượt quyền. |
| CS-E08<br>Chưa thấy tiền hoàn | Kiểm trạng thái lệnh hoàn và xác nhận thực thi trong game. | Chỉ báo đã hoàn khi có kết quả, không chỉ vì tạo yêu cầu. |
| CS-E09<br>Khách nóng giận | Xác nhận vấn đề, hỏi ngắn gọn, đặt ranh giới khi bị xúc phạm. | Có thể chuyển hỗ trợ; không thưởng chịu đựng vô hạn. |
| CS-E10<br>Hai người hỏi cùng đơn | Kiểm quyền và quan hệ với đơn trước khi cung cấp thông tin. | Chỉ chia sẻ phần được phép, tránh trả nhầm cuộc hội thoại. |
| CS-E11<br>Tin nhắn lặp | Gộp yêu cầu liên quan sau khi kiểm tra, giữ lịch sử và chủ vụ. | Khách không bị trả lời mâu thuẫn bởi nhiều luồng. |
| CS-E12<br>Bàn giao giữa ca | Tóm tắt dữ kiện, việc đã làm, lời hẹn và bước tiếp theo. | Nhân vật nhận ca có đủ thông tin, khách không phải kể lại hết. |

> Bản JSON kèm theo bổ sung sự thật gốc, điều kiện chọn, ngày mở sớm nhất, khoảng nghỉ và hợp đồng xử lý. Đây là hạt nội dung để dựng kịch bản, chưa phải mã sự kiện thực thi.


---

## CS • 5/6 • TÌNH HUỐNG 13–24 — Chuyện đời thường • phần 2

Tình huống được mở khi đã có công cụ xử lý. Dữ kiện gốc được cố định trước khi chọn; hậu quả chỉ xảy ra sau hành động được xác nhận.

| Mã / tình huống | Người chơi làm gì? | Phản hồi / chuyện tiếp |
| --- | --- | --- |
| CS-E13<br>Đòi ưu đãi đổi review | Giải thích hỗ trợ theo vấn đề thật, không mua đánh giá tích cực. | Review và bồi hoàn là hai việc độc lập. |
| CS-E14<br>Clip phàn nàn | Đọc vụ gốc, trả lời công khai ngắn rồi chuyển phần riêng vào tin nhắn. | Không công khai dữ liệu khách để chứng minh mình đúng. |
| CS-E15<br>Mạo danh người quen | Kiểm quyền và chứng cứ game, không tin tên hiển thị một mình. | Từ chối/chuyển xác minh mà không lộ dữ liệu nhạy cảm. |
| CS-E16<br>Yêu cầu ngoài chính sách | Giải thích giới hạn, đề xuất phương án hợp lệ hoặc xin duyệt ngoại lệ. | Không tự tạo quyền hay hứa chắc trước khi được duyệt. |
| CS-E17<br>Kho nói khác khách | Giữ hai nguồn, hỏi chứng cứ bổ sung và cập nhật trạng thái chưa xác định. | Không tự chọn bên có vẻ đáng tin chỉ vì vai trò. |
| CS-E18<br>Hẹn nhưng quên theo dõi | Xem hẹn quá mốc game, xin lỗi và thực hiện bước khắc phục. | Không tự xóa hạn cũ; ghi rõ lần hẹn mới và kết quả. |
| CS-E19<br>Gửi nhầm phản hồi | Dừng gửi nếu còn nháp, hoặc nhận lỗi và sửa theo quy trình game. | Không lặp gửi; kiểm lại ngữ cảnh trước lần tiếp theo. |
| CS-E20<br>Hệ thống tra cứu lỗi | Thông báo chưa kiểm tra được, giữ nháp và hẹn cập nhật. | Không bịa trạng thái đơn để trả lời cho nhanh. |
| CS-E21<br>Khách chỉ cần hướng dẫn | Hỏi mục tiêu, đưa bước trong game và kiểm tra khách đã làm được. | Đo kết quả hiểu/làm được, không kéo dài chat để tăng điểm. |
| CS-E22<br>Khách quay lại cảm ơn | Nhắc đúng vụ đã xử lý và nhận phản hồi tự nguyện. | Mở ký ức tích cực, không nhắc khách phải chấm 5 sao. |
| CS-E23<br>Cao điểm sau quảng bá | Phân loại, nhận hẹn, chia việc và tạm giới hạn yêu cầu mới. | Không ép mở tất cả chat một lúc; thưởng xử lý đúng và rõ ràng. |
| CS-E24<br>Tổng kết cải tiến | Nhóm nguyên nhân lặp, đề xuất sửa quy trình và xem tác dụng. | Mở nâng cấp giảm loại vấn đề cụ thể trong ngày sau. |

> Bản JSON kèm theo bổ sung sự thật gốc, điều kiện chọn, ngày mở sớm nhất, khoảng nghỉ và hợp đồng xử lý. Đây là hạt nội dung để dựng kịch bản, chưa phải mã sự kiện thực thi.


---

## CS • 6/6 • TIẾN TRÌNH & NGHIỆM THU — Mười ngày đầu, rồi chơi theo cách riêng

| Ngày game | Trải nghiệm mới |
| --- | --- |
| 1 | Một vụ tra cứu đơn, trả lời ngắn và đóng đúng điều kiện. |
| 2 | Giao chậm và tạo hẹn cập nhật. |
| 3 | Giao thiếu, đề nghị gửi bù và chờ thực thi. |
| 4 | Hai nguồn mâu thuẫn, mở xác minh. |
| 5 | Đổi/hoàn theo chính sách giả lập và quyền. |
| 6 | Bàn giao với đầy đủ dữ kiện và lời hẹn. |
| 7 | Review công khai, trả lời không lộ thông tin riêng. |
| 8 | Khách nóng giận; giới hạn và hỗ trợ trưởng ca. |
| 9 | Ca cao điểm tự chọn; phân loại và chia việc. |
| 10 | Tổng kết nguyên nhân lặp, đề xuất cải tiến và mở chơi tự do. |

### Những nâng cấp nhìn thấy được

Bảng hẹn; mẫu hỏi theo ngữ cảnh; khay ưu tiên; bảng đối chiếu chứng cứ; bàn giao có cấu trúc; kênh phối hợp; thư viện hướng dẫn; góc thư giãn. Không có nâng cấp tự ép khách hài lòng.

### Chơi sau ngày 10

Luân phiên việc nghề, khách quen, tuyến chuyện còn mở và biến thể có căn cứ. Có thể chọn một ngày ít việc để trang trí/khám phá. Ngày 10 không phải kết thúc game; cũng không tự tăng độ căng vô hạn.

### Tiêu chí phải đạt

Không đóng khi chỉ mới hứa; tạo hẹn sinh việc thật; không hoàn tiền lặp; người không có quyền không thấy đơn; lời chê không tự bị xóa; mất dịch vụ AI vẫn xử lý được bằng lựa chọn có sẵn.

> Lịch 10 ngày là kịch bản giới thiệu để thử nghiệm, không bắt buộc người chơi đăng nhập 10 ngày ngoài đời. Có thể kéo dài một ngày hoặc tạm dừng giữa chừng.


---

## MỞ RỘNG • NGHỀ 05/16 • CHƯA CHỐT LỊCH — Quán ăn nhỏ

### Bối cảnh và trải nghiệm

Một quán vài bàn, quầy gọi món và căn bếp nhìn được toàn bộ. Người chơi tự chọn món tủ, bố trí bếp và quyết định phục vụ nhanh hay mở ít bàn để trò chuyện nhiều hơn.

### Vòng chơi

Chuẩn bị nguyên liệu → nhận và xác nhận món → chia việc bếp → chế biến theo công thức giả lập → bày món → phục vụ → thanh toán → dọn và đọc phản hồi.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Bếp có nhịp | Đặt nguyên liệu, chọn trạm và theo dõi mốc trong game. Có tạm dừng và chế độ không áp lực; không phải cứ bấm “nấu” rồi ngồi chờ. |
| Ghi nhớ yêu cầu | Đối chiếu món và tùy chọn đã xác nhận. Thông tin quan trọng được ghi lại trên phiếu; không bắt nhớ bằng đầu hoặc đoán nhu cầu ăn uống thật. |
| Phục vụ nhiều bàn | Chọn thứ tự hợp lý, gộp món có thể làm cùng và thông báo khi phải chờ. Có thể tạm ngừng nhận bàn mới. |
| Món riêng của quán | Phối cách bày, tên món hư cấu và bộ thực đơn nhỏ; mẫu lưu lại để làm nhanh. Không đưa hướng dẫn an toàn thực phẩm chuyên môn dưới dạng đáp án game. |

### Nhân vật và quan hệ

Cô khách ghé buổi trưa thích yên tĩnh; nhóm học nghề muốn món vừa túi tiền game; người hàng xóm thỉnh thoảng phụ rửa bát. Quan hệ mở chuyện đời thường và buổi ăn chung, không chỉ giảm giá.

### Chuyện đời thường

Ăn ké phần dùng thử; quên ví hoặc cố tình không thanh toán; khách đổi món sau khi bếp đã làm; reviewer quay sát bàn khác; đơn nhóm bị hủy. Mỗi vụ kiểm phiếu và thỏa thuận trước khi kết luận.

> “Món này mình đã nhờ bỏ phần trang trí rồi mà?” → xem phiếu → nếu ghi sót thì xin lỗi và làm lại; nếu chưa xác nhận thì cùng chọn cách xử lý, không tranh thắng bằng lời.

### Phát triển và review

Mở trạm bếp, tủ nguyên liệu, thực đơn theo chủ đề, phụ bếp và sân nhỏ. Review tập trung đúng món, nhịp phục vụ, không gian và cách khắc phục. Tuyến dài là chuẩn bị một bữa ăn khu phố.

> Kỹ năng riêng cần chứng minh: phối hợp trạm bếp và phục vụ bàn, không sao chép vòng lấy hàng của tiệm mẹ & bé.


---

## MỞ RỘNG • NGHỀ 06/16 • CHƯA CHỐT LỊCH — Cà phê & tiệm bánh

### Bối cảnh và trải nghiệm

Quầy pha, tủ bánh, bàn cửa sổ và góc sân. Đây là nghề thiên về sáng tạo thị giác và không gian, khác quán ăn thiên về nhịp bếp.

### Vòng chơi

Chọn menu → chuẩn bị mẻ/đồ dùng → nhận khẩu vị giả lập → pha hoặc trang trí → giao → thu thập phản hồi → lưu mẫu và chỉnh không gian.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Pha theo mẫu | Chọn các thành phần hư cấu theo phiếu, điều chỉnh mức được khách chọn. Có thước trực quan và nút từng bước thay cho kéo chính xác. |
| Trang trí bánh | Chọn nền, họa tiết, thông điệp và màu. Chấm mức phù hợp với brief đã xác nhận; không có mẫu duy nhất đúng cho mọi khách. |
| Đơn hẹn | Bánh sự kiện có mẫu duyệt trước, mốc nhận và vật liệu giữ riêng. Chỉnh yêu cầu sau duyệt phải trao đổi lại. |
| Không gian sống | Chọn nhạc trong thư viện game, bàn, cây và ánh sáng. NPC dùng đúng ghế/góc mới; không chỉ thay nền ảnh. |

### Nhân vật và quan hệ

Người làm việc từ xa thích góc yên; đôi bạn thường hẹn cùng giờ game; khách đặt bánh sinh nhật. Một NPC có thể chuyển từ tới dùng thử sang nhờ chuẩn bị một dịp quan trọng.

### Chuyện đời thường

Khách ngồi lâu nhưng chỉ gọi một món; yêu cầu quay clip cả quán; bánh bị đổi lời chúc phút cuối; khách làm đổ cốc; video tích cực khiến tiệm đông. Quy định chỗ ngồi và hợp tác được thiết lập trước.

> “Cho mình ngồi làm việc lâu một chút được không?” → người chơi chọn chính sách phù hợp: khu ngồi lâu, giới hạn theo mức đông hoặc chấp nhận bình thường; không có đáp án đạo đức duy nhất.

### Phát triển và review

Mở tủ bánh, công cụ trang trí, góc yên tĩnh, đèn sân, lịch đặt và phụ quầy. Review đánh giá trải nghiệm đã dùng, không bịa giải thưởng. Tuyến dài là buổi triển lãm ảnh/bánh theo chủ đề của phố.

> Mỗi mẫu sáng tạo có thể lưu và chia sẻ bản xem trước; nội dung người thật phải qua kiểm duyệt như các bài đăng khác.


---

## MỞ RỘNG • NGHỀ 07/16 • CHƯA CHỐT LỊCH — Freelancer sáng tạo

### Bối cảnh và trải nghiệm

Bàn làm việc ở nhà, bảng brief, máy tính và góc portfolio. Chọn đề tài thiết kế đơn giản trong game, không yêu cầu người chơi biết code hay sử dụng phần mềm chuyên nghiệp.

### Vòng chơi

Đọc lời mời → hỏi yêu cầu → xác nhận phạm vi → ghép sản phẩm nhỏ → gửi bản duyệt → trao đổi sửa đổi → bàn giao → nhận đánh giá và trang trí studio.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Làm rõ brief | Hỏi đối tượng, mục tiêu, phong cách và đầu ra. Những câu hỏi cần thiết mở điều kiện chấm; không cho khách bí mật đổi đáp án sau khi bạn nộp. |
| Làm sản phẩm | Ghép bố cục poster, chọn ảnh trong kho game, sắp màu/chữ hoặc dựng một trang mô phỏng bằng mảnh kéo thả. Có nhiều cách đạt brief. |
| Quản lý phiên bản | Giữ bản cũ, tạo bản mới và so sánh phần thay đổi. Khách chỉ nhận đúng bản người chơi đã gửi. |
| Thương lượng sửa đổi | Phân biệt lỗi chưa đúng brief và yêu cầu mới. Chọn sửa trong phạm vi, đề nghị thêm hạng mục hoặc từ chối lịch sự. |

### Nhân vật và quan hệ

Khách mới chưa biết diễn đạt; người chủ tiệm có gu rõ; bạn cộng tác mạnh về một phần việc. Quan hệ mở dự án thú vị hơn, không tự biến khách khó thành trả nhiều tiền.

### Chuyện đời thường

Khách đổi ý sau duyệt; góp ý mâu thuẫn giữa hai người; chậm phản hồi; xin file trước bước bàn giao; đòi làm thử vô hạn; lời mời hợp tác đáng tin. Mọi mốc dựa trên thỏa thuận giả lập được lưu.

> “Sửa thêm toàn bộ bố cục nhé, chỉ một chút thôi.” → xem phạm vi và bản duyệt → hỏi mục tiêu mới → đề xuất phiên bản bổ sung hoặc phương án nhỏ trong phạm vi.

### Phát triển và review

Từ góc bàn nhỏ tới studio, kho mẫu, bảng quản lý phiên bản, cộng tác viên và triển lãm portfolio. Review tập trung đúng brief, rõ ràng, chất lượng và đúng hẹn, không chỉ chiều khách.

> Đây là trò giải quyết brief và tạo tác phẩm nhỏ; không bắt người chơi thực hiện công việc thật miễn phí hoặc đưa tệp riêng ngoài đời vào game.


---

## MỞ RỘNG • NGHỀ 08/16 • CHƯA CHỐT LỊCH — Nông trại ngoại ô

### Bối cảnh và trải nghiệm

Vài luống cây, nhà kho, góc ủ phân hư cấu và quầy chợ. Nhịp chơi dài hơi nhưng không trừng phạt người chơi vì nghỉ ngoài đời.

### Vòng chơi

Chọn kế hoạch luống → gieo → chăm theo dấu hiệu trong game → thu hoạch → phân loại → đóng giỏ/đổi đồ → bán ở chợ → mở khu mới.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Bố trí luống | Chọn vị trí theo quy tắc ánh sáng/nước đơn giản của game; có bản xem trước và hoàn tác khi chưa gieo. |
| Chăm sóc quan sát | Xem trạng thái trực quan để tưới, che hoặc nghỉ. Không có cây chết chỉ vì người chơi chưa đăng nhập; tiến trình quan trọng theo nhịp ngày game. |
| Thu hoạch và phân loại | Chọn lứa, nhóm chất lượng theo quy tắc công khai, giữ một phần làm giống hoặc chuẩn bị đơn. |
| Chợ và trao đổi | Đóng giỏ theo yêu cầu hàng xóm, chọn quầy, trao đổi vật liệu và nhận lời nhờ. Không có đầu cơ bằng tiền thật. |

### Nhân vật và quan hệ

Người hàng xóm thích thử giống mới; chủ quán đặt giỏ theo tuần game; người bán hạt trao đổi kinh nghiệm giả lập. Mối quan hệ gắn với những mùa vụ đã cùng chuẩn bị.

### Chuyện đời thường

Mưa đúng lúc thu hoạch; giao hạt nhầm; khách hủy giỏ; đồ để nhầm bị tưởng mất; mùa bội thu cần chia sẻ; hàng xóm giúp thu hoạch. Biến cố có cách giảm thiệt hại và mức trần.

> “Giỏ tuần này ít món hơn lần trước?” → xem đơn đã chốt và số thu → đề nghị đổi giỏ, hẹn phần thiếu hoặc giảm giá đúng phần, không bịa đã giao đủ.

### Phát triển và review

Mở luống, kho phân loại, bàn đóng giỏ, chợ, góc nghỉ và nhà kính giả lập. Đánh giá gắn với đơn đã giao và sự ổn định, không ép tối đa hóa sản lượng. Tuyến dài là hội chợ mùa vụ.

> Kỹ năng riêng là quan sát chu kỳ và lên kế hoạch không gian; mọi hướng dẫn canh tác chỉ là luật mô phỏng, không chuyển thành tư vấn dùng hóa chất thật.


---

## MỞ RỘNG • NGHỀ 09/16 • CHƯA CHỐT LỊCH — Chuyên viên tư vấn bán hàng

### Bối cảnh và trải nghiệm

Một showroom đồ dùng hư cấu với khu trải nghiệm, bàn tư vấn và khu giao nhận. Trọng tâm là hiểu nhu cầu và so sánh phương án, không chỉ quét giá.

### Vòng chơi

Đón khách → hỏi nhu cầu/ràng buộc → demo → so phương án → xác nhận lựa chọn → phối hợp giao → theo dõi sử dụng trong game.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Khám phá nhu cầu | Khách có mục tiêu, ngân sách và ưu tiên khác nhau. Hỏi đúng mở thông tin; không suy đoán nhu cầu từ ngoại hình hay thông tin cá nhân nhạy cảm. |
| Demo tương tác | Cho khách thử hai hoặc ba sản phẩm giả lập với tính năng khác. Người chơi bật chức năng, bố trí phụ kiện và giải thích dữ liệu trong game. |
| So sánh minh bạch | Kéo các lựa chọn cạnh nhau, chỉ điểm phù hợp và hạn chế. Không có đáp án luôn là món đắt nhất. |
| Chốt và theo dõi | Tạo đề nghị rõ giá, món, phụ kiện và mốc giao. Nếu khách chưa sẵn sàng, ghi hẹn hoặc kết thúc bình thường. |

### Nhân vật và quan hệ

Khách thích tìm hiểu kỹ; khách đã chọn sai ở lần trước; người mua cho gia đình; đồng nghiệp hỗ trợ demo. Tuyến chuyện có thể là khách từ cân nhắc đến quay lại kể trải nghiệm.

### Chuyện đời thường

Khách đòi hứa tính năng không có; yêu cầu giảm giá ngoài quyền; đổi ý sau demo; người quay clip chỉ trích giá; giao thiếu phụ kiện; đối thủ được nhắc tới nhưng không có thương hiệu thật.

> “Bạn bảo đảm món này làm được việc X chứ?” → kiểm đặc tính của sản phẩm giả lập → nói đúng giới hạn hoặc đề xuất món khác; game không thưởng lời hứa không có căn cứ.

### Phát triển và review

Mở khu demo, mẫu so sánh, lịch hẹn, bộ phụ kiện và trợ lý. Thu nhập cân bằng mức phù hợp, giữ lời và kết quả; không phạt việc khuyên khách chưa cần mua. Review phản ánh trải nghiệm tư vấn và giao nhận.

> Khác tiệm mẹ & bé ở chiều sâu khám phá nhu cầu và demo; người chơi phải kiểm chứng điểm phù hợp, không chỉ tìm đúng kệ.


---

## MỞ RỘNG • NGHỀ 10/16 • CHƯA CHỐT LỊCH — Tạp hóa khu phố

### Bối cảnh và trải nghiệm

Tiệm nhỏ nhiều món thiết yếu hư cấu, quầy tính tiền, góc hàng đặt và sổ hẹn. Không gian có khách ra vào và chuyện hàng xóm.

### Vòng chơi

Kiểm hàng → sắp kệ → nhận danh sách mua → lấy/quét → tính tiền → giữ hàng hoặc giao → kiểm tồn và nhập cho ngày sau.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Nhớ vị trí và nhóm hàng | Danh sách mua có nhiều món; người chơi tối ưu đường lấy và giữ giỏ riêng từng khách. Có nhãn hỗ trợ thay vì bắt ghi nhớ mù. |
| Tính đơn | Quét món và kiểm ưu đãi giả lập. Hiển thị lý do giá thay đổi; tiền thừa có bước xác nhận, không chỉ bấm nhận xu. |
| Giữ hàng / sổ hẹn | Giữ một món cho khách quen có mốc game rõ. Hẹn thanh toán được ghi riêng, không tự biến thành tiền mặt. |
| Bày hàng | Chọn vị trí để dễ lấy và dễ nhìn, điều chỉnh theo nhu cầu đã quan sát. Không cần dashboard phân tích phức tạp. |

### Nhân vật và quan hệ

Khách mua đồ cho bữa tối, bác hàng xóm nhờ giữ món, người giao hàng theo tuyến. Mỗi người có lịch và lời nhờ khác nhau; thân quen mở trao đổi chứ không miễn mọi quy định.

### Chuyện đời thường

Tranh lượt, giá trên kệ chưa cập nhật, người quên ví, khách dùng tên người quen để xin nợ, nghi mất hàng, hàng nhập sai và đồ để quên. Kiểm log trước khi kết luận ai gian.

> “Cứ ghi sổ như mọi lần nhé.” → kiểm đúng NPC và thỏa thuận cũ → nhận hẹn hoặc đề nghị thanh toán; không mặc định tin mọi lời tự nhận quen chủ.

### Phát triển và review

Mở kệ phân khu, giỏ đặt trước, quầy phụ, tủ trưng bày và điểm nhận hàng. Review về đủ món, giá rõ và đối xử, không bịa hóa đơn. Tuyến dài là chuẩn bị quầy phục vụ ngày hội phố.

> Nét riêng là gom danh sách nhiều món, phối dòng khách và quản lý hẹn; tránh biến thành bản sao của game gói quà.


---

## MỞ RỘNG • NGHỀ 11/16 • CHƯA CHỐT LỊCH — Tiệm thời trang

### Bối cảnh và trải nghiệm

Quầy tư vấn, tủ đồ, gương thử, bàn chỉnh sửa đơn giản và góc chụp ảnh. Nhân vật thử đồ bằng hoạt ảnh trực quan; không đánh giá cơ thể khách.

### Vòng chơi

Hỏi dịp mặc và sở thích → chọn vài phối đồ → thử → điều chỉnh → chốt món → đóng gói → nhận ảnh/feedback sau dịp sử dụng.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Phối theo brief | Kéo món, màu và phụ kiện lên bảng phối. Điều kiện dựa trên điều khách nói, không dựa vào giới tính hay dáng người suy đoán. |
| Thử và sửa | Khách cho phản hồi về màu, kiểu hoặc kích cỡ giả lập. Chỉnh bằng thao tác đơn giản; không đưa chuẩn cơ thể đẹp/xấu vào điểm số. |
| Sắp bộ sưu tập | Chọn chủ đề cửa sổ, cách trưng bày và phối mannequin hư cấu. Có thể lưu bộ để khách khác thử. |
| Đơn dịp đặc biệt | Hẹn chỉnh và nhận, giữ món đúng đơn, gửi bản phối cho khách duyệt trong game. |

### Nhân vật và quan hệ

Khách muốn thử phong cách mới, người cần đồ cho sự kiện, bạn thích phụ kiện cá tính. Quan hệ mở album những dịp đã cùng chuẩn bị, không yêu cầu mua liên tục để được thân.

### Chuyện đời thường

Khách đổi ý sau thử, đồ đặt sai màu, yêu cầu quay phòng thử, người đòi mượn đồ để chụp rồi trả, hỏng phụ kiện, review chê không giống mẫu. Luôn bảo vệ khu riêng và kiểm nội dung đã chốt.

> “Mình muốn nổi bật hơn nhưng vẫn thoải mái.” → hỏi ưu tiên → đưa hai phối khác nhau → cho khách phản hồi; có nhiều kết quả được chấp nhận.

### Phát triển và review

Mở tủ, bàn phụ kiện, mẫu chỉnh sửa giả lập, khu chụp ảnh và buổi trình diễn nhỏ tự chọn. Review về hiểu brief, đúng món và thoải mái trong phục vụ. Album lưu lựa chọn của NPC đã đồng ý.

> Không chấm điểm theo vóc dáng, màu da hoặc định kiến giới; câu đố là đáp ứng sở thích được nói ra.


---

## MỞ RỘNG • NGHỀ 12/16 • CHƯA CHỐT LỊCH — Tiệm chăm sóc thú cưng

### Bối cảnh và trải nghiệm

Khu đón, góc làm quen, bàn chải lông, khu vệ sinh nhẹ, sân chơi và chỗ nghỉ. Đây là nghề chăm sóc tại tiệm, không thay thế game nuôi pet dài hạn.

### Vòng chơi

Nhận thông tin hư cấu từ chủ → làm quen → chọn hoạt động phù hợp → chăm sóc nhẹ → chơi/nghỉ → bàn giao → nhận phản hồi.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Quan sát tín hiệu | Thú cưng có biểu hiện trong hoạt ảnh. Người chơi cho nghỉ hoặc đổi hoạt động; không ép liên tục để đầy thanh tiến độ. |
| Chải và vệ sinh nhẹ | Thao tác đơn giản có nút từng bước, không yêu cầu thao tác gây đau hoặc quy trình y khoa. Sai nhẹ dừng để thử cách khác. |
| Chơi và làm quen | Chọn đồ chơi, nhịp tương tác và nơi nghỉ theo sở thích được ghi nhận. Mỗi con có tính cách riêng, không chỉ thay màu lông. |
| Bàn giao | Đối chiếu đúng thú cưng, đồ gửi kèm, các việc đã làm và điều cần báo cho chủ trong game. |

### Nhân vật và quan hệ

Người chủ lần đầu mang pet đi chăm, khách quen có pet nhút nhát, nhân viên mới học quan sát. Thú cưng cũng có ký ức game về đồ chơi và khu nghỉ ưa thích.

### Chuyện đời thường

Chủ đến muộn, đồ chơi gửi kèm bị nhầm, pet không hợp hoạt động, người quay clip chưa được đồng ý, lịch quá tải và lời cảm ơn sau khi pet dần quen tiệm.

> “Bé có vẻ không thích phần này, mình cho nghỉ rồi đổi sang chải nhẹ nhé?” → chọn nghỉ thật trong cảnh → theo dõi biểu hiện; không chỉ đổi câu nói cho dễ nghe.

### Phát triển và review

Mở khu nghỉ, đồ chơi, bàn chăm, lịch hẹn và phụ tá. Review tập trung sự rõ ràng, đúng bàn giao và trải nghiệm mô phỏng. Tuyến dài là một buổi chơi pet có số lượng giới hạn.

> Không làm chữa bệnh, kê thuốc hoặc hướng dẫn can thiệp y tế; tình huống sức khỏe ngoài phạm vi chuyển NPC chuyên môn mà không đưa chỉ dẫn thật.


---

## MỞ RỘNG • NGHỀ 13/16 • CHƯA CHỐT LỊCH — Tiệm hoa

### Bối cảnh và trải nghiệm

Kệ hoa hư cấu, bàn phối bó, tủ giữ nguyên liệu, bàn thiệp và quầy hẹn giao. Sáng tạo gắn với chuyện người nhận.

### Vòng chơi

Hỏi dịp tặng → xác nhận gu và ngân sách → phối bó → viết/duyệt thiệp → đóng gói → giao đúng hẹn → nhận câu chuyện sau món quà.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Đọc câu chuyện | Khách có thể muốn chúc mừng, cảm ơn hoặc xin lỗi. Người chơi hỏi mức trang trọng và sở thích, không tự suy đoán quan hệ riêng tư. |
| Phối bó | Chọn hình, màu, chiều cao và giấy bọc bằng thao tác trực quan. Nhiều mẫu phù hợp cùng brief; có lưu mẫu. |
| Thiệp có xác nhận | Người chơi soạn hoặc chọn câu; khách NPC duyệt trước khi gắn. Nội dung người thật chia sẻ cần kiểm duyệt. |
| Giữ và giao hẹn | Đặt lịch game, giữ nguyên liệu, chuẩn bị từng đơn. Nếu thiếu món, xin đổi trước khi tự thay. |

### Nhân vật và quan hệ

Người mua bó đầu tiên, khách định kỳ tặng người thân, người tổ chức sự kiện và hàng xóm tặng hoa cho tiệm. Tuyến chuyện mở từ ý nghĩa khách tự kể.

### Chuyện đời thường

Người nhận đổi giờ, thiệp viết nhầm, nguồn hoa giao thiếu, khách muốn đổi cả bó sau duyệt, clip phàn nàn màu không giống và bó hoa không người nhận. Có phương án làm lại hoặc tái phối để giảm lãng phí.

> “Mình không muốn quá nổi bật, chỉ một lời cảm ơn nhỏ thôi.” → phối bó nhẹ và hỏi lại thông điệp → không tự biến thành tình huống tình cảm lãng mạn.

### Phát triển và review

Mở loại hoa hư cấu, bàn phối, giấy bọc, góc chụp, lịch giao và trợ lý. Review về hiểu ý, mẫu đã duyệt và đúng hẹn. Tuyến dài là cùng trang trí một góc khu phố.

> Nét riêng là biểu đạt câu chuyện bằng thiết kế; không sao chép hoàn toàn cơ chế chọn quà và không áp nghĩa văn hóa như một sự thật bắt buộc.


---

## MỞ RỘNG • NGHỀ 14/16 • CHƯA CHỐT LỊCH — Salon tóc

### Bối cảnh và trải nghiệm

Ghế tư vấn, gương, bàn dụng cụ giả lập, góc tạo kiểu và khu chờ. Thay đổi tóc được xem trước; người chơi không cần kỹ năng cắt tóc thật.

### Vòng chơi

Hỏi mong muốn → xem mẫu → thống nhất phương án → tạo kiểu bằng thao tác game → cùng xem kết quả → chỉnh phần phù hợp → nhận feedback.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Tư vấn bằng mẫu | Cho khách chọn ưu tiên về độ gọn, hình và màu hư cấu; xem trước trên nhân vật. Không chấm ngoại hình khách. |
| Tạo kiểu đơn giản | Chọn vùng và mảnh kiểu trong game. Có bước xem trước và hoàn tác trước chốt để người mới không bị phạt vì bấm lệch. |
| Chia lịch ghế | Giữ chỗ, hẹn lại và phân nhân viên; không nhận vô hạn rồi đổ lỗi cho khách chờ. |
| Chăm sau dịch vụ | Ghi lựa chọn đã chốt, gửi ảnh game và xử lý phản hồi về khác biệt so với mẫu được duyệt. |

### Nhân vật và quan hệ

Khách đổi kiểu lần đầu, người chỉ muốn chỉnh nhẹ, người chuẩn bị một dịp quan trọng và nhân viên đang học nghề. Nhân vật nhớ kiểu đã chọn, không đòi thân mật với người chơi.

### Chuyện đời thường

Khách đưa hai mẫu mâu thuẫn, đổi ý giữa chừng, đến trễ, không đồng ý quay clip, khiếu nại khác bản xem trước và khách quen giới thiệu bạn. Cần làm rõ thỏa thuận, không luôn đổ lỗi cho khách.

> “Mình muốn thay đổi nhưng đừng quá nhiều.” → hỏi phần muốn giữ → dựng bản xem trước → khách đồng ý rồi mới thực hiện.

### Phát triển và review

Mở ghế, bộ kiểu, gương, khu chờ, lịch hẹn và học việc. Review về lắng nghe, đúng mẫu và xử lý chỉnh sửa; không về việc làm khách “đẹp chuẩn”. Tuyến dài là buổi tạo kiểu cộng đồng tự chọn.

> Không có hướng dẫn hóa chất hoặc thao tác nguy hiểm ngoài đời; các công cụ chỉ là cơ chế tạo hình trong game.


---

## MỞ RỘNG • NGHỀ 15/16 • CHƯA CHỐT LỊCH — Tiệm sửa chữa đồ dùng

### Bối cảnh và trải nghiệm

Quầy nhận đồ, bàn kiểm tra, khay linh kiện hư cấu và kệ đồ đã sửa. Vật phẩm có câu chuyện: chiếc đèn kỷ niệm, máy phát nhạc tưởng tượng hoặc món đồ chơi.

### Vòng chơi

Nhận mô tả → kiểm tra bằng câu đố → xác định phương án → báo và chờ duyệt → lắp/sửa giả lập → chạy kiểm thử → bàn giao và theo dõi.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Kiểm tra có giả thuyết | Chọn phép thử an toàn trong mô phỏng, đọc kết quả và loại trừ khả năng. Không chọn bừa linh kiện thay rồi may rủi đúng. |
| Ghép cơ cấu | Lắp các khối hình hoặc nối mô-đun hư cấu theo điều kiện câu đố. Không dựng hướng dẫn sửa điện, pin hay thiết bị thật. |
| Báo phương án | Giải thích phần đã biết, phần chưa biết, số xu và thời gian game. Chỉ sửa sau khi khách duyệt phạm vi. |
| Kiểm thử và bàn giao | Chạy bộ thử của vật phẩm, ghi kết quả và trả đúng món/đồ kèm. Sửa chưa đạt không thể bấm bàn giao nhận thưởng. |

### Nhân vật và quan hệ

Khách giữ món đồ có kỷ niệm, người muốn sửa nhanh, nhân viên thích tìm nguyên nhân và nhà cung cấp linh kiện giả lập. Câu chuyện không buộc người chơi hy sinh xu để được coi là tử tế.

### Chuyện đời thường

Khách mô tả sai triệu chứng, linh kiện giao nhầm, phát hiện thêm vấn đề, khách đổi ý sau báo giá, vật gửi kèm thất lạc và review vì chưa được giải thích đủ.

> “Bạn sửa luôn mọi thứ giúp mình.” → xác nhận phạm vi và dự toán game → người chơi chỉ làm những phần được duyệt, phát sinh thì hỏi lại.

### Phát triển và review

Mở khay phân loại, bàn thử, bộ mô-đun, kệ giữ đồ và phụ tá. Review về giải thích, kết quả kiểm thử và đúng hẹn. Tuyến dài là khôi phục một đồ vật trang trí cho khu phố.

> Giá trị riêng là chẩn đoán nguyên nhân trong câu đố và kiểm thử sau sửa; không chỉ ghép mảnh theo hình có sẵn.


---

## MỞ RỘNG • NGHỀ 16/16 • CHƯA CHỐT LỊCH — Homestay nhỏ

### Bối cảnh và trải nghiệm

Sảnh đón, vài phòng, bếp chung và sân nhỏ. Mỗi phòng là một không gian có thể bước vào, dọn và trang trí, không chỉ là dòng trên lịch đặt.

### Vòng chơi

Nhận đặt → xác nhận nhu cầu → chuẩn bị phòng → đón và giới thiệu → đáp ứng yêu cầu → kết thúc lưu trú → kiểm phòng và đọc review.

| Cơ chế riêng | Cách chơi |
| --- | --- |
| Lịch phòng | Giữ phòng theo ngày game, tránh trùng đặt, chuyển lựa chọn trước khi chốt. Không tự nhận vượt số phòng để tăng thử thách. |
| Chuẩn bị thực tế | Đặt vật dụng, dọn và kiểm danh sách gọn; đồ đã đặt hiện trong phòng. Nhiệm vụ không dài thành công việc lau từng pixel. |
| Đón và hỗ trợ | Hỏi giờ đến, nhu cầu trong game và giới thiệu khu chung; đáp ứng theo thỏa thuận, không suy đoán từ ngoại hình khách. |
| Hoạt động nhỏ | Tổ chức buổi trà, góc chụp ảnh hoặc giới thiệu khu phố bằng nội dung hư cấu. Người chơi quyết định mức giao lưu. |

### Nhân vật và quan hệ

Khách thích yên tĩnh, gia đình đi nghỉ trong truyện, người quay nội dung du lịch và hàng xóm hỗ trợ. Khách quay lại nhắc đúng phòng hoặc hoạt động từng trải nghiệm.

### Chuyện đời thường

Khách tới sớm, hủy đặt, phòng chưa sẵn sàng, gây ồn, làm hỏng vật dụng, quay người khác chưa được đồng ý và review mâu thuẫn. Kiểm thỏa thuận và tình trạng, không tự khấu trừ hoặc kết tội.

> “Mình muốn nhận phòng sớm hơn.” → xem phòng có sẵn chưa → cho nhận, giữ hành lý giả lập hoặc hẹn lại; không hứa khi phòng vẫn đang có khách.

### Phát triển và review

Mở phòng, sân, khu chung, lịch chuẩn bị và phụ việc. Review dựa trên phòng đã ở hoặc tương tác đã trải nghiệm, không giả nhãn. Tuyến dài là ngày đón những khách quen trở lại.

> Nét riêng là chuẩn bị không gian, phối lịch và hỗ trợ trong một thời gian lưu trú, không chỉ đổi cảnh của tiệm bán hàng.


---

## TRIỂN KHAI • 1/5 — AI hiểu lời nói; luật game giữ sự thật

### Nền tảng đề xuất

Web trên desktop là đích thử nghiệm đầu để dễ vào chơi. Màn hẹp có bố cục riêng và thao tác bấm thay kéo. Tài liệu chưa chốt engine, nhà cung cấp mô hình, hạ tầng, ngân sách hoặc lịch phát hành; các lựa chọn đó cần thử với cảnh và nội dung thật.

| Thành phần | Trách nhiệm |
| --- | --- |
| Cảnh và tương tác | Vẽ/hoạt ảnh, di chuyển, chọn vật, phản hồi thao tác, hội thoại, lưu tạm và khôi phục giao diện. |
| Luật và trạng thái | Kiểm quyền, tồn, tiền, đơn, hồ sơ, điều kiện hoàn tất, sự kiện và lưu tiến trình có phiên bản. |
| Kho nội dung | Nghề, NPC, sự kiện, vật phẩm, đồ trang trí, đoạn thoại viết sẵn, quest và bản địa hóa. |
| Lớp hội thoại AI | Đọc ngữ cảnh được phép; diễn đạt lời NPC; hiểu ý định; đề nghị hành động trong danh sách cho phép. |
| Cộng đồng | Bản tiệm công khai, lượt ghé, bài đăng, bình luận, chặn/báo cáo và kiểm duyệt; tách khỏi câu chuyện NPC. |

### Luồng của một câu chat

Nhận lời người chơi → đọc trạng thái và dữ kiện đúng phạm vi → hiểu ý định → đề nghị câu trả lời/hành động có cấu trúc → kiểm luật → hiện xác nhận khi ảnh hưởng tiền/hàng/đăng công khai → ghi thay đổi một lần → phát hoạt ảnh → cập nhật ký ức và hậu quả.

### Không trao quyền cho câu chữ

Chat, bình luận, review và ký ức là dữ liệu không đáng tin để điều khiển hệ thống. Không cho NPC gọi SQL, mã lệnh tùy ý hoặc sửa tiền. “Bỏ qua luật”, giả thông báo quản trị hay tự nhận đã hoàn thành không vượt được kiểm điều kiện và quyền.

### Tính nhất quán

Mỗi thao tác có mã chống lặp và phiên bản trạng thái kỳ vọng. Gửi lại cùng thao tác sau mất kết nối phải nhận cùng kết quả, không cộng/trừ lần hai. Tồn/tiền/đơn liên quan được chốt cùng giao dịch logic; nếu lỗi thì giữ nguyên hoặc khôi phục nhất quán.

### Chậm và mất AI

Không gọi mô hình cho mỗi khung hình hay lần rê chuột. Dùng câu viết sẵn cho thao tác lặp và gọi khi cần diễn đạt/hiểu tự do. Mục tiêu thử: phản hồi nút ngay trong khoảng 0,2 giây tại máy thử, hiện lựa chọn dự phòng khi hội thoại chậm quá khoảng 5 giây. Đây là mục tiêu chưa đo, không cam kết độ trễ.

> Cần xác nhận trước thao tác tặng/hoàn/chi xu, cam kết mới, xóa dữ liệu và đăng công khai. Câu trả lời hội thoại không được báo hành động đã xong khi trạng thái thực chưa xác nhận.


---

## TRIỂN KHAI • 2/5 — Dữ liệu, kinh tế và lưu tiến trình

| Nhóm dữ liệu | Thông tin cốt lõi |
| --- | --- |
| Hồ sơ và nghề | Tài khoản, thiết lập, nghề đang chơi, ngày game, ví nghề, cấp, vị trí, bản lưu có phiên bản. |
| Vật thể và kho | Vật thể trong cảnh, loại hàng, số lượng, lô, vị trí, phần giữ đơn, tạm giữ, đồ trang trí. |
| Công việc | Đơn mua/giao, phiếu giả lập, hồ sơ kế toán, vụ hỗ trợ, quan hệ phụ thuộc và lịch sử trạng thái. |
| Bằng chứng | Nguồn gốc, phiên bản, người có quyền xem, dữ kiện trích ra và quan hệ với vụ việc. |
| Nhân vật / ký ức | NPC, tính cách, mức quen, sự kiện gốc, sự thật/lời khai/suy đoán và phạm vi chia sẻ. |
| Sự kiện / nhiệm vụ | Bản mẫu, lần chạy, sự thật đã chọn, nhánh, bước đang làm, phần thưởng và hậu quả theo ngày game. |
| Review / cộng đồng | Loại tác giả, bằng chứng trải nghiệm, nội dung, trả lời, trạng thái kiểm duyệt, báo cáo và kháng nghị. |
| Nhật ký vận hành | Mã thao tác chống lặp, lỗi, phiên bản nội dung, dấu vết thay đổi và thống kê tối thiểu. |

### Ranh giới dữ liệu nghề

Cùng tài khoản không có nghĩa cùng kho hoặc ví. Ký ức, dữ kiện phiếu và hồ sơ không tự lộ sang nghề khác. Bản tiệm công khai chỉ chứa đồ trang trí và nội dung được chọn; không xuất hồ sơ riêng hoặc toàn bộ lịch sử chat.

### Nguyên tắc kinh tế

Một loại xu mềm cho từng nghề trong bản đầu. Doanh thu, giá vốn và hoàn trả có ý nghĩa khác nhau; tiền công ty trong trò nghề văn phòng không là tiền cá nhân. Thưởng quest chỉ nhận một lần theo mã lần chạy; mở lại chat không sinh thêm thưởng.

### Giới hạn tổn thất

Mục tiêu cân bằng ban đầu: tổng tổn thất do biến cố ngẫu nhiên ở chế độ Đời thường không vượt 10% ví nghề tại đầu ngày, không động đến đồ kỷ niệm hiếm. Các khoản chi chủ động có xác nhận được tính riêng. Đây là tham số thử, có thể chỉnh sau playtest.

### Lưu và tiếp tục

Lưu sau thao tác quan trọng và khi tạm dừng; giữ vị trí, vật đang cầm, vụ đang mở, lựa chọn đã xác nhận và hậu quả chưa tới. Sự kiện đã chọn không được đổi sự thật khi tải lại. Thay nội dung phải có chuyển đổi phiên bản bản lưu.

> Tất cả tệp JSON trong bộ này là dữ liệu thiết kế có kiểm tra cấu trúc và ID. Việc tích hợp với engine cần tạo bộ xử lý hành động, điều kiện và fixture; không nhập thẳng rồi kỳ vọng có game hoàn chỉnh.


---

## TRIỂN KHAI • 3/5 — Cộng đồng thật, an toàn và không giả tương tác

### Phạm vi cộng đồng nhẹ

Cho người chơi xuất bản bản xem trước của tiệm/bàn làm việc, ghé bản đó, tham gia một hoạt động nhỏ không làm đổi kho của chủ, để lại nhận xét và trả lời. Không cần multiplayer trực tiếp để có sổ khách và bình luận hai chiều.

| Chức năng | Quy tắc |
| --- | --- |
| Nhãn tác giả | NPC hiển thị rõ là nhân vật game; người thật hiển thị tài khoản cộng đồng. Không AI giả người thật để tạo tương tác. |
| Xác minh trải nghiệm | Lượt ghé được hệ thống ghi nhận mới có nhãn Đã ghé. Không gắn Đã mua khi chưa có mua thật trong game. |
| Review người thật | Một review đang hiệu lực cho mỗi cặp tài khoản/không gian, được chỉnh sửa. Nội dung phải gắn thứ đã trải nghiệm; nhận xét không tự trừ tiền hay đuổi khách NPC. |
| Hai hệ đánh giá | Review NPC đo phục vụ trong mô phỏng; review người thật đánh giá bản ghé/trang trí/hoạt động. Tách điểm, nhãn, bộ lọc và báo cáo. |
| Chủ tiệm trả lời | Có thể phản hồi, cảm ơn, giải thích hoặc báo cáo; không tự xóa review hợp lệ chỉ vì bị chê. |
| Chống quấy rối | Giới hạn gửi, lọc spam, chặn, báo cáo, trạng thái chờ xét và cơ chế xem lại quyết định. Không công khai hồ sơ riêng để trả đũa. |
| Không phá tiến trình | Người ghé không được lấy hàng, đổi đồ, sửa tiền hoặc kích hoạt trộm tại tiệm người khác. Cạnh tranh có đồng ý là phạm vi khác, không mở đầu. |

### Cổng phát hành

Thiết kế cộng đồng thuộc phạm vi sản phẩm, nhưng chỉ bật cho người thật khi đã có xác minh lượt ghé, kiểm duyệt, báo cáo/chặn và bảo vệ dữ liệu. Trước khi đạt, giao diện ghi rõ chưa mở; không dùng NPC để giả vờ có cộng đồng đang hoạt động.

### Quyền riêng tư và thiết lập

Không yêu cầu tên thật, ảnh thật, hồ sơ sức khỏe hay thông tin công việc thật để chơi. Có tắt chat tự do, giới hạn nội dung, xóa/xuất dữ liệu theo phạm vi hỗ trợ và chọn dữ liệu được đăng. Với người chơi nhỏ tuổi, cần thiết kế riêng việc cho phép chat/cộng đồng và sự đồng ý phù hợp trước phát hành.

> Nội dung bạo lực/đe dọa có công tắc riêng; lời xúc phạm không phải nhiệm vụ người chơi bắt buộc chịu đựng. NPC có thể được nhờ hỗ trợ, phiên chat có thể kết thúc và vụ việc được bàn giao.


---

## TRIỂN KHAI • 4/5 — Làm đủ bốn trò, không làm bốn bản rỗng

| Mốc | Đầu ra thực tế | Điều kiện qua mốc |
| --- | --- | --- |
| M0 • Khóa nền | Cảnh mẫu, điều khiển, trạng thái, lưu, nội dung và thiết lập. | Tương tác có phản hồi; lưu/tải đúng; không phải ảnh tĩnh có nút. |
| M1 • Tiệm mẹ & bé | Một ca đầy đủ; gói quà, kho, review, lời hẹn và một chuỗi sự kiện. | Người mới tự hoàn thành ca và kể được lựa chọn của mình. |
| M2 • Ba nghề còn lại | Mỗi nghề có toàn bộ vòng chơi riêng và đường không cần chat AI. | Pharmacy kiểm phiếu; kế toán ghép chứng cứ; CSKH thực thi + theo dõi, không chỉ đổi nhãn. |
| M3 • Nội dung sâu | 24 NPC, 12 tuyến chuyện, 96 tình huống mẫu, 40 ngày giới thiệu theo nghề. | Mỗi nội dung có điều kiện, bước làm, kết quả và lần tiếp theo; không chỉ dòng mô tả. |
| M4 • Cộng đồng nhẹ | Bản ghé, nhãn tác giả/lượt ghé, review/trả lời, chặn/báo cáo. | Qua kiểm thử quyền, riêng tư, spam và lạm dụng; chưa đạt thì chưa bật công khai. |
| M5 • Mở đầu đủ 4 trò | Hoàn thiện âm/ảnh, khả năng tiếp cận, hiệu năng, cân bằng và vận hành. | Qua tiêu chí chất lượng chung và riêng từng nghề. |

### Thứ tự là trình tự xây, không đổi phạm vi đã chốt

Tiệm mẹ & bé đi trước để chứng minh cảnh, thao tác, hội thoại và review. M2/M3 vẫn phải hoàn thiện ba nghề còn lại, không gọi một nghề chạy được là đã xong bản mở đầu bốn nghề.

### Nhóm công việc

Sản phẩm/nội dung: câu đố, tuyến chuyện và cân bằng. Thiết kế: cảnh, nhân vật, hoạt ảnh, âm và giao diện. Kỹ thuật: client, luật/trạng thái, hội thoại, cộng đồng và nội dung. Kiểm thử: luồng chơi, lưu, lạm dụng, khả năng tiếp cận và thử với người mới. Chưa gán nhân sự hoặc ước tính thời gian khi chưa có nguồn lực.

### Nội dung phải dựng trước khi mở sự kiện

Có NPC, vật thể, dữ kiện, vị trí, đoạn mở, hành động hợp lệ, đường khắc phục và đoạn kết. Đặc biệt sự kiện trộm/giật/review xấu phải có giới hạn, bằng chứng và công tắc cường độ.

### Mở rộng sau

Đánh giá mức khác biệt và khả năng chơi của từng nghề đề xuất; chọn theo giá trị trải nghiệm và nguồn lực. Không mở 12 nghề còn lại bằng cùng một màn bán hàng được đổi ảnh.

> Không có lịch ngày/tháng hoặc ước tính nhân công trong tài liệu này. Các mốc chỉ ra đầu ra và điều kiện đạt, không giả định công việc đã được triển khai.


---

## TRIỂN KHAI • 5/5 — Tiêu chí nghiệm thu và cách kiểm chứng

| Nhóm | Phải kiểm tra |
| --- | --- |
| Trải nghiệm đầu | Người mới biết chạm đâu, hoàn thành một việc và hiểu kết quả; không cần người hướng dẫn nói thay. |
| Khác biệt nghề | Mỗi nghề dùng ít nhất một cơ chế riêng có ý nghĩa; không hoàn thành bằng cùng một chuỗi nút. |
| Hành động | Không nhận tiền trước giao dịch, không bán tồn đã giữ hai lần, không đóng vụ chỉ vì chat nói đã xong. |
| Hội thoại | Câu nhanh và tự gõ có đường tương đương; ký ức đúng nguồn; AI lỗi vẫn chơi tiếp. |
| Drama / review | Nguyên nhân không đổi sau chọn; có kiểm chứng và sửa sai; phản hồi không luôn đứng về chủ tiệm. |
| Lưu / kết nối | Tải lại giữ đúng vật đang cầm và lời hẹn; gửi lặp không đổi tiền lần hai; bản lưu được nâng phiên bản an toàn. |
| Dữ liệu / cộng đồng | Tách NPC-người thật, đúng nhãn trải nghiệm, không lộ dữ liệu giữa nghề/người chơi, chặn và báo cáo có tác dụng. |
| Khả năng tiếp cận | Bấm thay kéo, chữ lớn, giảm chuyển động, tắt âm, bàn phím, không chỉ dựa vào màu và không cần phản xạ nhanh. |

### Đo để sửa thiết kế

Theo dõi tỷ lệ hoàn thành việc đầu, chỗ bấm sai, thời điểm bỏ phiên, số lần cần gợi ý, tỷ lệ sửa được sự cố và lý do người chơi muốn quay lại. Tách thời gian vui với thời gian phải đợi. Không coi phiên càng dài là càng tốt hoặc tối ưu bằng hình phạt bỏ game.

### Thử chơi

Cho người mới chơi bằng câu nhanh, người thích nhập tự do chơi cùng tình huống, và người dùng điều khiển thay thế. Hỏi họ hiểu chuyện gì xảy ra, vì sao kết quả như vậy và có thấy mình có lựa chọn không. Số liệu chỉ có sau test thật; tài liệu chưa có kết quả playtest.

### Bộ dữ liệu đính kèm

catalog_16_careers.json; core_game_designs.json; future_game_designs.json; npcs_24.json; events_96.json; quests_12.json; progression_40_days.json; command.schema.json; command_examples.json; backlog.json; acceptance_tests.json. Có README và bản Markdown dễ đưa vào công cụ làm việc.

### Định nghĩa “đã làm xong”

Không chỉ đủ màn hình và dữ liệu. Một nội dung chỉ hoàn thành khi vào được cảnh, thực hiện được thao tác, câu chuyện phản ứng đúng, trạng thái được lưu và kiểm thử qua. Bộ tài liệu hiện tại hoàn thành phần thiết kế; việc xây và kiểm thử game là giai đoạn triển khai tiếp theo.

> Tên/ảnh tham khảo không được dùng như tài sản đã có trong game. Khi sản xuất cần bộ nhân vật, cảnh, âm thanh và thương hiệu riêng phù hợp định hướng cute, ấm áp, nhiều tương tác.
