# Kế hoạch mở rộng kinh doanh từ cơ chế hiện tại

## Chốt triển khai ngày 13/10/2026

Người dùng yêu cầu đưa lên hệ thống. Triển khai ba mức phí cơ sở 500/2.000/5.000, kiểm tra từ ba quầy và hạn 72 giờ thực kể từ khi giao biên bản trong phiên chơi. Bản đầu không thêm ngưỡng cấp 3 cho xe đẩy/sạp: cấp cơ bản cho nhiều quầy nhỏ, nâng cao cho tối đa hai ki-ốt, chuỗi cho từ ba ki-ốt. Đây là phạm vi triển khai đã chọn; các ý tưởng công cụ chuỗi/tăng giá trị sạp vẫn để đợt sau.

Quầy bị hạn chế dừng nhận khách mới; đơn đã nhận trước hạn vẫn được hoàn tất. Dùng chính sách dừng chi phí tự động khi quầy bị hạn chế, tương tự quầy tạm dừng hiện có, và hiển thị rõ điều này; không tạo khoản nợ thuê/lương mới chỉ do chế tài. Việc bán đơn tồn vẫn ghi giá vốn, thuế và chi phí trực tiếp như hiện tại. Chủ cũ chưa có quyền vận hành phù hợp còn một quầy đã sở hữu để kiếm học phí. Không mở lại quầy chủ tự đóng.

Kiểm thử và triển khai phải xác nhận bản lưu chứng chỉ/hồ sơ tương thích; dùng bản rollback có mã mới nhưng tắt điều kiện/cưỡng chế, không quay thẳng về mã cũ không biết chứng chỉ. Dữ liệu DB ngày 12/10 là bằng chứng thiết kế, không phải danh sách tài khoản để sửa trực tiếp.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tạo tiến trình làm nghề → quầy nhỏ → học kinh doanh → tiệm lớn, tận dụng hệ thống Quầy riêng và chứng chỉ hiện có.

**Architecture:** Dùng lại trạng thái chứng chỉ trong journey, bài thi do máy chủ chấm và các lệnh mở/nâng cấp quầy. Một mô-đun điều kiện kinh doanh dùng chung cho kiểm tra trên máy chủ và dữ liệu hiển thị. Bổ sung hồ sơ kiểm tra theo chủ và điều kiện nhận đơn trong vòng vận hành để xử lý quá hạn; không đổi công thức lợi nhuận chỉ vì có chứng chỉ.

**Tech Stack:** Python, JavaScript ES modules, unittest và các Node/browser harness hiện có.

**Trạng thái cập nhật 13/10:** Đã triển khai mã và đang nghiệm thu/phát hành theo phạm vi chốt ở đầu tài liệu. Các checklist bên dưới là kế hoạch gốc; bằng chứng kiểm thử và phạm vi phát hành được ghi trong báo cáo triển khai 2.0.6.

**Cập nhật sau tính kinh tế:** Xem [phân tích lợi ích và hoàn vốn](2026-10-12-business-economics.md). Mức thực trả theo chỉ số giá hiện tại là 550 / 2.200 / 5.500 xu. Rút khuyến nghị áp cấp 3 cho mọi cơ sở thứ ba: ví dụ xe đẩy trà sữa thứ ba mất khoảng 28–37 giờ thu hồi khoản đầu tư mới, trong khi ki-ốt thứ ba khoảng 15 giờ. Bảng dưới dùng ngưỡng đề xuất mới là ba ki-ốt cho cấp 3; ngưỡng chuỗi quầy nhỏ lớn hơn vẫn cần tính tiếp. Chứng chỉ theo bản này chưa tăng lãi trực tiếp. Sạp cũng cần xem lại giá trị so với hai xe đẩy trước khi chốt gameplay.

**Quyết định mới về chủ cũ:** Theo ý kiến người dùng ngày 12/10/2026, công an trong game kiểm tra chủ nhiều quầy và yêu cầu học có trả phí. Bỏ phương án miễn chứng chỉ vô thời hạn cho cơ sở đã mở. Đề xuất kiểm tra từ ba quầy, cho 72 giờ bổ sung kể từ khi giao thông báo trong phiên chơi, quá hạn hạn chế quầy vượt quyền; chi tiết tại mục 5. Ngưỡng/thời hạn là đề xuất, chưa phải gameplay đã triển khai.

