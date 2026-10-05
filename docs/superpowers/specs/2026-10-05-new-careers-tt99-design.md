# Đợt nghề mới và chứng chỉ TT99

Yêu cầu ngày 05/10: triển khai bản sửa lag trước, sau đó bổ sung nghề mới đã hoãn và chia TT99 thành chứng chỉ từng phần/toàn bộ. Đợt tính năng này chưa có lệnh deploy riêng.

## Phương án đề xuất

Dùng nghề riêng có quy trình chơi riêng, cùng nền tảng lượt làm, trả tiền, đánh giá và lưu tiến độ hiện tại. Tách TT99 khỏi nhóm chứng chỉ chung, tái dùng nguyên bài học và bài tập đang có. Mỗi phần hoàn thành cộng 10 điểm phần trăm cơ hội được nhận ở nghề TT99; đủ 10 phần có nút nhận việc chắc chắn.

Phương án chỉ thêm tên nghề vào hoạt động đi chơi không đáp ứng yêu cầu nghề nghiệp. Phương án xây chín minigame thời gian thực hoàn toàn riêng tốn nhiều công và tăng tải giao diện; đề xuất quy trình có thao tác đặc trưng, nội dung theo nghề, tải module khi mở và giữ UI di động gọn trước.

## Chín nghề trong backlog

| Nghề | Vòng chơi chính | Kết quả và thao tác đặc trưng |
|---|---|---|
| Bác sĩ | Tiếp nhận → hỏi bệnh → xem kết quả → chọn hướng xử lý → dặn dò | Hồ sơ hư cấu, lựa chọn theo thông tin ca, chuyển ca khi vượt khả năng; không nhập liều thuốc tự do |
| Ca sĩ | Nhận chương trình → chọn bài/phong cách → tập → biểu diễn | Ghép bài với khán giả, giữ nhịp các đoạn, xử lý yêu cầu và sự cố sân khấu |
| Diễn viên | Đọc vai → chọn phục trang → tập thoại → diễn cảnh | Chọn lời thoại và biểu cảm theo kịch bản, quay lại đoạn chưa đạt |
| YouTuber | Nhận chủ đề → viết dàn ý → quay → dựng → đăng video trong game | Chọn cảnh, thứ tự dựng, tiêu đề và ảnh bìa; lượt xem và phản hồi theo chất lượng, không đăng ra nền tảng thật |
| MC | Nhận lịch → xếp chương trình → dẫn từng mục → xử lý phát sinh | Chọn câu dẫn, gọi đúng người, chuyển mục đúng thứ tự và ứng biến |
| Quản lý khách sạn | Nhận đặt phòng → xếp phòng → điều phối dọn → nhận/trả phòng | Nhiều hạng phòng, số đêm, yêu cầu khách; khác nghề homestay hiện có |
| Shop giày | Hỏi mẫu/cỡ → lấy hàng → thử → đóng gói/thanh toán | Tồn kho theo mẫu và cỡ, đổi đúng cỡ, không trừ kho trước khi hoàn tất |
| Tiệm sách cũ | Nhập sách → kiểm tra tình trạng → định giá → tư vấn/bán | Thể loại, độ cũ, giá mua/bán và yêu cầu sách của khách |
| Vận hành karaoke | Nhận nhóm → xếp phòng → chuẩn bị thiết bị → phục vụ → tính giờ | Sức chứa, thời lượng, đồ gọi thêm, kiểm tra hóa đơn; khác hoạt động đi hát |

Mỗi nghề xuất hiện trong màn đổi nghề và có nơi làm trên phố; được lưu độc lập, có ca chơi và hướng dẫn thao tác đầu tiên. Đơn phải tạo lại ổn định từ seed, kiểm tra ở server, trả tiền một lần khi hoàn thành. Tích hợp hỗ trợ thuê nhân viên/ghé thăm theo khả năng thực của từng nghề; không hiển thị nút chưa hoạt động. Không tự thêm quảng cáo thông báo hay gửi trả lời người chơi trong đợt này.