## 1. Nền hiện tại

Đối chiếu checkout main tại 35e97593 và ref origin/main có sẵn tại 3f303053. Đây là bằng chứng mã nguồn local, không phải xác nhận phiên bản đang chạy trên production. Các file Python về quầy và chứng chỉ được xét không khác giữa hai ref này.

| Cơ chế | Đã có | Cách tận dụng |
|---|---|---|
| Mở Quầy riêng | Hành trình từ chương 3, làm 10 việc đúng nghề, ví không âm, đủ tiền | Giữ làm điều kiện nền |
| Mặt bằng | Xe đẩy, sạp chợ, ki-ốt | Dùng làm các mốc trưởng thành |
| Mở rộng | Nâng quầy lên mặt bằng lớn hơn; trả chênh lệch mặt bằng và thiết bị | Thêm điều kiện chứng chỉ trước giao dịch |
| Vận hành | Nhân viên, hàng tồn, quỹ, két, chi phí, tình huống | Giữ cơ chế hiện có; đưa vào bài học |
| Nhiều quầy | Không có giới hạn số quầy trong cấu hình hiện tại | Thêm điều kiện cho việc mở thêm, không đặt giới hạn số lượng mới |
| Chứng chỉ | Tự học miễn phí qua ngày sau, lớp trả phí thi ngay, thi 6 câu đúng 4 đạt | Thêm nhóm chứng chỉ kinh doanh bắt buộc đóng học phí, dùng lại lớp trả phí và bộ chấm thi |
| Giấy chứng nhận | Tên người chơi, điểm, ngày cấp, số hiệu, xem và tải ảnh | Dùng lại giấy hiện tại |

## 2. Quy tắc bản đầu

Ba chứng chỉ kế tiếp nhau, dùng quyền lợi riêng (`hire=False`), không cộng tỷ lệ xin việc:

| Cấp | Chứng chỉ và mã đề xuất | Học phí cơ sở | Quyền mở rộng |
|---|---|---|---|
| 1 | Kinh doanh cơ bản — `business_basics` | 500 xu | Mở/nâng lên sạp; mở nhiều xe đẩy/sạp theo ngưỡng chuỗi nhỏ sẽ chốt |
| 2 | Quản lý cửa tiệm — `business_advanced` | 2.000 xu | Mở/nâng lên ki-ốt, tối đa hai ki-ốt; không tính xe đẩy thành ki-ốt |
| 3 | Quản lý chuỗi — `business_chain` | 5.000 xu | Từ ba ki-ốt; ngưỡng cho chuỗi xe đẩy/sạp lớn cần tính tiếp |

Phải thi đạt cấp trước mới đăng ký cấp sau. Học phí mỗi cấp là khoản riêng, không phải tổng cộng hoặc khoản bù chênh lệch. Học từ đầu đến cấp 3 hết 7.500 xu ở hệ số giá 1 nếu đậu ngay, chưa gồm vốn mở tiệm. Không bắt buộc mua mặt bằng cấp thấp trước khi học cấp cao.

| Hành động | Điều kiện mới |
|---|---|
| Mở xe đẩy khi chưa sở hữu quầy nào | Không bắt chứng chỉ |
| Mở/nâng lên sạp | Cấp 1; kiểm tra thêm ngưỡng chuỗi quầy nhỏ khi đã chốt |
| Mở/nâng lên ki-ốt | Cấp 2; nếu sau giao dịch có từ ba ki-ốt cần cấp 3 |
| Mở xe đẩy thứ hai | Cấp 1 |
| Mở cơ sở thứ ba trở đi | Xét loại mặt bằng và quy mô, không mặc định cấp 3 |
| Tiếp tục vận hành, tạm đóng/mở lại quầy đã có | Áp dụng hồ sơ kiểm tra, thời hạn và quyền vận hành tại mục 5 |

Mọi trường hợp vẫn áp dụng điều kiện tiền, kinh nghiệm và trạng thái giao dịch hiện có. Chứng chỉ thuộc người chơi, dùng cho mọi quầy; không phải học lại cho từng cửa hàng. Lấy cấp yêu cầu cao nhất giữa mặt bằng đích và quy mô sau giao dịch. Đếm quầy đang sở hữu, kể cả đang tạm đóng. Nâng cấp không tăng tổng số cơ sở nhưng có thể làm tăng số ki-ốt nên phải xét lại ngưỡng chuỗi. Không ép mua lần lượt đủ ba mặt bằng: người đủ chứng chỉ và vốn có thể mở ki-ốt trực tiếp.

Một người bán hết quầy rồi mở lại một xe đẩy vẫn thuộc diện chưa sở hữu quầy và được mở không cần chứng chỉ. Đây là lựa chọn chủ ý để cho phép làm lại sau thất bại; không cần lưu cờ “đã từng mở quầy”.

Chưa thêm điều kiện số ngày có lãi, gia hạn giấy, lệ phí đăng ký, mức phạt thiếu giấy hoặc thưởng phần trăm lợi nhuận ở bản đầu.

## 3. Học và thi

Mỗi cấp có nội dung riêng tương ứng số tiền bỏ ra:

- Cấp 1: vốn ban đầu; giá vốn và giá bán; nhập hàng và hao hụt; lương và tiền thuê; quỹ tiệm so với tiền cá nhân; khách phàn nàn.
- Cấp 2: dự toán nâng cấp; điểm hòa vốn; vốn lưu động; chọn lượng tồn kho; bố trí và chi phí nhân sự; xử lý sự cố vận hành tiệm lớn.
- Cấp 3: so sánh kết quả từng cơ sở; ngân sách mở chi nhánh; phân bổ vốn; kế hoạch hàng hóa từng nơi; nhu cầu nhân sự toàn chuỗi; ưu tiên phục hồi cơ sở hoạt động kém. Bài học dùng các thao tác game đã hỗ trợ, không giả định có cơ chế tự động điều chuyển hàng/nhân viên.

- Mỗi cấp có 6 bài đọc ngắn, mỗi bài có một tình huống lấy từ cơ chế game; tổng cộng 18 bài.
- Mỗi cấp có 6 câu luyện tập có giải thích và ngân hàng thi riêng 12 câu khác câu luyện tập, rút 6 câu theo hệ thống hiện có. Cấp cao dùng tình huống quản lý nhiều khoản chi/cơ sở, không chỉ đổi tên đề cơ bản.
- Đúng 4/6 thì đậu. Đề thi có gợi ý theo cơ chế hiện tại; không thêm bài thao tác bắt buộc trong lần phát hành này.
- Ba khóa kinh doanh chỉ nhận đăng ký lớp trả phí: học phí cơ sở lần lượt 500, 2.000 và 5.000 xu, đi qua hệ số giá hiện tại. Học phí bao gồm học, một lần thi và cấp giấy nếu đạt; được học và thi ngay trong ngày theo cơ chế lớp hiện có.
- Tài liệu và câu luyện tập xem miễn phí. Muốn thi lấy chứng chỉ phải đóng học phí; cả ba nhóm mới không có đường đăng ký tự học miễn phí để vào thi. Những chứng chỉ hiện có khác giữ nguyên chế độ học.
- Học lại để thi lại: dùng cơ chế nửa học phí hiện có, lần lượt 250, 1.000 và 2.500 xu ở hệ số giá 1; giá thực tế là nửa học phí cấp tương ứng đã điều chỉnh, làm tròn lên. Chứng chỉ không hết hạn, trượt cấp cao không mất cấp đã đạt; thi lại không làm mất chứng chỉ đã đạt. Không thu lại học phí khi dùng giấy để mở tiệm khác.
- Chỉ trừ học phí khi đăng ký thành công qua phương thức thanh toán được game hỗ trợ. Thiếu tiền thì hiển thị số còn thiếu và giữ nguyên tiến độ; người chơi vẫn có thể làm nghề hoặc vận hành quầy nhỏ để kiếm học phí. Bỏ khóa đã đăng ký không hoàn học phí, theo cơ chế hiện tại; thông báo rõ trước khi xác nhận bỏ.
- Hiển thị đúng quyền lợi từng cấp theo bảng trên và điều kiện chứng chỉ cấp trước; không hiển thị nhầm thông báo tăng tỷ lệ được tuyển dụng.
- Giấy dùng mẫu hiện có. Treo giấy trong cảnh tiệm là phần trang trí để sau, không phải điều kiện hoàn thành bản đầu.