## TT99: 10 phần và hai cấp chứng chỉ

Hiện tại TT99 là khóa `vn_business` gồm 60 bài thuộc 15 chương; nghề dùng là `group_accounting` tại Sông Hồng Group. Giữ các ID bài và đáp án đã học, chia giao diện chứng chỉ thành 10 phần sau:

1. Phạm vi, chính sách, chứng từ và sổ (framework + documents).
2. Tiền và ngoại tệ (money).
3. Phải thu và dự phòng (receivables).
4. Tồn kho và giá thành (inventory).
5. Tài sản, dự án và phân bổ (longassets + projects).
6. Đầu tư (investments).
7. Công nợ, vốn và phân phối (liabilities + equity).
8. Lương và kế toán thuế (payrolltax).
9. Doanh thu, chi phí và khóa sổ (revenues + results).
10. Báo cáo tài chính và chuyển đổi (financialreports + transition).

Hoàn thành một phần nghĩa là đã đọc và làm đúng tất cả bài tập của các bài thuộc phần đó, được server kiểm tra. Chỉ mở bài hoặc sửa dữ liệu client không được tính. Mỗi phần cấp chứng chỉ riêng trong game; đủ 10 cấp chứng chỉ toàn bộ. Các chứng chỉ là ghi nhận trong game, không phải bằng nghề ngoài đời.

Tiến độ và chứng chỉ cũ giữ nguyên. Người đã có chứng nhận TT99 toàn khóa tiếp tục đủ điều kiện toàn bộ, không phải học lại. Khóa kế toán cơ bản giữ riêng. Không thêm rào cản phải thi lại toàn khóa sau khi đã hoàn thành 10 phần.

## Ứng tuyển nghề TT99

- 0 phần: hướng dẫn tới khóa học.
- 1–9 phần: được mở hồ sơ ứng tuyển. Nếu điểm phỏng vấn đạt, nhận thư mời như thường; nếu chưa đạt, cơ hội bổ sung từ chứng chỉ lần lượt 10–90%, server quyết định một lần cho mỗi hồ sơ, tải lại không quay lại kết quả.
- 10 phần/chứng chỉ toàn bộ: nút “Nhận việc kế toán TT99” bỏ qua phỏng vấn, hiển thị hợp đồng và chỉ chuyển nghề khi người chơi bấm nhận. Không tự bỏ nghề hiện tại khi nộp bài cuối.
- Không cộng thêm chứng chỉ kế toán chung để vượt 100%. Phần đã hoàn thành không tăng lại khi học lại.
- Người đang làm nghề này giữ việc và tiến độ hiện tại. Lương và tiền đã có không bị sửa bởi việc chia chứng chỉ.

Giao diện có thẻ “Chứng chỉ Thông tư 99”, tiến độ n/10, các phần đã đạt/chưa đạt, nút tiếp tục bài gần nhất và nút xem nơi tuyển dụng. Mỗi phần cho thấy phần còn thiếu; không buộc người chơi tự đoán chương/bài nào cần học tiếp.

## Kiểm chứng và thứ tự

1. Deploy và xác nhận bản lag 1.7.13.
2. Triển khai TT99 và kiểm tra tiến độ cũ, ranh giới 0/1/9/10 phần, phỏng vấn/retry, nhận việc và lưu/tải.
3. Triển khai nghề theo ba nhóm: dịch vụ bán hàng (khách sạn/giày/sách/karaoke), sáng tạo (YouTube/ca sĩ/diễn viên/MC), bác sĩ.
4. Kiểm tra mỗi nghề từ mở → ca đầu → hoàn thành → trả tiền → lưu/tải; thao tác sai không mất tiền/nhân đôi hàng. Kiểm tra nghề cũ và gói release không đổi nhiệm vụ đang dở.
5. Kiểm tra browser di động: nút vừa tay, không bị che, tự cuộn hợp lý, chỉ nạp nghề đang mở. Báo phần hoàn thành và phần còn thiếu bằng kết quả thực, chưa tự deploy đợt nghề mới.