## 4. Luồng người chơi

Trong Quầy riêng, thêm mục “Lộ trình mở tiệm”. Mỗi điều kiện hiển thị riêng: chương, việc đã làm đúng nghề, chứng chỉ, tiền cần có. Không chỉ hiện một nút khóa không giải thích.

Ví dụ mở sạp trà sữa: Chương 3 đã đạt; kinh nghiệm 10/10; chưa có chứng chỉ; tiền hiển thị theo giá mở quầy thực tế. Cạnh điều kiện chứng chỉ có nút “Học kinh doanh” dẫn thẳng đến khóa tương ứng. Trang khóa học hiển thị học phí thực tế do máy chủ tính, nút “Đăng ký học”, và ghi rõ phí đã gồm một lần thi/cấp giấy. Tách học phí với vốn mở quầy để người chơi biết phải chuẩn bị cả hai khoản; cập nhật lại tiền còn lại sau khi đóng học phí.

Giữ lựa chọn nghề/mặt bằng khi người chơi đi học rồi trở lại. Thi đạt thì cập nhật điều kiện ngay, nhưng người chơi vẫn phải xem chi phí và xác nhận mở/nâng cấp như hiện tại. Nếu đang học khóa khác, giải thích cần thi xong hoặc chủ động bỏ khóa đó; không tự hủy việc học.

Màn hình nâng cấp tiếp tục cho xem mức chi phí vận hành mới. Chứng chỉ không có nghĩa người chơi đã đủ vốn.

## 5. Người chơi và bản lưu cũ

Đối chiếu DB production ngày 12/10/2026, lượt đọc 04:54–04:56 UTC+7: 6.336 tài khoản đăng ký có 275 chủ quầy, tổng 403 quầy; 69 chủ có ít nhất hai quầy, 20 chủ có ít nhất ba quầy, 10 chủ có ít nhất ba ki-ốt. Hai chủ có 12 ki-ốt mỗi người. Đây là dữ liệu quan sát; không tự cấp chứng chỉ hoặc thay đổi tài sản trong lượt kiểm tra. Số liệu bản lưu khách được báo cáo riêng, không coi mỗi bản lưu là một người duy nhất.

Đã kiểm tra bổ sung 54.598 bản lưu khách, hoàn tất 05:02 UTC+7: 31 bản có tổng 32 quầy, chỉ một bản có hai quầy và không có bản nào từ ba quầy. Chi tiết phạm vi, chứng chỉ và quy mô tại [báo cáo chủ quầy hiện có](2026-10-12-business-existing-owners.md).

- Từ ba quầy sở hữu, công an kiểm tra theo chủ và lập một hồ sơ nếu thiếu giấy. Không dựa vào xác suất sự kiện ngẫu nhiên khiến một số chủ né mãi; kiểm tra được giao khi người chơi trở lại game. Một/hai quầy cũ chưa thuộc đợt kiểm tra này; mở rộng vẫn xét điều kiện mới.
- Biên bản ghi quy mô, cấp còn thiếu, từng học phí thực tế và nút đi học. Đề xuất hạn 72 giờ thực từ lần giao thông báo đầu trong phiên chơi, không tính từ deploy, không chờ người chơi bấm xác nhận để trì hoãn. Trong hạn mọi quầy cũ tiếp tục bán; không phạt tiền lần đầu.
- Quá hạn thì dừng đơn mới ở phần quầy vượt quyền vận hành; cho chủ chọn quầy giữ hoạt động trong giới hạn. Nếu chưa chọn, máy chủ dùng thứ tự ổn định và thông báo rõ. Riêng chủ cũ chưa có cấp nào được giữ một quầy hiện có để kiếm học phí trong đợt chuyển đổi; không biến thành quyền mở ki-ốt mới miễn chứng chỉ. Tiêu chí xác định chủ cũ dựa trên mốc triển khai phía máy chủ, không do client khai báo.
- Bảo toàn nhân viên, hàng tồn, két, quỹ, trang bị và lịch sử; không hạ mặt bằng/tịch thu hay tự trừ học phí. Đơn đã nhận xử lý xong. Thu két, quản lý hàng/quỹ/nhân viên, bán bớt tài sản vẫn được dùng. Cần chốt và hiển thị rõ thuê/lương tiếp tục phát sinh khi bị hạn chế trước khi phát hành.
- Thi đạt thì đánh giá lại ngay và gỡ hạn chế tương ứng; không tự mở quầy chủ chủ động đóng. Học lần lượt các cấp, có thể phục hồi từng phần quyền; không nộp phạt thay việc học. Bán bớt quầy giảm quy mô thì đánh giá lại; đóng/mở tạm thời không giảm số sở hữu, đặt lại hạn hoặc né hạn chế.
- Chủ 12 ki-ốt phải học các khóa còn thiếu đến cấp 3 ngay trong đợt kiểm tra dù không mở tiệm thứ 13. Từ chưa có giấy đến đủ ba cấp tốn 8.250 xu theo chỉ số giá đã tính nếu đậu ngay, không nhân học phí với 12. Không tự cấp giấy hoặc đổi chứng chỉ nghề cũ thành giấy kinh doanh.
- Bổ sung trạng thái hồ sơ theo chủ: phiên bản chính sách, thời điểm giao, hạn, trạng thái và lựa chọn quầy. Lưu và xử lý lệnh có tính lặp an toàn; read/public view không tự tạo vi phạm hoặc trừ tiền. Không làm bản lưu cũ thành không hợp lệ vì thiếu giấy; các trường mới có mặc định/migration.
- Khi quyết toán thời gian offline phải tách tại hạn: chỉ chặn đơn phát sinh sau hạn, không xóa doanh thu hợp lệ trước hạn. Việc gia hạn, đổi chính sách và tính phí duy trì cần quy tắc rõ, không tự suy diễn trong triển khai.
- Chuẩn bị rollback đọc được cả ba mã chứng chỉ và hồ sơ kiểm tra. Công tắc tắt cưỡng chế gỡ hạn chế do kiểm tra nhưng giữ trạng thái chủ tự đóng; không giả định rollback thẳng về bản cũ là an toàn.

## 6. Phân rã triển khai bản đầu

Các đường dẫn dưới đây tương đối với repository. Khi thực thi, chọn checkout cập nhật và cô lập thay đổi theo quy trình dự án; không dùng nguyên ref cũ chỉ vì kế hoạch dẫn nó.

### Công việc 1: Nội dung chứng chỉ

Files: `game/certificate_content.py`, `game/certificates.py`, `public/js/v4/certificates.js`; tests `tests/test_certificates.py`, `tests/test_business_certificates.py` mới.

- [ ] Biên soạn mỗi cấp đủ 6 bài, 6 câu luyện tập và 12 câu thi; tổng cộng 18 bài, 18 câu luyện tập và 36 câu thi; ghi đáp án và giải thích từng câu theo luật game.
- [ ] Thêm ba nhóm `business_basics`, `business_advanced`, `business_chain`, gắn các nghề có trong danh mục Quầy riêng và quyền lợi tương ứng; tránh thay đổi ánh xạ chứng chỉ xin việc. Cấu hình nhóm chỉ cho `class`, mặc định nhóm cũ vẫn cho `class` và `self`; trả chế độ được phép và cấp tiên quyết trong catalogue để giao diện và máy chủ dùng chung.
- [ ] Trong `jr_cert_enrol`, từ chối `self` hoặc đăng ký cấp cao khi chưa đậu cấp trước cho khóa kinh doanh trước bước trừ tiền hoặc tạo khóa; không chỉ ẩn nút trên trình duyệt. Giá cơ sở tương ứng 500 / 2.000 / 5.000 xu; dùng hàm học phí và học lại hiện có. Giữ quyền xem bài/câu luyện tập miễn phí.
- [ ] Kiểm tra đóng đúng học phí lần đầu/học lại khi hệ số giá bằng 1 và khác 1, thiếu tiền không trừ tiền/không tạo khóa, yêu cầu đăng ký lặp không thu hai lần, gửi trực tiếp `self` bị từ chối. Chế độ tự học của chứng chỉ cũ vẫn hoạt động.
- [ ] Kiểm tra thời điểm mở thi, 3/6 trượt và 4/6 đạt, thi lại, giữ chứng chỉ đã đạt, một khóa tại một thời điểm; tải lại giữa khóa giữ tiến độ và không phải trả lần nữa. Bỏ khóa tuân theo luật không hoàn phí hiện có.
- [ ] Kiểm tra đăng ký lần lượt ba cấp, từ chối nhảy cấp trước thu phí, trượt cấp cao vẫn giữ quyền cấp thấp, tổng học phí 7.500 xu khi đậu mỗi cấp lần đầu ở hệ số giá 1.
- [ ] Kiểm tra giấy chứng nhận, tên khóa và lời chúc mừng đúng quyền lợi, không cộng xu hoặc nhân hệ số lợi nhuận.

### Công việc 2: Điều kiện mở và nâng cấp

Files: `game/business_progression.py` mới; `game/quay.py`; tests `tests/test_business_progression.py` mới, `tests/test_quay.py`, `tests/test_quay_fb295.py`.

- [ ] Tạo một bộ đánh giá điều kiện, nhận hành động mở/nâng cấp và mặt bằng đích; trả danh sách điều kiện, lý do thiếu và trạng thái được phép.
- [ ] Chốt ngưỡng chuỗi xe đẩy/sạp trước triển khai. Quy tắc đang đề xuất: mặt bằng `xe=0`, `sap=1`, `kiot=2`; nhiều quầy tối thiểu cấp 1, từ ba ki-ốt cấp 3. Xét trạng thái sau cả mở mới và nâng cấp; quầy tạm đóng vẫn được tính. Đóng/mở lại tuân theo hồ sơ kiểm tra, không đặt lại hạn.
- [ ] Gọi bộ đánh giá trong `jr_quay_open` và `jr_quay_upgrade` trước bước trừ vốn/thay mặt bằng; public view dùng cùng kết quả để tránh lệch giao diện và máy chủ.
- [ ] Kiểm thử người mới, người có chứng chỉ, chủ quầy cũ, mở thêm xe đẩy, mở thẳng ki-ốt và bán hết rồi làm lại. Gửi lệnh trực tiếp từ client cũng không bỏ qua điều kiện.
- [ ] Kiểm thử cấp 1 không mở được ki-ốt; cấp 2 chưa mở/nâng thành ki-ốt thứ ba; không bắt cấp 3 chỉ vì xe đẩy thứ ba; quầy tạm đóng vẫn được tính. Quyền của chủ cũ chuyển theo thông báo, hạn và chứng chỉ tại mục 5.
- [ ] Kiểm thử yêu cầu bị từ chối không trừ vốn/không mở hoặc nâng quầy. Phân biệt với việc quyết toán doanh thu theo thời gian vốn đã chạy khi nhận lệnh.
- [ ] Kiểm thử nâng cấp thành công giữ nhân viên, hàng tồn, két, quỹ và lịch sử; chống tạo quầy/trừ tiền hai lần theo cơ chế command hiện tại.

### Công việc 3: Giao diện lộ trình

Files: `public/js/v4/quay.js`, `public/js/v4/quay-manage.js` nếu màn quản lý chung cần cập nhật, `public/js/v4/certificates.js`, `game/guide_content.py`, các file dịch theo quy trình repository.

- [ ] Hiển thị checklist của đúng giao dịch đang chọn, tiền theo dữ liệu máy chủ, và nút vào khóa học tương ứng. Khóa kinh doanh hiển thị học phí, quyền lợi bao gồm trong phí, số tiền còn thiếu; không hiện lựa chọn thi bằng tự học miễn phí.
- [ ] Giữ ngữ cảnh khi quay về từ khóa học, làm mới trạng thái khi thi đạt, không tự mua hoặc tự nâng cấp.
- [ ] Thêm biên bản công an kiểm tra: cấp còn thiếu, từng học phí, thời hạn, nút học, số quầy được tiếp tục bán và chọn quầy. Phân biệt chủ tự đóng với hạn chế do quá hạn. Hiển thị chi phí duy trì nếu còn phát sinh.
- [ ] Kiểm tra ở 390×844 và desktop: mở quầy, thiếu tiền, thiếu chứng chỉ, đang học khóa khác, thi đạt và trở về xác nhận nâng cấp.

### Công việc 4: Kiểm tra và hạn chế vận hành

Files dự kiến: `game/business_progression.py`, `game/quay_business.py`, bộ xử lý lệnh/thông báo/lưu trữ hiện hành; tests `tests/test_business_inspections.py` mới. Kiểm tra lại điểm tích hợp trên checkout cập nhật khi thực hiện.

- [ ] Tạo hồ sơ theo chủ từ ba quầy, giao thông báo trong phiên chơi; không đặt lại thời hạn bởi refresh, lệnh lặp, tự đóng quầy hoặc tái đăng nhập. Tách kiểm tra chứng chỉ khỏi sự kiện ngẫu nhiên `shop_inspection` hiện tại vốn chỉ xử lý nhãn hàng.
- [ ] Chốt thời hạn đề xuất 72 giờ và chính sách thuê/lương của quầy bị hạn chế; kiểm chứng người thiếu tiền còn đường kiếm học phí. Không tự thêm tiền phạt.
- [ ] Áp dụng hạn chế đơn mới theo quyền; bảo toàn đơn đã nhận và thu nhập trước hạn. Quyết toán offline cắt đúng mốc thời gian. Giữ một quầy hiện có cho chủ cũ chưa đạt cấp nào theo ngoại lệ chuyển đổi.
- [ ] Thi đậu hoặc giảm quy mô đánh giá lại hồ sơ; gỡ hạn chế theo cấp đã đạt, không mở nhầm quầy chủ tự đóng. Không xóa hạn chỉ bằng thao tác đóng/mở.
- [ ] Kiểm thử trước/đúng/sau hạn, lần nhận thông báo đầu sau nhiều ngày offline, chọn quầy, đăng ký/thi trượt/thi đạt, bán bớt, nâng cấp ki-ốt thứ ba, lệnh lặp và tắt cưỡng chế. Không trừ phí kiểm tra hoặc học phí nếu chưa đăng ký.

### Công việc 5: Tương thích và phát hành

Files: tests `tests/test_business_storage.py`, `tests/test_business_progression.py`, tài liệu phát hành và cấu hình bật/tắt tính năng theo hạ tầng hiện có.

- [ ] Chuẩn bị bản lưu thử trước tính năng gồm xe đẩy/sạp/ki-ốt, nhiều quầy và một khóa đang học; chạy migrate, validate, export/import trong môi trường thử.
- [ ] Thêm fixture tổng hợp chủ 12 ki-ốt chưa có chứng chỉ: tải/lưu thành công; nhận một thông báo; trong hạn vận hành 12 tiệm; quá hạn hạn chế đúng phần vượt quyền; thi đạt khôi phục đúng hoạt động. Không truy thu phí theo quầy/tự cấp giấy; không sao chép bản lưu thật vào tests.
- [ ] Phát hành khóa học trả phí và checklist trước khi bật điều kiện bắt buộc; thông báo trước để người chơi có thời gian kiếm học phí, đăng ký học và thi. Ngay từ lúc phát hành khóa đã yêu cầu đóng học phí.
- [ ] Chuẩn bị công tắc máy chủ cho điều kiện mở rộng và riêng cho cưỡng chế sau kiểm tra; tắt vẫn giữ khóa học, chứng chỉ và hồ sơ. Tắt cưỡng chế phục hồi phần bị hạn chế, không thay đổi quầy tự đóng. Khi bật lại không tạo hạn hồi tố bất ngờ.
- [ ] Chạy các suite quầy, chứng chỉ, nâng cấp, lưu trữ và UI liên quan; sửa dữ liệu fixture chỉ khi đúng quy tắc mới, không xóa kiểm tra hồi quy.
- [ ] Trước bật production, xác nhận bản rollback đọc được bản lưu mới và bộ kiểm tra chạy trên DB thử, không dùng DB người chơi thật.

Lệnh kiểm tra mục tiêu sau khi đã tạo tests, chạy từ root repository:

```text
python -m unittest tests.test_business_certificates tests.test_business_progression tests.test_business_inspections tests.test_certificates tests.test_certificates_afford tests.test_quay tests.test_quay_fb295 tests.test_business_storage
node tests/quay_manage.mjs
```

Kỳ vọng: toàn bộ kiểm thử qua; browser walkthrough hoàn tất luồng mở/nâng cấp sau khi thi đạt. Các lệnh trên là kế hoạch kiểm tra, chưa được chạy cho tính năng chưa triển khai.

## 7. Các lần mở rộng tiếp theo

| Đợt | Phạm vi | Điều kiện làm tiếp |
|---|---|---|
| 1 | Ba cấp chứng chỉ và học phí, checklist, điều kiện mở/nâng cấp, công an kiểm tra chủ nhiều quầy và thời hạn bổ sung | Chốt ngưỡng và chi phí khi hạn chế trước triển khai |
| 2 | Nội dung chuyên ngành cho đồ ăn/thức uống; treo giấy trong tiệm | Sau khi quan sát việc học và mở tiệm không gây bỏ cuộc đáng kể |
| 3 | Công cụ quản lý chuỗi sâu hơn, giao diện tổng quan và mục tiêu hiệu quả vận hành | Sau khi đánh giá nhu cầu quản lý nhiều quầy và dữ liệu lãi/lỗ đủ tin cậy |

Đợt 2 ưu tiên khóa chuyên ngành tự chọn, có lợi ích trong tình huống kiểm tra/vệ sinh; không mặc định thêm một lớp khóa bắt buộc thứ hai. Không tạo chứng chỉ riêng cho từng món.

Ba cấp kinh doanh và kiểm tra chủ nhiều quầy thuộc đợt 1; không áp mặc định cấp 3 cho mọi cơ sở thứ ba. Đợt 3 mở rộng công cụ thực hành quản lý, không thu thêm phí để nhận lại quyền đã mở.

Đợt 3 chưa khóa mở rộng theo “có lãi vài ngày”: doanh thu đang tính theo thời gian máy chủ, nên cần chốt kỳ kế toán, chi phí được tính và cách xử lý thời gian offline trước khi biến lợi nhuận thành điều kiện. Không dùng số dư két hay tiền chủ góp vào làm bằng chứng có lãi.

## 8. Đo lường và tiêu chí nghiệm thu

Đo số người xem điều kiện, đăng ký học trả phí thành công, bị thiếu học phí, thi đậu, mở quầy đầu tiên và mở rộng thành công, phân tách theo cấp chứng chỉ. Phân biệt người mới/người có tiệm và các lý do bị chặn; tái dùng telemetry hiện có, không đưa tên hoặc số tiền chi tiết của người chơi vào sự kiện nếu không cần.

So sánh tỷ lệ chuyển đổi và thời gian từ đủ kinh nghiệm đến mở tiệm trước/sau khi bật điều kiện; thêm số biên bản đã giao, đăng ký học trong hạn, quá hạn và hoàn tất. Chưa đặt mục tiêu phần trăm khi chưa có baseline; nếu xuất hiện lỗi lưu, mất tiền hoặc chặn sai quyền vận hành thì tắt cưỡng chế và sửa lỗi.

Nghiệm thu bản đầu: người mới có thể mở xe đẩy không chứng chỉ; đóng học phí, thi đạt rồi mở rộng theo cấp; chủ cũ nhiều quầy nhận biên bản và thời hạn thực, quá hạn chỉ hạn chế đúng phần vượt quyền, học xong khôi phục đúng phần hoạt động; thiếu tiền vẫn xem tài liệu và có nguồn kiếm tiền; yêu cầu trực tiếp không bỏ qua học phí, điều kiện hoặc hạn chế; giấy chứng nhận xem được; chỉ thu đúng phí đăng ký đã xác nhận, bảo toàn tài sản và bản lưu.
